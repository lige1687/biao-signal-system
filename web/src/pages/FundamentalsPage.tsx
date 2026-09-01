import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, fundamentalsApi } from "../api/client";
import OverlayChart, { type OverlayMode, type OverlaySeries } from "../components/trend/OverlayChart";
import Sparkline from "../components/trend/Sparkline";
import MetricCard from "../components/trend/MetricCard";
import TrendChart from "../components/trend/TrendChart";
import TrendDrawer, { type DrawerState } from "../components/trend/TrendDrawer";
import SentimentProjectionCard from "../components/SentimentProjectionCard";
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
  CAPE_US_ZONES,
  ERP_CN_ZONES,
  ERP_US_ZONES,
  PE_CN_ZONES,
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

/** 小图分界线（单条，落在数据区间内才有意义）。 */
const SPARK_MARK: Record<string, number> = {
  us_10y: 4.5,
  cn_10y: 2.0,
  cn_us_spread_10y: 0,
  vix: 20,
  margin_rzyezb: 3.0,
  pmi: 50,
  cpi: 0,
  ppi: 0,
  erp_us: 1.9,
  erp_cn: 5.1,
  // 估值分位对照：小图分界线取各自标定窗口中位（CAPE 1950 起 / 沪深300 PE 2010 起）。
  cape_us: 20.2,
  pe_cn: 11.9,
  // 美国宏观（FRED）
  wei: 0,
  hy_oas: 4.5,
  payems_yoy: 0,
  ppiaco_yoy: 0,
  cpiaucsl_yoy: 2,
  cshpi_yoy: 0,
  dgorder_yoy: 0,
};

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

/** 叠图卡片头部的当前宽度 chip：实时显示 50 日宽度所处压力/机会区。 */
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


