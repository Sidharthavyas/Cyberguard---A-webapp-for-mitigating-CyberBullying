"""
In-memory metrics tracking system with MongoDB persistence.
Data is tracked in-memory for speed and periodically flushed to MongoDB.
On startup, loads the last snapshot from MongoDB.
"""

from threading import Lock
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MetricsTracker:
    """Thread-safe in-memory metrics storage with MongoDB persistence."""
    
    def __init__(self):
        self._lock = Lock()
        self.total_scanned = 0
        self.total_flagged = 0
        self.total_deleted = 0
        self.per_language: Dict[str, Dict[str, int]] = {}
        self._flush_counter = 0
        self._flush_interval = 10  # Flush to MongoDB every N increments
        
    def increment_scanned(self, language: str = "unknown"):
        """Increment total scanned counter and per-language counter."""
        with self._lock:
            self.total_scanned += 1
            self._ensure_language_exists(language)
            self.per_language[language]["scanned"] += 1
            
    def increment_flagged(self, language: str = "unknown"):
        """Increment total flagged counter and per-language counter."""
        with self._lock:
            self.total_flagged += 1
            self._ensure_language_exists(language)
            self.per_language[language]["flagged"] += 1
            
    def increment_deleted(self, language: str = "unknown"):
        """Increment total deleted counter and per-language counter."""
        with self._lock:
            self.total_deleted += 1
            self._ensure_language_exists(language)
            self.per_language[language]["deleted"] += 1
    
    def _ensure_language_exists(self, language: str):
        """Ensure language entry exists in per_language dict."""
        if language not in self.per_language:
            self.per_language[language] = {
                "scanned": 0,
                "flagged": 0,
                "deleted": 0
            }
    
    def get_stats(self) -> Dict:
        """Get current metrics snapshot."""
        with self._lock:
            return {
                "total_scanned": self.total_scanned,
                "total_flagged": self.total_flagged,
                "total_deleted": self.total_deleted,
                "per_language": dict(self.per_language),
                "status": "active",
            }
    
    def load_from_snapshot(self, snapshot: Dict):
        """Load metrics from a MongoDB snapshot (call on startup)."""
        with self._lock:
            self.total_scanned = snapshot.get("total_scanned", 0)
            self.total_flagged = snapshot.get("total_flagged", 0)
            self.total_deleted = snapshot.get("total_deleted", 0)
            self.per_language = snapshot.get("per_language", {})
            logger.info(
                f"Loaded metrics from MongoDB: scanned={self.total_scanned}, "
                f"flagged={self.total_flagged}, deleted={self.total_deleted}"
            )
    
    async def flush_to_mongodb(self):
        """Flush current metrics to MongoDB."""
        try:
            import database as db
            stats = self.get_stats()
            await db.save_metrics_snapshot(stats)
        except Exception as e:
            logger.error(f"Error flushing metrics to MongoDB: {e}")
    
    async def _maybe_flush(self):
        """Flush to MongoDB periodically."""
        self._flush_counter += 1
        if self._flush_counter >= self._flush_interval:
            self._flush_counter = 0
            await self.flush_to_mongodb()
    
    def reset(self):
        """Reset all metrics to zero. Use with caution."""
        with self._lock:
            self.total_scanned = 0
            self.total_flagged = 0
            self.total_deleted = 0
            self.per_language = {}
            logger.warning("All metrics have been reset to zero")


# Global singleton instance
metrics = MetricsTracker()
