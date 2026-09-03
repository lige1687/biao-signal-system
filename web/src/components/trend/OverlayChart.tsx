import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { zoneBands, zoneMarkLines } from "./marks";
import type { HighlightBand, MarkLine, ZoneLevel } from "./zones";

export interface OverlaySeries {
  name: string;
  values: (number | null)[];
  color: string;
  /** 左轴 = 指数点位；右轴 = 收益率/占比（%）；breadth = 市场宽度（0–100%）。 */
  axis: "left" | "right" | "breadth";
  /** 虚线（用于宽度线，与实线指数/债券区分）。 */
  dashed?: boolean;
  /** 线宽（默认 1.4，实线 / 1.2 虚线）。 */
  lineWidth?: number;
  /** 透明度 0–1（用于弱化辅助线）。 */
  opacity?: number;
  /** 在原始刻度指数格里，是否作为配角（不单独占一把 Y 轴，与主角共轴）。 */
  secondary?: boolean;
}

/**
 * raw    = 原始刻度：指数走左轴、利率走右轴，能标压力位/机会位色带，但两者涨跌幅不可比。
 * rebase = 归一化：全部除以「当前可视窗口起点」再 ×100，同一把尺子，直接读涨跌比
 *          （标普涨 80% 而 10Y 只涨 20% 这种关系一眼可见）；代价是利率的绝对分界线失效。
 */
export type OverlayMode = "raw" | "rebase";

interface OverlayChartProps {
  dates: string[];
  series: OverlaySeries[];
  /** 左轴名（指数）。 */
  leftName?: string;
  /** 右轴名（收益率%）。 */
  rightName?: string;
  /** 宽度轴名（仅当含 breadth 序列时出现）。 */
  breadthName?: string;
  /** 初始可视窗口占全序列的百分比（如 15 = 展示最近 15%）。 */
  startPercent?: number;
  height?: number;
  /** 宽度轴的分界线（压力/机会位），仅在有 breadth 序列时渲染。 */
  breadthMarkLines?: MarkLine[];
  /** 宽度格条件高亮色带（来自 6 条规则的多选计算），覆盖宽度格 0–100% 范围。 */
  breadthHighlightBands?: HighlightBand[];
  /** 右轴（利率/两融占比）的分界线：压力位 / 机会位。 */
  rightMarkLines?: MarkLine[];
  /** 右轴的区间色带（机会绿 → 风险红），画在整个绘图区背景上。 */
  rightZones?: readonly ZoneLevel[];
  mode?: OverlayMode;
}

/** 长周期叠加大图：指数 × 利率/两融占比 × 市场宽度，底部 dataZoom 滑动窗口。 */
export default function OverlayChart({
  dates,
  series,
  leftName = "指数",
  rightName = "收益率 %",
  breadthName = "宽度 %",
  startPercent = 15,
  height = 400,
  breadthMarkLines,
  breadthHighlightBands,
  rightMarkLines,
  rightZones,
  mode = "raw",
}: OverlayChartProps) {
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
    const inst = instRef.current;
    if (!inst) return;
    const cfg: OverlayConfig = {
      dates,
      series,
      leftName,
      rightName,
      breadthName,
      startPercent,
      breadthMarkLines,
      breadthHighlightBands,
      rightMarkLines,
      rightZones,
      mode,
    };
    inst.setOption(buildOverlayOption(cfg, initialStartIndex(cfg), height), true);

    if (mode !== "rebase") return;
    // 归一化的基准必须跟着可视窗口走：拖动 dataZoom 后重算共同基准，
    // 否则「近 4 年」和「20 年」读出来的涨跌比是同一条曲线，切窗口就没意义了。
    const onZoom = () => {
      const { iBase, baseDate } = rebaseBase(cfg, visibleStartIndex(inst, dates.length));
      inst.setOption({
        series: buildSeries(cfg, paneLayout(cfg, height), iBase),
        yAxis: [{ name: rebaseAxisName(baseDate) }],
      });
    };
    inst.on("dataZoom", onZoom);
    return () => {
      inst.off("dataZoom", onZoom);
    };
  }, [
    dates,
    series,
    leftName,
    rightName,
    breadthName,
    startPercent,
    breadthMarkLines,
    breadthHighlightBands,
    rightMarkLines,
    rightZones,
    mode,
    height,
  ]);

  return <div ref={ref} className="macro-chart" style={{ height }} />;
}

