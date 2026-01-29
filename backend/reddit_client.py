"""
Reddit client for CyberGuard - Moderate Reddit comments and posts.
Uses Reddit API (PRAW - Python Reddit API Wrapper).
"""

import os
import logging
import praw
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RedditModerationClient:
    """Reddit client for comment/post moderation"""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str, 
                 username: Optional[str] = None, password: Optional[str] = None,
                 subreddits: Optional[List[str]] = None):
        """
        Initialize Reddit client.
        
        Args:
            client_id: Reddit app client ID
            client_secret: Reddit app client secret
            user_agent: User agent (e.g., 'CyberGuard/1.0')
            username: Reddit username (optional, for write access)
            password: Reddit password (optional, for write access)
            subreddits: List of subreddits to monitor (e.g., ['python', 'programming'])
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self.subreddits = subreddits or []
        
        # Initialize PRAW client
        if username and password:
            # Authenticated (can moderate)
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                username=username,
                password=password
            )
        else:
            # Read-only
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
        
        self.is_ready = True
        logger.info(f"Reddit client initialized (authenticated: {bool(username)})")
    
    async def get_recent_comments(self, limit: int = 100) -> List[Dict]:
        """
        Fetch recent comments from monitored subreddits.
        
        Args:
            limit: Max comments to fetch per subreddit
            
        Returns:
            List of comment dictionaries
        """
        if not self.is_ready:
            logger.warning("Reddit client not ready")
            return []
        
        comments = []
        
        try:
            for subreddit_name in self.subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    logger.info(f"Fetching comments from r/{subreddit_name}")
                    
                    # Get recent comments
                    for comment in subreddit.comments(limit=limit):
                        # Skip deleted/removed comments
                        if comment.author is None or comment.body in ['[deleted]', '[removed]']:
                            continue
                        
                        comments.append({
                            "id": comment.id,
                            "text": comment.body,
                            "author": str(comment.author),
                            "author_id": comment.author.id if hasattr(comment.author, 'id') else None,
                            "subreddit": subreddit_name,
                            "post_title": comment.submission.title if hasattr(comment, 'submission') else None,
                            "post_id": comment.submission.id if hasattr(comment, 'submission') else None,
                            "score": comment.score,
                            "timestamp": datetime.fromtimestamp(comment.created_utc).isoformat(),
                            "permalink": f"https://reddit.com{comment.permalink}",
                            "platform": "reddit"
                        })
                
                except Exception as e:
                    logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                    continue
            
            logger.info(f"Fetched {len(comments)} Reddit comments")
            return comments
        
        except Exception as e:
            logger.error(f"Error fetching Reddit comments: {e}")
            return []
    
    async def get_recent_posts(self, limit: int = 50) -> List[Dict]:
        """
        Fetch recent posts from monitored subreddits.
        
        Args:
            limit: Max posts to fetch per subreddit
            
        Returns:
            List of post dictionaries
        """
        if not self.is_ready:
            logger.warning("Reddit client not ready")
            return []
        
        posts = []
        
        try:
            for subreddit_name in self.subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    logger.info(f"Fetching posts from r/{subreddit_name}")
                    
                    # Get recent posts
                    for post in subreddit.new(limit=limit):
                        # Skip deleted/removed posts
                        if post.author is None:
                            continue
                        
                        posts.append({
                            "id": post.id,
                            "text": post.title + "\n\n" + (post.selftext or ""),
                            "title": post.title,
                            "author": str(post.author),
                            "author_id": post.author.id if hasattr(post.author, 'id') else None,
                            "subreddit": subreddit_name,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "timestamp": datetime.fromtimestamp(post.created_utc).isoformat(),
                            "permalink": f"https://reddit.com{post.permalink}",
                            "platform": "reddit"
                        })
                
                except Exception as e:
                    logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
                    continue
            
            logger.info(f"Fetched {len(posts)} Reddit posts")
            return posts
        
        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {e}")
            return []
    
    async def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a Reddit comment (requires mod permissions).
        
        Args:
            comment_id: Reddit comment ID
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.username:
            logger.error("Cannot delete comment: not authenticated")
            return False
        
        try:
            comment = self.reddit.comment(id=comment_id)
            comment.mod.remove()
            logger.info(f"Deleted Reddit comment {comment_id}")
            return True
        
        except praw.exceptions.PRAWException as e:
            logger.error(f"Failed to delete Reddit comment: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting Reddit comment: {e}")
            return False
    
    async def report_comment(self, comment_id: str, reason: str = "Toxic content") -> bool:
        """
        Report a Reddit comment.
        
        Args:
            comment_id: Reddit comment ID
            reason: Report reason
            
        Returns:
            True if reported, False otherwise
        """
        try:
            comment = self.reddit.comment(id=comment_id)
            comment.report(reason)
            logger.info(f"Reported Reddit comment {comment_id}")
            return True
        
        except praw.exceptions.PRAWException as e:
            logger.error(f"Failed to report Reddit comment: {e}")
            return False
        except Exception as e:
            logger.error(f"Error reporting Reddit comment: {e}")
            return False


def get_reddit_client(client_id: str, client_secret: str, user_agent: str,
                      username: Optional[str] = None, password: Optional[str] = None,
                      subreddits: Optional[List[str]] = None) -> RedditModerationClient:
    """
    Create a Reddit client instance.
    
    Args:
        client_id: Reddit app client ID
        client_secret: Reddit app client secret
        user_agent: User agent string
        username: Reddit username (optional)
        password: Reddit password (optional)
        subreddits: List of subreddits to monitor
        
    Returns:
        RedditModerationClient instance
    """
    return RedditModerationClient(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        username=username,
        password=password,
        subreddits=subreddits
    )
