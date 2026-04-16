"""
Workflow Orchestrator 模块 - 工作流编排器

这是整个项目的核心模块，负责：
1. 初始化和管理所有15个智能体
2. 创建和管理LangGraph工作流
3. 协调智能体间的执行顺序
4. 处理并行和条件分支逻辑
5. 管理辩论轮次

工作流结构：
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 0: 公司概述分析师                                              │
│   └─→ 获取公司基础信息（名称、代码、行业等）                            │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 1: 6个分析师并行                                               │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │ Market │ Sentiment │ News │ Fundamentals │ Shareholder │ Product│
│   └──────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 2: 研究员辩论（看涨 ↔ 看跌）                                    │
│   └─→ 投资计划（研究经理）                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 3: 交易员                                                     │
│   └─→ 交易计划                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 4: 风险辩论（激进 ↔ 保守 ↔ 中性）                               │
│   └─→ 最终决策（风险经理）                                           │
└─────────────────────────────────────────────────────────────────────┘
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from .agent_states import AgentState
from .mcp_manager import MCPManager
from .progress_tracker import ProgressTracker
from .agents.analysts import (
    CompanyOverviewAnalyst,
    MarketAnalyst,
    SentimentAnalyst,
    NewsAnalyst,
    FundamentalsAnalyst,
    ShareholderAnalyst,
    ProductAnalyst,
)
from .agents.researchers import BullResearcher, BearResearcher
from .agents.managers import ResearchManager, Trader
from .agents.risk_management import (
    AggressiveRiskAnalyst,
    SafeRiskAnalyst,
    NeutralRiskAnalyst,
    RiskManager,
)


class WorkflowOrchestrator:
    """
    工作流编排器 - 管理整个智能体交互流程

    核心职责：
    - 管理15个智能体的生命周期
    - 创建LangGraph状态图定义工作流
    - 处理并行执行（asyncio.gather）
    - 处理条件分支（辩论轮次控制）
    - 提供取消机制
    """

    def __init__(self, config_file: str = "mcp_config.json"):
        """
        初始化工作流编排器

        Args:
            config_file: MCP配置文件路径
        """
        # 加载环境变量
        load_dotenv()

        # 初始化MCP管理器
        self.mcp_manager = MCPManager(config_file)

        # 初始化进度管理器（延迟创建）
        self.progress_manager = None

        # 初始化所有智能体
        self.agents = self._initialize_agents()

        # 工作流配置
        self.max_debate_rounds = int(os.getenv("MAX_DEBATE_ROUNDS", "3"))
        self.max_risk_debate_rounds = int(os.getenv("MAX_RISK_DEBATE_ROUNDS", "2"))
        self.debug_mode = os.getenv("DEBUG_MODE", "true").lower() == "true"
        self.verbose_logging = os.getenv("VERBOSE_LOGGING", "true").lower() == "true"

        # 创建状态图
        self.workflow = self._create_workflow()

        # 本轮启用的智能体集合（为空表示默认启用全部）
        self.active_agents: Set[str] = set()

        # 取消检查器
        self.cancel_checker = None

        print("🚀 工作流编排器初始化完成")

    # =========================================================================
    # 智能体初始化
    # =========================================================================

    def _initialize_agents(self) -> Dict[str, Any]:
        """
        初始化所有15个智能体

        智能体分为4个团队：
        1. 分析师团队（7个）- 并行执行
        2. 研究员团队（2个）- 辩论
        3. 管理层（2个）- 决策
        4. 风险管理团队（4个）- 风险辩论

        Returns:
            Dict[str, Agent]: 智能体名称到实例的映射
        """
        agents = {
            # ========== 分析师团队（Phase 1 并行执行）==========
            "company_overview_analyst": CompanyOverviewAnalyst(self.mcp_manager),
            "market_analyst": MarketAnalyst(self.mcp_manager),
            "sentiment_analyst": SentimentAnalyst(self.mcp_manager),
            "news_analyst": NewsAnalyst(self.mcp_manager),
            "fundamentals_analyst": FundamentalsAnalyst(self.mcp_manager),
            "shareholder_analyst": ShareholderAnalyst(self.mcp_manager),
            "product_analyst": ProductAnalyst(self.mcp_manager),
            # ========== 研究员团队（Phase 2 辩论）==========
            "bull_researcher": BullResearcher(self.mcp_manager),
            "bear_researcher": BearResearcher(self.mcp_manager),
            # ========== 管理层（Phase 3 决策）==========
            "research_manager": ResearchManager(self.mcp_manager),
            "trader": Trader(self.mcp_manager),
            # ========== 风险管理团队（Phase 4 风险辩论）==========
            "aggressive_risk_analyst": AggressiveRiskAnalyst(self.mcp_manager),
            "safe_risk_analyst": SafeRiskAnalyst(self.mcp_manager),
            "neutral_risk_analyst": NeutralRiskAnalyst(self.mcp_manager),
            "risk_manager": RiskManager(self.mcp_manager),
        }

        print(f"初始化了 {len(agents)} 个智能体")
        return agents

    # =========================================================================
    # 工作流图定义
    # =========================================================================

    def _create_workflow(self) -> StateGraph:
        """
        创建LangGraph工作流状态图

        工作流使用StateGraph定义，包含：
        - 节点：每个节点是一个处理函数
        - 边：定义节点间的执行顺序
        - 条件边：根据状态决定下一个节点

        Returns:
            CompiledStateGraph: 编译后的工作流图
        """
        workflow = StateGraph(AgentState)

        # =====================================================================
        # 添加节点
        # =====================================================================
        # Phase 0: 公司概述分析师
        workflow.add_node(
            "company_overview_analyst", self._company_overview_analyst_node
        )

        # Phase 1: 6个分析师（通过并行聚合节点）
        workflow.add_node("market_analyst", self._market_analyst_node)
        workflow.add_node("sentiment_analyst", self._sentiment_analyst_node)
        workflow.add_node("news_analyst", self._news_analyst_node)
        workflow.add_node("fundamentals_analyst", self._fundamentals_analyst_node)
        workflow.add_node("shareholder_analyst", self._shareholder_analyst_node)
        workflow.add_node("product_analyst", self._product_analyst_node)

        # 分析师并行聚合节点（内部并发执行6个分析师）
        workflow.add_node("analysts_parallel", self._analysts_parallel_node)

        # Phase 2: 研究员辩论
        workflow.add_node("bull_researcher", self._bull_researcher_node)
        workflow.add_node("bear_researcher", self._bear_researcher_node)

        # Phase 3: 管理层
        workflow.add_node("research_manager", self._research_manager_node)
        workflow.add_node("trader", self._trader_node)

        # Phase 4: 风险管理
        workflow.add_node("aggressive_risk_analyst", self._aggressive_risk_analyst_node)
        workflow.add_node("safe_risk_analyst", self._safe_risk_analyst_node)
        workflow.add_node("neutral_risk_analyst", self._neutral_risk_analyst_node)
        workflow.add_node("risk_manager", self._risk_manager_node)

        # =====================================================================
        # 设置入口点
        # =====================================================================
        workflow.set_entry_point("company_overview_analyst")

        # =====================================================================
        # 添加边（定义流程）
        # =====================================================================
        # Phase 0 → Phase 1
        workflow.add_edge("company_overview_analyst", "analysts_parallel")

        # Phase 1 → Phase 2（并行完成后进入辩论）
        workflow.add_edge("analysts_parallel", "bull_researcher")

        # Phase 2: 投资辩论（条件边）
        # 根据辩论轮次决定是继续辩论还是进入研究经理
        workflow.add_conditional_edges(
            "bull_researcher",
            self._should_continue_investment_debate,
            {
                "bear_researcher": "bear_researcher",
                "research_manager": "research_manager",
            },
        )
        workflow.add_conditional_edges(
            "bear_researcher",
            self._should_continue_investment_debate,
            {
                "bull_researcher": "bull_researcher",
                "research_manager": "research_manager",
            },
        )

        # Phase 3: 研究经理 → 交易员
        workflow.add_edge("research_manager", "trader")

        # Phase 4: 交易员 → 风险辩论
        workflow.add_edge("trader", "aggressive_risk_analyst")

        # 风险辩论（三方循环）
        workflow.add_conditional_edges(
            "aggressive_risk_analyst",
            self._should_continue_risk_debate,
            {"safe_risk_analyst": "safe_risk_analyst", "risk_manager": "risk_manager"},
        )
        workflow.add_conditional_edges(
            "safe_risk_analyst",
            self._should_continue_risk_debate,
            {
                "neutral_risk_analyst": "neutral_risk_analyst",
                "risk_manager": "risk_manager",
            },
        )
        workflow.add_conditional_edges(
            "neutral_risk_analyst",
            self._should_continue_risk_debate,
            {
                "aggressive_risk_analyst": "aggressive_risk_analyst",
                "risk_manager": "risk_manager",
            },
        )

        # 结束
        workflow.add_edge("risk_manager", END)

        return workflow.compile()

    # =========================================================================
    # 节点处理函数
    # =========================================================================

    async def _company_overview_analyst_node(self, state: AgentState) -> AgentState:
        """
        公司概述分析师节点 (Phase 0)

        首先执行的智能体，负责获取公司基础信息：
        - 公司名称、股票代码、交易所
        - 所属行业、公司简介
        - 主要产品或服务

        这些信息会被传递给其他6个分析师使用。
        """
        print("🏢 第0阶段：公司概述分析师")
        self._check_cancel()
        if not self._is_active("company_overview_analyst"):
            self._skip_agent("company_overview_analyst")
            self._check_cancel()
            return state
        result = await self.agents["company_overview_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _market_analyst_node(self, state: AgentState) -> AgentState:
        """市场分析师节点（由并行节点内部调用）"""
        print("🔍 市场分析师")
        self._check_cancel()
        if not self._is_active("market_analyst"):
            self._skip_agent("market_analyst")
            self._check_cancel()
            return state
        result = await self.agents["market_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _sentiment_analyst_node(self, state: AgentState) -> AgentState:
        """情绪分析师节点（由并行节点内部调用）"""
        print("😊 情绪分析师")
        self._check_cancel()
        if not self._is_active("sentiment_analyst"):
            self._skip_agent("sentiment_analyst")
            self._check_cancel()
            return state
        result = await self.agents["sentiment_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _news_analyst_node(self, state: AgentState) -> AgentState:
        """新闻分析师节点（由并行节点内部调用）"""
        print("📰 新闻分析师")
        self._check_cancel()
        if not self._is_active("news_analyst"):
            self._skip_agent("news_analyst")
            self._check_cancel()
            return state
        result = await self.agents["news_analyst"].process(state, self.progress_manager)
        self._check_cancel()
        return result

    async def _fundamentals_analyst_node(self, state: AgentState) -> AgentState:
        """基本面分析师节点（由并行节点内部调用）"""
        print("📊 基本面分析师")
        self._check_cancel()
        if not self._is_active("fundamentals_analyst"):
            self._skip_agent("fundamentals_analyst")
            self._check_cancel()
            return state
        result = await self.agents["fundamentals_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _shareholder_analyst_node(self, state: AgentState) -> AgentState:
        """股东分析师节点（由并行节点内部调用）"""
        print("👥 股东分析师")
        self._check_cancel()
        if not self._is_active("shareholder_analyst"):
            self._skip_agent("shareholder_analyst")
            self._check_cancel()
            return state
        result = await self.agents["shareholder_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _product_analyst_node(self, state: AgentState) -> AgentState:
        """产品分析师节点（由并行节点内部调用）"""
        print("🏭 产品分析师")
        self._check_cancel()
        if not self._is_active("product_analyst"):
            self._skip_agent("product_analyst")
            self._check_cancel()
            return state
        result = await self.agents["product_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _analysts_parallel_node(self, state: AgentState) -> AgentState:
        """
        分析师并行节点 (Phase 1)

        这是工作流的核心优化点：6个分析师并行执行。
        使用asyncio.gather实现真正的并发，大幅提升效率。

        并行执行优势：
        - 串行：总时间 = T1 + T2 + T3 + T4 + T5 + T6
        - 并行：总时间 ≈ max(T1, T2, T3, T4, T5, T6)

        状态管理：
        - 每个分析师使用深拷贝避免并发写冲突
        - 完成后合并结果到主状态
        """
        import copy
        from asyncio import gather, create_task, wait, FIRST_COMPLETED

        # 收集需要执行的分析师
        analyst_names = [
            name
            for name in [
                "market_analyst",
                "sentiment_analyst",
                "news_analyst",
                "fundamentals_analyst",
                "shareholder_analyst",
                "product_analyst",
            ]
            if self._is_active(name)
        ]

        if not analyst_names:
            return state

        self._check_cancel()

        # 为每个分析师创建深拷贝（避免状态竞争）
        tasks = []
        for name in analyst_names:
            state_copy = copy.deepcopy(state)
            tasks.append(
                create_task(
                    self.agents[name].process(state_copy, self.progress_manager)
                )
            )

        # 协作式取消：使用wait返回已完成的tasks
        pending = set(tasks)
        done_results = []

        while pending:
            self._check_cancel()
            done, pending = await wait(
                pending, timeout=0.3, return_when=FIRST_COMPLETED
            )
            for d in done:
                done_results.append(await d)
        results = done_results

        # 合并结果到主状态
        def setter(key: str, value: Any):
            if isinstance(state, dict):
                state[key] = value
            else:
                setattr(state, key, value)

        def getter_from(res, key: str) -> str:
            if isinstance(res, dict):
                return res.get(key, "")
            return getattr(res, key, "")

        # 合并报告字段
        report_keys = [
            "market_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
            "shareholder_report",
            "product_report",
        ]

        for key in report_keys:
            for res in results:
                val = getter_from(res, key)
                # 只覆盖非空值
                if isinstance(val, str) and val.strip():
                    setter(key, val)

        # 合并执行历史
        hist_keys = ["agent_execution_history", "mcp_tool_calls", "warnings", "errors"]
        for hkey in hist_keys:
            merged: List[Any] = []
            for res in results:
                part = getter_from(res, hkey)
                if isinstance(part, list):
                    merged.extend(part)
            if merged:
                setter(hkey, merged)

        return state

    async def _bull_researcher_node(self, state: AgentState) -> AgentState:
        """
        看涨研究员节点 (Phase 2)

        基于7份分析师报告，构建看涨投资论证。
        反驳看跌研究员的观点。
        """
        print("📈 看涨研究员")
        self._check_cancel()
        if not self._is_active("bull_researcher"):
            self._increment_investment_round(state)
            self._skip_agent("bull_researcher")
            self._check_cancel()
            return state
        result = await self.agents["bull_researcher"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _bear_researcher_node(self, state: AgentState) -> AgentState:
        """
        看跌研究员节点 (Phase 2)

        基于7份分析师报告，构建看跌投资论证。
        指出风险和问题。
        """
        print("📉 看跌研究员")
        self._check_cancel()
        if not self._is_active("bear_researcher"):
            self._increment_investment_round(state)
            self._skip_agent("bear_researcher")
            self._check_cancel()
            return state
        result = await self.agents["bear_researcher"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _research_manager_node(self, state: AgentState) -> AgentState:
        """
        研究经理节点 (Phase 3)

        综合辩论结果，给出投资建议和计划。
        """
        print("🧑‍💼 研究经理")
        self._check_cancel()
        if not self._is_active("research_manager"):
            self._skip_agent("research_manager")
            self._check_cancel()
            return state
        result = await self.agents["research_manager"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _trader_node(self, state: AgentState) -> AgentState:
        """
        交易员节点 (Phase 3)

        将投资计划转化为具体的交易策略。
        """
        print("👨‍💻 交易员")
        self._check_cancel()
        if not self._is_active("trader"):
            self._skip_agent("trader")
            self._check_cancel()
            return state
        result = await self.agents["trader"].process(state, self.progress_manager)
        self._check_cancel()
        return result

    async def _aggressive_risk_analyst_node(self, state: AgentState) -> AgentState:
        """
        激进风险分析师节点 (Phase 4)

        关注收益，适合高风险偏好。
        """
        print("🔥 激进风险分析师")
        self._check_cancel()
        if not self._is_active("aggressive_risk_analyst"):
            self._increment_risk_round(state)
            self._skip_agent("aggressive_risk_analyst")
            self._check_cancel()
            return state
        result = await self.agents["aggressive_risk_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _safe_risk_analyst_node(self, state: AgentState) -> AgentState:
        """
        保守风险分析师节点 (Phase 4)

        关注风险，适合低风险偏好。
        """
        print("🛡️ 保守风险分析师")
        self._check_cancel()
        if not self._is_active("safe_risk_analyst"):
            self._increment_risk_round(state)
            self._skip_agent("safe_risk_analyst")
            self._check_cancel()
            return state
        result = await self.agents["safe_risk_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _neutral_risk_analyst_node(self, state: AgentState) -> AgentState:
        """
        中性风险分析师节点 (Phase 4)

        平衡收益和风险。
        """
        print("⚖️ 中立风险分析师")
        self._check_cancel()
        if not self._is_active("neutral_risk_analyst"):
            self._increment_risk_round(state)
            self._skip_agent("neutral_risk_analyst")
            self._check_cancel()
            return state
        result = await self.agents["neutral_risk_analyst"].process(
            state, self.progress_manager
        )
        self._check_cancel()
        return result

    async def _risk_manager_node(self, state: AgentState) -> AgentState:
        """
        风险经理节点 (Phase 4 - 结束)

        综合所有风险分析，给出最终交易决策。
        """
        print("🛡️ 风险管理器")
        self._check_cancel()
        if not self._is_active("risk_manager"):
            self._skip_agent("risk_manager")
            self._check_cancel()
            return state
        result = await self.agents["risk_manager"].process(state, self.progress_manager)
        self._check_cancel()
        return result

    # =========================================================================
    # 条件判断函数
    # =========================================================================

    def _should_continue_investment_debate(self, state) -> str:
        """
        判断是否继续投资辩论

        辩论规则：
        - 看涨研究员先发言（count=0时）
        - 双方轮流发言，每方发言count+1
        - 每2次发言为1轮
        - 达到max_debate_rounds后进入研究经理

        Args:
            state: 当前状态

        Returns:
            str: 下一个节点名称
        """
        if isinstance(state, dict):
            investment_debate_state = state.get("investment_debate_state", {})
        else:
            investment_debate_state = state.investment_debate_state
        count = investment_debate_state.get("count", 0)

        # 计算当前轮数：每2次发言为1轮
        current_round = (count + 1) // 2 + ((count + 1) % 2)

        print(
            f"🤔 投资辩论: count={count}, round={current_round}, max={self.max_debate_rounds}"
        )

        if current_round <= self.max_debate_rounds:
            if count % 2 == 1:  # 奇数次，看跌研究员
                return "bear_researcher"
            else:  # 偶数次，看涨研究员
                return "bull_researcher"
        else:
            return "research_manager"

    def _should_continue_risk_debate(self, state) -> str:
        """
        判断是否继续风险辩论

        辩论规则：
        - 三方轮流发言：激进 → 保守 → 中性 → 激进...
        - 每3次发言为1轮
        - 达到max_risk_debate_rounds后进入风险经理

        Args:
            state: 当前状态

        Returns:
            str: 下一个节点名称
        """
        if isinstance(state, dict):
            risk_debate_state = state.get("risk_debate_state", {})
        else:
            risk_debate_state = state.risk_debate_state
        count = risk_debate_state.get("count", 0)

        # 计算当前轮数
        current_round = (count + 1) // 3 + ((count + 1) % 3 > 0)

        print(
            f"🤔 风险辩论: count={count}, round={current_round}, max={self.max_risk_debate_rounds}"
        )

        if current_round <= self.max_risk_debate_rounds:
            remainder = count % 3
            if remainder == 1:
                return "safe_risk_analyst"
            elif remainder == 2:
                return "neutral_risk_analyst"
            else:
                return "aggressive_risk_analyst"
        else:
            return "risk_manager"

    # =========================================================================
    # 取消机制
    # =========================================================================

    def _check_cancel(self):
        """
        检查是否需要取消分析

        如果cancel_checker返回True，抛出CancelledError中断工作流。
        """
        if self.cancel_checker and callable(self.cancel_checker):
            if self.cancel_checker():
                raise asyncio.CancelledError("分析已被用户取消")

    # =========================================================================
    # 公开接口
    # =========================================================================

    async def initialize(self) -> bool:
        """
        初始化MCP连接

        Returns:
            bool: 初始化是否成功
        """
        try:
            success = await self.mcp_manager.initialize()
            if success:
                print("✅ 工作流编排器初始化成功")
            else:
                print("⚠️ MCP连接失败，将在无工具模式下运行")
            return success
        except Exception as e:
            print(f"❌ 工作流编排器初始化失败: {e}")
            return False

    async def run_analysis(
        self,
        user_query: str,
        cancel_checker=None,
        active_agents: Optional[List[str]] = None,
    ) -> AgentState:
        """
        运行完整的交易分析流程

        这是工作流的主入口，调用后执行完整的工作流：
        1. 初始化状态
        2. 执行工作流图
        3. 返回最终状态

        Args:
            user_query: 用户查询（如"分析苹果公司股票"）
            cancel_checker: 取消检查函数（返回True时取消）
            active_agents: 本轮启用的智能体列表（None表示全部启用）

        Returns:
            AgentState: 包含所有分析结果的最终状态
        """
        print("🚀 智能交易分析系统启动")
        print(f"📝 用户查询: {user_query}")

        # 存储取消检查器
        self.cancel_checker = cancel_checker

        # 配置本轮启用的智能体
        if active_agents is None or len(active_agents) == 0:
            self.active_agents = set(self.agents.keys())
        else:
            self.active_agents = set([a for a in active_agents if a in self.agents])

        # 初始化进度跟踪器
        self.progress_manager = ProgressTracker()
        self.progress_manager.update_user_query(user_query)
        self.progress_manager.set_active_agents(sorted(list(self.active_agents)))
        self.progress_manager.log_workflow_start({"user_query": user_query})

        # 初始化状态
        initial_state = AgentState(
            user_query=user_query,
            investment_debate_state={
                "count": 0,
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
            },
            risk_debate_state={
                "count": 0,
                "history": "",
                "aggressive_history": "",
                "safe_history": "",
                "neutral_history": "",
                "current_aggressive_response": "",
                "current_safe_response": "",
                "current_neutral_response": "",
            },
            messages=[],
        )

        try:
            self._check_cancel()

            # 执行工作流
            workflow_result = await self.workflow.ainvoke(initial_state)

            # 转换结果为AgentState对象
            if isinstance(workflow_result, dict):
                final_state = AgentState(
                    user_query=workflow_result.get("user_query", user_query),
                    investment_debate_state=workflow_result.get(
                        "investment_debate_state", {}
                    ),
                    risk_debate_state=workflow_result.get("risk_debate_state", {}),
                    messages=workflow_result.get("messages", []),
                    market_report=workflow_result.get("market_report", ""),
                    sentiment_report=workflow_result.get("sentiment_report", ""),
                    news_report=workflow_result.get("news_report", ""),
                    fundamentals_report=workflow_result.get("fundamentals_report", ""),
                    shareholder_report=workflow_result.get("shareholder_report", ""),
                    investment_plan=workflow_result.get("investment_plan", ""),
                    trader_investment_plan=workflow_result.get(
                        "trader_investment_plan", ""
                    ),
                    final_trade_decision=workflow_result.get(
                        "final_trade_decision", ""
                    ),
                    errors=workflow_result.get("errors", []),
                    warnings=workflow_result.get("warnings", []),
                    agent_execution_history=workflow_result.get(
                        "agent_execution_history", []
                    ),
                    mcp_tool_calls=workflow_result.get("mcp_tool_calls", []),
                )
            else:
                final_state = workflow_result

            print("✅ 分析流程完成")

            # 记录最终结果
            if self.progress_manager:
                final_results = {
                    "final_state": self._state_to_dict(final_state),
                    "completion_time": datetime.now().isoformat(),
                    "success": True,
                }
                self.progress_manager.set_final_results(final_results)
                self.progress_manager.log_workflow_completion({"success": True})

            if self.verbose_logging:
                self._log_analysis_summary(final_state)

            return final_state

        except asyncio.CancelledError as e:
            print(f"⚠️ 分析流程已取消: {e}")
            if self.progress_manager:
                self.progress_manager.add_warning("分析已被用户取消")
                self.progress_manager.session_data["status"] = "cancelled"
                self.progress_manager._save_json()
                self.progress_manager.log_workflow_completion(
                    {"success": False, "cancelled": True}
                )
            return initial_state

        except Exception as e:
            print(f"❌ 分析流程失败: {e}")
            if self.progress_manager:
                self.progress_manager.add_error(str(e))
                self.progress_manager.log_workflow_completion({"success": False})
            return initial_state

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _state_to_dict(self, state):
        """
        将AgentState对象转换为字典

        用于序列化和日志记录。
        """
        if isinstance(state, dict):
            return state

        state_dict = {}
        for attr in dir(state):
            if not attr.startswith("_") and not callable(getattr(state, attr)):
                try:
                    value = getattr(state, attr)
                    if isinstance(
                        value, (str, int, float, bool, list, dict, type(None))
                    ):
                        state_dict[attr] = value
                    else:
                        state_dict[attr] = str(value)
                except Exception:
                    continue
        return state_dict

    def _log_analysis_summary(self, state):
        """记录分析摘要"""
        print("\n" + "=" * 50)
        print("分析流程摘要")
        print("=" * 50)

        if isinstance(state, dict):
            user_query = state.get("user_query", "")
            agent_execution_history = state.get("agent_execution_history", [])
            mcp_tool_calls = state.get("mcp_tool_calls", [])
            errors = state.get("errors", [])
            warnings = state.get("warnings", [])
        else:
            user_query = state.user_query
            agent_execution_history = state.agent_execution_history
            mcp_tool_calls = state.mcp_tool_calls
            errors = state.errors
            warnings = state.warnings

        print(f"用户问题: {user_query}")
        print(f"智能体执行次数: {len(agent_execution_history)}")
        print(f"MCP工具调用次数: {len(mcp_tool_calls)}")

        if errors:
            print(f"错误数量: {len(errors)}")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print(f"警告数量: {len(warnings)}")
            for warning in warnings:
                print(f"  - {warning}")

        print("=" * 50)

    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        return {
            "agents_count": len(self.agents),
            "max_debate_rounds": self.max_debate_rounds,
            "max_risk_debate_rounds": self.max_risk_debate_rounds,
            "debug_mode": self.debug_mode,
            "verbose_logging": self.verbose_logging,
            "mcp_tools_info": self.mcp_manager.get_tools_info(),
            "agents_info": {
                name: agent.get_agent_info() for name, agent in self.agents.items()
            },
        }

    def get_agent_permissions(self) -> Dict[str, bool]:
        """获取智能体MCP权限配置"""
        return self.mcp_manager.agent_permissions

    def get_enabled_agents(self) -> List[str]:
        """获取启用MCP工具的智能体列表"""
        return self.mcp_manager.get_enabled_agents()

    async def close(self):
        """关闭工作流，释放资源"""
        await self.mcp_manager.close()
        print("工作流编排器已关闭")

    def set_debate_rounds(
        self, investment_rounds: Optional[int] = None, risk_rounds: Optional[int] = None
    ):
        """
        设置辩论轮次

        Args:
            investment_rounds: 投资辩论轮次
            risk_rounds: 风险辩论轮次
        """
        if isinstance(investment_rounds, int) and investment_rounds >= 0:
            self.max_debate_rounds = investment_rounds
            print(f"🌀 投资辩论轮次: {investment_rounds}")
        if isinstance(risk_rounds, int) and risk_rounds >= 0:
            self.max_risk_debate_rounds = risk_rounds
            print(f"🌀 风险辩论轮次: {risk_rounds}")

    def set_active_agents(self, active_agents: List[str]):
        """设置本轮启用的智能体"""
        if not active_agents:
            self.active_agents = set(self.agents.keys())
        else:
            self.active_agents = set([a for a in active_agents if a in self.agents])

    def _is_active(self, agent_name: str) -> bool:
        """检查智能体是否启用"""
        return (not self.active_agents) or (agent_name in self.active_agents)

    def _skip_agent(self, agent_name: str):
        """记录跳过的智能体"""
        try:
            if self.progress_manager:
                self.progress_manager.add_warning(
                    f"智能体已禁用，本轮跳过", agent_name=agent_name
                )
        except Exception:
            pass

    def _increment_investment_round(self, state: AgentState):
        """增加投资辩论轮次计数"""
        try:
            if isinstance(state, dict):
                inv = state.get("investment_debate_state", {})
                inv["count"] = int(inv.get("count", 0)) + 1
                state["investment_debate_state"] = inv
            else:
                inv = getattr(state, "investment_debate_state", {}) or {}
                inv["count"] = int(inv.get("count", 0)) + 1
                state.investment_debate_state = inv
        except Exception:
            pass

    def _increment_risk_round(self, state: AgentState):
        """增加风险辩论轮次计数"""
        try:
            if isinstance(state, dict):
                rsk = state.get("risk_debate_state", {})
                rsk["count"] = int(rsk.get("count", 0)) + 1
                state["risk_debate_state"] = rsk
            else:
                rsk = getattr(state, "risk_debate_state", {}) or {}
                rsk["count"] = int(rsk.get("count", 0)) + 1
                state.risk_debate_state = rsk
        except Exception:
            pass
