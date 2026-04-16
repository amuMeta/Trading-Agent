"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, ComposedChart, Line, Bar, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Api } from "@/lib/api";

type Point = { time: string; price: number; volume?: number; open?: number; high?: number; low?: number };

type Indicator = {
  rsi?: number[];
  macd?: { value: number[]; signal: number[]; histogram: number[] };
  ma5?: number[];
  ma10?: number[];
  ma20?: number[];
};

type RealTimePrice = {
  ticker: string;
  price: number;
  change?: number;
  change_percent?: number;
  volume?: number;
  timestamp?: string;
};

interface Props {
  data: Point[];
  indicators?: Indicator | null;
  stockCode?: string;
}

export default function PriceChart({ data, indicators, stockCode }: Props) {
  const [realTimePrice, setRealTimePrice] = useState<RealTimePrice | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载实时价格
  useEffect(() => {
    if (!stockCode) return;
    
    const loadPrice = async () => {
      try {
        setLoading(true);
        const res = await Api.getStockPrice(stockCode);
        if (res?.price?.[0]) {
          setRealTimePrice(res.price[0]);
        }
      } catch (e) {
        console.error("加载实时价格失败:", e);
      } finally {
        setLoading(false);
      }
    };

    loadPrice();
    
    // 每30秒刷新一次
    const interval = setInterval(loadPrice, 30000);
    return () => clearInterval(interval);
  }, [stockCode]);

  if (!data.length) {
    return (
      <div className="card h-80 flex items-center justify-center text-gray-400">
        暂无K线数据，请输入股票代码进行查询
      </div>
    );
  }

  const latestPrice = data[data.length - 1]?.price || 0;
  const priceChange = data.length >= 2 ? latestPrice - data[data.length - 2].price : 0;
  const priceChangePercent = data.length >= 2 && data[data.length - 2].price ? (priceChange / data[data.length - 2].price * 100) : 0;

  // 实时价格优先显示
  const displayPrice = realTimePrice?.price ?? latestPrice;
  const displayChange = realTimePrice?.change ?? priceChange;
  const displayChangePercent = realTimePrice?.change_percent ?? priceChangePercent;
  const isUp = displayChange >= 0;

  return (
    <div className="card">
      {/* 实时价格头部 */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">价格走势</h3>
        <div className="flex items-center gap-4">
          {loading && <span className="text-xs text-gray-500">刷新中...</span>}
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">¥{displayPrice.toFixed(2)}</div>
            <div className={`text-sm font-medium ${isUp ? "text-green-600" : "text-red-600"}`}>
              {isUp ? "+" : ""}{displayChange?.toFixed(2)} ({displayChangePercent?.toFixed(2)}%)
            </div>
          </div>
          {indicators?.rsi && (
            <div className="text-right">
              <div className="text-xs text-gray-500">RSI(14)</div>
              <div className={`text-sm font-medium ${
                indicators.rsi[indicators.rsi.length - 1] > 70 ? "text-red-600" :
                indicators.rsi[indicators.rsi.length - 1] < 30 ? "text-green-600" : "text-gray-700"
              }`}>
                {indicators.rsi[indicators.rsi.length - 1]?.toFixed(1)}
              </div>
            </div>
          )}
          {realTimePrice?.volume && (
            <div className="text-right">
              <div className="text-xs text-gray-500">成交量</div>
              <div className="text-sm text-gray-700">{(realTimePrice.volume / 10000).toFixed(1)}万</div>
            </div>
          )}
        </div>
      </div>
      
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data.map((item, idx) => ({
            ...item,
            ma5: indicators?.ma5?.[idx] ?? null,
            ma10: indicators?.ma10?.[idx] ?? null,
            ma20: indicators?.ma20?.[idx] ?? null,
          }))}>
            <CartesianGrid stroke="#f0f0f0" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="#999999" fontSize={11} interval="preserveStartEnd" />
            <YAxis yAxisId="price" stroke="#999999" fontSize={11} domain={["auto", "auto"]} />
            <YAxis yAxisId="volume" orientation="right" stroke="#999999" fontSize={11} domain={[0, "auto"]} />
            <Tooltip
              contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e5e7', borderRadius: '8px' }}
              labelStyle={{ color: '#666666' }}
            />
            {indicators?.ma5 && <Line yAxisId="price" type="monotone" dataKey="ma5" stroke="#f59e0b" dot={false} strokeWidth={1} strokeDasharray="3 3" />}
            {indicators?.ma10 && <Line yAxisId="price" type="monotone" dataKey="ma10" stroke="#3b82f6" dot={false} strokeWidth={1} />}
            {indicators?.ma20 && <Line yAxisId="price" type="monotone" dataKey="ma20" stroke="#8b5cf6" dot={false} strokeWidth={1} />}
            <Line yAxisId="price" type="monotone" dataKey="price" stroke="#34C759" dot={false} strokeWidth={2} />
            <Bar yAxisId="volume" dataKey="volume" fill="#e5e5e7" opacity={0.5} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex justify-center gap-4 text-xs">
        {indicators?.ma5 && <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500"></span>MA5</span>}
        {indicators?.ma10 && <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-500"></span>MA10</span>}
        {indicators?.ma20 && <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-violet-500"></span>MA20</span>}
      </div>
    </div>
  );
}