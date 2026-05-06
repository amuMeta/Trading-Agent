"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/useAuth";
import { Api, DBSessionRecord } from "@/lib/api";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";

export default function HistoryPage() {
  const ready = useAuth();
  const [sessions, setSessions] = useState<DBSessionRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Api.searchDBSessions({ limit: 50 })
      .then((res) => {
        setSessions(res.sessions ?? []);
        setError("");
      })
      .catch(() => {
        Api.getSessions("completed")
          .then((res) => setSessions(res.sessions ?? []))
          .catch((e) => setError(e?.response?.data?.detail ?? "历史会话加载失败"));
      })
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
          <h1 className="mb-6 text-3xl font-bold text-gray-900">历史会话</h1>
          {error ? <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 mb-4">{error}</div> : null}
          <div className="space-y-3">
            {sessions.length === 0 ? (
              <div className="card text-center text-gray-500 py-8">暂无历史会话</div>
            ) : (
              sessions.map((s) => (
                <Link
                  className="card block hover:shadow-md hover:-translate-y-0.5 transition-all"
                  href={`/analysis/${s.session_id}`}
                  key={s.session_id}
                >
                  <div className="font-semibold text-gray-900">{s.user_query || s.session_id}</div>
                  <div className="text-sm text-gray-500 mt-1 flex flex-wrap gap-2 items-center">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                      s.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {s.status}
                    </span>
                    <span>股票: {s.stock_code}</span>
                    <span>用时: {s.duration_seconds}s</span>
                    {s.mcp_success_rate > 0 && (
                      <span>MCP成功率: {(s.mcp_success_rate * 100).toFixed(0)}%</span>
                    )}
                    {s.quality_score > 0 && (
                      <span>质量: {s.quality_score.toFixed(1)}</span>
                    )}
                    <span className="ml-auto">{s.created_at}</span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

