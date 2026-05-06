"""
TradingAgents 多级缓存系统

提供三级缓存：
- L1: 内存缓存（LRU）- 热点数据如股票行情
- L2: 磁盘缓存 - 会话数据、分析结果
- L3: Redis接口（可选）- 分布式缓存

支持：
- TTL过期
- LRU淘汰
- 缓存统计
- 线程安全
"""

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class MemoryCache:
    """
    LRU内存缓存

    特点：
    - 线程安全
    - LRU淘汰策略
    - 可配置TTL
    - 容量限制
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
        cleanup_interval: int = 60,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval

    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_expired(self, expiry: float) -> bool:
        """检查是否过期"""
        return time.time() > expiry

    def _cleanup_expired(self):
        """清理过期条目"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        with self._lock:
            expired_keys = [
                k for k, (_, expiry) in self._cache.items() if now > expiry
            ]
            for key in expired_keys:
                del self._cache[key]
            self._last_cleanup = now

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            value, expiry = self._cache[key]
            if self._is_expired(expiry):
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1

            expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def cached(self, ttl: Optional[int] = None) -> Callable:
        """
        缓存装饰器

        Args:
            ttl: 过期时间（秒）
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                key = self._generate_key(func.__name__, *args, **kwargs)
                result = self.get(key)

                if result is not None:
                    return result

                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result

            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": round(hit_rate * 100, 2),
            }


class DiskCache:
    """
    磁盘缓存

    特点：
    - 持久化存储
    - 自动过期清理
    - JSON格式存储
    """

    def __init__(
        self,
        cache_dir: str = "src/cache",
        max_size_mb: int = 500,
        default_ttl: int = 3600,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0, "writes": 0, "errors": 0}

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"

    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_path = self._get_cache_path(key)

        with self._lock:
            if not cache_path.exists():
                self._stats["misses"] += 1
                return None

            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                expiry = data.get("_expiry", 0)
                if time.time() > expiry:
                    cache_path.unlink()
                    self._stats["misses"] += 1
                    return None

                self._stats["hits"] += 1
                return data.get("value")
            except Exception:
                self._stats["errors"] += 1
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        cache_path = self._get_cache_path(key)
        ttl = ttl if ttl is not None else self.default_ttl

        data = {
            "value": value,
            "_created": time.time(),
            "_expiry": time.time() + ttl,
        }

        with self._lock:
            try:
                self._cleanup_check()
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, default=str)
                self._stats["writes"] += 1
            except Exception:
                self._stats["errors"] += 1

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        cache_path = self._get_cache_path(key)
        with self._lock:
            if cache_path.exists():
                cache_path.unlink()
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()

    def _cleanup_check(self):
        """检查并清理缓存大小"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        if total_size > self.max_size_bytes:
            files = sorted(
                self.cache_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
            )
            for f in files[: len(files) // 2]:
                f.unlink()

    def cleanup_expired(self):
        """清理过期文件"""
        now = time.time()
        with self._lock:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if now > data.get("_expiry", 0):
                        cache_file.unlink()
                except Exception:
                    pass

    def cached(self, ttl: Optional[int] = None) -> Callable:
        """缓存装饰器"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                key = self._generate_key(func.__name__, *args, **kwargs)
                result = self.get(key)
                if result is not None:
                    return result
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result
            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        return {
            "files": len(list(self.cache_dir.glob("*.json"))),
            "size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_size_bytes // (1024 * 1024),
            **self._stats,
        }


_global_memory_cache: Optional[MemoryCache] = None
_global_disk_cache: Optional[DiskCache] = None


def get_memory_cache() -> MemoryCache:
    """获取内存缓存单例"""
    global _global_memory_cache
    if _global_memory_cache is None:
        _global_memory_cache = MemoryCache(
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "300")),
        )
    return _global_memory_cache


def get_disk_cache() -> DiskCache:
    """获取磁盘缓存单例"""
    global _global_disk_cache
    if _global_disk_cache is None:
        _global_disk_cache = DiskCache(
            cache_dir=os.getenv("CACHE_DISK_DIR", "src/cache"),
            max_size_mb=int(os.getenv("CACHE_DISK_SIZE_MB", "500")),
            default_ttl=int(os.getenv("CACHE_DISK_TTL", "3600")),
        )
    return _global_disk_cache


def cached(
    ttl: int = 300,
    use_disk: bool = False,
    key_prefix: str = "",
) -> Callable:
    """
    多级缓存装饰器

    Args:
        ttl: 过期时间（秒）
        use_disk: 是否使用磁盘缓存
        key_prefix: 缓存键前缀
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            cache = get_disk_cache() if use_disk else get_memory_cache()
            raw_key = json.dumps({"prefix": key_prefix, "args": args, "kwargs": kwargs}, sort_keys=True, default=str)
            key = hashlib.md5(raw_key.encode()).hexdigest()

            result = cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper
    return decorator