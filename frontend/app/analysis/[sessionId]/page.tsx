"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { Api } from "@/lib/api";
import ResultTabs from "@/components/results/ResultTabs";
import ExportButtons from "@/components/results/ExportButtons";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";

export default function AnalysisDetailPage({
  params
}: {
  params: { sessionId: string };
}) {
  const ready = useAuth();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    Api.getSession(params.sessionId)
      .then((res) => {
        setData(res);
        setError("");
      })
      .catch((e) => {
        setError(e?.response?.data?.detail ?? "会话加载失败");
        setData(null);
      });
  }, [params.sessionId, ready]);

  if (!ready) return (
    <div className="fixed inset-0 flex items-center justify-center bg-white">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500" />
    </div>
  );

  if (error) {
    return (
      <main className="bg-gray-50 min-h-screen">
        <Header />
        <div className="flex">
          <Sidebar />
          <section className="flex-1 p-8">
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">
              加载失败: {error}
            </div>
          </section>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="bg-gray-50 min-h-screen">
        <Header />
        <div className="flex">
          <Sidebar />
          <section className="flex-1 p-8">
            <div className="card text-center text-gray-500 py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-500 mb-2"></div>
              <div>加载中...</div>
            </div>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="bg-gray-50 min-h-screen">
      <Header />
      <div className="flex">
        <Sidebar />
        <section className="flex-1 space-y-6 p-8">
          <h1 className="text-3xl font-bold text-gray-900">会话详情</h1>
          <div className="card">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg bg-gray-50 p-4">
                <div className="text-xs text-gray-500">会话ID</div>
                <div className="text-sm font-medium text-gray-900 mt-1">{data.session_id}</div>
              </div>
              <div className="rounded-lg bg-gray-50 p-4">
                <div className="text-xs text-gray-500">状态</div>
                <div className={`text-sm font-medium mt-1 ${
                  data.status === 'completed' ? 'text-green-600' : 'text-gray-900'
                }`}>{data.status}</div>
              </div>
              <div className="rounded-lg bg-gray-50 p-4">
                <div className="text-xs text-gray-500">查询</div>
                <div className="text-sm font-medium text-gray-900 mt-1">{data.user_query}</div>
              </div>
            </div>
          </div>
          <ResultTabs agents={data.agents ?? []} />
          <div className="card space-y-3">
            <h3 className="text-lg font-semibold text-gray-900">错误与警告</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-gray-50 p-3">
                <div className="text-xs text-gray-500">错误数</div>
                <div className="text-lg font-bold text-red-600">{(data.errors ?? []).length}</div>
              </div>
              <div className="rounded-lg bg-gray-50 p-3">
                <div className="text-xs text-gray-500">警告数</div>
                <div className="text-lg font-bold text-amber-600">{(data.warnings ?? []).length}</div>
              </div>
            </div>
            <pre className="whitespace-pre-wrap text-xs text-gray-700 bg-gray-50 p-4 rounded-lg overflow-auto max-h-64">
              {JSON.stringify(
                {
                  errors: data.errors ?? [],
                  warnings: data.warnings ?? [],
                  mcp_calls: data.mcp_calls ?? [],
                  final_results: data.final_results ?? {}
                },
                null,
                2
              )}
            </pre>
          </div>
          <ExportButtons sessionId={data.session_id} />
        </section>
      </div>
    </main>
  );
}

