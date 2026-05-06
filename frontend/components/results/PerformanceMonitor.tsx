"use client";

import { useEffect, useState } from "react";
import { Api, DBStatistics } from "@/lib/api";

interface PerformanceMonitorProps {
  className?: string;
}

export default function PerformanceMonitor({ className = "" }: PerformanceMonitorProps) {
  const [stats, setStats] = useState<DBStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdate, setLastUpdate] = useState<string>("");

  useEffect(() => {
    loadStatistics();
    const timer = setInterval(loadStatistics, 30000);
    return () => clearInterval(timer);
  }, []);

  const loadStatistics = async () => {
    try {
      const data = await Api.getDBStatistics();
      setStats(data);
      setLastUpdate(new Date().toLocaleTimeString());
      setError("");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load statistics");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={`card ${className}`}>
        <h3 className="text-2xl font-bold text-gray-900 mb-4">📊 性能监控</h3>
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`card ${className}`}>
        <h3 className="text-2xl font-bold text-gray-900 mb-4">📊 性能监控</h3>
        <div className="text-red-500 text-center py-4">{error}</div>
        <button
          onClick={loadStatistics}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          重试
        </button>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className={`card ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold text-gray-900">📊 性能监控</h3>
        <span className="text-sm text-gray-400">更新: {lastUpdate}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-indigo-100 p-4 rounded-xl border border-blue-200">
          <div className="text-sm text-gray-600 mb-1">总会话数</div>
          <div className="text-3xl font-bold text-blue-600">{stats.total_sessions}</div>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-emerald-100 p-4 rounded-xl border border-green-200">
          <div className="text-sm text-gray-600 mb-1">已完成</div>
          <div className="text-3xl font-bold text-green-600">{stats.completed_sessions}</div>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-pink-100 p-4 rounded-xl border border-purple-200">
          <div className="text-sm text-gray-600 mb-1">平均耗时</div>
          <div className="text-3xl font-bold text-purple-600">
            {stats.avg_duration_seconds.toFixed(1)}s
          </div>
        </div>
        <div className="bg-gradient-to-br from-amber-50 to-orange-100 p-4 rounded-xl border border-amber-200">
          <div className="text-sm text-gray-600 mb-1">MCP成功率</div>
          <div className="text-3xl font-bold text-amber-600">
            {stats.avg_mcp_success_rate.toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="mb-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-3">🤖 智能体使用统计</h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {stats.agent_statistics?.slice(0, 10).map((agent) => (
            <div
              key={agent.agent_name}
              className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
            >
              <span className="text-sm font-medium text-gray-700 truncate">{agent.agent_name}</span>
              <div className="flex items-center gap-4">
                <span className="text-xs text-gray-500">
                  {agent.call_count}次
                </span>
                <span className="text-xs text-gray-500">
                  {agent.avg_duration?.toFixed(2)}s
                </span>
              </div>
            </div>
          )) || <div className="text-gray-400 text-sm">暂无数据</div>}
        </div>
      </div>

      <div>
        <h4 className="text-lg font-semibold text-gray-800 mb-3">🔧 MCP工具使用排行</h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {stats.tool_statistics?.slice(0, 10).map((tool) => (
            <div
              key={tool.tool_name}
              className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
            >
              <span className="text-sm font-medium text-gray-700 truncate">{tool.tool_name}</span>
              <div className="flex items-center gap-4">
                <span className="text-xs text-gray-500">{tool.call_count}次</span>
                <span className="text-xs text-green-500">
                  {tool.successful_calls}成功
                </span>
              </div>
            </div>
          )) || <div className="text-gray-400 text-sm">暂无数据</div>}
        </div>
      </div>

      <button
        onClick={loadStatistics}
        className="mt-4 w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
      >
        刷新数据
      </button>
    </div>
  );
}