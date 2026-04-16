"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { Api, TaskSummary } from "@/lib/api";
import { useAnalysisStore, useSessionStore, useSystemStore } from "@/lib/stores";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import AgentSelector from "@/components/layout/AgentSelector";
import QueryInput from "@/components/analysis/QueryInput";
import AgentCards from "@/components/analysis/AgentCards";
import DebatePanel from "@/components/analysis/DebatePanel";
import ResultTabs from "@/components/results/ResultTabs";
import ExportButtons from "@/components/results/ExportButtons";
import PriceChart from "@/components/charts/PriceChart";
import StockDataPanel from "@/components/charts/StockDataPanel";

export default function HomePage() {
  const ready = useAuth();
  const router = useRouter();
  const { connected, capabilities, setConnected, setCapabilities } = useSystemStore();
  const { taskId, sessionId, status, running, setTask, setStatus } = useAnalysisStore();
  const {
    currentSessionData,
    historySessions,
    setCurrentSessionData,
    setHistorySessions
  } = useSessionStore();
  const [query, setQuery] = useState("");
  const [teams, setTeams] = useState<Record<string, string[]>>({});
  const [displayNames, setDisplayNames] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [investmentRounds, setInvestmentRounds] = useState(1);
  const [riskRounds, setRiskRounds] = useState(1);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [health, setHealth] = useState<{ env_exists: boolean; mcp_config_exists: boolean } | null>(null);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [indicators, setIndicators] = useState<any>(null);
  const [realTimePrice, setRealTimePrice] = useState<any>(null);

  // 加载K线数据
  const loadKlineData = async (stockCode: string) => {
    try {
      const [klineRes, indRes, priceRes] = await Promise.all([
        Api.getStockKline(stockCode, "30d"),
        Api.getStockIndicators(stockCode),
        Api.getStockPrice(stockCode)
      ]);
      if (klineRes?.data?.data) {
        setKlineData(klineRes.data.data);
      }
      if (indRes?.indicators) {
        setIndicators(indRes.indicators);
      }
      if (priceRes?.price) {
        setRealTimePrice(priceRes.price[0]);
      }
    } catch (e) {
      console.error("加载K线失败:", e);
    }
  };

  useEffect(() => {
    Api.getCapabilities()
      .then((res) => {
        setConnected(true);
        setCapabilities(res.workflow_info ?? null);
      })
      .catch(() => {
        setConnected(false);
        setCapabilities(null);
      });
    Api.getAgentConfig().then((cfg) => {
      setTeams(cfg.teams ?? {});
      setDisplayNames(cfg.display_names ?? {});
      setSelected(cfg.defaults ?? {});
    });
    Api.getSessions("completed").then((res) => setHistorySessions(res.sessions ?? []));
    Api.getHealth().then(setHealth).catch(() => setHealth(null));
  }, [setCapabilities, setConnected, setHistorySessions]);

  useEffect(() => {
    if (!running || !taskId) return;
    const timer = setInterval(async () => {
      try {
        const progress = await Api.getProgress(taskId);
        if (progress.session_id) {
          setTask(taskId, progress.session_id);
        }
        if (progress.session_data) {
          setCurrentSessionData(progress.session_data);
        }
        if (progress.error) {
          setAnalysisError(progress.error);
        }
        if (["completed", "failed", "cancelled", "cancelling"].includes(progress.task_status)) {
          setStatus(progress.task_status);
        }
      } catch {
        // Ignore transient polling errors to avoid runtime crash.
      }
    }, 2500);
    return () => clearInterval(timer);
  }, [running, taskId, setCurrentSessionData, setStatus, setTask]);

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const res = await Api.getTasks();
        setTasks((res.tasks ?? []) as TaskSummary[]);
      } catch {
        setTasks([]);
      }
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const selectedAgents = useMemo(
    () => Object.keys(selected).filter((k) => selected[k]),
    [selected]
  );

  // 转换K线数据为图表格式
  const chartData = useMemo(() => {
    if (!klineData.length) return [];
    return klineData.map((item: any) => ({
      time: item.date?.slice(5) || item.time || "",
      price: item.close || item.price || 0,
      volume: item.volume || 0,
      open: item.open || 0,
      high: item.high || 0,
      low: item.low || 0
    }));
  }, [klineData]);

  if (!ready) return (
    <div className="fixed inset-0 flex items-center justify-center bg-white">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500" />
    </div>
  );

  return (
    <main className="bg-gradient-to-b from-gray-50 via-white to-gray-50 min-h-screen">
      <Header />
      <div className="flex">
        <Sidebar />
        
        {/* 主内容区 - 居中布局，两侧留白 */}
        <section className="flex-1 overflow-y-auto">
          <div className="container-centered py-16 space-y-16">
            
            {/* 顶部状态卡片组 */}
            <div className="grid gap-8 md:grid-cols-3">
              <AgentSelector count={selectedAgents.length} />
              <div className="card text-center">
                <span className="text-sm text-gray-500 block mb-3">系统状态</span>
                <div className={`text-3xl font-bold ${connected ? "text-green-600" : "text-red-600"}`}>
                  {connected ? "✓ 已连接" : "✗ 未连接"}
                </div>
              </div>
              <div className="card text-center">
                <span className="text-sm text-gray-500 block mb-3">任务状态</span>
                <div className="text-3xl font-bold text-gray-900">{status}</div>
              </div>
            </div>

            {/* 查询输入 */}
            <QueryInput
              value={query}
              onChange={setQuery}
              running={running}
              onStart={async () => {
                const code = query.match(/(\d{6})/)?.[1];
                if (code) {
                  loadKlineData(code);
                }
                setAnalysisError("");
                try {
                  const res = await Api.startAnalysis({
                    query,
                    active_agents: selectedAgents,
                    investment_rounds: investmentRounds,
                    risk_rounds: riskRounds
                  });
                  setTask(res.task_id, res.session_id ?? "");
                  setStatus("running");
                } catch (e: any) {
                  setAnalysisError(e?.response?.data?.detail ?? "启动分析失败");
                }
              }}
              onStop={async () => {
                if (!taskId) return;
                await Api.cancelAnalysis(taskId);
                setStatus("cancelling");
              }}
              onLoadKline={() => {
                const code = query.match(/(\d{6})/)?.[1];
                if (code) {
                  loadKlineData(code);
                }
              }}
            />
            
            {analysisError && (
              <div className="card border-red-200 bg-red-50 text-red-700">
                <div className="flex items-center gap-3">
                  <svg className="w-6 h-6 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span>{analysisError}</span>
                </div>
              </div>
            )}

            {/* 智能体选择 */}
            <AgentCards
              teams={teams}
              displayNames={displayNames}
              selected={selected}
              onToggle={(agent, value) =>
                setSelected((prev) => ({ ...prev, [agent]: value }))
              }
              onSelectAll={(value) =>
                setSelected((prev) =>
                  Object.fromEntries(Object.keys(prev).map((k) => [k, value]))
                )
              }
            />

            {/* 辩论配置 */}
            <DebatePanel
              investmentRounds={investmentRounds}
              riskRounds={riskRounds}
              onChangeInvestment={setInvestmentRounds}
              onChangeRisk={setRiskRounds}
              investmentDebate={currentSessionData?.final_results?.final_state?.investment_debate_state as any ?? currentSessionData?.investment_debate_state as any}
              riskDebate={currentSessionData?.final_results?.final_state?.risk_debate_state as any ?? currentSessionData?.risk_debate_state as any}
              isRunning={running}
            />

            {/* K线图表 */}
            <PriceChart 
              data={chartData} 
              indicators={indicators} 
              stockCode={query.match(/(\d{6})/)?.[1]} 
            />
            
            {/* 股票数据面板 */}
            {query.match(/(\d{6})/) && (
              <StockDataPanel stockCode={query.match(/(\d{6})/)?.[1]!} />
            )}

            {/* 当前任务进度 */}
            <div className="card">
              <h3 className="text-2xl font-bold text-gray-900 mb-8">当前任务进度</h3>
              {tasks.length === 0 ? (
                <div className="text-center text-gray-400 py-16 text-lg">
                  <div className="text-6xl mb-4">📊</div>
                  <div>暂无进行中的任务</div>
                </div>
              ) : (
                <div className="space-y-5">
                  {tasks.map((t) => (
                    <button
                      key={t.session_id}
                      className="block w-full rounded-2xl border-2 border-gray-200 p-6 text-left hover:border-blue-400 hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-white"
                      onClick={async () => {
                        const data = await Api.getSession(t.session_id);
                        setCurrentSessionData(data);
                        setTask(taskId, t.session_id);
                      }}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <span className="font-semibold text-gray-900 text-lg">{t.user_query || t.session_id}</span>
                        <span className="text-sm text-gray-500 font-medium bg-gray-100 px-3 py-1 rounded-full">{t.completed}/{t.total}</span>
                      </div>
                      <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
                        <div 
                          className="h-3 rounded-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-700 ease-out" 
                          style={{ width: `${Math.min(100, Math.max(0, t.progress))}%` }} 
                        />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 历史会话 */}
            <div className="card">
              <h3 className="text-2xl font-bold text-gray-900 mb-8">历史会话</h3>
              <select
                className="w-full rounded-xl border-2 border-gray-200 bg-white p-5 text-gray-900 text-lg focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all cursor-pointer"
                value={selectedHistoryId}
                onChange={async (e) => {
                  const id = e.target.value;
                  setSelectedHistoryId(id);
                  if (!id) return;
                  const data = await Api.getSession(id);
                  setCurrentSessionData(data);
                  setTask(taskId, id);
                }}
              >
                <option value="">请选择历史会话…</option>
                {historySessions.map((s: any) => (
                  <option key={s.session_id} value={s.session_id}>
                    {(s.user_query || s.session_id).slice(0, 48)}
                  </option>
                ))}
              </select>
            </div>

            {/* 辩论状态 */}
            <div className="card">
              <h3 className="text-2xl font-bold text-gray-900 mb-8">辩论状态</h3>
              <div className="space-y-6">
                <div className="rounded-2xl bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 p-8 border border-green-100">
                  <h4 className="font-bold text-gray-800 mb-4 text-lg flex items-center gap-2">
                    <span className="text-2xl">🐂</span>
                    投资辩论
                  </h4>
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 overflow-auto max-h-64 font-mono">
                    {JSON.stringify(currentSessionData?.final_results?.final_state?.investment_debate_state ?? currentSessionData?.investment_debate_state ?? {}, null, 2)}
                  </pre>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-amber-50 via-orange-50 to-red-50 p-8 border border-amber-100">
                  <h4 className="font-bold text-gray-800 mb-4 text-lg flex items-center gap-2">
                    <span className="text-2xl">⚖️</span>
                    风险辩论
                  </h4>
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 overflow-auto max-h-64 font-mono">
                    {JSON.stringify(currentSessionData?.final_results?.final_state?.risk_debate_state ?? currentSessionData?.risk_debate_state ?? {}, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* 系统概览 */}
            <div className="card">
              <h3 className="text-2xl font-bold text-gray-900 mb-8">系统概览</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-100 p-8 text-center border border-blue-200 hover:shadow-lg transition-shadow">
                  <div className="text-sm text-gray-600 mb-3 font-medium">.env</div>
                  <div className={`text-4xl font-bold ${health?.env_exists ? "text-green-600" : "text-red-600"}`}>
                    {health?.env_exists ? "✓" : "✗"}
                  </div>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-purple-50 to-pink-100 p-8 text-center border border-purple-200 hover:shadow-lg transition-shadow">
                  <div className="text-sm text-gray-600 mb-3 font-medium">mcp_config</div>
                  <div className={`text-4xl font-bold ${health?.mcp_config_exists ? "text-green-600" : "text-red-600"}`}>
                    {health?.mcp_config_exists ? "✓" : "✗"}
                  </div>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-green-50 to-teal-100 p-8 text-center border border-green-200 hover:shadow-lg transition-shadow">
                  <div className="text-sm text-gray-600 mb-3 font-medium">MCP工具</div>
                  <div className="text-3xl font-bold text-gray-900">
                    {capabilities?.mcp_tools_info?.total_tools ?? "-"}
                  </div>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-orange-50 to-yellow-100 p-8 text-center border border-orange-200 hover:shadow-lg transition-shadow">
                  <div className="text-sm text-gray-600 mb-3 font-medium">MCP服务器</div>
                  <div className="text-3xl font-bold text-gray-900">
                    {capabilities?.mcp_tools_info?.server_count ?? "-"}
                  </div>
                </div>
              </div>
            </div>

            {/* 分析结果 */}
            {currentSessionData?.agents?.length ? (
              <ResultTabs agents={currentSessionData.agents} />
            ) : (
              <div className="card text-center text-gray-400 py-16">
                <div className="text-6xl mb-4">📋</div>
                <div className="text-xl">暂无分析结果</div>
              </div>
            )}

            {/* 错误与警告 */}
            <div className="card">
              <h3 className="text-2xl font-bold text-gray-900 mb-8">错误与警告</h3>
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="rounded-2xl bg-gradient-to-br from-red-50 to-rose-100 p-8 text-center border border-red-200">
                  <div className="text-sm text-gray-600 mb-2 font-medium">错误数</div>
                  <div className="text-4xl font-bold text-red-600">{(currentSessionData?.errors ?? []).length}</div>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-amber-50 to-yellow-100 p-8 text-center border border-amber-200">
                  <div className="text-sm text-gray-600 mb-2 font-medium">警告数</div>
                  <div className="text-4xl font-bold text-amber-600">{(currentSessionData?.warnings ?? []).length}</div>
                </div>
              </div>
              <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-6 rounded-2xl overflow-auto max-h-96 border border-gray-200 font-mono">
                {JSON.stringify(
                  {
                    errors: currentSessionData?.errors ?? [],
                    warnings: currentSessionData?.warnings ?? [],
                    mcp_calls: currentSessionData?.mcp_calls ?? []
                  },
                  null,
                  2
                )}
              </pre>
            </div>

            {/* 导出按钮 */}
            <ExportButtons sessionId={sessionId} />

            {/* 底部间距 */}
            <div className="h-16"></div>
          </div>
        </section>
      </div>
    </main>
  );
}
