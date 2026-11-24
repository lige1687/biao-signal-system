import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { sourceHref } from "./metrics";
import { caseNeedsRecheck, filterProgressCases, progressQuery, updateProgressQuery, isCatalogRecord, loadWorkflowProgress, PAGE_SIZE, selectProgressCase, stageNeedsRecheck, type CaseKind, type ProgressSource, type WorkflowProgressData } from "./workflowProgress";
import "./workflow-progress.css";

type Selection = { datasetId: string; factorId: string };
interface Props { initialSelection?: Selection; onOpenDiagnostics?: (selection: Selection & { poolId: string }) => void }
const kinds: { value: "all" | CaseKind; label: string }[] = [
  { value: "all", label: "全部" }, { value: "factor", label: "因子" }, { value: "strategy", label: "策略" }, { value: "data", label: "资料" }, { value: "reference", label: "参考" }, { value: "benchmark", label: "基准" },
];
const kindLabel: Record<CaseKind, string> = { factor: "因子", strategy: "策略", data: "资料", reference: "参考", benchmark: "基准" };
const catalogTypeLabel: Record<string, string> = { feature: "特征", "policy/strategy": "策略", benchmark: "基准", factor: "因子", data: "资料", reference: "参考", state_signal: "状态指标", factor_return: "因子收益", risk_metric: "风险指标", published_reference: "公开研究参考", method: "研究方法", case: "研究案例", model_definition: "模型定义" };
const catalogPurposeLabel: Record<string, string> = { description: "说明对象含义", comparison: "比较研究结果", ranking: "候选排序", diagnostic: "诊断检查", research_signal: "研究观察指标" };
const catalogLabel = (value: string, labels: Record<string, string>) => value.split("、").map(part => labels[part] ?? part).join("、");
const statusLabel: Record<string, string> = { done: "已记录完成", partial: "部分完成", blocked: "受阻", not_evaluated: "未评价", not_applicable: "本轮不适用", unknown: "待核对" };
const conclusionLabel: Record<string, string> = { limited: "有限结论", unsupported: "未发现支持", inconclusive: "证据不足", not_evaluated: "未评价", unknown: "待核对" };

function readableVersion(value: string) {
  const dated = value.match(/(20\d{2})-?(\d{2})-?(\d{2})/);
  const version = value.match(/(?:^|[\s/-])v(\d+(?:\.\d+)*)/i);
  return [dated ? `${dated[1]}-${dated[2]}-${dated[3]} 版` : null, version ? `v${version[1]}` : null].filter(Boolean).join(" · ") || "版本见原报告";
}

function Evidence({ ids, sources, catalog = false }: { ids: string[]; sources: ProgressSource[]; catalog?: boolean }) {
  const related = sources.filter(source => ids.includes(source.id));
  if (!related.length) return <p className="wp-muted">本项未列出可核对来源。</p>;
  const changed = related.filter(source => source.status !== "verified").length;
  return <details className="wp-evidence"><summary>{related.length} 份可核资料{changed ? `，其中 ${changed} 份需重新核对` : ""} · 展开查看</summary><div className="wp-evidence-list">{related.map(source => {
    const href = source.reportPath ? sourceHref(source.reportPath) : source.path.endsWith(".md") ? sourceHref(source.path) : null;
    return <article className="wp-source" key={source.id}>
      <div><strong>{source.title}</strong><span className={source.status === "verified" ? "wp-source-ok" : "wp-source-warn"}>{source.status === "verified" ? (catalog ? "登记来源已核" : "来源已核对") : "来源需重新核对"}</span></div>
      <p>来源日期：{source.sourceDate}</p>
      {href ? <a href={href}>打开{source.reportPath ? "原报告" : "来源"}</a> : <p className="wp-muted">原始资料暂不能从页面打开。</p>}
    </article>;
  })}</div></details>;
}

