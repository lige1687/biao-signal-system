import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi } from "../../api/client";
import { seriesPoints, volatilityHistory } from "../market-style/marketRiskMetrics";
import { fromObservation, formatValue, type MetricPoint } from "../observation-library/metricData";
import {
  fromSmallcapSnapshot, parseSmallcapSnapshot, SMALLCAP_QUERY_KEY, SMALLCAP_URL,
} from "../observation-library/candidateData";
import { marketReferenceBands } from "../observation-library/marketReferenceBands";
import { innerErpRails } from "../observation-library/erpComparisonDisplay";
import { usErpBands } from "../observation-library/usErpBands";
import { PROJECTION_METRICS, useProjectionSource } from "../observation-library/projectionSources";
import { parseBreadth, type BreadthMarket } from "./adapters";
import ChartLegend, { CHART_COLORS } from "./ChartLegend";
import { INDICATOR_BY_ID, MICRO_INDICATORS } from "./indicatorCatalog";
import {
  breadthThumbnail, historyState, microThumbnail, microThumbnailId, thumbnailWindow,
  type ThumbnailReading,
} from "./indicatorThumbnailData";
import { parseIncrementObservation, SESSION_DIFFERENCE_COLOR } from "./incrementObservationData";
import { parseIndustryStructure } from "./industryStructureData";
import { INDUSTRY_TURNOVER_ID, INDUSTRY_TURNOVER_OPTIONS } from "./industryTurnoverOptions";
import { parseMicrostructure, type MicroPacket } from "./microstructureData";
import MiniTrend from "./MiniTrend";
import { EtfPriceHeatThumbnail } from "./EtfPriceHeatObservation";
import { parseRelativeObservationSnapshot, relativeObservationReading, RELATIVE_OBSERVATION_CARDS } from "./relativeObservationData";
import { isSectorStructure } from "./SectorStructureCard";
import { isEarningsRevisionSamples } from "./EarningsRevisionSampleCard";
import { isStarWeightedBreadth } from "../market-style/StarWeightedBreadthSnapshot";

const fiveMinutes = 5 * 60_000;
const microIds = new Set(MICRO_INDICATORS.map(({ id }) => id));
const relativeIds = new Set<string>(RELATIVE_OBSERVATION_CARDS.map(({ id }) => id));
const projectedIds = new Set(PROJECTION_METRICS.map(({ id }) => id));

async function readJson(url: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal, cache: "no-cache" });
  if (!response.ok) throw new Error("观察资料暂不可读");
  return response.json();
}

function Loading({ pending, failed }: { pending?: boolean; failed?: boolean }) {
  return <p className="mit-state" role="status">{failed ? "资料暂不可读。" : pending ? "正在读取小图…" : "暂无可绘历史。"}</p>;
}

function Thumbnail({ data, label, showScale = false }: { data: ThumbnailReading; label: string; showScale?: boolean }) {
  const chart = data.chart && thumbnailWindow(data.chart);
  const history = chart ? historyState(chart.lines) : "empty";
  return <>
    <p className="mit-reading"><strong>{data.value}</strong>{data.date && <> · <time dateTime={data.date.replace(" ", "T")}>{data.date}</time></>}
      {data.note && <small> · {data.note}</small>}</p>
    {chart && history === "chart" ? <>
      {(chart.lines.length > 1 || chart.references?.length) ? <ChartLegend items={[
        ...chart.lines.map((line) => ({ label: line.name, color: line.color })),
        ...(chart.references ?? []).map((line) => ({ label: line.name, color: line.color, dashed: line.dashed !== false })),
      ]} /> : null}
      <MiniTrend {...chart} label={label} showScale={showScale} />
    </> : <p className="mit-state">{
      history === "disconnected" ? "有效读数不连续，暂无法绘制曲线。"
        : history === "snapshot" ? "仅有一条有效读数，暂无历史曲线。" : "暂无可绘历史。"
    }</p>}
  </>;
}

function pointChart(points: readonly MetricPoint[], name: string, color: string = CHART_COLORS.primary) {
  return {
    dates: points.map((point) => point.date),
    lines: [{ name, color, values: points.map((point) => point.value) }],
  };
}

