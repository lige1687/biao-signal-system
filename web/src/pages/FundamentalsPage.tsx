import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import SentimentPage from "./SentimentPage";
import NewsPage from "./NewsPage";
import HomeEnvironmentStrip from "../components/HomeEnvironmentStrip";
import "./reference-reading.css";
import { api, fundamentalsApi } from "../api/client";
import OverlayChart, { type OverlayMode, type OverlaySeries } from "../components/trend/OverlayChart";
import Sparkline from "../components/trend/Sparkline";
import MetricCard from "../components/trend/MetricCard";
import TrendChart from "../components/trend/TrendChart";
import TrendDrawer, { type DrawerState } from "../components/trend/TrendDrawer";
import SentimentProjectionCard from "../components/SentimentProjectionCard";
import MarketObservationCards from "../components/MarketObservationCards";
import MarketStylePanel from "../components/market-style/MarketStylePanel";
import { ObservationLibrary } from "../components/observation-library";
import ObservationMetric from "../components/observation-library/ObservationMetric";
import ObservationDetailDialog from "../components/observation-library/ObservationDetailDialog";
import { OBSERVATION_BY_ID } from "../components/observation-library/catalog";
import { fromValuation } from "../components/observation-library/metricData";
import { marketReferenceBands } from "../components/observation-library/marketReferenceBands";
import ErpReferenceCard from "../components/observation-library/ErpReferenceCard";
import { useProjectionSource, type ProjectionSource } from "../components/observation-library/projectionSources";
import { buildDrawer } from "../components/trend/drawer";
import { alignTo, unionDates } from "../components/trend/align";
import { fmt, pctClass } from "../utils/format";
import {
  isRealAShare,
  hasBreadth,
  AShareBar,
  AShareSourceLine,
  BreadthAsOf,
  fmtPct as fmtPctAD,
  fmtRatio as fmtRatioAD,
} from "../components/aShareBreadthView";
import {
  BREADTH_HIGHLIGHT_RULES,
  BREADTH_LINES,
  BREADTH_ZONES,
  ERP_CN_ZONES,
  ERP_US_ZONES,
  RATE_LOOKBACK_OPTIONS,
  MARKLINES,
  OVERLAY_MARKLINES,
  SOURCE_NOTES,
  ZONES,
  computeHighlightBands,
  findZone,
  type HighlightBand,
} from "../components/trend/zones";
import type {
  BreadthHistoryResponse,
  CommodityRatios,
  EtfItem,
  GlobalPanel,
  GlobalSentiment,
  GlobalSentimentSeries,
  MacroHistoryResponse,
  RatesHistoryResponse,
  RatesHistorySeries,
  RatesResponse,
  SentimentIngest,
} from "../types";

/** Small-chart reference lines share the same evidence-qualified definitions as the drawer. */
const SPARK_MARK: Record<string, number | null> = Object.fromEntries(
  Object.entries(MARKLINES).map(([key, lines]) => [key, lines[0]?.y ?? null]),
);

type MacroItem = {
  key: string;
  name_cn: string;
  period?: string | null;
  value: number | null;
  note_cn: string;
};

// ── 长周期叠加：利率/两融 × 股指（20 年级，dataZoom 滑动窗口）────────────

const OVERLAY_RANGES = [
  { key: "2y", label: "近2年", years: 2 },
  { key: "4y", label: "近4年", years: 4 },
  { key: "5y", label: "5年", years: 5 },
  { key: "10y", label: "10年", years: 10 },
  { key: "20y", label: "20年", years: 20 },
  { key: "all", label: "全部", years: 0 },
] as const;
type OverlayRange = (typeof OVERLAY_RANGES)[number]["key"];

/**
 * 把市场宽度历史对齐到叠图日期，输出可直接叠加的 breadth 序列。
 * 同时返回有效点数（用于退化判定）与最新 B50（用于卡片头部 chip）。
 * 退化：有效点 < 4 → 不画误导横线，由调用方显示「积累中」提示。
 * coverage 是给用户看的实话：宽度只覆盖哪一段、为什么没叠上去
 * ——指数是 20 年全史，宽度快照只有最近一年甚至几天，不说清就会显得「曲线不匹配」。
 */
function breadthOverlay(
  dates: string[],
  hist?: BreadthHistoryResponse,
): {
  series: OverlaySeries[];
  v20: (number | null)[];
  v50: (number | null)[];
  v200: (number | null)[];
  valid: number;
  last50: number | null;
  degenerate: boolean;
  coverage: string;
} {
  const empty = {
    series: [] as OverlaySeries[],
    v20: [] as (number | null)[],
    v50: [] as (number | null)[],
    v200: [] as (number | null)[],
    valid: 0,
    last50: null as number | null,
    degenerate: true,
    coverage: "无宽度快照",
  };
  if (!hist || hist.history.length === 0) return empty;
  const pick = (k: "breadth_20" | "breadth_50" | "breadth_200") => {
    const m = new Map(hist.history.map((p) => [p.date, p[k]]));
    return dates.map((d) => m.get(d) ?? null);
  };
  const v20 = pick("breadth_20");
  const v50 = pick("breadth_50");
  const v200 = pick("breadth_200");
  const valid = dates.filter((_, i) => v20[i] != null || v50[i] != null || v200[i] != null).length;
  const hit = dates.filter((_, i) => v20[i] != null || v50[i] != null || v200[i] != null);
  const window = hit.length ? `${hit[0]} ~ ${hit[hit.length - 1]}` : "无对齐点";
  // 退化判定：点数过少，或三条线均为恒值（如 SP500 历史为冻结占位值，
  // 否则会画出误导性的「横线」，复现此前 SP500 趋势图横线问题）。
  const span = (arr: (number | null)[]) => {
    const v = arr.filter((x): x is number => x != null);
    return v.length < 2 ? 0 : Math.max(...v) - Math.min(...v);
  };
  const allFlat = span(v20) < 1 && span(v50) < 1 && span(v200) < 1;
  const degenerate = valid < 4 || allFlat;
  if (degenerate) {
    const why = allFlat
      ? `${valid} 个点全为同一组冻结值（${window}）`
      : `仅 ${valid} 个有效点（${window}）`;
    return { series: [], v20, v50, v200, valid, last50: null, degenerate, coverage: `${why}，样本不足未叠加` };
  }
  let last50: number | null = null;
  for (let i = dates.length - 1; i >= 0; i--) {
    if (v50[i] != null) {
      last50 = v50[i];
      break;
    }
  }
  const series: OverlaySeries[] = [
    { name: "宽度20日", values: v20, color: BREADTH_LINES[0].color, axis: "breadth", dashed: true, lineWidth: 1, opacity: 0.45 },
    { name: "宽度50日", values: v50, color: BREADTH_LINES[1].color, axis: "breadth", dashed: false, lineWidth: 2.2, opacity: 1 },
    { name: "宽度200日", values: v200, color: BREADTH_LINES[2].color, axis: "breadth", dashed: true, lineWidth: 1, opacity: 0.45 },
  ];
  return { series, v20, v50, v200, valid, last50, degenerate, coverage: `宽度覆盖 ${window}（${valid} 个交易日）` };
}

/** 叠图卡片头部的当前宽度 chip：显示50日均线上方的股票比例。 */
function BreadthChip({ value, missing }: { value: number | null; missing?: boolean }) {
  if (missing) {
    return <span className="macro-chip muted-chip breadth-chip--missing">宽度：数据缺失</span>;
  }
  if (value == null) {
    return <span className="macro-chip muted-chip">宽度：积累中</span>;
  }
  const z = findZone(value, BREADTH_ZONES);
  return (
    <span className={`macro-chip ${z.tone}`}>宽度(50日) {value.toFixed(1)}% · {z.label}</span>
  );
}


/** Match observations on their actual dates; absent weeks or days remain null. */
function alignErp(dates: string[], source: ProjectionSource): (number | null)[] {
  if (source.isPending || source.error) return dates.map(() => null);
  const values = new Map(source.points.map(point => [point.date, point.value]));
  return dates.map(date => values.get(date) ?? null);
}

function erpStatus(source: ProjectionSource): string {
  if (source.isPending) return "股债利差读取中";
  if (source.error) return "股债利差来源读取失败";
  const last = source.points[source.points.length - 1];
  return last?.value == null ? "股债利差读数缺失" : `${source.sourceName} · 截至 ${last.date} · ${source.frequency === "weekly" ? "周频" : "日线含月频盈利输入"} · 百分点`;
}

