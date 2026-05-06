"""
TradingAgents 异常层次结构

定义系统中所有异常的基类和具体异常类型，
支持错误码、上下文信息和统一序列化。
"""

from typing import Any, Dict, Optional
from datetime import datetime


class TradingAgentsException(Exception):
    """TradingAgents异常基类"""

    error_code: str = "E_INTERNAL"
    message: str = "内部错误"
    status_code: int = 500

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now().isoformat()

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        if self.cause and hasattr(self.cause, "args"):
            result["error"]["cause"] = str(self.cause)
        return result


# =============================================================================
# 智能体相关异常
# =============================================================================

class AgentException(TradingAgentsException):
    """智能体基础异常"""
    error_code = "E_AGENT"
    message = "智能体执行错误"
    status_code = 500


class AgentInitializationError(AgentException):
    """智能体初始化失败"""
    error_code = "E_AGENT_INIT"
    message = "智能体初始化失败"
    status_code = 500


class AgentTimeoutError(AgentException):
    """智能体执行超时"""
    error_code = "E_AGENT_TIMEOUT"
    message = "智能体执行超时"
    status_code = 504


class AgentValidationError(AgentException):
    """智能体输入验证失败"""
    error_code = "E_AGENT_VALIDATION"
    message = "智能体输入验证失败"
    status_code = 400


class AgentLLMError(AgentException):
    """LLM调用失败"""
    error_code = "E_AGENT_LLM"
    message = "LLM调用失败"
    status_code = 500


# =============================================================================
# MCP相关异常
# =============================================================================

class MCPException(TradingAgentsException):
    """MCP基础异常"""
    error_code = "E_MCP"
    message = "MCP协议错误"
    status_code = 500


class MCPConnectionError(MCPException):
    """MCP连接失败"""
    error_code = "E_MCP_CONNECTION"
    message = "MCP服务器连接失败"
    status_code = 503


class MCPToolNotFoundError(MCPException):
    """MCP工具不存在"""
    error_code = "E_MCP_TOOL_NOT_FOUND"
    message = "MCP工具不存在"
    status_code = 404


class MCPToolExecutionError(MCPException):
    """MCP工具执行失败"""
    error_code = "E_MCP_TOOL_EXEC"
    message = "MCP工具执行失败"
    status_code = 500


class MCPHTTPFallbackError(MCPException):
    """MCP HTTP回退失败"""
    error_code = "E_MCP_HTTP_FALLBACK"
    message = "MCP HTTP回退调用失败"
    status_code = 500


class MCPConfigurationError(MCPException):
    """MCP配置错误"""
    error_code = "E_MCP_CONFIG"
    message = "MCP配置错误"
    status_code = 500


# =============================================================================
# 工作流相关异常
# =============================================================================

class WorkflowException(TradingAgentsException):
    """工作流基础异常"""
    error_code = "E_WORKFLOW"
    message = "工作流执行错误"
    status_code = 500


class WorkflowInitializationError(WorkflowException):
    """工作流初始化失败"""
    error_code = "E_WORKFLOW_INIT"
    message = "工作流初始化失败"
    status_code = 500


class WorkflowValidationError(WorkflowException):
    """工作流输入验证失败"""
    error_code = "E_WORKFLOW_VALIDATION"
    message = "工作流输入验证失败"
    status_code = 400


class WorkflowCancellationError(WorkflowException):
    """工作流被取消"""
    error_code = "E_WORKFLOW_CANCELLED"
    message = "工作流已被取消"
    status_code = 499


class DebateConsensusError(WorkflowException):
    """辩论共识未达成"""
    error_code = "E_DEBATE_CONSENSUS"
    message = "辩论未能达成共识"
    status_code = 500


# =============================================================================
# 数据库相关异常
# =============================================================================

class DatabaseException(TradingAgentsException):
    """数据库基础异常"""
    error_code = "E_DATABASE"
    message = "数据库错误"
    status_code = 500


