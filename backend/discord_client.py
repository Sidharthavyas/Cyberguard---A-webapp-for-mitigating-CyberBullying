"""
Discord client for CyberGuard - Moderate Discord server messages.
Uses Discord REST API (HTTP) — no gateway bot connection needed.
Works inside FastAPI's async event loop without blocking.

Includes DNS-over-HTTPS (Cloudflare) for HF Spaces where discord.com
cannot be resolved via normal OS-level DNS.
"""

import os
import ssl
import socket
import logging
import http.client
import json as _json
import aiohttp
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


def _resolve_discord_ip() -> Optional[str]:
    """
    Resolve discord.com via Cloudflare DNS-over-HTTPS (1.1.1.1).
    HF Spaces OS-level DNS can't resolve discord.com, so we manually
    query Cloudflare's DoH endpoint by IP (no DNS needed for that).
    """
    for dns_ip in ("1.1.1.1", "1.0.0.1"):
        try:
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(dns_ip, 443, timeout=5, context=ctx)
            conn.request(
                "GET",
                "/dns-query?name=discord.com&type=A",
                headers={"Accept": "application/dns-json"},
            )
            resp = conn.getresponse()
            data = _json.loads(resp.read())
            conn.close()

            for answer in data.get("Answer", []):
                if answer.get("type") == 1:  # A record
                    ip = answer["data"]
                    logger.info(f"Resolved discord.com via DoH ({dns_ip}) → {ip}")
                    return ip
        except Exception as e:
            logger.warning(f"DoH via {dns_ip} failed: {e}")

    return None


