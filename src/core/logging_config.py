"""
TradingAgents 日志格式化和配置

提供统一的日志格式和配置：
- 结构化日志输出（JSON格式）
- 可配置的日志级别
- 请求追踪ID
- 日志分类（API、智能体、MCP等）
"""

import json
import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON日志格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "thread": record.threadName,
            "process": record.process,
        }

        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id

        if hasattr(record, "agent_name") and record.agent_name:
            log_data["agent_name"] = record.agent_name

        if hasattr(record, "session_id") and record.session_id:
            log_data["session_id"] = record.session_id

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        if self.include_extra:
            extra_fields = {
                k: v
                for k, v in record.__dict__.items()
                if k
                not in {
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "stack_info",
                    "exc_info",
                    "exc_text",
                    "thread",
                    "threadName",
                    "message",
                    "request_id",
                    "agent_name",
                    "session_id",
                }
            }
            if extra_fields:
                log_data["extra"] = extra_fields

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, fmt: Optional[str] = None):
        super().__init__(fmt)

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class StructuredLogger:
    """
    结构化日志记录器

    提供类型安全的日志记录方法，支持：
    - API请求/响应日志
    - 智能体执行日志
    - MCP工具调用日志
    - 工作流状态日志
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}

    def set_context(self, **kwargs):
        """设置日志上下文"""
        self._context.update(kwargs)

    def clear_context(self):
        """清除日志上下文"""
        self._context = {}

    def _log(
        self,
        level: int,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        log_record = {"message": msg}
        log_record.update(self._context)
        if extra:
            log_record.update(extra)

        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(unknown)",
            0,
            msg,
            (),
            exc_info,
        )

        for key, value in log_record.items():
            setattr(record, key, value)

        self.logger.handle(record)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, kwargs)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, kwargs)

    def error(self, msg: str, exc_info: bool = True, **kwargs):
        self._log(logging.ERROR, msg, kwargs, exc_info=exc_info)

    def critical(self, msg: str, exc_info: bool = True, **kwargs):
        self._log(logging.CRITICAL, msg, kwargs, exc_info=exc_info)

    def api_request(self, method: str, path: str, **kwargs):
        """记录API请求"""
        self.info(f"API Request: {method} {path}", api_request=True, method=method, path=path, **kwargs)

    def api_response(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        """记录API响应"""
        self.info(
            f"API Response: {method} {path} -> {status_code}",
            api_response=True,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs,
        )

    def agent_start(self, agent_name: str, action: str, **kwargs):
        """记录智能体开始执行"""
        self.info(f"Agent Start: {agent_name} - {action}", agent_start=True, agent_name=agent_name, action=action, **kwargs)

    def agent_complete(self, agent_name: str, action: str, duration_ms: float, **kwargs):
        """记录智能体完成"""
        self.info(
            f"Agent Complete: {agent_name} - {action} ({duration_ms:.2f}ms)",
            agent_complete=True,
            agent_name=agent_name,
            action=action,
            duration_ms=duration_ms,
            **kwargs,
        )

    def agent_error(self, agent_name: str, action: str, error: str, **kwargs):
        """记录智能体错误"""
        self.error(
            f"Agent Error: {agent_name} - {action} - {error}",
            agent_name=agent_name,
            action=action,
            error=error,
            **kwargs,
        )

    def mcp_call(self, tool_name: str, args: Dict, **kwargs):
        """记录MCP工具调用"""
        self.debug(f"MCP Call: {tool_name}", mcp_call=True, tool_name=tool_name, args=args, **kwargs)

    def mcp_result(self, tool_name: str, success: bool, duration_ms: float, **kwargs):
        """记录MCP工具结果"""
        level = logging.DEBUG if success else logging.WARNING
        self._log(
            level,
            f"MCP Result: {tool_name} - {'OK' if success else 'FAILED'} ({duration_ms:.2f}ms)",
            {"mcp_result": True, "tool_name": tool_name, "success": success, "duration_ms": duration_ms, **kwargs},
        )

    def workflow_start(self, session_id: str, query: str, **kwargs):
        """记录工作流开始"""
        self.info(f"Workflow Start: {session_id}", workflow_start=True, session_id=session_id, query=query, **kwargs)

    def workflow_complete(self, session_id: str, duration_ms: float, agents_count: int, **kwargs):
        """记录工作流完成"""
        self.info(
            f"Workflow Complete: {session_id} - {agents_count} agents ({duration_ms:.2f}ms)",
            workflow_complete=True,
            session_id=session_id,
            duration_ms=duration_ms,
            agents_count=agents_count,
            **kwargs,
        )

    def workflow_error(self, session_id: str, error: str, **kwargs):
        """记录工作流错误"""
        self.error(
            f"Workflow Error: {session_id} - {error}",
            workflow_error=True,
            session_id=session_id,
            error=error,
            **kwargs,
        )


_api_logger: Optional[StructuredLogger] = None
_agent_logger: Optional[StructuredLogger] = None
_mcp_logger: Optional[StructuredLogger] = None
_workflow_logger: Optional[StructuredLogger] = None


def get_api_logger() -> StructuredLogger:
    """获取API日志记录器"""
    global _api_logger
    if _api_logger is None:
        _api_logger = StructuredLogger("tradingagents.api")
    return _api_logger


def get_agent_logger() -> StructuredLogger:
    """获取智能体日志记录器"""
    global _agent_logger
    if _agent_logger is None:
        _agent_logger = StructuredLogger("tradingagents.agent")
    return _agent_logger


def get_mcp_logger() -> StructuredLogger:
    """获取MCP日志记录器"""
    global _mcp_logger
    if _mcp_logger is None:
        _mcp_logger = StructuredLogger("tradingagents.mcp")
    return _mcp_logger


def get_workflow_logger() -> StructuredLogger:
    """获取工作流日志记录器"""
    global _workflow_logger
    if _workflow_logger is None:
        _workflow_logger = StructuredLogger("tradingagents.workflow")
    return _workflow_logger


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
):
    """
    配置日志系统

    Args:
        level: 日志级别
        json_output: 是否输出JSON格式
        log_file: 日志文件路径（可选）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if json_output:
        console_handler.setFormatter(JSONFormatter())
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        console_handler.setFormatter(ColoredFormatter(fmt))

    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)