"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Api } from "@/lib/api";

type CandlestickData = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

type VolumeData = {
  time: string;
  value: number;
  color: string;
};

type Indicator = {
  rsi?: number[];
  macd?: { value: number[]; signal: number[]; histogram: number[] };
  ma5?: number[];
  ma10?: number[];
  ma20?: number[];
  ma30?: number[];
};

interface Props {
  data: any[];
  indicators?: Indicator | null;
  stockCode?: string;
}

export default function PriceChart({ data, indicators, stockCode }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const ma5SeriesRef = useRef<any>(null);
  const ma10SeriesRef = useRef<any>(null);
  const ma20SeriesRef = useRef<any>(null);
  const [realTimePrice, setRealTimePrice] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isChartReady, setIsChartReady] = useState(false);
  const [hasDataBeenSet, setHasDataBeenSet] = useState(false);

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
    const interval = setInterval(loadPrice, 30000);
    return () => clearInterval(interval);
  }, [stockCode]);

  // 初始化图表函数
  const initChart = useCallback(async () => {
    if (!chartContainerRef.current) {
      console.log('[PriceChart] 图表容器未就绪');
      return;
    }

    if (chartRef.current) {
      console.log('[PriceChart] 图表已存在，跳过初始化');
      return;
    }

    try {
      console.log('[PriceChart] 开始初始化图表');
      const { createChart, ColorType, CrosshairMode, LineStyle } = await import("lightweight-charts");

      const chart = createChart(chartContainerRef.current!, {
        layout: {
          background: { type: ColorType.Solid, color: "#ffffff" },
          textColor: "#666666",
        },
        grid: {
          vertLines: { color: "#f0f0f0" },
          horzLines: { color: "#f0f0f0" },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: {
            width: 1,
            color: "#999999",
            style: LineStyle.Dashed,
            labelBackgroundColor: "#4B5563",
          },
          horzLine: {
            width: 1,
            color: "#999999",
            style: LineStyle.Dashed,
            labelBackgroundColor: "#4B5563",
          },
        },
        rightPriceScale: {
          borderColor: "#E5E5E5",
        },
        timeScale: {
          borderColor: "#E5E5E5",
          timeVisible: true,
          secondsVisible: false,
        },
        handleScroll: { vertTouchDrag: false },
      });

      chartRef.current = chart;
      console.log('[PriceChart] 图表对象创建成功');

      // K线系列
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: "#EF4444",
        downColor: "#22C55E",
        borderDownColor: "#22C55E",
        borderUpColor: "#EF4444",
        wickDownColor: "#22C55E",
        wickUpColor: "#EF4444",
      });
      candlestickSeriesRef.current = candlestickSeries;
      console.log('[PriceChart] K线系列创建成功');

      // 成交量系列
      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volumeSeriesRef.current = volumeSeries;

      // 均线系列
      const ma5Series = chart.addLineSeries({
        color: "#F59E0B",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ma5SeriesRef.current = ma5Series;

      const ma10Series = chart.addLineSeries({
        color: "#3B82F6",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ma10SeriesRef.current = ma10Series;

      const ma20Series = chart.addLineSeries({
        color: "#8B5CF6",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ma20SeriesRef.current = ma20Series;

      // 响应式
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
          });
        }
      };

      window.addEventListener("resize", handleResize);
      handleResize();

      setIsChartReady(true);
      console.log('[PriceChart] 图表初始化完成');

      return () => {
        window.removeEventListener("resize", handleResize);
      };
    } catch (error) {
      console.error('[PriceChart] 图表初始化失败:', error);
    }
  }, []);

  // 初始化图表 - 监听容器就绪
  useEffect(() => {
    const container = chartContainerRef.current;
    if (container && !chartRef.current) {
      console.log('[PriceChart] 检测到容器，开始初始化');
      initChart();
    }
  }, [initChart]);

  // 清理图表
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        console.log('[PriceChart] 清理图表');
        chartRef.current.remove();
        chartRef.current = null;
        candlestickSeriesRef.current = null;
        volumeSeriesRef.current = null;
        ma5SeriesRef.current = null;
        ma10SeriesRef.current = null;
        ma20SeriesRef.current = null;
        setIsChartReady(false);
        setHasDataBeenSet(false);
      }
    };
  }, []);

  // 更新图表数据
  useEffect(() => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      console.log('[PriceChart] 无数据或数据不是数组:', data);
      return;
    }

    console.log('[PriceChart] 原始数据:', data.slice(0, 2));

    // 等待图表初始化完成
    const waitAndSetData = () => {
      if (!chartRef.current || !candlestickSeriesRef.current) {
        console.log('[PriceChart] 等待图表初始化完成...当前状态:', {
          chartExists: !!chartRef.current,
          candlestickExists: !!candlestickSeriesRef.current,
          volumeExists: !!volumeSeriesRef.current
        });

        // 如果图表还未初始化，先初始化
        if (!chartRef.current && chartContainerRef.current) {
          console.log('[PriceChart] 触发图表初始化...');
          initChart();
        }

        setTimeout(waitAndSetData, 100);
        return;
      }

      console.log('[PriceChart] 图表系列已就绪，开始设置数据');

      // 转换数据格式
      const candlestickData: CandlestickData[] = data.map((item: any) => {
        let timeStr = item.timestamp || item.time;
        if (typeof timeStr === "number" || /^\d+$/.test(String(timeStr))) {
          const date = new Date(parseInt(String(timeStr)) * 1000);
          timeStr = date.toISOString().split("T")[0];
        } else if (timeStr && timeStr.includes("T")) {
          timeStr = timeStr.split("T")[0];
        }
        return {
          time: timeStr,
          open: parseFloat(item.open ?? item.open_price ?? item.price ?? 0),
          high: parseFloat(item.high ?? item.high_price ?? item.price ?? 0),
          low: parseFloat(item.low ?? item.low_price ?? item.price ?? 0),
          close: parseFloat(item.close ?? item.close_price ?? item.price ?? 0),
        };
      });

      // 成交量数据
      const volumeData: VolumeData[] = data.map((item: any, index: number) => {
        const close = parseFloat(item.close ?? item.close_price ?? item.price ?? 0);
        const open = parseFloat(item.open ?? item.open_price ?? item.price ?? 0);
        const isUp = close >= open;
        return {
          time: candlestickData[index].time,
          value: parseFloat(item.volume ?? 0),
          color: isUp ? "rgba(34, 197, 94, 0.5)" : "rgba(239, 68, 68, 0.5)",
        };
      });

      console.log('[PriceChart] 图表系列状态:', {
        chartExists: !!chartRef.current,
        candlestickSeriesExists: !!candlestickSeriesRef.current,
        volumeSeriesExists: !!volumeSeriesRef.current
      });

      // 更新K线
      if (candlestickSeriesRef.current) {
        try {
          candlestickSeriesRef.current.setData(candlestickData);
          console.log('[PriceChart] K线数据已设置，共', candlestickData.length, '条');
        } catch (e) {
          console.error('[PriceChart] 设置K线数据失败:', e);
        }
      }

      // 更新成交量
      if (volumeSeriesRef.current) {
        try {
          volumeSeriesRef.current.setData(volumeData);
          console.log('[PriceChart] 成交量数据已设置');
        } catch (e) {
          console.error('[PriceChart] 设置成交量数据失败:', e);
        }
      }

      // 更新均线
      if (indicators && chartRef.current) {
        if (ma5SeriesRef.current && indicators.ma5) {
          const ma5Data = indicators.ma5.map((value, index) => ({
            time: candlestickData[index]?.time,
            value: value,
          })).filter(item => item.value != null);
          ma5SeriesRef.current.setData(ma5Data);
        }

        if (ma10SeriesRef.current && indicators.ma10) {
          const ma10Data = indicators.ma10.map((value, index) => ({
            time: candlestickData[index]?.time,
            value: value,
          })).filter(item => item.value != null);
          ma10SeriesRef.current.setData(ma10Data);
        }

        if (ma20SeriesRef.current && indicators.ma20) {
          const ma20Data = indicators.ma20.map((value, index) => ({
            time: candlestickData[index]?.time,
            value: value,
          })).filter(item => item.value != null);
          ma20SeriesRef.current.setData(ma20Data);
        }

        chartRef.current.timeScale().fitContent();
      }

      setHasDataBeenSet(true);
    };

    waitAndSetData();
  }, [data, indicators, initChart]);

  // 计算涨跌
  const latestCandle = data[data.length - 1];
  const prevCandle = data[data.length - 2];
  const latestPrice = realTimePrice?.price ?? latestCandle?.close ?? latestCandle?.close_price ?? latestCandle?.price ?? 0;
  const prevPrice = prevCandle?.close ?? prevCandle?.close_price ?? prevCandle?.price ?? latestCandle?.open ?? latestCandle?.open_price ?? latestPrice;
  const priceChange = latestPrice - prevPrice;
  const priceChangePercent = prevPrice ? (priceChange / prevPrice * 100) : 0;
  const isUp = priceChange >= 0;

  const latestRSI = indicators?.rsi?.[indicators.rsi.length - 1];
  const latestMACD = indicators?.macd?.value?.[indicators.macd.value.length - 1];

  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className="card">
        <div className="h-[400px] flex items-center justify-center text-gray-400">
          <div className="text-center">
            <div className="text-4xl mb-2">📊</div>
            <div>暂无K线数据，请输入股票代码查看</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      {/* 标题栏 */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          {stockCode ? (stockCode.startsWith("SSE:") ? stockCode : `SSE:${stockCode}`) : ""} K线走势
        </h3>
        <div className="flex items-center gap-4">
          {loading && <span className="text-xs text-gray-500">刷新中...</span>}

          {/* 价格显示 */}
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">¥{latestPrice.toFixed(2)}</div>
            <div className={`text-sm font-medium ${isUp ? "text-red-500" : "text-green-500"}`}>
              {isUp ? "+" : ""}{priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
            </div>
          </div>

          {/* 技术指标 */}
          {latestRSI && (
            <div className="text-right px-3 py-1 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">RSI(14)</div>
              <div className={`text-sm font-medium ${
                latestRSI > 70 ? "text-red-500" : latestRSI < 30 ? "text-green-500" : "text-gray-700"
              }`}>
                {latestRSI.toFixed(1)}
              </div>
            </div>
          )}

          {/* 成交量 */}
          {realTimePrice?.volume && (
            <div className="text-right px-3 py-1 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">成交量</div>
              <div className="text-sm text-gray-700">
                {(realTimePrice.volume / 10000).toFixed(1)}万
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 图表容器 */}
      <div className="h-[350px]" ref={chartContainerRef} />

      {/* 图例 */}
      <div className="mt-4 flex justify-center gap-6 text-xs">
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-sm bg-red-500"></span>
          <span className="text-gray-600">阳线（上涨）</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-sm bg-green-500"></span>
          <span className="text-gray-600">阴线（下跌）</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-2 w-4 rounded-sm bg-amber-500"></span>
          <span className="text-gray-600">MA5</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-2 w-4 rounded-sm bg-blue-500"></span>
          <span className="text-gray-600">MA10</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-2 w-4 rounded-sm bg-violet-500"></span>
          <span className="text-gray-600">MA20</span>
        </div>
      </div>
    </div>
  );
}