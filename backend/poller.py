"""
Background polling service for Twitter mentions.
Runs as separate worker on Render (free tier).
Polls every 20-30 seconds instead of using expensive streaming API.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from twitter_client import get_twitter_client
from moderation import moderation_engine
from websocket_manager import manager
import database as db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "25"))  # seconds


async def poll_mentions():
    """
    Continuously poll for mentions AND replies to user's posts.
    Uses Free Tier endpoints: mentions + search_recent_tweets.
    """
    logger.info(f"Starting poller (interval: {POLL_INTERVAL}s)")
    
    twitter = get_twitter_client()
    
    # Redis setup for session retrieval
    import redis
    import json
    redis_url = os.getenv("REDIS_URL")
    
    redis_client = None
    if redis_url:
        redis_client = redis.from_url(redis_url)
    else:
        logger.warning("No Redis URL - cannot load user session")

    # Track whether we've authenticated with user token
    user_authenticated = False
    current_token = None  # Track current token to detect re-login

    # Try to load OAuth2 user token from Redis (set during login)
    if redis_client:
        session_data = redis_client.get("session:twitter")
        if session_data:
            user_data = json.loads(session_data)
            oauth2_token = user_data.get("access_token")
            if oauth2_token:
                logger.info("Found OAuth2 user token in Redis — authenticating...")
                if twitter.set_oauth2_user_token(oauth2_token):
                    user_authenticated = True
                    current_token = oauth2_token
                    logger.info("✓ Poller using OAuth2 user token for API calls")
    
    # Fallback: Load OAuth 1.0a credentials from .env for auto-delete
    if not user_authenticated:
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        
        if access_token and access_token_secret:
            logger.info("Trying OAuth 1.0a credentials from env...")
            twitter.set_user_credentials(access_token, access_token_secret)
        else:
            logger.warning("No OAuth credentials available - will retry after user login")

    processed_ids = set()  # Track processed tweet IDs to avoid duplicates
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1

            # If active user is on Discord, skip Twitter polling entirely
            if redis_client:
                current_session = redis_client.get("session:current_user")
                if current_session:
                    current_data = json.loads(current_session)
                    if current_data.get("platform") == "discord":
                        # Discord user is active — no need to poll Twitter
                        if cycle_count % 12 == 1:
                            logger.debug("Active session is Discord — Twitter poller sleeping")
                        await asyncio.sleep(POLL_INTERVAL * 5)  # Sleep 2+ min
                        continue

            logger.info(f"Poller tick {cycle_count}")

            # Always check for latest OAuth2 token from Redis
            # (user may re-login and get a new token at any time)
            if redis_client:
                session_data = redis_client.get("session:twitter")
                if session_data:
                    user_data = json.loads(session_data)
                    oauth2_token = user_data.get("access_token")
                    if oauth2_token and oauth2_token != current_token:
                        logger.info("New OAuth2 token detected — re-authenticating...")
                        if twitter.set_oauth2_user_token(oauth2_token):
                            current_token = oauth2_token
                            user_authenticated = True
                            logger.info("✓ Poller refreshed OAuth2 user token")

            await poll_once(twitter, redis_client, processed_ids)
            
            # Log heartbeat if no user found, but don't spam
            if cycle_count % 12 == 1:
                if redis_client:
                    session = redis_client.get("session:twitter")
                    if not session:
                        logger.info(f"Poller heartbeat: no 'session:twitter' found. Waiting for login...")
            
            # Limit memory usage - keep only last 1000 IDs
            if len(processed_ids) > 1000:
                processed_ids.clear()
            
            # Wait before next poll
            await asyncio.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Poller stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            # Wait a bit longer on error
            await asyncio.sleep(POLL_INTERVAL * 2)


async def poll_once(twitter, redis_client, processed_ids: set):
    """
    Execute a single polling iteration.
    Extracted for debugging purposes.
    """
    import json
    
    # Dynamic user loading inside loop to handle logins
    user_id = None
    username = None
    
    if redis_client:
        # Read from per-platform key first, fallback to current_user
        session_data = redis_client.get("session:twitter")
        if not session_data:
            session_data = redis_client.get("session:current_user")
        
        if session_data:
            user_data = json.loads(session_data)
            # Only use this session if it's a Twitter session
            if user_data.get("platform", "twitter") == "twitter":
                username = user_data.get("username")
                user_id = user_data.get("user_id")
                
                if not (username and user_id):
                    logger.warning("Incomplete Twitter user session data")
            else:
                logger.debug("Current session is not Twitter - waiting for Twitter login")
    
    if not user_id:
        # Only show waiting message if no Twitter session — Discord has its own poller
        return

    # Broadcast start of poll
    await manager.broadcast({"type": "status", "message": f"Polling Twitter for @{username}...", "status": "working"})

    all_tweets = []
    
    # 1. Get mentions (tweets that @mention the user)
    # logger.info(f"Polling mentions for @{username}...")
    try:
        mentions = twitter.get_recent_mentions(max_results=10, user_id=user_id)
        if mentions:
            logger.info(f"Found {len(mentions)} mentions")
            all_tweets.extend(mentions)
    except Exception as e:
        if "429" in str(e) or "Too Many Requests" in str(e):
            logger.warning(f"Rate limit hit on mentions. Will retry next cycle.")
        else:
            logger.error(f"Error fetching mentions: {e}")
    
    # 2. Search for replies to user's posts (Free tier: search_recent_tweets)
    if username:
        # logger.info(f"Searching for replies to @{username}...")
        try:
            # "to:username" finds tweets directed at the user (replies & mentions)
            replies = twitter.search_recent_tweets(f"to:{username}", max_results=10)
            if replies:
                logger.info(f"Found {len(replies)} replies/conversations")
                all_tweets.extend(replies)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                logger.warning(f"Rate limit hit on search. Will retry next cycle.")
            else:
                logger.error(f"Error searching tweets: {e}")
    
    # Deduplicate: check in-memory set first, then MongoDB
    new_tweets = []
    for tweet in all_tweets:
        tweet_id = tweet.get("id")
        if not tweet_id or tweet_id in processed_ids:
            continue
        # Check MongoDB for tweets processed in previous sessions
        if db.is_connected() and await db.is_message_processed(str(tweet_id), "twitter"):
            processed_ids.add(tweet_id)  # Cache locally
            continue
        new_tweets.append(tweet)
        processed_ids.add(tweet_id)
    
    if new_tweets:
        await manager.broadcast({"type": "status", "message": f"Processing {len(new_tweets)} new tweets...", "status": "working"})
        logger.info(f"Processing {len(new_tweets)} unique new tweets")
        
        for tweet in new_tweets:
            if moderation_engine.should_process(tweet):
                try:
                    await moderation_engine.process_tweet(tweet)
                except Exception as e:
                    logger.error(f"Error processing tweet {tweet['id']}: {e}")
            else:
                logger.info(f"Skipping tweet {tweet['id']} (filtered)")
            
        await manager.broadcast({"type": "status", "message": f"Processed {len(new_tweets)} tweets", "status": "success"})
    else:
        await manager.broadcast({"type": "status", "message": "No new tweets found", "status": "idle"})


async def poll_search_query(query: str):
    """
    Poll for tweets matching a search query.
    Alternative to mention polling.
    
    Args:
        query: Twitter search query (e.g., '@yourhandle')
    """
    logger.info(f"Starting search poller for query: {query}")
    
    twitter = get_twitter_client()
    
    while True:
        try:
            logger.info(f"Searching for: {query}")
            
            tweets = twitter.search_recent_tweets(query, max_results=10)
            
            if tweets:
                logger.info(f"Found {len(tweets)} tweets matching query")
                
                for tweet in tweets:
                    if moderation_engine.should_process(tweet):
                        try:
                            await moderation_engine.process_tweet(tweet)
                        except Exception as e:
                            logger.error(f"Error processing tweet {tweet['id']}: {e}")
            else:
                logger.info("No matching tweets found")
            
            await asyncio.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Search poller stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in search polling loop: {e}")
            await asyncio.sleep(POLL_INTERVAL * 2)


if __name__ == "__main__":
    """
    Run the background poller.
    Can be run standalone or as Render background worker.
    """
    import sys
    
    # Check if search query provided
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        logger.info(f"Running in SEARCH mode with query: {query}")
        asyncio.run(poll_search_query(query))
    else:
        logger.info("Running in MENTIONS mode")
        asyncio.run(poll_mentions())
