# TradingAgents-MCPmode

基于 MCP 工具的多智能体交易分析系统
<img width="2463" height="1211" alt="image" src="https://github.com/user-attachments/assets/5ab6e99b-cbf6-493b-b10d-fd27615ed207" />
<img width="2550" height="1236" alt="image" src="https://github.com/user-attachments/assets/ee21ccfc-0671-4b72-a6e7-0edf72fafc37" />


## 项目概述

**TradingAgents-MCPmode** 是一个创新的多智能体交易分析系统，集成了 Model Context Protocol (MCP) 工具，实现了智能化的股票分析和交易决策流程。系统通过 15 个专业化智能体的协作，提供全面的市场分析、投资建议和风险管理。

## 核心特性

- **多智能体协作**: 15 个专业化智能体分工合作
- **并行处理**: 分析师团队采用并行架构，显著提升分析效率
- **MCP 工具集成**: 支持外部数据源和实时信息获取
- **全面分析**: 公司概述、市场、情绪、新闻、基本面、股东结构、产品业务七维度分析
- **智能辩论**: 看涨/看跌研究员辩论机制，可配置辩论轮次
- **风险管理**: 三层风险分析和管理决策，支持动态风险辩论
- **智能体控制**: 前端可动态启用/禁用特定智能体，灵活定制工作流
- **辩论轮次配置**: 前端实时设置投资和风险辩论轮次，精确控制分析深度
- **K 线图表**: 实时股票 K 线数据可视化，支持技术指标展示
- **股票数据面板**: 股票实时价格、涨跌幅、成交量等核心数据
- **用户认证**: 完整的登录注册系统，支持会话持久化
- **历史管理**: 便捷的历史会话管理，支持导出分析报告
- **多市场支持**: 美股(US)、A股(CN)、港股(HK)
- **自然语言**: 支持自然语言查询，无需指定市场和日期

## 系统架构

### 智能体组织结构

```
┌─────────────────────────────────────────────────────────────┐
│                    TradingAgents-MCPmode                   │
├─────────────────────────────────────────────────────────────┤
│  分析师团队 (Analysts) - 并行执行                           │
│  ├── CompanyOverviewAnalyst (公司概述分析师)               │
│  ├── MarketAnalyst      (市场分析师)        ┐               │
│  ├── SentimentAnalyst   (情绪分析师)        │ 并行处理       │
│  ├── NewsAnalyst        (新闻分析师)        │ 6 个分析师    │
│  ├── FundamentalsAnalyst(基本面分析师)      │ 同时执行       │
│  ├── ShareholderAnalyst (股东分析师)        │               │
│  └── ProductAnalyst     (产品分析师)        ┘               │
├─────────────────────────────────────────────────────────────┤
│  研究员团队 (Researchers)                                │
│  ├── BullResearcher     (看涨研究员)                        │
│  └── BearResearcher     (看跌研究员)                       │
├─────────────────────────────────────────────────────────────┤
│  管理层 (Managers)                                       │
│  ├── ResearchManager    (研究经理)                          │
│  └── Trader             (交易员)                            │
├─────────────────────────────────────────────────────────────┤
│  风险管理团队 (Risk Management)                          │
│  ├── AggressiveRiskAnalyst (激进风险分析师)                 │
│  ├── SafeRiskAnalyst       (保守风险分析师)                 │
│  ├── NeutralRiskAnalyst    (中性风险分析师)                 │
│  └── RiskManager           (风险经理)                       │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

- **前端**: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **后端**: Python + FastAPI + LangGraph
- **智能体框架**: LangChain + LangGraph
- **数据可视化**: Recharts
- **状态管理**: Zustand

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 18+
- 支持的操作系统：Windows、macOS、Linux

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/amuMeta/Trading-Agent.git
cd Trading-Agent
```

2. **安装 Python 依赖**
```bash
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd frontend
npm install
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置你的 API 密钥和工作流参数
```

5. **配置 MCP 工具**
```bash
# 编辑 mcp_config.json 文件，配置 MCP 服务器
```

### 启动服务

#### 方式一：一键启动（推荐）

双击运行 `start_all.bat`，选择启动模式：
- `1` - Streamlit Web 界面
- `2` - React 前端 + API 后端（推荐）
- `3` - 仅 API 后端
- `4` - 仅 MCP 服务

#### 方式二：分开启动

**终端 1 - 启动 API 后端**
```bash
python run_api.py
```

**终端 2 - 启动前端开发服务器**
```bash
cd frontend
npm run dev
```

**终端 3 - 启动 MCP 服务**（可选）
```bash
# 请确保 MCP 服务器已启动
```

### 访问地址

- **React 前端**: http://localhost:3000
- **API 后端**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## 功能模块

### 前端功能

- **登录页面**: 粒子动效背景，现代化登录体验
- **首页仪表盘**: 系统状态、任务状态实时展示
- **智能体管理**: 按团队分组，灵活启用/禁用智能体
- **辩论配置**: 投资辩论和风险辩论轮次可视化配置
- **K 线图表**: 30 天 K 线数据，支持 MA、MACD、KDJ、RSI 指标
- **股票数据面板**: 实时行情、涨跌幅、成交量展示
- **分析结果**: 多标签展示各智能体分析报告
- **历史会话**: 完整的会话历史管理
- **报告导出**: Markdown、PDF、DOCX 多格式导出
- **系统监控**: MCP 工具数量、服务器状态监控

