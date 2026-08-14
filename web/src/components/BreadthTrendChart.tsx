import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { api } from "../api/client";
import type { BreadthHistoryPoint } from "../types";

const LOOKBACK_DAYS = 180;
// 分界线：15% 超卖（绿）/ 50% 长期多空分界（灰）/ 85% 超买（红）
const DIVIDING_LINES: { y: number; label: string; color: string }[] = [
  { y: 85, label: "85 超买", color: "#dc2626" },
  { y: 50, label: "50 多空分界", color: "#6b7280" },
  { y: 15, label: "15 超卖", color: "#16a34a" },
];

export default function BreadthTrendChart({
  marketId,
  displayName,
}: {
  marketId: string;
  displayName: string;
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["breadthHistory", marketId, LOOKBACK_DAYS],
    queryFn: () => api.marketContextBreadthHistory(marketId, LOOKBACK_DAYS),
    staleTime: 60_000,
  });

  const points: BreadthHistoryPoint[] = data?.history ?? [];

  useEffect(() => {
    if (!chartRef.current) return;
    const inst = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instRef.current = inst;
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(chartRef.current);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!instRef.current) return;
    instRef.current.setOption(buildTrendOption(points), true);
  }, [points]);

  return (
    <div className="breadth-trend-card">
      <div className="breadth-trend-title">
        {displayName} 宽度趋势（近 {LOOKBACK_DAYS} 交易日）
      </div>
      {isLoading && <div className="loading">加载历史…</div>}
      {isError && <div className="fund-errors">趋势数据加载失败</div>}
      {!isLoading && !isError && points.length < 2 && (
        <div className="muted">暂无历史（首次写入后才有序列）</div>
      )}
      <div ref={chartRef} className="macro-chart" style={{ height: 240 }} />
    </div>
  );
}

function buildTrendOption(
  points: BreadthHistoryPoint[],
): echarts.EChartsOption {
  const dates = points.map((p) => p.date);
  const b20 = points.map((p) => p.breadth_20);
  const b50 = points.map((p) => p.breadth_50);
  const b200 = points.map((p) => p.breadth_200);

  return {
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (v == null ? "—" : `${Number(v).toFixed(1)}%`),
    },
    legend: { data: ["20日", "50日", "200日"], top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 42, right: 16, top: 30, bottom: 26 },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#6b7280", hideOverlap: true },
      axisLine: { lineStyle: { color: "#d6dde6" } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { fontSize: 10, color: "#6b7280", formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#eef1f5" } },
    },
    series: [
      {
        name: "20日",
        type: "line",
        data: b20,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#ea580c" },
        itemStyle: { color: "#ea580c" },
        markLine: {
          silent: true,
          symbol: "none",
          data: DIVIDING_LINES.map((d) => ({
            yAxis: d.y,
            lineStyle: { color: d.color, type: "dashed", width: 1 },
            label: {
              formatter: d.label,
              color: d.color,
              fontSize: 10,
              position: "insideEndTop",
            },
          })),
        },
      },
      {
        name: "50日",
        type: "line",
        data: b50,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#3a7bd5" },
        itemStyle: { color: "#3a7bd5" },
      },
      {
        name: "200日",
        type: "line",
        data: b200,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#7c3aed" },
        itemStyle: { color: "#7c3aed" },
      },
    ],
  };
}
