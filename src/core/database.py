"""
数据库模块 - SQLite会话存储和查询

本模块提供：
1. 会话数据持久化到SQLite
2. 多条件会话查询
3. 性能指标统计分析

使用方式：
    from src.core.database import SessionDatabase
    db = SessionDatabase()
    sessions = db.search_sessions(stock_code="600519", status="completed")
"""

import sqlite3
import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager

from src.core.paths import SESSION_DIR


@dataclass
class SessionRecord:
    """会话记录数据结构"""
    session_id: str
    user_query: str
    stock_code: str
    status: str
    created_at: str
    completed_at: Optional[str]
    duration_seconds: float
    agents_count: int
    mcp_calls_count: int
    mcp_success_rate: float
    error_count: int
    quality_score: float


@dataclass
class ChatMessageRecord:
    """聊天消息记录"""
    message_id: int
    conversation_id: str
    role: str
    content: str
    sources: Optional[str]
    created_at: str


@dataclass
class ChatConversationRecord:
    """聊天会话记录"""
    conversation_id: str
    title: str
    preview: str
    created_at: str
    updated_at: str
    message_count: int


class SessionDatabase:
    """SQLite会话数据库"""

    def __init__(self, db_path: str = "data/sessions.db"):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.db_dir = os.path.dirname(db_path)
        os.makedirs(self.db_dir, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 会话主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_query TEXT,
                    stock_code TEXT,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    agents_count INTEGER,
                    mcp_calls_count INTEGER,
                    mcp_success_rate REAL,
                    error_count INTEGER,
                    warning_count INTEGER,
                    quality_score REAL,
                    raw_data TEXT
                )
            """)

            # 智能体执行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    agent_name TEXT,
                    status TEXT,
                    duration_seconds REAL,
                    result_length INTEGER,
                    mcp_calls_count INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # MCP工具调用记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mcp_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    agent_name TEXT,
                    tool_name TEXT,
                    success INTEGER,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # 聊天会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT,
                    preview TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # 聊天消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    sources TEXT,
                    created_at TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(conversation_id)
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_stock ON sessions(stock_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_executions_session ON agent_executions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_calls_session ON mcp_calls(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated ON chat_conversations(updated_at)")

            conn.commit()
            print(f"✅ 数据库初始化完成: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """
        保存会话数据到数据库

        Args:
            session_data: 会话数据字典

        Returns:
            bool: 是否保存成功
        """
        try:
            session_id = session_data.get("session_id", "")
            if not session_id:
                return False

            # 提取会话基本信息
            metrics = session_data.get("metrics", {})
            agents = session_data.get("agents", [])

            # 提取股票代码
            user_query = session_data.get("user_query", "")
            stock_code = self._extract_stock_code(user_query)

            # 计算MCP成功率
            mcp_calls = session_data.get("mcp_calls", [])
            total_mcp = len(mcp_calls)
            successful_mcp = sum(1 for c in mcp_calls if c.get("success", True))
            mcp_success_rate = successful_mcp / total_mcp if total_mcp > 0 else 1.0

            # 计算质量评分
            quality_score = self._calculate_quality_score(agents)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 插入会话主记录
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_query, stock_code, status, created_at, completed_at,
                     duration_seconds, agents_count, mcp_calls_count, mcp_success_rate,
                     error_count, warning_count, quality_score, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    user_query,
                    stock_code,
                    session_data.get("status", "unknown"),
                    session_data.get("created_at", ""),
                    session_data.get("updated_at", ""),
                    metrics.get("total_duration_seconds", 0.0),
                    len(agents),
                    total_mcp,
                    mcp_success_rate,
                    len(session_data.get("errors", [])),
                    len(session_data.get("warnings", [])),
                    quality_score,
                    json.dumps(session_data, ensure_ascii=False)
                ))

                # 插入智能体执行记录
                for agent in agents:
                    cursor.execute("""
                        INSERT INTO agent_executions
                        (session_id, agent_name, status, duration_seconds, result_length,
                         mcp_calls_count, start_time, end_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        agent.get("agent_name", ""),
                        agent.get("status", ""),
                        agent.get("duration_seconds", 0.0),
                        agent.get("result_length", 0),
                        agent.get("mcp_calls_count", 0),
                        agent.get("start_time", ""),
                        agent.get("end_time", "")
                    ))

                # 插入MCP调用记录
                for call in mcp_calls:
                    cursor.execute("""
                        INSERT INTO mcp_calls
                        (session_id, agent_name, tool_name, success, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        call.get("agent_name", ""),
                        call.get("tool_name", ""),
                        1 if call.get("success", True) else 0,
                        call.get("timestamp", "")
                    ))

                conn.commit()
                print(f"💾 会话已保存到数据库: {session_id}")
                return True

        except Exception as e:
            print(f"❌ 保存会话失败: {e}")
            return False

    def search_sessions(
        self,
        stock_code: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SessionRecord]:
        """
        搜索会话

        Args:
            stock_code: 股票代码
            status: 会话状态
            start_date: 开始日期 (ISO格式)
            end_date: 结束日期 (ISO格式)
            min_quality_score: 最低质量评分
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[SessionRecord]: 会话记录列表
        """
        conditions = []
        params = []

        if stock_code:
            conditions.append("stock_code = ?")
            params.append(stock_code)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if start_date:
            conditions.append("created_at >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("created_at <= ?")
            params.append(end_date)

        if min_quality_score is not None:
            conditions.append("quality_score >= ?")
            params.append(min_quality_score)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM sessions
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [SessionRecord(
                session_id=row["session_id"],
                user_query=row["user_query"],
                stock_code=row["stock_code"],
                status=row["status"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                duration_seconds=row["duration_seconds"],
                agents_count=row["agents_count"],
                mcp_calls_count=row["mcp_calls_count"],
                mcp_success_rate=row["mcp_success_rate"],
                error_count=row["error_count"],
                quality_score=row["quality_score"]
            ) for row in rows]

    def get_session_raw_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话原始数据

        Args:
            session_id: 会话ID

        Returns:
            Dict: 原始数据字典
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_data FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row and row["raw_data"]:
                return json.loads(row["raw_data"])
            return None

    def get_agent_executions(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取智能体执行记录

        Args:
            session_id: 会话ID

        Returns:
            List[Dict]: 智能体执行记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_executions
                WHERE session_id = ?
                ORDER BY start_time
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_mcp_calls(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取MCP调用记录

        Args:
            session_id: 会话ID

        Returns:
            List[Dict]: MCP调用记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM mcp_calls
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计数据

        Returns:
            Dict: 统计信息
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 会话统计
            cursor.execute("SELECT COUNT(*) as total FROM sessions")
            total_sessions = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM sessions WHERE status = 'completed'")
            completed_sessions = cursor.fetchone()["total"]

            # 性能统计
            cursor.execute("""
                SELECT AVG(duration_seconds) as avg_duration,
                       AVG(mcp_success_rate) as avg_mcp_rate,
                       AVG(quality_score) as avg_quality
                FROM sessions WHERE status = 'completed'
            """)
            perf = cursor.fetchone()

            # 智能体使用统计
            cursor.execute("""
                SELECT agent_name, COUNT(*) as call_count,
                       AVG(duration_seconds) as avg_duration,
                       SUM(mcp_calls_count) as total_mcp_calls
                FROM agent_executions
                GROUP BY agent_name
                ORDER BY call_count DESC
            """)
            agent_stats = [dict(row) for row in cursor.fetchall()]

            # MCP工具使用统计
            cursor.execute("""
                SELECT tool_name, COUNT(*) as call_count,
                       SUM(success) as successful_calls
                FROM mcp_calls
                GROUP BY tool_name
                ORDER BY call_count DESC
            """)
            tool_stats = [dict(row) for row in cursor.fetchall()]

            return {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "avg_duration_seconds": round(perf["avg_duration"] or 0, 2),
                "avg_mcp_success_rate": round((perf["avg_mcp_rate"] or 0) * 100, 2),
                "avg_quality_score": round(perf["avg_quality"] or 0, 2),
                "agent_statistics": agent_stats,
                "tool_statistics": tool_stats
            }

    def import_from_json_file(self, json_path: str) -> bool:
        """
        从JSON文件导入会话数据

        Args:
            json_path: JSON文件路径

        Returns:
            bool: 是否导入成功
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            session_id = session_data.get("session_id", "")
            if not session_id:
                print(f"⚠️ JSON文件缺少session_id: {json_path}")
                return False

            # 检查是否已存在
            existing = self.get_session_raw_data(session_id)
            if existing:
                print(f"ℹ️ 会话已存在，跳过: {session_id}")
                return True

            return self.save_session(session_data)

        except Exception as e:
            print(f"❌ 导入失败: {json_path}, 错误: {e}")
            return False

    def import_all_from_directory(self, directory: str = None) -> Tuple[int, int]:
        """
        从目录导入所有JSON会话文件

        Args:
            directory: 目录路径，默认使用 SESSION_DIR

        Returns:
            Tuple[int, int]: (成功数, 失败数)
        """
        success_count = 0
        fail_count = 0

        if directory is None:
            directory = str(SESSION_DIR)
        dump_dir = Path(directory)
        if not dump_dir.exists():
            print(f"⚠️ 目录不存在: {directory}")
            return (0, 0)

        for json_file in dump_dir.glob("session_*.json"):
            if self.import_from_json_file(str(json_file)):
                success_count += 1
            else:
                fail_count += 1

        print(f"📥 导入完成: 成功 {success_count}, 失败 {fail_count}")
        return (success_count, fail_count)

    @staticmethod
    def _extract_stock_code(query: str) -> str:
        """从查询中提取股票代码"""
        patterns = [r"(\d{6})", r"(SSE:\d{6})", r"(SZSE:\d{6})"]
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                code = match.group(1)
                # 添加交易所前缀
                if len(code) == 6 and code.isdigit():
                    return f"SSE:{code}" if code.startswith(("6", "5", "9")) else f"SZSE:{code}"
                return code
        return "UNKNOWN"

    @staticmethod
    def _calculate_quality_score(agents: List[Dict[str, Any]]) -> float:
        """计算分析质量评分"""
        if not agents:
            return 0.0

        core_agents = [
            "company_overview_analyst",
            "market_analyst",
            "fundamentals_analyst",
            "research_manager",
            "trader",
            "risk_manager"
        ]

        completed_names = [a.get("agent_name", "") for a in agents if a.get("status") == "completed"]
        core_completed = sum(1 for c in core_agents if c in completed_names)
        completeness_score = core_completed / len(core_agents) * 50

        report_lengths = {a["agent_name"]: a.get("result_length", 0) for a in completed_names}
        if report_lengths:
            avg_length = sum(report_lengths.values()) / len(report_lengths)
            depth_score = min(avg_length / 10000 * 50, 50)
        else:
            depth_score = 0

        return round(completeness_score + depth_score, 2)

    # ========================================
    # 聊天会话管理方法
    # ========================================

    def create_chat_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str = "新对话"
    ) -> bool:
        """创建聊天会话"""
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_conversations
                    (conversation_id, user_id, title, preview, created_at, updated_at)
                    VALUES (?, ?, ?, '', ?, ?)
                """, (conversation_id, user_id, title, now, now))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 创建聊天会话失败: {e}")
            return False

    def get_chat_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatConversationRecord]:
        """获取用户的聊天会话列表"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.conversation_id, c.title, c.preview, c.created_at, c.updated_at,
                           COUNT(m.message_id) as message_count
                    FROM chat_conversations c
                    LEFT JOIN chat_messages m ON c.conversation_id = m.conversation_id
                    WHERE c.user_id = ?
                    GROUP BY c.conversation_id
                    ORDER BY c.updated_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                rows = cursor.fetchall()
                return [ChatConversationRecord(
                    conversation_id=row["conversation_id"],
                    title=row["title"],
                    preview=row["preview"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    message_count=row["message_count"]
                ) for row in rows]
        except Exception as e:
            print(f"❌ 获取聊天会话列表失败: {e}")
            return []

    def get_chat_conversation(self, conversation_id: str, user_id: str) -> Optional[ChatConversationRecord]:
        """获取单个聊天会话"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.conversation_id, c.title, c.preview, c.created_at, c.updated_at,
                           COUNT(m.message_id) as message_count
                    FROM chat_conversations c
                    LEFT JOIN chat_messages m ON c.conversation_id = m.conversation_id
                    WHERE c.conversation_id = ? AND c.user_id = ?
                    GROUP BY c.conversation_id
                """, (conversation_id, user_id))
                row = cursor.fetchone()
                if row:
                    return ChatConversationRecord(
                        conversation_id=row["conversation_id"],
                        title=row["title"],
                        preview=row["preview"] or "",
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        message_count=row["message_count"]
                    )
                return None
        except Exception as e:
            print(f"❌ 获取聊天会话失败: {e}")
            return None

    def delete_chat_conversation(self, conversation_id: str, user_id: str) -> bool:
        """删除聊天会话及其所有消息"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM chat_messages WHERE conversation_id = ?",
                    (conversation_id,)
                )
                cursor.execute(
                    "DELETE FROM chat_conversations WHERE conversation_id = ? AND user_id = ?",
                    (conversation_id, user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 删除聊天会话失败: {e}")
            return False

    def update_chat_conversation(self, conversation_id: str, user_id: str, title: str = None, preview: str = None) -> bool:
        """更新聊天会话"""
        try:
            updates = []
            params = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if preview is not None:
                updates.append("preview = ?")
                params.append(preview)
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.extend([conversation_id, user_id])

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE chat_conversations SET {', '.join(updates)} WHERE conversation_id = ? AND user_id = ?",
                    params
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 更新聊天会话失败: {e}")
            return False

    def add_chat_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None
    ) -> Optional[int]:
        """添加聊天消息"""
        try:
            now = datetime.now().isoformat()
            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (conversation_id, role, content, sources_json, now))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ 添加聊天消息失败: {e}")
            return None

    def get_chat_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChatMessageRecord]:
        """获取聊天消息列表"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT message_id, conversation_id, role, content, sources, created_at
                    FROM chat_messages
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC
                    LIMIT ? OFFSET ?
                """, (conversation_id, limit, offset))
                rows = cursor.fetchall()
                return [ChatMessageRecord(
                    message_id=row["message_id"],
                    conversation_id=row["conversation_id"],
                    role=row["role"],
                    content=row["content"],
                    sources=row["sources"],
                    created_at=row["created_at"]
                ) for row in rows]
        except Exception as e:
            print(f"❌ 获取聊天消息失败: {e}")
            return []

    def delete_chat_message(self, message_id: int) -> bool:
        """删除聊天消息"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chat_messages WHERE message_id = ?", (message_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 删除聊天消息失败: {e}")
            return False
