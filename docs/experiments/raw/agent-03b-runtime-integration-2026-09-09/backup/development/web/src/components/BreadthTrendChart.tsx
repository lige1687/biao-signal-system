import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { api } from "../api/client";
import type { BreadthHistoryPoint } from "../types";

const LOOKBACK_DAYS = 1260;
// 分界线：20% 机会位（超卖·绿）/ 50% 多空分界（灰）/ 80% 压力位（超买·红）
// 行业通用标准：% 站上均线个股占比的广度极值以 80% 超买 / 20% 超卖 / 50% 多空分界为准
// （TradingView 官方宽度脚本、marketinout %Above50MA、thetrading.tools / pomegra.io 等
//  quant 框架；华泰证券《A股择时之技术面指标测试》(2021) 亦建议对 A 股采用标准/默认参数）。
const DIVIDING_LINES: { y: number; label: string; color: string }[] = [
  { y: 80, label: "压力位 80%", color: "#e33d47" },
  { y: 50, label: "50 多空分界", color: "#6b7280" },
  { y: 20, label: "机会位 20%", color: "#16a34a" },
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
  const degenerate = detectDegenerate(points);

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
    if (!instRef.current || degenerate.isDegenerate) return;
    instRef.current.setOption(buildTrendOption(points), true);
  }, [points, degenerate.isDegenerate]);

  // 全A(CN_ALL_A) 的 MA 上方占比历史来自本机预计算落盘（/market-context/breadth-history
  // 对 CN_ALL_A 已改为返回真宽度历史）。有历史则绘制真实趋势，无则显示「暂无历史」占位——
  // 不再展示旧 fixture 假序列。涨跌家数口径实时可用，见上方占比条与数字。

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
      {!isLoading && !isError && degenerate.isDegenerate && points.length >= 2 && (
        <div className="muted" style={{ padding: "40px 16px", textAlign: "center", color: "#9ca3af" }}>
          <div style={{ fontSize: 13, marginBottom: 4 }}>⏳ {degenerate.reason}</div>
          <div style={{ fontSize: 11, color: "#b0b7bf" }}>
            {marketId === "SP500"
              ? "提示：需在终端重新运行 SP500 入库脚本（增大 --max-bars）以拉取全量 K 线"
              : "系统会在每个交易日自动积累宽度历史"}
          </div>
        </div>
      )}
      <div
        ref={chartRef}
        className="macro-chart"
        style={{ height: degenerate.isDegenerate && points.length >= 2 ? 0 : 240 }}
      />
    </div>
  );
}

/** 检测历史数据是否退化（全是 null / 全同值 / 有效点太少） */
function detectDegenerate(points: BreadthHistoryPoint[]): {
  isDegenerate: boolean;
  reason: string;
} {
  if (points.length < 2) return { isDegenerate: true, reason: "暂无历史（首次写入后才有序列）" };
  // 过滤出至少有一条线有值的点
  const validPoints = points.filter(
    (p) => p.breadth_20 != null || p.breadth_50 != null || p.breadth_200 != null,
  );
  if (validPoints.length < 4) {
    return { isDegenerate: true, reason: `宽度历史积累中（${validPoints.length} 个有效交易日，需更多数据）` };
  }
  // 检查每条线是否全同值（标准差 ≈ 0）
  for (const [key, label] of [
    ["breadth_20", "20日"],
    ["breadth_50", "50日"],
    ["breadth_200", "200日"],
  ] as const) {
    const vals = validPoints.map((p) => p[key]).filter((v): v is number => v != null);
    if (vals.length >= 2) {
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      const variance = vals.reduce((a, v) => a + (v - mean) ** 2, 0) / vals.length;
      if (variance < 0.001) {
        return { isDegenerate: true, reason: `${label}宽度历史值恒定（K线窗口不足导致MA不变，需重新入库全量历史）` };
      }
    }
  }
  return { isDegenerate: false, reason: "" };
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
      },
      {
        name: "50日",
        type: "line",
        data: b50,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#2563eb" },
        itemStyle: { color: "#2563eb" },
      },
      {
        name: "200日",
        type: "line",
        data: b200,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#7c3aed" },
        itemStyle: { color: "#7c3aed" },
      },
      // 超买超卖分界线（20/50/80）改挂到隐形式锚点序列：用户隐藏「20日」线时，
      // 分界线不再连带消失（legend.data 不含此锚点名，图例无法开关它）。
      {
        name: "__breadth_axis_marks__",
        type: "line",
        data: [],
        xAxisIndex: 0,
        yAxisIndex: 0,
        showSymbol: false,
        silent: true,
        tooltip: { show: false },
        lineStyle: { opacity: 0 },
        itemStyle: { opacity: 0 },
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
    ],
  };
}
