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
    
    # Load OAuth 1.0a credentials from environment for auto-delete
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    if access_token and access_token_secret:
        logger.info("Found OAuth 1.0a credentials - enabling auto-delete")
        twitter.set_user_credentials(access_token, access_token_secret)
    else:
        logger.warning("No OAuth 1.0a credentials - deletion will be disabled")
    
    # Load user info from Redis session (for username)
    import redis
    import json
    redis_url = os.getenv("REDIS_URL")
    username = None
    
    if redis_url:
        redis_client = redis.from_url(redis_url)
        session_data = redis_client.get("session:current_user")
        if session_data:
            user_data = json.loads(session_data)
            username = user_data.get("username")
            if username:
                logger.info(f"Monitoring @{username}'s account")
            else:
                logger.warning("No username found in session")
        else:
            logger.info("No user session in Redis yet - will monitor once user logs in via dashboard")
    else:
        logger.warning("No Redis URL - cannot load user session")
    
    processed_ids = set()  # Track processed tweet IDs to avoid duplicates
    
    while True:
        try:
            all_tweets = []
            
            # 1. Get mentions (tweets that @mention the user)
            logger.info("Polling for mentions...")
            try:
                mentions = twitter.get_recent_mentions(max_results=10)
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
                logger.info(f"Searching for replies to @{username}...")
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
            
            # Deduplicate and process
            new_tweets = []
            for tweet in all_tweets:
                tweet_id = tweet.get("id")
                if tweet_id and tweet_id not in processed_ids:
                    new_tweets.append(tweet)
                    processed_ids.add(tweet_id)
            
            if new_tweets:
                logger.info(f"Processing {len(new_tweets)} new tweets...")
                for tweet in new_tweets:
                    if moderation_engine.should_process(tweet):
                        try:
                            await moderation_engine.process_tweet(tweet)
                        except Exception as e:
                            logger.error(f"Error processing tweet {tweet['id']}: {e}")
                    else:
                        logger.info(f"Skipping tweet {tweet['id']} (filtered)")
            else:
                logger.info("No new tweets to process")
            
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
