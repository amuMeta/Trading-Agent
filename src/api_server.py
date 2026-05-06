import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.errors import (
    build_error_response,
    generic_exception_handler,
    http_exception_handler,
    trading_agents_exception_handler,
    validation_exception_handler,
)
from src.core.exceptions import (
    APIExportError,
    APITaskLimitError,
    APITaskNotFoundError,
    RAGEngineNotAvailableError,
    TradingAgentsException,
)
from src.core.paths import SESSION_DIR
from src.export.json_to_markdown import JSONToMarkdownConverter
from src.export.md2docx import MarkdownToDocxConverter
from src.export.md2pdf import MarkdownToPDFConverter
from src.mcp.http_client import StockMCPHTTPClient as HttpClient
from src.workflow_orchestrator import WorkflowOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DUMP_DIR = SESSION_DIR
MAX_RECENT_MINUTES = 5


def get_agent_display_name(agent_name: str) -> str:
    mapping = {
        "company_overview_analyst": "公司概述分析师",
        "market_analyst": "市场分析师",
        "sentiment_analyst": "情绪分析师",
        "news_analyst": "新闻分析师",
        "fundamentals_analyst": "基本面分析师",
        "shareholder_analyst": "股东分析师",
        "product_analyst": "产品分析师",
        "bull_researcher": "看涨研究员",
        "bear_researcher": "看跌研究员",
        "research_manager": "研究经理",
        "trader": "交易员",
        "aggressive_risk_analyst": "激进风险分析师",
        "safe_risk_analyst": "保守风险分析师",
        "neutral_risk_analyst": "中性风险分析师",
        "risk_manager": "风险经理",
    }
    return mapping.get(agent_name, agent_name)


def list_session_files() -> List[Path]:
    if not DUMP_DIR.exists():
        return []
    return sorted(
        (
            f
            for f in DUMP_DIR.glob("session_*.json")
            if f.suffix.lower() not in (".corrupted", ".bad", ".broken")
        ),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARN] 读取会话文件失败 {path.name}: {e}")
        return None


def parse_session_progress(sf: Path) -> Optional[Dict[str, Any]]:
    try:
        data = read_json(sf)
        agents = data.get("agents", [])
        total_agents = len(data.get("active_agents", [])) or 15
        completed_agents = len([a for a in agents if a.get("status") == "completed"])
        progress = (completed_agents / total_agents) * 100 if total_agents > 0 else 0
        raw_status = (data.get("status") or "").lower()
        if raw_status == "completed" or completed_agents >= total_agents:
            status = "completed"
        elif raw_status == "cancelled":
            status = "cancelled"
        else:
            if any((a.get("status") or "").lower() == "running" for a in agents):
                status = "running"
            elif agents and completed_agents < total_agents:
                status = "running"
            else:
                status = raw_status or "unknown"
        user_query = (data.get("user_query") or "").strip()
        created_at = data.get("created_at", "")
        try:
            created_dt = (
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_at
                else datetime.fromtimestamp(sf.stat().st_mtime)
            )
        except Exception:
            created_dt = datetime.fromtimestamp(sf.stat().st_mtime)
        return {
            "file": str(sf),
            "session_id": data.get("session_id", sf.stem),
            "user_query": user_query,
            "status": status,
            "completed": completed_agents,
            "total": total_agents,
            "progress": progress,
            "created_at": created_dt.isoformat(),
            "mtime": sf.stat().st_mtime,
        }
    except Exception:
        return None


