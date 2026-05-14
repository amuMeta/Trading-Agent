import os
import requests
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps


CACHE_ENABLED = os.getenv("MCP_CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_SHORT = int(os.getenv("MCP_CACHE_TTL_SHORT", "60"))
CACHE_TTL_MEDIUM = int(os.getenv("MCP_CACHE_TTL_MEDIUM", "300"))
CACHE_TTL_LONG = int(os.getenv("MCP_CACHE_TTL_LONG", "1800"))


class MCPCache:
    """
    MCP响应缓存

    为不同的MCP工具提供差异化的缓存策略：
    - 实时行情：60秒TTL
    - 技术指标：5分钟TTL
    - 基本面数据：30分钟TTL
    """

    def __init__(self):
        self._memory_cache = None
        self._enabled = CACHE_ENABLED

    def _get_cache(self):
        if self._memory_cache is None:
            from src.core.cache import get_memory_cache
            self._memory_cache = get_memory_cache()
        return self._memory_cache

    def _make_key(self, tool_name: str, params: Dict) -> str:
        import hashlib
        import json
        key_data = json.dumps({"tool": tool_name, "params": params}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, tool_name: str, params: Dict) -> Optional[Dict]:
        if not self._enabled:
            return None
        cache = self._get_cache()
        key = self._make_key(tool_name, params)
        return cache.get(key)

    def set(self, tool_name: str, params: Dict, result: Dict):
        if not self._enabled:
            return

        cache = self._get_cache()
        key = self._make_key(tool_name, params)

        ttl = self._get_ttl_for_tool(tool_name)
        cache.set(key, result, ttl)

    def _get_ttl_for_tool(self, tool_name: str) -> int:
        """根据工具类型返回合适的TTL"""
        if tool_name in ("get_real_time_price", "get_kline_data"):
            return CACHE_TTL_SHORT
        elif tool_name in ("get_technical_indicators", "get_money_flow"):
            return CACHE_TTL_MEDIUM
        elif tool_name in ("get_financial_reports", "get_valuation_metrics", "get_asset_info"):
            return CACHE_TTL_LONG
        return CACHE_TTL_MEDIUM

    def invalidate(self, tool_name: str, params: Dict):
        if not self._enabled:
            return
        cache = self._get_cache()
        key = self._make_key(tool_name, params)
        cache.delete(key)

    def clear(self):
        if not self._enabled:
            return
        cache = self._get_cache()
        cache.clear()

    def get_stats(self) -> Dict:
        if not self._enabled:
            return {"enabled": False}
        cache = self._get_cache()
        return {"enabled": True, **cache.get_stats()}


_mcp_cache: Optional[MCPCache] = None


def get_mcp_cache() -> MCPCache:
    global _mcp_cache
    if _mcp_cache is None:
        _mcp_cache = MCPCache()
    return _mcp_cache


def with_retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """
    Exponential backoff retry decorator for functions that make HTTP requests.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if isinstance(result, dict) and "error" in result:
                        error_msg = result.get("error", "")
                        if any(e in error_msg.lower() for e in ["timeout", "connection", "refused", "network"]):
                            last_exception = Exception(error_msg)
                            if attempt < max_attempts - 1:
                                delay = min(base_delay * (2 ** attempt), max_delay)
                                time.sleep(delay)
                                continue
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        time.sleep(delay)
                    else:
                        return {"error": str(e)}
            return {"error": str(last_exception)}
        return wrapper
    return decorator


def normalize_stock_code(user_input: str) -> str:
    """将用户输入转换为 stock-mcp 需要的格式"""
    if not user_input:
        return ""
    user_input = user_input.strip()
    if ":" in user_input:
        return user_input
    code = re.findall(r"\d{6}", user_input)
    if code:
        return f"SSE:{code[0]}"
    return user_input


class StockMCPHTTPClient:
    """直接通过HTTP API调用stock-mcp服务器（带缓存支持）"""

    BASE_URL = "http://127.0.0.1:9898/api/v1"

    def __init__(self, base_url: str = None, use_cache: bool = True):
        self.BASE_URL = base_url or "http://127.0.0.1:9898/api/v1"
        self.session = requests.Session()
        self._use_cache = use_cache and CACHE_ENABLED
        self._cache = get_mcp_cache() if self._use_cache else None

    @with_retry(max_attempts=3, base_delay=1.0)
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET请求"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}", params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("请求超时")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"连接失败: {e}")
        except Exception as e:
            return {"error": str(e)}

    @with_retry(max_attempts=3, base_delay=1.0)
    def _post(self, endpoint: str, data: Dict = None) -> Dict:
        """POST请求"""
        try:
            response = self.session.post(
                f"{self.BASE_URL}{endpoint}", json=data, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("请求超时")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"连接失败: {e}")
        except Exception as e:
            return {"error": str(e)}

    def _get_cached(self, tool_name: str, params: Dict, fallback_func) -> Dict:
        """带缓存的GET请求"""
        if self._use_cache and self._cache:
            cached = self._cache.get(tool_name, params)
            if cached is not None:
                return cached

        result = fallback_func()
        if self._use_cache and self._cache and "error" not in result:
            self._cache.set(tool_name, params, result)
        return result

    def _post_cached(self, tool_name: str, params: Dict, fallback_func) -> Dict:
        """带缓存的POST请求"""
        if self._use_cache and self._cache:
            cached = self._cache.get(tool_name, params)
            if cached is not None:
                return cached

        result = fallback_func()
        if self._use_cache and self._cache and "error" not in result:
            self._cache.set(tool_name, params, result)
        return result

    # ========== market (3个工具) ==========
    def get_kline_data(
        self, symbol: str, period: str = "30d", interval: str = "1d"
    ) -> Dict:
        """获取K线数据"""
        params = {"symbol": symbol, "period": period, "interval": interval}

        def _fetch():
            return self._post(
                "/market/prices/history",
                {
                    "symbol": normalize_stock_code(symbol),
                    "period": period,
                    "interval": interval,
                },
            )

        return self._post_cached("get_kline_data", params, _fetch)

    def get_real_time_price(self, tickers: List[str]) -> Dict:
        """批量获取实时价格"""
        params = {"tickers": tuple(sorted(tickers))}

        def _fetch():
            normalized_tickers = [normalize_stock_code(t) for t in tickers]
            return self._post("/market/prices/batch", {"tickers": normalized_tickers})

        return self._post_cached("get_real_time_price", params, _fetch)

    def get_asset_info(self, symbol: str) -> Dict:
        """获取资产信息"""
        params = {"symbol": symbol}

        def _fetch():
            return self._get("/market/asset/info", {"symbol": normalize_stock_code(symbol)})

        return self._get_cached("get_asset_info", params, _fetch)

    # ========== technical (3个工具) ==========
    def get_technical_indicators(
        self, symbol: str, period: str = "30d", interval: str = "1d"
    ) -> Dict:
        """计算技术指标"""
        params = {"symbol": symbol, "period": period, "interval": interval}

        def _fetch():
            return self._post(
                "/technical/indicators/calculate",
                {
                    "symbol": normalize_stock_code(symbol),
                    "period": period,
                    "interval": interval,
                },
            )

        return self._post_cached("get_technical_indicators", params, _fetch)

    def generate_trading_signal(
        self, symbol: str, period: str = "30d", interval: str = "1d"
    ) -> Dict:
        """生成交易信号"""
        params = {"symbol": symbol, "period": period, "interval": interval}

        def _fetch():
            return self._post(
                "/technical/signals/trading",
                {
                    "symbol": normalize_stock_code(symbol),
                    "period": period,
                    "interval": interval,
                },
            )

        return self._post_cached("generate_trading_signal", params, _fetch)

    def calculate_support_resistance(self, symbol: str, period: str = "90d") -> Dict:
        """计算支撑阻力位"""
        params = {"symbol": symbol, "period": period}

        def _fetch():
            return self._post(
                "/technical/analysis/support-resistance",
                {"symbol": normalize_stock_code(symbol), "period": period},
            )

        return self._post_cached("calculate_support_resistance", params, _fetch)

    # ========== fundamental (3个工具) ==========
    def get_financial_reports(self, symbol: str) -> Dict:
        """获取财务报告"""
        params = {"symbol": symbol}

        def _fetch():
            return self._get(
                "/fundamental/report", {"symbol": normalize_stock_code(symbol)}
            )

        return self._get_cached("get_financial_reports", params, _fetch)

    def get_valuation_metrics(self, symbol: str) -> Dict:
        """获取估值指标"""
        params = {"symbol": symbol}

        def _fetch():
            return self._get(
                "/fundamental/ratios", {"symbol": normalize_stock_code(symbol)}
            )

        return self._get_cached("get_valuation_metrics", params, _fetch)

    def get_us_valuation_metrics(self, symbol: str) -> Dict:
        """获取美股估值指标"""
        params = {"symbol": symbol}
        return self._get("/fundamental/ratios", {"symbol": symbol})

    # ========== money_flow (3个工具) ==========
    def get_money_flow(self, symbol: str, days: int = 20) -> Dict:
        """获取资金流向"""
        params = {"symbol": symbol, "days": days}

        def _fetch():
            return self._get(
                f"/money-flow/stock/{normalize_stock_code(symbol)}", {"days": days}
            )

        return self._get_cached("get_money_flow", params, _fetch)

    def get_north_bound_flow(self, days: int = 30) -> Dict:
        """获取北向资金"""
        params = {"days": days}
        return self._get("/money-flow/north-bound", {"days": days})

    def get_chip_distribution(self, symbol: str) -> Dict:
        """获取筹码分布"""
        params = {"symbol": symbol}

        def _fetch():
            return self._get(
                f"/money-flow/chip-distribution/{normalize_stock_code(symbol)}"
            )

        return self._get_cached("get_chip_distribution", params, _fetch)

    # ========== news (3个工具) ==========
    def get_stock_news(
        self, symbol: str, days_back: int = 7, limit: int = 10
    ) -> Dict:
        """获取股票新闻"""
        params = {"symbol": symbol, "days_back": days_back, "limit": limit}

        def _fetch():
            return self._get(
                "/news/stock",
                {
                    "symbol": normalize_stock_code(symbol),
                    "days_back": days_back,
                    "limit": limit,
                },
            )

        return self._get_cached("get_stock_news", params, _fetch)

    def get_latest_news(self, query: str, days_back: int = 7, limit: int = 10) -> Dict:
        """获取最新新闻"""
        params = {"query": query, "days_back": days_back, "limit": limit}
        return self._get(
            "/news/search", {"query": query, "days_back": days_back, "limit": limit}
        )

    def get_us_news_sentiment(self, symbol: str, days_back: int = 3) -> Dict:
        """获取美股新闻情绪"""
        params = {"symbol": symbol, "days_back": days_back}
        return self._get(
            "/news/sentiment/us", {"symbol": symbol, "days_back": days_back}
        )

    # ========== filings (5个工具) ==========
    def get_sec_periodic_filings(
        self, ticker: str, year: int = 2024, limit: int = 10
    ) -> Dict:
        """获取SEC定期披露"""
        params = {"ticker": ticker, "year": year, "limit": limit}
        return self._get(
            "/filings/sec/periodic", {"ticker": ticker, "year": year, "limit": limit}
        )

    def get_sec_event_filings(self, ticker: str, limit: int = 10) -> Dict:
        """获取SEC事件披露"""
        params = {"ticker": ticker, "limit": limit}
        return self._get("/filings/sec/event", {"ticker": ticker, "limit": limit})

    def get_ashare_filings(self, symbol: str, limit: int = 10) -> Dict:
        """获取A股公告"""
        params = {"symbol": symbol, "limit": limit}
        return self._get("/filings/ashare", {"symbol": symbol, "limit": limit})

    def get_filings_markdown(self, ticker: str, doc_id: str) -> Dict:
        """获取公告markdown"""
        params = {"ticker": ticker, "doc_id": doc_id}
        return self._get("/filings/markdown", {"ticker": ticker, "doc_id": doc_id})

    def get_filings_chunks(self, ticker: str, doc_id: str) -> Dict:
        """获取公告chunk"""
        params = {"ticker": ticker, "doc_id": doc_id}
        return self._get("/filings/chunks", {"ticker": ticker, "doc_id": doc_id})

    # ========== code_export (2个工具) ==========
    def export_tushare_code(self, api_name: str, kwargs: Dict) -> Dict:
        """导出tushare代码"""
        return self._post(
            "/code-export/tushare/csv", {"api_name": api_name, "kwargs": kwargs}
        )

    def export_alphavantage_code(self, function: str, symbol: str) -> Dict:
        """导出alphavantage代码"""
        return self._post(
            "/code-export/alphavantage/json", {"function": function, "symbol": symbol}
        )

    # ========== 工具调用统一入口 ==========
    def call_tool(self, tool_name: str, params: Dict = None) -> Dict:
        """统一工具调用入口"""
        params = params or {}

        tool_mapping = {
            # market
            "get_kline_data": lambda: self.get_kline_data(**params),
            "get_real_time_price": lambda: self.get_real_time_price(**params),
            "get_asset_info": lambda: self.get_asset_info(**params),
            # technical
            "get_technical_indicators": lambda: self.get_technical_indicators(**params),
            "generate_trading_signal": lambda: self.generate_trading_signal(**params),
            "calculate_support_resistance": lambda: self.calculate_support_resistance(
                **params
            ),
            # fundamental
            "get_financial_reports": lambda: self.get_financial_reports(**params),
            "get_valuation_metrics": lambda: self.get_valuation_metrics(**params),
            "get_us_valuation_metrics": lambda: self.get_us_valuation_metrics(**params),
            # money_flow
            "get_money_flow": lambda: self.get_money_flow(**params),
            "get_north_bound_flow": lambda: self.get_north_bound_flow(**params),
            "get_chip_distribution": lambda: self.get_chip_distribution(**params),
            # news
            "get_stock_news": lambda: self.get_stock_news(**params),
            "get_latest_news": lambda: self.get_latest_news(**params),
            "get_us_news_sentiment": lambda: self.get_us_news_sentiment(**params),
            # filings
            "get_sec_periodic_filings": lambda: self.get_sec_periodic_filings(**params),
            "get_sec_event_filings": lambda: self.get_sec_event_filings(**params),
            "get_ashare_filings": lambda: self.get_ashare_filings(**params),
            "get_filings_markdown": lambda: self.get_filings_markdown(**params),
            "get_filings_chunks": lambda: self.get_filings_chunks(**params),
            # code_export
            "export_tushare_code": lambda: self.export_tushare_code(**params),
            "export_alphavantage_code": lambda: self.export_alphavantage_code(**params),
        }

        if tool_name in tool_mapping:
            return tool_mapping[tool_name]()
        else:
            return {"error": f"Unknown tool: {tool_name}"}


def normalize_stock_code_to_tencent(user_input: str) -> str:
    """将用户输入转换为腾讯财经需要的格式"""
    if not user_input:
        return ""
    user_input = user_input.strip()
    if user_input.startswith(("sh", "sz")):
        return user_input
    code = re.findall(r"\d{6}", user_input)
    if code:
        code = code[0]
        if code.startswith(("6", "9")):
            return f"sh{code}"
        else:
            return f"sz{code}"
    return user_input


class TencentHTTPClient:
    """腾讯财经数据源HTTP客户端"""

    BASE_URL = "https://web.ifzjq.gtimg.cn/appstock/app/fqkline/get"

    def __init__(self, use_cache: bool = True):
        self.session = requests.Session()
        self._use_cache = use_cache and CACHE_ENABLED
        self._cache = get_mcp_cache() if self._use_cache else None

    def _get_cached(self, tool_name: str, params: Dict, fallback_func) -> Dict:
        if self._use_cache and self._cache:
            cached = self._cache.get(tool_name, params)
            if cached is not None:
                return cached
        result = fallback_func()
        if self._use_cache and self._cache and "error" not in result:
            self._cache.set(tool_name, params, result)
        return result

    def _parse_period(self, period: str) -> tuple:
        """解析period参数，返回(type, days)"""
        if period.endswith("d"):
            days = int(period[:-1])
            if days <= 5:
                return ("day", 5)
            elif days <= 20:
                return ("day", days)
            elif days <= 60:
                return ("week", days // 7 + 1)
            else:
                return ("month", days // 30 + 1)
        elif period.endswith("w"):
            return ("week", int(period[:-1]))
        elif period.endswith("m"):
            return ("month", int(period[:-1]))
        return ("day", 30)

    def get_kline_data(self, symbol: str, period: str = "30d", interval: str = "1d") -> Dict:
        """获取K线数据"""
        params = {"symbol": symbol, "period": period}
        tencent_symbol = normalize_stock_code_to_tencent(symbol)
        period_type, limit = self._parse_period(period)
        if limit > 320:
            limit = 320

        def _fetch():
            url = f"{self.BASE_URL}?_var=kline_{period_type}&param={tencent_symbol},{period_type},,,,,{limit},qfq&r=0.1"
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                text = response.text
                return self._parse_tencent_response(text)
            except Exception as e:
                return {"error": str(e)}

        return self._get_cached("tencent_kline_data", params, _fetch)

    def _parse_tencent_response(self, text: str) -> Dict:
        """解析腾讯财经K线数据响应"""
        try:
            import json
            match = re.search(r"=(.+)$", text)
            if not match:
                return {"error": "Invalid response format"}
            data = json.loads(match.group(1))
            qfqkey = data.get("qfqkey", "")
            data_list = data.get("data", {}).get(qfqkey, {}).get("day", [])
            if not data_list:
                return {"error": "No data available"}
            result = []
            for item in data_list:
                if len(item) >= 5:
                    result.append({
                        "timestamp": item[0],
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]) if len(item) > 5 else 0
                    })
            return {"data": result}
        except Exception as e:
            return {"error": f"Parse error: {e}"}


def normalize_stock_code_to_yahoo(user_input: str) -> str:
    """将用户输入转换为Yahoo Finance需要的格式"""
    if not user_input:
        return ""
    user_input = user_input.strip()
    if user_input.endswith((".SS", ".SZ", ".NY", ".OB")):
        return user_input
    code = re.findall(r"\d{6}", user_input)
    if code:
        code = code[0]
        if code.startswith(("6", "9")):
            return f"{code}.SS"
        else:
            return f"{code}.SZ"
    return user_input


class YahooFinanceHTTPClient:
    """Yahoo Finance数据源HTTP客户端"""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, use_cache: bool = True):
        self.session = requests.Session()
        self._use_cache = use_cache and CACHE_ENABLED
        self._cache = get_mcp_cache() if self._use_cache else None

    def _get_cached(self, tool_name: str, params: Dict, fallback_func) -> Dict:
        if self._use_cache and self._cache:
            cached = self._cache.get(tool_name, params)
            if cached is not None:
                return cached
        result = fallback_func()
        if self._use_cache and self._cache and "error" not in result:
            self._cache.set(tool_name, params, result)
        return result

    def _parse_period_to_range(self, period: str) -> str:
        """将period转换为Yahoo Finance的range参数"""
        if period.endswith("d"):
            days = int(period[:-1])
            if days <= 5:
                return "5d"
            elif days <= 30:
                return "1mo"
            elif days <= 90:
                return "3mo"
            elif days <= 180:
                return "6mo"
            elif days <= 365:
                return "1y"
            else:
                return "2y"
        elif period.endswith("w"):
            return "1mo"
        elif period.endswith("m"):
            months = int(period[:-1])
            if months <= 1:
                return "1mo"
            elif months <= 3:
                return "3mo"
            elif months <= 6:
                return "6mo"
            elif months <= 12:
                return "1y"
            else:
                return "2y"
        return "1mo"

    def get_kline_data(self, symbol: str, period: str = "30d", interval: str = "1d") -> Dict:
        """获取K线数据"""
        params = {"symbol": symbol, "period": period}
        yahoo_symbol = normalize_stock_code_to_yahoo(symbol)
        range_param = self._parse_period_to_range(period)

        def _fetch():
            url = f"{self.BASE_URL}/{yahoo_symbol}"
            try:
                response = self.session.get(
                    url,
                    params={"interval": "1d", "range": range_param},
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_yahoo_response(data)
            except Exception as e:
                return {"error": str(e)}

        return self._get_cached("yahoo_kline_data", params, _fetch)

    def _parse_yahoo_response(self, data: Dict) -> Dict:
        """解析Yahoo Finance K线数据响应"""
        try:
            result = data.get("chart", {}).get("result", [])
            if not result:
                return {"error": "No data available"}
            item = result[0]
            timestamps = item.get("timestamp", [])
            quote = item.get("indicators", {}).get("quote", [{}])[0]
            if not timestamps:
                return {"error": "No timestamp data"}
            result_data = []
            for i, ts in enumerate(timestamps):
                result_data.append({
                    "timestamp": str(ts),
                    "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "",
                    "open": quote.get("open", [0])[i] if quote.get("open") else 0,
                    "high": quote.get("high", [0])[i] if quote.get("high") else 0,
                    "low": quote.get("low", [0])[i] if quote.get("low") else 0,
                    "close": quote.get("close", [0])[i] if quote.get("close") else 0,
                    "volume": quote.get("volume", [0])[i] if quote.get("volume") else 0,
                })
            return {"data": result_data}
        except Exception as e:
            return {"error": f"Parse error: {e}"}

    def get_company_info(self, symbol: str) -> Dict:
        """获取公司基本信息 - 使用 Yahoo Finance chart API"""
        params = {"symbol": symbol}
        yahoo_symbol = normalize_stock_code_to_yahoo(symbol)

        def _fetch():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
                response = self.session.get(
                    url,
                    params={"interval": "1d", "range": "1d"},
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_company_info_from_chart(data)
            except Exception as e:
                return {"error": str(e)}

        return self._get_cached("yahoo_company_info", params, _fetch)

    def _parse_company_info_from_chart(self, data: Dict) -> Dict:
        """从 Yahoo Finance chart API 解析公司基本信息"""
        try:
            result = data.get("chart", {}).get("result", [])
            if not result:
                return {"error": "No data available"}
            item = result[0]
            meta = item.get("meta", {})
            return {
                "name": meta.get("longName", "") or meta.get("shortName", "") or "",
                "industry": "",
                "sector": "",
                "market_cap": 0,
                "currency": meta.get("currency", "USD"),
                "price": meta.get("regularMarketPrice", 0) or 0,
                "exchange": meta.get("exchangeName", ""),
                "list_date": "",
                "summary": "",
                "pe_ratio": 0,
                "ebitda": 0,
                "week52_high": meta.get("fiftyTwoWeekHigh", 0) or 0,
                "week52_low": meta.get("fiftyTwoWeekLow", 0) or 0,
            }
        except Exception as e:
            return {"error": f"Parse error: {e}"}

    def get_stock_news(self, symbol: str, limit: int = 10) -> Dict:
        """获取股票最新资讯"""
        params = {"symbol": symbol, "limit": limit}
        yahoo_symbol = normalize_stock_code_to_yahoo(symbol)

        def _fetch():
            try:
                url = f"https://query2.finance.yahoo.com/v1/finance/news"
                response = self.session.get(
                    url,
                    params={"symbols": yahoo_symbol, "news": limit},
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_news(data)
            except Exception as e:
                return {"error": str(e)}

        return self._get_cached("yahoo_stock_news", params, _fetch)

    def _parse_news(self, data: Dict) -> Dict:
        """解析股票资讯"""
        try:
            news_list = data.get("news", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            if not news_list:
                return {"news": []}
            result = []
            for item in news_list[:limit]:
                result.append({
                    "title": item.get("title", ""),
                    "pub_date": item.get("pubDate", ""),
                    "source": item.get("publisher", ""),
                    "url": item.get("link", item.get("url", "")),
                    "content": item.get("description", item.get("summary", "")),
                })
            return {"news": result}
        except Exception as e:
            return {"error": f"Parse error: {e}"}

    def get_company_info_alpha(self, symbol: str) -> Dict:
        """使用 Alpha Vantage 获取公司基本信息"""
        ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "XAH6LSH8ZZHDFONF")
        params = {"symbol": symbol}

        def _fetch():
            try:
                url = "https://www.alphavantage.co/query"
                response = self.session.get(
                    url,
                    params={"function": "OVERVIEW", "symbol": symbol, "apikey": ALPHA_VANTAGE_KEY},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_alpha_company_info(data)
            except Exception as e:
                return {"error": str(e)}

        return self._get_cached("alpha_company_info", params, _fetch)

    def _parse_alpha_company_info(self, data: Dict) -> Dict:
        """解析 Alpha Vantage 公司信息"""
        try:
            if not data.get("Symbol"):
                return {"error": "No data available"}
            return {
                "name": data.get("Name", ""),
                "industry": data.get("Industry", ""),
                "sector": data.get("Sector", ""),
                "market_cap": int(data.get("MarketCapitalization", 0)) if data.get("MarketCapitalization") else 0,
                "currency": data.get("Currency", "USD"),
                "price": float(data.get("AnalystTargetPrice", 0)) if data.get("AnalystTargetPrice") else 0,
                "exchange": data.get("Exchange", ""),
                "list_date": data.get(" IPODate", ""),
                "summary": data.get("Description", ""),
                "pe_ratio": float(data.get("PERatio", 0)) if data.get("PERatio") else 0,
                "ebitda": int(data.get("EBITDA", 0)) if data.get("EBITDA") else 0,
            }
        except Exception as e:
            return {"error": f"Parse error: {e}"}

    def get_stock_news_alpha(self, symbol: str, limit: int = 10) -> Dict:
        """使用 Alpha Vantage 获取股票新闻"""
        ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "XAH6LSH8ZZHDFONF")
        params = {"symbol": symbol, "limit": limit}

        def _fetch():
            try:
                url = "https://www.alphavantage.co/query"
                response = self.session.get(
                    url,
                    params={"function": "NEWS_SENTIMENT", "tickers": symbol, "apikey": ALPHA_VANTAGE_KEY, "limit": limit},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_alpha_news(data, limit)
            except Exception as e:
                return {"error": str(e)}

        return self._get_cached("alpha_stock_news", params, _fetch)

    def _parse_alpha_news(self, data: Dict, limit: int) -> Dict:
        """解析 Alpha Vantage 新闻"""
        try:
            feed = data.get("feed", [])
            if not feed:
                return {"news": []}
            result = []
            for item in feed[:limit]:
                result.append({
                    "title": item.get("title", ""),
                    "pub_date": item.get("time_published", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "content": item.get("summary", ""),
                })
            return {"news": result}
        except Exception as e:
            return {"error": f"Parse error: {e}"}