function BreadthThumbnail({ market, label, showScale }: { market: BreadthMarket; label: string; showScale?: boolean }) {
  const query = useQuery({
    queryKey: ["homeObservationBreadth", market, 90],
    queryFn: async ({ signal }) => parseBreadth(await readJson(
      `/api/market-context/breadth-history?market_id=${market}&lookback_days=90&include_observation=true`, signal), market),
    staleTime: fiveMinutes, retry: false,
  });
  if (query.isPending || query.isError) return <Loading pending={query.isPending} failed={query.isError} />;
  return <Thumbnail data={breadthThumbnail(market, query.data)} label={`${label} · 50日宽度历史高低参考`} showScale={showScale} />;
}

function ErpThumbnail({ id, label, showScale }: { id: "erp-cn" | "erp-us"; label: string; showScale?: boolean }) {
  const source = useProjectionSource(id);
  const rows = useMemo(() => {
    try { return id === "erp-us" ? usErpBands(source.points) : source.bands ?? []; }
    catch { return null; }
  }, [id, source.points, source.bands]);
  if (source.error || source.isPending || !rows) return <Loading pending={source.isPending} failed={!!source.error || !rows} />;
  const latest = rows[rows.length - 1];
  const inner = rows.map(innerErpRails);
  return <Thumbnail showScale={showScale} label={`${label} · 近90条及1.5/2倍标准差参考轨道`} data={{
    value: formatValue(latest?.value ?? null, "个百分点"), date: latest?.date,
    note: id === "erp-cn" ? "周频历史" : "盈利端月频",
    chart: {
      ...pointChart(rows, "股债利差"),
      references: [
        { name: "2σ上轨", color: CHART_COLORS.low, values: rows.map((row) => row.upper) },
        { name: "2σ下轨", color: CHART_COLORS.high, values: rows.map((row) => row.lower) },
        { name: "1.5σ上轨", color: showScale ? CHART_COLORS.low : "#73a89f", dashed: showScale ? false : undefined, values: inner.map((row) => row.upper) },
        { name: "1.5σ下轨", color: showScale ? CHART_COLORS.high : "#bc9974", dashed: showScale ? false : undefined, values: inner.map((row) => row.lower) },
      ],
    },
  }} />;
}

function ProjectionThumbnail({ id, label }: { id: string; label: string }) {
  const source = useProjectionSource(id);
  if (source.error || source.isPending) return <Loading pending={source.isPending} failed={!!source.error} />;
  const latest = source.points[source.points.length - 1];
  const reference = marketReferenceBands(id, source.points);
  return <Thumbnail label={`${label} · ${source.unit || "历史读数"}`} data={{
    value: formatValue(latest?.value ?? null, source.unit), date: latest?.date,
    chart: {
      ...pointChart(source.points, label),
      references: reference ? [
        { name: reference.lowerLabel, color: CHART_COLORS.low, values: reference.rows.map((row) => row.lower) },
        { name: reference.upperLabel, color: CHART_COLORS.high, values: reference.rows.map((row) => row.upper) },
      ] : id === "nfci" ? [
        { name: "0 · 长期平均", color: "#9b7953", values: source.points.map(() => 0) },
      ] : undefined,
    },
  }} />;
}

function MicroThumbnail({ id, label, sample }: { id: string; label: string; sample?: string }) {
  const query = useQuery({
    queryKey: ["microstructureObservationPacketsV1"],
    queryFn: ({ signal }) => Promise.all(["funding", "equity", "derivatives"].map(async (branch) => {
      try {
        const data = parseMicrostructure(await readJson(`/research/microstructure-observations-20261108/${branch}.json`, signal));
        return { branch, data, failed: false };
      } catch {
        return { branch, data: null as MicroPacket | null, failed: true };
      }
    })),
    staleTime: 60_000, refetchOnWindowFocus: true,
  });
  const card = query.data?.flatMap(({ data }) => data?.cards ?? []).find((entry) => entry.id === microThumbnailId(id));
  if (!card) {
    const missing = query.data?.flatMap(({ data }) => data?.unavailable ?? []).find((entry) => entry.id === microThumbnailId(id));
    if (missing) return <p className="mit-state">{missing.reason}</p>;
    return <Loading pending={query.isPending} failed={query.isError || query.data?.some(({ failed }) => failed)} />;
  }
  const data = microThumbnail(card);
  if (id === "turnover-concentration") data.note = `日频 · 前5% · ${data.note ?? ""}`;
  if (sample) data.note = `${sample} · ${data.note ?? ""}`;
  return <Thumbnail data={data} label={`${label}${id === "turnover-concentration" ? " · 日频前5%" : ""} · ${card.unit}`} />;
}