class StartAnalysisReq(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    active_agents: List[str] = Field(default_factory=list)
    investment_rounds: int = Field(default=1, ge=1, le=10)
    risk_rounds: int = Field(default=1, ge=1, le=9)

    @classmethod
    def validate(cls, data):
        validated = super().validate(data)
        query = validated.query.strip() if validated.query else ""
        if len(query) < 1:
            raise ValueError("查询内容不能为空")
        validated.query = query
        return validated


class ExportReq(BaseModel):
    session_file: Optional[str] = Field(default=None, max_length=500)
    session_id: Optional[str] = Field(default=None, max_length=64)
    key_agents_only: bool = False

    @classmethod
    def validate(cls, data):
        validated = super().validate(data)
        if not validated.session_file and not validated.session_id:
            raise ValueError("session_file or session_id is required")
        return validated


class TaskRecord:
    def __init__(self, task_id: str, query: str, active_agents: List[str]):
        self.task_id = task_id
        self.query = query
        self.active_agents = active_agents
        self.status = "running"
        self.error = ""
        self.session_id = ""
        self.cancelled = False
        self.created_at = datetime.now().isoformat()
        self.finished_at = ""
        self._orchestrator: Optional[WorkflowOrchestrator] = None


TASKS: Dict[str, TaskRecord] = {}
TASK_LOCK = threading.Lock()

app = FastAPI(title="TradingAgents API", version="1.0.0")

rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
if rate_limit_enabled:
    from src.core.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, enabled=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(TradingAgentsException, trading_agents_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

from fastapi import WebSocket, WebSocketDisconnect
from src.core.websocket import get_connection_manager


@app.websocket("/ws/analysis/{task_id}")
async def websocket_analysis(websocket: WebSocket, task_id: str):
    """
    分析进度WebSocket端点

    连接URL: ws://host/ws/analysis/{task_id}

    消息格式:
    - progress: 进度更新
    - agent_start: 智能体开始
    - agent_complete: 智能体完成
    - agent_error: 智能体错误
    - debate: 辩论更新
    - task_complete: 任务完成
    - task_error: 任务错误
    """
    manager = get_connection_manager()
    await websocket.accept()

    connection_id = manager.connect(websocket, task_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "connection_id": connection_id,
            "message": "WebSocket连接已建立"
        })

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message.get("type") == "subscribe":
                    other_task = message.get("task_id")
                    if other_task:
                        manager._subscribers[connection_id].add(other_task)

                elif message.get("type") == "unsubscribe":
                    other_task = message.get("task_id")
                    if other_task and other_task in manager._subscribers.get(connection_id, set()):
                        manager._subscribers[connection_id].discard(other_task)

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "无效的JSON格式"
                })

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, connection_id)


@app.websocket("/ws/all")
async def websocket_all(websocket: WebSocket):
    """
    全局WebSocket端点（接收所有任务广播）

    连接URL: ws://host/ws/all
    """
    manager = get_connection_manager()
    await websocket.accept()

    connection_id = manager.connect(websocket, None)

    try:
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "WebSocket连接已建立（全局订阅）"
        })

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, connection_id)


@app.get("/api/system/connect")
async def connect_system():
    load_dotenv()
    orchestrator = WorkflowOrchestrator()
    await orchestrator.initialize()
    info = orchestrator.get_workflow_info()
    await orchestrator.close()
    return {"ok": True, "workflow_info": info}


@app.get("/api/system/capabilities")
async def system_capabilities():
    return await connect_system()


@app.get("/api/system/health")
async def system_health():
    from src.core.health import system_health_check
    return await system_health_check()


@app.get("/api/system/health/live")
async def system_liveness():
    from src.core.health import system_liveness_check
    return await system_liveness_check()


@app.get("/api/system/health/ready")
async def system_readiness():
    from src.core.health import system_readiness_check
    return await system_readiness_check()


@app.get("/api/system/info")
async def system_info():
    """获取系统详细信息"""
    from src.core.health import get_health_checker

    checker = get_health_checker()
    checker.run_all_checks()

    return {
        "version": "1.0.0",
        "environment": "development" if os.getenv("DEBUG") else "production",
        "python_version": None,
        "checks": checker.checks,
    }


@app.get("/api/agents/config")
async def agents_config():
    load_dotenv()
    orchestrator = WorkflowOrchestrator()
    await orchestrator.initialize()
    info = orchestrator.get_workflow_info()
    await orchestrator.close()
    teams = {
        "analysts": [
            "company_overview_analyst",
            "market_analyst",
            "sentiment_analyst",
            "news_analyst",
            "fundamentals_analyst",
            "shareholder_analyst",
            "product_analyst",
        ],
        "researchers": ["bull_researcher", "bear_researcher"],
        "managers": ["research_manager", "trader"],
        "risk": [
            "aggressive_risk_analyst",
            "safe_risk_analyst",
            "neutral_risk_analyst",
            "risk_manager",
        ],
    }
    all_agents = list(info.get("agents_info", {}).keys())
    return {
        "teams": teams,
        "all_agents": all_agents,
        "defaults": {name: True for name in all_agents},
        "display_names": {name: get_agent_display_name(name) for name in all_agents},
        "debate_ranges": {
            "investment": {"min": 0, "max": 10},
            "risk": {"min": 0, "max": 9},
        },
    }


