import time
import asyncio
from typing import Any, Dict, Optional, Tuple


class SimpleTTLCache:
    def __init__(self, default_ttl_seconds: float = 60.0):
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                # expired
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        async with self._lock:
            self._store[key] = (time.monotonic() + ttl, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


risk_signals_cache = SimpleTTLCache(default_ttl_seconds=60.0)