export default function WorkflowProgress({ initialSelection, onOpenDiagnostics }: Props) {
  const [data, setData] = useState<WorkflowProgressData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const caseListRef = useRef<HTMLDivElement>(null);
  const [params, setParams] = useSearchParams();
  const { query, kind, scope, page, selectedId, stageId, attention } = progressQuery(params);
  const stageChoice = selectedId && stageId ? { caseId: selectedId, stageId } : null;
  const update = (changes: Record<string, string | null>, replace = false) => setParams(previous => updateProgressQuery(previous, changes), { replace });
  const setStageChoice = (choice: { caseId: string; stageId: string } | null) => update({ wpCase: choice?.caseId ?? selectedId, wpStage: choice?.stageId ?? null });


  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setData(null); setError("");
    void loadWorkflowProgress(controller.signal).then(setData).catch(e => {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "研究进度暂无法读取。");
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reload]);

  const filtered = useMemo(() => filterProgressCases(data?.cases ?? [], query, kind, scope).filter(c => !attention || c.execution.state === "blocked" || caseNeedsRecheck(c, data?.sources ?? [])), [data, kind, query, scope, attention]);
  const chosen = useMemo(() => {
    const previous = filtered.find(c => c.id === selectedId);
    return previous ?? selectProgressCase(filtered, initialSelection);
  }, [filtered, selectedId, initialSelection?.datasetId, initialSelection?.factorId]);
  useEffect(() => { caseListRef.current?.querySelector('[aria-current="true"]')?.scrollIntoView({ block: "nearest" }); }, [chosen?.id]);
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const selectedIndex = chosen ? filtered.findIndex(c => c.id === chosen.id) : -1;
  const currentPage = selectedIndex >= 0 && Math.floor(selectedIndex / PAGE_SIZE) + 1 !== page ? Math.floor(selectedIndex / PAGE_SIZE) + 1 : Math.min(page, Math.max(1, pageCount));
  const visibleCases = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const catalogRecord = chosen ? isCatalogRecord(chosen) : false;
  const linkedCases = chosen?.relatedCaseIds?.map(id => data?.cases.find(c => c.id === id)).filter((c): c is NonNullable<typeof c> => Boolean(c) && !isCatalogRecord(c!)) ?? [];
  function openRelated(id: string) { update({ wpQ: null, wpKind: null, wpScope: "reviewed", wpPage: "1", wpCase: id, wpStage: null, wpAttention: null }); }
  function changePage(next: number) { update({ wpPage: String(next), wpCase: filtered[(next - 1) * PAGE_SIZE]?.id ?? null, wpStage: null }); }
  const stage = chosen?.stages.find(s => s.id === (stageChoice?.caseId === chosen.id ? stageChoice.stageId : chosen.currentStageId));
  const stale = chosen && data ? caseNeedsRecheck(chosen, data.sources) : false;
  const stageStale = stage && data ? stageNeedsRecheck(stage, data.sources, Boolean(stale)) : false;

  const catalogIssues = !loading && data?.catalog?.issues.length ? <p className="wp-catalog-issues" role="alert">研究目录来源仍有待核对之处，相关旧记录暂不能视为最新结论。</p> : null;

  return <section className="wp-root" aria-label="研究进度">
    <div className="wp-intro"><div><h2>研究进度</h2><p>目录覆盖全部登记对象；研究结论只来自已审阅记录。新报告仍需证据审阅。</p>{data?.catalog && <p className="wp-catalog-count">目录覆盖 {data.catalog.total} 条 · 已有研究记录 {data.catalog.reviewedResearchCases} 条</p>}</div>{data && <div className="wp-intro-meta"><span>内容审阅：{data.reviewedAt.slice(0, 10)}</span><span>来源核对：{new Date(data.checkedAt).toLocaleString("zh-CN", {hour12:false, month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit"})}</span><button type="button" onClick={() => setReload(n => n + 1)}>重新核对资料</button>{catalogIssues}</div>}</div>
    {loading && <div className="wp-state" role="status">正在读取研究记录…</div>}
    {!loading && error && <div className="wp-state" role="alert"><strong>研究进度暂无法读取</strong><p>目前无法取得完整研究进度，请重新读取。</p><button type="button" onClick={() => setReload(n => n + 1)}>重新读取</button></div>}
    {!loading && data?.intake && <details className="wp-intake"><summary>审阅后新增报告 · {data.intake.items.length} 份待关联</summary><p>依据报告文件日期筛出，尚未逐份判断与哪个对象相关。关联和内容审阅完成前，原研究进度保持原判定。</p><div className="wp-intake-list">{data.intake.items.map(item => <a key={item.path} href={sourceHref(item.path) ?? undefined}><time>{item.date}</time><span>{item.title}</span><small>{item.category} · 待审阅</small></a>)}</div></details>}
    {!loading && data && <div className="wp-layout">
      <aside className="wp-sidebar" aria-label="研究对象">
        <div className="wp-sidebar-head"><strong>研究对象</strong><span>{filtered.length} 条匹配</span></div>
        <label className="wp-search"><span>查找对象</span><input type="search" value={query} onChange={e => { update({ wpQ: e.target.value, wpPage: "1", wpCase: null, wpStage: null }, true); }} placeholder="名称或研究版本" /></label>
        <label className="wp-filter"><span>证据范围</span><select value={scope} onChange={e => { update({ wpScope: e.target.value, wpPage: "1", wpCase: null, wpStage: null }); }}><option value="all">全部</option><option value="reviewed">已有研究记录</option><option value="catalog">目录档案</option></select></label>
        <label className="wp-filter"><span>对象类型</span><select value={kind} onChange={e => { update({ wpKind: e.target.value, wpPage: "1", wpCase: null, wpStage: null }); }}>{kinds.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label className="wp-filter"><span>优先事项</span><select value={attention ? "attention" : "all"} onChange={e => update({ wpAttention: e.target.value === "attention" ? "1" : null, wpCase: null, wpPage: "1", wpStage: null })}><option value="all">当前范围全部记录</option><option value="attention">受阻或来源需复核</option></select></label><div className="wp-case-list" ref={caseListRef}>{filtered.length ? visibleCases.map(c => {
          const needsCheck = caseNeedsRecheck(c, data.sources);
          return <button type="button" key={c.id} className="wp-case" aria-current={c.id === chosen?.id ? "true" : undefined} onClick={() => { update({ wpCase: c.id, wpStage: null }); }}>
            <span className="wp-case-top"><span>{kindLabel[c.kind]}</span><span className={needsCheck ? "wp-caution" : ""}>{needsCheck ? "需重新核对" : isCatalogRecord(c) ? "目录档案" : c.execution.label}</span></span>
            <strong>{c.title}</strong><small>研究版本 {readableVersion(c.researchVersion)}</small>
          </button>;
        }) : <p className="wp-no-match">没有符合筛选条件的记录。可清空搜索或切换范围。</p>}</div>
        {pageCount > 1 && <div className="wp-pager"><button type="button" disabled={currentPage <= 1} onClick={() => changePage(currentPage - 1)}>上一页</button><span>第 {currentPage} / {pageCount} 页</span><button type="button" disabled={currentPage >= pageCount} onClick={() => changePage(currentPage + 1)}>下一页</button></div>}
      </aside>
      {chosen && catalogRecord ? <div className="wp-main wp-catalog-detail" key={chosen.id}>
        <header className="wp-object-head"><div><div className="wp-object-kicker">目录档案 · {kindLabel[chosen.kind]} · {readableVersion(chosen.researchVersion)}</div><h3>{chosen.title}</h3><p>{catalogLabel(chosen.purpose, catalogPurposeLabel)}</p></div><span className={stale ? "wp-integrity wp-integrity-warn" : "wp-integrity"}>{stale ? "登记来源需重新核对" : "登记来源已核"}</span></header>
        <div className="wp-meta"><div><span>研究版本</span><strong>{readableVersion(chosen.researchVersion)}</strong></div><div><span>对象类型</span><strong>{chosen.objectType ? catalogLabel(chosen.objectType, catalogTypeLabel) : kindLabel[chosen.kind]}</strong></div><div><span>目录读取日</span><strong>{chosen.evidenceAsOf}</strong></div></div>
        {linkedCases.length > 0 && <section className="wp-related wp-related-compact"><h4>已有相关研究</h4>{linkedCases.map(c => <button key={c.id} type="button" onClick={() => openRelated(c.id)}>{c.title} · {readableVersion(c.researchVersion)}</button>)}</section>}
        <section className="wp-catalog-message"><h4>{linkedCases.length || chosen.execution.label.includes("旧记录") ? "已登记，相关研究待核对" : "已登记，研究证据待关联"}</h4><p>{chosen.execution.label.includes("旧记录") ? `${chosen.execution.label}；旧摘要见八阶段下方，需按原报告核对。` : "目录登记不代表研究完成或效果成立。"}</p>{chosen.limitations.length > 0 && <details className="wp-catalog-limits"><summary>适用边界与来源说明</summary><ul>{chosen.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></details>}{chosen.legacyCatalogUrl && <a className="wp-legacy-link" href={chosen.legacyCatalogUrl}>查看旧研究档案</a>}<Evidence ids={chosen.sourceIds} sources={data.sources} catalog /></section>
        <section className="wp-stage-section"><div className="wp-section-line"><h4>八个研究阶段</h4><span>目录记载，未知保持未知</span></div><div className="wp-stage-strip">{chosen.stages.map((item, index) => {
          const needsCheck = stageNeedsRecheck(item, data.sources, Boolean(stale));
          return <button type="button" key={item.id} className="wp-stage" data-status={needsCheck ? "unknown" : item.status} aria-pressed={stage?.id === item.id} onClick={() => setStageChoice({ caseId: chosen.id, stageId: item.id })}><span className="wp-stage-index">{String(index + 1).padStart(2, "0")}</span><strong>{item.title}</strong><small className={needsCheck ? "wp-caution" : ""}>{needsCheck ? "需重新核对" : statusLabel[item.status]}</small></button>;
        })}</div>{stage && <article className="wp-stage-detail"><div className="wp-section-line"><h5>{stage.title}</h5><span className={stageStale ? "wp-caution" : ""}>{stageStale ? "来源待复核" : statusLabel[stage.status]}</span></div><p>{stage.summary}</p>{stage.missing && <p><b>尚缺：</b>{stage.missing}</p>}{stage.nextAction && <p><b>后续条件：</b>{stage.nextAction}</p>}<Evidence ids={stage.sourceIds} sources={data.sources} catalog /></article>}</section>
        {chosen.execution.label.includes("旧记录") && chosen.stages[4]?.summary && <section className="wp-historical"><h4>已有历史研究摘要 · 待核对</h4><p>{chosen.stages[4].summary}</p><Evidence ids={chosen.stages[4].sourceIds} sources={data.sources} catalog /></section>}
      </div> : chosen ? <div className="wp-main" key={chosen.id}>
        <header className="wp-object-head"><div><div className="wp-object-kicker">{chosen.kind === "factor" ? "因子研究" : chosen.kind === "strategy" ? "策略研究" : "数据核查"} · {readableVersion(chosen.researchVersion)}</div><h3>{chosen.title}</h3><p>{chosen.purpose}</p></div><span className={stale ? "wp-integrity wp-integrity-warn" : "wp-integrity"}>{stale ? "来源有变化 · 需要重新核对" : "已核对原记录"}</span></header>
        <div className="wp-meta"><div><span>研究范围</span><strong>{chosen.universe}</strong></div><div><span>观察期间</span><strong>{chosen.period}</strong></div><div><span>证据截至</span><strong>{chosen.evidenceAsOf}</strong></div></div>
        <div className="wp-outcomes"><article><span>研究执行</span><strong>{stale ? "需重新核对来源" : chosen.execution.label}</strong><p>{chosen.execution.state === "completed" ? "这轮研究已有结案记录。" : chosen.execution.state === "paused" ? "研究已暂停，待满足恢复条件。" : chosen.execution.state === "blocked" ? "执行受阻，详见主卡点。" : "执行状态尚未核定。"}</p></article><article><span>效果结论</span><strong>{stale ? "原结论待复核" : conclusionLabel[chosen.conclusion.state]}</strong><p>{stale ? "原记录可供回查；来源变化或缺失后，暂不把旧结论作为当前判断。" : chosen.conclusion.text}</p></article></div>
        <div className="wp-bottleneck-brief"><span>{chosen.bottleneck.scope === "本轮" ? "当前卡点" : "扩大用途待补"}</span><strong>{stale ? "来源变化，先重新核对" : chosen.bottleneck.title}</strong></div>
        <section className="wp-stage-section"><div className="wp-section-line"><h4>八个研究阶段</h4><span>点击查看已有记录</span></div><div className="wp-stage-strip">{chosen.stages.map((item, index) => {
          const needsCheck = stageNeedsRecheck(item, data.sources, Boolean(stale));
          return <button type="button" key={item.id} className="wp-stage" data-status={needsCheck ? "unknown" : item.status} aria-pressed={stage?.id === item.id} onClick={() => setStageChoice({ caseId: chosen.id, stageId: item.id })}><span className="wp-stage-index">{String(index + 1).padStart(2, "0")}</span><strong>{item.title}</strong><small className={needsCheck ? "wp-caution" : ""}>{needsCheck ? "需重新核对" : statusLabel[item.status]}</small></button>;
        })}</div>{stage && <article className="wp-stage-detail"><div className="wp-section-line"><h5>{stage.title}</h5><span className={stageStale ? "wp-caution" : ""}>{stageStale ? "来源待复核" : statusLabel[stage.status]}</span></div><p>{stageStale ? "以下是原记录；来源变化或缺失后，阶段状态暂不能作为当前结果。" : stage.summary}</p>{stage.missing && <p><b>尚缺：</b>{stage.missing}</p>}{stage.nextAction && <p><b>后续条件：</b>{stage.nextAction}</p>}<Evidence ids={stage.sourceIds} sources={data.sources} /></article>}</section>
        <section className="wp-bottleneck"><div className="wp-section-line"><h4>当前主卡点</h4><span>{chosen.bottleneck.scope}</span></div><strong>{stale ? "先重新核对证据来源" : chosen.bottleneck.title}</strong><p>{stale ? "来源内容变更或缺失，下面的阶段和结论只能作为历史记录阅读。" : chosen.bottleneck.detail}</p><div className="wp-action-grid"><div><span>下一动作</span><p>{stale ? "核对变更或缺失的原始资料后再判断下一步。" : chosen.bottleneck.nextAction}</p></div><div><span>依赖条件</span><p>{chosen.bottleneck.dependency}</p></div></div><Evidence ids={chosen.bottleneck.sourceIds} sources={data.sources} /></section>
        {chosen.limitations.length > 0 && <section className="wp-limitations"><h4>适用边界</h4><ul>{chosen.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></section>}
        {onOpenDiagnostics && chosen.datasetId && chosen.factorId && chosen.poolIds.length > 0 && <button type="button" className="wp-diagnostics" onClick={() => onOpenDiagnostics({ datasetId: chosen.datasetId!, factorId: chosen.factorId!, poolId: chosen.poolIds[0] })}>查看这组对象的诊断资料</button>}
        <section className="wp-timeline"><div className="wp-section-line"><h4>已记录事件</h4><span>来自文档，不代表实时运行</span></div>{chosen.timeline.length ? <ol>{chosen.timeline.map((event, index) => <li key={`${event.date}-${index}`}><time dateTime={event.date}>{event.date}</time><span>{event.label}</span><Evidence ids={event.sourceIds} sources={data.sources} /></li>)}</ol> : <p className="wp-muted">暂无可定位的文档事件。</p>}</section>
      </div> : <div className="wp-state">没有可显示的对象。请调整筛选条件。</div>}
    </div>}
  </section>;
}
