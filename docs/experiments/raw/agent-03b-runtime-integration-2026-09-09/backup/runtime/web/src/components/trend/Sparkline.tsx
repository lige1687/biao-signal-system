import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface SparklineProps {
  values: number[];
  color?: string;
  height?: number;
  /** 可选：在指定 y 值画一条淡色分界线，让小图也能感知「当前在哪一档」。 */
  markY?: number | null;
  onClick?: () => void;
  /** 默认可见窗口（最近多少个交易日）。数据更多时只展开这一段，用户可用鼠标
   *  滚轮缩小/拖拽平移查看更早数据；默认 756 ≈ 3 年（1260 个点≈5 年的密度太高）。 */
  defaultWindowDays?: number;
}

/** 卡片级迷你趋势线：无坐标轴/网格，带淡色区域填充，可点击展开大图。 */
export default function Sparkline({
  values,
  color = "#2563eb",
  height = 48,
  markY = null,
  onClick,
  defaultWindowDays = 756,
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

  // 兜底：阻止浏览器把触控板「双指上下滑 / 双指捏合（Ctrl+滚轮）」抢去当页面滚动/页面缩放。
  // React 的 onWheel 是 passive 监听，preventDefault 无效，必须用原生 non-passive 监听；
  // ECharts 的 dataZoom.inside 在 canvas 上同样监听 wheel 并缩放，这里仅负责拦住浏览器默认行为。
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => {
    instRef.current?.setOption(
      buildSparkOption(values, color, markY, defaultWindowDays),
      true,
    );
  }, [values, color, markY, defaultWindowDays]);

  if (values.length < 2) {
    return <div className="sparkline sparkline-empty" style={{ height }}>—</div>;
  }

  return (
    <div
      ref={ref}
      className="sparkline"
      style={{ height, cursor: onClick ? "grab" : "default" }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      aria-label="点击查看大图；可滚轮缩放、拖拽平移"
    />
  );
}

function buildSparkOption(
  values: number[],
  color: string,
  markY: number | null,
  defaultWindowDays: number,
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
  // 默认只展开最近 defaultWindowDays 个交易日；用户可用鼠标滚轮缩小（看更早）或拖拽平移。
  // start/end 是数据索引区间的百分比（0–100）；数据更少时直接全展。
  const n = values.length;
  const startPct =
    n > defaultWindowDays
      ? Math.max(0, ((n - defaultWindowDays) / n) * 100)
      : 0;
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
    // inside: 滚轮缩放 + 拖拽平移，无可见控件（适合迷你图）
    dataZoom: [
      {
        type: "inside",
        start: startPct,
        end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
      },
    ],
    series: [seriesOpt],
  };
}