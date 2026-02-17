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

                        messages.append(
                            {
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
                            }
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
