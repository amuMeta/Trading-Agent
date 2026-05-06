import json
import os
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

from src.core.paths import SESSION_DIR


class ProgressTracker:
    """简化的进度跟踪器 - 输出核心agent结果并保存到JSON"""

    def __init__(self, session_id: str = None):
        # 生成强唯一的会话ID：微秒 + UUID短码，避免并发同秒冲突
        self.session_id = session_id or f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:8]}"
        self.current_stage = ""
        self.current_agent = ""

        # 初始化dump文件夹和JSON文件
        self.dump_dir = SESSION_DIR
        os.makedirs(self.dump_dir, exist_ok=True)
        self.json_file = os.path.join(self.dump_dir, f"session_{self.session_id}.json")

        # 初始化JSON数据结构
        self.session_data = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active",
            "user_query": "",
            "active_agents": [],
            "stages": [],
            "agents": [],
            "actions": [],
            "mcp_calls": [],
            "errors": [],
            "warnings": [],
            "final_results": {},
            "metrics": {
                "total_duration_seconds": 0.0,
                "agent_executions": [],
                "mcp_tool_stats": {},
                "llm_call_count": 0,
                "llm_total_tokens": 0,
                "error_count": 0,
                "warning_count": 0,
                "success": True
            }
        }

        # 性能指标收集
        self._agent_start_times: Dict[str, float] = {}
        self._workflow_start_time: Optional[float] = None

        # 首次写入时确保原子创建，若意外存在则重新生成ID
        self._init_json_file()
        print(f"🚀 会话开始: {self.session_id}")
    
    def _init_json_file(self):
        """原子创建JSON文件，避免并发命名冲突。"""
        try:
            # 尝试独占创建；如已存在则换一个ID
            while True:
                try:
                    with open(self.json_file, 'x', encoding='utf-8') as f:
                        json.dump(self.session_data, f, ensure_ascii=False, indent=2)
                    break
                except FileExistsError:
                    # 极小概率碰撞，重生成ID与路径
                    self.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:8]}"
                    self.json_file = os.path.join(self.dump_dir, f"session_{self.session_id}.json")
        except Exception as e:
            print(f"❌ 初始化JSON失败: {e}")

    def _save_json(self):
        """保存数据到JSON文件（Windows友好：带重试的原子替换，必要时回退为直接写）。"""
        self.session_data["updated_at"] = datetime.now().isoformat()
        tmp_path = f"{self.json_file}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 写临时文件失败: {e}")
            return

        # Windows 下 os.replace 可能因目的文件被读取而临时拒绝访问；重试几次
        replaced = False
        for i in range(6):  # ~ 累计约 1.5 秒
            try:
                os.replace(tmp_path, self.json_file)
                replaced = True
                break
            except PermissionError as e:
                # 回退等待后重试
                time.sleep(0.25 * (i + 1))
            except Exception as e:
                print(f"❌ 替换JSON失败: {e}")
                break

        if not replaced:
            # 回退：直接覆盖写入目标（可能不是全原子，但尽量保证成功）
            try:
                with open(self.json_file, 'w', encoding='utf-8') as f:
                    json.dump(self.session_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"❌ 覆盖写入JSON失败: {e}")
            finally:
                # 清理残留临时文件
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
    
    def update_user_query(self, query: str):
        """更新用户查询"""
        self.session_data["user_query"] = query
        self._save_json()
        print(f"📝 用户查询: {query}")

    def set_active_agents(self, active_agents):
        """记录本轮启用的智能体列表"""
        try:
            self.session_data["active_agents"] = list(active_agents or [])
            self._save_json()
        except Exception:
            pass
    
    def start_stage(self, stage_name: str, description: str = ""):
        """开始新阶段"""
        self.current_stage = stage_name
        stage_data = {
            "stage_name": stage_name,
            "description": description,
            "start_time": datetime.now().isoformat()
        }
        self.session_data["stages"].append(stage_data)
        self._save_json()
        print(f"📍 阶段开始: {stage_name}")
        if description:
            print(f"   描述: {description}")
    
    def start_agent(self, agent_name: str, action: str = "", system_prompt: str = "", user_prompt: str = "", context: str = ""):
        """开始智能体工作"""
        self.current_agent = agent_name
        start_time_iso = datetime.now().isoformat()
        start_timestamp = time.time()

        agent_data = {
            "agent_name": agent_name,
            "action": action,
            "start_time": start_time_iso,
            "start_timestamp": start_timestamp,
            "status": "running",
            "result": "",
            "result_length": 0,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "context": context,
            "mcp_calls_count": 0,
            "llm_call_count": 0,
            "error": None
        }
        self.session_data["agents"].append(agent_data)
        self._agent_start_times[agent_name] = start_timestamp
        self._save_json()
        print(f"🤖 智能体开始工作: {agent_name}")
        if action:
            print(f"   执行: {action}")
    
    def complete_agent(self, agent_name: str, result: str = "", success: bool = True):
        """完成智能体工作"""
        end_time_iso = datetime.now().isoformat()
        end_timestamp = time.time()

        # 更新对应的agent记录
        for agent in self.session_data["agents"]:
            if agent["agent_name"] == agent_name and agent["status"] == "running":
                agent["status"] = "completed" if success else "failed"
                agent["result"] = result
                agent["result_length"] = len(result) if result else 0
                agent["end_time"] = end_time_iso
                agent["end_timestamp"] = end_timestamp

                # 计算执行时长
                start_ts = self._agent_start_times.get(agent_name, end_timestamp)
                duration = end_timestamp - start_ts
                agent["duration_seconds"] = round(duration, 3)

                # 更新全局指标
                self._update_agent_metrics(agent_name, duration, success)
                break

        self._save_json()
        status = "✅ 成功" if success else "❌ 失败"
        duration = agent.get("duration_seconds", 0) if success else 0
        print(f"🏁 智能体完成: {agent_name} - {status} (耗时: {duration:.3f}秒)")

        # 输出完整的agent结果内容
        if result:
            print(f"\n📋 {agent_name} 输出结果:")
            print("=" * 50)
            print(result[:500] + "..." if len(result) > 500 else result)
            print("=" * 50)
    
    def add_agent_action(self, agent_name: str, action: str, details: Dict[str, Any] = None):
        """添加智能体行动记录"""
        action_data = {
            "agent_name": agent_name,
            "action": action,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.session_data["actions"].append(action_data)
        self._save_json()
        print(f"🔄 {agent_name}: {action}")
    
    def add_mcp_tool_call(self, agent_name: str, tool_name: str, tool_args: Dict, tool_result: Any):
        """记录MCP工具调用"""
        mcp_data = {
            "agent_name": agent_name,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": str(tool_result)[:200] if tool_result else "",
            "timestamp": datetime.now().isoformat(),
            "success": not (isinstance(tool_result, dict) and "error" in tool_result)
        }
        self.session_data["mcp_calls"].append(mcp_data)

        # 更新智能体的MCP调用计数
        for agent in self.session_data["agents"]:
            if agent["agent_name"] == agent_name and agent["status"] == "running":
                agent["mcp_calls_count"] = agent.get("mcp_calls_count", 0) + 1
                break

        # 更新MCP工具统计
        tool_stats = self.session_data["metrics"].setdefault("mcp_tool_stats", {})
        if tool_name not in tool_stats:
            tool_stats[tool_name] = {"total_calls": 0, "successful_calls": 0, "failed_calls": 0}
        tool_stats[tool_name]["total_calls"] += 1
        if mcp_data["success"]:
            tool_stats[tool_name]["successful_calls"] += 1
        else:
            tool_stats[tool_name]["failed_calls"] += 1

        self._save_json()
        print(f"🔧 {agent_name} 调用工具: {tool_name}")
    
    def update_global_state(self, state_key: str, state_value: Any):
        """更新全局状态"""
        pass  # 简化：不再保存状态
    
    def update_debate_state(self, debate_type: str, debate_data: Dict[str, Any]):
        """更新辩论状态"""
        print(f"🗣️ 辩论更新: {debate_type} - 轮次 {debate_data.get('count', 0)}")
    
    def add_error(self, error_msg: str, agent_name: str = None):
        """添加错误记录"""
        error_data = {
            "error_msg": error_msg,
            "agent_name": agent_name or "",
            "timestamp": datetime.now().isoformat()
        }
        self.session_data["errors"].append(error_data)
        self._save_json()
        if agent_name:
            print(f"❌ {agent_name} 错误: {error_msg}")
        else:
            print(f"❌ 错误: {error_msg}")
    
    def add_warning(self, warning_msg: str, agent_name: str = None):
        """添加警告记录"""
        warning_data = {
            "warning_msg": warning_msg,
            "agent_name": agent_name or "",
            "timestamp": datetime.now().isoformat()
        }
        self.session_data["warnings"].append(warning_data)
        self._save_json()
        if agent_name:
            print(f"⚠️ {agent_name} 警告: {warning_msg}")
        else:
            print(f"⚠️ 警告: {warning_msg}")
    
    def set_final_results(self, results: Dict[str, Any]):
        """设置最终结果并计算最终性能指标"""
        # 计算总执行时长
        if self._workflow_start_time:
            total_duration = time.time() - self._workflow_start_time
            self.session_data["metrics"]["total_duration_seconds"] = round(total_duration, 2)

        # 统计错误和警告数量
        self.session_data["metrics"]["error_count"] = len(self.session_data["errors"])
        self.session_data["metrics"]["warning_count"] = len(self.session_data["warnings"])

        # 判断整体成功状态（无critical错误）
        critical_errors = [e for e in self.session_data["errors"] if "MCP" not in e.get("error_msg", "")]
        self.session_data["metrics"]["success"] = len(critical_errors) == 0

        # 统计LLM调用次数（基于agents记录）
        total_llm_calls = sum(agent.get("llm_call_count", 0) for agent in self.session_data["agents"])
        self.session_data["metrics"]["llm_call_count"] = total_llm_calls

        # 统计MCP调用成功率和工具使用排行
        mcp_calls = self.session_data["mcp_calls"]
        if mcp_calls:
            successful_mcp = sum(1 for call in mcp_calls if call.get("success", True))
            self.session_data["metrics"]["mcp_success_rate"] = round(successful_mcp / len(mcp_calls), 4)
            self.session_data["metrics"]["total_mcp_calls"] = len(mcp_calls)
        else:
            self.session_data["metrics"]["mcp_success_rate"] = 1.0
            self.session_data["metrics"]["total_mcp_calls"] = 0

        self.session_data["final_results"] = results
        self.session_data["status"] = "completed"
        self._save_json()
        print(f"🏁 会话完成 (总耗时: {self.session_data['metrics']['total_duration_seconds']}秒)")
        print("\n📊 性能指标:")
        print("=" * 60)
        self._print_metrics_summary()
        print("=" * 60)
    
    def _update_agent_metrics(self, agent_name: str, duration: float, success: bool):
        """更新智能体性能指标"""
        metrics = self.session_data["metrics"]
        agent_executions = metrics["agent_executions"]

        # 查找是否已有该智能体的记录
        existing = None
        for exec_data in agent_executions:
            if exec_data["agent_name"] == agent_name:
                existing = exec_data
                break

        if existing:
            # 更新现有记录
            existing["call_count"] += 1
            existing["total_duration"] += duration
            existing["avg_duration"] = existing["total_duration"] / existing["call_count"]
            if not success:
                existing["failure_count"] += 1
            existing["last_call_time"] = datetime.now().isoformat()
        else:
            # 新增记录
            agent_executions.append({
                "agent_name": agent_name,
                "call_count": 1,
                "total_duration": duration,
                "avg_duration": duration,
                "min_duration": duration,
                "max_duration": duration,
                "failure_count": 0 if success else 1,
                "last_call_time": datetime.now().isoformat()
            })

    def log_workflow_start(self, workflow_info: Dict[str, Any]):
        """记录工作流开始"""
        self._workflow_start_time = time.time()
        print(f"🚀 工作流开始: {workflow_info.get('user_query', '')}")
    
    def log_workflow_completion(self, completion_info: Dict[str, Any]):
        """记录工作流完成"""
        status = "成功" if completion_info.get("success", False) else "失败"
        print(f"🏁 工作流完成: {status}")
    
    def log_agent_start(self, agent_name: str, context: Dict[str, Any] = None):
        """记录智能体开始工作"""
        self.start_agent(agent_name, context.get("action", "") if context else "")
    
    def log_agent_complete(self, agent_name: str, result: Any = None, context: Dict[str, Any] = None):
        """记录智能体完成工作"""
        result_str = str(result) if result else ""
        success = context.get("success", True) if context else True
        self.complete_agent(agent_name, result_str, success)
    
    def log_llm_call(self, agent_name: str, prompt_preview: str, context: Dict[str, Any] = None):
        """记录LLM调用"""
        self.add_agent_action(agent_name, "LLM调用")
    
    def log_error(self, agent_name: str, error: str, context: Dict[str, Any] = None):
        """记录错误"""
        self.add_error(error, agent_name)
    
    def _print_metrics_summary(self):
        """打印性能指标摘要"""
        m = self.session_data["metrics"]
        print(f"  总执行时长: {m['total_duration_seconds']}秒")
        print(f"  智能体执行次数: {len(m['agent_executions'])}")
        print(f"  MCP工具调用次数: {m.get('total_mcp_calls', len(self.session_data['mcp_calls']))}")
        print(f"  MCP成功率: {m.get('mcp_success_rate', 1.0)*100:.1f}%")
        print(f"  错误数: {m['error_count']}")
        print(f"  警告数: {m['warning_count']}")

        # 各智能体耗时排行
        if m["agent_executions"]:
            sorted_agents = sorted(m["agent_executions"], key=lambda x: x["total_duration"], reverse=True)
            print("\n  各智能体耗时:")
            for a in sorted_agents[:5]:
                print(f"    {a['agent_name']}: {a['avg_duration']:.3f}秒 (调用{a['call_count']}次)")

        # MCP工具使用排行
        tool_stats = m.get("mcp_tool_stats", {})
        if tool_stats:
            sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1]["total_calls"], reverse=True)
            print("\n  MCP工具使用排行 (Top5):")
            for tool_name, stats in sorted_tools[:5]:
                print(f"    {tool_name}: {stats['total_calls']}次 (成功{stats['successful_calls']}次)")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取性能指标摘要（用于API返回）"""
        m = self.session_data["metrics"]
        return {
            "total_duration_seconds": m["total_duration_seconds"],
            "agent_executions": m["agent_executions"],
            "total_mcp_calls": m.get("total_mcp_calls", len(self.session_data["mcp_calls"])),
            "mcp_success_rate": m.get("mcp_success_rate", 1.0),
            "mcp_tool_stats": m.get("mcp_tool_stats", {}),
            "llm_call_count": m["llm_call_count"],
            "error_count": m["error_count"],
            "warning_count": m["warning_count"],
            "success": m["success"]
        }

    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        return {
            "session_id": self.session_id,
            "status": self.session_data["status"],
            "user_query": self.session_data["user_query"],
            "active_agents_count": len(self.session_data["active_agents"]),
            "total_agents_count": len(self.session_data["agents"]),
            "completed_agents_count": len([a for a in self.session_data["agents"] if a.get("status") == "completed"]),
            "metrics": self.get_metrics_summary()
        }