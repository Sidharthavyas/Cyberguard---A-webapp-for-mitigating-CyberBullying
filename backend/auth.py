"""
Twitter OAuth2 authentication flow.
Manages login, callback, and token storage using Upstash Redis (free tier).
Extended to support Discord and Reddit OAuth.
"""

import os
import logging
import secrets
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import tweepy
import redis
import json
from typing import Optional, Dict, Any
import urllib.parse
import httpx
import aiohttp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)

# Allow HTTP during local development (oauthlib blocks non-HTTPS by default)
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

# Twitter OAuth2 setup
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

# Discord OAuth2 setup
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

# URLs — on HF Spaces, frontend is served from the same origin as backend
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", BACKEND_URL)

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
        scope=["tweet.read", "tweet.write", "tweet.moderate.write", "users.read", "offline.access"],
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
            # Per-platform session so Discord login doesn't overwrite Twitter
            redis_client.set("session:twitter", json.dumps(token_data))
            redis_client.set("session:current_user", json.dumps(token_data))
            
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
        redirect_uri = f"{BACKEND_URL}/auth/discord/callback"
        params = {
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify guilds",
            "state": state
            # First, just authenticate user to get their guilds
        }
        
        authorization_url = f"https://discord.com/api/oauth2/authorize?{urllib.parse.urlencode(params)}"
        
        logger.info(f"Initiating Discord Login.")
        logger.info(f"Expected Redirect URI: {redirect_uri}") 
        logger.info(f"Please ensure this EXACT URL is whitelisted in Discord Dev Portal.")
        logger.info(f"Full Auth URL: {authorization_url}")
        
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
        
        # Use synchronous requests via thread pool — async clients (aiohttp, httpx)
        # fail DNS resolution for discord.com on HF Spaces, but sync requests works.
        import requests as sync_requests
        import asyncio
        
        logger.info("Exchanging code for Discord token using sync requests...")
        
        token_data_payload = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{BACKEND_URL}/auth/discord/callback"
        }
        
        def _do_discord_exchange():
            """
            Synchronous Discord token exchange + user info fetch.
            Uses DNS-over-HTTPS (Cloudflare 1.1.1.1) to resolve discord.com
            because HF Spaces OS-level DNS can't resolve it.
            """
            import socket
            import http.client
            import ssl as _ssl
            
            # Step 1: Resolve discord.com via Cloudflare DNS-over-HTTPS
            # We connect to 1.1.1.1 by IP so no DNS resolution is needed
            discord_ip = None
            for dns_ip in ("1.1.1.1", "1.0.0.1"):
                try:
                    ctx = _ssl.create_default_context()
                    conn = http.client.HTTPSConnection(dns_ip, 443, timeout=5, context=ctx)
                    conn.request(
                        "GET",
                        "/dns-query?name=discord.com&type=A",
                        headers={"Accept": "application/dns-json"}
                    )
                    resp = conn.getresponse()
                    data = json.loads(resp.read())
                    conn.close()
                    for answer in data.get("Answer", []):
                        if answer.get("type") == 1:  # A record
                            discord_ip = answer["data"]
                            break
                    if discord_ip:
                        break
                except Exception as e:
                    logger.warning(f"DoH resolution via {dns_ip} failed: {e}")
            
            if not discord_ip:
                raise Exception("Could not resolve discord.com via DNS-over-HTTPS")
            
            logger.info(f"Resolved discord.com via DoH → {discord_ip}")
            
            # Step 2: Temporarily patch socket.getaddrinfo so requests uses our resolved IP
            # This keeps the URL as discord.com (for correct TLS SNI/Host header)
            _original_getaddrinfo = socket.getaddrinfo
            
            def _patched_getaddrinfo(host, port, *args, **kwargs):
                if host in ("discord.com", "discordapp.com"):
                    # Resolve our known IP instead
                    return _original_getaddrinfo(discord_ip, port, *args, **kwargs)
                return _original_getaddrinfo(host, port, *args, **kwargs)
            
            socket.getaddrinfo = _patched_getaddrinfo
            try:
                # Exchange code for access token
                token_resp = sync_requests.post(
                    "https://discord.com/api/oauth2/token",
                    data=token_data_payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30
                )
                token_resp.raise_for_status()
                t_data = token_resp.json()
                
                # Get user info
                user_resp = sync_requests.get(
                    "https://discord.com/api/users/@me",
                    headers={"Authorization": f"Bearer {t_data['access_token']}"},
                    timeout=30
                )
                user_resp.raise_for_status()
                u_info = user_resp.json()
                
                return t_data, u_info
            finally:
                # Always restore original DNS resolution
                socket.getaddrinfo = _original_getaddrinfo
        
        # Run synchronous requests in thread pool to avoid blocking event loop
        token_data, user_info = await asyncio.to_thread(_do_discord_exchange)
        access_token = token_data["access_token"]
        logger.info("Successfully got Discord access token")
        
        user_id = user_info["id"]
        username = user_info["username"]
        
        # Fetch user's guilds where they have admin permissions
        def _fetch_user_guilds():
            """Fetch guilds where user can add the bot."""
            try:
                # Use the access token to get user's guilds
                guilds_resp = sync_requests.get(
                    "https://discord.com/api/users/@me/guilds",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30
                )
                guilds_resp.raise_for_status()
                return guilds_resp.json()
            except Exception as e:
                logger.warning(f"Failed to fetch user guilds: {e}")
                return []
        
        user_guilds = await asyncio.to_thread(_fetch_user_guilds)
        admin_guilds = [g for g in user_guilds if (g.get("permissions", 0) & 0x8) == 0x8]  # ADMIN permission
        logger.info(f"User has admin access to {len(admin_guilds)} servers")
        
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
            
            # Per-platform session so Twitter login doesn't get overwritten
            session_data = {
                "user_id": str(user_id),
                "username": username,
                "platform": "discord",
                "access_token": access_token,
                "guilds": admin_guilds,  # Store user's admin guilds
                "total_guilds": len(admin_guilds)
            }
            redis_client.set("session:discord", json.dumps(session_data))
            redis_client.set("session:current_user", json.dumps(session_data))
            
            logger.info(f"Stored Discord tokens for {username} ({user_id}) and set active session")
            logger.info(f"User has admin access to {len(admin_guilds)} servers")
            
            # Check if user has admin guilds and redirect to server selection
            if len(admin_guilds) > 0:
                # Store guilds temporarily for server selection
                redis_client.setex(
                    f"temp_guilds:{user_id}",
                    600,  # 10 minutes
                    json.dumps({
                        "guilds": admin_guilds,
                        "access_token": access_token,
                        "username": username
                    })
                )
                
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/server-selection?user_id={user_id}&username={username}&guilds_count={len(admin_guilds)}"
                )
            else:
                # No admin guilds, just login normally
                return RedirectResponse(
                    url=(
                        f"{FRONTEND_URL}/callback"
                        f"?platform=discord"
                        f"&access_token={access_token}"
                        f"&user_id={user_id}"
                        f"&username={username}"
                        f"&message=Login successful! No servers where you have admin permissions."
                    )
                )
            
            # Start Discord Poller immediately after login for ALL servers
            try:
                from unified_poller import add_platform
                import asyncio
                bot_token = os.getenv("DISCORD_BOT_TOKEN")
                if bot_token:
                    logger.info("🚀 Starting Discord poller for ALL servers after login...")
                    # Run in background so callback response isn't delayed
                    asyncio.create_task(add_platform("discord", {
                        "bot_token": bot_token,
                        "guild_ids": [],  # EMPTY = Monitor ALL servers the bot is in
                        "poll_interval": 60,  # Check every 60 seconds for real-time moderation
                    }))
                else:
                    logger.error(
                        "DISCORD_BOT_TOKEN not set — Discord scanning disabled!  "
                        "Add DISCORD_BOT_TOKEN as an HF Space secret."
                    )
            except Exception as e:
                logger.error(f"Failed to auto-start Discord poller: {e}")
        
        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/callback"
                f"?platform=discord"
                f"&access_token={access_token}"
                f"&user_id={user_id}"
                f"&username={username}"
                f"&guilds_count={len(admin_guilds)}"
                f"&message=Login successful! Bot added to {len(admin_guilds)} servers."
            )
        )
    
    except Exception as e:
        logger.error(f"Discord callback error: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?error=discord_auth_failed&details={str(e)}")


