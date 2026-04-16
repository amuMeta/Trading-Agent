"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { Api, SessionSummary } from "@/lib/api";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";

export default function HistoryPage() {
  const ready = useAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    Api.getSessions("completed")
      .then((res) => {
        setSessions(res.sessions ?? []);
        setError("");
      })
      .catch((e) => {
        setError(e?.response?.data?.detail ?? "历史会话加载失败");
        setSessions([]);
      });
  }, [ready]);

  if (!ready) return (
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
                  <div className="text-sm text-gray-500 mt-1">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mr-2 ${
                      s.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {s.status}
                    </span>
                    {s.created_at}
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

