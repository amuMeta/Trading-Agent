"""
src/mcp/http_client.py 测试
"""

import pytest
from unittest.mock import patch, MagicMock
from src.mcp.http_client import (
    StockMCPHTTPClient,
    MCPCache,
    normalize_stock_code,
    with_retry,
)


class TestNormalizeStockCode:
    """股票代码规范化测试"""

    @pytest.mark.parametrize("input_code,expected", [
        ("600519", "SSE:600519"),
        ("SSE:600519", "SSE:600519"),
        ("SZSE:000001", "SZSE:000001"),
        ("", ""),
        ("AAPL", "AAPL"),
    ])
    def test_normalize_stock_code(self, input_code, expected):
        assert normalize_stock_code(input_code) == expected


class TestMCPCache:
    """MCP缓存测试"""

    def test_make_key_consistency(self):
        cache = MCPCache()
        key1 = cache._make_key("get_kline_data", {"symbol": "600519", "period": "30d"})
        key2 = cache._make_key("get_kline_data", {"symbol": "600519", "period": "30d"})

        assert key1 == key2

    def test_make_key_different_params(self):
        cache = MCPCache()
        key1 = cache._make_key("get_kline_data", {"symbol": "600519", "period": "30d"})
        key2 = cache._make_key("get_kline_data", {"symbol": "600519", "period": "90d"})

        assert key1 != key2

    def test_get_ttl_for_tool_short(self):
        cache = MCPCache()
        assert cache._get_ttl_for_tool("get_real_time_price") == 60
        assert cache._get_ttl_for_tool("get_kline_data") == 60

    def test_get_ttl_for_tool_medium(self):
        cache = MCPCache()
        assert cache._get_ttl_for_tool("get_technical_indicators") == 300
        assert cache._get_ttl_for_tool("get_money_flow") == 300

    def test_get_ttl_for_tool_long(self):
        cache = MCPCache()
        assert cache._get_ttl_for_tool("get_financial_reports") == 1800
        assert cache._get_ttl_for_tool("get_valuation_metrics") == 1800
        assert cache._get_ttl_for_tool("get_asset_info") == 1800

    def test_get_ttl_for_tool_default(self):
        cache = MCPCache()
        assert cache._get_ttl_for_tool("unknown_tool") == 300


class TestStockMCPHTTPClient:
    """HTTP客户端测试"""

    def test_init_with_default_url(self):
        client = StockMCPHTTPClient()
        assert client.BASE_URL == "http://127.0.0.1:9898/api/v1"

    def test_init_with_custom_url(self):
        client = StockMCPHTTPClient(base_url="http://custom:8080/api")
        assert client.BASE_URL == "http://custom:8080/api"

    def test_init_cache_disabled_by_default_in_test(self):
        import os
        original = os.environ.get("MCP_CACHE_ENABLED")
        os.environ["MCP_CACHE_ENABLED"] = "false"
        try:
            client = StockMCPHTTPClient(use_cache=True)
            assert client._use_cache is False
        finally:
            if original is not None:
                os.environ["MCP_CACHE_ENABLED"] = original


class TestWithRetryDecorator:
    """重试装饰器测试"""

    def test_successful_call_no_retry(self):
        @with_retry(max_attempts=3)
        def success_func():
            return {"data": "success"}

        result = success_func()
        assert result == {"data": "success"}

    def test_call_with_error_no_retry_on_value_error(self):
        call_count = 0

        @with_retry(max_attempts=3)
        def error_func():
            nonlocal call_count
            call_count += 1
            return {"error": "Not a network error"}

        result = error_func()
        assert call_count == 1
        assert "error" in result

    def test_call_with_network_error_retries(self):
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.1)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Connection refused")
            return {"data": "success"}

        result = flaky_func()
        assert call_count == 3
        assert result == {"data": "success"}