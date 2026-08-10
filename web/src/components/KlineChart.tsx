import * as echarts from "echarts/core";
import { BarChart, CandlestickChart, CustomChart, LineChart } from "echarts/charts";
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
  CustomChart,
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
    | "top_line"
    | "highlight_price";
  /** 标记类点击带日期；横线类点击没有日期，用 level 表示价位 */
  date?: string;
  price?: number;
  level?: number;
  structureId?: string;
  structureType?: string;
  colorState?: string;
  pivotDate?: string | null;
  distancePct?: number | null;
  /** 买点分析联动：高亮价位线点击时带回，与对话卡片同 id 双向联动。 */
  annoId?: string;
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
  /** 筹码分布（CYQ）：成交量按价格纵向铺开，看密集支撑/阻力。默认关。 */
  chipDist: boolean;
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
  chipDist: false,
  colorMode: "red_green",
};

/** 买点分析的高亮标注指令。由 DetailPage 根据对话卡片联动驱动。
 *  标注数据全部来自确定性层（review 候选价位 + 主图已有结构标记），
 *  不依赖 LLM 输出坐标。 */
export interface HighlightPriceLine {
  annoId: string; // 与对话卡片同一 id，双向联动
  price: number;
  label: string; // 如「买点① 关键价」「止损」
  color: string;
  kind: "entry" | "stop" | "target"; // 决定线型
}

export interface HighlightSpec {
  /** 高亮价位水平线（买点关键价 / 止损 / 目标）。 */
  priceLines: HighlightPriceLine[];
  /** 要点亮的结构标记 id（底部菱形/B1/C点/颈线/关键波动）。
   *  匹配 ChartPayload 里标记的 structure_id；空则不点亮结构。 */
  structureIds: string[];
  /** true = 其余标记/均线调暗，突出高亮项。 */
  dimOthers: boolean;
}

interface Props {
  payload: ChartPayload;
  display: ChartDisplay;
  onPick?: (pick: MarkPick) => void;
  /** 买点分析联动高亮；不传或 null 则不标注（正常看盘态）。 */
  highlight?: HighlightSpec | null;
  /** 父组件要导出当前图为 PNG 时传入：函数体里执行下载。 */
  onDownload?: (download: () => void) => void;
}

