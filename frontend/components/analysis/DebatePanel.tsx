"use client";

import { useState } from "react";

type DebateState = {
  count?: number;
  history?: string;
  bull_history?: string;
  bear_history?: string;
  current_response?: string;
};

type InvestmentDebate = DebateState & {
  count: number;
  history: string;
  bull_history: string;
  bear_history: string;
  current_response: string;
};

type RiskDebate = {
  aggressive_history?: string;
  safe_history?: string;
  neutral_history?: string;
  current_aggressive_response?: string;
  current_safe_response?: string;
  current_neutral_response?: string;
};

interface Props {
  investmentRounds: number;
  riskRounds: number;
  onChangeInvestment: (value: number) => void;
  onChangeRisk: (value: number) => void;
  investmentDebate?: InvestmentDebate | null;
  riskDebate?: RiskDebate | null;
  isRunning?: boolean;
}

export default function DebatePanel({
  investmentRounds,
  riskRounds,
  onChangeInvestment,
  onChangeRisk,
  investmentDebate,
  riskDebate,
  isRunning = false
}: Props) {
  const [activeTab, setActiveTab] = useState<"config" | "invest" | "risk">("config");

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <h3 className="text-lg font-semibold text-gray-900">🌀 辩论配置</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${isRunning ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>
          {isRunning ? "进行中" : "待开始"}
        </span>
      </div>

      {/* 标签页导航 */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        {[
          { key: "config", label: "配置" },
          { key: "invest", label: "投资辩论" },
          { key: "risk", label: "风险辩论" }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 配置面板 */}
      {activeTab === "config" && (
        <div className="space-y-4">
          <div className="space-y-2 rounded-lg bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">🐂 投资辩论轮次</span>
              <span className="font-mono text-lg font-bold text-green-600">{investmentRounds} 轮</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={investmentRounds}
              onChange={(e) => onChangeInvestment(Math.max(1, Number(e.target.value)))}
              className="w-full accent-green-500"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>1轮</span>
              <span>每轮: 看涨→看跌 各发言1次</span>
              <span>10轮</span>
            </div>
          </div>

          <div className="space-y-2 rounded-lg bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">⚖️ 风险辩论轮次</span>
              <span className="font-mono text-lg font-bold text-amber-600">{riskRounds} 轮</span>
            </div>
            <input
              type="range"
              min={1}
              max={9}
              value={riskRounds}
              onChange={(e) => onChangeRisk(Math.max(1, Number(e.target.value)))}
              className="w-full accent-amber-500"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>1轮</span>
              <span>每轮: 激进→保守→中性 各发言1次</span>
              <span>9轮</span>
            </div>
          </div>
        </div>
      )}

      {/* 投资辩论面板 */}
      {activeTab === "invest" && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className={`rounded-lg border p-4 ${investmentDebate?.bull_history ? "border-green-300 bg-green-50" : "border-gray-200 bg-gray-50"}`}>
              <div className="mb-2 flex items-center gap-2">
                <span className="text-lg">🐂</span>
                <span className="font-medium text-green-700">看涨方</span>
              </div>
              <div className="text-sm text-gray-700">
                {investmentDebate?.bull_history?.slice(0, 200) || "等待发言..."}
              </div>
            </div>
            <div className={`rounded-lg border p-4 ${investmentDebate?.bear_history ? "border-red-300 bg-red-50" : "border-gray-200 bg-gray-50"}`}>
              <div className="mb-2 flex items-center gap-2">
                <span className="text-lg">🐻</span>
                <span className="font-medium text-red-700">看跌方</span>
              </div>
              <div className="text-sm text-gray-700">
                {investmentDebate?.bear_history?.slice(0, 200) || "等待发言..."}
              </div>
            </div>
          </div>
          {investmentDebate?.count && (
            <div className="text-center text-xs text-gray-500">
              已完成 {investmentDebate.count} 轮辩论
            </div>
          )}
        </div>
      )}

      {/* 风险辩论面板 */}
      {activeTab === "risk" && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <div className={`rounded-lg border p-3 ${riskDebate?.aggressive_history ? "border-red-300 bg-red-50" : "border-gray-200 bg-gray-50"}`}>
              <div className="mb-1 flex items-center gap-1">
                <span className="text-sm">⚡</span>
                <span className="text-xs font-medium text-red-700">激进</span>
              </div>
              <div className="text-xs text-gray-700">
                {riskDebate?.aggressive_history?.slice(0, 100) || "等待..."}
              </div>
            </div>
            <div className={`rounded-lg border p-3 ${riskDebate?.safe_history ? "border-blue-300 bg-blue-50" : "border-gray-200 bg-gray-50"}`}>
              <div className="mb-1 flex items-center gap-1">
                <span className="text-sm">🛡️</span>
                <span className="text-xs font-medium text-blue-700">保守</span>
              </div>
              <div className="text-xs text-gray-700">
                {riskDebate?.safe_history?.slice(0, 100) || "等待..."}
              </div>
            </div>
            <div className={`rounded-lg border p-3 ${riskDebate?.neutral_history ? "border-gray-400 bg-gray-100" : "border-gray-200 bg-gray-50"}`}>
              <div className="mb-1 flex items-center gap-1">
                <span className="text-sm">⚖️</span>
                <span className="text-xs font-medium text-gray-700">中性</span>
              </div>
              <div className="text-xs text-gray-700">
                {riskDebate?.neutral_history?.slice(0, 100) || "等待..."}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}