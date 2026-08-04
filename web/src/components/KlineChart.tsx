import * as echarts from "echarts/core";
import { BarChart, CandlestickChart, LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";
import type { ChartPayload, LevelLine } from "../types";
import { buildStructureMarkPoints } from "./klineStructureMarks";

echarts.use([
  CandlestickChart,
  LineChart,
  BarChart,
  GridComponent,
  DataZoomComponent,
  LegendComponent,
  TooltipComponent,
  MarkLineComponent,
  MarkPointComponent,
  CanvasRenderer,
]);

/** 点击图上标记/参考线时回传给详情页的信息。 */
export interface MarkPick {
  kind:
    | "bottom_mark"
    | "top_mark"
    | "invalidated_mark"
    | "key_volatility"
    | "b1_line"
    | "bottom_line"
    | "top_line";
  /** 标记类点击带日期；横线类点击没有日期，用 level 表示价位 */
  date?: string;
  price?: number;
  level?: number;
  structureId?: string;
  structureType?: string;
  colorState?: string;
  pivotDate?: string | null;
  distancePct?: number | null;
}

/** 均线开关键。 */
export type MaKey = "ema20" | "sma20" | "ema60" | "ema120" | "sma60" | "sma120";

/**
 * 均线样式：按周期配色，按类型配线型。
 *
 * 同一周期的 EMA/SMA 共用一个颜色，靠线型区分（EMA 实线、SMA 虚线），
 * 这样一眼就能看出「这两条是同一周期的快慢版本」，而不是六个互不相干
 * 的颜色。周期用冷暖递进：20 蓝（短）、60 绿（中）、120 红（长）。
 */
export const MA_META: {
  key: MaKey;
  label: string;
  color: string;
  dashed: boolean;
}[] = [
  { key: "ema20", label: "EMA20", color: "#2563eb", dashed: false },
  { key: "sma20", label: "SMA20", color: "#2563eb", dashed: true },
  { key: "ema60", label: "EMA60", color: "#0b9b64", dashed: false },
  { key: "sma60", label: "SMA60", color: "#0b9b64", dashed: true },
  { key: "ema120", label: "EMA120", color: "#dc2626", dashed: false },
  { key: "sma120", label: "SMA120", color: "#dc2626", dashed: true },
];

/** K 线着色模式。 */
export type ColorMode = "red_green" | "lei_state";

/** 图上标记/参考线的显示开关。默认全关，避免遮挡看盘。 */
export interface ChartDisplay {
  bottomMarks: boolean; // 底部确认菱形（绿/灰=失效）
  topMarks: boolean; // 顶部确认菱形
  invalidatedMarks: boolean; // 结构失效 ×
  keyVolatility: boolean; // 关键性波动竖线与把手
  levels: boolean; // B1 / C 点 / 颈线
  ma: Record<MaKey, boolean>;
  colorMode: ColorMode;
}

export const DEFAULT_DISPLAY: ChartDisplay = {
  bottomMarks: false,
  topMarks: false,
  invalidatedMarks: false,
  keyVolatility: false,
  levels: false,
  ma: {
    ema20: true,
    sma20: true,
    ema60: false,
    sma60: false,
    ema120: false,
    sma120: false,
  },
  colorMode: "red_green",
};

interface Props {
  payload: ChartPayload;
  display: ChartDisplay;
  onPick?: (pick: MarkPick) => void;
  /** 父组件要导出当前图为 PNG 时传入：函数体里执行下载。 */
  onDownload?: (download: () => void) => void;
}

export default function KlineChart({ payload, display, onPick, onDownload }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  // onPick 存进 ref，不进 setOption 的依赖，避免父组件 re-render 导致整图重建。
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  // init 只跑一次：创建实例 + 绑定不变的 click/resize 监听。
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;

    const onClick = (params: { data?: unknown }) => {
      const data = params?.data as { pick?: MarkPick } | null | undefined;
      const pick = data?.pick;
      if (pick && onPickRef.current) onPickRef.current(pick);
    };
    chart.on("click", onClick as (params: unknown) => void);

    // markPoint hover：光标变手型，提示用户标记可点
    const onOver = (params: { data?: unknown }) => {
      const data = params?.data as { pick?: MarkPick } | null | undefined;
      if (ref.current) ref.current.style.cursor = data?.pick ? "pointer" : "crosshair";
    };
    chart.on("mouseover", onOver as (params: unknown) => void);
    chart.on("mouseout", () => {
      if (ref.current) ref.current.style.cursor = "crosshair";
    });

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.off("click", onClick as (params: unknown) => void);
      chart.off("mouseover", onOver as (params: unknown) => void);
      chart.off("mouseout");
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  // 把「下载当前图为 PNG」的能力回传给父组件（ChartControls 的导出按钮）
  useEffect(() => {
    if (!onDownload) return;
    onDownload(() => {
      const chart = chartRef.current;
      if (!chart) return;
      const url = chart.getDataURL({
        type: "png",
        pixelRatio: 2,
        backgroundColor: "#ffffff",
      });
      const a = document.createElement("a");
      a.href = url;
      a.download = `${payload.symbol}-kline-${new Date().toISOString().slice(0, 10)}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
  }, [onDownload, payload.symbol]);

  // setOption 独立 effect：data/开关变化时只更新 option，不销毁实例，
  // 保留 dataZoom 缩放位置，不闪烁。用 notMerge 防止旧标记/均线残留。
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(buildKlineOption(payload, display), { notMerge: true });
  }, [payload, display]);

  return <div className="kline" ref={ref} />;
}

/** 大数收敛：成交量/成交额这类数用万/亿单位，避免一长串。 */
function fmtBig(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(n / 1e4).toFixed(0)}万`;
  return String(n);
}

/** 把 payload + display 组装成 ECharts option。
 *  抽成纯函数：setOption effect 每次调用它，不接触 chart 实例。 */
function buildKlineOption(payload: ChartPayload, display: ChartDisplay) {
    const d = payload;
    const up = d.priceUp;
    const down = d.priceDown;
    // 本站已改为亮色主题，与 Streamlit 研究页一致，因此直接使用后端
    // stateColors（green=#0b9b64 / gray=#8c96a8 / black=#1f2937）——
    // 它本就是为白底设计的，无需再做暗底重映射。
    const stateColors: Record<string, string> = d.stateColors ?? {};

    const markLineData: object[] = [];
    const markPointData: object[] = [];

    // ---- 水平参考线（B1 / C 点 / 顶部颈线）----
    // ECharts 的 markLine 不派发 click，因此每条线在最右端放一个可点圆点把手。
    const lastDate = d.dates.length ? d.dates[d.dates.length - 1] : null;

    const pushLine = (
      line: LevelLine,
      kind: MarkPick["kind"],
      labelPrefix: string,
      dash: "dashed" | "dotted",
    ) => {
      markLineData.push({
        yAxis: line.yAxis,
        lineStyle: { color: line.color, type: dash, width: line.width ?? 1.4 },
        // markLine 自带 label 默认在图中央偏右（vertical:mid, horizontal:center），
        // 当 K 线图宽时与最右端的把手重叠，**关闭**。把手本身带 label 显示
        // 名字 + 价位，信息一致。
        label: { show: false },
      });
      if (lastDate) {
        markPointData.push({
          coord: [lastDate, line.yAxis],
          symbol: "circle",
          symbolSize: 11,
          symbolOffset: [16, 0],
          itemStyle: { color: line.color, borderColor: "#ffffff", borderWidth: 1.5 },
          // 把手右侧加文字标签：名称 + 价位，与原 markLine 同样信息量
          // 但贴在右端不与线重叠。
          label: {
            show: true,
            position: "right",
            distance: 14,
            color: line.color,
            fontSize: 10,
            fontWeight: 600,
            formatter: `${labelPrefix} ${line.yAxis.toFixed(2)}`,
            backgroundColor: "rgba(255,255,255,0.85)",
            padding: [1, 3],
            borderRadius: 2,
          },
          pick: {
            kind,
            level: line.yAxis,
            structureId: line.structure_id,
            structureType: line.structure_type,
            pivotDate: line.pivot_date ?? null,
            distancePct: line.distance_pct ?? null,
          },
          tooltip: {
            formatter: `${line.label_cn ?? labelPrefix} ${line.yAxis}<br/>点击查看解释`,
          },
        });
      }
    };

    if (display.levels) {
      if (d.b1Line) pushLine(d.b1Line, "b1_line", "B1", "dashed");
      for (const line of d.bottomLines) pushLine(line, "bottom_line", "C", "dotted");
      for (const line of d.topLines) pushLine(line, "top_line", "颈线", "dotted");
    }

    // ---- 关键性波动竖线 + 可点三角把手 ----
    if (display.keyVolatility) {
      for (const kv of d.keyVolatility) {
        markLineData.push({
          xAxis: kv.date,
          lineStyle: {
            color: kv.state === "green" ? "#0b9b64" : "#1f2937",
            type: "solid",
            width: 0.8,
            opacity: 0.35,
          },
          label: { show: false },
        });
        const idx = d.dates.indexOf(kv.date);
        const bar = idx >= 0 ? d.ohlc[idx] : null;
        if (bar) {
          markPointData.push({
            coord: [kv.date, bar[3]],
            symbol: "triangle",
            symbolSize: 9,
            symbolOffset: [0, -14],
            itemStyle: {
              color: kv.state === "green" ? "#0b9b64" : "#1f2937",
              opacity: 0.9,
            },
            label: { show: false },
            pick: { kind: "key_volatility", date: kv.date, colorState: kv.state },
            tooltip: { formatter: `关键性波动 · ${kv.label} ${kv.date}` },
          });
        }
      }
    }

    // ---- 结构菱形 / 失效叉 ----
    // 纯函数内部按三个同级条件构建，保证顶部/失效不依赖底部开关。
    markPointData.push(...buildStructureMarkPoints(d, display));

    // ---- K 线着色 ----
    // red_green：中国惯例红涨绿跌，看涨跌用。
    // lei_state：按当日 LEI 三色（绿/灰/黑）着色，看信号状态段落用。
    //            此模式**不**用空心/实心区分涨跌——颜色只表达「当日状态」，
    //            涨跌方向需另看今日概述里的"开/高/低/收"四项，混在 K 线里
    //            会让本就低调的黑灰绿更看不清。
    const isLei = display.colorMode === "lei_state";
    const ohlcSeriesData = isLei
      ? d.ohlc.map((bar, i) => {
          // LEI 模式：颜色只表达「当日状态（绿/灰/黑）」，
          // 实体统一实心 + 较细的同色描边；不再用空心表示涨跌，
          // 否则「黑」色 K 线的空心几乎看不见。
          const state = d.states[i] ?? "unknown";
          const color = stateColors[state] ?? "#9ca3af";
          return {
            value: bar,
            itemStyle: {
              color,
              color0: color,
              borderColor: color,
              borderColor0: color,
              borderWidth: 1,
              opacity: 0.95,
            },
          };
        })
      : d.ohlc;

    const maSeries = MA_META.filter((m) => display.ma[m.key]).map((m) => ({
      name: m.label,
      type: "line" as const,
      data: d[m.key],
      xAxisIndex: 0,
      yAxisIndex: 0,
      showSymbol: false,
      smooth: true,
      lineStyle: {
        width: 1.2,
        color: m.color,
        // 同色的 SMA 走虚线，和实线 EMA 区分开
        type: m.dashed ? ("dashed" as const) : ("solid" as const),
      },
      itemStyle: { color: m.color },
      z: 3,
    }));

    return {
        backgroundColor: "transparent",
        animation: false,
        legend: {
          data: maSeries.map((s) => s.name),
          textStyle: { color: "#5b6473", fontSize: 11 },
          top: 4,
        },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "cross" },
          backgroundColor: "#ffffff",
          borderColor: "#dfe5ee",
          textStyle: { color: "#1f2937", fontSize: 12 },
          // 自定义 formatter：标清开/收/高/低，量能用万/亿收敛
          formatter: (params: unknown) => {
            const arr = params as Array<{
              seriesName: string;
              value: number | [number, number, number, number] | { value: number };
              axisValue: string;
              color: string;
            }>;
            if (!Array.isArray(arr) || arr.length === 0) return "";
            const date = arr[0].axisValue;
            const lines = [date];
            for (const p of arr) {
              const v = p.value;
              if (p.seriesName === "K线" && Array.isArray(v)) {
                // ECharts candlestick: [open, close, low, high]
                const [o, c, l, h] = v as [number, number, number, number];
                const chg = o ? ((c / o - 1) * 100).toFixed(2) : "0";
                lines.push(
                  `开 ${o.toFixed(2)}　收 ${c.toFixed(2)}　高 ${h.toFixed(2)}　低 ${l.toFixed(2)}　${chg > "0" ? "+" : ""}${chg}%`,
                );
              } else if (p.seriesName === "量能") {
                const vol = typeof v === "object" && v !== null && "value" in v ? (v as { value: number }).value : (v as number);
                lines.push(`量能 ${fmtBig(vol)}`);
              } else if (typeof v === "number" && v) {
                lines.push(`${p.seriesName} ${v.toFixed(2)}`);
              }
            }
            return lines.join("<br/>");
          },
        },
        axisPointer: { link: [{ xAxisIndex: "all" }] },
        grid: [
          { left: 56, right: 34, top: 32, height: "62%" },
          { left: 56, right: 34, top: "72%", height: "18%" },
        ],
        xAxis: [
          {
            type: "category",
            data: d.dates,
            gridIndex: 0,
            axisLine: { lineStyle: { color: "#dfe5ee" } },
            axisLabel: { color: "#7b8494", fontSize: 10 },
            splitLine: { show: false },
          },
          {
            type: "category",
            data: d.dates,
            gridIndex: 1,
            axisLine: { lineStyle: { color: "#dfe5ee" } },
            axisLabel: { show: false },
            splitLine: { show: false },
          },
        ],
        yAxis: [
          {
            scale: true,
            gridIndex: 0,
            axisLine: { show: false },
            axisLabel: { color: "#7b8494", fontSize: 10 },
            splitLine: { lineStyle: { color: "#f0f3f8" } },
          },
          {
            scale: true,
            gridIndex: 1,
            axisLine: { show: false },
            axisLabel: { color: "#7b8494", fontSize: 10 },
            splitLine: { show: false },
          },
        ],
        dataZoom: [
          { type: "inside", xAxisIndex: [0, 1], start: 40, end: 100 },
          {
            type: "slider",
            xAxisIndex: [0, 1],
            bottom: 6,
            height: 18,
            start: 40,
            end: 100,
            borderColor: "#dfe5ee",
            backgroundColor: "transparent",
            textStyle: { color: "#7b8494", fontSize: 10 },
          },
        ],
        series: [
          {
            name: "K线",
            type: "candlestick",
            data: ohlcSeriesData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: isLei
              ? undefined
              : { color: up, color0: down, borderColor: up, borderColor0: down },
            markLine: { silent: true, symbol: "none", data: markLineData },
            markPoint: { silent: false, data: markPointData },
          },
          ...maSeries,
          {
            name: "量能",
            type: "bar",
            data: d.volumes.map((v, i) => ({
              value: v,
              itemStyle: { color: d.volColors[i] ?? "#8aa0bd" },
            })),
            xAxisIndex: 1,
            yAxisIndex: 1,
          },
        ],
      };
}