export default function KlineChart({ payload, display, onPick, onDownload, highlight }: Props) {
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
    // 容器尺寸变化（如买点侧栏滑入让主图变窄）也要 resize，否则标注位置错乱
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);

    return () => {
      window.removeEventListener("resize", onResize);
      ro.disconnect();
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
    chart.setOption(buildKlineOption(payload, display, highlight), { notMerge: true });
  }, [payload, display, highlight]);

  return (
    <>
      <div className="kline" ref={ref} />
      {display.chipDist && (
        <div className="chip-legend">
          <span className="chip-leg-item">
            <i className="chip-leg-swatch" style={{ background: "#f59e0b" }} />
            获利盘　价位 ≤ 当前价
          </span>
          <span className="chip-leg-item">
            <i className="chip-leg-swatch" style={{ background: "#6366f1" }} />
            套牢盘　价位高于当前价
          </span>
        </div>
      )}
    </>
  );
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
function buildKlineOption(payload: ChartPayload, display: ChartDisplay, highlight?: HighlightSpec | null) {
    const d = payload;
    const up = d.priceUp;
    const down = d.priceDown;
    // 本站已改为亮色主题，与 Streamlit 研究页一致，因此直接使用后端
    // stateColors（green=#0b9b64 / gray=#8c96a8 / black=#1f2937）——
    // 它本就是为白底设计的，无需再做暗底重映射。
    const stateColors: Record<string, string> = d.stateColors ?? {};

    const markLineData: object[] = [];
    const markPointData: object[] = [];

    // ---- 买点分析联动高亮预处理 ----
    // hl 非空时：priceLines 画亮线（买点关键价/止损/目标），
    // structureIds 点亮命中结构（即使对应开关关也强制显示）。
    // dimOthers=true 时把 K 线/均线/其余标记调暗，突出高亮项。
    const hl = highlight ?? null;
    const hlStructSet = new Set<string>(hl?.structureIds ?? []);
    const hasHl =
      !!hl && (hl.priceLines.length > 0 || hl.structureIds.length > 0);
    const dim = !!(hl && hl.dimOthers && hasHl);
    const DIM_OPACITY = 0.3;

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

    // 高亮命中的水平参考线跳过常规绘制，稍后在高亮块里强制点亮，避免重复
    const lineIsLit = (line: LevelLine): boolean =>
      hasHl && !!line.structure_id && hlStructSet.has(line.structure_id);
    if (display.levels) {
      if (d.b1Line && !lineIsLit(d.b1Line)) pushLine(d.b1Line, "b1_line", "B1", "dashed");
      for (const line of d.bottomLines) if (!lineIsLit(line)) pushLine(line, "bottom_line", "C", "dotted");
      for (const line of d.topLines) if (!lineIsLit(line)) pushLine(line, "top_line", "颈线", "dotted");
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
    {
      let structPoints = buildStructureMarkPoints(d, display);
      if (hasHl && hl!.structureIds.length) {
        // 命中项留给高亮块强制点亮（即使开关关）；这里只画非命中项，避免重复
        structPoints = structPoints.filter(
          (p) => !(p.pick.structureId && hlStructSet.has(p.pick.structureId)),
        );
      }
      markPointData.push(...structPoints);
    }

    // ---- 高亮调暗：已加入的常规标记/参考线统一降透明度 ----
    // 高亮项（价位线/点亮结构/点亮参考线）在下方高亮块才加入，不受此影响。
    if (dim) {
      for (const ml of markLineData) {
        const o = ml as { lineStyle?: Record<string, unknown> };
        o.lineStyle = { ...(o.lineStyle ?? {}), opacity: DIM_OPACITY };
      }
      for (const mp of markPointData) {
        const o = mp as { itemStyle?: Record<string, unknown> };
        o.itemStyle = { ...(o.itemStyle ?? {}), opacity: DIM_OPACITY };
      }
    }

    // ---- 买点高亮：强制点亮命中结构 / 参考线 + 买点价位线 ----
    // 全部数据来自确定性层：structureIds 命中主图已有标记，priceLines 来自
    // review 候选的 key_price / invalidation_price。不取 LLM 坐标。
    if (hasHl && hl) {
      // 取首条价位线的 annoId 作为本组高亮的卡片锚点，点亮的结构/参考线
      // 点击时也带回它，实现「点图上高亮项 → 对话卡片高亮」。
      const hlAnnoId = hl.priceLines[0]?.annoId ?? null;

      // 1) 命中结构菱形/叉：全开重建后筛出，放大点亮（即使原开关关）
      if (hl.structureIds.length) {
        const forced = buildStructureMarkPoints(d, {
          bottomMarks: true,
          topMarks: true,
          invalidatedMarks: true,
        });
        const lit = forced.filter(
          (p) => p.pick.structureId && hlStructSet.has(p.pick.structureId),
        );
        for (const p of lit) {
          markPointData.push({
            ...p,
            symbolSize: p.symbolSize + 7,
            itemStyle: { ...p.itemStyle, opacity: 1 },
            pick: { ...p.pick, annoId: hlAnnoId ?? undefined },
          });
        }
      }

      // 2) 命中水平参考线（B1/C/颈线）：即使 display.levels 关也强制点亮
      const pushLitLine = (
        line: LevelLine,
        kind: MarkPick["kind"],
        labelPrefix: string,
      ) => {
        markLineData.push({
          yAxis: line.yAxis,
          lineStyle: { color: line.color, type: "solid", width: 2.2 },
          label: { show: false },
        });
        if (lastDate) {
          markPointData.push({
            coord: [lastDate, line.yAxis],
            symbol: "circle",
            symbolSize: 13,
            symbolOffset: [16, 0],
            itemStyle: { color: line.color, borderColor: "#ffffff", borderWidth: 2 },
            label: {
              show: true,
              position: "right",
              distance: 14,
              color: line.color,
              fontSize: 10,
              fontWeight: 700,
              formatter: `${labelPrefix} ${line.yAxis.toFixed(2)}`,
              backgroundColor: "rgba(255,255,255,0.92)",
              padding: [1, 3],
              borderRadius: 2,
            },
            pick: {
              kind,
              level: line.yAxis,
              structureId: line.structure_id,
              structureType: line.structure_type,
              annoId: hlAnnoId ?? undefined,
            },
            tooltip: {
              formatter: `${line.label_cn ?? labelPrefix} ${line.yAxis}<br/>点击查看解释`,
            },
          });
        }
      };
      if (d.b1Line && d.b1Line.structure_id && hlStructSet.has(d.b1Line.structure_id))
        pushLitLine(d.b1Line, "b1_line", "B1");
      for (const line of d.bottomLines)
        if (line.structure_id && hlStructSet.has(line.structure_id)) pushLitLine(line, "bottom_line", "C");
      for (const line of d.topLines)
        if (line.structure_id && hlStructSet.has(line.structure_id)) pushLitLine(line, "top_line", "颈线");

      // 3) 买点价位线（关键价/止损/目标）：加粗亮线 + 起点标签 + 可点把手
      for (const pl of hl.priceLines) {
        const lineType =
          pl.kind === "entry" ? "solid" : pl.kind === "stop" ? "dashed" : "dotted";
        const isEntry = pl.kind === "entry";
        markLineData.push({
          yAxis: pl.price,
          lineStyle: {
            color: pl.color,
            type: lineType,
            width: isEntry ? 3 : 2,
            // 入场线加发光，在密集 K 线里也能一眼看到
            shadowBlur: isEntry ? 8 : 0,
            shadowColor: pl.color,
          },
          // 线起点贴一个标签徽章（不只在右端把手），扫一眼就看到价位
          label: {
            show: true,
            position: "insideStartTop",
            color: "#ffffff",
            backgroundColor: pl.color,
            padding: [2, 7],
            borderRadius: 3,
            fontSize: 11,
            fontWeight: 700,
            formatter: `${pl.label} ${pl.price.toFixed(2)}`,
          },
        });
        if (lastDate) {
          markPointData.push({
            coord: [lastDate, pl.price],
            symbol: "circle",
            symbolSize: isEntry ? 14 : 12,
            symbolOffset: [16, 0],
            itemStyle: { color: pl.color, borderColor: "#ffffff", borderWidth: 2 },
            label: {
              show: true,
              position: "right",
              distance: 14,
              color: pl.color,
              fontSize: 11,
              fontWeight: 700,
              formatter: `${pl.label} ${pl.price.toFixed(2)}`,
              backgroundColor: "rgba(255,255,255,0.92)",
              padding: [1, 4],
              borderRadius: 3,
            },
            pick: { kind: "highlight_price", level: pl.price, annoId: pl.annoId },
            tooltip: {
              formatter: `${pl.label} ${pl.price.toFixed(2)}<br/>点击高亮对应买点`,
            },
          });
        }
      }
    }

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
              opacity: dim ? DIM_OPACITY : 0.95,
            },
          };
        })
      : dim
        ? d.ohlc.map((bar) => ({ value: bar, itemStyle: { opacity: DIM_OPACITY } }))
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
        ...(dim ? { opacity: DIM_OPACITY } : {}),
      },
      itemStyle: { color: m.color },
      z: 3,
    }));

    // ---- 筹码峰（CYQ）：成交量按价格纵向分布 ----
    // custom series 共享主图价格轴（yAxisIndex:0），价格自动对齐；绑一个隐藏
    // value x 轴、不进 dataZoom，缩放时间轴时筹码柱不被过滤，只随价格轴范围
    // 裁剪--用户缩到哪段，就看那段价格区间的筹码堆积。
    let chipSeries: object | null = null;
    let chipXAxis: object | null = null;
    if (display.chipDist) {
      const chip = computeChipDistribution(d.ohlc, d.volumes);
      if (chip) {
        const lastClose = d.lastClose ?? d.ohlc[d.ohlc.length - 1]?.[1] ?? 0;
        const { step, maxAmount, buckets } = chip;
        const barW = 0.3; // 筹码峰最大宽度占主图比例
        // 局部峰：比左右邻居量大的桶，取量最大的前 3 个作为密集区高亮标注。
        const peakIdx: number[] = [];
        for (let i = 1; i < buckets.length - 1; i++) {
          if (
            buckets[i].amount > buckets[i - 1].amount &&
            buckets[i].amount > buckets[i + 1].amount
          ) {
            peakIdx.push(i);
          }
        }
        peakIdx.sort((a, b) => buckets[b].amount - buckets[a].amount);
        const peakSet = new Set(peakIdx.slice(0, 3));
        chipSeries = {
          name: "筹码峰",
          type: "custom",
          xAxisIndex: 2,
          yAxisIndex: 0,
          clip: true,
          z: 2,
          renderItem: (params: ChipRenderParams, api: ChipRenderApi) => {
            // price/amount 从闭包取，不进 data 维度--否则全历史价格会污染主图
            // yAxis 的自动 scale，把 K 线压扁。yAxis[0] 仍只算 K 线+均线。
            const { price, amount } = buckets[params.dataIndex] ?? { price: 0, amount: 0 };
            if (!amount) return;
            const cs = params.coordSys;
            const yMid = api.coord([0, price])[1];
            const yTop = api.coord([0, price + step / 2])[1];
            const yBot = api.coord([0, price - step / 2])[1];
            const barH = Math.max(1, Math.abs(yTop - yBot) * 0.92);
            const w = maxAmount > 0 ? (amount / maxAmount) * (cs.width * barW) : 0;
            if (w < 0.5) return;
            const profitable = price <= lastClose;
            const color = profitable ? "#f59e0b" : "#6366f1";

            // 峰值密集区：实色柱 + 贯穿实线 + 价格标签，明显高亮（不用虚线，虚线在 K 线上糊）
            if (peakSet.has(params.dataIndex)) {
              return {
                type: "group",
                children: [
                  {
                    type: "rect",
                    shape: { x: cs.x, y: yMid - barH / 2, width: w, height: barH },
                    style: { fill: color, opacity: 0.9 },
                    silent: true,
                  },
                  {
                    type: "line",
                    shape: { x1: cs.x, y1: yMid, x2: cs.x + cs.width, y2: yMid },
                    style: { stroke: color, lineWidth: 1.3, opacity: 0.7 },
                    silent: true,
                  },
                  {
                    type: "text",
                    style: {
                      text: price.toFixed(2),
                      x: cs.x + cs.width - 3,
                      y: yMid,
                      fill: color,
                      font: "600 10px sans-serif",
                      align: "right",
                      verticalAlign: "middle",
                    },
                    silent: true,
                  },
                ],
              };
            }

            // 普通柱：从左边缘向右，横向渐变（左实右淡）与 K 线柔和过渡
            return {
              type: "rect",
              shape: { x: cs.x, y: yMid - barH / 2, width: w, height: barH },
              style: {
                fill: {
                  type: "linear",
                  x: 0, y: 0, x2: 1, y2: 0,
                  colorStops: [
                    { offset: 0, color },
                    {
                      offset: 1,
                      color: profitable ? "rgba(245,158,11,0.06)" : "rgba(99,102,241,0.06)",
                    },
                  ],
                },
                opacity: 0.55,
              },
              silent: true,
            };
          },
          data: buckets.map(() => ({ value: [0] })),
          tooltip: { show: false },
        };
        chipXAxis = {
          type: "value",
          gridIndex: 0,
          min: 0,
          max: 1,
          show: false,
          axisLine: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        };
      }
    }

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
          ...(chipXAxis ? [chipXAxis] : []),
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
          ...(chipSeries ? [chipSeries] : []),
        ],
      };
}

