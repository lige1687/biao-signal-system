import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { MarkLine, ZoneLevel } from "./zones";
import { zoneToneColor } from "./zones";

export interface LineSeries {
  name: string;
  values: (number | null)[];
  color: string;
}

interface TrendChartProps {
  dates: string[];
  series: LineSeries[];
  unit: string;
  markLines?: MarkLine[];
  /** 区间框架：在图上渲染成纵向色带（机会绿 -> 风险红，低透明度）。 */
  zones?: readonly ZoneLevel[];
  height?: number;
  /** 固定 y 轴区间（宽度用 0–100）；不传则自适应 scale。 */
  yRange?: [number, number];
}

/** 大图趋势线：坐标轴 + tooltip + 分界线 + 区间色带，支持单线/多线（宽度 20/50/200）。 */
export default function TrendChart({
  dates,
  series,
  unit,
  markLines = [],
  zones = [],
  height = 300,
  yRange,
}: TrendChartProps) {
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
      buildTrendOption(dates, series, unit, markLines, zones, yRange),
      true,
    );
  }, [dates, series, unit, markLines, zones, yRange]);

  return <div ref={ref} className="macro-chart" style={{ height }} />;
}

/** 区间 -> markArea 色带：相邻区间边界围成一个矩形，首尾贴 y 轴 min/max。 */
function zoneBands(
  zones: readonly ZoneLevel[],
): NonNullable<echarts.LineSeriesOption["markArea"]> {
  return {
    silent: true,
    data: zones.map((z, i) => {
      const lo = i === 0 ? "min" : zones[i - 1].max;
      const hi = z.max === Infinity ? "max" : z.max;
      return [
        { yAxis: lo, xAxis: 0 },
        {
          yAxis: hi,
          xAxis: "max",
          itemStyle: { color: zoneToneColor(z.tone), opacity: 0.06 },
        },
      ];
    }),
  };
}

function buildTrendOption(
  dates: string[],
  series: LineSeries[],
  unit: string,
  markLines: MarkLine[],
  zones: readonly ZoneLevel[],
  yRange?: [number, number],
): echarts.EChartsOption {
  const multi = series.length > 1;
  const seriesOpt: echarts.LineSeriesOption[] = series.map((s) => ({
    name: s.name,
    type: "line",
    data: s.values,
    showSymbol: false,
    lineStyle: { width: 1.6, color: s.color },
    itemStyle: { color: s.color },
  }));
  if (zones.length && seriesOpt.length) {
    seriesOpt[0].markArea = zoneBands(zones);
  }
  if (markLines.length && seriesOpt.length) {
    seriesOpt[0].markLine = {
      silent: true,
      symbol: "none",
      data: markLines.map((mk) => ({
        yAxis: mk.y,
        lineStyle: { color: mk.color, type: "dashed", width: 1 },
        label: {
          formatter: mk.label,
          color: mk.color,
          fontSize: 10,
          position: "insideEndTop",
        },
      })),
    };
  }

  return {
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (v == null ? "-" : `${Number(v).toFixed(2)}${unit}`),
    },
    legend: multi
      ? { data: series.map((s) => s.name), top: 0, textStyle: { fontSize: 11 } }
      : undefined,
    grid: { left: 46, right: 16, top: multi ? 30 : 18, bottom: 24 },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#6b7280", hideOverlap: true },
      axisLine: { lineStyle: { color: "#d6dde6" } },
    },
    yAxis: {
      type: "value",
      scale: yRange == null,
      min: yRange?.[0],
      max: yRange?.[1],
      axisLabel: { fontSize: 10, color: "#6b7280" },
      splitLine: { lineStyle: { color: "#eef1f5" } },
    },
    series: seriesOpt,
  };
}
