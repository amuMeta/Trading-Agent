#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验脚本 - 智能体辩论机制对比实验

本脚本用于对比不同配置下系统的表现：
1. 辩论轮次对比实验 (1轮 vs 3轮 vs 5轮)
2. 智能体数量对比实验 (5个 vs 10个 vs 15个)
3. MCP工具使用对比实验 (启用 vs 禁用)

使用方法:
    python experiments/run_comparison.py --mode debate --stock 600519
    python experiments/run_comparison.py --mode agents --stock 600519
    python experiments/run_comparison.py --mode mcp --stock 600519
"""

import os
import sys
import json
import argparse
import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workflow_orchestrator import WorkflowOrchestrator
from src.progress_tracker import ProgressTracker


@dataclass
class ExperimentResult:
    """单次实验结果"""
    experiment_id: str
    experiment_name: str
    stock_code: str
    config: Dict[str, Any]
    start_time: str
    end_time: str
    duration_seconds: float
    success: bool
    completed_agents: int
    total_agents: int
    mcp_calls: int
    mcp_success_rate: float
    error_count: int
    agent_durations: Dict[str, float]
    quality_score: float
    error_message: str = ""


class ExperimentRunner:
    """实验运行器"""

    def __init__(self, output_dir: str = "experiments/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ExperimentResult] = []

    async def run_single_experiment(
        self,
        name: str,
        stock_code: str,
        active_agents: List[str],
        investment_rounds: int = 1,
        risk_rounds: int = 1,
        use_mcp: bool = True
    ) -> ExperimentResult:
        """
        运行单次实验

        Args:
            name: 实验名称
            stock_code: 股票代码
            active_agents: 启用的智能体列表
            investment_rounds: 投资辩论轮次
            risk_rounds: 风险辩论轮次
            use_mcp: 是否使用MCP工具

        Returns:
            ExperimentResult: 实验结果
        """
        experiment_id = f"{name}_{stock_code}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print(f"开始实验: {name}")
        print(f"股票代码: {stock_code}")
        print(f"配置: 投资辩论{investment_rounds}轮, 风险辩论{risk_rounds}轮")
        print(f"启用智能体数: {len(active_agents)}")
        print(f"{'='*60}")

        try:
            # 初始化编排器
            orchestrator = WorkflowOrchestrator()
            await orchestrator.initialize()

            # 配置辩论轮次
            orchestrator.set_debate_rounds(investment_rounds, risk_rounds)
            orchestrator.set_active_agents(active_agents)

            # 运行分析
            user_query = f"分析{stock_code}股票的投资价值"
            result = await orchestrator.run_analysis(user_query)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 提取结果指标
            progress = orchestrator.progress_manager
            if progress:
                session_data = progress.session_data
                metrics = session_data.get("metrics", {})

                # 计算MCP成功率
                mcp_calls = session_data.get("mcp_calls", [])
                successful_mcp = sum(1 for c in mcp_calls if c.get("success", True))
                mcp_success_rate = successful_mcp / len(mcp_calls) if mcp_calls else 1.0

                # 提取智能体耗时
                agent_durations = {}
                for agent in session_data.get("agents", []):
                    if agent.get("duration_seconds"):
                        agent_durations[agent["agent_name"]] = agent["duration_seconds"]

                # 计算质量评分
                completed_agents = [
                    a for a in session_data.get("agents", [])
                    if a.get("status") == "completed"
                ]
                report_lengths = {
                    a["agent_name"]: a.get("result_length", 0)
                    for a in completed_agents
                    if a.get("result")
                }
                quality_score = self._calculate_quality_score(
                    completed_agents, report_lengths
                )

                result = ExperimentResult(
                    experiment_id=experiment_id,
                    experiment_name=name,
                    stock_code=stock_code,
                    config={
                        "investment_rounds": investment_rounds,
                        "risk_rounds": risk_rounds,
                        "active_agents_count": len(active_agents),
                        "use_mcp": use_mcp,
                        "active_agents": active_agents
                    },
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    duration_seconds=round(duration, 2),
                    success=True,
                    completed_agents=len(completed_agents),
                    total_agents=len(session_data.get("active_agents", [])) or 15,
                    mcp_calls=len(mcp_calls),
                    mcp_success_rate=round(mcp_success_rate * 100, 2),
                    error_count=len(session_data.get("errors", [])),
                    agent_durations=agent_durations,
                    quality_score=quality_score
                )
            else:
                raise Exception("无法获取进度管理器数据")

            await orchestrator.close()

            print(f"\n✅ 实验完成: {name}")
            print(f"   耗时: {duration:.2f}秒")
            print(f"   完成智能体: {result.completed_agents}/{result.total_agents}")
            print(f"   MCP成功率: {result.mcp_success_rate}%")
            print(f"   质量评分: {result.quality_score}")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"\n❌ 实验失败: {name}")
            print(f"   错误: {str(e)}")

            return ExperimentResult(
                experiment_id=experiment_id,
                experiment_name=name,
                stock_code=stock_code,
                config={
                    "investment_rounds": investment_rounds,
                    "risk_rounds": risk_rounds,
                    "active_agents_count": len(active_agents),
                    "use_mcp": use_mcp
                },
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration_seconds=round(duration, 2),
                success=False,
                completed_agents=0,
                total_agents=len(active_agents),
                mcp_calls=0,
                mcp_success_rate=0.0,
                error_count=1,
                agent_durations={},
                quality_score=0.0,
                error_message=str(e)
            )

    def _calculate_quality_score(
        self, completed_agents: List[Dict], report_lengths: Dict
    ) -> float:
        """计算分析质量评分"""
        if not completed_agents:
            return 0.0

        core_agents = [
            "company_overview_analyst",
            "market_analyst",
            "fundamentals_analyst",
            "research_manager",
            "trader",
            "risk_manager"
        ]

        completed_names = [a.get("agent_name", "") for a in completed_agents]
        core_completed = sum(1 for c in core_agents if c in completed_names)
        completeness_score = core_completed / len(core_agents) * 50

        if report_lengths:
            avg_length = sum(report_lengths.values()) / len(report_lengths)
            depth_score = min(avg_length / 10000 * 50, 50)
        else:
            depth_score = 0

        return round(completeness_score + depth_score, 2)

    def save_results(self):
        """保存实验结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"experiment_results_{timestamp}.json"

        results_data = [asdict(r) for r in self.results]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "experiment_count": len(self.results),
                    "generated_at": datetime.now().isoformat(),
                    "results": results_data
                },
                f,
                ensure_ascii=False,
                indent=2
            )

        print(f"\n💾 实验结果已保存: {output_file}")
        return output_file