def _run_task(record: TaskRecord, req: StartAnalysisReq):
    async def _run():
        orchestrator = WorkflowOrchestrator()
        record._orchestrator = orchestrator
        try:
            await orchestrator.initialize()
            # 防御性检查：确保辩论轮次至少为1
            inv_rounds = max(1, req.investment_rounds)
            risk_rounds = max(1, req.risk_rounds)
            orchestrator.set_debate_rounds(inv_rounds, risk_rounds)
            orchestrator.set_active_agents(req.active_agents)

            def cancel_checker():
                return record.cancelled

            await orchestrator.run_analysis(
                req.query,
                cancel_checker=cancel_checker,
                active_agents=req.active_agents,
            )
            if orchestrator.progress_manager:
                record.session_id = orchestrator.progress_manager.session_id
            record.status = "cancelled" if record.cancelled else "completed"
        except Exception as e:
            record.status = "failed"
            record.error = str(e)
        finally:
            record.finished_at = datetime.now().isoformat()
            try:
                await orchestrator.close()
            except Exception:
                pass

    asyncio.run(_run())


@app.post("/api/analysis/start")
async def start_analysis(req: StartAnalysisReq):
    max_limit = int(os.getenv("MAX_CONCURRENT_ANALYSIS", "2"))
    running_count = len([t for t in TASKS.values() if t.status == "running"])
    if running_count >= max_limit:
        raise APITaskLimitError(
            message=f"运行中的任务数量已达到上限 ({running_count}/{max_limit})",
            details={"running_count": running_count, "max_limit": max_limit}
        )

    task_id = uuid.uuid4().hex[:12]
    record = TaskRecord(
        task_id=task_id, query=req.query, active_agents=req.active_agents
    )
    with TASK_LOCK:
        TASKS[task_id] = record

    thread = threading.Thread(target=_run_task, args=(record, req), daemon=True)
    thread.start()
    return {"task_id": task_id, "status": "running", "session_id": record.session_id}


@app.post("/api/analysis/{task_id}/cancel")
async def cancel_analysis(task_id: str):
    record = TASKS.get(task_id)
    if not record:
        raise APITaskNotFoundError(
            message=f"任务不存在: {task_id}",
            details={"task_id": task_id}
        )
    record.cancelled = True
    record.status = "cancelling"
    return {"ok": True, "task_id": task_id, "status": "cancelling"}


@app.get("/api/analysis/{task_id}/progress")
async def analysis_progress(task_id: str):
    record = TASKS.get(task_id)
    if not record:
        raise APITaskNotFoundError(
            message=f"任务不存在: {task_id}",
            details={"task_id": task_id}
        )

    session_data = None
    if record.session_id:
        path = DUMP_DIR / f"session_{record.session_id}.json"
        if path.exists():
            session_data = read_json(path)
    elif list_session_files():
        session_data = read_json(list_session_files()[0])
        if session_data:
            record.session_id = session_data.get("session_id", "")

    return {
        "task_id": task_id,
        "task_status": record.status,
        "error": record.error,
        "session_id": record.session_id,
        "session_data": session_data,
    }


@app.get("/api/analysis/tasks")
async def analysis_tasks():
    sessions: List[Dict[str, Any]] = []
    for sf in list_session_files():
        parsed = parse_session_progress(sf)
        if parsed:
            sessions.append(parsed)
    sessions.sort(key=lambda x: x["mtime"], reverse=True)
    now_ts = datetime.now().timestamp()
    active = [
        s
        for s in sessions
        if (
            (s["status"] == "running")
            or (s["progress"] < 100 and s["status"] not in ("completed", "cancelled"))
        )
        and (now_ts - s["mtime"]) <= MAX_RECENT_MINUTES * 60
    ]
    return {"tasks": active, "all_sessions": sessions}


