import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, backtestApi } from "../api/client";
import AgentMarkdown from "../components/AgentMarkdown";
import KlineChart, { DEFAULT_DISPLAY } from "../components/KlineChart";
import { CopilotCardDispatcher } from "../components/copilot/CopilotCards";
import PlanDraftCard, {
  parsePlanDraft, planDraftFromArtifact,
} from "../components/PlanDraftCard";
import EvidenceCardView from "../components/EvidenceCardView";
import ResizeHandle from "../components/ResizeHandle";
import { parseBacktestExit, parseBacktestModule, resolveRoute } from "../utils/resolveRoute";
import {
  phaseLabelCn, pollTask, recoverActiveTasks, taskStatusTextCn, trackTask,
} from "../utils/backtestTasks";
import type {
  AgentMessageDTO, AgentSessionDTO, BacktestRequestStatus, CopilotResolveReply,
  EvidenceCard, PlanArtifact, TradePreview,
} from "../types";

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
  /** 标的速览卡（结合右栏 K 线读图用） */
  quickCard?: QuickCard | null;
  /** 03B-R2 契约3：本轮证据卡（流式 done / 历史恢复同一产物） */
  evidenceCard?: EvidenceCard | null;
  /** 03B-R2 契约4：补测任务卡（queued/running 原地更新，终态只处理一次） */
  taskId?: string;
  /** 03B-R2 契约4：本回合原问题（草稿卡绑定用） */
  questionId?: number | null;
  /** 03B-R2 契约4：终态可点开的原运行结果 */
  detailRun?: string | null;
  /** 03B-R3 S5：服务端计划产物（模型不参与构造） */
  planArtifact?: PlanArtifact | null;
};