function OverlaySection() {
  const cnErp = useProjectionSource("erp-cn");
  const usErp = useProjectionSource("erp-us");
  const { data, isLoading, error } = useQuery({
    queryKey: ["fundOverlay", 20],
    queryFn: () => fundamentalsApi.overlayHistory(20),
    staleTime: 12 * 3600_000,
    retry: 1,
  });
  const [range, setRange] = useState<OverlayRange>("2y");
  // 原始刻度看绝对水位，归一化看涨跌比（同一把尺子）。
  const [mode, setMode] = useState<OverlayMode>("raw");
  // 三张 600px 大图纵向堆叠太长，内部再分页签一次只看一张。
  const [panel, setPanel] = useState<"cn" | "us" | "margin" | "vix">("cn");
  // 6 条宽度规则的激活集：可同时多选，触发区间叠加到宽度格（0–100%）。
  // 同期数值条件仅按需选择，默认关闭；不是预测阈值。
  // 使用新版本偏好键，避免旧预测分区自动显示。
  const RULES_STORAGE_KEY = "biao-overlay-numeric-conditions-v2";
  const RULES_DEFAULT: readonly string[] = [];
  const RULES_ALL_OFF = "__ALL_OFF__";
  const [activeRules, setActiveRules] = useState<ReadonlySet<string>>(() => {
    try {
      const saved = localStorage.getItem(RULES_STORAGE_KEY);
      if (saved === RULES_ALL_OFF) return new Set();
      if (saved) {
        const arr = JSON.parse(saved);
        if (Array.isArray(arr) && arr.length > 0) return new Set(arr as string[]);
      }
    } catch { /* ignore corrupt storage */ }
    return new Set(RULES_DEFAULT as readonly string[]);
  });
  const toggleRule = (key: string) => {
    setActiveRules((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      try {
        const val = next.size === 0 ? RULES_ALL_OFF : JSON.stringify([...next]);
        localStorage.setItem(RULES_STORAGE_KEY, val);
      } catch { /* ignore */ }
      return next;
    });
  };
  // 宽度阈值口径（A股 / 美股各自独立、持久化防刷新丢失）：
  //   80/20 与 85/15 是原有数值查询选项，不是本轮验证的交易阈值。
  // 高亮是否显示的开关就是顶部的 6 条规则 chip（选中=显示、不选=不显示），无需额外总开关。
  const CN_THRESHOLD_KEY = "biao-overlay-cn-threshold";
  const US_THRESHOLD_KEY = "biao-overlay-us-threshold";
  const readThreshold = (key: string, fallback: "strict" | "standard"): "strict" | "standard" => {
    try {
      const v = localStorage.getItem(key);
      if (v === "standard" || v === "strict") return v;
    } catch { /* ignore corrupt storage */ }
    return fallback;
  };
  const [cnThreshold, setCnThreshold] = useState<"strict" | "standard">(() => readThreshold(CN_THRESHOLD_KEY, "standard"));
  const [usThreshold, setUsThreshold] = useState<"strict" | "standard">(() => readThreshold(US_THRESHOLD_KEY, "strict"));
  const setCnThresholdPersist = (v: "strict" | "standard") => {
    setCnThreshold(v);
    try { localStorage.setItem(CN_THRESHOLD_KEY, v); } catch { /* ignore */ }
  };
  const setUsThresholdPersist = (v: "strict" | "standard") => {
    setUsThreshold(v);
    try { localStorage.setItem(US_THRESHOLD_KEY, v); } catch { /* ignore */ }
  };
  const cnThresholds = cnThreshold === "standard" ? { hot: 80, cold: 20 } : { hot: 85, cold: 15 };
  const usThresholds = usThreshold === "standard" ? { hot: 80, cold: 20 } : { hot: 85, cold: 15 };
  const s = data?.series ?? {};

  // 市场宽度历史（真全A 来自收盘后预计算缓存；标普500 来自东财K线）。
  // 与指数同周期对齐后叠加到叠图第三轴，并在宽度轴标定义参照。
  const { data: cnBreadth } = useQuery({
    queryKey: ["overlayBreadth", "CN_ALL_A", 1260],
    queryFn: () => api.marketContextBreadthHistory("CN_ALL_A", 1260),
    staleTime: 12 * 3600_000,
    retry: 1,
  });
  const { data: usBreadth } = useQuery({
    queryKey: ["overlayBreadth", "SP500", 1260],
    queryFn: () => api.marketContextBreadthHistory("SP500", 1260),
    staleTime: 12 * 3600_000,
    retry: 1,
  });

  const cnDates = useMemo(
    () => unionDates(...[s.sse, s.hs300, s.kc50, s.kc100, s.cybz].filter(Boolean), { dates: cnErp.points.map(point => point.date) }),
    [s.sse, s.hs300, s.kc50, s.kc100, s.cybz, cnErp.points],
  );
  const usDates = useMemo(
    () => unionDates(...[s.sp500, s.nasdaq].filter(Boolean), { dates: usErp.points.map(point => point.date) }),
    [s.sp500, s.nasdaq, usErp.points],
  );

  /** 可视窗口占全序列百分比（echarts dataZoom start 换算）。 */
  const startPercent = (dates: string[]): number => {
    if (range === "all" || dates.length < 2) return 100;
    const years = OVERLAY_RANGES.find((r) => r.key === range)?.years ?? 10;
    const span = new Date(dates[dates.length - 1]).getTime() - new Date(dates[0]).getTime();
    if (span <= 0) return 100;
    // 注意：*100 必须在 Math.max(1, …) 内部——最小钳制的是「百分比下限 1%」，
    // 而非把 0~1 的比例钳成 1（否则所有档位都会退化成 100%，dataZoom 全展）。
    return Math.min(100, Math.max(1, ((years * 365.25 * 86400_000) / span) * 100));
  };

  const cnB = useMemo(() => breadthOverlay(cnDates, cnBreadth), [cnDates, cnBreadth]);
  const usB = useMemo(() => breadthOverlay(usDates, usBreadth), [usDates, usBreadth]);
  const cnDegenerate = cnB.degenerate;
  const usDegenerate = usB.degenerate;

  const cnSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "上证指数", values: alignTo(cnDates, s.sse), color: "#ea580c", axis: "left" },
      { name: "沪深300", values: alignTo(cnDates, s.hs300), color: "#2563eb", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      // 成长宽基配角线：点位口径与上证/300 差异大，原始刻度共轴只看形态，
      // 直接比涨跌切「涨跌比(=100)」；点图例可单独开关。
      { name: "科创50", values: alignTo(cnDates, s.kc50), color: "#9333ea", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      { name: "科创100", values: alignTo(cnDates, s.kc100), color: "#db2777", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      { name: "创业板指", values: alignTo(cnDates, s.cybz), color: "#16a34a", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      { name: "中国10Y", values: alignTo(cnDates, s.cn_10y), color: "#e36b1c", axis: "right" },
      // A股股债收益差（Fed Model 口径）：与 10Y 共用右轴，颜色区分；虚线表示这是辅助指标
      { name: "A股股债差", values: alignErp(cnDates, cnErp), connectNulls: false, color: "#0891b2", axis: "right", dashed: true, lineWidth: 1.4, opacity: 0.95 },
      ...(cnDegenerate ? [] : cnB.series),
    ],
    [cnDates, s.sse, s.hs300, s.kc50, s.kc100, s.cybz, s.cn_10y, cnErp, cnDegenerate, cnB.series],
  );
  const usSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "标普500", values: alignTo(usDates, s.sp500), color: "#2563eb", axis: "left" },
      { name: "纳斯达克", values: alignTo(usDates, s.nasdaq), color: "#7c3aed", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      { name: "美国10Y", values: alignTo(usDates, s.us_10y), color: "#e36b1c", axis: "right" },
      // 美股股债收益差：同上，与 10Y 共用右轴
      { name: "美股股债差", values: alignErp(usDates, usErp), connectNulls: false, color: "#0891b2", axis: "right", dashed: true, lineWidth: 1.4, opacity: 0.95 },
      ...(usDegenerate ? [] : usB.series),
    ],
    [usDates, s.sp500, s.nasdaq, s.us_10y, usErp, usDegenerate, usB.series],
  );
  // 美股 × VIX 映射：VIX 来自 rates-history（与页面级查询同 key，共享缓存不重拉）。
  const { data: ratesHistLocal } = useQuery({
    queryKey: ["fundamentalsRatesHistory", 7300],
    queryFn: () => fundamentalsApi.ratesHistory(7300),
    staleTime: 30 * 60_000,
  });
  const vixSer = ratesHistLocal?.series?.vix;
  const vixDates = useMemo(
    () => unionDates(...[s.sp500, vixSer].filter((x): x is RatesHistorySeries => !!x)),
    [s.sp500, vixSer],
  );
  const vixSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "标普500", values: alignTo(vixDates, s.sp500), color: "#2563eb", axis: "left" },
      { name: "VIX", values: alignTo(vixDates, vixSer), color: "#e33d47", axis: "right", lineWidth: 1.6 },
    ],
    [vixDates, s.sp500, vixSer],
  );

  const marginSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "上证指数", values: alignTo(cnDates, s.sse), color: "#ea580c", axis: "left" },
      { name: "沪深300", values: alignTo(cnDates, s.hs300), color: "#2563eb", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      {
        name: "融资余额占流通市值比",
        values: alignTo(cnDates, s.margin_rzyezb),
        color: "#e33d47",
        axis: "right",
      },
    ],
    [cnDates, s.sse, s.hs300, s.margin_rzyezb],
  );

  // 把当前激活规则展开为两套高亮色带：A 股/美股各自用独立阈值（卡片内可切换）。
  // 退化（有效点 <4）/ rebase（宽度线被剔除）时强制空数组，避免脏数据染色。
  const cnBands = useMemo<HighlightBand[]>(
    () =>
      !cnDegenerate && mode !== "rebase"
        ? computeHighlightBands(activeRules, "CN", cnDates, cnB.v20, cnB.v50, cnB.v200, cnThresholds)
        : [],
    [activeRules, cnDegenerate, mode, cnDates, cnB.v20, cnB.v50, cnB.v200, cnThresholds],
  );
  const usBands = useMemo<HighlightBand[]>(
    () =>
      !usDegenerate && mode !== "rebase"
        ? computeHighlightBands(activeRules, "US", usDates, usB.v20, usB.v50, usB.v200, usThresholds)
        : [],
    [activeRules, usDegenerate, mode, usDates, usB.v20, usB.v50, usB.v200, usThresholds],
  );
  const activeRuleCount = activeRules.size;

  if (isLoading) {
    return (
      <div className="card-skeleton" style={{ height: 220 }}>
        <div className="muted" style={{ padding: 12 }}>
          首次加载需翻页拉取 20 年全史（约 15 秒），之后 12 小时走缓存…
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="fund-errors">长周期叠加加载失败：{(error as Error | undefined)?.message ?? "未知错误"}</div>
    );
  }

  return (
    <div className="overlay-block">
      <div className="overlay-toolbar">
        <span className="muted">可视窗口：</span>
        {OVERLAY_RANGES.map((r) => (
          <button
            key={r.key}
            className={`ma-toggle${range === r.key ? " on" : ""}`}
            onClick={() => setRange(r.key)}
          >
            {r.label}
          </button>
        ))}
        <span className="muted" style={{ marginLeft: 10 }}>纵轴：</span>
        <button
          className={`ma-toggle${mode === "raw" ? " on" : ""}`}
          onClick={() => setMode("raw")}
          title="指数走左轴、利率走右轴，分别读取原值"
        >
          原始刻度
        </button>
        <button
          className={`ma-toggle${mode === "rebase" ? " on" : ""}`}
          onClick={() => setMode("rebase")}
          title="全部除以可视窗口起点×100，直接比较涨跌幅"
        >
          涨跌比(=100)
        </button>
        {data.errors.length > 0 && (
          <span className="muted" style={{ marginLeft: 8 }}>{data.errors.join("；")}</span>
        )}
      </div>

      <div className="overlay-toolbar overlay-toolbar--rules">
        <span className="muted">高亮条件（多选，对 A股/美股两图共用；勾选即显示对应色带）：</span>
        {BREADTH_HIGHLIGHT_RULES.map((r) => {
          const on = activeRules.has(r.key);
          return (
            <button
              key={r.key}
              type="button"
              className={`breadth-rule-chip${on ? " on" : ""}`}
              title={r.full}
              aria-pressed={on}
              style={on ? { borderColor: r.color, color: r.color } : undefined}
              onClick={() => toggleRule(r.key)}
            >
              <span className="breadth-rule-dot" style={{ background: r.color }} />
              {r.short}
            </button>
          );
        })}
        {activeRuleCount > 0 && (
          <button
            type="button"
            className="breadth-rule-chip breadth-rule-chip--clear"
            title="清除所有高亮"
            onClick={() => setActiveRules(new Set())}
          >
            × 清除
          </button>
        )}
        <span className="muted" style={{ marginLeft: 6 }}>
          阈值在各自卡片内可切（A股默认 80/20、美股默认 85/15）。
        </span>
      </div>

      <div className="fund-hint-row">
        {mode === "raw"
          ? "原始刻度：指数（左轴实线）+ 利率/占比（中轴色带）+ 宽度（底轴 0–100%）。三格共享时间轴，拖动底部滑块联动。要比涨跌形态切「涨跌比」。"
          : "涨跌比：以窗口内最早共同有数据日为 100，纵轴对数刻度，相同垂直距离 = 相同涨跌倍数。此模式下利率绝对水位与宽度线隐藏。"}
      </div>

      <div className="overlay-toolbar">
        <span className="muted">图：</span>
        <button type="button" className={`ma-toggle${panel === "cn" ? " on" : ""}`} onClick={() => setPanel("cn")}>A股 × 10Y</button>
        <button type="button" className={`ma-toggle${panel === "us" ? " on" : ""}`} onClick={() => setPanel("us")}>美股 × 10Y</button>
        <button type="button" className={`ma-toggle${panel === "margin" ? " on" : ""}`} onClick={() => setPanel("margin")}>A股 × 两融</button>
        <button type="button" className={`ma-toggle${panel === "vix" ? " on" : ""}`} onClick={() => setPanel("vix")}>美股 × VIX</button>
      </div>

      {panel === "cn" && (
      <div className="overlay-card">
        <h4>
          <span>A股 × 10Y国债</span>
          <BreadthChip value={cnB.last50} />
        </h4>
        <div className="overlay-market-controls">
          <span className="muted">阈值</span>
          <button
            type="button"
            className={`ma-toggle${cnThreshold === "standard" ? " on" : ""}`}
            onClick={() => setCnThresholdPersist("standard")}
            title="按80%和20%选择同期数值，不表示未来顶底"
          >
            80/20
          </button>
          <button
            type="button"
            className={`ma-toggle${cnThreshold === "strict" ? " on" : ""}`}
            onClick={() => setCnThresholdPersist("strict")}
            title="按85%和15%选择同期数值，不表示未来顶底"
          >
            85/15
          </button>
        </div>
        <OverlayChart
          dates={cnDates}
          series={cnSeries}
          startPercent={startPercent(cnDates)}
          mode={mode}
          breadthMarkLines={cnDegenerate ? undefined : MARKLINES.breadth}
          breadthHighlightBands={cnBands}
          // 仅保留有定义依据的参考线。
          rightMarkLines={[...OVERLAY_MARKLINES.cn_10y, ...OVERLAY_MARKLINES.erp_cn]}
          // 不用经验分位推断机会或风险。
          rightZones={ERP_CN_ZONES}
          height={600}
        />
        <div className="fund-hint-row">
          左轴：上证（实线主角）；沪深300 / 科创50 / 科创100 / 创业板指为虚线配角
          （科创50 自 2019-12 基日、科创100 自 2023-08、创业板指自 2010-06 起），
          点图例可开关。五指数点位口径不同，直接比涨跌请切上方「涨跌比(=100)」。
          右轴实线：中国10Y；虚线：沪深300盈利收益率减国债收益率，零线表示两者相等。{erpStatus(cnErp)}。
          宽度：实线 = B50，虚线 = B20/B200；可选数值条件
          <strong>{cnThreshold === "standard" ? "80/20" : "85/15"}</strong>（本卡可切）。{cnB.coverage}。
        </div>
      </div>
      )}

      {panel === "us" && (
      <div className="overlay-card">
        <h4>
          <span>美股 × 10Y国债</span>
          <BreadthChip value={usB.last50} missing={usDegenerate} />
        </h4>
        <div className="overlay-market-controls">
          <span className="muted">阈值</span>
          <button
            type="button"
            className={`ma-toggle${usThreshold === "standard" ? " on" : ""}`}
            onClick={() => setUsThresholdPersist("standard")}
            title="按80%和20%选择同期数值，不表示未来顶底"
          >
            80/20
          </button>
          <button
            type="button"
            className={`ma-toggle${usThreshold === "strict" ? " on" : ""}`}
            onClick={() => setUsThresholdPersist("strict")}
            title="按85%和15%选择同期数值，不表示未来顶底"
          >
            85/15
          </button>
        </div>
        {usDegenerate && (
          <div className="breadth-missing-notice">
            <strong>美股宽度数据异常：</strong>
            标普500 的 B20/B50/B200 暂未正常加载（可能后端宽度历史为空或退化）。
            可取消上方高亮条件的勾选以隐藏色带，或检查后端 SP500 宽度是否回填成功。A股高亮不受影响。
          </div>
        )}
        <OverlayChart
          dates={usDates}
          series={usSeries}
          startPercent={startPercent(usDates)}
          mode={mode}
          breadthMarkLines={usDegenerate ? undefined : MARKLINES.breadth}
          breadthHighlightBands={usBands}
          rightMarkLines={[...OVERLAY_MARKLINES.us_10y, ...OVERLAY_MARKLINES.erp_us]}
          rightZones={ERP_US_ZONES}
          height={600}
        />
        <div className="fund-hint-row">
          右轴实线：美国10Y；虚线：标普500盈利收益率减国债收益率，零线表示两者相等。{erpStatus(usErp)}。
          标普500仅近10年数据，纳斯达克为来源可用历史。美股宽度数值条件
          <strong>{usThreshold === "standard" ? "80/20" : "85/15"}</strong>
          （本卡可切）。{usB.coverage}{usDegenerate && "（宽度未叠加）"}。
        </div>
      </div>
      )}

      {panel === "margin" && (
      <div className="overlay-card">
        <h4><span>A股 × 融资余额占比</span></h4>
        <OverlayChart
          dates={cnDates}
          series={marginSeries}
          height={520}
          rightName="占比 %"
          startPercent={startPercent(cnDates)}
          mode={mode}
          rightMarkLines={OVERLAY_MARKLINES.margin_rzyezb}
          rightZones={ZONES.margin_rzyezb}
        />
        <div className="fund-hint-row">
          两融数据始于2010-03；占比表示融资余额相对流通市值的大小，未建立固定机会或风险线。
        </div>
      </div>
      )}

      {panel === "vix" && (
      <div className="overlay-card">
        <h4><span>美股 × VIX 恐慌指数</span></h4>
        <OverlayChart
          dates={vixDates}
          series={vixSeries}
          height={520}
          rightName="VIX"
          startPercent={Math.min(100, Math.max(1, (10 * 365.25) / (
            (new Date(vixDates[vixDates.length - 1]).getTime() - new Date(vixDates[0]).getTime()) / 86400000 || 1
          ) * 100))}
          mode={mode}
          rightMarkLines={MARKLINES.vix}
        />
        <div className="fund-hint-row">
          左轴标普500（近 10 年）；右轴 VIX。月度相关性：同期 <strong>-0.78</strong>（构造性镜像——VIX 本身由标普期权定价反推，见「相关性速查」卡），
          指数领先 VIX 变化 +0.28（旧研究窗口）。VIX只描述期权市场对未来约30天波动幅度的预期；不设未经验证的固定顶底线。
        </div>
      </div>
      )}
    </div>
  );
}

