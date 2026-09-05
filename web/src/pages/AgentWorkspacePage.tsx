import { useEffect, useMemo, useRef, useState } from "react";
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
  resolved?: string | null;
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
};

const QUICK = [
  { label: "今天看什么", kind: "recommend" },
  { label: "持仓速览", kind: "holdings" },
  { label: "我要报单", kind: "trade" },
  { label: "本周复盘", kind: "review" },
] as const;

const EXAMPLES = ["通信设备怎么看", "515880 现在是什么阶段", "黄金ETF 的买点"];

/** CJK 慢一点、西文快一点；长文加速，超过 500 字每步多吐几个字。 */
function charDelay(ch: string, total: number): number {
  const base = /[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/.test(ch) ? 24 : 9;
  const accel = total > 500 ? 0.35 : total > 200 ? 0.6 : 1;
  return base * accel;
}
function stepSize(total: number): number {
  return total > 500 ? 3 : total > 200 ? 2 : 1;
}

/** 打字机 hook：active=false 直接全文（历史回合不动画）。skip() 立即完成。 */
function useTypewriter(text: string, active: boolean) {
  const [shown, setShown] = useState(active ? "" : text);
  const [done, setDone] = useState(!active);
  const skipRef = useRef(false);

  useEffect(() => {
    if (!active) {
      setShown(text);
      setDone(true);
      return;
    }
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !text) {
      setShown(text);
      setDone(true);
      return;
    }
    skipRef.current = false;
    setShown("");
    setDone(false);
    let i = 0;
    let timer = 0;
    const step = () => {
      if (skipRef.current) {
        setShown(text);
        setDone(true);
        return;
      }
      i = Math.min(text.length, i + stepSize(text.length));
      setShown(text.slice(0, i));
      if (i >= text.length) {
        setDone(true);
        return;
      }
      timer = window.setTimeout(step, charDelay(text[i - 1] ?? "", text.length));
    };
    timer = window.setTimeout(step, 60);
    return () => window.clearTimeout(timer);
  }, [text, active]);

  return {
    shown,
    done,
    skip: () => {
      skipRef.current = true;
    },
  };
}

function ThinkingRow() {
  return (
    <div className="ws-thinking" role="status" aria-label="正在生成回复">
      <span className="ws-dots" aria-hidden>
        <i /><i /><i />
      </span>
      正在读取系统判定
    </div>
  );
}

function TurnRow({ turn, animate }: { turn: Turn; animate: boolean }) {
  const tw = useTypewriter(turn.text ?? "", animate && turn.who === "agent");
  if (turn.who === "you") {
    return (
      <div className="ws-you-wrap">
        <div className="ws-you">{turn.text}</div>
      </div>
    );
  }
  return (
    <div className="ws-agent">
      <div className="ws-agent-head">
        {turn.resolved && (
          <Link to={`/symbol/${turn.resolved}`} className="ws-sym-chip">
            {turn.resolved}
          </Link>
        )}
        {turn.grounded === false && (
          <span className="ws-badge tpl">判定层数据直出</span>
        )}
        {turn.grounded === true && <span className="ws-badge ok">已接地</span>}
        {!tw.done && (
          <button className="ws-skip" onClick={tw.skip}>
            跳过动画
          </button>
        )}
      </div>
      {turn.text &&
        (tw.done ? (
          <AgentMarkdown text={turn.text} onBp={() => undefined} notableCount={0} />
        ) : (
          <pre className="ws-typing">
            {tw.shown}
            <span className="ws-caret" aria-hidden>▍</span>
          </pre>
        ))}
      <CopilotCardDispatcher card={turn.card ?? null} preview={turn.preview ?? null} />
    </div>
  );
}