function RelativeThumbnail({ id, label }: { id: string; label: string }) {
  const query = useQuery({
    queryKey: ["relativeObservationSnapshotV1"],
    queryFn: async ({ signal }) => parseRelativeObservationSnapshot(await readJson("/research/relative-market-observations-20261108/data.json", signal)),
    staleTime: fiveMinutes, retry: false,
  });
  const card = query.data?.cards.find((entry) => entry.id === id);
  if (!card) return <Loading pending={query.isPending} failed={query.isError} />;
  const { latest, value } = relativeObservationReading(card);
  return <Thumbnail label={`${label} · 比值`} data={{
    value, date: latest.date, note: "历史快照",
    chart: {
      ...pointChart(card.points.map((point) => ({ date: point.date, value: point.ratio })), "实际比值", "#28629e"),
      references: [{ name: card.kind === "term" ? "1倍 · 两者相同" : "60日均线", color: "#67747e",
        values: card.points.map((point) => card.kind === "term" ? 1 : point.ma60) }],
    },
  }} />;
}

function VolatilityThumbnail({ market, label }: { market: "cn" | "us"; label: string }) {
  const query = useQuery({
    queryKey: ["fundOverlay", 20], queryFn: () => fundamentalsApi.overlayHistory(20), staleTime: fiveMinutes, retry: false,
  });
  const price = query.data?.series[market === "cn" ? "sse" : "sp500"];
  const rows = useMemo(() => volatilityHistory(price?.dates ?? [], price?.values ?? []), [price]);
  if (query.isPending || query.isError) return <Loading pending={query.isPending} failed={query.isError} />;
  const latest = rows[rows.length - 1];
  return <Thumbnail label={`${label} · 年化百分比`} data={{
    value: `20日 ${formatValue(latest?.hv20 ?? null, "%")} / 60日 ${formatValue(latest?.hv60 ?? null, "%")}`, date: latest?.date,
    chart: {
      dates: rows.map((point) => point.date),
      lines: [
        { name: "20日", color: CHART_COLORS.primary, values: rows.map((point) => point.hv20) },
        { name: "60日", color: CHART_COLORS.secondary, values: rows.map((point) => point.hv60) },
      ],
    },
  }} />;
}

type RiskSupplement = { series?: Record<string, { points: MetricPoint[]; unit: string; snapshotTime?: string }> };
function Dr007Thumbnail({ label }: { label: string }) {
  const query = useQuery({
    queryKey: ["crossMarketRiskSupplement", "20261102-v2"],
    queryFn: async ({ signal }) => await readJson("/research/cross-market-risk-context-20261102/supplement-v2.json", signal) as RiskSupplement,
    staleTime: fiveMinutes, retry: false,
  });
  const series = query.data?.series?.dr007;
  const latest = series?.points[series.points.length - 1];
  if (!series || !latest) return <Loading pending={query.isPending} failed={query.isError} />;
  return <Thumbnail label={label} data={{
    value: latest.value == null ? "暂无可核读数" : `${latest.value.toFixed(4)}${series.unit}`,
    date: series.snapshotTime ?? latest.date, note: "历史快照",
    chart: pointChart(series.points, label),
  }} />;
}