interface OverlayConfig {
  dates: string[];
  series: OverlaySeries[];
  leftName: string;
  rightName: string;
  breadthName: string;
  startPercent: number;
  breadthMarkLines?: MarkLine[];
  breadthHighlightBands?: HighlightBand[];
  rightMarkLines?: MarkLine[];
  rightZones?: readonly ZoneLevel[];
  mode: OverlayMode;
}

/** 当前可视窗口的左边界索引（dataZoom 用百分比或 value 两种表述，都要兼容）。 */
function visibleStartIndex(inst: echarts.ECharts, n: number): number {
  const dz = (inst.getOption() as { dataZoom?: Array<Record<string, unknown>> }).dataZoom?.[0];
  if (!dz || n === 0) return 0;
  const sv = dz.startValue;
  if (typeof sv === "number") return clamp(Math.round(sv), 0, n - 1);
  const st = dz.start;
  if (typeof st === "number") return clamp(Math.floor((st / 100) * (n - 1)), 0, n - 1);
  return 0;
}

/**
 * 把 HighlightBand[] 拍平为 ECharts markArea 的 data 数组。
 * 每个区间固定 yAxis 0–100，确保色带覆盖宽度格整体（不染指数/利率格）。
 * xAxis 用 category 日期字符串，由 ECharts 自动匹配下标。
 * flatMap 的元组在严格 TS 下会被推导成过窄的 union，加 as cast 让 ECharts 自己校验。
 */
function highlightBandsToMarkArea(
  bands: readonly HighlightBand[],
): NonNullable<echarts.LineSeriesOption["markArea"]> {
  return {
    silent: true,
    data: bands.flatMap((b) =>
      b.ranges.map(([start, end]) => [
        { xAxis: start, yAxis: 0 },
        { xAxis: end, yAxis: 100, itemStyle: { color: b.color, opacity: b.opacity } },
      ]),
    ) as never,
  };
}

