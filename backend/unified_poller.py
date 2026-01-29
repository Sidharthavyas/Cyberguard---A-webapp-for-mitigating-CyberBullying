"""
Unified poller for CyberGuard - Dynamically polls all connected platforms.
Only runs pollers for platforms that users have connected.
"""

import asyncio
import logging
import os
from typing import Dict, List
from platform_manager import get_platform_manager
from discord_poller import DiscordPoller
from reddit_poller import RedditPoller
import redis
import json

logger = logging.getLogger(__name__)

# Redis for storing platform connections
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    redis_client = redis.from_url(REDIS_URL)
else:
    redis_client = None


def get_connected_platforms() -> Dict:
    """
    Get list of connected platforms from Redis.
    
    Returns:
        Dict of platform configs
    """
    if not redis_client:
        logger.warning("No Redis client - cannot fetch connected platforms")
        return {}
    
    try:
        platforms_json = redis_client.get("connected_platforms")
        if not platforms_json:
            logger.info("No platforms connected yet")
            return {}
        
        platforms = json.loads(platforms_json)
        return platforms
    
    except Exception as e:
        logger.error(f"Error fetching connected platforms: {e}")
        return {}


async def start_platform_pollers():
    """
    Start pollers for all connected platforms.
    Only runs pollers for platforms that users have connected.
    """
    logger.info("Starting unified platform pollers...")
    
    platform_manager = get_platform_manager()
    platforms = get_connected_platforms()
    
    if not platforms:
        logger.info("No platforms connected - pollers will start when platforms are connected")
        return
    
    # Start Twitter poller (existing logic)
    if platforms.get("twitter", {}).get("enabled"):
        logger.info("Twitter connection found - poller already running from existing system")
    
    # Start Discord poller
    if platforms.get("discord", {}).get("enabled"):
        try:
            disc_config = platforms["discord"]
            credentials = {
                "bot_token": disc_config.get("bot_token"),
                "guild_ids": disc_config.get("guild_ids", []),
                "poll_interval": disc_config.get("poll_interval", 120)
            }
            
            await platform_manager.connect_platform(
                "discord",
                credentials,
                DiscordPoller
            )
            logger.info("✓ Discord poller started")
        
        except Exception as e:
            logger.error(f"Failed to start Discord poller: {e}")
    
    # Start Reddit poller
    if platforms.get("reddit", {}).get("enabled"):
        try:
            reddit_config = platforms["reddit"]
            credentials = {
                "client_id": reddit_config.get("client_id"),
                "client_secret": reddit_config.get("client_secret"),
                "user_agent": reddit_config.get("user_agent", "CyberGuard/1.0"),
                "username": reddit_config.get("username"),
                "password": reddit_config.get("password"),
                "subreddits": reddit_config.get("subreddits", []),
                "poll_interval": reddit_config.get("poll_interval", 120)
            }
            
            await platform_manager.connect_platform(
                "reddit",
                credentials,
               RedditPoller
            )
            logger.info("✓ Reddit poller started")
        
        except Exception as e:
            logger.error(f"Failed to start Reddit poller: {e}")
    
    logger.info(f"Unified pollers running for: {platform_manager.get_connected_platforms()}")


async def add_platform(platform: str, credentials: Dict) -> bool:
    """
    Add a new platform and start its poller.
    
    Args:
        platform: Platform name (twitter, discord, reddit)
        credentials: Platform-specific credentials
        
    Returns:
        True if successful, False otherwise
    """
    platform_manager = get_platform_manager()
    
    try:
        # Map platform to poller class
        if platform == "discord":
            poller_class = DiscordPoller
        elif platform == "reddit":
            poller_class = RedditPoller
        else:
            logger.error(f"Unknown platform: {platform}")
            return False
        
        # Connect platform
        await platform_manager.connect_platform(platform, credentials, poller_class)
        
        # Store in Redis
        if redis_client:
            platforms = get_connected_platforms()
            platforms[platform] = {
                "enabled": True,
                **credentials
            }
            redis_client.set("connected_platforms", json.dumps(platforms))
        
        logger.info(f"✓ Added platform: {platform}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to add platform {platform}: {e}")
        return False


async def remove_platform(platform: str) -> bool:
    """
    Remove a platform and stop its poller.
    
    Args:
        platform: Platform name to remove
        
    Returns:
        True if successful, False otherwise
    """
    platform_manager = get_platform_manager()
    
    try:
        # Disconnect platform
        await platform_manager.disconnect_platform(platform)
        
        # Remove from Redis
        if redis_client:
            platforms = get_connected_platforms()
            if platform in platforms:
                del platforms[platform]
                redis_client.set("connected_platforms", json.dumps(platforms))
        
        logger.info(f"✗ Removed platform: {platform}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to remove platform {platform}: {e}")
        return False


async def shutdown_all_pollers():
    """Shutdown all platform pollers"""
    platform_manager = get_platform_manager()
    await platform_manager.shutdown()
