#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingAgents-MCPmode Web前端 - 超简化版本
删除了有问题的摘要展开功能和高级配置模块
"""

import streamlit as st
import sys
import os
import asyncio
import threading
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入样式加载器
try:
    from src.web.css_loader import (
        load_financial_css,
        inject_custom_html,
        create_header_html,
        apply_button_style,
        create_section_card_html,
        create_metric_card_html,
    )
except ImportError as e:
    # 生产环境下可能因为PYTHONPATH或打包方式导致导入失败。
    # 提示会被全局CSS隐藏，这里同时打印到控制台便于排查。
    print(f"[web_app] CSS样式模块导入失败: {e}")
    st.error(f"无法导入CSS样式模块: {e}")

# 导入工作流程编排器
try:
    from src.workflow_orchestrator import WorkflowOrchestrator
except ImportError as e:
    WorkflowOrchestrator = None
    st.error(f"无法导入WorkflowOrchestrator: {e}")

# 导入导出工具
try:
    from src.dumptools.json_to_markdown import JSONToMarkdownConverter
    from src.dumptools.md2pdf import MarkdownToPDFConverter
    from src.dumptools.md2docx import MarkdownToDocxConverter
except ImportError as e:
    st.error(f"无法导入导出工具: {e}")
    JSONToMarkdownConverter = None
    MarkdownToPDFConverter = None
    MarkdownToDocxConverter = None

# 页面配置
st.set_page_config(
    page_title="AI实验室 - TradingAgents",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 隐藏Streamlit警告信息
import warnings

warnings.filterwarnings("ignore")

# 隐藏控制台日志
import logging

logging.getLogger().setLevel(logging.ERROR)

# 隐藏Streamlit的一些UI元素
try:
    st.set_option("client.showErrorDetails", False)
    st.set_option("client.toolbarMode", "minimal")
except:
    pass

# 添加CSS隐藏不需要的元素（保留）
st.markdown(
    """
