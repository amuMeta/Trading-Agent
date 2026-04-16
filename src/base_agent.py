"""
Base Agent 模块 - 所有智能体的基类

本模块定义了所有智能体的通用行为：
1. 与MCPManager交互获取工具
2. 调用LLM进行推理
3. 处理MCP工具调用
4. 管理执行状态和错误处理

每个具体智能体（如MarketAnalyst、BullResearcher）都继承自此类，
并实现get_system_prompt()和process()方法。

调用流程：
WorkflowOrchestrator → Agent.process() → BaseAgent.call_llm_with_context()
                                        ↓
                               MCPManager.get_tools_for_agent()
                                        ↓
                               ReAct Agent (create_react_agent)
                                        ↓
                               LLM + MCP Tools → 分析结果
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from .agent_states import AgentState
from .mcp_manager import MCPManager


class BaseAgent(ABC):
    """
    基础智能体类
    
    所有具体智能体的父类，提供通用功能：
    - MCP工具管理
    - LLM调用封装
    - 上下文构建
    - 错误处理
    
    子类必须实现：
    - get_system_prompt(): 返回该智能体的系统提示词
    - process(): 实现该智能体的处理逻辑
    """
    
    def __init__(
        self, agent_name: str, mcp_manager: MCPManager, role_description: str = ""
    ):
        """
        初始化基础智能体
        
        Args:
            agent_name: 智能体名称，用于标识和权限控制
            mcp_manager: MCP管理器实例，用于获取工具和LLM
            role_description: 角色描述（供子类使用）
        """
        self.agent_name = agent_name
        self.mcp_manager = mcp_manager
        self.role_description = role_description
        
        # 从MCPManager获取共享的LLM实例
        self.llm = mcp_manager.llm
        
        # 检查该智能体是否被授权使用MCP工具
        self.mcp_enabled = mcp_manager.is_agent_mcp_enabled(agent_name)
        
        # 可用工具列表（延迟初始化）
        self.available_tools = []
        
        # ReAct智能体实例（延迟创建）
        self.agent = None
        
        print(
            f"智能体 {agent_name} 初始化完成，MCP工具: {'启用' if self.mcp_enabled else '禁用'}"
        )
    
    def ensure_agent_created(self):
        """
        确保ReAct智能体实例已创建
        
        由于MCP工具在运行时才初始化，智能体实例也延迟创建。
        此方法在首次调用LLM前确保智能体已创建。
        """
        if self.agent is None:
            self.agent = self.mcp_manager.create_agent_with_tools(self.agent_name)
            print(f"智能体 {self.agent_name} 实例创建完成")
    
    @abstractmethod
    def get_system_prompt(self, state: AgentState) -> str:
        """
        获取系统提示词
        
        子类必须实现此方法，返回定义该智能体角色和行为的提示词。
        
        Args:
            state: 当前工作流状态
            
        Returns:
            str: 系统提示词
        """
        pass
    
    @abstractmethod
    async def process(self, state: AgentState, progress_tracker=None) -> AgentState:
        """
        处理智能体逻辑
        
        子类必须实现此方法，定义该智能体如何处理输入并生成输出。
        
        Args:
            state: 当前工作流状态
            progress_tracker: 进度跟踪器（可选）
            
        Returns:
            AgentState: 更新后的状态
        """
        pass
    
    # =========================================================================
    # 上下文构建
    # =========================================================================
    
    def build_context_prompt(self, state: AgentState) -> str:
        """
        构建上下文提示词（用于研究员、管理层、风险分析师）
        
        这些智能体需要看到：
        - 用户原始问题
        - 所有7个分析师的报告
        - 辩论历史
        - 投资计划
        
        Args:
            state: 当前工作流状态
            
        Returns:
            str: 格式化的上下文提示词
        """
        context_parts = []
        
        # 添加当前日期时间信息（帮助LLM理解时间上下文）
        current_datetime = datetime.now()
        context_parts.append(
            f"当前日期时间: {current_datetime.strftime('%Y年%m月%d日 %H:%M:%S')} ({current_datetime.strftime('%A')})"
        )
        
        # 处理状态可能是字典或AgentState对象
        if isinstance(state, dict):
            user_query = state.get("user_query", "")
            investment_plan = state.get("investment_plan", "")
            trader_investment_plan = state.get("trader_investment_plan", "")
            
            # 获取所有报告
            reports = {
                "company_overview_report": state.get("company_overview_report", ""),
                "market_report": state.get("market_report", ""),
                "sentiment_report": state.get("sentiment_report", ""),
                "news_report": state.get("news_report", ""),
                "fundamentals_report": state.get("fundamentals_report", ""),
                "shareholder_report": state.get("shareholder_report", ""),
                "product_report": state.get("product_report", ""),
            }
            
            # 获取辩论历史
            investment_debate_state = state.get("investment_debate_state", {})
            risk_debate_state = state.get("risk_debate_state", {})
            investment_history = investment_debate_state.get("history", "")
            risk_history = risk_debate_state.get("history", "")
            
            debate_summary = ""
            if investment_history:
                debate_summary += f"投资辩论历史:\n{investment_history}\n\n"
            if risk_history:
                debate_summary += f"风险管理辩论历史:\n{risk_history}\n\n"
            debate_summary = debate_summary.strip()
        else:
            user_query = state.user_query
            investment_plan = state.investment_plan
            trader_investment_plan = state.trader_investment_plan
            reports = state.get_all_reports()
            debate_summary = state.get_debate_summary()
        
        # 基础信息
        context_parts.append(f"用户问题: {user_query}")
        
        # 分析师报告（只添加非空的）
        for report_name, report_content in reports.items():
            if report_content.strip():
                context_parts.append(f"{report_name}: {report_content}")
        
        # 辩论历史
        if debate_summary:
            context_parts.append(f"辩论历史:\n{debate_summary}")
        
        # 投资计划
        if investment_plan:
            context_parts.append(f"研究经理决策: {investment_plan}")
        
        # 交易员计划
        if trader_investment_plan:
            context_parts.append(f"交易员计划: {trader_investment_plan}")
        
        return "\n\n".join(context_parts)
    
    def build_analyst_context_prompt(self, state: AgentState) -> str:
        """
        构建分析师上下文提示词
        
        分析师只需要看到：
        - 用户原始问题
        - 公司基础信息（由CompanyOverviewAnalyst预先获取）
        
        分析师不直接获取其他分析师的报告，避免信息重复。
        
        Args:
            state: 当前工作流状态
            
        Returns:
            str: 格式化的上下文提示词
        """
        context_parts = []
        
        # 添加当前日期时间
        current_datetime = datetime.now()
        context_parts.append(
            f"当前日期时间: {current_datetime.strftime('%Y年%m月%d日 %H:%M:%S')} ({current_datetime.strftime('%A')})"
        )
        
        # 处理状态
        if isinstance(state, dict):
            user_query = state.get("user_query", "")
            company_details = state.get("company_details", "")
        else:
            user_query = state.user_query
            company_details = state.company_details
        
        # 基础信息
        context_parts.append(f"用户问题: {user_query}")
        
        # 公司基础信息（仅供分析师使用）
        if company_details.strip():
            context_parts.append(f"公司基础信息: {company_details}")
        
        return "\n\n".join(context_parts)
    
    # =========================================================================
    # LLM调用
    # =========================================================================
    
    async def call_llm_with_context(
        self, state: AgentState, user_message: str, progress_tracker=None
    ) -> str:
        """
        调用LLM并处理上下文
        
        这是智能体的核心方法，处理完整的LLM调用流程：
        1. 确保智能体实例已创建
        2. 构建系统提示和上下文
        3. 选择调用方式（MCP工具 / HTTP回退 / 无工具）
        4. 处理工具调用结果
        5. 返回分析结果
        
        Args:
            state: 当前工作流状态
            user_message: 用户消息/任务描述
            progress_tracker: 进度跟踪器
            
        Returns:
            str: LLM生成的分析结果
        """
        try:
            # 确保智能体实例已创建
            self.ensure_agent_created()
            
            # 记录开始执行
            if progress_tracker:
                should_start_new = True
                if hasattr(progress_tracker, "session_data"):
                    for agent in progress_tracker.session_data.get("agents", []):
                        if (
                            agent.get("agent_name") == self.agent_name
                            and agent.get("status") == "running"
                        ):
                            should_start_new = False
                            break
                
                if should_start_new:
                    if hasattr(progress_tracker, "start_agent"):
                        system_prompt = self.get_system_prompt(state)
                        # 全局输出格式要求：连续段落，不使用标题符号
                        system_prompt = (
                            system_prompt
                            + "\n\n输出格式要求：请将本次输出写成一篇完整的说明文，使用连续段落表述，不要使用标题符号（如##）、项目符号或编号，保持逻辑清晰、语言连贯。若需输出代码/伪代码，可使用代码块，不受上述限制。"
                        )
                        is_analyst = self.agent_name.endswith("_analyst")
                        if is_analyst:
                            context_prompt = self.build_analyst_context_prompt(state)
                        else:
                            context_prompt = self.build_context_prompt(state)
                        
                        progress_tracker.start_agent(
                            agent_name=self.agent_name,
                            action=f"分析: {user_message}",
                            system_prompt=system_prompt,
                            user_prompt=user_message,
                            context=context_prompt,
                        )
            
            print(f"🤖 [{self.agent_name}] 开始分析...")
            
            # 构建提示词
            system_prompt = self.get_system_prompt(state)
            system_prompt = (
                system_prompt
                + "\n\n输出格式要求：请将本次输出写成一篇完整的说明文，使用连续段落表述，不要使用标题符号（如##）、项目符号或编号，保持逻辑清晰、语言连贯。若需输出代码/伪代码，可使用代码块，不受上述限制。"
            )
            
            is_analyst = self.agent_name.endswith("_analyst")
            if is_analyst:
                context_prompt = self.build_analyst_context_prompt(state)
            else:
                context_prompt = self.build_context_prompt(state)
            
            system_level_prompt = f"""{system_prompt}

