"""
CyberGuard - FastAPI Backend for Hugging Face Spaces
Full-featured backend with OAuth, WebSocket, and platform integrations
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

# Import the FastAPI app from backend
from backend.main import app

# The app is already configured in backend/main.py
# HF Spaces will run this file and serve the FastAPI app on port 7860

if __name__ == "__main__":
    import uvicorn
    
    # HF Spaces uses port 7860
    port = int(os.getenv("PORT", "7860"))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
