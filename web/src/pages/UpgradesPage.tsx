import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { upgradesApi, type GoalAction, type GoalContent, type GoalKind, type GoalStatus, type UpgradeGoal } from "../api/upgrades";
import "./upgrades.css";

const STATUS: Record<GoalStatus, string> = {
  planned: "待规划", awaiting_approval: "待授权", approved: "已授权", in_progress: "进行中",
  review: "待验收", done: "已完成", paused: "已搁置", dropped: "不再推进",
};
const ACTION: Record<GoalAction, string> = {
  note: "记录进展", request_approval: "提交待授权", authorize: "授权本项目", revoke: "撤回授权",
  start: "记录开始推进", pause: "暂时搁置", submit_review: "提交验收", accept: "验收完成", drop: "不再推进", reopen: "重新打开",
};
const PRIORITY = { high: "优先", medium: "常规", low: "稍后" };
const time = (s: string) => new Date(s).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
const closed = (g: UpgradeGoal) => g.status === "done" || g.status === "dropped";
const milestoneId = () => `m-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
const badge = (s: GoalStatus) => <span className={`upgrade-status status-${s}`}>{STATUS[s]}</span>;

type DialogState = { mode: "create"; kind: GoalKind; parent?: string } | { mode: "edit"; goal: UpgradeGoal } | { mode: "action"; goal: UpgradeGoal; action: GoalAction };

export default function UpgradesPage() {
  const [params, setParams] = useSearchParams();
  const [kind, setKind] = useState<"all" | GoalKind>(params.has("goal") ? "all" : "directional");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["upgrades"], queryFn: upgradesApi.list, staleTime: 0, refetchInterval: 30_000, refetchOnWindowFocus: true });
  const items = query.data?.items ?? [];
  const directions = items.filter(g => g.kind === "directional");
  const concrete = items.filter(g => g.kind === "concrete");
  const keyword = search.trim().toLowerCase();
  const filtered = items.filter(g => (kind === "all" || g.kind === kind) && (!status || g.status === status)
    && (!keyword || [g.title, g.purpose, g.evidence, g.id, directions.find(d => d.id === g.parent_id)?.title ?? ""].join(" ").toLowerCase().includes(keyword)));
  const selected = filtered.find(g => g.id === params.get("goal")) ?? filtered[0];
  const parent = directions.find(g => g.id === selected?.parent_id);
  const children = items.filter(g => g.parent_id === selected?.id);
  const choose = (id: string, reveal = false) => {
    if (reveal) { setKind("all"); setStatus(""); setSearch(""); }
    setParams({ goal: id }, { replace: true });
  };
  const open = (next: DialogState) => { setError(""); setNotice(""); setDialog(next); };
  async function save(work: () => Promise<UpgradeGoal>, message: string, closeDialog = false) {
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const goal = await work();
      await client.invalidateQueries({ queryKey: ["upgrades"] });
      if (closeDialog) { setDialog(null); choose(goal.id, true); }
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
      await client.invalidateQueries({ queryKey: ["upgrades"] });
    } finally { setBusy(false); }
  }
  const action = (g: UpgradeGoal, a: GoalAction) => open({ mode: "action", goal: g, action: a });
  const waiting = concrete.filter(g => g.status === "awaiting_approval").length;
  const active = concrete.filter(g => g.status === "in_progress").length;
  const review = concrete.filter(g => g.status === "review").length;

  return <main className="upgrades-page">
    <header className="upgrades-header pg-head">
      <div className="pg-head-title">
        <h1>系统待升级项目</h1>
        <p className="pg-head-sub">把想做的改进留下来，等合适的时候逐项推进。授权只针对选中的具体目标，不会自动启动研究或改规则。</p>
      </div>
      <div className="pg-head-kv">
        <span className="pg-kv"><span className="k">方向性目标</span><b>{query.isLoading ? "未知" : directions.length}</b></span>
        <span className="pg-kv"><span className="k">具体目标</span><b>{query.isLoading ? "未知" : concrete.length}</b></span>
        <span className="pg-kv"><span className="k">待授权</span><b>{query.isLoading ? "未知" : waiting}</b></span>
        <span className="pg-kv"><span className="k">进行中</span><b>{query.isLoading ? "未知" : active}</b></span>
        <span className="pg-kv"><span className="k">待验收</span><b>{query.isLoading ? "未知" : review}</b></span>
      </div>
      <div className="pg-head-actions upgrades-header-actions">
        <a className="upgrade-button" href="/api/upgrades/export" download="system-upgrades.json">导出完整台账</a>
        <button className="upgrade-button primary" onClick={() => open({ mode: "create", kind: "concrete" })}>＋ 登记目标</button>
      </div>
    </header>
    <section className="upgrades-overview" aria-label="具体目标进展概览">
      <div className="upgrades-overview-copy"><strong>目标与关键结果 <span>OKR</span></strong><span>方向说清要改善什么，具体目标说清怎样算做到了。</span></div>
      <button onClick={() => { setKind("concrete"); setStatus("awaiting_approval"); }}><b>{waiting}</b> 待你授权</button>
      <button onClick={() => { setKind("concrete"); setStatus("in_progress"); }}><b>{active}</b> 正在推进</button>
      <button onClick={() => { setKind("concrete"); setStatus("review"); }}><b>{review}</b> 等待验收</button>
    </section>
    <div className="upgrades-guidance">授权只针对选中的具体目标和范围。这里记录决定与进度；点击授权不会自动启动研究、回测或改规则。</div>
    {notice && <div className="upgrade-notice" role="status">{notice}</div>}
    {error && !dialog && <div className="upgrade-error" role="alert">{error}</div>}
    {query.isError ? <div className="upgrade-error" role="alert">台账加载失败：{(query.error as Error).message}<button onClick={() => void query.refetch()}>重新加载</button></div> : query.isLoading ? <div className="upgrade-empty" role="status">正在读取已保存的目标…</div> : <>
      <div className="upgrades-filters">
        <div className="upgrades-tabs" aria-label="目标类型">
          {([['directional', `方向性目标 ${directions.length}`], ['concrete', `具体目标 ${concrete.length}`], ['all', '全部']] as const).map(([k, label]) => <button key={k} aria-pressed={kind === k} onClick={() => setKind(k)}>{label}</button>)}
        </div>
        <input aria-label="搜索目标" placeholder="搜索目标、依据或编号" value={search} onChange={e => setSearch(e.target.value)} />
        <select aria-label="筛选状态" value={status} onChange={e => setStatus(e.target.value)}><option value="">全部状态</option>{Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      </div>
      <div className="upgrades-layout">
        <aside className="upgrades-list" aria-label="目标列表">
          <div className="upgrades-list-caption"><span>{filtered.length} 个目标</span><button onClick={() => open({ mode: "create", kind: "directional" })}>＋ 新方向</button></div>
          {filtered.map(g => <button key={g.id} className={`upgrade-row${selected?.id === g.id ? " selected" : ""}`} onClick={() => choose(g.id)} aria-pressed={selected?.id === g.id}>
            <span className="upgrade-row-meta"><span>{g.kind === "directional" ? "方向" : PRIORITY[g.priority]}</span>{badge(g.status)}</span>
            <strong>{g.title}</strong>
            <span className="upgrade-row-purpose">{g.purpose}</span>
            <span className="upgrade-row-footer">{g.progress?.total ? `${g.progress.done} / ${g.progress.total} ${g.kind === "directional" ? "具体目标已完成" : "完成标准已达成"}` : "尚未拆分完成标准"}<span>{time(g.updated_at)}</span></span>
          </button>)}
          {!filtered.length && <div className="upgrade-empty">没有匹配的目标。<button onClick={() => { setKind("all"); setStatus(""); setSearch(""); }}>清除筛选</button></div>}
        </aside>
        {selected ? <article className="upgrade-detail" aria-label="目标详情" key={selected.id}>
          <div className="upgrade-detail-top"><span>{selected.kind === "directional" ? "方向性目标" : "具体目标"} · {selected.id}</span><span>{PRIORITY[selected.priority]}</span></div>
          <h2>{selected.title}</h2>
          <div className="upgrade-detail-meta">{badge(selected.status)}<span>负责人：{selected.owner}</span><span>目标日期：{selected.target_date ?? "尚未约定"}</span></div>
          {parent && <button className="upgrade-parent" onClick={() => choose(parent.id, true)}>所属方向：{parent.title}</button>}
          <p className="upgrade-purpose">{selected.purpose || "还未填写这个目标希望带来的改变。"}</p>
          <div className="upgrade-next"><strong>下一步</strong><p>{selected.next_action || "待明确下一步范围。"}</p></div>
          <div className="upgrade-detail-actions">
            {!closed(selected) && <button className="upgrade-button" onClick={() => open({ mode: "edit", goal: selected })}>编辑目标与证据</button>}
            <button className="upgrade-button" onClick={() => action(selected, "note")}>记录进展</button>
            {selected.kind === "concrete" && !closed(selected) && !selected.authorization.granted && <button className="upgrade-button primary" onClick={() => action(selected, "authorize")}>授权本项目</button>}
            {selected.kind === "concrete" && selected.authorization.granted && ["approved", "paused"].includes(selected.status) && <button className="upgrade-button primary" onClick={() => action(selected, "start")}>记录开始推进</button>}
            {selected.status === "in_progress" && <button className="upgrade-button primary" onClick={() => action(selected, "submit_review")}>提交验收</button>}
            {selected.status === "review" && <button className="upgrade-button primary" onClick={() => action(selected, "accept")}>验收完成</button>}
            {closed(selected) && <button className="upgrade-button" onClick={() => action(selected, "reopen")}>重新打开</button>}
            {!closed(selected) && <details className="upgrade-more"><summary>其他操作</summary><div>
              {selected.kind === "concrete" && !selected.authorization.granted && <button onClick={() => action(selected, "request_approval")}>提交待授权</button>}
              {selected.authorization.granted && <button onClick={() => action(selected, "revoke")}>撤回授权</button>}
              {selected.status !== "paused" && <button onClick={() => action(selected, "pause")}>暂时搁置</button>}
              {selected.kind === "directional" && <button onClick={() => action(selected, "submit_review")}>提交方向验收</button>}
              <button onClick={() => action(selected, "drop")}>不再推进，保留记录</button>
            </div></details>}
          </div>
          {selected.kind === "concrete" && <section className={`upgrade-authorization${selected.authorization.granted ? " granted" : ""}`}>
            <strong>{selected.authorization.granted ? "本项授权范围" : selected.authorization.scope ? "此前范围 · 当前未授权" : closed(selected) ? "历史成果记录" : "尚未授权推进"}</strong>
            <p>{selected.authorization.scope || (closed(selected) ? "这是此前已完成的历史成果记录。" : "你可以先补充完成标准，再决定何时授权。")}</p>
          </section>}
          {selected.kind === "directional" ? <section className="upgrade-section"><div className="upgrade-section-heading"><h3>具体目标</h3>{!closed(selected) && <button onClick={() => open({ mode: "create", kind: "concrete", parent: selected.id })}>＋ 拆分目标</button>}</div>
            {children.length ? children.map(g => <button className="upgrade-child" key={g.id} onClick={() => choose(g.id, true)}><span><strong>{g.title}</strong><small>{g.next_action}</small></span>{badge(g.status)}</button>) : <p className="upgrade-muted">先把方向拆成一次可以推进和验收的工作。</p>}
          </section> : <section className="upgrade-section"><div className="upgrade-section-heading"><h3>怎样算做到了</h3><span>{selected.progress?.done ?? 0} / {selected.milestones.length} 项</span></div>
            {selected.milestones.length ? selected.milestones.map(m => <label className="upgrade-check" key={m.id}><input type="checkbox" checked={m.done} disabled={busy || closed(selected) || !selected.authorization.granted} onChange={e => { const done = e.target.checked; void save(() => upgradesApi.patch(selected.id, selected.version, { milestones: selected.milestones.map(x => x.id === m.id ? { ...x, done } : x) }), "完成标准已保存。"); }} /><span>{m.title}</span></label>) : <p className="upgrade-muted">尚未约定完成标准，编辑目标即可补充。</p>}
            <p className="upgrade-hint">勾选表示已有结果；研究不成立也可以完成，需在证据里说明。</p>
          </section>}
          <section className="upgrade-section"><h3>结果与依据</h3><p className="upgrade-evidence">{selected.evidence || "尚无新的结果。完成后在这里写清结论，并附上可核对的材料。"}</p>
            <div className="upgrade-links">{selected.links.map((l, i) => l.url.startsWith("/") ? <Link key={i} to={l.url}>{l.label} ↗</Link> : <a key={i} href={l.url} target="_blank" rel="noopener noreferrer">{l.label} ↗</a>)}</div>
          </section>
          <section className="upgrade-section"><h3>更新记录 <span className="upgrade-muted">{selected.history.length}</span></h3><ol className="upgrade-history">{[...selected.history].reverse().map((h, i) => <li key={`${h.at}-${i}`}><div><strong>{ACTION[h.action as GoalAction] ?? (h.action === "seed" ? "首次登记" : h.action === "edited" ? "内容更新" : "创建目标")}</strong><time>{time(h.at)}</time>{h.to_status && badge(h.to_status)}</div><p>{h.note}</p>{h.scope && <p className="upgrade-muted">范围：{h.scope}</p>}{h.before && h.after && <details><summary>查看改动内容</summary>{Object.keys(h.after).map(key => <div key={key} className="upgrade-change"><span>{({ title: "目标", purpose: "希望改善", parent_id: "所属方向", priority: "优先级", owner: "负责人", target_date: "目标日期", next_action: "下一步", evidence: "结果与证据", milestones: "完成标准", links: "依据链接" } as Record<string, string>)[key] ?? key}</span><pre>{JSON.stringify(h.before?.[key], null, 2)} → {JSON.stringify(h.after?.[key], null, 2)}</pre></div>)}</details>}</li>)}</ol></section>
        </article> : <div className="upgrade-detail upgrade-empty">登记第一个目标，从一个明确的方向开始。</div>}
      </div>
    </>}
    {dialog && <GoalDialog state={dialog} directions={directions} busy={busy} error={error} onClose={() => { if (!busy) { setDialog(null); setError(""); } }} onSave={(work, message) => void save(work, message, true)} />}
  </main>;
}

function GoalDialog({ state, directions, busy, error, onClose, onSave }: {
  state: DialogState; directions: UpgradeGoal[]; busy: boolean; error: string; onClose: () => void;
  onSave: (work: () => Promise<UpgradeGoal>, message: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const goal = state.mode !== "create" ? state.goal : undefined;
  const [kind, setKind] = useState<GoalKind>(goal?.kind ?? (state.mode === "create" ? state.kind : "concrete"));
  const [content, setContent] = useState<GoalContent>({ title: goal?.title ?? "", purpose: goal?.purpose ?? "", parent_id: goal?.parent_id ?? (state.mode === "create" ? state.parent ?? null : null), priority: goal?.priority ?? "medium", owner: goal?.owner ?? "待安排", target_date: goal?.target_date ?? null, next_action: goal?.next_action ?? "", evidence: goal?.evidence ?? "", milestones: goal?.milestones ?? [], links: goal?.links ?? [] });
  const [note, setNote] = useState(state.mode === "action" && state.action === "accept" ? "已核对完成标准和成果，确认本项目完成。" : "");
  const [scope, setScope] = useState(goal?.authorization.scope ?? "");
  const [localError, setLocalError] = useState("");
  const isAction = state.mode === "action";
  const title = isAction ? ACTION[state.action] : state.mode === "edit" ? "编辑目标" : "登记新目标";
  useEffect(() => { ref.current?.showModal(); }, []);
  const field = <K extends keyof GoalContent>(k: K, value: GoalContent[K]) => setContent(c => ({ ...c, [k]: value }));
  const submit = (e: React.FormEvent) => {
    e.preventDefault(); setLocalError("");
    if (state.mode === "action") {
      onSave(() => upgradesApi.action(state.goal.id, state.goal.version, state.action, note, scope), state.action === "authorize" ? "授权范围已记录。尚未启动执行，可在后续对话中按此范围推进。" : "更新已保存。");
    } else {
      if (!content.title.trim()) { setLocalError("请填写目标名称。"); return; }
      if (content.milestones.some(m => !m.title.trim()) || content.links.some(l => !l.label.trim() || !l.url.trim())) { setLocalError("请填完完成标准和链接，或移除空白行。"); return; }
      const data = { ...content, parent_id: kind === "directional" ? null : content.parent_id };
      onSave(() => state.mode === "edit" ? upgradesApi.patch(state.goal.id, state.goal.version, data) : upgradesApi.create({ ...data, kind }), state.mode === "edit" ? "目标已更新。范围或完成标准有变化时，原授权会撤回。" : "目标已登记，尚未授权执行。");
    }
  };
  return <dialog ref={ref} className="upgrade-dialog" aria-labelledby="upgrade-dialog-title" onCancel={e => { e.preventDefault(); onClose(); }}>
    <form onSubmit={submit}><header><h2 id="upgrade-dialog-title">{title}</h2><button type="button" onClick={onClose} disabled={busy} aria-label="关闭对话框">×</button></header>
      <div className="upgrade-dialog-body">
        {isAction ? <><p className="upgrade-action-subject">{goal?.title}</p>
          {state.action === "authorize" && <><p className="upgrade-guidance-inline">只授权这个具体项目。请写清本次做到哪一步；登记授权不会自动运行任何工作。</p><label>此次授权范围<textarea required maxLength={4000} value={scope} onChange={e => setScope(e.target.value)} placeholder="例如：筛选近期论文并提交候选清单，不改规则、不运行回测。" /></label></>}
          {state.action === "accept" && <p className="upgrade-guidance-inline">确认完成标准与成果已核对。研究完成不代表策略有效。</p>}
          {state.action === "reopen" && <p className="upgrade-guidance-inline">历史记录保留。重新打开后，需要重新确认具体推进范围。</p>}
          <label>{state.action === "note" ? "本次进展与下一步" : "决定依据或说明"}<textarea required maxLength={6000} value={note} onChange={e => setNote(e.target.value)} placeholder="写下实际做了什么、依据在哪里，或者为什么作出这个决定。" /></label>
        </> : <>
          {state.mode === "create" && <label>目标类型<select value={kind} onChange={e => setKind(e.target.value as GoalKind)}><option value="directional">方向性目标：长期希望改善什么</option><option value="concrete">具体目标：一次能推进和验收的工作</option></select></label>}
          <label>目标名称<input required maxLength={150} value={content.title} onChange={e => field("title", e.target.value)} placeholder="用一句话写清想做到什么" /></label>
          {kind === "concrete" && <label>所属方向<select value={content.parent_id ?? ""} onChange={e => field("parent_id", e.target.value || null)}><option value="">暂未归入方向</option>{directions.filter(g => !closed(g)).map(g => <option key={g.id} value={g.id}>{g.title}</option>)}</select></label>}
          <label>希望带来什么改变<textarea maxLength={6000} value={content.purpose} onChange={e => field("purpose", e.target.value)} /></label>
          <div className="upgrade-form-grid"><label>优先级<select value={content.priority} onChange={e => field("priority", e.target.value as GoalContent["priority"])}>{Object.entries(PRIORITY).map(([k, v]) => <option value={k} key={k}>{v}</option>)}</select></label><label>负责人<input maxLength={100} value={content.owner} onChange={e => field("owner", e.target.value)} /></label><label>目标日期（可不填）<input type="date" value={content.target_date ?? ""} onChange={e => field("target_date", e.target.value || null)} /></label></div>
          <label>下一步做什么<textarea maxLength={2000} value={content.next_action} onChange={e => field("next_action", e.target.value)} /></label>
          {kind === "concrete" && <fieldset><legend>怎样算做到了</legend>{content.milestones.map((m, i) => <div className="upgrade-form-row" key={m.id}><input aria-label={`完成标准 ${i + 1}`} maxLength={500} required value={m.title} onChange={e => field("milestones", content.milestones.map(x => x.id === m.id ? { ...x, title: e.target.value } : x))} /><button type="button" aria-label={`移除完成标准 ${i + 1}`} onClick={() => field("milestones", content.milestones.filter(x => x.id !== m.id))}>移除</button></div>)}<button type="button" disabled={content.milestones.length >= 50} onClick={() => field("milestones", [...content.milestones, { id: milestoneId(), title: "", done: false }])}>＋ 添加完成标准</button></fieldset>}
          <label>已有结果与证据<textarea maxLength={10000} value={content.evidence} onChange={e => field("evidence", e.target.value)} placeholder="如尚未执行，可留空；写清发现了什么以及局限。" /></label>
          <fieldset><legend>依据链接</legend>{content.links.map((l, i) => <div className="upgrade-form-link" key={i}><input aria-label={`链接名称 ${i + 1}`} required maxLength={150} placeholder="材料名称" value={l.label} onChange={e => field("links", content.links.map((x, j) => i === j ? { ...x, label: e.target.value } : x))} /><input aria-label={`链接地址 ${i + 1}`} required maxLength={2000} placeholder="https:// 或 /library?report=…" value={l.url} onChange={e => field("links", content.links.map((x, j) => i === j ? { ...x, url: e.target.value } : x))} /><button type="button" onClick={() => field("links", content.links.filter((_, j) => i !== j))}>移除</button></div>)}<button type="button" disabled={content.links.length >= 30} onClick={() => field("links", [...content.links, { label: "", url: "" }])}>＋ 添加链接</button></fieldset>
          {state.mode === "edit" && goal?.authorization.granted && <p className="upgrade-guidance-inline">改变目标名称、目的、所属方向或完成标准，需要重新授权。</p>}
        </>}
        {(localError || error) && <div className="upgrade-error" role="alert">{localError || error}</div>}
      </div>
      <footer><button className="upgrade-button" type="button" disabled={busy} onClick={onClose}>取消</button><button className="upgrade-button primary" disabled={busy} type="submit">{busy ? "保存中…" : isAction ? title : "保存目标"}</button></footer>
    </form>
  </dialog>;
}