{context_prompt}"""
            
            # 获取当前可用工具
            current_tools = (
                self.mcp_manager.get_tools_for_agent(self.agent_name)
                if self.mcp_enabled
                else []
            )
            
            # 检查模型是否支持ReAct工具调用
            model_name = str(
                getattr(self.llm, "model", getattr(self.llm, "model_name", ""))
            ).lower()
            react_tool_supported = not model_name.startswith("deepseek")
            
            print(
                f"[LLM CALL] agent={self.agent_name}, model={getattr(self.llm, 'model', getattr(self.llm, 'model_name', None))}, "
                f"mcp_enabled={self.mcp_enabled}, tools_count={len(current_tools)}"
            )
            
            # 模式1：使用MCP工具的ReAct模式
            if (
                self.mcp_enabled
                and current_tools
                and self.mcp_manager.client
                and react_tool_supported
            ):
                print(f"⚡ [{self.agent_name}] 正在调用LLM（带MCP工具）...")
                
                try:
                    messages = [
                        {"role": "system", "content": system_level_prompt},
                        {"role": "user", "content": user_message},
                    ]
                    
                    # 调用ReAct智能体（会自动处理工具调用循环）
                    response = await self.agent.ainvoke({"messages": messages})
                    
                    # 解析工具调用信息
                    messages = response.get("messages", [])
                    tool_calls_found = []
                    
                    for msg in messages:
                        # 工具调用请求
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tool_name = tool_call.get("name", "unknown")
                                tool_args = tool_call.get("args", {})
                                tool_id = tool_call.get("id", "unknown")
                                
                                print(f"🔧 [{self.agent_name}] 调用工具: {tool_name}")
                                
                                tool_calls_found.append({
                                    "tool_name": tool_name,
                                    "tool_args": tool_args,
                                    "tool_id": tool_id,
                                })
                        
                        # 工具返回结果
                        elif hasattr(msg, "tool_call_id"):
                            tool_result = getattr(msg, "content", "No result")
                            print(f"📋 [{self.agent_name}] 工具返回: {str(tool_result)[:200]}...")
                            
                            # 记录工具调用
                            for tool_call in tool_calls_found:
                                if tool_call.get("tool_id") == getattr(msg, "tool_call_id", None):
                                    if progress_tracker:
                                        progress_tracker.add_mcp_tool_call(
                                            agent_name=self.agent_name,
                                            tool_name=tool_call["tool_name"],
                                            tool_args=tool_call["tool_args"],
                                            tool_result=tool_result,
                                        )
                                    
                                    # 记录到state
                                    if isinstance(state, dict):
                                        if "mcp_tool_calls" not in state:
                                            state["mcp_tool_calls"] = []
                                        state["mcp_tool_calls"].append({
                                            "agent_name": self.agent_name,
                                            "tool_name": tool_call["tool_name"],
                                            "tool_args": tool_call["tool_args"],
                                            "tool_result": str(tool_result),
                                            "timestamp": datetime.now().isoformat(),
                                        })
                                    else:
                                        state.add_mcp_tool_call(
                                            agent_name=self.agent_name,
                                            tool_name=tool_call["tool_name"],
                                            tool_args=tool_call["tool_args"],
                                            tool_result=tool_result,
                                        )
                    
                    # 提取最终回复
                    if messages:
                        final_message = messages[-1]
                        if hasattr(final_message, "content"):
                            result = final_message.content
                        else:
                            result = "(无法提取内容)"
                    else:
                        result = "(未收到消息)"
                
                except Exception as mcp_error:
                    error_msg = str(mcp_error)
                    print(f"⚠️ [{self.agent_name}] MCP工具调用失败: {error_msg}")
                    
                    # 尝试HTTP回退
                    if "messages[" in error_msg and "invalid type" in error_msg:
                        print(f"🔄 [{self.agent_name}] 尝试通过HTTP API获取数据...")
                        try:
                            http_result = await self._call_http_fallback(user_message)
                            if http_result and _check_http_result_valid(http_result):
                                http_context = f"基于以下实时数据进行分析：\n{str(http_result)[:3000]}\n\n"
                                full_prompt = f"{http_context}{system_level_prompt}\n\n用户请求: {user_message}"
                                response = await self.llm.ainvoke([HumanMessage(content=full_prompt)])
                                result = response.content
                            else:
                                raise Exception("HTTP调用返回空结果")
                        except Exception as http_error:
                            print(f"❌ [{self.agent_name}] HTTP调用也失败: {http_error}")
                            result = await self._fallback_to_no_tool(user_message, system_level_prompt)
                    else:
                        result = await self._fallback_to_no_tool(user_message, system_level_prompt)
            
            # 模式2：HTTP回退模式（不支持ReAct的模型如DeepSeek）
            elif self.mcp_enabled and current_tools and not react_tool_supported:
                print(f"⚠️ [{self.agent_name}] 当前模型 {model_name} 不支持ReAct，改用HTTP回退")
                try:
                    http_result = await self._call_http_fallback(user_message)
                    if http_result and _check_http_result_valid(http_result):
                        http_context = f"基于以下实时数据进行分析：\n{str(http_result)[:3000]}\n\n"
                        full_prompt = f"{http_context}{system_level_prompt}\n\n用户请求: {user_message}"
                        response = await self.llm.ainvoke([HumanMessage(content=full_prompt)])
                        result = response.content
                    else:
                        result = await self._fallback_to_no_tool(user_message, system_level_prompt)
                except Exception as http_error:
                    print(f"❌ [{self.agent_name}] HTTP回退失败: {http_error}")
                    result = await self._fallback_to_no_tool(user_message, system_level_prompt)
            
            # 模式3：无工具模式
            else:
                print(f"⚡ [{self.agent_name}] 正在调用LLM（无工具）...")
                full_prompt = f"""{system_level_prompt}\n\n用户请求: {user_message}"""
                response = await self.llm.ainvoke([HumanMessage(content=full_prompt)])
                result = response.content
                
                # 记录执行
                if isinstance(state, dict):
                    if "agent_executions" not in state:
                        state["agent_executions"] = []
                    state["agent_executions"].append({
                        "agent_name": self.agent_name,
                        "action": "LLM调用(无工具)",
                        "result": result,
                        "mcp_used": False,
                    })
                else:
                    state.add_agent_execution(
                        agent_name=self.agent_name,
                        action="LLM调用(无工具)",
                        result=result,
                        mcp_used=False,
                    )
            
            print(f"✅ [{self.agent_name}] 分析完成，结果长度: {len(result)} 字符")
            
            # 记录执行完成
            if progress_tracker:
                if hasattr(progress_tracker, "complete_agent"):
                    progress_tracker.complete_agent(self.agent_name, result, True)
            
            return result
            
        except Exception as e:
            error_msg = f"LLM调用失败: {str(e)}"
            print(f"❌ 智能体 {self.agent_name} - {error_msg}")
            
            if progress_tracker:
                if hasattr(progress_tracker, "complete_agent"):
                    progress_tracker.complete_agent(self.agent_name, error_msg, False)
            
            if isinstance(state, dict):
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append(f"{self.agent_name}: {error_msg}")
            else:
                state.add_error(f"{self.agent_name}: {error_msg}")
            return f"抱歉，处理过程中出现错误: {error_msg}"
    
    async def _fallback_to_no_tool(self, user_message: str, system_prompt: str) -> str:
        """
        回退到无工具模式
        
        当MCP工具不可用时，直接使用LLM生成分析。
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            
        Returns:
            str: LLM生成的结果
        """
        print(f"⚡ [{self.agent_name}] 回退到无工具模式...")
        full_prompt = f"""{system_prompt}\n\n用户请求: {user_message}"""
        response = await self.llm.ainvoke([HumanMessage(content=full_prompt)])
        return response.content
    
    async def _call_http_fallback(self, user_message: str) -> Dict:
        """
        HTTP回退模式：通过直接调用MCP HTTP API获取数据
        
        根据智能体类型调用不同的工具获取数据：
        - MarketAnalyst: K线数据、技术指标
        - NewsAnalyst: 新闻数据
        - FundamentalsAnalyst: 财务报表、估值指标
        - ...
        
        Args:
            user_message: 用户消息（从中提取股票代码）
            
        Returns:
            Dict: 获取到的数据
        """
        import re
        
        # 从用户消息中提取股票代码
        symbol = ""
        stock_patterns = [
            r"(\d{6})",      # A股代码 600519
            r"(SSE:\d{6})",  # 上交所
            r"(SZSE:\d{6})",  # 深交所
            r"(NASDAQ:[A-Za-z]+)",  # 美股
            r"([A-Za-z]+)",  # 股票名称
        ]
        
        for pattern in stock_patterns:
            match = re.search(pattern, user_message)
            if match:
                symbol = match.group(1)
                break
        
        if not symbol:
            return {"error": "无法从消息中提取股票代码"}
        
        # A股数字代码添加交易所前缀
        if symbol.isdigit():
            symbol = f"SSE:{symbol}"
        
        # 根据智能体类型调用不同工具
        result = {}
        
        if "market" in self.agent_name or "技术" in self.role_description:
            # 市场分析师：K线数据和技术指标
            try:
                kline = self.mcp_manager.call_tool_via_http(
                    "get_kline_data", {"symbol": symbol, "period": "30d"}
                )
                if _check_http_result_valid(kline):
                    result["kline"] = kline
            except:
                pass
            
            try:
                tech = self.mcp_manager.call_tool_via_http(
                    "get_technical_indicators", {"symbol": symbol, "period": "30d"}
                )
                if _check_http_result_valid(tech):
                    result["technical"] = tech
            except:
                pass
        
        elif "sentiment" in self.agent_name or "情绪" in self.role_description:
            # 情绪分析师：新闻数据
            try:
                news = self.mcp_manager.call_tool_via_http(
                    "get_stock_news", {"symbol": symbol, "days_back": 7, "limit": 10}
                )
                if _check_http_result_valid(news):
                    result["news"] = news
            except:
                pass
        
        elif "news" in self.agent_name:
            # 新闻分析师：新闻数据
            try:
                news = self.mcp_manager.call_tool_via_http(
                    "get_stock_news", {"symbol": symbol, "days_back": 7, "limit": 10}
                )
                if _check_http_result_valid(news):
                    result["news"] = news
            except:
                pass
        
        elif "fundament" in self.agent_name or "基本面" in self.role_description:
            # 基本面分析师：财务数据和估值
            try:
                fin = self.mcp_manager.call_tool_via_http(
                    "get_financial_reports", {"symbol": symbol}
                )
                if _check_http_result_valid(fin):
                    result["financial"] = fin
            except:
                pass
            
            try:
                val = self.mcp_manager.call_tool_via_http(
                    "get_valuation_metrics", {"symbol": symbol}
                )
                if _check_http_result_valid(val):
                    result["valuation"] = val
            except:
                pass
        
        elif "shareholder" in self.agent_name or "股东" in self.role_description:
            # 股东分析师：资金流向
            try:
                mf = self.mcp_manager.call_tool_via_http(
                    "get_money_flow", {"symbol": symbol, "days": 20}
                )
                if _check_http_result_valid(mf):
                    result["money_flow"] = mf
            except:
                pass
        
        elif "product" in self.agent_name or "产品" in self.role_description:
            # 产品分析师：公司信息
            try:
                info = self.mcp_manager.call_tool_via_http(
                    "get_asset_info", {"symbol": symbol}
                )
                if _check_http_result_valid(info):
                    result["asset_info"] = info
            except:
                pass
        
        elif "overview" in self.agent_name or "公司概述" in self.role_description:
            # 公司概述分析师：基本信息和新闻
            try:
                info = self.mcp_manager.call_tool_via_http(
                    "get_asset_info", {"symbol": symbol}
                )
                if _check_http_result_valid(info):
                    result["asset_info"] = info
            except:
                pass
            
            try:
                news = self.mcp_manager.call_tool_via_http(
                    "get_stock_news", {"symbol": symbol, "days_back": 7, "limit": 5}
                )
                if _check_http_result_valid(news):
                    result["news"] = news
            except:
                pass
        
        return result if result else {"error": "HTTP调用未返回有效数据"}
    
    # =========================================================================
    # MCP工具直接调用
    # =========================================================================
    
    async def call_mcp_tool(
        self, state: AgentState, tool_name: str, tool_args: Dict
    ) -> Any:
        """
        显式调用MCP工具
        
        用于智能体需要主动调用特定工具的场景。
        
        Args:
            state: 当前工作流状态
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            Any: 工具执行结果
        """
        if not self.mcp_enabled:
            error_msg = f"智能体 {self.agent_name} 未启用MCP工具"
            print(f"⚠️ {error_msg}")
            if isinstance(state, dict):
                if "warnings" not in state:
                    state["warnings"] = []
                state["warnings"].append(error_msg)
            else:
                state.add_warning(error_msg)
            return {"error": error_msg}
        
        try:
            print(f"🔧 [{self.agent_name}] 准备调用工具: {tool_name}")
            
            result = await self.mcp_manager.call_tool_for_agent(
                agent_name=self.agent_name, tool_name=tool_name, tool_args=tool_args
            )
            
            # 记录工具调用
            if isinstance(state, dict):
                if "mcp_tool_calls" not in state:
                    state["mcp_tool_calls"] = []
                state["mcp_tool_calls"].append({
                    "agent_name": self.agent_name,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_result": result,
                })
            else:
                state.add_mcp_tool_call(
                    agent_name=self.agent_name,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_result=result,
                )
            
            print(f"✅ [{self.agent_name}] 工具 {tool_name} 调用成功")
            return result
            
        except Exception as e:
            error_msg = f"MCP工具调用失败: {str(e)}"
            print(f"❌ [{self.agent_name}] {error_msg}")
            if isinstance(state, dict):
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append(f"{self.agent_name}: {error_msg}")
            else:
                state.add_error(f"{self.agent_name}: {error_msg}")
            return {"error": error_msg}
    
    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取智能体信息
        
        Returns:
            Dict: 智能体名称、角色、工具使用情况等
        """
        return {
            "name": self.agent_name,
            "role_description": self.role_description,
            "mcp_enabled": self.mcp_enabled,
            "available_tools_count": len(self.available_tools),
            "available_tools": [tool.name for tool in self.available_tools]
            if self.available_tools
            else [],
        }
    
    def validate_state(self, state: AgentState) -> bool:
        """
        验证状态有效性
        
        Args:
            state: 待验证的状态
            
        Returns:
            bool: 状态是否有效
        """
        if isinstance(state, dict):
            user_query = state.get("user_query", "")
            if not user_query:
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append(f"{self.agent_name}: 缺少用户查询信息")
                return False
        else:
            if not state.user_query:
                state.add_error(f"{self.agent_name}: 缺少用户查询信息")
                return False
        return True
    
    def format_output(self, content: str, state: AgentState) -> str:
        """
        格式化输出内容
        
        Args:
            content: 原始内容
            state: 当前状态
            
        Returns:
            str: 格式化后的内容
        """
        from datetime import datetime
        
        if isinstance(state, dict):
            user_query = state.get("user_query", "")
        else:
            user_query = state.user_query
        
        formatted_content = f"""
=== {self.agent_name} 分析报告 ===
时间: {datetime.now().strftime("%Y%m%d %H:%M:%S")}
用户问题: {user_query}
MCP工具: {"启用" if self.mcp_enabled else "禁用"}

{content}

=== 报告结束 ===
"""
        return formatted_content.strip()


def _check_http_result_valid(result: Dict) -> bool:
    """
    检查HTTP结果是否有效
    
    Args:
        result: HTTP响应结果
        
    Returns:
        bool: 结果是否有效（非空、无错误）
    """
    if not isinstance(result, dict):
        return False
    if "error" in result and result["error"]:
        return False
    if "code" in result and result.get("code") != 0:
        return False
    if "data" in result:
        data = result["data"]
        if isinstance(data, dict) and "error" in data:
            return False
        if isinstance(data, dict) and not data:
            return False
        if data is None:
            return False
    return True
