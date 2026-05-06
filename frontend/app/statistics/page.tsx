"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/useAuth";
import { Api, DBStatistics } from "@/lib/api";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";

export default function StatisticsPage() {
  const ready = useAuth();
  const [stats, setStats] = useState<DBStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    Api.getDBStatistics()
      .then((res) => setStats(res))
      .catch((e) => setError(e?.response?.data?.detail ?? "统计加载失败"))
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready || loading) return (
    <div className="fixed inset-0 flex items-center justify-center bg-white">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500" />
    </div>
  );

  return (
    <main className="bg-gray-50 min-h-screen">
      <Header />
      <div className="flex">
        <Sidebar />
        <section className="flex-1 p-8">
          <h1 className="mb-6 text-3xl font-bold text-gray-900">统计分析</h1>
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 mb-4">{error}</div>
          )}
          {stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="card">
                  <div className="text-2xl font-bold text-blue-600">{stats.total_sessions}</div>
                  <div className="text-sm text-gray-500">总会话数</div>
                </div>
                <div className="card">
                  <div className="text-2xl font-bold text-green-600">{stats.completed_sessions}</div>
                  <div className="text-sm text-gray-500">已完成会话</div>
                </div>
                <div className="card">
                  <div className="text-2xl font-bold text-purple-600">{stats.avg_duration_seconds}s</div>
                  <div className="text-sm text-gray-500">平均用时</div>
                </div>
                <div className="card">
                  <div className="text-2xl font-bold text-orange-600">{stats.avg_mcp_success_rate}%</div>
                  <div className="text-sm text-gray-500">MCP成功率</div>
                </div>
              </div>

              {stats.agent_statistics && stats.agent_statistics.length > 0 && (
                <div className="card">
                  <h2 className="text-lg font-semibold mb-4">智能体使用统计</h2>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2">智能体</th>
                          <th className="text-right py-2">调用次数</th>
                          <th className="text-right py-2">平均耗时</th>
                          <th className="text-right py-2">MCP调用数</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.agent_statistics.map((agent: any) => (
                          <tr key={agent.agent_name} className="border-b last:border-0">
                            <td className="py-2 font-mono text-xs">{agent.agent_name}</td>
                            <td className="text-right">{agent.call_count}</td>
                            <td className="text-right">{agent.avg_duration?.toFixed(2)}s</td>
                            <td className="text-right">{agent.total_mcp_calls}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {stats.tool_statistics && stats.tool_statistics.length > 0 && (
                <div className="card">
                  <h2 className="text-lg font-semibold mb-4">MCP工具使用统计</h2>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2">工具</th>
                          <th className="text-right py-2">调用次数</th>
                          <th className="text-right py-2">成功次数</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.tool_statistics.map((tool: any) => (
                          <tr key={tool.tool_name} className="border-b last:border-0">
                            <td className="py-2 font-mono text-xs">{tool.tool_name}</td>
                            <td className="text-right">{tool.call_count}</td>
                            <td className="text-right">{tool.successful_calls}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}