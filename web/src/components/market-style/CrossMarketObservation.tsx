import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi } from "../../api/client";
import type { BreadthHistoryPoint, MarketObservation } from "../../types";
import { MetricProjection } from "../observation-library/projectionView";
import { useProjectionSource } from "../observation-library/projectionSources";
import BreadthComparison from "./BreadthComparison";
import MarketTrendChart from "./MarketTrendChart";
import HyOasCard from "./HyOasCard";
import MiniTrend from "../market-observation-alerts/MiniTrend";
import UsErpCard from "../market-observation-alerts/UsErpCard";
import ChartLegend, { CHART_COLORS } from "../market-observation-alerts/ChartLegend";
import { priorReferenceBands } from "../market-observation-alerts/referenceBands";
import type { CandidateSummary } from "../market-observation-alerts/CandidateShelf";
import { historicalPosition, recentDelta } from "./indicatorReading";
import { priorVolatilityPercentile, seriesPoints, volatilityHistory, type Point } from "./marketRiskMetrics";
import "./cross-market-observation.css";

type Market = "cn" | "us";
type Topic = "breadth" | "erp" | "volatility" | "heat" | "funding" | "earnings";
type Supplement = { asOf: string; series?: Record<string, { points: Point[]; unit: string; sourceName: string; sourceUrl?: string; note?: string; snapshotTime?: string }>; gaps?: { id: string; reason: string }[];
  provenance?: { policyAnnouncement?: { url?: string } } };
type Card = { topic: Topic; title: string; value: string; date: string; frequency: string; points: Point[];
  reading: string; source: string; sourceUrl?: string; policyUrl?: string; note: string; state?: string; reference?: string; unit?: string;
  displayReading?: string; displayLimit?: string; hv60Reference?: { low: number; high: number } | null;
  comparison?: Point[]; secondary?: { label: string; points: Point[]; value: string; date: string; source: string; sourceUrl?: string; state?: string; unit?: string } };
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const formatted = (value: number | null | undefined, digits = 2) => finite(value) ? value.toFixed(digits) : "未知";
const last = <T,>(points: T[]) => points[points.length - 1];
const STATICS = "/research/cross-market-risk-context-20261102/supplement-v2.json";
const HV_EXPLAINER = "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/historical-volatility";
const FED_ERP_EXPLAINER = "https://www.federalreserve.gov/publications/may-2021-asset-valuations.htm";
const CBOE_VIX_EXPLAINER = "https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ";
const NFCI_EXPLAINER = "https://www.chicagofed.org/research/data/nfci/about";

function DetailTrend({ points, comparison, label, unit }: { points: Point[]; comparison?: Point[]; label: string; unit: string }) {
  if (points.filter((point) => finite(point.value)).length < 2) return <p className="cmo-empty">当前仅有快照或历史不足，无法画历史曲线。</p>;
  const dates = points.map((point) => point.date);
  const compareMap = new Map(comparison?.map((point) => [point.date, point.value]) ?? []);
  return <MarketTrendChart dates={dates} unit={unit} height={330} series={[
    { name: label, values: points.map((point) => point.value), color: CHART_COLORS.primary },
    ...(comparison ? [{ name: "HV60", values: dates.map((date) => compareMap.get(date) ?? null), color: CHART_COLORS.secondary }] : []),
  ]} />;
}

