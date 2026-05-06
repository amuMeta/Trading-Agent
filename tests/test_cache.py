"""
src/core/cache.py 测试
"""

import pytest
import time
from src.core.cache import MemoryCache, DiskCache


class TestMemoryCache:
    """内存缓存测试"""

    def test_set_and_get(self):
        cache = MemoryCache(max_size=100, default_ttl=60)

        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")

        assert result == {"data": "value1"}

    def test_get_nonexistent(self):
        cache = MemoryCache(max_size=100, default_ttl=60)

        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiration(self):
        cache = MemoryCache(max_size=100, default_ttl=1)

        cache.set("key1", "value1")
        time.sleep(1.1)

        result = cache.get("key1")
        assert result is None

    def test_lru_eviction(self):
        cache = MemoryCache(max_size=3, default_ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_delete(self):
        cache = MemoryCache(max_size=100, default_ttl=60)

        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_clear(self):
        cache = MemoryCache(max_size=100, default_ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats(self):
        cache = MemoryCache(max_size=100, default_ttl=60)

        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_hit_rate(self):
        cache = MemoryCache(max_size=100, default_ttl=60)

        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["hit_rate"] == pytest.approx(66.67, rel=0.1)


class TestDiskCache:
    """磁盘缓存测试"""

    def test_set_and_get(self, tmp_path):
        cache = DiskCache(cache_dir=str(tmp_path / "cache"), default_ttl=60)

        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")

        assert result == {"data": "value1"}

    def test_get_nonexistent(self, tmp_path):
        cache = DiskCache(cache_dir=str(tmp_path / "cache"), default_ttl=60)

        result = cache.get("nonexistent")
        assert result is None

    def test_delete(self, tmp_path):
        cache = DiskCache(cache_dir=str(tmp_path / "cache"), default_ttl=60)

        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_stats(self, tmp_path):
        cache = DiskCache(cache_dir=str(tmp_path / "cache"), default_ttl=60)

        cache.set("key1", "value1")
        cache.get("key1")

        stats = cache.get_stats()
        assert stats["writes"] >= 1
        assert stats["files"] >= 1