// ---- 筹码峰计算 ----

/** custom series renderItem 的最小类型（echarts 原始类型导入成本高，按需取字段）。 */
interface ChipRenderParams {
  coordSys: { x: number; y: number; width: number; height: number };
  dataIndex: number;
}
interface ChipRenderApi {
  value: (idx: number) => number;
  coord: (pt: number[]) => number[];
}

/**
 * 筹码分布（CYQ）：把每个交易日的成交量按当日 [low, high] 价格区间均匀
 * 分配到等宽价格桶里累计。纯累计、不衰减--用户要的是「量的纵向展示」，
 * 看哪个价位历史成交堆积多。桶价 ≤ 最新收盘价视为获利盘，否则套牢盘。
 */
function computeChipDistribution(
  ohlc: [number, number, number, number][],
  volumes: number[],
  bucketCount = 80,
): { buckets: { price: number; amount: number }[]; maxAmount: number; step: number } | null {
  if (ohlc.length === 0) return null;
  let lo = Infinity;
  let hi = -Infinity;
  for (const bar of ohlc) {
    if (bar[2] < lo) lo = bar[2];
    if (bar[3] > hi) hi = bar[3];
  }
  if (!(hi > lo) || !isFinite(lo) || !isFinite(hi)) return null;
  const step = (hi - lo) / bucketCount;
  const amounts = new Array<number>(bucketCount).fill(0);
  for (let i = 0; i < ohlc.length; i++) {
    const v = volumes[i] ?? 0;
    const l = ohlc[i][2];
    const h = ohlc[i][3];
    if (v <= 0) continue;
    if (!(h > l)) {
      // 当日一字板/无波动：按收盘价所在桶计入
      const b = Math.min(bucketCount - 1, Math.max(0, Math.floor((ohlc[i][1] - lo) / step)));
      amounts[b] += v;
      continue;
    }
    let b0 = Math.floor((l - lo) / step);
    let b1 = Math.floor((h - lo) / step);
    b0 = Math.min(bucketCount - 1, Math.max(0, b0));
    b1 = Math.min(bucketCount - 1, Math.max(0, b1));
    if (b1 < b0) [b0, b1] = [b1, b0];
    const per = v / (b1 - b0 + 1);
    for (let b = b0; b <= b1; b++) amounts[b] += per;
  }
  let maxAmount = 0;
  for (const a of amounts) if (a > maxAmount) maxAmount = a;
  const buckets = amounts.map((a, b) => ({ price: lo + (b + 0.5) * step, amount: a }));
  return { buckets, maxAmount, step };
}
