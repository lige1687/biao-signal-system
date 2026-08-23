import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, fundamentalsApi } from "../api/client";
import OverlayChart, { type OverlayMode, type OverlaySeries } from "../components/trend/OverlayChart";
import Sparkline from "../components/trend/Sparkline";
import MetricCard from "../components/trend/MetricCard";
import TrendDrawer, { type DrawerState } from "../components/trend/TrendDrawer";
import { buildDrawer } from "../components/trend/drawer";
import { alignTo, unionDates } from "../components/trend/align";
import { fmt, fmtYi, pctClass } from "../utils/format";
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
  IndustryBoard,
  MacroHistoryResponse,
  RatesHistoryResponse,
  RatesResponse,
  SentimentIngest,
} from "../types";

type SortKey = "pct_change" | "main_net_inflow_yi" | "main_net_inflow_pct" | "turnover_rate";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "pct_change", label: "涨跌幅" },
  { key: "main_net_inflow_yi", label: "主力净流入" },
  { key: "main_net_inflow_pct", label: "主力净占比" },
  { key: "turnover_rate", label: "换手率" },
];

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
    () => unionDates(...[s.sse, s.hs300].filter(Boolean)),
    [s.sse, s.hs300],
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
      { name: "中国10Y", values: alignTo(cnDates, s.cn_10y), color: "#e36b1c", axis: "right" },
      // A股股债收益差（Fed Model 口径）：与 10Y 共用右轴，颜色区分；虚线表示这是辅助指标
      { name: "A股股债差", values: alignTo(cnDates, s.erp_cn), color: "#0891b2", axis: "right", dashed: true, lineWidth: 1.4, opacity: 0.95 },
      ...(cnDegenerate ? [] : cnB.series),
    ],
    [cnDates, s.sse, s.hs300, s.cn_10y, s.erp_cn, cnDegenerate, cnB.series],
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
          右轴实线：中国 10Y；虚线：A股股债收益差。色带：
          <strong>绿=相对债券便宜，红=相对债券贵</strong>。
          分界线：1.8% / 2.2% / 2.5%（10Y 阈值）+ 股债差 2.8 / 5.1 / 6.4。
          宽度：实线 = B50，虚线 = B20/B200；超买/超卖阈值
          <strong>{cnThreshold === "standard" ? "80/20" : "85/15"}</strong>（本卡可切）。{cnB.coverage}。
        </div>
      </div>

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
    </div>
  );
}

// ── 利率面板：5 个指标卡（小图点开大图）──────────────────────────────────

