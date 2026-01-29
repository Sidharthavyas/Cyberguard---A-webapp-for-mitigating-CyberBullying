"""
Discord poller for CyberGuard - Background monitoring of Discord messages.
Integrates with dynamic platform manager.
"""

import asyncio
import logging
from typing import Dict
from discord_client import get_discord_client
from platform_manager import PlatformPoller
from models import get_detector
from moderation import moderation_engine
from websocket_manager import manager

logger = logging.getLogger(__name__)


class DiscordPoller(PlatformPoller):
    """Polls Discord servers for messages and moderates them"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize Discord poller.
        
        Args:
            credentials: Dict with 'bot_token' and optional 'guild_ids'
        """
        super().__init__("Discord")
        
        self.bot_token = credentials.get("bot_token")
        self.guild_ids = credentials.get("guild_ids", [])
        self.poll_interval = int(credentials.get("poll_interval", 120))  # 2 minutes default
        
        if not self.bot_token:
            raise ValueError("Discord bot_token is required")
        
        # Initialize Discord client
        self.client = get_discord_client(self.bot_token, self.guild_ids)
        self.processed_messages = set()  # Track processed message IDs
        
        logger.info(f"Discord poller initialized (interval: {self.poll_interval}s)")
    
    async def _poll_loop(self):
        """Main polling loop for Discord messages"""
        # Start Discord bot
        await self.client.start()
        
        logger.info("Discord poller started")
        
        while self.is_running:
            try:
                await self._poll_once()
                await asyncio.sleep(self.poll_interval)
            
            except asyncio.CancelledError:
                logger.info("Discord poller cancelled")
                break
            except Exception as e:
                logger.error(f"Discord poller error: {e}")
                await asyncio.sleep(self.poll_interval)
        
        # Stop Discord bot
        await self.client.stop()
        logger.info("Discord poller stopped")
    
    async def _poll_once(self):
        """Poll Discord once for new messages"""
        try:
            # Fetch recent messages
            messages = await self.client.get_recent_messages(limit=50)
            
            if not messages:
                logger.debug("No Discord messages found")
                return
            
            # Process new messages only
            new_messages = [
                msg for msg in messages 
                if msg["id"] not in self.processed_messages
            ]
            
            if not new_messages:
                logger.debug("No new Discord messages")
                return
            
            logger.info(f"Processing {len(new_messages)} new Discord messages")
            
            # Moderate each message
            for message in new_messages:
                await self._moderate_message(message)
                self.processed_messages.add(message["id"])
            
            # Clean up old processed IDs (keep last 10000)
            if len(self.processed_messages) > 10000:
                self.processed_messages = set(list(self.processed_messages)[-5000:])
        
        except Exception as e:
            logger.error(f"Error in Discord poll: {e}")
    
    async def _moderate_message(self, message: Dict):
        """
        Moderate a single Discord message.
        
        Args:
            message: Discord message dictionary
        """
        try:
            # Prepare message for moderation
            tweet_data = {
                "id": message["id"],
                "text": message["text"],
                "language": "unknown"  # Will be detected by moderation engine
            }
            
            # Run moderation
            result = await moderation_engine.process_tweet(tweet_data)
            
            # Update result with Discord-specific fields
            result.update({
                "platform": "discord",
                "author": message["author"],
                "channel": message["channel"],
                "guild": message["guild"],
                "channel_id": message["channel_id"],
                "guild_id": message["guild_id"]
            })
            
            # If message was flagged for deletion, delete it
            if result["action"] == "delete" and result["deleted"]:
                deleted = await self.client.delete_message(
                    message["channel_id"], 
                    message["id"]
                )
                
                if deleted:
                    logger.warning(f"Deleted Discord message {message['id']}")
                    result["deleted"] = True
                else:
                    logger.error(f"Failed to delete Discord message {message['id']}")
                    result["deleted"] = False
            
            # Broadcast to WebSocket clients
            await manager.broadcast(result)
        
        except Exception as e:
            logger.error(f"Error moderating Discord message {message['id']}: {e}")
