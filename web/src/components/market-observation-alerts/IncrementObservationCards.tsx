import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import MarketTrendChart from "../market-style/MarketTrendChart";
import type { CandidateSummary } from "./CandidateShelf";
import ChartLegend, { CHART_COLORS } from "./ChartLegend";
import MiniTrend from "./MiniTrend";
import { parseIncrementObservation, sessionReading, signed, SESSION_DIFFERENCE_COLOR, type IncrementObservationSnapshot, type SessionPoint } from "./incrementObservationData";
import "./increment-observation.css";

const SOURCE = "/research/market-increment-observations/cn.v1.json";
const SESSION_ID = "cn-session";
const INSTITUTION_ID = "cn-institution";
const money = (yuan: number) => `${(Math.abs(yuan) / 1e8).toFixed(2)}亿元`;
const netMoney = (yuan: number) => `${yuan < 0 ? "−" : yuan > 0 ? "+" : ""}${money(yuan)}`;
const netLabel = (yuan: number) => yuan < 0 ? "净卖出" : yuan > 0 ? "净买入" : "买卖持平";
const sessionMeaning = (point: SessionPoint) => sessionReading(point);

function DetailDialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [ready, setReady] = useState(false);
  const trigger = useRef<HTMLElement | null>(null);
  useEffect(() => {
    trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const node = ref.current;
    if (!node) return;
    node.showModal();
    setReady(true);
    return () => { node.close(); if (trigger.current?.isConnected) trigger.current.focus({ preventScroll: true }); };
  }, []);
  return createPortal(<dialog ref={ref} className="io-dialog" aria-label={title}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="io-dialog-surface"><header><h2>{title}</h2><button type="button" onClick={onClose}>关闭 ×</button></header>
      {ready && children}
    </div>
  </dialog>, document.body);
}

function SessionDetail({ snapshot, onClose }: { snapshot: IncrementObservationSnapshot; onClose: () => void }) {
  const [period, setPeriod] = useState<120 | 252 | "all">(120);
  const source = snapshot.session;
  const points = useMemo(() => period === "all" ? source.points : source.points.slice(-period), [source.points, period]);
  const series = useMemo(() => [
    { name: "隔夜", color: CHART_COLORS.primary, values: points.map((row) => row.overnight20_pp) },
    { name: "日内", color: CHART_COLORS.secondary, values: points.map((row) => row.intraday20_pp) },
    { name: "日内－隔夜", color: SESSION_DIFFERENCE_COLOR, values: points.map((row) => row.diff20_pp) },
    { name: "0 · 基准线", color: CHART_COLORS.zero, values: points.map(() => 0) },
  ], [points]);
  return <DetailDialog title="沪深300 · 隔夜与日内表现" onClose={onClose}>
    <p className="io-detail-lead">{source.asof}：{sessionMeaning(source.latest)}。隔夜 {signed(source.latest.overnight20_pp)}、日内 {signed(source.latest.intraday20_pp)}、两段之差 <span data-session-difference style={{ color: SESSION_DIFFERENCE_COLOR }}>{signed(source.latest.diff20_pp)}</span> 个百分点。</p>
    <div className="io-period" role="group" aria-label="图表时间范围">{([120, 252, "all"] as const).map((range) => <button key={range} type="button" aria-pressed={period === range} onClick={() => setPeriod(range)}>{range === "all" ? "全部" : `近${range}日`}</button>)}</div>
    <p className="io-range">所选历史：{points[0]?.date} 至 {points[points.length - 1]?.date} · 拖动滑块或滚轮缩放</p>
    <MarketTrendChart dates={points.map((row) => row.date)} series={series} unit="百分点" height={360} />
    <p className="io-explain">隔夜、日内两线高于0表示近20日合计上涨，低于0表示合计下跌。灰色差值高于0表示日内表现强于隔夜，低于0表示隔夜表现更强。</p>
    <p className="io-explain">隔夜为开盘价 ÷ 前收盘价 − 1；日内为收盘价 ÷ 开盘价 − 1。两段各取过去20个交易日简单收益之和，差值为日内减隔夜。</p>
    <p className="io-source">用于区分价格变化发生在隔夜还是开盘后。价格：<a href={source.source_url} target="_blank" rel="noreferrer">腾讯行情 · 沪深300价格指数</a>，不含分红。快照截至 {source.asof}，未自动按日更新。<a href="/library?report=docs%2Fexperiments%2Fmarket-increment-three-modules-2026-11-03.md">查看指标与仓位研究</a></p>
  </DetailDialog>;
}

