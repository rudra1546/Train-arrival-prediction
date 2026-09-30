"""
In-memory TTL cache for Live Railway ETA responses.
Prevents redundant external API hits to RailRadar for repeated queries on the same train.
Thread-safe and configurable via RAILRADAR_CACHE_TTL_SECONDS.
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple

from app.live.config import RAILRADAR_CACHE_TTL_SECONDS


class LiveETACache:
    """Thread-safe in-memory cache with per-item TTL expiration."""

    def __init__(self, default_ttl: float = RAILRADAR_CACHE_TTL_SECONDS):
        self._default_ttl = default_ttl
        self._cache: Dict[str, Tuple[float, Any]] = {}  # key -> (expires_at, data)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _build_key(self, train_no: str, journey_date: Optional[str] = None) -> str:
        clean_train = str(train_no).strip().zfill(5)
        clean_date = str(journey_date).strip() if journey_date else "latest"
        return f"{clean_train}:{clean_date}"

    def get(self, train_no: str, journey_date: Optional[str] = None) -> Optional[Any]:
        """Retrieve unexpired entry, or None if expired or absent."""
        key = self._build_key(train_no, journey_date)
        now = time.monotonic()
        with self._lock:
            if key in self._cache:
                expires_at, data = self._cache[key]
                if now < expires_at:
                    self._hits += 1
                    return data
                else:
                    # Expired
                    del self._cache[key]
            self._misses += 1
            return None

    def set(
        self,
        train_no: str,
        data: Any,
        journey_date: Optional[str] = None,
        ttl: Optional[float] = None
    ) -> None:
        """Store entry with TTL."""
        key = self._build_key(train_no, journey_date)
        duration = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + duration
        with self._lock:
            self._cache[key] = (expires_at, data)

    def invalidate(self, train_no: str, journey_date: Optional[str] = None) -> None:
        """Remove specific item from cache."""
        key = self._build_key(train_no, journey_date)
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Evict all items and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> Dict[str, int]:
        """Return cache hit and miss statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses
            }


# Global singleton cache instance
eta_cache = LiveETACache()