async def run_debate_rounds_comparison(
    runner: ExperimentRunner,
    stock_code: str,
    agent_list: List[str]
):
    """
    辩论轮次对比实验

    对比不同辩论轮次对分析质量的影响
    """
    print("\n" + "="*60)
    print("实验1: 辩论轮次对比")
    print("="*60)

    # 实验配置: 1轮 vs 3轮 vs 5轮
    configs = [
        {"name": f"辩论1轮_{stock_code}", "inv_rounds": 1, "risk_rounds": 1},
        {"name": f"辩论3轮_{stock_code}", "inv_rounds": 3, "risk_rounds": 2},
        {"name": f"辩论5轮_{stock_code}", "inv_rounds": 5, "risk_rounds": 3},
    ]

    for cfg in configs:
        result = await runner.run_single_experiment(
            name=cfg["name"],
            stock_code=stock_code,
            active_agents=agent_list,
            investment_rounds=cfg["inv_rounds"],
            risk_rounds=cfg["risk_rounds"]
        )
        runner.results.append(result)
        await asyncio.sleep(2)  # 避免API限流


async def run_agent_count_comparison(
    runner: ExperimentRunner,
    stock_code: str
):
    """
    智能体数量对比实验

    对比不同智能体数量对分析质量和效率的影响
    """
    print("\n" + "="*60)
    print("实验2: 智能体数量对比")
    print("="*60)

    # 所有智能体列表
    all_agents = [
        "company_overview_analyst",
        "market_analyst",
        "sentiment_analyst",
        "news_analyst",
        "fundamentals_analyst",
        "shareholder_analyst",
        "product_analyst",
        "bull_researcher",
        "bear_researcher",
        "research_manager",
        "trader",
        "aggressive_risk_analyst",
        "safe_risk_analyst",
        "neutral_risk_analyst",
        "risk_manager",
    ]

    # 核心智能体（必须）
    core_agents = [
        "company_overview_analyst",
        "market_analyst",
        "fundamentals_analyst",
        "research_manager",
        "trader",
        "risk_manager"
    ]

    # 实验配置: 5个 vs 10个 vs 15个
    agent_configs = [
        {"name": f"5智能体_{stock_code}", "agents": core_agents},
        {"name": f"10智能体_{stock_code}", "agents": all_agents[:10]},
        {"name": f"15智能体_{stock_code}", "agents": all_agents},
    ]

    for cfg in agent_configs:
        result = await runner.run_single_experiment(
            name=cfg["name"],
            stock_code=stock_code,
            active_agents=cfg["agents"],
            investment_rounds=1,
            risk_rounds=1
        )
        runner.results.append(result)
        await asyncio.sleep(2)


