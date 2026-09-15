import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { matchPath, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import EvidenceCardView from "./EvidenceCardView";
import { CopilotCardDispatcher } from "./copilot/CopilotCards";
import ProvenanceBadge from "./ProvenanceBadge";
import AnswerText from "./agent/AnswerText";
import NextStepsBar from "./agent/NextStepsBar";
import BacktestSetupPanel, { type BacktestSetupPayload } from "./agent/BacktestSetupPanel";
import { subjectLabel, atrDiscussionDraft, detectUnsupportedExitRequest, SUPPORTED_EXITS_CN, windowLabelFromComparisonConfig } from "../utils/agentUx";
import { useAgentConsole } from "../App";
import { readAgentEvents } from "../pages/agentWorkspaceLogic";
import { parseBacktestModule, resolveRoute } from "../utils/resolveRoute";
import {
  pollTask, recoverActiveTasks, requestBacktestTask, taskCreatedTextCn, taskStatusTextCn,
} from "../utils/backtestTasks";
import PlanDraftCard, {
  parsePlanDraft, planDraftFromArtifact,
} from "./PlanDraftCard";
import type {
  BacktestRequestStatus, EvidenceCard, NextStep, PlanArtifact,
  TraceItem, TradePreview,
} from "../types";

type Turn = {
  /** U1/U3 返修：补测准备面板挂在原回答上（与工作台同一形态），需要 id 定位 */
  id?: string;
  who: "you" | "agent";
  text: string;
  grounded?: boolean;
  trace?: TraceItem[];
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
  /** 03B-R2 契约3：本轮证据卡 */
  evidenceCard?: EvidenceCard | null;
  resolved?: string | null;
  questionId?: number | null;
  /** 03B-R2 契约4：补测任务卡（queued/running 原地更新，终态只处理一次） */
  taskId?: string;
  detailRun?: string | null;
  /** 03B-R3 S5：服务端计划产物 */
  planArtifact?: PlanArtifact | null;
  /** UX 第一期：服务端推导的下一步动作（与工作台同一份结构） */
  nextSteps?: NextStep[] | null;
  /** U1/U3 返修：补测中文选择面板（绑定本回答的问题与标的） */
  setupPanel?: BacktestSetupPayload | null;
  panelSubmitting?: boolean;
  /** 可靠性一期 2026-09-14：讨论路径改走流式端点后的轮次状态 */
  status?: "working" | "complete" | "failed" | "stopped";
  stages?: { key: string; text: string }[];
  /** prepared 事件已到——系统资料就绪，AI 解释未完成 */
  factsReady?: boolean;
  fallback?: string;
  verifyNote?: string;
  /** 补修二 2026-09-15：本次请求的稳定身份与快照（未完成时可同 cid 重试） */
  clientRequestId?: string;
  requestBody?: {
    session_id: string | null; context_kind: "symbol" | "global";
    symbol: string | null; message: string;
  };
  /** done 且 answer_state=incomplete：可重试再生成 */
  incompleteDone?: boolean;
  /** 2026-09-15 提问稳定性：done answer_state=failed 且 retryable——可同 cid 重试 */
  failedRetryable?: boolean;
};

const SYMBOL_CHIPS = ["这个买点为什么是买点", "技术面讨论", "给这个买点建计划", "这个标的我的计划"];
/** 全局快捷指令：走 copilot dispatch（零 LLM 直达流水线），未命中回落通用讨论。 */
const GLOBAL_CHIPS = ["今天看什么", "持仓速览", "我要报单", "本周复盘"];

/** U4 返修：控制台单条对话抽为组件——本地保存"查看依据详情"的展开状态，
 * 点击动作条按钮时与工作台同行为：定位到本回答并真正展开依据区；
 * U1/U3：补测面板挂在原回答上（setupPanel），提交/取消都在本条内完成。 */
function ConsoleTurnView({ index, turn, symbol, sessionId, navigate, registerRef, scrollToTurn, onDraft, onPrepareBacktest, onSetupSubmit, onSetupCancel, onRetryIncomplete }: {
  index: number;
  turn: Turn;
  symbol: string | null;
  sessionId: string | null;
  navigate: (path: string) => void;
  registerRef: (index: number, el: HTMLDivElement | null) => void;
  scrollToTurn: (index: number) => void;
  onDraft: (message: string) => void;
  onPrepareBacktest: (turn: Turn, sym: string) => void;
  onSetupSubmit: (turn: Turn, module: string, exitVariant: string) => void;
  onSetupCancel: (turn: Turn) => void;
  /** 补修二 2026-09-15：未完成回答的同 cid 重试 */
  onRetryIncomplete: (turn: Turn) => void;
}) {
  const [detailsExpanded, setDetailsExpanded] = useState(false);
  const working = turn.status === "working";
  return (
    <div className="turn" ref={(el) => registerRef(index, el)}>
      <div className="who">{turn.who === "you" ? "你" : "agent"}</div>
      {turn.who === "agent" && working && (
        <div className="muted" role="status">
          {turn.factsReady
            ? "系统资料已就绪（见下方依据卡），AI 解释仍在生成…"
            : (turn.stages?.[turn.stages.length - 1]?.text ?? "已提交，等待系统确认…")}
        </div>
      )}
      {turn.who === "you" && <div className="msg">{turn.text}</div>}
      {turn.who === "agent" && !working && (
        /* 控制台无主图上下文：onBp 置空、notableCount=0，「买点①」chip 渲染为不可点的暗态 */
        /* FR-3: plan-draft 围栏块从正文剔除（卡片已单独渲染原始 JSON），防裸 JSON 进对话流 */
        /* UX 第一期：首屏/正文拆段与工作台共用同一组件（expanded=控制台保持全文） */
        <AnswerText
          text={(turn.fallback || turn.text).replace(/```plan-draft[\s\S]*?```/g, "").trim()}
          markdown={(t) => (
            <AgentMarkdown text={t} onBp={() => undefined} notableCount={0} />
          )}
          expanded
        />
      )}
      {turn.who === "agent" && turn.evidenceCard && (
        <EvidenceCardView card={turn.evidenceCard} forceDetailsOpen={detailsExpanded} />
      )}
      {turn.who === "agent" && turn.status !== "working" && turn.nextSteps && turn.nextSteps.length > 0 && (
        <NextStepsBar
          steps={turn.nextSteps}
          symbol={turn.resolved ?? symbol}
          displayName={turn.evidenceCard?.facts?.display_name}
          onDraft={onDraft}
          onExpand={() => { setDetailsExpanded(true); scrollToTurn(index); }}
          onPrepareBacktest={(sym) => onPrepareBacktest(turn, sym)}
        />
      )}
      {turn.setupPanel && (
        <BacktestSetupPanel
          setup={turn.setupPanel}
          submitting={turn.panelSubmitting}
          onSubmit={(m, e) => onSetupSubmit(turn, m, e)}
          onCancel={() => onSetupCancel(turn)}
        />
      )}
      {(() => {
        // 03B-R3 S5：优先服务端产物；文本解析仅旧格式兼容（来源不可考）
        const bound = turn.resolved ?? symbol;
        if (turn.planArtifact && bound) {
          const adapted = planDraftFromArtifact(turn.planArtifact);
          if (adapted) {
            return (
              <PlanDraftCard
                draft={adapted.draft}
                symbol={bound}
                questionId={turn.questionId}
                sessionId={sessionId}
                artifact={turn.planArtifact}
              />
            );
          }
        }
        const draft = parsePlanDraft(turn.text);
        return draft && bound ? (
          <PlanDraftCard
            draft={draft}
            symbol={bound}
            questionId={turn.questionId}
            sessionId={sessionId}
            legacy={!turn.planArtifact}
          />
        ) : null;
      })()}
      {turn.who === "agent" && turn.detailRun && (
        <button
          className="btn small"
          style={{ marginTop: 4 }}
          onClick={() => navigate(`/backtest?run=${encodeURIComponent(turn.detailRun!)}`)}
        >
          查看该次回测详情（{turn.detailRun}）
        </button>
      )}
      {turn.who === "agent" && (turn.card || turn.preview) && (
        <CopilotCardDispatcher
          card={turn.card ?? null}
          preview={turn.preview ?? null}
        />
      )}
      {turn.who === "agent" && turn.trace && turn.trace.length > 0 && (
        <ProvenanceBadge items={turn.trace} />
      )}
      {turn.who === "agent" && turn.verifyNote && (
        <div className="grounded-tag warn">{turn.verifyNote}</div>
      )}
      {turn.who === "agent" && turn.status === "failed" && turn.evidenceCard && (
        <div className="grounded-tag warn">AI 解释未完成；上面的系统资料仍然可用。</div>
      )}
      {turn.status === "failed" && turn.incompleteDone && turn.requestBody && (
        <p>
          <button className="btn small" onClick={() => onRetryIncomplete(turn)}>
            重试生成这个回答（复用原问题与依据，不新增记录）
          </button>
        </p>
      )}
      {turn.status === "failed" && turn.failedRetryable && turn.requestBody && (
        <p>
          <button className="btn small" onClick={() => onRetryIncomplete(turn)}>
            重试这个问题（沿用原请求，不重复记录）
          </button>
        </p>
      )}
      {turn.who === "agent" && turn.grounded === false && (
        <div className="grounded-tag warn">判定层数据直出（LLM 不可用或未过校验）</div>
      )}
    </div>
  );
}

/**
 * 全局 agent 控制台：上下文跟随当前页面（详情页=该标的，其余=全局）。
 * 能力 chips 一键发起；多轮记忆由后端会话层承载。
 */
export default function AgentConsole() {
  const { open, closeConsole } = useAgentConsole();
  const location = useLocation();
  const symbol = useMemo(() => {
    const m = matchPath("/symbol/:symbol", location.pathname);
    return m?.params.symbol ?? null;
  }, [location.pathname]);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const turnRefs = useRef(new Map<number, HTMLDivElement>());
  // U3 返修：面板提交的同步忙锁（不依赖组件渲染周期）
  const setupBusyRef = useRef(false);
  const navigate = useNavigate();
  // 会话世代计数：切标的 / 开新会话 时 +1，发起提问时捕获当前值。
  // 回复到达时世代已变 → 说明期间发生过重置，丢弃回复，不回灌 sessionId/turns。
  // U1/U3 返修：与工作台统一命名为 generationRef，两入口同一套流程词汇。
  const generationRef = useRef(0);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns]);

  /** 03B-R2 契约4：五状态逐一处理——queued/running 原地更新任务卡；终态收口一次。 */
  const onTaskStatus = (st: BacktestRequestStatus) => {
    setTurns((cur) => {
      const idx = cur.findIndex((t) => t.taskId === st.request_id);
      const next = [...cur];
      if (idx >= 0) {
        if (next[idx].text === taskStatusTextCn(st)) return cur;
        next[idx] = { ...next[idx], text: taskStatusTextCn(st),
                      detailRun: st.status === "completed" ? st.run_id : null };
        return next;
      }
      return [...next, {
        who: "agent" as const, grounded: true, taskId: st.request_id,
        text: taskStatusTextCn(st),
        detailRun: st.status === "completed" ? st.run_id : null,
      }];
    });
  };

  // 03B-R2 契约4：控制台打开/挂载即恢复（服务端列表为权威）
  useEffect(() => {
    const gen = generationRef.current;
    void recoverActiveTasks(
      () => generationRef.current === gen,
      (st) => {
        if (generationRef.current !== gen) return;
        onTaskStatus(st);
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 可靠性一期（2026-09-14）：讨论路径从一次性 agentChat 改走流式端点——
  // prepared 事件先渲染系统资料卡，模型正文逐段追加；失败保留已显示资料。
  // 补测准备（handleBacktest）仍走普通接口，两套接口按既有分工并存。
  // 补修二（主控复核 2026-09-15）：请求带稳定 client_request_id；done 且
  // answer_state=incomplete 的回答按失败态展示，可同 cid 重试再生成。
  const [pending, setPending] = useState(false);

  const runStream = async (
    body: { session_id: string | null; context_kind: "symbol" | "global";
            symbol: string | null; message: string; client_request_id: string },
    turnId: string, gen: number,
  ) => {
    const patchTurn = (value: Partial<Turn>) => setTurns((cur) => cur.map(
      (t) => (t.id === turnId ? { ...t, ...value } : t),
    ));
    const controller = new AbortController();
    let received = "";
    let completed = false;
    try {
      const response = await fetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify(body),
      });
      if (!response.ok || !response.body) throw new Error(`服务返回 ${response.status}`);
      const stages: NonNullable<Turn["stages"]> = [];
      for await (const event of readAgentEvents(response.body)) {
        // 迟到防护：期间切标的/开新会话（世代已变）→ 丢弃后续事件，不串入新会话
        if (generationRef.current !== gen) { controller.abort(); return; }
        if (event.event === "stage") {
          const key = String(event.data.key);
          // 等待心跳：同键连续只保留最新一条（与工作台同一规则）
          if (key === "waiting" && stages.length && stages[stages.length - 1].key === "waiting") {
            stages[stages.length - 1] = { key, text: String(event.data.text) };
          } else {
            stages.push({ key, text: String(event.data.text) });
          }
          patchTurn({ stages: [...stages] });
        } else if (event.event === "prepared") {
          const p = event.data as {
            session_id?: string; resolved_symbol?: string | null;
            evidence_card?: EvidenceCard | null; next_steps?: NextStep[] | null;
          };
          if (p.session_id) setSessionId(p.session_id);
          patchTurn({
            factsReady: true,
            resolved: p.resolved_symbol ?? null,
            evidenceCard: p.evidence_card ?? null,
            nextSteps: p.next_steps ?? null,
          });
        } else if (event.event === "token") {
          received += String(event.data.t ?? "");
          patchTurn({ text: received });
        } else if (event.event === "error") {
          throw new Error(String(event.data.message ?? event.data.error ?? "分析服务暂时不可用"));
        } else if (event.event === "done") {
          completed = true;
          const d = event.data as {
            session_id?: string; resolved_symbol?: string | null; grounded?: boolean;
            fallback?: string; verify_note?: string; question_id?: number | null;
            plan_artifact?: PlanArtifact | null; next_steps?: NextStep[] | null;
            answer_state?: string; retryable?: boolean;
          };
          if (d.session_id) setSessionId(d.session_id);
          // done 不都是完整答案（补修二）：incomplete 按失败态展示，可同 cid 重试；
          // 2026-09-15：answer_state=failed（准备/保存失败）同样按失败态，
          // retryable=true 时给同 cid 重试入口（问题已保留，不重复记录）
          const incomplete = d.answer_state === "incomplete";
          const failed = d.answer_state === "failed";
          patchTurn({
            text: received || (d.fallback ?? ""),
            status: (incomplete || failed) ? "failed" : "complete",
            grounded: d.grounded,
            fallback: d.fallback,
            verifyNote: d.verify_note,
            resolved: d.resolved_symbol ?? null,
            questionId: d.question_id ?? null,
            planArtifact: d.plan_artifact ?? null,
            nextSteps: d.next_steps ?? null,
            incompleteDone: incomplete,
            failedRetryable: failed && d.retryable === true,
          });
        }
      }
      if (!completed && generationRef.current === gen) {
        patchTurn({
          status: "failed",
          failedRetryable: true,
          text: received,
          verifyNote: "连接提前结束；已保留收到的内容。重试同一问题会复用原问题，不会重复记录。",
        });
      }
    } catch (e) {
      if (generationRef.current !== gen) return;
      patchTurn({
        status: "failed",
        failedRetryable: true,
        text: received,
        verifyNote: `未能完成：${e instanceof Error ? e.message : String(e)}（可点「重试」沿用原请求再试，不重复记录）`,
      });
    } finally {
      // 世代已变时由 resetConversation 负责清 pending，避免盖掉新请求的忙态
      if (generationRef.current === gen) setPending(false);
    }
  };

  const send = (message: string) => {
    const text = message.trim();
    if (!text || pending) return;
    const gen = generationRef.current;
    const body = {
      session_id: sessionId,
      context_kind: (symbol ? "symbol" : "global") as "symbol" | "global",
      symbol,
      message: text,
      client_request_id: crypto.randomUUID(),
    };
    const turnId = crypto.randomUUID();
    setInput("");
    setTurns((cur) => [
      ...cur,
      { who: "you" as const, text },
      {
        id: turnId, who: "agent" as const, text: "", status: "working" as const,
        stages: [], clientRequestId: body.client_request_id, requestBody: body,
      },
    ]);
    setPending(true);
    void runStream(body, turnId, gen);
  };

  /** 补修二：未完成回答的同 cid 重试（复用原问题、原会话与原对象快照，
   * 服务端 resume 重新生成，不新增问题记录）。 */
  const retryIncomplete = (turn: Turn) => {
    if (pending || !turn.requestBody || !turn.clientRequestId) return;
    const gen = generationRef.current;
    const turnId = crypto.randomUUID();
    setTurns((cur) => [
      ...cur,
      {
        id: turnId, who: "agent" as const, text: "", status: "working" as const,
        stages: [], clientRequestId: turn.clientRequestId, requestBody: turn.requestBody,
      },
    ]);
    setPending(true);
    void runStream({ ...turn.requestBody, client_request_id: turn.clientRequestId }, turnId, gen);
  };

  // 上下文重置（切标的 / 开新会话共用）：作废在飞回复并清 pending 状态与本地视图。
  // reset 只清 observer 状态（pending 立即回落），在飞请求因世代不匹配不会写回——
  // UI 与数据两条路都不串扰。
  const resetConversation = () => {
    generationRef.current += 1;
    setPending(false);
    setSessionId(null);
    setTurns([]);
  };

  // 切标的 = 切会话上下文：重置对话（会话仍在后端，可从历史恢复），并作废在飞请求
  useEffect(() => {
    resetConversation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  // copilot dispatch：全局快捷指令/自由输入先走规则意图路由（零 LLM），
  // 命中流水线直接出卡片；chat_fallback 再转通用讨论（一次 LLM）。
  const dispatch = useMutation({
    mutationFn: (message: string) =>
      api.copilotDispatch({ message, symbol: symbol ?? undefined }),
    onSuccess: (reply, message) => {
      if (reply.chat_fallback) {
        send(message);
        return;
      }
      setTurns((cur) => [
        ...cur,
        { who: "you", text: message },
        {
          who: "agent",
          text: reply.note_cn,
          card: reply.card,
          preview: reply.preview,
          grounded: true,
        },
      ]);
    },
    onError: (_e, message) => send(message),
  });

  /** U1 返修（主控复核 2026-09-13）：直接说"帮我补测"与点"准备补测"按钮
   * 走**同一个准备入口**——先按原链路把问题建档（agentChat 记录原问题），
   * 然后在原回答上打开中文选择面板；不再追加"请说明要补测的模块"这类
   * 要求手敲代码的文字。原话已选的方法只作预选，未选的不代选；提交复用
   * 与按钮同一套共享函数（requestBacktestTask）。与工作台同构。 */
  const handleBacktest = async (message: string) => {
    const frozenGen = generationRef.current;
    try {
      const reply = await api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
        client_request_id: crypto.randomUUID(),
      });
      if (generationRef.current !== frozenGen) return; // 期间已切会话/对象：不落地
      setSessionId(reply.session_id);
      const boundSymbol = reply.resolved_symbol ?? null;
      const turnId = crypto.randomUUID();
      const evidenceCard = reply.evidence_card ?? null;
      setTurns((cur) => [...cur,
        { id: turnId, who: "agent", text: reply.reply, grounded: reply.grounded,
          evidenceCard,
          planArtifact: reply.plan_artifact ?? null,
          resolved: boundSymbol,
          questionId: reply.question_id ?? null,
          nextSteps: reply.next_steps ?? null }]);
      if (!reply.question_id || !boundSymbol) {
        setTurns((cur) => [...cur, {
          who: "agent",
          text: !reply.question_id ? "会话未建立，无法绑定补测任务。"
            : "请先说明补测哪个标的（一次只跑一个标的）。",
        }]);
        return;
      }
      const setupPanel: BacktestSetupPayload = {
        symbol: boundSymbol, displayName: reply.evidence_card?.facts?.display_name, sessionId: reply.session_id, questionId: reply.question_id,
        defaultModule: parseBacktestModule(message),
        windowLabel: windowLabelFromComparisonConfig(evidenceCard?.history_and_scope?.comparison_config),
        hint: null,
      };
      setTurns((cur) => cur.map((t) => (t.id === turnId ? { ...t, setupPanel } : t)));
    } catch (e) {
      if (generationRef.current === frozenGen) {
        setTurns((cur) => [...cur, {
          who: "agent",
          text: `补测准备失败：${e instanceof Error ? e.message : String(e)}`,
        }]);
      }
    }
  };

  /** UX 第一期：动作条"准备补测"→ 在该回答上打开中文选择面板（U1/U3：
   * 与工作台同构，面板挂在原回答上）。缺绑定时如实说明，不假装可用。
   * U2 返修：原问题有冻结窗口时如实带出。 */
  const openSetupPanel = (turn: Turn, sym: string) => {
    if (!sessionId || !turn.questionId || !turn.id) {
      setTurns((cur) => [...cur, {
        who: "agent",
        grounded: true,
        text: "发起补测需要绑定当前对话里的一个提问——请就这个标的重新提一个问题（例如“它现在怎么看”），在新回答下点「准备补测」即可。",
      }]);
      return;
    }
    const setupPanel: BacktestSetupPayload = {
      symbol: sym, displayName: turn.evidenceCard?.facts?.display_name, sessionId, questionId: turn.questionId, defaultModule: null,
      windowLabel: windowLabelFromComparisonConfig(turn.evidenceCard?.history_and_scope?.comparison_config),
      hint: null,
    };
    setTurns((cur) => cur.map((t) => (t.id === turn.id ? { ...t, setupPanel } : t)));
  };

  /** U3 返修：面板提交在请求发出前冻结会话/问题/对象与世代；响应、错误、
   * 结束处理都先核对上下文——用户切到新会话后，迟到的旧任务消息绝不插入
   * 新会话视图（任务已创建并登记）。同步忙锁 + 稳定请求身份防重复提交。 */
  const submitSetup = async (turn: Turn, module: string, exitVariant: string) => {
    const setup = turn.setupPanel;
    if (!setup || !turn.id || setupBusyRef.current || turn.panelSubmitting) return;
    setupBusyRef.current = true;
    const frozenGen = generationRef.current;
    const patchTurn = (value: Partial<Turn>) => setTurns((cur) => cur.map(
      (t) => (t.id === turn.id ? { ...t, ...value } : t),
    ));
    patchTurn({ panelSubmitting: true });
    try {
      const btr = await requestBacktestTask({
        sessionId: setup.sessionId, questionId: setup.questionId,
        symbol: setup.symbol, module, exitVariant,
      });
      if (generationRef.current !== frozenGen) { patchTurn({ setupPanel: null, panelSubmitting: false }); return; }
      patchTurn({ setupPanel: null, panelSubmitting: false });
      setTurns((cur) => [...cur, {
        who: "agent", grounded: true, taskId: btr.request_id,
        detailRun: btr.status === "completed" ? btr.run_id : null,
        text: taskCreatedTextCn(btr),
      }]);
      pollTask(btr.request_id, () => generationRef.current === frozenGen, onTaskStatus);
    } catch (e) {
      patchTurn({ panelSubmitting: false });
      if (generationRef.current === frozenGen) {
        setTurns((cur) => [...cur, {
          who: "agent",
          text: `补测创建失败：${e instanceof Error ? e.message : String(e)}`,
        }]);
      }
    } finally {
      setupBusyRef.current = false;
    }
  };

  const routeAndAct = async (raw: string) => {
    const text = raw.trim();
    if (!text || dispatch.isPending || pending) return;
    let route: Awaited<ReturnType<typeof resolveRoute>>;
    try {
      route = await resolveRoute({ message: text, sessionId, symbol });
    } catch {
      if (symbol) send(text);
      else dispatch.mutate(text);
      return;
    }
    for (const c of route.resolve.clarification) {
      setTurns((cur) => [...cur, { who: "agent", text: c.question_cn }]);
    }
    if (route.action === "dispatch") {
      dispatch.mutate(text);
      return;
    }
    if (route.action === "backtest") {
      // UX 第一期（场景5）：点名当前引擎没有的退出方式（如 ATR 止损）→
      // 如实说明暂未支持，不静默替换、不声称已比较。
      // U1 返修：原草稿含"补测"会被再次判成补测请求形成死循环——换用
      // 不含触发词的讨论草稿，并提供"继续讨论"动作（点击放回输入框，
      // 可改后发送），保证讨论入口真实可用。
      const unsupported = detectUnsupportedExitRequest(text);
      if (unsupported) {
        const sym = route.resolve.resolved_symbol ?? symbol;
        setTurns((cur) => [...cur, {
          who: "agent",
          grounded: true,
          resolved: sym,
          nextSteps: [{ kind: "draft_discussion", label_cn: "继续讨论（不做数值比较）", draft_cn: atrDiscussionDraft(sym) }],
          text: `这项比较暂未支持：当前补测引擎的退出方式只有${SUPPORTED_EXITS_CN}；${unsupported}不在其中。我不会把它偷偷换成别的退出规则，也没有做过这项比较。\n\n想继续的话：① 就支持的退出方式补测——点下方「准备补测」之前，先就这个标的提一个问题；② 点「继续讨论」把思路问题放回输入框，可修改后发送。`,
        }]);
        return;
      }
      await handleBacktest(text);
      return;
    }
    send(text);
  };

  const dispatchOrSend = (raw: string) => {
    void routeAndAct(raw);
  };

  if (!open) return null;
  const chips = symbol ? SYMBOL_CHIPS : GLOBAL_CHIPS;

  return (
    <>
      <div className="drawer-overlay" onClick={closeConsole} />
      <aside className="drawer-panel agent-console">
        <div className="drawer-head">
          <h2>Agent · {subjectLabel(symbol, [...turns].reverse().find(t=>t.resolved===symbol)?.evidenceCard?.facts?.display_name)}</h2>
          <button className="btn small" onClick={resetConversation}>
            开新会话
          </button>
          <button className="btn small" onClick={closeConsole}>关闭</button>
        </div>
        <div className="drawer-body" ref={bodyRef}>
          {turns.length === 0 && (
            <div className="muted" style={{ fontSize: 12 }}>
              {symbol ? "就当前标的提问" : "全局问答"} · 判定在系统，agent 只讲解。
            </div>
          )}
          {turns.map((turn, i) => (
            <ConsoleTurnView key={i} index={i} turn={turn} symbol={symbol} sessionId={sessionId}
              onRetryIncomplete={retryIncomplete}
              navigate={navigate}
              registerRef={(idx, el) => { if (el) turnRefs.current.set(idx, el); else turnRefs.current.delete(idx); }}
              scrollToTurn={(idx) => turnRefs.current.get(idx)?.scrollIntoView({ behavior: "smooth", block: "start" })}
              onDraft={setInput}
              onPrepareBacktest={openSetupPanel}
              onSetupSubmit={submitSetup}
              onSetupCancel={(t) => setTurns((cur) => cur.map((x) => (x.id === t.id ? { ...x, setupPanel: null } : x)))}
            />
          ))}
          {pending && <div className="muted">agent 正在整理…</div>}
        </div>
        <div className="agent-chips">
          {chips.map((c) => (
            <button
              key={c}
              className="btn small chip"
              disabled={pending || dispatch.isPending}
              onClick={() => (symbol ? send(c) : c === "我要报单" ? setInput("我") : dispatchOrSend(c))}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="drawer-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // IME 守卫：中文输入法组合中（选候选词）的 Enter 不发送。
              // isComposing 覆盖 Chrome/Firefox；keyCode 229 覆盖 Safari 组合态 keydown。
              if (e.key !== "Enter" || e.nativeEvent.isComposing || e.keyCode === 229) return;
              dispatchOrSend(input);
            }}
            placeholder={symbol ? "就这个标的讨论（多轮记忆）" : "问点什么"}
            disabled={pending}
          />
          <button className="btn small primary" onClick={() => dispatchOrSend(input)} disabled={pending || !input.trim()}>
            发送
          </button>
        </div>
      </aside>
    </>
  );
}


// R7：PlanDraftCard/parsePlanDraft 抽为共用组件（保存草稿与确认生效分离），
// 工作台与侧边助手共用同一实现。
