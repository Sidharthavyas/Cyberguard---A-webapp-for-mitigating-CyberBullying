"""
FastAPI main application.
Handles WebSocket connections, REST endpoints, and CORS configuration.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional

# Import routers and modules
from auth import router as auth_router, get_current_user
from websocket_manager import manager
from metrics import metrics
from models import get_detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - load models and start poller on startup."""
    logger.info("Application starting up...")
    
    # Pre-load ML models
    try:
        logger.info("Loading ML models...")
        detector = get_detector()
        logger.info("✓ ML models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ML models: {e}")
        raise
    
    # Initialize MongoDB
    import database as db
    try:
        connected = await db.init_mongodb()
        if connected:
            # Load persisted metrics
            snapshot = await db.load_metrics_snapshot()
            if snapshot:
                metrics.load_from_snapshot(snapshot)
                logger.info("✓ Metrics restored from MongoDB")
            else:
                logger.info("No metrics snapshot in MongoDB — starting fresh")
        else:
            logger.warning("MongoDB not available — running without persistence")
    except Exception as e:
        logger.error(f"MongoDB init error: {e}")
    
    # Start background pollers (Twitter + dynamic platforms)
    from poller import poll_mentions
    from unified_poller import start_platform_pollers
    import asyncio
    
    # Start Twitter poller (existing)
    twitter_poller_task = asyncio.create_task(poll_mentions())
    logger.info("✓ Twitter poller started")
    
    # Start unified platform pollers (Discord, Reddit, etc.)
    await start_platform_pollers()
    logger.info("✓ All platform pollers initialized")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Application shutting down...")
    
    # Stop Twitter poller
    twitter_poller_task.cancel()
    try:
        await twitter_poller_task
    except asyncio.CancelledError:
        logger.info("✓ Twitter poller stopped")
    
    # Stop all platform pollers
    from unified_poller import shutdown_all_pollers
    await shutdown_all_pollers()
    logger.info("✓ All pollers stopped")
    
    # Flush metrics and close MongoDB
    import database as db
    await metrics.flush_to_mongodb()
    await db.close_mongodb()
    logger.info("✓ MongoDB closed")