function FinancingThumbnail() {
  const query = useQuery({
    queryKey: ["fundamentalsRatesHistory", 7300], queryFn: () => fundamentalsApi.ratesHistory(7300),
    staleTime: 30 * 60_000, retry: false,
  });
  const funding = useQuery({
    queryKey: ["microstructureFundingPacketV1"],
    queryFn: async ({ signal }) => await readJson("/research/microstructure-observations-20261108/funding.json", signal) as {
      cards?: { id: string; points: MetricPoint[]; lines?: { key: string; values: (number | null)[] }[] }[];
    },
    staleTime: 30 * 60_000, retry: false,
  });
  const balance = seriesPoints(query.data?.series.margin_rzyezb);
  const latestBalance = balance[balance.length - 1];
  const mainFunding = funding.data?.cards?.find((card) => card.id === "cn-margin-buy-share-a-stocks");
  const buy = mainFunding?.points ?? [];
  const ma20Line = mainFunding?.lines?.find((line) => line.key === "ma20")?.values;
  const ma20 = ma20Line
    ? buy.map((point, index) => ({ date: point.date, value: ma20Line[index] ?? null }))
    : funding.data?.cards?.find((card) => card.id === "cn-margin-buy-share-a-stocks-ma20")?.points ?? [];
  if (query.isPending || funding.isPending) return <Loading pending failed={false} />;
  if (query.isError && funding.isError) return <Loading pending={false} failed />;
  if (buy.length >= 2) {
    const balanceByDate = new Map(balance.map((point) => [point.date, point.value]));
    const ma20ByDate = new Map(ma20.map((point) => [point.date, point.value]));
    const latest = buy[buy.length - 1];
    return <Thumbnail label="A股两融三合一 · 买入额/成交额 + 20日均值 + 余额/流通市值" data={{
      value: `买入占比 ${formatValue(latest.value, "%")} · 余额占比 ${formatValue(balanceByDate.get(latest.date) ?? null, "%")}`,
      date: latest.date, note: "融资余额占比为同日读数",
      chart: {
        dates: buy.map((point) => point.date),
        lines: [
          { name: "融资买入额占成交额", color: CHART_COLORS.primary, values: buy.map((point) => point.value) },
          { name: "20日均值", color: CHART_COLORS.secondary, values: buy.map((point) => ma20ByDate.get(point.date) ?? null) },
          { name: "融资余额占流通市值", color: "#327c72", values: buy.map((point) => balanceByDate.get(point.date) ?? null) },
        ],
      },
    }} />;
  }
  return <Thumbnail label="A股融资余额占流通市值比 · 百分比" data={{
    value: `融资余额占流通市值 ${formatValue(latestBalance?.value ?? null, "%")}`, date: latestBalance?.date,
    note: "融资买入占比历史未取得",
    chart: pointChart(balance, "融资余额占流通市值"),
  }} />;
}

function IncrementThumbnail({ id, label }: { id: string; label: string }) {
  const query = useQuery({
    queryKey: ["incrementObservationCnV1"],
    queryFn: async ({ signal }) => parseIncrementObservation(await readJson("/research/market-increment-observations/cn.v1.json", signal)),
    staleTime: fiveMinutes, retry: false,
  });
  if (query.isPending || query.isError) return <Loading pending={query.isPending} failed={query.isError} />;
  if (id === "cn-institution") {
    const source = query.data.institutional_disclosure;
    return <Thumbnail label={label} data={{
      value: `披露机构净额 ${formatValue(source.net_yuan / 1e8, "亿元")}`, date: source.asof, note: "单日披露",
    }} />;
  }
  const source = query.data.session;
  return <Thumbnail label={`${label} · 百分点`} data={{
    value: `日内－隔夜 ${formatValue(source.latest.diff20_pp, "个百分点")}`, date: source.asof, note: "历史快照",
    chart: {
      dates: source.points.map((point) => point.date),
      lines: [
        { name: "隔夜", color: CHART_COLORS.primary, values: source.points.map((point) => point.overnight20_pp) },
        { name: "日内", color: CHART_COLORS.secondary, values: source.points.map((point) => point.intraday20_pp) },
        { name: "日内－隔夜", color: SESSION_DIFFERENCE_COLOR, values: source.points.map((point) => point.diff20_pp) },
      ],
      references: [{ name: "0 · 涨跌分界", color: CHART_COLORS.zero, values: source.points.map(() => 0) }],
    },
  }} />;
}

function IndustryThumbnail() {
  const query = useQuery({
    queryKey: ["industryStructureCnV1"],
    queryFn: async ({ signal }) => parseIndustryStructure(await readJson("/research/industry-structure/cn.v1.json", signal)),
    staleTime: fiveMinutes, retry: false,
  });
  if (query.isPending || query.isError) return <Loading pending={query.isPending} failed={query.isError} />;
  const { latest, history } = query.data;
  return <Thumbnail label="沪深300十行业涨跌同步程度 · 相关系数" data={{
    value: `同步程度 ${formatValue(latest.correlation, "")} · 分化 ${formatValue(latest.dispersion5, "个百分点")}`,
    date: latest.date, note: "历史快照 · 图示同步程度",
    chart: pointChart(history.map((point) => ({ date: point.date, value: point.correlation })), "同步程度"),
  }} />;
}

