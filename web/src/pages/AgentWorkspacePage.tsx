import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "../components/AgentMarkdown";
import KlineChart, { DEFAULT_DISPLAY } from "../components/KlineChart";
import { CopilotCardDispatcher } from "../components/copilot/CopilotCards";
import ResizeHandle from "../components/ResizeHandle";
import type { TradePreview } from "../types";

type Turn = {
  who: "you" | "agent";
  text: string;
  grounded?: boolean;
  resolved?: string | null;
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
  /** 流式进行中的回合：正文实时追加、打字机禁用 */
  streaming?: boolean;
  /** 调用链阶段（流式回合专属） */
  stages?: { key: string; text: string }[];
  /** 校验未过时的模板直出（附在流式原文之后） */
  fallback?: string;
  verifyNote?: string;
};

type StreamDone = {
  session_id: string;
  resolved_symbol: string | null;
  grounded: boolean;
  verify_note?: string;
  fallback?: string;
};

/** 解析 SSE 字节流为事件序列（stage/token/done）。 */
async function* readSse(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<{ event: string; data: Record<string, unknown> }> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 2);
      let event = "";
      let data = "{}";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (event) {
        yield { event, data: JSON.parse(data) as Record<string, unknown> };
      }
    }
  }
}

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
      正在读取系统判定 · 首次分析新标的约需 1 分钟
    </div>
  );
}

function StageBar({ stages, active }: { stages: { key: string; text: string }[]; active: boolean }) {
  return (
    <div className="ws-stages" role="status" aria-label="调用链进度">
      {stages.map((st, i) => (
        <div className="ws-stage" key={st.key + String(i)}>
          <span className="ws-stage-dot">
            {i < stages.length - 1 || !active ? "✓" : <i />}
          </span>
          {st.text}
        </div>
      ))}
      {active && stages.length === 0 && (
        <div className="ws-stage">
          <span className="ws-stage-dot"><i /></span>
          建立会话…
        </div>
      )}
    </div>
  );
}

