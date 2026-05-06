"""
src/core/rate_limit.py 测试
"""

import pytest
import time
from src.core.rate_limit import RateLimiter, PerEndpointRateLimiter


class TestRateLimiter:
    """限流器测试"""

    def test_first_request_allowed(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)

        allowed, info = limiter.check_rate_limit("client1")
        assert allowed is True
        assert info["remaining"] == 9

    def test_rate_limit_enforced(self):
        limiter = RateLimiter(requests_per_minute=3, requests_per_hour=100, burst_size=3)

        for i in range(3):
            allowed, _ = limiter.check_rate_limit("client1")
            assert allowed is True

        allowed, info = limiter.check_rate_limit("client1")
        assert allowed is False
        assert info["remaining"] == 0

    def test_different_clients_independent(self):
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=100)

        limiter.check_rate_limit("client1")
        limiter.check_rate_limit("client1")

        allowed1, _ = limiter.check_rate_limit("client1")
        allowed2, _ = limiter.check_rate_limit("client2")

        assert allowed1 is False
        assert allowed2 is True

    def test_get_status(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)

        limiter.check_rate_limit("client1")
        limiter.check_rate_limit("client1")

        status = limiter.get_status("client1")
        assert status["minute"]["used"] == 2
        assert status["minute"]["remaining"] == 8

    def test_status_does_not_consume(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)

        limiter.check_rate_limit("client1")
        status1 = limiter.get_status("client1")
        status2 = limiter.get_status("client1")

        assert status1["minute"]["used"] == status2["minute"]["used"]


class TestPerEndpointRateLimiter:
    """端点限流器测试"""

    def test_get_limiter_for_chat_endpoint(self):
        limiter = PerEndpointRateLimiter()

        chat_limiter = limiter.get_limiter("/api/chat/rag", "POST")
        assert chat_limiter.requests_per_minute == 30

    def test_get_limiter_for_analysis_endpoint(self):
        limiter = PerEndpointRateLimiter()

        analysis_limiter = limiter.get_limiter("/api/analysis/start", "POST")
        assert analysis_limiter.requests_per_minute == 5

    def test_get_limiter_for_health_endpoint(self):
        limiter = PerEndpointRateLimiter()

        health_limiter = limiter.get_limiter("/api/system/health", "GET")
        assert health_limiter.requests_per_minute == 120

    def test_same_endpoint_same_limiter(self):
        limiter = PerEndpointRateLimiter()

        limiter1 = limiter.get_limiter("/api/chat/rag", "POST")
        limiter2 = limiter.get_limiter("/api/chat/rag", "POST")

        assert limiter1 is limiter2

    def test_different_endpoints_different_limiters(self):
        limiter = PerEndpointRateLimiter()

        chat_limiter = limiter.get_limiter("/api/chat/rag", "POST")
        analysis_limiter = limiter.get_limiter("/api/analysis/start", "POST")

        assert chat_limiter is not analysis_limiter

    def test_check_limit(self):
        limiter = PerEndpointRateLimiter()

        allowed, info = limiter.check_limit("/api/chat/rag", "POST", "client1")
        assert allowed is True
        assert info["remaining"] >= 0