import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { matchPath, useLocation } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import { useAgentConsole } from "../App";
import type { TraceItem } from "../types";

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean; trace?: TraceItem[] };

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

  // 切标的 = 切会话上下文：重置对话（会话仍在后端，可从历史恢复）
  useEffect(() => {
    setSessionId(null);
    setTurns([]);
  }, [symbol]);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns]);

  const ask = useMutation({
    mutationFn: (message: string) =>
      api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
      }),
    onSuccess: (reply) => {
      setSessionId(reply.session_id);
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: reply.reply, grounded: reply.grounded, trace: reply.trace },
      ]);
    },
    onError: (e: unknown) =>
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: `取回失败：${e instanceof Error ? e.message : String(e)}` },
      ]),
  });

  const send = (message: string) => {
    const text = message.trim();
    if (!text || ask.isPending) return;
    setTurns((cur) => [...cur, { who: "you", text }]);
    setInput("");
    ask.mutate(text);
  };

  if (!open) return null;
  const chips = symbol ? SYMBOL_CHIPS : GLOBAL_CHIPS;

  return (
    <>
      <div className="drawer-overlay" onClick={closeConsole} />
      <aside className="drawer-panel agent-console">
        <div className="drawer-head">
          <h2>agent · {symbol ?? "全局"}</h2>
          <button className="btn small" onClick={() => { setSessionId(null); setTurns([]); }}>
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
            onKeyDown={(e) => e.key === "Enter" && send(input)}
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