<style>
.stAlert[data-testid="stAlertContainer"], .stAlert, [data-baseweb="notification"], .stException { display: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

# 初始化会话状态
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "analysis_running" not in st.session_state:
    st.session_state.analysis_running = False
if "selected_session_file" not in st.session_state:
    st.session_state.selected_session_file = None
if "current_session_data" not in st.session_state:
    st.session_state.current_session_data = None
if "analysis_completed" not in st.session_state:
    st.session_state.analysis_completed = False
if "active_agents" not in st.session_state:
    # 默认全部启用
    st.session_state.active_agents = {
        "company_overview_analyst": True,
        "market_analyst": True,
        "sentiment_analyst": True,
        "news_analyst": True,
        "fundamentals_analyst": True,
        "shareholder_analyst": True,
        "product_analyst": True,
        "bull_researcher": True,
        "bear_researcher": True,
        "research_manager": True,
        "trader": True,
        "aggressive_risk_analyst": True,
        "safe_risk_analyst": True,
        "neutral_risk_analyst": True,
        "risk_manager": True,
    }


def load_page_styles():
    """加载页面样式"""
    try:
        load_financial_css()
        inject_custom_html()
        try:
            apply_button_style()
        except Exception:
            pass
    except:
        pass


def render_top_header():
    """将抬头组件紧贴页面最上方（去掉Streamlit默认header与顶部留白）。"""
    # 移除 Streamlit 自带 header 占位，并压缩主容器的顶部内边距
    st.markdown(
        """
<style>
header { display: none !important; }
.main .block-container { padding-top: 0 !important; }
.header-container { margin-top: 0 !important; }
</style>
        """,
        unsafe_allow_html=True,
    )
    try:
        st.markdown(create_header_html(), unsafe_allow_html=True)
    except Exception as e:
        # 回退到原生标题，避免公网环境抬头缺失
        print(f"[web_app] 渲染自定义抬头失败，使用fallback: {e}")
        st.title("TradingAgents-MCPmode")
        st.caption("基于MCP工具的多智能体交易分析系统")


def render_sidebar_toggle_controls():
    return


def _get_agent_groups():
    """按团队返回智能体分组"""
    return {
        "📊 分析师团队": [
            "company_overview_analyst",
            "market_analyst",
            "sentiment_analyst",
            "news_analyst",
            "fundamentals_analyst",
            "shareholder_analyst",
            "product_analyst",
        ],
        "🔬 研究员团队": ["bull_researcher", "bear_researcher"],
        "👔 管理层": ["research_manager", "trader"],
        "⚖️ 风险管理团队": [
            "aggressive_risk_analyst",
            "safe_risk_analyst",
            "neutral_risk_analyst",
            "risk_manager",
        ],
    }


def render_main_agent_selector():
    """主页面：选择本轮启用的智能体（不使用侧边栏）。"""
    with st.expander("🤖 本轮启用智能体", expanded=False):
        c1, c2, c3 = st.columns([1, 1, 6])
        with c1:
            if st.button("全选", key="main_select_all_agents"):
                for k in st.session_state.active_agents.keys():
                    st.session_state.active_agents[k] = True
                st.rerun()
        with c2:
            if st.button("全不选", key="main_deselect_all_agents"):
                for k in st.session_state.active_agents.keys():
                    st.session_state.active_agents[k] = False
                st.rerun()

        # 分组复选 - 先处理所有checkbox，再计算统计
        checkbox_states = {}
        for team_name, agents in _get_agent_groups().items():
            st.markdown(f"**{team_name}**")
            cols = st.columns(max(3, min(5, len(agents))))
            for i, agent in enumerate(agents):
                with cols[i % len(cols)]:
                    display = get_agent_display_name(agent)
                    checkbox_states[agent] = st.checkbox(
                        display,
                        value=st.session_state.active_agents.get(agent, True),
                        key=f"main_agent_enable_{agent}",
                    )

        # 更新session_state并计算实时统计
        for agent, state in checkbox_states.items():
            st.session_state.active_agents[agent] = state

        with c3:
            selected_count = len([1 for v in checkbox_states.values() if v])
            total_count = len(checkbox_states)
            st.caption(f"已启用 {selected_count}/{total_count}")


def render_debate_round_controls():
    """主页面：辩论轮次配置（投资辩论与风险辩论）。"""
    with st.expander("🌀 辩论轮次设置", expanded=False):
        # 从已连接的 orchestrator 获取当前默认值
        cur_inv = 1
        cur_risk = 1
        try:
            if st.session_state.get("orchestrator"):
                info = st.session_state.orchestrator.get_workflow_info()
                cur_inv = int(info.get("max_debate_rounds", cur_inv))
                cur_risk = int(info.get("max_risk_debate_rounds", cur_risk))
        except Exception:
            pass

        # 从 session_state 获取保存的值，如果没有则使用默认值
        if "debate_inv_rounds" not in st.session_state:
            st.session_state.debate_inv_rounds = cur_inv
        if "debate_risk_rounds" not in st.session_state:
            st.session_state.debate_risk_rounds = cur_risk

        inv_rounds = st.slider(
            "投资辩论轮次 (bull/bear各发言1次为1轮)",
            min_value=0,
            max_value=10,
            value=st.session_state.debate_inv_rounds,
            step=1,
            key="slider_inv_rounds",
        )
        risk_rounds = st.slider(
            "风险辩论轮次 (激进/保守/中性各发言1次为1轮)",
            min_value=0,
            max_value=9,
            value=st.session_state.debate_risk_rounds,
            step=1,
            key="slider_risk_rounds",
        )

        # 实时保存滑块值到 session_state
        st.session_state.debate_inv_rounds = inv_rounds
        st.session_state.debate_risk_rounds = risk_rounds

        # 显示当前设置
        st.caption(
            f"💡 当前设置: 投资{inv_rounds}轮 风险{risk_rounds}轮 (开始分析时自动应用)"
        )


@st.cache_data(ttl=15)
def get_session_files_list():
    """获取会话文件列表"""
    try:
        dump_dir = Path("src/dump")
        if not dump_dir.exists():
            return []
        return sorted(
            dump_dir.glob("session_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
    except:
        return []


def get_agent_display_name(agent_name):
    """获取智能体显示名称"""
    name_mapping = {
        "company_overview_analyst": "🏢 公司概述分析师",
        "market_analyst": "📈 市场分析师",
        "sentiment_analyst": "😊 情绪分析师",
        "news_analyst": "📰 新闻分析师",
        "fundamentals_analyst": "📋 基本面分析师",
        "shareholder_analyst": "👥 股东分析师",
        "product_analyst": "🏭 产品分析师",
        "bull_researcher": "🐂 看涨研究员",
        "bear_researcher": "🐻 看跌研究员",
        "research_manager": "👔 研究经理",
        "trader": "💼 交易员",
        "aggressive_risk_analyst": "⚡ 激进风险分析师",
        "safe_risk_analyst": "🛡️ 保守风险分析师",
        "neutral_risk_analyst": "⚖️ 中性风险分析师",
        "risk_manager": "🎯 风险经理",
    }
    return name_mapping.get(agent_name, agent_name)


async def connect_orchestrator_async():
    """异步连接WorkflowOrchestrator"""
    if WorkflowOrchestrator is None:
        return False

    try:
        load_dotenv()
        orchestrator = WorkflowOrchestrator()

        # 🔑 关键步骤：按照main.py的方式正确初始化MCP连接
        print("正在初始化MCP连接...")
        await orchestrator.initialize()

        # 获取工具信息验证连接成功
        workflow_info = orchestrator.get_workflow_info()
        tools_count = workflow_info["mcp_tools_info"]["total_tools"]
        print(f"✅ 成功连接到MCP服务器，发现 {tools_count} 个工具")

        st.session_state.orchestrator = orchestrator
        return True
    except Exception as e:
        print(f"连接失败: {e}")
        return False


def connect_orchestrator():
    """连接WorkflowOrchestrator - 同步包装器"""
    try:
        # 使用正确的异步处理方式
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果循环正在运行，创建新的线程运行
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(connect_orchestrator_async())
                    )
                    result = future.result(timeout=30)
                    return result
            else:
                return loop.run_until_complete(connect_orchestrator_async())
        except RuntimeError:
            return asyncio.run(connect_orchestrator_async())
    except Exception as e:
        print(f"连接失败: {e}")
        return False


async def get_system_capabilities_async():
    """异步获取系统能力统计信息（保留简化版本）。"""
    try:
        temp_orchestrator = WorkflowOrchestrator()
        await temp_orchestrator.initialize()
        info = temp_orchestrator.get_workflow_info()
        await temp_orchestrator.close()
        return info
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_system_capabilities():
    """获取系统能力统计信息（保留，作为底部概览使用）。"""
    try:
        if st.session_state.get("orchestrator"):
            return st.session_state.orchestrator.get_workflow_info()
        return asyncio.run(get_system_capabilities_async())
    except Exception:
        return {
            "agents_count": 15,
            "mcp_tools_info": {
                "total_tools": 0,
                "server_count": 1,
                "servers": {},
                "agent_permissions": {},
            },
        }


def show_system_overview():
    """显示系统概览"""
    st.markdown("### 🏛️ AI交易分析实验室")

    # 获取系统能力信息
    capabilities = get_system_capabilities()

    if capabilities and capabilities.get("mcp_tools_info"):
        # 创建概览卡片
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            mcp_info = capabilities.get("mcp_tools_info", {})
            total_tools = mcp_info.get("total_tools", 0)
            if total_tools > 0:
                st.metric("🔧 MCP工具总数", total_tools)
            else:
                st.metric("🔧 MCP工具总数", "未连接")

        with col2:
            server_count = mcp_info.get("server_count", 0)
            if server_count > 0:
                st.metric("🖥️ MCP服务器", server_count)
            else:
                st.metric("🖥️ MCP服务器", "未检测")

        with col3:
            agents_count = capabilities.get("agents_count", 0)
            if agents_count > 0:
                st.metric("🤖 智能体总数", agents_count)
            else:
                st.metric("🤖 智能体总数", "未知")

        with col4:
            enabled_agents = len(
                [
                    agent
                    for agent, enabled in mcp_info.get("agent_permissions", {}).items()
                    if enabled
                ]
            )
            if enabled_agents > 0:
                st.metric("✅ 启用MCP权限", enabled_agents)
            else:
                st.metric("✅ 启用MCP权限", "未配置")

        # 显示详细工具信息
        if total_tools > 0:
            with st.expander("🔍 查看详细工具信息", expanded=False):
                servers_info = mcp_info.get("servers", {})
                for server_name, server_data in servers_info.items():
                    st.markdown(
                        f"**{server_name}** ({server_data.get('tool_count', 0)} 个工具)"
                    )
                    tools = server_data.get("tools", [])
                    for tool in tools[:5]:  # 只显示前5个工具
                        tool_desc = tool.get("description", "无描述")[:50] + (
                            "..." if len(tool.get("description", "")) > 50 else ""
                        )
                        st.markdown(f"  - `{tool.get('name', '未知')}`: {tool_desc}")
                    if len(tools) > 5:
                        st.markdown(f"  - ... 还有 {len(tools) - 5} 个工具")
        else:
            # 如果工具数量为0，显示调试信息
            with st.expander("🔧 MCP连接状态调试", expanded=True):
                if st.session_state.get("orchestrator"):
                    orchestrator = st.session_state.orchestrator
                    if hasattr(orchestrator, "mcp_manager"):
                        mcp_manager = orchestrator.mcp_manager
                        st.write(
                            f"MCP客户端状态: {'已连接' if mcp_manager.client else '未连接'}"
                        )
                        st.write(f"工具列表长度: {len(mcp_manager.tools)}")
                        st.write(
                            f"按服务器分组的工具: {len(mcp_manager.tools_by_server)}"
                        )
                        if mcp_manager.tools:
                            st.write("发现的工具:")
                            for i, tool in enumerate(mcp_manager.tools[:3]):
                                st.write(f"  - {tool.name}: {tool.description}")

                        # 显示连接的服务器信息
                        st.write(
                            f"配置的服务器: {list(mcp_manager.config.get('servers', {}).keys())}"
                        )
                else:
                    st.warning("尚未连接WorkflowOrchestrator")

        # 显示智能体权限状态
        with st.expander("👥 智能体MCP权限状态", expanded=False):
            permissions = mcp_info.get("agent_permissions", {})

            # 按团队分组显示
            teams = {
                "📊 分析师团队": [
                    "company_overview_analyst",
                    "market_analyst",
                    "sentiment_analyst",
                    "news_analyst",
                    "fundamentals_analyst",
                    "shareholder_analyst",
                    "product_analyst",
                ],
                "🔬 研究员团队": ["bull_researcher", "bear_researcher"],
                "👔 管理层": ["research_manager", "trader"],
                "⚖️ 风险管理团队": [
                    "aggressive_risk_analyst",
                    "safe_risk_analyst",
                    "neutral_risk_analyst",
                    "risk_manager",
                ],
            }

            for team_name, team_agents in teams.items():
                st.markdown(f"**{team_name}**")
                team_cols = st.columns(len(team_agents))
                for i, agent in enumerate(team_agents):
                    with team_cols[i]:
                        status = "✅" if permissions.get(agent, False) else "❌"
                        agent_display = get_agent_display_name(agent)
                        st.markdown(
                            f"{status} {agent_display}",
                            help=f"{agent}: {'启用' if permissions.get(agent, False) else '禁用'}",
                        )
    else:
        # 如果无法获取系统信息，显示简化的状态信息
        st.info("🔄 正在初始化系统，请稍候...")

    st.markdown("---")


def show_real_time_analysis():
    """实时分析模块 - 自动连接版本"""
    if WorkflowOrchestrator is None:
        st.error("😱 无法加载WorkflowOrchestrator，请检查后端配置")
        return

    # 自动连接系统（如果未连接）
    if not st.session_state.get("orchestrator"):
        if connect_orchestrator():
            st.session_state.auto_connected = True

    # 简化的输入和控制
    query = st.text_input(
        "输入查询",
        placeholder="例如：给我分析一下600833吧",
        key="analysis_query_simple",
    )

    # 简化的按钮布局 - 只显示开始/停止
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.session_state.analysis_running:
            if st.button("⏹️ 停止分析", use_container_width=True):
                stop_analysis()
        else:
            orchestrator_connected = st.session_state.get("orchestrator") is not None
            analysis_disabled = not query or not orchestrator_connected
            if st.button(
                "🚀 开始分析", disabled=analysis_disabled, use_container_width=True
            ):
                if query:
                    start_analysis(query)
                    # 立即刷新，让“当前任务进度”尽快显示新任务
                    try:
                        get_all_sessions_progress.clear()
                    except Exception:
                        pass
                    st.rerun()

    with btn_col2:
        # 不在此处显示进度；只提示查看“当前任务进度”模块
        if st.session_state.get("analysis_running") or st.session_state.get(
            "analysis_completed"
        ):
            st.caption("进度已移动到下方 ‘当前任务进度’ 模块查看")
        else:
            if st.session_state.get("orchestrator"):
                st.success("🟢 系统已就绪")
            else:
                st.error("🔴 系统未连接")

    # 完成提示
    if st.session_state.analysis_completed:
        st.success("✅ 分析完成！请查看下方结果。")


def show_history_management():
    """历史会话管理 - 超简化版本"""
    # 获取所有JSON文件
    json_files = get_session_files_list()
    if not json_files:
        st.info("📭 暂无历史分析数据")
        return

    # 只纳入已完成任务的会话；标签显示用户问题而非文件名
    completed_files = []
    file_options = []
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if (data.get("status") or "").lower() != "completed":
                continue
            file_time = datetime.fromtimestamp(json_file.stat().st_mtime)
            time_str = file_time.strftime("%m-%d %H:%M")
            user_query = (data.get("user_query") or "").strip()
            label = (
                f"(无查询) - {time_str}"
                if not user_query
                else f"{(user_query[:40] + '...') if len(user_query) > 40 else user_query} - {time_str}"
            )
            completed_files.append(json_file)
            file_options.append(label)
        except Exception:
            continue

    if not completed_files:
        st.info("📝 暂无已完成的历史会话")
        return

    # 下拉选择：默认占位提示“请选择历史会话…”，用户需主动展开选择
    if "history_selected_index" not in st.session_state:
        st.session_state.history_selected_index = -1

    def on_session_change():
        selected_idx = st.session_state.history_selector_simple
        if (
            isinstance(selected_idx, int)
            and selected_idx >= 0
            and selected_idx < len(completed_files)
        ):
            selected_file = str(completed_files[selected_idx])
            load_session_data(selected_file)
            st.session_state.history_selected_index = selected_idx

    st.selectbox(
        "选择历史会话",
        list(range(len(file_options))),
        index=None,
        format_func=lambda i: file_options[i],
        key="history_selector_simple",
        on_change=on_session_change,
        placeholder="请选择历史会话…",
    )

    # 静默加载会话信息，不显示提示
    if st.session_state.current_session_data:
        # 静默处理，不显示任何提示
        pass


def show_export_options():
    """导出选项 - 包含完整版和关键分析版"""
    if (
        not st.session_state.current_session_data
        or not st.session_state.selected_session_file
    ):
        st.info("请先加载会话数据")
        return

    # 完整版导出
    st.markdown("**📄 完整报告导出**")
    export_col1, export_col2, export_col3 = st.columns(3)

    with export_col1:
        if st.button("📄 导出MD", key="export_md_full"):
            export_to_markdown(key_agents_only=False)

    with export_col2:
        if st.button("📄 导出PDF", key="export_pdf_full"):
            export_to_pdf(key_agents_only=False)

    with export_col3:
        if st.button("📄 导出Word", key="export_word_full"):
            export_to_docx(key_agents_only=False)

    st.markdown("---")

    # 关键分析导出
    st.markdown("**🎯 关键分析导出** (仅研究经理、交易员、风险经理)")
    key_col1, key_col2, key_col3 = st.columns(3)

    with key_col1:
        if st.button("🎯 关键MD", key="export_md_key"):
            export_to_markdown(key_agents_only=True)

    with key_col2:
        if st.button("🎯 关键PDF", key="export_pdf_key"):
            export_to_pdf(key_agents_only=True)

    with key_col3:
        if st.button("🎯 关键Word", key="export_word_key"):
            export_to_docx(key_agents_only=True)


def show_analysis_results():
    """分析结果展示 - 简化版本"""
    if not st.session_state.current_session_data:
        st.info("请先运行分析或加载历史会话查看结果")
        return

    data = st.session_state.current_session_data

    # 显示会话基本信息
    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.metric("会话ID", data.get("session_id", "N/A")[:8] + "...")
    with info_col2:
        st.metric("状态", data.get("status", "N/A"))
    with info_col3:
        completed_agents = len(
            [
                agent
                for agent in data.get("agents", [])
                if agent.get("status") == "completed"
            ]
        )
        st.metric("完成智能体", f"{completed_agents}/{len(data.get('agents', []))}")

    # 显示用户查询
    if data.get("user_query"):
        st.markdown("**🔍 分析查询:**")
        st.info(data["user_query"])

    # 智能体结果标签页
    if data.get("agents"):
        completed_agents = [
            agent for agent in data["agents"] if agent.get("status") == "completed"
        ]

        if completed_agents:
            # 按智能体类型分组
            agent_groups = {
                "📊 分析师团队": [
                    "company_overview_analyst",
                    "market_analyst",
                    "sentiment_analyst",
                    "news_analyst",
                    "fundamentals_analyst",
                    "shareholder_analyst",
                    "product_analyst",
                ],
                "🔄 看涨看跌辩论": ["bull_researcher", "bear_researcher"],
                "👔 研究与交易": ["research_manager", "trader"],
                "⚖️ 风险管理": [
                    "aggressive_risk_analyst",
                    "safe_risk_analyst",
                    "neutral_risk_analyst",
                    "risk_manager",
                ],
            }

            group_tabs = st.tabs(list(agent_groups.keys()))

            for tab_idx, (group_name, agent_names) in enumerate(agent_groups.items()):
                with group_tabs[tab_idx]:
                    group_agents = [
                        agent
                        for agent in completed_agents
                        if agent.get("agent_name") in agent_names
                    ]

                    if group_agents:
                        for agent in group_agents:
                            show_agent_result(agent)
                    else:
                        st.info(f"{group_name.split(' ', 1)[1]}暂无完成的分析结果")
        else:
            st.info("该会话中暂无完成的智能体分析结果")
    else:
        st.info("该会话中暂无智能体数据")


def show_agent_result(agent: Dict[str, Any]):
    """显示单个智能体结果 - 简洁直接模式，不搞复杂的摘要展开"""
    agent_name = agent.get("agent_name", "Unknown")
    display_name = get_agent_display_name(agent_name)
    result_content = agent.get("result", "")

    if not result_content:
        with st.expander(display_name, expanded=False):
            st.info("该智能体暂无分析结果")
        return

    # 直接显示完整内容，删除有问题的摘要展开功能
    with st.expander(display_name, expanded=False):
        st.markdown(result_content)


# 导出功能
def export_to_markdown(key_agents_only: bool = False):
    """导出Markdown"""
    if not JSONToMarkdownConverter:
        st.error("❌ Markdown导出器不可用")
        return

    try:
        converter = JSONToMarkdownConverter("src/dump", key_agents_only=key_agents_only)
        result = converter.convert_json_to_markdown(
            st.session_state.selected_session_file
        )
        if result and os.path.exists(result):
            export_type = "关键分析" if key_agents_only else "完整"
            st.success(f"✅ {export_type}Markdown导出成功: {result}")

            # 提供下载链接
            with open(result, "r", encoding="utf-8") as f:
                content = f.read()

            st.download_button(
                label="⬇️ 下载Markdown文件",
                data=content,
                file_name=f"{Path(result).name}",
                mime="text/markdown",
            )
        else:
            st.error("❌ Markdown导出失败")
    except Exception as e:
        st.error(f"❌ 导出错误: {str(e)}")


def export_to_pdf(key_agents_only: bool = False):
    """导出PDF"""
    if not MarkdownToPDFConverter:
        st.error("❌ PDF导出器不可用")
        return

    try:
        converter = MarkdownToPDFConverter(
            "src/dump", include_toc=True, key_agents_only=key_agents_only
        )
        result = converter.convert_json_to_pdf_via_markdown(
            st.session_state.selected_session_file
        )
        if result and os.path.exists(result):
            export_type = "关键分析" if key_agents_only else "完整"
            st.success(f"✅ {export_type}PDF导出成功: {result}")

            # 提供下载链接
            with open(result, "rb") as f:
                content = f.read()

            st.download_button(
                label="⬇️ 下载PDF文件",
                data=content,
                file_name=f"{Path(result).name}",
                mime="application/pdf",
            )
        else:
            st.error("❌ PDF导出失败")
    except Exception as e:
        st.error(f"❌ PDF导出错误: {str(e)}")


def export_to_docx(key_agents_only: bool = False):
    """导出Word文档"""
    if not MarkdownToDocxConverter:
        st.error("❌ DOCX导出器不可用")
        return

    try:
        converter = MarkdownToDocxConverter("src/dump", key_agents_only=key_agents_only)
        result = converter.convert_json_to_docx_via_markdown(
            st.session_state.selected_session_file
        )
        if result and os.path.exists(result):
            export_type = "关键分析" if key_agents_only else "完整"
            st.success(f"✅ {export_type}DOCX导出成功: {result}")

            # 提供下载链接
            with open(result, "rb") as f:
                content = f.read()

            st.download_button(
                label="⬇️ 下载Word文件",
                data=content,
                file_name=f"{Path(result).name}",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        else:
            st.error("❌ DOCX导出失败")
    except Exception as e:
        st.error(f"❌ DOCX导出错误: {str(e)}")


def load_session_data(json_file_path: str):
    """加载会话数据"""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        st.session_state.selected_session_file = json_file_path
        st.session_state.current_session_data = session_data
        # 静默加载，不显示任何提示，不调用st.rerun()
    except Exception as e:
        # 静默处理错误，不在前端显示
        print(f"加载失败: {str(e)}")


@st.cache_data(ttl=5)
def get_real_analysis_progress():
    """从真实的会话JSON文件获取进度"""
    try:
        dump_dir = Path("src/dump")
        if not dump_dir.exists():
            return None

        # 查找最新的会话文件
        session_files = list(dump_dir.glob("session_*.json"))
        if not session_files:
            return None

        latest_session = max(session_files, key=lambda f: f.stat().st_mtime)

        # 解析会话进度
        with open(latest_session, "r", encoding="utf-8") as f:
            data = json.load(f)

        agents = data.get("agents", [])
        # 以会话中记录的 active_agents 为准；若缺省则回退到15
        total_agents = len(data.get("active_agents", [])) or 15
        completed_agents = len([a for a in agents if a.get("status") == "completed"])

        progress = (completed_agents / total_agents) * 100 if total_agents > 0 else 0

        # 生成状态描述
        if data.get("status") == "completed":
            status = "分析完成"
        elif data.get("status") == "cancelled":
            status = "分析已取消"
        elif completed_agents == 0:
            status = "正在初始化..."
        else:
            running_agent = next(
                (a for a in agents if a.get("status") == "running"), None
            )
            if running_agent:
                agent_name = running_agent.get("agent_name", "未知智能体")
                display_name = get_agent_display_name(agent_name)
                status = f"正在执行: {display_name}"
            else:
                status = f"已完成 {completed_agents} 个智能体"

        return {
            "progress": progress,
            "status": status,
            "completed_agents": completed_agents,
            "total_agents": total_agents,
            "session_file": str(latest_session),
        }

    except Exception as e:
        return None


@st.cache_data(ttl=10)
def get_all_sessions_progress():
    """扫描所有会话文件，返回进度汇总列表。"""
    sessions_info: List[Dict[str, Any]] = []
    dump_dir = Path("src/dump")
    try:
        if not dump_dir.exists():
            return []
        session_files = list(dump_dir.glob("session_*.json"))
        for sf in session_files:
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                agents = data.get("agents", [])
                total_agents = len(data.get("active_agents", [])) or 15
                completed_agents = len(
                    [a for a in agents if a.get("status") == "completed"]
                )
                progress = (
                    (completed_agents / total_agents) * 100 if total_agents > 0 else 0
                )
                raw_status = (data.get("status") or "").lower()
                # 推导更稳健的任务状态
                if raw_status == "completed" or completed_agents >= total_agents:
                    status = "completed"
                elif raw_status == "cancelled":
                    status = "cancelled"
                else:
                    if any(
                        (a.get("status") or "").lower() == "running" for a in agents
                    ):
                        status = "running"
                    elif agents and completed_agents < total_agents:
                        status = "running"
                    else:
                        status = raw_status or "unknown"
                user_query = (data.get("user_query") or "").strip()
                session_id = data.get("session_id", sf.stem)
                created_at = data.get("created_at", "")
                # 解析时间
                try:
                    created_dt = (
                        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if created_at
                        else datetime.fromtimestamp(sf.stat().st_mtime)
                    )
                except Exception:
                    created_dt = datetime.fromtimestamp(sf.stat().st_mtime)
                sessions_info.append(
                    {
                        "file": str(sf),
                        "session_id": session_id,
                        "user_query": user_query,
                        "status": status,
                        "completed": completed_agents,
                        "total": total_agents,
                        "progress": progress,
                        "created_at": created_dt,
                        "mtime": sf.stat().st_mtime,
                    }
                )
            except Exception:
                continue
        # 最新在前
        sessions_info.sort(key=lambda x: x["mtime"], reverse=True)
        return sessions_info
    except Exception:
        return []


def show_tasks_overview():
    """展示当前任务进度（多任务）。"""
    st.markdown("### 🧵 当前任务进度")
    sessions = get_all_sessions_progress()
    if not sessions:
        st.info("当前没有会话任务记录")
        return

    # 仅显示“正在运行”的任务，并且限定为最近一段时间内活跃的会话（根据文件修改时间判断）
    recent_minutes = 5  # 认为5分钟内修改的会话仍在活跃
    now_ts = datetime.now().timestamp()
    filtered = [
        s
        for s in sessions
        if (
            (s["status"] == "running")
            or (s["progress"] < 100 and s["status"] not in ("completed", "cancelled"))
        )
        and (now_ts - s["mtime"]) <= recent_minutes * 60
    ]
    if not filtered:
        st.info("暂无进行中的任务")
        return

    for s in filtered[:20]:  # 最多显示20条，避免过长
        q = s["user_query"] or s["session_id"]
        title = q if len(q) <= 50 else q[:50] + "..."
        c1, c2, c3, c4 = st.columns([3, 2, 4, 1])
        with c1:
            st.markdown(f"**{title}**")
            st.caption(s["created_at"].strftime("%m-%d %H:%M"))
        with c2:
            emoji = (
                "✅"
                if s["status"] == "completed"
                else "🔄"
                if s["status"] == "running"
                else "⏳"
            )
            st.markdown(f"{emoji} {s['status']}")
            st.caption(f"{s['completed']}/{s['total']}")
        with c3:
            st.progress(min(max(s["progress"], 0), 100) / 100.0)
        with c4:
            if st.button("查看", key=f"view_{s['session_id']}"):
                load_session_data(s["file"])
                st.rerun()


def get_max_concurrent_limit() -> int:
    """从 .env 读取最大并发任务上限，默认 2。"""
    try:
        val = os.getenv("MAX_CONCURRENT_ANALYSIS", "2").strip()
        limit = int(val)
        return max(1, limit)
    except Exception:
        return 2


def get_current_running_tasks_count() -> int:
    """统计当前正在运行的任务数量（使用与任务列表一致的判定逻辑）。"""
    sessions = get_all_sessions_progress()
    if not sessions:
        return 0
    now_ts = datetime.now().timestamp()
    # 使用与 show_tasks_overview 相同的 5 分钟活跃窗口
    recent_minutes = 5
    running = [
        s
        for s in sessions
        if (
            (s["status"] == "running")
            or (s["progress"] < 100 and s["status"] not in ("completed", "cancelled"))
        )
        and (now_ts - s["mtime"]) <= recent_minutes * 60
    ]
    return len(running)


def start_analysis(query: str):
    """开始分析"""
    # 检查连接状态
    if not st.session_state.get("orchestrator"):
        st.error("系统未连接，无法开始分析")
        return

    # 并发上限控制
    max_limit = get_max_concurrent_limit()
    running_count = get_current_running_tasks_count()
    if running_count >= max_limit:
        st.warning(
            f"当前运行中的任务已达上限（{running_count}/{max_limit}），请稍后再试或等待任务完成"
        )
        return

    # 选取本轮启用的智能体
    try:
        selected_agents = [
            a for a, enabled in st.session_state.active_agents.items() if enabled
        ]
    except Exception:
        selected_agents = []

    # 获取前端设置的辩论轮次并自动应用
    try:
        # 从前端获取当前设置的辩论轮次
        cur_inv = 1
        cur_risk = 1
        if st.session_state.get("orchestrator"):
            info = st.session_state.orchestrator.get_workflow_info()
            cur_inv = int(info.get("max_debate_rounds", cur_inv))
            cur_risk = int(info.get("max_risk_debate_rounds", cur_risk))

        # 应用辩论轮次设置（防御性检查：至少为1轮）
        if (
            "debate_inv_rounds" in st.session_state
            and "debate_risk_rounds" in st.session_state
        ):
            inv_rounds = max(1, st.session_state.debate_inv_rounds)
            risk_rounds = max(1, st.session_state.debate_risk_rounds)
            st.session_state.orchestrator.set_debate_rounds(inv_rounds, risk_rounds)
            print(f"自动应用辩论轮次设置: 投资={inv_rounds}, 风险={risk_rounds}")
    except Exception as e:
        print(f"应用辩论轮次设置失败: {e}")

    # 重置状态
    st.session_state.analysis_running = True
    st.session_state.analysis_completed = False
    st.session_state.analysis_cancelled = False

    # 将orchestrator传递给分析函数
    run_analysis_sync(query, st.session_state.orchestrator, selected_agents)
    # 清理会话列表缓存，确保新任务能立刻出现在任务进度中
    try:
        get_all_sessions_progress.clear()
    except Exception:
        pass


def run_analysis_sync(query: str, orchestrator, active_agents: List[str]):
    """在后台线程中运行分析，避免阻塞Streamlit主线程"""
    import threading

    class AnalysisState:
        def __init__(self):
            self.cancelled = False
            self.running = True
            self.completed = False
            self.result = None
            self.error = None

    # 创建状态对象
    analysis_state = AnalysisState()

    def run_analysis_thread():
        """后台线程执行分析"""
        try:
            load_dotenv()

            # 检查是否已被取消
            if analysis_state.cancelled:
                analysis_state.running = False
                return

            # 在新的事件循环中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    run_single_analysis_async_safe(
                        query, orchestrator, analysis_state, active_agents
                    )
                )

                # 再次检查是否已被取消
                if analysis_state.cancelled:
                    analysis_state.running = False
                    return

                # 分析成功
                analysis_state.result = result
                analysis_state.completed = True
                analysis_state.running = False

            finally:
                loop.close()

        except Exception as e:
            # 检查是否是取消导致的异常
            if not analysis_state.cancelled:
                error_msg = str(e)
                analysis_state.error = error_msg
            analysis_state.running = False
            analysis_state.completed = False

    # 启动后台线程
    thread = threading.Thread(target=run_analysis_thread, daemon=True)
    thread.start()

    # 存储线程引用和状态对象
    st.session_state.analysis_thread = thread
    st.session_state.analysis_state_obj = analysis_state


async def run_single_analysis_async_safe(
    user_query: str, orchestrator, analysis_state, active_agents: List[str]
) -> Optional[dict]:
    """安全的异步分析函数"""
    try:
        # 检查取消状态
        if analysis_state.cancelled:
            return None

        workflow_info = orchestrator.get_workflow_info()
        enabled_agents = orchestrator.get_enabled_agents()

        # 检查取消状态
        if analysis_state.cancelled:
            return None

        # 创建取消检查器函数
        def cancel_checker():
            return analysis_state.cancelled

        # 传入本轮启用的智能体列表
        try:
            orchestrator.set_active_agents(active_agents)
        except Exception:
            pass
        result = await orchestrator.run_analysis(
            user_query, cancel_checker, active_agents=active_agents
        )

        # 检查取消状态
        if analysis_state.cancelled:
            return None

        return result

    except Exception as e:
        # 检查是否是取消导致的异常
        if analysis_state.cancelled:
            return None
        raise


def stop_analysis():
    """停止正在运行的分析"""
    st.session_state.analysis_cancelled = True
    st.session_state.analysis_running = False

    # 设置状态对象的取消标志
    analysis_state_obj = st.session_state.get("analysis_state_obj")
    if analysis_state_obj:
        analysis_state_obj.cancelled = True
        analysis_state_obj.running = False


def main():
    """主界面 - 精简信息架构，结果优先"""
    # 加载样式
    load_page_styles()

    # 不再使用侧边栏，跳过强制可见逻辑

    # 显示贴顶抬头（紧贴页面最上方）
    render_top_header()

    # 主页面：智能体启用开关（置于关键操作区之前，便于先选后跑）
    render_main_agent_selector()
    render_debate_round_controls()

    # 采用三段式结构：关键操作区（上）→ 工作区（中）→ 结果与导出（下）
    st.markdown("---")

    # 1) 关键操作区：输入 + 快速状态
    op_c1, op_c2, op_c3 = st.columns([1, 1, 1])
    with op_c1:
        st.markdown("### 🔍 实时分析")
        show_real_time_analysis()
    with op_c2:
        st.markdown("### 📚 历史会话")
        show_history_management()
    with op_c3:
        st.markdown("### 🧭 系统状态")
        env_status = "✅" if Path(".env").exists() else "❌"
        mcp_status = "✅" if Path("mcp_config.json").exists() else "❌"
        status_c1, status_c2 = st.columns(2)
        with status_c1:
            st.metric("环境", env_status)
        with status_c2:
            st.metric("MCP", mcp_status)

    # 不再渲染顶部侧边栏开关

    # 2) 多任务进度总览
    st.markdown("---")
    show_tasks_overview()

    # 3) 结果与导出
    st.markdown("---")
    res_c1, res_c2 = st.columns([3, 1])
    with res_c1:
        st.markdown("### 📈 分析结果")
        show_analysis_results()
    with res_c2:
        st.markdown("### 📤 报告导出")
        with st.expander("📌 操作说明（可收起）", expanded=False):
            st.caption(
                "输入查询后点击‘开始分析’，历史会话可直接切换查看结果；导出在本区‘报告导出’模块。"
            )
        show_export_options()

    # 系统概览移至页面底部，避免打断主流程
    st.markdown("---")
    with st.expander("🏛️ AI交易分析实验室 - 系统概览", expanded=False):
        show_system_overview()


if __name__ == "__main__":
    main()
