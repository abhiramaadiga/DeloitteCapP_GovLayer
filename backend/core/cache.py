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
_NEGATIVE_SENTINEL = "__NOT_REVOKED__"

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
    # Pre-warm socket connection pool so first request doesn't pay TCP handshake penalty
    try:
        _REDIS_CLIENT.get("health_prewarm")
    except Exception:
        pass
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
                _REDIS_CLIENT.set(namespaced_key, value, ex=ttl_seconds)
            except Exception:
                pass

    @staticmethod
    def get(key: str) -> Optional[str]:
        namespaced_key = settings.REDIS_PREFIX + key
        
        # 1. Fast-path: Check L1 memory (<0.01ms)
        if namespaced_key in _L1_CACHE:
            if time.time() < _L1_EXPIRY.get(namespaced_key, 0):
                cached = _L1_CACHE[namespaced_key]
                if cached == _NEGATIVE_SENTINEL:
                    return None
                return cached
            else:
                # Expired
                _L1_CACHE.pop(namespaced_key, None)
                _L1_EXPIRY.pop(namespaced_key, None)
                
        # 2. Secondary check: Redis
        if _REDIS_CLIENT:
            try:
                val = _REDIS_CLIENT.get(namespaced_key)
                if val is not None:
                    _L1_CACHE[namespaced_key] = val
                    _L1_EXPIRY[namespaced_key] = time.time() + 60
                    return val
                else:
                    # Negative cache: agent is healthy/unrevoked. Store for 60s to avoid repeated Redis roundtrips.
                    _L1_CACHE[namespaced_key] = _NEGATIVE_SENTINEL
                    _L1_EXPIRY[namespaced_key] = time.time() + 60.0
                    return None
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

    @staticmethod
    def clear_all_revocations() -> None:
        """Clears all agent quarantines from both L1 cache and Redis."""
        prefix = settings.REDIS_PREFIX + "revoked:agent:"
        keys_to_delete = [k for k in list(_L1_CACHE.keys()) if k.startswith(prefix) or "revoked:agent:" in k]
        for k in keys_to_delete:
            _L1_CACHE.pop(k, None)
            _L1_EXPIRY.pop(k, None)
        if _REDIS_CLIENT:
            try:
                for k in _REDIS_CLIENT.keys(prefix + "*"):
                    _REDIS_CLIENT.delete(k)
            except Exception:
                pass