"""
Twitter OAuth2 authentication flow.
Manages login, callback, and token storage using Upstash Redis (free tier).
"""

import os
import logging
import secrets
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
import tweepy
import redis
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Allow HTTP during local development (oauthlib blocks non-HTTPS by default)
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

# Twitter OAuth2 setup
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Upstash Redis for token storage
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    redis_client = redis.from_url(REDIS_URL)
    logger.info("Connected to Upstash Redis for token storage")
else:
    logger.warning("No Redis URL provided - tokens will not persist")
    redis_client = None

# Store pending OAuth state -> code_verifier (in-memory; Redis not needed for CSRF protection)
pending_oauth: Dict[str, str] = {}


def _store_state(state: str, code_verifier: str):
    logger.info(f"Storing OAuth state {state}")
    if redis_client:
        # Store in Redis with 10-minute expiry
        redis_client.setex(f"oauth_state:{state}", 600, code_verifier)
    else:
        pending_oauth[state] = code_verifier


def _pop_state(state: str) -> Optional[str]:
    if redis_client:
        # Retrieve and delete from Redis
        key = f"oauth_state:{state}"
        code_verifier = redis_client.get(key)
        if code_verifier:
            redis_client.delete(key)
            code_verifier = code_verifier.decode('utf-8')
        logger.info(f"Popping OAuth state {state}: {'found' if code_verifier else 'missing'}")
        return code_verifier
    else:
        code_verifier = pending_oauth.pop(state, None)
        logger.info(f"Popping OAuth state {state}: {'found' if code_verifier else 'missing'}")
        return code_verifier


def _create_oauth_handler() -> tweepy.OAuth2UserHandler:
    return tweepy.OAuth2UserHandler(
        client_id=TWITTER_CLIENT_ID,
        redirect_uri=f"{BACKEND_URL}/auth/twitter/callback",
        scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
        client_secret=TWITTER_CLIENT_SECRET
    )


@router.get("/twitter/login")
async def twitter_login():
    """
    Initiate Twitter OAuth2 flow.
    Redirects user to Twitter authorization page.
    """
    try:
        oauth2_user_handler = _create_oauth_handler()
        authorization_url = oauth2_user_handler.get_authorization_url()
        
        # Extract state and code_verifier from the handler
        # Parse the actual state from the authorization URL to ensure we store the correct one
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(authorization_url)
        query_params = parse_qs(parsed_url.query)
        state = query_params.get('state', [None])[0]
        
        # Get code_verifier (may be callable)
        code_verifier = oauth2_user_handler._client.code_verifier
        if callable(code_verifier):
            code_verifier = code_verifier()
        
        if not state:
            raise ValueError("Failed to extract state from authorization URL")
            
        _store_state(state, code_verifier)
        logger.info(f"Redirecting to Twitter OAuth: {authorization_url}")
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        logger.error(f"Error initiating OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate Twitter login")


@router.get("/twitter/callback")
async def twitter_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """
    Handle OAuth2 callback from Twitter.
    Exchanges authorization code for access tokens.
    """
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error={error}")
    
    if not code or not state:
        logger.error("Missing authorization code or state")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_code_or_state")
    
    try:
        code_verifier = _pop_state(state)
        if not code_verifier:
            logger.error("State mismatch or expired")
            return RedirectResponse(url=f"{FRONTEND_URL}?error=state_mismatch")

        oauth2_user_handler = _create_oauth_handler()
        # Restore the state and PKCE verifier so oauthlib validation passes
        oauth2_user_handler.state = state
        oauth2_user_handler._client.code_verifier = code_verifier

        # Build full authorization response URL for fetch_token
        authorization_response = str(request.url)
        access_token = oauth2_user_handler.fetch_token(authorization_response)
        
        if not access_token:
            raise ValueError("Failed to fetch access token")
        
        # Get user information using OAuth 2.0 user access token
        client = tweepy.Client(access_token["access_token"])
        user_response = client.get_me(user_auth=False)
        
        if not user_response.data:
            raise ValueError("Failed to get user information")
        
        user_id = user_response.data.id
        username = user_response.data.username
        
        # Store tokens in Redis
        if redis_client:
            token_data = {
                "access_token": access_token["access_token"],
                "refresh_token": access_token.get("refresh_token"),
                "user_id": str(user_id),
                "username": username
            }
            redis_client.set(f"user:{user_id}", json.dumps(token_data))
            redis_client.set(f"session:current_user", json.dumps(token_data))  # Simple session for demo
            
            # Store with 90-day expiration (Twitter token lifetime)
            redis_client.setex(
                f"twitter_token:{user_id}",
                90 * 24 * 60 * 60,  # 90 days in seconds
                json.dumps(token_data)
            )
            
            logger.info(f"Stored tokens for user {username} ({user_id})")
            
        # Frontend `CallbackPage` expects `access_token`, `user_id`, and `username`
        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/callback"
                f"?access_token={access_token['access_token']}"
                f"&user_id={user_id}"
                f"&username={username}"
            )
        )
        
    except Exception as e:
        logger.error(f"Auth callback error: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_failed&details={str(e)}")


@router.get("/token/{user_id}")
async def get_stored_token(user_id: str):
    """
    Retrieve stored tokens for a user (if using Redis).
    
    Args:
        user_id: Twitter user ID
        
    Returns:
        Token data or 404
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Token storage not available")
    
    try:
        token_json = redis_client.get(f"twitter_token:{user_id}")
        
        if not token_json:
            raise HTTPException(status_code=404, detail="No token found for user")
        
        token_data = json.loads(token_json)
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving token: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve token")


@router.post("/logout/{user_id}")
async def logout(user_id: str):
    """
    Logout user by deleting their stored tokens.
    
    Args:
        user_id: Twitter user ID
    """
    if not redis_client:
        return {"message": "No token storage configured"}
    
    try:
        redis_client.delete(f"twitter_token:{user_id}")
        logger.info(f"Logged out user {user_id}")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")
