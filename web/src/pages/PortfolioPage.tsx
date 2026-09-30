import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, portfolioApi } from "../api/client";
import { ReviewFetcher, TradesLedgerView } from "../components/copilot/CopilotCards";
import PortfolioTechnicalDetail from "../components/portfolio/PortfolioTechnicalDetail";
import { agentConsoleStore } from "../App";
import { fmtChange } from "../utils/format";
import { classifySymbol, mapHoldingsToSymbols, type HoldingSymbolMap, type SymbolSource } from "../utils/portfolioSymbols";
import type { PortfolioGroup, PortfolioHolding } from "../types";
import "./portfolio.css";

type Row = { holding: PortfolioHolding; group: PortfolioGroup };
type SortKey = "amount" | "return";
const money = (v: number) => `¥${v.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (v: number) => `${v.toFixed(1)}%`;
const marketName: Record<string, string> = { cn: "A股", hk: "港股", us: "美股", other: "其他" };

function askDraftFor(h: PortfolioHolding, map: HoldingSymbolMap | undefined, asOf: string) {
  return `我持有「${h.name}」（基金代码${h.code ?? "未记录"}；${map ? `已关联同一产品行情 ${map.symbol}` : "尚未关联自身行情"}）。持仓记录日期 ${asOf}，金额与收益是已有记录，逐只更新日期未提供，并非实时账户。请只根据该产品自身资料核对阶段、道路和触发条件；原入场依据与失效位未记录时请明确说明。`;
}

export default function PortfolioPage() {
  const { data, error, isLoading } = useQuery({ queryKey: ["portfolio"], queryFn: portfolioApi.get, staleTime: 5 * 60_000 });
  const { data: dashboard } = useQuery({ queryKey: ["cards"], queryFn: () => api.dashboard(), staleTime: 60_000 });
  const { data: catalog } = useQuery({ queryKey: ["sectors"], queryFn: () => api.sectors(), staleTime: Infinity });
  const [tab, setTab] = useState<"holdings" | "trades">("holdings");
  const [search, setSearch] = useState("");
  const [groupFilter, setGroupFilter] = useState("all");
  const [sort, setSort] = useState<SortKey>("amount");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detailRef = useRef<HTMLElement>(null);
  const selectHolding = (holdingId: string) => {
    setSelectedId(holdingId);
    const detail = detailRef.current;
    if (!detail) return;
    const navigationHeight = document.querySelector(".top-nav")?.getBoundingClientRect().height ?? 60;
    detail.style.scrollMarginTop = `${navigationHeight + 12}px`;
    detail.scrollIntoView({
      block: window.matchMedia("(max-width: 1100px)").matches ? "start" : "nearest",
      behavior: "auto",
    });
  };
  const rows = useMemo<Row[]>(() => data?.groups.flatMap(group => group.holdings.map(holding => ({ holding, group }))) ?? [], [data]);
  const symbolMap = useMemo(() => {
    const sources: SymbolSource[] = [
      ...(dashboard?.cards ?? []).filter(c => !c.error).map(c => ({
        symbol: c.symbol, name: c.display_name,
        identity: c.group === "watchlist" ? classifySymbol(c.symbol) : "insufficient" as const,
      })),
      ...(catalog?.us_etfs ?? []).map(s => ({ symbol: s.symbol, name: s.name, identity: "us_etf_catalog" as const })),
    ];
    return mapHoldingsToSymbols(rows.map(r => r.holding), sources);
  }, [rows, dashboard, catalog]);
  const visible = useMemo(() => rows.filter(({ holding, group }) =>
    (groupFilter === "all" || group.group_key === groupFilter) &&
    (!search.trim() || `${holding.name} ${holding.code ?? ""} ${group.name}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
  ).sort((a, b) => {
    const av = sort === "return" ? a.holding.return_pct : a.holding.market_value;
    const bv = sort === "return" ? b.holding.return_pct : b.holding.market_value;
    return (bv ?? -Infinity) - (av ?? -Infinity) || a.holding.name.localeCompare(b.holding.name, "zh-CN");
  }), [rows, groupFilter, search, sort]);
  const selected = visible.find(r => r.holding.holding_id === selectedId) ?? visible[0];
  if (isLoading) return <div className="page pl-page">加载持仓中…</div>;
  if (error || !data) return <div className="page pl-page" role="alert">持仓数据加载失败：{(error as Error | null)?.message ?? "未知错误"}</div>;
  const max = Math.max(0, ...rows.map(r => r.holding.market_value));
  return <div className="page pl-page">
    <header className="pl-header"><div><h1>我的持仓</h1><p>持仓记录日期 {data.as_of}</p></div><span>{data.holdings_count} 只基金</span></header>
    <p className="pl-data-note" role="note">金额与收益为已有记录，逐只更新日期未提供，非实时账户。以下基金内占比以所录基金金额为分母，不含现金。行情判断另按各自日期展示。</p>
    <div className="pl-overview" aria-label="持仓概览">
      <div><span>所录基金金额</span><strong>{rows.length ? money(data.total_value) : "—"}</strong></div>
      <div><span>基金只数</span><strong>{data.holdings_count}</strong></div>
      <div><span>最大单只基金内占比</span><strong>{rows.length && data.total_value > 0 ? pct(max / data.total_value * 100) : "—"}</strong></div>
      <div><span>已关联自身行情</span><strong>{symbolMap.size}<small> / {rows.length}</small></strong></div>
    </div>
    <div className="pl-tabs" role="tablist" aria-label="持仓页面">
      <button type="button" role="tab" aria-selected={tab === "holdings"} onClick={() => setTab("holdings")}>持仓明细</button>
      <button type="button" role="tab" aria-selected={tab === "trades"} onClick={() => setTab("trades")}>成交记录</button>
    </div>
    {tab === "holdings" ? <>
      <div className="pl-toolbar">
        <label>分组<select value={groupFilter} onChange={e => setGroupFilter(e.target.value)}><option value="all">全部分组</option>{data.groups.map(g => <option key={g.group_key} value={g.group_key}>{g.name}</option>)}</select></label>
        <label>搜索<input type="search" placeholder="基金名称或代码" value={search} onChange={e => setSearch(e.target.value)} /></label>
        <label>排序<select value={sort} onChange={e => setSort(e.target.value as SortKey)}><option value="amount">金额和占比从高到低</option><option value="return">持有收益率从高到低</option></select></label>
        <span>显示 {visible.length} / {rows.length} 只</span>
      </div>
      <div className="pl-workspace">
        <section className="pl-list" aria-label="基金清单"><div className="pl-list-scroll"><table><thead><tr><th>基金</th><th className="pl-num">金额</th><th className="pl-num">基金内占比</th><th className="pl-num">收益率</th><th>资料</th></tr></thead><tbody>
          {visible.map(({ holding, group }) => {
            const ret = fmtChange(holding.return_pct);
            return <tr key={holding.holding_id} className={selected?.holding.holding_id === holding.holding_id ? "pl-selected" : ""}>
              <td><button type="button" className="pl-row-select" aria-pressed={selected?.holding.holding_id === holding.holding_id} onClick={() => selectHolding(holding.holding_id)}><strong>{holding.name}</strong><span>{holding.code ?? "代码未记录"} · {group.name}</span></button></td>
              <td className="pl-num">{money(holding.market_value)}</td><td className="pl-num">{data.total_value > 0 ? pct(holding.market_value / data.total_value * 100) : "—"}</td>
              <td className={`pl-num ${ret.cls}`}>{ret.text}</td><td className="pl-source">{symbolMap.has(holding.holding_id) ? "自身行情已关联" : "未关联"}</td>
            </tr>;
          })}
        </tbody></table></div>{visible.length === 0 && <p className="pl-empty">{rows.length ? "没有符合条件的基金。调整分组或搜索词后再看。" : "暂无基金持仓记录。"}</p>}</section>
        <aside ref={detailRef} className="pl-detail" aria-label="单只基金核对" aria-live="polite">{selected ? <>
          <div className="pl-detail-head"><span>当前选择</span><h2>{selected.holding.name}</h2><p>{selected.holding.code ?? "代码未记录"} · {selected.group.name}</p></div>
          <dl className="pl-facts"><div><dt>记录金额</dt><dd>{money(selected.holding.market_value)}</dd></div><div><dt>基金内占比</dt><dd>{data.total_value > 0 ? pct(selected.holding.market_value / data.total_value * 100) : "—"}</dd></div><div><dt>记录收益率</dt><dd className={fmtChange(selected.holding.return_pct).cls}>{fmtChange(selected.holding.return_pct).text}</dd></div></dl>
          <section className="pl-quarter"><h3>季报已披露前十大持仓</h3>{selected.holding.top10_total_pct == null ? <p>暂无可展示的季报前十大资料。</p> : <>
            <p>季报 {selected.holding.report_quarter ?? "日期未提供"} · 前十大合计占基金净值 {pct(selected.holding.top10_total_pct)}</p>
            <p>{Object.entries(selected.holding.top10_by_market_pct).filter(([, v]) => v > 0).map(([m, v]) => `${marketName[m] ?? m} ${pct(v)}`).join(" · ") || "市场拆分未提供"}</p>
            <small>仅覆盖已披露前十大；各比例为原占基金净值比例，不代表整只基金或整个组合的地域分布。</small>
          </>}</section>
          <PortfolioTechnicalDetail holding={selected.holding} map={symbolMap.get(selected.holding.holding_id)} />
          <div className="pl-actions">{symbolMap.get(selected.holding.holding_id) && <Link to={`/?symbol=${encodeURIComponent(symbolMap.get(selected.holding.holding_id)!.symbol)}`}>看图</Link>}<button type="button" title="只放入可编辑草稿，不自动发送" onClick={() => agentConsoleStore.openConsole(null, askDraftFor(selected.holding, symbolMap.get(selected.holding.holding_id), data.as_of))}>问助手</button></div>
          {selected.holding.note && <details className="pl-item-note"><summary>持仓原备注</summary><p>{selected.holding.note}</p></details>}
        </> : <p className="pl-empty">选择一只基金查看资料。</p>}</aside>
      </div>
      <section className="pl-allocation"><h2>分组金额分布</h2><p>按所录基金金额计算，不含现金；分组用于整理持仓，不代表技术判定。</p>{data.groups.map(g => <div className="pl-allocation-row" key={g.group_key}><span>{g.name}</span><div className="pl-bar"><i style={{ width: `${Math.max(0, Math.min(100, g.pct))}%` }} /></div><strong>{pct(g.pct)}</strong><small>{money(g.amount)}</small></div>)}</section>
      <details className="pl-history"><summary>历史组合备注 <span>原提示、建议与分组说明</span></summary>
        <p>以下保留旧研究及写入时的文字；其适用范围和写入日期未必对应当前持仓或行情，不代表当前技术结论。</p>
        <section><h3>原始录入来源</h3><p>{data.data_source_cn}</p></section>
        {data.observations.length > 0 && <section><h3>组合提示</h3><ul>{data.observations.map((o, i) => <li key={i}>{o}</li>)}</ul></section>}
        {data.advices.length > 0 && <section><h3>原调仓建议</h3>{data.advices.map(a => <article key={a.advice_id}><h4>{a.title_cn} <small>{a.strength_cn}</small></h4><p>{a.detail_cn}</p>{a.evidence.length > 0 && <p>原依据：{a.evidence.map(e => `${e.label}（${e.ref}）`).join("；")}</p>}{a.trigger_cn && <p>原时机：{a.trigger_cn}</p>}{a.execution_cn && <p>原执行说明：{a.execution_cn}</p>}</article>)}</section>}
        {data.groups.map(g => <section key={g.group_key}><h3>{g.name} · 原分组说明</h3><p>{g.verdict_cn}</p>{g.verdict_basis && <p>原依据：{g.verdict_basis}</p>}</section>)}
      </details>
    </> : <section className="pl-trades" role="tabpanel"><p>成交记录是手动报单台账，与上方持仓记录分别维护；这里不自动改变持仓金额。</p><div className="pl-trade-review"><ReviewFetcher weekly /></div><TradesLedgerView /></section>}
  </div>;
}
