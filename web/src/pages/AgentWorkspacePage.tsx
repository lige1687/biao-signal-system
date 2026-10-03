import MacroReadingPanel from '../features/market-understanding/MacroReadingPanel';
import {isMacroQuestion,isMacroFollowup} from '../features/market-understanding/macro-reading';
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "../components/AgentMarkdown";
import EvidenceCardView from "../components/EvidenceCardView";
import PlanDraftCard, { parsePlanDraft, planDraftFromArtifact } from "../components/PlanDraftCard";
import ColorBadge from "../components/ColorBadge";
import KlineChart, { DEFAULT_DISPLAY, type HighlightSpec } from "../components/KlineChart";
import { CopilotCardDispatcher } from "../components/copilot/CopilotCards";
import { findPriceMentions, validPriceLevels, priceLineKind, type AgentPriceLevel, type AgentPriceFocus } from "../components/agent/priceLinks";
import { ResultContext } from "../components/agent/ResultContext";
import AnswerText from "../components/agent/AnswerText";
import NextStepsBar from "../components/agent/NextStepsBar";
import BacktestSetupPanel, { type BacktestSetupPayload } from "../components/agent/BacktestSetupPanel";
import { subjectLabel, atrDiscussionDraft, detectUnsupportedExitRequest, SUPPORTED_EXITS_CN, windowLabelFromComparisonConfig } from "../utils/agentUx";
import { parseBacktestModule, resolveRoute } from "../utils/resolveRoute";
import { pollTask, recoverActiveTasks, requestBacktestTask, taskCreatedTextCn, taskStatusTextCn } from "../utils/backtestTasks";
import { readAgentEvents, shouldFollowOutput } from "./agentWorkspaceLogic";
import type { AgentSessionDTO, BacktestRequestStatus, EvidenceCard, NextStep, PlanArtifact, TradePreview } from "../types";
import "./agent-workspace.css";

type QuickCard = {
  symbol: string; display_name: string; as_of?: string; close: number;
  color_cn?: string; stage_cn?: string; risk_cn?: string;
  levels: AgentPriceLevel[];
  note_cn?: string;
};
type Turn = {
  id: string; who: "you" | "agent"; text: string; createdAt: string;
  grounded?: boolean; resolved?: string | null;
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null; quickCard?: QuickCard | null;
  status?: "working" | "complete" | "failed" | "stopped";
  stages?: { key: string; text: string }[];
  /** 可靠性一期 2026-09-14：prepared 事件已到——系统资料就绪，AI 解释未完成 */
  factsReady?: boolean;
  fallback?: string; verifyNote?: string; error?: string; history?: boolean;
  evidenceCard?: EvidenceCard | null; questionId?: number | null;
  taskId?: string; detailRun?: string | null; planArtifact?: PlanArtifact | null;
  /** UX 第一期：服务端推导的下一步动作（历史恢复同款） */
  nextSteps?: NextStep[] | null;
  /** 计划流程 P2：历史接口 plan_draft 绑定（该问题此前已保存的计划） */
  planDraft?: { plan_id: string; symbol: string; client_request_id: string } | null;
  /** UX 第一期：补测中文选择面板（绑定原问题与原标的） */
  setupPanel?: BacktestSetupPayload | null;
  panelSubmitting?: boolean;
  /** 补修二 2026-09-15：本次请求的稳定身份与快照（未完成时可同 cid 重试） */
  clientRequestId?: string;
  requestBody?: {
    session_id: string | null; context_kind: "symbol" | "global";
    symbol: string | null; message: string;
  };
  /** done 且 answer_state=incomplete：可重试再生成 */
  incompleteDone?: boolean;
  /** 历史恢复的回答带未完成标记（answer_incomplete） */
  answerIncomplete?: { reason?: string; reason_cn?: string } | null;
};
type Resource = { kind: "chart"; symbol: string; focus?: AgentPriceFocus } | { kind: "result"; id: string };
const QUICK = [
  { label: "最近机会", hint: "查看系统已发现的机会", kind: "scout" },
  { label: "今天看什么", hint: "整理今日关注清单", kind: "recommend" },
  { label: "持仓速览", hint: "持仓与进行中的计划", kind: "holdings" },
  { label: "记录基金成交", hint: "填写后核对确认", kind: "trade" },
  { label: "本周复盘", hint: "回顾交易与执行记录", kind: "review" },
];
const TITLES: Record<string, string> = { scout: "机会扫描", recommend: "今日关注清单", holdings: "持仓速览", review: "交易复盘", sizing: "仓位档位" };
const titleOf = (turn: Turn) => turn.preview ? "基金成交确认" : turn.card ? TITLES[turn.card.card_type] ?? "功能结果" : turn.quickCard ? `${turn.quickCard.display_name} · 分析` : "分析回复";

function QuickCardView({ card, onChart }: { card: QuickCard; onChart: (symbol: string, focus?: AgentPriceFocus) => void }) {
  const color = ({ "绿色": "green", "灰色": "gray", "黑色": "black" } as Record<string, string>)[card.color_cn ?? ""] ?? "unknown";
  return <section className="ar-quick-card" aria-label={`${card.display_name}关键数据`}>
    <header><div><strong>{card.display_name}</strong><span>{card.symbol} · {card.as_of ?? "数据日期未提供"}</span></div>
      <div className="ar-quick-head-actions">
        {card.color_cn && <ColorBadge color={color} colorCn={card.color_cn} descriptive />}
        {/* UX 第二轮：看图操作放在价位区同一屏，不用翻到动作条才找到 */}
        <button className="ar-quick-chart-btn" onClick={() => onChart(card.symbol)} title="在资料区打开该标的的最新图表">看图 ↗</button>
      </div></header>
    <dl className="ar-metrics"><div><dt>收盘价</dt><dd>{card.close}</dd></div>
      {card.stage_cn && <div><dt>当前阶段</dt><dd>{card.stage_cn}</dd></div>}
      {card.risk_cn && <div><dt>风险关注</dt><dd>{card.risk_cn}</dd></div>}</dl>
    {validPriceLevels(card.levels).length > 0 && <div className="ar-levels">
      <div className="ar-section-label">系统价位与条件（点价位在图上定位）</div>
      {validPriceLevels(card.levels).map((level, i) => <button key={i} onClick={() => onChart(card.symbol, {level, levels:validPriceLevels(card.levels), asOf:card.as_of})} title={`在图上定位该价位 · ${level.from_cn}`}>
        <span>{level.role}</span><strong>{level.price}</strong><span>距现价 {level.dist_pct}%</span><span>查看图表 ↗</span>
      </button>)}</div>}
    {card.note_cn && <p className="ar-footnote">{card.note_cn}</p>}
  </section>;
}

