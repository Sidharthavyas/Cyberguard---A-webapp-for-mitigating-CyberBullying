"""
In-memory metrics tracking system.
All data is ephemeral and resets on server restart.
Thread-safe operations for concurrent access.
"""

from threading import Lock
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MetricsTracker:
    """Thread-safe in-memory metrics storage."""
    
    def __init__(self):
        self._lock = Lock()
        self.total_scanned = 0
        self.total_flagged = 0
        self.total_deleted = 0
        self.per_language: Dict[str, Dict[str, int]] = {}
        
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
        """
        Get current metrics snapshot.
        
        Returns:
            Dictionary containing all current metrics
        """
        with self._lock:
            return {
                "total_scanned": self.total_scanned,
                "total_flagged": self.total_flagged,
                "total_deleted": self.total_deleted,
                "per_language": dict(self.per_language),
                "status": "in_memory",
                "warning": "Metrics reset on server restart"
            }
    
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
