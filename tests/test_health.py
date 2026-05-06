"""
src/core/health.py 测试
"""

import pytest
from src.core.health import HealthChecker, get_health_checker


class TestHealthChecker:
    """健康检查器测试"""

    def test_add_check(self):
        checker = HealthChecker()
        checker.add_check("test_check", "ok", "Test passed")

        assert len(checker.checks) == 1
        assert checker.checks[0]["name"] == "test_check"
        assert checker.checks[0]["status"] == "ok"

    def test_run_all_checks_returns_status(self):
        checker = HealthChecker()
        result = checker.run_all_checks()

        assert "status" in result
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert "summary" in result
        assert "checks" in result
        assert len(result["checks"]) > 0

    def test_summary_counts(self):
        checker = HealthChecker()
        result = checker.run_all_checks()

        summary = result["summary"]
        assert "total" in summary
        assert "ok" in summary
        assert "warnings" in summary
        assert "errors" in summary
        assert summary["total"] == len(result["checks"])

    def test_liveness_returns_alive(self):
        checker = HealthChecker()
        result = checker.get_liveness()

        assert result["alive"] is True
        assert "timestamp" in result

    def test_readiness_requires_critical_checks(self):
        checker = HealthChecker()
        checker.run_all_checks()
        result = checker.get_readiness()

        assert "ready" in result
        assert "critical_checks" in result
        assert isinstance(result["critical_checks"], dict)


class TestHealthCheckerChecks:
    """健康检查项测试"""

    def test_check_env_file(self):
        checker = HealthChecker()
        result = checker.check_env_file()

        assert isinstance(result, bool)

    def test_check_mcp_config(self):
        checker = HealthChecker()
        result = checker.check_mcp_config()

        assert isinstance(result, bool)

    def test_check_database(self):
        checker = HealthChecker()
        result = checker.check_database()

        assert isinstance(result, bool)

    def test_check_dependencies(self):
        checker = HealthChecker()
        result = checker.check_dependencies()

        assert isinstance(result, bool)

    def test_check_dump_directory(self):
        checker = HealthChecker()
        result = checker.check_dump_directory()

        assert isinstance(result, bool)