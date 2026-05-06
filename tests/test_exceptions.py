"""
src/core/exceptions.py 测试
"""

import pytest
from src.core.exceptions import (
    TradingAgentsException,
    AgentException,
    MCPException,
    WorkflowException,
    DatabaseException,
    APIException,
    APIRateLimitError,
    APITaskNotFoundError,
    APIValidationError,
)


class TestTradingAgentsException:
    """TradingAgents异常基类测试"""

    def test_exception_attributes(self):
        exc = TradingAgentsException(
            message="Test error",
            error_code="E_TEST",
            details={"key": "value"},
        )
        assert exc.message == "Test error"
        assert exc.error_code == "E_TEST"
        assert exc.details == {"key": "value"}
        assert exc.status_code == 500

    def test_to_dict(self):
        exc = TradingAgentsException(message="Error", error_code="E_TEST")
        result = exc.to_dict()

        assert "error" in result
        assert result["error"]["code"] == "E_TEST"
        assert result["error"]["message"] == "Error"
        assert "timestamp" in result["error"]

    def test_exception_with_cause(self):
        cause = ValueError("Original error")
        exc = TradingAgentsException(message="Wrapper error", cause=cause)

        result = exc.to_dict()
        assert "cause" in result["error"]
        assert "ValueError" in result["error"]["cause"]


class TestAPIException:
    """API异常测试"""

    def test_api_rate_limit_error(self):
        exc = APIRateLimitError(
            message="Rate limit exceeded",
            details={"limit": 60, "remaining": 0}
        )
        assert exc.status_code == 429
        assert exc.error_code == "E_API_RATE_LIMIT"

    def test_api_task_not_found_error(self):
        exc = APITaskNotFoundError(message="Task not found", details={"task_id": "123"})
        assert exc.status_code == 404
        assert exc.error_code == "E_API_TASK_NOT_FOUND"

    def test_api_validation_error(self):
        exc = APIValidationError(
            message="Validation failed",
            details={"field": "query", "error": "too short"}
        )
        assert exc.status_code == 400
        assert exc.error_code == "E_API_VALIDATION"


class TestExceptionHierarchy:
    """异常层次结构测试"""

    def test_agent_exception_inherits(self):
        exc = AgentException()
        assert isinstance(exc, TradingAgentsException)

    def test_mcp_exception_inherits(self):
        exc = MCPException()
        assert isinstance(exc, TradingAgentsException)

    def test_workflow_exception_inherits(self):
        exc = WorkflowException()
        assert isinstance(exc, TradingAgentsException)

    def test_database_exception_inherits(self):
        exc = DatabaseException()
        assert isinstance(exc, TradingAgentsException)

    def test_api_exception_inherits(self):
        exc = APIException()
        assert isinstance(exc, TradingAgentsException)