"""
Discord client for CyberGuard - Moderate Discord server messages.
Uses Discord REST API (HTTP) — no gateway bot connection needed.
Works inside FastAPI's async event loop without blocking.
"""

import os
import logging
import aiohttp
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


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
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ---- REST helpers ----

    async def _get(self, path: str) -> Optional[any]:
        session = await self._get_session()
        url = f"{DISCORD_API}{path}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    body = await resp.text()
                    logger.error(f"Discord API GET {path} → {resp.status}: {body}")
                    return None
        except Exception as e:
            logger.error(f"Discord API request failed: {e}")
            return None

    async def _delete(self, path: str) -> bool:
        session = await self._get_session()
        url = f"{DISCORD_API}{path}"
        try:
            async with session.delete(url) as resp:
                if resp.status == 204:
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"Discord API DELETE {path} → {resp.status}: {body}")
                    return False
        except Exception as e:
            logger.error(f"Discord API delete failed: {e}")
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
                logger.warning("Bot is not in any guilds")
                return []

            for guild in guilds:
                gid = guild["id"]
                gname = guild.get("name", gid)

                # Skip if guild_ids specified and this one isn't in the list
                if self.guild_ids and gid not in self.guild_ids:
                    continue

                channels = await self.get_guild_text_channels(gid)

                for channel in channels:
                    cid = channel["id"]
                    cname = channel.get("name", cid)

                    try:
                        raw_msgs = await self.get_channel_messages(cid, limit=limit)
                    except Exception as e:
                        logger.warning(f"Error fetching #{cname}: {e}")
                        continue

                    for msg in raw_msgs:
                        # Skip bot messages
                        author = msg.get("author", {})
                        if author.get("bot"):
                            continue
                        # Skip empty messages (images/embeds only)
                        if not msg.get("content"):
                            continue

                        messages.append({
                            "id": msg["id"],
                            "text": msg["content"],
                            "author": f"{author.get('username', 'unknown')}#{author.get('discriminator', '0')}",
                            "author_id": author.get("id", ""),
                            "channel": cname,
                            "channel_id": cid,
                            "guild": gname,
                            "guild_id": gid,
                            "timestamp": msg.get("timestamp"),
                            "platform": "discord",
                        })

            logger.info(f"Fetched {len(messages)} Discord messages from {len(guilds)} guild(s)")
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

    async def timeout_user(
        self, guild_id: str, user_id: str, duration_minutes: int = 10
    ) -> bool:
        """Timeout a user in a guild."""
        from datetime import datetime, timedelta, timezone

        until = (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat()
        session = await self._get_session()
        url = f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}"
        try:
            async with session.patch(url, json={"communication_disabled_until": until}) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Timed out user {user_id} for {duration_minutes}m")
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"Timeout failed: {resp.status} {body}")
                    return False
        except Exception as e:
            logger.error(f"Failed to timeout user: {e}")
            return False


# Factory function
def get_discord_client(
    bot_token: str, guild_ids: Optional[List[str]] = None
) -> DiscordModerationClient:
    return DiscordModerationClient(bot_token, guild_ids)
