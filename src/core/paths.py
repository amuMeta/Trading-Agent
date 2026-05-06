"""
TradingAgents 集中式路径配置

提供统一的路径管理，支持：
- 环境变量覆盖
- 相对路径解析
- 目录自动创建
- 向后兼容

所有路径都基于 PROJECT_ROOT 解析，确保在任何工作目录下都能正确运行。
"""

import os
from pathlib import Path
from typing import Optional


def _get_project_root() -> Path:
    """
    获取项目根目录

    通过向上查找 pyproject.toml 或 setup.py 确定项目根目录
    """
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent

    return current.parent.parent


PROJECT_ROOT: Path = _get_project_root()


SRC_DIR: Path = PROJECT_ROOT / "src"


STORAGE_DIR: Path = PROJECT_ROOT / "storage"
STORAGE_DIR.mkdir(exist_ok=True)


SESSION_DIR: Path = STORAGE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)


CACHE_DIR: Path = STORAGE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)


ANALYSIS_CACHE_DIR: Path = CACHE_DIR / "analysis"
ANALYSIS_CACHE_DIR.mkdir(exist_ok=True)


CHROMA_DB_DIR: Path = Path(os.getenv("CHROMA_DB_DIR", str(PROJECT_ROOT / "data" / "chroma_db")))


EXPORT_DIR: Path = SRC_DIR / "export"


MARKDOWN_REPORTS_DIR: Path = EXPORT_DIR / "markdown_reports"
MARKDOWN_REPORTS_DIR.mkdir(exist_ok=True, parents=True)


PDF_REPORTS_DIR: Path = EXPORT_DIR / "pdf_reports"
PDF_REPORTS_DIR.mkdir(exist_ok=True, parents=True)


DOCX_REPORTS_DIR: Path = EXPORT_DIR / "docx_reports"
DOCX_REPORTS_DIR.mkdir(exist_ok=True, parents=True)


DUMP_DIR_LEGACY: Path = SRC_DIR / "dump"
DUMP_DIR_LEGACY.mkdir(exist_ok=True, parents=True)


DUMPTOOLS_LEGACY_DIR: Path = SRC_DIR / "dumptools"


TOOLS_DIR_LEGACY: Path = SRC_DIR / "tools"


EXTERNAL_DIR: Path = PROJECT_ROOT / "external"
EXTERNAL_DIR.mkdir(exist_ok=True)


STOCK_MCP_DIR: Path = EXTERNAL_DIR / "stock-mcp"


def get_session_file_path(session_id: str, base_dir: Optional[Path] = None) -> Path:
    """获取会话文件路径"""
    base = base_dir or SESSION_DIR
    return base / f"session_{session_id}.json"


def resolve_legacy_dump_path(path: str) -> Path:
    """
    解析旧版dump路径（兼容新路径）

    优先使用新路径，如果不存在则回退到旧路径
    """
    new_path = SESSION_DIR / Path(path).name
    if new_path.exists():
        return new_path

    legacy_path = DUMP_DIR_LEGACY / Path(path).name
    return legacy_path


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_markdown_report_path(session_id: str) -> Path:
    """获取Markdown报告路径"""
    return MARKDOWN_REPORTS_DIR / f"session_{session_id}.md"


def get_pdf_report_path(session_id: str) -> Path:
    """获取PDF报告路径"""
    return PDF_REPORTS_DIR / f"session_{session_id}.pdf"


def get_docx_report_path(session_id: str) -> Path:
    """获取DOCX报告路径"""
    return DOCX_REPORTS_DIR / f"session_{session_id}.docx"


__all__ = [
    "PROJECT_ROOT",
    "SRC_DIR",
    "STORAGE_DIR",
    "SESSION_DIR",
    "CACHE_DIR",
    "ANALYSIS_CACHE_DIR",
    "CHROMA_DB_DIR",
    "EXPORT_DIR",
    "MARKDOWN_REPORTS_DIR",
    "PDF_REPORTS_DIR",
    "DOCX_REPORTS_DIR",
    "DUMP_DIR_LEGACY",
    "DUMPTOOLS_LEGACY_DIR",
    "TOOLS_DIR_LEGACY",
    "EXTERNAL_DIR",
    "STOCK_MCP_DIR",
    "get_session_file_path",
    "resolve_legacy_dump_path",
    "ensure_dir",
    "get_markdown_report_path",
    "get_pdf_report_path",
    "get_docx_report_path",
]
