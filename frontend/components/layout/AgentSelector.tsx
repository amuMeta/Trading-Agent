type Props = {
  count: number;
};

export default function AgentSelector({ count }: Props) {
  return (
    <div className="card text-center group hover:scale-105 transition-transform duration-300">
      <div className="text-sm text-gray-500 mb-3 font-medium">当前已选智能体</div>
      <div className="text-5xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
        {count}
      </div>
    </div>
  );
}

