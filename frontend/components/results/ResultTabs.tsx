"use client";

import { useMemo, useState } from "react";
import AgentReport from "./AgentReport";

type AgentItem = {
  agent_name: string;
  result: string;
  status: string;
};

const groups: Record<string, string[]> = {
  "分析师团队": [
    "company_overview_analyst",
    "market_analyst",
    "sentiment_analyst",
    "news_analyst",
    "fundamentals_analyst",
    "shareholder_analyst",
    "product_analyst"
  ],
  "看涨看跌辩论": ["bull_researcher", "bear_researcher"],
  "研究与交易": ["research_manager", "trader"],
  "风险管理": [
    "aggressive_risk_analyst",
    "safe_risk_analyst",
    "neutral_risk_analyst",
    "risk_manager"
  ]
};

export default function ResultTabs({ agents }: { agents: AgentItem[] }) {
  const tabNames = Object.keys(groups);
  const [activeTab, setActiveTab] = useState(tabNames[0]);

  const filtered = useMemo(() => {
    const include = new Set(groups[activeTab] ?? []);
    return agents.filter((a) => include.has(a.agent_name));
  }, [activeTab, agents]);

  return (
    <div className="space-y-4">
      <div className="flex border-b border-gray-200">
        {tabNames.map((tab) => (
          <button
            key={tab}
            className={`px-4 py-3 font-medium transition-colors ${
              tab === activeTab
                ? "text-blue-500 border-b-2 border-blue-500"
                : "text-gray-600 hover:text-gray-900"
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {filtered.map((agent) => (
          <AgentReport
            key={`${agent.agent_name}-${agent.status}`}
            agentName={agent.agent_name}
            result={agent.result}
            status={agent.status}
          />
        ))}
      </div>
    </div>
  );
}

