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
    Also checks Redis for existing sessions to auto-resume after restarts.
    """
    logger.info("Starting unified platform pollers...")

    platform_manager = get_platform_manager()
    platforms = get_connected_platforms()

    # Start from stored config first
    discord_started = False

    if platforms.get("discord", {}).get("enabled"):
        try:
            disc_config = platforms["discord"]
            credentials = {
                "bot_token": disc_config.get("bot_token"),
                "guild_ids": disc_config.get("guild_ids", []),
                "poll_interval": disc_config.get("poll_interval", 60),
            }

            await platform_manager.connect_platform(
                "discord", credentials, DiscordPoller
            )
            discord_started = True
            logger.info("✓ Discord poller started from stored config")
        except Exception as e:
            logger.error(f"Failed to start Discord poller from config: {e}")

    # Fallback: check Redis for an existing Discord session (user logged in before)
    if not discord_started and redis_client:
        try:
            session_data = redis_client.get("session:discord")
            if session_data:
                import os
                bot_token = os.getenv("DISCORD_BOT_TOKEN")
                if bot_token:
                    logger.info("Found Discord session in Redis — auto-starting poller...")
                    credentials = {
                        "bot_token": bot_token,
                        "guild_ids": [],
                        "poll_interval": 60,
                    }
                    await platform_manager.connect_platform(
                        "discord", credentials, DiscordPoller
                    )
                    discord_started = True
                    logger.info("✓ Discord poller auto-started from session")
                else:
                    logger.warning("Discord session found but DISCORD_BOT_TOKEN not in env")
        except Exception as e:
            logger.error(f"Failed to auto-start Discord from session: {e}")

    if not platforms and not discord_started:
        logger.info("No platforms connected - pollers will start when platforms are connected")
        return

    logger.info(f"Unified pollers running for: {platform_manager.get_connected_platforms()}")


async def add_platform(platform: str, credentials: Dict) -> bool:
    """
    Add a new platform and start its poller.
    
    Args:
        platform: Platform name (twitter, discord)
        credentials: Platform-specific credentials
        
    Returns:
        True if successful, False otherwise
    """
    platform_manager = get_platform_manager()
    
    try:
        # Map platform to poller class
        if platform == "discord":
            poller_class = DiscordPoller
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


def get_platform_client(platform: str):
    """
    Get the active client for a platform.
    
    Args:
        platform: Platform name (discord, twitter)
        
    Returns:
        Platform client instance or None
    """
    platform_manager = get_platform_manager()
    return platform_manager.get_client(platform)