@app.get("/api/analysis/{session_id}/evaluate")
async def evaluate_session(session_id: str):
    """
    评估会话分析质量（实验数据收集接口）

    返回性能指标和分析质量评估，用于论文实验数据支撑
    """
    from src.core.exceptions import DatabaseSessionNotFoundError

    path = DUMP_DIR / f"session_{session_id}.json"
    if not path.exists():
        raise DatabaseSessionNotFoundError(
            message=f"会话不存在: {session_id}",
            details={"session_id": session_id}
        )

    data = read_json(path)
    if data is None:
        raise APIExportError(
            message="会话数据已损坏，无法读取",
            details={"session_id": session_id}
        )

    # 提取性能指标
    metrics = data.get("metrics", {})
    agents = data.get("agents", [])
    mcp_calls = data.get("mcp_calls", [])
    errors = data.get("errors", [])
    warnings = data.get("warnings", [])

    # 计算评估指标
    total_duration = metrics.get("total_duration_seconds", 0)
    completed_agents = [a for a in agents if a.get("status") == "completed"]
    failed_agents = [a for a in agents if a.get("status") == "failed"]
    agent_executions = metrics.get("agent_executions", [])

    # 智能体执行效率
    avg_agent_duration = 0.0
    if agent_executions:
        total_agent_time = sum(e.get("total_duration", 0) for e in agent_executions)
        avg_agent_duration = total_agent_time / len(agent_executions)

    # MCP工具使用统计
    total_mcp_calls = len(mcp_calls)
    successful_mcp = sum(1 for c in mcp_calls if c.get("success", True))
    mcp_success_rate = successful_mcp / total_mcp_calls if total_mcp_calls > 0 else 1.0

    # 各阶段耗时分析
    stage_durations = {}
    for agent in agents:
        if agent.get("start_time") and agent.get("end_time"):
            try:
                start = datetime.fromisoformat(agent["start_time"])
                end = datetime.fromisoformat(agent["end_time"])
                duration = (end - start).total_seconds()
                stage_durations[agent["agent_name"]] = round(duration, 3)
            except Exception:
                pass

    # 分析报告长度统计
    report_lengths = {}
    for agent in completed_agents:
        result = agent.get("result", "")
        if result:
            report_lengths[agent["agent_name"]] = len(result)

    # 辩论轮次统计
    investment_debate_state = data.get("investment_debate_state", {})
    risk_debate_state = data.get("risk_debate_state", {})
    investment_rounds = investment_debate_state.get("count", 0) // 2 if investment_debate_state else 0
    risk_rounds = risk_debate_state.get("count", 0) // 3 if risk_debate_state else 0

    # 构建评估报告
    evaluation = {
        "session_id": session_id,
        "user_query": data.get("user_query", ""),
        "evaluation_time": datetime.now().isoformat(),
        "status": data.get("status", "unknown"),

        # 性能指标
        "performance_metrics": {
            "total_duration_seconds": total_duration,
            "total_duration_formatted": f"{total_duration:.2f}秒" if total_duration else "N/A",
            "completed_agents_count": len(completed_agents),
            "failed_agents_count": len(failed_agents),
            "total_mcp_calls": total_mcp_calls,
            "mcp_success_rate": round(mcp_success_rate * 100, 2),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "avg_agent_duration_seconds": round(avg_agent_duration, 3),
        },

        # 智能体详细耗时
        "agent_durations": stage_durations,

        # MCP工具使用排行
        "mcp_tool_usage": {
            tool_name: {
                "total_calls": stats["total_calls"],
                "success_rate": round(stats["successful_calls"] / stats["total_calls"] * 100, 2) if stats["total_calls"] > 0 else 0
            }
            for tool_name, stats in metrics.get("mcp_tool_stats", {}).items()
        },

        # 分析报告长度
        "report_lengths": report_lengths,

        # 辩论统计
        "debate_statistics": {
            "investment_debate_rounds": investment_rounds,
            "risk_debate_rounds": risk_rounds,
            "total_debate_rounds": investment_rounds + risk_rounds
        },

        # 智能体执行详情
        "agent_executions": [
            {
                "agent_name": a.get("agent_name", ""),
                "status": a.get("status", ""),
                "duration_seconds": a.get("duration_seconds", 0),
                "result_length": a.get("result_length", 0),
                "mcp_calls_count": a.get("mcp_calls_count", 0)
            }
            for a in agents
        ],

        # 实验对比所需数据
        "experiment_data": {
            "timestamp": datetime.now().isoformat(),
            "stock_code": _extract_stock_code(data.get("user_query", "")),
            "total_agents": len(data.get("active_agents", [])) or 15,
            "enabled_agents": data.get("active_agents", []),
            "analysis_quality_score": _calculate_quality_score(completed_agents, report_lengths)
        }
    }

    return evaluation


def _extract_stock_code(query: str) -> str:
    """从查询中提取股票代码"""
    import re
    patterns = [r"(\d{6})", r"(SSE:\d{6})", r"(SZSE:\d{6})"]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            return match.group(1)
    return "UNKNOWN"


def _calculate_quality_score(completed_agents: List[Dict], report_lengths: Dict) -> float:
    """
    计算分析质量评分（简单启发式评分）

    评分维度：
    - 报告完整性（是否有足够多的智能体完成）
    - 报告深度（平均报告长度）
    - 覆盖面（是否有核心智能体完成）
    """
    if not completed_agents:
        return 0.0

    # 核心智能体列表
    core_agents = [
        "company_overview_analyst",
        "market_analyst",
        "fundamentals_analyst",
        "research_manager",
        "trader",
        "risk_manager"
    ]

    # 完整性得分（完成的核心智能体比例）
    completed_names = [a.get("agent_name", "") for a in completed_agents]
    core_completed = sum(1 for c in core_agents if c in completed_names)
    completeness_score = core_completed / len(core_agents) * 50

    # 深度得分（平均报告长度，阈值10KB）
    if report_lengths:
        avg_length = sum(report_lengths.values()) / len(report_lengths)
        depth_score = min(avg_length / 10000 * 50, 50)
    else:
        depth_score = 0

    return round(completeness_score + depth_score, 2)


