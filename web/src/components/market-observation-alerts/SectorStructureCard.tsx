import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import MiniTrend from "./MiniTrend";
import { BREADTH_LINES } from "../trend/zones";
import "./sector-structure.css";

type Reading = { above: number; eligible: number; total: number; missing: number; percent: number | null };
type Observation = { date: string; windows: Record<string, Reading> };
type MarginPoint = { date: string; buyAmount: number; turnoverAmount: number; percent: number; reportedCount: number; denominatorCount: number; total: number };
type Board = { code: string; name: string; memberCount: number; memberRetrievedAt: string; sourceUrl?: string; breadth: { observations: Observation[] }; margin?: { basis: "disclosed-buy/full-sector-turnover"; points: MarginPoint[] } };
type Snapshot = { schemaVersion: 1; asOf: string; boards: Board[] };
const PERIODS = ["20", "50", "200"] as const;
const isDate = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v));
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function isSectorStructure(value: unknown): value is Snapshot {
  if (!value || typeof value !== "object") return false;
  const d = value as Snapshot;
  return d.schemaVersion === 1 && isDate(d.asOf) && Array.isArray(d.boards) && d.boards.length === 2
    && new Set(d.boards.map(b => b.code)).size === 2 && d.boards.every(b => {
      if (!["BK1036", "BK0448"].includes(b.code) || typeof b.name !== "string" || !Number.isInteger(b.memberCount) || b.memberCount <= 0
        || !isDate(b.memberRetrievedAt?.slice(0, 10)) || !Array.isArray(b.breadth?.observations) || !b.breadth.observations.length) return false;
      const rows = b.breadth.observations;
      if (rows[rows.length - 1].date !== d.asOf) return false;
      const valid = rows.every((row, i) => isDate(row.date) && (i === 0 || row.date > rows[i - 1].date) && PERIODS.every(period => {
        const w = row.windows?.[period];
        return w && [w.above, w.eligible, w.total, w.missing].every(Number.isInteger) && w.total === b.memberCount && w.above >= 0
          && w.above <= w.eligible && w.eligible <= w.total && w.missing === w.total - w.eligible
          && (w.eligible === 0 ? w.percent === null : finite(w.percent) && Math.abs(w.percent - 100 * w.above / w.eligible) < .015);
      }));
      if (!valid) return false;
      return !b.margin || b.margin.basis === "disclosed-buy/full-sector-turnover" && Array.isArray(b.margin.points) && b.margin.points.every((row, i) => isDate(row.date)
        && (i === 0 || row.date > b.margin!.points[i - 1].date) && [row.buyAmount, row.turnoverAmount, row.percent].every(finite)
        && row.buyAmount >= 0 && row.turnoverAmount > 0 && row.buyAmount <= row.turnoverAmount && row.total === b.memberCount
        && Number.isInteger(row.reportedCount) && row.reportedCount >= 0 && row.reportedCount <= row.total && row.denominatorCount === row.total
        && Math.abs(row.percent - 100 * row.buyAmount / row.turnoverAmount) < .015);
    });
}

