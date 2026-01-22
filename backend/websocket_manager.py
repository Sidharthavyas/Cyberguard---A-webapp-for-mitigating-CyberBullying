"""
WebSocket connection manager for real-time event broadcasting.
Handles connection lifecycle and message broadcasting to all connected clients.
"""

from fastapi import WebSocket
from typing import List, Dict, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events to all clients."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Dictionary containing event data
        """
        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Convert to JSON
        json_message = json.dumps(message)
        
        # Send to all active connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific client.
        
        Args:
            message: Dictionary containing event data
            websocket: Target WebSocket connection
        """
        message["timestamp"] = datetime.utcnow().isoformat() + "Z"
        json_message = json.dumps(message)
        
        try:
            await websocket.send_text(json_message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)


# Global singleton instance
manager = ConnectionManager()
