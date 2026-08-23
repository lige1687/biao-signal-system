import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { matchPath, useLocation } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import { useAgentConsole } from "../App";
import type { CreatePlanPayload, TraceItem } from "../types";

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean; trace?: TraceItem[] };

/** 发起提问时捕获的上下文快照：回复落地前据此校验上下文未变，防止串扰。 */
type AskVars = { message: string; symbol: string | null; sessionId: string | null; epoch: number };

const SYMBOL_CHIPS = ["这个买点为什么是买点", "技术面讨论", "给这个买点建计划", "这个标的我的计划"];
const GLOBAL_CHIPS = ["扫描自选买点", "今日待办", "市场环境怎么样"];

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
                <AgentMarkdown text={turn.text} onBp={() => undefined} notableCount={0} />
              ) : (
                <div className="msg">{turn.text}</div>
              )}
              {(() => {
                const draft = parsePlanDraft(turn.text);
                return draft && symbol ? (
                  <PlanDraftCard draft={draft} symbol={symbol} />
                ) : null;
              })()}
              {turn.who === "agent" && turn.trace && turn.trace.length > 0 && (
                <ProvLite trace={turn.trace} />
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
            <button key={c} className="btn small chip" disabled={ask.isPending} onClick={() => send(c)}>
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
              send(input);
            }}
            placeholder={symbol ? "就这个标的讨论（多轮记忆）" : "问点什么"}
            disabled={ask.isPending}
          />
          <button className="btn small primary" onClick={() => send(input)} disabled={ask.isPending || !input.trim()}>
            发送
          </button>
        </div>
      </aside>
    </>
  );
}

/** 回答尾部的溯源角标（轻量版，不引 ProvenanceBadge 的完整映射）。 */
function ProvLite({ trace }: { trace: TraceItem[] }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="prov-badge-wrap">
      <button className="prov-badge" onClick={() => setOpen((v) => !v)}>ⓘ</button>
      {open && (
        <div className="prov-popover">
          {trace.map((t, i) => (
            <div key={i} className="prov-item">
              <div>{t.label}</div>
              {t.rule_id && <div className="muted">rule_id: {t.rule_id}</div>}
            </div>
          ))}
        </div>
      )}
    </span>
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

function PlanDraftCard({ draft, symbol }: { draft: PlanDraft; symbol: string }) {
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
      await api.confirmPlan(plan.plan_id);
      return plan;
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
        disabled={create.isPending}
        onClick={() => create.mutate()}
      >
        {create.isPending ? "提交中…" : "确认落库（draft→armed）"}
      </button>
      {create.error && (
        <div className="cp-error">{String(create.error)}</div>
      )}
      {create.isSuccess && <div className="cp-hint">已落库并激活，见「监督待办」页。</div>}
    </div>
  );
}
