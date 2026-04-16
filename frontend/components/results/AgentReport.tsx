type Props = {
  agentName: string;
  result: string;
  status: string;
};

export default function AgentReport({ agentName, result, status }: Props) {
  const statusColors: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    running: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    pending: "bg-gray-100 text-gray-700"
  };

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="font-semibold text-gray-900">{agentName}</h4>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusColors[status] || statusColors.pending}`}>
          {status}
        </span>
      </div>
      <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-4 rounded-lg max-h-96 overflow-auto">
        {result || "暂无结果"}
      </pre>
    </div>
  );
}