// ── 利率面板：5 个指标卡（小图点开大图）──────────────────────────────────

function RatesSection({ data, hist }: {
  data: RatesResponse;
  hist?: RatesHistoryResponse;
}) {
  const valuationHistory = useQuery({ queryKey: ["fundamentalsValuationHistory"],
    queryFn: () => fundamentalsApi.valuationHistory(), staleTime: 5 * 60_000, retry: false });
  const [openValuation, setOpenValuation] = useState<"hs300-pe" | "sp500-cape" | null>(null);
  const valuationItem = openValuation ? OBSERVATION_BY_ID.get(openValuation) : undefined;
  const valuationCard = (id: "hs300-pe" | "sp500-cape") => {
    const reading = fromValuation(data, id, valuationHistory.data?.series[id === "hs300-pe" ? "pe_cn" : "cape_us"]);
    const bands = marketReferenceBands(id, reading?.points ?? []);
    const rank = bands?.kind === "valuation" ? bands.latest?.percentile : null;
    const date = reading?.date ? `${reading.dateLabel} ${reading.date} · ` : "";
    return <MetricCard label={OBSERVATION_BY_ID.get(id)?.label ?? id}
      value={reading?.value == null ? "暂不可用" : `${reading.value.toFixed(2)} 倍`}
      sub={date + (rank == null ? valuationHistory.isPending ? "读取历史参照…" : "近10年分位暂不可用" : `近10年 P${rank.toFixed(1)}`)}
      zoneLabel={bands?.kind === "valuation" ? bands.position ?? undefined : undefined}
      sparkValues={reading?.points.slice(-24).flatMap(point => point.value == null ? [] : [point.value])}
      onOpen={() => setOpenValuation(id)} />;
  };
  const t = data.treasury;
  const s = hist?.series ?? {};
  // 卡片小图固定看最近 2 年（≈504 个交易日），与趋势抽屉的缩放窗口互不影响。
  const spark = (key: string) => s[key]?.values.slice(-504) ?? [];
  // 只存「打开了哪个指标」，序列数据渲染时从当前 hist 取。
  const [openMeta, setOpenMeta] = useState<{
    key: string;
    title: string;
    cur: number | null;
    curDisplay?: string;
  } | null>(null);
  const open = (key: string, title: string, cur: number | null, curDisplay?: string) => () => {
    const ser = s[key];
    if (!ser || ser.dates.length < 2) return;
    setOpenMeta({ key, title, cur, curDisplay });
  };
  const drawer = useMemo(() => {
    if (!openMeta) return null;
    const ser = s[openMeta.key];
    if (!ser || ser.dates.length < 2) return null;
    return buildDrawer({
      title: openMeta.title,
      cur: openMeta.cur,
      unit: ser.unit,
      label: ser.label,
      dates: ser.dates,
      values: ser.values,
      key: openMeta.key,
      periodLabel: "日",
      curDisplay: openMeta.curDisplay,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openMeta, hist]);

  const spread = t.cn_us_spread_10y;
  return (
    <div className="rates-grid">
      <MetricCard
        label="中 10Y 国债"
        value={fmt(t.cn.cn_10y, 3, "%")}
        sub={`2Y ${fmt(t.cn.cn_2y, 3)} · 5Y ${fmt(t.cn.cn_5y, 3)} · 30Y ${fmt(t.cn.cn_30y, 3)}`}
        zoneLabel={findZone(t.cn.cn_10y, ZONES.cn_10y).label}
        zoneTone={findZone(t.cn.cn_10y, ZONES.cn_10y).tone}
        sparkValues={spark("cn_10y")}
        markY={SPARK_MARK.cn_10y}
        onOpen={open("cn_10y", "中国 10Y 国债收益率", t.cn.cn_10y)}
      />
      <MetricCard
        label="美 10Y 国债"
        value={fmt(t.us.us_10y, 3, "%")}
        sub={`2Y ${fmt(t.us.us_2y, 3)} · 5Y ${fmt(t.us.us_5y, 3)} · 30Y ${fmt(t.us.us_30y, 3)}`}
        zoneLabel={findZone(t.us.us_10y, ZONES.us_10y).label}
        zoneTone={findZone(t.us.us_10y, ZONES.us_10y).tone}
        sparkValues={spark("us_10y")}
        markY={SPARK_MARK.us_10y}
        onOpen={open("us_10y", "美国 10Y 国债收益率", t.us.us_10y)}
      />
      <MetricCard
        label="中美 10Y 利差"
        value={fmt(spread, 2, "%")}
        sub="中国10Y减美国10Y；负值仅表示美债名义收益率更高"
        zoneLabel={findZone(spread, ZONES.cn_us_spread_10y).label}
        zoneTone={findZone(spread, ZONES.cn_us_spread_10y).tone}
        sparkValues={spark("cn_us_spread_10y")}
        markY={SPARK_MARK.cn_us_spread_10y}
        onOpen={open("cn_us_spread_10y", "中美 10 年利差", spread)}
      />
      <MetricCard
        label="VIX 恐慌指数"
        value={data.vix == null ? "暂不可用" : data.vix.value.toFixed(2)}
        sub={
          data.vix == null
            ? "yfinance 限流，稍后刷新重试"
            : data.vix.value > 30
              ? "预期波动较高；不表示价格方向"
              : data.vix.value < 15
                ? "预期波动较低；不表示价格方向"
                : "处于原页面15–30参考范围"
        }
        zoneLabel={data.vix == null ? undefined : findZone(data.vix.value, ZONES.vix).label}
        zoneTone={data.vix == null ? undefined : findZone(data.vix.value, ZONES.vix).tone}
        sparkValues={spark("vix")}
        markY={SPARK_MARK.vix}
        onOpen={open("vix", "VIX 恐慌指数", data.vix?.value ?? null)}
      />
      <MetricCard
        label="两融杠杆（占流通市值比）"
        value={data.margin?.rzyezb_pct == null ? "暂不可用" : `${data.margin.rzyezb_pct.toFixed(2)}%`}
        sub={
          data.margin == null
            ? "东财数据中心暂不可用"
            : data.margin.rzrqye_yi == null
              ? "两融余额缺数"
              : `两融余额 ${(data.margin.rzrqye_yi / 10000).toFixed(2)}万亿 · 融资 ${data.margin.rzye_yi?.toFixed(0)}亿 · 买入 ${data.margin.buy_yi?.toFixed(0)}亿`
        }
        zoneLabel={
          data.margin?.rzyezb_pct == null
            ? undefined
            : findZone(data.margin.rzyezb_pct, ZONES.margin_rzyezb).label
        }
        zoneTone={
          data.margin?.rzyezb_pct == null
            ? undefined
            : findZone(data.margin.rzyezb_pct, ZONES.margin_rzyezb).tone
        }
        sparkValues={spark("margin_rzyezb")}
        markY={SPARK_MARK.margin_rzyezb}
        onOpen={open(
          "margin_rzyezb",
          "融资余额占流通市值比",
          data.margin?.rzyezb_pct ?? null,
          data.margin?.rzyezb_pct == null
            ? undefined
            : `${data.margin.rzyezb_pct.toFixed(2)}%（两融余额 ${data.margin.rzrqye_yi == null ? "-" : `${(data.margin.rzrqye_yi / 10000).toFixed(2)}万亿`}）`,
        )}
      />
      <ErpReferenceCard market="us" />
      {valuationCard("sp500-cape")}
      <ErpReferenceCard market="cn" />
      {valuationCard("hs300-pe")}
      <div className="macro-card metric-card">
        <div className="macro-head"><span className="macro-name">纳斯达克100 PE_TTM</span></div>
        <ObservationMetric id="nasdaq100-pe" />
      </div>
      {valuationItem && <ObservationDetailDialog item={valuationItem} onClose={() => setOpenValuation(null)} />}
      <HyOasCard />
      {drawer && (
        <TrendDrawer
          {...drawer}
          periodOptions={RATE_LOOKBACK_OPTIONS}
          activeDays={1095}
          resetKey={openMeta?.key}
          onClose={() => setOpenMeta(null)}
        />
      )}
    </div>
  );
}

// ── 信用利差卡（FRED 高收益债 OAS，自包含取数与抽屉）──────────────────────
// 视频组合：信用利差与 10Y 做减法、搭配 VIX 评估系统性风险，故放在利率区。
function HyOasCard() {
  const { data: us } = useUsMacro();
  const [hyDrawer, setHyDrawer] = useState<DrawerState>(null);
  const hy = us?.items.find((it) => it.key === "hy_oas");
  const hySer = us?.series?.["hy_oas"];
  const hyZone = hy?.value == null ? undefined : findZone(hy.value, ZONES.hy_oas ?? []);
  return (
    <>
      <MetricCard
        label="信用利差（高收益债 OAS）"
        value={hy?.value == null ? "暂不可用" : `${hy.value.toFixed(2)}%`}
        sub={hy ? `日更 · ${hy.date ?? "-"} · 高收益债相对国债的额外收益率；未建立固定顶底线` : "FRED 拉取中，稍后刷新重试"}
        zoneLabel={hyZone?.label}
        zoneTone={hyZone?.tone}
        sparkValues={hySer?.values}
        markY={SPARK_MARK.hy_oas}
        onOpen={() => {
          if (!hySer || hySer.dates.length < 2) return;
          setHyDrawer(
            buildDrawer({
              title: "高收益债信用利差（OAS）",
              cur: hy?.value ?? null,
              unit: hySer.unit,
              label: hySer.label,
              dates: hySer.dates,
              values: hySer.values,
              key: "hy_oas",
              periodLabel: "日",
              curDisplay: hy?.value == null ? "-" : `${hy.value.toFixed(2)}%`,
            }),
          );
        }}
      />
      {hyDrawer && <TrendDrawer {...hyDrawer} onClose={() => setHyDrawer(null)} />}
    </>
  );
}

// ── 市场面板：宽度小图卡片，点开看 20/50/200 大图 ────────────────────────

function BreadthSparkCard({
  panel,
  onOpen,
}: {
  panel: GlobalPanel;
  onOpen: (d: DrawerState) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["breadthHistory", panel.market_id, 1260],
    queryFn: () => api.marketContextBreadthHistory(panel.market_id, 1260),
    staleTime: 60_000,
  });
  const points = data?.history ?? [];
  const b50 = points
    .map((p) => p.breadth_50)
    .filter((v): v is number => v != null);
  const cur = panel.breadth_50;
  const zone = findZone(cur, BREADTH_ZONES);

  const open = () => {
    if (points.length < 2) return;
    onOpen({
      title: `${panel.display_name} 宽度趋势`,
      subtitle: `当前 50日 ${cur != null ? `${cur.toFixed(1)}%` : "-"} · ${zone.label}（近 ${points.length} 日）`,
      dates: points.map((p) => p.date),
      series: BREADTH_LINES.map((ln, i) => ({
        name: ln.name,
        values: points.map((p) => [p.breadth_20, p.breadth_50, p.breadth_200][i]),
        color: ln.color,
      })),
      unit: "%",
      markLines: MARKLINES.breadth,
      yRange: [0, 100],
      zones: BREADTH_ZONES,
      // 全 A 历史有 8109 日（≈32 年），默认只展开最近 756 日（≈3 年），
      // 用户可滚轮/双指捏合缩小看完整 32 年。
      defaultWindowDays: 756,
      footnote:
        "宽度 = 站上 N 个交易日均线的个股占比。50日读数描述上涨参与范围；20/80 是观察参考范围，不能单凭它判断短期顶底。" +
        SOURCE_NOTES.breadth,
    });
  };

  if (isRealAShare(panel) && !hasBreadth(panel)) {
    return (
      <div className="macro-card metric-card">
        <div className="macro-head">
          <span className="macro-name">{panel.display_name} 真全A涨跌家数</span>
        </div>
        <AShareBar p={panel} />
        <div className="macro-value">
          {panel.up != null ? `${panel.up}` : "-"} 涨 / {panel.down != null ? `${panel.down}` : "-"} 跌
        </div>
        <div className="macro-note">
          上涨占比 {fmtPctAD(panel.up_pct)} · 涨跌比 {fmtRatioAD(panel.adv_dec_ratio)}
        </div>
        <AShareSourceLine p={panel} />
        <BreadthAsOf p={panel} />
      </div>
    );
  }

  // 全部宽度缺失时（快照行是空壳）：明确说"中断+恢复方式"，不摆一张
  // 只有横杠的空卡让用户以为页面坏了（2026-09-07 用户截图反馈）。
  if (cur == null) {
    return (
      <div className="macro-card metric-card">
        <div className="macro-head">
          <span className="macro-name">{panel.display_name} 宽度</span>
          <span className="macro-chip muted-chip">数据中断</span>
        </div>
        <div className="macro-note" style={{ lineHeight: 1.7 }}>
          宽度数据暂不可用（成分股行情源中断）。<br />
          <span className="muted">
            宽度 = 指数成分股里站上 N 日均线的比例，用来判断市场整体冷热。
            数据恢复后本卡自动显示。
          </span>
        </div>
        {b50.length >= 2 && (
          <>
            <div className="macro-note">历史最后读数（{points[points.length - 1]?.date}）：</div>
            <Sparkline values={b50} height={56} />
          </>
        )}
      </div>
    );
  }

  return (
    <div className="macro-card metric-card clickable" onClick={open}>
      <div className="macro-head">
        <span className="macro-name">{panel.display_name} 宽度</span>
        <span className={`macro-chip ${zone.tone}`}>{zone.label}</span>
      </div>
      <div className="macro-value">{cur != null ? `${cur.toFixed(1)}%` : "-"}</div>
      <div className="macro-note">
        20日 {panel.breadth_20?.toFixed(0) ?? "-"}% · 200日 {panel.breadth_200?.toFixed(0) ?? "-"}%
        {(panel.breadth_as_of || panel.breadth_trading_day) && (
          <span className="muted">（{(panel.breadth_as_of || panel.breadth_trading_day) as string}）</span>
        )}
      </div>
      {b50.length >= 2 ? (
        <Sparkline values={b50} height={56} />
      ) : (
        <div className="sparkline-muted">{isLoading ? "加载历史…" : "暂无历史"}</div>
      )}
    </div>
  );
}

function MarketSection({ onOpen }: { onOpen: (d: DrawerState) => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["marketContextGlobalStrip"],
    queryFn: () => api.marketContextGlobalStrip(),
    staleTime: 60_000,
  });
  if (isLoading) return <div className="card-skeleton" style={{ height: 180 }} />;
  if (error || !data) return <div className="fund-errors">市场宽度加载失败</div>;
  return (
    <div className="breadth-trends">
      {data.panels.map((p, idx) => (
        <BreadthSparkCard key={`${p.market_id}-${idx}`} panel={p} onOpen={onOpen} />
      ))}
      <SentimentCard sentiment={data.sentiment} onOpen={onOpen} />
    </div>
  );
}

