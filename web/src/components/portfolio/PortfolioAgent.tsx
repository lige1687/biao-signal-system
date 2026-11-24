import { useEffect, useRef, useState } from "react";
import AgentMarkdown from "../AgentMarkdown";
import {
  isCurrentScope, loadPortfolioChat, portfolioScopeKey,
  savePortfolioChat, type PortfolioChatState, type PortfolioTurn,
} from "./portfolioAgentState";

export default function PortfolioAgent(props: {
  holdingId: string | null; holdingName?: string; initialQuestion?: string;
  onClose: () => void;
}): JSX.Element {
  const { holdingId, holdingName, initialQuestion, onClose } = props;
  const [chat, setChat] = useState<PortfolioChatState>(() => {
    const saved = loadPortfolioChat(localStorage, holdingId);
    return { ...saved, draft: saved.draft || initialQuestion || "" };
  });
  const [activeHoldingId, setActiveHoldingId] = useState(holdingId);
  const [loadingHistory, setLoadingHistory] = useState(Boolean(chat.sessionId));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [storageWarning, setStorageWarning] = useState("");
  const [material, setMaterial] = useState<{ date: string; gaps: string[];
    items: Array<{ name: string; title: string; reason: string; next: string }> } | null>(null);
  const scopeRef = useRef(portfolioScopeKey(holdingId));
  const generationRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const chatRef = useRef(chat);
  chatRef.current = chat;

  useEffect(() => {
    const scope = portfolioScopeKey(holdingId);
    scopeRef.current = scope;
    generationRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    setError("");
    setLoadingHistory(false);
    setMaterial(null);
    const saved = loadPortfolioChat(localStorage, holdingId);
    const next = { ...saved, draft: saved.draft || initialQuestion || "" };
    setActiveHoldingId(holdingId);
    setChat(next);
    if (saved.sessionId) {
      setLoadingHistory(true);
      const generation = generationRef.current;
      const params = new URLSearchParams({ context_kind: "portfolio" });
      if (holdingId !== null) params.set("portfolio_holding_id", holdingId);
      fetch(`/api/agent/sessions/${encodeURIComponent(saved.sessionId)}/messages?${params}`)
        .then((response) => {
          if (response.status === 404 || response.status === 409) {
            throw new Error("已保存会话与当前持仓范围不一致");
          }
          if (!response.ok) throw new Error(`恢复会话失败（${response.status}）`);
          return response.json();
        })
        .then((rows: Array<{ message_id?: number; role: string; content: string; question_id?: number | null;
          grounded?: boolean; answer_incomplete?: unknown; retry?: PortfolioTurn["retry"];
          verify_note?: string | null; fallback?: string | null; evidence_card?: { portfolio?: {
            holding_as_of?: string; review_date?: string; items?: Array<{ gaps?: string[];
              name?: string; title_cn?: string; reason_cn?: string; next_step_cn?: string }> }} }>) => {
          if (generationRef.current !== generation || scopeRef.current !== scope
              || !isCurrentScope(scope, holdingId)) return;
          setChat((old) => {
            const turns: PortfolioTurn[] = rows.filter((r) => r.role === "user" || r.role === "assistant")
            .map((r) => ({ id: `history-${r.message_id}`, role: r.role as "user" | "assistant",
              text: r.content, questionId: r.question_id,
              grounded: r.grounded, verifyNote: r.verify_note || undefined,
              fallback: r.fallback || undefined,
              retry: r.retry?.portfolio_holding_id === holdingId ? r.retry : undefined,
              status: r.answer_incomplete ? "failed" as const : "complete" as const }));
            const lastUser = [...rows].reverse().find((r) => r.role === "user");
            const hasAnswer = rows.some((r) => r.role === "assistant" && r.question_id === lastUser?.message_id);
            if (lastUser && !hasAnswer) {
              const local = [...old.turns].reverse().find((turn) => turn.role === "assistant"
                && turn.status === "failed" && turn.retry?.message === lastUser.content);
              if (local) turns.push(local);
            }
            return { ...old, turns };
          });
          const portfolio = [...rows].reverse().find((r) => r.evidence_card?.portfolio)?.evidence_card?.portfolio;
          if (portfolio) setMaterial({ date: portfolio.holding_as_of || portfolio.review_date || "未知",
            gaps: (portfolio.items || []).flatMap((item) => item.gaps || []),
            items: (portfolio.items || []).map((item) => ({ name: item.name || "未命名持仓",
              title: item.title_cn || "资料待补", reason: item.reason_cn || "原因待核实",
              next: item.next_step_cn || "核实资料" })) });
        })
        .catch((cause) => {
          if (generationRef.current !== generation || scopeRef.current !== scope) return;
          if (cause?.message === "已保存会话与当前持仓范围不一致") {
            setChat((old) => ({ sessionId: null, draft: old.draft, turns: [] }));
            setError("已保存会话失效，草稿仍在；发送后会开始新会话。");
          } else setError(String(cause.message || cause));
        })
        .finally(() => {
          if (generationRef.current === generation && scopeRef.current === scope) setLoadingHistory(false);
        });
    }
  }, [holdingId, initialQuestion]);

  useEffect(() => {
    if (!savePortfolioChat(localStorage, activeHoldingId, chat)) {
      setStorageWarning("浏览器未允许保存本机资料；关闭面板后会话与草稿可能无法恢复。");
    }
  }, [chat, activeHoldingId]);
  useEffect(() => () => { generationRef.current += 1; abortRef.current?.abort(); }, []);

  function patchTurn(id: string, patch: Partial<PortfolioTurn>) {
    setChat((current) => ({ ...current, turns: current.turns.map((turn) => turn.id === id ? { ...turn, ...patch } : turn) }));
  }

  async function send(retry?: PortfolioTurn) {
    const question = retry ? (retry.retry?.message || chat.turns.find((turn) => turn.id === retry.id.replace("assistant", "user"))?.text) : chat.draft.trim();
    if (!question || busy || loadingHistory) return;
    const requestScope = scopeRef.current;
    const generation = generationRef.current;
    const cid = retry?.retry?.client_request_id || retry?.cid || crypto.randomUUID();
    const turnId = retry?.id || `assistant-${cid}`;
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError("");
    const sessionId = chatRef.current.sessionId;
    if (!retry) {
      setChat((current) => ({ ...current, draft: "", turns: [...current.turns,
        { id: `user-${cid}`, role: "user", text: question, cid },
        { id: turnId, role: "assistant", text: "", status: "pending", cid,
          retry: { message: question, client_request_id: cid, portfolio_holding_id: holdingId } }] }));
    } else patchTurn(turnId, { status: "pending", text: "", fallback: undefined, verifyNote: undefined });
    let text = "";
    let done = false;
    try {
      const response = await fetch("/api/agent/chat/stream", {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
        body: JSON.stringify({ session_id: sessionId, context_kind: "portfolio",
          portfolio_holding_id: holdingId, symbol: null, message: question, client_request_id: cid }),
      });
      if (!response.ok || !response.body) throw new Error(`服务返回 ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() || "";
        for (const frame of frames) {
          if (generationRef.current !== generation || scopeRef.current !== requestScope) { controller.abort(); return; }
          const event = frame.match(/^event:\s*(.+)$/m)?.[1];
          const raw = frame.match(/^data:\s*(.+)$/m)?.[1];
          if (!raw) continue;
          const data = JSON.parse(raw);
          if (event === "prepared") {
            if (data.session_id) setChat((current) => ({ ...current, sessionId: data.session_id }));
            const portfolio = data.evidence_card?.portfolio;
            if (portfolio) setMaterial({ date: portfolio.holding_as_of || portfolio.review_date || "未知",
              gaps: (portfolio.items || []).flatMap((item: { gaps?: string[] }) => item.gaps || []),
              items: (portfolio.items || []).map((item: { name?: string; title_cn?: string;
                reason_cn?: string; next_step_cn?: string }) => ({ name: item.name || "未命名持仓",
                  title: item.title_cn || "资料待补", reason: item.reason_cn || "原因待核实",
                  next: item.next_step_cn || "核实资料" })) });
          } else if (event === "token") {
            text += String(data.t || "");
            patchTurn(turnId, { text });
          } else if (event === "done") {
            done = true;
            if (data.session_id) setChat((current) => ({ ...current, sessionId: data.session_id }));
            const portfolio = data.evidence_card?.portfolio;
            if (portfolio) setMaterial({ date: portfolio.holding_as_of || portfolio.review_date || "未知",
              gaps: (portfolio.items || []).flatMap((item: { gaps?: string[] }) => item.gaps || []),
              items: (portfolio.items || []).map((item: { name?: string; title_cn?: string;
                reason_cn?: string; next_step_cn?: string }) => ({ name: item.name || "未命名持仓",
                  title: item.title_cn || "资料待补", reason: item.reason_cn || "原因待核实",
                  next: item.next_step_cn || "核实资料" })) });
            patchTurn(turnId, { text: text || data.fallback || "", fallback: data.fallback,
              verifyNote: data.verify_note, questionId: data.question_id,
              grounded: Boolean(data.grounded),
              status: ["failed", "incomplete"].includes(data.answer_state) ? "failed" : "complete" });
          }
        }
      }
      if (!done) throw new Error("连接提前结束，可重试原问题");
    } catch (cause) {
      if (generationRef.current === generation && scopeRef.current === requestScope) {
        const message = cause instanceof Error ? cause.message : "请求失败";
        patchTurn(turnId, { text: text || message, status: "failed" });
        setError(message);
      }
    } finally {
      if (generationRef.current === generation && scopeRef.current === requestScope) setBusy(false);
    }
  }

  const label = holdingId === null ? "全部持仓" : (holdingName || "这只持仓");
  return <section className="pwa-panel" role="dialog" aria-label={`${label}持仓讨论`}>
    <header className="pwa-head"><div><strong>讨论范围：{label}</strong><small>只解释已有持仓资料，不会自动建立计划或记录成交</small></div>
      <button type="button" onClick={onClose} aria-label="关闭持仓讨论">关闭</button></header>
    {material && <div className="pwa-material">持仓资料日期：{material.date}。{material.gaps.length > 0
      ? `待补：${[...new Set(material.gaps)].join("；")}` : "当前材料未列出缺口。"}
      <details><summary>本次讨论使用的 {material.items.length} 只持仓资料</summary><ul>{material.items.map((item, index) => <li key={`${item.name}-${index}`}>
        <strong>{item.name}：</strong>{item.title}。{item.reason} 下一步：{item.next}
      </li>)}</ul></details></div>}
    <div className="pwa-turns" aria-live="polite">{chat.turns.map((turn) => <div className={`pwa-turn pwa-${turn.role}`} key={turn.id}>
      <strong>{turn.role === "user" ? "你" : "持仓 Agent"}</strong>{turn.role === "assistant"
        ? <AgentMarkdown text={turn.text || (turn.status === "pending" ? "正在读取资料…" : "")} onBp={() => {}} notableCount={0} />
        : <p>{turn.text}</p>}
      {turn.role === "assistant" && turn.grounded === false && <p className="pwa-note">
        {turn.fallback && turn.fallback === turn.text
          ? "AI 未生成解读，显示的是已有系统资料。"
          : "这段回答未通过资料核实，请以上方系统资料为准。"}
      </p>}
      {turn.verifyNote && <p className="pwa-note">{turn.verifyNote}</p>}
      {turn.fallback && turn.fallback !== turn.text && <p className="pwa-note">系统资料：{turn.fallback}</p>}
      {turn.role === "assistant" && turn.status === "failed" && <button type="button" disabled={busy || loadingHistory} onClick={() => void send(turn)}>重试原问题</button>}
    </div>)}</div>
    {error && <p className="pwa-error" role="alert">{error}</p>}
    {storageWarning && <p className="pwa-note" role="status">{storageWarning}</p>}
    <div className="pwa-shortcuts">{(holdingId === null
      ? ["全部持仓里哪些需要按计划处理？", "哪些持仓资料还缺，下一步先核实什么？"]
      : ["这只持仓的原计划现在满足吗？", "哪些资料还缺，下一步看什么？"])
      .map((question) => <button key={question} type="button" onClick={() => setChat((old) => ({ ...old, draft: question }))}>{question}</button>)}</div>
    <form className="pwa-compose" onSubmit={(event) => { event.preventDefault(); void send(); }}>
      <textarea aria-label="持仓问题" value={chat.draft} onChange={(event) => setChat((old) => ({ ...old, draft: event.target.value }))} />
      <button type="submit" disabled={busy || loadingHistory || !chat.draft.trim()}>{loadingHistory ? "恢复会话中" : "发送"}</button>
    </form><small className="pwa-storage">会话与草稿保存在此浏览器的本机存储中。</small>
  </section>;
}
