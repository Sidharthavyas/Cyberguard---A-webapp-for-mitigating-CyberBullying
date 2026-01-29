"""
FastAPI main application.
Handles WebSocket connections, REST endpoints, and CORS configuration.
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import routers and modules
from auth import router as auth_router
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

# Include routers
app.include_router(auth_router)


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
async def get_stats():
    """
    Get current in-memory metrics.
    
    Returns:
        Current statistics including scan/flag/delete counts
    """
    return metrics.get_stats()


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


# ============= PLATFORM MANAGEMENT APIS =============

@app.get("/platforms/connected")
async def get_connected_platforms():
    """
    Get list of currently connected platforms.
    
    Returns:
        List of connected platform names
    """
    from platform_manager import get_platform_manager
    from unified_poller import get_connected_platforms
    
    platform_manager = get_platform_manager()
    active = platform_manager.get_connected_platforms()
    
    # Also get stored platforms from Redis
    stored = get_connected_platforms()
    
    return {
        "active_pollers": active,
        "configured_platforms": list(stored.keys()),
        "platforms": {
            "twitter": {"enabled": True, "status": "active"},
            "discord": {
                "enabled": "discord" in active,
                "status": "active" if "discord" in active else "inactive"
            },
            "reddit": {
                "enabled": "reddit" in active,
                "status": "active" if "reddit" in active else "inactive"
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
