import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi } from "../../api/client";
import MiniTrend from "../market-observation-alerts/MiniTrend";
import { GROUP_LABELS, type ObservationEntry } from "./catalog";
import ObservationMetric from "./ObservationMetric";
import ObservationDetailDialog from "./ObservationDetailDialog";
import { formatValue, fromObservation } from "./metricData";
import { PROJECTION_METRICS, useProjectionSource } from "./projectionSources";
import { HOME_HISTORICAL_IDS, HOME_READINGS, summarizeHomeSeries } from "./homeCardModel";
import "./home-observation-cards.css";

function HistoryReading({ id }: { id: string }) {
  const source = useProjectionSource(id);
  const definition = PROJECTION_METRICS.find(row => row.id === id)!;
  const frequency = source.frequency ?? definition.frequency;
  const today = new Date().toISOString().slice(0, 10);
  const view = summarizeHomeSeries(id, source.points, today);
  if (source.isPending) return <p className="hoc-unavailable" role="status">资料读取中…</p>;
  if (source.error || view.invalid) return <p className="hoc-unavailable" role="alert">{view.invalid ? "资料日期异常，暂不显示读数" : "资料读取失败"}<button type="button" onClick={source.retry}>重试</button></p>;
  const points = view.points.slice(frequency === "weekly" ? -52 : -120);
  const dateDay = view.date?.length === 7 ? `${view.date}-01` : view.date;
  // A recency notice, not a financial threshold or a claim of freshness.
  const old = dateDay && (Date.parse(today) - Date.parse(dateDay)) / 86400000 > (frequency === "monthly" ? 100 : frequency === "weekly" ? 35 : 14);
  return <>
    <div className="hoc-reading"><strong>{formatValue(view.value, source.unit)}</strong>
      <span>{view.change !== null ? `${view.change > 0 ? "+" : ""}${formatValue(view.change, source.unit === "%" ? "百分点" : source.unit)}` : view.value === null ? "暂无有效读数" : ""}</span></div>
    <p className="hoc-date">{frequency === "monthly" ? "所属月" : "资料日"} {view.date ?? "未核"}{view.change !== null && ` · 较 ${view.previousDate}`}</p>
    {old && <p className="hoc-age">较早资料 · 当前值未核</p>}
    <MiniTrend dates={points.map(row => row.date)} lines={[{ name: definition.label, color: "#527f9e", values: points.map(row => row.value) }]}
      label={`${definition.label}历史趋势，缺失处断线；${points[0]?.date ?? ""}至${points[points.length - 1]?.date ?? ""}`} />
  </>;
}

const FUNDING_URL = "/research/microstructure-observations-20261108/funding.json";
type FundingPoint = { date: string; value: number | null };
type FundingPacket = { cards?: { id: string; points: FundingPoint[] }[] };

