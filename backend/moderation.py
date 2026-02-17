"""
Auto-moderation engine with configurable rules.
Processes tweets, applies moderation decisions, and broadcasts events.
Uses binary classification (0=safe, 1=bullying) with optimal thresholds.
"""

import os
import re
import logging
from typing import Dict, Any
from models import get_detector
from twitter_client import get_twitter_client
from metrics import metrics
from websocket_manager import manager
import database as db

logger = logging.getLogger(__name__)


class ModerationEngine:
    """Automated moderation based on toxicity levels."""
    
    def __init__(self):
        self.delete_threshold = int(os.getenv("DELETE_THRESHOLD", "4"))
        self.flag_threshold = int(os.getenv("FLAG_THRESHOLD", "3"))
        logger.info(
            f"Moderation thresholds - Delete: ≥{self.delete_threshold}, "
            f"Flag: ={self.flag_threshold}"
        )
    
    @staticmethod
    def clean_text_for_ml(text: str) -> str:
        """
        Clean text before sending to ML model.
        Removes @mentions, URLs, and extra whitespace that
        confuse the model (trained on clean text).
        """
        # Remove @mentions (e.g. @UnbotheredDev24)
        cleaned = re.sub(r'@\w+', '', text)
        # Remove URLs
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        # Remove # symbol but keep the word
        cleaned = cleaned.replace('#', '')
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    async def process_tweet(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single tweet through the moderation pipeline.
        Uses binary classification: 0=safe, 1=bullying
        
        Args:
            tweet: Tweet dictionary with 'id', 'text', 'language' fields
            
        Returns:
            Moderation result dictionary
        """
        tweet_id = tweet.get("id")
        text = tweet.get("text", "")
        platform = tweet.get("platform", "twitter")
        
        logger.info(f"Processing {platform} content {tweet_id}")
        
        # Clean text for ML — strip @mentions, URLs, etc.
        cleaned_text = self.clean_text_for_ml(text)
        if not cleaned_text:
            logger.info(f"SKIPPED {platform} content {tweet_id} (empty after cleaning)")
            return {"tweet_id": str(tweet_id), "action": "ignore", "label_name": "SAFE"}
        
        # Run ML inference on CLEANED text
        detector = get_detector()
        analysis = detector.analyze(cleaned_text)
        
        label = analysis["label"]  # 0=safe, 1=bullying
        label_name = analysis["label_name"]  # "SAFE" or "BULLYING"
        language = analysis["language"]
        confidence = analysis["confidence"]
        bullying_probability = analysis["bullying_probability"]
        
        # Update metrics
        metrics.increment_scanned(language)
        
        # Determine action based on binary classification
        action = "ignore"
        deleted = False
        
        if label == 1:  # Bullying detected
            # Check confidence threshold for deletion
            # High confidence (>= threshold) -> delete
            # Lower confidence -> flag for review
            delete_confidence = float(os.getenv("DELETE_CONFIDENCE_THRESHOLD", "0.8"))
            
            if confidence >= delete_confidence:
                # Delete tweet
                action = "delete"
                
                # Only attempt deletion here if it's Twitter
                # Other platforms handle deletion in their poller
                if platform == "twitter":
                    twitter = get_twitter_client()
                    result = twitter.delete_tweet(tweet_id)
                    
                    if result == "deleted":
                        deleted = True
                        metrics.increment_deleted(language)
                        logger.warning(f"DELETED tweet {tweet_id} (Bullying, confidence: {confidence:.2f})")
                    elif result == "hidden":
                        deleted = False
                        action = "hidden"
                        metrics.increment_deleted(language)
                        logger.warning(f"HIDDEN reply {tweet_id} (Bullying, confidence: {confidence:.2f})")
                    else:
                        logger.error(f"Failed to moderate tweet {tweet_id}")
                        action = "delete_failed"
                else:
                    logger.info(f"Marked {platform} content {tweet_id} for deletion (handled by poller)")
            else:
                # Flag for review (lower confidence)
                action = "flag"
                metrics.increment_flagged(language)
                logger.warning(f"FLAGGED {platform} content {tweet_id} (Bullying, confidence: {confidence:.2f})")
        else:
            # Safe content
            logger.info(f"IGNORED {platform} content {tweet_id} (Safe, confidence: {confidence:.2f})")
        
        # Prepare event for WebSocket broadcast
        event = {
            "tweet_id": str(tweet_id),
            "text": text,
            "language": language,
            "label": int(label),
            "label_name": label_name,
            "confidence": float(confidence),
            "bullying_probability": float(bullying_probability),
            "deleted": deleted,
            "action": action,
            "timestamp": tweet.get("created_at"),
            "platform": platform,
            "author": tweet.get("author_id") or tweet.get("author"),
            "channel": tweet.get("channel_id") or tweet.get("channel"),
            "primary_label": analysis["primary_label"],
            "secondary_label": analysis["secondary_label"],
            "models_agree": analysis["models_agree"],
            "confidence_gap": analysis["confidence_gap"],
            "source": analysis["source"]
        }
        
        # Broadcast to all connected clients
        await manager.broadcast(event)
        
        # Persist to MongoDB
        await db.save_platform_message(tweet)
        await db.save_moderation_event(event)
        
        return event
    
    def should_process(self, tweet: Dict[str, Any]) -> bool:
        """
        Determine if a tweet should be processed.
        Can add filtering logic here (e.g., language filter, author filter).
        
        Args:
            tweet: Tweet dictionary
            
        Returns:
            True if should process, False to skip
        """
        # For now, process all tweets
        return True


# Global singleton instance
moderation_engine = ModerationEngine()