function SessionCard({ snapshot, onCollapse }: { snapshot: IncrementObservationSnapshot; onCollapse: () => void }) {
  const [open, setOpen] = useState(false);
  const data = snapshot.session;
  const last = data.latest;
  const rows = data.points.slice(-252);
  const prior = data.points[data.points.length - 21];
  return <article className="moa-item io-card" data-tone="neutral" data-overview-card={SESSION_ID} aria-label="沪深300隔夜与日内表现">
    <div className="moa-item-head"><h3>沪深300 · 隔夜与日内表现</h3><span className="moa-quality">历史快照</span></div>
    <p className="io-lead">{sessionMeaning(last)}</p>
    <div className="io-values"><div><span>隔夜 · 近20日</span><strong style={{ color: CHART_COLORS.primary }}>{signed(last.overnight20_pp)}</strong></div><div><span>日内 · 近20日</span><strong style={{ color: CHART_COLORS.secondary }}>{signed(last.intraday20_pp)}</strong></div><div><span>日内－隔夜</span><strong data-session-difference style={{ color: SESSION_DIFFERENCE_COLOR }}>{signed(last.diff20_pp)}</strong></div></div>
    <p className="io-unit">20日简单收益之和 · 百分点</p>
    <ChartLegend items={[{ label: "隔夜", color: CHART_COLORS.primary }, { label: "日内", color: CHART_COLORS.secondary }, { label: "0 · 涨跌分界", color: CHART_COLORS.zero, dashed: true }]} />
    <MiniTrend dates={rows.map((row) => row.date)} lines={[{ name: "隔夜", color: CHART_COLORS.primary, values: rows.map((row) => row.overnight20_pp) }, { name: "日内", color: CHART_COLORS.secondary, values: rows.map((row) => row.intraday20_pp) }]} references={[{ name: "0 · 涨跌分界", color: CHART_COLORS.zero, values: rows.map(() => 0), dashed: true, endLabel: "0" }]} label="沪深300近252个交易日隔夜与日内20日合计收益，灰线为零" />
    {prior && <p className="io-comparison">较 {prior.date}（20个交易日前）：两段之差 {signed(last.diff20_pp - prior.diff20_pp)} 个百分点。</p>}
    <p className="moa-card-meta">截至 {data.asof} · 未自动按日更新 · <a href={data.source_url} target="_blank" rel="noreferrer">腾讯行情</a></p>
    <footer><button type="button" onClick={() => setOpen(true)}>看大图 ↗</button><button type="button" onClick={onCollapse}>收起</button></footer>
    {open && <SessionDetail snapshot={snapshot} onClose={() => setOpen(false)} />}
  </article>;
}

type Institution = IncrementObservationSnapshot["institutional_disclosure"];
function InstitutionDetail({ data, onClose }: { data: Institution; onClose: () => void }) {
  const buys = [...data.rows].filter((row) => row.net_yuan > 0).sort((a, b) => b.net_yuan - a.net_yuan).slice(0, 5);
  const sells = [...data.rows].filter((row) => row.net_yuan < 0).sort((a, b) => a.net_yuan - b.net_yuan).slice(0, 5);
  const table = (rows: typeof buys, label: string) => <section className="io-ranking" aria-label={label}><h3>{label}</h3><ol>{rows.map((row) => <li key={row.code}><a href={row.source_url} target="_blank" rel="noreferrer">{row.name} <small>{row.code}</small></a><strong className={row.net_yuan > 0 ? "io-buy" : "io-sell"}>{netMoney(row.net_yuan)}</strong></li>)}</ol></section>;
  return <DetailDialog title="龙虎榜 · 已披露机构席位" onClose={onClose}>
    <p className="io-detail-lead">{data.asof}，本快照覆盖 {data.coverage.unique_stocks} 只上榜股票。披露范围内机构席位买入 {money(data.buy_yuan)}、卖出 {money(data.sell_yuan)}，{netLabel(data.net_yuan)} {money(data.net_yuan)}。</p>
    <div className="io-ranking-grid">{table(buys, "净买入前五")}{table(sells, "净卖出前五")}</div>
    <p className="io-explain">汇总当日龙虎榜披露的股票机构席位单日买卖额，剔除可转债和多日累计；净额为买入减卖出，所列股票按净额排序。范围覆盖当日上榜股票中的已披露机构席位，全A机构总量和散户买卖额待补。</p>
    <p className="io-source">来源：<a href={data.source_url} target="_blank" rel="noreferrer">东方财富 Choice 汇总</a>。<a href={data.exchange_scope_url} target="_blank" rel="noreferrer">上交所公开信息（沪市）</a>可用于核对沪市记录；当前逐席位原件待核。仅有 {data.asof} 单日快照，未自动按日更新。</p>
  </DetailDialog>;
}

