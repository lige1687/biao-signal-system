import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { matchPath, useLocation, useNavigate } from "react-router-dom";
import { api, backtestApi } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import EvidenceCardView from "./EvidenceCardView";
import { CopilotCardDispatcher } from "./copilot/CopilotCards";
import ProvenanceBadge from "./ProvenanceBadge";
import { useAgentConsole } from "../App";
import { parseBacktestExit, parseBacktestModule, resolveRoute } from "../utils/resolveRoute";
import {
  phaseLabelCn, pollTask, recoverActiveTasks, taskStatusTextCn, trackTask,
} from "../utils/backtestTasks";
import PlanDraftCard, {
  parsePlanDraft, planDraftFromArtifact,
} from "./PlanDraftCard";
import type {
  BacktestRequestStatus, CopilotResolveReply, EvidenceCard, PlanArtifact,
  TraceItem, TradePreview,
} from "../types";

type Turn = {
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
};

/** 发起提问时捕获的上下文快照：回复落地前据此校验上下文未变，防止串扰。 */
type AskVars = { message: string; symbol: string | null; sessionId: string | null; epoch: number };

const SYMBOL_CHIPS = ["这个买点为什么是买点", "技术面讨论", "给这个买点建计划", "这个标的我的计划"];
/** 全局快捷指令：走 copilot dispatch（零 LLM 直达流水线），未命中回落通用讨论。 */
const GLOBAL_CHIPS = ["今天看什么", "持仓速览", "我要报单", "本周复盘"];

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
  const navigate = useNavigate();
  // 会话世代计数：切标的 / 开新会话 时 +1，发起提问时捕获当前值。
  // 回复到达时世代已变 → 说明期间发生过重置，丢弃回复，不回灌 sessionId/turns。
  const epochRef = useRef(0);

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
    const gen = epochRef.current;
    void recoverActiveTasks(
      () => epochRef.current === gen,
      (st) => {
        if (epochRef.current !== gen) return;
        onTaskStatus(st);
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ask = useMutation({
    // 请求参数全部来自 mutate 时捕获的 AskVars 快照，不读渲染闭包里的最新状态
    mutationFn: ({ message, symbol: askSymbol, sessionId: askSession }: AskVars) =>
      api.agentChat({
        session_id: askSession,
        context_kind: askSymbol ? "symbol" : "global",
        symbol: askSymbol,
        message,
      }),
    onSuccess: (reply, vars) => {
      // I-1 防护：仅当发起时的标的与世代均未变才落地；pending 期间切标的 / 开新会话 → 丢弃。
      if (vars.symbol !== symbol || vars.epoch !== epochRef.current) return;
      setSessionId(reply.session_id);
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: reply.reply, grounded: reply.grounded, trace: reply.trace,
          // 03B-R3 S5/S4：服务端计划产物 + 精确问题归属随回答落地
          evidenceCard: reply.evidence_card ?? null,
          planArtifact: reply.plan_artifact ?? null,
          resolved: reply.resolved_symbol ?? null,
          questionId: reply.question_id ?? null },
      ]);
    },
    onError: (e: unknown, vars) => {
      if (vars.epoch !== epochRef.current) return;
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: `取回失败：${e instanceof Error ? e.message : String(e)}` },
      ]);
    },
  });

  // 上下文重置（切标的 / 开新会话共用）：作废在飞回复并清 pending 状态与本地视图。
  // reset 只清 observer 状态（isPending 立即回落），mutation 本身仍会 settle，
  // 但其 onSuccess/onError 因世代不匹配不会写回——UI 与数据两条路都不串扰。
  const resetConversation = () => {
    epochRef.current += 1;
    ask.reset();
    setSessionId(null);
    setTurns([]);
  };

  // 切标的 = 切会话上下文：重置对话（会话仍在后端，可从历史恢复），并作废在飞请求
  useEffect(() => {
    resetConversation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const send = (message: string) => {
    const text = message.trim();
    if (!text || ask.isPending) return;
    setTurns((cur) => [...cur, { who: "you", text }]);
    setInput("");
    // 捕获发起时的完整上下文（标的 + 会话 + 世代），供落地前校验
    ask.mutate({ message: text, symbol, sessionId, epoch: epochRef.current });
  };

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

  /** 03B：统一解析后分流（服务端 resolve，去「有 symbol 就一概 chat」旁路）。
   * 报单/发现/已有功能 → dispatch 流水线；补测 → chat 记原问题后建任务；
   * 其余（含假设/否定说法）→ 通用讨论。解析不可用时回落旧行为。
   * 03B-R2：五状态任务卡 + 退出方式显式/服务端默认披露。 */
  const handleBacktest = async (message: string, r: CopilotResolveReply) => {
    try {
      const reply = await api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
        client_request_id: crypto.randomUUID(),
      });
      setSessionId(reply.session_id);
      setTurns((cur) => [...cur,
        { who: "agent", text: reply.reply, grounded: reply.grounded,
          evidenceCard: reply.evidence_card ?? null,
          planArtifact: reply.plan_artifact ?? null,
          resolved: reply.resolved_symbol ?? null,
          questionId: reply.question_id ?? null }]);
      const module = parseBacktestModule(message);
      if (!reply.question_id) {
        setTurns((cur) => [...cur,
          { who: "agent", text: "会话未建立，无法绑定补测任务。" }]);
        return;
      }
      if (!module) {
        setTurns((cur) => [...cur, {
          who: "agent",
          text: "请说明要补测的模块：A 回调 / B 突破 / C 2B / D 假突破（例：「补测一下 模块A」）。不默认选 A。",
        }]);
        return;
      }
      if (!r.resolved_symbol) {
        setTurns((cur) => [...cur,
          { who: "agent", text: "请先说明补测哪个标的（一次只跑一个标的）。" }]);
        return;
      }
      let exit = parseBacktestExit(message);
      const exitExplicit = exit != null;
      if (!exit) {
        try {
          exit = (await backtestApi.options()).defaults?.exit_variant || "a6_1_costbasis";
        } catch {
          exit = "a6_1_costbasis";
        }
      }
      const btr = await api.copilotBacktestRequest({
        session_id: reply.session_id, question_id: reply.question_id,
        client_request_id: crypto.randomUUID(), symbol: r.resolved_symbol,
        module, exit_variant: exit,
      });
      trackTask({ requestId: btr.request_id, sessionId: btr.session_id,
                  questionId: btr.question_id, symbol: btr.symbol });
      setTurns((cur) => [...cur, {
        who: "agent",
        grounded: true,
        taskId: btr.request_id,
        detailRun: btr.status === "completed" ? btr.run_id : null,
        text: `已创建补测任务 ${btr.request_id}（${btr.symbol} · 模块${btr.method} · 退出 ${btr.exit_variant}${exitExplicit ? "" : "，系统默认；可用「退出1/2/3」指定"} · 状态 ${phaseLabelCn(btr.status)}）；完成后结果回到本会话。`,
      }]);
      // R6：共用任务控制——五状态机维护同一张任务卡
      const genAtSubmit = epochRef.current;
      pollTask(btr.request_id, () => epochRef.current === genAtSubmit, onTaskStatus);
    } catch (e) {
      setTurns((cur) => [...cur, {
        who: "agent",
        text: `补测创建失败：${e instanceof Error ? e.message : String(e)}`,
      }]);
    }
  };

  const routeAndAct = async (raw: string) => {
    const text = raw.trim();
    if (!text || dispatch.isPending || ask.isPending) return;
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
      await handleBacktest(text, route.resolve);
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
          <h2>agent · {symbol ?? "全局"}</h2>
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
            <div className="turn" key={i}>
              <div className="who">{turn.who === "you" ? "你" : "agent"}</div>
              {turn.who === "agent" ? (
                /* 控制台无主图上下文：onBp 置空、notableCount=0，「买点①」chip 渲染为不可点的暗态 */
                /* FR-3: plan-draft 围栏块从正文剔除（卡片已单独渲染原始 JSON），防裸 JSON 进对话流 */
                <AgentMarkdown
                  text={turn.text.replace(/```plan-draft[\s\S]*?```/g, "").trim()}
                  onBp={() => undefined}
                  notableCount={0}
                />
              ) : (
                <div className="msg">{turn.text}</div>
              )}
              {turn.who === "agent" && turn.evidenceCard && (
                <EvidenceCardView card={turn.evidenceCard} />
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
              {turn.who === "agent" && turn.grounded === false && (
                <div className="grounded-tag warn">判定层数据直出（LLM 不可用或未过校验）</div>
              )}
            </div>
          ))}
          {ask.isPending && <div className="muted">agent 正在整理…</div>}
        </div>
        <div className="agent-chips">
          {chips.map((c) => (
            <button
              key={c}
              className="btn small chip"
              disabled={ask.isPending || dispatch.isPending}
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
            disabled={ask.isPending}
          />
          <button className="btn small primary" onClick={() => dispatchOrSend(input)} disabled={ask.isPending || !input.trim()}>
            发送
          </button>
        </div>
      </aside>
    </>
  );
}


// R7：PlanDraftCard/parsePlanDraft 抽为共用组件（保存草稿与确认生效分离），
// 工作台与侧边助手共用同一实现。
