"""
backend/core/cache.py
Dual-tier high-speed revocation cache for sub-millisecond status checks.
"""
import time
from typing import Optional, Dict, Any
from backend.core.config import settings

# In-memory L1 cache dictionary (Thread-safe fallback)
_L1_CACHE: Dict[str, Any] = {}
_L1_EXPIRY: Dict[str, float] = {}

# Try connecting to Redis if available
_REDIS_CLIENT = None
try:
    import redis
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=0.2
    )
    client.ping()
    _REDIS_CLIENT = client
    print("[Cache] Connected to Redis successfully.")
except Exception:
    print("[Cache] Redis not detected. Using high-speed in-memory L1 cache fallback.")

class RevocationCache:
    """Provides <0.2ms key-value lookups for agent revocation status."""
    
    @staticmethod
    def set(key: str, value: str, ttl_seconds: int = 86400) -> None:
        namespaced_key = settings.REDIS_PREFIX + key
        
        # 1. Store in L1 memory
        _L1_CACHE[namespaced_key] = value
        _L1_EXPIRY[namespaced_key] = time.time() + ttl_seconds
        
        # 2. Store in Redis if connected
        if _REDIS_CLIENT:
            try:
                _REDIS_CLIENT.setex(namespaced_key, ttl_seconds, value)
            except Exception:
                pass

    @staticmethod
    def get(key: str) -> Optional[str]:
        namespaced_key = settings.REDIS_PREFIX + key
        
        # 1. Fast-path: Check L1 memory (<0.01ms)
        if namespaced_key in _L1_CACHE:
            if time.time() < _L1_EXPIRY.get(namespaced_key, 0):
                return _L1_CACHE[namespaced_key]
            else:
                # Expired
                _L1_CACHE.pop(namespaced_key, None)
                _L1_EXPIRY.pop(namespaced_key, None)
                
        # 2. Secondary check: Redis
        if _REDIS_CLIENT:
            try:
                val = _REDIS_CLIENT.get(namespaced_key)
                if val:
                    _L1_CACHE[namespaced_key] = val
                    _L1_EXPIRY[namespaced_key] = time.time() + 60
                    return val
            except Exception:
                pass
                
        return None

    @staticmethod
    def delete(key: str) -> None:
        namespaced_key = settings.REDIS_PREFIX + key
        _L1_CACHE.pop(namespaced_key, None)
        _L1_EXPIRY.pop(namespaced_key, None)
        if _REDIS_CLIENT:
            try:
                _REDIS_CLIENT.delete(namespaced_key)
            except Exception:
                pass