import { useState } from "react";
import { OBSERVATION_BY_ID } from "../observation-library/catalog";
import "./candidate-shelf.css";

export type CandidateSummary = { value: string; meaning: string; date?: string };
type Entry = { id: string; label: string };
type Market = "cn" | "us";
const marketFor = (id: string): Market => {
  if (id === "breadth-us" || id === "hv-us" || id === "erp-us" || ["vix", "hy-oas", "nfci", "finra-margin", "aaii",
    "vix-term-structure", "us-semiconductor-relative", "us-equal-weight-relative"].includes(id)) return "us";
  return OBSERVATION_BY_ID.get(id)?.market === "us" ? "us" : "cn";
};

export default function CandidateShelf({ market, entries, selectedIds, collapsedIds, summaries, onRestore, onAdd }: {
  market: Market; entries: readonly Entry[]; selectedIds: readonly string[]; collapsedIds: readonly string[];
  summaries: Readonly<Record<string, CandidateSummary>>;
  onRestore: (id: string) => void; onAdd: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const unique = [...new Map(entries.map((entry) => [entry.id, entry])).values()]
    .filter((entry) => entry.id === "earnings-revisions" || marketFor(entry.id) === market);
  const collapsed = unique.filter((entry) => selectedIds.includes(entry.id) && collapsedIds.includes(entry.id));
  const available = unique.filter((entry) => !selectedIds.includes(entry.id) && entry.label.toLowerCase().includes(search.trim().toLowerCase()));
  return <section className="moa-candidate-shelf" aria-label={`${market === "cn" ? "A股" : "美股"}收起的观察卡与候选`}>
    <div className="moa-shelf-head"><h4>收起的观察卡</h4><span>{collapsed.length} 项 · 随时恢复</span></div>
    {collapsed.length ? <div className="moa-shelf-items">{collapsed.map((entry) => {
      const summary = summaries[`${market}:${entry.id}`] ?? summaries[entry.id];
      return <div className="moa-shelf-item" key={entry.id}>
        <div><b>{entry.label}</b><span>{summary ? `${summary.value}${summary.date ? ` · ${summary.date}` : ""}` : "当前读数待载入"}</span>
          <small>{summary?.meaning ?? "恢复后可看完整曲线与口径"}</small></div>
        <div className="moa-shelf-actions"><button type="button" data-shelf-restore={entry.id} onClick={() => onRestore(entry.id)} aria-label={`恢复${entry.label}完整观察卡`}>恢复完整卡</button></div>
      </div>;
    })}</div> : <p className="moa-shelf-empty">当前没有收起的卡。</p>}
    <details className="moa-shelf-more"><summary>添加其他观察卡</summary>
      <label>查找候选 <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="输入名称" /></label>
      <div className="moa-shelf-available">{available.map((entry) => <div key={entry.id}><span>{entry.label}</span><button type="button" onClick={() => onAdd(entry.id)}>加入首页</button></div>)}</div>
      {!available.length && <p>没有匹配的候选。</p>}
    </details>
  </section>;
}
