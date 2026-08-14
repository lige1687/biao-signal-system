import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface SparklineProps {
  values: number[];
  color?: string;
  height?: number;
  /** 可选：在指定 y 值画一条淡色分界线，让小图也能感知「当前在哪一档」。 */
  markY?: number | null;
  onClick?: () => void;
}

/** 卡片级迷你趋势线：无坐标轴/网格，带淡色区域填充，可点击展开大图。 */
export default function Sparkline({
  values,
  color = "#3a7bd5",
  height = 48,
  markY = null,
  onClick,
}: SparklineProps) {
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
    instRef.current?.setOption(buildSparkOption(values, color, markY), true);
  }, [values, color, markY]);

  if (values.length < 2) {
    return <div className="sparkline sparkline-empty" style={{ height }}>—</div>;
  }

  return (
    <div
      ref={ref}
      className="sparkline"
      style={{ height, cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      aria-label="点击查看大图"
    />
  );
}

function buildSparkOption(
  values: number[],
  color: string,
  markY: number | null,
): echarts.EChartsOption {
  const seriesOpt: echarts.LineSeriesOption = {
    type: "line",
    data: values,
    showSymbol: false,
    lineStyle: { width: 1.5, color },
    itemStyle: { color },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: `${color}33` },
        { offset: 1, color: `${color}05` },
      ]),
    },
  };
  if (markY != null) {
    seriesOpt.markLine = {
      silent: true,
      symbol: "none",
      data: [
        {
          yAxis: markY,
          lineStyle: { color: "#9ca3af", type: "dashed", width: 1 },
          label: { show: false },
        },
      ],
    };
  }
  return {
    grid: { left: 0, right: 0, top: 3, bottom: 0 },
    xAxis: {
      type: "category",
      show: false,
      boundaryGap: false,
      data: values.map((_, i) => i),
    },
    yAxis: { type: "value", show: false, scale: true },
    tooltip: { show: false },
    series: [seriesOpt],
  };
}
