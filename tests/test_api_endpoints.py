"""
API端点集成测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHealthEndpoints:
    """健康检查端点测试"""

    @pytest.fixture
    def client(self):
        with patch("src.workflow_orchestrator.WorkflowOrchestrator"):
            from src.api_server import app
            return TestClient(app)

    def test_health_endpoint(self, client):
        response = client.get("/api/system/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "summary" in data
        assert "checks" in data

    def test_liveness_endpoint(self, client):
        response = client.get("/api/system/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True

    def test_readiness_endpoint(self, client):
        response = client.get("/api/system/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "critical_checks" in data

    def test_info_endpoint(self, client):
        response = client.get("/api/system/info")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "checks" in data


class TestCacheEndpoints:
    """缓存管理端点测试"""

    @pytest.fixture
    def client(self):
        with patch("src.workflow_orchestrator.WorkflowOrchestrator"):
            from src.api_server import app
            return TestClient(app)

    def test_mcp_cache_stats(self, client):
        response = client.get("/api/cache/mcp/stats")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data or "hits" in data or "size" in data

    def test_mcp_cache_clear(self, client):
        response = client.post("/api/cache/mcp/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_memory_cache_stats(self, client):
        response = client.get("/api/cache/memory/stats")

        assert response.status_code == 200

    def test_memory_cache_clear(self, client):
        response = client.post("/api/cache/memory/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_analysis_cache_stats(self, client):
        response = client.get("/api/cache/analysis/stats")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data or "hits" in data

    def test_analysis_cache_list(self, client):
        response = client.get("/api/cache/analysis/list")

        assert response.status_code == 200
        data = response.json()
        assert "cached_analyses" in data


class TestAnalysisEndpoints:
    """分析端点测试（有限 mocking）"""

    @pytest.fixture
    def client(self):
        with patch("src.workflow_orchestrator.WorkflowOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.initialize.return_value = None
            mock_instance.close.return_value = None
            mock_instance.get_workflow_info.return_value = {"agents": []}
            mock_orch.return_value = mock_instance

            from src.api_server import app
            return TestClient(app)

    def test_agents_config(self, client):
        response = client.get("/api/agents/config")

        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert "all_agents" in data

    def test_tasks_endpoint(self, client):
        response = client.get("/api/analysis/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "all_sessions" in data


class TestValidationEndpoints:
    """输入验证端点测试"""

    @pytest.fixture
    def client(self):
        with patch("src.workflow_orchestrator.WorkflowOrchestrator"):
            from src.api_server import app
            return TestClient(app)

    def test_start_analysis_validation(self, client):
        response = client.post("/api/analysis/start", json={
            "query": "",
            "investment_rounds": 1,
            "risk_rounds": 1
        })

        assert response.status_code == 422

    def test_start_analysis_invalid_rounds(self, client):
        response = client.post("/api/analysis/start", json={
            "query": "分析贵州茅台",
            "investment_rounds": 100,
            "risk_rounds": 1
        })

        assert response.status_code == 422

    def test_progress_nonexistent_task(self, client):
        response = client.get("/api/analysis/nonexistent_id/progress")

        assert response.status_code == 404

    def test_cancel_nonexistent_task(self, client):
        response = client.post("/api/analysis/nonexistent_id/cancel")

        assert response.status_code == 404