import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { matchPath, useLocation } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import { CopilotCardDispatcher } from "./copilot/CopilotCards";
import ProvenanceBadge from "./ProvenanceBadge";
import { useAgentConsole } from "../App";
import type { CreatePlanPayload, TraceItem, TradePreview } from "../types";

type Turn = {
  who: "you" | "agent";
  text: string;
  grounded?: boolean;
  trace?: TraceItem[];
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
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
  // 会话世代计数：切标的 / 开新会话 时 +1，发起提问时捕获当前值。
  // 回复到达时世代已变 → 说明期间发生过重置，丢弃回复，不回灌 sessionId/turns。
  const epochRef = useRef(0);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns]);

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
        { who: "agent", text: reply.reply, grounded: reply.grounded, trace: reply.trace },
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

  const dispatchOrSend = (raw: string) => {
    const text = raw.trim();
    if (!text || dispatch.isPending || ask.isPending) return;
    if (symbol) {
      send(text); // 标的上下文的问题走通用讨论（带技术材料）
      return;
    }
    dispatch.mutate(text);
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
              {(() => {
                const draft = parsePlanDraft(turn.text);
                return draft && symbol ? (
                  <PlanDraftCard draft={draft} symbol={symbol} />
                ) : null;
              })()}
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

type PlanDraft = {
  module: string; direction: string; entry_rule_id?: string | null;
  entry_trigger_cn?: string; invalidation_price?: number | null;
  valid_until?: string; thesis_cn?: string; invalidation_criteria_cn?: string;
  drawdown_playbook_cn?: string; take_profit_plan_cn?: string; stop_plan_cn?: string;
};

/** 从 assistant 回复中解析 ```plan-draft {json}``` 代码块。 */
export function parsePlanDraft(text: string): PlanDraft | null {
  const m = /```plan-draft\s*([\s\S]*?)```/.exec(text);
  if (!m) return null;
  try {
    return JSON.parse(m[1]) as PlanDraft;
  } catch {
    return null;
  }
}

/**
 * confirmPlan 阶段失败（createPlan 已落库、激活被拒，如 conformance 硬阻断 422）。
 * 此时重试只会再造一个孤儿 draft，渲染层据此类区分错误路径并给出 plan_id。
 */
class ConfirmPlanError extends Error {
  readonly planId: string;
  constructor(planId: string, message: string) {
    super(message);
    this.name = "ConfirmPlanError";
    this.planId = planId;
  }
}

function PlanDraftCard({ draft, symbol }: { draft: PlanDraft; symbol: string }) {
  const queryClient = useQueryClient();
  const create = useMutation({
    mutationFn: async () => {
      // ruleset_version：后端 create 不校验非空，但留空会让 monitor 跳过规则集
      // 版本漂移检测；从买点审阅响应带当前版本，取不到再降级空串（create 仍可过）。
      let rulesetVersion = "";
      try {
        rulesetVersion = (await api.buyPointReview(symbol)).ruleset_version || "";
      } catch {
        rulesetVersion = "";
      }
      const payload: CreatePlanPayload = {
        symbol,
        module: draft.module,
        direction: draft.direction,
        ruleset_version: rulesetVersion,
        reason: "对话式建计划（agent 引导）",
        entry_rule_id: draft.entry_rule_id ?? null,
        entry_trigger_cn: draft.entry_trigger_cn ?? "",
        entry_price_ref: null,
        invalidation_price: draft.invalidation_price ?? null,
        valid_until: draft.valid_until ?? "",
        thesis_cn: draft.thesis_cn ?? "",
        invalidation_criteria_cn: draft.invalidation_criteria_cn ?? "",
        drawdown_playbook_cn: draft.drawdown_playbook_cn ?? "",
        take_profit_plan_cn: draft.take_profit_plan_cn ?? "",
        stop_plan_cn: draft.stop_plan_cn ?? "",
      };
      const plan = await api.createPlan(payload);
      try {
        await api.confirmPlan(plan.plan_id);
      } catch (err) {
        // draft 已在库、激活被拒：不能用「再点一次」恢复（会产出第二个孤儿 draft），
        // 携带 plan_id 上抛，由渲染层引导用户走监督待办 / 详情页表单。
        throw new ConfirmPlanError(
          plan.plan_id,
          err instanceof Error ? err.message : String(err),
        );
      }
      return plan;
    },
    onSuccess: () => {
      // 全局 staleTime=60s 且 SupervisorPage 打开控制台时不卸载：不失效则监督页
      // 最长 1 分钟看不到新计划（同 ReviewDrawer confirm 成功后的失效范式）。
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
    },
  });
  const rows: Array<[string, string]> = [
    ["模块/方向", `${draft.module} · ${draft.direction}`],
    ["入场理由", draft.entry_rule_id ?? "-"],
    ["失效价", draft.invalidation_price != null ? String(draft.invalidation_price) : "未给出（需人工确认）"],
    ["有效期至", draft.valid_until ?? "-"],
    ["交易假设", draft.thesis_cn ?? "-"],
    ["失效标准", draft.invalidation_criteria_cn ?? "-"],
    ["回撤预案", draft.drawdown_playbook_cn ?? "-"],
    ["止盈预案", draft.take_profit_plan_cn ?? "-"],
    ["止损预案", draft.stop_plan_cn ?? "-"],
  ];
  return (
    <div className="plan-draft-card">
      <div className="cp-label">计划草稿（确认后落库）</div>
      {rows.map(([k, v]) => (
        <div key={k} style={{ fontSize: 12 }}>
          <span className="muted">{k}：</span>
          {v}
        </div>
      ))}
      <button
        className="btn small primary"
        disabled={
          create.isPending ||
          create.isSuccess ||
          create.error instanceof ConfirmPlanError
        }
        title={
          create.error instanceof ConfirmPlanError
            ? "草案已落库，重试会新建重复草案；请走下方指引处理"
            : undefined
        }
        onClick={() => create.mutate()}
      >
        {create.isPending ? "提交中…" : create.isSuccess ? "已落库" : "确认落库（draft→armed）"}
      </button>
      {create.error instanceof ConfirmPlanError ? (
        <div className="cp-error">
          草案已创建但未激活：到监督待办页处理，或从标的详情页的表单继续
          {create.error.planId ? `（plan_id: ${create.error.planId}）` : ""}。
          <span className="muted">原因：{create.error.message}</span>
        </div>
      ) : (
        create.error && (
          <div className="cp-error">
            {create.error instanceof Error ? create.error.message : String(create.error)}
            （未落库，可安全重试）
          </div>
        )
      )}
      {create.isSuccess && <div className="cp-hint">已落库并激活，见「监督待办」页。</div>}
    </div>
  );
}
