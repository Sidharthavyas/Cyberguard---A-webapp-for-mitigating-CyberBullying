"""
Twitter OAuth2 authentication flow.
Manages login, callback, and token storage using Upstash Redis (free tier).
Extended to support Discord and Reddit OAuth.
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
import urllib.parse
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Allow HTTP during local development (oauthlib blocks non-HTTPS by default)
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

# Twitter OAuth2 setup
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

# Discord OAuth2 setup
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

# Reddit OAuth2 setup
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

# URLs
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


# ============= TWITTER OAuth =============

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
        # Restore the state and PKCE verifier so oauth lib validation passes
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
                "username": username,
                "platform": "twitter"
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
                f"?platform=twitter"
                f"&access_token={access_token['access_token']}"
                f"&user_id={user_id}"
                f"&username={username}"
            )
        )
        
    except Exception as e:
        logger.error(f"Auth callback error: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_failed&details={str(e)}")


# ============= DISCORD OAuth =============

@router.get("/discord/login")
async def discord_login():
    """
    Initiate Discord OAuth2 flow.
    Redirects user to Discord authorization page.
    """
    if not DISCORD_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Discord OAuth not configured")
    
    try:
        state = secrets.token_urlsafe(32)
        _store_state(state, "discord_oauth")  # Store state for verification
        
        # Discord OAuth URL
        params = {
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": f"{BACKEND_URL}/auth/discord/callback",
            "response_type": "code",
            "scope": "identify guilds",
            "state": state
        }
        
        authorization_url = f"https://discord.com/api/oauth2/authorize?{urllib.parse.urlencode(params)}"
        
        logger.info(f"Redirecting to Discord OAuth: {authorization_url}")
        return RedirectResponse(url=authorization_url)
    
    except Exception as e:
        logger.error(f"Error initiating Discord OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate Discord login")


@router.get("/discord/callback")
async def discord_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """
    Handle OAuth2 callback from Discord.
    """
    if error:
        logger.error(f"Discord OAuth error: {error}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error={error}")
    
    if not code or not state:
        logger.error("Missing authorization code or state")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_code_or_state")
    
    try:
        # Verify state
        stored_state = _pop_state(state)
        if not stored_state:
            logger.error("State mismatch or expired")
            return RedirectResponse(url=f"{FRONTEND_URL}?error=state_mismatch")
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": DISCORD_CLIENT_ID,
                    "client_secret": DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{BACKEND_URL}/auth/discord/callback"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data["access_token"]
            
            # Get user info
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()
            user_info = user_response.json()
            
            user_id = user_info["id"]
            username = user_info["username"]
            
            # Store in Redis
            if redis_client:
                platform_data = {
                    "access_token": access_token,
                    "refresh_token": token_data.get("refresh_token"),
                    "user_id": user_id,
                    "username": username,
                    "platform": "discord"
                }
                
                redis_client.setex(
                    f"discord_token:{user_id}",
                    30 * 24 * 60 * 60,  # 30 days
                    json.dumps(platform_data)
           )
                
                logger.info(f"Stored Discord tokens for {username} ({user_id})")
            
            return RedirectResponse(
                url=(
                    f"{FRONTEND_URL}/callback"
                    f"?platform=discord"
                    f"&access_token={access_token}"
                    f"&user_id={user_id}"
                    f"&username={username}"
                )
            )
    
    except Exception as e:
        logger.error(f"Discord callback error: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?error=discord_auth_failed&details={str(e)}")


# ============= REDDIT OAuth =============

@router.get("/reddit/login")
async def reddit_login():
    """
    Initiate Reddit OAuth2 flow.
    Redirects user to Reddit authorization page.
    """
    if not REDDIT_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Reddit OAuth not configured")
    
    try:
        state = secrets.token_urlsafe(32)
        _store_state(state, "reddit_oauth")
        
        # Reddit OAuth URL
        params = {
            "client_id": REDDIT_CLIENT_ID,
            "response_type": "code",
            "state": state,
            "redirect_uri": f"{BACKEND_URL}/auth/reddit/callback",
            "duration": "permanent",
            "scope": "identity read submit modposts"
        }
        
        authorization_url = f"https://www.reddit.com/api/v1/authorize?{urllib.parse.urlencode(params)}"
        
        logger.info(f"Redirecting to Reddit OAuth: {authorization_url}")
        return RedirectResponse(url=authorization_url)
    
    except Exception as e:
        logger.error(f"Error initiating Reddit OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate Reddit login")


@router.get("/reddit/callback")
async def reddit_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """
    Handle OAuth2 callback from Reddit.
    """
    if error:
        logger.error(f"Reddit OAuth error: {error}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error={error}")
    
    if not code or not state:
        logger.error("Missing authorization code or state")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_code_or_state")
    
    try:
        # Verify state
        stored_state = _pop_state(state)
        if not stored_state:
            logger.error("State mismatch or expired")
            return RedirectResponse(url=f"{FRONTEND_URL}?error=state_mismatch")
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            auth = httpx.BasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
            
            token_response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{BACKEND_URL}/auth/reddit/callback"
                },
                headers={"User-Agent": "CyberGuard/1.0"}
            )
            
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data["access_token"]
            
            # Get user info
            user_response = await client.get(
                "https://oauth.reddit.com/api/v1/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": "CyberGuard/1.0"
                }
            )
            user_response.raise_for_status()
            user_info = user_response.json()
            
            user_id = user_info["id"]
            username = user_info["name"]
            
            # Store in Redis
            if redis_client:
                platform_data = {
                    "access_token": access_token,
                    "refresh_token": token_data.get("refresh_token"),
                    "user_id": user_id,
                    "username": username,
                    "platform": "reddit"
                }
                
                redis_client.setex(
                    f"reddit_token:{user_id}",
                    365 * 24 * 60 * 60,  # 1 year (Reddit tokens don't expire if refreshed)
                    json.dumps(platform_data)
                )
                
                logger.info(f"Stored Reddit tokens for {username} ({user_id})")
            
            return RedirectResponse(
                url=(
                    f"{FRONTEND_URL}/callback"
                    f"?platform=reddit"
                    f"&access_token={access_token}"
                    f"&user_id={user_id}"
                    f"&username={username}"
                )
            )
    
    except Exception as e:
        logger.error(f"Reddit callback error: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?error=reddit_auth_failed&details={str(e)}")


# ============= COMMON ROUTES =============

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
