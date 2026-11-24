import { useState } from "react";
import { marketReferenceBands, NASDAQ_VALUATION_SNAPSHOT, VALUATION_SOURCES } from "./marketReferenceBands";
import ValuationReferenceReading from "./ValuationReferenceReading";
import BakerReading from "./BakerReading";
import ErpBandSummary from "./ErpBandSummary";
import { erpBands, ERP_BAND_METHOD, type ErpBandPoint } from "./erpBands";
import { ERP_REFERENCE_QUERY_KEY, ERP_REFERENCE_URL, fromErpReference, parseErpReference } from "./erpReferenceData";
import { useQuery } from "@tanstack/react-query";
import { api, fundamentalsApi } from "../../api/client";
import type { MarketObservation } from "../../types";
import { useFocusMomentumObservation } from "../focus-momentum/data";
import MarketTrendChart from "../market-style/MarketTrendChart";
import { OBSERVATION_BY_ID } from "./catalog";
import { CONCENTRATION_QUERY_KEY, CONCENTRATION_URL, fromConcentration, parseConcentration } from "./concentrationData";
import { CANDIDATE_QUERY_KEY, CANDIDATE_URL, HISTORICAL_CANDIDATE_IDS, fromCandidateHistory,
  parseCandidateHistory, SMALLCAP_QUERY_KEY, SMALLCAP_URL, parseSmallcapSnapshot,
  fromSmallcapSnapshot, type HistoricalCandidateId } from "./candidateData";
import {
  formatValue, fromCnPmi, fromErpHistory, fromFocus, fromObservation,
  fromReused, fromSurveyHistory, fromUsMacro, fromValuation, parseBaker, parseReused,
  type MetricReading,
} from "./metricData";

const STATIC_PREFIX = "/research/observation-library-20261026/";
async function readJson(url: string): Promise<unknown> {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  if (!(response.headers.get("content-type") ?? "").includes("json")) throw new Error("返回的不是 JSON");
  return response.json();
}

function Failure({ error, retry }: { error: unknown; retry: () => void }) {
  return <p role="alert" className="ol-metric-error">资料读取失败：{error instanceof Error ? error.message : "未知错误"}。<button type="button" onClick={retry}>重试</button></p>;
}

