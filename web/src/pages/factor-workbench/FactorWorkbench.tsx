import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import FactorCurves from "../factor-research/FactorCurves";
import { CURVE_QUERY_KEYS, comparisonRows, defaultSelection, feeLabel, loadCurveLibrary, percentagePoints, selectCurves, type CurveSelection } from "../factor-research/factorCurvesModel";
import { loadWorkbenchMetrics, matchingMetrics, metric, pct, sourceHref, type CorrelationRecord, type ICRecord, type IRRecord } from "./metrics";
import "./factor-workbench.css";
import traceability from "./traceability.json";
import WorkflowProgress from "./ResearchWorkflowProgress";
import { MetricReference, ResearchIdentity } from "./MetricReference";
import { FocusMomentumPanel, FocusMomentumSummary } from "../../components/focus-momentum";
import ResearchUseReview from "./ResearchUseReview";
import { diagnosticParams } from "./workbenchNavigation";
import "./workbench-readability.css";

type View = "overview" | "observation" | "progress" | "study" | "compare" | "records";
const views: { id: View; name: string }[] = [
  { id: "overview", name: "研究总览" }, { id: "observation", name: "市场观察" }, { id: "progress", name: "研究进度" }, { id: "study", name: "单因子诊断" },
  { id: "compare", name: "比较与组合增量" }, { id: "records", name: "数据与记录" },
];
const questions = [
  ["1. 自己赚钱吗？", "单因子页已接收益、回撤和波动曲线及费用情景；目前是固定股票样本的报价模拟，实际账户收益未评价。"],
  ["2. 跑赢母指数了吗？", "当前样本没有唯一母指数；已展示相对同池共同基准的超额与 IR。不能据此宣称跑赢沪深300或其他母指数。"],
  ["3. 谁贡献了表现？", "行业权重、前十大持仓和收益贡献未接入；目前无法判断是否由少数行业或股票撑起。"],
  ["4. 风格现在处于什么位置？", "历史表现可以观察；当前估值与估值分位未绑定，研究截止日期也不代表今日市场位置。"],
  ["5. 多个策略是否押同一风格？", "比较页可看候选账户收益的同步程度；真实策略持仓重叠、共同风格暴露和个人组合增量仍未评价。"],
];
const stages = [
  ["金融含义与用途", "说明为什么可能有用、想改善哪项低频决定，并写出简单对手。"],
  ["定义研究范围", "确定研究哪些股票或 ETF、历史成员、母指数及观察期限；没有唯一母指数时明确标注。"],
  ["数据准备与核验", "核对当时可得时间、报价、缺价、退市、分红和覆盖范围。"],
  ["固定研究定义", "测试前保存因子公式及版本；策略另固定买卖、仓位和费用规则。"],
  ["实验测试", "因子按用途看 IC、分组表现或风险效果；策略看收益、回撤、超额、IR 与费用。"],
  ["验证与反例", "检查未来信息、不同历史阶段、少数股票贡献和全部尝试；未参与选规则的新资料单列。"],
  ["相对母指数与已有方法的增量", "有明确母指数时比较超额、IR、回撤与波动；另看加入原策略或组合后的改善、费用及放弃的收益。固定期间、币种和分红口径，注明费用假设；同池基准不冒充母指数。"],
  ["结论与人工处置", "保留、补证或暂停；研究完成与效果成立分开，需要新资料观察时另行记录，不自动试盘。"],
];

