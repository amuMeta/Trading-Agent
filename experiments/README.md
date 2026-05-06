# TradingAgents 实验指南

本目录包含用于评估和对比系统性能的实验脚本。

## 目录结构

```
experiments/
├── __init__.py              # Python包标识
├── run_comparison.py        # 对比实验脚本
├── report_template.md       # 实验报告模板
└── results/                 # 实验结果存放目录 (自动创建)
    └── experiment_results_*.json
```

## 快速开始

### 前置条件

1. 确保系统已正确配置（.env, mcp_config.json）
2. MCP服务已启动 (`stock-mcp` 服务)
3. 已安装依赖: `pip install -r requirements.txt`

### 运行实验

```bash
# 运行全部实验 (辩论轮次 + 智能体数量 + MCP对比)
python experiments/run_comparison.py --mode all --stock 600519

# 仅运行辩论轮次对比实验
python experiments/run_comparison.py --mode debate --stock 600519

# 仅运行智能体数量对比实验
python experiments/run_comparison.py --mode agents --stock 600519

# 仅运行MCP效果对比实验
python experiments/run_comparison.py --mode mcp --stock 600519
```

### 查看实验结果

实验结果会自动保存到 `experiments/results/` 目录，文件名格式为:
`experiment_results_YYYYMMDD_HHMMSS.json`

## 实验类型说明

### 1. 辩论轮次对比实验

验证不同辩论轮次(1/3/5轮)对分析质量和效率的影响。

**预期结论**:
- 更多辩论轮次 → 更高分析质量（边际效益递减）
- 更多辩论轮次 → 更长执行时间

### 2. 智能体数量对比实验

对比不同智能体配置(5/10/15个)对分析完整性的影响。

**预期结论**:
- 更多智能体 → 更完整分析（但有重叠冗余）
- 更多智能体 → 更长执行时间

### 3. MCP工具效果对比

验证MCP工具对数据获取和分析质量的影响。

**预期结论**:
- 启用MCP → 更准确的数据
- 启用MCP → 稍长执行时间（API调用）

## API评估接口

除了实验脚本，还可以通过API获取单个会话的评估数据:

```bash
# 获取会话评估
curl http://localhost:8000/api/analysis/{session_id}/evaluate

# 对比多个会话
curl "http://localhost:8000/api/analysis/compare?session_ids=id1,id2,id3"
```

## 生成实验报告

1. 运行实验收集数据
2. 复制 `report_template.md` 为新报告
3. 从 `experiments/results/` 目录读取JSON数据
4. 填写报告中的各项指标
5. 生成图表进行可视化分析

## 注意事项

1. 每次实验之间有2秒间隔，避免API限流
2. 建议在非高峰时段运行完整实验
3. 实验会占用较多API配额，请注意成本控制
4. 某些实验需要完整的MCP服务支持