# ============= COMMON ROUTES =============

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Get current authenticated user from token.
    Supports both Bearer tokens and query parameters for WebSocket compatibility.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    if not token:
        return None
    
    if not redis_client:
        return None
    
    try:
        # Try to find user by token in Redis
        # Check both platform-specific tokens and session tokens
        for platform in ["twitter", "discord"]:
            # Check if token matches any stored platform token
            pattern = f"{platform}_token:*"
            keys = redis_client.keys(pattern)
            for key in keys:
                try:
                    token_data = json.loads(redis_client.get(key) or "{}")
                    if token_data.get("access_token") == token:
                        return {
                            "user_id": token_data.get("user_id"),
                            "username": token_data.get("username"),
                            "platform": token_data.get("platform")
                        }
                except (json.JSONDecodeError, AttributeError):
                    continue
        
        # Check session tokens
        session_data = redis_client.get("session:current_user")
        if session_data:
            try:
                session = json.loads(session_data)
                if session.get("access_token") == token:
                    return {
                        "user_id": session.get("user_id"),
                        "username": session.get("username"),
                        "platform": session.get("platform")
                    }
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return None
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None

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


@router.post("/add-bot-to-servers")
async def add_bot_to_servers(
    user_id: str,
    selected_guilds: List[str],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add bot to selected servers.
    """
    try:
        # Get temporary guilds data
        temp_data = redis_client.get(f"temp_guilds:{user_id}")
        if not temp_data:
            raise HTTPException(status_code=400, detail="Server selection session expired")
        
        data = json.loads(temp_data)
        guilds = data.get("guilds", [])
        access_token = data.get("access_token")
        
        # Generate OAuth2 URLs for each selected guild
        bot_oauth_urls = []
        for guild_id in selected_guilds:
            guild = next((g for g in guilds if g["id"] == guild_id), None)
            if guild:
                oauth_url = (
                    f"https://discord.com/oauth2/authorize"
                    f"?client_id={DISCORD_CLIENT_ID}"
                    f"&permissions=68608"
                    f"&response_type=code"
                    f"&scope=bot%20applications.commands"
                    f"&guild_id={guild_id}"
                    f"&disable_guild_select=true"
                    f"&redirect_uri={BACKEND_URL}/auth/discord/bot-callback"
                )
                bot_oauth_urls.append({
                    "guild_id": guild_id,
                    "guild_name": guild.get("name", "Unknown Server"),
                    "oauth_url": oauth_url
                })
        
        return {
            "message": "Please authorize the bot in each server",
            "oauth_urls": bot_oauth_urls,
            "total_servers": len(bot_oauth_urls)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding bot to servers: {e}")
        raise HTTPException(status_code=500, detail="Failed to add bot to servers")


@router.get("/discord/bot-callback")
async def discord_bot_callback(
    guild_id: Optional[str] = Query(None),
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """
    Handle bot addition callback for individual servers.
    """
    if error:
        logger.error(f"Bot addition error: {error}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error={error}")
    
    if code and guild_id:
        try:
            # Exchange code for bot token
            import requests as sync_requests
            
            token_data = {
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{BACKEND_URL}/auth/discord/bot-callback"
            }
            
            resp = sync_requests.post(
                "https://discord.com/api/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            resp.raise_for_status()
            
            logger.info(f"✅ Bot successfully added to guild {guild_id}")
            
            # Start monitoring if not already running
            bot_token = os.getenv("DISCORD_BOT_TOKEN")
            if bot_token:
                from unified_poller import add_platform
                import asyncio
                asyncio.create_task(add_platform("discord", {
                    "bot_token": bot_token,
                    "guild_ids": [],  # Monitor all servers
                    "poll_interval": 60
                }))
            
            return RedirectResponse(
                url=f"{FRONTEND_URL}?message=Bot successfully added to server!&guild_id={guild_id}"
            )
            
        except Exception as e:
            logger.error(f"Bot callback error: {e}")
            return RedirectResponse(url=f"{FRONTEND_URL}?error=bot_addition_failed")
    
    return RedirectResponse(url=f"{FRONTEND_URL}?error=invalid_bot_callback")