function SidePanel({
  symbol,
  onAsk,
}: {
  symbol: string | null;
  onAsk: (q: string) => void;
}) {
  const detail = useQuery({
    queryKey: ["symbolDetail", symbol],
    queryFn: () => api.detail(symbol!),
    enabled: !!symbol,
    staleTime: 60_000,
  });
  const name = detail.data?.display_name;
  return (
    <aside className="ws-side">
      {symbol ? (
        <>
          <header className="ws-side-head">
            <div className="ws-side-title">
              <strong>{name ?? symbol}</strong>
              <span className="muted">{symbol}</span>
            </div>
            <span className="ws-live" title="K线随对话联动">
              <i />跟随对话
            </span>
            <Link to={`/symbol/${symbol}`} className="cp-link">
              大图 →
            </Link>
          </header>
          {detail.data ? (
            <KlineChart
              payload={detail.data.chart}
              display={DEFAULT_DISPLAY}
              onPick={() => undefined}
              onDownload={() => undefined}
            />
          ) : (
            <div className="ws-kline-skeleton" aria-label="K线加载中">
              <div /><div /><div />
            </div>
          )}
        </>
      ) : (
        <div className="ws-empty">
          <p className="ws-empty-title">聊到哪个标的，这里就出哪张图</p>
          <p className="muted">直接说名字或代码都行，比如：</p>
          <div className="ws-empty-chips">
            {EXAMPLES.map((e) => (
              <button key={e} className="btn small chip" onClick={() => onAsk(e)}>
                {e}
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}

/** Agent 工作台（/agent）：左对话流 + 右联动 K 线（resolved_symbol 驱动）。 */
export default function AgentWorkspacePage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);
  const usedQuick = useRef<Set<string>>(new Set());
  const [quickUsed, setQuickUsed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight });
  }, [turns]);

  // 输入框自动增高（1–4 行）
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 96)}px`;
  }, [input]);

  const pushTurn = (t: Turn) => setTurns((cur) => [...cur, t]);

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
      pushTurn({
        who: "agent",
        text: r.reply,
        grounded: r.grounded,
        resolved: r.resolved_symbol ?? null,
      });
    },
    onError: (e) =>
      pushTurn({
        who: "agent",
        text: `取回失败：${e instanceof Error ? e.message : String(e)}`,
        grounded: false,
      }),
  });

  const dispatch = useMutation({
    mutationFn: (message: string) =>
      api.copilotDispatch({ message, symbol: symbol ?? undefined }),
    onSuccess: (reply, message) => {
      if (reply.chat_fallback) {
        chat.mutate(message);
        return;
      }
      pushTurn({ who: "you", text: message });
      pushTurn({
        who: "agent",
        text: reply.note_cn,
        card: reply.card,
        preview: reply.preview,
        grounded: true,
      });
    },
    onError: (_e, message) => {
      pushTurn({ who: "you", text: message });
      chat.mutate(message);
    },
  });

  const busy = dispatch.isPending || chat.isPending;

  const send = (raw: string) => {
    const message = raw.trim();
    if (!message || busy) return;
    setInput("");
    if (symbol) {
      pushTurn({ who: "you", text: message });
      chat.mutate(message);
      return;
    }
    dispatch.mutate(message);
  };

  const askExample = (q: string) => {
    if (symbol) {
      send(q);
      return;
    }
    // 空态示例：直接走通用讨论（能触发中文名解析联动）
    pushTurn({ who: "you", text: q });
    chat.mutate(q);
  };

  const lastAgentIdx = useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i -= 1)
      if (turns[i].who === "agent") return i;
    return -1;
  }, [turns]);

  return (
    <div className="ws-layout">
      <section className="ws-chat">
        <header className="ws-toolbar">
          <div className="ws-brand">
            <span className="ws-brand-dot" aria-hidden />
            工作台
            {symbol && <span className="muted">· 正在聊 {symbol}</span>}
          </div>
          <div className="ws-quick">
            {QUICK.map((q) => {
              const used = quickUsed[q.kind];
              return (
                <button
                  key={q.kind}
                  className={`btn small chip ${used ? "is-used" : ""}`}
                  disabled={busy}
                  title={used ? "本回合已用过" : undefined}
                  onClick={() => {
                    if (q.kind === "trade") {
                      setInput("我");
                      taRef.current?.focus();
                      return;
                    }
                    usedQuick.current.add(q.kind);
                    setQuickUsed((m) => ({ ...m, [q.kind]: true }));
                    dispatch.mutate(q.label);
                  }}
                >
                  {q.label}
                </button>
              );
            })}
          </div>
        </header>

        <div className="ws-turns" ref={bodyRef}>
          {turns.length === 0 && (
            <div className="ws-hello">
              <p className="ws-hello-title">说一句话开始</p>
              <p className="muted">
                判定在系统，AI 只讲解；报单说金额即可记账。试试：
              </p>
              <div className="ws-empty-chips">
                {EXAMPLES.map((e) => (
                  <button
                    key={e}
                    className="btn small chip"
                    onClick={() => askExample(e)}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
          )}
          {turns.map((t, i) => (
            <TurnRow key={i} turn={t} animate={i === lastAgentIdx} />
          ))}
          {busy && <ThinkingRow />}
        </div>

        <footer className="ws-inputbar">
          <textarea
            ref={taRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== "Enter" || e.nativeEvent.isComposing || e.keyCode === 229)
                return;
              if (e.shiftKey) return; // Shift+Enter 换行
              e.preventDefault();
              send(input);
            }}
            placeholder={symbol ? `就 ${symbol} 讨论，或随便问` : "问点什么，比如「通信设备怎么看」"}
            disabled={busy}
          />
          <button
            className="btn small primary ws-send"
            disabled={busy || !input.trim()}
            onClick={() => send(input)}
          >
            {busy ? "输出中…" : "发送"}
          </button>
        </footer>
      </section>

      <SidePanel symbol={symbol} onAsk={askExample} />
    </div>
  );
}
