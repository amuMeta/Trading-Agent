"""
src/core/validators.py 测试
"""

import pytest
from src.core.validators import (
    validate_stock_code,
    normalize_stock_code,
    validate_session_id,
    validate_query_string,
    validate_pagination_params,
    validate_date_range,
    validate_agent_name,
    validate_rounds,
    validate_file_extension,
)


class TestValidateStockCode:
    """股票代码验证测试"""

    @pytest.mark.parametrize("code,expected", [
        ("600519", True),
        ("SSE:600519", True),
        ("SZSE:000001", True),
        ("NASDAQ:AAPL", True),
        ("HK:00700", True),
        ("", False),
        ("12345", False),
        ("INVALID", False),
    ])
    def test_stock_code_validation(self, code, expected):
        is_valid, _ = validate_stock_code(code)
        assert is_valid == expected


class TestNormalizeStockCode:
    """股票代码规范化测试"""

    @pytest.mark.parametrize("input_code,expected", [
        ("600519", "SSE:600519"),
        ("SSE:600519", "SSE:600519"),
        ("SZSE:000001", "SZSE:000001"),
        ("NASDAQ:AAPL", "NASDAQ:AAPL"),
    ])
    def test_normalize_stock_code(self, input_code, expected):
        assert normalize_stock_code(input_code) == expected


class TestValidateSessionId:
    """会话ID验证测试"""

    def test_valid_session_id(self):
        is_valid, error = validate_session_id("abc123_session")
        assert is_valid is True
        assert error is None

    def test_empty_session_id(self):
        is_valid, error = validate_session_id("")
        assert is_valid is False
        assert "不能为空" in error

    def test_short_session_id(self):
        is_valid, error = validate_session_id("ab")
        assert is_valid is False
        assert "至少4位" in error

    def test_long_session_id(self):
        is_valid, error = validate_session_id("a" * 65)
        assert is_valid is False
        assert "不能超过64位" in error

    def test_invalid_characters(self):
        is_valid, error = validate_session_id("session@123")
        assert is_valid is False
        assert "只能包含" in error


class TestValidateQueryString:
    """查询字符串验证测试"""

    def test_valid_query(self):
        is_valid, error = validate_query_string("分析贵州茅台的财务状况")
        assert is_valid is True

    def test_empty_query(self):
        is_valid, error = validate_query_string("")
        assert is_valid is False

    def test_query_too_long(self):
        is_valid, error = validate_query_string("a" * 1001, max_length=1000)
        assert is_valid is False
        assert "不能超过" in error

    def test_query_too_short(self):
        is_valid, error = validate_query_string("", min_length=5)
        assert is_valid is False


class TestValidatePaginationParams:
    """分页参数验证测试"""

    def test_valid_pagination(self):
        is_valid, error = validate_pagination_params(limit=20, offset=0)
        assert is_valid is True

    def test_invalid_limit_zero(self):
        is_valid, error = validate_pagination_params(limit=0, offset=0)
        assert is_valid is False

    def test_invalid_limit_too_large(self):
        is_valid, error = validate_pagination_params(limit=101, offset=0)
        assert is_valid is False

    def test_negative_offset(self):
        is_valid, error = validate_pagination_params(limit=20, offset=-1)
        assert is_valid is False


class TestValidateAgentName:
    """智能体名称验证测试"""

    @pytest.mark.parametrize("name,expected", [
        ("company_overview_analyst", True),
        ("market_analyst", True),
        ("bull_researcher", True),
        ("risk_manager", True),
        ("invalid_agent", False),
        ("", False),
    ])
    def test_agent_name_validation(self, name, expected):
        is_valid, _ = validate_agent_name(name)
        assert is_valid == expected


class TestValidateRounds:
    """辩论轮次验证测试"""

    def test_valid_rounds(self):
        is_valid, error = validate_rounds(5, min_val=1, max_val=10)
        assert is_valid is True

    def test_rounds_too_low(self):
        is_valid, error = validate_rounds(0, min_val=1, max_val=10)
        assert is_valid is False

    def test_rounds_too_high(self):
        is_valid, error = validate_rounds(15, min_val=1, max_val=10)
        assert is_valid is False


class TestValidateFileExtension:
    """文件扩展名验证测试"""

    def test_valid_pdf(self):
        is_valid, _ = validate_file_extension("document.pdf", {".pdf", ".docx"})
        assert is_valid is True

    def test_invalid_extension(self):
        is_valid, error = validate_file_extension("document.exe", {".pdf", ".docx"})
        assert is_valid is False
        assert "不支持" in error

    def test_empty_filename(self):
        is_valid, error = validate_file_extension("", {".pdf"})
        assert is_valid is False