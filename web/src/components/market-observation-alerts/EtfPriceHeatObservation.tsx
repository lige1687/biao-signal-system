import { useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import MarketTrendChart from "../market-style/MarketTrendChart";
import MiniTrend from "./MiniTrend";
import ChartLegend, { CHART_COLORS } from "./ChartLegend";
import { ETF_PRICE_HEAT_ID, ETF_PRICE_HEAT_URL, parseEtfPriceHeatSnapshot,
  type EtfHeatCard, type EtfHeatPoint, type EtfPriceHeatSnapshot } from "./etfPriceHeatData";
import "./increment-observation.css";
import "./relative-observation.css";
import "./etf-price-heat.css";

const TITLE = "ETF · 量价热度与分歧";
const HEAT = CHART_COLORS.high;
const ACTIVITY = CHART_COLORS.primary;
const PRICE = "#28629e";
const PERIODS = [120, 252, "all"] as const;
type Period = typeof PERIODS[number];
type MetricKey = "amountSharePct" | "relativeTurnover" | "turnoverSurge";
const METRICS: Record<MetricKey, { name: string; unit: string; digits: number }> = {
  amountSharePct: { name: "ETF成交额占沪深市场", unit: "%", digits: 3 },
  relativeTurnover: { name: "相对换手", unit: "倍", digits: 2 },
  turnoverSurge: { name: "5日/60日换手", unit: "倍", digits: 2 },
};
const fmt = (v: number | null, digits = 1, unit = "") => v == null ? "无数据" : `${v.toFixed(digits)}${unit}`;

function useSnapshot() {
  return useQuery({ queryKey: ["etfPriceHeatSnapshotV1"], queryFn: async ({ signal }) => {
    const response = await fetch(ETF_PRICE_HEAT_URL, { signal, cache: "no-cache" });
    if (!response.ok) throw new Error("ETF观察快照暂不可用");
    return parseEtfPriceHeatSnapshot(await response.json());
  }, staleTime: 5 * 60_000, retry: false });
}

function Reading({ point }: { point: EtfHeatPoint }) {
  return <>
    <p className="eph-main"><strong>{fmt(point.heat, 1, "分")}</strong><span>当前综合热度</span></p>
    <p className="eph-values"><span>成交活跃 <b>{fmt(point.activity, 1, "分")}</b></span>
      <span>较20日热度峰值回落 <b>{fmt(point.heatDrop20, 1, "分")}</b></span></p>
    <p className="eph-fact">20日收盘新高：{point.priceHigh20 == null ? "无数据" : point.priceHigh20 ? "是" : "否"}
      {point.divergence === true && " · 价热分歧已出现"}</p>
  </>;
}

function Detail({ card, snapshot, onClose, trigger }: { card: EtfHeatCard; snapshot: EtfPriceHeatSnapshot;
  onClose: () => void; trigger: HTMLButtonElement | null }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const metricId = useId();
  const [ready, setReady] = useState(false);
  const [period, setPeriod] = useState<Period>(120);
  const [metric, setMetric] = useState<MetricKey>("amountSharePct");
  const points = useMemo(() => period === "all" ? card.points : card.points.slice(-period), [card.points, period]);
  const dates = useMemo(() => points.map(p => p.date), [points]);
  const latest = card.points[card.points.length - 1];
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    node.showModal(); setReady(true);
    return () => { node.close(); if (trigger?.isConnected) trigger.focus({ preventScroll: true }); };
  }, [trigger]);
  return createPortal(<dialog ref={dialog} className="io-dialog eph-dialog" aria-label={`${card.name}量价热度详情`}
    onCancel={e => { e.preventDefault(); onClose(); }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="io-dialog-surface">
      <header><h2>{card.name} · 量价热度</h2><button type="button" onClick={onClose}>关闭 ×</button></header>
      <p className="io-detail-lead">{latest.date} · 历史快照 · 综合热度{fmt(latest.heat, 1, "分")}</p>
      <Reading point={latest} />
      <p className="io-explain">价格触及20日收盘新高，且热度过去20日峰值≥75分、回落≥10分时记录价热分歧。记录的是价与热度不同步的状态。</p>
      <div className="io-period" role="group" aria-label="历史范围">{PERIODS.map(p =>
        <button key={p} type="button" aria-pressed={period === p} onClick={() => setPeriod(p)}>{p === "all" ? "全部" : `近${p}日`}</button>)}</div>
      <p className="io-range">{dates[0]} 至 {dates[dates.length - 1]} · 价格与分数分图显示</p>
      <h3>ETF价格</h3>
      {ready && <MarketTrendChart dates={dates} series={[{ name: "收盘价", color: PRICE, values: points.map(p => p.price) }]} unit="元" height={240} precision={3} />}
      <h3>综合热度与成交活跃</h3>
      {ready && <MarketTrendChart dates={dates} series={[
        { name: "综合热度", color: HEAT, values: points.map(p => p.heat) },
        { name: "成交活跃", color: ACTIVITY, values: points.map(p => p.activity) },
      ]} unit="分" height={260} precision={1} valueBounds={[0, 100]} />}
      <p className="eph-values"><span>成交额占沪深市场 <b>{fmt(latest.amountSharePct, 3, "%")}</b></span>
        <span>相对换手 <b>{fmt(latest.relativeTurnover, 2, "倍")}</b></span>
        <span>5日/60日换手 <b>{fmt(latest.turnoverSurge, 2, "倍")}</b></span></p>
      <div className="eph-metric-pick"><label htmlFor={metricId}>原始量能</label><select id={metricId} value={metric} onChange={e => setMetric(e.target.value as MetricKey)}>
        {Object.entries(METRICS).map(([key, value]) => <option key={key} value={key}>{value.name}</option>)}</select></div>
      {ready && <MarketTrendChart dates={dates} series={[{ name: METRICS[metric].name, color: CHART_COLORS.secondary,
        values: points.map(p => p[metric]) }]} unit={METRICS[metric].unit} height={220} precision={METRICS[metric].digits} />}
      <p className="io-explain">{card.turnoverComparison}。综合热度是多项量价指标的合成分数；成交活跃是ETF自身交易量能读数，两者都不是下跌概率。均线趋势不等于行业成分股宽度。</p>
      <details className="eph-evidence"><summary>热度如何计算</summary>
        <p>成交活跃分：ETF成交额占沪深市场、相对换手、5日/60日换手，各取最近60日历史排名后平均。市场成交额沿用缓存中的沪深两市指数合计代理口径。排名包含当日，至少36个有效值；分项不完整时留空。</p>
        <p>综合热度：35%成交活跃＋25%价格动能＋20%波动与涨跌日量能差异＋20%均线发散，再做5日指数平滑。它衡量量价状态，80分不等于历史前20%或80%下跌概率。</p>
      </details>
      <details className="eph-evidence"><summary>最近出现价热分歧的日期</summary>
        {card.points.some(p => p.divergence === true) ? <p>{card.points.filter(p => p.divergence === true).slice(-8).map(p => p.date).join("、")}。相邻触发日可能属于同一次行情。</p> : <p>当前历史中未记录到满足三项条件的日期。</p>}
      </details>
      <details className="eph-evidence"><summary>历史观察依据</summary><p>价热分歧后20日平均收益 {fmt(card.research.mean20, 2, "%")}；其他20日新高日为 {fmt(card.research.otherHighMean20, 2, "%")}。成熟触发日 {card.research.matureDays} 个，按20日间隔保留 {card.research.spacedEvents} 次，后续均值 {fmt(card.research.spacedMean20, 2, "%")}。历史已用于选择规则，未在独立新样本验证。</p></details>
      <p className="io-source">{snapshot.sourceLabel} · 截至 {snapshot.snapshotAsOf}。{snapshot.sourceNote} {snapshot.priceNote}</p>
    </div>
  </dialog>, document.body);
}