/** 初始渲染时的窗口左边界（与 dataZoom 的 start 百分比一致，避免首帧基准错位后再跳）。 */
function initialStartIndex(cfg: OverlayConfig): number {
  const n = cfg.dates.length;
  if (n === 0) return 0;
  const start = Math.max(0, 100 - cfg.startPercent);
  return clamp(Math.floor((start / 100) * (n - 1)), 0, n - 1);
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

/** 序列在 from 之后的第一个可用（正数）下标；没有则 -1。 */
function firstUsable(values: (number | null)[], from: number): number {
  for (let i = from; i < values.length; i++) {
    const v = values[i];
    if (v != null && v > 0) return i;
  }
  return -1;
}

/**
 * 共同基准：窗口内**所有**序列都已有数据的最早那天。
 * 必须共同——标普只有 2016-08 起的数据（FRED 授权限制），若各自以「自己在窗口里的
 * 第一个点」为 100，标普的 100 在 2016、纳斯达克的 100 在 2006，两条线的起跑线不在
 * 同一天，涨跌比就是错的。宁可把基准日推后并标注出来，也不能让对比失真。
 */
function rebaseBase(cfg: OverlayConfig, i0: number): { iBase: number; baseDate: string } {
  const n = cfg.dates.length;
  let iBase = clamp(i0, 0, Math.max(0, n - 1));
  for (const s of shownSeries(cfg)) {
    const f = firstUsable(s.values, i0);
    if (f < 0) continue; // 窗口内完全没有数据的序列不参与决定基准
    if (f > iBase) iBase = f;
  }
  return { iBase, baseDate: cfg.dates[iBase] ?? "" };
}

/** 对数轴刻度会给出 31.6 这类值，整数就不留小数尾巴。 */
function logLabel(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(v < 10 ? 1 : 0);
}

function rebaseAxisName(baseDate: string): string {
  return baseDate ? `基准 ${baseDate} = 100（对数轴）` : "基准 = 100（对数轴）";
}

/** 以 iBase 处的值为 100 重算整条线；非正值在对数轴上无意义，置空。 */
function rebaseFrom(values: (number | null)[], iBase: number): (number | null)[] {
  const f = firstUsable(values, iBase);
  if (f < 0) return values.map(() => null);
  const base = values[f] as number;
  return values.map((v) => (v == null || v <= 0 ? null : (v / base) * 100));
}

/** 归一化模式下宽度线（本身就是 0–100 的占比）没有「涨跌比」含义，直接剔除。 */
function shownSeries(cfg: OverlayConfig): OverlaySeries[] {
  return cfg.mode === "rebase" ? cfg.series.filter((s) => s.axis !== "breadth") : cfg.series;
}

function buildSeries(
  cfg: OverlayConfig,
  layout: PaneLayout,
  iBase: number,
): echarts.LineSeriesOption[] {
  const rebase = cfg.mode === "rebase";
  const shown = shownSeries(cfg);

  return shown.map((s) => {
    const { x, y } = layout.locate(s);
    const opt: echarts.LineSeriesOption = {
      name: s.name,
      type: "line",
      xAxisIndex: x,
      yAxisIndex: y,
      data: rebase ? rebaseFrom(s.values, iBase) : s.values,
      showSymbol: false,
      connectNulls: true, // 债券/股票交易日历不完全重合，跳过空点连线
      lineStyle: {
        width: s.lineWidth ?? (s.dashed ? 1.2 : 1.4),
        color: s.color,
        type: s.dashed ? "dashed" : "solid",
        opacity: s.opacity ?? 1,
      },
      itemStyle: { color: s.color, opacity: s.opacity ?? 1 },
    };
    if (rebase && s === shown[0]) {
      // 100 = 窗口起点，线在上方就是涨、下方就是跌。
      opt.markLine = zoneMarkLines([{ y: 100, label: "100 基准", color: "#6b7280" }]);
    }
    return opt;
  });
}

/**
 * 把某分面的分界线/区间色带改挂到一条「隐形式锚点序列」上，而非第一条数据序列。
 * 原因：ECharts 里 markLine/markArea 属于某条 series，一旦用户在图例里把那条
 * 数据线（如「宽度20日」）隐藏，挂它身上的超买超卖分界线 / 区间色带会跟着整条
 * 序列一起消失。锚点序列不带任何数据点、不进图例，专属承载这些参考标记，确保
 * 无论用户怎么开关各条数据线，超买超卖区间都始终可见。
 */
const PANE_MARK_ANCHOR_BREADTH = "__breadth_pane_marks__";
const PANE_MARK_ANCHOR_RIGHT = "__right_pane_marks__";

function buildPaneMarkAnchor(
  loc: { x: number; y: number },
  marks: {
    markLine?: echarts.LineSeriesOption["markLine"];
    markArea?: echarts.LineSeriesOption["markArea"];
  },
  name: string,
  dataLength: number,
): echarts.LineSeriesOption {
  // 注意：data 必须是与 xAxis 等长的 null 数组（不能用 data: [] 空数组）——
  // 实测：空 data 时 markArea 的角落 (start, y1)/(end, y2) 会被 ECharts 画成对角 bowtie
  // （"X 形交叉"），而非 axis-aligned 矩形（横向水平带）。给 null 数据点是为了让
  // ECharts 建立序列的坐标系上下文，line 仍 opacity:0 不可见。
  return {
    name,
    type: "line",
    xAxisIndex: loc.x,
    yAxisIndex: loc.y,
    data: new Array(dataLength).fill(null),
    showSymbol: false,
    silent: true,
    tooltip: { show: false },
    lineStyle: { opacity: 0 },
    itemStyle: { opacity: 0 },
    ...marks,
  };
}

const PANE_TOP = 12; // 顶部标题区（图例已移到右侧竖排）
const PANE_BOTTOM = 56; // 底部 dataZoom 滑块 + 末格日期标签
const PANE_GAP = 10; // 格与格之间的纵向留白
const LEFT_AXIS_GAP = 52; // 指数格内相邻两把独立轴之间的横向间距（够放 5 位数点位标签）

/** 格高占比：指数格始终最大；两格 = 指数+宽度，三格 = 指数+利率+宽度。 */
const PANE_FRACTIONS: Record<number, number[]> = {
  1: [1],
  2: [0.62, 0.38],
  3: [0.44, 0.34, 0.22],
};

interface Pane {
  kind: "index" | "right" | "breadth";
  series: OverlaySeries[];
}

function panesOf(cfg: OverlayConfig): Pane[] {
  const pick = (axis: OverlaySeries["axis"]) =>
    shownSeries(cfg).filter((s) => s.axis === axis);
  const panes: Pane[] = [];
  const index = pick("left");
  const right = pick("right");
  const breadth = pick("breadth");
  if (index.length) panes.push({ kind: "index", series: index });
  if (right.length) panes.push({ kind: "right", series: right });
  if (breadth.length) panes.push({ kind: "breadth", series: breadth });
  return panes;
}

interface PaneLayout {
  grids: echarts.GridComponentOption[];
  xAxes: echarts.XAXisComponentOption[];
  yAxes: echarts.YAXisComponentOption[];
  /** 序列 -> 它所在格的 xAxis/yAxis 全局下标。 */
  locate: (s: OverlaySeries) => { x: number; y: number };
}

/**
 * 分面布局：指数 / 利率·占比 / 宽度各占一格，共享同一条 category 时间轴
 * （每格一把 xAxis，dataZoom 滑块与悬停十字线跨格联动）。
 * 每格只有一把轴（指数格内多条指数线仍是「一线一轴」错位着色），不再出现
 * 「一张图上左右各两把轴、靠颜色猜哪把轴属于哪条线」的读图负担；利率格的
 * 区间色带铺满整格、宽度格的 0–100 超买超卖线有了稳定坐标，都比挤在同一
 * 绘图区时清晰得多。rebase 模式退化为单格（对数轴），布局逻辑统一走这里。
 */
/** 计算序列在本视图下的波动跨度（max - min），用于判断是否需要独立 Y 轴。 */
function seriesSpan(s: OverlaySeries): number {
  const v = s.values.filter((x): x is number => x != null && x > 0);
  if (v.length < 2) return 0;
  return Math.max(...v) - Math.min(...v);
}

function paneLayout(cfg: OverlayConfig, height: number): PaneLayout {
  const panes = panesOf(cfg);
  const n = panes.length;
  const fractions = PANE_FRACTIONS[n] ?? panes.map(() => 1 / n);
  const usable = Math.max(80, height - PANE_TOP - PANE_BOTTOM);
  const body = usable - PANE_GAP * (n - 1);

  // 原始刻度下多指数可能共用一把左轴，也可能因量级差过大而分轴，
  // 左侧距要兼容最多两把轴的偏移，避免第二把轴标签被画布裁掉。
  const gridLeft = panes.some(
    (p) =>
      p.kind === "index" &&
      p.series.length > 1 &&
      (() => {
        const spans = p.series.map(seriesSpan);
        const minSpan = Math.min(...spans.filter((v) => v > 0)) || 1;
        return Math.max(...spans) / minSpan > 5;
      })(),
  )
    ? 58 + LEFT_AXIS_GAP
    : 58;
  // 图例改为右侧竖排，给 legend 留 68px 宽度。
  const gridRight = 78;

  const grids: echarts.GridComponentOption[] = [];
  const xAxes: echarts.XAXisComponentOption[] = [];
  const yAxes: echarts.YAXisComponentOption[] = [];
  const locateMap = new Map<OverlaySeries, { x: number; y: number }>();

  let top = PANE_TOP;
  panes.forEach((pane, gi) => {
    const h = Math.round(body * fractions[gi]);
    grids.push({ left: gridLeft, right: gridRight, top, height: h });
    const isLast = gi === n - 1;
    // 每格一把 xAxis；只有末格显示日期，其余格共享时间轴但隐藏刻度。
    xAxes.push({
      type: "category",
      data: cfg.dates,
      gridIndex: gi,
      boundaryGap: false,
      axisLabel: isLast ? { fontSize: 10, color: "#6b7280", hideOverlap: true } : { show: false },
      axisTick: { show: isLast },
      axisLine: { show: isLast, lineStyle: { color: "#d6dde6" } },
    });
    top += h + PANE_GAP;

    if (cfg.mode === "rebase") {
      // 对数轴是关键：纳斯达克有 1971 年起的全史（100 -> 26729，涨 267 倍），
      // 线性轴上它会把标普（最多 3.6 倍）和 10Y 压成贴地的平线。对数轴上
      // 「相同垂直距离 = 相同涨跌倍数」，几条线才真的可比。
      const { baseDate } = rebaseBase(cfg, 0);
      yAxes.push({
        type: "log",
        logBase: 10,
        gridIndex: gi,
        name: rebaseAxisName(baseDate),
        nameTextStyle: { fontSize: 10 },
        axisLabel: { fontSize: 10, color: "#6b7280", formatter: logLabel },
        splitLine: { lineStyle: { color: "#eef1f5" } },
        minorSplitLine: { show: true, lineStyle: { color: "#f6f8fa" } },
      });
      pane.series.forEach((s) => locateMap.set(s, { x: gi, y: yAxes.length - 1 }));
      return;
    }

    if (pane.kind === "index") {
      // 注：rebase 模式已在上方统一处理，走到这里一定是原始刻度。
      const spans = pane.series.map(seriesSpan);
      const maxSpan = Math.max(...spans);
      const minSpan = Math.min(...spans.filter((v) => v > 0)) || 1;
      // 若同格多指数跨度差异 >5 倍（如标普500 6000 点 vs 纳斯达克 26000 点），
      // 强制分轴：共轴会把低量级线压成贴地平线。A股上证/沪深300 跨度接近则共轴。
      const shouldSeparate = pane.series.length > 1 && maxSpan / minSpan > 5;

      pane.series.forEach((s, k) => {
        const solo = pane.series.length === 1 || !shouldSeparate;
        const color = solo ? "#d6dde6" : s.color;
        yAxes.push({
          type: "value",
          scale: true,
          min: "dataMin",
          max: "dataMax",
          gridIndex: gi,
          position: "left",
          offset: solo ? 0 : k * LEFT_AXIS_GAP,
          name: solo ? cfg.leftName : s.name,
          nameTextStyle: { fontSize: 10, color: solo ? "#6b7280" : s.color },
          axisLine: { show: true, lineStyle: { color } },
          axisTick: { show: false },
          axisLabel: { fontSize: 10, color: solo ? "#6b7280" : s.color },
          // 只让第一把指数轴画网格线，否则 N 把轴的横线互相穿插看不清。
          splitLine: k === 0 ? { lineStyle: { color: "#eef1f5" } } : { show: false },
        });
        locateMap.set(s, { x: gi, y: yAxes.length - 1 });
      });
      return;
    }

    if (pane.kind === "right") {
      yAxes.push({
        type: "value",
        scale: true,
        min: "dataMin",
        max: "dataMax",
        gridIndex: gi,
        position: "left",
        name: cfg.rightName,
        nameTextStyle: { fontSize: 10 },
        axisLabel: {
          fontSize: 10,
          color: "#6b7280",
          formatter: (v: number) => `${v.toFixed(2)}%`,
        },
        splitLine: { lineStyle: { color: "#eef1f5" } },
      });
      pane.series.forEach((s) => locateMap.set(s, { x: gi, y: yAxes.length - 1 }));
      return;
    }

    // breadth：0–100 固定刻度，超买/超卖分界线才有稳定坐标。
    yAxes.push({
      type: "value",
      gridIndex: gi,
      min: 0,
      max: 100,
      position: "left",
      name: cfg.breadthName,
      nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, color: "#6b7280", formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#eef1f5" } },
    });
    pane.series.forEach((s) => locateMap.set(s, { x: gi, y: yAxes.length - 1 }));
  });

  return {
    grids,
    xAxes,
    yAxes,
    locate: (s) => locateMap.get(s) ?? { x: 0, y: 0 },
  };
}

function buildOverlayOption(
  cfg: OverlayConfig,
  i0: number,
  height: number,
): echarts.EChartsOption {
  const rebase = cfg.mode === "rebase";
  const { iBase } = rebaseBase(cfg, i0);
  const layout = paneLayout(cfg, height);
  const allX = layout.xAxes.map((_, i) => i);

  const seriesOpts = buildSeries(cfg, layout, iBase);
  const anchorNames: string[] = [];

  // 非归一化模式下，把各分面的参考标记挂到隐形式锚点序列上（原因见 buildPaneMarkAnchor）。
  // 这样用户隐藏任意一条数据线（如「宽度20日」），超买超卖分界线 / 区间色带都不会跟着消失。
  if (!rebase) {
    const breadthSeries = shownSeries(cfg).find((s) => s.axis === "breadth");
    if (breadthSeries && (cfg.breadthMarkLines?.length || cfg.breadthHighlightBands?.length)) {
      const loc = layout.locate(breadthSeries);
      seriesOpts.push(
        buildPaneMarkAnchor(
          loc,
          {
            markLine: cfg.breadthMarkLines?.length ? zoneMarkLines(cfg.breadthMarkLines) : undefined,
            markArea: cfg.breadthHighlightBands?.length
              ? highlightBandsToMarkArea(cfg.breadthHighlightBands)
              : undefined,
          },
          PANE_MARK_ANCHOR_BREADTH,
          cfg.dates.length,
        ),
      );
      anchorNames.push(PANE_MARK_ANCHOR_BREADTH);
    }
    const rightSeries = shownSeries(cfg).find((s) => s.axis === "right");
    if (rightSeries && (cfg.rightMarkLines?.length || cfg.rightZones?.length)) {
      const loc = layout.locate(rightSeries);
      seriesOpts.push(
        buildPaneMarkAnchor(
          loc,
          {
            markArea: cfg.rightZones?.length ? zoneBands(cfg.rightZones, 0.08) : undefined,
            markLine: cfg.rightMarkLines?.length ? zoneMarkLines(cfg.rightMarkLines) : undefined,
          },
          PANE_MARK_ANCHOR_RIGHT,
          cfg.dates.length,
        ),
      );
      anchorNames.push(PANE_MARK_ANCHOR_RIGHT);
    }
  }

  const legendData: string[] | undefined =
    anchorNames.length > 0
      ? seriesOpts.map((s) => s.name as string).filter((n) => !anchorNames.includes(n))
      : undefined;

  return {
    tooltip: {
      trigger: "axis",
      // 归一化模式同时给出「相对窗口起点涨跌幅」，这才是要对比的那个数。
      valueFormatter: (v) =>
        v == null
          ? "-"
          : rebase
            ? `${Number(v).toFixed(1)} (${Number(v) >= 100 ? "+" : ""}${(Number(v) - 100).toFixed(1)}%)`
            : Number(v).toFixed(2),
    },
    // 跨格十字线联动：悬停任一格，其余格同一天也亮竖线。
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    legend: {
      type: "scroll",
      orient: "vertical",
      right: 6,
      top: 10,
      bottom: 64,
      textStyle: { fontSize: 11 },
      itemGap: 8,
      itemWidth: 16,
      itemHeight: 8,
      ...(legendData ? { data: legendData } : {}),
    },
    grid: layout.grids,
    xAxis: layout.xAxes,
    yAxis: layout.yAxes,
    dataZoom: [
      {
        type: "slider",
        xAxisIndex: allX,
        start: Math.max(0, 100 - cfg.startPercent),
        end: 100,
        bottom: 6,
        height: 20,
      },
      { type: "inside", xAxisIndex: allX },
    ],
    series: seriesOpts,
  };
}
