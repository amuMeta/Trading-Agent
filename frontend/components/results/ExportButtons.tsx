"use client";

import { Api } from "@/lib/api";

async function downloadExport(
  format: "md" | "pdf" | "docx",
  sessionId: string,
  keyAgentsOnly: boolean
) {
  const response = await Api.exportFile(format, {
    session_id: sessionId,
    key_agents_only: keyAgentsOnly
  });
  const blob = new Blob([response.data]);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `report_${sessionId}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ExportButtons({ sessionId }: { sessionId: string }) {
  if (!sessionId) return null;
  return (
    <div className="card space-y-3">
      <h3 className="text-lg font-semibold text-gray-900">报告导出</h3>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <button className="rounded-lg bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 font-medium transition-colors active:scale-95" onClick={() => downloadExport("md", sessionId, false)}>
            📄 完整MD
          </button>
          <button className="rounded-lg bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 font-medium transition-colors active:scale-95" onClick={() => downloadExport("pdf", sessionId, false)}>
            📕 完整PDF
          </button>
          <button className="rounded-lg bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 font-medium transition-colors active:scale-95" onClick={() => downloadExport("docx", sessionId, false)}>
            📘 完整Word
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="rounded-lg bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 font-medium transition-colors active:scale-95" onClick={() => downloadExport("md", sessionId, true)}>
            ⭐ 关键MD
          </button>
          <button className="rounded-lg bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 font-medium transition-colors active:scale-95" onClick={() => downloadExport("pdf", sessionId, true)}>
            ⭐ 关键PDF
          </button>
          <button className="rounded-lg bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 font-medium transition-colors active:scale-95" onClick={() => downloadExport("docx", sessionId, true)}>
            ⭐ 关键Word
          </button>
        </div>
      </div>
    </div>
  );
}

