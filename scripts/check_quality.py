#!/usr/bin/env python
"""
TradingAgents 代码质量检查脚本

运行所有代码质量检查：
- ruff lint
- ruff format check
- mypy type check

用法:
    python scripts/check_quality.py
    python scripts/check_quality.py --fix  # 自动修复格式问题
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> int:
    """运行命令并报告结果"""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="运行代码质量检查")
    parser.add_argument("--fix", action="store_true", help="自动修复格式问题")
    parser.add_argument("--skip-format", action="store_true", help="跳过格式检查")
    parser.add_argument("--skip-lint", action="store_true", help="跳过lint检查")
    parser.add_argument("--skip-type", action="store_true", help="跳过类型检查")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"
    tests_path = project_root / "tests"

    errors = []

    if not args.skip_format:
        fmt_cmd = ["ruff", "format", "--check", str(src_path)]
        if args.fix:
            fmt_cmd = ["ruff", "format", str(src_path)]
            fmt_cmd[2] = "--fix"

        ret = run_command(fmt_cmd, "代码格式检查")
        if ret != 0 and not args.fix:
            errors.append("代码格式检查失败")
        elif args.fix:
            print("✓ 格式问题已自动修复")

    if not args.skip_lint:
        lint_cmd = ["ruff", "check", str(src_path)]
        if args.fix:
            lint_cmd.append("--fix")

        ret = run_command(lint_cmd, "代码Lint检查")
        if ret != 0 and not args.fix:
            errors.append("Lint检查失败")
        elif args.fix:
            print("✓ Lint问题已自动修复")

    if not args.skip_type:
        type_cmd = ["mypy", str(src_path), "--ignore-missing-imports"]
        ret = run_command(type_cmd, "静态类型检查")
        if ret != 0:
            errors.append("类型检查失败")

    print(f"\n{'=' * 60}")
    print(f"  检查完成")
    print(f"{'=' * 60}")

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个问题:")
        for error in errors:
            print(f"   - {error}")
        return 1
    else:
        print("\n✓ 所有检查通过!")
        return 0


if __name__ == "__main__":
    sys.exit(main())