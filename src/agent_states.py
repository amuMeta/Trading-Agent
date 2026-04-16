"""
Agent State 模块 - 定义智能体工作流中的核心状态数据结构

本模块定义了三个核心状态类：
1. InvestDebateState - 投资辩论状态（看涨vs看跌）
2. RiskDebateState - 风险管理辩论状态（激进vs保守vs中性）
3. AgentState - 整个工作流的核心状态，贯穿所有智能体间的数据传递

状态数据流向：
用户查询 → 公司概述分析师 → 6个分析师并行 → 研究员辩论 → 管理层 → 风险辩论 → 最终决策
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import MessagesState
from pydantic import BaseModel


class InvestDebateState(BaseModel):
    """
    投资辩论状态管理

    用于记录看涨研究员和看跌研究员之间的辩论过程。
    每轮辩论，双方各发言一次，记录辩论历史和当前状态。
    """

    history: str = ""  # 完整辩论历史（包含双方所有发言）
    bull_history: str = ""  # 看涨方发言历史
    bear_history: str = ""  # 看跌方发言历史
    current_response: str = ""  # 当前轮次的最新回应
    count: int = 0  # 辩论轮次计数器（每方发言+1）


class RiskDebateState(BaseModel):
    """
    风险管理辩论状态

    用于记录激进、保守、中性三个风险分析师之间的辩论过程。
    三方轮流发言，辩论投资风险和仓位管理策略。
    """

    history: str = ""  # 完整辩论历史
    aggressive_history: str = ""  # 激进方发言历史（追求高收益）
    safe_history: str = ""  # 保守方发言历史（注重风险控制）
    neutral_history: str = ""  # 中性方发言历史（平衡策略）
    current_aggressive_response: str = ""  # 激进方最新回应
    current_safe_response: str = ""  # 保守方最新回应
    current_neutral_response: str = ""  # 中性方最新回应
    count: int = 0  # 辩论轮次计数器（三方发言共+3）


class AgentState(MessagesState):
    """
    智能体状态管理 - 所有智能体间传递的核心状态

    这个状态对象是整个工作流的"数据总线"，每个智能体处理完后
    会将自己的分析结果写入状态，后续智能体可以读取前面的结果。

    状态流转阶段：
    Phase 0: user_query → company_details（公司概述分析师获取公司基本信息）
    Phase 1: 6个分析师并行处理（基于company_details生成各自的分析报告）
    Phase 2: 研究员辩论（基于所有分析师报告进行投资辩论）
    Phase 3: 管理层决策（研究经理→交易员）
    Phase 4: 风险辩论（三方风险分析师辩论）
    """

    # =========================================================================
    # 基础信息
    # =========================================================================
    user_query: str = ""  # 用户原始查询问题，如"分析苹果公司股票"
    company_details: str = ""  # 公司基础信息（名称、代码、交易所、行业等）
    # 仅供分析师阶段使用，后续智能体不传递此字段

    # =========================================================================
    # 分析师报告（Phase 1 并行生成）
    # =========================================================================
    # 每个分析师将自己的分析结果写入对应的字段
    company_overview_report: str = (
        ""  # 公司概述分析师：公司基本情况、业务范围、市场地位
    )
    market_report: str = ""  # 市场分析师：行业趋势、竞争格局、市场空间
    sentiment_report: str = ""  # 情绪分析师：投资者情绪、资金流向、市场热点
    news_report: str = ""  # 新闻分析师：最新新闻、公告、事件影响
    fundamentals_report: str = ""  # 基本面分析师：财务数据、估值指标、盈利能力
    shareholder_report: str = ""  # 股东分析师：股东结构、机构持仓、筹码分布
    product_report: str = ""  # 产品分析师：核心产品、技术优势、研发投入

    # =========================================================================
    # 投资辩论阶段（Phase 2）
    # =========================================================================
    # 看涨研究员和看跌研究员基于7份分析师报告进行辩论
    investment_debate_state: Dict[str, Any] = {}  # 辩论状态对象
    investment_plan: str = ""  # 研究经理综合辩论结果给出的投资计划

    # =========================================================================
    # 管理层决策（Phase 3）
    # =========================================================================
    # 研究经理制定投资计划后，交易员给出具体的交易策略
    trader_investment_plan: str = ""  # 交易员的具体投资计划（包含买入卖出时机建议）

    # =========================================================================
    # 风险管理辩论阶段（Phase 4）
    # =========================================================================
    # 三个风险分析师辩论后，风险经理给出最终决策
    risk_debate_state: Dict[str, Any] = {}  # 风险辩论状态对象
    final_trade_decision: str = ""  # 最终交易决策（综合所有分析和风险评估）

    # =========================================================================
    # 执行记录
    # =========================================================================
    mcp_tool_calls: List[Dict[str, Any]] = []  # MCP工具调用记录（谁调用了什么工具）
    agent_execution_history: List[Dict[str, Any]] = []  # 所有智能体的执行历史

    # =========================================================================
    # 错误和警告
    # =========================================================================
    errors: List[str] = []  # 执行过程中的错误信息
    warnings: List[str] = []  # 警告信息（如智能体被跳过等）

    def add_agent_execution(
        self, agent_name: str, action: str, result: str, mcp_used: bool = False
    ):
        """
        添加智能体执行记录

        Args:
            agent_name: 智能体名称
            action: 执行的动作描述
            result: 执行结果
            mcp_used: 是否使用了MCP工具
        """
        from datetime import datetime

        self.agent_execution_history.append(
            {
                "agent_name": agent_name,
                "action": action,
                "result": result,
                "mcp_used": mcp_used,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    def add_mcp_tool_call(
        self, agent_name: str, tool_name: str, tool_args: Dict, tool_result: Any
    ):
        """
        添加MCP工具调用记录

        Args:
            agent_name: 调用工具的智能体名称
            tool_name: 工具名称（如get_kline_data）
            tool_args: 工具参数
            tool_result: 工具返回结果
        """
        from datetime import datetime

        self.mcp_tool_calls.append(
            {
                "agent_name": agent_name,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "tool_result": str(tool_result),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    def add_error(self, error_msg: str):
        """添加错误信息到状态"""
        self.errors.append(error_msg)

    def add_warning(self, warning_msg: str):
        """添加警告信息到状态"""
        self.warnings.append(warning_msg)

    def get_all_reports(self) -> Dict[str, str]:
        """
        获取所有分析师报告

        Returns:
            Dict[str, str]: 以报告名称为key，报告内容为value的字典
        """
        return {
            "company_overview_report": self.company_overview_report,
            "market_report": self.market_report,
            "sentiment_report": self.sentiment_report,
            "news_report": self.news_report,
            "fundamentals_report": self.fundamentals_report,
            "shareholder_report": self.shareholder_report,
            "product_report": self.product_report,
        }

    def get_debate_summary(self) -> str:
        """
        获取辩论摘要，用于后续智能体了解辩论过程

        Returns:
            str: 投资辩论和风险辩论的历史摘要
        """
        investment_history = self.investment_debate_state.get("history", "")
        risk_history = self.risk_debate_state.get("history", "")

        summary = ""
        if investment_history:
            summary += f"投资辩论历史:\n{investment_history}\n\n"
        if risk_history:
            summary += f"风险管理辩论历史:\n{risk_history}\n\n"

        return summary.strip()
