import requests
import re
from typing import Dict, Any, List, Optional


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
    """直接通过HTTP API调用stock-mcp服务器"""

    BASE_URL = "http://127.0.0.1:9898/api/v1"

    def __init__(self, base_url: str = None):
        self.BASE_URL = base_url or "http://127.0.0.1:9898/api/v1"
        self.session = requests.Session()

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET请求"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}", params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _post(self, endpoint: str, data: Dict = None) -> Dict:
        """POST请求"""
        try:
            response = self.session.post(
                f"{self.BASE_URL}{endpoint}", json=data, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    # ========== market (3个工具) ==========
    def get_kline_data(
        self, symbol: str, period: str = "30d", interval: str = "1d"
    ) -> Dict:
        """获取K线数据"""
        return self._post(
            "/market/prices/history",
            {
                "symbol": normalize_stock_code(symbol),
                "period": period,
                "interval": interval,
            },
        )

    def get_real_time_price(self, tickers: List[str]) -> Dict:
        """批量获取实时价格"""
        normalized_tickers = [normalize_stock_code(t) for t in tickers]
        return self._post("/market/prices/batch", {"tickers": normalized_tickers})

    def get_asset_info(self, symbol: str) -> Dict:
        """获取资产信息"""
        return self._get("/market/asset/info", {"symbol": normalize_stock_code(symbol)})

    # ========== technical (3个工具) ==========
    def get_technical_indicators(
        self, symbol: str, period: str = "30d", interval: str = "1d"
    ) -> Dict:
        """计算技术指标"""
        return self._post(
            "/technical/indicators/calculate",
            {
                "symbol": normalize_stock_code(symbol),
                "period": period,
                "interval": interval,
            },
        )

    def generate_trading_signal(
        self, symbol: str, period: str = "30d", interval: str = "1d"
    ) -> Dict:
        """生成交易信号"""
        return self._post(
            "/technical/signals/trading",
            {
                "symbol": normalize_stock_code(symbol),
                "period": period,
                "interval": interval,
            },
        )

    def calculate_support_resistance(self, symbol: str, period: str = "90d") -> Dict:
        """计算支撑阻力位"""
        return self._post(
            "/technical/analysis/support-resistance",
            {"symbol": normalize_stock_code(symbol), "period": period},
        )

    # ========== fundamental (3个工具) ==========
    def get_financial_reports(self, symbol: str) -> Dict:
        """获取财务报告"""
        return self._get(
            "/fundamental/report", {"symbol": normalize_stock_code(symbol)}
        )

    def get_valuation_metrics(self, symbol: str) -> Dict:
        """获取估值指标"""
        return self._get(
            "/fundamental/ratios", {"symbol": normalize_stock_code(symbol)}
        )

    def get_us_valuation_metrics(self, symbol: str) -> Dict:
        """获取美股估值指标"""
        return self._get("/fundamental/ratios", {"symbol": symbol})

    # ========== money_flow (3个工具) ==========
    def get_money_flow(self, symbol: str, days: int = 20) -> Dict:
        """获取资金流向"""
        return self._get(
            f"/money-flow/stock/{normalize_stock_code(symbol)}", {"days": days}
        )

    def get_north_bound_flow(self, days: int = 30) -> Dict:
        """获取北向资金"""
        return self._get("/money-flow/north-bound", {"days": days})

    def get_chip_distribution(self, symbol: str) -> Dict:
        """获取筹码分布"""
        return self._get(
            f"/money-flow/chip-distribution/{normalize_stock_code(symbol)}"
        )

    # ========== news (3个工具) ==========
    def get_stock_news(
        self, symbol: str, days_back: int = 7, limit: int = 10
    ) -> Dict:
        """获取股票新闻"""
        return self._get(
            "/news/stock",
            {
                "symbol": normalize_stock_code(symbol),
                "days_back": days_back,
                "limit": limit,
            },
        )

    def get_latest_news(self, query: str, days_back: int = 7, limit: int = 10) -> Dict:
        """获取最新新闻"""
        return self._get(
            "/news/search", {"query": query, "days_back": days_back, "limit": limit}
        )

    def get_us_news_sentiment(self, symbol: str, days_back: int = 3) -> Dict:
        """获取美股新闻情绪"""
        return self._get(
            "/news/sentiment/us", {"symbol": symbol, "days_back": days_back}
        )

    # ========== filings (5个工具) ==========
    def get_sec_periodic_filings(
        self, ticker: str, year: int = 2024, limit: int = 10
    ) -> Dict:
        """获取SEC定期披露"""
        return self._get(
            "/filings/sec/periodic", {"ticker": ticker, "year": year, "limit": limit}
        )

    def get_sec_event_filings(self, ticker: str, limit: int = 10) -> Dict:
        """获取SEC事件披露"""
        return self._get("/filings/sec/event", {"ticker": ticker, "limit": limit})

    def get_ashare_filings(self, symbol: str, limit: int = 10) -> Dict:
        """获取A股公告"""
        return self._get("/filings/ashare", {"symbol": symbol, "limit": limit})

    def get_filings_markdown(self, ticker: str, doc_id: str) -> Dict:
        """获取公告markdown"""
        return self._get("/filings/markdown", {"ticker": ticker, "doc_id": doc_id})

    def get_filings_chunks(self, ticker: str, doc_id: str) -> Dict:
        """获取公告chunk"""
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
