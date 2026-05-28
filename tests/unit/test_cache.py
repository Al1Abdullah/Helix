"""Unit tests for TTLCache — no network calls."""
import asyncio
import time
import pytest
from helix.cache import TTLCache


@pytest.mark.asyncio
async def test_set_and_get():
    cache = TTLCache(default_ttl=60)
    await cache.set("k", {"v": 1})
    assert await cache.get("k") == {"v": 1}


@pytest.mark.asyncio
async def test_get_missing_key():
    cache = TTLCache(default_ttl=60)
    assert await cache.get("does_not_exist") is None


@pytest.mark.asyncio
async def test_expired_entry():
    """Manually plant an already-expired entry and verify it's evicted on get."""
    cache = TTLCache(default_ttl=60)
    async with cache._lock:
        cache._store["stale"] = ("value", time.monotonic() - 1)  # expired 1s ago
    assert await cache.get("stale") is None
    # Key should have been cleaned up
    assert "stale" not in cache._store


@pytest.mark.asyncio
async def test_delete_existing():
    cache = TTLCache(default_ttl=60)
    await cache.set("key", "val")
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_delete_nonexistent():
    cache = TTLCache(default_ttl=60)
    await cache.delete("ghost")  # must not raise


@pytest.mark.asyncio
async def test_clear():
    cache = TTLCache(default_ttl=60)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.clear()
    assert cache.stats()["total_keys"] == 0


@pytest.mark.asyncio
async def test_stats_all_valid():
    cache = TTLCache(default_ttl=60)
    await cache.set("x", 1)
    await cache.set("y", 2)
    s = cache.stats()
    assert s["total_keys"] == 2
    assert s["valid_keys"] == 2
    assert s["expired_keys"] == 0


@pytest.mark.asyncio
async def test_stats_with_expired():
    cache = TTLCache(default_ttl=60)
    await cache.set("live", "value")
    async with cache._lock:
        cache._store["dead"] = ("value", time.monotonic() - 1)
    s = cache.stats()
    assert s["total_keys"] == 2
    assert s["valid_keys"] == 1
    assert s["expired_keys"] == 1


@pytest.mark.asyncio
async def test_custom_ttl_overrides_default():
    cache = TTLCache(default_ttl=10)
    await cache.set("key", "val", ttl=3600)
    _, expires_at = cache._store["key"]
    # Should expire roughly 3600s from now, not 10s
    assert expires_at > time.monotonic() + 3590