function InstitutionCard({ data, onCollapse }: { data: Institution; onCollapse: () => void }) {
  const [open, setOpen] = useState(false);
  const max = Math.max(data.buy_yuan, data.sell_yuan, 1);
  return <article className="moa-item io-card" data-tone="neutral" data-overview-card={INSTITUTION_ID} aria-label="龙虎榜已披露机构席位">
    <div className="moa-item-head"><h3>龙虎榜 · 已披露机构席位</h3><span className="moa-quality">单日披露</span></div>
    <p className="io-scope">{data.asof} · 本快照覆盖 {data.coverage.unique_stocks} 只上榜股票</p>
    <p className="io-lead">披露范围内机构席位{data.net_yuan < 0 ? "卖出多于买入" : data.net_yuan > 0 ? "买入多于卖出" : "买卖持平"}</p>
    <div className="io-net-value"><span>{netLabel(data.net_yuan)}</span><strong>{(Math.abs(data.net_yuan) / 1e8).toFixed(2)}</strong><span>亿元</span></div>
    <div className="io-bars" aria-label={`买入${money(data.buy_yuan)}，卖出${money(data.sell_yuan)}`}>
      <div><span>买入</span><i><b className="io-bar-buy" style={{ width: `${data.buy_yuan / max * 100}%` }} /></i><strong>{money(data.buy_yuan)}</strong></div>
      <div><span>卖出</span><i><b className="io-bar-sell" style={{ width: `${data.sell_yuan / max * 100}%` }} /></i><strong>{money(data.sell_yuan)}</strong></div>
    </div>
    <p className="io-scope-note">看这 {data.coverage.unique_stocks} 只上榜股票已披露机构席位的买卖倾向；全A机构总量、散户买卖额待补。</p>
    <p className="moa-card-meta">来源：<a href={data.source_url} target="_blank" rel="noreferrer">Choice 汇总</a> · 逐席位交易所原件待核 · 未自动按日更新</p>
    <footer><button type="button" onClick={() => setOpen(true)}>看买卖明细 ↗</button><button type="button" onClick={onCollapse}>收起</button></footer>
    {open && <InstitutionDetail data={data} onClose={() => setOpen(false)} />}
  </article>;
}

export default function IncrementObservationCards({ selectedIds, collapsedIds, onCollapse, onSummary }: {
  selectedIds: readonly string[]; collapsedIds: readonly string[]; onCollapse: (id: string) => void;
  onSummary: (id: string, summary: CandidateSummary) => void;
}) {
  const selectedSession = selectedIds.includes(SESSION_ID);
  const selectedInstitution = selectedIds.includes(INSTITUTION_ID);
  const query = useQuery({ queryKey: ["incrementObservationCnV1"], enabled: selectedSession || selectedInstitution,
    queryFn: async ({ signal }) => { const response = await fetch(SOURCE, { signal, cache: "no-cache" }); if (!response.ok) throw new Error("观察资料读取失败"); return parseIncrementObservation(await response.json()); },
    staleTime: 5 * 60_000, retry: false });
  const snapshot = query.data;
  const session = snapshot?.session;
  const institution = snapshot?.institutional_disclosure;
  useEffect(() => {
    if (!selectedSession) return;
    onSummary(SESSION_ID, session ? { value: `隔夜 ${signed(session.latest.overnight20_pp)} / 日内 ${signed(session.latest.intraday20_pp)} 个百分点`, meaning: sessionMeaning(session.latest), date: session.asof } : { value: query.isError ? "读取失败" : "读取中", meaning: query.isError ? "资料暂不可读，可恢复卡片重试" : "历史快照读取中" });
  }, [selectedSession, session, query.isError, onSummary]);
  useEffect(() => {
    if (!selectedInstitution) return;
    onSummary(INSTITUTION_ID, institution ? { value: `${netLabel(institution.net_yuan)} ${money(institution.net_yuan)}`, meaning: `已披露机构席位，本快照覆盖${institution.coverage.unique_stocks}只上榜股票`, date: institution.asof } : { value: query.isError ? "读取失败" : "读取中", meaning: query.isError ? "资料暂不可读，可恢复卡片重试" : "单日披露读取中" });
  }, [selectedInstitution, institution, query.isError, onSummary]);
  const visibleSession = selectedSession && !collapsedIds.includes(SESSION_ID);
  const visibleInstitution = selectedInstitution && !collapsedIds.includes(INSTITUTION_ID);
  if (!visibleSession && !visibleInstitution) return null;
  if (query.isPending || query.isError) return <div className="io-status" role={query.isError ? "alert" : "status"}>
    {query.isError ? "增量观察资料暂不可读。" : "增量观察资料读取中…"}{query.isError && <button type="button" onClick={() => void query.refetch()}>重试</button>}
  </div>;
  return <>
    {visibleSession && <SessionCard snapshot={query.data} onCollapse={() => onCollapse(SESSION_ID)} />}
    {visibleInstitution && <InstitutionCard data={query.data.institutional_disclosure} onCollapse={() => onCollapse(INSTITUTION_ID)} />}
  </>;
}
