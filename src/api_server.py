import asyncio
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.dumptools.json_to_markdown import JSONToMarkdownConverter
from src.dumptools.md2docx import MarkdownToDocxConverter
from src.dumptools.md2pdf import MarkdownToPDFConverter
from src.tools.http_client import StockMCPHTTPClient as HttpClient
from src.workflow_orchestrator import WorkflowOrchestrator


DUMP_DIR = Path(__file__).resolve().parent / "dump"
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
        DUMP_DIR.glob("session_*.json"), key=lambda f: f.stat().st_mtime, reverse=True
    )


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    query: str = Field(min_length=1)
    active_agents: List[str] = Field(default_factory=list)
    investment_rounds: int = 1
    risk_rounds: int = 1


class ExportReq(BaseModel):
    session_file: Optional[str] = None
    session_id: Optional[str] = None
    key_agents_only: bool = False


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {
        "env_exists": Path(".env").exists(),
        "mcp_config_exists": Path("mcp_config.json").exists(),
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
        raise HTTPException(
            status_code=429,
            detail=f"running tasks reached limit ({running_count}/{max_limit})",
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
        raise HTTPException(status_code=404, detail="task not found")
    record.cancelled = True
    record.status = "cancelling"
    return {"ok": True, "task_id": task_id, "status": "cancelling"}


@app.get("/api/analysis/{task_id}/progress")
async def analysis_progress(task_id: str):
    record = TASKS.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="task not found")

    session_data = None
    if record.session_id:
        path = DUMP_DIR / f"session_{record.session_id}.json"
        if path.exists():
            session_data = read_json(path)
    elif list_session_files():
        session_data = read_json(list_session_files()[0])
        if isinstance(session_data, dict):
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


@app.get("/api/sessions")
async def sessions(status: Optional[str] = None):
    items = []
    for sf in list_session_files():
        data = read_json(sf)
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
    return read_json(path)


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
        "src/dump", key_agents_only=payload.key_agents_only
    )
    result = converter.convert_json_to_markdown(session_file)
    if not result:
        raise HTTPException(status_code=500, detail="markdown export failed")
    return FileResponse(result, media_type="text/markdown", filename=Path(result).name)


@app.post("/api/exports/pdf")
async def export_pdf(payload: ExportReq):
    session_file = _resolve_session_file(payload)
    converter = MarkdownToPDFConverter(
        "src/dump", include_toc=True, key_agents_only=payload.key_agents_only
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
        "src/dump", key_agents_only=payload.key_agents_only
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