class _DiscordDNSResolver(aiohttp.abc.AbstractResolver):
    """
    Custom aiohttp resolver that uses a pre-resolved IP for discord.com.
    Falls back to normal DNS for everything else.
    """

    def __init__(self, discord_ip: str):
        self._discord_ip = discord_ip

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        if host in ("discord.com", "discordapp.com"):
            return [
                {
                    "hostname": host,
                    "host": self._discord_ip,
                    "port": port,
                    "family": family,
                    "proto": 0,
                    "flags": socket.AI_NUMERICHOST,
                }
            ]
        # Fall back to default system DNS
        infos = await aiohttp.DefaultResolver().resolve(host, port, family)
        return infos

    async def close(self) -> None:
        pass


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
        self._discord_ip: Optional[str] = None
        logger.info("Discord REST client initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with DoH DNS resolver."""
        if self._session is None or self._session.closed:
            # Resolve discord.com IP via DoH on first use
            if self._discord_ip is None:
                self._discord_ip = _resolve_discord_ip()

            connector = None
            if self._discord_ip:
                resolver = _DiscordDNSResolver(self._discord_ip)
                connector = aiohttp.TCPConnector(resolver=resolver)
                logger.info(f"Using DoH-resolved IP for Discord API: {self._discord_ip}")
            else:
                logger.warning("DoH resolution failed — trying system DNS")

            self._session = aiohttp.ClientSession(
                headers=self.headers, connector=connector
            )
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
        except aiohttp.ClientConnectorError as e:
            # DNS / connection failed — invalidate cached IP and retry next time
            logger.error(f"Discord API connection error: {e}")
            self._discord_ip = None
            await self.close()
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
                        # Try to get message content via alternative method
                        await self._try_alternative_message_fetch(cid, cname, limit, messages)

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

    async def _try_alternative_message_fetch(self, channel_id: str, channel_name: str, limit: int, messages: List[Dict]):
        """
        Try alternative methods to fetch message content when MESSAGE CONTENT INTENT is missing.
        This attempts to use webhook data or audit logs as fallback.
        """
        try:
            # Method 1: Try to get message content from audit logs (if available)
            audit_logs = await self._get_audit_logs(channel_id)
            if audit_logs:
                logger.info(f"  #{channel_name}: Found {len(audit_logs)} entries from audit logs")
                for log_entry in audit_logs:
                    if log_entry.get("content"):
                        messages.append({
                            "id": log_entry["id"],
                            "text": log_entry["content"],
                            "author": log_entry.get("author", "audit_log"),
                            "author_id": log_entry.get("author_id", ""),
                            "channel": channel_name,
                            "channel_id": channel_id,
                            "guild": log_entry.get("guild", "unknown"),
                            "guild_id": log_entry.get("guild_id", ""),
                            "timestamp": log_entry.get("timestamp"),
                            "platform": "discord",
                            "source": "audit_log"
                        })
                        
            # Method 2: Try webhook-based message fetching
            webhook_data = await self._get_webhook_messages(channel_id)
            if webhook_data:
                logger.info(f"  #{channel_name}: Found {len(webhook_data)} entries from webhooks")
                for webhook_msg in webhook_data:
                    messages.append({
                        "id": webhook_msg["id"],
                        "text": webhook_msg["content"],
                        "author": webhook_msg.get("author", "webhook"),
                        "author_id": webhook_msg.get("author_id", ""),
                        "channel": channel_name,
                        "channel_id": channel_id,
                        "guild": webhook_msg.get("guild", "unknown"),
                        "guild_id": webhook_msg.get("guild_id", ""),
                        "timestamp": webhook_msg.get("timestamp"),
                        "platform": "discord",
                        "source": "webhook"
                    })
                    
        except Exception as e:
            logger.warning(f"Alternative message fetch failed for #{channel_name}: {e}")
    
    async def _get_audit_logs(self, channel_id: str) -> List[Dict]:
        """Get audit logs for message deletions (may contain content)."""
        try:
            # Get guild ID from channel
            channel_info = await self._get(f"/channels/{channel_id}")
            if not channel_info:
                return []
                
            guild_id = channel_info.get("guild_id")
            if not guild_id:
                return []
                
            # Get audit logs for message deletions
            logs = await self._get(f"/guilds/{guild_id}/audit-logs?limit=50&action_type=72")  # MESSAGE_DELETE
            if not logs:
                return []
                
            formatted_logs = []
            for log in logs.get("audit_log_entries", []):
                if log.get("target_id") == channel_id or log.get("options", {}).get("channel_id") == channel_id:
                    formatted_logs.append({
                        "id": log.get("id"),
                        "content": log.get("options", {}).get("content", ""),
                        "author": log.get("user_tag", "audit_log"),
                        "author_id": log.get("user_id", ""),
                        "guild_id": guild_id,
                        "timestamp": log.get("created_at")
                    })
            
            return formatted_logs
        except Exception as e:
            logger.debug(f"Audit log fetch failed: {e}")
            return []
    
    async def _get_webhook_messages(self, channel_id: str) -> List[Dict]:
        """Get messages from webhooks in the channel."""
        try:
            webhooks = await self._get(f"/channels/{channel_id}/webhooks")
            if not webhooks:
                return []
                
            webhook_messages = []
            for webhook in webhooks:
                # Try to get recent webhook messages
                webhook_url = webhook.get("url")
                if webhook_url:
                    try:
                        # This is a simplified approach - in practice you'd need to query webhook-specific endpoints
                        webhook_messages.append({
                            "id": webhook.get("id"),
                            "content": f"Webhook message from {webhook.get('name', 'unknown')}",
                            "author": webhook.get("name", "webhook"),
                            "author_id": webhook.get("id"),
                            "timestamp": webhook.get("created_at")
                        })
                    except Exception:
                        continue
                        
            return webhook_messages
        except Exception as e:
            logger.debug(f"Webhook message fetch failed: {e}")
            return []
    
    async def ban_user(
        self, guild_id: str, user_id: str, reason: str = "Cyberbullying violation", delete_message_days: int = 7
    ) -> bool:
        """Ban a user from a guild."""
        session = await self._get_session()
        url = f"{DISCORD_API}/guilds/{guild_id}/bans/{user_id}"
        try:
            async with session.put(
                url, 
                json={
                    "reason": reason,
                    "delete_message_days": delete_message_days
                }
            ) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Banned user {user_id} from guild {guild_id}: {reason}")
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"Ban failed: {resp.status} {body}")
                    return False
        except Exception as e:
            logger.error(f"Failed to ban user: {e}")
            return False
    
    async def kick_user(
        self, guild_id: str, user_id: str, reason: str = "Cyberbullying violation"
    ) -> bool:
        """Kick a user from a guild."""
        session = await self._get_session()
        url = f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}"
        try:
            async with session.delete(
                url,
                json={"reason": reason}
            ) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Kicked user {user_id} from guild {guild_id}: {reason}")
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"Kick failed: {resp.status} {body}")
                    return False
        except Exception as e:
            logger.error(f"Failed to kick user: {e}")
            return False
    
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
        session = await self._get_session()
        url = f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}"
        try:
            async with session.patch(
                url, json={"communication_disabled_until": until}
            ) as resp:
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
