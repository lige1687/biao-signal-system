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
  BREADTH_LINES,
  BREADTH_ZONES,
  MARKLINES,
  OVERLAY_MARKLINES,
  SOURCE_NOTES,
  ZONES,
  findZone,
} from "../components/trend/zones";
import type {
  BreadthHistoryResponse,
  CommodityRatios,
  EtfItem,
  GlobalPanel,
  IndustryBoard,
  MacroHistoryResponse,
  RatesHistoryResponse,
  RatesResponse,
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
  valid: number;
  last50: number | null;
  degenerate: boolean;
  coverage: string;
} {
  const empty = {
    series: [] as OverlaySeries[],
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
    return { series: [], valid, last50: null, degenerate, coverage: `${why}，样本不足未叠加` };
  }
  let last50: number | null = null;
  for (let i = dates.length - 1; i >= 0; i--) {
    if (v50[i] != null) {
      last50 = v50[i];
      break;
    }
  }
  const series: OverlaySeries[] = [
    { name: "宽度20日", values: v20, color: BREADTH_LINES[0].color, axis: "breadth", dashed: true },
    { name: "宽度50日", values: v50, color: BREADTH_LINES[1].color, axis: "breadth", dashed: true },
    { name: "宽度200日", values: v200, color: BREADTH_LINES[2].color, axis: "breadth", dashed: true },
  ];
  return { series, valid, last50, degenerate, coverage: `宽度覆盖 ${window}（${valid} 个交易日）` };
}

/** 叠图卡片头部的当前宽度 chip：实时显示 50 日宽度所处压力/机会区。 */
function BreadthChip({ value }: { value: number | null }) {
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
      { name: "沪深300", values: alignTo(cnDates, s.hs300), color: "#3a7bd5", axis: "left" },
      { name: "中国10Y", values: alignTo(cnDates, s.cn_10y), color: "#f59e0b", axis: "right" },
      ...(cnDegenerate ? [] : cnB.series),
    ],
    [cnDates, s.sse, s.hs300, s.cn_10y, cnDegenerate, cnB.series],
  );
  const usSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "标普500", values: alignTo(usDates, s.sp500), color: "#3a7bd5", axis: "left" },
      { name: "纳斯达克", values: alignTo(usDates, s.nasdaq), color: "#7c3aed", axis: "left" },
      { name: "美国10Y", values: alignTo(usDates, s.us_10y), color: "#f59e0b", axis: "right" },
      ...(usDegenerate ? [] : usB.series),
    ],
    [usDates, s.sp500, s.nasdaq, s.us_10y, usDegenerate, usB.series],
  );
  const marginSeries = useMemo<OverlaySeries[]>(
    () => [
      { name: "上证指数", values: alignTo(cnDates, s.sse), color: "#ea580c", axis: "left" },
      { name: "沪深300", values: alignTo(cnDates, s.hs300), color: "#3a7bd5", axis: "left" },
      {
        name: "融资余额占流通市值比",
        values: alignTo(cnDates, s.margin_rzyezb),
        color: "#dc2626",
        axis: "right",
      },
    ],
    [cnDates, s.sse, s.hs300, s.margin_rzyezb],
  );

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

      <div className="fund-hint-row">
        {mode === "raw"
          ? "原始刻度：每个指数各占一把左轴（轴的颜色 = 线的颜色），各自自适应可视窗口，所以两条指数线都能铺满高度、形态看得清；代价是纵向高低不再可比（标普的线在纳斯达克上面不代表任何含义）。利率/占比在右轴（%），可读绝对水位与压力位/机会位。要比涨跌幅请切「涨跌比」。"
          : "涨跌比：全部线取「共同基准日」的值为 100（基准日 = 窗口内所有线都已有数据的最早那天，标注在纵轴上）——标普只有 2016-08 起的数据，若各自用自己的起点当 100，起跑线不同，比出来的涨跌比是错的。纵轴为对数轴：相同垂直距离 = 相同涨跌倍数，纳斯达克 267 倍的全史才不会把标普压成平线。悬停读涨跌幅；拖底部滑块换窗口，基准自动重算；点图例可隐藏某条线，纵轴会跟着重新适配。此模式下利率的绝对分界线与色带不适用（它们是绝对收益率坐标）故隐藏，宽度线本身已是百分比也一并隐去。"}
      </div>

      <div className="overlay-card">
        <h4>
          A 股 × 中国 10Y 国债
          <BreadthChip value={cnB.last50} />
        </h4>
        <OverlayChart
          dates={cnDates}
          series={cnSeries}
          startPercent={startPercent(cnDates)}
          mode={mode}
          breadthMarkLines={cnDegenerate ? undefined : MARKLINES.breadth}
          rightMarkLines={OVERLAY_MARKLINES.cn_10y}
          rightZones={ZONES.cn_10y}
        />
        <div className="fund-hint-row">
          背景色带 = 中国 10Y 所处区间（绿=机会/资产荒，红=收紧），右轴虚线标机会位 1.8% / 中枢 2.2% / 压力位 2.5%。
          虚线细线 = 市场宽度（站上均线的个股占比），80% 超买 / 20% 超卖（行业通用标准）。{cnB.coverage}。
          分档按当前利率环境标定（2024–2025 券商口径），2014 年以前 10Y 常年在 3–4%，那段历史的色带仅作参考。
        </div>
      </div>

      <div className="overlay-card">
        <h4>
          美股 × 美国 10Y 国债
          <BreadthChip value={usB.last50} />
        </h4>
        <OverlayChart
          dates={usDates}
          series={usSeries}
          startPercent={startPercent(usDates)}
          mode={mode}
          breadthMarkLines={usDegenerate ? undefined : MARKLINES.breadth}
          rightMarkLines={OVERLAY_MARKLINES.us_10y}
          rightZones={ZONES.us_10y}
        />
        <div className="fund-hint-row">
          背景色带 = 美国 10Y 所处区间，右轴虚线标机会位 3.5% / 压力位 4.5% / 强压力 5.0%
          （FRED DGS10 全史实测：2007 年来 ≥4.5% 仅占 6.9%、≥5.0% 仅 0.6%）。
          标普500 受 FRED 授权限制仅近 10 年，纳斯达克为全史（1971 起）。
          美股宽度：{usB.coverage}
          {usDegenerate && "（宽度快照不足，未叠加）"}。宽度由 503 只当期成分股回填，
          期间被剔除的公司不在样本内（存活者偏差，历史宽度略偏高）；B200 需 200 根K线，
          起点比 B20/B50 晚约 10 个月。
          分档由 2007 年后的分布标定，1998–2007 年 10Y 常年 4–6.8%，那段色带仅作参考。
        </div>
      </div>

      <div className="overlay-card">
        <h4>A 股 × 融资余额占流通市值比</h4>
        <OverlayChart
          dates={cnDates}
          series={marginSeries}
          rightName="占比 %"
          startPercent={startPercent(cnDates)}
          mode={mode}
          rightMarkLines={OVERLAY_MARKLINES.margin_rzyezb}
          rightZones={ZONES.margin_rzyezb}
        />
        <div className="fund-hint-row">
          两融数据自 2010-03 开闸；背景色带为杠杆水位分档，占比 &gt; 3.5% 进入 2015 式警戒区（历史顶 2015-07-03 达 4.70%）。
        </div>
      </div>
    </div>
  );
}

