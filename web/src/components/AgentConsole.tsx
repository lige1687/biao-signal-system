import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { matchPath, useLocation } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import { useAgentConsole } from "../App";
import type { TraceItem } from "../types";

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
