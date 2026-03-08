"""
Discord poller for CyberGuard - Background monitoring of Discord messages.
Uses the REST-based DiscordModerationClient (no gateway bot).
"""

import asyncio
import logging
from typing import Dict
from discord_client import get_discord_client, DiscordModerationClient
from platform_manager import PlatformPoller
from moderation import moderation_engine
from metrics import metrics
from websocket_manager import manager
import database as db

logger = logging.getLogger(__name__)


class DiscordPoller(PlatformPoller):
    """Polls Discord servers for messages and moderates them."""

    def __init__(self, credentials: Dict):
        """
        Initialize Discord poller.

        Args:
            credentials: Dict with 'bot_token' and optional 'guild_ids'
        """
        super().__init__("Discord")

        self.bot_token = credentials.get("bot_token")
        # Empty guild_ids means monitor ALL servers the bot is in
        self.guild_ids = credentials.get("guild_ids", [])  
        self.poll_interval = int(credentials.get("poll_interval", 60))  # Faster polling for real-time moderation

        if not self.bot_token:
            raise ValueError("Discord bot_token is required")

        # Initialize REST-based Discord client
        self.client: DiscordModerationClient = get_discord_client(
            self.bot_token, self.guild_ids
        )
        self.processed_messages: set = set()  # Track processed message IDs
        self._no_guilds_warned: bool = False  # Avoid spamming "no guilds" log

        logger.info(f"Discord poller initialized - monitoring ALL servers (interval: {self.poll_interval}s)")

    async def _poll_loop(self):
        """Main polling loop for Discord messages."""
        logger.info("Discord poller started (REST API mode)")

        while self.is_running:
            try:
                messages = await self._poll_once()

                # If no guilds were found, back off to avoid hammering
                if messages is None:
                    # messages=None signals "no guilds" condition
                    await asyncio.sleep(self.poll_interval * 5)
                else:
                    await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info("Discord poller cancelled")
                break
            except Exception as e:
                logger.error(f"Discord poller error: {e}")
                await asyncio.sleep(self.poll_interval)

        # Close HTTP session
        await self.client.close()
        logger.info("Discord poller stopped")

    async def _poll_once(self):
        """
        Poll Discord once for new messages.
        Returns None if bot has no guilds (signals backoff to poll loop).
        Returns list of messages otherwise.
        """
        try:
            # Broadcast status
            await manager.broadcast({
                "type": "status",
                "message": "Polling Discord servers...",
                "status": "working",
            })

            messages = await self.client.get_recent_messages(limit=50)

            if not messages:
                # get_recent_messages already logs a clear "not installed" warning
                # when the bot has no guilds. Avoid re-checking or spamming.
                if not self._no_guilds_warned:
                    self._no_guilds_warned = True
                    logger.info(
                        "No Discord messages found. If the bot has no guilds, "
                        "polling will back off automatically."
                    )

                await manager.broadcast({
                    "type": "status",
                    "message": "No new Discord messages",
                    "status": "idle",
                })
                return []

            # Filter out already-processed messages
            new_messages = []
            for msg in messages:
                msg_id = msg["id"]
                if msg_id in self.processed_messages:
                    continue
                # Check MongoDB for cross-restart deduplication
                if db.is_connected() and await db.is_message_processed(str(msg_id), "discord"):
                    self.processed_messages.add(msg_id)
                    continue
                new_messages.append(msg)

            if not new_messages:
                await manager.broadcast({
                    "type": "status",
                    "message": "No new Discord messages",
                    "status": "idle",
                })
                return []

            logger.info(f"Processing {len(new_messages)} new Discord messages")
            await manager.broadcast({
                "type": "status",
                "message": f"Processing {len(new_messages)} Discord messages...",
                "status": "working",
            })

            # Moderate each message
            for message in new_messages:
                await self._moderate_message(message)
                self.processed_messages.add(message["id"])

            await manager.broadcast({
                "type": "status",
                "message": f"Processed {len(new_messages)} Discord messages",
                "status": "success",
            })

            # Clean up old processed IDs (keep last 10000)
            if len(self.processed_messages) > 10000:
                self.processed_messages = set(list(self.processed_messages)[-5000:])

        except Exception as e:
            logger.error(f"Error in Discord poll: {e}")

    async def _moderate_message(self, message: Dict):
        """
        Moderate a single Discord message through the ML pipeline.

        Args:
            message: Discord message dictionary
        """
        try:
            # Prepare message for moderation engine
            tweet_data = {
                "id": message["id"],
                "text": message["text"],
                "platform": "discord",
                "author": message.get("author"),
                "author_id": message.get("author_id"),
                "channel": message.get("channel"),
                "channel_id": message.get("channel_id"),
                "guild": message.get("guild"),
                "guild_id": message.get("guild_id"),
                "language": "unknown",  # Will be detected by ML models
            }

            # Run moderation (ML inference + WebSocket broadcast + MongoDB save)
            result = await moderation_engine.process_tweet(tweet_data)

            # If marked for deletion, delete the Discord message immediately
            if result.get("action") == "delete":
                logger.info(f"🚨 TOXIC CONTENT DETECTED - Deleting Discord message {message['id']} from {message.get('guild', 'unknown server')}")
                
                deleted = await self.client.delete_message(
                    message["channel_id"],
                    message["id"],
                )

                if deleted:
                    logger.warning(f"✅ DELETED toxic message in {message.get('channel', 'unknown')}#{message.get('guild', 'unknown')}")
                    metrics.increment_deleted(result.get("language", "unknown"))
                    
                    # Broadcast deletion event
                    await manager.broadcast({
                        "type": "moderation_action",
                        "action": "delete",
                        "platform": "discord",
                        "message_id": message["id"],
                        "guild": message.get("guild"),
                        "channel": message.get("channel"),
                        "author": message.get("author"),
                        "reason": "Cyberbullying/Hate speech detected",
                        "confidence": result.get("bullying_probability", 0)
                    })
                else:
                    logger.error(f"❌ Failed to delete toxic message {message['id']} - Check bot permissions!")
            
            # Also handle timeout for severe cases
            elif result.get("action") == "flag" and result.get("bullying_probability", 0) > 0.8:
                # Auto-timeout users with very high toxicity scores
                guild_id = message.get("guild_id")
                author_id = message.get("author_id")
                if guild_id and author_id:
                    logger.info(f"⚠️ High toxicity ({result.get('bullying_probability', 0):.2f}) - timing out user {author_id}")
                    timeout_success = await self.client.timeout_user(guild_id, author_id, duration_minutes=30)
                    
                    if timeout_success:
                        await manager.broadcast({
                            "type": "moderation_action", 
                            "action": "timeout",
                            "platform": "discord",
                            "user_id": author_id,
                            "guild": message.get("guild"),
                            "duration_minutes": 30,
                            "reason": "High toxicity auto-timeout"
                        })

        except Exception as e:
            logger.error(f"Error moderating Discord message {message['id']}: {e}")
