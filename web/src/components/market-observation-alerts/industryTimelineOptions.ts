import type { EChartsOption } from "echarts";
import { CHART_COLORS } from "./ChartLegend";
import type { IndustryHistoryPoint } from "./industryStructureData";

export type IndustryRange = { start: number; end: number };

export function industryRange(length: number, days: 60 | 120 | "all" = 120): IndustryRange {
  return { start: days === "all" ? 0 : Math.max(0, length - days), end: Math.max(0, length - 1) };
}

export function industryRangeFromZoom(length: number, start: number, end: number): IndustryRange {
  const clamp = (value: number) => Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const a = clamp(start); const b = clamp(end); const last = Math.max(0, length - 1);
  return { start: Math.round(Math.min(a, b) * last / 100), end: Math.round(Math.max(a, b) * last / 100) };
}

/** A single zoom model targets both date axes, so either panel and the slider stay aligned. */
export function industryTimelineOption(history: IndustryHistoryPoint[], height: number): EChartsOption {
  const dates = history.map(point => point.date);
  const range = industryRange(history.length);
  const plotHeight = (height - 128) / 2;
  const secondTop = 28 + plotHeight + 40;
  const text = { fontSize: 13, color: "#5d655e" };
  return {
    animation: false,
    textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
    title: [
      { text: "同步程度 · 相关系数", left: 0, top: 0, textStyle: { ...text, color: CHART_COLORS.primary, fontWeight: 600 } },
      { text: "行业分化 · 百分点", left: 0, top: secondTop - 28, textStyle: { ...text, color: CHART_COLORS.secondary, fontWeight: 600 } },
    ],
    grid: [
      { left: 44, right: 18, top: 28, height: plotHeight },
      { left: 44, right: 18, top: secondTop, height: plotHeight },
    ],
    axisPointer: { link: [{ xAxisIndex: [0, 1] }], lineStyle: { color: "#8b9388", type: "dashed" } },
    tooltip: {
      trigger: "axis", confine: true, textStyle: { ...text }, backgroundColor: "#fffffff5", borderColor: "#d9ded5",
      formatter: (raw: unknown) => {
        const first = (Array.isArray(raw) ? raw[0] : raw) as { axisValue?: string; dataIndex?: number } | undefined;
        const point = history.find(item => item.date === first?.axisValue) ?? history[first?.dataIndex ?? -1];
        return point ? `${point.date}<br/>同步程度：${point.correlation.toFixed(3)}<br/>行业分化：${point.dispersion5.toFixed(2)} 个百分点` : "—";
      },
    },
    xAxis: [0, 1].map(gridIndex => ({
      type: "category", gridIndex, data: dates, boundaryGap: false,
      axisLabel: { ...text, show: gridIndex === 1, hideOverlap: true, showMinLabel: true, showMaxLabel: true, margin: 10,
        alignMinLabel: "left", alignMaxLabel: "right", formatter: (date: string) => height < 300 ? date.slice(2) : date },
      axisTick: { show: false }, axisLine: { lineStyle: { color: "#c2c8bd" } },
    })),
    yAxis: [0, 1].map(gridIndex => ({
      type: "value", gridIndex, scale: true, splitNumber: 2,
      axisLabel: { ...text, formatter: (value: number) => Number(value.toFixed(2)).toString() },
      splitLine: { lineStyle: { color: "#e6e9e1" } },
    })),
    dataZoom: [
      { id: "industry-inside", type: "inside", xAxisIndex: [0, 1], startValue: range.start, endValue: range.end,
        minValueSpan: 9, filterMode: "filter", zoomOnMouseWheel: true, moveOnMouseMove: true, moveOnMouseWheel: false },
      { id: "industry-slider", type: "slider", xAxisIndex: [0, 1], startValue: range.start, endValue: range.end,
        minValueSpan: 9, filterMode: "filter", bottom: 3, left: 44, right: 18, height: 19, showDetail: false,
        brushSelect: false, borderColor: "#cbd2c5", fillerColor: "#52675e22", handleStyle: { color: "#728577" },
        textStyle: text },
    ],
    series: [
      { name: "同步程度", type: "line", xAxisIndex: 0, yAxisIndex: 0, data: history.map(point => point.correlation),
        showSymbol: false, lineStyle: { width: 2, color: CHART_COLORS.primary }, itemStyle: { color: CHART_COLORS.primary } },
      { name: "行业分化", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: history.map(point => point.dispersion5),
        showSymbol: false, lineStyle: { width: 2, color: CHART_COLORS.secondary }, itemStyle: { color: CHART_COLORS.secondary } },
    ],
  };
}