function TurnRow({ turn, onOpen, onChart, onAsk, expanded = false, sessionId, onPrepareBacktest, onSetupSubmit, onSetupCancel, onRetryIncomplete }: {
  turn: Turn; onOpen?: () => void; onChart: (symbol: string, focus?:AgentPriceFocus)=>void;
  onAsk: (message: string) => void; expanded?: boolean; sessionId?: string | null;
  /** UX 第一期：动作条上的"准备补测"→ 打开中文选择面板（绑定本回答的标的与问题） */
  onPrepareBacktest?: (turn: Turn, symbol: string) => void;
  onSetupSubmit?: (turn: Turn, module: string, exitVariant: string) => void;
  onSetupCancel?: (turnId: string) => void;
  /** 补修二 2026-09-15：未完成回答的同 cid 重试（复用原问题，不新增记录） */
  onRetryIncomplete?: (turn: Turn) => void;
}) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  /** UX 第一期：动作条"查看依据详情"展开本回答（区别于资料区的 expanded） */
  const [selfExpanded, setSelfExpanded] = useState(false);
  const fullText = turn.fallback || turn.text;
  const working = turn.status === "working";
  const card = !working && turn.quickCard && (!turn.resolved || turn.quickCard.symbol === turn.resolved) ? turn.quickCard : null;
  // 买点①编号定位已降级（2026-09-16 定向补修）：回答只带 quick_card.levels（随回答
  // 本身，可绑定）与 evidence_card.facts.buy_point_candidate_n（仅数量），**没有**
  // 候选快照/候选 ID/审阅版本——按 symbol 事后请求 buyPointReview 不能证明与回答
  // 生成时一致，故工作台编号一律渲染为普通文字。后端提供回答级候选绑定前不恢复。
  // 系统价位（quick_card.levels）随回答携带，定位功能保留。
  const markdown = (text: string) => <AgentMarkdown text={text}
    onBp={() => undefined} notableCount={0}
    priceLevels={card ? validPriceLevels(card.levels) : []}
    onPrice={card ? level => onChart(card.symbol, {level, levels:validPriceLevels(card.levels), asOf:card.as_of}) : undefined} />;
  if (turn.who === "you") return <div className="ar-user-message"><span>你</span><p>{turn.text}</p></div>;
  return <article className={`ar-answer ${working ? "is-working" : ""}`}>
    <header className="ar-answer-head"><div><span className="ar-agent-mark" aria-hidden="true">L</span><strong>{titleOf(turn)}</strong></div>
      <span className="ar-answer-meta">{working ? "正在整理" : turn.history ? "历史记录" : turn.grounded === true ? "依据系统数据" : turn.grounded === false ? "系统结果 / 请查看说明" : ""}</span>
    </header>
    {turn.stages?.length ? <details className="ar-progress"><summary>{working ? turn.stages[turn.stages.length - 1]?.text : "查看处理过程"}</summary>
      <ol>{turn.stages.map((s, i) => <li key={`${s.key}-${i}`}>{s.text}</li>)}</ol></details> : working && <p className="ar-working" role="status">正在读取资料，首次分析可能需要一些时间…</p>}
    {working && turn.factsReady && <p className="ar-working" role="status">系统资料已就绪（见下方卡片），AI 解释仍在生成…</p>}
    {turn.fallback && <p className="ar-notice">本次采用系统提供的结果，请结合下方说明查看。</p>}
    {/* UX 第二轮 2026-09-17：层级改为「结论 → 系统价位与条件 → 完整分析（可展开）
        → 依据卡」。系统价位卡通过 middle 插槽插在结论与正文之间；没有价位卡的
        回答（如历史恢复、清单类结果）顺序与原来一致，不造新结论。 */}
    <AnswerText text={fullText} markdown={markdown} expanded={expanded || working || selfExpanded}
      middle={turn.quickCard ? <QuickCardView card={turn.quickCard} onChart={onChart} /> : undefined} />
    {/* 可靠性一期：资料卡在 prepared 事件后即显示（working 期间也可看），
        失败/超时后同样保留——先于 AI 解释到达，不随模型失败消失。 */}
    {turn.evidenceCard && <EvidenceCardView card={turn.evidenceCard} forceDetailsOpen={expanded || selfExpanded} />}
    <CopilotCardDispatcher card={turn.card ?? null} preview={expanded ? null : turn.preview ?? null} />
    {!working && (() => {
      const bound = turn.resolved;
      if (turn.planArtifact && bound) {
        const adapted = planDraftFromArtifact(turn.planArtifact);
        return adapted ? <PlanDraftCard draft={adapted.draft} symbol={bound} questionId={turn.questionId} sessionId={sessionId} artifact={turn.planArtifact} savedPlanId={turn.planDraft?.plan_id ?? null} /> : null;
      }
      const draft = parsePlanDraft(turn.text);
      return draft && bound ? <PlanDraftCard draft={draft} symbol={bound} questionId={turn.questionId} sessionId={sessionId} legacy savedPlanId={turn.planDraft?.plan_id ?? null} /> : null;
    })()}
    {!working && turn.nextSteps && turn.nextSteps.length > 0 && (
      <NextStepsBar
        steps={turn.nextSteps}
        symbol={turn.resolved ?? turn.quickCard?.symbol ?? null}
        displayName={turn.evidenceCard?.facts?.display_name ?? turn.quickCard?.display_name}
        onDraft={onAsk}
        onExpand={() => setSelfExpanded(true)}
        onPrepareBacktest={(sym) => onPrepareBacktest?.(turn, sym)}
      />
    )}
    {turn.setupPanel && onSetupSubmit && (
      <BacktestSetupPanel
        setup={turn.setupPanel}
        submitting={turn.panelSubmitting}
        onSubmit={(m, e) => onSetupSubmit(turn, m, e)}
        onCancel={() => onSetupCancel?.(turn.id)}
      />
    )}
    {turn.detailRun && <Link className="btn small" to={`/backtest?run=${encodeURIComponent(turn.detailRun)}`}>查看该次回测详情（{turn.detailRun}）</Link>}
    {turn.verifyNote && <p className="ar-notice">{turn.verifyNote}</p>}
    {turn.error && <p className="ar-notice" role="alert">{turn.error}</p>}
    {turn.status === "failed" && (turn.quickCard || turn.evidenceCard) && <p className="ar-notice">AI 解释未完成；上面的系统资料仍然可用。</p>}
    {!working && turn.answerIncomplete && <p className="ar-notice">此回答当时未完成（{turn.answerIncomplete.reason_cn ?? "生成中断"}）；历史保留的是当时的部分原文，可重新提问生成。</p>}
    {!working && turn.incompleteDone && turn.requestBody && onRetryIncomplete && (
      <p><button className="btn small" onClick={()=>onRetryIncomplete(turn)}>重试生成这个回答（复用原问题与依据，不新增记录）</button></p>
    )}
    {!working && <footer className="ar-answer-actions">
      {onOpen && !turn.preview && <button onClick={onOpen}>展开到资料区</button>}
      {turn.resolved && <button onClick={() => onChart(turn.resolved!)}>查看图表</button>}
      <button onClick={() => onAsk(`关于${turn.resolved ?? turn.quickCard?.symbol ?? ""}「${titleOf(turn)}」，请进一步解释依据。`)}>继续追问</button>
      {fullText && <button onClick={async () => {
        try { await navigator.clipboard.writeText(fullText); setCopied(true); setCopyError(false); }
        catch { setCopyError(true); }
      }}>{copied ? "已复制" : "复制文字"}</button>}
      {copyError && <span role="status">复制失败，可选中文字复制</span>}
      <time dateTime={turn.createdAt}>{new Date(turn.createdAt).toLocaleString("zh-CN", {month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"})}</time>
    </footer>}
  </article>;
}

function HistoryPanel({ activeId, onPick, onNew, onClose, disabled }: { onClose: () => void; activeId: string | null; onPick: (s: AgentSessionDTO) => void; onNew: () => void; disabled: boolean }) {
  const [search, setSearch] = useState("");
  const q = useQuery({ queryKey: ["agentSessions"], queryFn: () => api.agentSessions(), staleTime: 30_000 });
  const sessions = (q.data ?? []).filter(s => `${s.title_cn} ${s.display_name ?? ""} ${s.symbol ?? ""} ${s.last_message_cn}`.toLowerCase().includes(search.toLowerCase()));
  const today = new Date().toLocaleDateString("zh-CN");
  let previous = "";
  return <aside className="ar-history" aria-label="历史对话">
    <div className="ar-history-head"><strong>我的对话</strong><button className="btn small" disabled={disabled} onClick={onNew}>＋ 新对话</button><button className="ar-icon-btn" onClick={onClose} aria-label="关闭历史对话">×</button></div>
    <label className="ar-search"><span className="ar-sr-only">搜索历史对话</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索标题或标的" type="search" /></label>
    <div className="ar-history-list">
      {q.isLoading && <p className="ar-footnote">正在读取历史…</p>}
      {q.isError && <div className="ar-notice">历史读取失败。<button onClick={() => q.refetch()}>重试</button></div>}
      {!q.isLoading && !q.isError && !sessions.length && <p className="ar-footnote">{search ? "没有匹配的对话" : "新的研究从一段对话开始"}</p>}
      {sessions.map(s => {
        const date = new Date(s.last_active_at).toLocaleDateString("zh-CN");
        const group = date === today ? "今天" : date;
        const show = group !== previous; previous = group;
        return <div key={s.session_id}>{show && <div className="ar-history-date">{group}</div>}
          <button className={`ar-history-item ${s.session_id === activeId ? "is-active" : ""}`} disabled={disabled} onClick={() => onPick(s)} aria-current={s.session_id === activeId ? "true" : undefined}>
            <span>{s.title_cn || "新对话"}</span><small>{subjectLabel(s.symbol, s.display_name)} · {new Date(s.last_active_at).toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"})}</small>
          </button></div>;
      })}
    </div>
    <div className="ar-history-footer">BIAO 研究工作台<br/><span>系统给出判定，AI 帮你读懂依据</span></div>
  </aside>;
}

function ChartResource({ resource, displayName, onFocus }: { displayName?: string | null; resource: Extract<Resource,{kind:"chart"}>; onFocus: (focus?:AgentPriceFocus)=>void }) {
  const [colorMode, setColorMode] = useState(DEFAULT_DISPLAY.colorMode);
  const detail = useQuery({queryKey:["detail",resource.symbol],queryFn:()=>api.detail(resource.symbol),staleTime:60_000});
  const c = detail.data;
  const focus = resource.focus;
  const highlight: HighlightSpec | undefined = focus ? {
    priceLines: [{ annoId: "agent-level", price: focus.level.price, label: focus.level.role,
      color: priceLineKind(focus.level) === "stop" ? "#a74422" : "#2458c6", kind: priceLineKind(focus.level) }],
    structureIds: [], dimOthers: false, ensureVisible: true,
  } : undefined;
  return <div className="ar-chart-resource">
    <header><div><strong>{subjectLabel(resource.symbol, displayName || c?.display_name)}</strong></div>
      <Link to={`/?symbol=${encodeURIComponent(resource.symbol)}`} className="cp-link">打开看盘页 ↗</Link></header>
    {c && <div className="ar-chart-status"><ColorBadge color={c.assessment.color} colorCn={c.assessment.color_cn} descriptive /><span>数据日期 {c.meta.last_bar_date ?? c.meta.data_time ?? "未提供"}</span></div>}
    {focus && <section className="ar-chart-focus" aria-label="当前定位价位">
      <header><div><strong>{focus.level.role} {focus.level.price}</strong><span>回复日期 {focus.asOf ?? "未提供"}</span></div><button onClick={()=>onFocus(undefined)}>清除定位</button></header>
      <div>{focus.levels.map((level,i)=><button key={i} aria-pressed={level===focus.level} onClick={()=>onFocus({...focus,level})}>{level.role} {level.price}</button>)}</div>
    </section>}
    <div className="ar-chart-controls"><span>K线着色</span><button className={colorMode === "biao_state" ? "selected" : ""} onClick={()=>setColorMode("biao_state")}>黑灰绿状态</button><button className={colorMode === "red_green" ? "selected" : ""} onClick={()=>setColorMode("red_green")}>红涨绿跌</button></div>
    {detail.isError ? <div className="ar-notice" role="alert">图表读取失败。<button onClick={()=>detail.refetch()}>重新读取</button></div> : !c ? <div className="ar-resource-loading" role="status">正在加载图表…</div> :
      <KlineChart payload={c.chart} display={{...DEFAULT_DISPLAY,colorMode}} highlight={highlight} />}
    {focus && <div className="ar-footnote"><p>价位来源：{focus.level.from_cn || "系统结构"}。系统计算的参考价位（研究代理），不代表已经触发买卖。</p>
      {focus.asOf && c?.meta.last_bar_date && focus.asOf !== c.meta.last_bar_date && <p className="ar-notice">回复与图表日期不同，请核对后使用。</p>}</div>}
  </div>;
}

export default function AgentWorkspacePage() {
  const [macroQuestion,setMacroQuestion]=useState<string|null>(new URLSearchParams(window.location.search).has('macro')?'当前宏观环境怎么看？':null);
  const queryClient = useQueryClient();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(() => window.innerWidth > 1100);
  const [resource, setResource] = useState<Resource | null>(null);
  const [chartSelection, setChartSelection] = useState<Extract<Resource,{kind:"chart"}> | null>(null);
  const [pinned, setPinned] = useState(false);
  const pinnedRef = useRef(pinned); pinnedRef.current = pinned;
  const [wideResource, setWideResource] = useState(false);
  const [busy, setBusy] = useState(false);
  const requestId = useRef(0);
  const generationRef = useRef(0);
  const requestLock = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const activeTurn = useRef<string | null>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const followRef = useRef(true);
  const [hasNew, setHasNew] = useState(false);
  const latest = turns.filter(t=>t.who === "agent" && t.status !== "working" && !t.preview).slice(-1)[0];
  const selectedResult = resource?.kind === "result" ? turns.find(t=>t.id === resource.id) : null;
  const patch = (id:string, value:Partial<Turn>) => setTurns(cur=>cur.map(t=>t.id === id ? {...t,...value}:t));

  useEffect(()=>()=>{requestId.current++; abortRef.current?.abort();},[]);
  useEffect(()=>{
    if (!turns.length) { bodyRef.current?.scrollTo({top:0}); return; }
    if (followRef.current) bodyRef.current?.scrollTo({top:bodyRef.current.scrollHeight});
    else setHasNew(true);
  },[turns]);
  useEffect(()=>{const el=taRef.current;if(el){el.style.height="auto";el.style.height=`${Math.min(el.scrollHeight,160)}px`;}},[input]);
  const toBottom = () => {followRef.current=true;setHasNew(false);bodyRef.current?.scrollTo({top:bodyRef.current.scrollHeight});};
  const draft = (message:string) => {setInput(message);if(window.innerWidth<=1100){setResource(null);setHistoryOpen(false);}taRef.current?.focus();};
  const inspect = (s:string, focus?:AgentPriceFocus) => {const next = {kind:"chart" as const,symbol:s,focus};setChartSelection(next);setResource(next);};
  /** 关闭资料区时同步清掉定位状态，重开不残留上一条信号高亮。 */
  const closeResource = () => {
    setResource(null);
    setChartSelection(cur => cur ? {kind:"chart", symbol:cur.symbol} : cur);
  };

  const newSession = () => {
    if(requestLock.current)return;
    generationRef.current += 1;
    requestId.current++;setLoadingHistory(false);
    setSessionId(null);setTurns([]);setSymbol(null);setResource(null);setChartSelection(null);setPinned(false);setInput("");setHistoryError("");setHasNew(false);followRef.current=true;taRef.current?.focus();
  };
  const loadSession = async (s:AgentSessionDTO) => {
    if(requestLock.current || loadingHistory)return;
    generationRef.current += 1;
    const ticket=++requestId.current;setLoadingHistory(true);setHistoryError("");
    try {
      const messages=await api.agentSessionMessages(s.session_id);
      if(ticket!==requestId.current)return;
      followRef.current=true;setHasNew(false);
      setTurns(messages.map((m,i)=>{
        const base:Turn={id:`${s.session_id}-${i}`,who:m.role === "user"?"you":"agent",text:m.content,grounded:m.grounded,createdAt:m.created_at,history:true,status:"complete",resolved:m.resolved_symbol??null,evidenceCard:m.evidence_card??null,planArtifact:m.plan_artifact??null,questionId:m.question_id??null,nextSteps:m.next_steps??null,planDraft:m.plan_draft??null,answerIncomplete:m.answer_incomplete??null};
        // 二轮复验：历史重试身份来自服务端投影（可核实的 cid+原始三输入），
        // 不得用当前会话/标的猜原请求；旧记录不可考→只有标签、无重试按钮。
        if(m.answer_incomplete && m.retry){
          base.incompleteDone=true;
          base.clientRequestId=m.retry.client_request_id;
          base.requestBody={session_id:s.session_id,context_kind:m.retry.context_kind==="symbol"?"symbol":"global",symbol:m.retry.symbol,message:m.retry.message};
        }
        return base;
      }));
      const sectorHistory=messages.some(m=>m.resolved_symbol===s.symbol && m.evidence_card?.facts?.subject_kind==="sector");
      setSessionId(s.session_id);setSymbol(s.symbol);setResource(s.symbol && !sectorHistory?{kind:"chart",symbol:s.symbol}:null);setChartSelection(s.symbol && !sectorHistory?{kind:"chart",symbol:s.symbol}:null);setPinned(false);setInput("");
      if(window.innerWidth<=1100)setHistoryOpen(false);
      // U3 返修：回到原会话时按会话重新接线任务轮询——此前在别处发起、
      // 归属本会话的补测任务在这里恢复卡片，而不是插进别的会话。
      const recGen=generationRef.current;
      void recoverActiveTasks(()=>generationRef.current===recGen,st=>{if(generationRef.current===recGen)onTaskStatus(st);},s.session_id);
    } catch(e){if(ticket===requestId.current)setHistoryError(`历史对话读取失败：${e instanceof Error?e.message:String(e)}`);}
    finally{if(ticket===requestId.current)setLoadingHistory(false);}
  };
  const onTaskStatus = (st: BacktestRequestStatus) => setTurns(cur => {
    const idx=cur.findIndex(t=>t.taskId===st.request_id);
    if(idx<0)return [...cur,{id:`task-${st.request_id}`,who:"agent",text:taskStatusTextCn(st),createdAt:new Date().toISOString(),grounded:true,status:"complete",taskId:st.request_id,detailRun:st.status==="completed"?st.run_id:null}];
    if(cur[idx].text===taskStatusTextCn(st))return cur;
    const next=[...cur];next[idx]={...next[idx],text:taskStatusTextCn(st),detailRun:st.status==="completed"?st.run_id:null};return next;
  });
  useEffect(()=>{const gen=generationRef.current;void recoverActiveTasks(()=>generationRef.current===gen,st=>{if(generationRef.current===gen)onTaskStatus(st);});},[]);

  const executeMessage = async (raw:string, forceDispatch=false, userAlreadyPushed=false, forceChat=false, symbolOverride?:string|null, outerLockHeld=false, fixed?:{cid:string; body:{session_id:string|null;context_kind:"symbol"|"global";symbol:string|null;message:string}}) => {
    const message=(fixed ? fixed.body.message : raw).trim();if(!message || (!outerLockHeld && requestLock.current) || loadingHistory)return;
    if(!outerLockHeld){requestLock.current=true;setBusy(true);}
    setInput("");followRef.current=true;setHasNew(false);
    const ticket=++requestId.current;const id=crypto.randomUUID();const createdAt=new Date().toISOString();activeTurn.current=id;
    const clientRequestId=fixed?fixed.cid:crypto.randomUUID();
    const effSymbol=fixed?fixed.body.symbol:(symbolOverride===undefined?symbol:symbolOverride);
    const requestBody={session_id:fixed?fixed.body.session_id:sessionId,context_kind:fixed?fixed.body.context_kind:(effSymbol?"symbol" as const:"global" as const),symbol:effSymbol,message};
    setTurns(cur=>[...cur,...(userAlreadyPushed?[]:[{id:crypto.randomUUID(),who:"you" as const,text:message,createdAt}]),{id,who:"agent",text:"",createdAt,status:"working",stages:[],clientRequestId,requestBody}]);
    let received="";
    try {
      const effectiveSymbol=effSymbol;
      if(!fixed && !forceChat && (forceDispatch || !effectiveSymbol || /买了|卖了|申购|赎回|报单|成交了/.test(message))) {
        const result=await api.copilotDispatch({message,symbol:effectiveSymbol});
        if(ticket!==requestId.current)return;
        if(!result.chat_fallback) {
          patch(id,{text:result.note_cn,card:result.card,preview:result.preview,grounded:true,status:"complete",resolved:result.symbol});
          return;
        }
      }
      const controller=new AbortController();abortRef.current=controller;
      const response=await fetch("/api/agent/chat/stream",{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,body:JSON.stringify({session_id:requestBody.session_id,context_kind:requestBody.context_kind,symbol:requestBody.symbol,message,client_request_id:clientRequestId})});
      if(!response.ok || !response.body)throw new Error(`服务返回 ${response.status}`);
      let completed=false;const stages:NonNullable<Turn["stages"]>=[];
      for await(const event of readAgentEvents(response.body)) {
        if(ticket!==requestId.current)return;
        if(event.event === "stage") {stages.push({key:String(event.data.key),text:String(event.data.text)});patch(id,{stages:[...stages]});}
        else if(event.event === "prepared") {
          // 可靠性一期：资料就绪即渲染（不等模型）。字段与 done 同源，
          // done 到达时覆盖为终值，不产生第二份记录。
          const p=event.data as {session_id?:string;resolved_symbol?:string|null;quick_card?:QuickCard;evidence_card?:EvidenceCard|null;next_steps?:NextStep[]|null};
          if(p.session_id)setSessionId(p.session_id);
          patch(id,{factsReady:true,resolved:p.resolved_symbol??null,quickCard:p.quick_card??null,evidenceCard:p.evidence_card??null,nextSteps:p.next_steps??null});
        }
        else if(event.event === "token") {received+=String(event.data.t??"");patch(id,{text:received});}
        else if(event.event === "error")throw new Error(String(event.data.message??event.data.error??"分析服务暂时不可用"));
        else if(event.event === "done") {
          completed=true;
          const d=event.data as {session_id?:string;resolved_symbol?:string|null;grounded?:boolean;fallback?:string;verify_note?:string;quick_card?:QuickCard;evidence_card?:EvidenceCard|null;plan_artifact?:PlanArtifact|null;question_id?:number|null;next_steps?:NextStep[]|null;answer_state?:string};
          if(d.session_id)setSessionId(d.session_id);
          if(d.resolved_symbol){
            setSymbol(d.resolved_symbol);
            if(!pinnedRef.current && d.evidence_card?.facts?.subject_kind !== "sector") {
              const card = d.quick_card?.symbol === d.resolved_symbol ? d.quick_card : undefined;
              const levels = card ? validPriceLevels(card.levels) : [];
              const mention = findPriceMentions(d.fallback || received, levels)[0];
              inspect(d.resolved_symbol, mention && card ? {level:mention.level, levels, asOf:card.as_of} : undefined);
            }
          }
          // 补修二：done 不都是完整答案——incomplete 按失败态展示并允许同 cid 重试
          const incomplete = d.answer_state === "incomplete";
          patch(id,{text:received,resolved:d.resolved_symbol,grounded:d.grounded,fallback:d.fallback,verifyNote:d.verify_note,quickCard:d.quick_card,evidenceCard:d.evidence_card??null,planArtifact:d.plan_artifact??null,questionId:d.question_id??null,nextSteps:d.next_steps??null,status:incomplete?"failed":"complete",incompleteDone:incomplete});
          void queryClient.invalidateQueries({queryKey:["agentSessions"]});
        }
      }
      if(!completed)throw new Error("连接提前结束，已保留收到的内容，可继续提问。");
    } catch(e){if(ticket===requestId.current)patch(id,{status:"failed",error:`未能完成：${e instanceof Error?e.message:String(e)}`});}
    finally {if(ticket===requestId.current){if(!outerLockHeld){requestLock.current=false;setBusy(false);}abortRef.current=null;activeTurn.current=null;}}
  };
  /** U1 返修（主控复核 2026-09-13）：直接说"帮我补测"与点"准备补测"按钮
   * 走**同一个准备入口**——先按原链路把问题建档（agentChat 记录原问题），
   * 然后在原回答上打开中文选择面板；不再追加"请说明要补测的模块"这类
   * 要求手敲代码的文字。原话已选的方法只作预选，未选的不代选；提交复用
   * 与按钮同一套共享函数（requestBacktestTask）。 */
  const handleBacktest = async (message: string) => {
    const frozenGen = generationRef.current;
    try {
      const reply = await api.agentChat({session_id:sessionId,context_kind:symbol?"symbol":"global",symbol,message,client_request_id:crypto.randomUUID()});
      if (generationRef.current !== frozenGen) return;
      setSessionId(reply.session_id);if(reply.resolved_symbol)setSymbol(reply.resolved_symbol);
      const boundSymbol = reply.resolved_symbol ?? null;
      const turnId = crypto.randomUUID();
      const evidenceCard = reply.evidence_card ?? null;
      setTurns(cur=>[...cur,{id:turnId,who:"agent",text:reply.reply,createdAt:new Date().toISOString(),grounded:reply.grounded,status:"complete",resolved:boundSymbol,evidenceCard,planArtifact:reply.plan_artifact??null,questionId:reply.question_id??null,nextSteps:reply.next_steps??null}]);
      if(!reply.question_id||!boundSymbol){setTurns(cur=>[...cur,{id:crypto.randomUUID(),who:"agent",text:!reply.question_id?"会话未建立，无法绑定补测任务。":"请先说明补测哪个标的（一次只跑一个标的）。",createdAt:new Date().toISOString(),status:"complete"}]);return;}
      const setupPanel={symbol:boundSymbol,displayName:evidenceCard?.facts?.display_name,sessionId:reply.session_id,questionId:reply.question_id,defaultModule:parseBacktestModule(message),windowLabel:windowLabelFromComparisonConfig(evidenceCard?.history_and_scope?.comparison_config),hint:null};
      setTurns(cur=>cur.map(t=>t.id===turnId?{...t,setupPanel}:t));
    }catch(e){if(generationRef.current===frozenGen)setTurns(cur=>[...cur,{id:crypto.randomUUID(),who:"agent",text:`补测准备失败：${e instanceof Error?e.message:String(e)}`,createdAt:new Date().toISOString(),status:"failed"}]);}
  };
  /** UX 第一期：动作条"准备补测"→ 打开中文选择面板。绑定本回答的会话问题；
   * 缺绑定（旧记录/无问题）时如实说明，不假装可用。
   * U2 返修：原问题有冻结窗口时如实带出（沿用原问题窗口），没有则区分说明。 */
  const openSetupPanel = (turn: Turn, sym: string) => {
    if (!sessionId || !turn.questionId) {
      setTurns(cur => [...cur, { id: crypto.randomUUID(), who: "agent" as const, text: "发起补测需要绑定当前对话里的一个提问——请就这个标的重新提一个问题（例如“它现在怎么看”），在新回答下点「准备补测」即可。", createdAt: new Date().toISOString(), grounded: true, status: "complete" as const }]);
      return;
    }
    patch(turn.id, { setupPanel: { symbol: sym, displayName: turn.evidenceCard?.facts?.display_name, sessionId, questionId: turn.questionId, defaultModule: null, windowLabel: windowLabelFromComparisonConfig(turn.evidenceCard?.history_and_scope?.comparison_config), hint: null } });
  };
  /** U3 返修（主控复核 2026-09-13）：面板提交在请求发出前冻结会话/问题/
   * 对象与世代；响应、错误、结束处理都先核对上下文——用户切到新会话后，
   * 迟到的旧任务消息绝不插入新会话视图（任务已创建并登记，回到原会话时
   * 由任务恢复重新接线）。同步忙锁（ref）+ 稳定请求身份（共享函数内
   * stableClientId，服务端幂等）共同防连续点击重复提交，不依赖组件渲染。 */
  const setupBusyRef = useRef(false);
  const submitSetup = async (turn: Turn, module: string, exitVariant: string) => {
    const setup = turn.setupPanel;
    if (!setup || setupBusyRef.current || turn.panelSubmitting) return;
    setupBusyRef.current = true;
    patch(turn.id, { panelSubmitting: true });
    const frozenGen = generationRef.current;
    try {
      const task = await requestBacktestTask({sessionId: setup.sessionId, questionId: setup.questionId, symbol: setup.symbol, module, exitVariant});
      if (generationRef.current !== frozenGen) { patch(turn.id, { setupPanel: null, panelSubmitting: false }); return; }
      patch(turn.id, { setupPanel: null, panelSubmitting: false });
      setTurns(cur => [...cur, { id: `task-${task.request_id}`, who: "agent", text: taskCreatedTextCn(task), createdAt: new Date().toISOString(), grounded: true, status: "complete", taskId: task.request_id, detailRun: task.status === "completed" ? task.run_id : null }]);
      pollTask(task.request_id, () => generationRef.current === frozenGen, onTaskStatus);
    } catch (e) {
      patch(turn.id, { panelSubmitting: false });
      if (generationRef.current === frozenGen) {
        setTurns(cur => [...cur, { id: crypto.randomUUID(), who: "agent", text: `补测创建失败：${e instanceof Error ? e.message : String(e)}`, createdAt: new Date().toISOString(), status: "failed" }]);
      }
    } finally { setupBusyRef.current = false; }
  };
  const send = async (raw:string, forceDispatch=false) => {
    const message=raw.trim();if(!message||requestLock.current||loadingHistory)return;
    if(!forceDispatch&&(isMacroQuestion(message)||(macroQuestion!==null&&isMacroFollowup(message)))){setMacroQuestion(message);setInput('');return;}
    requestLock.current=true;setBusy(true);
    const gen=generationRef.current;
    try{
      if(forceDispatch){await executeMessage(message,true,false,false,undefined,true);return;}
      setInput("");setTurns(cur=>[...cur,{id:crypto.randomUUID(),who:"you",text:message,createdAt:new Date().toISOString()}]);
      const route=await resolveRoute({message,sessionId,symbol});if(!guardGeneration(gen))return;
      if(route.resolve.resolved_symbol)setSymbol(route.resolve.resolved_symbol);
      route.resolve.clarification.forEach(c=>setTurns(cur=>[...cur,{id:crypto.randomUUID(),who:"agent",text:c.question_cn,createdAt:new Date().toISOString(),grounded:true,status:"complete"}]));
      if(route.action==="backtest"){
        // UX 第一期（场景5）：用户点名当前引擎没有的退出方式（如 ATR 止损）→
        // 如实说明暂未支持，不静默替换、不声称已比较。
        // U1 返修：原草稿含"补测"会被再次判成补测请求形成死循环——换用
        // 不含触发词的讨论草稿，并提供"继续讨论"动作（点击放回输入框，
        // 可改后发送），保证讨论入口真实可用。
        const unsupported=detectUnsupportedExitRequest(message);
        if(unsupported){
          const sym=route.resolve.resolved_symbol??symbol;
          setTurns(cur=>[...cur,{id:crypto.randomUUID(),who:"agent",createdAt:new Date().toISOString(),grounded:true,status:"complete",resolved:sym,nextSteps:[{kind:"draft_discussion",label_cn:"继续讨论（不做数值比较）",draft_cn:atrDiscussionDraft(sym)}],text:`这项比较暂未支持：当前补测引擎的退出方式只有${SUPPORTED_EXITS_CN}；${unsupported}不在其中。我不会把它偷偷换成别的退出规则，也没有做过这项比较。\n\n想继续的话：① 就支持的退出方式补测——点下方「准备补测」之前，先就这个标的提一个问题；② 点「继续讨论」把思路问题放回输入框，可修改后发送。`}]);
          return;
        }
        await handleBacktest(message);return;
      }
      await executeMessage(message,route.action==="dispatch",true,route.action==="chat",route.resolve.resolved_symbol??symbol,true);
    }catch{if(guardGeneration(gen))await executeMessage(message,false,true,false,undefined,true);}
    finally{requestLock.current=false;setBusy(false);}
  };
  const guardGeneration=(gen:number)=>generationRef.current===gen;
  /** 补修二 2026-09-15：未完成回答的同 cid 重试——复用原问题、原会话与原
   * 对象快照（request_hash 一致才不会 409），服务端 resume 重新生成，不新增问题。 */
  const retryIncomplete = (turn: Turn) => {
    if (busy || !turn.requestBody || !turn.clientRequestId) return;
    void executeMessage(turn.requestBody.message, false, true, true, turn.requestBody.symbol, false,
      { cid: turn.clientRequestId, body: turn.requestBody });
  };
  const stopReceiving = () => {
    requestId.current++;generationRef.current+=1;abortRef.current?.abort();abortRef.current=null;requestLock.current=false;setBusy(false);
    if(activeTurn.current)patch(activeTurn.current,{status:"stopped",error:"已停止接收。后台可能仍在完成分析，可稍后查看历史记录。"});
    activeTurn.current=null;
  };
  const quick = (kind:string,label:string) => {
    if(kind === "trade"){draft("我买了 ");return;}
    void send(label,true);
  };

  return <ResultContext.Provider value={{inspectSymbol:inspect,ask:draft}}>
    <div className={`ar-workspace ${historyOpen?"has-history":""} ${resource?"has-resource":""} ${wideResource?"wide-resource":""}`}>
      {historyOpen && <HistoryPanel activeId={sessionId} onPick={loadSession} onNew={newSession} onClose={()=>setHistoryOpen(false)} disabled={busy||loadingHistory} />}
      <main className="ar-chat">
        <header className="ar-toolbar"><div><button className="ar-icon-btn" onClick={()=>setHistoryOpen(v=>!v)} aria-label={historyOpen?"收起历史对话":"展开历史对话"} aria-expanded={historyOpen}>☰</button><h1>研究工作台</h1><span className="ar-toolbar-caption">把问题说清，把依据看清</span></div>
          <div>{(symbol||latest) && <button className="btn small" onClick={()=>resource?closeResource():symbol?inspect(symbol):latest&&setResource({kind:"result",id:latest.id})}>{resource?"收起资料":"查看资料"}</button>}<button className="btn small" disabled={busy} onClick={newSession}>新对话</button></div></header>
        {historyError && <p className="ar-notice" role="alert">{historyError}</p>}
        <div className="ar-messages" ref={bodyRef} onScroll={()=>{const el=bodyRef.current;if(el){followRef.current=shouldFollowOutput(el.scrollTop,el.clientHeight,el.scrollHeight);if(followRef.current)setHasNew(false);}}}>
          {macroQuestion!==null&&<MacroReadingPanel initialQuestion={macroQuestion} onClose={()=>setMacroQuestion(null)}/>}
          {turns.some(t=>t.history) && <p className="ar-footnote">以下是按当时内容恢复的历史记录（回答、数据日期与动作都是当时的）；右侧图表展示的是当前最新数据，两者日期可能不同。</p>}
          {loadingHistory && <div className="ar-working" role="status">正在恢复对话…</div>}
          {!turns.length && !loadingHistory && <div className="ar-welcome"><span className="ar-welcome-mark" aria-hidden="true">BIAO</span><h2>今天，从哪个问题开始？</h2><p>查看机会、讨论标的，或回顾你的交易。<br/>分析与资料会在这里逐步展开。</p>
            <div className="ar-start-actions">{QUICK.filter(q=>q.kind!=="recommend").map(q=><button key={q.kind} onClick={()=>quick(q.kind,q.label)}><strong>{q.label}</strong><span>{q.hint}</span><b aria-hidden="true">↗</b></button>)}</div>
            <div className="ar-examples"><span>也可以直接问</span>{["通信设备怎么看","515880 现在是什么阶段"].map(q=><button key={q} onClick={()=>draft(q)}>{q}</button>)}</div>
          </div>}
          {turns.map(turn=><TurnRow key={turn.id} turn={turn} onOpen={()=>setResource({kind:"result",id:turn.id})} onChart={inspect} onAsk={draft} sessionId={sessionId} onPrepareBacktest={openSetupPanel} onSetupSubmit={submitSetup} onSetupCancel={(id)=>patch(id,{setupPanel:null})} onRetryIncomplete={retryIncomplete} />)}
        </div>
        {hasNew && <button className="ar-new-output" onClick={toBottom}>回到最新回复 ↓</button>}
        <footer className="ar-composer">
          <div className="ar-composer-context"><span>当前讨论</span><strong>{subjectLabel(symbol, [...turns].reverse().find(t=>t.resolved===symbol)?.evidenceCard?.facts?.display_name)}</strong>{symbol && <button disabled={busy} onClick={()=>setSymbol(null)}>切回全局</button>}<span className="ar-context-hint">{resource?.kind === "chart" && resource.symbol!==symbol?`正在查看 ${resource.symbol}，提问仍沿用当前讨论`:""}</span></div>
          <div className="ar-input-box"><label className="ar-sr-only" htmlFor="agent-question">输入问题</label><textarea id="agent-question" ref={taRef} rows={2} value={input} onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{if(e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode!==229){e.preventDefault();if(!busy)void send(input);}}}
            placeholder={busy?"可以先写下一条问题，当前回复完成后再发送":"输入问题，或说出标的名称 / 代码…"} />
            <div className="ar-input-bottom"><span>Enter 发送 · Shift + Enter 换行</span>{busy?<button className="btn ar-stop" onClick={stopReceiving}>停止接收</button>:<button className="btn primary" disabled={!input.trim()||loadingHistory} onClick={()=>void send(input)}>发送 ↑</button>}</div>
          </div>
          <div className="ar-composer-tools"><button disabled={busy||loadingHistory} onClick={()=>setMacroQuestion('当前宏观环境怎么看？')}>宏观解读</button>{QUICK.map(q=><button key={q.kind} disabled={busy||loadingHistory} onClick={()=>quick(q.kind,q.label)}>{q.label}</button>)}</div>
          {input.startsWith("我买了") && <p className="ar-footnote">填写实际成交，例如“我买了1万元012414”。发送后先核对确认卡，确认后才记入基金台账。</p>}
        </footer>
      </main>
      {resource && <aside className="ar-resource" aria-label="资料区"><header className="ar-resource-head"><strong>研究资料</strong><div><button className={pinned?"selected":""} onClick={()=>setPinned(v=>!v)} aria-pressed={pinned}>{pinned?"已固定":"固定"}</button><button onClick={()=>setWideResource(v=>!v)}>{wideResource?"还原":"放大"}</button><button onClick={closeResource} aria-label="关闭资料区">×</button></div></header>
        <div className="ar-resource-tabs">{(chartSelection || symbol) && <button className={resource.kind === "chart"?"selected":""} onClick={()=>chartSelection?setResource(chartSelection):symbol&&inspect(symbol)}>标的图表</button>}{latest && <button className={resource.kind === "result"?"selected":""} onClick={()=>setResource({kind:"result",id:latest.id})}>对话结果</button>}<span>{pinned?"保持当前资料":"随分析展开"}</span></div>
        <div className="ar-resource-content">{resource.kind === "chart"?<ChartResource key={resource.symbol} resource={resource} displayName={[...turns].reverse().find(t=>t.resolved===resource.symbol)?.evidenceCard?.facts?.display_name} onFocus={focus=>inspect(resource.symbol,focus)}/>:selectedResult?<ResultContext.Provider value={{inspectSymbol:inspect,ask:draft,readOnly:true}}><TurnRow turn={selectedResult} onChart={inspect} onAsk={draft} expanded sessionId={sessionId} onPrepareBacktest={openSetupPanel} onSetupSubmit={submitSetup} onSetupCancel={(id)=>patch(id,{setupPanel:null})} onRetryIncomplete={retryIncomplete} /></ResultContext.Provider>:<p className="ar-footnote">选择一条回复查看详情。</p>}</div>
      </aside>}
    </div>
  </ResultContext.Provider>;
}