export function SectorBreadthView({ board, asOf }: { board: Board; asOf: string }) {
  const rows = board.breadth.observations;
  const last = rows[rows.length - 1];
  const values50 = rows.map(r => r.windows["50"].percent).filter(finite);
  const bounds = values50.length ? [Math.min(...values50), Math.max(...values50)] : [];
  const references = bounds.length && bounds[1] - bounds[0] > 2 ? bounds.map((v, i) => ({
    name: `本段50日${i ? "最高" : "最低"}`, color: i ? "#a3825c" : "#398579", values: rows.map(() => v), dashed: true,
    endLabel: `50日${i ? "最高" : "最低"} ${v.toFixed(1)}%`,
  })) : [];
  return <>
    <p className="sector-date">{asOf} · 看多少股票站上自身均线</p>
    <div className="sector-values">{PERIODS.map((period, i) => {
      const v = last.windows[period];
      return <div key={period} style={{ borderColor: BREADTH_LINES[i].color }}><span>{period}日</span>
        <strong>{v.percent === null ? "不足" : `${v.percent.toFixed(1)}%`}</strong><small>{v.above}/{v.eligible}只{v.missing ? ` · 缺${v.missing}` : ""}</small></div>;
    })}</div>
    <div className="sector-legend">{PERIODS.map((period, i) => <span key={period} style={{ color: BREADTH_LINES[i].color }}>━ {period}日</span>)}</div>
    <MiniTrend percent showScale dates={rows.map(r => r.date)} label={`${board.name}固定名单数量宽度，0%至100%`}
      lines={PERIODS.map((period, i) => ({ name: `${period}日`, color: BREADTH_LINES[i].color, values: rows.map(r => r.windows[period].percent) }))} references={references} />
    <p className="sector-note">{board.memberCount}只沪深A股 · 东方财富名单{board.memberRetrievedAt.slice(5, 10)}取得，BaoStock价格；固定名单回看。</p>
  </>;
}

export default function SectorStructureCard({ mode = "breadth", onCollapse }: { mode?: "breadth" | "margin"; onCollapse: () => void }) {
  const [selected, setSelected] = useState("BK1036");
  const q = useQuery({ queryKey: ["sectorStructureSnapshot", "20261115"], queryFn: async ({ signal }) => {
    const response = await fetch("/research/sector-structure-20261115.json", { signal, cache: "no-cache" });
    if (!response.ok) throw new Error("unavailable");
    const data: unknown = await response.json();
    if (!isSectorStructure(data)) throw new Error("invalid");
    return data;
  }, staleTime: 60_000, retry: false });
  const board = q.data?.boards.find(b => b.code === selected);
  const margin = board?.margin?.points;
  const last = margin?.[margin.length - 1];
  const title = mode === "breadth" ? "半导体 / 通信 · 内部宽度" : "半导体 / 通信 · 已披露融资交易";
  return <article className="moa-item sector-structure-card" data-overview-card={mode === "breadth" ? "sector-breadth" : "sector-margin-share"} aria-label={title}>
    <div className="moa-item-head"><h3>{title}</h3><button type="button" onClick={onCollapse}>收起</button></div>
    <label className="sector-select">行业<select value={selected} onChange={event => setSelected(event.target.value)}>
      <option value="BK1036">半导体 · 沪深A股</option><option value="BK0448">通信设备 · 沪深A股</option>
    </select></label>
    {q.isPending && <p role="status">正在读取行业资料…</p>}
    {q.isError && <p role="alert">行业资料暂不可读。<button type="button" onClick={() => void q.refetch()}>重试</button></p>}
    {board && (mode === "breadth" ? <SectorBreadthView board={board} asOf={q.data!.asOf} /> : last && margin ? <>
      <div className="sector-margin-value"><strong>{last.percent.toFixed(2)}%</strong><time>{last.date}</time></div>
      <p className="sector-date">已披露融资买入额 / 行业全部股票成交额</p>
      {margin.length > 1 ? <MiniTrend dates={margin.map(p => p.date)} lines={[{ name: "已披露融资买入 / 行业成交", color: "#28629e", values: margin.map(p => p.percent) }]} label={`${board.name}已披露融资买入额占同池成交额`} /> : <p className="sector-note">当前只有单日资料，连续历史待补。</p>}
      <p className="sector-note">融资明细{last.reportedCount}/{last.total}只；其余股票资格未核，完整行业融资占比未知。按11-15固定名单回看。</p>
    </> : <p className="sector-note">同池融资明细与成交额尚未齐全。</p>)}
    {board?.sourceUrl && <a className="sector-source" href={board.sourceUrl} target="_blank" rel="noreferrer">东方财富行业资料 ↗</a>}
  </article>;
}