type QuickLevel = {
  role: string; price: number; kind: "below" | "above";
  dist_pct: number; from_cn: string;
};
type QuickCard = {
  symbol: string; display_name: string; as_of?: string; close: number;
  color_cn?: string; stage_cn?: string; risk_cn?: string;
  levels: QuickLevel[]; note_cn?: string;
};
type StreamDone = {
  session_id: string;
  resolved_symbol: string | null;
  grounded: boolean;
  verify_note?: string;
  fallback?: string;
  quick_card?: QuickCard | null;
  question_id?: number | null;
  evidence_card?: EvidenceCard | null;
  plan_artifact?: PlanArtifact | null;
  answer_state?: string | null;
  replayed?: boolean;
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
  { label: "最近机会", kind: "scout" },
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

/** 标的速览卡：总评徽标 + 关键价位与距离，配合右栏 K 线读图。 */
function QuickCardView({ card }: { card: QuickCard }) {
  return (
    <div className="cp-card" style={{ marginTop: 6 }}>
      <div className="cp-label">
        {card.display_name}（{card.symbol}）· 收盘 {card.close} · {card.as_of}
      </div>
      <div className="cp-row">
        {card.color_cn && <span className="cp-chip">{card.color_cn}</span>}
        {card.stage_cn && <span className="cp-chip">阶段：{card.stage_cn}</span>}
        {card.risk_cn && <span className="cp-chip">风险：{card.risk_cn}</span>}
      </div>
      {card.levels.length > 0 && (
        <div className="ws-quick-levels">
          {card.levels.map((lv, i) => (
            <div className="ws-quick-level" key={i}>
              <span className={lv.kind === "below" ? "lv-down" : "lv-up"}>
                {lv.kind === "below" ? "↓" : "↑"}
              </span>
              <strong>{lv.role} {lv.price}</strong>
              <span className="muted">
                距现价 {lv.dist_pct}%{lv.from_cn ? ` · ${lv.from_cn}` : ""}
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="muted" style={{ fontSize: 10.5 }}>
        {card.note_cn} · 右栏 K 线已联动，价位线以图上标注为准
      </div>
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

function TurnRow({ turn, animate, symbol, sessionId }: {
  turn: Turn; animate: boolean; symbol: string | null; sessionId: string | null;
}) {
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
      {!turn.streaming && turn.quickCard && <QuickCardView card={turn.quickCard} />}
      {turn.evidenceCard && !turn.streaming && (
        <EvidenceCardView card={turn.evidenceCard} />
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
      {(() => {
        // 03B-R3 S5：优先渲染**服务端计划产物**（模型只解释）；文本解析仅
        // 旧格式兼容（来源不可考须标注）
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
      {turn.detailRun && (
        <Link
          className="btn small"
          style={{ marginTop: 4 }}
          to={`/backtest?run=${encodeURIComponent(turn.detailRun)}`}
        >
          查看该次回测详情（{turn.detailRun}）
        </Link>
      )}
    </div>
  );
}

/** 历史对话侧栏：会话列表、点击恢复、新对话。 */
function timeLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  if (sameDay) return hm;
  if (d.getFullYear() === now.getFullYear())
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

function HistoryPanel({
  activeId,
  onPick,
  onNew,
}: {
  activeId: string | null;
  onPick: (s: AgentSessionDTO) => void;
  onNew: () => void;
}) {
  const q = useQuery({
    queryKey: ["agentSessions"],
    queryFn: () => api.agentSessions(),
    staleTime: 30_000,
  });
  const sessions = q.data ?? [];
  return (
    <aside className="ws-history">
      <div className="ws-history-head">
        <span>历史对话</span>
        <button className="btn small" onClick={onNew}>
          ＋ 新对话
        </button>
      </div>
      <div className="ws-history-list">
        {q.isLoading && <div className="muted" style={{ fontSize: 12, padding: 8 }}>加载中…</div>}
        {!q.isLoading && sessions.length === 0 && (
          <div className="muted" style={{ fontSize: 12, padding: 8 }}>
            还没有历史对话。
          </div>
        )}
        {sessions.map((sess) => (
          <button
            key={sess.session_id}
            className={`ws-history-item ${sess.session_id === activeId ? "is-active" : ""}`}
            onClick={() => onPick(sess)}
          >
            <div className="ws-history-title">
              {sess.title_cn || "新会话"}
            </div>
            <div className="ws-history-meta">
              {sess.symbol && <span className="ws-history-sym">{sess.symbol}</span>}
              <span>{timeLabel(sess.last_active_at)}</span>
            </div>
          </button>
        ))}
      </div>
    </aside>
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
  const queryClient = useQueryClient();
  const [loadingHistory, setLoadingHistory] = useState(false);
  // 左右分栏：像素宽持久化（与买点侧栏 ResizeHandle 同模式）；窄屏自动单栏
  const [narrow, setNarrow] = useState(
    () => window.matchMedia("(max-width: 980px)").matches,
  );
  const [leftPx, setLeftPx] = useState(() => {
    const saved = Number(localStorage.getItem("ws-left-px")) || 0;
    const def = Math.round(window.innerWidth * 0.55);
    return Math.max(380, Math.min(window.innerWidth - 596, saved || def));
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
  // R6：页面世代——开新对话/切对象时 +1，过期世代的任务视图更新一律丢弃
  const generationRef = useRef(0);
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

  /** 恢复历史会话：拉取消息流并映射为 turns（trace 不还原，保留接地徽标）。
   * 03B-R2：问题归属/证据卡/草稿绑定随历史一起恢复（刷新/重开同卡同 plan_id）。 */
  const loadSession = async (sess: AgentSessionDTO) => {
    if (busy || loadingHistory) return;
    setLoadingHistory(true);
    setSessionId(sess.session_id);
    try {
      const msgs: AgentMessageDTO[] = await api.agentSessionMessages(sess.session_id);
      // 03B-R3 S4：归属走服务端**精确列**绑定（question_id），不按相邻位置猜；
      // 旧记录 question_id 为空 → 未知（卡片不带问题归属，标旧格式）
      setTurns(
        msgs.map((m) => {
          const runMatch =
            m.role === "assistant" && /运行 ([0-9]{8}-[0-9]{6}-[0-9a-f]+)/.exec(m.content);
          return {
            who: m.role === "user" ? ("you" as const) : ("agent" as const),
            text: m.content,
            grounded: m.grounded,
            resolved: m.resolved_symbol ?? null,
            evidenceCard: m.evidence_card ?? null,
            planArtifact: m.plan_artifact ?? null,
            questionId: m.question_id ?? null,
            detailRun: runMatch ? runMatch[1] : null,
          };
        }),
      );
      // 恢复该会话最后讨论的标的（优先取消息 meta，缺失时用会话 symbol）
      const lastResolved = [...msgs].reverse().find((m) => m.resolved_symbol);
      setSymbol(lastResolved?.resolved_symbol ?? sess.symbol ?? null);
    } finally {
      setLoadingHistory(false);
    }
  };

  const newSession = () => {
    if (busy) return;
    generationRef.current += 1; // R6：旧任务的完成卡不再插入新对话
    setSessionId(null);
    setTurns([]);
    setSymbol(null);
  };

  const [chatBusy, setChatBusy] = useState(false);

  /** 03B-R2 契约4：五状态逐一处理——queued/running 原地更新当前任务卡
   * （不显示中断、不每轮追加新消息）；终态只在任务卡上收口一次。 */
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
      // 恢复路径发现本页没有任务卡：补一张（不重复）
      return [...next, {
        who: "agent" as const, grounded: true, taskId: st.request_id,
        text: taskStatusTextCn(st),
        detailRun: st.status === "completed" ? st.run_id : null,
      }];
    });
  };

  // 03B-R2 契约4：挂载即恢复——服务端任务列表为权威，未终态任务重新接线
  // 轮询；刷新/侧边关闭重开/切换对象后都能接上（localStorage 只是提示）。
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
  const runChatStream = async (message: string, symbolOverride?: string | null) => {
    setChatBusy(true);
    pushTurn({ who: "agent", text: "", streaming: true, stages: [] });
    const effectiveSymbol = symbolOverride ?? symbol;
    try {
      const resp = await fetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          context_kind: effectiveSymbol ? "symbol" : "global",
          symbol: effectiveSymbol,
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
          void queryClient.invalidateQueries({ queryKey: ["agentSessions"] });
          if (d.resolved_symbol) setSymbol(d.resolved_symbol);
          patchLastAgent({
            text: text,
            grounded: d.grounded,
            resolved: d.resolved_symbol ?? null,
            fallback: d.fallback,
            verifyNote: d.verify_note,
            quickCard: d.quick_card ?? null,
            evidenceCard: d.evidence_card ?? null,
            planArtifact: d.plan_artifact ?? null,
            questionId: d.question_id ?? null,
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

  const runChat = (message: string, symbolOverride?: string | null) => {
    void runChatStream(message, symbolOverride);
  };
  const runDispatch = (message: string) => {
    dispatch.mutate(message, {
      onError: () => runChat(message),
      onSuccess: (reply) => {
        if (reply.chat_fallback) runChat(message);
      },
    });
  };

  /** 03B：统一解析后分流——报单/发现/已有功能走 dispatch 流水线，补测走
   * 任务流，其余（含假设/否定/拟交易说法）进入讨论。解析不可用时回落
   * 旧行为（dispatch → chat）。 */
  const routeMessage = async (message: string) => {
    const gen = generationRef.current; // R6：捕获发起时的世代
    let route: Awaited<ReturnType<typeof resolveRoute>>;
    try {
      route = await resolveRoute({ message, sessionId, symbol });
    } catch {
      runDispatch(message);
      return;
    }
    // R1：resolve 结果即时生效——本轮明确改问的对象优先于旧选中
    if (route.resolve.resolved_symbol) setSymbol(route.resolve.resolved_symbol);
    for (const c of route.resolve.clarification) {
      if (gen !== generationRef.current) return;
      pushTurn({ who: "agent", text: c.question_cn, grounded: true });
    }
    if (route.action === "dispatch") {
      runDispatch(message);
      return;
    }
    if (route.action === "backtest") {
      await handleBacktest(message, route.resolve, gen);
      return;
    }
    runChat(message, route.resolve.resolved_symbol);
  };

  /** 补测（03B §5）：先经 chat 记录原问题（拿 question_id），再创建单标的
   * 固定配置任务并轮询状态；完成后完成卡会回填到原问题。 */
  /** 补测（R5/R6 + 03B-R2）：先经 chat 记录原问题（question_id），再经共用
   * 任务控制提交并轮询；五状态机维护同一张任务卡（queued/running 原地更新，
   * 终态收口一次+详情可点开原运行）。退出方式：用户消息明确指定（退出1/2/3、
   * a6_x 等）则用之；未指定时取**服务端声明的默认退出**并在任务卡披露，
   * 前端不再硬编码固定退出值。 */
  const handleBacktest = async (message: string, r: CopilotResolveReply, gen: number) => {
    const genGuard = () => generationRef.current === gen;
    try {
      const reply = await api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
        client_request_id: crypto.randomUUID(),
      });
      if (!genGuard()) return; // 期间已切对象/新对话：视图丢弃，任务留在原问题
      if (reply.session_id) setSessionId(reply.session_id);
      const newSym = reply.resolved_symbol ?? symbol;
      if (newSym) setSymbol(newSym);
      pushTurn({
        who: "agent", text: reply.reply, grounded: reply.grounded,
        resolved: reply.resolved_symbol ?? null,
        evidenceCard: reply.evidence_card ?? null,
        planArtifact: reply.plan_artifact ?? null,
        questionId: reply.question_id ?? null,
      });
      const module = parseBacktestModule(message);
      if (!module) {
        pushTurn({ who: "agent", grounded: true,
          text: "请说明要补测的模块：A 回调 / B 突破 / C 2B / D 假突破（例：「补测一下 模块A」）。不默认选 A。" });
        return;
      }
      if (!reply.question_id) {
        pushTurn({ who: "agent", grounded: false, text: "会话未建立，无法绑定补测任务。" });
        return;
      }
      if (!r.resolved_symbol) {
        pushTurn({ who: "agent", grounded: true, text: "请先说明补测哪个标的（一次只跑一个标的）。" });
        return;
      }
      // 退出方式：显式解析 > 服务端默认（披露）。可用「退出1/2/3」「a6_x」指定。
      let exit = parseBacktestExit(message);
      let exitExplicit = exit != null;
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
      if (!genGuard()) return;
      trackTask({ requestId: btr.request_id, sessionId: btr.session_id,
                  questionId: btr.question_id, symbol: btr.symbol });
      pushTurn({ who: "agent", grounded: true, taskId: btr.request_id,
        detailRun: btr.status === "completed" ? btr.run_id : null,
        text: `已创建补测任务 ${btr.request_id}（${btr.symbol} · 模块${btr.method} · 退出 ${btr.exit_variant}${exitExplicit ? "" : "，系统默认；可用「退出1/2/3」指定"} · 状态 ${phaseLabelCn(btr.status)}）；完成后结果自动回到这里。` });
      pollTask(btr.request_id, genGuard, onTaskStatus);
    } catch (e) {
      if (!genGuard()) return;
      pushTurn({ who: "agent", grounded: false,
        text: `补测创建失败：${e instanceof Error ? e.message : String(e)}` });
    }
  };

  const send = (raw: string) => {
    const message = raw.trim();
    if (!message || busy) return;
    setInput("");
    pushTurn({ who: "you", text: message });
    void routeMessage(message);
  };

  const askExample = (q: string) => {
    send(q);
  };

  const lastAgentIdx = useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i -= 1)
      if (turns[i].who === "agent") return i;
    return -1;
  }, [turns]);

  return (
    <div
      className="ws-layout"
      style={
        narrow
          ? undefined
          : { gridTemplateColumns: `236px ${leftPx}px 10px 1fr` }
      }
    >
      {!narrow && (
        <HistoryPanel activeId={sessionId} onPick={loadSession} onNew={newSession} />
      )}
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
          {loadingHistory && (
            <div className="muted" style={{ fontSize: 12 }}>正在恢复对话…</div>
          )}
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
            <TurnRow key={i} turn={t} animate={i === lastAgentIdx}
                     symbol={symbol} sessionId={sessionId} />
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
            max={Math.max(420, window.innerWidth - 360 - 236)}
            onChange={changeLeft}
            cursor="col-resize"
          />
        </div>
      )}
      <SidePanel symbol={symbol} onAsk={askExample} />
    </div>
  );
}
