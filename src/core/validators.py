"""
TradingAgents 输入验证器

提供通用的输入验证函数，用于：
- 股票代码格式验证
- 会话ID格式验证
- 查询字符串验证
- 分页参数验证
"""

import re
from typing import Optional, Tuple


def validate_stock_code(stock_code: str) -> Tuple[bool, Optional[str]]:
    """
    验证股票代码格式

    支持格式：
    - 6位数字代码（会自动添加SSE:前缀）
    - SSE:xxxxxx（上交所）
    - SZSE:xxxxxx（深交所）
    - NASDAQ:xxxxx（美股）

    Args:
        stock_code: 股票代码

    Returns:
        (是否有效, 错误信息)
    """
    if not stock_code:
        return False, "股票代码不能为空"

    stock_code = stock_code.strip()

    patterns = [
        r"^\d{6}$",
        r"^SSE:\d{6}$",
        r"^SZSE:\d{6}$",
        r"^NASDAQ:[A-Za-z]+$",
        r"^HK:\d{5}$",
    ]

    for pattern in patterns:
        if re.match(pattern, stock_code):
            return True, None

    return False, f"不支持的股票代码格式: {stock_code}"


def normalize_stock_code(stock_code: str) -> str:
    """
    规范化股票代码格式

    Args:
        stock_code: 原始股票代码

    Returns:
        str: 规范化后的股票代码
    """
    stock_code = stock_code.strip()

    if re.match(r"^\d{6}$", stock_code):
        return f"SSE:{stock_code}"

    return stock_code


def validate_session_id(session_id: str) -> Tuple[bool, Optional[str]]:
    """
    验证会话ID格式

    Args:
        session_id: 会话ID

    Returns:
        (是否有效, 错误信息)
    """
    if not session_id:
        return False, "会话ID不能为空"

    if len(session_id) < 4:
        return False, "会话ID长度至少4位"

    if len(session_id) > 64:
        return False, "会话ID长度不能超过64位"

    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        return False, "会话ID只能包含字母、数字、下划线和连字符"

    return True, None


def validate_query_string(query: str, min_length: int = 1, max_length: int = 1000) -> Tuple[bool, Optional[str]]:
    """
    验证查询字符串

    Args:
        query: 查询字符串
        min_length: 最小长度
        max_length: 最大长度

    Returns:
        (是否有效, 错误信息)
    """
    if not query:
        return False, "查询内容不能为空"

    query = query.strip()

    if len(query) < min_length:
        return False, f"查询内容长度至少{min_length}个字符"

    if len(query) > max_length:
        return False, f"查询内容长度不能超过{max_length}个字符"

    return True, None


def validate_pagination_params(limit: int, offset: int) -> Tuple[bool, Optional[str]]:
    """
    验证分页参数

    Args:
        limit: 每页数量
        offset: 偏移量

    Returns:
        (是否有效, 错误信息)
    """
    if limit < 1:
        return False, "每页数量不能小于1"

    if limit > 100:
        return False, "每页数量不能超过100"

    if offset < 0:
        return False, "偏移量不能为负数"

    return True, None


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证日期范围

    Args:
        start_date: 开始日期（ISO格式）
        end_date: 结束日期（ISO格式）

    Returns:
        (是否有效, 错误信息)
    """
    from datetime import datetime

    if start_date:
        try:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            return False, f"开始日期格式错误，应为ISO格式: {start_date}"

    if end_date:
        try:
            datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            return False, f"结束日期格式错误，应为ISO格式: {end_date}"

    if start_date and end_date:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        if start > end:
            return False, "开始日期不能晚于结束日期"

    return True, None


def validate_agent_name(agent_name: str) -> Tuple[bool, Optional[str]]:
    """
    验证智能体名称

    Args:
        agent_name: 智能体名称

    Returns:
        (是否有效, 错误信息)
    """
    valid_agents = [
        "company_overview_analyst",
        "market_analyst",
        "sentiment_analyst",
        "news_analyst",
        "fundamentals_analyst",
        "shareholder_analyst",
        "product_analyst",
        "bull_researcher",
        "bear_researcher",
        "research_manager",
        "trader",
        "aggressive_risk_analyst",
        "safe_risk_analyst",
        "neutral_risk_analyst",
        "risk_manager",
    ]

    if not agent_name:
        return False, "智能体名称不能为空"

    if agent_name not in valid_agents:
        return False, f"不支持的智能体: {agent_name}"

    return True, None


def validate_rounds(rounds: int, min_val: int = 1, max_val: int = 10) -> Tuple[bool, Optional[str]]:
    """
    验证辩论轮次

    Args:
        rounds: 轮次
        min_val: 最小值
        max_val: 最大值

    Returns:
        (是否有效, 错误信息)
    """
    if rounds < min_val:
        return False, f"轮次不能小于{min_val}"

    if rounds > max_val:
        return False, f"轮次不能超过{max_val}"

    return True, None


def validate_file_extension(filename: str, allowed_extensions: set) -> Tuple[bool, Optional[str]]:
    """
    验证文件扩展名

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名集合

    Returns:
        (是否有效, 错误信息)
    """
    if not filename:
        return False, "文件名为空"

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in allowed_extensions:
        return False, f"不支持的文件类型: {ext}，支持的类型: {', '.join(sorted(allowed_extensions))}"

    return True, None