import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "../components/AgentMarkdown";
import KlineChart, { DEFAULT_DISPLAY } from "../components/KlineChart";
import { CopilotCardDispatcher } from "../components/copilot/CopilotCards";
import type { TradePreview } from "../types";

type Turn = {
  who: "you" | "agent";
  text: string;
  grounded?: boolean;
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
};

const QUICK = [
  { label: "今天看什么", kind: "recommend" },
  { label: "持仓速览", kind: "holdings" },
  { label: "我要报单", kind: "trade" },
  { label: "本周复盘", kind: "review" },
] as const;

/** Agent 工作台（/agent）：左对话流 + 右联动 K 线（resolved_symbol 驱动）。 */
export default function AgentWorkspacePage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns]);

  const dispatch = useMutation({
    mutationFn: (message: string) =>
      api.copilotDispatch({ message, symbol: symbol ?? undefined }),
    onSuccess: (reply, message) => {
      if (reply.chat_fallback) {
        chat.mutate(message);
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
    onError: (_e, message) => chat.mutate(message),
  });

  const chat = useMutation({
    mutationFn: (message: string) =>
      api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
      }),
    onSuccess: (r) => {
      setSessionId(r.session_id);
      if (r.resolved_symbol) setSymbol(r.resolved_symbol);
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: r.reply, grounded: r.grounded },
      ]);
    },
  });

  const detail = useQuery({
    queryKey: ["symbolDetail", symbol],
    queryFn: () => api.detail(symbol!),
    enabled: !!symbol,
    staleTime: 60_000,
  });

  const send = (raw: string) => {
    const message = raw.trim();
    if (!message || dispatch.isPending || chat.isPending) return;
    setInput("");
    if (symbol) {
      chat.mutate(message); // 标的上下文走通用讨论（带技术材料）
      return;
    }
    dispatch.mutate(message);
  };

  return (
    <div className="ws-layout">
      <div className="ws-chat">
        <div className="ws-quick">
          {QUICK.map((q) => (
            <button
              key={q.kind}
              className="btn small"
              disabled={dispatch.isPending || chat.isPending}
              onClick={() =>
                q.kind === "trade" ? setInput("我") : dispatch.mutate(q.label)
              }
            >
              {q.label}
            </button>
          ))}
          {symbol && (
            <Link to={`/symbol/${symbol}`} className="cp-link">
              {symbol} 大图
            </Link>
          )}
        </div>
        <div className="ws-turns" ref={bodyRef}>
          {turns.length === 0 && (
            <div className="muted" style={{ fontSize: 12 }}>
              说一句话开始：点上方快捷指令，或直接问（如「515880 现在怎么看」）。
              聊到的标的会在右侧自动出 K 线。
            </div>
          )}
          {turns.map((t, i) => (
            <div key={i} className={t.who === "you" ? "ws-you" : "ws-agent"}>
              {t.text && (
                t.who === "agent" ? (
                  <AgentMarkdown text={t.text} onBp={() => undefined} notableCount={0} />
                ) : (
                  <div>{t.text}</div>
                )
              )}
              <CopilotCardDispatcher
                card={t.card ?? null}
                preview={t.preview ?? null}
              />
            </div>
          ))}
          {(dispatch.isPending || chat.isPending) && (
            <div className="muted">思考中…</div>
          )}
        </div>
        <div className="drawer-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key !== "Enter" ||
                e.nativeEvent.isComposing ||
                e.keyCode === 229
              )
                return;
              send(input);
            }}
            placeholder={symbol ? `就 ${symbol} 讨论，或随便问` : "问点什么"}
            disabled={dispatch.isPending || chat.isPending}
          />
          <button
            className="btn small primary"
            disabled={dispatch.isPending || chat.isPending || !input.trim()}
            onClick={() => send(input)}
          >
            发送
          </button>
        </div>
      </div>
      <div className="ws-side">
        {symbol ? (
          detail.data ? (
            <KlineChart
              payload={detail.data.chart}
              display={DEFAULT_DISPLAY}
              onPick={() => undefined}
              onDownload={() => undefined}
            />
          ) : (
            <div className="muted">K线加载中…</div>
          )
        ) : (
          <div className="muted" style={{ padding: 12, fontSize: 12 }}>
            右栏会自动跟随对话里提到的标的（K 线 + 系统标记）；提到代码即切。
            想看完整看盘页点左侧「大图」。
          </div>
        )}
      </div>
    </div>
  );
}
