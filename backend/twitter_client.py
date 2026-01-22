"""
Twitter API client using Standard API v2 (Free Tier).
Handles authentication, mention polling, and tweet deletion.
"""

import tweepy
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import redis

logger = logging.getLogger(__name__)


class TwitterClient:
    """Twitter API v2 client for free tier operations."""
    
    def __init__(self):
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.client_id = os.getenv("TWITTER_CONSUMER_KEY")
        self.client_secret = os.getenv("TWITTER_CONSUMER_SECRET")
        
        if not all([self.bearer_token, self.client_id, self.client_secret]):
            raise ValueError("Missing Twitter API credentials")
        
        # Initialize API v2 client
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.client_id,
            consumer_secret=self.client_secret,
            wait_on_rate_limit=False  # Don't block on rate limits
        )
        
        # Redis for storing last poll timestamp
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        else:
            logger.warning("No Redis URL provided, using in-memory state")
            self.redis_client = None
        
        self.user_id = None
        logger.info("Twitter client initialized")
    
    def set_user_credentials(self, access_token: str, access_token_secret: str):
        """
        Set user-specific OAuth credentials for tweet deletion.
        
        Args:
            access_token: User's OAuth access token
            access_token_secret: User's OAuth access token secret
        """
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.client_id,
            consumer_secret=self.client_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=False  # Don't block on rate limits
        )
        
        # Get authenticated user ID
        try:
            me = self.client.get_me()
            if me.data:
                self.user_id = me.data.id
                logger.info(f"Authenticated as user ID: {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
    
    def get_recent_mentions(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent mentions for the authenticated user.
        Uses free tier endpoint with rate limit: 75 requests per 15 minutes.
        
        Args:
            max_results: Maximum number of mentions to retrieve (5-100)
            
        Returns:
            List of mention dictionaries
        """
        if not self.user_id:
            logger.warning("No user ID set, cannot fetch mentions")
            return []
        
        try:
            # Get last poll time from Redis
            since_id = None
            if self.redis_client:
                since_id = self.redis_client.get("last_mention_id")
                if since_id:
                    since_id = since_id.decode('utf-8')
            
            # Fetch mentions
            response = self.client.get_users_mentions(
                id=self.user_id,
                max_results=min(max_results, 100),
                since_id=since_id,
                tweet_fields=["created_at", "text", "author_id", "lang"]
            )
            
            if not response.data:
                logger.info("No new mentions found")
                return []
            
            mentions = []
            for tweet in response.data:
                mentions.append({
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": tweet.author_id,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "language": tweet.lang if hasattr(tweet, 'lang') else "unknown"
                })
            
            # Update last poll ID
            if mentions and self.redis_client:
                latest_id = mentions[0]["id"]
                self.redis_client.set("last_mention_id", str(latest_id))
            
            logger.info(f"Retrieved {len(mentions)} new mentions")
            return mentions
            
        except tweepy.errors.TweepyException as e:
            logger.error(f"Error fetching mentions: {e}")
            return []
    
    def delete_tweet(self, tweet_id: str) -> bool:
        """
        Delete a tweet owned by the authenticated user.
        
        Args:
            tweet_id: ID of tweet to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.delete_tweet(tweet_id)
            
            if response.data and response.data.get('deleted'):
                logger.info(f"Successfully deleted tweet {tweet_id}")
                return True
            else:
                logger.warning(f"Tweet {tweet_id} deletion returned unexpected response")
                return False
                
        except tweepy.errors.Forbidden as e:
            logger.error(f"Forbidden to delete tweet {tweet_id}: {e}")
            return False
        except tweepy.errors.TweepyException as e:
            logger.error(f"Error deleting tweet {tweet_id}: {e}")
            return False
    
    def search_recent_tweets(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search recent tweets (free tier: last 7 days).
        
        Args:
            query: Search query
            max_results: Maximum results (10-100)
            
        Returns:
            List of tweet dictionaries
        """
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=["created_at", "text", "author_id", "lang"]
            )
            
            if not response.data:
                return []
            
            tweets = []
            for tweet in response.data:
                tweets.append({
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": tweet.author_id,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "language": tweet.lang if hasattr(tweet, 'lang') else "unknown"
                })
            
            return tweets
            
        except tweepy.errors.TweepyException as e:
            logger.error(f"Error searching tweets: {e}")
            return []


# Global singleton instance
twitter_client = None


def get_twitter_client() -> TwitterClient:
    """Get or create the global Twitter client instance."""
    global twitter_client
    if twitter_client is None:
        twitter_client = TwitterClient()
    return twitter_client