function Reading({ data, compact, id, variant, onVariant, bands, lines }: {
  data: MetricReading | null; compact: boolean; id: string;
  variant?: "orth" | "raw"; onVariant?: (value: "orth" | "raw") => void;
  bands?: ErpBandPoint[]; lines?: readonly { name: string; values: (number | null)[]; color?: string }[];
}) {
  const entry = OBSERVATION_BY_ID.get(id);
  if (!data) return <p className="ol-metric-empty">尚无可核读数；不以零或其他指标代替。</p>;
  const reference = marketReferenceBands(id, data.points, data.valuationFull);
  const level = reference?.latest;
  return <div className={`ol-metric${compact ? " ol-metric-compact" : ""}`}>
    <div className="ol-metric-head">
      <strong>{formatValue(data.value, data.unit)}</strong>
      {data.change !== null && id !== "baker-wurgler" && <span>较{data.comparisonPeriod ?? (entry?.id === "focus-momentum" ? "前一观测" : "上一期")} {data.change > 0 ? "+" : ""}{formatValue(data.change, data.changeUnit ?? data.unit)}</span>}
      <small>{data.dateLabel}：{data.date ?? "未核"}</small>
    </div>
    {reference?.kind === "valuation" && <div className="ol-reference-reading"><ValuationReferenceReading reference={reference} compact={compact} /></div>}
    {reference?.kind === "concentration" && level?.lower != null && level.upper != null && <div className="ol-reference-reading">
      <p><strong>{data.value == null ? "当期缺资料" : data.value <= level.lower ? reference.lowerLabel : data.value >= level.upper ? reference.upperLabel : "位于高低参照之间"}</strong> · {reference.lowerLabel} {level.lower.toFixed(2)}{reference.unit} / {reference.upperLabel} {level.upper.toFixed(2)}{reference.unit}</p>
      <p>{reference.meaning}</p>
      <small><a href={reference.source.url} target="_blank" rel="noreferrer">{reference.source.source} ↗</a> · {reference.coverage}</small>
      {!compact && <p>{reference.detail}</p>}
    </div>}
    {bands && <ErpBandSummary row={bands[bands.length - 1]} compact={compact} />}
    {compact ? <small className="ol-metric-brief">{data.status}</small> : <>
      {data.guide && <p className="ol-metric-status">{data.guide}</p>}
      {data.points.length >= 2 && <a className="op-open-link" href={`/fundamentals?observation=${encodeURIComponent(id)}#fund-sec-market`}>与股指价格对照 →</a>}
      {id === "baker-wurgler" && onVariant && <div className="ol-metric-switch" role="group" aria-label="Baker 情绪指标版本">
        <button type="button" aria-pressed={variant !== "raw"} onClick={() => onVariant("orth")}>SENT_ORTH · 宏观调整后</button>
        <button type="button" aria-pressed={variant === "raw"} onClick={() => onVariant("raw")}>SENT · 原始综合水平</button>
      </div>}
      {data.points.length >= 2 ? <div className="ol-metric-chart">
        <MarketTrendChart dates={data.points.map((point) => point.date)}
          series={lines?.length ? lines.map((line, index) => ({
            name: line.name, values: line.values,
            color: line.color ?? ["#52789e", "#c0563b", "#327c72", "#80678a"][index % 4],
          })) : [{ name: id === "baker-wurgler" ? (variant === "raw" ? "SENT" : "SENT_ORTH") : entry?.label ?? id,
            values: data.points.map((point) => point.value), color: "#52789e" }, ...(reference ? [
              { name: reference.lowerLabel, values: reference.rows.map(row => row.lower), color: "#3c867a", dashed: true },
              { name: reference.upperLabel, values: reference.rows.map(row => row.upper), color: "#ac7032", dashed: true },
            ] : []), ...(bands ? [
            { name: "上轨 +2σ", values: bands.map((p) => p.upper), color: "#327c72" },
            { name: "中轨 · 3年均值", values: bands.map((p) => p.middle), color: "#8693a3" },
            { name: "下轨 −2σ", values: bands.map((p) => p.lower), color: "#986737" },
          ] : [])]}
          unit={data.unit} height={bands ? 280 : 210} />
        <small>历史曲线：{data.points[0].date}—{data.points[data.points.length - 1].date}；缺失值保留断线。</small>
      </div> : <p className="ol-metric-empty">{id === "smallcap-turnover" ? "仅一次快照，暂无历史曲线。" : "历史曲线尚未接通或有效点数不足；仅显示已核读数。"}</p>}
      <p className="ol-metric-status">{data.status}</p>
      {data.alternative && <p>另一版本 {data.alternative.label}：{formatValue(data.alternative.value, data.unit)}（同属 {data.date}）</p>}
      {data.auxiliary?.map((row) => <p key={row.label}>{row.label}：{formatValue(row.value, row.unit)}（所属期 {row.date ?? "未核"}）</p>)}
      <details><summary>口径、来源与限制</summary>
        <p>{data.note}</p><p>来源：{data.sourceUrl ? <a href={data.sourceUrl} target="_blank" rel="noreferrer">{data.sourceName} ↗</a> : data.sourceName}</p>
        {bands && <p>轨道方法：<a href={ERP_BAND_METHOD.url} target="_blank" rel="noreferrer">{ERP_BAND_METHOD.source}</a>。历史位置不等于买卖指令。</p>}
        {id !== "erp-cn" && id !== "erp-us" && <p>版本／口径：{data.sourceVersion}</p>}
      </details>
    </>}
  </div>;
}

const FUNDING_PACKET_URL = "/api/fundamentals/cn-financing-history";
type FundingCard = { id: string; points: { date: string; value: number | null }[]; lines?: { key: string; values: (number | null)[] }[] };

