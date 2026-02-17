"""
MongoDB database module for CyberGuard.
Provides persistent storage for moderation events, platform messages,
user sessions, and metrics. Uses motor (async MongoDB driver).
Includes auto-cleanup to prevent unbounded growth.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Global MongoDB client and database
_client: Optional[AsyncIOMotorClient] = None
_db = None


async def init_mongodb():
    """
    Initialize MongoDB connection.
    Call this once during app startup.
    """
    global _client, _db

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.warning("MONGODB_URI not set — MongoDB persistence disabled")
        return False

    try:
        _client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Ping to verify connection
        await _client.admin.command("ping")

        _db = _client.get_default_database()
        if _db is None:
            # Fallback if database not in URI
            _db = _client["cyberguard"]

        logger.info(f"✓ Connected to MongoDB database: {_db.name}")

        # Create indexes for fast queries + TTL cleanup
        await _create_indexes()
        # Run cleanup on startup to trim old records
        await cleanup_old_records()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        _client = None
        _db = None
        return False


# Max records to keep per collection (prevents unbounded growth)
MAX_RECORDS = int(os.getenv("MAX_MONGO_RECORDS", "5000"))
# Auto-expire records older than this (days)
TTL_DAYS = int(os.getenv("MONGO_TTL_DAYS", "7"))


async def _create_indexes():
    """Create indexes for efficient querying + TTL auto-expiry."""
    if _db is None:
        return

    # moderation_events: unique by platform_id + platform, indexed by timestamp
    await _db.moderation_events.create_index(
        [("platform_id", 1), ("platform", 1)], unique=True
    )
    await _db.moderation_events.create_index([("timestamp", -1)])
    await _db.moderation_events.create_index([("platform", 1)])
    await _db.moderation_events.create_index([("action", 1)])
    # TTL index: auto-delete records older than TTL_DAYS
    await _db.moderation_events.create_index(
        [("saved_at", 1)],
        expireAfterSeconds=TTL_DAYS * 86400,
        name="ttl_saved_at"
    )

    # platform_messages: unique by platform_id + platform
    await _db.platform_messages.create_index(
        [("platform_id", 1), ("platform", 1)], unique=True
    )
    await _db.platform_messages.create_index([("fetched_at", -1)])
    await _db.platform_messages.create_index([("platform", 1)])
    # TTL index: auto-delete records older than TTL_DAYS
    await _db.platform_messages.create_index(
        [("fetched_at", 1)],
        expireAfterSeconds=TTL_DAYS * 86400,
        name="ttl_fetched_at"
    )

    # user_sessions: unique by platform
    await _db.user_sessions.create_index([("platform", 1)], unique=True)

    logger.info(f"✓ MongoDB indexes created (TTL: {TTL_DAYS}d, cap: {MAX_RECORDS})")


async def cleanup_old_records():
    """
    Enforce record cap — delete oldest records beyond MAX_RECORDS.
    TTL handles time-based expiry, this handles count-based cap.
    Runs on startup and can be called periodically.
    """
    if _db is None:
        return

    try:
        for collection_name, sort_field in [
            ("moderation_events", "saved_at"),
            ("platform_messages", "fetched_at"),
        ]:
            collection = _db[collection_name]
            count = await collection.count_documents({})
            if count > MAX_RECORDS:
                excess = count - MAX_RECORDS
                # Find the oldest 'excess' docs and delete them
                oldest = await collection.find(
                    {}, {"_id": 1}
                ).sort(sort_field, 1).limit(excess).to_list(length=excess)
                
                ids = [doc["_id"] for doc in oldest]
                result = await collection.delete_many({"_id": {"$in": ids}})
                logger.info(
                    f"🗑 Cleaned {result.deleted_count} old records from {collection_name} "
                    f"({count} → {count - result.deleted_count})"
                )
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def is_connected() -> bool:
    """Check if MongoDB is connected."""
    return _db is not None


# ============= MODERATION EVENTS =============

async def save_moderation_event(event: Dict[str, Any]) -> bool:
    """
    Save a moderation event (ML analysis result) to MongoDB.
    Upserts by platform_id + platform to avoid duplicates.

    Args:
        event: Moderation result dict from ModerationEngine.process_tweet()

    Returns:
        True if saved, False otherwise
    """
    if _db is None:
        return False

    try:
        doc = {
            "platform_id": str(event.get("tweet_id") or event.get("id")),
            "platform": event.get("platform", "twitter"),
            "text": event.get("text", ""),
            "label": event.get("label"),
            "label_name": event.get("label_name"),
            "confidence": event.get("confidence"),
            "bullying_probability": event.get("bullying_probability"),
            "action": event.get("action"),
            "deleted": event.get("deleted", False),
            "language": event.get("language", "unknown"),
            "author": event.get("author"),
            "channel": event.get("channel"),
            "primary_label": event.get("primary_label"),
            "secondary_label": event.get("secondary_label"),
            "models_agree": event.get("models_agree"),
            "confidence_gap": event.get("confidence_gap"),
            "source": event.get("source"),
            "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "saved_at": datetime.now(timezone.utc),
        }

        await _db.moderation_events.update_one(
            {"platform_id": doc["platform_id"], "platform": doc["platform"]},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"Error saving moderation event: {e}")
        return False


async def get_moderation_events(
    platform: str = "all",
    limit: int = 50,
    skip: int = 0,
    action_filter: Optional[str] = None,
) -> List[Dict]:
    """
    Get paginated moderation events from MongoDB.

    Args:
        platform: Filter by platform ("all", "twitter", "discord")
        limit: Max results
        skip: Offset for pagination
        action_filter: Filter by action ("flag", "delete", "ignore")

    Returns:
        List of moderation event dicts
    """
    if _db is None:
        return []

    try:
        query: Dict[str, Any] = {}
        if platform != "all":
            query["platform"] = platform
        if action_filter:
            query["action"] = action_filter

        cursor = (
            _db.moderation_events.find(query, {"_id": 0})
            .sort("saved_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)
    except Exception as e:
        logger.error(f"Error fetching moderation events: {e}")
        return []


async def count_moderation_events(platform: str = "all") -> int:
    """Count total moderation events."""
    if _db is None:
        return 0
    try:
        query: Dict[str, Any] = {}
        if platform != "all":
            query["platform"] = platform
        return await _db.moderation_events.count_documents(query)
    except Exception as e:
        logger.error(f"Error counting moderation events: {e}")
        return 0


# ============= PLATFORM MESSAGES =============

async def save_platform_message(message: Dict[str, Any]) -> bool:
    """
    Save a raw platform message (tweet, Discord message).
    Upserts by platform_id + platform.

    Args:
        message: Raw message dict

    Returns:
        True if saved
    """
    if _db is None:
        return False

    try:
        platform = message.get("platform", "twitter")
        platform_id = str(message.get("id") or message.get("tweet_id", ""))

        doc = {
            "platform_id": platform_id,
            "platform": platform,
            "text": message.get("text", ""),
            "author": message.get("author") or message.get("author_id"),
            "author_id": str(message.get("author_id", "")),
            "channel": message.get("channel"),
            "channel_id": message.get("channel_id"),
            "guild": message.get("guild"),
            "guild_id": message.get("guild_id"),
            "language": message.get("language", "unknown"),
            "created_at": message.get("created_at") or message.get("timestamp"),
            "fetched_at": datetime.now(timezone.utc),
        }

        await _db.platform_messages.update_one(
            {"platform_id": platform_id, "platform": platform},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"Error saving platform message: {e}")
        return False


async def is_message_processed(platform_id: str, platform: str) -> bool:
    """
    Check if a message has already been processed (exists in moderation_events).

    Args:
        platform_id: Platform-specific message ID
        platform: Platform name

    Returns:
        True if already processed
    """
    if _db is None:
        return False

    try:
        doc = await _db.moderation_events.find_one(
            {"platform_id": str(platform_id), "platform": platform},
            {"_id": 1},
        )
        return doc is not None
    except Exception as e:
        logger.error(f"Error checking processed message: {e}")
        return False


async def get_platform_messages(
    platform: str = "all", limit: int = 50, skip: int = 0
) -> List[Dict]:
    """Get paginated platform messages."""
    if _db is None:
        return []

    try:
        query: Dict[str, Any] = {}
        if platform != "all":
            query["platform"] = platform

        cursor = (
            _db.platform_messages.find(query, {"_id": 0})
            .sort("fetched_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)
    except Exception as e:
        logger.error(f"Error fetching platform messages: {e}")
        return []


# ============= USER SESSIONS =============

async def save_user_session(session_data: Dict[str, Any]) -> bool:
    """Save/update a user session for a platform."""
    if _db is None:
        return False

    try:
        platform = session_data.get("platform", "twitter")
        doc = {
            **session_data,
            "updated_at": datetime.now(timezone.utc),
        }
        await _db.user_sessions.update_one(
            {"platform": platform},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"Error saving user session: {e}")
        return False


async def get_user_session(platform: str) -> Optional[Dict]:
    """Get stored user session for a platform."""
    if _db is None:
        return None

    try:
        return await _db.user_sessions.find_one(
            {"platform": platform}, {"_id": 0}
        )
    except Exception as e:
        logger.error(f"Error fetching user session: {e}")
        return None


# ============= METRICS SNAPSHOT =============

async def save_metrics_snapshot(metrics_data: Dict[str, Any]) -> bool:
    """
    Save metrics snapshot to MongoDB.
    Uses a single document with _id='current' that gets upserted.
    """
    if _db is None:
        return False

    try:
        doc = {
            **metrics_data,
            "updated_at": datetime.now(timezone.utc),
        }
        await _db.metrics_snapshot.update_one(
            {"_id": "current"},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"Error saving metrics snapshot: {e}")
        return False


async def load_metrics_snapshot() -> Optional[Dict]:
    """Load the last metrics snapshot from MongoDB."""
    if _db is None:
        return None

    try:
        doc = await _db.metrics_snapshot.find_one({"_id": "current"})
        if doc:
            doc.pop("_id", None)
            doc.pop("updated_at", None)
        return doc
    except Exception as e:
        logger.error(f"Error loading metrics snapshot: {e}")
        return None


async def get_aggregate_stats() -> Dict:
    """
    Get aggregate statistics directly from MongoDB collections.
    More accurate than in-memory counters.
    """
    if _db is None:
        return {}

    try:
        total = await _db.moderation_events.count_documents({})
        flagged = await _db.moderation_events.count_documents({"action": "flag"})
        deleted = await _db.moderation_events.count_documents(
            {"action": {"$in": ["delete", "delete_failed"]}, "deleted": True}
        )

        # Per-platform breakdown
        pipeline = [
            {
                "$group": {
                    "_id": "$platform",
                    "total": {"$sum": 1},
                    "flagged": {
                        "$sum": {"$cond": [{"$eq": ["$action", "flag"]}, 1, 0]}
                    },
                    "deleted": {
                        "$sum": {"$cond": [{"$eq": ["$deleted", True]}, 1, 0]}
                    },
                }
            }
        ]
        per_platform = {}
        async for doc in _db.moderation_events.aggregate(pipeline):
            per_platform[doc["_id"]] = {
                "total": doc["total"],
                "flagged": doc["flagged"],
                "deleted": doc["deleted"],
            }

        return {
            "total_scanned": total,
            "total_flagged": flagged,
            "total_deleted": deleted,
            "per_platform": per_platform,
            "source": "mongodb",
        }
    except Exception as e:
        logger.error(f"Error getting aggregate stats: {e}")
        return {}


async def close_mongodb():
    """Close MongoDB connection on shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("✗ MongoDB connection closed")