class DatabaseConnectionError(DatabaseException):
    """数据库连接失败"""
    error_code = "E_DATABASE_CONN"
    message = "数据库连接失败"
    status_code = 503


class DatabaseQueryError(DatabaseException):
    """数据库查询失败"""
    error_code = "E_DATABASE_QUERY"
    message = "数据库查询失败"
    status_code = 500


class DatabaseSessionNotFoundError(DatabaseException):
    """会话记录不存在"""
    error_code = "E_DATABASE_SESSION_NOT_FOUND"
    message = "会话记录不存在"
    status_code = 404


# =============================================================================
# API相关异常
# =============================================================================

class APIException(TradingAgentsException):
    """API基础异常"""
    error_code = "E_API"
    message = "API错误"
    status_code = 500


class APIValidationError(APIException):
    """API请求验证失败"""
    error_code = "E_API_VALIDATION"
    message = "请求参数验证失败"
    status_code = 400


class APITaskNotFoundError(APIException):
    """任务不存在"""
    error_code = "E_API_TASK_NOT_FOUND"
    message = "任务不存在"
    status_code = 404


class APITaskLimitError(APIException):
    """任务并发数超限"""
    error_code = "E_API_TASK_LIMIT"
    message = "运行中的任务数量已达到上限"
    status_code = 429


class APIRateLimitError(APIException):
    """API调用频率超限"""
    error_code = "E_API_RATE_LIMIT"
    message = "API调用频率超限，请稍后重试"
    status_code = 429


class APIExportError(APIException):
    """导出失败"""
    error_code = "E_API_EXPORT"
    message = "文件导出失败"
    status_code = 500


class APIFileNotFoundError(APIException):
    """文件不存在"""
    error_code = "E_API_FILE_NOT_FOUND"
    message = "请求的文件不存在"
    status_code = 404


# =============================================================================
# RAG相关异常
# =============================================================================

class RAGException(TradingAgentsException):
    """RAG基础异常"""
    error_code = "E_RAG"
    message = "RAG知识库错误"
    status_code = 500


class RAGEngineNotAvailableError(RAGException):
    """RAG引擎未初始化"""
    error_code = "E_RAG_ENGINE_NOT_AVAILABLE"
    message = "RAG引擎未初始化"
    status_code = 500


class RAGCollectionNotFoundError(RAGException):
    """知识库集合不存在"""
    error_code = "E_RAG_COLLECTION_NOT_FOUND"
    message = "知识库集合不存在"
    status_code = 404


class RAGIndexingError(RAGException):
    """文档索引失败"""
    error_code = "E_RAG_INDEXING"
    message = "文档索引失败"
    status_code = 500


class RAGSearchError(RAGException):
    """知识检索失败"""
    error_code = "E_RAG_SEARCH"
    message = "知识检索失败"
    status_code = 500


# =============================================================================
# 配置相关异常
# =============================================================================

class ConfigurationException(TradingAgentsException):
    """配置基础异常"""
    error_code = "E_CONFIG"
    message = "配置错误"
    status_code = 500


class ConfigurationNotFoundError(ConfigurationException):
    """配置文件不存在"""
    error_code = "E_CONFIG_NOT_FOUND"
    message = "配置文件不存在"
    status_code = 500


class EnvironmentVariableError(ConfigurationException):
    """环境变量配置错误"""
    error_code = "E_CONFIG_ENV"
    message = "环境变量配置错误"
    status_code = 500


# =============================================================================
# 工具函数
# =============================================================================

def format_exception(exc: Exception) -> Dict[str, Any]:
    """
    将异常格式化为字典

    Args:
        exc: 异常实例

    Returns:
        Dict: 格式化的错误信息
    """
    if isinstance(exc, TradingAgentsException):
        return exc.to_dict()

    return {
        "error": {
            "code": "E_INTERNAL",
            "message": str(exc),
            "type": type(exc).__name__,
            "timestamp": datetime.now().isoformat(),
        }
    }