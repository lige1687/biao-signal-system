import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi } from "../api/client";
import { OBSERVATION_BY_ID } from "./observation-library/catalog";
import type { CnFinancingTab } from "./observation-library/CnFinancingProjection";
import ObservationDetailDialog from "./observation-library/ObservationDetailDialog";
import { ERP_REFERENCE_QUERY_KEY, ERP_REFERENCE_URL, parseErpReference } from "./observation-library/erpReferenceData";
import { erpBands } from "./observation-library/erpBands";
import { innerErpRails } from "./observation-library/erpComparisonDisplay";
import { withErpSigma } from "./observation-library/erpSensitivity";
import { usErpBands } from "./observation-library/usErpBands";
import { useProjectionSource } from "./observation-library/projectionSources";
import { buildMetricThresholds } from "./observation-library/projectionThresholds";
import { MetricProjection } from "./observation-library/projectionView";
import BreadthComparison from "./market-style/BreadthComparison";
import { breadthInterpretation } from "./market-style/breadthInterpretation";
import { BREADTH_EXTERNAL_REFERENCES } from "./market-style/breadthInstitutionalReferences";
import { historicalPosition, recentDelta } from "./market-style/indicatorReading";
import { seriesPoints } from "./market-style/marketRiskMetrics";
import { breadthInput, erpInput, parseBreadth, type BreadthMarket } from "./market-observation-alerts/adapters";
import { buildAlertSnapshot } from "./market-observation-alerts/model";
import MiniTrend from "./market-observation-alerts/MiniTrend";
import { CHART_COLORS } from "./market-observation-alerts/ChartLegend";
import { PANEL_QUERY_KEY, PANEL_URL, type ObservationPanelData } from "./market-observation-panel/model";
import { BREADTH_LINES } from "./trend/zones";
import MarketObservationAlerts from "./market-observation-alerts";
import "./home-environment-strip.css";

type CoreDetailId = "erp-cn" | "erp-us" | "breadth-cn" | "breadth-us";
type CoreDetailState = { id: CoreDetailId; initialRuleId?: string };
type SubModalState = { id: "hy-oas" | "vix" | "cn-financing"; financingTab?: CnFinancingTab };
type StanceTone = "supportive" | "caution" | "neutral";
type DatedNum = { date: string; value: number };
type EvidenceChip = { label: string; value: string; tone?: "warn" | "good" | "muted" };
type JointVerdict = {
  tone: StanceTone;
  verdict: string;
  chips: EvidenceChip[];
  lead: string;
  highlight: string;
  tail?: string;
  action?: { label: string; onClick: () => void };
};

const CHART_H = 92;
const FUNDING_PACKET_URL = "/api/fundamentals/cn-financing-history";

type FundingCard = {
  id: string;
  points: { date: string; value: number | null }[];
  lines?: { key: string; values: (number | null)[] }[];
};

async function getJson(url: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`资料读取失败 (${response.status})`);
  return response.json();
}

function useBreadth(market: BreadthMarket) {
  return useQuery({
    queryKey: ["homeObservationBreadth", market, 90],
    queryFn: async ({ signal }) =>
      parseBreadth(
        await getJson(
          `/api/market-context/breadth-history?market_id=${market}&lookback_days=90&include_observation=true`,
          signal,
        ),
        market,
      ),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: false,
  });
}

const todayShanghai = () =>
  new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai" }).format(new Date());

const isFiniteNum = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

const fmt = (n: number | null | undefined, dp = 2) =>
  isFiniteNum(n) ? n.toFixed(dp) : "—";

const signedFmt = (n: number | null | undefined, dp = 2) =>
  isFiniteNum(n) ? `${n > 0 ? "+" : ""}${n.toFixed(dp)}` : "—";

function cleanPoints(points: { date: string; value: number | null }[] | undefined): DatedNum[] {
  if (!points) return [];
  return points.filter(
    (p): p is DatedNum =>
      Boolean(p?.date) && /^\d{4}-\d{2}-\d{2}$/.test(p.date) && isFiniteNum(p.value),
  );
}

function mergeSeries(...lists: ({ date: string; value: number | null }[] | undefined)[]): DatedNum[] {
  const byDate = new Map<string, number>();
  for (const list of lists) {
    for (const item of cleanPoints(list)) {
      byDate.set(item.date, item.value);
    }
  }
  return [...byDate.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, value]) => ({ date, value }));
}

/** Asymmetric upper-rail distance helper: ERP upper rail (+1.5σ) has empirical bounce edge; lower rail does not time tops. */
function upperRailGapText(value: number | null | undefined, upper15: number | null | undefined): string | null {
  if (!isFiniteNum(value) || !isFiniteNum(upper15)) return null;
  const diff = value - upper15;
  if (diff >= 0) return `已站上+1.5σ便宜轨 ${diff.toFixed(2)}pp`;
  return `距+1.5σ便宜轨 ${Math.abs(diff).toFixed(2)}pp`;
}