function Plot({ title, points, valueLabel, color = "#20665b", zero = false, secondary }: { title: string; points: [string, number | null][]; valueLabel: (n: number) => string; color?: string; zero?: boolean; secondary?: { label: string; points: [string, number | null][]; color: string } }) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(560);
  useEffect(() => {
    if (!plotRef.current) return;
    const observer = new ResizeObserver(entries => { const next = Math.floor(entries[0]?.contentRect.width ?? 0); if (next > 0) setWidth(Math.max(310, next)); });
    observer.observe(plotRef.current);
    return () => observer.disconnect();
  }, []);
  const numeric = [...points, ...(secondary?.points || [])].map(p => p[1]).filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!numeric.length) return <div className="fw-empty">{title}暂无可画的有效月份。</div>;
  const all = zero ? [...numeric, 0] : numeric;
  let min = Math.min(...all), max = Math.max(...all);
  if (max === min) { min -= 0.01; max += 0.01; }
  const pad = (max - min) * 0.12; min -= pad; max += pad;
  const left = 58, right = 20, top = 16, bottom = 38, height = 208;
  const x = (i: number) => left + i * (width - left - right) / Math.max(1, points.length - 1);
  const y = (v: number) => top + (max - v) * (height - top - bottom) / (max - min);
  const pathSegments = (series: [string, number | null][]) => { const segments: string[] = []; let path = ""; series.forEach(([, value], index) => { if (value == null || !Number.isFinite(value)) { if (path) segments.push(path); path = ""; } else path += `${path ? " L" : "M"}${x(index).toFixed(1)} ${y(value).toFixed(1)}`; }); if (path) segments.push(path); return segments; };
  const paths = pathSegments(points);
  const secondaryPaths = secondary ? pathSegments(secondary.points) : [];
  const ticks = [max, (min + max) / 2, min];
  return <figure className="fw-plot" ref={plotRef}><figcaption>{title}</figcaption>{secondary && <div className="fw-plot-legend"><span style={{color}}>逐期 RankIC</span><span style={{color:secondary.color}}>{secondary.label}</span></div>}<svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}，从${points[0]?.[0]}到${points[points.length-1]?.[0]}，纵轴${valueLabel(min)}至${valueLabel(max)}`}>
    {ticks.map((v, i) => <g key={i}><line x1={left} x2={width-right} y1={y(v)} y2={y(v)} stroke="#dce4e8" strokeDasharray={i === 1 ? "3 4" : undefined} /><text x={left-8} y={y(v)+4} textAnchor="end">{valueLabel(v)}</text></g>)}
    {zero && min < 0 && max > 0 && <line x1={left} x2={width-right} y1={y(0)} y2={y(0)} stroke="#85959f" />}
    {paths.map((p, i) => <path key={i} d={p} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />)}
    {secondaryPaths.map((p, i) => <path key={`secondary-${i}`} d={p} fill="none" stroke={secondary?.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />)}
    {[0, Math.floor((points.length-1)/2), points.length-1].filter((v,i,a) => a.indexOf(v) === i).map(i => <text key={i} x={x(i)} y={height-10} textAnchor={i===0 ? "start" : i===points.length-1 ? "end" : "middle"}>{points[i]?.[0]?.slice(0,7)}</text>)}
  </svg><p>线段在缺值处断开；刻度仅帮助读取研究端保存的数值。</p></figure>;
}

const reasonText = (reason: string | null | undefined) => {
  if (!reason) return "";
  const named: Record<string,string> = { too_few_periods: "有效期数不足", zero_variance: "各期差异为零", missing_months: "月份缺失", insufficient_data: "资料不足" };
  return named[reason] || (/^[a-z_]+$/.test(reason) ? "研究端未提供可读原因" : reason);
};

function ICPanel({ record }: { record?: ICRecord }) {
  if (!record) return <section className="fw-block"><h3>排序与未来结果的关系</h3><p className="fw-empty">当前样本、范围与分期未接入 RankIC 和 ICIR；资金曲线不能反推出个股预测能力。</p></section>;
  return <section className="fw-block"><div className="fw-block-head"><h3>排序与未来结果的关系</h3><span>{record.range.join(" 至 ")} · {record.nPeriods}个有效观察期</span></div>
    <div className="fw-metrics"><div><span>平均 RankIC</span><strong>{metric(record.mean)}</strong><small>每期因子排序与之后结果的相关程度，再取平均</small></div><div><span>ICIR（不年化）</span><strong>{metric(record.icir, 2)}</strong><small>平均相关程度除以各期波动{record.icirReason && `；${reasonText(record.icirReason)}`}</small></div><div><span>有效覆盖</span><strong>{pct(record.coverage, 1)}</strong><small>{record.horizon}</small></div></div>
    {record.uncertainty && typeof record.uncertainty === "object" && <p className="fw-uncertainty">平均 RankIC 的历史不确定范围：{metric(record.uncertainty.lower)} 至 {metric(record.uncertainty.upper)}。这是均值范围，不是 ICIR 范围。</p>}
    <div className="fw-plot-grid"><Plot title="逐期与过去 12 期平均 RankIC" points={record.points.map(p => [p[0], p[1]])} secondary={{ label:"过去 12 期均值", points:record.rolling.map(p => [p[0],p[1]]), color:"#536caa" }} valueLabel={v => v.toFixed(2)} zero /><Plot title="过去 12 期 ICIR（不年化）" points={record.rolling.map(p => [p[0], p[2]])} valueLabel={v => v.toFixed(2)} zero color="#536caa" /></div>
    <details className="fw-limits"><summary>口径与资料限制</summary><p>未来结果定义：{record.labelDefinition}。{record.uncertainty && typeof record.uncertainty === "object" && record.uncertainty.method}</p><p>RankIC 是排序诊断，不是收益率；累计 IC 不代表账户回报。Pearson IC 暂未评价。{record.limitations?.join(" ")}</p></details>
  </section>;
}

function IRPanel({ record }: { record?: IRRecord }) {
  if (!record) return <section className="fw-block"><h3>相对同池基准的稳定程度</h3><p className="fw-empty">当前样本、范围、费用与分期没有可用 IR；此处不从图上重算。</p></section>;
  return <section className="fw-block"><div className="fw-block-head"><h3>相对同池基准的稳定程度</h3><span>{record.range.join(" 至 ")} · {record.nPeriods}个月 · {record.feeLabel || feeLabel(record.feeBps)}</span></div>
    <div className="fw-metrics"><div><span>年化 IR</span><strong>{metric(record.ir, 2)}</strong><small>G5 相对同池共同基准的月差额，经波动调整{record.reason && `；${reasonText(record.reason)}`}</small></div><div><span>平均每月超额</span><strong>{percentagePoints(record.meanExcess)}</strong><small>同池共同基准；并非母指数或真实账户</small></div><div><span>每月相对差额波动</span><strong>{percentagePoints(record.trackingError)}</strong><small>研究端保存口径；最高缺价 {pct(record.unknownMax)}</small></div></div>
    <p className="fw-quote-caveat">报价账户含缺价假设；最高缺价 {pct(record.unknownMax)}，不能当作可成交收益。</p><div className="fw-plot-grid"><Plot title="G5 每月相对同池基准的差额（百分点）" points={record.points.map(p => [p[0], p[1]])} valueLabel={v => (v*100).toFixed(1)} zero /><Plot title="过去 12 个月 IR（年化）" points={record.points.map(p => [p[0], p[2]])} valueLabel={v => v.toFixed(1)} zero color="#536caa" /></div><details className="fw-limits"><summary>口径与资料限制</summary><p>{record.limitations?.join(" ")}</p></details>
  </section>;
}

function Heatmap({ record, names }: { record: CorrelationRecord; names: Map<string, string> }) {
  const ids = record.factorIds;
  return <div className="fw-table-wrap"><table className="fw-heat"><caption>G5 报价账户逐月收益的相关程度</caption><thead><tr><th scope="col">因子</th>{ids.map(id => <th scope="col" key={id}>{names.get(id) || id}</th>)}</tr></thead><tbody>{ids.map((id,i) => <tr key={id}><th scope="row">{names.get(id) || id}</th>{ids.map((other,j) => { const value = record.matrix?.[i]?.[j]; const count = record.counts?.[i]?.[j]; return <td key={other} style={value == null ? undefined : { backgroundColor: value >= 0 ? `rgba(32,102,91,${Math.min(.36,Math.abs(value)*.32+.04)})` : `rgba(154,111,72,${Math.min(.32,Math.abs(value)*.3+.04)})` }} title={count == null ? "共同月份未记录" : `${count}个共同月份`}>{metric(value, 2)}<small>{count == null ? "" : `${count}个月`}</small></td>; })}</tr>)}</tbody></table><p className="fw-note">相关程度只描述这些 G5 报价账户的历史月收益一起变化多少；不能推出真实持仓重合、行业原因或未来分散效果。{record.limitations?.join(" ")}</p></div>;
}

function exportDraft(draft: string, context: object) { const blob = new Blob([JSON.stringify({ kind: "factor-workbench-browser-draft", exportedAt: new Date().toISOString(), context, draft }, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "factor-workbench-review-draft.json"; a.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); }

interface AgentCard { id: string; title: string; text: string; source?: string; methodSource?: string }
interface AgentReply { mode: "agent" | "rules"; cards: AgentCard[]; snapshotId: string; modelRequests: number; asOf: string; limitations?: string[] }

export default function FactorWorkbench() {
  const [params, setParams] = useSearchParams();
  const view = views.find(v => v.id === params.get("wb"))?.id || "overview";
  const showAccountContext = view !== "progress" && view !== "observation";
  const curves = useQuery({ queryKey: ["factorCurveLibrary"], queryFn: ({ signal }) => loadCurveLibrary(signal), staleTime: 60_000, retry: false, enabled: view !== "observation" });
  const metrics = useQuery({ queryKey: ["factorWorkbenchMetrics"], queryFn: ({ signal }) => loadWorkbenchMetrics(signal), staleTime: 60_000, retry: false, enabled: view !== "observation" });
  const selection = curves.data ? defaultSelection(curves.data, params) : null;
  const selected = useMemo(() => { if (!curves.data || !selection) return null; try { return selectCurves(curves.data, selection); } catch { return null; } }, [curves.data, selection?.dataset, selection?.curveFactor, selection?.pool, selection?.fee, selection?.period, selection?.regime]);
  const matched = selection ? matchingMetrics(metrics.data, selection, selected?.range) : { ic: undefined, ir: undefined, correlation: undefined };
  const [agent, setAgent] = useState<AgentReply | null>(null);
  const [agentContext, setAgentContext] = useState("");
  const [agentError, setAgentError] = useState("");
  const [agentBusy, setAgentBusy] = useState(false);
  const selectionKey = selection ? [selection.dataset, selection.curveFactor, selection.pool, selection.period, selection.fee].join("|") : "";
  const draftKey = selection ? `factor-workbench-draft:${selection.dataset}:${selection.curveFactor}:${selection.pool}:${selection.period}:${selection.fee}` : "factor-workbench-draft:general";
  const [draft, setDraft] = useState(() => { try { return localStorage.getItem(draftKey) || ""; } catch { return ""; } });
  const [draftSaved, setDraftSaved] = useState(false);
  useEffect(() => { try { setDraft(localStorage.getItem(draftKey) || ""); } catch { setDraft(""); } setDraftSaved(false); }, [draftKey]);
  const navigate = (to: View) => { const next = new URLSearchParams(params); next.set("wb", to); setParams(next); window.scrollTo({ top: 0, behavior: "instant" }); };
  const changeSelection = (changes: Partial<CurveSelection>, reset = false, goTo?: View) => {
    if (!curves.data) return;
    const next = new URLSearchParams(params);
    if (reset) {
      CURVE_QUERY_KEYS.forEach(key => next.delete(key));
      if (changes.dataset) next.set("dataset", changes.dataset);
      const defaults = defaultSelection(curves.data, next);
      CURVE_QUERY_KEYS.forEach(key => next.set(key, defaults[key]));
    }
    Object.entries(changes).forEach(([key,value]) => { if (value != null) next.set(key,value); });
    if (goTo === "progress") {
      ["wpCase", "wpStage", "wpQ", "wpKind", "wpScope", "wpPage", "wpAttention"].forEach(key => next.delete(key));
    }
    if (goTo) next.set("wb", goTo);
    setParams(next);
  };
  const interpret = async () => {
    if (!selection || !selected || agentBusy) return;
    const requestedKey = selectionKey;
    setAgentBusy(true); setAgent(null); setAgentContext(requestedKey); setAgentError("");
    try {
      const response = await fetch("/api/factor-workbench/interpret", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ datasetId: selection.dataset, factorId: selection.curveFactor, poolId: selection.pool, periodId: selection.period, feeBps: Number(selection.fee) }) });
      if (!response.ok) throw new Error(`解读暂不可用（HTTP ${response.status}）。`);
      const result = await response.json() as AgentReply;
      if (!Array.isArray(result.cards) || !["agent", "rules"].includes(result.mode)) throw new Error("解读内容格式不完整。");
      setAgent(result);
    } catch (error) { setAgentError(error instanceof Error ? error.message : "解读暂不可用。"); }
    finally { setAgentBusy(false); }
  };
  const d = selected?.dataset ?? curves.data?.datasets.find(item => item.id === selection?.dataset);
  const boundDefinition = d?.id === traceability.datasetId ? traceability.factors.find(f => f.factorId === selection?.curveFactor) : undefined;
  const factorNames = new Map(d?.factors.map(f => [f.id, f.name]) || []);
  const available = curves.data?.datasets.filter(item => item.available) || [];
  const availableFactors = new Set(available.flatMap(item => item.factors.filter(f => f.available).map(f => f.id)));
  const largestUnknown = metrics.data?.irRecords.filter(record => record.unknownMax != null).reduce<typeof metrics.data.irRecords[number] | null>((best, record) => !best || Number(record.unknownMax) > Number(best.unknownMax) ? record : best, null) ?? null;
  const incrementRows = d && selection && Number(selection.fee) === 25 ? comparisonRows(d, selection) : [];
  const asNumber = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value : null;
  return <main className="fw-page"><header className="fw-head"><div><h1>因子研究工作台</h1><p>把研究证据接到个人低频决定：先看同池基准与资料边界，再判断增量和代价。</p></div>{showAccountContext && <div className="fw-head-meta"><strong>{available.length}</strong><span>批已接入资金记录</span><strong>{availableFactors.size}</strong><span>种有曲线的因子定义</span></div>}</header>
    <nav className="fw-nav" aria-label="工作台视图">{views.map(item => <button key={item.id} type="button" aria-current={view === item.id ? "page" : undefined} onClick={() => navigate(item.id)}>{item.name}</button>)}</nav>
    {showAccountContext && <div className="fw-snapshot">页面资料更新：资金曲线 {curves.data?.generated_at?.slice(0,10) || "读取中"}；专业指标 {metrics.data?.generatedAt?.slice(0,10) || "暂未读取"}。实际数据截至请查所选实验原报告。{selection && <span className="fw-current-fee">当前所选费用：{feeLabel(Number(selection.fee))}；{d?.name || "样本名称未记录"} / {selected?.factor.name || "因子名称未记录"}。</span>}</div>}
    {showAccountContext && curves.data && selection && d?.available && <div className="fw-selector" role="group" aria-label="工作台研究条件"><label>研究样本<select value={selection.dataset} onChange={event => changeSelection({dataset:event.target.value},true)}>{curves.data.datasets.map(item => <option key={item.id} value={item.id} disabled={!item.available}>{item.name}{!item.available ? `（${item.statusLabel || "资料未接入"}）` : ""}</option>)}</select></label><label>因子<select value={selection.curveFactor} onChange={event => changeSelection({curveFactor:event.target.value})}>{d.factors.filter(item => item.available).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>候选范围<select value={selection.pool} onChange={event => changeSelection({pool:event.target.value})}>{d.pools.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>买卖费用<select value={selection.fee} onChange={event => changeSelection({fee:event.target.value})}>{d.fees_bps.map(value => <option key={value} value={value}>{feeLabel(value)}</option>)}</select></label><label>历史分期<select value={selection.period} onChange={event => changeSelection({period:event.target.value})}>{Object.entries(d.periods).map(([id,range]) => <option key={id} value={id}>{range.join(" 至 ")}</option>)}</select></label></div>}
    {view === "overview" && <div className="fw-content fw-overview"><section className="fw-intro"><div><h2>因子证据与研究用途</h2><p>先按当前样本、范围和费用比较已有证据；真实账户效果仍未评价。</p></div><div className="fw-actions"><button type="button" onClick={() => navigate("progress")}>查看全部因子与进展</button><button type="button" onClick={() => navigate("study")}>查看有曲线的研究</button></div></section>
      <section className="fw-block"><div className="fw-block-head"><h3>已接资金曲线的因子证据</h3><span>{d?.name || "资料读取中"} · {d?.pools.find(item => item.id === selection?.pool)?.label || ""} · {selection && feeLabel(Number(selection.fee))} · {selection?.period || ""}</span></div>{largestUnknown && <p className="fw-quote-caveat">报价模拟含缺价：已接入历史最高缺价 {pct(largestUnknown.unknownMax)}。相应净值不能当作可成交收益。</p>}{d && selection ? <div className="fw-table-wrap"><table className="fw-factor-table"><thead><tr><th>因子</th><th>研究用途</th><th>平均 RankIC</th><th>ICIR（不年化）</th><th>报价模拟 IR（年化）</th><th>查看</th></tr></thead><tbody>{d.factors.filter(item => item.available).map(factor => { const row = matchingMetrics(metrics.data,{...selection,curveFactor:factor.id},d.periods[selection.period]); return <tr key={factor.id}><th>{factor.name}<small className="fw-factor-context">{d.market} · {d.pools.find(pool => pool.id === selection.pool)?.label || "候选范围未提供"}</small></th><td>{factor.purpose || "原研究未写明"}</td><td title={row.ic ? `${row.ic.horizon}；形成日期 ${row.ic.range.join(" 至 ")}；${row.ic.nPeriods} 个有效月` : "当前研究条件未评价"}>{metric(row.ic?.mean)}</td><td>{metric(row.ic?.icir,2)}</td><td>{metric(row.ir?.ir,2)}</td><td><button type="button" onClick={() => changeSelection({curveFactor:factor.id},false,"study")}>诊断</button> <button type="button" onClick={() => changeSelection({curveFactor:factor.id},false,"progress")}>进度</button></td></tr>; })}</tbody></table></div> : <p className="fw-empty">研究目录读取后显示当前条件的因子表。</p>}<p className="fw-note">这张表只列研究端已有指标。RankIC、ICIR 衡量因子排序与未来结果的关系；IR 衡量 G5 相对同池基准的历史月差额是否稳定，含所选费用。不同用途不能按一个数字统一打分。</p></section>
      <details className="fw-block fw-overview-details"><summary>对象身份与焦点动量观察</summary><FocusMomentumSummary />{d && selection && <ResearchIdentity dataset={d} selection={selection} record={matched.ic} />}</details>
      <MetricReference />
      <details className="fw-block fw-process"><summary>从假设到人工决定：八步研究流程</summary><p className="fw-note">以下是通用核对项，不代表当前对象的实际进度。每项研究应绑定对象、版本、用途与范围；研究完成不等于效果成立，因子结论也不能代替完整策略验证。</p><ol className="fw-steps">{stages.map(([title, detail],i) => <li key={title}><span className="fw-step-index">{i+1}</span><div><strong>{title}</strong><p>{detail}</p></div><small>{i===stages.length-1 ? "人工决定" : "核对项"}</small></li>)}</ol></details>
      <section className="fw-block"><h3>五个实际问题</h3><div className="fw-questions">{questions.map(([q,a]) => <div key={q}><strong>{q}</strong><p>{a}</p></div>)}</div></section>
      <section className="fw-block"><h3>当前资料边界</h3>{curves.isLoading ? <p>正在读取研究目录…</p> : curves.error ? <p role="alert">研究目录暂不能读取。 <button type="button" onClick={() => void curves.refetch()}>重试</button></p> : <><p>已接入：{available.map(item => item.name).join("、") || "无"}。</p>{curves.data?.datasets.filter(item => !item.available).map(item => <p className="fw-unavailable" key={item.id}><strong>{item.name}</strong>：{item.unavailableReason}</p>)}</>}{largestUnknown && <p className="fw-quality-warning"><strong>报价不确定性：</strong>已接入历史中有一条 G5 报价账户最高缺价 {pct(largestUnknown.unknownMax)}（{curves.data?.datasets.find(item => item.id === largestUnknown.datasetId)?.name || "样本名称未记录"} / {curves.data?.datasets.find(item => item.id === largestUnknown.datasetId)?.factors.find(f => f.id === largestUnknown.factorId)?.name || "因子名称未记录"} / {d?.periods[largestUnknown.periodId]?.join(" 至 ") || "观察期未记录"} / {feeLabel(largestUnknown.feeBps)}）。这一段模拟净值不能当作可成交收益。</p>}{metrics.error && <p role="alert">专业指标暂不可用，请重试或查看原报告。</p>}</section>
      <div className="fw-legacy-links"><a href="/factors?tab=catalog">查看原因子目录</a><a href="/factors?tab=experiments">查看原实验记录</a><a href="/factors?tab=curves">打开原资金曲线页</a></div>
    </div>}
    {view === "observation" && <div className="fw-content"><FocusMomentumPanel /></div>}
    {view === "progress" && <div className="fw-content"><WorkflowProgress initialSelection={selection ? {datasetId:selection.dataset,factorId:selection.curveFactor} : undefined} onOpenDiagnostics={target => {
      if (!curves.data) return;
      setParams(diagnosticParams(curves.data, params, target));
    }} /></div>}
    {view === "study" && <div className="fw-content fw-study-content">
      <div className="fw-block-head"><p className="fw-note">当前诊断对应所选研究版本；完整进展、卡点与原始证据可回查。</p><button type="button" onClick={() => navigate("progress")}>查看此因子的研究进度</button></div>
      {metrics.error && <p className="fw-alert" role="alert">专业指标暂不能读取，请重试或查看原报告。 <button type="button" onClick={() => void metrics.refetch()}>重试</button></p>}
      {d && selection && <ResearchIdentity dataset={d} selection={selection} record={matched.ic} />}
      <ICPanel record={matched.ic} /><IRPanel record={matched.ir} />
      <MetricReference />
      <section className="fw-block"><div className="fw-block-head"><h3>五组资金线与已有对照</h3><span>沿用已保存的 G1–G5、共同池、回撤、缺价和增量表</span></div><div className="fw-embedded-curves"><FactorCurves /></div></section>
      <section className="fw-block"><h3>按需解释当前证据</h3><p>仅点击后才请求一次；返回的文字供人工核对，不改变因子状态或发起交易。</p><button type="button" className="fw-primary" disabled={!selected || agentBusy} onClick={() => void interpret()}>{agentBusy ? "正在读取解释…" : "解释当前证据"}</button>{agentError && agentContext === selectionKey && <p role="alert" className="fw-alert">{agentError}</p>}{agent && agentContext === selectionKey && <div className="fw-agent"><p>{agent.mode === "agent" ? "Agent 解读" : "研究检查卡（模型暂不可用）"} · 资料截至 {agent.asOf}</p>{agent.cards.map(card => <article key={card.id}><strong>{card.title}</strong><p>{card.text}</p><div className="fw-agent-links">{card.source && sourceHref(card.source) && <a href={sourceHref(card.source)!}>查看研究资料</a>}{card.methodSource && sourceHref(card.methodSource) && <a href={sourceHref(card.methodSource)!}>查看方法说明</a>}</div></article>)}{agent.limitations?.map((v,i) => <p key={i} className="fw-note">{v}</p>)}</div>}</section>
    </div>}
    {view === "compare" && <div className="fw-content"><section className="fw-intro"><div><h2>比较已有办法，再问真实组合是否受益</h2><p>同池共同基准和有限替代因子的报价结果可以对照。真实持仓、费率、换手和账户约束尚未接入，个人组合的边际收益与风险目前未评价。</p></div><button type="button" onClick={() => navigate("study")}>看所选因子资金线</button></section>
      <section className="fw-block"><div className="fw-block-head"><h3>所选因子的同池对照</h3><span>{d?.name || "资料读取中"} · {selected?.factor.name || ""}</span></div>{selected ? <div className="fw-metrics"><div><span>所选历史范围</span><strong>{selected.range.join(" 至 ")}</strong><small>{d?.pools.find(p => p.id===selection?.pool)?.label}；{selection && feeLabel(Number(selection.fee))}</small></div><div><span>相对共同池的 IR</span><strong>{metric(matched.ir?.ir,2)}</strong><small>同池 G5 月收益差额；年化口径</small></div><div><span>真实账户增量</span><strong>未评价</strong><small>需结合现有持仓和可执行交易成本</small></div></div> : <p className="fw-empty">所选资料尚不能比较，请在单因子页选择已接入范围。</p>}{selection && Number(selection.fee) !== 25 ? <div className="fw-empty" role="status">当前选择的{feeLabel(Number(selection.fee))}暂无已保存的简单办法增量对照；已有增量仅按单边 0.25% 费用计算。{d?.fees_bps.includes(25) && <button type="button" onClick={() => changeSelection({fee:"25"})}>切到单边 0.25% 查看增量</button>}</div> : incrementRows.length ? <div className="fw-table-wrap fw-increment"><table><caption>原研究保存的 G5 相对简单办法差额 · 单边费用 0.25%</caption><thead><tr><th>简单对手</th><th>每月平均差额</th><th>历史不确定范围</th><th>上涨月差额</th><th>下跌月差额</th><th>最大跌幅改善</th></tr></thead><tbody>{incrementRows.map(({key,label,item}) => <tr key={key}><th>{label}</th><td>{percentagePoints(asNumber(item.mean))}</td><td>{Array.isArray(item.descriptive95) ? `${percentagePoints(asNumber(item.descriptive95[0]))} 至 ${percentagePoints(asNumber(item.descriptive95[1]))}` : "未提供"}</td><td>{percentagePoints(asNumber(item.up_month_difference))}</td><td>{percentagePoints(asNumber(item.down_month_difference))}</td><td>{percentagePoints(asNumber(item.drawdown_difference))}</td></tr>)}</tbody></table><p className="fw-note">本表与当前 IR 使用同一单边 0.25% 费用；上涨月少赚和下跌月少亏一起看。历史不确定范围不等于未来保证。</p></div> : <p className="fw-empty">当前因子没有已保存的简单办法增量对照。</p>}<p className="fw-note">具体 G1–G5 收益、最大回撤、费用和夏普可在“单因子诊断”核对。</p></section>
      <ResearchUseReview />
      <section className="fw-block"><div className="fw-block-head"><h3>候选间的历史同步程度</h3><span>仅同一研究样本、同一候选范围和费用</span></div>{matched.correlation ? <Heatmap record={matched.correlation} names={factorNames} /> : <p className="fw-empty">当前筛选条件下没有可比的逐月账户相关记录。</p>}</section>
      <section className="fw-block"><h3>组合增量需要补齐什么</h3><div className="fw-questions"><div><strong>现有持仓</strong><p>先绑定真实 ETF、股票和现金，再量化与候选的重合。</p></div><div><strong>交易代价</strong><p>按真实账户费率、税费、换手和可成交价格比较。</p></div><div><strong>机会成本</strong><p>同时记录过滤掉的少亏与少赚，尤其大行情中错过的收益。</p></div><div><strong>新数据</strong><p>已看历史与未来独立观察分开；没有新证据时不升级用途。</p></div></div></section>
    </div>}
    {view === "records" && <div className="fw-content"><section className="fw-intro"><div><h2>研究资料与个人记录</h2><p>这里列出本页读取的研究材料与待补项目。手写记录只保存在当前浏览器，导出后仍需人工审阅和归档。</p></div></section>
      <section className="fw-block"><h3>从问题追到原始研究</h3><p><strong>{selected?.factor.name}</strong> · {selected?.factor.purpose || "用途见原研究"}</p><p>公式：{selected?.factor.formula || "未接入"}</p>{boundDefinition ? <><p>{traceability.question}</p><p>所选研究：{selected?.factor.name || "名称未记录"}；研究阶段：{boundDefinition.stage}。</p><p>研究条件固定于 {traceability.frozenAt.slice(0,10)}；这段历史已用于研究，尚需后续新数据验证。</p><p><a href={sourceHref(traceability.report)!}>原报告：结论、反例和完整研究路径</a></p></> : <p>所选研究的定义版本尚未核实，暂以原报告为准。</p>}<div className="fw-actions"><a href="/factors?tab=catalog">因子定义与生命周期记录</a><a href="/factors?tab=experiments">原实验与反例</a><a href="/fwd">单独查看前向观察账户</a><a href="/upgrades?goal=okr-28c527055f04">批量挖掘待办 · 暂缓</a></div></section>
      <section className="fw-block"><h3>研究来源</h3>{d?.source_report && sourceHref(d.source_report) ? <p><a href={sourceHref(d.source_report)!}>阅读所选研究原报告</a></p> : <p className="fw-empty">所选研究的原报告暂不能打开。</p>}<p className="fw-note">原报告包含样本范围、比较基准、费用和数据限制。页面更新不代表完成新的研究验证。</p></section>
      <section className="fw-block"><h3>未接入的能力</h3><ul className="fw-list"><li>跨市场宽基和 ETF 的合格历史成员、母指数对照，仍按各自资料状态核对。</li><li>真实账户持仓与增量、行业集中度、估值和真实费用尚未评价。</li><li>批量自动挖掘维持暂停；研究结果不会自动进入模拟盘或实盘。</li><li>未来新数据观察和人工生命周期决定尚需独立记录。</li></ul>{Array.isArray(metrics.data?.missingCapabilities) && <details><summary>尚缺资料</summary><ul className="fw-list">{metrics.data.missingCapabilities.filter((item): item is string => typeof item === "string").map(item => <li key={item}>{item}</li>)}</ul></details>}</section>
      <section className="fw-block"><h3>人工审阅草稿</h3><p className="fw-note">当前浏览器本地保存；不是研究登记、生产状态或交易指令。切换样本时草稿按样本、因子、范围和费用分别保存。</p><textarea aria-label="人工审阅草稿" value={draft} onChange={e => { setDraft(e.target.value); setDraftSaved(false); }} placeholder="记录改善的决定、证据反例、代价、保留或暂停的理由…" /><div className="fw-actions"><button type="button" onClick={() => { try { localStorage.setItem(draftKey,draft); setDraftSaved(true); } catch { setDraftSaved(false); } }}>保存到此浏览器</button><button type="button" onClick={() => exportDraft(draft,{ dataset: selection?.dataset, factor: selection?.curveFactor, pool: selection?.pool, period: selection?.period, fee: selection?.fee })}>下载审阅草稿</button>{draftSaved && <span role="status">已保存到此浏览器</span>}</div></section>
    </div>}
  </main>;
}
