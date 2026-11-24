import { priceAxisBounds } from "./agent/priceLinks";
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
import { useEffect, useMemo, useRef, useState } from "react";
import type { ChartPayload, LevelLine } from "../types";
import {
  MARK_DENSE_WINDOW_BARS,
  buildStructureMarkPoints,
  type MarksScope,
} from "./klineStructureMarks";
import { aggregateChartPayload, timeframeLabel, type Timeframe } from "./klineTimeframe";

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
    | "highlight_price"
    | "macd_event"
    | "news_mark";
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
  /** MACD 事件的中文名（金叉/死叉/上穿0轴/下穿0轴），供解释面板标题用。 */
  macdStatusCn?: string;
  /** 消息日标记（news_mark）：当日多空定调与标题列表，供 tooltip/联动。 */
  newsDirection?: string;
  newsTitles?: string[];
  newsImportance?: number;
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
  { key: "ema120", label: "EMA120", color: "#e33d47", dashed: false },
  { key: "sma120", label: "SMA120", color: "#e33d47", dashed: true },
];

/** K 线着色模式。 */
export type ColorMode = "red_green" | "biao_state";

/** 筹码峰计算口径。 */
export type ChipMode = "full" | "decay";

/** 快捷可视时间区间（仅控制默认缩放窗口，用户可随时滚轮/拖动自由缩放）。 */
export type RangePreset = "3M" | "6M" | "1Y" | "ALL";

export const RANGE_PRESET_META: { key: RangePreset; label: string; title: string }[] = [
  { key: "3M", label: "3月", title: "近 3 个月视图，适合细看近期 K 线形态与影线" },
  { key: "6M", label: "6月", title: "近 6 个月视图（默认），兼顾中期趋势与单根清晰度" },
  { key: "1Y", label: "1年", title: "近 1 年视图，观察完整波段与筹码堆积" },
  { key: "ALL", label: "全部", title: "展示后端下发的全部历史 K 线" },
];

/** 按周期与快捷区间解析右对齐的起止索引。 */
export function resolveRangeWindow(n: number, tf: Timeframe, preset: RangePreset): ZoomRange {
  if (n <= 1) return { startValue: 0, endValue: 0 };
  if (preset === "ALL") return { startValue: 0, endValue: n - 1 };
  const barsByTf: Record<Timeframe, Record<Exclude<RangePreset, "ALL">, number>> = {
    D: { "3M": 63, "6M": 126, "1Y": 252 },
    W: { "3M": 14, "6M": 26, "1Y": 52 },
    M: { "3M": 12, "6M": 24, "1Y": 36 },
  };
  const want = barsByTf[tf][preset];
  return { startValue: Math.max(0, n - want), endValue: n - 1 };
}

const STATE_SHORT_CN: Record<string, string> = {
  green: "绿·多头",
  gray: "灰·中性",
  black: "黑·规避",
};

/** 超过该可视根数时对 MACD 交叉标记降密，避免数十个三角/圆圈糊住曲线。 */
const MACD_COMPACT_WINDOW_BARS = 160;
const MACD_COMPACT_RECENT_COUNT = 6;

/**
 * MACD 事件标记样式。红=强度增强方向（A股涨红），绿=强度减弱方向。
 * 金叉/死叉用实心三角（DIF×DEA 交叉）；上/下穿0轴用空心圆（两线排列翻转，
 * 空心与实心区分「排列翻转」和「交叉」两件不同的事）。
 */
const MACD_EVENT_META: Record<
  "golden_cross" | "death_cross" | "zero_cross_up" | "zero_cross_down",
  { symbol: string; rotate: number; color: string; hollow: boolean; legend: string }
> = {
  golden_cross: { symbol: "triangle", rotate: 0, color: "#e33d47", hollow: false, legend: "▲" },
  death_cross: { symbol: "triangle", rotate: 180, color: "#0b9b64", hollow: false, legend: "▼" },
  zero_cross_up: { symbol: "circle", rotate: 0, color: "#e33d47", hollow: true, legend: "○" },
  zero_cross_down: { symbol: "circle", rotate: 0, color: "#0b9b64", hollow: true, legend: "○" },
};

/** 图上标记/参考线的显示开关。默认全关，避免遮挡看盘。 */
export interface ChartDisplay {
  bottomMarks: boolean; // 底部确认菱形（绿/灰=失效）
  topMarks: boolean; // 顶部确认菱形
  invalidatedMarks: boolean; // 结构失效 ×
  keyVolatility: boolean; // 关键性波动竖线与把手
  levels: boolean; // B1 / C 点 / 颈线
  ma: Record<MaKey, boolean>;
  /** 筹码分布（CYQ）：成交量按价格纵向铺开，看密集支撑/阻力。默认开。 */
  chipDist: boolean;
  /**
   * 筹码峰计算口径：
   *   - "full"  全历史（默认，维持原行为：纯累计、不衰减）
   *   - "decay" 衰减模式：成交量按距最新交易日的天数做指数衰减后再入桶，
   *             历史久远的成交权重趋近 0，峰值更偏向近期价位。
   */
  chipMode: ChipMode;
  /** MACD 副图：DIF/DEA 线 + 红绿柱（研究代理强度指标）。默认关。 */
  macd: boolean;
  colorMode: ColorMode;
  /**
   * K 线周期：日（默认，后端原始数据）/ 周 / 月。
   * 周月由前端聚合日线得到，**只是展示视图**：所有日线口径的判定
   * （BIAO 三色、结构标记、参考线、MACD 事件、关键性波动）在聚合视图下
   * 一律隐藏，见 effectiveDisplay。
   */
  timeframe: Timeframe;
  /**
   * 结构标记口径：alive（默认）只画存活结构的确认标记，历史标的数百个
   * 确认/失效标记全画会遮挡 K 线到不可读；all 为研究视角全量铺开。
   * 见 klineStructureMarks.ts 的密度治理。
   */
  marksScope: MarksScope;
}

/**
 * 把用户的开关意图降级成「当前周期下真正生效」的开关。
 *
 * 为什么要派生而不是直接改 display：用户在日线下打开的标记/着色是**意图**，
 * 切到周线只是临时不适用，切回日线必须原样恢复——所以 display 保留原值，
 * 由本函数在渲染侧统一降级。图表与页面图例都用它，保证「图上没画的东西
 * 图例里也不会写」。
 *
 * 周/月线下强制：红涨绿跌着色、无结构标记、无参考线、无关键性波动、无 MACD。
 * MACD 选择「隐藏」而非前端重算：判定权在 Python 规则层（macd_strength），
 * 前端自算会出现与后端口径分叉的两套 MACD。
 */
export function effectiveDisplay(display: ChartDisplay): ChartDisplay {
  if (display.timeframe === "D") return display;
  return {
    ...display,
    colorMode: "red_green",
    bottomMarks: false,
    topMarks: false,
    invalidatedMarks: false,
    keyVolatility: false,
    levels: false,
    macd: false,
  };
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
  chipDist: true, // 默认开筹码峰（CYQ）
  chipMode: "full", // 默认全历史口径（维持原行为：纯累计、不衰减）
  macd: true, // 默认开 MACD 副图
  colorMode: "biao_state", // 默认 BIAO 黑绿灰着色（颜色=当日状态）
  timeframe: "D", // 默认日线；用户选择由 ChartControls 持久化到 localStorage
  marksScope: "alive", // 默认仅存活结构：失效标记是看盘噪音，研究时再切「全部」
};

/** 买点分析的高亮标注指令。由 DetailPage 根据对话卡片联动驱动。
 *  标注数据全部来自确定性层（review 候选价位 + 主图已有结构标记），
 *  不依赖 LLM 输出坐标。 */
export interface HighlightPriceLine {
  annoId: string; // 与对话卡片同一 id，双向联动
  price: number;
  label: string; // 如「买点① 关键价」「止损」
  color: string;
  kind: "entry" | "stop" | "target" | "reference"; // 决定线型
}

export interface HighlightSpec {
  /** 高亮价位水平线（买点关键价 / 止损 / 目标）。 */
  priceLines: HighlightPriceLine[];
  /** 要点亮的结构标记 id（底部菱形/B1/C点/颈线/关键波动）。
   *  匹配 ChartPayload 里标记的 structure_id；空则不点亮结构。 */
  structureIds: string[];
  /** true = 其余标记/均线调暗，突出高亮项。 */
  dimOthers: boolean;
  /** Agent 定位时把参考线纳入纵轴显示范围；默认沿用原来的缩放。 */
  ensureVisible?: boolean;
}