function CoreDetailModal({
  id,
  initialRuleId,
  onClose,
}: {
  id: CoreDetailId;
  initialRuleId?: string;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const backdropDown = useRef(false);
  useEffect(() => {
    const node = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    node?.showModal();
    return () => {
      node?.close();
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);
  const titles: Record<CoreDetailId, string> = {
    "erp-cn": "沪深300 · 股债利差",
    "erp-us": "标普500 · 股债利差",
    "breadth-cn": "全A · 市场宽度",
    "breadth-us": "标普500 · 市场宽度",
  };
  return createPortal(
    <dialog
      ref={dialog}
      className="moa-detail-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onMouseDown={(event) => {
        backdropDown.current = event.target === event.currentTarget;
      }}
      onClick={(event) => {
        if (backdropDown.current && event.target === event.currentTarget) onClose();
        backdropDown.current = false;
      }}
    >
      <header>
        <h2>{titles[id]}</h2>
        <button type="button" onClick={onClose}>
          关闭 ×
        </button>
      </header>
      {id === "erp-cn" || id === "erp-us" ? (
        <MetricProjection id={id} market={id === "erp-cn" ? "cn" : "us"} />
      ) : (
        <BreadthComparison
          market={id === "breadth-cn" ? "cn" : "us"}
          initialRuleId={initialRuleId}
          onMarketChange={() => {}}
        />
      )}
    </dialog>,
    document.body,
  );
}

/**
 * 首页第 1 步：大环境水位（中美四维正交交叉判读 + 8张小图与大图100%对齐阈值矩阵）。
 */
const ENV_EXPANDED_KEY = "lei.homeEnv.expanded";
function loadEnvExpanded(): boolean {
  try {
    return window.localStorage.getItem(ENV_EXPANDED_KEY) === "1";
  } catch {
    return false;
  }
}

export default function HomeEnvironmentStrip({ mode = "barometer" }: { mode?: "barometer" | "full" } = {}) {
  const isFullMode = mode === "full";
  const [coreDetail, setCoreDetail] = useState<CoreDetailState | null>(null);
  const setCoreDetailId = (id: CoreDetailId | null, initialRuleId?: string) =>
    setCoreDetail(id ? { id, initialRuleId } : null);
  const [subModal, setSubModal] = useState<SubModalState | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  // 第一层大环境在看盘首页默认收起成单行晴雨表（给首屏 K 线让位）；在宏观页（mode="full"）直接全景展开
  const [expanded, setExpanded] = useState(() => isFullMode || loadEnvExpanded());
  const isExpanded = isFullMode || expanded;
  const toggleExpanded = () => {
    if (isFullMode) return;
    setExpanded((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(ENV_EXPANDED_KEY, next ? "1" : "0");
      } catch {
        /* 忽略隐私窗口写入限制 */
      }
      if (!next) setMoreOpen(false);
      return next;
    });
  };

  const nowDate = useMemo(todayShanghai, []);

  // ── 数据源 ──
  const cnBreadth = useBreadth("CN_ALL_A");
  const usBreadth = useBreadth("SP500");
  const cnErp = useQuery({
    queryKey: ERP_REFERENCE_QUERY_KEY,
    queryFn: async ({ signal }) => parseErpReference(await getJson(ERP_REFERENCE_URL, signal)),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: false,
  });
  const usErpSource = useProjectionSource("erp-us");
  const hySource = useProjectionSource("hy-oas");
  const vixSource = useProjectionSource("vix");

  const ratesQuery = useQuery({
    queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: false,
  });
  const overlayPriceQuery = useQuery({
    queryKey: ["fundOverlay", 47],
    queryFn: () => fundamentalsApi.overlayHistory(47),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const cnObsQuery = useQuery({
    queryKey: ["marketStyleCnObservations"],
    queryFn: () => fundamentalsApi.observations("cn"),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const usObsQuery = useQuery({
    queryKey: ["marketStyleUsObservations"],
    queryFn: () => fundamentalsApi.observations("us"),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const fundingQuery = useQuery({
    queryKey: ["homeFinancingPacketV1"],
    queryFn: async ({ signal }) =>
      (await getJson(FUNDING_PACKET_URL, signal)) as { cards?: FundingCard[] },
    staleTime: 30 * 60_000,
    retry: false,
  });
  const panelQuery = useQuery({
    queryKey: PANEL_QUERY_KEY,
    queryFn: async ({ signal }) =>
      (await getJson(PANEL_URL, signal)) as ObservationPanelData,
    staleTime: 10 * 60_000,
    retry: false,
  });

  // ── 1. 沪深300 股债利差 ──
  const cnErpSnap = useMemo(
    () => buildAlertSnapshot(erpInput(cnErp.data, cnErp.isError), nowDate),
    [cnErp.data, cnErp.isError, nowDate],
  );
  const cnErpInputPoints = useMemo(
    () => erpInput(cnErp.data, cnErp.isError).points.slice(-260),
    [cnErp.data, cnErp.isError],
  );
  const cnErpInnerRows = useMemo(() => cnErpInputPoints.map(innerErpRails), [cnErpInputPoints]);

  // ── 3. 标普500 股债利差 ──
  const usErpRows = useMemo(() => {
    try {
      return usErpBands(usErpSource.points);
    } catch {
      return [] as ReturnType<typeof erpBands>;
    }
  }, [usErpSource.points]);
  const usErpRails = useMemo(
    () =>
      ([1.5, 2] as const).map((sigma) => ({
        sigma,
        rows: withErpSigma(usErpRows, sigma),
      })),
    [usErpRows],
  );

  // ── 5~8 补充卡共用序列与阈值计算（与大图完全同源） ──
  const buyCard = useMemo(
    () => fundingQuery.data?.cards?.find((c) => c.id === "cn-margin-buy-share-a-stocks"),
    [fundingQuery.data],
  );
  const buyRawPts = buyCard?.points ?? [];
  const buyThresholds = useMemo(
    () => buildMetricThresholds("cn-margin-buy", buyRawPts),
    [buyRawPts],
  );

  const marginRatioPts = useMemo(
    () => cleanPoints(seriesPoints(ratesQuery.data?.series.margin_rzyezb)),
    [ratesQuery.data],
  );
  const marginBalanceThresholds = useMemo(
    () => buildMetricThresholds("cn-margin-balance", marginRatioPts),
    [marginRatioPts],
  );

  const hyMerged = useMemo(() => {
    const usObsHy = usObsQuery.data?.items.find((i) => i.metric_id === "hy_oas");
    const obsPt =
      isFiniteNum(usObsHy?.value) && usObsHy?.observation_date
        ? [{ date: usObsHy.observation_date, value: usObsHy.value }]
        : undefined;
    return mergeSeries(panelQuery.data?.cards["hy-oas"]?.points, hySource.points, obsPt);
  }, [panelQuery.data, hySource.points, usObsQuery.data]);
  const hyThresholds = useMemo(() => buildMetricThresholds("hy-oas", hyMerged), [hyMerged]);

  const vixMerged = useMemo(
    () => mergeSeries(panelQuery.data?.cards["vix"]?.points, vixSource.points),
    [panelQuery.data, vixSource.points],
  );
  const vixThresholds = useMemo(() => buildMetricThresholds("vix", vixMerged), [vixMerged]);
  const vixTermLast = useMemo(() => {
    const live = cleanPoints(seriesPoints(ratesQuery.data?.series.vix_term));
    if (live.length > 0) return live[live.length - 1];
    const pts = cleanPoints(panelQuery.data?.cards["vix-term-structure"]?.points);
    return pts[pts.length - 1] ?? null;
  }, [ratesQuery.data, panelQuery.data]);

  const fixedBreadth = BREADTH_EXTERNAL_REFERENCES.stockcharts.sma50;
  const fetching =
    cnBreadth.isFetching ||
    usBreadth.isFetching ||
    cnErp.isFetching ||
    usErpSource.isPending ||
    hySource.isPending ||
    ratesQuery.isFetching ||
    cnObsQuery.isFetching;

  // ── 中美四维交叉判读摘要（估值 × 多周期宽度 × 信用两融 × 波动，聚焦高胜率实证场景） ──
  const cnJointSummary = useMemo((): JointVerdict => {
    const bHist = cnBreadth.data?.history ?? [];
    const nB = bHist.length;
    const bLast = bHist[nB - 1];
    const bPrev5 = nB > 5 ? bHist[nB - 6] : undefined;
    const b50 = bLast?.breadth_50;
    const b20 = bLast?.breadth_20;
    const b200 = bLast?.breadth_200;
    const bLow = cnBreadth.data?.observation?.latest?.horizons["50"]?.lower;
    const erpVal = cnErpSnap.latest?.value;
    const erpInner = cnErpSnap.latest ? innerErpRails(cnErpSnap.latest) : null;
    const buyClean = cleanPoints(buyRawPts);
    const buyVal = buyClean[buyClean.length - 1]?.value;
    const buyMa20 = buyThresholds?.dynamicSeries[0]?.latest;
    const marginBalPct3y =
      marginRatioPts.length >= 60
        ? historicalPosition(marginRatioPts, Math.min(756, marginRatioPts.length - 1))
        : null;

    if (!isFiniteNum(b50)) {
      return { tone: "neutral", verdict: "读取中", chips: [], lead: "", highlight: "正在同步宽度与两融数据…" };
    }

    const isDualLow = isFiniteNum(b200) && b50 <= 20 && b200 <= 20;
    const wasDualLow30d = bHist
      .slice(Math.max(0, nB - 31))
      .some((r) => isFiniteNum(r.breadth_50) && isFiniteNum(r.breadth_200) && r.breadth_50 <= 20 && r.breadth_200 <= 20);
    const isLowBreadth = isFiniteNum(bLow) ? b50 <= bLow || b50 <= 20 : b50 <= 20;
    const wasLow50_30d = bHist
      .slice(Math.max(0, nB - 31))
      .some((r) => isFiniteNum(r.breadth_50) && r.breadth_50 <= (isFiniteNum(bLow) ? Math.max(20, bLow) : 20));
    const b20Delta5 = isFiniteNum(b20) && isFiniteNum(bPrev5?.breadth_20) ? b20 - bPrev5!.breadth_20! : null;
    const b20Rising = isFiniteNum(b20Delta5) && b20Delta5 > 0;
    const b50Falling = isFiniteNum(bPrev5?.breadth_50) && b50 < bPrev5!.breadth_50!;

    const sseVals = (overlayPriceQuery.data?.series.sse?.values ?? []).filter(isFiniteNum);
    const sseLast = sseVals.length ? sseVals[sseVals.length - 1] : null;
    const sseMa20 = sseVals.length >= 20 ? sseVals.slice(-20).reduce((a, b) => a + b, 0) / 20 : null;
    const sseMa50 = sseVals.length >= 50 ? sseVals.slice(-50).reduce((a, b) => a + b, 0) / 50 : null;
    const priceAboveMa50 = isFiniteNum(sseLast) && isFiniteNum(sseMa50) && sseLast > sseMa50;
    const priceBelowMa20 = isFiniteNum(sseLast) && isFiniteNum(sseMa20) && sseLast < sseMa20;

    const erpMid =
      isFiniteNum(erpInner?.upper) && isFiniteNum(erpInner?.lower)
        ? (erpInner!.upper! + erpInner!.lower!) / 2
        : null;
    const erpOneSigma =
      isFiniteNum(erpMid) && isFiniteNum(erpInner?.upper)
        ? erpMid + ((erpInner!.upper! - erpMid) * 2) / 3
        : null;
    const cheapErp15 = isFiniteNum(erpVal) && isFiniteNum(erpInner?.upper) && erpVal >= erpInner!.upper!;
    const cheapErp10 = isFiniteNum(erpVal) && isFiniteNum(erpOneSigma) && erpVal >= erpOneSigma;
    const erpBelowMean = isFiniteNum(erpVal) && isFiniteNum(erpMid) && erpVal <= erpMid;

    const buyIce = isFiniteNum(buyVal) && buyVal <= 6.8;
    const crowdedMargin = isFiniteNum(buyVal) && buyVal >= 10.2;
    const marginHeavy80 = isFiniteNum(marginBalPct3y) && marginBalPct3y >= 80;
    const marginWarming = isFiniteNum(buyVal) && isFiniteNum(buyMa20) && buyVal > buyMa20;

    const wasB20Over70_10d =
      nB >= 4
      && bHist.slice(Math.max(0, nB - 11), nB - 1).some((r) => isFiniteNum(r.breadth_20) && r.breadth_20 >= 70);
    const wasB50Over80_30d =
      nB >= 6
      && bHist.slice(Math.max(0, nB - 31), nB - 1).some((r) => isFiniteNum(r.breadth_50) && r.breadth_50 >= 80);
    const wasB20Over80_20d =
      nB >= 6
      && bHist.slice(Math.max(0, nB - 21), nB - 1).some((r) => isFiniteNum(r.breadth_20) && r.breadth_20 >= 80);
    const zweigThrust =
      isFiniteNum(b20)
      && b20 >= 75
      && bHist.slice(Math.max(0, nB - 13), nB - 1).some((r) => isFiniteNum(r.breadth_20) && r.breadth_20 <= 20);

    // 1. 股票偏便宜 + 前期跌透后站上50日均线（33年全史后60日胜率76.0%）
    if (cheapErp10 && wasLow50_30d && priceAboveMa50) {
      return {
        tone: "supportive",
        verdict: "股票划算 + 站回50日线",
        chips: [
          { label: "股债利差", value: `${erpVal!.toFixed(2)}pp 偏便宜`, tone: "good" },
          { label: "指数趋势", value: "站上50日均线", tone: "good" },
        ],
        lead: "买股比买国债划算，且前期大跌后指数已重新站上50日均线（33年历史后60日上涨率76%）",
        highlight: "止跌转强已确认，可给正常至偏积极仓位",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-cn", initialRuleId: "erp_cheap_w3" }) },
      };
    }

    // 2. 长短线跌透后 · 指数站上50日均线（近5年60日胜率80.0%）
    if (wasDualLow30d && priceAboveMa50) {
      return {
        tone: "supportive",
        verdict: "跌透回暖 · 站上50日线",
        chips: [
          { label: "指数趋势", value: "站上50日均线", tone: "good" },
          { label: "50日宽度", value: `${b50.toFixed(1)}%`, tone: "good" },
          ...(marginWarming && isFiniteNum(buyVal)
            ? [{ label: "融资买入", value: `${buyVal.toFixed(2)}% 回暖`, tone: "good" as const }]
            : []),
        ],
        lead: "前期长短线跌透后，指数重新站回50日均线（近5年后60日上涨率80%）",
        highlight: "走势回暖已确认，分批恢复正常仓位",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-cn", initialRuleId: "dual_low_w3" }) },
      };
    }

    // 3. 长短线都跌透（B50&B200≤20%，等站上50日均线）
    if (isDualLow && !priceAboveMa50) {
      return {
        tone: "caution",
        verdict: buyIce ? "全场跌透 + 没人借钱买" : "长短线都跌透 · 等企稳",
        chips: [
          { label: "50/200日", value: `${b50.toFixed(1)}% / ${b200!.toFixed(1)}% 均≤20%`, tone: "good" },
          { label: "指数趋势", value: "还在50日线下", tone: "warn" },
          ...(cheapErp15
            ? [{ label: "股债利差", value: "偏便宜", tone: "good" as const }]
            : isFiniteNum(buyVal)
              ? [{ label: "融资买入", value: `${buyVal.toFixed(2)}%${buyIce ? " 冷清" : ""}`, tone: buyIce ? ("good" as const) : ("muted" as const) }]
              : []),
        ],
        lead: "站上50日和200日均线的股票都不到2成（近5年后120日上涨率86%，但弱市里可能还会磨底）",
        highlight: "手头底仓别恐慌割肉；想加仓等 指数站上50日均线 再动手",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-cn", initialRuleId: "reversal_bottom" }) },
      };
    }

    // 4. 一般低位（仅50日低位，200日未破20%）
    if (isLowBreadth && !priceAboveMa50) {
      return {
        tone: "caution",
        verdict: "多数股跌透 · 还没止跌",
        chips: [
          { label: "50日宽度", value: `${b50.toFixed(1)}% 低位`, tone: "warn" },
          { label: "指数趋势", value: "还在50日线下", tone: "muted" },
          ...(isFiniteNum(buyVal)
            ? [{ label: "融资买入", value: `${buyVal.toFixed(2)}%${buyIce ? " 冷清" : ""}`, tone: buyIce ? ("good" as const) : ("muted" as const) }]
            : []),
        ],
        lead: "站上50日线的股票很少，同时指数还没回到50日均线上方",
        highlight: "别急着伸手抄底，等 指数站上50日均线 再跟进",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-cn", initialRuleId: "dual_low_w3" }) },
      };
    }

    // 5. 股票不算便宜 + 大涨过热后跌破20日线
    if (erpBelowMean && wasB20Over80_20d && b50 < 50 && isFiniteNum(b20) && b20 < 50 && priceBelowMa20) {
      return {
        tone: "caution",
        verdict: "不算便宜 + 大涨后破20日线",
        chips: [
          { label: "股债利差", value: `${erpVal!.toFixed(2)}pp 低于均值`, tone: "warn" },
          { label: "50日宽度", value: `${b50.toFixed(1)}% 跌破半数`, tone: "warn" },
        ],
        lead: "股票已不算便宜，且短线大涨过热后跌破20日均线（沪深300历史后20日平均跌3.0%）",
        highlight: "波段转弱信号，优先减仓把利润落袋",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "erp-cn" }) },
      };
    }

    // 6. 全面普涨过热后跌破20日线
    if (wasB50Over80_30d && b50 < 50 && priceBelowMa20) {
      return {
        tone: "caution",
        verdict: "普涨退潮 · 跌破20日线",
        chips: [
          { label: "50日宽度", value: `${b50.toFixed(1)}% 跌破半数`, tone: "warn" },
          { label: "指数趋势", value: "跌破20日均线", tone: "warn" },
        ],
        lead: "前期普涨过热后退潮，过半股票掉队且指数跌破20日线（上证33年历史后20日61%概率下跌）",
        highlight: "上涨势头转弱，破位品种及时减仓锁利",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-cn", initialRuleId: "hot_retreat_break" }) },
      };
    }

    // 7. 大势偏弱 + 短线冲高跌破20日线
    if (isFiniteNum(b200) && b200 < 50 && wasB20Over70_10d && isFiniteNum(b20) && b20 < 50 && priceBelowMa20) {
      return {
        tone: "caution",
        verdict: "大势偏弱 · 反弹破20日线",
        chips: [
          { label: "200日宽度", value: `${b200.toFixed(1)}% 过半在年线下`, tone: "warn" },
          { label: "20日宽度", value: `${b20.toFixed(1)}% 冲高回落`, tone: "warn" },
        ],
        lead: "过半股票还在年线下方，短线急涨一波后又跌破20日线（33年历史后20日平均跌1.5%）",
        highlight: "弱势反弹容易打回原形，别追高、先减仓",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-cn", initialRuleId: "weak_base_rally_fade" }) },
      };
    }

    // 8. 借钱炒股过热 + 多数股走弱
    if ((crowdedMargin || marginHeavy80) && b50 < 50 && (b50Falling || priceBelowMa20)) {
      return {
        tone: "caution",
        verdict: "借钱炒股过热 · 走势转弱",
        chips: [
          crowdedMargin
            ? { label: "融资买入", value: `${buyVal!.toFixed(2)}% 偏热`, tone: "warn" }
            : { label: "融资余额", value: `3年P${Math.round(marginBalPct3y!)} 偏高`, tone: "warn" },
          { label: "50日宽度", value: `${b50.toFixed(1)}% <50%`, tone: "warn" },
        ],
        lead: "借钱买股处于高位，但超过一半的股票已跌破50日均线",
        highlight: "别再追高，收紧止盈线防回撤",
        action: {
          label: "看历史表现 ↗",
          onClick: () => setSubModal({ id: "cn-financing", financingTab: crowdedMargin ? "buy" : "balance" }),
        },
      };
    }

    // 9. 两周内买盘全面爆发
    if (zweigThrust) {
      return {
        tone: "supportive",
        verdict: "两周内买盘全面爆发",
        chips: [
          { label: "20日宽度", value: `${b20!.toFixed(1)}% 冲上75%`, tone: "good" },
          { label: "50日宽度", value: `${b50.toFixed(1)}%`, tone: "good" },
        ],
        lead: "两周内站上20日线的股票从不足2成猛增到75%以上（33年96次后20日平均涨2.5%）",
        highlight: "大资金集中进场信号，顺势跟进强势主线",
      };
    }

    return {
      tone: "neutral",
      verdict: "市场常态",
      chips: [
        { label: "50日宽度", value: `${b50.toFixed(1)}%`, tone: "muted" },
        ...(isFiniteNum(buyVal) ? [{ label: "融资买入", value: `${buyVal.toFixed(2)}%`, tone: "muted" as const }] : []),
      ],
      lead: b20Rising ? "近期上涨股票在变多" : "近期上涨股票在减少",
      highlight: "按 BIAO 主图趋势正常持仓即可",
    };
  }, [cnBreadth.data, cnErpSnap, buyRawPts, buyThresholds, marginRatioPts, overlayPriceQuery.data]);

  const usJointSummary = useMemo((): JointVerdict => {
    const bHist = usBreadth.data?.history ?? [];
    const nB = bHist.length;
    const bLast = bHist[nB - 1];
    const bPrev1 = nB > 1 ? bHist[nB - 2] : undefined;
    const bPrev3 = nB > 3 ? bHist[nB - 4] : undefined;
    const bPrev20 = nB > 20 ? bHist[nB - 21] : undefined;
    const b50 = bLast?.breadth_50;
    const b20 = bLast?.breadth_20;
    const b200 = bLast?.breadth_200;
    const hyLast = hyMerged[hyMerged.length - 1]?.value;
    const hyD20 = recentDelta(hyMerged, 20)?.difference;
    const vixLast = vixMerged[vixMerged.length - 1]?.value;
    const termVal = vixTermLast?.value;

    if (!isFiniteNum(b50) || !isFiniteNum(hyLast) || !isFiniteNum(vixLast)) {
      return { tone: "neutral", verdict: "读取中", chips: [], lead: "", highlight: "正在同步宽度、信用与波动数据…" };
    }

    const isDualLowUs = isFiniteNum(b200) && b50 <= 15 && b200 <= 15;
    const creditStressed = hyLast >= 4.0 || (isFiniteNum(hyD20) && hyD20 >= 0.5);
    const creditContagion = (hyLast >= 4.5 || (isFiniteNum(hyD20) && hyD20 >= 0.5)) && vixLast >= 25 && b50 < 40;
    const vixElevated = vixLast >= 20;
    const vixPanic = vixLast >= 30;
    const termInverted = isFiniteNum(termVal) && termVal >= 1.0;
    const breadthWeakening = isFiniteNum(b20) && b20 < b50;

    const wasB20Low5d = bHist
      .slice(Math.max(0, nB - 6))
      .some((r) => isFiniteNum(r.breadth_20) && r.breadth_20 <= 18);
    const isBullPullbackTurn =
      isFiniteNum(b200)
      && b200 > 50
      && wasB20Low5d
      && isFiniteNum(b20)
      && isFiniteNum(bPrev1?.breadth_20)
      && b20 > bPrev1!.breadth_20!;

    const recentVix10 = vixMerged.slice(-11);
    const peakVix10 = recentVix10.reduce((mx, p) => (p.value > mx ? p.value : mx), -Infinity);
    const isVixUnwind =
      peakVix10 >= 28
      && vixLast <= peakVix10 * 0.88
      && isFiniteNum(b20)
      && isFiniteNum(bPrev3?.breadth_20)
      && b20 > bPrev3!.breadth_20!;

    const b50Delta20 = isFiniteNum(bPrev20?.breadth_50) ? b50 - bPrev20!.breadth_50! : null;

    // 1. 长短线都跌透黄金坑（标普46年仅12次，后20日与120日胜率均达91.7%）
    if (isDualLowUs) {
      return {
        tone: "supportive",
        verdict: "长短线跌透 · 罕见大底",
        chips: [
          { label: "50/200日", value: `${b50.toFixed(1)}% / ${b200!.toFixed(1)}% 均≤15%`, tone: "good" },
          { label: "企业债利差", value: `${hyLast.toFixed(2)}%`, tone: creditStressed ? "warn" : "good" },
          { label: "恐慌VIX", value: `${vixLast.toFixed(1)}`, tone: "warn" },
        ],
        lead: "标普46年只出现过12次这么透的大跌，之后20日与120日上涨率均达92%（平均涨7.5% / 13.0%）",
        highlight: "难得的恐慌黄金坑，分批积极买入核心资产",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-us", initialRuleId: "reversal_bottom" }) },
      };
    }

    // 2. 股市大跌 + 企业借钱变贵（真出风险）
    if (creditStressed && (vixElevated || vixPanic)) {
      return {
        tone: "caution",
        verdict: creditContagion ? "股市大跌 + 企业借钱变贵" : "股市波动 + 企业借钱变贵",
        chips: [
          { label: "恐慌VIX", value: `${vixLast.toFixed(1)} 偏高`, tone: "warn" },
          { label: "企业债利差", value: `${hyLast.toFixed(2)}% 飙升`, tone: "warn" },
          { label: "50日宽度", value: `${b50.toFixed(1)}%`, tone: "muted" },
        ],
        lead: "连企业发债借钱的利息都明显涨上来了，说明资金面真吃紧（历史上20日平均最大回撤9.1%）",
        highlight: "一旦跌破趋势果断减仓避险",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-us", initialRuleId: "us_credit_contagion" }) },
      };
    }

    // 3. 牛市急跌后止跌 / 恐慌冲高回落
    if (isBullPullbackTurn) {
      return {
        tone: "supportive",
        verdict: "牛市急跌后止跌",
        chips: [
          { label: "200日宽度", value: `${b200!.toFixed(1)}% 大势向上`, tone: "good" },
          { label: "20日宽度", value: `${b20!.toFixed(1)}% 止跌回升`, tone: "good" },
          { label: "企业债利差", value: `${hyLast.toFixed(2)}% 平稳`, tone: "good" },
        ],
        lead: "过半股票仍在年线上方，短线急跌洗盘后重新回升（标普46年81次后20日上涨率80%）",
        highlight: "牛市回头买点确认，恢复正常仓位",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-us", initialRuleId: "bull_pullback_turn" }) },
      };
    }

    if (isVixUnwind && !creditStressed) {
      return {
        tone: "supportive",
        verdict: "恐慌冲高回落 · 企稳",
        chips: [
          { label: "恐慌VIX", value: `${vixLast.toFixed(1)} 见顶回落`, tone: "good" },
          { label: "20日宽度", value: `${b20!.toFixed(1)}% 回升`, tone: "good" },
          { label: "企业债利差", value: `${hyLast.toFixed(2)}% 平稳`, tone: "good" },
        ],
        lead: "恐慌指数从高点回落超12%，上涨股票同步变多（标普105段后60日上涨率77%）",
        highlight: "恐慌情绪缓解，恢复正常仓位",
        action: { label: "看历史表现 ↗", onClick: () => setSubModal({ id: "vix" }) },
      };
    }

    // 4. 股市恐慌但债市没事（纯情绪虚惊）
    if (vixElevated && !creditStressed) {
      const immuneBull = isFiniteNum(b200) && b200 > 50 && vixLast >= 22;
      const nearBaseEdge = isFiniteNum(b200) && b200 <= 50;
      return {
        tone: "caution",
        verdict: immuneBull ? "股市恐慌 · 但债市没事" : "股市回调 · 债市很稳",
        chips: [
          {
            label: "恐慌VIX",
            value: `${vixLast.toFixed(1)}${termInverted ? " 短线极慌" : " >20升温"}`,
            tone: "warn",
          },
          { label: "企业债利差", value: `${hyLast.toFixed(2)}% 平稳`, tone: "good" },
          immuneBull
            ? { label: "200日宽度", value: `${b200!.toFixed(1)}% 大势向上`, tone: "good" }
            : { label: "200日宽度", value: `${isFiniteNum(b200) ? b200.toFixed(1) : b50.toFixed(1)}% 靠近50%线`, tone: "warn" },
        ],
        lead: immuneBull
          ? "美股短线被吓跌，但企业借钱利率很稳、公司没出真事（历史同类后60日上涨率89%、平均涨5.4%）"
          : "企业借钱利率稳在4%以下没出事，标普正回踩年线强弱分界",
        highlight: nearBaseEdge
          ? "底仓别被吓跑，新买仓位先减半；盯紧企业债利差别超4%"
          : "大趋势没坏别乱砍底仓，等恐慌回落或走势站稳再加仓",
        tail: immuneBull ? "（新买仓位先减半）" : undefined,
        action: {
          label: "看历史表现 ↗",
          onClick: () => setCoreDetail({ id: "breadth-us", initialRuleId: "us_vix_spike_credit_calm" }),
        },
      };
    }

    // 5. 指数高位 · 多数股票掉队
    if (b50 < 50 && isFiniteNum(b50Delta20) && b50Delta20 <= -8 && isFiniteNum(b200) && b200 >= 45) {
      return {
        tone: "caution",
        verdict: "指数高位 · 多数股掉队",
        chips: [
          { label: "50日宽度", value: `${b50.toFixed(1)}% (${signedFmt(b50Delta20, 1)}pp)`, tone: "warn" },
          { label: "企业债利差", value: `${hyLast.toFixed(2)}% 平稳`, tone: "good" },
        ],
        lead: "只剩少数大盘股撑着指数，超过一半的股票已经跌破50日均线",
        highlight: "别追高，小心大盘补跌",
        action: { label: "看历史表现 ↗", onClick: () => setCoreDetail({ id: "breadth-us", initialRuleId: "top_divergence" }) },
      };
    }

    return {
      tone: b50 >= 50 && !breadthWeakening ? "supportive" : "neutral",
      verdict: b50 >= 50 && !breadthWeakening ? "大势健康" : "走势平稳",
      chips: [
        { label: "50日宽度", value: `${b50.toFixed(1)}%`, tone: b50 >= 50 ? "good" : "muted" },
        { label: "企业债利差", value: `${hyLast.toFixed(2)}% 平稳`, tone: "good" },
        { label: "恐慌VIX", value: `${vixLast.toFixed(1)} 平静`, tone: "muted" },
      ],
      lead: "企业债与恐慌指数都很平静",
      highlight: "顺应主图趋势正常持仓",
    };
  }, [usBreadth.data, hyMerged, vixMerged, vixTermLast]);

  // ── 卡片 1：沪深300 · 股债利差 ──
  const renderCnErpCard = () => {
    const s = cnErpSnap;
    const known = Boolean(s.latest) && s.quality !== "error" && s.quality !== "missing";
    const latest = s.latest;
    const innerLatest = latest ? innerErpRails(latest) : { lower: null, upper: null };
    const tone: StanceTone = !known
      ? "neutral"
      : latest?.phase === "high" || (isFiniteNum(latest?.value) && isFiniteNum(innerLatest.upper) && latest!.value >= innerLatest.upper!)
        ? "supportive"
        : "neutral";
    const headline = !known
      ? cnErp.isPending
        ? "读取中…"
        : "估值待补"
      : latest?.phase === "high"
        ? "高于+2σ · 明显便宜"
        : isFiniteNum(latest?.value) && isFiniteNum(innerLatest.upper) && latest!.value >= innerLatest.upper!
          ? "高于+1.5σ · 偏便宜"
          : latest?.phase === "low"
            ? "低于−2σ · 偏贵背景"
            : "2σ区间内";
    const delta = recentDelta(cleanPoints(cnErpInputPoints), 4);
    const upperGap = upperRailGapText(latest?.value, innerLatest.upper);

    return (
      <article className="hes-card" aria-label="沪深300 · 股债利差">
        <div className="hes-card-top">
          <h3 className="hes-card-title">沪深300 · 股债利差</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{headline}</span>
            <button type="button" className="hes-zoom-btn" onClick={() => setCoreDetailId("erp-cn")}>
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-value-row">
          <span className="hes-val">
            {known ? fmt(latest?.value) : "—"}
            <small>百分点</small>
          </span>
          <span className="hes-meta-inline">
            {delta ? (
              <span>
                较{delta.previous.date.slice(5)} <b>{signedFmt(delta.difference)}</b>
              </span>
            ) : null}
            <time dateTime={latest?.date}>{latest?.date ?? "待更"}</time>
          </span>
        </div>

        <div className="hes-rail-line" title="滚动3年均值±1.5σ/2σ；冲过上轨代表股票比国债划算，跌破下轨在牛市很常见、别单凭偏贵卖股票">
          <span>
            便宜上轨 <b className="rail-high">+1.5σ {fmt(innerLatest.upper)}</b> /{" "}
            <b className="rail-high">+2σ {fmt(latest?.upper)}</b>
          </span>
          <span className="hes-dot">·</span>
          <span>
            下轨 <b className="rail-low">{fmt(innerLatest.lower)}</b>
          </span>
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近5年·周"
          unitSuffix="pp"
          invertShade
          shadeAbove={cnErpInnerRows.map((p) => p.upper)}
          shadeBelow={cnErpInputPoints.map((p) => p.lower)}
          dates={cnErpInputPoints.map((p) => p.date)}
          lines={[{ name: "股债利差", color: CHART_COLORS.primary, values: cnErpInputPoints.map((p) => p.value) }]}
          lower={cnErpInputPoints.map((p) => p.lower)}
          upper={cnErpInputPoints.map((p) => p.upper)}
          references={[
            {
              name: "+1.5σ便宜轨",
              color: "#2f756b",
              values: cnErpInnerRows.map((p) => p.upper),
              endLabel: isFiniteNum(innerLatest.upper) ? `+1.5σ ${innerLatest.upper.toFixed(1)}` : undefined,
            },
            {
              name: "−1.5σ下轨",
              color: "#b49d81",
              values: cnErpInnerRows.map((p) => p.lower),
              endLabel: isFiniteNum(innerLatest.lower) ? `−1.5σ ${innerLatest.lower.toFixed(1)}` : undefined,
            },
          ]}
          label="沪深300股债利差近五年周频走势，含1.5σ与2σ双层上下轨"
        />

        <p className="hes-takeaway">
          {upperGap ? <>{upperGap} · <b>过上轨代表划算，破下轨别乱卖</b></> : <>滚动3年轨 · <b>过上轨代表划算，破下轨别乱卖</b></>}
        </p>
      </article>
    );
  };

  // ── 卡片 3：标普500 · 股债利差 ──
  const renderUsErpCard = () => {
    const latest = usErpRows[usErpRows.length - 1];
    const ready = !usErpSource.error && !usErpSource.isPending && isFiniteNum(latest?.value);
    const z = latest?.z;
    const innerRows = usErpRails[0]?.rows ?? [];
    const outerRows = usErpRails[1]?.rows ?? [];
    const innerLast = innerRows[innerRows.length - 1];
    const outerLast = outerRows[outerRows.length - 1];
    const visible = usErpRows.slice(-1260);
    const visInner = innerRows.slice(-1260);
    const visOuter = outerRows.slice(-1260);
    const prior = usErpRows.length > 20 ? usErpRows[usErpRows.length - 21] : undefined;
    const change = ready && isFiniteNum(prior?.value) ? latest!.value! - prior!.value! : null;

    const aboveUpper = ready && isFiniteNum(z) && z >= 1.5;
    const tone: StanceTone = aboveUpper ? "supportive" : "neutral";
    const headline = !ready
      ? usErpSource.isPending
        ? "读取中…"
        : "资料暂不可读"
      : !isFiniteNum(z)
        ? "历史不足"
        : z > 2
          ? "高于+2σ · 估值改善"
          : z < -2
            ? "低于−2σ · 利率压低"
            : "2σ区间内";
    const upperGap = upperRailGapText(latest?.value, innerLast?.upper);

    return (
      <article className="hes-card" aria-label="标普500 · 股债利差">
        <div className="hes-card-top">
          <h3 className="hes-card-title">标普500 · 股债利差</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{headline}</span>
            <button type="button" className="hes-zoom-btn" onClick={() => setCoreDetailId("erp-us")}>
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-value-row">
          <span className="hes-val">
            {ready ? fmt(latest?.value) : "—"}
            <small>百分点</small>
          </span>
          <span className="hes-meta-inline">
            {change !== null && prior ? (
              <span>
                较{prior.date.slice(5)} <b>{signedFmt(change)}</b>
              </span>
            ) : null}
            <time dateTime={latest?.date}>{latest?.date ?? "待更"}</time>
          </span>
        </div>

        <div className="hes-rail-line" title="此前3年均值±1.5σ/2σ；近3年美债高利率压低利差且带宽极窄，下轨不作减仓线">
          <span>
            上轨 <b className="rail-high">+1.5σ {fmt(innerLast?.upper)}</b> /{" "}
            <b className="rail-high">+2σ {fmt(outerLast?.upper)}</b>
          </span>
          <span className="hes-dot">·</span>
          <span>
            下轨 <b className="rail-low">{fmt(innerLast?.lower)}</b>
          </span>
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近5年·日"
          unitSuffix="pp"
          invertShade
          shadeAbove={visInner.map((r) => r.upper)}
          shadeBelow={visOuter.map((r) => r.lower)}
          dates={visible.map((r) => r.date)}
          lines={[{ name: "美股利差", color: CHART_COLORS.primary, values: visible.map((r) => r.value) }]}
          references={[
            {
              name: "+2σ上轨",
              color: "#327c72",
              values: visOuter.map((r) => r.upper),
              endLabel: isFiniteNum(outerLast?.upper) ? `+2σ ${outerLast!.upper!.toFixed(2)}` : undefined,
            },
            {
              name: "+1.5σ上轨",
              color: "#73a89f",
              values: visInner.map((r) => r.upper),
            },
            {
              name: "−1.5σ下轨",
              color: "#bc9974",
              values: visInner.map((r) => r.lower),
            },
            {
              name: "−2σ下轨",
              color: "#986737",
              values: visOuter.map((r) => r.lower),
              endLabel: isFiniteNum(outerLast?.lower) ? `−2σ ${outerLast!.lower!.toFixed(2)}` : undefined,
            },
          ]}
          label="标普500股债利差近五年日频走势，含1.5σ与2σ双层上下轨"
        />

        <p className="hes-takeaway">
          {upperGap ? <>{upperGap} · <b>美债息高拉低利差，破下轨别乱卖</b></> : <>盈利月频 · <b>美债息高拉低利差，破下轨别乱卖</b></>}
        </p>
      </article>
    );
  };

  // ── 卡片 2 & 4：全A / 标普500 · 市场宽度 ──
  const renderBreadthCard = (
    id: "breadth-cn" | "breadth-us",
    title: string,
    market: BreadthMarket,
    q: ReturnType<typeof useBreadth>,
  ) => {
    const snap = buildAlertSnapshot(breadthInput(market, q.data, q.isError), nowDate);
    const rows = (q.data?.history ?? []).slice(-90);
    const latest = rows[rows.length - 1];
    const obsLatest = q.data?.observation?.latest ?? null;
    const reading =
      snap.quality === "ready" && obsLatest?.date === snap.latest?.date ? obsLatest : obsLatest;
    const interp = breadthInterpretation(reading);
    const delta = recentDelta(
      cleanPoints(rows.map((p) => ({ date: p.date, value: p.breadth_50 ?? null }))),
      20,
    );
    const boundsByDate = new Map(
      (q.data?.observation?.history ?? []).map((p) => [p.date, p.horizons["50"]]),
    );
    const low = rows.map((p) =>
      boundsByDate.get(p.date)?.status === "ready" ? boundsByDate.get(p.date)!.lower : null,
    );
    const high = rows.map((p) =>
      boundsByDate.get(p.date)?.status === "ready" ? boundsByDate.get(p.date)!.upper : null,
    );
    const dynLow = snap.latest?.lower ?? null;
    const dynHigh = snap.latest?.upper ?? null;
    const b50 = latest?.breadth_50 ?? null;
    const b20 = latest?.breadth_20 ?? null;
    const b200 = latest?.breadth_200 ?? null;
    const coldThresh = market === "CN_ALL_A" ? 20 : 15;
    const isDualLowCard = isFiniteNum(b50) && isFiniteNum(b200) && b50 <= coldThresh && b200 <= coldThresh;
    const tone: StanceTone =
      q.isError || !isFiniteNum(b50)
        ? "neutral"
        : market === "SP500" && isDualLowCard
          ? "supportive"
          : interp.tone === "supportive"
            ? "supportive"
            : interp.tone === "caution" || snap.latest?.phase === "low" || isDualLowCard
              ? "caution"
              : "neutral";
    const headline = q.isError
      ? "资料暂不可读"
      : q.isPending && !latest
        ? "读取中…"
        : isDualLowCard
          ? "长短线跌透"
          : interp.headline;

    const colors = {
      "20": BREADTH_LINES[0].color,
      "50": BREADTH_LINES[1].color,
      "200": BREADTH_LINES[2].color,
    };
    const takeaway = isDualLowCard ? (
      market === "SP500" ? (
        <>长短线跌透(46年胜率92%) · <b>罕见大底，分批买</b></>
      ) : (
        <>长短线跌透(5年120日胜率86%) · <b>加仓等站上50日均线</b></>
      )
    ) : isFiniteNum(b50) && isFiniteNum(dynLow) && b50 <= dynLow ? (
      <>多数股票已跌透 · <b>加仓等指数站回50日均线</b></>
    ) : reading && snap.latest?.phase === "high" ? (
      <>高位观察区 · <b>{interp.watch}</b></>
    ) : (
      <>{interp.meaning}</>
    );

    return (
      <article className="hes-card" aria-label={title}>
        <div className="hes-card-top">
          <h3 className="hes-card-title">{title}</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{headline}</span>
            <button type="button" className="hes-zoom-btn" onClick={() => setCoreDetailId(id)}>
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-breadth-vals" aria-label="20日、50日、200日均线宽度读数">
          <div className="hes-breadth-triplet">
            <span className="hes-b-chip is-primary">
              <i style={{ background: colors["50"] }} />
              <em>50日</em>
              <strong>{isFiniteNum(b50) ? `${b50.toFixed(1)}%` : "—"}</strong>
            </span>
            <span className="hes-b-chip">
              <i style={{ background: colors["20"] }} />
              <em>20日</em>
              <b>{isFiniteNum(b20) ? `${b20.toFixed(1)}%` : "—"}</b>
            </span>
            <span className="hes-b-chip">
              <i style={{ background: colors["200"] }} />
              <em>200日</em>
              <b>{isFiniteNum(latest?.breadth_200) ? `${latest!.breadth_200!.toFixed(1)}%` : "—"}</b>
            </span>
          </div>
          <time className="hes-date-tag" dateTime={latest?.date} title={latest?.date}>
            {latest?.date ? latest.date.slice(5) : "待更"}
          </time>
        </div>

        <div
          className="hes-rail-line"
          title="50日均线宽度近5年（1260日）滚动P10/P90分位轨；括号内为美股StockCharts传统50日30%/70%固定参考，非200日线"
        >
          <span>
            50日轨(5年P10/P90) 低≤<b className="rail-high">{fmt(dynLow, 1)}%</b> / 高≥
            <b className="rail-low">{fmt(dynHigh, 1)}%</b>
            <small className="hes-ref-muted">({fixedBreadth.lower}/{fixedBreadth.upper}%)</small>
          </span>
          {delta ? (
            <>
              <span className="hes-dot">·</span>
              <span>
                较20日前 <b>{signedFmt(delta.difference, 1)}pp</b>
              </span>
            </>
          ) : null}
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近90日·日"
          dates={rows.map((p) => p.date)}
          percent
          lower={low}
          upper={high}
          lines={(["50", "20", "200"] as const).map((period) => ({
            name: `${period}日`,
            color: colors[period],
            values: rows.map((p) => p[`breadth_${period}`] ?? null),
          }))}
          label={`${title}近90条记录，加粗蓝线为50日宽度，配橙色20日与紫色200日及50日P10/P90历史区间`}
        />

        <p className="hes-takeaway">{takeaway}</p>
      </article>
    );
  };

  // ── 卡片 5：A股 · 融资买入占比 ──
  const renderCnMarginBuyCard = () => {
    const visiblePts = buyRawPts.slice(-120);
    const valid = cleanPoints(buyRawPts);
    const latest = valid[valid.length - 1];
    const delta5 = recentDelta(valid, 5);
    const ma20Series = buyThresholds?.dynamicSeries.find((d) => d.key === "ma20");
    const ma20Last = ma20Series?.latest ?? null;
    const visibleMa20 = visiblePts.map((p) => ma20Series?.byDate.get(p.date) ?? null);
    const liveBuy = cnObsQuery.data?.items.find((item) => item.metric_id === "margin_buy");

    const tone: StanceTone = !latest
      ? "neutral"
      : latest.value > 10.5
        ? "caution"
        : latest.value < 6.5
          ? "supportive"
          : "neutral";
    const badge = !latest
      ? fundingQuery.isPending
        ? "读取中…"
        : "资料待补"
      : latest.value > 10.5
        ? "拥挤 >10.5%"
        : latest.value < 6.5
          ? "冰点 <6.5%"
          : "常态热度";

    return (
      <article className="hes-card" aria-label="A股 · 融资买入占比">
        <div className="hes-card-top">
          <h3 className="hes-card-title">A股 · 融资买入占比</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{badge}</span>
            <button
              type="button"
              className="hes-zoom-btn"
              onClick={() => setSubModal({ id: "cn-financing", financingTab: "buy" })}
            >
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-value-row">
          <span className="hes-val">
            {latest ? `${latest.value.toFixed(2)}%` : "—"}
            <small>占A股成交</small>
          </span>
          <span className="hes-meta-inline">
            {delta5 ? (
              <span>
                5日 <b>{signedFmt(delta5.difference)}pp</b>
              </span>
            ) : null}
            <time dateTime={latest?.date}>{latest?.date ?? "待更"}</time>
          </span>
        </div>

        <div className="hes-rail-line" title="近一年实测经验分位 P5=6.60%、P95=10.60%；6.5%与10.5%对应杠杆冰点与短线亢奋边界">
          <span>
            20日均 <b>{isFiniteNum(ma20Last) ? `${ma20Last.toFixed(2)}%` : "—"}</b>
          </span>
          <span className="hes-dot">·</span>
          <span>
            P5/P95轨 <b className="rail-high">6.5%</b>(冰点)~<b className="rail-low">10.5%</b>(拥挤)
          </span>
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近半年·日"
          unitSuffix="%"
          shadeAbove={visiblePts.map((p) => (isFiniteNum(p.value) ? 10.5 : null))}
          shadeBelow={visiblePts.map((p) => (isFiniteNum(p.value) ? 6.5 : null))}
          dates={visiblePts.map((p) => p.date)}
          lines={[
            {
              name: "买入占比",
              color: CHART_COLORS.primary,
              values: visiblePts.map((p) => p.value),
            },
            {
              name: "20日均",
              color: "#d97706",
              values: visibleMa20,
            },
          ]}
          references={[
            {
              name: "拥挤线 10.5%",
              color: "#986737",
              values: visiblePts.map((p) => (isFiniteNum(p.value) ? 10.5 : null)),
              endLabel: "拥挤 10.5%",
            },
            {
              name: "冰点线 6.5%",
              color: "#327c72",
              values: visiblePts.map((p) => (isFiniteNum(p.value) ? 6.5 : null)),
              endLabel: "冰点 6.5%",
            },
          ]}
          label="沪深A股融资买入占成交额比例近半年走势，含20日均线及6.5%/10.5%高低参考线"
        />

        <p className="hes-takeaway">
          {isFiniteNum(liveBuy?.value) && liveBuy?.observation_date ? (
            <>日买入 {Math.round(liveBuy.value)}亿 ({liveBuy.observation_date.slice(5)}) · <b>破6.5%看企稳，超10.5%防过热</b></>
          ) : (
            <>借钱买股热度 · <b>破6.5%冷清看企稳，超10.5%防追高</b></>
          )}
        </p>
      </article>
    );
  };

  // ── 卡片 6：A股 · 融资余额占比 ──
  const renderCnMarginBalanceCard = () => {
    const valid = marginRatioPts;
    const latest = valid[valid.length - 1];
    const delta20 = recentDelta(valid, 20);
    const pct3y = historicalPosition(valid, Math.min(756, Math.max(60, valid.length - 1)));
    const visible = valid.slice(-252);

    const p85Series = marginBalanceThresholds?.dynamicSeries.find((d) => d.key === "p85_3y");
    const p50Series = marginBalanceThresholds?.dynamicSeries.find((d) => d.key === "p50_3y");
    const p15Series = marginBalanceThresholds?.dynamicSeries.find((d) => d.key === "p15_3y");

    const visHigh = visible.map((p) => p85Series?.byDate.get(p.date) ?? null);
    const visMid = visible.map((p) => p50Series?.byDate.get(p.date) ?? null);
    const visLow = visible.map((p) => p15Series?.byDate.get(p.date) ?? null);

    const totalSeries = ratesQuery.data?.series.margin_rzrqye;
    const totalYi =
      totalSeries && totalSeries.values.length
        ? totalSeries.values[totalSeries.values.length - 1]
        : null;

    const tone: StanceTone = !isFiniteNum(pct3y)
      ? "neutral"
      : pct3y >= 85
        ? "caution"
        : pct3y <= 15
          ? "supportive"
          : "neutral";
    const badge = !latest
      ? ratesQuery.isPending
        ? "读取中…"
        : "资料待补"
      : isFiniteNum(pct3y)
        ? pct3y >= 85
          ? `偏高 · P${pct3y.toFixed(0)}`
          : pct3y <= 15
            ? `偏低 · P${pct3y.toFixed(0)}`
            : `常态 · P${pct3y.toFixed(0)}`
        : "余额观察";

    return (
      <article className="hes-card" aria-label="A股 · 融资余额占比">
        <div className="hes-card-top">
          <h3 className="hes-card-title">A股 · 融资余额占比</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{badge}</span>
            <button
              type="button"
              className="hes-zoom-btn"
              onClick={() => setSubModal({ id: "cn-financing", financingTab: "balance" })}
            >
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-value-row">
          <span className="hes-val">
            {latest ? `${latest.value.toFixed(2)}%` : "—"}
            <small>占流通市值</small>
          </span>
          <span className="hes-meta-inline">
            {delta20 ? (
              <span>
                20日 <b>{signedFmt(delta20.difference)}pp</b>
              </span>
            ) : null}
            <time dateTime={latest?.date}>{latest?.date ?? "待更"}</time>
          </span>
        </div>

        <div className="hes-rail-line" title="过去3年（756交易日）滚动P15/P50/P85分位轨，看借钱炒股盘子轻重">
          <span>
            3年P15/P85轨 <b className="rail-high">{fmt(p15Series?.latest)}%</b>~
            <b className="rail-low">{fmt(p85Series?.latest)}%</b>
          </span>
          <span className="hes-dot">·</span>
          <span>
            {isFiniteNum(totalYi) ? (
              <>
                两融 <b>{(totalYi / 10000).toFixed(2)}万亿</b>
              </>
            ) : (
              "两融总额水位"
            )}
          </span>
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近1年·日"
          unitSuffix="%"
          shadeAbove={visHigh}
          shadeBelow={visLow}
          dates={visible.map((p) => p.date)}
          lines={[
            {
              name: "余额占比",
              color: CHART_COLORS.primary,
              values: visible.map((p) => p.value),
            },
          ]}
          references={[
            {
              name: "3年P85上轨",
              color: "#986737",
              values: visHigh,
              endLabel: isFiniteNum(p85Series?.latest) ? `P85 ${p85Series!.latest!.toFixed(2)}%` : undefined,
            },
            {
              name: "3年P50中枢",
              color: "#94a3b8",
              values: visMid,
            },
            {
              name: "3年P15下轨",
              color: "#327c72",
              values: visLow,
              endLabel: isFiniteNum(p15Series?.latest) ? `P15 ${p15Series!.latest!.toFixed(2)}%` : undefined,
            },
          ]}
          label="A股融资余额占流通市值比例近一年走势，含过去三年滚动P15/P50/P85经验分位轨"
        />

        <p className="hes-takeaway">
          {isFiniteNum(pct3y) ? (
            <>近3年 P{pct3y.toFixed(0)}分位 · <b>偏高且多数股走弱时注意防跌</b></>
          ) : (
            <>滚动3年分位 · <b>看借钱炒股盘子轻重</b></>
          )}
        </p>
      </article>
    );
  };

  // ── 卡片 7：美股 · 高收益债利差 HY OAS ──
  const renderUsHyOasCard = () => {
    const latest = hyMerged[hyMerged.length - 1];
    const delta20 = recentDelta(hyMerged, 20);
    const visible = hyMerged.slice(-252);
    const ma20Series = hyThresholds?.dynamicSeries.find((d) => d.key === "ma20");
    const p85Series = hyThresholds?.dynamicSeries.find((d) => d.key === "p85_1y");
    const visMa20 = visible.map((p) => ma20Series?.byDate.get(p.date) ?? null);
    const visP85 = visible.map((p) => p85Series?.byDate.get(p.date) ?? null);

    const rapidWiden = isFiniteNum(delta20?.difference) && delta20!.difference >= 0.5;
    const tone: StanceTone = !latest
      ? "neutral"
      : latest.value >= 4.0 || rapidWiden
        ? "caution"
        : "neutral";
    const badge = !latest
      ? hySource.isPending || panelQuery.isPending
        ? "读取中…"
        : "资料待补"
      : latest.value >= 5.0
        ? "借钱极贵 >5%"
        : latest.value >= 4.0 || rapidWiden
          ? "借钱变贵"
          : "债市平稳";

    return (
      <article className="hes-card" aria-label="美股 · 高收益债利差">
        <div className="hes-card-top">
          <h3 className="hes-card-title">美股 · 高收益债利差</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{badge}</span>
            <button
              type="button"
              className="hes-zoom-btn"
              onClick={() => setSubModal({ id: "hy-oas" })}
            >
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-value-row">
          <span className="hes-val">
            {latest ? fmt(latest.value) : "—"}
            <small>百分点</small>
          </span>
          <span className="hes-meta-inline">
            {delta20 ? (
              <span>
                20日 <b>{signedFmt(delta20.difference)}</b>
              </span>
            ) : null}
            <time dateTime={latest?.date}>{latest?.date ?? "待更"}</time>
          </span>
        </div>

        <div className="hes-rail-line" title="企业发债比美债多付的利息：4.0%为偏紧警戒线，5.0%代表企业借钱明显变难">
          <span>
            20日均 <b>{fmt(ma20Series?.latest)}%</b> · 1年P85 <b>{fmt(p85Series?.latest)}%</b>
          </span>
          <span className="hes-dot">·</span>
          <span>
            警戒 <b className="rail-low">4.0</b>/<b className="rail-low">5.0%</b>
          </span>
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近1年·日"
          unitSuffix="%"
          shadeAbove={visible.map(() => 4.0)}
          dates={visible.map((p) => p.date)}
          lines={[
            {
              name: "HY OAS",
              color: CHART_COLORS.primary,
              values: visible.map((p) => p.value),
            },
            {
              name: "20日均",
              color: "#64748b",
              values: visMa20,
            },
          ]}
          references={[
            {
              name: "警戒线 4.0%",
              color: "#986737",
              values: visible.map(() => 4.0),
              endLabel: "警戒 4.0%",
            },
            {
              name: "近1年P85高位轨",
              color: "#7c6a96",
              values: visP85,
              endLabel: isFiniteNum(p85Series?.latest) ? `P85 ${p85Series!.latest!.toFixed(2)}%` : undefined,
            },
          ]}
          label="美国高收益企业债利差近一年走势，含20日均线、近一年P85高位轨与4.0%警戒线"
        />

        <p className="hes-takeaway">
          {!latest ? (
            <>看美国企业借钱贵不贵 · <b>债市稳则美股大跌多是虚惊</b></>
          ) : latest.value >= 4.0 || rapidWiden ? (
            <>超4%警戒或急升 · <b>企业借钱变贵，小心美股真跌</b></>
          ) : (
            <>低于4%警戒线 · <b>企业借钱正常，股市波动多属虚惊</b></>
          )}
        </p>
      </article>
    );
  };

  // ── 卡片 8：美股 · VIX 恐慌指数 ──
  const renderUsVixCard = () => {
    const latest = vixMerged[vixMerged.length - 1];
    const delta5 = recentDelta(vixMerged, 5);
    const visible = vixMerged.slice(-180);
    const ma20Series = vixThresholds?.dynamicSeries.find((d) => d.key === "ma20");
    const p85Series = vixThresholds?.dynamicSeries.find((d) => d.key === "p85_3y");
    const visMa20 = visible.map((p) => ma20Series?.byDate.get(p.date) ?? null);
    const visP85 = visible.map((p) => p85Series?.byDate.get(p.date) ?? null);

    const tone: StanceTone = !latest
      ? "neutral"
      : latest.value >= 20
        ? "caution"
        : "neutral";
    const badge = !latest
      ? vixSource.isPending || panelQuery.isPending
        ? "读取中…"
        : "资料待补"
      : latest.value >= 30
        ? "恐慌 >30"
        : latest.value >= 20
          ? "波动升温"
          : "波动平静";

    const vixVsMa =
      latest && isFiniteNum(ma20Series?.latest) ? latest.value / ma20Series!.latest! : null;

    return (
      <article className="hes-card" aria-label="美股 · VIX 恐慌指数">
        <div className="hes-card-top">
          <h3 className="hes-card-title">美股 · VIX 恐慌指数</h3>
          <div className="hes-card-top-right">
            <span className={`hes-stance ${tone}`}>{badge}</span>
            <button
              type="button"
              className="hes-zoom-btn"
              onClick={() => setSubModal({ id: "vix" })}
            >
              大图 ↗
            </button>
          </div>
        </div>

        <div className="hes-value-row">
          <span className="hes-val">
            {latest ? fmt(latest.value) : "—"}
            <small>点</small>
          </span>
          <span className="hes-meta-inline">
            {delta5 ? (
              <span>
                5日 <b>{signedFmt(delta5.difference, 1)}</b>
              </span>
            ) : null}
            <time dateTime={latest?.date}>{latest?.date ?? "待更"}</time>
          </span>
        </div>

        <div className="hes-rail-line" title="20以上代表市场开始紧张，30以上代表极度恐慌">
          <span>
            20日均 <b>{fmt(ma20Series?.latest, 1)}</b> · 3年P85 <b>{fmt(p85Series?.latest, 1)}</b>
          </span>
          <span className="hes-dot">·</span>
          <span>
            参考线 <b className="rail-low">20</b>/<b className="rail-low">30</b>
          </span>
        </div>

        <MiniTrend
          height={CHART_H}
          windowTag="近9月·日"
          shadeAbove={visible.map(() => 20)}
          dates={visible.map((p) => p.date)}
          lines={[
            {
              name: "VIX",
              color: CHART_COLORS.primary,
              values: visible.map((p) => p.value),
            },
            {
              name: "20日均",
              color: "#64748b",
              values: visMa20,
            },
          ]}
          references={[
            {
              name: "恐慌线 30",
              color: "#986737",
              values: visible.map(() => 30),
              endLabel: "恐慌 30",
            },
            {
              name: "近3年P85高波轨",
              color: "#7c6a96",
              values: visP85,
              endLabel: isFiniteNum(p85Series?.latest) ? `P85 ${p85Series!.latest!.toFixed(1)}` : undefined,
            },
            {
              name: "升温线 20",
              color: "#bc9974",
              values: visible.map(() => 20),
              endLabel: "升温 20",
            },
          ]}
          label="标普500预期波动率VIX近九个月走势，含20日均线、近3年P85分位轨及20/30机制线"
        />

        <p className="hes-takeaway">
          {!latest ? (
            <>看美股短期恐慌程度 · <b>搭配左边企业债利差一起看</b></>
          ) : latest.value >= 30 ? (
            <>超30极度恐慌 · <b>新买仓位建议先减半</b></>
          ) : latest.value >= 20 ? (
            <>
              {isFiniteNum(vixVsMa) && vixVsMa > 1.15 ? `比均线高${((vixVsMa - 1) * 100).toFixed(0)}% · ` : ""}
              <b>超20恐慌升温，看债市稳不稳</b>
            </>
          ) : (
            <>低于20 · <b>市场情绪平静</b></>
          )}
        </p>
      </article>
    );
  };

  const activeObsEntry = subModal ? OBSERVATION_BY_ID.get(subModal.id) ?? null : null;

  const renderJointBanner = (marketTitle: string, summary: JointVerdict) => (
    <div className={`hes-combo-banner ${summary.tone}`}>
      <div className="hes-combo-top">
        <span className="hes-combo-market">{marketTitle}</span>
        <span className="hes-combo-verdict">{summary.verdict}</span>
        {summary.chips.length > 0 && (
          <div className="hes-combo-chips">
            {summary.chips.map((chip) => (
              <span key={chip.label} className={`hes-evi-chip ${chip.tone ?? "muted"}`}>
                <i>{chip.label}</i>
                <b>{chip.value}</b>
              </span>
            ))}
          </div>
        )}
        {summary.action && (
          <button type="button" className="hes-combo-jump" onClick={summary.action.onClick}>
            {summary.action.label}
          </button>
        )}
      </div>
      <div className="hes-combo-bottom">
        <span className="hes-combo-arrow">结论</span>
        <span>
          {summary.lead ? <span className="hes-combo-lead">{summary.lead} → </span> : null}
          <strong className="hes-combo-hl">{summary.highlight}</strong>
          {summary.tail ? <span className="hes-combo-tail">{summary.tail}</span> : null}
        </span>
      </div>
    </div>
  );

  const refreshAllEnv = () => {
    void Promise.all([
      cnErp.refetch(),
      cnBreadth.refetch(),
      usBreadth.refetch(),
      ratesQuery.refetch(),
      cnObsQuery.refetch(),
      usObsQuery.refetch(),
      fundingQuery.refetch(),
      panelQuery.refetch(),
    ]);
    usErpSource.retry();
    hySource.retry();
  };

  return (
    <>
      <section className={`hes-wrap${isFullMode ? " hes-full-mode" : isExpanded ? "" : " is-collapsed"}`} aria-label="大环境水位速览">
        {!isExpanded ? (
          <div className="hes-bar">
            <span className="hes-bar-tag">大环境</span>
            <button
              type="button"
              className={`hes-bar-pill ${cnJointSummary.tone}`}
              onClick={toggleExpanded}
              title={`A股：${cnJointSummary.lead ? `${cnJointSummary.lead} → ` : ""}${cnJointSummary.highlight}（点击展开 8 图水位）`}
            >
              <i className="hes-bar-dot" />
              <span className="hes-bar-mkt">A股</span>
              <b>{cnJointSummary.verdict}</b>
              {cnJointSummary.chips.slice(0, 2).map((chip) => (
                <span key={chip.label} className="hes-bar-kv">
                  {chip.label} {chip.value}
                </span>
              ))}
            </button>
            <button
              type="button"
              className={`hes-bar-pill ${usJointSummary.tone}`}
              onClick={toggleExpanded}
              title={`美股：${usJointSummary.lead ? `${usJointSummary.lead} → ` : ""}${usJointSummary.highlight}（点击展开 8 图水位）`}
            >
              <i className="hes-bar-dot" />
              <span className="hes-bar-mkt">美股</span>
              <b>{usJointSummary.verdict}</b>
              {usJointSummary.chips.slice(0, 2).map((chip) => (
                <span key={chip.label} className="hes-bar-kv">
                  {chip.label} {chip.value}
                </span>
              ))}
            </button>
            <div className="hes-bar-actions">
              <button
                type="button"
                className="btn small"
                aria-expanded={false}
                onClick={toggleExpanded}
              >
                展开 8 图水位 ▾
              </button>
              <Link className="hes-link" to="/fundamentals">
                宏观全景 →
              </Link>
            </div>
          </div>
        ) : (
          <>
            <header className="hes-head">
              <div className="hes-head-left">
                <h2>{isFullMode ? "中美核心水位全景" : "大环境水位"}</h2>
                <span
                  className="hes-help-icon"
                  tabIndex={0}
                  title="价格趋势定买卖方向，四维环境（估值 · 宽度 · 杠杆 · 波动）仅在极端区间提醒仓位轻重；点任意卡片右上角「大图 ↗」可叠加指数查看历史。"
                >
                  ?
                </span>
              </div>
              <div className="hes-actions">
                <button
                  type="button"
                  className="btn small"
                  disabled={fetching}
                  onClick={refreshAllEnv}
                >
                  {fetching ? "刷新中…" : "刷新水位"}
                </button>
                <button
                  type="button"
                  className="btn small"
                  aria-expanded={moreOpen}
                  onClick={() => setMoreOpen((v) => !v)}
                >
                  {moreOpen ? "收起更多指标 ▴" : "更多指标库 ▾"}
                </button>
                {!isFullMode && (
                  <>
                    <Link className="hes-link" to="/fundamentals">
                      宏观全景 →
                    </Link>
                    <button
                      type="button"
                      className="btn small"
                      aria-expanded={true}
                      onClick={toggleExpanded}
                    >
                      收起 ▴
                    </button>
                  </>
                )}
              </div>
            </header>

            {/* 中美四维交叉判读条（左对A股4卡，右对美股4卡） */}
            <div className="hes-combo-row" aria-label="中美多指标交叉判读">
              {renderJointBanner("A股交叉判读", cnJointSummary)}
              {renderJointBanner("美股交叉判读", usJointSummary)}
            </div>

            <div className="hes-grid">
              {/* 上排：估值赔率 + 参与宽度（左2 A股，右2 美股） */}
              {renderCnErpCard()}
              {renderBreadthCard("breadth-cn", "全A · 市场宽度", "CN_ALL_A", cnBreadth)}
              {renderUsErpCard()}
              {renderBreadthCard("breadth-us", "标普500 · 市场宽度", "SP500", usBreadth)}

              {/* 下排：两融杠杆 + 信用恐慌防线（左2 A股，右2 美股；小图与大图阈值100%同源对齐） */}
              {renderCnMarginBuyCard()}
              {renderCnMarginBalanceCard()}
              {renderUsHyOasCard()}
              {renderUsVixCard()}
            </div>
          </>
        )}
      </section>

      {isExpanded && moreOpen && (
        <div className="hes-more-drawer">
          <MarketObservationAlerts />
        </div>
      )}

      {coreDetail && (
        <CoreDetailModal
          id={coreDetail.id}
          initialRuleId={coreDetail.initialRuleId}
          onClose={() => setCoreDetail(null)}
        />
      )}
      {activeObsEntry && (
        <ObservationDetailDialog
          item={activeObsEntry}
          financingTab={subModal?.financingTab}
          onClose={() => setSubModal(null)}
        />
      )}
    </>
  );
}