// ── 投资者情绪（NAAIM/AAII，来自 LEI_SENTIMENT_ROOT，与 Streamlit 同源）────

function SentimentRow({
  kind,
  s,
  title,
  sparkValues,
  onOpen,
}: {
  kind: "naaim" | "aaii";
  s: GlobalSentimentSeries;
  title: string;
  sparkValues?: number[];
  onOpen?: () => void;
}) {
  const tone = "neutral";
  const delayed =
    s.license_status != null && s.license_status.toLowerCase().includes("public_delayed");
  const clickable = !!onOpen && (sparkValues?.length ?? 0) >= 2;
  return (
    <div
      className={`sentiment-row${clickable ? " clickable" : ""}`}
      onClick={clickable ? onOpen : undefined}
      title={clickable ? "点开历史大图（含分界线与区间说明）" : undefined}
    >
      <div className="sentiment-row-head">
        <span className="sentiment-name">{title}</span>
        <span className={`macro-chip ${tone}`}>调查读数</span>
      </div>
      {sparkValues && sparkValues.length >= 2 ? (
        <Sparkline
          values={sparkValues}
          height={40}
          markY={kind === "naaim" ? null : 0}
          color={kind === "naaim" ? "#2563eb" : "#7c3aed"}
        />
      ) : null}
      <div className="sentiment-metrics">
        {kind === "naaim" ? (
          <>
            <span>暴露 {fmt(s.exposure_index, 1)}</span>
            <span>百分位 {fmt(s.percentile, 0, "%")}</span>
          </>
        ) : (
          <>
            <span>多 {fmt(s.bullish, 0)}%</span>
            <span>中 {fmt(s.neutral, 0)}%</span>
            <span>空 {fmt(s.bearish, 0)}%</span>
            <span>多空差 {fmt(s.bull_bear, 0, "%")}</span>
          </>
        )}
      </div>
      <div className="sentiment-meta">
        调查周 {s.survey_week ?? "—"}
        {s.current_eligible ? "" : " · 数据过期"}
        {delayed ? " · 延迟数据" : ""}
      </div>
    </div>
  );
}

