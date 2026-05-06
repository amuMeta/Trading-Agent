"""
TradingAgents WebSocket实时通信模块

提供实时进度推送功能：
- 任务进度实时更新
- 智能体执行状态推送
- 辩论状态实时通知
- SSE（Server-Sent Events）备用方案
"""

import asyncio
import json
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket连接管理器

    管理所有WebSocket连接，支持：
    - 任务级别的订阅
    - 广播消息
    - 连接状态管理
    """

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self._all_connections: List[WebSocket] = []
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Set[str]] = defaultdict(set)

    def connect(self, websocket: WebSocket, task_id: Optional[str] = None) -> str:
        """接受WebSocket连接"""
        connection_id = f"conn_{id(websocket)}_{datetime.now().timestamp()}"

        with self._lock:
            websocket = websocket
            self._all_connections.append(websocket)

            if task_id:
                self._connections[task_id].append(websocket)
                self._subscribers[connection_id].add(task_id)

        logger.info(f"WebSocket connected: {connection_id}, task_id={task_id}")
        return connection_id

    def disconnect(self, websocket: WebSocket, connection_id: str):
        """断开WebSocket连接"""
        with self._lock:
            if websocket in self._all_connections:
                self._all_connections.remove(websocket)

            for task_id, connections in list(self._connections.items()):
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:
                        del self._connections[task_id]

            if connection_id in self._subscribers:
                del self._subscribers[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """发送个人消息"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send personal message: {e}")

    async def broadcast_task(self, task_id: str, message: Dict):
        """向特定任务的所有连接广播消息"""
        with self._lock:
            connections = list(self._connections.get(task_id, []))

        if not connections:
            return

        disconnected = []
        for websocket in connections:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to task {task_id}: {e}")
                    disconnected.append(websocket)

        with self._lock:
            for ws in disconnected:
                if ws in self._connections.get(task_id, []):
                    self._connections[task_id].remove(ws)

    async def broadcast_all(self, message: Dict):
        """向所有连接广播消息"""
        with self._lock:
            connections = list(self._all_connections)

        disconnected = []
        for websocket in connections:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast: {e}")
                    disconnected.append(websocket)

        with self._lock:
            for ws in disconnected:
                if ws in self._all_connections:
                    self._all_connections.remove(ws)

    def get_task_connection_count(self, task_id: str) -> int:
        """获取任务连接数"""
        with self._lock:
            return len(self._connections.get(task_id, []))


_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器单例"""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


class ProgressBroadcaster:
    """
    进度广播器

    将分析任务的进度实时广播给所有订阅者
    """

    def __init__(self):
        self._manager = get_connection_manager()
        self._task_events: Dict[str, asyncio.Event] = {}
        self._task_lock = threading.Lock()

    def register_task(self, task_id: str):
        """注册任务"""
        with self._task_lock:
            self._task_events[task_id] = asyncio.Event()

    def unregister_task(self, task_id: str):
        """注销任务"""
        with self._task_lock:
            if task_id in self._task_events:
                del self._task_events[task_id]

    async def broadcast_progress(
        self,
        task_id: str,
        session_id: str,
        agent_name: str,
        status: str,
        progress: float,
        message: str = "",
        data: Optional[Dict] = None,
    ):
        """
        广播进度更新

        Args:
            task_id: 任务ID
            session_id: 会话ID
            agent_name: 智能体名称
            status: 状态 (running/completed/failed)
            progress: 进度百分比
            message: 消息
            data: 额外数据
        """
        payload = {
            "type": "progress",
            "task_id": task_id,
            "session_id": session_id,
            "agent_name": agent_name,
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        if data:
            payload["data"] = data

        await self._manager.broadcast_task(task_id, payload)

    async def broadcast_agent_start(
        self, task_id: str, session_id: str, agent_name: str, action: str
    ):
        """广播智能体开始"""
        await self.broadcast_progress(
            task_id=task_id,
            session_id=session_id,
            agent_name=agent_name,
            status="agent_start",
            progress=0,
            message=f"开始执行: {action}",
        )

    async def broadcast_agent_complete(
        self,
        task_id: str,
        session_id: str,
        agent_name: str,
        progress: float,
        duration_ms: float,
    ):
        """广播智能体完成"""
        await self.broadcast_progress(
            task_id=task_id,
            session_id=session_id,
            agent_name=agent_name,
            status="agent_complete",
            progress=progress,
            message=f"执行完成 (耗时: {duration_ms:.2f}ms)",
        )

    async def broadcast_agent_error(
        self, task_id: str, session_id: str, agent_name: str, error: str
    ):
        """广播智能体错误"""
        await self.broadcast_progress(
            task_id=task_id,
            session_id=session_id,
            agent_name=agent_name,
            status="agent_error",
            progress=0,
            message=f"执行失败: {error}",
        )

    async def broadcast_debate_update(
        self,
        task_id: str,
        session_id: str,
        debate_type: str,
        round_num: int,
        message: str,
    ):
        """广播辩论更新"""
        payload = {
            "type": "debate",
            "task_id": task_id,
            "session_id": session_id,
            "debate_type": debate_type,
            "round": round_num,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        await self._manager.broadcast_task(task_id, payload)

    async def broadcast_task_complete(
        self,
        task_id: str,
        session_id: str,
        total_duration_ms: float,
        agents_count: int,
    ):
        """广播任务完成"""
        payload = {
            "type": "task_complete",
            "task_id": task_id,
            "session_id": session_id,
            "duration_ms": total_duration_ms,
            "agents_count": agents_count,
            "timestamp": datetime.now().isoformat(),
        }
        await self._manager.broadcast_task(task_id, payload)

    async def broadcast_task_error(
        self, task_id: str, session_id: str, error: str
    ):
        """广播任务错误"""
        payload = {
            "type": "task_error",
            "task_id": task_id,
            "session_id": session_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        await self._manager.broadcast_task(task_id, payload)


_broadcaster: Optional[ProgressBroadcaster] = None


def get_progress_broadcaster() -> ProgressBroadcaster:
    """获取进度广播器单例"""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = ProgressBroadcaster()
    return _broadcaster


class SSEProgressServer:
    """
    SSE（Server-Sent Events）进度服务器

    提供基于SSE的进度推送，作为WebSocket的备用方案
    """

    def __init__(self):
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._lock = threading.Lock()

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """订阅任务进度"""
        queue = asyncio.Queue()
        with self._lock:
            self._subscribers[task_id] = queue
        return queue

    async def unsubscribe(self, task_id: str):
        """取消订阅"""
        with self._lock:
            if task_id in self._subscribers:
                del self._subscribers[task_id]

    async def publish(self, task_id: str, event: Dict):
        """发布事件"""
        with self._lock:
            queue = self._subscribers.get(task_id)

        if queue:
            await queue.put(event)

    async def event_generator(self, task_id: str):
        """生成SSE事件流"""
        queue = await self.subscribe(task_id)

        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await self.unsubscribe(task_id)