interface Props {
  payload: ChartPayload;
  display: ChartDisplay;
  onPick?: (pick: MarkPick) => void;
  /** 买点分析联动高亮；不传或 null 则不标注（正常看盘态）。 */
  highlight?: HighlightSpec | null;
  /** 父组件要导出当前图为 PNG 时传入：函数体里执行下载。 */
  onDownload?: (download: () => void) => void;
  /** 工具栏触发的快捷视野切换（seq 递增确保重复点击同区间也能复位到最新端）。 */
  rangeRequest?: { preset: RangePreset; seq: number } | null;
  /** 当前默认视野档（切换标的时沿用），默认近 6 个月。 */
  defaultRangePreset?: RangePreset;
  /** 用户手动滚轮/拖动缩放时通知父组件取消快捷按钮高亮。 */
  onRangeCustom?: () => void;
}

export default function KlineChart({
  payload,
  display,
  onPick,
  onDownload,
  highlight,
  rangeRequest,
  defaultRangePreset = "6M",
  onRangeCustom,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  // onPick / onRangeCustom 存进 ref，不进 setOption 的依赖，避免父组件 re-render 导致整图重建。
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;
  const onRangeCustomRef = useRef(onRangeCustom);
  onRangeCustomRef.current = onRangeCustom;
  // 最近一次 setOption 的完整 option：ResizeObserver 里 resize 后重发自愈用
  //（echarts resize 会丢弃尚未完成的分帧渲染，大数据量下主体 K 线不再补画）。
  const lastOptionRef = useRef<ReturnType<typeof buildKlineOption> | null>(null);
  // 容器尺寸缓存与防抖句柄：尺寸没变不动作，变了等布局稳定再 resize+重发
  const lastSizeRef = useRef({ w: 0, h: 0 });
  const resizeTimerRef = useRef(0);
  // 忽略程序内部触发的 dataZoom 事件（避免刚点快捷区间就被误判为手动自定义缩放）
  const suppressCustomZoomRef = useRef(false);

  const tf = display.timeframe;
  const isDaily = tf === "D";
  // 周期视图：日线原样返回同一引用（零开销），周/月聚合出新的 payload。
  // 聚合发生在图表内部，父组件持有的仍是日线 payload——顶栏最新价、
  // 趋势清单等一切页面级展示都不受周期切换影响。
  const view = useMemo(() => aggregateChartPayload(payload, tf), [payload, tf]);
  // 生效开关：周/月线自动隐藏日线专属内容（见 effectiveDisplay）
  const eff = useMemo(() => effectiveDisplay(display), [display]);
  // 12-1 动量序列（Carhart 1997 口径）—— 永远从日线 close 算，聚合视图不重算。
  // 周/月线不显示 12-1：聚合后点数不足 252 根，12-1 无意义。
  const mom121Series = useMemo(
    () => (isDaily ? computeMom121(payload.ohlc) : []),
    [payload, isDaily],
  );
  const mom121Summary = useMemo(() => {
    if (!mom121Series.length) return null;
    const latest = mom121Series[mom121Series.length - 1];
    if (latest == null) return null;
    return {
      value: latest,
      pct: computeMom121PercentileCurrent(mom121Series),
    };
  }, [mom121Series]);

  // 20 期均量线（纯展示参考，用于成交量副图基准线及顶部动态量比读数）
  const volMa20 = useMemo(() => computeRollingMean(view.volumes, 20), [view.volumes]);

  // 筹码分布（CYQ）：主图自定义绘制与底部获利比例/均价统计共用一次计算
  const chipData = useMemo(() => {
    if (!eff.chipDist) return null;
    const halfLifeDays =
      eff.chipMode === "decay"
        ? CHIP_DECAY_HALF_LIFE_DAYS / CHIP_BARS_PER_PERIOD[eff.timeframe]
        : undefined;
    const lastClose = view.lastClose ?? view.ohlc[view.ohlc.length - 1]?.[1] ?? 0;
    return computeChipDistribution(view.ohlc, view.volumes, 80, halfLifeDays, lastClose);
  }, [eff.chipDist, eff.chipMode, eff.timeframe, view.ohlc, view.volumes, view.lastClose]);

  // 买点联动高亮依赖日线结构标记，聚合视图下一并停用
  const effHighlight = isDaily ? highlight ?? null : null;

  // 结构标记降密档：可视窗口 > MARK_DENSE_WINDOW_BARS 根时进入。
  // MACD 事件降密档：可视窗口 > MACD_COMPACT_WINDOW_BARS 根时仅保留最近 6 个事件。
  const [dense, setDense] = useState(false);
  const denseRef = useRef(false);
  const [macdCompact, setMacdCompact] = useState(false);
  const macdCompactRef = useRef(false);

  // 顶部动态读数栏当前索引（null = 展示最新一根）
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const hoverIdxRef = useRef<number | null>(null);

  // 切换标的或周期时，悬停索引回落到最新一根
  useEffect(() => {
    hoverIdxRef.current = null;
    setHoverIdx(null);
  }, [payload.symbol, tf]);

  // init 只跑一次：创建实例 + 绑定不变的 click/resize/axisPointer 监听。
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

    // 十字光标联动顶部动态读数栏（只在实际换根时 setState，不触发 ECharts 重绘）
    const onAxisPointer = (ev: { axesInfo?: Array<{ axisDim?: string; value?: number }> }) => {
      const xInfo = ev?.axesInfo?.find((a) => a.axisDim === "x" && typeof a.value === "number");
      if (!xInfo || typeof xInfo.value !== "number") return;
      const next = Math.round(xInfo.value);
      if (next !== hoverIdxRef.current) {
        hoverIdxRef.current = next;
        setHoverIdx(next);
      }
    };
    const onGlobalOut = () => {
      if (hoverIdxRef.current !== null) {
        hoverIdxRef.current = null;
        setHoverIdx(null);
      }
    };
    chart.on("updateAxisPointer", onAxisPointer as (params: unknown) => void);
    chart.on("globalout", onGlobalOut);

    // dataZoom 吸附：拖拽/滚轮缩放时把窗口起止索引取整回写，使边缘始终对齐
    // 到「整根 K 线」，不出现半根蜡烛、也不在极细缩放时漂离数据顶点。若当前
    // 已是整数索引则跳过，避免 setOption 触发 dataZoom 事件造成死循环。
    const onDataZoom = (ev: {
      startValue?: number;
      endValue?: number;
      batch?: Array<{ startValue?: number; endValue?: number }>;
    }) => {
      const batches = Array.isArray(ev?.batch) ? ev.batch! : [ev];
      let s: number | null = null;
      let e: number | null = null;
      for (const b of batches) {
        if (b.startValue != null && b.endValue != null) {
          const rs = Math.round(b.startValue);
          const re = Math.round(b.endValue);
          // 取跨度最大的一段（inside 与 slider 可能同时派发）
          if (s === null || re - rs > e! - s!) {
            s = rs;
            e = re;
          }
        }
      }
      if (s === null || e === null) return;
      // getOption() 在首次 setOption 前返回 undefined，必须可选链兜底
      const cur = (chart.getOption()?.dataZoom as Array<{ startValue?: number; endValue?: number }> | undefined) ?? [];
      const c0 = cur[0];
      const alreadyInt =
        c0 && c0.startValue != null && c0.endValue != null &&
        Number.isInteger(c0.startValue) && Number.isInteger(c0.endValue);
      if (!alreadyInt) {
        suppressCustomZoomRef.current = true;
        chart.setOption({
          dataZoom: [
            { startValue: s, endValue: e },
            { startValue: s, endValue: e },
          ],
        });
        suppressCustomZoomRef.current = false;
      }
      if (!suppressCustomZoomRef.current) {
        onRangeCustomRef.current?.();
      }
      // 降密档位检测：窗口跨度跨过阈值才翻转一次 state，触发 setOption 重过滤。
      const span = e - s;
      const nowDense = span > MARK_DENSE_WINDOW_BARS;
      if (nowDense !== denseRef.current) {
        denseRef.current = nowDense;
        setDense(nowDense);
      }
      const nowMacdCompact = span > MACD_COMPACT_WINDOW_BARS;
      if (nowMacdCompact !== macdCompactRef.current) {
        macdCompactRef.current = nowMacdCompact;
        setMacdCompact(nowMacdCompact);
      }
    };
    chart.on("dataZoom", onDataZoom as (params: unknown) => void);

    const onResize = () => scheduleSelfHealingResize();
    window.addEventListener("resize", onResize);
    // 容器尺寸变化（如买点侧栏滑入让主图变窄、骨架屏切换、字体加载后的布局微调）
    // 也要 resize，否则标注位置错乱。
    //
    // 修复（2026-09-05）：echarts 的 resize() 会丢弃尚未完成的分帧渲染，大数据量
    // 标的（如科创50 指数）首帧渲染窗口内被 resize 打断后，K 线/均线/MACD 主体
    // 永不补画，页面上表现为「只剩信号标签飘在空白图上」。因此尺寸变化时在
    // resize 之后补发一次完整 option（notMerge）；补发前读出当前 dataZoom 窗口
    // 写回，不重置用户缩放位置。防抖 80ms 等布局稳定，拖拽分栏时不连续重发。
    const scheduleSelfHealingResize = () => {
      const el = ref.current;
      const chart2 = chartRef.current;
      if (!el || !chart2) return;
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (w === lastSizeRef.current.w && h === lastSizeRef.current.h) return;
      lastSizeRef.current = { w, h };
      window.clearTimeout(resizeTimerRef.current);
      resizeTimerRef.current = window.setTimeout(() => {
        const c = chartRef.current;
        if (!c) return;
        c.resize();
        const opt = lastOptionRef.current;
        if (!opt) return;
        const dz = (
          c.getOption()?.dataZoom as
            Array<{ startValue?: number; endValue?: number }> | undefined
        )?.[0];
        const patch: { dataZoom?: Array<{ startValue?: number; endValue?: number }> } = {};
        if (
          dz && dz.startValue != null && dz.endValue != null &&
          Array.isArray(opt.dataZoom)
        ) {
          patch.dataZoom = opt.dataZoom.map((z) => ({
            ...z,
            startValue: Math.round(dz.startValue!),
            endValue: Math.round(dz.endValue!),
          }));
        }
        c.setOption({ ...opt, ...patch }, { notMerge: true });
      }, 80);
    };
    const ro = new ResizeObserver(() => scheduleSelfHealingResize());
    if (ref.current) {
      lastSizeRef.current = { w: ref.current.clientWidth, h: ref.current.clientHeight };
      ro.observe(ref.current);
    }

    return () => {
      window.removeEventListener("resize", onResize);
      window.clearTimeout(resizeTimerRef.current);
      ro.disconnect();
      chart.off("click", onClick as (params: unknown) => void);
      chart.off("mouseover", onOver as (params: unknown) => void);
      chart.off("mouseout");
      chart.off("updateAxisPointer", onAxisPointer as (params: unknown) => void);
      chart.off("globalout", onGlobalOut);
      chart.off("dataZoom", onDataZoom as (params: unknown) => void);
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
      // 文件名带周期后缀，导出周/月线不会与日线图混淆
      const tfTag = isDaily ? "" : `-${tf === "W" ? "weekly" : "monthly"}`;
      a.download = `${payload.symbol}-kline${tfTag}-${new Date().toISOString().slice(0, 10)}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
  }, [onDownload, payload.symbol, tf, isDaily]);

  // 响应工具栏快捷时间区间切换（3月 / 6月 / 1年 / 全部）
  const lastRangeSeqRef = useRef<number>(0);
  useEffect(() => {
    if (!rangeRequest || rangeRequest.seq === lastRangeSeqRef.current) return;
    lastRangeSeqRef.current = rangeRequest.seq;
    const chart = chartRef.current;
    const n = view.dates.length;
    if (!chart || n === 0) return;
    const nextWin = resolveRangeWindow(n, tf, rangeRequest.preset);
    suppressCustomZoomRef.current = true;
    chart.setOption({
      dataZoom: [
        { startValue: nextWin.startValue, endValue: nextWin.endValue },
        { startValue: nextWin.startValue, endValue: nextWin.endValue },
      ],
    });
    suppressCustomZoomRef.current = false;
    const span = nextWin.endValue - nextWin.startValue;
    const nowDense = span > MARK_DENSE_WINDOW_BARS;
    if (nowDense !== denseRef.current) {
      denseRef.current = nowDense;
      setDense(nowDense);
    }
    const nowMacdCompact = span > MACD_COMPACT_WINDOW_BARS;
    if (nowMacdCompact !== macdCompactRef.current) {
      macdCompactRef.current = nowMacdCompact;
      setMacdCompact(nowMacdCompact);
    }
  }, [rangeRequest, tf, view.dates.length]);

  // setOption 独立 effect：data/开关变化时只更新 option，不销毁实例，
  // 保留同标的下用户当前缩放位置，不闪烁。切换标的时按当前默认视野右对齐到最新日。
  const lastRenderRef = useRef<{ symbol: string; tf: Timeframe; n: number } | null>(null);
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const prev = lastRenderRef.current;
    const n = view.dates.length;
    const symbolChanged = !prev || prev.symbol !== payload.symbol;
    let zoom: ZoomRange | null = null;
    if (!symbolChanged) {
      const curDz = (chart.getOption()?.dataZoom as Array<{ startValue?: number; endValue?: number }> | undefined) ?? [];
      const z0 = curDz[0];
      zoom =
        z0 && z0.startValue != null && z0.endValue != null
          ? { startValue: Math.round(z0.startValue), endValue: Math.round(z0.endValue) }
          : null;
      if (zoom && prev && prev.tf !== tf && prev.n > 1 && n > 1) {
        const k = (n - 1) / (prev.n - 1);
        zoom = {
          startValue: Math.round(zoom.startValue * k),
          endValue: Math.round(zoom.endValue * k),
        };
      }
    }
    const effectiveZoom = zoom ?? resolveRangeWindow(n, tf, defaultRangePreset);
    const span = effectiveZoom.endValue - effectiveZoom.startValue;
    const initDense = span > MARK_DENSE_WINDOW_BARS;
    const initMacdCompact = span > MACD_COMPACT_WINDOW_BARS;
    denseRef.current = initDense;
    macdCompactRef.current = initMacdCompact;

    lastRenderRef.current = { symbol: payload.symbol, tf, n };
    const option = buildKlineOption(
      view,
      eff,
      effHighlight,
      effectiveZoom,
      initDense,
      initMacdCompact,
      chipData,
      volMa20,
    );
    lastOptionRef.current = option;
    chart.setOption(option, { notMerge: true });
  }, [view, eff, effHighlight, tf, dense, macdCompact, payload.symbol, defaultRangePreset, chipData, volMa20]);

  // 键盘平移：←/→ 一根，Shift+←/→ 半屏。与 ↑/↓ 切标的（WorkspacePage）互补，
  // 凑齐键盘看盘。只改 dataZoom 窗口（整根索引，天然满足吸附），不重建 series。
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      // 输入控件里（搜索框 / 回放日期选择器）不抢按键
      const t = e.target as HTMLElement | null;
      if (
        t &&
        (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)
      )
        return;
      const chart = chartRef.current;
      if (!chart) return;
      const n = view.dates.length;
      if (n === 0) return;
      const dz = (chart.getOption()?.dataZoom as Array<{ startValue?: number; endValue?: number }> | undefined)?.[0];
      if (!dz || dz.startValue == null || dz.endValue == null) return;
      const span = Math.round(dz.endValue) - Math.round(dz.startValue);
      if (span <= 0) return;
      // Shift 半屏（至少 5 根）；普通一根
      const step = e.shiftKey ? Math.max(5, Math.round(span / 2)) : 1;
      const dirSign = e.key === "ArrowLeft" ? -1 : 1;
      let s = Math.round(dz.startValue) + step * dirSign;
      let en = Math.round(dz.endValue) + step * dirSign;
      if (s < 0) { en -= s; s = 0; }
      if (en > n - 1) { s -= en - (n - 1); en = n - 1; }
      if (s < 0 || en <= s) return;
      e.preventDefault();
      chart.setOption({ dataZoom: [{ startValue: s, endValue: en }, { startValue: s, endValue: en }] });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view.dates.length]);

  // ---- 顶部动态读数栏计算（默认最新一根，光标滑过实时联动）----
  const activeIdx =
    view.dates.length > 0
      ? Math.max(0, Math.min(view.dates.length - 1, hoverIdx ?? view.dates.length - 1))
      : -1;
  const activeBar = activeIdx >= 0 ? view.ohlc[activeIdx] : null;
  const activeDate = activeIdx >= 0 ? view.dates[activeIdx] : null;
  const prevClose = activeIdx > 0 ? view.ohlc[activeIdx - 1]?.[1] ?? null : null;
  const activeChgPct =
    activeBar && prevClose && prevClose > 0 ? ((activeBar[1] / prevClose) - 1) * 100 : null;
  const activeChgColor =
    activeChgPct == null
      ? undefined
      : activeChgPct > 0
        ? view.priceUp
        : activeChgPct < 0
          ? view.priceDown
          : undefined;
  const activeVol = activeIdx >= 0 ? view.volumes[activeIdx] : null;
  const activeVolMa = activeIdx >= 0 ? volMa20[activeIdx] : null;
  const activeVolRatio =
    activeVol != null && activeVolMa != null && activeVolMa > 0 ? activeVol / activeVolMa : null;
  const activeState = isDaily && activeIdx >= 0 ? view.states[activeIdx] ?? "unknown" : null;
  const activeStateColor = activeState ? (view.stateColors ?? {})[activeState] : undefined;
  const activeStateLabel = activeState ? STATE_SHORT_CN[activeState] : null;
  const activeMas = MA_META.filter((m) => eff.ma[m.key]);
  const showSymbolCode =
    payload.displayName &&
    payload.symbol &&
    !payload.displayName.toUpperCase().includes(payload.symbol.toUpperCase());

  return (
    <>
      {activeBar && (
        <div className="kline-hud" aria-label="当前光标行情与均线读数">
          <div className="kline-hud-main">
            <span className="kline-hud-id">
              <strong>{payload.displayName || payload.symbol}</strong>
              {showSymbolCode && <small className="kline-hud-code">{payload.symbol}</small>}
            </span>
            {activeDate && <span className="kline-hud-date">{activeDate}</span>}
            {activeStateLabel && activeStateColor && (
              <span className="kline-hud-state" title="当日 BIAO 道路状态">
                <i style={{ background: activeStateColor }} />
                {activeStateLabel}
              </span>
            )}
            <span className="kline-hud-ohlc">
              <span>开 <b>{activeBar[0].toFixed(2)}</b></span>
              <span>高 <b>{activeBar[3].toFixed(2)}</b></span>
              <span>低 <b>{activeBar[2].toFixed(2)}</b></span>
              <span>收 <b style={activeChgColor ? { color: activeChgColor } : undefined}>{activeBar[1].toFixed(2)}</b></span>
              {activeChgPct != null && (
                <b className="kline-hud-chg" style={activeChgColor ? { color: activeChgColor } : undefined}>
                  {activeChgPct > 0 ? "+" : ""}{activeChgPct.toFixed(2)}%
                </b>
              )}
              {activeVol != null && (
                <span className="kline-hud-vol">
                  量 <b>{fmtBig(activeVol)}</b>
                  {activeVolRatio != null && <small>({activeVolRatio.toFixed(1)}×)</small>}
                </span>
              )}
            </span>
          </div>
          <div className="kline-hud-meta">
            {activeMas.map((m) => {
              const v = activeIdx >= 0 ? view[m.key][activeIdx] : null;
              return (
                <span key={m.key} className="kline-hud-ma" style={{ color: m.color }}>
                  <i className={`kline-hud-line${m.dashed ? " dashed" : ""}`} style={{ borderColor: m.color }} />
                  {m.label} <b>{v != null ? v.toFixed(2) : "—"}</b>
                </span>
              );
            })}
            {mom121Summary && (
              <span
                className="kline-hud-mom"
                title="中期动量：近一年剔除最近一个月的累计涨跌幅，及其在自身历史里的百分位位置（纯时间尺度参考，不直接做买卖判定）"
              >
                中期动量{" "}
                <b style={{ color: mom121Summary.value >= 0 ? view.priceUp : view.priceDown }}>
                  {mom121Summary.value >= 0 ? "+" : ""}
                  {(mom121Summary.value * 100).toFixed(1)}%
                </b>
                {mom121Summary.pct != null && (
                  <small>（历史 {mom121Summary.pct.toFixed(0)}% 分位）</small>
                )}
              </span>
            )}
          </div>
        </div>
      )}
      <div className="kline" ref={ref} />
      {!isDaily && (
        <div className="chip-legend tf-note">
          <span className="chip-leg-item">
            {timeframeLabel(tf)}线为日线聚合视图，仅展示价格与均线，BIAO 状态与日线结构标记自动隐藏
          </span>
        </div>
      )}
      {isDaily && dense && (eff.bottomMarks || eff.topMarks) && (
        <div className="chip-legend tf-note">
          <span className="chip-leg-item">
            当前区间较长：远端已失效标记已自动精简，存活结构完整保留；放大区间可查看全量
          </span>
        </div>
      )}
      {(eff.chipDist || eff.macd) && (
        <div className="kline-sub-legend">
          {eff.chipDist && (
            <div className="ksl-group">
              <span className="chip-leg-item">
                <i className="chip-leg-swatch" style={{ background: "#e36b1c" }} />
                获利盘{chipData?.profitRatioPct != null ? ` ${chipData.profitRatioPct.toFixed(0)}%` : ""}
              </span>
              <span className="chip-leg-item">
                <i className="chip-leg-swatch" style={{ background: "#6366f1" }} />
                套牢盘
              </span>
              {chipData?.avgCost != null && (
                <span className="chip-leg-item ksl-stat" title="按当前口径累计筹码加权估算的平均持仓成本">
                  筹码均价 <b>{chipData.avgCost.toFixed(2)}</b>
                </span>
              )}
              {eff.chipMode === "decay" && (
                <span className="chip-leg-item ksl-tag">衰减半衰期 {CHIP_DECAY_HALF_LIFE_DAYS}日</span>
              )}
            </div>
          )}
          {eff.macd && (
            <div className="ksl-group" title="MACD 表达均线扩散/密集的强弱程度（研究代理），不单独作买卖点">
              <span className="ksl-label">MACD 强度</span>
              <span className="chip-leg-item" style={{ color: MACD_EVENT_META.golden_cross.color }}>▲金叉</span>
              <span className="chip-leg-item" style={{ color: MACD_EVENT_META.death_cross.color }}>▼死叉</span>
              <span className="chip-leg-item" style={{ color: MACD_EVENT_META.zero_cross_up.color }}>○穿0上</span>
              <span className="chip-leg-item" style={{ color: MACD_EVENT_META.zero_cross_down.color }}>○穿0下</span>
              <span className="ksl-note">研究代理 · 仅看强弱</span>
            </div>
          )}
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
/** 当前缩放区间（数据索引），跨 setOption 续接用，避免 notMerge 把缩放位置重置。 */
interface ZoomRange {
  startValue: number;
  endValue: number;
}

function buildKlineOption(
  payload: ChartPayload,
  display: ChartDisplay,
  highlight?: HighlightSpec | null,
  zoom?: ZoomRange | null,
  dense = false,
  macdCompact = false,
  chipData?: ChipDistributionResult | null,
  volMa20?: (number | null)[],
) {
    const d = payload;
    const up = d.priceUp;
    const down = d.priceDown;
    const showMacd = display.macd;
    const isDaily = display.timeframe === "D";
    const lastClose = d.lastClose ?? d.ohlc[d.ohlc.length - 1]?.[1] ?? null;
    const prevClose = d.ohlc.length >= 2 ? d.ohlc[d.ohlc.length - 2]?.[1] ?? null : null;
    const lastCloseColor =
      lastClose != null && prevClose != null
        ? lastClose >= prevClose
          ? up
          : down
        : "#2458c6";
    // 筹码 value 轴排在所有 category 轴之后：开 MACD 时占 index 3，否则 2。
    const chipXAxisIndex = showMacd ? 3 : 2;
    // 本站已改为亮色主题，与 Streamlit 研究页一致，因此直接使用后端
    // stateColors（green=#0b9b64 / gray=#8c96a8 / black=#1f2937）——
    // 它本就是为白底设计的，无需再做暗底重映射。
    const stateColors: Record<string, string> = d.stateColors ?? {};

    const markLineData: object[] = [];
    const markPointData: object[] = [];

    // 格式化相对最新价的空间百分比（如「+17.7%」「-1.0%」）
    const fmtDistPct = (price: number): string => {
      if (!lastClose || lastClose <= 0) return "";
      const pct = ((price / lastClose) - 1) * 100;
      return ` (${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%)`;
    };

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

    // ---- 最新价参考水平虚线 + 右轴高亮价格标签 ----
    if (lastClose != null && Number.isFinite(lastClose)) {
      markLineData.push({
        yAxis: lastClose,
        lineStyle: { color: lastCloseColor, type: "dashed", width: 0.9, opacity: 0.48 },
        label: {
          show: true,
          position: "end",
          distance: 4,
          formatter: lastClose.toFixed(2),
          color: "#ffffff",
          backgroundColor: lastCloseColor,
          padding: [2, 5],
          borderRadius: 2,
          fontSize: 10,
          fontWeight: 600,
        },
      });
    }

    // ---- 水平参考线（B1 / C 点 / 顶部颈线）----
    // 价格轴已右置，可点圆点贴在最新日内缘，标签向左展开并带距现价百分比，避免与右轴重叠。
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
        label: { show: false },
      });
      if (lastDate) {
        markPointData.push({
          coord: [lastDate, line.yAxis],
          symbol: "circle",
          symbolSize: 10,
          symbolOffset: [0, 0],
          itemStyle: { color: line.color, borderColor: "#ffffff", borderWidth: 1.5 },
          label: {
            show: true,
            position: "left",
            distance: 8,
            color: line.color,
            fontSize: 10,
            fontWeight: 600,
            formatter: `${labelPrefix} ${line.yAxis.toFixed(2)}${fmtDistPct(line.yAxis)}`,
            backgroundColor: "rgba(255,255,255,0.92)",
            borderColor: line.color,
            borderWidth: 0.6,
            padding: [1, 4],
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
            formatter: `${line.label_cn ?? labelPrefix} ${line.yAxis}${fmtDistPct(line.yAxis)}<br/>点击查看解释`,
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
    // dense（可视窗口 >600 根）时远端非存活标记截断，见 klineStructureMarks。
    {
      let structPoints = buildStructureMarkPoints(d, display, dense);
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

      // 1) 命中结构菱形/叉：全开重建后筛出，放大点亮（即使原开关关）。
      //    强制点亮不受 marksScope/dense 限制——要点亮的结构由确定性层
      //    点名，数量极少，且用户正在等它出现。
      if (hl.structureIds.length) {
        const forced = buildStructureMarkPoints(
          d,
          {
            bottomMarks: true,
            topMarks: true,
            invalidatedMarks: true,
            marksScope: "all",
          },
          false,
        );
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
            symbolSize: 12,
            symbolOffset: [0, 0],
            itemStyle: { color: line.color, borderColor: "#ffffff", borderWidth: 2 },
            label: {
              show: true,
              position: "left",
              distance: 8,
              color: line.color,
              fontSize: 10,
              fontWeight: 700,
              formatter: `${labelPrefix} ${line.yAxis.toFixed(2)}${fmtDistPct(line.yAxis)}`,
              backgroundColor: "rgba(255,255,255,0.95)",
              borderColor: line.color,
              borderWidth: 0.8,
              padding: [1, 4],
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
              formatter: `${line.label_cn ?? labelPrefix} ${line.yAxis}${fmtDistPct(line.yAxis)}<br/>点击查看解释`,
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
          pl.kind === "entry" || pl.kind === "reference" ? "solid" : pl.kind === "stop" ? "dashed" : "dotted";
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
            formatter: `${pl.label} ${pl.price}${fmtDistPct(pl.price)}`,
          },
        });
        if (lastDate) {
          markPointData.push({
            coord: [lastDate, pl.price],
            symbol: "circle",
            symbolSize: isEntry ? 13 : 11,
            symbolOffset: [0, 0],
            itemStyle: { color: pl.color, borderColor: "#ffffff", borderWidth: 2 },
            label: {
              show: true,
              position: "left",
              distance: 8,
              color: pl.color,
              fontSize: 11,
              fontWeight: 700,
              formatter: `${pl.label} ${pl.price}`,
              backgroundColor: "rgba(255,255,255,0.95)",
              padding: [1, 4],
              borderRadius: 3,
            },
            pick: { kind: "highlight_price", level: pl.price, annoId: pl.annoId },
            tooltip: {
              formatter: `${pl.label.replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]!))} ${pl.price}${fmtDistPct(pl.price)}<br/>系统参考价位`,
            },
          });
        }
      }
    }

    // ---- K 线着色 ----
    // red_green：中国惯例红涨绿跌，看涨跌用。
    // biao_state：按当日 BIAO 三色（绿/灰/黑）着色，看信号状态段落用。
    //            此模式**不**用空心/实心区分涨跌——颜色只表达「当日状态」，
    //            涨跌方向需另看今日概述里的"开/高/低/收"四项，混在 K 线里
    //            会让本就低调的黑灰绿更看不清。
    const isBiao = display.colorMode === "biao_state";
    const ohlcSeriesData = isBiao
      ? d.ohlc.map((bar, i) => {
          // BIAO 模式：颜色只表达「当日状态（绿/灰/黑）」，
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
        width: m.key === "ema20" ? 1.6 : 1.25,
        color: m.color,
        // 同色的 SMA 走清晰短虚线，与实线 EMA 拉开视觉层次
        type: m.dashed ? ([4, 3] as [number, number]) : ("solid" as const),
        opacity: dim ? DIM_OPACITY : m.dashed ? 0.78 : 0.95,
      },
      itemStyle: { color: m.color },
      z: 3,
    }));

    // ---- 双 20 均线趋势云带（EMA20 与 SMA20 同时开启时铺淡色带）----
    // 一眼分清快线（EMA20）在慢线（SMA20）上方还是下方、粘合还是发散。
    const maRibbonSeries: object | null =
      display.ma.ema20 && display.ma.sma20
        ? {
            name: "双20云带",
            type: "custom",
            xAxisIndex: 0,
            yAxisIndex: 0,
            clip: true,
            silent: true,
            z: 1,
            tooltip: { show: false },
            data: d.ema20.map((v, i) => [i, v ?? d.ohlc[i]?.[1] ?? null]),
            renderItem: (params: ChipRenderParams, api: ChipRenderApi) => {
              const i = params.dataIndex;
              if (i <= 0) return;
              const e0 = d.ema20[i - 1];
              const s0 = d.sma20[i - 1];
              const e1 = d.ema20[i];
              const s1 = d.sma20[i];
              if (e0 == null || s0 == null || e1 == null || s1 == null) return;
              const pE0 = api.coord([i - 1, e0]);
              const pS0 = api.coord([i - 1, s0]);
              const pE1 = api.coord([i, e1]);
              const pS1 = api.coord([i, s1]);
              const bullish = e1 >= s1;
              return {
                type: "polygon",
                shape: { points: [pE0, pE1, pS1, pS0] },
                style: {
                  fill: bullish
                    ? dim
                      ? "rgba(37,99,235,0.03)"
                      : "rgba(37,99,235,0.09)"
                    : dim
                      ? "rgba(100,116,139,0.03)"
                      : "rgba(100,116,139,0.11)",
                },
                silent: true,
              };
            },
          }
        : null;

    // ---- 底部 BIAO 道路状态细色带（日线专属）----
    // 无论选用「红涨绿跌」还是「BIAO 绿灰黑」，底部 4px 细带始终呈现连续趋势段落，
    // 解决红涨绿跌看不到道路状态、绿灰黑看不到阴阳实体的二选一割裂。
    const stateStripSeries: object | null = isDaily
      ? {
          name: "道路状态带",
          type: "custom",
          xAxisIndex: 0,
          yAxisIndex: 0,
          clip: true,
          silent: true,
          z: 2,
          tooltip: { show: false },
          // y 借用当日收盘价（天然在 K 线区间内），绝不拉偏价格轴刻度
          data: d.ohlc.map((bar, i) => [i, bar[1]]),
          renderItem: (params: ChipRenderParams, api: ChipRenderApi) => {
            const i = params.dataIndex;
            const st = d.states[i];
            const fill = st ? stateColors[st] : undefined;
            if (!fill) return;
            const cs = params.coordSys;
            const cx = api.coord([i, d.ohlc[i][1]])[0];
            const stepW = Math.max(1, api.size([1, 0])[0]);
            return {
              type: "rect",
              shape: {
                x: cx - stepW / 2,
                y: cs.y + cs.height - 4.5,
                width: Math.max(1, stepW + 0.5),
                height: 4,
              },
              style: { fill, opacity: dim ? 0.25 : 0.85 },
              silent: true,
            };
          },
        }
      : null;

    // ---- 筹码峰（CYQ）：成交量按价格纵向分布，贴右侧价格轴展示 ----
    // custom series 共享主图价格轴（yAxisIndex:0），价格自动对齐；绑一个隐藏
    // value x 轴、不进 dataZoom，缩放时间轴时筹码柱不被过滤，只随价格轴范围裁剪。
    let chipSeries: object | null = null;
    let chipXAxis: object | null = null;
    if (display.chipDist && chipData) {
      const refClose = lastClose ?? d.ohlc[d.ohlc.length - 1]?.[1] ?? 0;
      const { step, maxAmount, buckets } = chipData;
      const barW = 0.22; // 筹码峰最大宽度收敛至 22%，贴右轴不压主图
      // 局部峰：按量降序挑选最多 3 个，同时保证峰间至少间隔 4.5% 桶距避免标签打架
      const peakCand: number[] = [];
      for (let i = 1; i < buckets.length - 1; i++) {
        if (
          buckets[i].amount > buckets[i - 1].amount &&
          buckets[i].amount > buckets[i + 1].amount
        ) {
          peakCand.push(i);
        }
      }
      peakCand.sort((a, b) => buckets[b].amount - buckets[a].amount);
      const minBucketGap = Math.max(3, Math.round(buckets.length * 0.045));
      const pickedPeaks: number[] = [];
      for (const idx of peakCand) {
        if (pickedPeaks.length >= 3) break;
        if (pickedPeaks.every((p) => Math.abs(p - idx) >= minBucketGap)) {
          pickedPeaks.push(idx);
        }
      }
      const peakSet = new Set(pickedPeaks);
      chipSeries = {
        name: "筹码峰",
        type: "custom",
        xAxisIndex: chipXAxisIndex,
        yAxisIndex: 0,
        clip: true,
        z: 2,
        renderItem: (params: ChipRenderParams, api: ChipRenderApi) => {
          const { price, amount } = buckets[params.dataIndex] ?? { price: 0, amount: 0 };
          if (!amount) return;
          const cs = params.coordSys;
          const yMid = api.coord([0, price])[1];
          const yTop = api.coord([0, price + step / 2])[1];
          const yBot = api.coord([0, price - step / 2])[1];
          const barH = Math.max(1, Math.abs(yTop - yBot) * 0.9);
          const w = maxAmount > 0 ? (amount / maxAmount) * (cs.width * barW) : 0;
          if (w < 0.5) return;
          const profitable = price <= refClose;
          const color = profitable ? "#e36b1c" : "#6366f1";
          const xRight = cs.x + cs.width - w;

          // 峰值密集区：右置实色柱 + 克制虚线 + 智能避让语义标签（远离现价贴右侧筹码峰空白区，贴近现价放左侧避开最新 K 线）
          if (peakSet.has(params.dataIndex)) {
            const peakTag = `${profitable ? "获利峰" : "套牢峰"} ${price.toFixed(2)}${fmtDistPct(price)}`;
            const yLabel = Math.max(cs.y + 10, Math.min(cs.y + cs.height - 16, yMid - 8));
            const farFromCurrent = refClose > 0 && Math.abs(price - refClose) / refClose > 0.06;
            return {
              type: "group",
              children: [
                {
                  type: "rect",
                  shape: { x: xRight, y: yMid - barH / 2, width: w, height: barH },
                  style: { fill: color, opacity: 0.82 },
                  silent: true,
                },
                {
                  type: "line",
                  shape: { x1: cs.x, y1: yMid, x2: cs.x + cs.width, y2: yMid },
                  style: { stroke: color, lineWidth: 1, lineDash: [3, 3], opacity: 0.45 },
                  silent: true,
                },
                {
                  type: "text",
                  style: {
                    text: peakTag,
                    x: farFromCurrent ? cs.x + cs.width - 4 : cs.x + 6,
                    y: yLabel,
                    fill: color,
                    backgroundColor: "rgba(255,255,255,0.9)",
                    padding: [1, 4],
                    borderRadius: 2,
                    font: "600 9.5px sans-serif",
                    align: farFromCurrent ? "right" : "left",
                    verticalAlign: "middle",
                  },
                  silent: true,
                },
              ],
            };
          }

          // 普通柱：从右侧价格轴向左淡出，与最新 K 线无缝对照
          return {
            type: "rect",
            shape: { x: xRight, y: yMid - barH / 2, width: w, height: barH },
            style: {
              fill: {
                type: "linear",
                x: 1, y: 0, x2: 0, y2: 0,
                colorStops: [
                  { offset: 0, color },
                  {
                    offset: 1,
                    color: profitable ? "rgba(227,107,28,0.05)" : "rgba(99,102,241,0.05)",
                  },
                ],
              },
              opacity: 0.42,
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

    // ---- K 线消息日标记（参考层，非交易信号）----
    // 后端 news_marks 把该标的 importance≥6 的消息按交易日聚合；前端只渲染，
    // 不自算。菱形贴在当日 K 线最高价上方：红=利多↑ 绿=利空↓（中国惯例配色）。
    const NEWS_MARK_COLOR: Record<string, string> = {
      bullish: "#e33d47",
      bearish: "#0b9b64",
      neutral: "#8a93a3",
    };
    const newsMarkPoints = (d.newsMarks ?? [])
      .map((m) => {
        const i = d.dates.indexOf(m.date);
        const high = i >= 0 ? d.ohlc[i]?.[3] : undefined;
        if (high == null) return null; // 对不上交易日/K线数据就不打点
        const color = NEWS_MARK_COLOR[m.direction] ?? NEWS_MARK_COLOR.neutral;
        const dirCn =
          m.direction === "bullish" ? "利多↑" : m.direction === "bearish" ? "利空↓" : "中性";
        return {
          coord: [m.date, high] as [string, number],
          symbol: "diamond",
          symbolSize: 11,
          itemStyle: {
            color: "#ffffff",
            borderColor: color,
            borderWidth: 2,
            opacity: dim ? DIM_OPACITY : 1,
          },
          label: { show: false },
          pick: {
            kind: "news_mark" as const,
            date: m.date,
            newsDirection: dirCn,
            newsTitles: m.titles,
            newsImportance: m.importance,
          },
          tooltip: {
            formatter:
              `📰 ${dirCn} · 重要 ${m.importance}/10 · ${m.date}<br/>` +
              m.titles.map((t) => `· ${t}`).join("<br/>") +
              (m.count > m.titles.length ? `<br/>…共 ${m.count} 条<br/>` : "<br/>") +
              `消息面参考层 · 非交易信号`,
          },
        };
      })
      .filter((p): p is NonNullable<typeof p> => p !== null);
    markPointData.push(...newsMarkPoints);

    // ---- 当前可视区间最高 / 最低价自动极值标注 ----
    markPointData.push(
      {
        name: "区间最高",
        type: "max",
        valueDim: "highest",
        symbol: "circle",
        symbolSize: 4,
        itemStyle: { color: "#475569" },
        label: {
          show: true,
          position: "top",
          distance: 4,
          color: "#475569",
          fontSize: 10,
          fontWeight: 600,
          backgroundColor: "rgba(255,255,255,0.85)",
          padding: [1, 3],
          borderRadius: 2,
          formatter: (p: { value?: number }) => (typeof p.value === "number" ? `高 ${p.value.toFixed(2)}` : ""),
        },
      },
      {
        name: "区间最低",
        type: "min",
        valueDim: "lowest",
        symbol: "circle",
        symbolSize: 4,
        itemStyle: { color: "#475569" },
        label: {
          show: true,
          position: "bottom",
          distance: 4,
          color: "#475569",
          fontSize: 10,
          fontWeight: 600,
          backgroundColor: "rgba(255,255,255,0.85)",
          padding: [1, 3],
          borderRadius: 2,
          formatter: (p: { value?: number }) => (typeof p.value === "number" ? `低 ${p.value.toFixed(2)}` : ""),
        },
      },
    );

    // ---- MACD 副图（研究代理强度指标）----
    // DIF/DEA 线 + 红绿柱 + 0 轴参考线。作强度/乖离解读，非转折（见 macd_strength）。
    // 事件标记（▲金叉 ▼死叉 ○穿0轴）来自后端 macd_strength 判定（macdEvents），
    // 前端不自算交叉——判定权在 Python 规则层（AGENTS.md 约束）。
    const macdOpacity = dim ? DIM_OPACITY : 1;
    const rawMacdEvents = d.macdEvents ?? [];
    const shownMacdEvents =
      macdCompact && rawMacdEvents.length > MACD_COMPACT_RECENT_COUNT
        ? rawMacdEvents.slice(-MACD_COMPACT_RECENT_COUNT)
        : rawMacdEvents;
    const macdMarkPoints = shownMacdEvents.map((ev) => {
      const meta = MACD_EVENT_META[ev.type] ?? MACD_EVENT_META.golden_cross;
      return {
        coord: [ev.date, ev.dif] as [string, number],
        symbol: meta.symbol,
        symbolSize: 7,
        symbolRotate: meta.rotate,
        itemStyle: meta.hollow
          ? { color: "#ffffff", borderColor: meta.color, borderWidth: 1.6, opacity: macdOpacity }
          : { color: meta.color, borderColor: "#ffffff", borderWidth: 0.8, opacity: macdOpacity },
        label: { show: false },
        pick: { kind: "macd_event" as const, date: ev.date, macdStatusCn: ev.statusCn },
        tooltip: {
          formatter:
            `MACD ${ev.statusCn} · ${ev.date}<br/>` +
            `强度${ev.dimension}（研究代理）<br/>` +
            `仅看强弱 · 点击查看讲解`,
        },
      };
    });
    const macdSeries: object[] = showMacd
      ? [
          {
            name: "MACD柱",
            type: "bar",
            itemStyle: { color: up },
            data: d.macdHist.map((v) => ({
              value: v,
              itemStyle: {
                color: v != null && v >= 0 ? up : down,
                opacity: macdOpacity * 0.78,
              },
            })),
            xAxisIndex: 2,
            yAxisIndex: 2,
            markLine: {
              silent: true,
              symbol: "none",
              lineStyle: { color: "#cbd5e1", type: "dashed", width: 0.8 },
              label: { show: false },
              data: [{ yAxis: 0 }],
            },
          },
          {
            name: "DIF",
            type: "line",
            data: d.macdDif,
            xAxisIndex: 2,
            yAxisIndex: 2,
            showSymbol: false,
            smooth: true,
            lineStyle: { width: 1.3, color: "#e36b1c", opacity: macdOpacity },
            itemStyle: { color: "#e36b1c" },
            z: 3,
            markPoint: { silent: false, data: macdMarkPoints },
          },
          {
            name: "DEA",
            type: "line",
            data: d.macdDea,
            xAxisIndex: 2,
            yAxisIndex: 2,
            showSymbol: false,
            smooth: true,
            lineStyle: { width: 1.3, color: "#8b5cf6", opacity: macdOpacity },
            itemStyle: { color: "#8b5cf6" },
            z: 3,
          },
        ]
      : [];
    const macdXAxis = showMacd
      ? [
          {
            type: "category",
            data: d.dates,
            gridIndex: 2,
            axisLine: { lineStyle: { color: "#dfe5ee" } },
            axisLabel: { show: false },
            splitLine: { show: false },
          },
        ]
      : [];
    const macdYAxis = showMacd
      ? [
          {
            scale: true,
            position: "right" as const,
            splitNumber: 3,
            gridIndex: 2,
            axisLine: { show: false },
            axisLabel: { color: "#64748b", fontSize: 10, margin: 8 },
            splitLine: { show: false },
          },
        ]
      : [];

    // 取消顶部混排 Legend 后，主图上沿收紧至 10px，三段留出清晰间隔防止刻度碰撞
    const grids = showMacd
      ? [
          { left: 12, right: 64, top: 10, height: "53%" },
          { left: 12, right: 64, top: "67%", height: "11%" },
          { left: 12, right: 64, top: "80.5%", height: "12.5%" },
        ]
      : [
          { left: 12, right: 64, top: 10, height: "68%" },
          { left: 12, right: 64, top: "81.5%", height: "11.5%" },
        ];
    const zoomAxes = showMacd ? [0, 1, 2] : [0, 1];

    const n = d.dates.length;
    const defWin = resolveRangeWindow(n, display.timeframe, "6M");
    const clampIdx = (v: number) => Math.max(0, Math.min(n - 1, Math.round(v)));
    let zs = clampIdx(zoom?.startValue ?? defWin.startValue);
    let ze = clampIdx(zoom?.endValue ?? defWin.endValue);
    if (zs > ze) [zs, ze] = [ze, zs];

    return {
        backgroundColor: "#ffffff",
        animation: false,
        // 顶部全局 Legend 移入组件内 .kline-hud 实时读数栏，画布顶部零浪费
        legend: { show: false },
        // 子图内部左上角轻量标签（与各自子图对齐，绝不压图/绝不与顶部重复）
        graphic: [
          {
            type: "text",
            left: 16,
            top: showMacd ? "67.2%" : "81.7%",
            z: 100,
            silent: true,
            style: { text: "量能  — 20日均量", fill: "#64748b", fontSize: 10, fontWeight: 500 },
          },
          ...(showMacd
            ? [
                {
                  type: "text",
                  left: 16,
                  top: "80.7%",
                  z: 100,
                  silent: true,
                  style: { text: "MACD", fill: "#64748b", fontSize: 10, fontWeight: 600 },
                },
                {
                  type: "text",
                  left: 56,
                  top: "80.7%",
                  z: 100,
                  silent: true,
                  style: { text: "● DIF", fill: "#e36b1c", fontSize: 10, fontWeight: 600 },
                },
                {
                  type: "text",
                  left: 96,
                  top: "80.7%",
                  z: 100,
                  silent: true,
                  style: { text: "● DEA", fill: "#8b5cf6", fontSize: 10, fontWeight: 600 },
                },
              ]
            : []),
        ],
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "cross" },
          backgroundColor: "rgba(255,255,255,0.96)",
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
              if (p.seriesName === "K线") {
                // 直接从原始 d.ohlc 按日期取值（ECharts 传入的 candlestick params.value 首项是类目下标，不可直接解构）
                const i = d.dates.indexOf(date);
                const bar = i >= 0 ? d.ohlc[i] : null;
                if (bar) {
                  const [o, c, l, h] = bar;
                  const prevC = i > 0 ? d.ohlc[i - 1][1] : null;
                  let chgLabel: string;
                  if (prevC == null) {
                    chgLabel = "--";
                  } else {
                    const pct = (c / prevC - 1) * 100;
                    chgLabel = (pct < 0 ? "" : "+") + pct.toFixed(2) + "%";
                  }
                  lines.push(
                    `开 ${o.toFixed(2)}　高 ${h.toFixed(2)}　低 ${l.toFixed(2)}　收 ${c.toFixed(2)}　${chgLabel}`,
                  );
                }
              } else if (p.seriesName === "量能") {
                const vol = typeof v === "object" && v !== null && "value" in v ? (v as { value: number }).value : (v as number);
                lines.push(`量能 ${fmtBig(vol)}`);
              } else if (p.seriesName === "20日均量") {
                if (typeof v === "number" && v > 0) lines.push(`20日均量 ${fmtBig(v)}`);
              } else if (p.seriesName === "DIF" || p.seriesName === "DEA") {
                if (typeof v === "number" && v) lines.push(`${p.seriesName} ${v.toFixed(4)}`);
              } else if (p.seriesName === "MACD柱") {
                const hv = typeof v === "object" && v !== null && "value" in v ? (v as { value: number }).value : (v as number);
                if (hv != null) lines.push(`MACD柱 ${hv.toFixed(4)}`);
              } else if (
                p.seriesName !== "双20云带" &&
                p.seriesName !== "道路状态带" &&
                typeof v === "number" &&
                v
              ) {
                lines.push(`${p.seriesName} ${v.toFixed(2)}`);
              }
            }
            return lines.join("<br/>");
          },
        },
        axisPointer: { link: [{ xAxisIndex: "all" }] },
        grid: grids,
        xAxis: [
          {
            type: "category",
            data: d.dates,
            gridIndex: 0,
            axisLine: { lineStyle: { color: "#dfe5ee" } },
            axisLabel: { color: "#64748b", fontSize: 10, margin: 6 },
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
          ...macdXAxis,
          ...(chipXAxis ? [chipXAxis] : []),
        ],
        yAxis: [
          {
            scale: true,
            boundaryGap: ["10%", "7%"],
            position: "right" as const,
            ...(hl?.ensureVisible ? {
              min: (extent: {min:number;max:number}) => priceAxisBounds(extent.min,extent.max,hl.priceLines.map(p=>p.price))?.min ?? extent.min,
              max: (extent: {min:number;max:number}) => priceAxisBounds(extent.min,extent.max,hl.priceLines.map(p=>p.price))?.max ?? extent.max,
            } : {}),
            gridIndex: 0,
            axisLine: { show: false },
            axisLabel: { color: "#64748b", fontSize: 10, margin: 8 },
            splitLine: { lineStyle: { color: "#f1f5f9" } },
          },
          {
            scale: true,
            position: "right" as const,
            gridIndex: 1,
            splitNumber: 2,
            axisLine: { show: false },
            axisLabel: {
              showMinLabel: false,
              color: "#64748b",
              fontSize: 10,
              margin: 8,
              formatter: (v: number) => fmtBig(v),
            },
            splitLine: { show: false },
          },
          ...macdYAxis,
        ],
        dataZoom: [
          { type: "inside", xAxisIndex: zoomAxes, startValue: zs, endValue: ze },
          {
            type: "slider",
            xAxisIndex: zoomAxes,
            left: 12,
            right: 64,
            bottom: 4,
            height: 16,
            startValue: zs,
            endValue: ze,
            borderColor: "#dfe5ee",
            backgroundColor: "#ffffff",
            textStyle: { color: "#64748b", fontSize: 10 },
          },
        ],
        series: [
          ...(maRibbonSeries ? [maRibbonSeries] : []),
          ...(stateStripSeries ? [stateStripSeries] : []),
          {
            name: "K线",
            type: "candlestick",
            data: ohlcSeriesData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: isBiao
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
          ...(volMa20
            ? [
                {
                  name: "20日均量",
                  type: "line" as const,
                  data: volMa20,
                  xAxisIndex: 1,
                  yAxisIndex: 1,
                  showSymbol: false,
                  smooth: true,
                  silent: true,
                  lineStyle: { width: 1.1, color: "#94a3b8", opacity: dim ? DIM_OPACITY : 0.9 },
                  z: 3,
                },
              ]
            : []),
          ...macdSeries,
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
  size: (val: number[]) => number[];
}

interface ChipDistributionResult {
  buckets: { price: number; amount: number }[];
  maxAmount: number;
  step: number;
  profitRatioPct: number | null;
  avgCost: number | null;
}

/** 简单滚动均值（用于成交量 20 日均量参考线）。 */
function computeRollingMean(values: number[], period: number): (number | null)[] {
  const out = new Array<number | null>(values.length).fill(null);
  if (period <= 0 || values.length === 0) return out;
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i] ?? 0;
    if (i >= period) sum -= values[i - period] ?? 0;
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

// 衰减模式半衰期（交易日）。经验值：约 1 个交易年的成交权重衰减到一半，
// 既能压低远古成交、又不至于让 1 年前的筹码完全消失。
const CHIP_DECAY_HALF_LIFE_DAYS = 250;

/** 各周期一根 K 线约含多少个交易日，用于把「日」口径的半衰期折算成「根」。 */
const CHIP_BARS_PER_PERIOD: Record<Timeframe, number> = { D: 1, W: 5, M: 21 };

/**
 * 筹码分布（CYQ）：把每个交易日的成交量按当日 [low, high] 价格区间均匀
 * 分配到等宽价格桶里累计，同时汇总获利盘比例与加权筹码均价。
 */
function computeChipDistribution(
  ohlc: [number, number, number, number][],
  volumes: number[],
  bucketCount = 80,
  halfLifeDays?: number,
  refClose?: number,
): ChipDistributionResult | null {
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
  const last = ohlc.length - 1; // 最新交易日下标，用于算距今天数
  for (let i = 0; i < ohlc.length; i++) {
    const raw = volumes[i] ?? 0;
    if (raw <= 0) continue;
    // 衰减权重：距最新越久权重越小；未指定半衰期时恒为 1（纯累计）。
    const weight = halfLifeDays
      ? Math.pow(0.5, (last - i) / halfLifeDays)
      : 1;
    const v = raw * weight;
    const l = ohlc[i][2];
    const h = ohlc[i][3];
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
  let totalAmount = 0;
  let profitAmount = 0;
  let weightedPriceSum = 0;
  const closePrice = refClose ?? ohlc[last]?.[1] ?? 0;
  const buckets = amounts.map((a, b) => {
    const price = lo + (b + 0.5) * step;
    if (a > maxAmount) maxAmount = a;
    if (a > 0) {
      totalAmount += a;
      weightedPriceSum += price * a;
      if (price <= closePrice) profitAmount += a;
    }
    return { price, amount: a };
  });
  return {
    buckets,
    maxAmount,
    step,
    profitRatioPct: totalAmount > 0 ? (profitAmount / totalAmount) * 100 : null,
    avgCost: totalAmount > 0 ? weightedPriceSum / totalAmount : null,
  };
}

// ---- 12-1 动量（Carhart 1997 口径）----

/** 12 个月交易日（≈ 252 根 K 线）。 */
const MOM121_LOOKBACK = 252;
/** 跳过最近 1 个月交易日（≈ 21 根 K 线），剥离短期反转。 */
const MOM121_SKIP = 21;

/**
 * 12-1 动量序列（研究代理 · 纯展示）。
 *
 * 公式: mom121[i] = close[i-21] / close[i-252] - 1
 * - 跳过最近 1 个月（≈21 交易日）剥离短期反转
 * - 起点为 12 个月前（≈252 交易日）
 * - i < 252 时返回 null（数据不足，序列前段留空）
 *
 * 学术依据（公式必须可追溯，不发明新变体）:
 * - Jegadeesh & Titman (1993) 原始 12 月动量
 * - Carhart (1997) 四因子模型 UMD 因子定义
 * - Asness, Frazzini, Israel, Moskowitz (2014) 12-2 变体复核
 *
 * 数据源: d.ohlc 现有 close 序列，不另接数据。
 * 用途: 仅作为「时间尺度外部锚点」在 K 线角标展示，不进入规则层 / 判定层。
 * 量级判读: **不引用美股分布做硬阈值**——A 股单标的环境不直接套用学术
 * 截面统计。百分位（如果有）必须用 252 日滚动窗口自洽计算。
 */
function computeMom121(
  ohlc: [number, number, number, number][],
): (number | null)[] {
  const n = ohlc.length;
  const result: (number | null)[] = new Array(n).fill(null);
  for (let i = MOM121_LOOKBACK; i < n; i++) {
    const closeRecent = ohlc[i - MOM121_SKIP]?.[1];   // close[i-21]
    const closeOld = ohlc[i - MOM121_LOOKBACK]?.[1];   // close[i-252]
    if (!closeOld || !closeRecent) continue;
    const v = closeRecent / closeOld - 1;
    result[i] = Number.isFinite(v) ? v : null;
  }
  return result;
}

/**
 * 12-1 当前值在资产自身历史中的百分位（自洽百分位）。
 *
 * 口径: X% = 历史中 X% 的 12-1 值 ≤ 当前值（CDF 约定，与 Carhart 1997
 * 截面研究同源；不引美股分布做硬阈值）。
 *
 * 用途: 给 12-1 当前值一个"在自身历史里排第几"的锚点。
 * 约束: **不做硬阈值判读**——A 股单标的没有学术意义上的"强势/弱势"切点，
 *       显示原始百分位数字，让用户/规则层自取。
 *
 * 边界: 序列全 null → null；当前值为 null → null；只有一个有效值 → 100
 *       （退化情况，因为 100% 的历史值 ≤ 当前值）。
 */
function computeMom121PercentileCurrent(
  mom121Series: (number | null)[],
): number | null {
  const n = mom121Series.length;
  if (n === 0) return null;
  const current = mom121Series[n - 1];
  if (current == null) return null;
  let count = 0;
  let total = 0;
  for (let j = 0; j < n; j++) {
    const v = mom121Series[j];
    if (v == null) continue;
    total++;
    if (v <= current) count++;
  }
  if (total < 1) return null;
  return (count / total) * 100;
}
