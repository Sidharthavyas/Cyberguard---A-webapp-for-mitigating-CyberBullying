"""
Discord client for CyberGuard - Moderate Discord server messages.
Uses Discord REST API (HTTP) — no gateway bot connection needed.
Works inside FastAPI's async event loop without blocking.
"""

import asyncio
import logging
import os
import aiohttp
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"

# Vercel proxy for HF Spaces (discord.com is blocked at network level)
# Set DISCORD_PROXY_URL to your Vercel deployment, e.g. https://cyberguard-a-webapp-for-mitigating.vercel.app/api/discord/proxy
DISCORD_PROXY_URL = os.getenv("DISCORD_PROXY_URL")
DISCORD_PROXY_SECRET = os.getenv("DISCORD_PROXY_SECRET", "")
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # seconds — delays: 1s, 2s, 4s


class DiscordModerationClient:
    """Discord REST API client for message moderation."""

    def __init__(self, bot_token: str, guild_ids: Optional[List[str]] = None):
        """
        Initialize Discord REST client.

        Args:
            bot_token: Discord bot token from Developer Portal
            guild_ids: Optional list of server IDs to monitor (None = all)
        """
        self.bot_token = bot_token
        self.guild_ids = guild_ids or []
        self.headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info("Discord REST client initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with proper timeout."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ---- REST helpers with retry + rate-limit handling ----
    
    def _prepare_request(self, method: str, path: str, json_data: Optional[Dict] = None) -> tuple[str, str, Dict, Optional[Dict]]:
        """
        Prepares the request URL, method, headers, and body.
        If DISCORD_PROXY_URL is set, formats the request to go through the Vercel proxy.
        Returns: (actual_url, actual_method, headers, body)
        """
        headers = {}
        
        if DISCORD_PROXY_URL:
            # Route through Vercel proxy
            actual_url = DISCORD_PROXY_URL
            actual_method = "POST"
            if DISCORD_PROXY_SECRET:
                headers["x-proxy-secret"] = DISCORD_PROXY_SECRET
                
            body = {
                "method": method.upper(),
                "path": path
            }
            if json_data:
                body["body"] = json_data
                
            return actual_url, actual_method, headers, body
        else:
            # Direct connection
            actual_url = f"{DISCORD_API}{path}"
            return actual_url, method.upper(), headers, json_data

    async def _get(self, path: str) -> Optional[any]:
        """
        GET request to Discord API with retry and rate-limit handling.
        Retries up to MAX_RETRIES times with exponential backoff.
        """
        url, method_name, extra_headers, body = self._prepare_request("GET", path)
        
        for attempt in range(MAX_RETRIES):
            session = await self._get_session()
            try:
                # We use session.request because method might be POST if using proxy
                async with session.request(method_name, url, headers=extra_headers, json=body) as resp:
                    # Rate-limited — wait and retry
                    if resp.status == 429:
                        data = await resp.json()
                        retry_after = data.get("retry_after", 1)
                        # Vercel proxy forwards Discord's retry-after header too
                        if resp.headers.get("retry-after"):
                            retry_after = float(resp.headers.get("retry-after"))
                        
                        logger.warning(
                            f"Discord rate limited on GET {path} — "
                            f"retrying after {retry_after}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if resp.status == 200:
                        return await resp.json()
                    else:
                        resp_body = await resp.text()
                        logger.error(
                            f"Discord API GET {path} → {resp.status}: {resp_body}"
                        )
                        return None

            except aiohttp.ClientConnectorError as e:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.error(
                    f"Discord API connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e} "
                    f"— retrying in {delay}s"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error("Discord API connection failed after all retries")
                    return None

            except asyncio.TimeoutError:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.error(
                    f"Discord API timeout on GET {path} (attempt {attempt + 1}/{MAX_RETRIES}) "
                    f"— retrying in {delay}s"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                else:
                    return None

            except Exception as e:
                logger.error(f"Discord API request failed: {e}")
                return None

        return None

    async def _delete(self, path: str) -> bool:
        """DELETE request to Discord API with retry and rate-limit handling."""
        url, method_name, extra_headers, body = self._prepare_request("DELETE", path)
        
        for attempt in range(MAX_RETRIES):
            session = await self._get_session()
            try:
                async with session.request(method_name, url, headers=extra_headers, json=body) as resp:
                    if resp.status == 429:
                        data = await resp.json()
                        retry_after = data.get("retry_after", 1)
                        if resp.headers.get("retry-after"):
                            retry_after = float(resp.headers.get("retry-after"))
                            
                        logger.warning(
                            f"Discord rate limited on DELETE {path} — "
                            f"retrying after {retry_after}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if resp.status in (204, 200):
                        return True
                    else:
                        resp_body = await resp.text()
                        logger.error(
                            f"Discord API DELETE {path} → {resp.status}: {resp_body}"
                        )
                        return False

            except aiohttp.ClientConnectorError as e:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.error(
                    f"Discord API connection error on DELETE (attempt {attempt + 1}/{MAX_RETRIES}): {e} "
                    f"— retrying in {delay}s"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                else:
                    return False

            except Exception as e:
                logger.error(f"Discord API delete failed: {e}")
                return False

        return False

    async def _put(self, path: str, json_data: Optional[Dict] = None) -> bool:
        """PUT request to Discord API with retry and rate-limit handling."""
        url, method_name, extra_headers, body = self._prepare_request("PUT", path, json_data)
        
        for attempt in range(MAX_RETRIES):
            session = await self._get_session()
            try:
                async with session.request(method_name, url, headers=extra_headers, json=body) as resp:
                    if resp.status == 429:
                        data = await resp.json()
                        retry_after = data.get("retry_after", 1)
                        if resp.headers.get("retry-after"):
                            retry_after = float(resp.headers.get("retry-after"))
                            
                        logger.warning(
                            f"Discord rate limited on PUT {path} — "
                            f"retrying after {retry_after}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if resp.status in (200, 204):
                        return True
                    else:
                        resp_body = await resp.text()
                        logger.error(
                            f"Discord API PUT {path} → {resp.status}: {resp_body}"
                        )
                        return False

            except Exception as e:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.error(
                    f"Discord API PUT error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                else:
                    return False

        return False

    async def _patch(self, path: str, json: Optional[Dict] = None) -> Optional[any]:
        """PATCH request to Discord API with retry and rate-limit handling."""
        for attempt in range(MAX_RETRIES):
            session = await self._get_session()
            url = f"{DISCORD_API}{path}"
            try:
                async with session.patch(url, json=json) as resp:
                    if resp.status == 429:
                        data = await resp.json()
                        retry_after = data.get("retry_after", 1)
                        logger.warning(
                            f"Discord rate limited on PATCH {path} — "
                            f"retrying after {retry_after}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if resp.status in (200, 204):
                        return True
                    else:
                        body = await resp.text()
                        logger.error(
                            f"Discord API PATCH {path} → {resp.status}: {body}"
                        )
                        return False

            except Exception as e:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.error(
                    f"Discord API PATCH error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                else:
                    return False

        return False

    # ---- Public API ----

    async def get_bot_guilds(self) -> List[Dict]:
        """Get list of guilds the bot is in."""
        data = await self._get("/users/@me/guilds")
        return data if data else []

    async def get_guild_text_channels(self, guild_id: str) -> List[Dict]:
        """Get text channels in a guild."""
        data = await self._get(f"/guilds/{guild_id}/channels")
        if not data:
            return []
        # Filter to text channels only (type 0)
        return [ch for ch in data if ch.get("type") == 0]

    async def get_channel_messages(
        self, channel_id: str, limit: int = 50
    ) -> List[Dict]:
        """Fetch recent messages from a channel."""
        data = await self._get(f"/channels/{channel_id}/messages?limit={limit}")
        return data if data else []

    async def get_recent_messages(self, limit: int = 25) -> List[Dict]:
        """
        Fetch recent messages from all monitored guilds/channels.

        Args:
            limit: Max messages per channel

        Returns:
            List of message dicts with standardized fields
        """
        messages = []

        try:
            guilds = await self.get_bot_guilds()
            if not guilds:
                logger.warning(
                    "Discord bot is not installed in any server. "
                    "Please invite the bot using the OAuth URL."
                )
                return []

            for guild in guilds:
                gid = guild["id"]
                gname = guild.get("name", gid)

                # Skip if guild_ids specified and this one isn't in the list
                if self.guild_ids and gid not in self.guild_ids:
                    continue

                channels = await self.get_guild_text_channels(gid)
                logger.info(f"Guild '{gname}' ({gid}): found {len(channels)} text channels")

                if not channels:
                    logger.warning(
                        f"No text channels visible in '{gname}' — "
                        f"bot may be missing VIEW_CHANNEL permission"
                    )
                    continue

                for channel in channels:
                    cid = channel["id"]
                    cname = channel.get("name", cid)

                    try:
                        raw_msgs = await self.get_channel_messages(cid, limit=limit)
                    except Exception as e:
                        logger.warning(f"Error fetching #{cname}: {e}")
                        continue

                    if raw_msgs is None:
                        logger.warning(
                            f"  #{cname}: API returned None — "
                            f"bot probably missing READ_MESSAGE_HISTORY permission"
                        )
                        continue

                    # Diagnostic counters
                    total_raw = len(raw_msgs)
                    skipped_bot = 0
                    skipped_empty = 0

                    for msg in raw_msgs:
                        # Skip bot messages
                        author = msg.get("author", {})
                        if author.get("bot"):
                            skipped_bot += 1
                            continue
                        # Skip empty messages (images/embeds only)
                        content = msg.get("content")
                        if not content:
                            skipped_empty += 1
                            continue

                        messages.append(
                            {
                                "id": msg["id"],
                                "text": content,
                                "author": f"{author.get('username', 'unknown')}#{author.get('discriminator', '0')}",
                                "author_id": author.get("id", ""),
                                "channel": cname,
                                "channel_id": cid,
                                "guild": gname,
                                "guild_id": gid,
                                "timestamp": msg.get("timestamp"),
                                "platform": "discord",
                            }
                        )

                    kept = total_raw - skipped_bot - skipped_empty
                    logger.info(
                        f"  #{cname}: {total_raw} raw msgs → "
                        f"{kept} kept, {skipped_bot} bot, {skipped_empty} empty-content"
                    )

                    # If ALL messages have empty content, it's likely a missing
                    # MESSAGE CONTENT privileged intent
                    if total_raw > 0 and skipped_empty == total_raw - skipped_bot and kept == 0:
                        logger.error(
                            f"  ⚠ All non-bot messages in #{cname} have empty content! "
                            f"Enable MESSAGE CONTENT INTENT in Discord Developer Portal → "
                            f"Bot → Privileged Gateway Intents"
                        )

            logger.info(
                f"Fetched {len(messages)} Discord messages from {len(guilds)} guild(s)"
            )
            return messages

        except Exception as e:
            logger.error(f"Error fetching Discord messages: {e}")
            return []

    async def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a Discord message."""
        ok = await self._delete(f"/channels/{channel_id}/messages/{message_id}")
        if ok:
            logger.info(f"Deleted Discord message {message_id} in #{channel_id}")
        return ok

    async def ban_user(
        self, guild_id: str, user_id: str, reason: str = "Cyberbullying violation", delete_message_days: int = 7
    ) -> bool:
        """Ban a user from a guild."""
        ok = await self._put(
            f"/guilds/{guild_id}/bans/{user_id}",
            json={"reason": reason, "delete_message_days": delete_message_days},
        )
        if ok:
            logger.info(f"Banned user {user_id} from guild {guild_id}: {reason}")
        else:
            logger.error(f"Ban failed for user {user_id} in guild {guild_id}")
        return ok

    async def kick_user(
        self, guild_id: str, user_id: str, reason: str = "Cyberbullying violation"
    ) -> bool:
        """Kick a user from a guild."""
        ok = await self._delete(f"/guilds/{guild_id}/members/{user_id}")
        if ok:
            logger.info(f"Kicked user {user_id} from guild {guild_id}: {reason}")
        else:
            logger.error(f"Kick failed for user {user_id} in guild {guild_id}")
        return ok

    async def moderate_user(
        self, guild_id: str, user_id: str, action: str, reason: str = "Cyberbullying violation", **kwargs
    ) -> bool:
        """
        Apply moderation action to a user.

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            action: 'ban', 'kick', 'timeout', 'delete_message'
            reason: Reason for moderation
            **kwargs: Additional parameters (duration_minutes for timeout, message_id for delete)

        Returns:
            True if action succeeded
        """
        if action == "ban":
            return await self.ban_user(
                guild_id, user_id, reason,
                delete_message_days=kwargs.get("delete_message_days", 7)
            )
        elif action == "kick":
            return await self.kick_user(guild_id, user_id, reason)
        elif action == "timeout":
            return await self.timeout_user(
                guild_id, user_id,
                duration_minutes=kwargs.get("duration_minutes", 10)
            )
        elif action == "delete_message":
            message_id = kwargs.get("message_id")
            channel_id = kwargs.get("channel_id")
            if message_id and channel_id:
                return await self.delete_message(channel_id, message_id)
            else:
                logger.error("delete_message action requires message_id and channel_id")
                return False
        else:
            logger.error(f"Unknown moderation action: {action}")
            return False

    async def timeout_user(
        self, guild_id: str, user_id: str, duration_minutes: int = 10
    ) -> bool:
        """Timeout a user in a guild."""
        from datetime import datetime, timedelta, timezone

        until = (
            datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        ).isoformat()

        ok = await self._patch(
            f"/guilds/{guild_id}/members/{user_id}",
            json={"communication_disabled_until": until},
        )
        if ok:
            logger.info(f"Timed out user {user_id} for {duration_minutes}m")
        else:
            logger.error(f"Timeout failed for user {user_id} in guild {guild_id}")
        return ok


# Factory function
def get_discord_client(
    bot_token: str, guild_ids: Optional[List[str]] = None
) -> DiscordModerationClient:
    return DiscordModerationClient(bot_token, guild_ids)
