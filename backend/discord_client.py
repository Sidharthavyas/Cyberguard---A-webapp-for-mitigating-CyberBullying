"""
Discord client for CyberGuard - Moderate Discord server messages.
Uses Discord Bot API (no user login required, just bot token).
"""

import os
import logging
import discord
from typing import Optional, List, Dict
from discord.ext import commands

logger = logging.getLogger(__name__)


class DiscordModerationClient:
    """Discord bot client for message moderation"""
    
    def __init__(self, bot_token: str, guild_ids: Optional[List[int]] = None):
        """
        Initialize Discord bot client.
        
        Args:
            bot_token: Discord bot token from Discord Developer Portal
            guild_ids: Optional list of server IDs to monitor (None = all servers)
        """
        self.bot_token = bot_token
        self.guild_ids = guild_ids or []
        
        # Initialize bot with required intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.guilds = True
        intents.guild_messages = True
        
        self.client = discord.Client(intents=intents)
        self.is_ready = False
        
        logger.info("Discord client initialized")
    
    async def start(self):
        """Start the Discord bot"""
        try:
            await self.client.login(self.bot_token)
            await self.client.connect()
            self.is_ready = True
            logger.info("✓ Discord bot connected")
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Discord bot"""
        try:
            await self.client.close()
            self.is_ready = False
            logger.info("✗ Discord bot disconnected")
        except Exception as e:
            logger.error(f"Failed to stop Discord bot: {e}")
    
    async def get_recent_messages(self, limit: int = 100) -> List[Dict]:
        """
        Fetch recent messages from monitored servers.
        
        Args:
            limit: Max messages to fetch per channel
            
        Returns:
            List of message dictionaries
        """
        if not self.is_ready:
            logger.warning("Discord bot not ready")
            return []
        
        messages = []
        
        try:
            for guild in self.client.guilds:
                # Skip if guild_ids specified and this guild not in list
                if self.guild_ids and guild.id not in self.guild_ids:
                    continue
                
                logger.info(f"Fetching messages from guild: {guild.name}")
                
                # Iterate through text channels
                for channel in guild.text_channels:
                    try:
                        # Fetch recent messages
                        async for message in channel.history(limit=limit):
                            if message.author.bot:
                                continue  # Skip bot messages
                            
                            messages.append({
                                "id": str(message.id),
                                "text": message.content,
                                "author": str(message.author),
                                "author_id": str(message.author.id),
                                "channel": channel.name,
                                "channel_id": str(channel.id),
                                "guild": guild.name,
                                "guild_id": str(guild.id),
                                "timestamp": message.created_at.isoformat(),
                                "platform": "discord"
                            })
                    
                    except discord.Forbidden:
                        logger.warning(f"No permission to read {channel.name}")
                        continue
                    except Exception as e:
                        logger.error(f"Error fetching from {channel.name}: {e}")
                        continue
            
            logger.info(f"Fetched {len(messages)} Discord messages")
            return messages
        
        except Exception as e:
            logger.error(f"Error fetching Discord messages: {e}")
            return []
    
    async def delete_message(self, channel_id: str, message_id: str) -> bool:
        """
        Delete a Discord message.
        
        Args:
            channel_id: Discord channel ID
            message_id: Discord message ID
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.is_ready:
            logger.warning("Discord bot not ready")
            return False
        
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return False
            
            message = await channel.fetch_message(int(message_id))
            if not message:
                logger.error(f"Message {message_id} not found")
                return False
            
            await message.delete()
            logger.info(f"Deleted Discord message {message_id}")
            return True
        
        except discord.Forbidden:
            logger.error(f"No permission to delete message {message_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete Discord message: {e}")
            return False
    
    async def timeout_user(self, guild_id: str, user_id: str, duration_minutes: int = 10) -> bool:
        """
        Timeout a user in a Discord server.
        
        Args:
            guild_id: Discord server ID
            user_id: User ID to timeout
            duration_minutes: Timeout duration in minutes
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_ready:
            logger.warning("Discord bot not ready")
            return False
        
        try:
            guild = self.client.get_guild(int(guild_id))
            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return False
            
            member = await guild.fetch_member(int(user_id))
            if not member:
                logger.error(f"Member {user_id} not found")
                return False
            
            import datetime
            until = discord.utils.utcnow() + datetime.timedelta(minutes=duration_minutes)
            await member.timeout(until)
            
            logger.info(f"Timed out user {user_id} for {duration_minutes} minutes")
            return True
        
        except discord.Forbidden:
            logger.error(f"No permission to timeout user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to timeout user: {e}")
            return False


def get_discord_client(bot_token: str, guild_ids: Optional[List[int]] = None) -> DiscordModerationClient:
    """
    Create a Discord client instance.
    
    Args:
        bot_token: Discord bot token
        guild_ids: Optional list of server IDs to monitor
        
    Returns:
        DiscordModerationClient instance
    """
    return DiscordModerationClient(bot_token, guild_ids)
