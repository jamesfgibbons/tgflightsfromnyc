import os
import json
import uuid
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to connect to Redis, fall back to in-memory if not available
try:
    import redis
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), 
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2
    )
    # Test connection
    redis_client.ping()
    USE_REDIS = True
    logger.info("Connected to Redis for session storage")
except Exception as e:
    logger.warning(f"Redis unavailable ({e}), using in-memory session store")
    redis_client = None
    USE_REDIS = False

# In-memory session store as fallback
_sessions: Dict[str, Dict[str, Any]] = {}
SESSION_TTL = int(os.getenv("SESSION_TTL", "300"))  # 5 minutes default to prevent memory leaks

def _cleanup_expired_sessions():
    """Remove expired sessions from memory."""
    if USE_REDIS:
        return  # Redis handles expiration automatically
        
    current_time = time.time()
    expired_keys = [
        sid for sid, data in _sessions.items() 
        if data.get('expires_at', 0) < current_time
    ]
    for sid in expired_keys:
        del _sessions[sid]
    
    if expired_keys:
        logger.info(f"Cleaned up {len(expired_keys)} expired sessions")

def new_session(data) -> str:
    """Create new session with data and return session ID."""
    sid = str(uuid.uuid4())
    
    if USE_REDIS:
        try:
            redis_client.setex(f"session:{sid}", SESSION_TTL, json.dumps(data))
            logger.debug(f"Stored session {sid} in Redis with {SESSION_TTL}s TTL")
            return sid
        except Exception as e:
            logger.error(f"Redis write failed ({e}), falling back to memory")
            # Fall through to memory storage
    
    # In-memory storage (fallback or primary if Redis unavailable)
    _cleanup_expired_sessions()
    expires_at = time.time() + SESSION_TTL
    
    _sessions[sid] = {
        'data': data,
        'expires_at': expires_at,
        'created_at': time.time()
    }
    
    logger.debug(f"Stored session {sid} in memory with {SESSION_TTL}s TTL")
    return sid

def get_session(sid: str) -> Optional[Any]:
    """Get session data by session ID."""
    if USE_REDIS:
        try:
            data = redis_client.get(f"session:{sid}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis read failed ({e}), checking memory fallback")
            # Fall through to memory check
    
    # In-memory retrieval
    _cleanup_expired_sessions()
    
    session = _sessions.get(sid)
    if session and session.get('expires_at', 0) > time.time():
        return session['data']
    
    return None

def get_session_stats() -> Dict[str, Any]:
    """Get session storage statistics for monitoring."""
    stats = {
        "storage_type": "redis" if USE_REDIS else "memory",
        "session_ttl": SESSION_TTL
    }
    
    if USE_REDIS:
        try:
            redis_info = redis_client.info()
            stats.update({
                "redis_connected": True,
                "redis_used_memory": redis_info.get("used_memory_human", "unknown"),
                "redis_connected_clients": redis_info.get("connected_clients", 0)
            })
        except:
            stats["redis_connected"] = False
    else:
        stats.update({
            "memory_sessions": len(_sessions),
            "redis_connected": False
        })
    
    return stats 