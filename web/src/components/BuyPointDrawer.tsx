import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import { moduleCn } from "../modules";
import type {
  BuyPointCandidate,
  BuyPointReview,
  HistoricalStructure,
  ResonanceGroup,
} from "../types";
import { type PlanPrefill } from "./CreatePlanDialog";
import PlanCreateFlow from "./PlanCreateFlow";
import WatchConditionsPanel from "./WatchConditionsPanel";

const VERDICT_STYLE: Record<string, string> = {
  actionable: "var(--lei-green)",
  blocked: "var(--warn)",
  waiting: "var(--text-faint)",
  none: "var(--text-faint)",
};

/** 圆圈数字，用于「买点①②③」展示与一一对应。 */
const CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩";
export function circled(n: number): string {
  return CIRCLED[n] ?? String(n + 1);
}

/** 匹配「买点①/买点1/买点一」等写法，用于解析 agent 文本里提到的买点序号。 */
const BP_RE = /买点\s*([①②③④⑤⑥⑦⑧⑨⑩]|[1-9][0-9]?|一|二|三|四|五|六|七|八|九|十)/g;

/** 把匹配到的序号 token 转成 0 起的候选下标。 */
function parseBpIndex(token: string): number | null {
  const ci = CIRCLED.indexOf(token);
  if (ci >= 0) return ci;
  const cni = "一二三四五六七八九十".indexOf(token);
  if (cni >= 0) return cni;
  const n = Number(token);
  if (Number.isInteger(n) && n >= 1) return n - 1;
  return null;
}

/** annoId「bp-N」<-> 候选下标 N。 */
export function annoToIndex(annoId: string | null | undefined): number | null {
  if (!annoId) return null;
  const m = /^bp-(\d+)$/.exec(annoId);
  return m ? Number(m[1]) : null;
}
export function indexToAnno(index: number): string {
  return `bp-${index}`;
}

/**
 * 只保留值得讲的候选（confirmed / watch），跳过 weakened 确认减弱的噪音。
 * 买点序号 ①②③ 按此筛选后的顺序编号，与 agent prompt 规则 10、主图高亮 annoId 一致。
 * 全部 weakened 时回退返回全部，避免无候选可显。
 */
export function notableCandidates(candidates: BuyPointCandidate[]): BuyPointCandidate[] {
  const notable = candidates.filter((c) => c.state !== "weakened");
  return notable.length > 0 ? notable : candidates;
}

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean };

/**
 * 买点分析对话栏（内嵌在详情页主图右侧，不再是全屏抽屉）。
 *
 * 打开即取买点审阅（Python 已判好的确定性结果），但**不再预放整坨候选明细**--
 * 只给一行结论 + 可点的买点序号。对话为主：agent 讲到「买点①」时，文本里的
 * 序号可点，并自动联动主图高亮（价位线 + 依据结构），形成「图 <-> 卡」一一对应。
 *
 * 高亮坐标全部来自确定性层（候选 key_price / invalidation_price + 主图已有结构标记），
 * LLM 文本只决定「现在讲哪个买点」，不提供坐标（接地红线）。
 */