function SnapshotThumbnail({ id, label }: { id: "smallcap-turnover" | "vxn"; label: string }) {
  const smallcap = useQuery({
    queryKey: SMALLCAP_QUERY_KEY,
    queryFn: async ({ signal }) => parseSmallcapSnapshot(await readJson(SMALLCAP_URL, signal)),
    enabled: id === "smallcap-turnover", staleTime: Infinity, retry: false, refetchOnWindowFocus: false,
  });
  const vxn = useQuery({
    queryKey: ["fundamentalsObservations", "us"],
    queryFn: () => fundamentalsApi.observations("us"),
    enabled: id === "vxn", staleTime: fiveMinutes, retry: false,
  });
  const query = id === "vxn" ? vxn : smallcap;
  if (query.isPending || query.isError) return <Loading pending={query.isPending} failed={query.isError} />;
  const snapshot = id === "smallcap-turnover"
    ? smallcap.data && fromSmallcapSnapshot(smallcap.data)
    : fromObservation(vxn.data?.items.find((row) => row.metric_id === "vxn"));
  if (!snapshot) return <Loading />;
  return <Thumbnail label={label} data={{
    value: formatValue(snapshot.value, snapshot.unit), date: snapshot.date ?? undefined, note: "单次快照",
  }} />;
}

const researchIds = new Set(["star-breadth", "star-weighted-breadth", "sector-breadth", "sector-margin-share", "earnings-revision-samples"]);
function ResearchThumbnail({ id, label }: { id: string; label: string }) {
  const file = id === "star-breadth" ? "star-breadth-20261115.json" : id === "star-weighted-breadth" ? "star-weighted-breadth-20261030.json"
    : id === "earnings-revision-samples" ? "earnings-revisions-20261115.json" : "sector-structure-20261115.json";
  const q = useQuery({ queryKey: ["researchCardThumbnail", file], queryFn: ({ signal }) => readJson(`/research/${file}`, signal), staleTime: fiveMinutes, retry: false });
  if (q.isPending || q.isError) return <Loading pending={q.isPending} failed={q.isError} />;
  if (id === "earnings-revision-samples") {
    if (!isEarningsRevisionSamples(q.data)) return <Loading failed />;
    return <p className="mit-reading"><strong>{q.data.sampleStocks}家公司 · {q.data.verifiedReports}份原研报</strong><time>{q.data.retrievalDate}</time><small>2027E同团队版本，点开查看</small></p>;
  }
  if (id === "star-weighted-breadth") {
    if (!isStarWeightedBreadth(q.data)) return <Loading failed />;
    const r = q.data.indices[0].readings.find(x => x.period === 50)!;
    return <><p className="mit-reading"><strong>科创50 · 50日同日对照</strong><time>{q.data.observationDate}</time></p>
      <svg viewBox="0 0 260 54" role="img" aria-label={`科创50数量宽度${r.countPct.toFixed(1)}%，权重宽度${r.weightedPct.toFixed(1)}%，横轴0至100%`}>
        <text x="52" y="9" fontSize="9" fill="#6b786e">0</text><text x="211" y="9" fontSize="9" fill="#6b786e">100%</text>
        {[{ name: "数量", value: r.countPct, color: "#2860a3" }, { name: "权重", value: r.weightedPct, color: "#28806e" }].map((v, i) => <g key={v.name}>
          <text x="0" y={26 + i * 22} fontSize="11" fill={v.color}>{v.name}</text><rect x="52" y={17 + i * 22} width="170" height="10" fill="#edf1ed" />
          <rect x="52" y={17 + i * 22} width={1.7 * v.value} height="10" fill={v.color} /><text x="228" y={26 + i * 22} fontSize="10" fill="#4d6053">{v.value.toFixed(1)}%</text>
        </g>)}
      </svg></>;
  }
  let points: { date: string; value: number | null }[], name: string, asOf: string, note: string;
  if (id === "sector-breadth" || id === "sector-margin-share") {
    if (!isSectorStructure(q.data)) return <Loading failed />;
    const b = q.data.boards[0]; name = b.name;
    if (id === "sector-margin-share") {
      const rows = b.margin?.points;
      if (!rows?.length) return <Loading failed />;
      const last = rows[rows.length - 1];
      return <Thumbnail label={`${name}已披露融资买入占行业成交`} data={{ value: `${last.percent.toFixed(2)}%`, date: last.date,
        note: `${name} · 明细${last.reportedCount}/${last.total}只`, chart: pointChart(rows.map(x => ({ date: x.date, value: x.percent })), "已披露融资 / 行业成交") }} />;
    }
    points = b.breadth.observations.map(x => ({ date: x.date, value: x.windows["50"].percent })); asOf = q.data.asOf; note = `${name} · 50日固定池宽度`;
  } else {
    const d = q.data as { asOf?: string; indices?: { name: string; observations: { date: string; windows: Record<string, { percent: number | null }> }[] }[] };
    const b = d?.indices?.[0];
    if (!d.asOf || !b?.observations?.length || !b.observations.every(x => typeof x.date === "string" && x.windows?.["50"] && (x.windows["50"].percent === null || Number.isFinite(x.windows["50"].percent)))) return <Loading failed />;
    name = b.name; points = b.observations.map(x => ({ date: x.date, value: x.windows["50"].percent })); asOf = d.asOf; note = `${name} · 50日固定池宽度`;
  }
  const valid = points.map(x => x.value).filter((v): v is number => v !== null && Number.isFinite(v));
  const last = points[points.length - 1].value;
  const references = valid.length ? [...new Set([Math.min(...valid), Math.max(...valid)])].map((v, i) => ({ name: `本段${i ? "高" : "低"} ${v.toFixed(1)}%`, color: "#829485", values: points.map(() => v), dashed: true })) : [];
  return <Thumbnail showScale label={`${label} · ${name}50日宽度`} data={{ value: last === null ? "不足" : `${last.toFixed(1)}%`, date: asOf, note,
    chart: { ...pointChart(points, "50日", "#2563eb"), percent: true, references } }} />;
}