### 后端功能

- **RESTful API**: 完整的分析任务管理接口
- **WebSocket 支持**: 实时任务进度推送（可选）
- **会话管理**: 持久化存储分析会话
- **MCP 集成**: 灵活的 MCP 工具管理
- **智能体编排**: 基于 LangGraph 的工作流编排
- **错误处理**: 完善的异常捕获和日志记录

## 配置说明

### 环境变量配置

在 `.env` 文件中配置以下参数：

```env
# 大模型配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4

# 工作流配置
MAX_DEBATE_ROUNDS=1           # 投资辩论默认轮次
MAX_RISK_DEBATE_ROUNDS=1      # 风险辩论默认轮次
DEBUG_MODE=true               # 调试模式
VERBOSE_LOGGING=true          # 详细日志输出

# 智能体 MCP 权限配置
COMPANY_OVERVIEW_ANALYST_MCP=true
MARKET_ANALYST_MCP=true
SENTIMENT_ANALYST_MCP=true
NEWS_ANALYST_MCP=true
FUNDAMENTALS_ANALYST_MCP=true
SHAREHOLDER_ANALYST_MCP=true
PRODUCT_ANALYST_MCP=true
BULL_RESEARCHER_MCP=false
BEAR_RESEARCHER_MCP=false
RESEARCH_MANAGER_MCP=false
TRADER_MCP=false
AGGRESSIVE_RISK_ANALYST_MCP=false
SAFE_RISK_ANALYST_MCP=false
NEUTRAL_RISK_ANALYST_MCP=false
RISK_MANAGER_MCP=false

# 任务并发控制
MAX_CONCURRENT_ANALYSIS=2
```

### MCP 工具配置

在 `mcp_config.json` 文件中配置 MCP 服务器：

```json
{
  "mcpServers": {
    "stock-mcp": {
      "timeout": 600,
      "transport": "streamable_http",
      "url": "http://127.0.0.1:9898/mcp",
      "headers": {}
    }
  }
}
```

## 数据流转机制

### 信息累积效应

- **第 0 阶段**：仅用户查询
- **第 1 阶段**：用户查询 + 公司详细信息（并行处理）
- **第 2 阶段**：用户查询 + 全部 7 个分析师报告
- **第 3 阶段**：用户查询 + 分析师报告 + 辩论历史 + 投资决策
- **第 4 阶段**：用户查询 + 所有信息 + 风险观点

### 双重辩论机制

- **投资辩论**：看涨 ↔ 看跌研究员循环辩论
- **风险辩论**：激进 ↔ 保守 ↔ 中性风险分析师循环辩论

## 项目结构

```
TradingAgents-MCPmode/
├── frontend/                 # Next.js 前端应用
│   ├── app/                # 页面组件
│   │   ├── page.tsx       # 首页
│   │   ├── login/         # 登录页面
│   │   ├── history/       # 历史记录
│   │   └── analysis/      # 分析详情
│   ├── components/        # React 组件
│   │   ├── layout/       # 布局组件
│   │   ├── analysis/     # 分析组件
│   │   ├── charts/       # 图表组件
│   │   └── results/      # 结果组件
│   └── lib/              # 工具库
├── src/                    # Python 后端源码
│   ├── agents/            # 智能体实现
│   ├── web/               # Web 相关模块
│   ├── core/              # 核心模块
│   └── dumptools/         # 报告导出工具
├── web_app.py             # Streamlit 界面（可选）
├── run_api.py             # API 服务入口
├── main.py                # 命令行入口
└── requirements.txt       # Python 依赖
```

## 使用示例

### 股票分析查询

在分析输入框中输入自然语言查询：

- "分析苹果公司股票"
- "帮我分析一下 600036 招商银行"
- "分析特斯拉的投资价值"
- "看一下英伟达的股票"

系统将自动：
1. 识别股票代码和市场
2. 加载 K 线图表
3. 启动多智能体分析流程
4. 实时展示分析进度
5. 生成完整分析报告

## 性能优化

### 并行处理优势

- **原串行架构**: 6 个分析师顺序执行，总耗时 = Σ(各分析师耗时)
- **新并行架构**: 6 个分析师并发执行，总耗时 ≈ max(各分析师耗时)
- **性能提升**: 理论上可提升 5-6 倍效率

## 开发指南

### 添加新的智能体

1. 在 `src/agents/` 目录下创建新的智能体类
2. 继承 `BaseAgent` 类
3. 在 `workflow_orchestrator.py` 中注册新智能体
4. 更新前端配置以支持新智能体

### 自定义 MCP 工具

1. 配置 `mcp_config.json`
2. 重启 MCP 管理器
3. 在智能体中使用新工具

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目！

## 许可证

本项目采用 MIT 许可证。

---

**TradingAgents-MCPmode** - 让 AI 智能体团队为你的投资决策保驾护航！
