# MCP工具集成与多智能体工作流设计指南

> **目标读者**：想要构建基于MCP工具的多智能体系统的开发者  
> **学习目标**：读完本文后，你能独立设计并实现一个简化版的多智能体交易分析系统  
> **技术栈**：Python + LangGraph + MCP + OpenAI

---

## 📚 目录

1. [核心概念速览](#1-核心概念速览)
2. [MCP工具集成实战](#2-mcp工具集成实战)
3. [多智能体工作流设计](#3-多智能体工作流设计)
4. [从零实现简化版项目](#4-从零实现简化版项目)
5. [进阶优化技巧](#5-进阶优化技巧)
6. [常见问题与解决方案](#6-常见问题与解决方案)

---

## 1. 核心概念速览

### 1.1 什么是MCP？

**MCP (Model Context Protocol)** 是一个让AI模型能够安全、标准化地调用外部工具的协议。

**简单类比**：
- **传统AI**：就像一个只会背书的学生，只能依靠训练数据回答问题
- **带MCP的AI**：就像一个能上网查资料、能用计算器的学生，可以实时获取最新信息

**实际例子**（本项目）：
```
用户：分析苹果公司股票
┌─────────────────────────────────────┐
│ AI（没有MCP）                        │
│ → 只能说"苹果是一家科技公司..."     │
│   信息可能过时，无法提供实时数据     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ AI（有MCP）                          │
│ → 调用MCP工具获取实时股价            │
│ → 调用MCP工具获取最新财报            │
│ → 调用MCP工具获取新闻资讯            │
│ → 基于实时数据生成专业分析           │
└─────────────────────────────────────┘
```

### 1.2 什么是多智能体工作流？

**多智能体工作流** 就是让多个AI智能体像公司团队一样分工协作完成复杂任务。

**类比理解**：
```
传统单智能体 = 一个人包揽所有工作（全科医生）
多智能体系统 = 专业团队协作（医院科室）
```

**本项目的团队结构**：
```
📊 分析师团队（7人）
   ├── 公司概述分析师：负责获取公司基础信息
   ├── 市场分析师：负责分析市场数据
   ├── 新闻分析师：负责分析新闻舆情
   └── ...其他专业分析师

🔬 研究员团队（2人）
   ├── 看涨研究员：提出看涨观点
   └── 看跌研究员：提出看跌观点（二者辩论）

👔 管理层（2人）
   ├── 研究经理：综合分析形成投资计划
   └── 交易员：制定具体交易策略

⚠️ 风险管理团队（4人）
   ├── 激进/保守/中性风险分析师：从不同角度评估风险
   └── 风险经理：最终决策
```

---

## 2. MCP工具集成实战

### 2.1 第一步：理解MCP的工作原理

```
┌─────────┐      ┌──────────────┐      ┌──────────────┐
│ 你的AI  │ ←→  │ MCP客户端     │ ←→  │ MCP服务器     │
│ 智能体  │      │ (你的代码)   │      │ (提供工具)   │
└─────────┘      └──────────────┘      └──────────────┘
                        ↓                       ↓
                  工具调用请求              执行并返回结果
```

**关键点**：
1. **MCP服务器**：提供工具能力（如金融数据API）
2. **MCP客户端**：你的代码，负责连接服务器并管理工具
3. **AI智能体**：决定何时、如何调用工具

### 2.2 第二步：配置MCP服务器

**创建配置文件** `mcp_config.json`：

```json
{
  "mcpServers": {
    "finance-mcp": {
      "disabled": false,
      "timeout": 600,
      "transport": "streamable_http",
      "url": "https://finvestai.top/mcp",
      "headers": {
        "X-Tushare-Token": "您的tushare令牌"
      }
    }
  }
}
```

**配置说明**：
- `mcpServers`：可以配置多个MCP服务器
- `finance-mcp`：服务器的名字（自定义）
- `disabled`：是否禁用该服务器（false表示启用）
- `timeout`：请求超时时间（秒）
- `transport`：传输协议类型（streamable_http、sse等）
- `url`：MCP服务器地址
- `headers`：认证信息（API密钥等）

### 2.3 第三步：创建MCP管理器（核心代码）

这是整个项目最核心的部分，我们逐行拆解：

```python
import asyncio
from typing import Dict, Any, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

class MCPManager:
    """MCP工具管理器 - 这是你的AI助手的工具箱管理员"""
    
    def __init__(self, config_file: str = "mcp_config.json"):
        # 1. 加载MCP服务器配置
        self.config = self._load_config(config_file)
        
        # 2. 初始化大模型（AI的大脑）
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key="你的API密钥",
            temperature=0.1  # 温度越低，回答越稳定
        )
        
        # 3. MCP客户端和工具（初始化为空）
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List = []
        self.tools_by_server: Dict[str, List] = {}
        
        # 4. 权限控制：哪些智能体可以用MCP工具
        self.agent_permissions = {
            "market_analyst": True,    # 市场分析师可以用
            "news_analyst": True,      # 新闻分析师可以用
            "bull_researcher": False,  # 看涨研究员不能用（专注分析）
            "bear_researcher": False   # 看跌研究员不能用
        }
```

**为什么要权限控制？**
- **分析师**：需要MCP工具获取实时数据
- **研究员/管理层**：应该基于分析师的报告做综合判断，不应直接调用工具
- **类比**：医生需要检测设备，但院长应该看检测报告做决策

### 2.4 第四步：初始化MCP客户端并发现工具

```python
async def initialize(self) -> bool:
    """连接MCP服务器，发现可用工具"""
    try:
        # 1. 创建MCP客户端
        config = self.config.get("servers", {})
        self.client = MultiServerMCPClient(config)
        
        print("🔧 正在从MCP服务器获取工具...")
        
        # 2. 从每个服务器获取工具列表
        all_tools = []
        for server_name in config.keys():
            print(f"正在连接服务器: {server_name}")
            
            # 获取该服务器提供的所有工具
            server_tools = await self.client.get_tools(server_name=server_name)
            
            print(f"✅ 从 {server_name} 获取到 {len(server_tools)} 个工具")
            all_tools.extend(server_tools)
        
        # 3. 保存工具列表
        self.tools = all_tools
        print(f"🎉 总计发现 {len(self.tools)} 个可用工具")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP初始化失败: {e}")
        return False
```

**这段代码做了什么？**
1. 连接你配置的MCP服务器
2. 询问服务器："你能提供哪些工具？"
3. 服务器返回工具列表（如：`get_stock_price`、`get_news`等）
4. 保存这些工具，供后续智能体使用

**实际输出示例**：
```
🔧 正在从MCP服务器获取工具...
正在连接服务器: finance-mcp
✅从 finance-mcp 获取到 15 个工具
🎉 总计发现 15 个可用工具

工具列表：
- stock_basic: 获取股票基本信息
- daily_price: 获取日行情数据
- company_info: 获取公司详细信息
- news_content: 获取新闻内容
- ...
```

### 2.5 第五步：为智能体分配工具

```python
def get_tools_for_agent(self, agent_name: str) -> List:
    """根据权限，给智能体分配工具"""
    
    # 1. 检查权限
    if not self.agent_permissions.get(agent_name, False):
        print(f"❌ {agent_name} 没有使用MCP工具的权限")
        return []  # 返回空列表 = 没有工具
    
    # 2. 检查MCP是否已初始化
    if not self.client or not self.tools:
        print(f"⚠️ MCP客户端未连接")
        return []
    
    # 3. 返回所有可用工具
    print(f"✅ {agent_name} 获得 {len(self.tools)} 个工具")
    return self.tools

def create_agent_with_tools(self, agent_name: str):
    """创建一个带工具的AI智能体"""
    
    # 1. 获取该智能体可用的工具
    tools = self.get_tools_for_agent(agent_name)
    
    # 2. 创建React智能体（能够思考-行动-观察的AI）
    agent = create_react_agent(
        self.llm,    # AI大脑
        tools        # 可用工具
    )
    
    return agent
```

**React智能体是什么？**

React = **Re**asoning（推理） + **Act**ion（行动）

```
智能体的思考过程：
1. Thought（思考）：我需要获取苹果公司的股价
2. Action（行动）：调用 get_stock_price 工具
3. Observation（观察）：工具返回 $175.43
4. Thought（思考）：基于这个价格，我可以...
5. Action（行动）：继续分析或返回结果
```

### 2.6 第六步：实际使用示例

```python
async def main():
    # 1. 创建MCP管理器
    mcp_manager = MCPManager("mcp_config.json")
    
    # 2. 初始化连接
    success = await mcp_manager.initialize()
    if not success:
        print("初始化失败")
        return
    
    # 3. 创建市场分析师（有MCP权限）
    market_analyst = mcp_manager.create_agent_with_tools("market_analyst")
    
    # 4. 让市场分析师工作
    result = await market_analyst.ainvoke({
        "messages": [
            ("user", "获取苹果公司（AAPL）今天的股价和涨跌幅")
        ]
    })
    
    print(result)

# 运行
asyncio.run(main())
```

**运行结果示例**：
```
🔧 正在从MCP服务器获取工具...
✅ 从 finance-mcp 获取到 15 个工具
🎉 总计发现 15 个可用工具
✅ market_analyst 获得 15 个工具

智能体思考过程：
Thought: 用户想要获取AAPL的股价信息，我需要调用股票数据工具
Action: 调用 daily_price 工具，参数 ts_code="AAPL"
Observation: {"close": 175.43, "change": 2.3, "pct_change": 1.33}
Thought: 我获取到了数据，现在整理成易读的格式
Answer: 苹果公司(AAPL)今日收盘价为$175.43，上涨$2.30，涨幅1.33%
```

---

## 3. 多智能体工作流设计

### 3.1 核心概念：State（状态）

在LangGraph中，**State** 是智能体之间传递信息的载体，就像公司里的**工作文档**。

**类比理解**：
```
传统函数调用：
  输入 → 函数 → 输出

LangGraph工作流：
  State → Agent1 → 更新State → Agent2 → 更新State → ...
   ↑___________________________________________________|
  (State在整个流程中不断更新和传递)
```

**本项目的State设计**：

```python
from typing import TypedDict, List, Dict

class AgentState(TypedDict):
    """智能体工作流的共享状态"""
    
    # ===== 用户输入 =====
    user_query: str  # 用户的原始查询，如"分析苹果公司股票"
    
    # ===== 第0阶段：公司信息 =====
    company_details: str  # 公司基础信息（股票代码、行业等）
    company_overview_report: str  # 公司概述分析报告
    
    # ===== 第1阶段：专业分析报告 =====
    market_report: str  # 市场分析报告
    sentiment_report: str  # 情绪分析报告
    news_report: str  # 新闻分析报告
    fundamentals_report: str  # 基本面分析报告
    shareholder_report: str  # 股东分析报告
    product_report: str  # 产品业务分析报告
    
    # ===== 第2阶段：研究员辩论 =====
    debate_history: List[Dict]  # 看涨/看跌研究员的辩论记录
    bull_arguments: str  # 看涨观点汇总
    bear_arguments: str  # 看跌观点汇总
    
    # ===== 第3阶段：管理层决策 =====
    investment_plan: str  # 研究经理的投资计划
    trader_investment_plan: str  # 交易员的交易策略
    
    # ===== 第4阶段：风险管理 =====
    risk_debate_history: List[Dict]  # 风险分析师的辩论记录
    aggressive_risk_view: str  # 激进风险观点
    safe_risk_view: str  # 保守风险观点
    neutral_risk_view: str  # 中性风险观点
    final_trade_decision: str  # 风险经理的最终决策
    
    # ===== 元数据 =====
    agents_executed: List[str]  # 已执行的智能体列表
    current_stage: str  # 当前执行阶段
```

**为什么这样设计？**

1. **阶段性累积**：每个阶段的智能体都能看到前面阶段的所有成果
2. **信息分层**：
   - 第0阶段：获取原始数据
   - 第1阶段：多维度专业分析
   - 第2阶段：正反辩论
   - 第3阶段：形成决策
   - 第4阶段：风险控制

### 3.2 工作流节点设计

**节点（Node）** 就是工作流中的一个智能体或处理步骤。

**示例：市场分析师节点**

```python
async def market_analyst_node(state: AgentState) -> AgentState:
    """市场分析师节点 - 分析市场数据"""
    
    print("📊 市场分析师开始工作...")
    
    # 1. 创建带MCP工具的智能体
    agent = mcp_manager.create_agent_with_tools("market_analyst")
    
    # 2. 构建提示词（告诉AI要做什么）
    prompt = f"""
    你是一名专业的市场分析师。
    
    用户查询：{state['user_query']}
    公司信息：{state['company_details']}
    
    任务：
    1. 使用MCP工具获取该公司的市场数据（股价、成交量、技术指标等）
    2. 分析价格趋势、市场情绪、技术面
    3. 生成详细的市场分析报告
    
    请开始工作。
    """
    
    # 3. 调用智能体
    result = await agent.ainvoke({
        "messages": [("user", prompt)]
    })
    
    # 4. 更新State
    state['market_report'] = result['messages'][-1].content
    state['agents_executed'].append("market_analyst")
    
    print("✅ 市场分析师完成工作")
    
    # 5. 返回更新后的State
    return state
```

**关键点**：
1. **输入**：从State中读取需要的信息
2. **处理**：调用AI智能体（可能使用MCP工具）
3. **输出**：将结果写回State
4. **传递**：返回更新后的State给下一个节点

### 3.3 并行执行节点设计

**为什么需要并行？**

```
串行执行（慢）：
市场分析(30s) → 新闻分析(25s) → 情绪分析(20s) = 总计75秒

并行执行（快）：
┌─ 市场分析(30s) ─┐
├─ 新闻分析(25s) ─┤ → 汇总 = 总计约30秒
└─ 情绪分析(20s) ─┘
```

**实现并行执行**：

```python
import asyncio
from copy import deepcopy

async def parallel_analysts_node(state: AgentState) -> AgentState:
    """并行执行6个分析师"""
    
    print("⚡ 启动并行分析节点...")
    
    # 1. 定义要并行执行的分析师
    analysts = [
        ("market_analyst", "market_report"),
        ("sentiment_analyst", "sentiment_report"),
        ("news_analyst", "news_report"),
        ("fundamentals_analyst", "fundamentals_report"),
        ("shareholder_analyst", "shareholder_report"),
        ("product_analyst", "product_report")
    ]
    
    # 2. 为每个分析师创建独立的State副本（避免冲突）
    tasks = []
    for agent_name, report_key in analysts:
        # 深拷贝State，每个分析师操作自己的副本
        state_copy = deepcopy(state)
        
        # 创建异步任务
        task = run_analyst(agent_name, report_key, state_copy)
        tasks.append((agent_name, report_key, task))
    
    # 3. 并发执行所有任务
    results = await asyncio.gather(*[task for _, _, task in tasks])
    
    # 4. 合并结果到主State
    for i, (agent_name, report_key, _) in enumerate(tasks):
        state[report_key] = results[i]
        state['agents_executed'].append(agent_name)
    
    print("✅ 并行分析完成")
    return state

async def run_analyst(agent_name: str, report_key: str, state: AgentState) -> str:
    """执行单个分析师"""
    agent = mcp_manager.create_agent_with_tools(agent_name)
    
    prompt = f"""
    用户查询：{state['user_query']}
    公司信息：{state['company_details']}
    
    请使用MCP工具获取数据并生成专业分析报告。
    """
    
    result = await agent.ainvoke({"messages": [("user", prompt)]})
    return result['messages'][-1].content
```

### 3.4 条件路由与辩论循环

**辩论机制**：看涨和看跌研究员相互辩论，多轮交锋。

```python
def should_continue_debate(state: AgentState) -> str:
    """判断是否继续辩论"""
    
    debate_history = state.get('debate_history', [])
    max_rounds = 3  # 最多3轮辩论
    
    if len(debate_history) < max_rounds * 2:
        # 每轮 = 看涨发言1次 + 看跌发言1次
        # 下一个该谁发言？
        if len(debate_history) % 2 == 0:
            return "bull_researcher"  # 偶数轮，看涨发言
        else:
            return "bear_researcher"  # 奇数轮，看跌发言
    else:
        return "debate_end"  # 辩论结束，进入下一阶段

async def bull_researcher_node(state: AgentState) -> AgentState:
    """看涨研究员节点"""
    
    agent = mcp_manager.create_agent_with_tools("bull_researcher")
    
    # 构建上下文：包含所有分析报告和辩论历史
    context = f"""
    === 分析报告汇总 ===
    市场分析：{state['market_report']}
    情绪分析：{state['sentiment_report']}
    新闻分析：{state['news_report']}
    ...
    
    === 辩论历史 ===
    {format_debate_history(state['debate_history'])}
    
    === 你的任务 ===
    作为看涨研究员，基于以上信息：
    1. 提出看涨的投资论证
    2. 反驳看跌研究员的观点（如果有）
    3. 强化你的论据
    """
    
    result = await agent.ainvoke({"messages": [("user", context)]})
    
    # 记录辩论发言
    state['debate_history'].append({
        "speaker": "bull_researcher",
        "content": result['messages'][-1].content,
        "round": len(state['debate_history']) // 2 + 1
    })
    
    return state

async def bear_researcher_node(state: AgentState) -> AgentState:
    """看跌研究员节点（逻辑类似）"""
    # ... 类似实现，但角度是看跌
    pass
```

### 3.5 组装完整工作流

```python
from langgraph.graph import StateGraph, END

def build_workflow():
    """构建完整的多智能体工作流"""
    
    # 1. 创建状态图
    workflow = StateGraph(AgentState)
    
    # 2. 添加节点
    workflow.add_node("company_overview_analyst", company_overview_analyst_node)
    workflow.add_node("parallel_analysts", parallel_analysts_node)
    workflow.add_node("bull_researcher", bull_researcher_node)
    workflow.add_node("bear_researcher", bear_researcher_node)
    workflow.add_node("research_manager", research_manager_node)
    workflow.add_node("trader", trader_node)
    workflow.add_node("risk_manager", risk_manager_node)
    
    # 3. 定义边（节点之间的连接）
    workflow.set_entry_point("company_overview_analyst")  # 入口
    
    # 线性流程
    workflow.add_edge("company_overview_analyst", "parallel_analysts")
    workflow.add_edge("parallel_analysts", "bull_researcher")
    
    # 条件路由（辩论循环）
    workflow.add_conditional_edges(
        "bull_researcher",
        should_continue_debate,
        {
            "bear_researcher": "bear_researcher",
            "debate_end": "research_manager"
        }
    )
    
    workflow.add_conditional_edges(
        "bear_researcher",
        should_continue_debate,
        {
            "bull_researcher": "bull_researcher",
            "debate_end": "research_manager"
        }
    )
    
    # 继续后续流程
    workflow.add_edge("research_manager", "trader")
    workflow.add_edge("trader", "risk_manager")
    workflow.add_edge("risk_manager", END)  # 结束
    
    # 4. 编译工作流
    app = workflow.compile()
    return app
```

**可视化工作流**：
```
开始
 ↓
公司概述分析师
 ↓
并行分析师节点 (6个分析师同时执行)
 ↓
看涨研究员 ←→ 看跌研究员 (辩论循环)
 ↓
研究经理
 ↓
交易员
 ↓
风险经理
 ↓
结束
```

---

## 4. 从零实现简化版项目

让我们用300行代码实现一个**简化版股票分析系统**。

### 4.1 项目结构

```
mini-trading-agent/
├── mcp_config.json       # MCP配置
├── .env                  # 环境变量
├── main.py              # 主程序
├── mcp_manager.py       # MCP管理器
└── workflow.py          # 工作流定义
```

### 4.2 完整代码实现

**文件1：mcp_manager.py**

```python
"""MCP管理器 - 简化版"""
import json
import asyncio
from typing import Dict, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

class SimpleMCPManager:
    def __init__(self, config_file: str = "mcp_config.json"):
        # 加载配置
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        # 初始化大模型
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key="你的API密钥",
            temperature=0.1
        )
        
        self.client = None
        self.tools = []
    
    async def initialize(self):
        """初始化MCP客户端"""
        config = self.config.get("servers", {})
        self.client = MultiServerMCPClient(config)
        
        # 获取所有工具
        for server_name in config.keys():
            tools = await self.client.get_tools(server_name=server_name)
            self.tools.extend(tools)
        
        print(f"✅ 发现 {len(self.tools)} 个MCP工具")
        return True
    
    def create_agent(self, system_prompt: str, use_tools: bool = True):
        """创建智能体"""
        tools = self.tools if use_tools else []
        
        # 创建带系统提示的LLM
        llm_with_prompt = self.llm.bind(system=system_prompt)
        
        # 创建React智能体
        agent = create_react_agent(llm_with_prompt, tools)
        return agent
```

**文件2：workflow.py**

```python
"""工作流定义 - 简化版（3个智能体）"""
import asyncio
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from mcp_manager import SimpleMCPManager

# 定义State
class SimpleState(TypedDict):
    user_query: str
    company_info: str
    market_analysis: str
    final_decision: str
    messages: List[str]

# 全局MCP管理器
mcp = SimpleMCPManager()

# 节点1：公司信息收集
async def company_info_node(state: SimpleState) -> SimpleState:
    print("\n📋 步骤1：收集公司信息...")
    
    agent = mcp.create_agent(
        system_prompt="你是信息收集专家，负责获取公司基础信息。",
        use_tools=True  # 使用MCP工具
    )
    
    prompt = f"获取以下公司的基本信息：{state['user_query']}"
    result = await agent.ainvoke({"messages": [("user", prompt)]})
    
    state['company_info'] = result['messages'][-1].content
    state['messages'].append(f"✅ 公司信息：{state['company_info'][:100]}...")
    
    return state

# 节点2：市场分析
async def market_analysis_node(state: SimpleState) -> SimpleState:
    print("\n📊 步骤2：市场分析...")
    
    agent = mcp.create_agent(
        system_prompt="你是市场分析师，负责分析股票市场数据。",
        use_tools=True  # 使用MCP工具
    )
    
    prompt = f"""
    公司信息：{state['company_info']}
    
    任务：
    1. 获取该公司的股价数据
    2. 分析价格趋势
    3. 给出技术面评估
    """
    
    result = await agent.ainvoke({"messages": [("user", prompt)]})
    
    state['market_analysis'] = result['messages'][-1].content
    state['messages'].append(f"✅ 市场分析：{state['market_analysis'][:100]}...")
    
    return state

# 节点3：投资决策
async def decision_node(state: SimpleState) -> SimpleState:
    print("\n💰 步骤3：投资决策...")
    
    agent = mcp.create_agent(
        system_prompt="你是投资决策专家，综合信息给出投资建议。",
        use_tools=False  # 不使用工具，纯分析
    )
    
    prompt = f"""
    === 已知信息 ===
    公司信息：{state['company_info']}
    市场分析：{state['market_analysis']}
    
    === 任务 ===
    基于以上信息，给出明确的投资建议：
    1. 是否建议买入/卖出/持有
    2. 理由是什么
    3. 风险提示
    """
    
    result = await agent.ainvoke({"messages": [("user", prompt)]})
    
    state['final_decision'] = result['messages'][-1].content
    state['messages'].append(f"✅ 投资决策：{state['final_decision'][:100]}...")
    
    return state

# 构建工作流
def build_simple_workflow():
    workflow = StateGraph(SimpleState)
    
    # 添加节点
    workflow.add_node("company_info", company_info_node)
    workflow.add_node("market_analysis", market_analysis_node)
    workflow.add_node("decision", decision_node)
    
    # 连接节点
    workflow.set_entry_point("company_info")
    workflow.add_edge("company_info", "market_analysis")
    workflow.add_edge("market_analysis", "decision")
    workflow.add_edge("decision", END)
    
    return workflow.compile()
```

**文件3：main.py**

```python
"""主程序 - 运行简化版系统"""
import asyncio
from workflow import build_simple_workflow, mcp, SimpleState

async def main():
    print("🚀 简化版股票分析系统启动")
    
    # 1. 初始化MCP
    print("\n初始化MCP连接...")
    await mcp.initialize()
    
    # 2. 构建工作流
    print("\n构建工作流...")
    app = build_simple_workflow()
    
    # 3. 用户输入
    user_query = input("\n请输入要分析的股票（如：苹果公司、AAPL、TSLA）：")
    
    # 4. 初始化State
    initial_state: SimpleState = {
        "user_query": user_query,
        "company_info": "",
        "market_analysis": "",
        "final_decision": "",
        "messages": []
    }
    
    # 5. 运行工作流
    print("\n开始分析...\n" + "="*50)
    result = await app.ainvoke(initial_state)
    
    # 6. 显示结果
    print("\n" + "="*50)
    print("\n📊 最终分析结果：\n")
    print(result['final_decision'])
    
    print("\n💾 执行日志：")
    for msg in result['messages']:
        print(f"  {msg}")

if __name__ == "__main__":
    asyncio.run(main())
```

**文件4：mcp_config.json**

```json
{
  "mcpServers": {
    "finance-mcp": {
      "disabled": false,
      "timeout": 600,
      "transport": "streamable_http",
      "url": "https://finvestai.top/mcp",
      "headers": {
        "X-Tushare-Token": "您的tushare令牌"
      }
    }
  }
}
```

### 4.3 运行项目

```bash
# 安装依赖
pip install langchain-openai langchain-mcp-adapters langgraph

# 运行
python main.py
```

**运行示例**：
```
🚀 简化版股票分析系统启动

初始化MCP连接...
✅ 发现 15 个MCP工具

构建工作流...

请输入要分析的股票：苹果公司

开始分析...
==================================================

📋 步骤1：收集公司信息...
✅ 公司信息：苹果公司（Apple Inc.），股票代码AAPL，NASDAQ上市...

📊 步骤2：市场分析...
✅ 市场分析：AAPL当前股价$175.43，日内上涨1.33%，成交量正常...

💰 步骤3：投资决策...
✅ 投资决策：建议：持有/小幅加仓...

==================================================

📊 最终分析结果：

基于苹果公司当前的市场表现和基本面分析：

**投资建议：持有/小幅加仓**

**理由：**
1. 公司基本面稳健，现金流充足
2. 股价处于合理估值区间
3. 技术面呈现上升趋势

**风险提示：**
1. 宏观经济不确定性
2. 行业竞争加剧
3. 建议分散投资，不要重仓单一股票
```

---

## 5. 进阶优化技巧

### 5.1 添加更多智能体

**扩展策略**：从3个智能体扩展到7个

```python
# 在workflow.py中添加新节点

async def news_analysis_node(state: SimpleState) -> SimpleState:
    """新闻分析节点"""
    agent = mcp.create_agent(
        system_prompt="你是新闻分析师，分析舆情和新闻对股价的影响。",
        use_tools=True
    )
    # ... 实现逻辑
    return state

async def sentiment_analysis_node(state: SimpleState) -> SimpleState:
    """情绪分析节点"""
    agent = mcp.create_agent(
        system_prompt="你是情绪分析师，分析市场情绪和投资者心态。",
        use_tools=True
    )
    # ... 实现逻辑
    return state

# 更新工作流
def build_advanced_workflow():
    workflow = StateGraph(AdvancedState)
    
    workflow.add_node("company_info", company_info_node)
    workflow.add_node("market_analysis", market_analysis_node)
    workflow.add_node("news_analysis", news_analysis_node)
    workflow.add_node("sentiment_analysis", sentiment_analysis_node)
    workflow.add_node("decision", decision_node)
    
    # 串行流程
    workflow.set_entry_point("company_info")
    workflow.add_edge("company_info", "market_analysis")
    workflow.add_edge("market_analysis", "news_analysis")
    workflow.add_edge("news_analysis", "sentiment_analysis")
    workflow.add_edge("sentiment_analysis", "decision")
    workflow.add_edge("decision", END)
    
    return workflow.compile()
```

### 5.2 实现辩论机制

```python
from typing import Literal

def should_continue_debate(state: DebateState) -> Literal["bull", "bear", "end"]:
    """判断辩论是否继续"""
    debate_rounds = len(state['debate_history']) // 2
    
    if debate_rounds >= 3:  # 最多3轮
        return "end"
    
    # 轮流发言
    if len(state['debate_history']) % 2 == 0:
        return "bull"  # 看涨研究员发言
    else:
        return "bear"  # 看跌研究员发言

async def bull_researcher_node(state: DebateState) -> DebateState:
    """看涨研究员"""
    agent = mcp.create_agent(
        system_prompt="你是看涨研究员，寻找买入理由。",
        use_tools=False
    )
    
    # 包含辩论历史
    debate_context = "\n".join([
        f"{item['speaker']}: {item['content']}" 
        for item in state['debate_history']
    ])
    
    prompt = f"""
    === 分析报告 ===
    {state['market_analysis']}
    
    === 辩论历史 ===
    {debate_context}
    
    === 你的任务 ===
    提出看涨观点，并反驳对方论据。
    """
    
    result = await agent.ainvoke({"messages": [("user", prompt)]})
    
    state['debate_history'].append({
        "speaker": "bull_researcher",
        "content": result['messages'][-1].content
    })
    
    return state

async def bear_researcher_node(state: DebateState) -> DebateState:
    """看跌研究员（类似实现）"""
    # ... 类似逻辑，但角度相反
    pass

# 工作流中添加条件路由
workflow.add_conditional_edges(
    "bull_researcher",
    should_continue_debate,
    {
        "bull": "bull_researcher",
        "bear": "bear_researcher",
        "end": "final_decision"
    }
)

workflow.add_conditional_edges(
    "bear_researcher",
    should_continue_debate,
    {
        "bull": "bull_researcher",
        "bear": "bear_researcher",
        "end": "final_decision"
    }
)
```

### 5.3 实现并行执行

```python
import asyncio
from copy import deepcopy

async def parallel_analysts_node(state: SimpleState) -> SimpleState:
    """并行执行多个分析师"""
    
    # 定义分析师任务
    analysts = [
        ("market_analyst", "market_analysis"),
        ("news_analyst", "news_analysis"),
        ("sentiment_analyst", "sentiment_analysis")
    ]
    
    # 并发执行
    tasks = []
    for agent_name, key in analysts:
        state_copy = deepcopy(state)
        task = run_single_analyst(agent_name, key, state_copy)
        tasks.append((key, task))
    
    # 等待所有任务完成
    results = await asyncio.gather(*[task for _, task in tasks])
    
    # 合并结果
    for i, (key, _) in enumerate(tasks):
        state[key] = results[i]
    
    return state

async def run_single_analyst(agent_name: str, key: str, state: SimpleState) -> str:
    """运行单个分析师"""
    agent = mcp.create_agent(
        system_prompt=f"你是{agent_name}，负责专业分析。",
        use_tools=True
    )
    
    result = await agent.ainvoke({
        "messages": [("user", f"分析：{state['user_query']}")]
    })
    
    return result['messages'][-1].content
```

### 5.4 添加错误处理和重试

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),  # 最多重试3次
    wait=wait_exponential(min=1, max=10)  # 指数退避
)
async def robust_agent_call(agent, prompt):
    """带重试的智能体调用"""
    try:
        result = await agent.ainvoke({"messages": [("user", prompt)]})
        return result['messages'][-1].content
    except Exception as e:
        print(f"⚠️ 调用失败: {e}，正在重试...")
        raise  # 触发重试

async def market_analysis_node_v2(state: SimpleState) -> SimpleState:
    """带错误处理的市场分析节点"""
    try:
        agent = mcp.create_agent(
            system_prompt="你是市场分析师。",
            use_tools=True
        )
        
        prompt = f"分析：{state['user_query']}"
        
        # 使用带重试的调用
        result = await robust_agent_call(agent, prompt)
        
        state['market_analysis'] = result
        
    except Exception as e:
        # 所有重试都失败后的fallback
        print(f"❌ 市场分析失败: {e}")
        state['market_analysis'] = "市场分析暂时无法完成，请稍后重试。"
    
    return state
```

### 5.5 添加流式输出

```python
async def streaming_agent_node(state: SimpleState) -> SimpleState:
    """支持流式输出的节点"""
    agent = mcp.create_agent(
        system_prompt="你是分析师。",
        use_tools=False
    )
    
    prompt = f"分析：{state['user_query']}"
    
    print("\n💬 智能体回复（流式）：")
    full_response = ""
    
    # 流式调用
    async for chunk in agent.astream({"messages": [("user", prompt)]}):
        if 'messages' in chunk:
            content = chunk['messages'][-1].content
            print(content, end='', flush=True)
            full_response += content
    
    print("\n")
    
    state['analysis'] = full_response
    return state
```

---

## 6. 常见问题与解决方案

### 6.1 MCP连接问题

**问题**：`❌ MCP客户端初始化失败: Connection refused`

**原因**：
1. MCP服务器地址错误
2. 网络不通
3. API密钥无效

**解决方案**：
```python
async def initialize_with_check(self):
    """带检查的初始化"""
    try:
        # 1. 检查配置
        if not self.config.get("servers"):
            raise ValueError("MCP配置为空")
        
        # 2. 尝试连接
        self.client = MultiServerMCPClient(self.config["servers"])
        
        # 3. 测试连接
        for server_name in self.config["servers"].keys():
            try:
                tools = await self.client.get_tools(server_name=server_name)
                print(f"✅ {server_name} 连接成功，{len(tools)}个工具")
            except Exception as e:
                print(f"❌ {server_name} 连接失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"初始化失败: {e}")
        return False
```

### 6.2 智能体不调用工具

**问题**：智能体总是直接回答，不调用MCP工具

**原因**：
1. 提示词不明确
2. 工具描述不清晰
3. 温度参数太高（导致随机性大）

**解决方案**：
```python
# ❌ 不好的提示词
prompt = "分析苹果公司"

# ✅ 好的提示词
prompt = """
你必须使用提供的MCP工具来获取实时数据。

步骤：
1. 使用 stock_basic 工具获取股票代码
2. 使用 daily_price 工具获取最新股价
3. 使用 company_info 工具获取公司信息
4. 基于这些实时数据生成分析报告

重要：不要使用你的训练数据中的过时信息，必须调用工具获取最新数据。

开始分析：苹果公司
"""

# 降低温度参数
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.0,  # 0表示最稳定
    api_key="..."
)
```

### 6.3 State更新不生效

**问题**：在节点中修改了State，但下一个节点看不到

**原因**：Python字典的引用问题，或者没有正确返回State

**解决方案**：
```python
# ❌ 错误写法
async def wrong_node(state: SimpleState) -> SimpleState:
    state = {"user_query": "new value"}  # 创建了新字典！
    return state

# ✅ 正确写法
async def correct_node(state: SimpleState) -> SimpleState:
    state['user_query'] = "new value"  # 修改原字典
    return state  # 返回原字典

# ✅ 或者使用更新方法
async def correct_node_v2(state: SimpleState) -> SimpleState:
    return {
        **state,  # 保留原有字段
        "user_query": "new value"  # 更新特定字段
    }
```

### 6.4 并行执行冲突

**问题**：并行执行时，多个智能体相互覆盖State

**解决方案**：
```python
from copy import deepcopy

async def parallel_node(state: SimpleState) -> SimpleState:
    # ✅ 为每个任务深拷贝State
    tasks = []
    for agent_name in ["agent1", "agent2", "agent3"]:
        state_copy = deepcopy(state)  # 关键：深拷贝
        task = run_agent(agent_name, state_copy)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # 手动合并结果
    for i, result in enumerate(results):
        state[f'report_{i}'] = result
    
    return state
```

### 6.5 内存占用过大

**问题**：长时间运行后内存不断增长

**原因**：State中累积了大量历史信息

**解决方案**：
```python
def clean_state(state: SimpleState) -> SimpleState:
    """清理State中的冗余信息"""
    
    # 1. 限制列表长度
    if 'debate_history' in state:
        state['debate_history'] = state['debate_history'][-20:]  # 只保留最近20条
    
    # 2. 清理已完成节点的中间结果
    if 'final_decision' in state and state['final_decision']:
        # 已经有最终决策，可以删除中间过程
        keys_to_keep = ['user_query', 'final_decision']
        state = {k: v for k, v in state.items() if k in keys_to_keep}
    
    return state

# 在workflow中定期清理
workflow.add_node("cleanup", clean_state)
```

### 6.6 调试技巧

```python
import logging

# 1. 开启详细日志
logging.basicConfig(level=logging.DEBUG)

# 2. 在节点中打印State
async def debug_node(state: SimpleState) -> SimpleState:
    print("\n🔍 当前State:")
    for key, value in state.items():
        if isinstance(value, str):
            print(f"  {key}: {value[:100]}...")  # 只打印前100字符
        else:
            print(f"  {key}: {value}")
    return state

# 3. 记录工具调用
class DebugMCPManager(SimpleMCPManager):
    async def call_tool(self, tool_name, args):
        print(f"\n🔧 调用工具: {tool_name}")
        print(f"   参数: {args}")
        
        result = await super().call_tool(tool_name, args)
        
        print(f"   结果: {str(result)[:200]}...")
        return result
```

---

## 7. 最佳实践总结

### 7.1 MCP工具使用原则

1. **分离关注点**：
   - ✅ 前端智能体（分析师）使用MCP获取数据
   - ✅ 后端智能体（管理层）专注综合分析
   - ❌ 避免所有智能体都调用工具（浪费资源）

2. **明确提示词**：
   - ✅ 告诉AI"必须使用工具"
   - ✅ 列出具体步骤
   - ❌ 避免模糊的指令

3. **错误处理**：
   - ✅ 使用重试机制
   - ✅ 提供fallback方案
   - ✅ 记录错误日志

### 7.2 工作流设计原则

1. **阶段性设计**：
   ```
   阶段1: 数据收集（使用MCP工具）
   阶段2: 专业分析（基于数据）
   阶段3: 辩论讨论（正反观点）
   阶段4: 综合决策（形成结论）
   ```

2. **并行优化**：
   - ✅ 无依赖的节点并行执行
   - ✅ 有依赖的节点串行执行
   - ✅ 使用深拷贝避免冲突

3. **状态管理**：
   - ✅ State只存必要信息
   - ✅ 定期清理冗余数据
   - ✅ 使用明确的字段命名

### 7.3 性能优化建议

1. **缓存机制**：
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_company_info(stock_code: str):
    """缓存公司信息，避免重复调用"""
    # ... MCP调用
    pass
```

2. **批量处理**：
```python
# ❌ 不好：多次单独调用
for code in stock_codes:
    price = await get_price(code)

# ✅ 好：批量调用
prices = await get_prices_batch(stock_codes)
```

3. **超时控制**：
```python
import asyncio

async def node_with_timeout(state: SimpleState) -> SimpleState:
    try:
        # 最多等待30秒
        result = await asyncio.wait_for(
            agent.ainvoke(...),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        print("⚠️ 节点执行超时，使用默认值")
        result = "分析超时，请稍后重试"
    
    state['analysis'] = result
    return state
```

---

## 8. 下一步学习路线

### 8.1 进阶主题

1. **持久化State**：使用数据库保存工作流状态
2. **人机协作**：在工作流中加入人工审核节点
3. **多模态输入**：支持图表、文档等输入
4. **实时监控**：可视化工作流执行状态

### 8.2 推荐资源

- **LangGraph文档**：https://python.langchain.com/docs/langgraph
- **MCP协议**：https://modelcontextprotocol.io/
- **本项目完整代码**：https://github.com/guangxiangdebizi/TradingAgents-MCPmode

---

## 9. 总结

通过本指南，你学到了：

✅ **MCP工具集成**：
- 如何配置MCP服务器
- 如何创建MCP管理器
- 如何让AI调用外部工具

✅ **工作流设计**：
- State的设计原则
- 节点的实现方法
- 串行、并行、条件路由的使用

✅ **实战经验**：
- 从零实现简化版项目
- 常见问题的解决方案
- 性能优化技巧

现在，你已经具备了构建自己的多智能体系统的能力！

**下一步行动**：
1. 运行简化版项目
2. 添加你自己的智能体
3. 接入你需要的MCP工具
4. 根据业务需求定制工作流

**记住**：复杂的系统都是从简单开始的，先跑通基础版本，再逐步优化！

---

**项目地址**：https://github.com/guangxiangdebizi/TradingAgents-MCPmode  
**作者**：guangxiangdebizi  
**许可证**：MIT

祝你构建出优秀的多智能体系统！🚀

