"""
TradingAgents 错误码和响应格式定义

提供统一的错误响应构建函数，支持：
- 错误码注册表
- 标准错误响应格式
- FastAPI异常处理器
"""

from typing import Any, Dict, Optional, Union
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import TradingAgentsException


ERROR_CODES = {
    "E_INTERNAL": {"status": 500, "message": "内部错误"},
    "E_AGENT": {"status": 500, "message": "智能体执行错误"},
    "E_AGENT_INIT": {"status": 500, "message": "智能体初始化失败"},
    "E_AGENT_TIMEOUT": {"status": 504, "message": "智能体执行超时"},
    "E_AGENT_VALIDATION": {"status": 400, "message": "智能体输入验证失败"},
    "E_AGENT_LLM": {"status": 500, "message": "LLM调用失败"},
    "E_MCP": {"status": 500, "message": "MCP协议错误"},
    "E_MCP_CONNECTION": {"status": 503, "message": "MCP服务器连接失败"},
    "E_MCP_TOOL_NOT_FOUND": {"status": 404, "message": "MCP工具不存在"},
    "E_MCP_TOOL_EXEC": {"status": 500, "message": "MCP工具执行失败"},
    "E_MCP_HTTP_FALLBACK": {"status": 500, "message": "MCP HTTP回退调用失败"},
    "E_MCP_CONFIG": {"status": 500, "message": "MCP配置错误"},
    "E_WORKFLOW": {"status": 500, "message": "工作流执行错误"},
    "E_WORKFLOW_INIT": {"status": 500, "message": "工作流初始化失败"},
    "E_WORKFLOW_VALIDATION": {"status": 400, "message": "工作流输入验证失败"},
    "E_WORKFLOW_CANCELLED": {"status": 499, "message": "工作流已被取消"},
    "E_DEBATE_CONSENSUS": {"status": 500, "message": "辩论未能达成共识"},
    "E_DATABASE": {"status": 500, "message": "数据库错误"},
    "E_DATABASE_CONN": {"status": 503, "message": "数据库连接失败"},
    "E_DATABASE_QUERY": {"status": 500, "message": "数据库查询失败"},
    "E_DATABASE_SESSION_NOT_FOUND": {"status": 404, "message": "会话记录不存在"},
    "E_API": {"status": 500, "message": "API错误"},
    "E_API_VALIDATION": {"status": 400, "message": "请求参数验证失败"},
    "E_API_TASK_NOT_FOUND": {"status": 404, "message": "任务不存在"},
    "E_API_TASK_LIMIT": {"status": 429, "message": "运行中的任务数量已达到上限"},
    "E_API_RATE_LIMIT": {"status": 429, "message": "API调用频率超限"},
    "E_API_EXPORT": {"status": 500, "message": "文件导出失败"},
    "E_API_FILE_NOT_FOUND": {"status": 404, "message": "请求的文件不存在"},
    "E_RAG": {"status": 500, "message": "RAG知识库错误"},
    "E_RAG_ENGINE_NOT_AVAILABLE": {"status": 500, "message": "RAG引擎未初始化"},
    "E_RAG_COLLECTION_NOT_FOUND": {"status": 404, "message": "知识库集合不存在"},
    "E_RAG_INDEXING": {"status": 500, "message": "文档索引失败"},
    "E_RAG_SEARCH": {"status": 500, "message": "知识检索失败"},
    "E_CONFIG": {"status": 500, "message": "配置错误"},
    "E_CONFIG_NOT_FOUND": {"status": 500, "message": "配置文件不存在"},
    "E_CONFIG_ENV": {"status": 500, "message": "环境变量配置错误"},
}


def build_error_response(
    error_code: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    构建标准错误响应

    Args:
        error_code: 错误码
        message: 自定义错误信息
        details: 额外详情
        request_id: 请求追踪ID

    Returns:
        Dict: 格式化的错误响应
    """
    error_info = ERROR_CODES.get(error_code, ERROR_CODES["E_INTERNAL"])

    response = {
        "error": {
            "code": error_code,
            "message": message or error_info["message"],
            "timestamp": datetime.now().isoformat(),
        }
    }

    if details:
        response["error"]["details"] = details

    if request_id:
        response["error"]["request_id"] = request_id

    return response


def build_success_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    构建标准成功响应

    Args:
        data: 响应数据
        message: 可选的成功消息
        meta: 可选的元数据

    Returns:
        Dict: 格式化的成功响应
    """
    response: Dict[str, Any] = {"ok": True}

    if message:
        response["message"] = message

    if data is not None:
        response["data"] = data

    if meta:
        response["meta"] = meta

    return response


async def trading_agents_exception_handler(
    request: Request, exc: TradingAgentsException
) -> JSONResponse:
    """TradingAgentsException统一处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers={
            "X-Error-Code": exc.error_code,
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """HTTPException处理器（统一错误响应格式）"""
    error_code = f"E_HTTP_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            error_code=error_code,
            message=exc.detail,
        ),
        headers={
            "X-Error-Code": error_code,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_response(
            error_code="E_API_VALIDATION",
            message="请求参数验证失败",
            details={"errors": errors},
        ),
        headers={
            "X-Error-Code": "E_API_VALIDATION",
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """通用异常处理器（兜底）"""
    import traceback

    error_details = {
        "type": type(exc).__name__,
    }

    if hasattr(exc, "__traceback__"):
        error_details["traceback"] = traceback.format_exception(
            type(exc), exc, exc.__traceback__
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_response(
            error_code="E_INTERNAL",
            message="服务器内部错误",
            details=error_details if len(str(exc)) < 200 else {"type": type(exc).__name__},
        ),
        headers={
            "X-Error-Code": "E_INTERNAL",
        },
    )


class RequestIDMiddleware:
    """请求ID中间件：为每个请求添加唯一追踪ID"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid

        request_id = uuid.uuid4().hex[:12]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                message["headers"].append(
                    (b"X-Request-ID", request_id.encode())
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)