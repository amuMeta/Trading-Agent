"""
TradingAgents 测试配置

提供测试夹具和配置
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-for-testing")
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
os.environ.setdefault("MCP_CACHE_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_LEVEL", "DEBUG")