function ThumbnailContent({ id, label, showScale }: { id: string; label: string; showScale?: boolean }) {
  if (researchIds.has(id)) return <ResearchThumbnail id={id} label={label} />;
  if (id === "etf-price-heat") return <EtfPriceHeatThumbnail />;
  if (id === INDUSTRY_TURNOVER_ID) {
    const industry = INDUSTRY_TURNOVER_OPTIONS[0];
    return <MicroThumbnail id={industry.id} label={`${industry.label}日换手率`} sample={industry.label} />;
  }
  if (id === "turnover-concentration" || microIds.has(id)) return <MicroThumbnail id={id} label={label} />;
  if (id === "breadth-cn" || id === "breadth-us") return <BreadthThumbnail market={id === "breadth-cn" ? "CN_ALL_A" : "SP500"} label={label} showScale={showScale} />;
  if (id === "erp-cn" || id === "erp-us") return <ErpThumbnail id={id} label={label} showScale={showScale} />;
  if (relativeIds.has(id)) return <RelativeThumbnail id={id} label={label} />;
  if (id === "hv-cn" || id === "hv-us") return <VolatilityThumbnail market={id === "hv-cn" ? "cn" : "us"} label={label} />;
  if (id === "dr007") return <Dr007Thumbnail label={label} />;
  if (id === "cn-financing") return <FinancingThumbnail />;
  if (id === "cn-session" || id === "cn-institution") return <IncrementThumbnail id={id} label={label} />;
  if (id === "industry-structure-cn") return <IndustryThumbnail />;
  if (id === "smallcap-turnover") return <SnapshotThumbnail id={id} label={label} />;
  if (projectedIds.has(id)) return <ProjectionThumbnail id={id} label={label} />;
  return <Loading />;
}

export default function IndicatorThumbnail({ id, showScale = false }: { id: string; showScale?: boolean }) {
  const item = INDICATOR_BY_ID.get(id);
  return <div className="mit-thumbnail">
    {item?.readable ? <ThumbnailContent key={id} id={id} label={item.label} showScale={showScale} /> : <Loading />}
  </div>;
}