export default function BuyPointDrawer({
  symbol,
  review: ctrlReview,
  reviewLoading: ctrlReviewLoading,
  activeAnnoId: ctrlActiveAnnoId,
  onActivateCandidate: ctrlOnActivate,
  onClose,
}: {
  symbol: string;
  /** 受控模式（详情页内嵌）：由父组件提供审阅与高亮联动。不传则自取（独立抽屉）。 */
  review?: BuyPointReview;
  reviewLoading?: boolean;
  activeAnnoId?: string | null;
  onActivateCandidate?: (index: number | null) => void;
  onClose: () => void;
}) {
  const controlled = ctrlOnActivate !== undefined;

  // 独立抽屉模式（Supervisor/Workspace）：自取审阅、自管当前候选
  const { data: localReview, isLoading: localReviewLoading } = useQuery({
    queryKey: ["buyPointReview", symbol],
    queryFn: () => api.buyPointReview(symbol),
    enabled: !controlled,
  });
  const [localActiveCand, setLocalActiveCand] = useState<number | null>(null);

  const review = controlled ? ctrlReview : localReview;
  const reviewLoading = controlled ? !!ctrlReviewLoading : localReviewLoading;
  const activeAnnoId = controlled
    ? (ctrlActiveAnnoId ?? null)
    : localActiveCand != null
      ? `bp-${localActiveCand}`
      : null;
  const onActivateCandidate = controlled
    ? ctrlOnActivate!
    : (i: number | null) => setLocalActiveCand(i);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showHistorical, setShowHistorical] = useState(false);
  const bodyRef = useRef<HTMLDivElement | null>(null);

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

  // 不再自动开聊: 打开时只展示确定性结论, 用户点 chip 主动激活,
  // 想聊再打字. 自动开聊会让 LLM 一坨文本抢屏, 反而挡住 next_step / 未来买点.

  // agent 最新一条消息里若提到「买点N」，自动把主图/卡片联动到那个买点
  useEffect(() => {
    const last = [...turns].reverse().find((t) => t.who === "agent");
    if (!last || !review) return;
    const notable = notableCandidates(review.candidates);
    const matches = [...last.text.matchAll(BP_RE)];
    if (matches.length === 0) return;
    const idx = parseBpIndex(matches[matches.length - 1][1]);
    if (idx != null && idx < notable.length) onActivateCandidate(idx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turns, review]);

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

  const activeCand = annoToIndex(activeAnnoId);
  const notable = review ? notableCandidates(review.candidates) : [];
  const activeCandidate = activeCand != null ? notable[activeCand] : undefined;

  return (
    <>
      {!controlled && <div className="drawer-overlay" onClick={onClose} />}
      <aside className={`bp-panel${controlled ? "" : " bp-standalone"}`}>
        <div className="bp-head">
          <h2>买点分析 · {symbol}</h2>
          <div className="bp-head-actions">
            {review?.suggested_plan && (
              <button className="btn small" onClick={() => setShowCreate(true)}>
                据此建计划
              </button>
            )}
            <button className="btn small" onClick={onClose}>关闭</button>
          </div>
        </div>

        {/* 结论区：上方一行「判定徽章 + 日期」，下方整行展开结论原文，
            避免长摘要被徽章/日期挤成窄高的一坨竖排。 */}
        {reviewLoading && !review && <div className="muted">正在审阅…</div>}
        {review && (
          <div className="bp-verdict-line">
            <div className="bp-verdict-meta">
              <span
                className="bp-verdict-chip"
                style={{ background: VERDICT_STYLE[review.verdict] || "var(--text-faint)" }}
              >
                {review.verdict_cn}
              </span>
              <span className="bp-verdict-date">
                {review.as_of} · 收盘 {review.last_close ?? "-"}
              </span>
            </div>
            <p className="bp-summary">{review.summary_cn}</p>
          </div>
        )}

        {/* 共振买点: 同价位 ±1.5% 内多个 rule 共识, 合并展示, 避免重复 */}
        {review && review.resonance_groups.length > 0 && (
          <ResonancePanel groups={review.resonance_groups} />
        )}

        {/* 买点序号选择器: 标签带 scenario 简述, 不用 hover 才能知道是啥 */}
        {notable.length > 0 && (
          <div className="bp-chips">
            {notable.map((c, i) => (
              <button
                key={c.scenario_id}
                className={`bp-chip ${activeCand === i ? "active" : ""}`}
                onClick={() => onActivateCandidate(activeCand === i ? null : i)}
                title={c.scenario_cn}
              >
                买点{circled(i)} · {c.scenario_cn}
              </button>
            ))}
          </div>
        )}

        {/* 当前买点的聚焦卡片（与主图高亮一一对应） */}
        {activeCandidate && activeCand != null && (
          <CandidateCard
            c={activeCandidate}
            index={activeCand}
            onActivate={onActivateCandidate}
          />
        )}

        {/* 未来买点 (watch_conditions): 提到 chat 之上, 直接回答"潜在哪里买".
            每条配 [设提醒] 按钮, 命中后由 14:45 checker 翻 pending_confirmation. */}
        {review && review.watch_conditions.length > 0 && (() => {
          const firstCand = notable[0];
          return (
            <WatchConditionsPanel
              symbol={symbol}
              conditions={review.watch_conditions}
              candidateDirection={
                review.suggested_plan?.direction ?? firstCand?.direction ?? "long"
              }
              candidateModule={
                review.suggested_plan?.module ?? firstCand?.module ?? "A"
              }
              sourceRuleId={
                review.suggested_plan?.entry_rule_id ?? firstCand?.rule_id ?? null
              }
              sourceCandidateId={firstCand?.scenario_id ?? null}
            />
          );
        })()}

        <div className="bp-body" ref={bodyRef}>
          {turns.length === 0 && !ask.isPending && (
            <div className="bp-empty-chat muted">
              已审阅 {notable.length} 个候选 · 共振 {review?.resonance_groups.length ?? 0} 组
              <br />
              点上方「买点」看入场/止损/下一步; 这里可以就买点提问.
            </div>
          )}
          {turns.map((turn, i) => (
            <div className={`turn ${turn.who}`} key={i}>
              <div className="who">{turn.who === "you" ? "你" : "分析"}</div>
              <div className="msg">
                {turn.who === "agent" ? (
                  <AgentMarkdown text={turn.text} onBp={(i) => onActivateCandidate(i)} notableCount={notable.length} />
                ) : (
                  turn.text
                )}
              </div>
              {turn.who === "agent" && turn.grounded !== undefined && (
                <div className={`grounded-tag ${turn.grounded ? "" : "warn"}`}>
                  {turn.grounded
                    ? "已过接地校验"
                    : "已降级为结构化模板（LLM 输出不可用：超时 / 被截断 / 未过接地校验）"}
                </div>
              )}
            </div>
          ))}
          {ask.isPending && (
            <div className="bp-spinner-wrap">
              <span className="bp-spinner" />
              <span className="muted">分析中…</span>
            </div>
          )}
        </div>

        <div className="bp-input">
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

        {review && <div className="muted bp-disclaimer">{review.disclaimer_cn}</div>}

        {/* 历史结构: recency 过滤掉的过期结构, 默认折叠, 仅作文案历史参考 */}
        {review && review.historical_structures.length > 0 && (
          <HistoricalPanel
            items={review.historical_structures}
            expanded={showHistorical}
            onToggle={() => setShowHistorical((v) => !v)}
          />
        )}
      </aside>

      {showCreate && (
        <PlanCreateFlow
          symbol={symbol}
          prefill={prefill}
          onClose={() => setShowCreate(false)}
        />
      )}
    </>
  );
}

