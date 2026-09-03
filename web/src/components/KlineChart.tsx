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
    | "macd_event";
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
export type ColorMode = "red_green" | "lei_state";

/** 筹码峰计算口径。 */
export type ChipMode = "full" | "decay";

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
   * （LEI 三色、结构标记、参考线、MACD 事件、关键性波动）在聚合视图下
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
  colorMode: "lei_state", // 默认 LEI 黑绿灰着色（颜色=当日状态）
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

  const tf = display.timeframe;
  const isDaily = tf === "D";
  // 周期视图：日线原样返回同一引用（零开销），周/月聚合出新的 payload。
  // 聚合发生在图表内部，父组件持有的仍是日线 payload——顶栏最新价、
  // 趋势清单等一切页面级展示都不受周期切换影响。
  const view = useMemo(() => aggregateChartPayload(payload, tf), [payload, tf]);
  // 生效开关：周/月线自动隐藏日线专属内容（见 effectiveDisplay）
  const eff = useMemo(() => effectiveDisplay(display), [display]);
  // 12-1 动量序列（Carhart 1997 口径）—— 永远从日线 close 算，聚合视图不重算。
  // 周/月线不显示 12-1：聚合后点数不足 252 根，12-1 无意义。空数组由 buildKlineOption
  // 内部判断后跳过角标。
  const mom121Series = useMemo(
    () => (isDaily ? computeMom121(payload.ohlc) : []),
    [payload, isDaily],
  );
  // 买点联动高亮依赖日线结构标记，聚合视图下一并停用
  const effHighlight = isDaily ? highlight ?? null : null;

  // 结构标记降密档：可视窗口 > MARK_DENSE_WINDOW_BARS 根时进入。
  // onDataZoom 里跨阈值才 setState（拖动全程只有两次翻转），effect 依赖
  // dense 触发 setOption 重新过滤——远端非存活标记截断，存活结构始终全画。
  const [dense, setDense] = useState(false);
  const denseRef = useRef(false);

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
        chart.setOption({
          dataZoom: [
            { startValue: s, endValue: e },
            { startValue: s, endValue: e },
          ],
        });
      }
      // 降密档位检测：窗口跨度跨过阈值才翻转一次 state，触发 setOption 重过滤。
      const nowDense = e - s > MARK_DENSE_WINDOW_BARS;
      if (nowDense !== denseRef.current) {
        denseRef.current = nowDense;
        setDense(nowDense);
      }
    };
    chart.on("dataZoom", onDataZoom as (params: unknown) => void);

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

  // setOption 独立 effect：data/开关变化时只更新 option，不销毁实例，
  // 保留 dataZoom 缩放位置，不闪烁。用 notMerge 防止旧标记/均线残留。
  // 但 notMerge 会整体替换 option、把 dataZoom 重置回默认，因此先读出当前
  // 窗口（整数索引）原样续接，既保留缩放位置、又保证吸附在整根 K 线。
  // 首次渲染时 chart 还没有 option，取 null 用默认区间。
  //
  // 周期切换时点数会变（日 500 根 ≈ 周 100 根），旧窗口是「日线索引」，
  // 直接沿用会被 clamp 成末尾几根。按新旧序列长度等比缩放索引 ——
  // 两个序列覆盖同一段日期，比例映射等价于「保持大致相同的可见日期区间」。
  const lastRenderRef = useRef<{ tf: Timeframe; n: number } | null>(null);
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    // 首次渲染时 chart 还没有 option，getOption() 返回 undefined，取 null 用默认区间。
    const curDz = (chart.getOption()?.dataZoom as Array<{ startValue?: number; endValue?: number }> | undefined) ?? [];
    const z0 = curDz[0];
    let zoom =
      z0 && z0.startValue != null && z0.endValue != null
        ? { startValue: Math.round(z0.startValue), endValue: Math.round(z0.endValue) }
        : null;
    const prev = lastRenderRef.current;
    const n = view.dates.length;
    if (zoom && prev && prev.tf !== tf && prev.n > 1 && n > 1) {
      const k = (n - 1) / (prev.n - 1);
      zoom = {
        startValue: Math.round(zoom.startValue * k),
        endValue: Math.round(zoom.endValue * k),
      };
    }
    lastRenderRef.current = { tf, n };
    chart.setOption(buildKlineOption(view, eff, effHighlight, zoom, mom121Series, dense), { notMerge: true });
  }, [view, eff, effHighlight, tf, mom121Series, dense]);

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

  return (
    <>
      <div className="kline" ref={ref} />
      {!isDaily && (
        <div className="chip-legend tf-note">
          <span className="chip-leg-item">
            {timeframeLabel(tf)}线为日线聚合视图，LEI 信号与结构标记仅日线模式可用
            （开/收取区间首末日、高/低取区间极值、量为区间求和；均线在聚合数据上重算，
            MACD 副图与关键性波动不显示）
          </span>
        </div>
      )}
      {isDaily && dense && (eff.bottomMarks || eff.topMarks) && (
        <div className="chip-legend tf-note">
          <span className="chip-leg-item">
            可视窗口超过 {MARK_DENSE_WINDOW_BARS} 根：已截断远端失效标记（保留最近
            数量见开关口径），存活结构确认始终完整显示；缩窄窗口可恢复全量
          </span>
        </div>
      )}
      {eff.chipDist && (
        <div className="chip-legend">
          <span className="chip-leg-item">
            <i className="chip-leg-swatch" style={{ background: "#e36b1c" }} />
            获利盘　价位 ≤ 当前价
          </span>
          <span className="chip-leg-item">
            <i className="chip-leg-swatch" style={{ background: "#6366f1" }} />
            套牢盘　价位高于当前价
          </span>
          {eff.chipMode === "decay" && (
            <span className="chip-leg-item chip-leg-decay">
              衰减半衰期 {CHIP_DECAY_HALF_LIFE_DAYS} 日
            </span>
          )}
        </div>
      )}
      {eff.macd && (
        <div className="chip-legend macd-legend">
          <span className="chip-leg-item" style={{ color: MACD_EVENT_META.golden_cross.color }}>
            ▲ 金叉（DIF 上穿 DEA）
          </span>
          <span className="chip-leg-item" style={{ color: MACD_EVENT_META.death_cross.color }}>
            ▼ 死叉（DIF 下穿 DEA）
          </span>
          <span className="chip-leg-item" style={{ color: MACD_EVENT_META.zero_cross_up.color }}>
            ○ 上穿0轴（排列转多）
          </span>
          <span className="chip-leg-item" style={{ color: MACD_EVENT_META.zero_cross_down.color }}>
            ○ 下穿0轴（排列转空）
          </span>
          <span className="chip-leg-item macd-leg-note">
            研究代理 · 强度非转折 · 金叉/死叉不是买卖点
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
  mom121Series?: (number | null)[],
  dense = false,
) {
    const d = payload;
    const up = d.priceUp;
    const down = d.priceDown;
    const showMacd = display.macd;
    // 筹码 value 轴排在所有 category 轴之后：开 MACD 时占 index 3，否则 2。
    const chipXAxisIndex = showMacd ? 3 : 2;
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
            backgroundColor: "rgba(255,255,255,0.95)",
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
              backgroundColor: "rgba(255,255,255,0.95)",
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
              backgroundColor: "rgba(255,255,255,0.95)",
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
      // 衰减模式：按距最新交易日的天数对成交量做指数衰减（半衰期 250 日）。
      // 全历史模式不传 halfLifeDays，computeChipDistribution 退化为纯累计。
      // computeChipDistribution 的衰减按「根数」计距，因此周/月聚合视图要把
      // 半衰期从「日」折算成「根」（1 周≈5 交易日、1 月≈21 交易日），
      // 否则周线下 250 根 = 250 周，衰减会形同失效。
      const halfLifeDays =
        display.chipMode === "decay"
          ? CHIP_DECAY_HALF_LIFE_DAYS / CHIP_BARS_PER_PERIOD[display.timeframe]
          : undefined;
      const chip = computeChipDistribution(d.ohlc, d.volumes, 80, halfLifeDays);
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
          xAxisIndex: chipXAxisIndex,
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
            const color = profitable ? "#e36b1c" : "#6366f1";

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

    // ---- MACD 副图（研究代理强度指标）----
    // DIF/DEA 线 + 红绿柱 + 0 轴参考线。作强度/乖离解读，非转折（见 macd_strength）。
    // 事件标记（▲金叉 ▼死叉 ○穿0轴）来自后端 macd_strength 判定（macdEvents），
    // 前端不自算交叉——判定权在 Python 规则层（AGENTS.md 约束）。
    const macdOpacity = dim ? DIM_OPACITY : 1;
    const macdMarkPoints = (d.macdEvents ?? []).map((ev) => {
      const meta = MACD_EVENT_META[ev.type] ?? MACD_EVENT_META.golden_cross;
      return {
        coord: [ev.date, ev.dif] as [string, number],
        symbol: meta.symbol,
        symbolSize: 10,
        symbolRotate: meta.rotate,
        itemStyle: meta.hollow
          ? { color: "#ffffff", borderColor: meta.color, borderWidth: 2, opacity: macdOpacity }
          : { color: meta.color, borderColor: "#ffffff", borderWidth: 1, opacity: macdOpacity },
        label: { show: false },
        pick: { kind: "macd_event" as const, date: ev.date, macdStatusCn: ev.statusCn },
        tooltip: {
          formatter:
            `MACD ${ev.statusCn} · ${ev.date}<br/>` +
            `强度${ev.dimension}（研究代理）<br/>` +
            `不是买卖点 · 点击查看讲解`,
        },
      };
    });
    const macdSeries: object[] = showMacd
      ? [
          {
            name: "MACD柱",
            type: "bar",
            data: d.macdHist.map((v) => ({
              value: v,
              itemStyle: {
                color: v != null && v >= 0 ? up : down,
                opacity: macdOpacity,
              },
            })),
            xAxisIndex: 2,
            yAxisIndex: 2,
            markLine: {
              silent: true,
              symbol: "none",
              lineStyle: { color: "#c0c6d0", type: "dashed", width: 0.8 },
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
            gridIndex: 2,
            axisLine: { show: false },
            axisLabel: { color: "#7b8494", fontSize: 10 },
            splitLine: { show: false },
          },
        ]
      : [];
    const grids = showMacd
      ? [
          { left: 56, right: 34, top: 32, height: "46%" },
          { left: 56, right: 34, top: "56%", height: "14%" },
          { left: 56, right: 34, top: "72%", height: "14%" },
        ]
      : [
          { left: 56, right: 34, top: 32, height: "62%" },
          { left: 56, right: 34, top: "72%", height: "18%" },
        ];
    const zoomAxes = showMacd ? [0, 1, 2] : [0, 1];

    // dataZoom 改用「数据索引」(startValue/endValue) 而非百分比，并由外部 dataZoom
    // 事件把索引取整回写，使拖拽/缩放时窗口永远对齐到「整根 K 线」——不会被切成
    // 半根、也不会在缩放到很细时漂离数据顶点。zoom 由 setOption effect 传入续接
    // 用户当前位置；首次/无续接时用默认展示右侧约 60%。
    const n = d.dates.length;
    const defStart = n > 1 ? Math.round(0.4 * (n - 1)) : 0;
    const defEnd = n > 0 ? n - 1 : 0;
    const clampIdx = (v: number) => Math.max(0, Math.min(n - 1, Math.round(v)));
    let zs = clampIdx(zoom?.startValue ?? defStart);
    let ze = clampIdx(zoom?.endValue ?? defEnd);
    if (zs > ze) [zs, ze] = [ze, zs];

    // ---- 12-1 动量角标（Carhart 1997 口径）----
    // 仅日线 + 数据足够（>252 根）时显示；周/月线或首 252 根数据时隐藏。
    // 不进 legend / tooltip / 判定层；纯右上角文字，作为时间尺度外部锚点。
    const lastMom121 =
      mom121Series && mom121Series.length > 0
        ? mom121Series[mom121Series.length - 1]
        : null;
    const mom121Pct = computeMom121PercentileCurrent(mom121Series ?? []);
    const mom121Label: object[] =
      lastMom121 != null
        ? [
            {
              type: "text",
              right: 10,
              top: 4,
              z: 100,
              silent: true,
              style: {
                text: `12-1 动量  ${lastMom121 >= 0 ? "+" : ""}${(lastMom121 * 100).toFixed(2)}%`,
                fill: lastMom121 >= 0 ? "#e33d47" : "#0b9b64",
                fontSize: 12,
                fontWeight: 600,
                backgroundColor: "rgba(255,255,255,0.92)",
                padding: [3, 8],
                borderRadius: 3,
              },
            },
            ...(mom121Pct != null
              ? [
                  {
                    type: "text",
                    right: 10,
                    top: 28,
                    z: 100,
                    silent: true,
                    style: {
                      text: `历史百分位  ${mom121Pct.toFixed(0)}%`,
                      fill: "#5b6473",
                      fontSize: 10,
                      fontWeight: 500,
                    },
                  },
                ]
              : []),
            {
              type: "text",
              right: 10,
              top: 46,
              z: 100,
              silent: true,
              style: {
                text: "Carhart 1997 · close[i−21]/close[i−252]−1",
                fill: "#9ca3af",
                fontSize: 9,
              },
            },
          ]
        : [];

    return {
        backgroundColor: "#ffffff",
        animation: false,
        legend: {
          data: [...maSeries.map((s) => s.name), ...(showMacd ? ["DIF", "DEA", "MACD柱"] : [])],
          textStyle: { color: "#5b6473", fontSize: 11 },
          top: 4,
        },
        // MACD 子图内直接标注两根线（固定位置，dataZoom 不影响）。
        // 左轴占 56px，故 left 用像素紧贴轴右侧；top 用百分比对齐 MACD 子图区（grid2: 72%–86%）。
        // 12-1 角标另由 mom121Label 提供，叠在 DIF/DEA 之后。
        graphic: [
          ...(showMacd
            ? [
                {
                  type: "text",
                  left: "60px",
                  top: "73.5%",
                  z: 100,
                  silent: true,
                  style: { text: "● DIF", fill: "#e36b1c", fontSize: 11, fontWeight: 600 },
                },
                {
                  type: "text",
                  left: "118px",
                  top: "73.5%",
                  z: 100,
                  silent: true,
                  style: { text: "● DEA", fill: "#8b5cf6", fontSize: 11, fontWeight: 600 },
                },
              ]
            : []),
          ...mom121Label,
        ],
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
                // 涨跌幅相对前一根收盘价(昨收)，与行情软件惯例及顶栏口径一致
                const i = d.dates.indexOf(date);
                const prevClose = i > 0 ? d.ohlc[i - 1][1] : null;
                let chgLabel: string;
                if (prevClose == null) {
                  chgLabel = "--";
                } else {
                  const pct = (c / prevClose - 1) * 100;
                  chgLabel = (pct < 0 ? "" : "+") + pct.toFixed(2) + "%";
                }
                lines.push(
                  `开 ${o.toFixed(2)}　收 ${c.toFixed(2)}　高 ${h.toFixed(2)}　低 ${l.toFixed(2)}　${chgLabel}`,
                );
              } else if (p.seriesName === "量能") {
                const vol = typeof v === "object" && v !== null && "value" in v ? (v as { value: number }).value : (v as number);
                lines.push(`量能 ${fmtBig(vol)}`);
              } else if (p.seriesName === "DIF" || p.seriesName === "DEA") {
                if (typeof v === "number" && v) lines.push(`${p.seriesName} ${v.toFixed(4)}`);
              } else if (p.seriesName === "MACD柱") {
                const hv = typeof v === "object" && v !== null && "value" in v ? (v as { value: number }).value : (v as number);
                if (hv != null) lines.push(`MACD柱 ${hv.toFixed(4)}`);
              } else if (typeof v === "number" && v) {
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
          ...macdXAxis,
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
          ...macdYAxis,
        ],
        dataZoom: [
          { type: "inside", xAxisIndex: zoomAxes, startValue: zs, endValue: ze },
          {
            type: "slider",
            xAxisIndex: zoomAxes,
            bottom: 6,
            height: 18,
            startValue: zs,
            endValue: ze,
            borderColor: "#dfe5ee",
            backgroundColor: "#ffffff",
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
}

// 衰减模式半衰期（交易日）。经验值：约 1 个交易年的成交权重衰减到一半，
// 既能压低远古成交、又不至于让 1 年前的筹码完全消失。
const CHIP_DECAY_HALF_LIFE_DAYS = 250;

/** 各周期一根 K 线约含多少个交易日，用于把「日」口径的半衰期折算成「根」。 */
const CHIP_BARS_PER_PERIOD: Record<Timeframe, number> = { D: 1, W: 5, M: 21 };

/**
 * 筹码分布（CYQ）：把每个交易日的成交量按当日 [low, high] 价格区间均匀
 * 分配到等宽价格桶里累计。
 *
 * 口径（halfLifeDays）：
 *   - 省略（全历史）：纯累计、不衰减——用户要的是「量的纵向展示」，
 *     看哪个价位历史成交堆积多。
 *   - 指定半衰期（衰减模式）：成交量按距最新交易日的天数做指数衰减
 *     weight = 0.5^(距今天数 / 半衰期) 后再入桶。历史久远的成交权重趋近 0，
 *     峰值更偏向近期价位，对「当前密集区代表性弱」的痛点更友好。
 *
 * 桶价 ≤ 最新收盘价视为获利盘，否则套牢盘。
 */
function computeChipDistribution(
  ohlc: [number, number, number, number][],
  volumes: number[],
  bucketCount = 80,
  halfLifeDays?: number,
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
  for (const a of amounts) if (a > maxAmount) maxAmount = a;
  const buckets = amounts.map((a, b) => ({ price: lo + (b + 0.5) * step, amount: a }));
  return { buckets, maxAmount, step };
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
