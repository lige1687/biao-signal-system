import { useEffect, useRef } from "react";
import * as echarts from "echarts";

export interface LineSeries {
  name: string;
  values: (number | null)[];
  color: string;
}

/** Market observation curves use vector text so monitor/zoom changes do not blur axes. */
export default function MarketTrendChart({ dates, series, unit, height = 260 }: {
  dates: string[]; series: LineSeries[]; unit: string; height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "svg" });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    const multi = series.length > 1;
    const zoom = dates.length > 60;
    const axisText = { fontSize: 12, color: "#374151" };
    const option: echarts.EChartsOption = {
      animation: false,
      textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
      tooltip: {
        trigger: "axis", confine: true, textStyle: { fontSize: 13 },
        valueFormatter: (value) => value == null ? "—" : `${Number(value).toFixed(2)}${unit}`,
      },
      legend: multi ? {
        type: "plain", top: 0, left: 0, right: 0,
        data: series.map((item) => item.name), textStyle: axisText,
      } : undefined,
      // Reserve half a date label at both ends; keep the slider below the date row.
      grid: { left: 60, right: 42, top: multi ? 62 : 28, bottom: zoom ? 66 : 40 },
      xAxis: {
        type: "category", data: dates, boundaryGap: false,
        axisLabel: { ...axisText, hideOverlap: true, showMinLabel: true, showMaxLabel: true, margin: 12 },
        axisTick: { show: false }, axisLine: { lineStyle: { color: "#9ca3af" } },
      },
      yAxis: {
        type: "value", scale: true, name: unit || "指数值", nameGap: 12,
        nameTextStyle: { ...axisText, align: "right" },
        axisLabel: { ...axisText, margin: 10 },
        splitNumber: 4, splitLine: { lineStyle: { color: "#e2e8f0" } },
      },
      dataZoom: zoom ? [
        { type: "inside", start: 0, end: 100, zoomOnMouseWheel: true, moveOnMouseMove: true, moveOnMouseWheel: false },
        { type: "slider", start: 0, end: 100, bottom: 4, height: 20, textStyle: axisText, showDetail: false },
      ] : [],
      series: series.map((item) => ({
        name: item.name, type: "line", data: item.values, showSymbol: dates.length <= 8,
        symbolSize: 5, lineStyle: { width: 2, color: item.color }, itemStyle: { color: item.color },
      })),
    };
    chartRef.current?.setOption(option, true);
  }, [dates, series, unit]);

  return <div ref={ref} className="ms-trend-chart" role="img"
    aria-label={`${series.map((item) => item.name).join("、")}历史曲线；横轴日期，纵轴${unit || "指数值"}`}
    style={{ height, minWidth: 0 }} />;
}