@app.get("/api/analysis/compare")
async def compare_sessions(
    session_ids: str,
    metrics_type: str = "duration"
):
    """
    对比多个会话的性能指标（用于实验对比）

    Query参数:
    - session_ids: 逗号分隔的session_id列表
    - metrics_type:对比类型 duration|quality|mcp
    """
    ids = [s.strip() for s in session_ids.split(",")]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="需要至少2个session_id进行对比")

    comparisons = []
    for sid in ids:
        eval_data = await evaluate_session(sid)
        comparisons.append({
            "session_id": sid,
            "user_query": eval_data["user_query"],
            "metrics": eval_data["performance_metrics"]
        })

    # 生成对比报告
    comparison_report = {
        "comparison_time": datetime.now().isoformat(),
        "metrics_type": metrics_type,
        "sessions_count": len(comparisons),
        "comparisons": comparisons,
        "summary": _generate_comparison_summary(comparisons, metrics_type)
    }

    return comparison_report


def _generate_comparison_summary(comparisons: List[Dict], metrics_type: str) -> Dict:
    """生成对比摘要"""
    if not comparisons:
        return {}

    metrics_key = "metrics"
    durations = [c[metrics_key].get("total_duration_seconds", 0) for c in comparisons]
    success_rates = [c[metrics_key].get("mcp_success_rate", 0) for c in comparisons]
    error_counts = [c[metrics_key].get("error_count", 0) for c in comparisons]

    return {
        "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
        "min_duration_seconds": min(durations) if durations else 0,
        "max_duration_seconds": max(durations) if durations else 0,
        "avg_mcp_success_rate": round(sum(success_rates) / len(success_rates), 2) if success_rates else 0,
        "total_errors": sum(error_counts),
        "fastest_session": comparisons[durations.index(min(durations))]["session_id"] if durations else None
    }


@app.get("/api/sessions")
async def sessions(status: Optional[str] = None):
    items = []
    for sf in list_session_files():
        data = read_json(sf)
        if data is None:
            continue
        if status and (data.get("status") or "").lower() != status.lower():
            continue
        items.append(
            {
                "session_id": data.get("session_id"),
                "status": data.get("status"),
                "user_query": data.get("user_query"),
                "created_at": data.get("created_at"),
                "file": str(sf),
            }
        )
    return {"sessions": items}


@app.get("/api/sessions/{session_id}")
async def session_detail(session_id: str):
    path = DUMP_DIR / f"session_{session_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="session not found")
    data = read_json(path)
    if data is None:
        raise HTTPException(status_code=422, detail="会话文件已损坏，无法读取")
    return data


def _resolve_session_file(payload: ExportReq) -> str:
    if payload.session_file:
        return payload.session_file
    if payload.session_id:
        path = DUMP_DIR / f"session_{payload.session_id}.json"
        if path.exists():
            return str(path)
    raise HTTPException(
        status_code=400, detail="session_file or session_id is required"
    )


@app.post("/api/exports/md")
async def export_md(payload: ExportReq):
    session_file = _resolve_session_file(payload)
    converter = JSONToMarkdownConverter(
        str(SESSION_DIR), key_agents_only=payload.key_agents_only
    )
    result = converter.convert_json_to_markdown(session_file)
    if not result:
        raise HTTPException(status_code=500, detail="markdown export failed")
    return FileResponse(result, media_type="text/markdown", filename=Path(result).name)


@app.post("/api/exports/pdf")
async def export_pdf(payload: ExportReq):
    session_file = _resolve_session_file(payload)
    converter = MarkdownToPDFConverter(
        str(SESSION_DIR), include_toc=True, key_agents_only=payload.key_agents_only
    )
    result = converter.convert_json_to_pdf_via_markdown(session_file)
    if not result:
        raise HTTPException(status_code=500, detail="pdf export failed")
    return FileResponse(
        result, media_type="application/pdf", filename=Path(result).name
    )


@app.post("/api/exports/docx")
async def export_docx(payload: ExportReq):
    session_file = _resolve_session_file(payload)
    converter = MarkdownToDocxConverter(
        str(SESSION_DIR), key_agents_only=payload.key_agents_only
    )
    result = converter.convert_json_to_docx_via_markdown(session_file)
    if not result:
        raise HTTPException(status_code=500, detail="docx export failed")
    return FileResponse(
        result,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(result).name,
    )


