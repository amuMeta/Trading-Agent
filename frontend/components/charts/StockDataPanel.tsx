"use client";

import { useEffect, useState } from "react";
import { Api } from "@/lib/api";

type MoneyFlowData = {
  date?: string;
  main_inflow?: number;
  main_outflow?: number;
  super_inflow?: number;
  super_outflow?: number;
  retail_inflow?: number;
  retail_outflow?: number;
};

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
  market?: string;
  list_date?: string;
  summary?: string;
};

interface Props {
  stockCode: string;
}

export default function StockDataPanel({ stockCode }: Props) {
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [moneyFlow, setMoneyFlow] = useState<MoneyFlowData[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<"info" | "flow" | "news">("info");

  useEffect(() => {
    if (!stockCode) return;

    const loadData = async () => {
      setLoading(true);
      try {
        const [infoRes, flowRes, newsRes] = await Promise.all([
          Api.getStockInfo(stockCode),
          Api.getMoneyFlow(stockCode, 10),
          Api.getStockNews(stockCode, 5)
        ]);

        if (infoRes?.info) setStockInfo(infoRes.info);
        if (flowRes?.data) setMoneyFlow(flowRes.data);
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
    { key: "flow", label: "资金流向", icon: "💰" },
    { key: "news", label: "最新资讯", icon: "📰" }
  ] as const;

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
      {/* 标签页导航 */}
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

      {/* 内容区域 */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500 mr-2"></span>
            加载中...
          </div>
        ) : (
          <>
            {/* 公司概况 */}
            {selectedTab === "info" && (
              <div className="space-y-4">
                {stockInfo ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-semibold text-gray-900">
                        {stockInfo.name || stockCode}
                      </span>
                      <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                        {stockInfo.market || "A股"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">所属行业</span>
                        <div className="mt-1 text-gray-900 font-medium">{stockInfo.industry || "-"}</div>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-4">
                        <span className="text-sm text-gray-500">上市日期</span>
                        <div className="mt-1 text-gray-900 font-medium">{stockInfo.list_date || "-"}</div>
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

            {/* 资金流向 */}
            {selectedTab === "flow" && (
              <div className="space-y-4">
                {moneyFlow.length > 0 ? (
                  <>
                    {/* 最近5天汇总 */}
                    <div className="grid grid-cols-3 gap-3">
                      {moneyFlow.slice(0, 5).map((item, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg bg-gray-50 p-3 text-center"
                        >
                          <div className="text-xs text-gray-500">{item.date?.slice(5) || "-"}</div>
                          <div
                            className={`text-sm font-bold mt-1 ${
                              (item.main_inflow || 0) >= 0
                                ? "text-green-600"
                                : "text-red-600"
                            }`}
                          >
                            {(item.main_inflow || 0) > 0 ? "+" : ""}
                            {((item.main_inflow || 0) / 10000).toFixed(1)}万
                          </div>
                        </div>
                      ))}
                    </div>
                    {/* 平均流入 */}
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <span className="text-sm font-medium text-gray-700">10日主力净流入</span>
                      <span
                        className={`text-xl font-bold ${
                          moneyFlow.reduce(
                            (sum, item) => sum + (item.main_inflow || 0),
                            0
                          ) >= 0
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {(
                          moneyFlow.reduce(
                            (sum, item) => sum + (item.main_inflow || 0),
                            0
                          ) / 10000
                        ).toFixed(1)}
                        万
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    暂无资金流向数据
                  </div>
                )}
              </div>
            )}

            {/* 新闻资讯 */}
            {selectedTab === "news" && (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {news.length > 0 ? (
                  news.map((item, idx) => (
                    <a
                      key={idx}
                      href={item.url || "#"}
                      target="_blank"
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