/** 空序列引导行：常规路径是每周四 launchd 自动抓取；抓取失败时用这里手动补录（同周覆盖自动值）。 */
function SentimentEmpty({ name, onAdd }: { name: string; onAdd: () => void }) {
  return (
    <div className="sentiment-row sentiment-empty">
      <span>{name}：暂无读数（每周四自动抓取；失败时手动补录）</span>
      <button type="button" className="btn mini" onClick={onAdd}>
        补录{name}
      </button>
    </div>
  );
}

/** 本周一（本地日期），作为调查周默认起点。 */
function mondayOfCurrentWeek(): string {
  const d = new Date();
  const day = d.getDay(); // 0=周日
  const diff = day === 0 ? -6 : 1 - day;
  const mon = new Date(d.getFullYear(), d.getMonth(), d.getDate() + diff);
  const m = String(mon.getMonth() + 1).padStart(2, "0");
  const dd = String(mon.getDate()).padStart(2, "0");
  return `${mon.getFullYear()}-${m}-${dd}`;
}

/** 调查周所在周四（NAAIM 07:00 / AAII 08:00 UTC），与 ingest 脚本默认发布时间一致。 */
function releaseHint(surveyWeek: string, series: "naaim" | "aaii"): string {
  if (!surveyWeek) return "";
  const d = new Date(`${surveyWeek}T00:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  const diff = (4 - d.getDay() + 7) % 7;
  const th = new Date(d.getFullYear(), d.getMonth(), d.getDate() + diff);
  const m = String(th.getMonth() + 1).padStart(2, "0");
  const dd = String(th.getDate()).padStart(2, "0");
  const hh = series === "naaim" ? "07:00" : "08:00";
  return `${th.getFullYear()}-${m}-${dd} ${hh}:00 UTC`;
}

/** 手动录入一期情绪读数（POST /market-context/sentiment）。 */
function SentimentUpdateForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [series, setSeries] = useState<"naaim" | "aaii">("naaim");
  const [surveyWeek, setSurveyWeek] = useState(mondayOfCurrentWeek());
  const [exposure, setExposure] = useState("");
  const [bullish, setBullish] = useState("");
  const [neutral, setNeutral] = useState("");
  const [bearish, setBearish] = useState("");
  const [availableAt, setAvailableAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (p: SentimentIngest) => api.updateSentiment(p),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketContextGlobalStrip"] });
      onDone();
    },
    onError: (e: Error) => setError(e.message),
  });

  const submit = () => {
    setError(null);
    const payload: SentimentIngest = {
      series,
      survey_week: surveyWeek,
      exposure: series === "naaim" ? Number(exposure) : null,
      bullish: series === "aaii" ? Number(bullish) : null,
      neutral: series === "aaii" ? Number(neutral) : null,
      bearish: series === "aaii" ? Number(bearish) : null,
      available_at: availableAt.trim() || null,
    };
    mutation.mutate(payload);
  };

  const naaimOk = exposure.trim() !== "";
  const aaiiOk = bullish.trim() !== "" && neutral.trim() !== "" && bearish.trim() !== "";
  const canSubmit = (series === "naaim" ? naaimOk : aaiiOk) && availableAt.trim() !== "";

  return (
    <div className="sentiment-update-form">
      <div className="sentiment-form-row">
        <span className="sentiment-form-label">序列</span>
        <div className="seg">
          <button type="button" className={`seg-btn${series === "naaim" ? " on" : ""}`} onClick={() => setSeries("naaim")}>NAAIM 机构</button>
          <button type="button" className={`seg-btn${series === "aaii" ? " on" : ""}`} onClick={() => setSeries("aaii")}>AAII 散户</button>
        </div>
      </div>

      <div className="sentiment-form-row">
        <label className="sentiment-form-label" htmlFor="sw">调查周</label>
        <input id="sw" type="date" value={surveyWeek} onChange={(e) => setSurveyWeek(e.target.value)} />
        <span className="sentiment-form-hint">默认本周一；常见周四安排仅供查证：{releaseHint(surveyWeek, series)}</span>
      </div>

      {series === "naaim" ? (
        <div className="sentiment-form-row">
          <label className="sentiment-form-label" htmlFor="exp">暴露指数</label>
          <input id="exp" type="number" step="0.1" value={exposure} placeholder="如 72.5" onChange={(e) => setExposure(e.target.value)} />
          <span className="sentiment-form-hint">NAAIM 平均多头暴露（典型 0–100）</span>
        </div>
      ) : (
        <div className="sentiment-form-row">
          <span className="sentiment-form-label">多/中/空 %</span>
          <div className="sentiment-triple">
            <input type="number" value={bullish} placeholder="看多" onChange={(e) => setBullish(e.target.value)} />
            <input type="number" value={neutral} placeholder="中性" onChange={(e) => setNeutral(e.target.value)} />
            <input type="number" value={bearish} placeholder="看空" onChange={(e) => setBearish(e.target.value)} />
          </div>
        </div>
      )}

      <div className="sentiment-form-row">
        <label className="sentiment-form-label" htmlFor="av">已核实发布时间</label>
        <input id="av" type="text" required value={availableAt} placeholder="按来源填写，不以调查周推算" onChange={(e) => setAvailableAt(e.target.value)} />
      </div>

      {error && <div className="sentiment-form-error">写入失败：{error}</div>}

      <div className="sentiment-form-actions">
        <button type="button" className="btn primary" disabled={!canSubmit || mutation.isPending} onClick={submit}>
          {mutation.isPending ? "保存中…" : "保存并刷新"}
        </button>
        <button type="button" className="btn" onClick={onDone}>取消</button>
      </div>
    </div>
  );
}

function SentimentCard({
  sentiment,
  onOpen,
}: {
  sentiment?: GlobalSentiment;
  onOpen: (d: DrawerState) => void;
}) {
  const [editing, setEditing] = useState(false);
  // 历史曲线：与卡片同源（同一后端加载器），有 ≥2 期数据即出小图，点行开大图。
  const { data: naaimHist } = useQuery({
    queryKey: ["sentimentHistory", "naaim"],
    queryFn: () => api.marketContextSentimentHistory("naaim"),
    staleTime: 5 * 60_000,
    enabled: !!sentiment?.root_set,
  });
  const { data: aaiiHist } = useQuery({
    queryKey: ["sentimentHistory", "aaii"],
    queryFn: () => api.marketContextSentimentHistory("aaii"),
    staleTime: 5 * 60_000,
    enabled: !!sentiment?.root_set,
  });
  if (!sentiment || !sentiment.root_set) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head">
          <span className="macro-name">投资者情绪</span>
        </div>
        <div className="macro-note">
          未设置 <code>LEI_SENTIMENT_ROOT</code>。设置后放入 naaim.csv / aaii.csv，或点「更新情绪」手动录入，本卡展示带日期的历史调查读数。
        </div>
        <details className="sentiment-setup">
          <summary>如何启用（一次性）</summary>
          <ol>
            <li>在 <code>biao</code> 启动脚本或后端 plist 中设置 <code>LEI_SENTIMENT_ROOT</code>（如 <code>~/Desktop/lei-signal-lab/data/sentiment</code>）。已为你默认写入 <code>biao</code>。</li>
            <li>重启后端：<code>biao restart</code>。</li>
            <li>回到本卡点「更新情绪」录入每期读数，卡片自动反映。</li>
          </ol>
        </details>
      </div>
    );
  }
  const openHistory = (series: "naaim" | "aaii") => {
    const hist = series === "naaim" ? naaimHist : aaiiHist;
    const obs = hist?.observations ?? [];
    if (obs.length < 2) return;
    const dates = obs.map((o) => o.survey_week);
    const cur = series === "naaim" ? sentiment.naaim : sentiment.aaii;
    if (series === "naaim") {
      onOpen({
        title: "NAAIM 主动投资管理人自报股票敞口（原值历史）",
        subtitle: `已记录 ${fmt(cur?.exposure_index, 1)} · ${cur?.label_cn ?? "-"}${
          cur?.percentile != null ? ` · 百分位 P${cur.percentile.toFixed(0)}` : ""
        }（共 ${obs.length} 期，周频）`,
        dates,
        series: [{ name: "暴露指数", values: obs.map((o) => o.exposure_index ?? null), color: "#2563eb" }],
        unit: "",
        yRange: [-200, 200],
        footnote:
          "NAAIM 是基金经理自报股票敞口，个别答复可为负值或超过100。横轴是调查周，不代表当周已公布；历史位置来自现有记录，不是顶底线。",
      });
    } else {
      onOpen({
        title: "AAII 会员未来六个月方向调查",
        subtitle: `已记录 多 ${fmt(cur?.bullish, 0)}% / 空 ${fmt(cur?.bearish, 0)}%（共 ${obs.length} 期，周频）`,
        dates,
        series: [
          { name: "看多 %", values: obs.map((o) => o.bullish ?? null), color: "#e33d47" },
          { name: "看空 %", values: obs.map((o) => o.bearish ?? null), color: "#0b9b64" },
        ],
        unit: "%",
        yRange: [0, 70],
        footnote:
          "AAII 是美国个人投资者协会会员对未来六个月股市方向的问卷；横轴是调查周，不代表当周已公布。看多和看空比例不能直接当作短期顶底线。",
      });
    }
  };
  return (
    <div className="macro-card sentiment-card">
      <div className="macro-head">
        <span className="macro-name">投资者情绪</span>
        <button type="button" className="btn mini" onClick={() => setEditing((v) => !v)}>
          {editing ? "收起" : "更新情绪"}
        </button>
      </div>
      {editing && <SentimentUpdateForm onDone={() => setEditing(false)} />}
      <div className="sentiment-body">
        {sentiment.naaim ? (
          <SentimentRow
            kind="naaim"
            s={sentiment.naaim}
            title="NAAIM 自报股票敞口"
            sparkValues={(naaimHist?.observations ?? []).map((o) => o.exposure_index).filter((v): v is number => v != null)}
            onOpen={() => openHistory("naaim")}
          />
        ) : (
          <SentimentEmpty name="NAAIM" onAdd={() => setEditing(true)} />
        )}
        {sentiment.aaii ? (
          <SentimentRow
            kind="aaii"
            s={sentiment.aaii}
            title="AAII 会员方向调查"
            sparkValues={(aaiiHist?.observations ?? []).map((o) => o.bull_bear).filter((v): v is number => v != null)}
            onOpen={() => openHistory("aaii")}
          />
        ) : (
          <SentimentEmpty name="AAII" onAdd={() => setEditing(true)} />
        )}
      </div>
    </div>
  );
}

// ── 美国宏观（FRED）：就业 / 房产 / 汽车 / WEI / 物价 / 订单 ─────────────

function useUsMacro() {
  return useQuery({
    queryKey: ["fundamentalsUsMacro"],
    queryFn: () => fundamentalsApi.usMacro(),
    staleTime: 30 * 60_000,
    retry: 1,
  });
}

/** 各序列当前值格式化（后端原始单位 -> 展示单位）。 */
const US_VALUE_FMT: Record<string, (v: number) => string> = {
  icwa: (v) => `${(v / 1e4).toFixed(1)} 万`,
  ccwa: (v) => `${(v / 1e4).toFixed(1)} 万`,
  payems_yoy: (v) => `${v.toFixed(2)}%`,
  hsales: (v) => `${(v / 10).toFixed(1)} 万套`,
  cshpi_yoy: (v) => `${v.toFixed(2)}%`,
  altsa: (v) => `${v.toFixed(2)} 百万辆`,
  wei: (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`,
  ppiaco_yoy: (v) => `${v.toFixed(2)}%`,
  cpiaucsl_yoy: (v) => `${v.toFixed(2)}%`,
  dgorder_yoy: (v) => `${v.toFixed(2)}%`,
  hy_oas: (v) => `${v.toFixed(2)}%`,
};

function UsMacroSection({ onOpen }: { onOpen: (d: DrawerState) => void }) {
  const { data, isLoading } = useUsMacro();
  const s = data?.series ?? {};
  // hy_oas 放在 ② 利率区展示（视频组合：信用利差搭配 VIX 评估系统性风险）
  const items = (data?.items ?? []).filter((it) => it.key !== "hy_oas");
  if (isLoading) {
    return (
      <div className="macro-grid">
        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="card-skeleton" />)}
      </div>
    );
  }
  if (!data || items.length === 0) {
    return (
      <div className="fund-errors">
        美国宏观暂不可用（FRED 可能限流，稍后刷新重试）：{data?.errors.join("；") ?? "无数据"}
      </div>
    );
  }
  return (
    <>
      <div className="macro-grid">
        {items.map((it) => {
          const ser = s[it.key];
          const zones = ZONES[it.key] ?? [];
          const zone = findZone(it.value ?? null, zones);
          const fmtVal = US_VALUE_FMT[it.key];
          return (
            <MetricCard
              key={it.key}
              label={it.name_cn}
              value={it.value == null || !fmtVal ? "-" : fmtVal(it.value)}
              sub={`${it.freq}更 · ${it.date ?? "-"} · ${it.key === "hy_oas" ? "高收益债相对国债的额外收益率；未建立固定顶底线" : it.note_cn}`}
              zoneLabel={it.value == null ? undefined : zone.label}
              zoneTone={it.value == null ? undefined : zone.tone}
              sparkValues={ser?.values}
              markY={SPARK_MARK[it.key] ?? null}
              onOpen={() => {
                if (!ser || ser.dates.length < 2) return;
                onOpen(
                  buildDrawer({
                    title: it.name_cn,
                    cur: it.value ?? null,
                    unit: ser.unit,
                    label: ser.label,
                    dates: ser.dates,
                    values: ser.values,
                    key: it.key,
                    periodLabel: it.freq,
                    curDisplay: it.value == null || !fmtVal ? "-" : fmtVal(it.value),
                  }),
                );
              }}
            />
          );
        })}
      </div>
      {data.errors.length > 0 && (
        <div className="fund-hint-row">部分美国指标暂不可用：{data.errors.join("；")}</div>
      )}
    </>
  );
}

