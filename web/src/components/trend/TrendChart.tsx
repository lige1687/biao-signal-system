import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { MarkLine, ZoneLevel } from "./zones";
import { zoneBands, zoneMarkLines } from "./marks";

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
  /** 分界线渲染为可拖动 graphic（默认静态虚线 markLine）。 */
  draggableMarkLines?: boolean;
  /** 默认可见窗口（最近多少个交易日）。数据更多时只展开这一段，用户可缩放查看全量。
   *  不传则展示全部（保持其它用法如利率抽屉的旧行为）。 */
  defaultWindowDays?: number;
}

/** 大图趋势线：坐标轴 + tooltip + 分界线 + 区间色带，支持单线/多线（宽度 20/50/200）。 */

/** 承载分界线/区间色带的隐形式锚点序列名（不进图例，专属渲染参考标记）。 */
const TREND_MARK_ANCHOR = "__trend_marks_anchor__";

export default function TrendChart({
  dates,
  series,
  unit,
  markLines = [],
  zones = [],
  height = 300,
  yRange,
  draggableMarkLines = false,
  defaultWindowDays,
}: TrendChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);
  /** 拖动后的自定义分界线位置（index -> y 值）；改 series/阈值时清空回到默认。 */
  const draggedRef = useRef<Record<number, number>>({});

  useEffect(() => {
    if (!ref.current) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    instRef.current = inst;
    const ro = new ResizeObserver(() => {
      inst.resize();
      applyGraphics();
    });
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 把分界线渲染为可拖动的 graphic 元素（markLine 本身不支持拖动）。 */
  function applyGraphics() {
    const inst = instRef.current;
    if (!inst || !draggableMarkLines || markLines.length === 0 || dates.length < 2) {
      inst?.setOption({ graphic: [] });
      return;
    }
    // 取当前 dataZoom 可见窗口的起止 index（无 dataZoom 时用全量 0..n-1），
    // 这样分界线横线只画在可见区间，不会延伸到被缩放隐藏的左侧/右侧。
    const dzOpt = (inst.getOption() as { dataZoom?: Array<{ start?: number; end?: number }> })
      .dataZoom?.[0];
    const n = dates.length;
    let iStart = 0;
    let iEnd = n - 1;
    if (dzOpt && typeof dzOpt.start === "number" && typeof dzOpt.end === "number") {
      iStart = Math.max(0, Math.min(n - 1, Math.round((dzOpt.start / 100) * (n - 1))));
      iEnd = Math.max(0, Math.min(n - 1, Math.round((dzOpt.end / 100) * (n - 1))));
    }
    const left = inst.convertToPixel({ gridIndex: 0 }, [iStart, 0])?.[0] ?? 46;
    const right = inst.convertToPixel({ gridIndex: 0 }, [iEnd, 0])?.[0] ?? 0;
    const els: echarts.GraphicComponentOption[] = markLines.map((mk, i) => {
      const y0 = draggedRef.current[i] ?? mk.y;
      const py = inst.convertToPixel({ yAxisIndex: 0 }, y0);
      const labelText = () =>
        `${mk.label} · ${(draggedRef.current[i] ?? mk.y).toFixed(2)}${unit}`;
      return {
        id: `ml-${i}`,
        type: "group",
        draggable: true,
        position: [0, py] as [number, number],
        // 拖动只允许纵向：每次 drag 把水平位移归零。
        ondrag(this: { position: [number, number] }) {
          this.position[0] = 0;
          const val = inst.convertFromPixel({ yAxisIndex: 0 }, this.position[1]);
          if (Number.isFinite(val)) {
            draggedRef.current[i] = val;
            const label = (this as unknown as { childOfName: (n: string) => { setStyle: (o: { text: string }) => void } })
              .childOfName("mlLabel");
            label?.setStyle({ text: labelText() });
          }
        },
        children: [
          {
            type: "line" as const,
            silent: true,
            shape: { x1: left, y1: 0, x2: right, y2: 0 },
            style: { stroke: mk.color, lineWidth: 1, lineDash: [4, 3] },
          },
          {
            type: "text" as const,
            name: "mlLabel",
            silent: true,
            style: {
              text: labelText(),
              x: right - 4,
              y: -6,
              fill: mk.color,
              fontSize: 10,
              align: "right",
            },
          },
        ],
        cursor: "ns-resize",
      };
    });
    inst.setOption({ graphic: els });
  }

  useEffect(() => {
    draggedRef.current = {}; // 数据/阈值变了，拖动位置作废，回到默认分位线
    instRef.current?.setOption(
      buildTrendOption(dates, series, unit, draggableMarkLines ? [] : markLines, zones, yRange, defaultWindowDays),
      true,
    );
    applyGraphics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates, series, unit, markLines, zones, yRange, draggableMarkLines, defaultWindowDays]);

  // dataZoom 改变时（用户滚轮/拖拽缩放）重算可拖动分界线的左右端点，确保分界线横跨可见窗口。
  useEffect(() => {
    const inst = instRef.current;
    if (!inst) return;
    const onZoom = () => applyGraphics();
    inst.on("dataZoom", onZoom);
    return () => {
      inst.off("dataZoom", onZoom);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={ref} className="macro-chart" style={{ height }} />;
}

function buildTrendOption(
  dates: string[],
  series: LineSeries[],
  unit: string,
  markLines: MarkLine[],
  zones: readonly ZoneLevel[],
  yRange?: [number, number],
  defaultWindowDays?: number,
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
  // 分界线/区间色带改挂到隐形式锚点序列，而非第一条数据线：多线图（如宽度 20/50/200）
  // 用户在图例里隐藏「20日」时，挂它身上的超买超卖区间/分界线不会跟着整条序列消失。
  // legend.data 只列输入的数据序列名，锚点名自动排除、无法被开关。
  // 注意 data 必须是与 xAxis 等长的 null 数组（不能用 [] 空数组）——空 data 时 ECharts
  // 会把 markArea 角落画成对角 bowtie（X 形交叉），而非 axis-aligned 矩形。line 仍
  // opacity:0 不可见，仅为给 ECharts 建立坐标系上下文。
  if ((zones.length || markLines.length) && seriesOpt.length) {
    seriesOpt.push({
      name: TREND_MARK_ANCHOR,
      type: "line",
      data: new Array(dates.length).fill(null),
      xAxisIndex: 0,
      yAxisIndex: 0,
      showSymbol: false,
      silent: true,
      tooltip: { show: false },
      lineStyle: { opacity: 0 },
      itemStyle: { opacity: 0 },
      markArea: zones.length ? zoneBands(zones) : undefined,
      markLine: markLines.length ? zoneMarkLines(markLines) : undefined,
    });
  }

  // 缩放：>60 个数据点即开启「滚轮缩放 + 底部滑块拖拽」；defaultWindowDays 只决定初始窗口。
  // 数据一次给全量，缩放/拖拽纯本地完成，不触发任何重拉。
  const nDates = dates.length;
  let dataZoomOpt: echarts.EChartsOption["dataZoom"];
  if (nDates > 60) {
    const startPct =
      defaultWindowDays != null && nDates > defaultWindowDays
        ? Math.max(0, ((nDates - defaultWindowDays) / nDates) * 100)
        : 0;
    dataZoomOpt = [
      {
        type: "inside",
        start: startPct,
        end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
      },
      { type: "slider", start: startPct, end: 100, bottom: 4, height: 18 },
    ];
  }

  return {
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (v == null ? "-" : `${Number(v).toFixed(2)}${unit}`),
    },
    legend: multi
      ? { data: series.map((s) => s.name), top: 0, textStyle: { fontSize: 11 } }
      : undefined,
    grid: { left: 46, right: 16, top: multi ? 30 : 18, bottom: dataZoomOpt ? 46 : 24 },
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
    ...(dataZoomOpt ? { dataZoom: dataZoomOpt } : {}),
    series: seriesOpt,
  };
}
