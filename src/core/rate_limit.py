"""
TradingAgents API限流机制

提供基于时间窗口的API限流功能：
- 内存存储（单机部署）
- 可配置的限流规则
- 指数退避重试支持
"""

import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .exceptions import APIRateLimitError


class RateLimiter:
    """滑动窗口限流器"""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        self._minute_window: Dict[str, list] = defaultdict(list)
        self._hour_window: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup_old_requests(self, key: str, now: float):
        """清理过期的请求记录"""
        minute_ago = now - 60
        hour_ago = now - 3600

        self._minute_window[key] = [
            t for t in self._minute_window[key] if t > minute_ago
        ]
        self._hour_window[key] = [
            t for t in self._hour_window[key] if t > hour_ago
        ]

    def check_rate_limit(
        self, key: str, now: Optional[float] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        检查限流状态

        Args:
            key: 限流标识（通常是客户端IP或用户ID）
            now: 当前时间戳

        Returns:
            (是否允许, 限流信息)
        """
        if now is None:
            now = time.time()

        with self._lock:
            self._cleanup_old_requests(key, now)

            minute_count = len(self._minute_window[key])
            hour_count = len(self._hour_window[key])

            minute_allowed = minute_count < self.requests_per_minute
            hour_allowed = hour_count < self.requests_per_hour
            burst_allowed = minute_count < self.burst_size

            if not minute_allowed:
                retry_after = int(self._minute_window[key][0] + 60 - now) if self._minute_window[key] else 60
                return False, {
                    "limit": self.requests_per_minute,
                    "remaining": 0,
                    "reset": int(now + retry_after),
                    "reason": "minute_limit",
                }

            if not hour_allowed:
                retry_after = int(self._hour_window[key][0] + 3600 - now) if self._hour_window[key] else 3600
                return False, {
                    "limit": self.requests_per_hour,
                    "remaining": 0,
                    "reset": int(now + retry_after),
                    "reason": "hour_limit",
                }

            self._minute_window[key].append(now)
            self._hour_window[key].append(now)

            return True, {
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute - minute_count - 1,
                "reset": int(now + 60),
                "reason": None,
            }

    def get_status(self, key: str) -> Dict[str, any]:
        """获取限流状态（不消耗配额）"""
        now = time.time()

        with self._lock:
            self._cleanup_old_requests(key, now)

            minute_count = len(self._minute_window[key])
            hour_count = len(self._hour_window[key])

            return {
                "minute": {
                    "used": minute_count,
                    "limit": self.requests_per_minute,
                    "remaining": max(0, self.requests_per_minute - minute_count),
                },
                "hour": {
                    "used": hour_count,
                    "limit": self.requests_per_hour,
                    "remaining": max(0, self.requests_per_hour - hour_count),
                },
            }


class PerEndpointRateLimiter:
    """针对特定端点的限流器"""

    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()

    def get_limiter(self, endpoint: str, method: str) -> RateLimiter:
        """获取或创建端点限流器"""
        key = f"{method}:{endpoint}"

        with self._lock:
            if key not in self._limiters:
                if "chat" in endpoint or "rag" in endpoint:
                    self._limiters[key] = RateLimiter(
                        requests_per_minute=30,
                        requests_per_hour=200,
                        burst_size=5,
                    )
                elif "analysis" in endpoint and "start" in endpoint:
                    self._limiters[key] = RateLimiter(
                        requests_per_minute=5,
                        requests_per_hour=30,
                        burst_size=2,
                    )
                elif "export" in endpoint:
                    self._limiters[key] = RateLimiter(
                        requests_per_minute=10,
                        requests_per_hour=50,
                        burst_size=3,
                    )
                elif "health" in endpoint or "info" in endpoint:
                    self._limiters[key] = RateLimiter(
                        requests_per_minute=120,
                        requests_per_hour=1000,
                        burst_size=20,
                    )
                else:
                    self._limiters[key] = RateLimiter(
                        requests_per_minute=60,
                        requests_per_hour=500,
                        burst_size=10,
                    )

            return self._limiters[key]

    def check_limit(
        self, endpoint: str, method: str, client_key: str
    ) -> Tuple[bool, Dict]:
        """检查限流"""
        limiter = self.get_limiter(endpoint, method)
        return limiter.check_rate_limit(client_key)


_global_limiter = PerEndpointRateLimiter()


def get_client_identifier(request: Request) -> str:
    """获取客户端标识符"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        method = request.method

        skip_paths = {"/", "/docs", "/openapi.json", "/redoc"}
        if path in skip_paths or path.startswith("/api/system/health/live"):
            return await call_next(request)

        client_id = get_client_identifier(request)
        allowed, limit_info = _global_limiter.check_limit(path, method, client_id)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "E_API_RATE_LIMIT",
                        "message": f"请求过于频繁，请于{limit_info['reset']}秒后重试",
                        "details": {
                            "limit": limit_info["limit"],
                            "remaining": 0,
                            "reset": limit_info["reset"],
                            "reason": limit_info["reason"],
                        },
                        "timestamp": datetime.now().isoformat(),
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(limit_info["reset"]),
                    "Retry-After": str(limit_info["reset"]),
                },
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])

        return response


async def rate_limit_check(
    request: Request,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
) -> None:
    """
    手动限流检查（用于特定端点）

    Raises:
        APIRateLimitError: 当超过限流时
    """
    if endpoint is None:
        endpoint = request.url.path
    if method is None:
        method = request.method

    client_id = get_client_identifier(request)
    allowed, limit_info = _global_limiter.check_limit(endpoint, method, client_id)

    if not allowed:
        raise APIRateLimitError(
            message="请求频率超限，请稍后重试",
            details={
                "limit": limit_info["limit"],
                "remaining": 0,
                "reset": limit_info["reset"],
                "reason": limit_info["reason"],
            },
        )