// ── 11 行业 ETF 相对强度（thememo 市场类，risk on/off）────────────────────

/** 11 条线的固定配色：进攻暖色、避险冷色、中性灰调，肉眼可分组。 */
const ETF_LINE_COLORS: Record<string, string> = {
  XLY: "#dc2626", // 可选消费（进攻）
  XLP: "#16a34a", // 必选消费（避险）
  XLV: "#0ea5e9", // 医疗（避险）
  XLU: "#14b8a6", // 公用事业（避险）
  XLE: "#78716c", // 能源
  XLF: "#a855f7", // 金融
  XLI: "#ca8a04", // 工业
  XLB: "#92400e", // 材料
  XLK: "#f97316", // 科技（进攻）
  XLC: "#ec4899", // 通信（进攻）
  XLRE: "#64748b", // 地产
};

// Prior ERP allocation advice was not adopted; preserve the audit entry without action guidance.
function PositionBandCard() {
  return <div className="macro-card"><h3>ERP历史研究</h3>
    <p className="macro-note">旧仓位带建议未获采用，现不展示为操作建议。盈利收益率与国债收益率的差只作估值背景。</p>
    <a href="/library?report=docs%2Fexperiments%2Ffundamentals-independent-review-2026-10-02.md">查看既有审阅</a>
  </div>;
}

// ── 指标 × 股指 相关性速查：三向相关 + 判型 + 机理解说 ─────────────────────
const KIND_TONE: Record<string, string> = {
  leading: "opportunity",
  lagging: "caution",
  mirror: "neutral",
  null: "muted-chip",
};

function CorrelationMapCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["fundamentalsCorrelationMap"],
    queryFn: () => fundamentalsApi.correlationMap(),
    staleTime: 12 * 3600_000, // 月度口径，半天内视为新鲜
  });
  const [openRow, setOpenRow] = useState<string | null>(null);
  if (isLoading) return <div className="card-skeleton" style={{ height: 200 }} />;
  if (!data?.ok || data.rows.length === 0) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">指标 × 股指 相关性</span></div>
        <div className="macro-note">相关性数据暂不可用，稍后刷新重试。</div>
      </div>
    );
  }
  const f = (r: number | null) => (r == null ? "—" : `${r > 0 ? "+" : ""}${r.toFixed(2)}`);
  const cls = (r: number | null, crit: number) =>
    r == null ? "" : Math.abs(r) > crit ? (r > 0 ? "up" : "down") : "sx-dim-num";
  return (
    <div className="macro-card corr-card">
      <div className="macro-head">
        <span className="macro-name">基本面指标 × 股指 相关性（月度三向）</span>
        <span className="macro-period">点击行看机理解说</span>
      </div>
      <table className="event-table fund-table corr-table">
        <thead>
          <tr>
            <th>指标 × 股指</th>
            <th className="num" title="corr(Δ指标, 同月股指收益)">同期</th>
            <th className="num" title="corr(Δ指标, 下月股指收益)">领先1月</th>
            <th className="num" title="corr(同月股指收益, 下月Δ指标)——高=指标跟着市场走">指数领先它</th>
            <th className="num">判型</th>
            <th className="num" title="样本月数 / 5%显著线">n/临界</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => {
            const key = `${r.indicator}×${r.index}`;
            const open = openRow === key;
            return (
              <Fragment key={key}>
                <tr
                  className={open ? "band-cur" : ""}
                  onClick={() => setOpenRow(open ? null : key)}
                  style={{ cursor: "pointer" }}
                >
                  <td>{r.indicator} × {r.index}</td>
                  <td className={`num ${cls(r.r_same, r.crit)}`}>{f(r.r_same)}</td>
                  <td className={`num ${cls(r.r_lead1, r.crit)}`}>{f(r.r_lead1)}</td>
                  <td className={`num ${cls(r.r_index_leads, r.crit)}`}>{f(r.r_index_leads)}</td>
                  <td className="num">
                    <span className={`macro-chip ${KIND_TONE[r.kind] ?? ""}`}>{r.kind_cn}</span>
                  </td>
                  <td className="num sx-dim-num">{r.n}/±{r.crit.toFixed(2)}</td>
                </tr>
                {open && (
                  <tr className="corr-explain-row">
                    <td colSpan={6}>
                      <div className="corr-explain">{r.explain_cn}</div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      <div className="macro-note">{data.method_cn}</div>
      <div className="macro-note">{data.note_cn}</div>
    </div>
  );
}

function EtfStrengthSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["fundamentalsEtf"],
    queryFn: () => fundamentalsApi.etfStrength(),
    staleTime: 30 * 60_000,
  });
  const navigate = useNavigate();
  const etf = data?.etf;
  if (isLoading) return <div className="card-skeleton" style={{ height: 220 }} />;
  if (!etf) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">11 行业 ETF 相对强度</span></div>
        <div className="macro-note">yfinance 限流，稍后刷新重试。领涨阵营判断 risk on/off。</div>
      </div>
    );
  }
  const regimeCn = etf.regime === "risk_off" ? "避险占优（risk-off）" : "风险偏好占优（risk-on）";
  // 发散条形：行业强弱排名的标准呈现，替代原来 11 行纵向长条表。
  const maxAbs = Math.max(1e-9, ...etf.items.map((it: EtfItem) => Math.abs(it.rel_1m ?? 0)));
  return (
    <div className="macro-card etf-card">
      <div className="macro-head">
        <span className="macro-name">11 行业 ETF 相对强度（vs SPY）</span>
        <span className="macro-period">{regimeCn}</span>
      </div>
      {etf.dates != null && etf.dates.length > 1 && (
        <TrendChart
          dates={etf.dates}
          series={etf.items.map((it: EtfItem) => ({
            name: it.name,
            values: it.rel_line ?? [],
            color: ETF_LINE_COLORS[it.code] ?? "#6b7280",
          }))}
          unit=""
          height={320}
          markLines={[{ y: 100, label: "SPY 基准 100", color: "#6b7280" }]}
        />
      )}
      <div className="macro-note" style={{ marginBottom: 8 }}>
        线图 = 各行业 ETF / SPY 比价（近 6 个月，起点归一为 100）：线在 100 上方 = 期间跑赢 SPY，
        上扬 = 相对走强。必选/医疗/公用（冷色）集体在上方 = risk-off 避险；可选/科技/通信（暖色）在上方 = risk-on。
        点图例可单独查看某行业，滚轮/滑块可缩放。
      </div>
      <div className="etf-bars">
        {etf.items.map((it: EtfItem) => {
          const rel = it.rel_1m ?? 0;
          const w = (Math.abs(rel) / maxAbs) * 50; // 中线两侧各 50%
          return (
            <div
              key={it.code}
              className="etf-bar-row clickable"
              onClick={() => navigate(`/?symbol=${encodeURIComponent(it.code)}`)}
              title={`打开 ${it.name}（${it.code}）K线工作台 · 相对强度 ${fmt(it.rel_1m, 2, "%")} · 1月涨幅 ${fmt(it.ret_1m, 2, "%")}`}
            >
              <span className="etf-bar-name">
                {it.name}
                {it.bias === "risk_off" && <span className="tag-off">避险</span>}
                {it.bias === "risk_on" && <span className="tag-on">进攻</span>}
              </span>
              <span className="etf-bar-track">
                {rel >= 0 ? (
                  <span className={`etf-bar-fill up`} style={{ left: "50%", width: `${w}%` }} />
                ) : (
                  <span className={`etf-bar-fill down`} style={{ right: "50%", width: `${w}%` }} />
                )}
              </span>
              <span className={`etf-bar-val ${pctClass(it.rel_1m)}`}>{fmt(it.rel_1m, 1, "%")}</span>
              <span className={`etf-bar-ret ${pctClass(it.ret_1m)}`}>{fmt(it.ret_1m, 1, "%")}</span>
            </div>
          );
        })}
      </div>
      <div className="macro-note">
        条形 = 相对 SPY 的 1 月相对强度（<span className="up">红=跑赢</span> / <span className="down">绿=跑输</span>，中线为 0）；
        右列 = 绝对 1 月涨幅。领涨阵营判断 risk on/off。
      </div>
      {etf.xly_xlp && (
        <div className="macro-note">
          可选/必选消费比价 XLY/XLP = {etf.xly_xlp.ratio.toFixed(2)}（1 月{" "}
          <span className={pctClass(etf.xly_xlp.chg_1m)}>{fmt(etf.xly_xlp.chg_1m, 2, "%")}</span>
          {" · "}3 月{" "}
          <span className={pctClass(etf.xly_xlp.chg_3m)}>{fmt(etf.xly_xlp.chg_3m, 2, "%")}</span>
          ）· 比价升 = 风险偏好，降 = 避险（二者相对，互为镜像）
        </div>
      )}
    </div>
  );
}

