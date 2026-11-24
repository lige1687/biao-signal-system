import { FOCUS_DISPLAY_KEY } from "../focus-momentum/recent";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { createPortal } from "react-dom";
import { ERP_REFERENCE_QUERY_KEY, ERP_REFERENCE_URL, parseErpReference } from "../observation-library/erpReferenceData";
import { bandDistance, ERP_BAND_METHOD } from "../observation-library/erpBands";
import { innerErpRails } from "../observation-library/erpComparisonDisplay";
import { breadthInput, erpInput, parseBreadth, type BreadthMarket } from "./adapters";
import { buildAlertSnapshot, eventLabel, parseSeen, type AlertSnapshot } from "./model";
import { acknowledge, SEEN_EVENT, SEEN_KEY } from "./storage";
import type { BreadthReadingPoint, BreadthReadingResponse } from "../market-style/breadthReadingTypes";
import { breadthInterpretation } from "../market-style/breadthInterpretation";
import type { AlertPoint } from "./model";
import MiniTrend from "./MiniTrend";
import ChartLegend, { CHART_COLORS } from "./ChartLegend";
import { BREADTH_LINES } from "../trend/zones";
import BreadthInstitutionalReference from "../market-style/BreadthInstitutionalReference";
import { BREADTH_EXTERNAL_REFERENCES } from "../market-style/breadthInstitutionalReferences";
import "./style.css";
import UsErpCard from "./UsErpCard";
import { usErpBands } from "../observation-library/usErpBands";
import CrossMarketObservation from "../market-style/CrossMarketObservation";
import BreadthComparison from "../market-style/BreadthComparison";
import { MetricProjection } from "../observation-library/projectionView";
import ExtraCandidateCard from "./ExtraCandidateCard";
import { useOverviewSelection } from "./useSelection";
import { interpretMarketContext, type ContextSignal } from "../market-context/interpretMarketContext";
import { fundamentalsApi } from "../../api/client";
import { priorVolatilityPercentile, volatilityHistory, seriesPoints } from "../market-style/marketRiskMetrics";
import { useProjectionSource } from "../observation-library/projectionSources";
import { marketConnections } from "./conditionalReading";
import CombinationReading from "./CombinationReading";
import { priorReferenceBands } from "./referenceBands";
import { recentDelta, historicalPosition } from "../market-style/indicatorReading";
import { IndustryStructureSection } from "./IndustryStructure";
import IncrementObservationCards from "./IncrementObservationCards";
import RelativeObservationCards from "./RelativeObservationCards";
import type { CandidateSummary } from "./CandidateShelf";
import IndicatorBrowser from "./IndicatorBrowser";
import IndicatorThumbnail from "./IndicatorThumbnail";
import { INDICATOR_BY_ID, MICRO_INDICATORS } from "./indicatorCatalog";
import MicrostructureObservations from "./MicrostructureObservations";
import IndustryTurnoverObservationCard from "./IndustryTurnoverObservationCard";
import { INDUSTRY_TURNOVER_ID } from "./industryTurnoverOptions";
import ObservationMetric from "../observation-library/ObservationMetric";
import EtfPriceHeatObservation from "./EtfPriceHeatObservation";
import { INDICATOR_META_CONFIG, ObservationPanel, ObservationPanelCard, ObservationPanelThumbnail, PANEL_QUERY_KEY } from "../market-observation-panel";
import CompactOverview from "./CompactOverview";
import SectorStructureCard from "./SectorStructureCard";
import EarningsRevisionSampleCard from "./EarningsRevisionSampleCard";
import StarBreadthSnapshot from "../market-style/StarBreadthSnapshot";
import StarWeightedBreadthSnapshot from "../market-style/StarWeightedBreadthSnapshot";

const panelId = (id: string) => id === "turnover-concentration" ? "cn-daily-amount-top5" : id;
const inPanel = (id: string) => Object.prototype.hasOwnProperty.call(INDICATOR_META_CONFIG, panelId(id));

async function getJson(url: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`资料读取失败 (${response.status})`);
  return response.json();
}

