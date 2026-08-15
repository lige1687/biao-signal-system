import { useEffect, useRef } from "react";
import * as echarts from "echarts";

export interface OverlaySeries {
  name: string;
  values: (number | null)[];
  color: string;
  /** 左轴 = 指数点位；右轴 = 收益率/占比（%）。 */
  axis: "left" | "right";
}

interface OverlayChartProps {
  dates: string[];
  series: OverlaySeries[];
  /** 左轴名（指数）。 */
  leftName?: string;
  /** 右轴名（收益率%）。 */
  rightName?: string;
  /** 初始可视窗口占全序列的百分比（如 15 = 展示最近 15%）。 */
  startPercent?: number;
  height?: number;
}

/** 长周期叠加大图：指数（左轴）× 利率/两融占比（右轴），底部 dataZoom 滑动窗口。 */
export default function OverlayChart({
  dates,
  series,
  leftName = "指数",
  rightName = "收益率 %",
  startPercent = 15,
  height = 400,
}: OverlayChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    instRef.current = inst;
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
  }, []);

  useEffect(() => {
    instRef.current?.setOption(
      buildOverlayOption(dates, series, leftName, rightName, startPercent),
      true,
    );
  }, [dates, series, leftName, rightName, startPercent]);

  return <div ref={ref} className="macro-chart" style={{ height }} />;
}

function buildOverlayOption(
  dates: string[],
  series: OverlaySeries[],
  leftName: string,
  rightName: string,
  startPercent: number,
): echarts.EChartsOption {
  return {
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (v == null ? "-" : Number(v).toFixed(2)),
    },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 58, right: 58, top: 30, bottom: 56 },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#6b7280", hideOverlap: true },
      axisLine: { lineStyle: { color: "#d6dde6" } },
    },
    yAxis: [
      {
        type: "value",
        scale: true,
        name: leftName,
        nameTextStyle: { fontSize: 10 },
        axisLabel: { fontSize: 10, color: "#6b7280" },
        splitLine: { lineStyle: { color: "#eef1f5" } },
      },
      {
        type: "value",
        scale: true,
        name: rightName,
        nameTextStyle: { fontSize: 10 },
        axisLabel: { fontSize: 10, color: "#6b7280", formatter: "{value}%" },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: "slider", start: Math.max(0, 100 - startPercent), end: 100, bottom: 6, height: 20 },
      { type: "inside" },
    ],
    series: series.map((s): echarts.LineSeriesOption => ({
      name: s.name,
      type: "line",
      yAxisIndex: s.axis === "right" ? 1 : 0,
      data: s.values,
      showSymbol: false,
      connectNulls: true, // 债券/股票交易日历不完全重合，跳过空点连线
      lineStyle: { width: 1.4, color: s.color },
      itemStyle: { color: s.color },
    })),
  };
}