function MarketColumn({ market, selectedIds, collapsedIds, onCollapse, onSummary, onDetail }: {
  market: Market; selectedIds: readonly string[]; collapsedIds: readonly string[];
  onCollapse: (id: string) => void; onSummary: (id: string, summary: CandidateSummary) => void;
  onDetail: (market: Market, card: Card) => void;
}) {
  const breadthId = market === "cn" ? "CN_ALL_A" : "SP500";
  const breadth = useQuery({ queryKey: ["overlayBreadthReading", breadthId, 12600],
    queryFn: async ({ signal }) => { const response = await fetch(`/api/market-context/breadth-history?market_id=${breadthId}&lookback_days=12600&include_observation=true`, { signal });
      if (!response.ok) throw new Error(String(response.status)); return response.json() as Promise<{ history: BreadthHistoryPoint[]; observation?: { latest?: { horizons: Record<string, { lower: number | null; upper: number | null; status: string }> } } }>; },
    enabled: selectedIds.includes(market === "cn" ? "breadth-cn" : "breadth-us"), staleTime: 5 * 60_000, retry: false });
  const overlay = useQuery({ queryKey: ["fundOverlay", 20], queryFn: () => fundamentalsApi.overlayHistory(20),
    enabled: selectedIds.includes(market === "cn" ? "hv-cn" : "hv-us"), staleTime: 5 * 60_000, retry: false });
  const rates = useQuery({ queryKey: ["fundamentalsRatesHistory", 7300], queryFn: () => fundamentalsApi.ratesHistory(7300),
    enabled: market === "cn" && selectedIds.includes("cn-financing"), staleTime: 30 * 60_000, retry: false });
  const cnObservations = useQuery({ queryKey: ["marketStyleCnObservations"], queryFn: () => fundamentalsApi.observations("cn"),
    enabled: market === "cn" && selectedIds.includes("cn-financing"), staleTime: 5 * 60_000, retry: false });
  const supplement = useQuery({ queryKey: ["crossMarketRiskSupplement", "20261102-v2"], queryFn: async (): Promise<Supplement> => {
    const response = await fetch(STATICS, { cache: "no-cache" }); if (!response.ok) throw new Error(String(response.status));
    return response.json() as Promise<Supplement>; }, enabled: selectedIds.includes(market === "cn" ? "dr007" : "nfci"), staleTime: 5 * 60_000, retry: false });
  const erp = useProjectionSource(selectedIds.includes(market === "cn" ? "erp-cn" : "erp-us") ? market === "cn" ? "erp-cn" : "erp-us" : "unknown");
  const sentiment = useProjectionSource(market === "us" && selectedIds.includes("aaii") ? "aaii" : "unknown");
  const finance = useProjectionSource(market === "us" && selectedIds.includes("finra-margin") ? "finra-margin" : "unknown");
  const hyOas = useProjectionSource(market === "us" && selectedIds.includes("hy-oas") ? "hy-oas" : "unknown");
  const vix = useProjectionSource(market === "us" && selectedIds.includes("vix") ? "vix" : "unknown");
  const price = overlay.data?.series[market === "cn" ? "sse" : "sp500"];
  const vol = useMemo(() => volatilityHistory(price?.dates ?? [], price?.values ?? []), [price]);
  const hvPoints = vol.map((point) => ({ date: point.date, value: point.hv20 }));
  const hv60Points = vol.map((point) => ({ date: point.date, value: point.hv60 }));
  const currentVol = last(vol);
  const percentile = priorVolatilityPercentile(vol, vol.length - 1);
  const breadthHistory = breadth.data?.history ?? [];
  const breadthPoints = (horizon: "20" | "50" | "200") => breadthHistory.map((row) => ({ date: row.date, value: row[`breadth_${horizon}`] }));
  const lastBreadth = last(breadthHistory);
  const boundsFor = (horizon: "20" | "50" | "200") => {
    const reading = breadth.data?.observation?.latest?.horizons[horizon];
    return reading?.status === "ready" && finite(reading.lower) && finite(reading.upper) && reading.lower <= reading.upper
      ? { low: reading.lower, high: reading.upper } : undefined;
  };
  const bounds = boundsFor("50");
  const cnItem = (id: string): MarketObservation | undefined => cnObservations.data?.items.find((item) => item.metric_id === id);
  const marginBalance = cnItem("margin_balance");
  const marginBuy = cnItem("margin_buy");
  const marginRatio = seriesPoints(rates.data?.series.margin_rzyezb);
  const marginRatioPosition = historicalPosition(marginRatio, 756);
  const marginChangePct = finite(marginBalance?.value) && marginBalance.value > 0 && finite(marginBalance.change)
    && marginBalance.value - marginBalance.change > 0
    ? marginBalance.change / (marginBalance.value - marginBalance.change) * 100 : null;
  const funding = market === "cn" ? supplement.data?.series?.dr007 : supplement.data?.series?.nfci;
  const fundingPoints = funding?.points ?? [];
  const priceDate = price?.dates[price.dates.length - 1];
  const cards: Card[] = [
    { topic: "breadth", title: "市场宽度 B20 / B50 / B200", value: lastBreadth ? `20日 ${formatted(lastBreadth.breadth_20, 0)}% · 50日 ${formatted(lastBreadth.breadth_50, 0)}% · 200日 ${formatted(lastBreadth.breadth_200, 0)}%` : "未知",
      date: lastBreadth?.date ?? "未提供", frequency: "日频", points: breadthPoints("50"),
      reading: `同池股票站上各自均线的比例；看参与面的位置和变化。${lastBreadth?.date && priceDate && lastBreadth.date !== priceDate ? `宽度截至${lastBreadth.date}，价格截至${priceDate}，日期不同步。` : ""}高低区间用来比较参与面的历史位置。`, source: market === "cn" ? "现有全A宽度历史" : "现有标普500样本宽度历史",
      note: `价格截至 ${priceDate ?? "未知"}；宽度与价格日期不同步时，不延用宽度读数。50日高低历史参考 ${bounds ? `${formatted(bounds.low, 1)}% / ${formatted(bounds.high, 1)}%` : "不足"}；StockCharts 30% / 70%仅作行业阅读参考，不是本池数据的验证阈值。`, state: breadth.isError ? "宽度读取失败" : breadth.isPending ? "读取中" : undefined,
      reference: bounds ? `B50历史P10 / P90：${formatted(bounds.low, 1)}% / ${formatted(bounds.high, 1)}% · StockCharts参考30% / 70%` : "B50历史参考区间不足 · StockCharts参考30% / 70%" },
    { topic: "erp", title: market === "cn" ? "股债利差 ERP" : "股债收益差 · TTM E/P−名义10Y", value: `${formatted(last(erp.points)?.value)} ${erp.unit || "百分点"}`, date: last(erp.points)?.date ?? "未提供", frequency: erp.frequency === "monthly" ? "月频" : erp.frequency === "weekly" ? "周频" : "日频", points: erp.points, unit: erp.unit,
      reading: market === "cn" ? "沪深300盈利收益率减中国10年国债收益率；相对估值位置需结合历史轨道。" : "标普500 TTM盈利收益率减美国名义10年国债收益率；与美联储前瞻盈利、实际利率口径不同，不套用其绝对阈值。",
      source: erp.sourceName, sourceUrl: erp.sourceUrl, note: erp.note, state: erp.error ? "读取失败" : erp.isPending ? "读取中" : undefined },
    { topic: "volatility", title: market === "us" ? "实现波动 HV20 / HV60 · VIX" : "实现波动 HV20 / HV60", value: `20日 ${formatted(currentVol?.hv20)}% · 60日 ${formatted(currentVol?.hv60)}%`, date: currentVol?.date ?? "未提供", frequency: "日频", points: hvPoints, comparison: hv60Points,
      reading: `20/60比值 ${formatted(currentVol?.ratio)}；1仅表示两窗口波动相等。20日三年历史位置 ${percentile === null ? "样本不足" : `${formatted(percentile, 1)}%`}。波动衡量价格起伏的幅度，用于观察冲击强弱。`, unit: "%",
      source: market === "cn" ? "现有上证指数收盘价" : "现有标普500收盘价", note: "富达仅用于波动率用途说明，其算法为对数收益；本系统使用简单日收益样本标准差×√252，20/60日分别需连续21/61个有效收盘价，缺值留空。三年P15/P85是本系统历史观察参考，不是富达或其他机构交易阈值。",
      state: overlay.isError ? "价格读取失败" : overlay.isPending ? "读取中" : undefined,
      ...(market === "us" ? { secondary: { label: "VIX预期波动", points: vix.points, value: `${formatted(last(vix.points)?.value)} ${vix.unit}`, date: last(vix.points)?.date ?? "未提供", source: vix.sourceName, sourceUrl: vix.sourceUrl, state: vix.error ? "读取失败" : vix.isPending ? "读取中" : undefined, unit: vix.unit } } : {}) },
    market === "cn"
      ? { topic: "heat", title: "交易热度与融资", value: `融资余额占比 ${formatted(last(marginRatio)?.value)}%`, date: last(marginRatio)?.date ?? "未提供", frequency: "日频", points: marginRatio, unit: "%",
        reading: `供应商融资余额/流通市值占比${marginRatioPosition === null ? "，此前756条完整历史位置不足" : `，此前756条历史位置 ${formatted(marginRatioPosition, 1)}%`}。比例偏高可由流通市值分母下降导致，需与余额变化分别看。`, source: marginBalance?.source_name ?? "东方财富融资融券历史汇总", sourceUrl: marginBalance?.source_url ?? undefined, note: `融资余额 ${formatted(marginBalance?.value, 0)}亿元（${marginBalance?.observation_date ?? "未核"}），较前20个有效观测日${marginChangePct === null ? "变化未知" : `变化 ${formatted(marginChangePct)}%`}；融资买入额 ${formatted(marginBuy?.value, 0)}亿元（${marginBuy?.observation_date ?? "未核"}）。两者不等于资金净流入。供应商占比分母为流通市值，同池范围待核；融资标的可能含基金，不是融资买入占股票成交额。融资余额与两融余额不同；全市场自由流通换手及融资买入额占成交额同池分母未核齐。历史P15/P85是本系统观察参考，非官方阈值。`,
        state: rates.isError && cnObservations.isError ? "融资资料读取失败" : rates.isPending && cnObservations.isPending ? "读取中" : undefined,
        secondary: { label: "融资余额 / 20日变化", points: marginBalance?.observation_date && finite(marginBalance.value) ? [{ date: marginBalance.observation_date, value: marginBalance.value }] : [], value: `${formatted(marginBalance?.value, 0)}亿 / ${marginChangePct === null ? "未知" : `${formatted(marginChangePct)}%`}`, date: marginBalance?.observation_date ?? "未提供", source: marginBalance?.source_name ?? "东方财富融资融券历史汇总", sourceUrl: marginBalance?.source_url ?? undefined, state: cnObservations.isError ? "读取失败" : cnObservations.isPending ? "读取中" : undefined, unit: "亿元" } }
      : { topic: "heat", title: "情绪与融资 AAII / FINRA", value: `看多−看空 ${formatted(last(sentiment.points)?.value)} ${sentiment.unit}`, date: last(sentiment.points)?.date ?? "未提供", frequency: "周频 / 月频", points: sentiment.points, unit: sentiment.unit,
        reading: `AAII只代表受访者意见；FINRA客户融资余额 ${formatted(last(finance.points)?.value, 0)} ${finance.unit}（${last(finance.points)?.date ?? "未核"}），反映融资债务存量及其变化。`, source: sentiment.sourceName, sourceUrl: sentiment.sourceUrl, note: `${sentiment.note} FINRA：${finance.note}`,
        state: sentiment.error ? "情绪读取失败" : sentiment.isPending ? "读取中" : undefined,
        secondary: { label: "FINRA客户融资余额", points: finance.points, value: `${formatted(last(finance.points)?.value, 0)} ${finance.unit}`, date: last(finance.points)?.date ?? "未提供", source: finance.sourceName, sourceUrl: finance.sourceUrl, state: finance.error ? "读取失败" : finance.isPending ? "读取中" : undefined, unit: finance.unit } },
    market === "cn"
      ? { topic: "funding", title: "资金条件 DR007", value: `${formatted(last(fundingPoints)?.value, 4)} ${funding?.unit ?? ""}`, date: funding?.snapshotTime ?? last(fundingPoints)?.date ?? "未提供", frequency: "当前快照", points: fundingPoints, unit: funding?.unit,
        reading: "银行间短期资金价格；官方当前快照。7天政策招标机制已调整，暂不计算DR007与政策利率之差。", source: funding?.sourceName ?? "待核来源", sourceUrl: funding?.sourceUrl,
        note: funding?.note ?? supplement.data?.gaps?.find((gap) => gap.id === "dr007")?.reason ?? "DR007资料尚未取得。", policyUrl: supplement.data?.provenance?.policyAnnouncement?.url,
        state: supplement.isError ? "补充资料读取失败" : supplement.isPending ? "读取中" : undefined }
      : { topic: "funding", title: "信用利差 HY OAS / NFCI", value: `${formatted(last(hyOas.points)?.value)} ${hyOas.unit}`, date: last(hyOas.points)?.date ?? "未提供", frequency: "日频 / 周频", points: hyOas.points, unit: hyOas.unit,
        reading: `高收益债信用利差扩大表示融资风险补偿增加；NFCI ${formatted(last(fundingPoints)?.value)} ${funding?.unit ?? ""}（${last(fundingPoints)?.date ?? "未核"}）上升表示条件趋紧。`, source: hyOas.sourceName, sourceUrl: hyOas.sourceUrl,
        note: `${hyOas.note} NFCI：${funding?.note ?? "历史展示包未读到。"}`, state: hyOas.error ? "信用利差读取失败" : hyOas.isPending ? "读取中" : undefined,
        secondary: { label: "NFCI金融条件", points: fundingPoints, value: `${formatted(last(fundingPoints)?.value)} ${funding?.unit ?? ""}`, date: last(fundingPoints)?.date ?? "未提供", source: funding?.sourceName ?? "Chicago Fed", sourceUrl: funding?.sourceUrl, state: supplement.isError ? "读取失败" : supplement.isPending ? "读取中" : undefined, unit: funding?.unit } },
    market === "cn"
      ? { topic: "earnings", title: "盈利预期修正", value: "未知", date: "未核", frequency: "预测财年", points: [], reading: "同一预测财年、相邻两期共识EPS中，上修家数减下修家数，再除以有效配对公司数。", source: "待核两期一致预期快照", note: "缺同池、同预测财年、相邻两期及首次可知时间，不能计算修正广度；PE或ERP不能替代。" }
      : { topic: "earnings", title: "盈利预期修正", value: "未知", date: "未核", frequency: "预测财年", points: [], reading: "同一预测财年、相邻两期共识EPS中，上修家数减下修家数，再除以有效配对公司数。", source: "待核两期一致预期快照", note: "缺同池、同预测财年、相邻两期及首次可知时间，不能计算修正广度；CAPE或ERP不能替代。" },
  ];
  const ids = market === "cn" ? ["breadth-cn", "erp-cn", "hv-cn", "cn-financing", "dr007", "earnings-cn"]
    : ["breadth-us", "erp-us", "hv-us", "aaii", "hy-oas", "earnings-us"];
  const displayCards = cards.flatMap((card, index) => {
    const id = ids[index] === "earnings-cn" || ids[index] === "earnings-us" ? "earnings-revisions" : ids[index];
    const primary = selectedIds.includes(id) ? [{ ...card, id,
      title: market === "us" && id === "hv-us" ? "实现波动 HV20 / HV60" : market === "us" && id === "aaii" ? "投资者情绪 AAII" : market === "us" && id === "hy-oas" ? "高收益债信用利差" : card.title,
      secondary: market === "us" ? undefined : card.secondary,
      reading: market === "us" && id === "aaii" ? "反映受访个人投资者对未来六个月的多空看法。"
        : market === "us" && id === "hy-oas" ? "利差扩大表示企业借债需要更多风险补偿，用于跟踪信用压力。" : card.reading,
      frequency: market === "us" && id === "aaii" ? "周频" : market === "us" && id === "hy-oas" ? "日频" : card.frequency,
    }] : [];
    const extra = market === "us" && card.secondary ? {
      ...card, id: id === "aaii" ? "finra-margin" : id === "hy-oas" ? "nfci" : "vix", title: card.secondary.label, value: card.secondary.value, date: card.secondary.date,
      points: card.secondary.points, unit: card.secondary.unit, source: card.secondary.source,
      sourceUrl: card.secondary.sourceUrl, state: card.secondary.state, secondary: undefined, comparison: undefined,
      frequency: id === "aaii" ? "月频" : id === "hy-oas" ? "周频" : "日频",
      note: id === "aaii" ? finance.note : id === "hy-oas" ? funding?.note ?? "周频金融条件；历史版本可能修订。" : `${vix.note} Cboe定义约30日预期波动，与收盘价计算的HV不同；本系统历史分位不是Cboe交易阈值。`,
      reading: id === "aaii" ? "客户融资负债存量，月度公布；并非净流入。" : id === "hy-oas" ? "高于零表示美国金融条件相对自身均值偏紧。" : "期权预期波动没有涨跌方向。",
    } : null;
    const extraId = id === "aaii" ? "finra-margin" : id === "hy-oas" ? "nfci" : id === "hv-us" ? "vix" : "";
    return [...primary, ...(extra && selectedIds.includes(extraId) ? [extra] : [])];
  });
  useEffect(() => {
    for (const card of displayCards) {
      if (market === "us" && card.id === "erp-us") continue;
      const value = card.state ?? (card.value.includes("未知") ? "读数待补" : card.value);
      const meaning = card.state || value === "读数待补" ? "读数待补齐，可先查看已有指标"
        : card.topic === "breadth" ? "看上涨参与面是否扩大"
          : card.topic === "erp" ? "看股债收益差与历史位置"
            : card.topic === "volatility" && card.id !== "vix" ? "看近期价格起伏与中期比较"
              : card.id === "vix" ? "看期权市场对未来约30日起伏幅度的预期"
                : card.id === "cn-financing" ? "融资占比需和余额变化一起看"
                  : card.topic === "funding" ? "看资金或信用条件变化"
                    : card.topic === "heat" ? "看情绪或融资存量变化" : "当前资料仍待核";
      onSummary(`${market}:${card.id}`, { value, meaning, date: card.date === "未提供" || card.date === "未核" ? undefined : card.date });
    }
  });
  const sourceLinks = (card: Card) => <>{card.sourceUrl ? <a href={card.sourceUrl} target="_blank" rel="noreferrer">{card.source}</a> : card.source}
    {card.topic === "erp" && market === "us" && <> · <a href={FED_ERP_EXPLAINER} target="_blank" rel="noreferrer">美联储不同口径说明</a></>}
    {card.comparison && <> · <a href={HV_EXPLAINER} target="_blank" rel="noreferrer">富达波动用途说明</a></>}
    {card.title.includes("VIX") && <> · <a href={CBOE_VIX_EXPLAINER} target="_blank" rel="noreferrer">Cboe定义</a></>}
    {card.title.includes("NFCI") && <> · <a href={NFCI_EXPLAINER} target="_blank" rel="noreferrer">芝加哥联储定义</a></>}</>;
  return <div className="cmo-card-grid" aria-label={`${market === "cn" ? "A股" : "美股"}补充观察`}>
    {displayCards.map((card, index) => {
      if (market === "us" && card.id === "erp-us") return <UsErpCard key={card.id}
        collapsed={collapsedIds.includes(card.id)} onCollapse={() => onCollapse(card.id)}
        onSummary={summary => onSummary(`${market}:${card.id}`, summary)} />;
      if (collapsedIds.includes(card.id)) return null;
      if (card.id === "hy-oas") return <HyOasCard key={card.id} title={card.title} points={card.points} state={card.state}
        source={card.source} sourceUrl={card.sourceUrl} onCollapse={() => onCollapse(card.id)}
        onDetail={(reading, limit) => onDetail(market, { ...card, displayReading: reading, displayLimit: limit })} />;
      const hasHistory = card.points.length > 1 && !card.state;
      const lookback = card.frequency === "月频" ? 36 : card.frequency === "周频" ? 156 : 756;
      const allowBands = card.topic === "erp" || card.topic === "volatility" || card.title === "交易热度与融资" ||
        /VIX|NFCI|AAII/.test(card.title);
      const mainBands = hasHistory && allowBands ? priorReferenceBands(card.points, lookback) : null;
      const chartStart = Math.max(0, card.points.length - 252);
      const visible = card.points.slice(chartStart);
      const zeroMeaning = card.topic === "erp" ? "0：盈利收益率与国债收益率相等" : card.title.includes("NFCI") ? "0：历史平均金融条件" : card.title.includes("AAII") ? "0：看多看空比例相等" : null;
      const lowColor = card.topic === "erp" ? CHART_COLORS.high : CHART_COLORS.low;
      const highColor = card.topic === "erp" ? CHART_COLORS.low : CHART_COLORS.high;
      const seriesLabel = card.comparison ? "20日波动" : card.topic === "erp" ? "股债收益差" : card.title === "交易热度与融资" ? "融资余额 / 流通市值" : card.title;
      const references = [
        ...(mainBands?.latest.low !== null && mainBands?.latest.low !== undefined ? [
          { name: "历史低位", color: lowColor, values: mainBands.low.slice(chartStart), endLabel: `低 ${formatted(mainBands.latest.low, 2)}` },
          { name: "历史高位", color: highColor, values: mainBands.high.slice(chartStart), endLabel: `高 ${formatted(mainBands.latest.high, 2)}` }] : []),
        ...(zeroMeaning ? [{ name: zeroMeaning, color: CHART_COLORS.zero, values: visible.map(() => 0), endLabel: "0" }] : []),
      ];
      const referenceReady = mainBands?.latest.low !== null && mainBands?.latest.low !== undefined;
      const historyLimit = allowBands && !referenceReady && hasHistory ? "可比历史还不够，暂不显示高低参考。" : null;
      const currentValue = last(card.points)?.value;
      const comparisonPeriods = card.frequency === "周频" ? 4 : card.frequency === "月频" ? 1 : card.frequency === "日频" ? 20 : null;
      const recent = comparisonPeriods && !card.state ? recentDelta(card.points, comparisonPeriods) : null;
      const changeUnit = card.unit === "%" || card.unit === "百分点" ? "个百分点" : card.unit === "指数" ? "指数点" : card.unit || "点";
      const recentText = recent ? `较 ${recent.previous.date} ${recent.difference >= 0 ? "上升" : "下降"} ${formatted(Math.abs(recent.difference))} ${changeUnit}` : comparisonPeriods ? "近期变化暂不可比" : null;
      const position = !card.state && finite(currentValue) && finite(mainBands?.latest.low) && finite(mainBands?.latest.high)
        ? currentValue < mainBands.latest.low ? "偏低" : currentValue > mainBands.latest.high ? "偏高" : "中间" : null;
      const conclusion = card.state ? "资料暂不可读"
        : card.topic === "erp" && position ? `收益差处历史${position}区`
        : card.topic === "volatility" && position ? `波动处历史${position}区`
        : card.title.includes("NFCI") && finite(currentValue) ? currentValue > 0 ? "金融条件较历史平均偏紧" : currentValue < 0 ? "金融条件较历史平均偏松" : "金融条件接近历史平均"
        : card.title.includes("VIX") && position ? `预期波动处自身历史${position}区`
        : card.title.includes("AAII") && position ? `受访者多空差处自身历史${position}区`
        : card.title.includes("FINRA") && recent ? recent.difference > 0 ? "融资债务存量较上月增加" : recent.difference < 0 ? "融资债务存量较上月减少" : "融资债务存量与上月持平"
        : card.title === "交易热度与融资" && position === "偏高" && marginChangePct !== null && marginChangePct < 0 ? "融资占比偏高，余额近期收缩"
        : card.title === "交易热度与融资" && position ? `融资占比处自身历史${position}区`
        : card.topic === "funding" && market === "cn" ? "银行间短期资金价格"
        : card.topic === "heat" ? "融资与观点" : card.topic === "funding" ? "资金与信用" : card.topic === "earnings" ? "盈利资料待核" : "历史资料观察";
      const plainReading = card.title === "交易热度与融资" ? "占比看融资负担相对市值的高低，余额变化看杠杆增减；两项一起读。"
        : card.comparison ? "20日看近期起伏，60日看中期起伏；比值大于1表示短期起伏更大，高分位表示近期起伏在自身历史中偏大。"
        : card.topic === "erp" ? "收益差低时估值缓冲较小，高时相对价格吸引力较强；盈利变化帮助观察这份吸引力的支撑。"
        : card.title.includes("VIX") ? "看期权市场对未来约30日起伏幅度的预期；读数升高表示预期起伏加大，可与20日实际波动对照。"
        : card.title.includes("NFCI") ? "高于零偏紧，低于零偏松；这是金融条件的历史平均线。"
        : card.title.includes("AAII") ? "看受访个人投资者的多空倾向：差值越高越乐观，越低越悲观。"
        : card.title.includes("FINRA") ? "看客户融资债务规模：余额增加表示杠杆使用增加，下降表示收缩。"
        : card.topic === "funding" ? "当前读数反映银行间短期资金价格；连续历史待补齐，后续可观察资金松紧的变化。"
        : card.topic === "earnings" ? "连续盈利预测待补齐；补齐后可比较上调与下调公司的比例，观察盈利预期方向。"
        : card.topic === "breadth" ? "看站上均线的股票是否增多，以判断上涨参与面。"
        : "对照历史位置与近期变化。";
      const plainLimit = card.title === "交易热度与融资" ? "占比使用供应商流通市值，股票范围仍待核。历史高低仅供观察。"
        : card.comparison ? "高低线按自身历史计算，用于比较当前价格起伏与历史水平。"
        : card.topic === "erp" && market === "us" ? "这里比较已实现盈利收益率与名义国债收益率，反映这一口径下的相对估值。"
        : card.topic === "funding" && market === "cn" ? "政策招标方式已变，当前先观察DR007本身的资金价格。"
        : card.topic === "earnings" ? "尚无可比读数。" : "高低线按自身历史计算，用于比较当前水平与历史位置。";
      const legend = [
        { label: seriesLabel, color: CHART_COLORS.primary, value: card.state ? undefined : finite(currentValue) ? `${formatted(currentValue)}${card.unit ?? ""}` : undefined },
        ...(card.comparison ? [{ label: "60日波动", color: CHART_COLORS.secondary, value: `${formatted(last(card.comparison)?.value)}%` }] : []),
        ...(referenceReady ? [
          { label: card.comparison ? "20日参考低位" : "参考低位", color: lowColor, dashed: true, value: `${formatted(mainBands.latest.low)}${card.unit ?? ""}` },
          { label: card.comparison ? "20日参考高位" : "参考高位", color: highColor, dashed: true, value: `${formatted(mainBands.latest.high)}${card.unit ?? ""}` },
        ] : []),
        ...(zeroMeaning ? [{ label: "0线", color: CHART_COLORS.zero, dashed: true, value: "0" }] : []),
      ];
      return <article key={`${card.title}-${index}`} className="moa-item cmo-home-card" aria-label={card.title} data-tone="neutral" data-overview-card={card.id}>
      <div className="moa-item-head"><h3>{card.comparison ? `${market === "cn" ? "上证" : "标普500"} · 20/60日波动率` : card.topic === "erp" && market === "us" ? "标普500 · 股债收益差" : card.title}</h3><div className="moa-item-actions">{(card.state || card.points.length < 2) && <span className="moa-quality">{card.state ?? "仅有当前值"}</span>}<button type="button" onClick={() => onCollapse(card.id)}>收起</button></div></div>
      <h4 className="moa-conclusion">{conclusion}</h4>
      <div className="moa-erp-value"><strong>{card.state ? "未知" : card.comparison ? `${formatted(last(card.points)?.value)}%` : card.value}</strong>{card.comparison && <span>年化 · 20日</span>}</div>
      <ChartLegend items={legend} label={`${card.title}曲线与参考`} />
      <MiniTrend dates={card.state ? [] : visible.map((point) => point.date)}
        lines={[{ name: card.comparison ? "20日波动" : card.title, color: CHART_COLORS.primary, values: card.state ? [] : visible.map((point) => point.value) },
          ...(card.comparison ? [{ name: "60日波动", color: CHART_COLORS.secondary, values: card.comparison.slice(chartStart).map((point) => point.value) }] : [])]}
        references={references}
        label={`${card.title}历史曲线，缺值保留断线`} />
      {recentText && <p className="moa-card-change">{recentText}</p>}
      {card.comparison && finite(currentVol?.ratio) && <p className="moa-card-change">20/60日之比 <b>{formatted(currentVol.ratio)}</b> · 短期波动{currentVol.ratio > 1 ? "大于" : currentVol.ratio < 1 ? "小于" : "等于"}中期</p>}
      {card.title === "交易热度与融资" && <p className="moa-card-change">融资余额较前期{marginChangePct === null ? "变化未知" : `${marginChangePct >= 0 ? "上升" : "下降"} ${formatted(Math.abs(marginChangePct))}%`}（{marginBalance?.observation_date ?? "日期未核"}）</p>}
      <p className="moa-card-reading">{plainReading}</p>
      {historyLimit && <p className="moa-card-limit">{historyLimit}</p>}
      <p className="moa-card-meta">资料截至 {card.date} · {card.frequency}</p>
      <footer><button type="button" onClick={() => { const hv60Bands = card.comparison ? priorReferenceBands(card.comparison, 756).latest : null;
        onDetail(market, { ...card, displayReading: plainReading, displayLimit: plainLimit,
          hv60Reference: hv60Bands?.low != null && hv60Bands.high != null ? { low: hv60Bands.low, high: hv60Bands.high } : null }); }}>看大图 ↗</button>
        <details><summary>来源与参考</summary><p>{plainLimit}</p><p>{sourceLinks(card)}</p></details></footer>
    </article>; })}
  </div>;
}

