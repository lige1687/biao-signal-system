import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { REVIEW_LABELS, workspaceApi, type ReviewStatus, type WorkspaceHolding } from "./portfolioWorkspace";
import PortfolioAgent from "./PortfolioAgent";
import { TradeConfirmCard } from "../copilot/CopilotCards";
import type { TradePreview } from "../../types";
import { fmtChange } from "../../utils/format";
import { patchPortfolioParams } from "../../pages/portfolioUrl";
import { groupPortfolioGaps } from "./portfolioGapGroups";
import "./portfolio-today-ux.css";

export type PortfolioAsk = { seq: number; holdingId: string | null; name?: string; question?: string };
const money = (n: number) => n.toLocaleString("zh-CN", { style: "currency", currency: "CNY" });
const dateText = (value?: string | null) => value || "未提供";
const localTime = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });

function PlanSection({ holding }: { holding: WorkspaceHolding }) {
  const qc = useQueryClient();
  const [candidate, setCandidate] = useState("");
  const [confirm, setConfirm] = useState(false);
  const link = useMutation({
    mutationFn: () => workspaceApi.linkPlan(holding.holding_id, candidate),
    onSuccess: () => { setConfirm(false); void qc.invalidateQueries({ queryKey: ["portfolioWorkspace"] }); },
  });
  const chosen = holding.plan_candidates.find(p => p.plan_id === candidate);
  const plan = holding.plan;
  return <section className="pwt-plan" aria-label="这笔持仓的计划">
    <h3>这笔持仓的计划</h3>
    {plan ? <>
      <p>{plan.reason || "计划未记录持有理由。"}</p>
      <dl className="pwt-facts"><dt>止损预案</dt><dd>{plan.stop_plan_cn || "未提供"}</dd><dt>止盈预案</dt><dd>{plan.take_profit_plan_cn || "未提供"}</dd><dt>关联日期</dt><dd>{plan.linked_at ? localTime(plan.linked_at) : "未提供"}，不代表原入场日期</dd></dl>
    </> : <p>尚未明确关联这笔持仓采用的计划。当前技术状态与个人原持有理由分别核对。</p>}
    {holding.original_note && <details className="pwt-original-note"><summary>查看原持仓备注</summary><p>{holding.original_note}</p><small className="pwt-muted">历史记录，仅供核对原理由；不代表已确认计划或当前技术结论。</small></details>}
    {holding.plan_candidates.length > 0 && <>
      <label className="pwt-field">选择同一产品的已有计划
        <select value={candidate} onChange={e => { setCandidate(e.target.value); setConfirm(false); link.reset(); }} disabled={link.isPending}>
          <option value="">请选择</option>
          {holding.plan_candidates.map(p => <option key={p.plan_id} value={p.plan_id}>{p.reason || p.plan_id}</option>)}
        </select>
      </label>
      {chosen && <div className="pwt-plan-check"><p>{chosen.reason || "未记录持有理由"}</p><p>止损：{chosen.stop_plan_cn || "未提供"}</p><p>止盈：{chosen.take_profit_plan_cn || "未提供"}</p>
        <label><input type="checkbox" checked={confirm} onChange={e => setConfirm(e.target.checked)} disabled={link.isPending} />我确认这份计划适用于当前这笔持仓</label>
        <button type="button" disabled={!confirm || link.isPending} onClick={() => link.mutate()}>{link.isPending ? "关联中…" : "确认关联计划"}</button>
      </div>}
    </>}
    {link.isError && <p role="alert" className="pwt-error">{link.error.message}</p>}
    <Link to="/plans">打开计划监督</Link>
    {!holding.symbol && <p className="pwt-muted">本产品尚无已核实的完整技术行情。可先与 Agent 整理已知持有依据；记不清的部分保留未知。</p>}
  </section>;
}

function TradeEntry({ holding, reviewDate }: { holding: WorkspaceHolding; reviewDate: string }) {
  const [side, setSide] = useState<"buy" | "sell" | "">("");
  const [preview, setPreview] = useState<TradePreview | null>(null);
  return <details className="pwt-trade-entry"><summary>登记已发生的基金成交</summary>
    <p className="pwt-muted">填写实际成交后确认记账。成交台账与持仓快照分别维护；这里不会下单或自动改变持仓金额。</p>
    {!preview ? <div className="pwt-action-row"><label>实际方向 <select aria-label="实际成交方向" value={side} onChange={e => setSide(e.target.value as typeof side)}><option value="">请选择</option><option value="buy">买入</option><option value="sell">卖出</option></select></label>
      <button type="button" disabled={!side} onClick={() => side && setPreview({ fund_code: holding.code, fund_name: holding.name, side, side_cn: side === "buy" ? "买入" : "卖出", amount: null, trade_date: reviewDate, missing: ["成交金额"], note_cn: "用户手动填写实际成交" })}>填写成交确认卡</button>
    </div> : <TradeConfirmCard preview={preview} />}
  </details>;
}