function OverlaySection() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["fundOverlay", 20],
    queryFn: () => fundamentalsApi.overlayHistory(20),
    staleTime: 12 * 3600_000,
    retry: 1,
  });
  const [range, setRange] = useState<OverlayRange>("2y");
  // 原始刻度看绝对水位（利率压力位/机会位有意义），归一化看涨跌比（同一把尺子）。
  const [mode, setMode] = useState<OverlayMode>("raw");
  // 三张 600px 大图纵向堆叠太长，内部再分页签一次只看一张。
  const [panel, setPanel] = useState<"cn" | "us" | "margin" | "vix">("cn");
  // 6 条宽度规则的激活集：可同时多选，触发区间叠加到宽度格（0–100%）。
  // 默认预选反转信号+牛熊底色（stage 顶/底触发较频，留用户按需开）；持久化到 localStorage 防刷新丢失。
  // 空数组/损坏值回退默认（避免浏览器残留 [] 把默认预选吃掉）；__ALL_OFF__ 哨兵 = 用户主动全关。
  const RULES_STORAGE_KEY = "lei-overlay-active-rules";
  const RULES_DEFAULT = ["reversal_top", "reversal_bottom", "bull_base", "bear_base"] as const;
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
  //   标准 80/20 = 行业共识，反转信号更易触发；严苛 85/15 = 与后端 classifier.py 一致，更难触发。
  // 高亮是否显示的开关就是顶部的 6 条规则 chip（选中=显示、不选=不显示），无需额外总开关。
  const CN_THRESHOLD_KEY = "lei-overlay-cn-threshold";
  const US_THRESHOLD_KEY = "lei-overlay-us-threshold";
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
  // 与指数同周期对齐后叠加到叠图第三轴，并在宽度轴标压力/机会位。
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
    () => unionDates(...[s.sse, s.hs300, s.kc50, s.kc100, s.cybz].filter(Boolean)),
    [s.sse, s.hs300, s.kc50, s.kc100, s.cybz],
  );
  const usDates = useMemo(
    () => unionDates(...[s.sp500, s.nasdaq].filter(Boolean)),
    [s.sp500, s.nasdaq],
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
      { name: "A股股债差", values: alignTo(cnDates, s.erp_cn), color: "#0891b2", axis: "right", dashed: true, lineWidth: 1.4, opacity: 0.95 },
      ...(cnDegenerate ? [] : cnB.series),
    ],
    [cnDates, s.sse, s.hs300, s.kc50, s.kc100, s.cybz, s.cn_10y, s.erp_cn, cnDegenerate, cnB.series],
  );
  const usSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "标普500", values: alignTo(usDates, s.sp500), color: "#2563eb", axis: "left" },
      { name: "纳斯达克", values: alignTo(usDates, s.nasdaq), color: "#7c3aed", axis: "left", secondary: true, dashed: true, lineWidth: 1, opacity: 0.5 },
      { name: "美国10Y", values: alignTo(usDates, s.us_10y), color: "#e36b1c", axis: "right" },
      // 美股股债收益差：同上，与 10Y 共用右轴
      { name: "美股股债差", values: alignTo(usDates, s.erp_us), color: "#0891b2", axis: "right", dashed: true, lineWidth: 1.4, opacity: 0.95 },
      ...(usDegenerate ? [] : usB.series),
    ],
    [usDates, s.sp500, s.nasdaq, s.us_10y, s.erp_us, usDegenerate, usB.series],
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
          title="指数走左轴、利率走右轴，可读绝对水位与压力位/机会位"
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
            title="80/20：行业共识，反转信号更易触发"
          >
            80/20
          </button>
          <button
            type="button"
            className={`ma-toggle${cnThreshold === "strict" ? " on" : ""}`}
            onClick={() => setCnThresholdPersist("strict")}
            title="85/15：与后端 classifier.py 一致，更难触发"
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
          // 右轴分界线 = 10Y 阈值 + 股债收益差阈值（共 6 条），便于一眼对照
          rightMarkLines={[...OVERLAY_MARKLINES.cn_10y, ...OVERLAY_MARKLINES.erp_cn]}
          // 色带用股债收益差的机会/风险区：<2.8 相对债券贵（红）/ >6.4 相对便宜（绿）。
          // 10Y 与股债差共用右轴，两套 zone 会重叠混淆，故只保留后者（用户明确要的高亮）。
          rightZones={ERP_CN_ZONES}
          height={600}
        />
        <div className="fund-hint-row">
          左轴：上证（实线主角）；沪深300 / 科创50 / 科创100 / 创业板指为虚线配角
          （科创50 自 2019-12 基日、科创100 自 2023-08、创业板指自 2010-06 起），
          点图例可开关。五指数点位口径不同，直接比涨跌请切上方「涨跌比(=100)」。
          右轴实线：中国 10Y；虚线：A股股债收益差。色带：
          <strong>绿=相对债券便宜，红=相对债券贵</strong>。
          分界线：1.8% / 2.2% / 2.5%（10Y 阈值）+ 股债差 2.8 / 5.1 / 6.4。
          宽度：实线 = B50，虚线 = B20/B200；超买/超卖阈值
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
            title="80/20：行业共识，反转信号更易触发"
          >
            80/20
          </button>
          <button
            type="button"
            className={`ma-toggle${usThreshold === "strict" ? " on" : ""}`}
            onClick={() => setUsThresholdPersist("strict")}
            title="85/15：与后端 classifier.py 一致，反转顶极少触发"
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
          右轴实线：美国 10Y；虚线：美股股债收益差。色带：
          <strong>绿=相对债券便宜，红=相对债券贵（含负值：债券占优）</strong>。
          分界线：3.5% / 4.5% / 5.0%（10Y 阈值）+ 股债差 0 / 1.9 / 2.8。
          标普500 仅近 10 年数据，纳斯达克为全史。宽度阈值：美股当前用
          <strong>{usThreshold === "standard" ? "标准 80/20" : "严苛 85/15"}</strong>
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
          两融数据自 2010-03 开闸；利率格背景色带为杠杆水位分档，占比 &gt; 3.5% 进入 2015 式警戒区（历史顶 2015-07-03 达 4.70%）。
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
          rightMarkLines={[
            { y: 20, label: "20 正常/升温界", color: "#6b7280" },
            { y: 30, label: "30 恐慌区（尖峰事后看多为阶段底）", color: "#e33d47" },
          ]}
        />
        <div className="fund-hint-row">
          左轴标普500（近 10 年）；右轴 VIX。月度相关性：同期 <strong>-0.78</strong>（构造性镜像——VIX 本身由标普期权定价反推，见「相关性速查」卡），
          指数领先 VIX 变化 +0.28。用法：VIX&gt;30 尖峰用于<strong>确认</strong>底部区域，不是领先抄底信号。
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
        sub="为负 = 美债收益更高，资本外流压力侧"
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
              ? "恐慌区：持股风险高，但常伴逆向机会"
              : data.vix.value < 15
                ? "低波动区：风险资产环境友好，需防自满"
                : "15–30 正常/升温区间"
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
      <MetricCard
        label="美股股债收益差（E/P − 10Y）"
        value={
          data.erp?.us == null
            ? "暂不可用"
            : `${data.erp.us.erp >= 0 ? "+" : ""}${data.erp.us.erp.toFixed(2)}%`
        }
        sub={
          data.erp?.us == null
            ? "盈利收益率源暂不可用，稍后刷新重试"
            : `盈利收益率 ${data.erp.us.earnings_yield.toFixed(2)}% − 10Y ${data.erp.us.risk_free.toFixed(2)}%　Fed Model 口径，ERP 粗略代理`
        }
        zoneLabel={data.erp?.us == null ? undefined : findZone(data.erp.us.erp, ERP_US_ZONES).label}
        zoneTone={data.erp?.us == null ? undefined : findZone(data.erp.us.erp, ERP_US_ZONES).tone}
        sparkValues={spark("erp_us")}
        markY={SPARK_MARK.erp_us}
        onOpen={open("erp_us", "美股股债收益差（E/P − 10Y）", data.erp?.us?.erp ?? null)}
      />
      <MetricCard
        label="美股 CAPE 估值分位"
        value={data.valuation?.us_cape == null ? "暂不可用" : `${data.valuation.us_cape.value.toFixed(1)} 倍`}
        sub={
          data.valuation?.us_cape == null
            ? "Shiller PE 源暂不可用，稍后刷新重试"
            : `${data.valuation.us_cape.calib_from} 年来分位 P${data.valuation.us_cape.percentile.toFixed(0)}　全史(${data.valuation.us_cape.full_from}起) P${data.valuation.us_cape.percentile_full.toFixed(0)}　不含利率项`
        }
        zoneLabel={
          data.valuation?.us_cape == null
            ? undefined
            : findZone(data.valuation.us_cape.value, CAPE_US_ZONES).label
        }
        zoneTone={
          data.valuation?.us_cape == null
            ? undefined
            : findZone(data.valuation.us_cape.value, CAPE_US_ZONES).tone
        }
        sparkValues={spark("cape_us")}
        markY={SPARK_MARK.cape_us}
        onOpen={open(
          "cape_us",
          "美股 CAPE（Shiller PE）",
          data.valuation?.us_cape?.value ?? null,
          data.valuation?.us_cape == null
            ? undefined
            : `${data.valuation.us_cape.value.toFixed(1)} 倍（${data.valuation.us_cape.calib_from} 年来 P${data.valuation.us_cape.percentile.toFixed(0)}）`,
        )}
      />
      <MetricCard
        label="A股股债收益差（E/P − 10Y）"
        value={
          data.erp?.cn == null
            ? "暂不可用"
            : `${data.erp.cn.erp >= 0 ? "+" : ""}${data.erp.cn.erp.toFixed(2)}%`
        }
        sub={
          data.erp?.cn == null
            ? "估值源暂不可用，稍后刷新重试"
            : `盈利收益率 ${data.erp.cn.earnings_yield.toFixed(2)}% − 10Y ${data.erp.cn.risk_free.toFixed(2)}%（PE ${data.erp.cn.pe_ttm?.toFixed(1) ?? "-"}）　Fed Model 口径`
        }
        zoneLabel={data.erp?.cn == null ? undefined : findZone(data.erp.cn.erp, ERP_CN_ZONES).label}
        zoneTone={data.erp?.cn == null ? undefined : findZone(data.erp.cn.erp, ERP_CN_ZONES).tone}
        sparkValues={spark("erp_cn")}
        markY={SPARK_MARK.erp_cn}
        onOpen={open("erp_cn", "A股股债收益差（E/P − 10Y）", data.erp?.cn?.erp ?? null)}
      />
      <MetricCard
        label="沪深300 PE_TTM 估值分位"
        value={data.valuation?.cn_pe == null ? "暂不可用" : `${data.valuation.cn_pe.value.toFixed(1)} 倍`}
        sub={
          data.valuation?.cn_pe == null
            ? "估值源暂不可用，稍后刷新重试"
            : `${data.valuation.cn_pe.calib_from} 年来分位 P${data.valuation.cn_pe.percentile.toFixed(0)}　全史(${data.valuation.cn_pe.full_from}起) P${data.valuation.cn_pe.percentile_full.toFixed(0)}　不含利率项`
        }
        zoneLabel={
          data.valuation?.cn_pe == null
            ? undefined
            : findZone(data.valuation.cn_pe.value, PE_CN_ZONES).label
        }
        zoneTone={
          data.valuation?.cn_pe == null
            ? undefined
            : findZone(data.valuation.cn_pe.value, PE_CN_ZONES).tone
        }
        sparkValues={spark("pe_cn")}
        markY={SPARK_MARK.pe_cn}
        onOpen={open(
          "pe_cn",
          "沪深300 PE_TTM",
          data.valuation?.cn_pe?.value ?? null,
          data.valuation?.cn_pe == null
            ? undefined
            : `${data.valuation.cn_pe.value.toFixed(1)} 倍（${data.valuation.cn_pe.calib_from} 年来 P${data.valuation.cn_pe.percentile.toFixed(0)}）`,
        )}
      />
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
        sub={hy ? `日更 · ${hy.date ?? "-"} · ${hy.note_cn}` : "FRED 拉取中，稍后刷新重试"}
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
        "宽度 = 站上 N 日均线的个股占比。50 日 >80% 大概率阶段顶部，<20% 短期底部；配合 200 日同低/同高可能见反转。" +
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

  return (
    <div className="macro-card metric-card clickable" onClick={open}>
      <div className="macro-head">
        <span className="macro-name">{panel.display_name} 宽度</span>
        <span className={`macro-chip ${zone.tone}`}>{zone.label}</span>
      </div>
      <div className="macro-value">{cur != null ? `${cur.toFixed(1)}%` : "-"}</div>
      <div className="macro-note">
        20日 {panel.breadth_20?.toFixed(0) ?? "-"}% · 200日 {panel.breadth_200?.toFixed(0) ?? "-"}%
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
      {data.panels.map((p) => (
        <BreadthSparkCard key={p.market_id} panel={p} onOpen={onOpen} />
      ))}
      <SentimentCard sentiment={data.sentiment} onOpen={onOpen} />
    </div>
  );
}