function useBreadth(market: BreadthMarket) {
  return useQuery({ queryKey: ["homeObservationBreadth", market, 90],
    queryFn: async ({ signal }) => parseBreadth(await getJson(
      `/api/market-context/breadth-history?market_id=${market}&lookback_days=90&include_observation=true`, signal), market),
    staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
}

function readSeen() {
  try { return { seen: parseSeen(localStorage.getItem(SEEN_KEY)), failed: false }; }
  catch { return { seen: {}, failed: true }; }
}

const today = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai" }).format(new Date());
const format = (n: number | null | undefined) => n == null || !Number.isFinite(n) ? "—" : n.toFixed(2);

function AlertRow({ snapshot: s, pending, onRead, onOpen, onCollapse, participation, breadth, points, erpSource }: {
  snapshot: AlertSnapshot; pending: boolean; onRead: () => void; onOpen: () => void; onCollapse: () => void;
  participation?: BreadthReadingPoint | null; breadth?: BreadthReadingResponse; points: AlertPoint[];
  erpSource?: { name: string; url: string };
}) {
  const [reference, setReference] = useState<"dynamic50" | "stockcharts50">("dynamic50");
  const fresh = s.quality === "ready";
  const reading = fresh && participation?.date === s.latest?.date ? participation : null;
  const interpretation = breadthInterpretation(reading);
  const isErp = s.kind === "erp";
  const quality = pending && !s.latest ? "读取中" : s.quality === "historical" ? "历史观察"
    : s.quality === "stale" ? "待更新" : s.quality === "error" ? "读取失败" : s.quality === "missing" ? "资料不足" : "";
  const erpKnown = !!s.latest && s.quality !== "error" && s.quality !== "missing";
  const headline = isErp ? !erpKnown ? "估值位置暂不判断" : s.latest?.phase === "high" ? "高于2σ上轨 · 相对便宜"
    : s.latest?.phase === "low" ? "低于2σ下轨 · 相对偏贵" : s.latest?.phase === "unknown" ? "参考历史不足" : "位于2σ参考区间内" : interpretation.headline;
  const tone = isErp ? !erpKnown ? "unknown" : s.latest?.phase === "high" ? "supportive" : s.latest?.phase === "low" ? "caution" : "neutral" : interpretation.tone;
  const rows = (breadth?.history ?? []).slice(-90);
  const erpRows = points.slice(-260);
  const erpInnerRows = erpRows.map(innerErpRails);
  const erpInnerLatest = s.latest ? innerErpRails(s.latest) : { lower: null, upper: null };
  const erpNearest = erpKnown && s.latest?.value != null && erpInnerLatest.lower != null && erpInnerLatest.upper != null
    ? bandDistance({ ...erpInnerLatest, value: s.latest.value },
      Math.abs(s.latest.value - erpInnerLatest.lower) <= Math.abs(s.latest.value - erpInnerLatest.upper) ? "lower" : "upper") : null;
  const latest = rows[rows.length - 1];
  const change = isErp ? recentDelta(points, 4) : recentDelta(rows.map(p => ({ date: p.date, value: p.breadth_50 })), 20);
  const boundsByDate = new Map((breadth?.observation?.history ?? []).map(p => [p.date, p.horizons["50"]]));
  const fixed = BREADTH_EXTERNAL_REFERENCES.stockcharts;
  const low = rows.map(p => reference === "stockcharts50"
    ? p.breadth_50 == null ? null : fixed.sma50.lower
    : boundsByDate.get(p.date)?.status === "ready" ? boundsByDate.get(p.date)!.lower : null);
  const high = rows.map(p => reference === "stockcharts50"
    ? p.breadth_50 == null ? null : fixed.sma50.upper
    : boundsByDate.get(p.date)?.status === "ready" ? boundsByDate.get(p.date)!.upper : null);
  const lineOrder = ["50", "20", "200"] as const;
  const referenceDescription = reference === "dynamic50" ? "50日历史参考区间，高低边界随历史变化"
    : "StockCharts 50日固定参考，低于30%、高于70%";
  // Display-only position follows the chosen reference; alert state remains unchanged.
  const displayPhase = reference === "dynamic50" ? s.latest?.phase
    : reference === "stockcharts50" && latest?.breadth_50 != null
      ? latest.breadth_50 < fixed.sma50.lower ? "low" : latest.breadth_50 > fixed.sma50.upper ? "high" : "middle"
      : undefined;
  const periods = ["20", "50", "200"] as const;
  const colors = { "20": BREADTH_LINES[0].color, "50": BREADTH_LINES[1].color, "200": BREADTH_LINES[2].color };
  return <article className={`moa-item moa-${s.quality}`} data-tone={tone} aria-label={s.label} data-overview-card={isErp ? "erp-cn" : s.id.startsWith("SP500:") ? "breadth-us" : "breadth-cn"}>
    <div className="moa-item-head"><h3>{isErp ? s.label : s.label.replace(" · 50日宽度", " · 市场宽度")}</h3>
      <div className="moa-item-actions">{quality && <span className="moa-quality" title={s.qualityLabel}>{quality}</span>}<button type="button" onClick={onCollapse}>收起</button></div></div>
    <h4 className="moa-conclusion">{headline}</h4>
    {isErp ? <>
      <div className="moa-erp-value"><strong>{erpKnown ? format(s.latest?.value) : "—"}</strong><span>个百分点</span><time dateTime={s.latest?.date}>{s.latest?.date ?? "日期待补"}</time></div>
      <ChartLegend items={[
        { label: "股债利差", color: CHART_COLORS.primary },
        { label: "上轨 · 相对便宜", color: CHART_COLORS.low, dashed: true },
        { label: "下轨 · 相对偏贵", color: CHART_COLORS.high, dashed: true },
      ]} />
      <div className="moa-erp-rails" aria-label="股债两档参考阈值">
        <span>内侧 1.5σ</span><span>下轨 <b>{format(erpInnerLatest.lower)}</b></span><span>上轨 <b>{format(erpInnerLatest.upper)}</b></span>
        <span>外侧 2σ</span><span>下轨 <b>{format(s.latest?.lower)}</b></span><span>上轨 <b>{format(s.latest?.upper)}</b></span>
      </div>
      <p className="moa-reference-caption">滚动3年 · 周频观测，含当期 · 单位：百分点</p>
      <MiniTrend dates={erpRows.map(p => p.date)} lines={[{ name: "股债利差", color: CHART_COLORS.primary, values: erpRows.map(p => p.value) }]}
        lower={erpRows.map(p => p.lower)} upper={erpRows.map(p => p.upper)} references={[
          { name: "1.5σ上轨 · 较早观察", color: "#82a69f", values: erpInnerRows.map(p => p.upper) },
          { name: "1.5σ下轨 · 较早观察", color: "#b49d81", values: erpInnerRows.map(p => p.lower) },
        ]} label="沪深300股债利差近五年趋势，三年均值的内侧1.5倍、外侧2倍标准差上下轨；青绿上轨看相对便宜，棕色下轨看相对偏贵" />
    </> : <>
      <div className="moa-horizons">{periods.map(period => <div key={period}><span><i style={{ background: colors[period] }} />{period}日</span><strong>{latest?.[`breadth_${period}`] == null ? "—" : `${latest[`breadth_${period}`]!.toFixed(1)}%`}</strong></div>)}</div>
      <div className="moa-reference-picker" role="group" aria-label="小图参考阈值">
        <button type="button" aria-pressed={reference === "dynamic50"} onClick={() => setReference("dynamic50")}><span>动态50日</span><strong>{format(s.latest?.lower)}% / {format(s.latest?.upper)}%</strong></button>
        <button type="button" aria-pressed={reference === "stockcharts50"} onClick={() => setReference("stockcharts50")}><span>StockCharts 50日</span><strong>&lt;{fixed.sma50.lower}% / &gt;{fixed.sma50.upper}%</strong></button>
      </div>
      <div className="moa-reference-caption" aria-live="polite">{reference === "dynamic50" ? "50日历史参考区间" : "StockCharts 50日固定参考"} · 加粗蓝线看50日参与面</div>
      <MiniTrend dates={rows.map(p => p.date)} percent lower={low} upper={high} lines={lineOrder.map(period => ({ name: `${period}日`, color: colors[period], values: rows.map(p => p[`breadth_${period}`] ?? null) }))}
        label={`${s.label.replace("50日宽度", "市场宽度")}近90条记录，蓝色50日、橙色20日、紫色200日；${referenceDescription}。50日曲线加粗，用于观察参与面的位置与变化`} />
      <div className="moa-threshold-meaning"><span>低位回升看参与修复</span><span>高位转弱看支撑收缩</span></div>
    </>}
    {change && <p className="moa-card-change">较{change.previous.date} <b>{change.difference > 0 ? "+" : ""}{format(change.difference)} 个百分点</b></p>}
    <p className="moa-use">{isErp ? erpNearest ? `1.5σ内轨：${erpNearest}` : "参考轨道待补齐" : reading && displayPhase === "low" ? `已在低位观察区。${interpretation.watch}` : reading && displayPhase === "high" ? `已在高位观察区。${interpretation.watch}` : interpretation.meaning}</p>
    {!isErp && <BreadthInstitutionalReference market={s.id.startsWith("SP500:") ? "us" : "cn"} showValues={false} />}
    <footer><button type="button" onClick={() => { onRead(); onOpen(); }}>看大图 <span aria-hidden="true">↗</span></button>
      <details className="moa-history"><summary>依据与变化{s.newEvents.length > 0 ? ` · ${s.newEvents.length}项新变化` : ""}</summary>
        <div><p>读数日期 {s.latest?.date ?? "未知"}。</p>
          {isErp ? <><p>两档轨道均按过去3个自然年的均值和标准差计算，含当期、不含窗口起日。1.5σ较早触及，2σ更极端；标题和新变化提醒按2σ。图示年限不改变计算窗口。</p>
            {erpSource && <p>数据：<a href={erpSource.url} target="_blank" rel="noreferrer">{erpSource.name}</a>。</p>}
            <p>2σ参照<a href={ERP_BAND_METHOD.url} target="_blank" rel="noreferrer">国信证券三年轨道方法</a>，1.5σ为本地观察参考。上轨历史事件较少，下轨未可靠提示顶部。<Link to="/library?report=docs%2Fexperiments%2Ferp-band-sensitivity-2026-11-02.md">查看检验</Link></p></>
            : <><p>{reading?.state.summary ?? "资料尚未齐备，当前参与变化未知。"}</p><p>50%表示半数股票站上均线。低位 {format(s.latest?.lower)}%、高位 {format(s.latest?.upper)}% 用于比较参与面的历史位置，再结合升降方向观察支撑变化。</p></>}
          {s.lastEvent && <p>最近历史位置变化：{eventLabel(s.kind, s.lastEvent.event)} · {s.lastEvent.date}。</p>}
          {s.revised && fresh && <p>该日读数有更正，请以当前数值为准。</p>}
          {s.newEvents.length > 0 && <button onClick={onRead}>知道了</button>}
        </div>
      </details>
    </footer>
  </article>;
}

type OverviewDetailId = "erp-cn" | "erp-us" | "breadth-cn" | "breadth-us";

function OverviewDetail({ id, onClose }: { id: OverviewDetailId; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const node = dialog.current; const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    node?.showModal(); return () => { node?.close(); if (trigger?.isConnected) trigger.focus({ preventScroll: true }); }; }, []);
  return createPortal(<dialog ref={dialog} className="moa-detail-dialog" onCancel={(event) => { event.preventDefault(); onClose(); }}>
    <header><h2>{id === "erp-cn" ? "沪深300 · 股债利差" : id === "erp-us" ? "标普500 · 股债利差" : id === "breadth-cn" ? "全A · 市场宽度" : "标普500 · 市场宽度"}</h2><button type="button" onClick={onClose}>关闭 ×</button></header>
    {id === "erp-cn" || id === "erp-us" ? <MetricProjection id={id} market={id === "erp-cn" ? "cn" : "us"} /> : <BreadthComparison market={id === "breadth-cn" ? "cn" : "us"} onMarketChange={() => {}} />}
  </dialog>, document.body);
}

function ContextPanel({ snapshots, cnBreadth, usBreadth, asOf }: { snapshots: AlertSnapshot[];
  cnBreadth?: BreadthReadingResponse; usBreadth?: BreadthReadingResponse; asOf: string }) {
  const prices = useQuery({ queryKey: ["fundOverlay", 47], queryFn: () => fundamentalsApi.overlayHistory(47), staleTime: 5 * 60_000, retry: false });
  const financing = useQuery({ queryKey: ["marketStyleCnObservations"], queryFn: () => fundamentalsApi.observations("cn"), staleTime: 5 * 60_000, retry: false });
  const ratios = useQuery({ queryKey: ["fundamentalsRatesHistory", 18250], queryFn: () => fundamentalsApi.ratesHistory(18250), staleTime: 30 * 60_000, retry: false });
  const vix = useProjectionSource("vix");
  const hy = useProjectionSource("hy-oas");
  const erpUs = useProjectionSource("erp-us");
  const supplement = useQuery({ queryKey: ["crossMarketRiskSupplement", "20261102-v2"], queryFn: async () => {
    const response = await fetch("/research/cross-market-risk-context-20261102/supplement-v2.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(String(response.status));
    return response.json() as Promise<{ series?: { nfci?: { points: { date: string; value: number | null }[]; sourceName: string; unit: string } } }>;
  }, staleTime: 5 * 60_000, retry: false });
  const stateFor = (market: "cn" | "us") => {
    const reading = market === "cn" ? cnBreadth : usBreadth;
    const anchorUniverse = market === "cn" ? "CN_ALL_A" : "SP500";
    const date = asOf;
    const signals: Parameters<typeof interpretMarketContext>[0]["signals"] = {};
    const sourcePoint = reading?.history ?? [];
    const breadthChange = recentDelta(sourcePoint.map(p => ({ date: p.date, value: p.breadth_50 })), 20);
    const lastBreadth = sourcePoint[sourcePoint.length - 1];
    const earlierBreadth = sourcePoint[sourcePoint.length - 2];
    const currentBreadth = lastBreadth?.breadth_50;
    if (lastBreadth && currentBreadth != null) signals.breadth50 = { value: currentBreadth,
      previous: earlierBreadth?.breadth_50 ?? null,
      percentile: reading?.observation?.latest?.horizons["50"]?.percentile ?? null,
      asOf: lastBreadth.date, source: market === "cn" ? "现有全A宽度历史" : "现有标普500样本宽度历史",
      universe: anchorUniverse, scope: "same_pool", unit: "%", frequency: "daily", quality: "provisional",
      note: "逐日成员与首次可知时间未核" };
    const erp = market === "cn" ? snapshots[0].quality === "error" || snapshots[0].quality === "missing" ? null : snapshots[0].latest
      : erpUs.error ? null : erpUs.points[erpUs.points.length - 1];
    if (erp?.value != null) signals.erp = { value: erp.value, asOf: erp.date,
      source: market === "cn" ? "沪深300股债利差三年轨道" : erpUs.sourceName,
      universe: market === "cn" ? "CSI300" : "SP500", scope: "same_pool", unit: "百分点",
      frequency: market === "cn" ? "weekly" : "daily", quality: "provisional",
      note: market === "cn" ? "与全A不同股票池；周频历史参考" : "盈利端月频，日值不是每日新增盈利" };
    const priceSeries = prices.isError ? undefined : prices.data?.series[market === "cn" ? "sse" : "sp500"];
    const volatility = volatilityHistory(priceSeries?.dates ?? [], priceSeries?.values ?? []);
    const current = volatility[volatility.length - 1];
    const previous = volatility[volatility.length - 6];
    const priceUniverse = market === "cn" ? "SHCOMP" : "SP500";
    if (current?.hv20 != null) {
      const base: ContextSignal = { value: current.hv20, previous: previous?.hv20 ?? null,
        asOf: current.date, source: market === "cn" ? "上证指数收盘价" : "标普500收盘价", universe: priceUniverse,
        scope: "same_pool", unit: "%", comparison: "较前5条记录", frequency: "daily", quality: "provisional" };
      signals.hv20 = base;
      const percentile = priorVolatilityPercentile(volatility, volatility.length - 1);
      if (percentile !== null) signals.hv20Percentile = { ...base, value: percentile,
        previous: previous ? priorVolatilityPercentile(volatility, volatility.length - 6) : null, unit: "分位%" };
      if (current.ratio !== null) signals.hv20Hv60Ratio = { ...base, value: current.ratio,
        previous: previous?.ratio ?? null, unit: "倍" };
    }
    if (market === "cn") {
      const balance = financing.isError ? undefined : financing.data?.items.find((item) => item.metric_id === "margin_balance");
      if (balance?.change != null && balance.observation_date) signals.financingBalanceChange20d = {
        value: balance.change, asOf: balance.observation_date, source: balance.source_name,
        universe: "CN_MARGIN_ELIGIBLE", scope: "same_pool", unit: "亿元", comparison: "较前20个有效观测日",
        frequency: "daily", quality: "provisional", note: "融资标的可能含基金，非全A股票池" };
    } else {
      const vixPoint = vix.points[vix.points.length - 1];
      if (vixPoint?.value != null) signals.vix = { value: vixPoint.value, asOf: vixPoint.date,
        source: vix.sourceName, universe: "SP500_OPTIONS", scope: "market_context", market: "us", unit: vix.unit,
        frequency: "daily", quality: "provisional" };
      const hyPoint = hy.points[hy.points.length - 1];
      const old = hy.points.length > 20 ? hy.points[hy.points.length - 21] : undefined;
      if (hyPoint?.value != null && old?.value != null) {
        signals.hyOasChange20d = { value: hyPoint.value - old.value,
          asOf: hyPoint.date, source: hy.sourceName, universe: "US_HY_CREDIT", scope: "market_context", market: "us",
          unit: "百分点", comparison: `较前20条观测（${old.date}）`, frequency: "daily", quality: "provisional" };
      }
      const nfci = supplement.data?.series?.nfci;
      const nfciPoint = nfci?.points[nfci.points.length - 1];
      if (nfciPoint?.value != null) signals.nfci = { value: nfciPoint.value, asOf: nfciPoint.date,
        source: nfci?.sourceName ?? "Chicago Fed", universe: "US_FINANCIAL_CONDITIONS", scope: "market_context", market: "us",
        unit: nfci?.unit ?? "指数", frequency: "weekly", quality: "provisional", note: "当前历史版本，可能修订" };
    }
    const erpBands = market === "cn" ? { low: snapshots[0].latest?.lower, high: snapshots[0].latest?.upper }
      : (() => { const rows = usErpBands(erpUs.points); const latest = rows[rows.length - 1]; return { low: latest?.lower, high: latest?.upper }; })();
    const marginRatio = ratios.isError ? [] : seriesPoints(ratios.data?.series.margin_rzyezb);
    const ratioDelta = recentDelta(marginRatio, 20);
    const ratioPosition = historicalPosition(marginRatio);
    const balance = financing.isError ? undefined : financing.data?.items.find(item => item.metric_id === "margin_balance");
    const balanceChangePct = balance?.value != null && balance.change != null && balance.value - balance.change > 0
      ? balance.change / (balance.value - balance.change) * 100 : null;
    const combined = marketConnections({ market, breadth50: signals.breadth50?.value,
      breadthLow: reading?.observation?.latest?.horizons["50"]?.lower,
      breadthChange20: breadthChange?.difference, erp: signals.erp?.value, erpLow: erpBands.low, erpHigh: erpBands.high,
      hvRatio: signals.hv20Hv60Ratio?.value, hvPercentile: signals.hv20Percentile?.value,
      financingChange: market === "cn" ? signals.financingBalanceChange20d?.value : null,
      financingPercentile: market === "cn" ? ratioPosition : null,
      financingRatioChange: market === "cn" ? ratioDelta?.difference : null,
      hyChange20: market === "us" ? signals.hyOasChange20d?.value : null,
      breadthDate: signals.breadth50?.asOf, breadthPreviousDate: breadthChange?.previous.date,
      erpDate: signals.erp?.asOf, hvDate: signals.hv20?.asOf, hv20: signals.hv20?.value,
      financingRatio: ratioDelta?.current.value, financingBalanceChangePct: balanceChangePct,
      financingDate: ratioDelta?.current.date, financingPreviousDate: ratioDelta?.previous.date,
      financingBalanceDate: signals.financingBalanceChange20d?.asOf,
      hyDate: signals.hyOasChange20d?.asOf, hyPreviousDate: hy.points.length > 20 ? hy.points[hy.points.length - 21].date : undefined,
      vix: signals.vix?.value, vixDate: signals.vix?.asOf, vixHigh: priorReferenceBands(vix.points).latest.high });
    return { result: interpretMarketContext({ market, asOf: date, anchorUniverse, signals }), signals, combined,
      breadthChange, erpBands, ratioDelta, ratioPosition, balanceChangePct };

  };
  const results = (["cn", "us"] as const).map((market) => ({ market, ...stateFor(market) }));
  return <section className="moa-context" aria-label="组合观察解读">
    <h3>组合观察</h3>
    <div className="moa-context-markets">{results.map(({ market, combined }) =>
      <CombinationReading key={market} market={market} reading={combined} />)}</div>
  </section>;
}

export default function MarketObservationAlerts({ placement = "home" }: { placement?: "home" | "market" }) {
  const queryClient = useQueryClient();
  const titleId = useId();
  const [stored, setStored] = useState(readSeen);
  const [nowDate, setNowDate] = useState(today);
  const { selectedIds, warning: selectionWarning, setPinned, resetCore } = useOverviewSelection();
  const [view, setView] = useState<"overview" | "panel" | "home" | "categories">("home");
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [contextOpen, setContextOpen] = useState(false);
  const [structureOpen, setStructureOpen] = useState(false);
  const [notice, setNotice] = useState<{ text: string; removedId?: string } | null>(null);
  const homeButton = useRef<HTMLButtonElement>(null);
  const [liveSummaries, setLiveSummaries] = useState<Record<string, CandidateSummary>>({});
  const updateSummary = useCallback((id: string, summary: CandidateSummary) => setLiveSummaries((current) => {
    const old = current[id];
    return old?.value === summary.value && old.meaning === summary.meaning && old.date === summary.date ? current : { ...current, [id]: summary };
  }), []);
  const [detailId, setDetailId] = useState<OverviewDetailId | null>(null);
  const cn = useBreadth("CN_ALL_A");
  const us = useBreadth("SP500");
  const erp = useQuery({ queryKey: ERP_REFERENCE_QUERY_KEY,
    queryFn: async ({ signal }) => parseErpReference(await getJson(ERP_REFERENCE_URL, signal)),
    staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  const inputs = useMemo(() => [erpInput(erp.data, erp.isError), breadthInput("CN_ALL_A", cn.data, cn.isError),
    breadthInput("SP500", us.data, us.isError)], [erp.data, erp.isError, cn.data, cn.isError, us.data, us.isError]);
  const snapshots = inputs.map(input => buildAlertSnapshot(input, nowDate, stored.seen[input.id]));
  const newCount = snapshots.reduce((n, s) => n + s.newEvents.length, 0);
  const monitored = snapshots.filter((_, i) => !inputs[i].historicalOnly);
  const readyCount = monitored.filter(s => s.quality === "ready").length;
  const panelFetching = useIsFetching({ queryKey: PANEL_QUERY_KEY }) > 0;
  const fetching = view === "panel" ? panelFetching : erp.isFetching || cn.isFetching || us.isFetching;
  const sources = [erp, cn, us];
  const participation = [null, cn.data?.observation?.latest, us.data?.observation?.latest];
  const summaries: Record<string, CandidateSummary> = { ...liveSummaries };
  snapshots.forEach((snapshot, index) => {
    const id = ["erp-cn", "breadth-cn", "breadth-us"][index];
    const history = (index === 1 ? cn.data : us.data)?.history ?? [];
    const breadthValue = history[history.length - 1]?.breadth_50;
    const value = snapshot.quality === "error" ? "读取失败" : !snapshot.latest ? sources[index].isPending ? "读取中" : "读数待补"
      : index === 0 ? `${format(snapshot.latest.value)} 个百分点${snapshot.quality === "stale" || snapshot.quality === "historical" ? " · 历史" : ""}`
        : `${format(breadthValue)}%站上50日均线${snapshot.quality === "stale" || snapshot.quality === "historical" ? " · 历史" : ""}`;
    summaries[id] = { value, meaning: index === 0 ? "股债收益差显示估值缓冲" : "看上涨参与面是否扩大", date: snapshot.latest?.date };
  });
  const changePinned = (id: string, pinned: boolean) => {
    setPinned(id, pinned);
    setNotice({ text: `${INDICATOR_BY_ID.get(id)?.label ?? id} · ${pinned ? "已加入首页" : "已移出首页"}`,
      removedId: pinned ? undefined : id });
  };
  const removeFromHome = (id: string) => {
    changePinned(id, false);
    homeButton.current?.focus({ preventScroll: true });
  };

  useEffect(() => {
    const sync = (event?: StorageEvent) => {
      if (event && event.key !== SEEN_KEY && event.key !== null) return;
      setStored(readSeen());
    };
    const localSync = () => sync();
    window.addEventListener("storage", sync);
    window.addEventListener(SEEN_EVENT, localSync);
    const timer = window.setInterval(() => setNowDate(today()), 60_000);
    return () => { window.removeEventListener("storage", sync); window.removeEventListener(SEEN_EVENT, localSync); window.clearInterval(timer); };
  }, []);

  const markRead = (items: AlertSnapshot[]) => {
    if (!items.some(s => s.quality === "ready")) return;
    try {
      localStorage.setItem(SEEN_KEY, acknowledge(localStorage.getItem(SEEN_KEY), items));
      setStored(readSeen());
      window.dispatchEvent(new Event(SEEN_EVENT));
    } catch { setStored(previous => ({ ...previous, failed: true })); }
  };
  const renderCard = (id: string, onDismiss: () => void) => {
    if (id === "sector-breadth") return <SectorStructureCard mode="breadth" onCollapse={onDismiss} />;
    if (id === "sector-margin-share") return <SectorStructureCard mode="margin" onCollapse={onDismiss} />;
    if (id === "earnings-revision-samples") return <EarningsRevisionSampleCard onCollapse={onDismiss} />;
    if (id === "star-breadth") return <StarBreadthSnapshot variant="card" onCollapse={onDismiss} />;
    if (id === "star-weighted-breadth") return <StarWeightedBreadthSnapshot variant="card" onCollapse={onDismiss} />;
    if (inPanel(id)) return <ObservationPanelCard id={panelId(id)} onCollapse={onDismiss} />;
    if (id === "etf-price-heat") return <EtfPriceHeatObservation onCollapse={onDismiss} />;
    const index = ["erp-cn", "breadth-cn", "breadth-us"].indexOf(id);
    if (index >= 0) return <AlertRow snapshot={snapshots[index]} pending={sources[index].isPending}
      participation={participation[index]} breadth={index === 1 ? cn.data : index === 2 ? us.data : undefined}
      points={inputs[index].points} onRead={() => markRead([snapshots[index]])}
      erpSource={index === 0 && erp.data ? { name: erp.data.sourceName, url: erp.data.sourceUrl } : undefined}
      onOpen={() => setDetailId(id as "erp-cn" | "breadth-cn" | "breadth-us")} onCollapse={onDismiss} />;
    if (id === INDUSTRY_TURNOVER_ID) return <IndustryTurnoverObservationCard onCollapse={onDismiss} />;
    if (id === "erp-us") return <UsErpCard collapsed={false} onCollapse={onDismiss} onSummary={summary => updateSummary(id, summary)} />;
    const market = INDICATOR_BY_ID.get(id)?.market === "us" ? "us" : "cn";
    if (["cn-style-relative", "us-semiconductor-relative", "us-equal-weight-relative"].includes(id))
      return <RelativeObservationCards market={market} selectedIds={[id]} collapsedIds={[]} onCollapse={onDismiss} onSummary={updateSummary} />;
    if (["cn-session", "cn-institution"].includes(id))
      return <IncrementObservationCards selectedIds={[id]} collapsedIds={[]} onCollapse={onDismiss} onSummary={updateSummary} />;
    if (["dr007", "earnings-revisions"].includes(id))
      return <CrossMarketObservation market={market} selectedIds={[id]} collapsedIds={[]} onCollapse={onDismiss} onSummary={updateSummary} />;
    if (id === "smallcap-turnover") return <article className="moa-item" data-overview-card={id} aria-label={INDICATOR_BY_ID.get(id)?.label}>
      <div className="moa-item-head"><h3>{INDICATOR_BY_ID.get(id)?.label}</h3><button onClick={onDismiss}>收起</button></div>
      <p>{INDICATOR_BY_ID.get(id)?.meaning}</p><ObservationMetric id={id} />
      <p className="moa-card-limit">{INDICATOR_BY_ID.get(id)?.limitation}</p></article>;
    if (id === "industry-structure-cn") return <div className="moa-standalone moa-wide-card" data-overview-card={id}>
      <button className="moa-remove" onClick={onDismiss}>收起</button><IndustryStructureSection /></div>;
    if (MICRO_INDICATORS.some(item => item.id === id)) return <div className="moa-standalone" data-overview-card={id}>
      <button className="moa-remove" onClick={onDismiss}>收起</button><MicrostructureObservations market={market} selectedIds={[id]} /></div>;
    return <ExtraCandidateCard id={id} collapsed={false} onCollapse={onDismiss} onSummary={summary => updateSummary(id, summary)} />;
  };
  return <section id="market-overview" className={`market-observation-alerts moa-placement-${placement}`} aria-labelledby={titleId}>
    <header className="moa-header"><div><h2 id={titleId}>市场速览</h2>
      <span aria-live="polite">{view === "overview" ? "中美估值与市场参与" : view === "panel" ? "波动、筹码、融资与情绪" : newCount ? `${newCount}条新变化` : readyCount === 0 ? "当前提醒待资料更新"
        : readyCount < monitored.length ? `${readyCount}/${monitored.length}项宽度资料可用 · 其余待更新` : "宽度看市场支撑 · 股债看估值"}</span></div>
      <div className="moa-actions">{newCount > 0 && <button onClick={() => markRead(snapshots)}>全部已读</button>}
        <button disabled={fetching} onClick={() => {
          if (view === "panel") {
            void queryClient.invalidateQueries({ queryKey: PANEL_QUERY_KEY });
            return;
          }
          void Promise.all([erp.refetch(), cn.refetch(), us.refetch(), queryClient.invalidateQueries({ queryKey: ["fundamentalsRatesHistory"] }), queryClient.invalidateQueries({ queryKey: FOCUS_DISPLAY_KEY }), queryClient.invalidateQueries({ queryKey: PANEL_QUERY_KEY })]);
        }}>{fetching ? "读取中…" : "刷新读数"}</button></div>
    </header>
    {stored.failed && <p className="moa-storage-error" role="status">浏览器未能保存已读状态，刷新后可能再次显示提醒。</p>}
    {selectionWarning && <p className="moa-storage-error" role="status">{selectionWarning}</p>}
    <div className="moa-viewbar">
      <div role="group" aria-label="市场速览视图">
        <button ref={homeButton} aria-pressed={view === "home"} onClick={() => { setView("home"); setPreviewId(null); }}>首页常看 · {selectedIds.length}</button>
        <button aria-pressed={view === "overview"} onClick={() => { setView("overview"); setPreviewId(null); }}>中美总览</button>
        <button aria-pressed={view === "panel"} onClick={() => { setView("panel"); setPreviewId(null); }}>三层市场观察</button>
        <button aria-pressed={view === "categories"} onClick={() => setView("categories")}>指标分类</button>
      </div>
      {view === "home" && <button onClick={() => { resetCore(); setView("home"); setPreviewId(null); setNotice({ text: "已恢复中美股债利差和市场宽度四项。" }); }}>恢复核心四项</button>}
    </div>
    {notice && <div className="moa-selection-notice"><span role="status">{notice.text}</span>
      {notice.removedId && <button onClick={() => { setPinned(notice.removedId!, true); setNotice(null); }}>撤销移除</button>}
      {view === "categories" && <button onClick={() => { setView("home"); setPreviewId(null); }}>查看首页</button>}
      <button aria-label="关闭提示" onClick={() => setNotice(null)}>×</button></div>}
    {view === "overview" ? <>
      <CompactOverview onOpen={id => {
        if (id === "erp-cn" || id === "erp-us" || id === "breadth-cn" || id === "breadth-us") setDetailId(id);
        else { setPreviewId(id); setView("categories"); }
      }} />
      <details className="moa-context-disclosure" open={structureOpen} onToggle={event => setStructureOpen(event.currentTarget.open)}>
        <summary>价格、宽度、集中度与融资 · 联合观察</summary>
        {structureOpen && <div className="compact-structure-reading">
          <p>先看所选指数的价格走势和全A宽度；成交集中度、融资按各自日期分别观察。只有观察日期与比较区间对齐后，才比较变化方向；股票池仍可能不同。</p>
          <div className="compact-structure-cards"><ObservationPanelCard id="cn-daily-amount-top5" /><ObservationPanelCard id="cn-financing" /></div>
          <p>成交集中不等于见顶；融资买入占比和融资余额分别反映交易占比与债务存量，也不是资金净流入。</p>
        </div>}
      </details>
      <details className="moa-context-disclosure" open={contextOpen} onToggle={event => setContextOpen(event.currentTarget.open)}>
        <summary>组合观察 · 一起看估值、参与和风险</summary>
        {contextOpen && <ContextPanel snapshots={snapshots} cnBreadth={cn.isError ? undefined : cn.data} usBreadth={us.isError ? undefined : us.data} asOf={nowDate} />}
      </details>
    </> : view === "panel" ? <ObservationPanel /> : view === "home" ? <>
      <p className="moa-home-guide">在「指标分类」加入或移出常看指标；选择保存在当前浏览器。</p>
      {selectedIds.length === 0 && <div className="moa-home-empty">首页还没有常看指标。<button onClick={() => setView("categories")}>去分类挑选</button></div>}
      <div className="moa-market-columns">
        {(["cn", "us", "global"] as const).map(market => {
          const ids = selectedIds.filter(id => INDICATOR_BY_ID.get(id)?.market === market);
          if (!ids.length) return null;
          const label = market === "cn" ? "A股" : market === "us" ? "美股" : "跨市场";
          return <section className={`moa-market${market === "global" ? " moa-global-market" : ""}`} key={market} aria-label={`${label}观察`}>
            <h3>{label}<small>{ids.length} 项常看</small></h3>
            <div className="moa-market-grid">{ids.map(id => <div key={id} className={`moa-card-slot${id === "industry-structure-cn" ? " moa-wide-card" : ""}`}>
              {renderCard(id, () => removeFromHome(id))}</div>)}</div>
          </section>;
        })}
      </div>
      <details className="moa-context-disclosure" open={contextOpen} onToggle={event => setContextOpen(event.currentTarget.open)}>
        <summary>组合观察 · 一起看估值、参与和风险</summary>
        {contextOpen && <ContextPanel snapshots={snapshots} cnBreadth={cn.isError ? undefined : cn.data} usBreadth={us.isError ? undefined : us.data} asOf={nowDate} />}
      </details>
    </> : <IndicatorBrowser selectedIds={selectedIds} summaries={summaries} onSetPinned={changePinned}
      renderThumbnail={id => inPanel(id) ? <ObservationPanelThumbnail id={panelId(id)} /> : <IndicatorThumbnail id={id} />}
      previewId={previewId} onPreview={setPreviewId} onClosePreview={() => setPreviewId(null)}
      preview={previewId ? <div className="moa-preview-card">{renderCard(previewId, () => setPreviewId(null))}</div> : null} />}
    {detailId && <OverviewDetail id={detailId} onClose={() => setDetailId(null)} />}
    <details className="moa-rules"><summary>这些信息怎样用</summary><div>
      <p>穿出上下界、重新回到界内时提示；持续在界外不重复报新变化。这里常驻显示读数，已读仅清除新变化标记。</p>
      <p>股债轨道：<a href={ERP_BAND_METHOD.url} target="_blank" rel="noreferrer">国信证券方法</a>计算的历史参考区间。
        <Link to="/library?report=docs%2Fexperiments%2Fequity-bond-bands-effect-2026-11-01.md">查看效果检验</Link>：上轨出现过反弹线索；下轨的顶部提示表现不稳定，目前用于观察相对偏贵。</p>
      <p>宽度：站上20、50、200日均线的股票占比，用来观察短、中、长期参与方向。高低区间用来比较历史位置；低位回升看参与修复，高位转弱看支撑收缩，再与估值、波动和融资一起观察。</p>
      <p>资料过旧或无法读取时，会标明待更新并暂停新提醒。</p>
    </div></details>
  </section>;
}
