"use client";

import { useEffect, useState } from "react";
import { Api } from "@/lib/api";

type NewsItem = {
  title?: string;
  pub_date?: string;
  source?: string;
  url?: string;
  content?: string;
};

type StockInfo = {
  name?: string;
  industry?: string;
  sector?: string;
  market_cap?: number;
  currency?: string;
  price?: number;
  exchange?: string;
  list_date?: string;
  summary?: string;
  pe_ratio?: number;
  ebitda?: number;
  week52_high?: number;
  week52_low?: number;
};

interface Props {
  stockCode: string;
}

export default function StockDataPanel({ stockCode }: Props) {
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<"info" | "news">("info");

  useEffect(() => {
    if (!stockCode) return;

    const loadData = async () => {
      setLoading(true);
      try {
        const [infoRes, newsRes] = await Promise.all([
          Api.getStockInfoYahoo(stockCode),
          Api.getStockNewsYahoo(stockCode, 5)
        ]);

        if (infoRes?.info) setStockInfo(infoRes.info);
        if (newsRes?.news) setNews(newsRes.news);
      } catch (e) {
        console.error("加载数据失败:", e);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [stockCode]);

  const tabs = [
    { key: "info", label: "公司概况", icon: "🏢" },
    { key: "news", label: "最新资讯", icon: "📰" }
  ] as const;

  const formatMarketCap = (marketCap: number, currency: string) => {
    if (!marketCap) return "-";
    if (marketCap >= 100000000000) {
      return (marketCap / 100000000000).toFixed(2) + "万亿" + (currency || "");
    } else if (marketCap >= 100000000) {
      return (marketCap / 100000000).toFixed(2) + "亿" + (currency || "");
    }
    return marketCap.toLocaleString() + (currency || "");
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
      <div className="flex border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSelectedTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
              selectedTab === tab.key
                ? "bg-white text-blue-500 border-b-2 border-blue-500"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500 mr-2"></span>
            加载中...
          </div>
        ) : (
          <>
            {selectedTab === "info" && (
              <div className="space-y-4">
                {stockInfo ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-semibold text-gray-900">
                        {stockInfo.name || stockCode}
                      </span>
                      <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                        {stockInfo.exchange || "NYSE"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">所属行业</span>
                        <div className="mt-1 text-gray-900 font-medium">{stockInfo.industry || stockInfo.sector || "-"}</div>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">总市值</span>
                        <div className="mt-1 text-gray-900 font-medium">
                          {formatMarketCap(stockInfo.market_cap || 0, stockInfo.currency || "USD")}
                        </div>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">当前价</span>
                        <div className="mt-1 text-gray-900 font-medium">
                          {stockInfo.price ? stockInfo.currency + " " + stockInfo.price : "-"}
                        </div>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">市盈率(PE)</span>
                        <div className="mt-1 text-gray-900 font-medium">
                          {stockInfo.pe_ratio ? stockInfo.pe_ratio.toFixed(2) : "-"}
                        </div>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">52周最高</span>
                        <div className="mt-1 text-gray-900 font-medium">
                          {stockInfo.week52_high ? stockInfo.currency + " " + stockInfo.week52_high : "-"}
                        </div>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">52周最低</span>
                        <div className="mt-1 text-gray-900 font-medium">
                          {stockInfo.week52_low ? stockInfo.currency + " " + stockInfo.week52_low : "-"}
                        </div>
                      </div>
                    </div>
                    {stockInfo.summary && (
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500 font-medium">公司简介</span>
                        <div className="mt-2 text-sm text-gray-700 line-clamp-3">
                          {stockInfo.summary}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    暂无公司信息
                  </div>
                )}
              </div>
            )}

            {selectedTab === "news" && (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {news.length > 0 ? (
                  news.map((item, idx) => (
                    <a
                      key={idx}
                      href={item.url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block rounded-lg border border-gray-200 p-4 hover:border-gray-300 hover:shadow-md transition-all"
                    >
                      <div className="text-sm text-gray-900 font-medium line-clamp-2">
                        {item.title || "无标题"}
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                        <span>{item.source || "-"}</span>
                        <span>•</span>
                        <span>{item.pub_date?.slice(0, 10) || "-"}</span>
                      </div>
                    </a>
                  ))
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    暂无新闻资讯
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}