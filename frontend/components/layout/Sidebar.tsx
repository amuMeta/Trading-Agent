import Link from "next/link";

export default function Sidebar() {
  return (
    <aside className="sticky top-0 w-56 h-screen border-r border-gray-200 bg-gray-50 p-4 flex-shrink-0">
      <nav className="space-y-2">
        <Link
          className="block rounded-lg px-4 py-3 font-medium transition-colors bg-gray-100 text-gray-900 hover:bg-blue-500 hover:text-white"
          href="/chat"
        >
          💬 智能对话
        </Link>
        <Link
          className="block rounded-lg px-4 py-3 font-medium transition-colors bg-gray-100 text-gray-900 hover:bg-blue-500 hover:text-white"
          href="/"
        >
          📊 分析入口
        </Link>
        <Link
          className="block rounded-lg px-4 py-3 font-medium transition-colors bg-gray-100 text-gray-900 hover:bg-blue-500 hover:text-white"
          href="/history"
        >
          📜 历史会话
        </Link>
        <Link
          className="block rounded-lg px-4 py-3 font-medium transition-colors bg-gray-100 text-gray-900 hover:bg-blue-500 hover:text-white"
          href="/knowledge"
        >
          📚 知识库管理
        </Link>
      </nav>

      <div className="mt-6 p-3 bg-white rounded-lg border border-gray-200">
        <div className="text-xs text-gray-500 mb-2">💡 提示</div>
        <div className="text-xs text-gray-400">
          智能对话基于RAG技术，可以回答关于您之前分析过的股票问题
        </div>
      </div>
    </aside>
  );
}