// ── 投资者情绪（NAAIM/AAII，来自 LEI_SENTIMENT_ROOT，与 Streamlit 同源）────
function sentimentTone(label: string): string {
  // 情绪分档→语义色：极端乐观=过度自满=风险；乐观=偏谨慎；悲观/极端悲观=机会；中性/未知=灰
  switch (label) {
    case "extreme_high":
      return "danger";
    case "high":
      return "caution";
    case "low":
    case "extreme_low":
      return "opportunity";
    default:
      return "neutral";
  }
}

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
  const tone = sentimentTone(s.label);
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
        <span className={`macro-chip ${tone}`}>{s.label_cn}</span>
      </div>
      {sparkValues && sparkValues.length >= 2 ? (
        <Sparkline
          values={sparkValues}
          height={40}
          markY={kind === "naaim" ? 50 : 0}
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
  const canSubmit = series === "naaim" ? naaimOk : aaiiOk;

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
        <span className="sentiment-form-hint">默认本周一；发布时间取 {releaseHint(surveyWeek, series)}</span>
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
        <label className="sentiment-form-label" htmlFor="av">发布时间(可选)</label>
        <input id="av" type="text" value={availableAt} placeholder="留空=默认周四发布时间" onChange={(e) => setAvailableAt(e.target.value)} />
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
          未设置 <code>LEI_SENTIMENT_ROOT</code>。设置后放入 naaim.csv / aaii.csv，或点「更新情绪」手动录入，本卡即展示最新读数与分档。
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
        title: "NAAIM 机构情绪（暴露指数）",
        subtitle: `当前 ${fmt(cur?.exposure_index, 1)} · ${cur?.label_cn ?? "-"}${
          cur?.percentile != null ? ` · 百分位 P${cur.percentile.toFixed(0)}` : ""
        }（共 ${obs.length} 期，周频）`,
        dates,
        series: [{ name: "暴露指数", values: obs.map((o) => o.exposure_index ?? null), color: "#2563eb" }],
        unit: "",
        yRange: [0, 100],
        markLines: [
          { y: 20, label: "20 极端悲观（逆向机会区）", color: "#0b9b64" },
          { y: 80, label: "80 极端乐观（自满风险区）", color: "#e33d47" },
        ],
        footnote:
          "NAAIM = 机构经理人平均多头暴露（0–100）。逆向解读：极端乐观常伴阶段顶，极端悲观常伴阶段底；百分位基于全部历史周排序。",
      });
    } else {
      onOpen({
        title: "AAII 散户情绪（多空调查）",
        subtitle: `当前 多 ${fmt(cur?.bullish, 0)}% / 空 ${fmt(cur?.bearish, 0)}%（共 ${obs.length} 期，周频）`,
        dates,
        series: [
          { name: "看多 %", values: obs.map((o) => o.bullish ?? null), color: "#e33d47" },
          { name: "看空 %", values: obs.map((o) => o.bearish ?? null), color: "#0b9b64" },
        ],
        unit: "%",
        yRange: [0, 70],
        footnote:
          "AAII = 散户多空调查（看多/看空占受访者 %）。散户情绪逆向用：看多极端常近顶，看空极端常近底；与 NAAIM 机构口径对照看分歧。",
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
            title="NAAIM 机构"
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
            title="AAII 散户"
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
              sub={`${it.freq}更 · ${it.date ?? "-"} · ${it.note_cn}`}
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

// ── 仓位带建议（A股 ERP，战略层）：只有两端调带，中间不动 ────────────────
function PositionBandCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["fundamentalsPositionBand"],
    queryFn: () => fundamentalsApi.positionBand(),
    staleTime: 60 * 60_000, // ERP 是慢变量，1 小时内视为新鲜
  });
  if (isLoading) return <div className="card-skeleton" style={{ height: 200 }} />;
  if (!data?.ok) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">仓位带建议（A股 ERP）</span></div>
        <div className="macro-note">ERP 历史暂不可用，稍后刷新重试。</div>
      </div>
    );
  }
  const ev12 = data.evidence.filter((e) => e.fwd_months === 12);
  const toneCls =
    data.zone === 3 ? "up" : data.zone === 0 ? "down" : "";
  return (
    <div className="macro-card band-card">
      <div className="macro-head">
        <span className="macro-name">仓位带建议（A股 ERP · 战略层）</span>
        <span className={`macro-chip ${data.zone_tone}`}>{data.zone_cn}</span>
      </div>
      <div className="band-main">
        <div className="band-erp">
          <div className="band-erp-val">ERP {data.erp.toFixed(2)}</div>
          <div className="macro-note">
            盈利收益率 − 中债10Y · 截至 {data.as_of}
            {data.percentile_5y != null && ` · 5年分位 P${data.percentile_5y.toFixed(0)}`}
          </div>
        </div>
        <div className={`band-action ${toneCls}`}>{data.action_cn}</div>
      </div>

      <table className="event-table fund-table band-table">
        <thead>
          <tr>
            <th>ERP 区间</th>
            <th className="num">样本</th>
            <th className="num">前瞻12月中位</th>
            <th className="num">胜率</th>
            <th className="num">年化(均值)</th>
          </tr>
        </thead>
        <tbody>
          {ev12.map((e) => (
            <tr key={e.zone} className={data.zone_cn.includes(e.zone) ? "band-cur" : ""}>
              <td>{e.zone}</td>
              <td className="num sx-dim-num">{e.n}</td>
              <td className={`num ${e.median_pct >= 0 ? "up" : "down"}`}>{e.median_pct > 0 ? "+" : ""}{e.median_pct}%</td>
              <td className="num">{e.win_rate_pct}%</td>
              <td className={`num ${e.annualized_pct >= 0 ? "up" : "down"}`}>{e.annualized_pct > 0 ? "+" : ""}{e.annualized_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="band-rules">
        {data.rules_cn.map((r, i) => (
          <div key={i} className="band-rule">· {r}</div>
        ))}
      </div>

      {data.backtest && (
        <>
          <h5 className="band-bt-title">规则回测（{data.backtest.from} ~ {data.backtest.to}，{data.backtest.months} 个月，换带 {data.backtest.band_turns} 次）</h5>
          <TrendChart
            dates={data.backtest.curve_dates}
            series={[
              { name: "带位±15pp", values: data.backtest.curves["band15"], color: "#2563eb" },
              { name: "只加不减", values: data.backtest.curves["asym"], color: "#7c3aed" },
              { name: "恒定60%", values: data.backtest.curves["const60"], color: "#98a2b3" },
              { name: "全仓", values: data.backtest.curves["full"], color: "#e0913a" },
            ]}
            unit="x"
            height={240}
          />
          <table className="event-table fund-table band-table">
            <thead>
              <tr>
                <th>策略</th>
                <th className="num">CAGR</th>
                <th className="num">年化波动</th>
                <th className="num">最大回撤</th>
                <th className="num">Sharpe(rf=2%)</th>
                <th className="num">终值</th>
              </tr>
            </thead>
            <tbody>
              {data.backtest.strategies.map((st) => (
                <tr key={st.key}>
                  <td>{st.name}</td>
                  <td className={`num ${st.cagr_pct >= 0 ? "up" : "down"}`}>{st.cagr_pct > 0 ? "+" : ""}{st.cagr_pct}%</td>
                  <td className="num sx-dim-num">{st.vol_pct}%</td>
                  <td className="num down">{st.maxdd_pct}%</td>
                  <td className="num">{st.sharpe.toFixed(2)}</td>
                  <td className="num sx-dim-num">{st.final_x}x</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="macro-note">{data.backtest.note_cn}</div>
        </>
      )}
      <div className="macro-note">
        样本 {data.sample.from} ~ {data.sample.to}（{data.sample.days} 期，月频）。{data.caveats_cn[0]}。
        证据实时重算，口径可复核。美股 ERP 不接仓位（近十年负 ERP 并不预示下跌），仅叠加图色带观察。
      </div>
    </div>
  );
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

// ── 情绪 × 标普500 同窗对照：逆向指标，情绪极端处常对应指数拐点 ─────────────
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

  const sp = ov?.series?.sp500;
  const dates = sp?.dates ?? [];
  const naaimObs = naaimHist?.observations ?? [];
  const aaiiObs = aaiiHist?.observations ?? [];

  // 周频情绪 → 日轴：每个调查周（周一）对齐到当天或之后第一个交易日；
  // 其余日期为 null，靠 OverlayChart 的 connectNulls 连成周频折线（与宽度叠加同法）。
  const weeklyToDaily = <T,>(obs: T[], weekOf: (o: T) => string, pick: (o: T) => number | null | undefined) => {
    const byWeek = new Map<string, number>();
    for (const o of obs) {
      const v = pick(o);
      if (v != null) byWeek.set(weekOf(o), v);
    }
    const hit = new Map<string, number>();
    let di = 0;
    for (const w of [...byWeek.keys()].sort()) {
      while (di < dates.length && dates[di] < w) di++;
      if (di < dates.length) {
        const d = dates[di] >= w ? dates[di] : null;
        if (d != null && !hit.has(d)) hit.set(d, byWeek.get(w)!);
      }
    }
    return dates.map((d) => hit.get(d) ?? null);
  };

  if (!sp || dates.length < 2) {
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
        <div className="macro-note">暂无情绪读数：每周四 launchd 自动抓取 NAAIM/AAII，攒满后此处叠加显示。</div>
      </div>
    );
  }

  const series: OverlaySeries[] = [
    { name: "标普500", values: alignTo(dates, sp), color: "#2563eb", axis: "left" },
    ...(naaimObs.length
      ? [{
          name: "NAAIM 暴露",
          values: weeklyToDaily(naaimObs, (o) => o.survey_week, (o) => o.exposure_index ?? null),
          color: "#7c3aed", axis: "right" as const, lineWidth: 1.6,
        }]
      : []),
    ...(aaiiObs.length
      ? [
          {
            name: "AAII 看多",
            values: weeklyToDaily(aaiiObs, (o) => o.survey_week, (o) => o.bullish ?? null),
            color: "#e33d47", axis: "right" as const, lineWidth: 1.2, opacity: 0.85,
          },
          {
            name: "AAII 看空",
            values: weeklyToDaily(aaiiObs, (o) => o.survey_week, (o) => o.bearish ?? null),
            color: "#0b9b64", axis: "right" as const, lineWidth: 1.2, opacity: 0.85,
          },
        ]
      : []),
  ];

  return (
    <div className="macro-card overlay-card">
      <h4>
        <span>情绪 × 标普500</span>
        <span className="macro-period">周频 · 逆向对照</span>
      </h4>
      <OverlayChart
        dates={dates}
        series={series}
        leftName="标普500"
        rightName="情绪（0–100）"
        height={380}
        startPercent={15}
        rightMarkLines={[
          { y: 20, label: "20 极端悲观·逆向机会", color: "#16a34a" },
          { y: 80, label: "80 极端乐观·自满风险", color: "#e33d47" },
        ]}
      />
      <div className="fund-hint-row">
        左轴标普500（日线）；右轴情绪（0–100，周频，周四发布）：紫=NAAIM 机构暴露，
        <span className="up">红=AAII 看多</span> / <span className="down">绿=AAII 看空</span>。
        逆向读法：情绪触及 20/80 分界线的极端区，常对应指数阶段拐点（历史由 NAAIM 官方 chart /
        AAII Wayback 快照回填，每周四自动追加最新一期）。
      </div>
    </div>
  );
}

// ── 情绪 × 标普500：同一区块两种视图（对照看拐点叙事 / 投影看关系强度）──────
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
          title="标普与情绪同窗叠加，看极端区与指数拐点的叙事对照"
        >
          同窗对照
        </button>
        <button
          type="button"
          className={`ma-toggle${view === "projection" ? " on" : ""}`}
          onClick={() => setView("projection")}
          title="X=情绪、Y=发布后 N 周标普涨跌的散点，看关系强度与极端区后续分布"
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
  return (
    <div className="macro-card">
      <div className="macro-head">
        <span className="macro-name">铜金比 / 油金比</span>
        <span className="macro-period">全球需求 × 避险</span>
      </div>
      {data == null ? (
        <div className="macro-value">暂不可用</div>
      ) : (
        <div className="commodity-grid">
          <div><span className="b-label">铜金比</span><span className="b-val">{data.copper_gold.toFixed(4)}</span></div>
          <div><span className="b-label">油金比</span><span className="b-val">{data.crude_gold.toFixed(4)}</span></div>
        </div>
      )}
      <div className="macro-note">
        铜金比升=工业需求回暖；油金比升=通胀预期升。配合国债/PMI 可抽象化把握全球经济。
      </div>
    </div>
  );
}

// ── 消费面板：PMI/CPI/PPI 小图卡片 + 商品 ────────────────────────────────

function MacroSection({
  macro,
  hist,
  commodities,
  onOpen,
}: {
  macro: MacroItem[];
  hist?: MacroHistoryResponse;
  commodities: CommodityRatios | null | undefined;
  onOpen: (d: DrawerState) => void;
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
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">更多消费指标</span></div>
        <div className="macro-note">
          就业（初请/续请失业金、非农）、WEI 周经济指数 - 第二批接入（需 FRED key）。
        </div>
      </div>
    </div>
  );
}

// ── 行业资金流抽屉（已随④行业总表下线：A 股行业全景在 /sectors 页；
//    /api/fundamentals/overview 与 industry flow 接口保留不变）──────────

/** 分区页签：原来 5 段纵向堆叠近万素深，「翻个东西要滚到最底」；改为点选直达。
 *  id 沿用锚点名并同步到 URL hash，刷新/深链保持当前分区。 */
const FUND_SECTIONS: { id: string; label: string; tip: string }[] = [
  { id: "fund-sec-market", label: "① 市场", tip: "宽度 + 情绪（最有用）" },
  { id: "fund-sec-rates", label: "② 利率", tip: "价格的标尺 / 资本的成本" },
  { id: "fund-sec-overlay", label: "②⁺ 叠加", tip: "利率 / 两融 × 股指（20 年级，可滑动缩放）" },
  { id: "fund-sec-macro", label: "③ 消费", tip: "就业 / 物价 / 景气" },
  { id: "fund-sec-usmacro", label: "③⁺ 美国宏观", tip: "就业 / 房产 / 汽车 / WEI / 物价 / 订单（FRED）" },
];

export default function FundamentalsPage() {
  const queryClient = useQueryClient();
  const [drawer, setDrawer] = useState<DrawerState>(null);
  // 利率趋势数据一次拉满 20 年：抽屉里的 3/5/10/20 年 chips 是纯本地缩放窗口，不再重拉。
  const ratesLookback = RATE_LOOKBACK_OPTIONS[RATE_LOOKBACK_OPTIONS.length - 1].days;
  // 当前页签：初始读 URL hash（深链/刷新保持），切换时写回 hash 并回到页首。
  const [activeSection, setActiveSection] = useState(() => {
    const h = window.location.hash.replace("#", "");
    return FUND_SECTIONS.some((s) => s.id === h) ? h : FUND_SECTIONS[0].id;
  });

  const jumpTo = (id: string) => {
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
  const { data: ratesHist } = useQuery({
    queryKey: ["fundamentalsRatesHistory", ratesLookback],
    queryFn: () => fundamentalsApi.ratesHistory(ratesLookback),
    staleTime: 30 * 60_000,
  });
  const { data: macroHist } = useQuery({
    queryKey: ["fundamentalsMacroHistory", 60],
    queryFn: () => fundamentalsApi.macroHistory(60),
    staleTime: 30 * 60_000,
  });
  const { data: commoditiesData } = useQuery({
    queryKey: ["fundamentalsCommodities"],
    queryFn: () => fundamentalsApi.commodities(),
    staleTime: 30 * 60_000,
  });

  // 硬刷新：overview + rates + commodities + etf 一起重拉。
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
      queryClient.invalidateQueries({ queryKey: ["fundamentalsMacroHistory"] });
    },
  });

  const allErrors = [
    ...(ov?.errors ?? []),
    ...(rates?.errors ?? []),
    ...(ratesHist?.errors ?? []),
    ...(macroHist?.errors ?? []),
  ];

  return (
    <div className="page">
      <div className="header">
        <h1>基本面参考</h1>
        {ov && (
          <span className="generated">
            更新于 {new Date(ov.generated_at).toLocaleString("zh-CN", { hour12: false })}
          </span>
        )}
        <span className="spacer" />
        <button
          className="btn primary"
          disabled={refreshMutation.isPending}
          onClick={() => refreshMutation.mutate()}
        >
          {refreshMutation.isPending ? "刷新中…" : "刷新"}
        </button>
      </div>

      {ov && <div className="legend">{ov.disclaimer_cn}</div>}
      {allErrors.length > 0 && (
        <div className="fund-errors">
          部分数据源暂不可用（其余内容不受影响）：
          {allErrors.map((e, i) => <div key={i}>· {e}</div>)}
        </div>
      )}
      {(ovError || ratesError) && (
        <div className="fund-errors">加载失败：{((ovError || ratesError) as Error).message}</div>
      )}

      {/* 分区页签：sticky 吸顶，点选直达（各卡点开仍有大图抽屉） */}
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

      {/* ── ① 市场 ── */}
      {activeSection === "fund-sec-market" && (
        <>
          <MarketSection onOpen={setDrawer} />
          <EtfStrengthSection />
          <SentimentViews />
        </>
      )}

      {/* ── ② 利率 ── */}
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

      {/* ── ②⁺ 长周期叠加 ── */}
      {activeSection === "fund-sec-overlay" && <OverlaySection />}

      {/* ── ③ 消费 ── */}
      {activeSection === "fund-sec-macro" &&
        (ovLoading ? (
          <div className="macro-grid">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="card-skeleton" />)}</div>
        ) : ov && ov.macro.length > 0 ? (
          <MacroSection
            macro={ov.macro}
            hist={macroHist}
            commodities={commoditiesData?.commodities}
            onOpen={setDrawer}
          />
        ) : null)}

      {/* ── ③⁺ 美国宏观 ── */}
      {activeSection === "fund-sec-usmacro" && (
        <>
          <div className="fund-section-title fund-tab-title">
            美国宏观 <span className="fund-count">消费驱动型经济体检（FRED，无需 API key）</span>
          </div>
          <UsMacroSection onOpen={setDrawer} />
        </>
      )}

      {/* ── ④ 行业（已下线：A 股行业全景在 /sectors 页有更完整的趋势工作台）── */}

      {drawer && <TrendDrawer {...drawer} onClose={() => setDrawer(null)} />}
    </div>
  );
}
