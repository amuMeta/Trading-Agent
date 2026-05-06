"""
TradingAgents 分析结果缓存

缓存已完成的投资分析结果，支持：
- 基于股票代码+查询的缓存
- TTL过期机制
- 缓存统计
- 分析质量评分
"""

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class AnalysisResultCache:
    """
    分析结果缓存

    缓存结构：
    - key: hash(stock_code + query_hash)
    - value: {
        "session_id": str,
        "stock_code": str,
        "user_query": str,
        "result": {...分析结果...},
        "quality_score": float,
        "created_at": timestamp,
        "expires_at": timestamp,
        "access_count": int,
        "last_accessed": timestamp,
    }
    """

    def __init__(
        self,
        cache_dir: str = "src/cache/analysis",
        max_entries: int = 100,
        default_ttl: int = 3600,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._memory_index: OrderedDict[str, Dict] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired": 0,
        }
        self._load_index()

    def _load_index(self):
        """从磁盘加载缓存索引"""
        index_file = self.cache_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._memory_index = OrderedDict(
                        {k: v for k, v in data.items() if time.time() < v.get("expires_at", 0)}
                    )
            except Exception:
                pass

    def _save_index(self):
        """保存缓存索引到磁盘"""
        index_file = self.cache_dir / "index.json"
        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(dict(self._memory_index), f, ensure_ascii=False)
        except Exception:
            pass

    def _generate_key(self, stock_code: str, query: str) -> str:
        """生成缓存键"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        key_data = f"{stock_code}:{query_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"

    def get(
        self, stock_code: str, query: str, min_quality_score: float = 0.0
    ) -> Optional[Dict]:
        """
        获取缓存的分析结果

        Args:
            stock_code: 股票代码
            query: 查询字符串
            min_quality_score: 最低质量评分要求

        Returns:
            缓存的分析结果，如果不存在或已过期则返回None
        """
        key = self._generate_key(stock_code, query)

        with self._lock:
            if key not in self._memory_index:
                self._stats["misses"] += 1
                return None

            entry = self._memory_index[key]

            if time.time() > entry.get("expires_at", 0):
                del self._memory_index[key]
                self._save_index()
                self._stats["expired"] += 1
                self._stats["misses"] += 1
                return None

            if entry.get("quality_score", 0) < min_quality_score:
                self._stats["misses"] += 1
                return None

            entry["access_count"] = entry.get("access_count", 0) + 1
            entry["last_accessed"] = time.time()
            self._memory_index.move_to_end(key)

            self._stats["hits"] += 1

            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass

            return entry.get("result")

    def set(
        self,
        stock_code: str,
        query: str,
        result: Dict,
        quality_score: float = 0.0,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        缓存分析结果

        Args:
            stock_code: 股票代码
            query: 查询字符串
            result: 分析结果
            quality_score: 质量评分
            ttl: 过期时间（秒）

        Returns:
            是否成功缓存
        """
        key = self._generate_key(stock_code, query)
        ttl = ttl if ttl is not None else self.default_ttl

        with self._lock:
            if len(self._memory_index) >= self.max_entries:
                self._evict_lru()

            cache_path = self._get_cache_path(key)

            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, default=str)

                entry = {
                    "key": key,
                    "stock_code": stock_code,
                    "user_query": query[:200] if len(query) > 200 else query,
                    "result": result,
                    "quality_score": quality_score,
                    "created_at": time.time(),
                    "expires_at": time.time() + ttl,
                    "access_count": 0,
                    "last_accessed": time.time(),
                }

                self._memory_index[key] = entry
                self._save_index()
                return True
            except Exception:
                return False

    def _evict_lru(self):
        """驱逐最久未使用的条目"""
        if not self._memory_index:
            return

        oldest_key = next(iter(self._memory_index))
        entry = self._memory_index[oldest_key]

        cache_path = self._get_cache_path(oldest_key)
        if cache_path.exists():
            cache_path.unlink()

        del self._memory_index[oldest_key]
        self._stats["evictions"] += 1

    def invalidate(self, stock_code: str, query: str) -> bool:
        """使缓存失效"""
        key = self._generate_key(stock_code, query)

        with self._lock:
            if key in self._memory_index:
                cache_path = self._get_cache_path(key)
                if cache_path.exists():
                    cache_path.unlink()
                del self._memory_index[key]
                self._save_index()
                return True
            return False

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            for key in list(self._memory_index.keys()):
                cache_path = self._get_cache_path(key)
                if cache_path.exists():
                    cache_path.unlink()
            self._memory_index.clear()
            self._save_index()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0

            return {
                "entries": len(self._memory_index),
                "max_entries": self.max_entries,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate * 100, 2),
                "evictions": self._stats["evictions"],
                "expired": self._stats["expired"],
            }

    def list_cached_analyses(
        self,
        stock_code: Optional[str] = None,
        min_quality_score: float = 0.0,
        limit: int = 20,
    ) -> List[Dict]:
        """列出缓存的分析"""
        results = []

        with self._lock:
            for key, entry in reversed(list(self._memory_index.items())):
                if time.time() > entry.get("expires_at", 0):
                    continue

                if stock_code and entry.get("stock_code") != stock_code:
                    continue

                if entry.get("quality_score", 0) < min_quality_score:
                    continue

                results.append({
                    "stock_code": entry.get("stock_code"),
                    "user_query": entry.get("user_query"),
                    "quality_score": entry.get("quality_score"),
                    "created_at": entry.get("created_at"),
                    "expires_at": entry.get("expires_at"),
                    "access_count": entry.get("access_count"),
                })

                if len(results) >= limit:
                    break

        return results


_global_analysis_cache: Optional[AnalysisResultCache] = None


def get_analysis_cache() -> AnalysisResultCache:
    """获取分析缓存单例"""
    global _global_analysis_cache
    if _global_analysis_cache is None:
        _global_analysis_cache = AnalysisResultCache(
            cache_dir=os.getenv("ANALYSIS_CACHE_DIR", "src/cache/analysis"),
            max_entries=int(os.getenv("ANALYSIS_CACHE_MAX_ENTRIES", "100")),
            default_ttl=int(os.getenv("ANALYSIS_CACHE_TTL", "3600")),
        )
    return _global_analysis_cache