"use client";

import { useEffect, useState } from "react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onStart: () => void;
  onStop: () => void;
  running: boolean;
  onLoadKline?: () => void;
};

export default function QueryInput({
  value,
  onChange,
  onStart,
  onStop,
  running,
  onLoadKline
}: Props) {
  const [error, setError] = useState("");

  // 自动提取股票代码
  const stockCode = value.match(/(\d{6})/)?.[1] || "";

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-10 shadow-sm hover:shadow-lg transition-shadow">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-2xl font-bold text-gray-900">🔍 查询输入</h3>
        {stockCode && (
          <span className="rounded-full bg-green-100 px-4 py-2 text-sm font-semibold text-green-700">
            识别代码: {stockCode}
          </span>
        )}
      </div>
      
      <div className="space-y-5">
        <input
          className="w-full rounded-xl border-2 border-gray-200 bg-white px-6 py-5 text-gray-900 text-lg placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all"
          placeholder="输入股票代码或公司名称，例如：600519贵州茅台"
          value={value}
          onChange={(e) => {
            setError("");
            onChange(e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && value && !running) {
              onStart();
            }
          }}
        />
        
        <div className="flex items-center gap-4">
          <button
            className={`flex-1 rounded-xl px-8 py-5 text-lg font-semibold transition-all duration-300 active:scale-95 ${
              running
                ? "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30"
                : value
                  ? "bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
            onClick={running ? onStop : onStart}
            disabled={!value && !running}
          >
            {running ? "⏹ 停止分析" : "🚀 开始分析"}
          </button>
          
          {stockCode && onLoadKline && (
            <button
              className="rounded-xl bg-blue-500 hover:bg-blue-600 text-white px-8 py-5 text-lg font-semibold transition-all duration-300 active:scale-95 shadow-lg shadow-blue-500/30"
              onClick={onLoadKline}
            >
              📈 K线
            </button>
          )}
          
          {running && (
            <div className="flex items-center gap-3 text-blue-500 px-4">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></span>
              <span className="text-base font-semibold">分析中...</span>
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-xl border-2 border-red-200 bg-red-50 px-6 py-4 text-base text-red-700">
            {error}
          </div>
        )}
        
        <div className="text-sm text-gray-500">
          💡 提示：输入6位股票代码（如600519）或公司名称（如贵州茅台）
        </div>
      </div>
    </div>
  );
}