function SnapshotReading({ id }: { id: "cn-financing" | "vxn" }) {
  const market = id === "cn-financing" ? "cn" : "us";
  const query = useQuery({ queryKey: ["fundamentalsObservations", market], queryFn: () => fundamentalsApi.observations(market), staleTime: 5 * 60_000, retry: false });
  const rates = useQuery({ queryKey: ["fundamentalsRatesHistory", 7300], queryFn: () => fundamentalsApi.ratesHistory(7300),
    enabled: id === "cn-financing", staleTime: 30 * 60_000, retry: false });
  const funding = useQuery({ queryKey: ["homeFinancingPacketV1"], queryFn: async () => {
    const response = await fetch(FUNDING_URL, { cache: "no-cache" });
    if (!response.ok) throw new Error("funding unavailable");
    return await response.json() as FundingPacket;
  }, enabled: id === "cn-financing", staleTime: 30 * 60_000, retry: false });
  if (query.isPending) return <p className="hoc-unavailable" role="status">资料读取中…</p>;
  if (query.isError) return <p className="hoc-unavailable" role="alert">资料读取失败<button type="button" onClick={() => { void query.refetch(); }}>重试</button></p>;
  const data = fromObservation(query.data?.items.find(row => row.metric_id === (id === "cn-financing" ? "margin_balance" : "vxn")));
  if (id === "vxn") {
    return <>
      <div className="hoc-reading"><strong>{formatValue(data?.value ?? null, data?.unit ?? "")}</strong></div>
      <p className="hoc-date">资料日 {data?.date ?? "未核"}{data?.change != null && ` · 较${data.comparisonPeriod ?? "前期"} ${data.change > 0 ? "+" : ""}${formatValue(data.change, data.changeUnit ?? data.unit)}`}</p>
      <div className="hoc-snapshot"><small>{data?.status ?? "尚无可核读数"}</small><small>VXN 为纳指100预期波动，不等于VIX</small></div>
    </>;
  }
  const buy = funding.data?.cards?.find(card => card.id === "cn-margin-buy-share-a-stocks")?.points ?? [];
  const ma20 = funding.data?.cards?.find(card => card.id === "cn-margin-buy-share-a-stocks-ma20")?.points ?? [];
  const balanceSeries = rates.data?.series.margin_rzyezb;
  const balance = balanceSeries && balanceSeries.dates.length === balanceSeries.values.length
    ? balanceSeries.dates.map((date, index) => ({ date, value: balanceSeries.values[index] })) : [];
  const latest = buy[buy.length - 1];
  if (buy.length < 2 || !latest) {
    return <>
      <div className="hoc-reading"><strong>{formatValue(data?.value ?? null, data?.unit ?? "")}</strong></div>
      <p className="hoc-date">资料日 {data?.date ?? "未核"}</p>
      <div className="hoc-snapshot"><small>{data?.status ?? "尚无可核读数"}</small><small>融资买入占比历史暂不可读</small></div>
    </>;
  }
  const previous = buy[buy.length - 2];
  const balanceByDate = new Map(balance.map(point => [point.date, point.value]));
  const ma20ByDate = new Map(ma20.map(point => [point.date, point.value]));
  const dates = buy.map(point => point.date);
  const change = previous && latest.value != null && previous.value != null ? latest.value - previous.value : null;
  return <>
    <div className="hoc-reading"><strong>{formatValue(latest.value, "%")}</strong>
      <span>{change === null ? "前一交易日资料不足" : `较前一交易日 ${change > 0 ? "+" : ""}${change.toFixed(2)}个百分点`}</span></div>
    <p className="hoc-date">资料日 {latest.date} · 融资余额占流通市值 {formatValue(balanceByDate.get(latest.date) ?? null, "%")}</p>
    <MiniTrend dates={dates} lines={[
      { name: "融资买入额占成交额", color: "#527f9e", values: buy.map(point => point.value) },
      { name: "20日均值", color: "#c0563b", values: dates.map(date => ma20ByDate.get(date) ?? null) },
      { name: "融资余额占流通市值", color: "#327c72", values: dates.map(date => balanceByDate.get(date) ?? null) },
    ]} label="A股两融三合一：融资买入额占成交额、20日均值、融资余额占流通市值；缺失处断线" />
  </>;
}

export default function HomeObservationCards({ items, onRemove }: { items: ObservationEntry[]; onRemove: (id: string) => void }) {
  const [active, setActive] = useState<ObservationEntry | null>(null);
  if (!items.length) return null;
  return <>
    <header className="hoc-heading"><h2>情绪与资金</h2><span>点击卡片看详细图表 · 在观察库增减</span></header>
    <div className="hoc-grid">{items.map(item => {
      const definition = PROJECTION_METRICS.find(row => row.id === item.id);
      const copy = HOME_READINGS[item.id];
      const frequency = definition?.frequency;
      const cadence = frequency === "monthly" ? "月度" : frequency === "weekly" ? "周度" : "日度";
      return <article className="hoc-card" key={item.id} data-observation-id={item.id}>
        <div className="hoc-kicker"><span>{item.market === "cn" ? "A股" : item.market === "us" ? "美股" : "跨市场"} · {copy?.dimension ?? GROUP_LABELS[item.group]}</span>
          <button type="button" className="hoc-remove" onClick={() => onRemove(item.id)} aria-label={`从首页收回：${item.label}`}>收回</button></div>
        <button type="button" className="hoc-title" aria-haspopup="dialog" onClick={() => setActive(item)}>{copy?.label ?? item.label}</button>
        <span className={`hoc-cadence${HOME_HISTORICAL_IDS.has(item.id) ? " is-history" : ""}`}>{HOME_HISTORICAL_IDS.has(item.id) ? `${item.id === "smallcap-turnover" ? "同日" : cadence}历史快照` : cadence}</span>
        <div className="hoc-data">{definition ? <HistoryReading id={item.id} /> : item.id === "cn-financing" || item.id === "vxn" ? <SnapshotReading id={item.id} /> : <ObservationMetric id={item.id} compact />}</div>
        <p className="hoc-reading-help">{copy?.reading ?? definition?.reading ?? item.meaning}</p>
        <button type="button" className="hoc-detail" aria-haspopup="dialog" onClick={() => setActive(item)} aria-label={`查看详情：${item.label}`}>{definition ? "价格与指标对照" : "查看读数与口径"}<span aria-hidden="true">↗</span></button>
      </article>;
    })}</div>
    {active && <ObservationDetailDialog key={active.id} item={active} onClose={() => setActive(null)} />}
  </>;
}