function TechnicalEvidence({ holding }: { holding: WorkspaceHolding }) {
  const a = holding.technical?.assessment;
  if (!a) return <p className="pwt-muted">完整技术资料尚不具备；已有净值只用于查看净值及其日期，不替代完整行情判断。</p>;
  return <section className="pwt-technical"><h3>已有技术依据</h3>
    <p className="pwt-muted">行情截至 {dateText(holding.technical?.meta.last_bar_date)}{holding.technical?.meta.is_intraday_forming ? " · 当日数据尚未完成" : ""}。本次能否完成计划复核，见上方状态与缺口。</p>
    <dl className="pwt-facts"><dt>阶段</dt><dd>{a.stage_cn || "未提供"}</dd><dt>均线与抵扣价</dt><dd>{a.color_cn || "未提供"}</dd><dt>长周期背景</dt><dd>{a.dimensions?.["长周期"] || "未提供"}</dd></dl>
    {(a.conflicts ?? []).map((f, i) => <p key={`conflict-${f.rule_id}-${i}`}><strong>冲突 · {f.label_cn}</strong>：{f.detail_cn}</p>)}
    {(a.supports ?? []).slice(0, 4).map((f, i) => <p key={`support-${f.rule_id}-${i}`}><strong>{f.label_cn}</strong>：{f.detail_cn}</p>)}
    {(a.exit_signals ?? []).map(e => <p key={e.rule_id}><strong>{e.rule_cn} · {e.state_cn}</strong>：{e.reason_cn}{e.research_proxy ? "（判定方式为研究代理）" : ""}</p>)}
    <p className="pwt-muted">上方技术事实由系统提供；个人处理方式以这笔持仓已确认的计划为准。</p>
  </section>;
}