/** 聚焦的买点卡片: 默认展开 (chat 不再自动抢屏, 空间够),
 * 露入场下一步/满足条件/缺失条件, 解决"我不知道该不该买"的痛点.
 * 折叠按钮可手动收起, 留出聊天空间. */
function CandidateCard({
  c,
  index,
  onActivate,
}: {
  c: BuyPointCandidate;
  index: number;
  onActivate: (index: number | null) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div
      className={`bp-card active${expanded ? " expanded" : ""}`}
      onClick={(e) => {
        // 折叠按钮单独处理，不触发取消激活
        if ((e.target as HTMLElement).closest(".bp-card-toggle")) return;
        onActivate(index);
      }}
    >
      <div className="bp-card-head">
        <b>买点{circled(index)} · {c.scenario_cn}</b>
        <span className="muted">[{c.state_cn}]</span>
        {c.module && <span className="sv-kind-chip">{moduleCn(c.module)}</span>}
        <span
          className="bp-card-toggle"
          role="button"
          aria-label={expanded ? "收起买点详情" : "展开买点详情"}
          title={expanded ? "收起详情" : "展开详情"}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
        >
          {expanded ? "▼" : "▶"}
        </span>
      </div>
      {/* 价位行始终显示——这是用户最常看的 3 项 */}
      <div className="bp-prices">
        <span>关键价 {c.key_price ?? "-"}</span>
        <span>止损 {c.invalidation_price ?? "（系统未给出，建计划时确认）"}</span>
        <span>
          {c.reward_risk_computable ? `R/R ${c.reward_risk_ratio}` : "R/R 不可计算"}
        </span>
      </div>
      {expanded && (
        <>
          {c.satisfied_conditions.length > 0 && (
            <div className="bp-cond">✓ {c.satisfied_conditions.join("；")}</div>
          )}
          {c.missing_conditions.length > 0 && (
            <div className="bp-cond miss">✗ {c.missing_conditions.join("；")}</div>
          )}
          {c.next_step_cn && <div className="bp-next">下一步：{c.next_step_cn}</div>}
          {c.caveat_cn && <div className="bp-caveat">注意：{c.caveat_cn}</div>}
          <div className="muted" style={{ fontSize: 11 }}>
            rule_id:{c.rule_id ?? "-"} · 判定方式为研究代理
          </div>
        </>
      )}
    </div>
  );
}

