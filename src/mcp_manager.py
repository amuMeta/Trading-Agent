"""
MCP Manager 模块 - MCP工具连接管理和智能体权限控制

MCP (Model Context Protocol) 是一种标准化协议，用于连接AI模型与外部工具。
本模块负责：
1. 从mcp_config.json加载MCP服务器配置
2. 使用langchain-mcp-adapters连接MCP服务器
3. 发现并管理可用的MCP工具
4. 控制每个智能体对MCP工具的访问权限
5. 提供HTTP回退模式（直接调用MCP API）

调用流程：
BaseAgent → MCPManager.get_tools_for_agent() → MultiServerMCPClient → stock-mcp服务
"""

import os
import json
import asyncio
import time
from typing import Dict, Any, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv


class MCPManager:
    """
    MCP工具管理器

    核心职责：
    - 管理MCP服务器连接
    - 工具发现和缓存
    - 智能体权限控制
    - LLM实例管理
    """

    def __init__(self, config_file: str = "mcp_config.json"):
        """
        初始化MCP管理器

        Args:
            config_file: MCP配置文件路径，默认为mcp_config.json
        """
        # 加载.env环境变量
        load_dotenv()

        # 加载MCP服务器配置
        self.config = self._load_config(config_file)

        # 初始化大语言模型（所有智能体共用）
        self.llm = self._init_llm()

        # MCP客户端（连接MCP服务器）
        self.client: Optional[MultiServerMCPClient] = None

        # 缓存的工具列表
        self.tools: List = []
        self.tools_by_server: Dict[str, List] = {}  # 按服务器分组

        # 从环境变量加载智能体MCP权限配置
        self.agent_permissions = self._load_agent_permissions()

        # 对话历史（可选，用于上下文增强）
        self.conversation_history: List[Dict[str, str]] = []

        # HTTP客户端（用于直接调用stock-mcp API，作为MCP的备用方案）
        try:
            from src.tools.http_client import StockMCPHTTPClient

            self.http_client = StockMCPHTTPClient()
            print("✅ HTTP客户端初始化成功")
        except Exception as e:
            print(f"⚠️ HTTP客户端初始化失败: {e}")
            self.http_client = None

        print("MCP管理器初始化完成")

    # =========================================================================
    # 配置加载
    # =========================================================================

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """
        加载MCP配置文件

        Args:
            config_file: 配置文件路径

        Returns:
            Dict: 解析后的配置对象
        """
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"配置文件加载成功: {config_file}")
            return config
        except FileNotFoundError:
            print(f"⚠️ 配置文件未找到: {config_file}，使用默认配置")
            return {"servers": {}, "agent_permissions": {}}
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件格式错误: {e}")
            return {"servers": {}, "agent_permissions": {}}

    def _init_llm(self) -> ChatOpenAI:
        """
        初始化大语言模型

        模型配置从环境变量读取：
        - LLM_API_KEY: API密钥
        - LLM_BASE_URL: API地址（支持代理）
        - LLM_MODEL: 模型名称
        - LLM_TEMPERATURE: 生成温度
        - LLM_MAX_TOKENS: 最大token数

        Returns:
            ChatOpenAI: 配置好的LLM实例
        """
        api_key = os.getenv(
            "OPENAI_API_KEY", os.getenv("LLM_API_KEY", "your_api_key_here")
        )
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        model_name = os.getenv("LLM_MODEL", "gpt-4")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))

        print(
            f"[LLM INIT] 配置 -> model={model_name}, temperature={temperature}, max_tokens={max_tokens}"
        )

        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        print(f"大模型初始化完成: {model_name} @ {base_url}")
        return llm

    def _load_agent_permissions(self) -> Dict[str, bool]:
        """
        从环境变量加载智能体MCP工具使用权限

        每个智能体是否可以使用MCP工具，由环境变量控制。
        分析师团队默认启用MCP（获取实时数据），
        研究员/管理层默认禁用（专注综合分析）。

        环境变量格式：{智能体名称}_MCP=true/false

        Returns:
            Dict[str, bool]: 智能体名称 -> 是否启用MCP
        """
        permissions = {}

        # 智能体名称到环境变量名的映射
        env_mapping = {
            "company_overview_analyst": "COMPANY_OVERVIEW_ANALYST_MCP",
            "market_analyst": "MARKET_ANALYST_MCP",
            "sentiment_analyst": "SENTIMENT_ANALYST_MCP",
            "news_analyst": "NEWS_ANALYST_MCP",
            "fundamentals_analyst": "FUNDAMENTALS_ANALYST_MCP",
            "shareholder_analyst": "SHAREHOLDER_ANALYST_MCP",
            "product_analyst": "PRODUCT_ANALYST_MCP",
            "bull_researcher": "BULL_RESEARCHER_MCP",
            "bear_researcher": "BEAR_RESEARCHER_MCP",
            "research_manager": "RESEARCH_MANAGER_MCP",
            "trader": "TRADER_MCP",
            "aggressive_risk_analyst": "AGGRESSIVE_RISK_ANALYST_MCP",
            "safe_risk_analyst": "SAFE_RISK_ANALYST_MCP",
            "neutral_risk_analyst": "NEUTRAL_RISK_ANALYST_MCP",
            "risk_manager": "RISK_MANAGER_MCP",
        }

        for agent_name, env_var in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 环境变量设置为true/false字符串
                permissions[agent_name] = env_value.lower() == "true"
            else:
                # 未设置默认禁用
                permissions[agent_name] = False

        print(f"智能体权限配置从环境变量加载完成: {permissions}")
        return permissions

    # =========================================================================
    # MCP连接管理
    # =========================================================================

    async def initialize(self, mcp_config: Optional[Dict] = None) -> bool:
        """
        初始化MCP客户端并连接服务器

        这是异步方法，需要在应用启动时调用。
        会连接配置的MCP服务器并获取可用工具列表。

        Args:
            mcp_config: 可选的MCP配置，覆盖文件配置

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 如果已有连接，先关闭
            if self.client:
                await self.close()

            # 获取服务器配置（支持两种格式：mcpServers 或 servers）
            config = mcp_config or self.config.get(
                "mcpServers", self.config.get("servers", {})
            )
            if not config:
                print("⚠️ 未找到MCP服务器配置，跳过MCP初始化")
                return False

            print(f"📡 MCP配置内容: {config}")

            # 创建MCP客户端
            self.client = MultiServerMCPClient(config)
            self.server_configs = config

            # 逐个获取各服务器的工具
            print("🔧 正在逐个获取服务器工具...")
            all_tools = []
            tools_by_server = {}

            for server_name in self.server_configs.keys():
                try:
                    print(f"─── 正在从服务器 '{server_name}' 获取工具 ───")

                    # 抑制MCP客户端的SSE解析错误日志
                    import logging

                    mcp_logger = logging.getLogger("mcp")
                    original_level = mcp_logger.level
                    mcp_logger.setLevel(logging.CRITICAL)

                    try:
                        # 获取该服务器的所有工具
                        server_tools = await self.client.get_tools(
                            server_name=server_name
                        )
                    finally:
                        mcp_logger.setLevel(original_level)

                    # 工具名去重和清洗
                    unique_tools = []
                    tool_names = set()

                    for tool in server_tools:
                        # 合法化工具名（去除特殊字符）
                        import re

                        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool.name)

                        # 去重检查
                        if clean_name not in tool_names:
                            tool_names.add(clean_name)
                            if clean_name != tool.name:
                                tool.name = clean_name
                            unique_tools.append(tool)
                        else:
                            print(f"⚠️ 跳过重复工具: {tool.name} -> {clean_name}")

                    tools_by_server[server_name] = unique_tools
                    all_tools.extend(unique_tools)
                    print(f"✅ 从 '{server_name}' 获取到 {len(unique_tools)} 个工具")

                except Exception as e:
                    print(f"⚠️ 从服务器 '{server_name}' 获取工具失败: {e}")
                    tools_by_server[server_name] = []

            self.tools = all_tools
            self.tools_by_server = tools_by_server
            print(f"🎉 总计发现 {len(self.tools)} 个可用工具")

            return True

        except Exception as e:
            print(f"❌ MCP客户端初始化失败: {e}")
            self.client = None
            self.tools = []
            self.tools_by_server = {}
            return False

    # =========================================================================
    # 工具访问控制
    # =========================================================================

    def get_tools_for_agent(self, agent_name: str) -> List:
        """
        获取指定智能体可用的工具列表

        根据智能体的MCP权限配置，返回该智能体可以使用的工具。
        未授权的智能体将获得空列表。

        Args:
            agent_name: 智能体名称

        Returns:
            List: 该智能体可用的MCP工具列表
        """
        # 检查权限
        if not self.agent_permissions.get(agent_name, False):
            print(f"智能体 {agent_name} 未被授权使用MCP工具")
            return []

        # 检查连接状态
        if not self.client or not self.tools:
            print(f"智能体 {agent_name} - MCP客户端未连接或无可用工具")
            return []

        # 返回所有可用工具（实际调用时由LLM决定使用哪些）
        print(f"智能体 {agent_name} 可使用 {len(self.tools)} 个MCP工具")
        return self.tools

    def create_agent_with_tools(self, agent_name: str):
        """
        为智能体创建带工具的ReAct智能体

        使用LangGraph的create_react_agent创建能够调用MCP工具的智能体。
        ReAct (Reasoning + Acting) 模式让智能体能够：
        1. 思考当前问题
        2. 决定是否调用工具
        3. 调用工具获取数据
        4. 基于工具结果继续推理

        Args:
            agent_name: 智能体名称

        Returns:
            Agent: 配置好的ReAct智能体
        """
        tools = self.get_tools_for_agent(agent_name)

        if not tools:
            # 无工具权限，返回空工具的智能体
            return create_react_agent(self.llm, [])

        # 创建带工具的智能体
        agent = create_react_agent(self.llm, tools)
        print(f"为智能体 {agent_name} 创建了带 {len(tools)} 个工具的React智能体")
        return agent

    # =========================================================================
    # HTTP回退模式
    # =========================================================================

    def call_tool_via_http(self, tool_name: str, params: Dict = None) -> Dict:
        """
        通过HTTP API直接调用stock-mcp工具

        当MCP工具调用失败时（如兼容性问题），使用HTTP方式直接调用。
        这是一种备用方案，不经过langchain-mcp-adapters。

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            Dict: 工具执行结果
        """
        if not self.http_client:
            return {"error": "HTTP客户端未初始化"}

        try:
            result = self.http_client.call_tool(tool_name, params or {})
            print(f"🔧 [HTTP] 工具 {tool_name} 调用成功")
            return result
        except Exception as e:
            print(f"❌ [HTTP] 工具 {tool_name} 调用失败: {e}")
            return {"error": str(e)}

    # =========================================================================
    # 工具信息查询
    # =========================================================================

    def get_tools_info(self) -> Dict[str, Any]:
        """
        获取工具信息摘要

        用于前端展示可用的MCP工具列表。

        Returns:
            Dict: 工具信息，包含工具名、描述、参数schema等
        """
        if not self.tools_by_server:
            return {"servers": {}, "total_tools": 0, "server_count": 0}

        servers_info = {}
        total_tools = 0

        for server_name, server_tools in self.tools_by_server.items():
            tools_info = []

            for tool in server_tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {},
                    "required": [],
                }

                # 提取工具参数schema
                try:
                    schema = None
                    if hasattr(tool, "args_schema") and tool.args_schema:
                        if isinstance(tool.args_schema, dict):
                            schema = tool.args_schema
                        elif hasattr(tool.args_schema, "model_json_schema"):
                            schema = tool.args_schema.model_json_schema()

                    if schema and isinstance(schema, dict):
                        if "properties" in schema:
                            tool_info["parameters"] = schema["properties"]
                            tool_info["required"] = schema.get("required", [])
                except Exception as e:
                    print(f"⚠️ 获取工具 '{tool.name}' 参数信息失败: {e}")

                tools_info.append(tool_info)

            servers_info[server_name] = {
                "name": server_name,
                "tools": tools_info,
                "tool_count": len(tools_info),
            }
            total_tools += len(tools_info)

        return {
            "servers": servers_info,
            "total_tools": total_tools,
            "server_count": len(servers_info),
            "agent_permissions": self.agent_permissions,
        }

    # =========================================================================
    # 工具调用
    # =========================================================================

    async def call_tool_for_agent(
        self, agent_name: str, tool_name: str, tool_args: Dict
    ) -> Any:
        """
        为指定智能体调用MCP工具

        Args:
            agent_name: 智能体名称（用于权限检查）
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            Any: 工具执行结果
        """
        # 权限检查
        if not self.agent_permissions.get(agent_name, False):
            error_msg = f"智能体 {agent_name} 未被授权使用MCP工具"
            print(f"⚠️ {error_msg}")
            return {"error": error_msg}

        # 连接检查
        if not self.client:
            error_msg = "MCP客户端未初始化或连接已断开"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

        # 查找目标工具
        target_tool = None
        for tool in self.tools:
            if tool.name == tool_name:
                target_tool = tool
                break

        if not target_tool:
            error_msg = f"未找到工具: {tool_name}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

        try:
            # 调用工具
            result = await target_tool.ainvoke(tool_args)
            print(f"智能体 {agent_name} 成功调用工具 {tool_name}")
            return result
        except Exception as e:
            error_msg = f"工具调用失败: {e}"
            print(f"❌ {error_msg}")
            # 连接错误时清理状态
            if "BrokenResourceError" in str(e) or "connection" in str(e).lower():
                print("🔄 检测到连接错误，清理MCP客户端状态")
                self.client = None
                self.tools = []
                self.tools_by_server = {}
            return {"error": error_msg}

    # =========================================================================
    # 连接管理
    # =========================================================================

    async def close(self):
        """
        关闭MCP连接

        应用退出时调用，释放资源。
        """
        if self.client:
            try:
                if hasattr(self.client, "close"):
                    await self.client.close()
                    print("MCP连接已关闭")
                else:
                    print("MCP客户端无需显式关闭")
                self.client = None
                self.tools = []
                self.tools_by_server = {}
            except Exception as e:
                print(f"❌ 关闭MCP连接时出错: {e}")
                self.client = None
                self.tools = []
                self.tools_by_server = {}

    # =========================================================================
    # 权限查询
    # =========================================================================

    def is_agent_mcp_enabled(self, agent_name: str) -> bool:
        """
        检查智能体是否启用了MCP工具

        Args:
            agent_name: 智能体名称

        Returns:
            bool: 是否启用MCP
        """
        return self.agent_permissions.get(agent_name, False)

    def get_enabled_agents(self) -> List[str]:
        """
        获取启用MCP工具的智能体列表

        Returns:
            List[str]: 已启用MCP的智能体名称列表
        """
        return [agent for agent, enabled in self.agent_permissions.items() if enabled]
