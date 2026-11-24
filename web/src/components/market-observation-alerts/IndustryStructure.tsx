import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { CHART_COLORS } from "./ChartLegend";
import IndustryTimeline from "./IndustryTimeline.tsx";
import { isIndustrySnapshotOld, parseIndustryStructure, type IndustryStructureSnapshot } from "./industryStructureData";
import "./industry-structure.css";

const URL = "/research/industry-structure/cn.v1.json";
const percent = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
const todayShanghai = () => {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const field = (name: string) => parts.find((part) => part.type === name)?.value ?? "";
  return `${field("year")}-${field("month")}-${field("day")}`;
};

function Ranking({ snapshot }: { snapshot: IndustryStructureSnapshot }) {
  const rows = snapshot.latest.rankings;
  const max = Math.max(...rows.map((row) => Math.abs(row.return20)), 1);
  return <section className="is-ranking" aria-label="十行业过去20日价格涨跌排行">
    <div className="is-ranking-head"><h4>行业近20日涨跌</h4><span>上涨 {snapshot.latest.up20_count}/10</span></div>
    <div className="is-ranking-list">{rows.map((row, index) => <div className="is-rank" key={row.code}>
      <span className="is-rank-no">{index + 1}</span><span className="is-rank-name">{row.name}</span>
      <span className="is-rank-track"><i style={{ left: `${row.return20 >= 0 ? 50 : 50 - Math.abs(row.return20) / max * 50}%`,
        width: `${Math.abs(row.return20) / max * 50}%`, background: row.return20 >= 0 ? CHART_COLORS.low : CHART_COLORS.high }} /></span>
      <strong className={row.return20 >= 0 ? "is-positive" : "is-negative"}>{percent(row.return20)}</strong>
    </div>)}</div>
    <p className="is-ranking-note">各行业价格指数过去20个交易日涨跌，不含分红。</p>
  </section>;
}

function IndustryDetail({ snapshot, onClose }: { snapshot: IndustryStructureSnapshot; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const element = dialog.current;
    if (!element) return;
    element.showModal();
    setReady(true);
    return () => { element.close(); if (trigger?.isConnected) trigger.focus({ preventScroll: true }); };
  }, []);
  return createPortal(<dialog ref={dialog} className="is-dialog" aria-labelledby="is-dialog-title"
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="is-dialog-surface"><header><div><h2 id="is-dialog-title">沪深300十行业 · 同步与分化</h2><p>历史快照截至 {snapshot.asOf} · 拖动时间范围可查看完整历史</p></div>
      <button type="button" onClick={onClose}>关闭 ×</button></header>
      <div className="is-detail-grid">
        <div className="is-detail-timeline">{ready && <IndustryTimeline snapshot={snapshot} large />}</div>
        <Ranking snapshot={snapshot} />
      </div>
      <p className="is-source">范围：{snapshot.scope}。价格：{snapshot.source.priceName}；<a href={snapshot.source.classificationUrl} target="_blank" rel="noreferrer">行业分类来源</a>。资料未自动按日更新。</p>
    </div>
  </dialog>, document.body);
}

/** Standalone section for the A-share lane; the parent chooses its placement. */
export function IndustryStructureSection() {
  const [expanded, setExpanded] = useState(false);
  const query = useQuery({ queryKey: ["industryStructureCnV1"], queryFn: async ({ signal }) => {
    const response = await fetch(URL, { signal, cache: "no-cache" });
    if (!response.ok) throw new Error("行业资料读取失败");
    return parseIndustryStructure(await response.json());
  }, staleTime: 5 * 60_000, retry: false });
  const snapshot = query.data;
  const old = snapshot ? isIndustrySnapshotOld(snapshot.asOf, todayShanghai()) : false;
  return <section className="industry-structure" aria-label="A股行业结构观察">
    <header className="is-header"><div><h3>行业结构 · 沪深300十行业</h3></div>
      {snapshot && <button type="button" onClick={() => setExpanded(true)}>看完整大图 ↗</button>}</header>
    {query.isPending && <p className="is-status" role="status">行业历史读取中…</p>}
    {query.isError && <p className="is-status" role="alert">行业历史暂不可读。<button type="button" onClick={() => void query.refetch()}>重试</button></p>}
    {snapshot && <>
      <p className={old ? "is-date is-old" : "is-date"}>快照 {snapshot.asOf} · {old && "资料已过期；"}未自动按日更新 · 金融地产合一</p>
      <p className="is-reading">近20日 {snapshot.latest.up20_count}/10 行业上涨；行业同步相对{snapshot.latest.correlationPastPercentile < 50 ? "较弱" : snapshot.latest.correlationPastPercentile > 50 ? "较强" : "居中"}，分化高于近一年 {snapshot.latest.dispersion5PastPercentile.toFixed(0)}% 的日期。</p>
      <div className="is-home-layout"><IndustryTimeline snapshot={snapshot} /><Ranking snapshot={snapshot} /></div>
      <p className="is-source">价格：{snapshot.source.priceName}；<a href={snapshot.source.classificationUrl} target="_blank" rel="noreferrer">行业分类来源</a>。历史位置仅描述自身分布。</p>
    </>}
    {expanded && snapshot && <IndustryDetail snapshot={snapshot} onClose={() => setExpanded(false)} />}
  </section>;
}

export default IndustryStructureSection;
