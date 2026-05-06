import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
  timeout: 30000
});

export type SessionSummary = {
  session_id: string;
  status: string;
  user_query: string;
  created_at: string;
  file: string;
};

export type TaskSummary = {
  file: string;
  session_id: string;
  user_query: string;
  status: string;
  completed: number;
  total: number;
  progress: number;
  created_at: string;
  mtime: number;
};

export type DBSessionRecord = {
  session_id: string;
  user_query: string;
  stock_code: string;
  status: string;
  created_at: string;
  completed_at: string;
  duration_seconds: number;
  agents_count: number;
  mcp_calls_count: number;
  mcp_success_rate: number;
  error_count: number;
  quality_score: number;
};

export type DBStatistics = {
  total_sessions: number;
  completed_sessions: number;
  avg_duration_seconds: number;
  avg_mcp_success_rate: number;
  avg_quality_score: number;
  agent_statistics: Array<{
    agent_name: string;
    call_count: number;
    avg_duration: number;
    total_mcp_calls: number;
  }>;
  tool_statistics: Array<{
    tool_name: string;
    call_count: number;
    successful_calls: number;
  }>;
};

export const Api = {
  getCapabilities: () => api.get("/api/system/capabilities").then((r) => r.data),
  getHealth: () => api.get("/api/system/health").then((r) => r.data),
  getAgentConfig: () => api.get("/api/agents/config").then((r) => r.data),
  getStockKline: (stockCode: string, period?: string, limit?: number) =>
    api.get(`/api/stock/kline/${stockCode}`, { params: { period, limit } }).then((r) => r.data),
  getStockIndicators: (stockCode: string) =>
    api.get(`/api/stock/indicators/${stockCode}`).then((r) => r.data),
  getStockPrice: (stockCode: string) =>
    api.get(`/api/stock/price/${stockCode}`).then((r) => r.data),
  getMoneyFlow: (stockCode: string, days?: number) =>
    api.get(`/api/stock/money-flow/${stockCode}`, { params: { days } }).then((r) => r.data),
  getStockNews: (stockCode: string, limit?: number) =>
    api.get(`/api/stock/news/${stockCode}`, { params: { limit } }).then((r) => r.data),
  getStockInfo: (stockCode: string) =>
    api.get(`/api/stock/info/${stockCode}`).then((r) => r.data),
  startAnalysis: (payload: {
    query: string;
    active_agents: string[];
    investment_rounds: number;
    risk_rounds: number;
  }) => api.post("/api/analysis/start", payload).then((r) => r.data),
  cancelAnalysis: (taskId: string) =>
    api.post(`/api/analysis/${taskId}/cancel`).then((r) => r.data),
  getProgress: (taskId: string) =>
    api.get(`/api/analysis/${taskId}/progress`).then((r) => r.data),
  getTasks: () => api.get("/api/analysis/tasks").then((r) => r.data),
  getSessions: (status?: string) =>
    api
      .get("/api/sessions", { params: status ? { status } : undefined })
      .then((r) => r.data),
  getSession: (sessionId: string) =>
    api.get(`/api/sessions/${sessionId}`).then((r) => r.data),
  exportFile: (
    format: "md" | "pdf" | "docx",
    payload: { session_id: string; key_agents_only?: boolean }
  ) =>
    api.post(`/api/exports/${format}`, payload, { responseType: "blob" }).then((r) => r),
  evaluateSession: (sessionId: string) =>
    api.get(`/api/analysis/${sessionId}/evaluate`).then((r) => r.data),
  compareSessions: (sessionIds: string[], metricsType?: string) =>
    api.get("/api/analysis/compare", {
      params: { session_ids: sessionIds.join(","), metrics_type: metricsType }
    }).then((r) => r.data),
  searchDBSessions: (params: {
    stock_code?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
    min_quality_score?: number;
    limit?: number;
    offset?: number;
  }) => api.post("/api/db/sessions/search", null, { params }).then((r) => r.data),
  getDBSession: (sessionId: string) =>
    api.get(`/api/db/sessions/${sessionId}`).then((r) => r.data),
  getDBStatistics: () => api.get("/api/db/statistics").then((r) => r.data),
  importSessionToDB: (sessionId: string) =>
    api.post(`/api/db/sessions/${sessionId}/import`).then((r) => r.data),
  importAllSessionsToDB: () => api.post("/api/db/import-all").then((r) => r.data)
};