@app.get("/api/stock/kline/{stock_code}")
async def get_stock_kline(stock_code: str, period: str = "30d"):
    """获取股票K线数据"""
    try:
        client = HttpClient()
        data = client.get_kline_data(stock_code, period=period)
        if not data:
            return {"error": "No data available"}
        return {"stock_code": stock_code, "period": period, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/indicators/{stock_code}")
async def get_stock_indicators(stock_code: str):
    """获取股票技术指标"""
    try:
        client = HttpClient()
        indicators = client.get_technical_indicators(stock_code)
        if not indicators:
            return {"error": "No data available"}
        return {"stock_code": stock_code, "indicators": indicators}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/price/{stock_code}")
async def get_stock_price(stock_code: str):
    """获取实时价格"""
    try:
        client = HttpClient()
        price_data = client.get_real_time_price([stock_code])
        if not price_data or not price_data.get("data"):
            return {"error": "No price data available"}
        return {"stock_code": stock_code, "price": price_data["data"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/money-flow/{stock_code}")
async def get_money_flow(stock_code: str, days: int = 20):
    """获取资金流向"""
    try:
        client = HttpClient()
        data = client.get_money_flow(stock_code, days=days)
        if not data:
            return {"error": "No data available"}
        return {"stock_code": stock_code, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/news/{stock_code}")
async def get_news(stock_code: str, limit: int = 10):
    """获取股票新闻"""
    try:
        client = HttpClient()
        data = client.get_stock_news(stock_code, limit=limit)
        if not data:
            return {"error": "No news available"}
        return {"stock_code": stock_code, "news": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/info/{stock_code}")
async def get_stock_info(stock_code: str):
    """获取公司基本信息"""
    try:
        client = HttpClient()
        data = client.get_asset_info(stock_code)
        if not data:
            return {"error": "No info available"}
        return {"stock_code": stock_code, "info": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# RAG金融智能对话API
# ========================================

from typing import List, Optional, Dict, Any
import asyncio

# RAG导入
try:
    from src.rag.engine import (
        get_rag_engine,
        index_session_reports,
        create_knowledge_base,
    )

    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"[WARN] RAG模块未可用: {e}")


# 请求模型
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    top_k: int = 5
    collection: str = "finance_knowledge"


class IndexRequest(BaseModel):
    texts: List[str]
    metadatas: Optional[List[Dict[str, Any]]] = None
    collection: str = "finance_knowledge"


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: str = "finance_knowledge"


class CreateCollectionRequest(BaseModel):
    name: str
    description: str = "金融知识库"


@app.post("/api/chat/rag")
async def chat_rag(request: ChatRequest):
    """RAG智能对话"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        result = engine.chat(
            query=request.message,
            conversation_history=request.history,
            top_k=request.top_k,
            collection_name=request.collection,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/rag/stream")
async def chat_rag_stream(request: ChatRequest):
    """RAG流式对话"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    async def generate():
        try:
            engine = get_rag_engine()

            # 检索
            search_results = engine.search(
                query=request.message,
                top_k=request.top_k,
                collection_name=request.collection,
            )

            # 构建上下文
            context = "\n\n".join(
                [
                    f"【文档{i + 1}】{r['content'][:500]}..."
                    for i, r in enumerate(search_results[: request.top_k])
                ]
            )

            history_text = ""
            if request.history:
                history_text = "\n".join(
                    [
                        f"{'用户' if msg['role'] == 'user' else 'AI助手'}: {msg['content'][:200]}"
                        for msg in request.history[-5:]
                    ]
                )

            full_prompt = f"""你是一个专业的金融AI助手。请根据以下参考文档回答用户的问题。

参考文档：
{context}

对话历史：
{history_text}

用户问题：{request.message}

请根据参考文档回答，要求：
1. 优先使用提供的参考文档内容
2. 如果参考文档中没有相关信息，请如实说明
3. 保持专业、易懂的语言风格

回答："""

            # 流式生成 - 使用engine的stream_chat方法
            try:
                # 直接使用engine.stream_chat()获取流式响应
                for chunk_data in engine.stream_chat(
                    query=request.message,
                    conversation_history=request.history,
                    top_k=request.top_k,
                    collection_name=request.collection
                ):
                    chunk_type = chunk_data.get("type", "")
                    if chunk_type == "content":
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk_data['content']})}\n\n"
                        await asyncio.sleep(0.01)
                    elif chunk_type == "error":
                        yield f"data: {json.dumps({'type': 'error', 'error': chunk_data['error']})}\n\n"
                        break
                    elif chunk_type == "sources":
                        # sources已经在最后发送了
                        pass
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

            # 发送来源
            sources_data = {
                "type": "sources",
                "sources": [
                    {
                        "content": r["content"][:200],
                        "score": round(r["score"], 3),
                        "metadata": r.get("metadata", {}),
                    }
                    for r in search_results[: request.top_k]
                ],
            }
            yield f"data: {json.dumps(sources_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/rag/index")
async def index_documents(request: IndexRequest):
    """添加文档到知识库"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        count = engine.add_documents(
            texts=request.texts,
            metadatas=request.metadatas,
            collection_name=request.collection,
        )
        return {"status": "success", "indexed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/search")
async def search_documents(request: SearchRequest):
    """检索文档"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        results = engine.search(
            query=request.query, top_k=request.top_k, collection_name=request.collection
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/index_reports")
async def index_reports():
    """索引会话报告"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        result = index_session_reports()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/collection")
async def create_collection(request: CreateCollectionRequest):
    """创建知识库"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        success = create_knowledge_base(request.name)
        if success:
            return {"status": "success", "name": request.name}
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/collections")
async def list_collections():
    """列出所有知识库"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        collections = engine.list_collections()

        # 获取每个集合的文档数量
        result = []
        for col in collections:
            count = engine.get_collection_count(col)
            result.append({"name": col, "count": count})

        return {"collections": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 用户知识库文件管理API
# ========================================

import tempfile
import shutil
from fastapi import UploadFile, File, Form
from typing import List, Optional


@app.post("/api/rag/upload")
async def upload_file(
    file: UploadFile = File(...),
    collection: str = Form(default="user_knowledge")
):
    """
    上传文件到知识库

    支持格式: PDF, Word(.docx), TXT, Markdown
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".md"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}，支持的格式: {', '.join(allowed_extensions)}"
        )

    temp_dir = Path(tempfile.gettempdir()) / "rag_uploads"
    temp_dir.mkdir(exist_ok=True)

    temp_path = temp_dir / file.filename

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        engine = get_rag_engine()
        result = engine.add_file(
            file_path=str(temp_path),
            collection_name=collection,
            metadata={"original_filename": file.filename}
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass


@app.post("/api/rag/upload/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    collection: str = Form(default="user_knowledge")
):
    """
    批量上传文件到知识库
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".md"}

    temp_dir = Path(tempfile.gettempdir()) / "rag_uploads"
    temp_dir.mkdir(exist_ok=True)

    results = []

    for file in files:
        if not file.filename:
            results.append({"status": "error", "error": "文件名为空"})
            continue

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            results.append({
                "status": "error",
                "filename": file.filename,
                "error": f"不支持的格式: {file_ext}"
            })
            continue

        temp_path = temp_dir / file.filename

        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            engine = get_rag_engine()
            result = engine.add_file(
                file_path=str(temp_path),
                collection_name=collection,
                metadata={"original_filename": file.filename}
            )
            results.append(result)

        except Exception as e:
            results.append({
                "status": "error",
                "filename": file.filename,
                "error": str(e)
            })
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

    success_count = len([r for r in results if r.get("status") == "success"])
    return {
        "status": "success",
        "total": len(files),
        "success": success_count,
        "failed": len(files) - success_count,
        "results": results
    }


@app.get("/api/rag/knowledge/info")
async def get_knowledge_base_info(
    collection: str = "user_knowledge"
):
    """
    获取用户知识库信息
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        info = engine.get_collection_info(collection)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/knowledge")
async def delete_knowledge_base(
    collection: str = "user_knowledge"
):
    """
    删除用户知识库
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        result = engine.delete_collection_data(collection)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/knowledge/search")
async def search_knowledge_base(request: SearchRequest):
    """
    在用户知识库中检索
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="RAG模块未初始化")

    try:
        engine = get_rag_engine()
        results = engine.search(
            query=request.query,
            top_k=request.top_k,
            collection_name=request.collection
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 数据库会话管理API
# ========================================

from src.core.database import SessionDatabase

_db_instance: Optional[SessionDatabase] = None


def get_session_db() -> SessionDatabase:
    """获取数据库实例（单例）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = SessionDatabase()
    return _db_instance


@app.post("/api/db/sessions/search")
async def search_db_sessions(
    stock_code: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_quality_score: Optional[float] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    搜索会话记录（支持多条件查询）

    参数:
    - stock_code: 股票代码 (如: SSE:600519)
    - status: 会话状态 (completed/running/failed)
    - start_date: 开始日期 (ISO格式: 2026-01-01)
    - end_date: 结束日期 (ISO格式: 2026-12-31)
    - min_quality_score: 最低质量评分 (0-100)
    - limit: 返回数量 (默认50)
    - offset: 偏移量 (默认0)
    """
    try:
        db = get_session_db()
        sessions = db.search_sessions(
            stock_code=stock_code,
            status=status,
            start_date=start_date,
            end_date=end_date,
            min_quality_score=min_quality_score,
            limit=limit,
            offset=offset
        )
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "user_query": s.user_query,
                    "stock_code": s.stock_code,
                    "status": s.status,
                    "created_at": s.created_at,
                    "completed_at": s.completed_at,
                    "duration_seconds": s.duration_seconds,
                    "agents_count": s.agents_count,
                    "mcp_calls_count": s.mcp_calls_count,
                    "mcp_success_rate": s.mcp_success_rate,
                    "error_count": s.error_count,
                    "quality_score": s.quality_score
                }
                for s in sessions
            ],
            "count": len(sessions),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/db/sessions/{session_id}")