# Create FastAPI app
app = FastAPI(
    title="Cyberbullying Mitigation API",
    description="Real-time Twitter toxicity detection and auto-moderation (Free Tier)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    # NOTE: Starlette does not support wildcard strings like "https://*.vercel.app" in allow_origins.
    # Use allow_origin_regex for Vercel preview/prod domains.
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory settings store (per user)
settings_store: Dict[str, Dict[str, Any]] = {}

# Include routers
# Include routers
from debug_router import router as debug_router
app.include_router(auth_router)
app.include_router(debug_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Cyberbullying Mitigation API",
        "version": "1.0.0",
        "mode": "free_tier",
        "features": {
            "ml_inference": "CPU-only",
            "database": "in-memory",
            "twitter_api": "Standard v2 Free",
            "websocket": "enabled"
        }
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "active_websocket_connections": len(manager.active_connections),
        "metrics": metrics.get_stats()
    }


@app.get("/stats")
async def get_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current in-memory metrics for authenticated user.
    
    Returns:
        Current statistics including scan/flag/delete counts
    """
    # Filter stats by user if available
    user_stats = metrics.get_stats()
    if current_user:
        user_stats["current_user"] = {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "platform": current_user.get("platform")
        }
    return user_stats


@app.get("/analytics/summary")
async def get_analytics_summary(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Analytics summary alias for current metrics (user-specific).
    Can be extended later with more derived insights.
    """
    user_stats = metrics.get_stats()
    if current_user:
        user_stats["current_user"] = {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "platform": current_user.get("platform")
        }
    return user_stats


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.
    Clients connect here to receive live moderation events.
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await manager.send_personal(
            {
                "type": "connection",
                "message": "Connected to moderation stream",
                "stats": metrics.get_stats()
            },
            websocket
        )
        
        # Keep connection alive and wait for client messages
        while True:
            # Receive (but don't necessarily need to process) client messages
            data = await websocket.receive_text()
            logger.info(f"Received from client: {data}")
            
            # Could implement client commands here if needed
            # For now, we just keep the connection alive
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.post("/reset-metrics")
async def reset_metrics():
    """
    Reset all in-memory metrics to zero.
    Use with caution!
    """
    metrics.reset()
    return {"message": "Metrics reset successfully"}


# ============= SETTINGS APIS =============

@app.get("/settings/{user_id}")
async def get_settings(user_id: str):
    """
    Get settings for a given user.
    Stored in-memory only (resets on server restart).
    """
    default_settings = {
        "realtime_enabled": True,
        "auto_delete": True,
        "language_filter": "all"
    }
    return settings_store.get(user_id, default_settings)


@app.post("/settings/{user_id}")
async def update_settings(user_id: str, payload: Dict[str, Any]):
    """
    Update settings for a given user.
    """
    existing = settings_store.get(user_id, {})
    existing.update(payload or {})
    settings_store[user_id] = existing
    return existing


# ============= PLATFORM MANAGEMENT APIS =============

@app.get("/platforms/connected")
async def get_connected_platforms():
    """
    Get list of currently connected platforms.
    Checks both active pollers AND Redis sessions.
    
    Returns:
        List of connected platform names
    """
    from platform_manager import get_platform_manager
    from unified_poller import get_connected_platforms as get_stored_platforms
    import redis
    import json
    
    platform_manager = get_platform_manager()
    active = platform_manager.get_connected_platforms()
    
    # Also get stored platforms from Redis
    stored = get_stored_platforms()
    
    # Also check Redis sessions for logged-in platforms
    redis_url = os.getenv("REDIS_URL")
    discord_session = False
    twitter_session = False
    if redis_url:
        try:
            r = redis.from_url(redis_url)
            if r.get("session:discord"):
                discord_session = True
            if r.get("session:twitter"):
                twitter_session = True
        except Exception:
            pass
    
    return {
        "active_pollers": active,
        "configured_platforms": list(stored.keys()),
        "platforms": {
            "twitter": {
                "enabled": twitter_session or "twitter" in active,
                "status": "active" if twitter_session else "inactive"
            },
            "discord": {
                "enabled": discord_session or "discord" in active,
                "status": "active" if ("discord" in active or discord_session) else "inactive"
            }
        }
    }


@app.post("/platforms/connect")
async def connect_platform(request: dict):
    """
    Connect a new platform and start its poller.
    
    Body:
        {
            "platform": "discord" | "reddit",
            "credentials": {...}
        }
    """
    platform = request.get("platform")
    credentials = request.get("credentials", {})
    
    if not platform:
        raise HTTPException(status_code=400, detail="Platform name required")
    
    from unified_poller import add_platform
    
    success = await add_platform(platform, credentials)
    
    if success:
        return {
            "message": f"{platform} connected successfully",
            "platform": platform
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to connect {platform}")


@app.delete("/platforms/{platform}")
async def disconnect_platform(platform: str):
    """
    Disconnect a platform and stop its poller.
    
    Args:
        platform: Platform name (discord, reddit)
    """
    from unified_poller import remove_platform
    
    success = await remove_platform(platform)
    
    if success:
        return {
            "message": f"{platform} disconnected successfully",
            "platform": platform
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect {platform}")


@app.get("/feed")
async def get_unified_feed(platform: str = "all", limit: int = 100):
    """
    Get unified feed from all or specific platforms.
    
    Args:
        platform: "all", "twitter", "discord", or "reddit"
        limit: Max items to return
    
    Returns:
        Unified feed with platform filtering
    """
    # TODO: Implement feed aggregation from multiple platforms
    # For now, return metrics
    return {
        "platform": platform,
        "limit": limit,
        "message": "Feed endpoint - to be implemented with actual feed data",
        "stats": metrics.get_stats()
    }


# ============= DISCORD MODERATION APIS =============

@app.post("/discord/moderate")
async def moderate_discord_user(
    request: dict,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Apply moderation action to a Discord user.
    
    Body:
        {
            "guild_id": "guild_id",
            "user_id": "user_id", 
            "action": "ban|kick|timeout|delete_message",
            "reason": "reason",
            "duration_minutes": 10,  # for timeout
            "message_id": "msg_id",  # for delete_message
            "channel_id": "channel_id",  # for delete_message
            "delete_message_days": 7  # for ban
        }
    """
    if not current_user or current_user.get("platform") != "discord":
        raise HTTPException(status_code=403, detail="Discord authentication required")
    
    from unified_poller import get_platform_client
    
    guild_id = request.get("guild_id")
    user_id = request.get("user_id")
    action = request.get("action")
    reason = request.get("reason", "Cyberbullying violation")
    
    if not all([guild_id, user_id, action]):
        raise HTTPException(status_code=400, detail="guild_id, user_id, and action required")
    
    # Get Discord client
    discord_client = get_platform_client("discord")
    if not discord_client:
        raise HTTPException(status_code=503, detail="Discord client not available")
    
    # Apply moderation
    success = await discord_client.moderate_user(
        guild_id=guild_id,
        user_id=user_id,
        action=action,
        reason=reason,
        **{k: v for k, v in request.items() if k not in ["guild_id", "user_id", "action", "reason"]}
    )
    
    if success:
        # Log the moderation action
        import database as db
        await db.save_moderation_event({
            "platform": "discord",
            "platform_id": user_id,
            "action": action,
            "author": current_user.get("username"),
            "author_id": current_user.get("user_id"),
            "text": f"Moderation action: {action} on user {user_id}",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guild_id": guild_id
        })
        
        return {
            "message": f"Successfully applied {action} to user {user_id}",
            "action": action,
            "user_id": user_id,
            "guild_id": guild_id
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to apply {action} to user")


@app.get("/discord/guilds")
async def get_discord_guilds(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get list of Discord guilds the bot has access to.
    """
    if not current_user or current_user.get("platform") != "discord":
        raise HTTPException(status_code=403, detail="Discord authentication required")
    
    from unified_poller import get_platform_client
    
    discord_client = get_platform_client("discord")
    if not discord_client:
        raise HTTPException(status_code=503, detail="Discord client not available")
    
    guilds = await discord_client.get_bot_guilds()
    return {"guilds": guilds}


@app.get("/discord/guilds/{guild_id}/channels")
async def get_discord_channels(
    guild_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get text channels for a Discord guild.
    """
    if not current_user or current_user.get("platform") != "discord":
        raise HTTPException(status_code=403, detail="Discord authentication required")
    
    from unified_poller import get_platform_client
    
    discord_client = get_platform_client("discord")
    if not discord_client:
        raise HTTPException(status_code=503, detail="Discord client not available")
    
    channels = await discord_client.get_guild_text_channels(guild_id)
    return {"channels": channels}


@app.get("/discord/status")
async def get_discord_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get Discord monitoring status and server information.
    """
    if not current_user or current_user.get("platform") != "discord":
        raise HTTPException(status_code=403, detail="Discord authentication required")
    
    from unified_poller import get_platform_client
    
    discord_client = get_platform_client("discord")
    if not discord_client:
        return {
            "status": "inactive",
            "message": "Discord monitoring not active - please log in first",
            "servers": []
        }
    
    try:
        guilds = await discord_client.get_bot_guilds()
        return {
            "status": "active",
            "message": f"Monitoring {len(guilds)} servers for hate speech",
            "servers": guilds,
            "monitoring_all_servers": True,
            "poll_interval": "60 seconds",
            "auto_delete": True,
            "auto_timeout": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting Discord status: {str(e)}",
            "servers": []
        }


@app.post("/discord/start-monitoring")
async def start_discord_monitoring(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Manually start Discord monitoring for all servers.
    """
    if not current_user or current_user.get("platform") != "discord":
        raise HTTPException(status_code=403, detail="Discord authentication required")
    
    try:
        from unified_poller import add_platform
        import os
        
        bot_token = os.getenv("DISCORD_BOT_TOKEN")
        if not bot_token:
            raise HTTPException(status_code=500, detail="DISCORD_BOT_TOKEN not configured")
        
        # Start monitoring all servers
        success = await add_platform("discord", {
            "bot_token": bot_token,
            "guild_ids": [],  # Monitor ALL servers
            "poll_interval": 60
        })
        
        if success:
            return {
                "message": "🚀 Discord monitoring started for ALL servers",
                "status": "active",
                "monitoring_all_servers": True
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start Discord monitoring")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting monitoring: {str(e)}")


@app.get("/discord/channels/{channel_id}/messages")
async def get_discord_channel_messages(
    channel_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get recent messages from a Discord channel.
    """
    if not current_user or current_user.get("platform") != "discord":
        raise HTTPException(status_code=403, detail="Discord authentication required")
    
    from unified_poller import get_platform_client
    
    discord_client = get_platform_client("discord")
    if not discord_client:
        raise HTTPException(status_code=503, detail="Discord client not available")
    
    messages = await discord_client.get_channel_messages(channel_id, limit)
    return {"messages": messages, "channel_id": channel_id}

@app.get("/history")
async def get_history(
    platform: str = Query("all", description="Filter by platform: all, twitter, discord"),
    action: Optional[str] = Query(None, description="Filter by action: flag, delete, ignore"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get paginated moderation event history from MongoDB for authenticated user.
    Survives server restarts.
    """
    import database as db
    if not db.is_connected():
        return {"events": [], "total": 0, "message": "MongoDB not connected"}
    
    # Filter events by current user if available
    user_filter = None
    if current_user:
        user_filter = current_user.get("user_id")
    
    events = await db.get_moderation_events(
        platform=platform, limit=limit, skip=skip, action_filter=action, user_id=user_filter
    )
    total = await db.count_moderation_events(platform=platform, user_id=user_filter)
    
    # Convert datetime objects to strings for JSON serialization
    for event in events:
        for key, value in event.items():
            if hasattr(value, 'isoformat'):
                event[key] = value.isoformat()
    
    return {"events": events, "total": total, "platform": platform, "user": current_user}


@app.get("/messages")
async def get_messages(
    platform: str = Query("all", description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get raw platform messages (tweets, Discord chats) for authenticated user.
    """
    import database as db
    if not db.is_connected():
        return {"messages": [], "message": "MongoDB not connected"}
    
    # Filter messages by current user if available
    user_filter = None
    if current_user:
        user_filter = current_user.get("user_id")
    
    messages = await db.get_platform_messages(
        platform=platform, limit=limit, skip=skip, user_id=user_filter
    )
    
    for msg in messages:
        for key, value in msg.items():
            if hasattr(value, 'isoformat'):
                msg[key] = value.isoformat()
    
    return {"messages": messages, "platform": platform, "user": current_user}


@app.get("/history/stats")
async def get_history_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get aggregate statistics from MongoDB for authenticated user (persistent, accurate).
    """
    import database as db
    if not db.is_connected():
        # Fallback to in-memory
        user_stats = metrics.get_stats()
        if current_user:
            user_stats["current_user"] = {
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "platform": current_user.get("platform")
            }
        return user_stats
    
    # Filter stats by user if available
    user_filter = None
    if current_user:
        user_filter = current_user.get("user_id")
    
    stats = await db.get_aggregate_stats(user_id=user_filter)
    if not stats:
        user_stats = metrics.get_stats()
        if current_user:
            user_stats["current_user"] = {
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "platform": current_user.get("platform")
            }
        return user_stats
    
    if current_user:
        stats["current_user"] = {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "platform": current_user.get("platform")
        }
    
    return stats


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