// ── 情绪 × 标普500 同窗对照：只在有明确发布时间时落点 ─────────────
function SentimentSp500Card() {
  // 与 OverlaySection / SentimentCard 共享同一 queryKey，不产生重复请求
  const { data: ov } = useQuery({
    queryKey: ["fundOverlay", 20],
    queryFn: () => fundamentalsApi.overlayHistory(20),
    staleTime: 12 * 3600_000,
    retry: 1,
  });
  const { data: naaimHist } = useQuery({
    queryKey: ["sentimentHistory", "naaim"],
    queryFn: () => api.marketContextSentimentHistory("naaim"),
    staleTime: 5 * 60_000,
  });
  const { data: aaiiHist } = useQuery({
    queryKey: ["sentimentHistory", "aaii"],
    queryFn: () => api.marketContextSentimentHistory("aaii"),
    staleTime: 5 * 60_000,
  });

  const naaimObs = naaimHist?.observations ?? [];
  const aaiiObs = aaiiHist?.observations ?? [];
  const dates = ov?.series?.sp500?.dates ?? [];
  // 只在记录的可用日之后落点；旧档 available_at 的首发真实性未逐条核实。
  const pointsAtAvailableDay = <T extends { available_at?: string | null }>(obs: T[], pick: (o: T) => number | null | undefined) => {
    const result: (number | null)[] = dates.map(() => null);
    for (const row of obs) {
      const value = pick(row);
      if (value == null || !row.available_at) continue;
      const date = row.available_at.slice(0, 10);
      const index = dates.findIndex((day) => day >= date);
      if (index >= 0) result[index] = value;
    }
    return result;
  };
  if (!ov?.series?.sp500 || ov.series.sp500.dates.length < 2) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">情绪 × 标普500</span></div>
        <div className="macro-note">标普500 长周期历史加载中或不可用（yfinance 限流时稍后自动重试）。</div>
      </div>
    );
  }
  if (naaimObs.length === 0 && aaiiObs.length === 0) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">情绪 × 标普500</span></div>
        <div className="macro-note">暂无调查历史读数。</div>
      </div>
    );
  }
  const series: OverlaySeries[] = [
    { name: "标普500", values: alignTo(dates, ov.series.sp500), color: "#2563eb", axis: "left" },
    { name: "NAAIM 股票敞口", values: pointsAtAvailableDay(naaimObs, (o) => o.exposure_index), color: "#7c3aed", axis: "right", connectNulls: false },
    { name: "AAII 看多", values: pointsAtAvailableDay(aaiiObs, (o) => o.bullish), color: "#e33d47", axis: "right", connectNulls: false },
    { name: "AAII 看空", values: pointsAtAvailableDay(aaiiObs, (o) => o.bearish), color: "#0b9b64", axis: "right", connectNulls: false },
  ];

  return (
    <div className="macro-card overlay-card">
      <h4>
        <span>调查历史 × 标普500</span>
        <span className="macro-period">事后资料对照</span>
      </h4>
      <OverlayChart dates={dates} series={series} leftName="标普500" rightName="调查原值（不同单位）" height={380} startPercent={15} />
      <div className="fund-hint-row">
        已保存 NAAIM {naaimObs.length} 期、AAII {aaiiObs.length} 期。调查用离散点表示，缺口不连线；没有可用日的记录不画。
        旧历史的首次发布时间未逐条核实，这只是事后资料对照，不能称当时已知或据此判定短期顶底。价格对象是标普500，不是纳斯达克。
      </div>
    </div>
  );
}

// ── 调查历史 × 标普500：两种事后资料对照视图 ──────
function SentimentViews() {
  const [view, setView] = useState<"overlay" | "projection">("overlay");
  return (
    <>
      <div className="overlay-market-controls" style={{ gap: 4, marginBottom: 8 }}>
        <span className="muted" style={{ fontSize: 12 }}>情绪 × 标普500：</span>
        <button
          type="button"
          className={`ma-toggle${view === "overlay" ? " on" : ""}`}
          onClick={() => setView("overlay")}
          title="调查记录可用日与标普500的事后对照；历史首次公开时间未逐条核实"
        >
          同窗对照
        </button>
        <button
          type="button"
          className={`ma-toggle${view === "projection" ? " on" : ""}`}
          onClick={() => setView("projection")}
          title="调查记录可用日后数周的标普500涨跌，仅供事后对照；历史首次公开时间未逐条核实"
        >
          投影散点
        </button>
      </div>
      {view === "overlay" ? <SentimentSp500Card /> : <SentimentProjectionCard />}
    </>
  );
}

// ── 铜金比 / 油金比（thememo 消费类，抽象化全球经济）─────────────────────

function CommodityCard({ data }: { data: CommodityRatios | null | undefined }) {
  const meta = data?.meta;
  const known = (value: string | undefined) => value && value !== "unknown" ? value : "未提供或未核实";
  const number = (value: number | undefined, digits: number) =>
    value != null && Number.isFinite(value) ? value.toFixed(digits) : "暂不可用";
  return (
    <div className="macro-card">
      <div className="macro-head">
        <span className="macro-name">铜金比 / 油金比</span>
        <span className="macro-period">日度期货报价比值 · 背景参考</span>
      </div>
      {data == null ? (
        <div className="macro-value">暂不可用</div>
      ) : (
        <div className="commodity-grid">
          <div><span className="b-label">铜金比（铜价 ÷ 金价）</span><span className="b-val">{number(data.copper_gold, 6)}</span></div>
          <div><span className="b-label">油金比（油价 ÷ 金价）</span><span className="b-val">{number(data.crude_gold, 6)}</span></div>
        </div>
      )}
      <div className="macro-note">
        共同报价日：{known(meta?.quote_date)}；报价单位：{known(meta?.quote_units)}。
        铜价、油价或作为分母的金价变动都会影响比值。无通用买卖阈值；仅作经济背景参考，不参与技术判定。
      </div>
      <details className="macro-note">
        <summary>资料口径与限制</summary>
        {data != null && (
          <>
            <div>读取时间（UTC）：{known(meta?.retrieved_at_utc)}。读取时间不等于行情日期或首次发布时间。</div>
            <div>
              原始报价：铜 {number(data.copper, 6)}（{known(meta?.tickers?.copper)}）；
              黄金 {number(data.gold, 6)}（{known(meta?.tickers?.gold)}）；
              原油 {number(data.crude, 6)}（{known(meta?.tickers?.crude)}）。
              {meta?.quote_date ? "三项报价取同一共同日期。" : "旧缓存未提供日期信息，无法确认三项报价是否同日。"}
            </div>
            <div>各源最新报价日：铜 {known(meta?.latest_dates?.["HG=F"])}；黄金 {known(meta?.latest_dates?.["GC=F"])}；原油 {known(meta?.latest_dates?.["CL=F"])}。</div>
          </>
        )}
        <div>
          来源：{known(meta?.provider)}
          {meta?.provider && <>{" · "}<a href="https://finance.yahoo.com/" target="_blank" rel="noreferrer">Yahoo Finance 来源入口</a></>}；
          首次发布时间：{known(meta?.publication_time)}；合约换月身份：{known(meta?.roll_contract_identity)}；
          数据使用许可：{known(meta?.data_usage_license)}。软件包许可不代表行情数据使用许可。
        </div>
        <div>
          铜价不动、金价下降，铜金比也会上升。单个数值不能判断趋势，也不能直接断言需求回暖或通胀上升；
          报价单位和合约换月身份未核实时，跨来源、跨时段比较需谨慎。
          可配合国债、PMI（采购经理调查指数）理解经济背景。
        </div>
      </details>
    </div>
  );
}

// ── 消费面板：PMI/CPI/PPI 小图卡片 + 商品 ────────────────────────────────

function MacroSection({
  macro,
  hist,
  commodities,
  onOpen,
  onJumpUsMacro,
}: {
  macro: MacroItem[];
  hist?: MacroHistoryResponse;
  commodities: CommodityRatios | null | undefined;
  onOpen: (d: DrawerState) => void;
  onJumpUsMacro?: () => void;
}) {
  const s = hist?.series ?? {};
  return (
    <div className="macro-grid">
      {macro.map((m) => {
        const ser = s[m.key];
        const zones = ZONES[m.key] ?? [];
        const zone = findZone(m.value ?? null, zones);
        const isPmi = m.key === "pmi";
        return (
          <MetricCard
            key={m.key}
            label={m.name_cn}
            value={m.value == null ? "-" : isPmi ? m.value.toFixed(1) : `${m.value.toFixed(1)}%`}
            sub={m.note_cn}
            zoneLabel={zone.label}
            zoneTone={zone.tone}
            sparkValues={ser?.values}
            markY={SPARK_MARK[m.key] ?? null}
            onOpen={() => {
              if (!ser || ser.dates.length < 2) return;
              onOpen(
                buildDrawer({
                  title: m.name_cn,
                  cur: m.value ?? null,
                  unit: ser.unit,
                  label: ser.label,
                  dates: ser.dates,
                  values: ser.values,
                  key: m.key,
                  periodLabel: "月",
                  footnote: isPmi
                    ? "制造业 PMI 荣枯线 50：>50 扩张，<50 收缩。"
                    : "同比口径，0 为通胀/通缩分界。",
                }),
              );
            }}
          />
        );
      })}
      <CommodityCard data={commodities} />
      {onJumpUsMacro && (
        <div className="macro-card clickable" onClick={onJumpUsMacro}>
          <div className="macro-head"><span className="macro-name">美国就业、房产与周经济指标</span></div>
          <div className="macro-note">
            初请/续请失业金、非农、新屋开工与 WEI 周经济指数已接入「美国宏观」分区，点此直接查看 →
          </div>
        </div>
      )}
    </div>
  );
}

// ── 行业资金流抽屉（已随④行业总表下线：A 股行业全景在 /sectors 页；
//    /api/fundamentals/overview 与 industry flow 接口保留不变）──────────

/** 分区页签：原来 5 段纵向堆叠近万素深，「翻个东西要滚到最底」；改为点选直达。
 *  id 沿用锚点名并同步到 URL hash，刷新/深链保持当前分区。 */
const FUND_SECTIONS: { id: string; label: string; tip: string }[] = [
  { id: "fund-sec-market", label: "市场水位", tip: "中美估值、市场宽度与风险条件" },
  { id: "fund-sec-sentiment", label: "情绪与热度", tip: "场内基金热度、杠杆资金、恐慌与调查" },
  { id: "fund-sec-rates", label: "利率", tip: "中美利率成本与曲线位置" },
  { id: "fund-sec-overlay", label: "长周期叠加", tip: "利率与两融叠加股指的 20 年对照" },
  { id: "fund-sec-macro", label: "中美宏观", tip: "就业、物价、消费景气与大宗商品" },
  { id: "fund-sec-news", label: "市场资讯", tip: "每日重要消息与自选雷达" },
];