// ── 利率面板：5 个指标卡（小图点开大图）──────────────────────────────────

function RatesSection({
  data,
  hist,
  onOpen,
}: {
  data: RatesResponse;
  hist?: RatesHistoryResponse;
  onOpen: (d: DrawerState) => void;
}) {
  const t = data.treasury;
  const s = hist?.series ?? {};
  const spark = (key: string) => s[key]?.values ?? [];
  const open = (key: string, title: string, cur: number | null, curDisplay?: string) => () => {
    const ser = s[key];
    if (!ser || ser.dates.length < 2) return;
    onOpen(
      buildDrawer({
        title,
        cur,
        unit: ser.unit,
        label: ser.label,
        dates: ser.dates,
        values: ser.values,
        key,
        periodLabel: "日",
        curDisplay,
      }),
    );
  };

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
              ? "高位，系统性风险偏高"
              : data.vix.value < 15
                ? "低位，情绪偏乐观"
                : "正常区间 15–30"
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
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">投资者情绪</span></div>
        <div className="macro-note">
          AAII 散户情绪（±25% 极值）、NAAIM 机构情绪（40%/100%）- 第二批接入（周报数据需配置）。
        </div>
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
    queryKey: ["fundamentalsRatesHistory", 730],
    queryFn: () => fundamentalsApi.ratesHistory(730),
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

      {/* ── 利率 ── */}
      <h2 className="fund-section-title">① 利率 <span className="fund-count">价格的标尺 / 资本的成本</span></h2>
      {rates ? <RatesSection data={rates} hist={ratesHist} onOpen={setDrawer} /> : <div className="card-skeleton" style={{ height: 180 }} />}

      {/* ── 长周期叠加 ── */}
      <h2 className="fund-section-title">①⁺ 长周期叠加 <span className="fund-count">利率 / 两融 × 股指（20 年级，可滑动缩放）</span></h2>
      <OverlaySection />

      {/* ── 市场 ── */}
      <h2 className="fund-section-title">② 市场 <span className="fund-count">宽度 + 情绪（最有用）</span></h2>
      <MarketSection onOpen={setDrawer} />
      <div className="rates-grid"><EtfStrengthSection /></div>

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
