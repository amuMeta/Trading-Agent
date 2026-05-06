#!/usr/bin/env python
"""
TradingAgents 测试运行脚本

运行单元测试和集成测试

用法:
    python scripts/run_tests.py
    python scripts/run_tests.py --unit
    python scripts/run_tests.py --integration
    python scripts/run_tests.py --cov
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="运行测试")
    parser.add_argument("--unit", action="store_true", help="仅运行单元测试")
    parser.add_argument("--integration", action="store_true", help="仅运行集成测试")
    parser.add_argument("--cov", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--cov-html", action="store_true", help="生成HTML覆盖率报告")
    parser.add_argument("--watch", action="store_true", help="监视模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    tests_path = project_root / "tests"

    cmd = ["pytest", str(tests_path)]

    if args.verbose:
        cmd.append("-vv")

    if args.unit and not args.integration:
        cmd.extend(["-m", "unit"])

    if args.integration and not args.unit:
        cmd.extend(["-m", "integration"])

    if args.cov:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])

    if args.cov_html:
        cmd.extend(["--cov=src", "--cov-report=html"])

    if args.watch:
        cmd.append("--watch")

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())