function FinancingMetric({ compact }: { compact: boolean }) {
  const rates = useQuery({ queryKey: ["fundamentalsRatesHistory", 18250], queryFn: () => fundamentalsApi.ratesHistory(18250),
    staleTime: 30 * 60_000, retry: false });
  const funding = useQuery({ queryKey: ["homeFinancingPacketV1"], queryFn: async () => {
    const response = await fetch(FUNDING_PACKET_URL, { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json() as { cards?: FundingCard[] };
  }, staleTime: 30 * 60_000, retry: false });
  if (rates.isPending || funding.isPending) return <p role="status">两融资料读取中…</p>;
  if (rates.isError && funding.isError) return <Failure error={rates.error ?? funding.error} retry={() => { void rates.refetch(); void funding.refetch(); }} />;
  const buy = funding.data?.cards?.find(card => card.id === "cn-margin-buy-share-a-stocks")?.points ?? [];
  const mainCard = funding.data?.cards?.find(card => card.id === "cn-margin-buy-share-a-stocks");
  const ma20Line = mainCard?.lines?.find(line => line.key === "ma20")?.values;
  const ma20 = ma20Line
    ? buy.map((point, index) => ({ date: point.date, value: ma20Line[index] ?? null }))
    : funding.data?.cards?.find(card => card.id === "cn-margin-buy-share-a-stocks-ma20")?.points ?? [];
  const balanceSeries = rates.data?.series.margin_rzyezb;
  const balance = balanceSeries && balanceSeries.dates.length === balanceSeries.values.length
    ? balanceSeries.dates.map((date, index) => ({ date, value: balanceSeries.values[index] })) : [];
  const latest = buy[buy.length - 1];
  if (!latest) return <p className="ol-metric-empty">融资买入占比历史暂不可读；不以其他指标代替。</p>;
  const previous = buy[buy.length - 2];
  const balanceByDate = new Map(balance.map(point => [point.date, point.value]));
  const ma20ByDate = new Map(ma20.map(point => [point.date, point.value]));
  const dates = buy.map(point => point.date);
  const change = previous && latest.value != null && previous.value != null ? latest.value - previous.value : null;
  const data: MetricReading = {
    value: latest.value, unit: "%", date: latest.date, dateLabel: "资料日期",
    change, changeUnit: "百分点", comparisonPeriod: "前一交易日",
    sourceName: "上交所、深交所融资融券明细与成交统计；东方财富融资余额/流通市值",
    sourceUrl: "https://www.sse.com.cn/market/othersdata/margin/sum/",
    sourceVersion: "融资买入占比按同日沪深A股口径；余额占比来自东财两融历史",
    status: "同日对齐；余额占比缺失日留空",
    note: "融资买入额是交易额，不是净流入；20日均值为最近20个官方交易日逐日占比的算术平均；融资余额占流通市值来自另一来源，按同日对齐。",
    points: buy,
  };
  return <Reading id="cn-financing" compact={compact} data={data} lines={[
    { name: "融资买入额占成交额", values: buy.map(point => point.value), color: "#52789e" },
    { name: "20日均值", values: dates.map(date => ma20ByDate.get(date) ?? null), color: "#c0563b" },
    { name: "融资余额占流通市值", values: dates.map(date => balanceByDate.get(date) ?? null), color: "#327c72" },
  ]} />;
}

function FocusMetric({ compact }: { compact: boolean }) {
  const query = useFocusMomentumObservation();
  if (query.isPending) return <p role="status">历史研究资料读取中…</p>;
  if (query.isError) return <Failure error={query.error} retry={() => { void query.refetch(); }} />;
  return <Reading id="focus-momentum" compact={compact} data={fromFocus(query.data)} />;
}

function CandidateMetric({ id, compact }: { id: HistoricalCandidateId; compact: boolean }) {
  const query = useQuery({ queryKey: CANDIDATE_QUERY_KEY,
    queryFn: async () => parseCandidateHistory(await readJson(CANDIDATE_URL)),
    staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  if (query.isPending) return <p role="status">历史观察资料读取中…</p>;
  if (query.isError) return <Failure error={query.error} retry={() => { void query.refetch(); }} />;
  return <Reading id={id} compact={compact} data={fromCandidateHistory(query.data, id)} />;
}

function SmallcapMetric({ compact }: { compact: boolean }) {
  const query = useQuery({ queryKey: SMALLCAP_QUERY_KEY,
    queryFn: async () => parseSmallcapSnapshot(await readJson(SMALLCAP_URL)),
    staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  if (query.isPending) return <p role="status">收盘快照读取中…</p>;
  if (query.isError) return <Failure error={query.error} retry={() => { void query.refetch(); }} />;
  return <Reading id="smallcap-turnover" compact={compact} data={fromSmallcapSnapshot(query.data)} />;
}

function ErpMetric({ id, compact }: { id: "erp-cn" | "erp-us"; compact: boolean }) {
  const query = useQuery({ queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250), enabled: id === "erp-us", staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  const reference = useQuery({ queryKey: ERP_REFERENCE_QUERY_KEY,
    queryFn: async () => parseErpReference(await readJson(ERP_REFERENCE_URL)),
    enabled: id === "erp-cn", staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  if (id === "erp-cn") {
    if (reference.isPending) return <p role="status">股债轨道历史资料读取中…</p>;
    if (reference.isError) return <Failure error={reference.error} retry={() => { void reference.refetch(); }} />;
    const data = fromErpReference(reference.data);
    return <Reading id={id} compact={compact} data={data} bands={erpBands(data.points)} />;
  }
  if (query.isPending) return <p role="status">股债利差资料读取中…</p>;
  if (query.isError) return <Failure error={query.error} retry={() => { void query.refetch(); }} />;
  return <Reading id={id} compact={compact} data={fromErpHistory(query.data, id)} />;
}

function ConcentrationMetric({ compact }: { compact: boolean }) {
  const query = useQuery({ queryKey: CONCENTRATION_QUERY_KEY,
    queryFn: async () => parseConcentration(await readJson(CONCENTRATION_URL)),
    staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  if (query.isPending) return <p role="status">月度成交额资料读取中…</p>;
  if (query.isError) return <Failure error={query.error} retry={() => { void query.refetch(); }} />;
  return <Reading id="turnover-concentration" compact={compact} data={fromConcentration(query.data)} />;
}

function StaticMetric({ id, compact }: { id: "ofr-fsi" | "finra-margin" | "baker-wurgler" | "nfci" | "vxn"; compact: boolean }) {
  const [variant, setVariant] = useState<"orth" | "raw">("orth");
  const url = `${STATIC_PREFIX}${id === "baker-wurgler" ? "baker.json" : "reused-series.json"}`;
  const query = useQuery({ queryKey: ["observationLibraryStatic", url],
    queryFn: async () => id === "baker-wurgler" ? parseBaker(await readJson(url)) : parseReused(await readJson(url)),
    staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  if (query.isPending) return <p role="status">已存历史资料读取中…</p>;
  if (query.isError) return <Failure error={query.error} retry={() => { void query.refetch(); }} />;
  if (id === "baker-wurgler") return <BakerReading data={parseBaker(query.data)} compact={compact} variant={variant} onVariant={setVariant} />;
  const data = fromReused(parseReused(query.data), id, compact);
  return <Reading id={id} compact={compact} data={data} />;
}

const OBS_IDS: Record<string, { market: "cn" | "us"; metric: string }> = {
  vix: { market: "us", metric: "vix" }, vxn: { market: "us", metric: "vxn" },
  "hy-oas": { market: "us", metric: "hy_oas" },
  "cn-financing": { market: "cn", metric: "margin_balance" },
  aaii: { market: "us", metric: "aaii" }, naaim: { market: "us", metric: "naaim" },
};

function ApiMetric({ id, compact }: { id: string; compact: boolean }) {
  const obs = OBS_IDS[id];
  const market = obs?.market ?? "us";
  const observationQuery = useQuery({ queryKey: ["fundamentalsObservations", market],
    queryFn: () => fundamentalsApi.observations(market), staleTime: 5 * 60_000, retry: false,
    enabled: !!obs });
  const ratesQuery = useQuery({ queryKey: ["fundamentalsRates"], queryFn: () => fundamentalsApi.rates(),
    staleTime: 5 * 60_000, retry: false, enabled: id === "hs300-pe" || id === "sp500-cape" });
  const ratesHistory = useQuery({ queryKey: ["fundamentalsRatesHistory", 18250], queryFn: () => fundamentalsApi.ratesHistory(18250),
    staleTime: 30 * 60_000, retry: false,
    enabled: !compact && id === "vix" });
  const valuationHistory = useQuery({ queryKey: ["fundamentalsValuationHistory"],
    queryFn: () => fundamentalsApi.valuationHistory(), enabled: id === "hs300-pe" || id === "sp500-cape",
    staleTime: 5 * 60_000, retry: false });
  const overview = useQuery({ queryKey: ["fundamentalsOverview"], queryFn: () => fundamentalsApi.overview(),
    staleTime: 5 * 60_000, retry: false, enabled: id === "pmi-cn" });
  const macroHistory = useQuery({ queryKey: ["fundamentalsMacroHistory", 60], queryFn: () => fundamentalsApi.macroHistory(60),
    staleTime: 30 * 60_000, retry: false, enabled: !compact && id === "pmi-cn" });
  const usMacro = useQuery({ queryKey: ["fundamentalsUsMacro"], queryFn: () => fundamentalsApi.usMacro(),
    staleTime: 30 * 60_000, retry: false, enabled: id === "wei" || (!compact && id === "hy-oas") });
  const survey = id === "aaii" || id === "naaim" ? id : "aaii";
  const surveyHistory = useQuery({ queryKey: ["sentimentHistory", survey],
    queryFn: () => api.marketContextSentimentHistory(survey), staleTime: 5 * 60_000,
    retry: false, enabled: !compact && (id === "aaii" || id === "naaim") });

  const primary = obs ? observationQuery : id === "hs300-pe" || id === "sp500-cape" ? ratesQuery
    : id === "pmi-cn" ? overview : id === "wei" ? usMacro : null;
  if (!primary) return <p className="ol-metric-empty">此指标的原读数尚未接通；不以其他指标代替。</p>;
  if (primary.isPending) return <p role="status">观察资料读取中…</p>;
  if (primary.isError) return <Failure error={primary.error} retry={() => { void primary.refetch(); }} />;

  let data: MetricReading | null = null;
  if (obs) {
    const item: MarketObservation | undefined = observationQuery.data?.items.find((row) => row.metric_id === obs.metric);
    let points = id === "vix" ? ratesHistory.data?.series.vix : undefined;
    if (id === "hy-oas") points = usMacro.data?.series.hy_oas;
    const historyPoints = points && !compact && points.dates.length === points.values.length
      ? points.dates.map((date, index) => ({ date, value: points.values[index] })) : [];
    data = fromObservation(item, historyPoints);
    if (data && (id === "aaii" || id === "naaim") && !compact) data.points = fromSurveyHistory(surveyHistory.data, id);
    if (data && id === "cn-financing") {
      const buy = observationQuery.data?.items.find((row) => row.metric_id === "margin_buy");
      const buyReading = fromObservation(buy);
      data.auxiliary = [{ label: "融资买入额（交易额，非净流入）", value: buyReading?.value ?? null,
        unit: buyReading?.unit ?? "亿元", date: buyReading?.date ?? null }];
      data.note += "；融资买入额是交易额，不是净流入。同口径融资余额历史曲线尚未接通；已有两融合计历史不可替代。";
    }
  } else if (id === "hs300-pe" || id === "sp500-cape") {
    data = fromValuation(ratesQuery.data, id, valuationHistory.data?.series[id === "hs300-pe" ? "pe_cn" : "cape_us"], valuationHistory.data?.valuation_full);
  } else if (id === "pmi-cn") data = fromCnPmi(overview.data, !compact ? macroHistory.data?.series.pmi : undefined);
  else if (id === "wei") data = fromUsMacro(usMacro.data, "wei", !compact);

  const secondaryError = !compact && (ratesHistory.isError || valuationHistory.isError || macroHistory.isError || surveyHistory.isError || (id === "hy-oas" && usMacro.isError));
  return <>
    <Reading id={id} compact={compact} data={data} />
    {secondaryError && <p role="alert" className="ol-metric-error">历史趋势资料读取失败；上方读数仍按其单独来源显示。<button type="button" onClick={() => {
      if (ratesHistory.isError) void ratesHistory.refetch();
      if (valuationHistory.isError) void valuationHistory.refetch();
      if (macroHistory.isError) void macroHistory.refetch();
      if (surveyHistory.isError) void surveyHistory.refetch();
      if (usMacro.isError) void usMacro.refetch();
    }}>重试趋势</button></p>}
  </>;
}

/** One adapter per mounted observation. Collapsed catalogue rows mount no queries. */
export default function ObservationMetric({ id, compact = false }: { id: string; compact?: boolean }) {
  if ((HISTORICAL_CANDIDATE_IDS as readonly string[]).includes(id)) return <CandidateMetric id={id as HistoricalCandidateId} compact={compact} />;
  if (id === "nasdaq100-pe") return <div className="ol-reference-reading">
    <p><strong>{NASDAQ_VALUATION_SNAPSHOT.value.toFixed(2)}倍</strong> · {NASDAQ_VALUATION_SNAPSHOT.date} 公开快照</p>
    <p>公开表主要是年末读数，缺连续月度历史，暂不计算近10年分位。</p>
    <a href={VALUATION_SOURCES[id].url} target="_blank" rel="noreferrer">{VALUATION_SOURCES[id].source} ↗</a>
  </div>;
  if (id === "smallcap-turnover") return <SmallcapMetric compact={compact} />;
  if (id === "turnover-concentration") return <ConcentrationMetric compact={compact} />;
  if (id === "erp-cn" || id === "erp-us") return <ErpMetric id={id} compact={compact} />;
  if (id === "focus-momentum") return <FocusMetric compact={compact} />;
  if (id === "ofr-fsi" || id === "finra-margin" || id === "baker-wurgler" || id === "nfci" || id === "vxn") return <StaticMetric id={id} compact={compact} />;
  if (id === "cn-financing") return <FinancingMetric compact={compact} />;
  return <ApiMetric id={id} compact={compact} />;
}