export default function PortfolioToday({ ask, onShowAll }: { ask: PortfolioAsk | null; onShowAll: () => void }) {
  const query = useQuery({ queryKey: ["portfolioWorkspace"], queryFn: workspaceApi.get, staleTime: 60_000, retry: 1 });
  const [params, setParams] = useSearchParams();
  const rawFilter = params.get("todayFilter");
  const filter: ReviewStatus | "all" = rawFilter && rawFilter in REVIEW_LABELS ? rawFilter as ReviewStatus : "all";
  const search = params.get("todayQ") ?? "";
  const selectedId = params.get("todayHolding");
  const update = (values: Record<string, string | null>, replace = true) => setParams(patchPortfolioParams(params, values), { replace });
  const [agent, setAgent] = useState<PortfolioAsk | null>(null);
  const [refreshNotice, setRefreshNotice] = useState("");
  const listRef = useRef<HTMLElement>(null);
  const detailRef = useRef<HTMLElement>(null);
  const incomingSeq = useRef<number | null>(null);
  const data = query.data;
  const gapGroups = useMemo(() => groupPortfolioGaps(data?.items ?? []), [data]);
  const items = (data?.items ?? []).filter(h => (filter === "all" || h.status === filter) && `${h.name} ${h.code ?? ""}`.toLowerCase().includes(search.trim().toLowerCase()));
  const selected = items.find(h => h.holding_id === selectedId) ?? items[0];
  const bringIntoView = (element: HTMLElement | null) => {
    if (!element) return;
    const navigationHeight = document.querySelector(".top-nav")?.getBoundingClientRect().height ?? 60;
    element.style.scrollMarginTop = `${navigationHeight + 12}px`;
    element.scrollIntoView({ block: "start", behavior: "auto" });
  };
  const bringDetail = () => bringIntoView(detailRef.current);
  useEffect(() => {
    if (!ask || incomingSeq.current === ask.seq || !data) return;
    incomingSeq.current = ask.seq;
    update({ todayFilter: null, todayQ: null, todayHolding: ask.holdingId }); setAgent(ask);
  }, [ask, data]);
  useEffect(() => { if (agent) bringDetail(); }, [agent]);

  const openAgent = (holding: WorkspaceHolding | null, question?: string) => setAgent({ seq: Date.now(), holdingId: holding?.holding_id ?? null, name: holding?.name, question });
  const refresh = async () => {
    setRefreshNotice("");
    const result = await query.refetch();
    if (!result.isError) setRefreshNotice("已重新读取现有资料。净值与行情日期见各只持仓，未发起行情更新。");
  };
  if (query.isPending) return <p className="pl-empty" role="status">正在读取今日持仓资料…</p>;
  if (!data) return <div className="pl-empty" role="alert">今日持仓读取失败：{query.error?.message ?? "未返回资料"}。<button type="button" onClick={() => void query.refetch()}>重新读取</button></div>;
  const c = data.coverage;
  return <section className="pwt-today" aria-label="今日持仓工作区">
    <div className="pwt-heading"><div><h2>今日持仓</h2><p>{data.review_date} · 各持仓按自身行情日期核对</p></div><div className="pwt-action-row"><button type="button" disabled={query.isFetching} onClick={() => void refresh()}>{query.isFetching ? "读取中…" : "重新读取资料"}</button><button type="button" className="pwt-primary" onClick={() => openAgent(null, "今天我的持仓先看什么？请列明已经核对和仍不能判断的部分。")}>问 Agent：全部持仓</button></div></div>
    <div className="pwt-summary"><strong>{c.action_required > 0 ? `${c.action_required} 只持仓有原计划事项待处理` : c.incomplete > 0 || c.waiting > 0 ? "本轮核对尚未全部完成" : c.total > 0 ? "本轮已核对，暂无新触发" : "尚无持仓记录"}</strong>
      <span>已关联计划 {c.with_plan}/{c.total} · 有技术结果 {c.with_technical}/{c.total} · 有净值记录 {c.with_nav}/{c.total}</span>
    </div>
    {(query.isError || refreshNotice) && <p className={query.isError ? "pwt-error" : "pwt-muted"} role={query.isError ? "alert" : "status"}>{query.isError ? `重新读取失败，当前仍显示上次成功读取的资料：${query.error.message}` : refreshNotice}</p>}
    {gapGroups.length > 0 && (
      <details className="pwt-gap-summary">
        <summary className="pwt-gap-top-summary">
          <span>待补资料汇总（{gapGroups.length} 类 · 场外基金无实时 K 线或未绑计划属常态，按需点开核对）</span>
        </summary>
        <div className="pwt-gap-summary-list">
          {gapGroups.map(({ gap, affected }) => (
            <details key={gap}>
              <summary><span>{gap}</span><strong>影响 {affected.length} 只</strong></summary>
              <div className="pwt-gap-products">
                {affected.map(h => (
                  <button type="button" key={h.holding_id} onClick={() => { update({ todayFilter: null, todayQ: null, todayHolding: h.holding_id }, false); setAgent(null); requestAnimationFrame(bringDetail); }}>
                    {h.name}{h.code ? ` · ${h.code}` : ""}
                  </button>
                ))}
              </div>
            </details>
          ))}
        </div>
      </details>
    )}
    <div className="pwt-controls"><div className="pwt-filters" aria-label="持仓核对状态"><button type="button" aria-pressed={filter === "all"} onClick={() => { update({ todayFilter: null, todayHolding: null }); setAgent(null); }}>全部 {c.total}</button>{(Object.keys(REVIEW_LABELS) as ReviewStatus[]).map(s => <button type="button" key={s} aria-pressed={filter === s} onClick={() => { update({ todayFilter: s, todayHolding: null }); setAgent(null); }}>{REVIEW_LABELS[s]} {c[s]}</button>)}</div><label>查找持仓<input type="search" value={search} onChange={e => { update({ todayQ: e.target.value, todayHolding: null }); setAgent(null); }} placeholder="名称或基金代码" /></label></div>
    <div className="pwt-workspace"><section className="pwt-list" ref={listRef} aria-label="今日持仓事项">
      {items.length === 0 ? <p className="pl-empty">{data.items.length ? "没有符合当前筛选的持仓。" : "尚无持仓记录。"}</p> : items.map(h => <button type="button" key={h.holding_id} className={`pwt-row pwt-${h.status}`} aria-pressed={!agent && selected?.holding_id === h.holding_id} onClick={() => { update({ todayHolding: h.holding_id }, false); setAgent(null); if (window.matchMedia("(max-width: 900px)").matches) requestAnimationFrame(bringDetail); }}>
        <span className="pwt-row-top"><strong>{h.name}</strong><span className="pwt-status">{REVIEW_LABELS[h.status]}</span></span>
        <span className="pwt-row-sub">{h.code || "代码未记录"} · {h.group_name}</span><span className="pwt-row-title" title={h.reason_cn}>{h.status === "incomplete" ? `资料缺口 ${h.gaps.length} 项 · 点开逐项核对` : h.title_cn}</span>
        <span className="pwt-row-bottom"><span>{money(h.market_value)} · 基金内 {h.weight_pct.toFixed(1)}%</span><span>{h.nav ? `净值 ${h.nav.date}` : "净值日期未提供"}</span></span>
      </button>)}
      <button type="button" className="pwt-all-link" onClick={onShowAll}>查看完整金额与收益明细</button>
    </section>
    <aside ref={detailRef} className="pwt-detail" aria-label="持仓依据和后续操作">
      <button type="button" className="pwt-back" onClick={() => bringIntoView(listRef.current)}>返回持仓清单</button>
      {agent ? <PortfolioAgent holdingId={agent.holdingId} holdingName={agent.name} initialQuestion={agent.question} onClose={() => setAgent(null)} /> : selected ? <div key={selected.holding_id}>
        <div className="pwt-detail-head"><span>{REVIEW_LABELS[selected.status]}</span><h2>{selected.name}</h2><p>{selected.code || "代码未记录"} · {selected.group_name}</p></div>
        <div className="pwt-capital"><span>记录金额 <strong>{money(selected.market_value)}</strong></span><span>基金内占比 <strong>{selected.weight_pct.toFixed(1)}%</strong></span><span>持有收益率 <strong className={fmtChange(selected.return_pct).cls}>{fmtChange(selected.return_pct).text}</strong></span></div>
        <section className="pwt-decision"><h3>{selected.title_cn}</h3><p>{selected.reason_cn}</p><p><strong>下一步：</strong>{selected.next_step_cn}</p></section>
        {(selected.alerts ?? []).length > 0 && <section className="pwt-alerts" aria-label="原计划触发依据">{selected.alerts!.map((alert, index) => <div key={`${alert.code}-${index}`}><p>{alert.next_step_cn}</p><small>依据行情 {dateText(alert.data_as_of)} · 最早处理日 {dateText(alert.actionable_from)}</small>{alert.caveat_cn && <p className="pwt-muted">{alert.caveat_cn}</p>}</div>)}</section>}
        <div className="pwt-action-row"><button type="button" className="pwt-primary" onClick={() => openAgent(selected, "原来的持有理由还成立吗？请按这笔持仓已有资料解释，未记录的计划不要推测。")}>追问这笔持仓</button>{selected.symbol && <Link to={`/?symbol=${encodeURIComponent(selected.symbol)}`}>查看本产品图表</Link>}</div>
        <PlanSection holding={selected} />
        <TechnicalEvidence holding={selected} />
        {selected.gaps.length > 0 && <section className="pwt-gaps"><h3>尚缺的资料</h3><ul>{selected.gaps.map(g => <li key={g}>{g}</li>)}</ul><button type="button" onClick={() => openAgent(selected, "针对当前资料缺口，我需要补充哪些信息？请区分我能提供的信息和系统尚未接入的数据。")}>让 Agent 帮我整理</button></section>}
        <details className="pwt-sources"><summary>资料日期与来源</summary><dl className="pwt-facts"><dt>原持仓记录日</dt><dd>{dateText(selected.holding_as_of)}</dd><dt>已有基金净值</dt><dd>{selected.nav ? `${selected.nav.value}（${selected.nav.date}）` : "未提供"}</dd><dt>净值读取记录</dt><dd>{selected.nav?.updated_at ? localTime(selected.nav.updated_at) : "未提供"}</dd><dt>完整行情</dt><dd>{dateText(selected.technical?.meta?.last_bar_date)}{selected.technical?.meta?.is_intraday_forming ? " · 盘中形成中" : ""}</dd><dt>本次资料读取</dt><dd>{localTime(data.generated_at)}</dd></dl><p>金额来自持仓记录，部分金额由净值估算更新；不含现金，不是券商实时账户。基金净值与完整技术行情分别核对。</p></details>
        {selected.technical?.meta.calendar_note_cn && <p className="pwt-muted">{selected.technical.meta.calendar_note_cn}</p>}
        {/^[0-9]{6}$/.test(selected.code ?? "") && <TradeEntry holding={selected} reviewDate={data.review_date} />}
      </div> : <p className="pl-empty">选择一只持仓查看依据。</p>}
    </aside></div>
  </section>;
}
