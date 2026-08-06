import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { BuyPointReview } from "../types";
import CreatePlanDialog, { type PlanPrefill } from "./CreatePlanDialog";

const VERDICT_STYLE: Record<string, string> = {
  actionable: "var(--lei-green)",
  blocked: "var(--warn)",
  waiting: "var(--text-faint)",
  none: "var(--text-faint)",
};

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean };

/**
 * 买点分析抽屉。
 *
 * 打开即取买点审阅（Python 已判好的确定性结果），按 verdict 展示结构化结论。
 * 可提问，LLM 只讲解审阅字段（接地校验 + 降级模板），不自行判断买点。
 * verdict=actionable 且有 suggested_plan 时，给「据此建计划」直接预填建计划表单。
 */
export default function BuyPointDrawer({
  symbol,
  onClose,
}: {
  symbol: string;
  onClose: () => void;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  const { data: review, isLoading } = useQuery({
    queryKey: ["buyPointReview", symbol],
    queryFn: () => api.buyPointReview(symbol),
  });

  const ask = useMutation({
    mutationFn: (message: string) => api.buyPointChat(symbol, message),
    onSuccess: (reply) =>
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: reply.reply, grounded: reply.grounded },
      ]),
    onError: (e: unknown) =>
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: `取回失败：${e instanceof Error ? e.message : String(e)}` },
      ]),
  });

  useEffect(() => {
    if (review) ask.mutate("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review?.as_of]);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns, ask.isPending]);

  const send = () => {
    const message = input.trim();
    if (!message || ask.isPending) return;
    setTurns((cur) => [...cur, { who: "you", text: message }]);
    setInput("");
    ask.mutate(message);
  };

  const prefill: PlanPrefill = review?.suggested_plan
    ? {
        module: review.suggested_plan.module,
        direction: review.suggested_plan.direction,
        entry_rule_id: review.suggested_plan.entry_rule_id,
        entry_lifecycle_id: review.suggested_plan.entry_lifecycle_id,
        invalidation_price: review.suggested_plan.invalidation_price,
        target_b_price: review.suggested_plan.target_b_price,
        reward_risk_at_plan: review.suggested_plan.reward_risk_at_plan,
      }
    : {};

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer-panel">
        <div className="drawer-head">
          <h2>买点分析 · {symbol}</h2>
          <button className="btn small" onClick={onClose}>关闭</button>
        </div>

        <div className="drawer-body" ref={bodyRef}>
          {isLoading && <div className="muted">正在审阅…</div>}
          {review && <ReviewSummary review={review} onBuildPlan={() => setShowCreate(true)} />}

          {turns.map((turn, i) => (
            <div className="turn" key={i}>
              <div className="who">{turn.who === "you" ? "你" : "分析"}</div>
              <div className="msg">{turn.text}</div>
              {turn.who === "agent" && turn.grounded !== undefined && (
                <div className={`grounded-tag ${turn.grounded ? "" : "warn"}`}>
                  {turn.grounded
                    ? "已过接地校验"
                    : "已降级为结构化模板（LLM 不可用或未过接地校验）"}
                </div>
              )}
            </div>
          ))}
          {ask.isPending && <div className="muted">正在整理…</div>}
        </div>

        <div className="drawer-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="就这个标的的买点提问"
            disabled={ask.isPending}
          />
          <button
            className="btn small primary"
            onClick={send}
            disabled={ask.isPending || !input.trim()}
          >
            发送
          </button>
        </div>
      </aside>

      {showCreate && (
        <CreatePlanDialog
          symbol={symbol}
          prefill={prefill}
          onClose={() => setShowCreate(false)}
        />
      )}
    </>
  );
}

function ReviewSummary({
  review,
  onBuildPlan,
}: {
  review: BuyPointReview;
  onBuildPlan: () => void;
}) {
  return (
    <div className="bp-review">
      <div className="bp-verdict">
        <span
          className="bp-verdict-chip"
          style={{ background: VERDICT_STYLE[review.verdict] || "var(--text-faint)" }}
        >
          {review.verdict_cn}
        </span>
        <span className="muted" style={{ fontSize: 11 }}>
          {review.as_of} · 收盘 {review.last_close ?? "-"}
          {review.has_active_plan && " · 已有活跃计划"}
        </span>
      </div>
      <p className="bp-summary">{review.summary_cn}</p>

      {review.candidates.map((c) => (
        <div className="bp-candidate" key={c.scenario_id}>
          <div className="bp-cand-head">
            <b>{c.scenario_cn}</b>
            <span className="muted">[{c.state_cn}]</span>
            {c.module && <span className="sv-kind-chip">{c.module}</span>}
          </div>
          {c.satisfied_conditions.length > 0 && (
            <div className="bp-cond">✓ {c.satisfied_conditions.join("；")}</div>
          )}
          {c.missing_conditions.length > 0 && (
            <div className="bp-cond miss">✗ {c.missing_conditions.join("；")}</div>
          )}
          <div className="bp-prices">
            <span>关键价 {c.key_price ?? "-"}</span>
            <span>
              止损 {c.invalidation_price ?? "（系统未给出，建计划时确认）"}
            </span>
            <span>
              {c.reward_risk_computable
                ? `R/R ${c.reward_risk_ratio}`
                : "R/R 不可计算"}
            </span>
          </div>
          <div className="muted" style={{ fontSize: 11 }}>
            rule_id:{c.rule_id ?? "-"} · 判定方式为研究代理
          </div>
        </div>
      ))}

      {review.watch_conditions.length > 0 && (
        <div className="bp-watch">
          <h3>到什么情况才算买点</h3>
          {review.watch_conditions.map((w, i) => (
            <div key={i} className="bp-watch-row">
              <span>· {w.text_cn}</span>
              {w.kind === "price" ? (
                <span className="muted">价位 {w.price}</span>
              ) : (
                <span className="muted">状态型条件，无单一价位</span>
              )}
            </div>
          ))}
        </div>
      )}

      {review.suggested_plan && (
        <button className="btn small primary" onClick={onBuildPlan} style={{ marginTop: 8 }}>
          据此建计划（预填已就绪）
        </button>
      )}

      <div className="muted bp-disclaimer">{review.disclaimer_cn}</div>
    </div>
  );
}