/** 共振买点面板: 展示同一价位 ±1.5% 内多个 rule 的共识。
 *  - 默认展开第一条, 其余折叠 (避免长面板)
 *  - 不与 chips 联动 (共振不是单个候选, 不进 chat 高亮) */
function ResonancePanel({ groups }: { groups: ResonanceGroup[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);
  if (groups.length === 0) return null;
  return (
    <div className="bp-resonance">
      <div className="bp-resonance-head">📡 共振买点 ({groups.length})</div>
      {groups.map((g, gi) => (
        <div
          key={gi}
          className={`bp-resonance-item${expandedIdx === gi ? " expanded" : ""}`}
          onClick={() => setExpandedIdx(expandedIdx === gi ? null : gi)}
        >
          <div className="bp-resonance-row">
            <b>价位 {g.level.toFixed(2)}</b>
            <span className="muted">±{(g.tolerance_pct * 100).toFixed(1)}%</span>
            <span className="muted">· {g.rule_ids.length} 个 rule 共识</span>
            <span className="bp-resonance-toggle">
              {expandedIdx === gi ? "▼" : "▶"}
            </span>
          </div>
          {expandedIdx === gi && (
            <div className="bp-resonance-detail">
              {g.candidates.map((c, ci) => (
                <div key={ci} className="bp-resonance-line">
                  · {c.scenario_cn} [{c.state_cn}] 关键价 {c.key_price?.toFixed(2) ?? "-"}
                  <span className="muted"> · {c.rule_id ?? "-"}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/** 历史结构面板: 展示被 recency 过滤掉的过期结构, 默认折叠。 */
function HistoricalPanel({
  items,
  expanded,
  onToggle,
}: {
  items: HistoricalStructure[];
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="bp-historical">
      <div className="bp-historical-head" onClick={onToggle} role="button">
        <span>
          📜 历史结构 ({items.length}) — 超出 recency 窗口, 仅作文案历史参考
        </span>
        <span className="bp-historical-toggle">{expanded ? "▼" : "▶"}</span>
      </div>
      {expanded && (
        <div className="bp-historical-detail">
          {items.map((h, hi) => (
            <div key={hi} className="bp-historical-line">
              · {h.scenario_cn} [{h.state_cn}] {h.days_since} 天前
              {h.key_price != null && ` · 关键价 ${h.key_price.toFixed(2)}`}
              <span className="muted"> · {h.rule_id ?? "-"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
