"""
Reddit poller for CyberGuard - Background monitoring of Reddit comments/posts.
Integrates with dynamic platform manager.
"""

import asyncio
import logging
from typing import Dict
from reddit_client import get_reddit_client
from platform_manager import PlatformPoller
from models import get_detector
from moderation import moderation_engine
from websocket_manager import manager

logger = logging.getLogger(__name__)


class RedditPoller(PlatformPoller):
    """Polls Reddit for comments/posts and moderates them"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize Reddit poller.
        
        Args:
            credentials: Dict with Reddit API credentials
        """
        super().__init__("Reddit")
        
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.user_agent = credentials.get("user_agent", "CyberGuard/1.0")
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.subreddits = credentials.get("subreddits", [])
        self.poll_interval = int(credentials.get("poll_interval", 120))  # 2 minutes default
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Reddit client_id and client_secret are required")
        
        # Initialize Reddit client
        self.client = get_reddit_client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
            username=self.username,
            password=self.password,
            subreddits=self.subreddits
        )
        
        self.processed_items = set()  # Track processed comment/post IDs
        
        logger.info(f"Reddit poller initialized (interval: {self.poll_interval}s)")
    
    async def _poll_loop(self):
        """Main polling loop for Reddit content"""
        logger.info("Reddit poller started")
        
        while self.is_running:
            try:
                await self._poll_once()
                await asyncio.sleep(self.poll_interval)
            
            except asyncio.CancelledError:
                logger.info("Reddit poller cancelled")
                break
            except Exception as e:
                logger.error(f"Reddit poller error: {e}")
                await asyncio.sleep(self.poll_interval)
        
        logger.info("Reddit poller stopped")
    
    async def _poll_once(self):
        """Poll Reddit once for new content"""
        try:
            # Fetch recent comments
            comments = await self.client.get_recent_comments(limit=50)
            
            # Fetch recent posts (optional, can be disabled for performance)
            # posts = await self.client.get_recent_posts(limit=25)
            
            # Combine all items
            all_items = comments  # + posts
            
            if not all_items:
                logger.debug("No Reddit content found")
                return
            
            # Process new items only
            new_items = [
                item for item in all_items 
                if item["id"] not in self.processed_items
            ]
            
            if not new_items:
                logger.debug("No new Reddit content")
                return
            
            logger.info(f"Processing {len(new_items)} new Reddit items")
            
            # Moderate each item
            for item in new_items:
                await self._moderate_item(item)
                self.processed_items.add(item["id"])
            
            # Clean up old processed IDs (keep last 10000)
            if len(self.processed_items) > 10000:
                self.processed_items = set(list(self.processed_items)[-5000:])
        
        except Exception as e:
            logger.error(f"Error in Reddit poll: {e}")
    
    async def _moderate_item(self, item: Dict):
        """
        Moderate a single Reddit comment/post.
        
        Args:
            item: Reddit item dictionary
        """
        try:
            # Prepare item for moderation
            tweet_data = {
                "id": item["id"],
                "text": item["text"],
                "language": "unknown"  # Will be detected by moderation engine
            }
            
            # Run moderation
            result = await moderation_engine.process_tweet(tweet_data)
            
            # Update result with Reddit-specific fields
            result.update({
                "platform": "reddit",
                "author": item["author"],
                "subreddit": item["subreddit"],
                "permalink": item["permalink"]
            })
            
            # If item was flagged for deletion, try to delete/report
            if result["action"] == "delete" and result["deleted"]:
                # Try to delete (requires mod permissions)
                deleted = await self.client.delete_comment(item["id"])
                
                if deleted:
                    logger.warning(f"Deleted Reddit item {item['id']}")
                    result["deleted"] = True
                else:
                    # If can't delete, report instead
                    reported = await self.client.report_comment(
                        item["id"], 
                        reason="Toxic content detected by CyberGuard"
                    )
                    result["deleted"] = False
                    result["action"] = "reported" if reported else "flag"
                    logger.info(f"Reported Reddit item {item['id']}")
            
            # Broadcast to WebSocket clients
            await manager.broadcast(result)
        
        except Exception as e:
            logger.error(f"Error moderating Reddit item {item['id']}: {e}")
