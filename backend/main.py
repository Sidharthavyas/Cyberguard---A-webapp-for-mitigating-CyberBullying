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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    
    # Start background poller
    from poller import poll_mentions
    import asyncio
    
    poller_task = asyncio.create_task(poll_mentions())
    logger.info("✓ Background poller started")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Application shutting down...")
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        logger.info("✓ Poller stopped")


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
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "https://*.vercel.app"],
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
