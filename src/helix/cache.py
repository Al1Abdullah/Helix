"""Async in-memory TTL cache — no external dependencies."""
import asyncio
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, default_ttl: int = 300):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        async with self._lock:
            self._store[key] = (value, time.monotonic() + (ttl or self.default_ttl))

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        now = time.monotonic()
        total = len(self._store)
        valid = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        return {"total_keys": total, "valid_keys": valid, "expired_keys": total - valid}


from helix.config import cache as _cfg

synthesis_cache = TTLCache(default_ttl=_cfg.synthesis_ttl)
trials_cache    = TTLCache(default_ttl=_cfg.trials_ttl)
papers_cache    = TTLCache(default_ttl=_cfg.papers_ttl)
drugs_cache     = TTLCache(default_ttl=_cfg.drugs_ttl)
