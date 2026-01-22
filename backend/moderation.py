"""
Auto-moderation engine with configurable rules.
Processes tweets, applies moderation decisions, and broadcasts events.
Uses binary classification (0=safe, 1=bullying) with optimal thresholds.
"""

import os
import logging
from typing import Dict, Any
from models import get_detector
from twitter_client import get_twitter_client
from metrics import metrics
from websocket_manager import manager

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
        
        logger.info(f"Processing tweet {tweet_id}")
        
        # Run ML inference
        detector = get_detector()
        analysis = detector.analyze(text)
        
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
                twitter = get_twitter_client()
                deleted = twitter.delete_tweet(tweet_id)
                
                if deleted:
                    metrics.increment_deleted(language)
                    logger.warning(f"DELETED tweet {tweet_id} (Bullying, confidence: {confidence:.2f})")
                else:
                    logger.error(f"Failed to delete tweet {tweet_id}")
                    action = "delete_failed"
            else:
                # Flag for review (lower confidence)
                action = "flag"
                metrics.increment_flagged(language)
                logger.warning(f"FLAGGED tweet {tweet_id} (Bullying, confidence: {confidence:.2f})")
        else:
            # Safe content
            logger.info(f"IGNORED tweet {tweet_id} (Safe, confidence: {confidence:.2f})")
        
        # Prepare event for WebSocket broadcast
        event = {
            "tweet_id": str(tweet_id),
            "text": text,
            "language": language,
            "label": label,
            "label_name": label_name,
            "confidence": confidence,
            "bullying_probability": bullying_probability,
            "action": action,
            "deleted": deleted,
            "primary_label": analysis["primary_label"],
            "secondary_label": analysis["secondary_label"],
            "source": analysis["source"]
        }
        
        # Broadcast to all connected clients
        await manager.broadcast(event)
        
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
