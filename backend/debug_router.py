"""
Debug router for diagnosing fetching issues.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
import os
import json
import redis
from twitter_client import get_twitter_client
from poller import poll_once as poll_twitter_once

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])

# Initialize Redis
redis_url = os.getenv("REDIS_URL")
redis_client = None
if redis_url:
    redis_client = redis.from_url(redis_url)


@router.get("/config")
async def get_config():
    """check backend configuration (masked)."""
    backend_url = os.getenv("BACKEND_URL", "default_localhost")
    frontend_url = os.getenv("FRONTEND_URL", "default_localhost")
    
    return {
        "backend_url": backend_url,
        "frontend_url": frontend_url,
        "has_redis": bool(os.getenv("REDIS_URL")),
        "has_twitter_id": bool(os.getenv("TWITTER_CLIENT_ID")),
        "has_discord_id": bool(os.getenv("DISCORD_CLIENT_ID")),
        "has_discord_secret": bool(os.getenv("DISCORD_CLIENT_SECRET")),
        "has_discord_bot_token": bool(os.getenv("DISCORD_BOT_TOKEN")),
    }


@router.get("/twitter/session")
async def get_twitter_session():
    """Check the current cached Twitter session in Redis."""
    if not redis_client:
        return {"error": "Redis not configured"}
        
    session_data = redis_client.get("session:current_user")
    if not session_data:
        return {"status": "no_session", "message": "No user currently logged in"}
        
    return {
        "status": "active",
        "data": json.loads(session_data)
    }


@router.get("/twitter/fetch")
async def trigger_twitter_fetch():
    """
    Manually trigger a single Twitter poll iteration.
    Useful to check for rate limits or API errors directly.
    """
    try:
        twitter = get_twitter_client()
        processed_ids = set() # We don't care about dupes for debug run
        
        # Capture logs or return structure? 
        # For now, just running it to see if it errors in logs or works.
        # Ideally we'd modify poll_once to return stats.
        
        await poll_twitter_once(twitter, redis_client, processed_ids)
        
        return {
            "status": "success", 
            "message": "Poll triggered. Check logs or WebSocket for results."
        }
    except Exception as e:
        logger.error(f"Manual fetch error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.api_route("/twitter/clear-since", methods=["GET", "POST"])
async def clear_since_id():
    """Clear the stored since_id to force re-fetching old mentions."""
    if not redis_client:
        return {"error": "Redis not configured"}
        
    # We need to know WHICH user to clear for.
    # For now, let's clear for the currently logged in user.
    session_data = redis_client.get("session:current_user")
    if not session_data:
        return {"error": "No user logged in"}
        
    user_data = json.loads(session_data)
    user_id = user_data.get("user_id")
    
    key = f"twitter:since_id:{user_id}"
    redis_client.delete(key)
    
    return {"status": "success", "message": f"Cleared since_id for user {user_id}"}


@router.get("/discord/status")
async def get_discord_status():
    """Check if Discord poller is active."""
    from platform_manager import get_platform_manager
    manager = get_platform_manager()
    
    # Check if it's actually running in the manager
    running_pollers = list(manager.active_pollers.keys())
    discord_running = "discord" in running_pollers
    
    # Check if it's configured in Redis
    from unified_poller import get_connected_platforms
    configured = get_connected_platforms()
    discord_configured = "discord" in configured
    
    return {
        "discord_running": discord_running,
        "discord_configured": discord_configured,
        "running_pollers": running_pollers,
        "configured_platforms": list(configured.keys())
    }