export default function EtfPriceHeatObservation({ onCollapse, page = false }: { onCollapse?: () => void; page?: boolean }) {
  const query = useSnapshot();
  const symbolId = useId();
  const [symbol, setSymbol] = useState("512480");
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const snapshot = query.data;
  const card = snapshot?.cards.find(c => c.symbol === symbol);
  const latest = card?.points[card.points.length - 1];
  const points = card?.points.slice(-120) ?? [];
  return <article className={`moa-item io-card ro-card eph-card${page ? " eph-page" : ""}`} data-overview-card={ETF_PRICE_HEAT_ID} data-tone="neutral" aria-label={TITLE}>
    <div className="moa-item-head"><h3>{TITLE}</h3></div>
    <div className="eph-selector"><label htmlFor={symbolId}>观察ETF</label><select id={symbolId} value={symbol} onChange={e => setSymbol(e.target.value)}>
      {snapshot?.cards.map(c => <option key={c.symbol} value={c.symbol}>{c.name} · {c.symbol}</option>) ?? <>
        <option value="512480">半导体 · 512480</option><option value="515880">通信 · 515880</option>
        <option value="159915">创业板 · 159915</option><option value="510300">沪深300 · 510300</option></>}
    </select></div>
    {card && latest ? <>
      <p className="ro-asof">{card.name} · 截至 {latest.date} · 历史快照</p>
      <Reading point={latest} />
      <ChartLegend items={[{ label: "综合热度 · 分", color: HEAT }, { label: "成交活跃 · 分", color: ACTIVITY }]} />
      <MiniTrend dates={points.map(p => p.date)} lines={[
        { name: "综合热度", color: HEAT, values: points.map(p => p.heat) },
        { name: "成交活跃", color: ACTIVITY, values: points.map(p => p.activity) },
      ]} label={`${card.name}近120日综合热度与成交活跃，单位均为分`} />
      <p className="io-scope-note">观察ETF自身交易与价格是否同步；热度是合成分数，非概率。</p>
      <p className="io-scope-note">{snapshot?.sourceLabel}。{snapshot?.sourceNote}</p>
      <footer><button ref={trigger} type="button" aria-haspopup="dialog" onClick={() => setOpen(true)}>看历史与口径</button>
        {onCollapse && <button type="button" onClick={onCollapse}>收起</button>}</footer>
      {open && snapshot && <Detail card={card} snapshot={snapshot} onClose={() => setOpen(false)} trigger={trigger.current} />}
    </> : <><p className="io-scope-note" role={query.isError ? "alert" : "status"}>
      {query.isError ? "历史快照读取失败，请稍后重试。" : query.isSuccess ? "这只ETF没有可用的历史快照。" : "历史快照读取中…"}</p>
      <footer>{query.isError && <button type="button" onClick={() => void query.refetch()}>重试</button>}
        {onCollapse && <button type="button" onClick={onCollapse}>收起</button>}</footer></>}
  </article>;
}

export function EtfPriceHeatThumbnail() {
  const { data, isError, isPending } = useSnapshot();
  const card = data?.cards.find(c => c.symbol === "512480");
  const points = card?.points.slice(-120) ?? [];
  const latest = points[points.length - 1];
  if (!latest) return <p className="mit-state" role="status">{isError ? "观察快照暂不可读。" : isPending ? "正在读取ETF观察…" : "半导体ETF暂无可用读数。"}</p>;
  return <div className="eph-thumbnail" aria-label="半导体ETF近120日量价热度缩略图">
    <p className="mit-reading"><strong>半导体ETF · 热度 {fmt(latest.heat, 1, "分")}</strong> · <time dateTime={latest.date}>{latest.date}</time></p>
    <ChartLegend items={[{ label: "综合热度 · 分", color: HEAT }, { label: "成交活跃 · 分", color: ACTIVITY }]} />
    <MiniTrend dates={points.map(p => p.date)} lines={[
      { name: "综合热度", color: HEAT, values: points.map(p => p.heat) },
      { name: "成交活跃", color: ACTIVITY, values: points.map(p => p.activity) },
    ]} label="半导体ETF近120日综合热度与成交活跃，单位均为分" />
  </div>;
}