function TurnRow({ turn, animate }: { turn: Turn; animate: boolean }) {
  const streamed = turn.who === "agent" && turn.streaming !== undefined;
  const tw = useTypewriter(
    turn.text ?? "",
    animate && turn.who === "agent" && !streamed,
  );
  if (turn.who === "you") {
    return (
      <div className="ws-you-wrap">
        <div className="ws-you">{turn.text}</div>
      </div>
    );
  }
  return (
    <div className="ws-agent">
      {(turn.stages?.length || turn.streaming) && (
        <StageBar stages={turn.stages ?? []} active={!!turn.streaming} />
      )}
      <div className="ws-agent-head">
        {turn.resolved && !turn.streaming && (
          <Link to={`/symbol/${turn.resolved}`} className="ws-sym-chip">
            {turn.resolved}
          </Link>
        )}
        {!turn.streaming && turn.grounded === false && (
          <span className="ws-badge tpl">判定层数据直出</span>
        )}
        {!turn.streaming && turn.grounded === true && (
          <span className="ws-badge ok">已接地</span>
        )}
        {!streamed && !tw.done && (
          <button className="ws-skip" onClick={tw.skip}>
            跳过动画
          </button>
        )}
      </div>
      {turn.text &&
        (streamed || tw.done ? (
          <AgentMarkdown text={turn.text} onBp={() => undefined} notableCount={0} />
        ) : (
          <pre className="ws-typing">
            {tw.shown}
            <span className="ws-caret" aria-hidden>▍</span>
          </pre>
        ))}
      {turn.streaming && !turn.text && (
        <div className="muted" style={{ fontSize: 12 }}>等待 AI 输出…</div>
      )}
      {turn.verifyNote && (
        <div className="cp-error" style={{ marginTop: 6 }}>{turn.verifyNote}</div>
      )}
      {turn.fallback && (
        <div className="cp-narrative" style={{ marginTop: 6 }}>
          <span className="muted">模板直出：</span>
          <AgentMarkdown text={turn.fallback} onBp={() => undefined} notableCount={0} />
        </div>
      )}
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
            <div className="ws-kline-box">
              <KlineChart
                payload={detail.data.chart}
                display={DEFAULT_DISPLAY}
                onPick={() => undefined}
                onDownload={() => undefined}
              />
            </div>
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
  // 左右分栏：像素宽持久化（与买点侧栏 ResizeHandle 同模式）；窄屏自动单栏
  const [narrow, setNarrow] = useState(
    () => window.matchMedia("(max-width: 980px)").matches,
  );
  const [leftPx, setLeftPx] = useState(() => {
    const saved = Number(localStorage.getItem("ws-left-px")) || 0;
    const def = Math.round(window.innerWidth * 0.55);
    return Math.max(380, Math.min(window.innerWidth - 360, saved || def));
  });
  const saveLeftTimer = useRef(0);
  const changeLeft = (w: number) => {
    setLeftPx(w);
    window.clearTimeout(saveLeftTimer.current);
    saveLeftTimer.current = window.setTimeout(
      () => localStorage.setItem("ws-left-px", String(w)),
      300,
    );
  };
  const resetLeft = () => {
    localStorage.removeItem("ws-left-px");
    setLeftPx(Math.round(window.innerWidth * 0.55));
  };
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

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 980px)");
    const update = () => setNarrow(mq.matches);
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const pushTurn = (t: Turn) => setTurns((cur) => [...cur, t]);

  const [chatBusy, setChatBusy] = useState(false);

  const patchLastAgent = (patch: Partial<Turn>) =>
    setTurns((cur) => {
      const next = [...cur];
      for (let i = next.length - 1; i >= 0; i -= 1) {
        if (next[i].who === "agent") {
          next[i] = { ...next[i], ...patch };
          break;
        }
      }
      return next;
    });

  /** 流式对话：SSE 阶段/token/done 实时驱动调用链步骤条与逐字渲染。 */
  const runChatStream = async (message: string) => {
    setChatBusy(true);
    pushTurn({ who: "agent", text: "", streaming: true, stages: [] });
    try {
      const resp = await fetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          context_kind: symbol ? "symbol" : "global",
          symbol,
          message,
        }),
      });
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);
      let text = "";
      let stages: { key: string; text: string }[] = [];
      for await (const { event, data } of readSse(resp.body)) {
        if (event === "stage") {
          stages = [...stages, { key: String(data.key), text: String(data.text) }];
          patchLastAgent({ stages });
        } else if (event === "token") {
          text += String(data.t ?? "");
          patchLastAgent({ text });
        } else if (event === "done") {
          const d = data as unknown as StreamDone;
          if (d.session_id) setSessionId(d.session_id);
          if (d.resolved_symbol) setSymbol(d.resolved_symbol);
          patchLastAgent({
            text: text,
            grounded: d.grounded,
            resolved: d.resolved_symbol ?? null,
            fallback: d.fallback,
            verifyNote: d.verify_note,
            streaming: false,
          });
        }
      }
    } catch (e) {
      patchLastAgent({
        text: `取回失败：${e instanceof Error ? e.message : String(e)}`,
        grounded: false,
        streaming: false,
      });
    } finally {
      setChatBusy(false);
    }
  };

  const dispatch = useMutation({
    mutationFn: (message: string) =>
      api.copilotDispatch({ message, symbol: symbol ?? undefined }),
    onSuccess: (reply) => {
      if (reply.chat_fallback) {
        // 由下方 chat.mutate 接管（send 已推过 you 消息，这里不重复）
        return;
      }
      pushTurn({
        who: "agent",
        text: reply.note_cn,
        card: reply.card,
        preview: reply.preview,
        grounded: true,
      });
    },
    onError: () => {
      // dispatch 挂了（网络等）：由 send 的 fallback 路径走 chat
    },
  });

  const busy = dispatch.isPending || chatBusy;

  /** 报单类说法无论当前聊着哪个标的都必须走 dispatch（意图优先于上下文）。 */
  const TRADE_HINT_RE = /买了|卖了|申购|赎回|报单|成交了/;

  const runChat = (message: string) => {
    void runChatStream(message);
  };
  const runDispatch = (message: string) => {
    dispatch.mutate(message, {
      onError: () => runChat(message),
      onSuccess: (reply) => {
        if (reply.chat_fallback) runChat(message);
      },
    });
  };

  const send = (raw: string) => {
    const message = raw.trim();
    if (!message || busy) return;
    setInput("");
    pushTurn({ who: "you", text: message });
    if (TRADE_HINT_RE.test(message) || !symbol) {
      runDispatch(message);
      return;
    }
    runChat(message);
  };

  const askExample = (q: string) => {
    if (TRADE_HINT_RE.test(q)) {
      send(q);
      return;
    }
    // 空态示例：直接走通用讨论（能触发中文名解析联动）
    pushTurn({ who: "you", text: q });
    void runChatStream(q);
  };

  const lastAgentIdx = useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i -= 1)
      if (turns[i].who === "agent") return i;
    return -1;
  }, [turns]);

  return (
    <div
      className="ws-layout"
      style={narrow ? undefined : { gridTemplateColumns: `${leftPx}px 10px 1fr` }}
    >
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
            placeholder={symbol ? `就 ${symbol} 讨论，或随便问` : "直接问；说标的名/代码，右栏出图"}
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

      {!narrow && (
        <div
          className="ws-split"
          onDoubleClick={resetLeft}
          title="拖动调整左右比例，双击恢复默认"
        >
          <ResizeHandle
            width={leftPx}
            min={380}
            max={Math.max(420, window.innerWidth - 360)}
            onChange={changeLeft}
            cursor="col-resize"
          />
        </div>
      )}
      <SidePanel symbol={symbol} onAsk={askExample} />
    </div>
  );
}
