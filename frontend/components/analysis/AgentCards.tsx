"use client";

type TeamConfig = {
  emoji: string;
  color: string;
  hoverColor: string;
  bgColor: string;
};

const teamStyles: Record<string, TeamConfig> = {
  analysts: { emoji: "📊", color: "border-blue-500", hoverColor: "hover:border-blue-400", bgColor: "bg-blue-50" },
  researchers: { emoji: "🔬", color: "border-violet-500", hoverColor: "hover:border-violet-400", bgColor: "bg-violet-50" },
  managers: { emoji: "👔", color: "border-amber-500", hoverColor: "hover:border-amber-400", bgColor: "bg-amber-50" },
  risk: { emoji: "⚖️", color: "border-green-500", hoverColor: "hover:border-green-400", bgColor: "bg-green-50" },
};

type Props = {
  teams: Record<string, string[]>;
  displayNames: Record<string, string>;
  selected: Record<string, boolean>;
  onToggle: (agent: string, value: boolean) => void;
  onSelectAll: (value: boolean) => void;
  agentStatus?: Record<string, "pending" | "running" | "completed" | "failed">;
};

export default function AgentCards({
  teams,
  displayNames,
  selected,
  onToggle,
  onSelectAll,
  agentStatus = {}
}: Props) {
  const selectedCount = Object.values(selected).filter(Boolean).length;
  const totalCount = Object.keys(selected).length;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">🤖 智能体选择</h3>
          <p className="text-xs text-gray-500">已选择 {selectedCount}/{totalCount} 个智能体</p>
        </div>
        <div className="flex gap-2">
          <button
            className="rounded-lg bg-green-100 px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-200 transition-colors active:scale-95"
            onClick={() => onSelectAll(true)}
          >
            全选
          </button>
          <button
            className="rounded-lg bg-red-100 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-200 transition-colors active:scale-95"
            onClick={() => onSelectAll(false)}
          >
            全不选
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(teams).map(([team, agents]) => {
          const style = teamStyles[team] || teamStyles.analysts;
          const teamSelected = agents.filter(a => selected[a]).length;
          
          return (
            <div key={team} className="space-y-2">
              <div className="flex items-center gap-2">
                <span>{style.emoji}</span>
                <span className="text-sm font-medium text-gray-700">{team}</span>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {teamSelected}/{agents.length}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                {agents.map((agent) => {
                  const isSelected = selected[agent] ?? false;
                  const status = agentStatus[agent];
                  const statusColor = {
                    pending: "bg-gray-400",
                    running: "bg-blue-500 animate-pulse",
                    completed: "bg-green-500",
                    failed: "bg-red-500"
                  }[status || "pending"];
                  
                  return (
                    <label
                      key={agent}
                      className={`flex cursor-pointer items-center gap-2 rounded-xl border p-3 transition-all hover:shadow-md hover:-translate-y-0.5 ${
                        isSelected 
                          ? `${style.color} ${style.bgColor} ${style.hoverColor}` 
                          : "border-gray-200 hover:border-gray-300 bg-white"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => onToggle(agent, e.target.checked)}
                        className="accent-blue-500 rounded h-4 w-4"
                      />
                      <div className="flex flex-1 flex-col gap-1">
                        <span className={`text-sm font-medium ${isSelected ? "text-gray-900" : "text-gray-600"}`}>
                          {displayNames[agent] ?? agent}
                        </span>
                        {status && (
                          <div className="flex items-center gap-1">
                            <span className={`h-1.5 w-1.5 rounded-full ${statusColor}`}></span>
                            <span className="text-xs text-gray-500">{status}</span>
                          </div>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}