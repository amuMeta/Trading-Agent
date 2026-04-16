import Link from "next/link";

export default function Sidebar() {
  return (
    <aside className="min-h-screen w-56 border-r border-gray-200 bg-gray-50 p-4">
      <nav className="space-y-2">
        <Link 
          className="block rounded-lg bg-blue-500 text-white px-4 py-3 font-medium hover:bg-blue-600 transition-colors" 
          href="/"
        >
          📊 分析入口
        </Link>
        <Link 
          className="block rounded-lg bg-gray-100 text-gray-900 px-4 py-3 font-medium hover:bg-gray-200 transition-colors" 
          href="/history"
        >
          📜 历史会话
        </Link>
      </nav>
    </aside>
  );
}