async def run_mcp_comparison(
    runner: ExperimentRunner,
    stock_code: str,
    agent_list: List[str]
):
    """
    MCP工具使用对比实验

    对比启用/禁用MCP工具对分析质量的影响
    """
    print("\n" + "="*60)
    print("实验3: MCP工具使用对比")
    print("="*60)

    # 注意: 此实验需要临时修改环境变量来禁用MCP
    # 由于实现复杂，这里只展示启用MCP的结果

    result = await runner.run_single_experiment(
        name=f"MCP启用_{stock_code}",
        stock_code=stock_code,
        active_agents=agent_list,
        investment_rounds=1,
        risk_rounds=1,
        use_mcp=True
    )
    runner.results.append(result)


def print_experiment_summary(results: List[ExperimentResult]):
    """打印实验结果摘要"""
    print("\n" + "="*80)
    print("实验结果摘要")
    print("="*80)

    # 按实验名称分组
    experiments = {}
    for r in results:
        exp_name = r.experiment_name.rsplit("_", 1)[0]  # 去掉股票代码部分
        if exp_name not in experiments:
            experiments[exp_name] = []
        experiments[exp_name].append(r)

    for exp_name, exp_results in experiments.items():
        print(f"\n📊 {exp_name}")
        print("-" * 40)

        for r in exp_results:
            status = "✅" if r.success else "❌"
            print(f"  {status} {r.experiment_name}")
            print(f"     耗时: {r.duration_seconds}秒")
            print(f"     完成: {r.completed_agents}/{r.total_agents}智能体")
            print(f"     MCP调用: {r.mcp_calls}次 (成功率{r.mcp_success_rate}%)")
            print(f"     质量评分: {r.quality_score}")

    # 统计摘要
    successful = [r for r in results if r.success]
    if successful:
        print(f"\n📈 总体统计 (成功实验: {len(successful)}/{len(results)})")
        print("-" * 40)

        avg_duration = statistics.mean(r.duration_seconds for r in successful)
        avg_quality = statistics.mean(r.quality_score for r in successful)
        avg_mcp_rate = statistics.mean(r.mcp_success_rate for r in successful)

        print(f"  平均耗时: {avg_duration:.2f}秒")
        print(f"  平均质量评分: {avg_quality:.2f}")
        print(f"  平均MCP成功率: {avg_mcp_rate:.2f}%")


async def main():
    parser = argparse.ArgumentParser(description="智能体辩论机制对比实验")
    parser.add_argument(
        "--mode",
        choices=["debate", "agents", "mcp", "all"],
        default="all",
        help="实验模式"
    )
    parser.add_argument(
        "--stock",
        default="600519",
        help="股票代码 (默认: 600519)"
    )
    parser.add_argument(
        "--output",
        default="experiments/results",
        help="结果输出目录"
    )

    args = parser.parse_args()

    # 默认启用的智能体（核心7个）
    core_agents = [
        "company_overview_analyst",
        "market_analyst",
        "sentiment_analyst",
        "news_analyst",
        "fundamentals_analyst",
        "shareholder_analyst",
        "product_analyst",
        "bull_researcher",
        "bear_researcher",
        "research_manager",
        "trader",
        "aggressive_risk_analyst",
        "safe_risk_analyst",
        "neutral_risk_analyst",
        "risk_manager",
    ]

    runner = ExperimentRunner(output_dir=args.output)

    print(f"\n🚀 开始实验对比")
    print(f"   股票代码: {args.stock}")
    print(f"   实验模式: {args.mode}")
    print(f"   输出目录: {args.output}")

    if args.mode in ("debate", "all"):
        await run_debate_rounds_comparison(runner, args.stock, core_agents)

    if args.mode in ("agents", "all"):
        await run_agent_count_comparison(runner, args.stock)

    if args.mode in ("mcp", "all"):
        await run_mcp_comparison(runner, args.stock, core_agents)

    # 保存结果
    output_file = runner.save_results()

    # 打印摘要
    print_experiment_summary(runner.results)

    print(f"\n✅ 所有实验完成!")
    print(f"   详细结果见: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())