export default function CrossMarketObservation({ market, selectedIds, collapsedIds = [], onCollapse = () => {}, onSummary = () => {} }: {
  market: Market; selectedIds: readonly string[]; collapsedIds?: readonly string[];
  onCollapse?: (id: string) => void; onSummary?: (id: string, summary: CandidateSummary) => void;
}) {
  const [detail, setDetail] = useState<{ market: Market; card: Card } | null>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const openDetail = (market: Market, card: Card) => { openerRef.current = document.activeElement as HTMLElement | null; setDetail({ market, card }); };
  useEffect(() => {
    if (!detail) return;
    const dialog = dialogRef.current;
    dialog?.querySelector<HTMLElement>("button")?.focus();
    const keys = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setDetail(null); }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = [...dialog.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) { event.preventDefault(); dialog.focus(); return; }
      const first = focusable[0], lastItem = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); lastItem.focus(); }
      else if (!event.shiftKey && document.activeElement === lastItem) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", keys);
    return () => { document.removeEventListener("keydown", keys); openerRef.current?.focus(); };
  }, [detail]);
  return <section className="cross-market-observation" aria-label={`${market === "cn" ? "A股" : "美股"}补充观察`}>
    <MarketColumn market={market} selectedIds={selectedIds} collapsedIds={collapsedIds} onCollapse={onCollapse} onSummary={onSummary} onDetail={openDetail} />
    {detail && <div className="cmo-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDetail(null); }}>
      <section ref={dialogRef} className="cmo-dialog" role="dialog" aria-modal="true" tabIndex={-1} aria-label={`${detail.market === "cn" ? "A股" : "美股"}${detail.card.title}`}>
        <header><div><h2>{detail.market === "cn" ? "A股" : "美股"} · {detail.card.title}</h2><p>{detail.card.frequency} · 资料截至 {detail.card.date}</p></div><button type="button" onClick={() => setDetail(null)} aria-label="关闭详情">关闭 ×</button></header>
        {detail.card.topic === "breadth" ? <BreadthComparison market={detail.market} onMarketChange={() => {}} />
          : detail.card.topic === "erp"
            ? <MetricProjection id={detail.market === "cn" ? "erp-cn" : "erp-us"} market={detail.market} />
            : <><p className="cmo-detail-reading">{detail.card.state ?? detail.card.value} · {detail.card.displayReading}</p>{detail.card.state ? <p>{detail.card.state}；历史曲线待资料补齐后展示。</p> : <DetailTrend points={detail.card.points} comparison={detail.card.comparison} label={detail.card.comparison ? "20日波动" : detail.card.title} unit={detail.card.unit ?? ""} />}</>}
        {detail.card.hv60Reference && <p>60日波动的历史参考：较低 {formatted(detail.card.hv60Reference.low)}%，较高 {formatted(detail.card.hv60Reference.high)}%。仅作历史比较。</p>}
        {detail.card.secondary && <div className="cmo-detail-secondary"><h3>{detail.card.secondary.label} · {detail.card.secondary.state ?? detail.card.secondary.value}</h3>{detail.card.secondary.state ? <p>{detail.card.secondary.state}；历史曲线待资料补齐后展示。</p> : <DetailTrend points={detail.card.secondary.points} label={detail.card.secondary.label} unit={detail.card.secondary.unit ?? ""} />}<p>{detail.card.secondary.sourceUrl ? <a href={detail.card.secondary.sourceUrl} target="_blank" rel="noreferrer">{detail.card.secondary.source}</a> : detail.card.secondary.source} · {detail.card.secondary.date}</p></div>}
        <p>{detail.card.displayLimit}</p><p>来源：{detail.card.sourceUrl ? <a href={detail.card.sourceUrl} target="_blank" rel="noreferrer">{detail.card.source}</a> : detail.card.source}。资料日期：{detail.card.date}。{detail.card.policyUrl && <> <a href={detail.card.policyUrl} target="_blank" rel="noreferrer">央行政策变更公告</a></>}</p>
      </section>
    </div>}
  </section>;
}