function resolveFundSection(hash: string): string {
  const clean = hash.replace("#", "");
  if (clean === "fund-sec-usmacro") return "fund-sec-macro";
  return FUND_SECTIONS.some((s) => s.id === clean) ? clean : FUND_SECTIONS[0].id;
}

export default function FundamentalsPage() {
  const queryClient = useQueryClient();
  const location = useLocation();
  const [market, setMarket] = useState<"cn" | "us">("cn");
  const [macroRegion, setMacroRegion] = useState<"cn" | "us">(() =>
    window.location.hash === "#fund-sec-usmacro" ? "us" : "cn",
  );
  const { data: observations, error: observationsError, isLoading: observationsLoading } = useQuery({
    queryKey: ["fundamentalsObservations", market],
    queryFn: () => fundamentalsApi.observations(market),
    staleTime: 5 * 60_000,
  });
  const [drawer, setDrawer] = useState<DrawerState>(null);
  // 利率趋势数据一次拉满 20 年：抽屉里的 3/5/10/20 年 chips 是纯本地缩放窗口，不再重拉。
  const ratesLookback = RATE_LOOKBACK_OPTIONS[RATE_LOOKBACK_OPTIONS.length - 1].days;
  // 当前页签：初始读 URL hash（深链/刷新保持），切换时写回 hash 并回到页首。
  const [activeSection, setActiveSection] = useState(() => resolveFundSection(window.location.hash));
  useEffect(() => {
    if (!location.hash) return;
    if (location.hash === "#fund-sec-usmacro") setMacroRegion("us");
    setActiveSection(resolveFundSection(location.hash));
  }, [location.hash]);

  const jumpTo = (id: string) => {
    if (id === "fund-sec-usmacro") {
      setMacroRegion("us");
      setActiveSection("fund-sec-macro");
      history.replaceState(null, "", "#fund-sec-macro");
      window.scrollTo({ top: 0 });
      return;
    }
    setActiveSection(id);
    history.replaceState(null, "", `#${id}`);
    window.scrollTo({ top: 0 });
  };

  const { data: ov, isLoading: ovLoading, error: ovError } = useQuery({
    queryKey: ["fundamentalsOverview"],
    queryFn: () => fundamentalsApi.overview(),
    staleTime: 5 * 60_000,
  });
  const { data: rates, error: ratesError } = useQuery({
    queryKey: ["fundamentalsRates"],
    queryFn: () => fundamentalsApi.rates(),
    staleTime: 5 * 60_000,
  });
  const { data: ratesHist, error: ratesHistError } = useQuery({
    queryKey: ["fundamentalsRatesHistory", ratesLookback],
    queryFn: () => fundamentalsApi.ratesHistory(ratesLookback),
    staleTime: 30 * 60_000,
  });
  const { data: macroHist, error: macroHistError } = useQuery({
    queryKey: ["fundamentalsMacroHistory", 60],
    queryFn: () => fundamentalsApi.macroHistory(60),
    staleTime: 30 * 60_000,
  });
  const { data: commoditiesData, error: commoditiesError } = useQuery({
    queryKey: ["fundamentalsCommodities"],
    queryFn: () => fundamentalsApi.commodities(),
    staleTime: 30 * 60_000,
  });

  // 硬刷新：overview + rates + commodities + etf + us-macro 一起重拉。
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const [o, r, c, e, um] = await Promise.all([
        fundamentalsApi.overview(true),
        fundamentalsApi.rates(true),
        fundamentalsApi.commodities(true),
        fundamentalsApi.etfStrength(true),
        fundamentalsApi.usMacro(true),
      ]);
      return { o, r, c, e, um };
    },
    onSuccess: ({ o, r, c, e, um }) => {
      queryClient.setQueryData(["fundamentalsOverview"], o);
      queryClient.setQueryData(["fundamentalsRates"], r);
      queryClient.setQueryData(["fundamentalsCommodities"], c);
      queryClient.setQueryData(["fundamentalsEtf"], e);
      queryClient.setQueryData(["fundamentalsUsMacro"], um);
      queryClient.invalidateQueries({ queryKey: ["marketContextGlobalStrip"] });
      queryClient.invalidateQueries({ queryKey: ["fundamentalsRatesHistory"] });
      queryClient.invalidateQueries({ queryKey: ["fundamentalsValuationHistory"] });
      queryClient.invalidateQueries({ queryKey: ["fundamentalsMacroHistory"] });
      queryClient.invalidateQueries({ queryKey: ["fundamentalsObservations"] });
    },
  });

  const allErrors = [
    ...(ov?.errors ?? []),
    ...(ovError ? [`概览：${ovError instanceof Error ? ovError.message : String(ovError)}`] : []),
    ...(ratesError ? [`利率：${ratesError instanceof Error ? ratesError.message : String(ratesError)}`] : []),
    ...(rates?.errors ?? []),
    ...(ratesHistError ? [`利率历史：${ratesHistError instanceof Error ? ratesHistError.message : String(ratesHistError)}`] : []),
    ...(ratesHist?.errors ?? []),
    ...(macroHistError ? [`经济历史：${macroHistError instanceof Error ? macroHistError.message : String(macroHistError)}`] : []),
    ...(macroHist?.errors ?? []),
    ...(commoditiesError
      ? [`大宗商品：${commoditiesError instanceof Error ? commoditiesError.message : String(commoditiesError)}`]
      : []),
  ];

  const showMacroRefresh =
    activeSection === "fund-sec-rates" ||
    activeSection === "fund-sec-overlay" ||
    activeSection === "fund-sec-macro";

  return (
    <div className={`page fund-reading-page ${activeSection === "fund-sec-market" ? "ms-page" : ""}`}>
      <div className="pg-head">
        <div className="pg-head-title">
          <h1>宏观与情绪</h1>
          <span className="pg-head-sub">大环境水位、场内情绪热度、利率与中美宏观一站查阅</span>
        </div>
        {showMacroRefresh && <div className="pg-head-kv">
          <span className="pg-kv">
            <span className="k">更新时间</span>
            <b>{ov ? new Date(ov.generated_at).toLocaleString("zh-CN", { hour12: false }) : "加载中"}</b>
          </span>
          <span className="pg-kv">
            <span className="k">数据状态</span>
            <b>{ov ? (allErrors.length > 0 ? "部分受限" : "正常") : "读取中"}</b>
          </span>
        </div>}
        {showMacroRefresh && <div className="pg-head-actions">
          <button
            className="btn primary"
            disabled={refreshMutation.isPending}
            onClick={() => refreshMutation.mutate()}
          >
            {refreshMutation.isPending ? "刷新中…" : "刷新"}
          </button>
        </div>}
      </div>

      {showMacroRefresh && allErrors.length > 0 && (
        <div className="fund-errors">
          部分数据源暂不可用（其余内容不受影响）：
          {Array.from(new Set(allErrors.map((e) => e.split(/[:：]/)[0]))).map((source, i) => <div key={i}>· {/[\u4e00-\u9fff]/.test(source) ? source : "部分来源"}资料读取失败</div>)}
        </div>
      )}
      {showMacroRefresh && (ovError || ratesError) && (
        <div className="fund-errors">加载失败：{((ovError || ratesError) as Error).message}</div>
      )}

      {/* 分区页签：整合大环境水位、情绪热度、利率、长周期叠图、中美宏观与市场资讯 */}
      <nav className="fund-nav" aria-label="分区导航">
        {FUND_SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`fund-nav-btn ${activeSection === s.id ? "on" : ""}`}
            onClick={() => jumpTo(s.id)}
            title={s.tip}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {/* ── ① 市场水位（直出中美 4×2 全景矩阵，与首页单行晴雨表形成分工） ── */}
      {activeSection === "fund-sec-market" && (
        <>
          <HomeEnvironmentStrip mode="full" />
          <MarketStylePanel market={market} onMarketChange={setMarket} observations={observations} ratesHistory={ratesHist} ratesHistoryFailed={!!ratesHistError} />
          <ObservationLibrary market={market} />
          {observationsError && <p className="fund-errors">{market === "cn" ? "A股" : "美股"}观察资料读取失败；风格事实表仍可查看。</p>}
          <details className="observation-legacy">
            <summary>更多补充参考：背景指标、宽度明细与产品强弱</summary>
            {observationsLoading && <p className="muted">观察资料加载中…</p>}
            <MarketObservationCards response={observations} title={`${market === "cn" ? "A股" : "美股"}背景观察`} limit={4}
              metricIds={market === "us" ? ["vix", "vxn", "real_yield_10y", "hy_oas"] : undefined} />
            {market === "us" && <MarketObservationCards response={observations} title="个人看法与管理人股票敞口调查" metricIds={["aaii", "naaim"]} />}
            <MarketSection onOpen={setDrawer} />
            <EtfStrengthSection />
            <SentimentViews />
          </details>
        </>
      )}

      {/* ── ② 情绪与热度（原「市场参与与情绪」整合） ── */}
      {activeSection === "fund-sec-sentiment" && <SentimentPage embedded />}

      {/* ── ③ 利率 ── */}
      {activeSection === "fund-sec-rates" &&
        (rates ? (
          <>
            <RatesSection data={rates} hist={ratesHist} />
            <PositionBandCard />
            <CorrelationMapCard />
          </>
        ) : (
          <div className="card-skeleton" style={{ height: 180 }} />
        ))}

      {/* ── ④ 长周期叠加 ── */}
      {activeSection === "fund-sec-overlay" && <OverlaySection />}

      {/* ── ⑤ 中美宏观（经济与物价 + 美国宏观合并切换） ── */}
      {activeSection === "fund-sec-macro" && (
        <>
          <div className="observation-market-switch" role="group" aria-label="宏观地区切换" style={{ marginBottom: 14 }}>
            <button
              type="button"
              className={macroRegion === "cn" ? "on" : ""}
              aria-pressed={macroRegion === "cn"}
              onClick={() => setMacroRegion("cn")}
            >
              国内经济与大宗
            </button>
            <button
              type="button"
              className={macroRegion === "us" ? "on" : ""}
              aria-pressed={macroRegion === "us"}
              onClick={() => setMacroRegion("us")}
            >
              美国宏观体检
            </button>
          </div>
          {macroRegion === "cn" ? (
            ovLoading ? (
              <div className="macro-grid">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="card-skeleton" />)}</div>
            ) : ov && ov.macro.length > 0 ? (
              <MacroSection
                macro={ov.macro}
                hist={macroHist}
                commodities={commoditiesData?.commodities}
                onOpen={setDrawer}
                onJumpUsMacro={() => setMacroRegion("us")}
              />
            ) : (
              <div className="macro-card todo-card">
                <div className="macro-head"><span className="macro-name">国内经济指标</span></div>
                <div className="macro-note">暂无最新数据（数据源可能限流）。点右上角「刷新」重试。</div>
              </div>
            )
          ) : (
            <UsMacroSection onOpen={setDrawer} />
          )}
        </>
      )}

      {/* ── ⑥ 市场资讯（原「资讯流」整合） ── */}
      {activeSection === "fund-sec-news" && <NewsPage embedded />}

      {drawer && <TrendDrawer {...drawer} onClose={() => setDrawer(null)} />}
    </div>
  );
}