async def get_db_session(session_id: str):
    """获取会话详细信息"""
    try:
        db = get_session_db()
        raw_data = db.get_session_raw_data(session_id)
        if not raw_data:
            raise HTTPException(status_code=404, detail="session not found")
        return raw_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/db/statistics")
async def get_db_statistics():
    """获取统计数据"""
    try:
        db = get_session_db()
        stats = db.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/db/sessions/{session_id}/import")
async def import_session_to_db(session_id: str):
    """从JSON文件导入会话到数据库"""
    try:
        db = get_session_db()

        json_path = str(SESSION_DIR / f"session_{session_id}.json")
        if not os.path.exists(json_path):
            for pattern in [f"**/session_{session_id}.json", f"**/*{session_id}*.json"]:
                from pathlib import Path
                matches = list(Path(".").glob(pattern))
                if matches:
                    json_path = str(matches[0])
                    break

        if not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail=f"JSON file not found for {session_id}")

        success = db.import_from_json_file(json_path)
        if success:
            return {"status": "success", "session_id": session_id, "imported": True}
        else:
            raise HTTPException(status_code=500, detail="import failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/db/import-all")
async def import_all_sessions_to_db():
    """从dump目录导入所有会话到数据库"""
    try:
        db = get_session_db()
        success_count, fail_count = db.import_all_from_directory(str(SESSION_DIR))
        return {
            "status": "success",
            "imported": success_count,
            "failed": fail_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 缓存管理API
# ========================================

@app.get("/api/cache/mcp/stats")
async def get_mcp_cache_stats():
    """获取MCP缓存统计"""
    from src.mcp.http_client import get_mcp_cache
    cache = get_mcp_cache()
    return cache.get_stats()


@app.post("/api/cache/mcp/clear")
async def clear_mcp_cache():
    """清空MCP缓存"""
    from src.mcp.http_client import get_mcp_cache
    cache = get_mcp_cache()
    cache.clear()
    return {"status": "success", "message": "MCP缓存已清空"}


@app.get("/api/cache/memory/stats")
async def get_memory_cache_stats():
    """获取内存缓存统计"""
    from src.core.cache import get_memory_cache
    cache = get_memory_cache()
    return cache.get_stats()


@app.post("/api/cache/memory/clear")
async def clear_memory_cache():
    """清空内存缓存"""
    from src.core.cache import get_memory_cache
    cache = get_memory_cache()
    cache.clear()
    return {"status": "success", "message": "内存缓存已清空"}


@app.get("/api/cache/analysis/stats")
async def get_analysis_cache_stats():
    """获取分析结果缓存统计"""
    from src.core.analysis_cache import get_analysis_cache
    cache = get_analysis_cache()
    return cache.get_stats()


@app.post("/api/cache/analysis/clear")
async def clear_analysis_cache():
    """清空分析结果缓存"""
    from src.core.analysis_cache import get_analysis_cache
    cache = get_analysis_cache()
    cache.clear()
    return {"status": "success", "message": "分析结果缓存已清空"}


@app.get("/api/cache/analysis/list")
async def list_cached_analyses(
    stock_code: Optional[str] = None,
    min_quality_score: float = 0.0,
    limit: int = 20
):
    """列出缓存的分析"""
    from src.core.analysis_cache import get_analysis_cache
    cache = get_analysis_cache()
    return {
        "cached_analyses": cache.list_cached_analyses(
            stock_code=stock_code,
            min_quality_score=min_quality_score,
            limit=limit
        )
    }
