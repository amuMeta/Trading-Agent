"""
TradingAgents 系统健康检查

提供全面的系统健康检查功能：
- 环境变量检查
- MCP配置检查
- 数据库连接检查
- RAG引擎状态检查
- LLM连接检查
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from src.core.paths import SESSION_DIR


class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        load_dotenv()
        self.checks: List[Dict[str, Any]] = []

    def add_check(self, name: str, status: str, details: Any = None, error: str = None):
        self.checks.append({
            "name": name,
            "status": status,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

    def check_env_file(self) -> bool:
        """检查环境配置文件"""
        try:
            env_path = Path(".env")
            if not env_path.exists():
                self.add_check("env_file", "warning", "配置文件不存在")
                return False

            required_vars = ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"]
            missing = []

            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
                for var in required_vars:
                    if var not in content or f"{var}=" not in content:
                        missing.append(var)

            if missing:
                self.add_check("env_file", "warning", f"缺少环境变量: {', '.join(missing)}")
                return False

            self.add_check("env_file", "ok", "环境变量配置正常")
            return True
        except Exception as e:
            self.add_check("env_file", "error", error=str(e))
            return False

    def check_mcp_config(self) -> bool:
        """检查MCP配置文件"""
        try:
            mcp_path = Path("mcp_config.json")
            if not mcp_path.exists():
                self.add_check("mcp_config", "warning", "MCP配置文件不存在")
                return False

            import json
            with open(mcp_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            servers = config.get("mcpServers", {})
            if not servers:
                self.add_check("mcp_config", "warning", "MCP服务器配置为空")
                return False

            self.add_check("mcp_config", "ok", f"MCP服务器数量: {len(servers)}")
            return True
        except Exception as e:
            self.add_check("mcp_config", "error", error=str(e))
            return False

    def check_database(self) -> bool:
        """检查数据库连接"""
        try:
            if not SESSION_DIR.exists():
                self.add_check("database", "warning", "dump目录不存在")
                return False

            session_files = list(SESSION_DIR.glob("session_*.json"))
            self.add_check("database", "ok", f"会话文件数量: {len(session_files)}")
            return True
        except Exception as e:
            self.add_check("database", "error", error=str(e))
            return False

    def check_rag_engine(self) -> bool:
        """检查RAG引擎状态"""
        try:
            RAG_AVAILABLE = False
            try:
                from src.rag.engine import get_rag_engine
                engine = get_rag_engine()
                if engine is not None:
                    RAG_AVAILABLE = True
            except ImportError:
                pass
            except Exception:
                pass

            if RAG_AVAILABLE:
                self.add_check("rag_engine", "ok", "RAG引擎已初始化")
                return True
            else:
                self.add_check("rag_engine", "warning", "RAG引擎未初始化或不可用")
                return False
        except Exception as e:
            self.add_check("rag_engine", "error", error=str(e))
            return False

    def check_llm_connection(self) -> bool:
        """检查LLM连接"""
        try:
            api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.add_check("llm_connection", "warning", "未配置API密钥")
                return False

            api_key_display = api_key[:8] + "..." if len(api_key) > 8 else "***"
            self.add_check("llm_connection", "ok", f"API密钥: {api_key_display}")
            return True
        except Exception as e:
            self.add_check("llm_connection", "error", error=str(e))
            return False

    def check_dump_directory(self) -> bool:
        """检查dump目录"""
        try:
            if not SESSION_DIR.exists():
                self.add_check("dump_directory", "warning", "dump目录不存在")
                return False

            session_files = list(SESSION_DIR.glob("session_*.json"))
            corrupted = list(SESSION_DIR.glob("session_*.corrupted")) + \
                       list(SESSION_DIR.glob("session_*.bad")) + \
                       list(SESSION_DIR.glob("session_*.broken"))

            self.add_check(
                "dump_directory",
                "ok" if not corrupted else "warning",
                f"会话文件: {len(session_files)}, 损坏文件: {len(corrupted)}"
            )
            return True
        except Exception as e:
            self.add_check("dump_directory", "error", error=str(e))
            return False

    def check_dependencies(self) -> bool:
        """检查关键依赖"""
        dependencies = {
            "fastapi": "fastapi",
            "uvicorn": "uvicorn",
            "langchain": "langchain",
            "langchain_openai": "langchain_openai",
            "chromadb": "chromadb",
            "peewee": "peewee",
        }

        missing = []
        available = []

        for name, import_name in dependencies.items():
            try:
                __import__(import_name)
                available.append(name)
            except ImportError:
                missing.append(name)

        if missing:
            self.add_check("dependencies", "warning", f"缺少依赖: {', '.join(missing)}")
            return False

        self.add_check("dependencies", "ok", f"已安装: {', '.join(available)}")
        return True

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有检查"""
        self.checks = []

        self.check_env_file()
        self.check_mcp_config()
        self.check_database()
        self.check_rag_engine()
        self.check_llm_connection()
        self.check_dump_directory()
        self.check_dependencies()

        total = len(self.checks)
        ok_count = sum(1 for c in self.checks if c["status"] == "ok")
        warning_count = sum(1 for c in self.checks if c["status"] == "warning")
        error_count = sum(1 for c in self.checks if c["status"] == "error")

        overall_status = "healthy"
        if error_count > 0:
            overall_status = "unhealthy"
        elif warning_count > 0:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "ok": ok_count,
                "warnings": warning_count,
                "errors": error_count,
            },
            "checks": self.checks,
        }

    def get_readiness(self) -> Dict[str, Any]:
        """
        获取就绪状态（用于Kubernetes readiness probe）

        返回系统是否可以接受请求
        """
        critical_checks = ["env_file", "llm_connection"]

        critical_status = {}
        for check_name in critical_checks:
            found = False
            for check in self.checks:
                if check["name"] == check_name:
                    critical_status[check_name] = check["status"]
                    found = True
                    break
            if not found:
                critical_status[check_name] = "unknown"

        is_ready = all(
            status in ("ok", "warning")
            for status in critical_status.values()
        )

        return {
            "ready": is_ready,
            "critical_checks": critical_status,
            "timestamp": datetime.now().isoformat(),
        }

    def get_liveness(self) -> Dict[str, Any]:
        """
        获取存活状态（用于Kubernetes liveness probe）

        返回系统是否存活
        """
        return {
            "alive": True,
            "timestamp": datetime.now().isoformat(),
        }


_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """获取健康检查器单例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


async def system_health_check() -> Dict[str, Any]:
    """异步获取系统健康状态"""
    checker = get_health_checker()
    return checker.run_all_checks()


async def system_readiness_check() -> Dict[str, Any]:
    """异步获取系统就绪状态"""
    checker = get_health_checker()
    checker.run_all_checks()
    return checker.get_readiness()


async def system_liveness_check() -> Dict[str, Any]:
    """异步获取系统存活状态"""
    checker = get_health_checker()
    return checker.get_liveness()