function RatesSection({
  data,
  hist,
  lookback,
  onLookbackChange,
  histFetching,
}: {
  data: RatesResponse;
  hist?: RatesHistoryResponse;
  /** 当前趋势周期（自然日）；抽屉 chips 切换。 */
  lookback: number;
  onLookbackChange: (days: number) => void;
  histFetching: boolean;
}) {
  const t = data.treasury;
  const s = hist?.series ?? {};
  const spark = (key: string) => s[key]?.values ?? [];
  // 只存「打开了哪个指标」，序列数据渲染时从当前 hist 取--
  // 周期切换重拉后抽屉内容自动跟随，无需重开。
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
      {drawer && (
        <TrendDrawer
          {...drawer}
          periodOptions={RATE_LOOKBACK_OPTIONS}
          activeDays={lookback}
          onPeriodChange={onLookbackChange}
          periodLoading={histFetching}
          onClose={() => setOpenMeta(null)}
        />
      )}
    </div>
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
      <SentimentCard sentiment={data.sentiment} />
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

function SentimentRow({ kind, s, title }: { kind: "naaim" | "aaii"; s: GlobalSentimentSeries; title: string }) {
  const tone = sentimentTone(s.label);
  const delayed =
    s.license_status != null && s.license_status.toLowerCase().includes("public_delayed");
  return (
    <div className="sentiment-row">
      <div className="sentiment-row-head">
        <span className="sentiment-name">{title}</span>
        <span className={`macro-chip ${tone}`}>{s.label_cn}</span>
      </div>
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

function SentimentEmpty({ name }: { name: string }) {
  return <div className="sentiment-row sentiment-empty">{name}：无数据文件</div>;
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

function SentimentCard({ sentiment }: { sentiment?: GlobalSentiment }) {
  const [editing, setEditing] = useState(false);
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
          <SentimentRow kind="naaim" s={sentiment.naaim} title="NAAIM 机构" />
        ) : (
          <SentimentEmpty name="NAAIM" />
        )}
        {sentiment.aaii ? (
          <SentimentRow kind="aaii" s={sentiment.aaii} title="AAII 散户" />
        ) : (
          <SentimentEmpty name="AAII" />
        )}
      </div>
    </div>
  );
}

// ── 11 行业 ETF 相对强度（thememo 市场类，risk on/off）────────────────────

function EtfStrengthSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["fundamentalsEtf"],
    queryFn: () => fundamentalsApi.etfStrength(),
    staleTime: 30 * 60_000,
  });
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
  return (
    <div className="macro-card etf-card">
      <div className="macro-head">
        <span className="macro-name">11 行业 ETF 相对强度（vs SPY，1 月）</span>
        <span className="macro-period">{regimeCn}</span>
      </div>
      <table className="event-table fund-table rates-table">
        <thead>
          <tr><th>行业</th><th className="num">相对强度</th><th className="num">1 月涨幅</th></tr>
        </thead>
        <tbody>
          {etf.items.map((it: EtfItem) => (
            <tr key={it.code}>
              <td>
                {it.name}
                {it.bias === "risk_off" && <span className="tag-off">避险</span>}
                {it.bias === "risk_on" && <span className="tag-on">进攻</span>}
              </td>
              <td className={`num ${pctClass(it.rel_1m)}`}>{fmt(it.rel_1m, 2, "%")}</td>
              <td className={`num ${pctClass(it.ret_1m)}`}>{fmt(it.ret_1m, 2, "%")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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

// ── 行业资金流抽屉 ───────────────────────────────────────────────────────

function IndustryFlowDrawer({ board, onClose }: { board: IndustryBoard; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["industryFlow", board.code],
    queryFn: () => fundamentalsApi.industryFlow(board.code, 20),
  });
  const points = data?.points ?? [];
  const maxAbs = Math.max(1e-9, ...points.map((p) => Math.abs(p.main_yi ?? 0)));
  const sum = points.reduce((acc, p) => acc + (p.main_yi ?? 0), 0);

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>
            {board.name} <span className="symbol">{board.code}</span> 主力资金流
            {data && `（近 ${points.length} 日）`}
          </h2>
          <button className="btn" onClick={onClose}>关闭</button>
        </div>
        <div className="drawer-body">
          {isLoading && <div>加载中…</div>}
          {error && <div className="error-msg">{(error as Error).message}</div>}
          {!isLoading && !error && (
            <>
              <div className="flow-summary">
                {points.length} 日主力累计净流入：
                <span className={pctClass(sum)}>{fmtYi(sum)}</span>
                <span className="spacer" />
                今日涨跌幅：
                <span className={pctClass(board.pct_change)}>{fmt(board.pct_change, 2, "%")}</span>
              </div>
              <div className="flow-bars">
                {points.map((p) => {
                  const v = p.main_yi ?? 0;
                  const width = Math.max(2, (Math.abs(v) / maxAbs) * 100);
                  return (
                    <div key={p.date} className="flow-row">
                      <span className="flow-date">{p.date.slice(5)}</span>
                      <span className="flow-track">
                        <span className={`flow-bar ${v >= 0 ? "up" : "down"}`} style={{ width: `${width}%` }} />
                      </span>
                      <span className={`flow-val ${pctClass(p.main_yi)}`}>{fmtYi(p.main_yi)}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function FundamentalsPage() {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<SortKey>("main_net_inflow_yi");
  const [sortAsc, setSortAsc] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [selected, setSelected] = useState<IndustryBoard | null>(null);
  const [drawer, setDrawer] = useState<DrawerState>(null);
  // 趋势周期（自然日）：默认 3 年，抽屉里可切 5/10/20 年。
  const [ratesLookback, setRatesLookback] = useState(1095);

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
  const { data: ratesHist, isFetching: ratesHistFetching } = useQuery({
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
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const [o, r, c, e] = await Promise.all([
        fundamentalsApi.overview(true),
        fundamentalsApi.rates(true),
        fundamentalsApi.commodities(true),
        fundamentalsApi.etfStrength(true),
      ]);
      return { o, r, c, e };
    },
    onSuccess: ({ o, r, c, e }) => {
      queryClient.setQueryData(["fundamentalsOverview"], o);
      queryClient.setQueryData(["fundamentalsRates"], r);
      queryClient.setQueryData(["fundamentalsCommodities"], c);
      queryClient.setQueryData(["fundamentalsEtf"], e);
      queryClient.invalidateQueries({ queryKey: ["marketContextGlobalStrip"] });
      queryClient.invalidateQueries({ queryKey: ["fundamentalsRatesHistory"] });
      queryClient.invalidateQueries({ queryKey: ["fundamentalsMacroHistory"] });
    },
  });

  const boards = useMemo(() => {
    let list = ov?.boards ?? [];
    if (keyword.trim()) {
      const k = keyword.trim().toLowerCase();
      list = list.filter((b) => b.name.toLowerCase().includes(k) || b.code.includes(k));
    }
    const dir = sortAsc ? 1 : -1;
    return [...list].sort((a, b) => ((b[sortKey] ?? -1e18) - (a[sortKey] ?? -1e18)) * dir);
  }, [ov, keyword, sortKey, sortAsc]);

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

      <div className="legend fund-hint-row">
        💡 利率 / 市场 / 消费各卡均带小图，点击卡片或小图可展开大图，含机会/风险分界线与区间说明。
      </div>

      {/* ── 市场 ── */}
      <h2 className="fund-section-title">① 市场 <span className="fund-count">宽度 + 情绪（最有用）</span></h2>
      <MarketSection onOpen={setDrawer} />
      <div className="rates-grid"><EtfStrengthSection /></div>

      {/* ── 利率 ── */}
      <h2 className="fund-section-title">② 利率 <span className="fund-count">价格的标尺 / 资本的成本</span></h2>
      {rates ? (
        <RatesSection
          data={rates}
          hist={ratesHist}
          lookback={ratesLookback}
          onLookbackChange={setRatesLookback}
          histFetching={ratesHistFetching}
        />
      ) : (
        <div className="card-skeleton" style={{ height: 180 }} />
      )}

      {/* ── 长周期叠加 ── */}
      <h2 className="fund-section-title">②⁺ 长周期叠加 <span className="fund-count">利率 / 两融 × 股指（20 年级，可滑动缩放）</span></h2>
      <OverlaySection />

      {/* ── 消费 ── */}
      <h2 className="fund-section-title">③ 消费 <span className="fund-count">就业 / 物价 / 景气</span></h2>
      {ovLoading ? (
        <div className="macro-grid">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="card-skeleton" />)}</div>
      ) : ov && ov.macro.length > 0 ? (
        <MacroSection
          macro={ov.macro}
          hist={macroHist}
          commodities={commoditiesData?.commodities}
          onOpen={setDrawer}
        />
      ) : null}

      {/* ── 行业 ── */}
      <h2 className="fund-section-title">④ 行业 <span className="fund-count">{ov?.board_count ?? 0} 个板块</span></h2>
      <div className="fund-toolbar">
        <input
          className="fund-search"
          placeholder="搜索行业名 / 代码…"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        {SORTS.map((s) => (
          <button
            key={s.key}
            className={`btn ${sortKey === s.key ? "primary" : ""}`}
            onClick={() => {
              if (sortKey === s.key) setSortAsc(!sortAsc);
              else { setSortKey(s.key); setSortAsc(false); }
            }}
          >
            {s.label}{sortKey === s.key ? (sortAsc ? " ↑" : " ↓") : ""}
          </button>
        ))}
        <span className="fund-hint">点行看 20 日主力资金流 · PE 为动态市盈率（负=亏损）</span>
      </div>
      <div className="fund-table-wrap">
        <table className="event-table fund-table">
          <thead>
            <tr>
              <th>行业</th>
              <th className="num">涨跌幅</th>
              <th className="num">PE(动)</th>
              <th className="num">换手率</th>
              <th className="num">主力净流入</th>
              <th className="num">净占比</th>
              <th className="num">涨/跌家数</th>
              <th className="num">总市值</th>
            </tr>
          </thead>
          <tbody>
            {boards.map((b) => (
              <tr key={b.code} onClick={() => setSelected(b)}>
                <td>{b.name} <span className="symbol">{b.code}</span></td>
                <td className={`num ${pctClass(b.pct_change)}`}>{fmt(b.pct_change, 2, "%")}</td>
                <td className="num">{b.pe_ttm == null ? "-" : b.pe_ttm < 0 ? "亏" : b.pe_ttm.toFixed(1)}</td>
                <td className="num">{fmt(b.turnover_rate, 2, "%")}</td>
                <td className={`num ${pctClass(b.main_net_inflow_yi)}`}>{fmtYi(b.main_net_inflow_yi)}</td>
                <td className={`num ${pctClass(b.main_net_inflow_pct)}`}>{fmt(b.main_net_inflow_pct, 2, "%")}</td>
                <td className="num"><span className="up">{b.up_count ?? "-"}</span>/<span className="down">{b.down_count ?? "-"}</span></td>
                <td className="num">{fmt(b.total_mv_yi, 0, "亿")}</td>
              </tr>
            ))}
            {boards.length === 0 && <tr><td colSpan={8}>无匹配行业</td></tr>}
          </tbody>
        </table>
      </div>

      {selected && <IndustryFlowDrawer board={selected} onClose={() => setSelected(null)} />}
      {drawer && <TrendDrawer {...drawer} onClose={() => setDrawer(null)} />}
    </div>
  );
}
