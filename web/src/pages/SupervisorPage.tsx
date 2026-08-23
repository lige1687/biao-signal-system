import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AgentDrawer from "../components/AgentDrawer";
import BuyPointDrawer from "../components/BuyPointDrawer";
import ProvenanceBadge from "../components/ProvenanceBadge";
import { directionCn, moduleCn } from "../modules";
import type { ActionItem, Plan, PlanAlert } from "../types";

const SEVERITY_CN: Record<string, string> = {
  block: "■ 阻断",
  remind: "■ 提醒",
  hint: "□ 提示",
};
const SEVERITY_ORDER: Record<string, number> = { block: 0, remind: 1, hint: 2 };
const KIND_CN: Record<string, string> = { ENTER: "入场", EXIT: "退出", REVIEW: "复核" };
const VERDICT_COLOR: Record<string, string> = {
  actionable: "var(--lei-green)",
  blocked: "var(--warn)",
  waiting: "var(--text-faint)",
  none: "var(--text-faint)",
};

/** 单条待办：已执行 / 推迟（推迟需原因 + 系统可计算的恢复条件）。 */
function ActionRow({ plan, item }: { plan: Plan; item: ActionItem }) {
  const queryClient = useQueryClient();
  const [deferring, setDeferring] = useState(false);
  const [reason, setReason] = useState("");
  const [resumeRaw, setResumeRaw] = useState('{"field":"close","op":">=","ref":"ema20"}');
  const [error, setError] = useState("");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["planActions", plan.plan_id] });
    queryClient.invalidateQueries({ queryKey: ["plans"] });
    queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
  };

  const done = useMutation({
    mutationFn: () => api.doneAction(plan.plan_id, item.action_id),
    onSuccess: invalidate,
    onError: (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
  });

  const defer = useMutation({
    mutationFn: () => {
      let predicate: Record<string, unknown>;
      try {
        predicate = JSON.parse(resumeRaw);
      } catch {
        throw new Error("恢复条件必须是合法 JSON");
      }
      return api.deferAction(plan.plan_id, item.action_id, {
        reason_cn: reason.trim(),
        resume_on: predicate,
      });
    },
    onSuccess: () => {
      setDeferring(false);
      setReason("");
      invalidate();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
  });

  const busy = done.isPending || defer.isPending;

  return (
    <div>
      <div className="sv-action-row">
        <span className="kind">{KIND_CN[item.kind] ?? item.kind}</span>
        <span className="muted">{item.source_alert_code}</span>
        {item.nag_count > 0 && <span className="nag">催办第 {item.nag_count} 次</span>}
        <span className="due">可执行日 {item.due_from ?? "-"}</span>
        <button className="btn small" disabled={busy} onClick={() => done.mutate()}>
          已执行
        </button>
        <button
          className="btn small"
          disabled={busy}
          onClick={() => {
            setError("");
            setDeferring((v) => !v);
          }}
        >
          推迟
        </button>
      </div>
      {deferring && (
        <div className="sv-defer-inline">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="推迟原因（必填）"
          />
          <input
            value={resumeRaw}
            onChange={(e) => setResumeRaw(e.target.value)}
            placeholder='恢复条件 JSON，如 {"field":"close","op":">=","ref":"ema20"} 或 {"rule_id":"..."}'
          />
          <span className="cp-hint">
            恢复条件只能引用系统算得出的字段（close / ema20 / tradability.tradable）或已注册 rule_id。
          </span>
          <div>
            <button
              className="btn small primary"
              disabled={busy || !reason.trim()}
              onClick={() => {
                setError("");
                defer.mutate();
              }}
            >
              {defer.isPending ? "提交中…" : "确认推迟"}
            </button>
          </div>
        </div>
      )}
      {error && <div className="cp-error">{error}</div>}
    </div>
  );
}

function PlanCard({ plan, onAsk }: { plan: Plan; onAsk: () => void }) {
  const { data: alerts } = useQuery({
    queryKey: ["planAlerts", plan.plan_id],
    queryFn: () => api.planAlerts(plan.plan_id),
  });
  const { data: actions } = useQuery({
    queryKey: ["planActions", plan.plan_id],
    queryFn: () => api.planActions(plan.plan_id, "open"),
  });

  const ordered: PlanAlert[] = [...(alerts ?? [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  const entryBlocked = ordered.some(
    (a) => a.severity === "block" && a.code.startsWith("ENTRY_"),
  );
  const isHolding = plan.plan_kind === "holding_watch";

  return (
    <div className="sv-plan-card">
      <div className="sv-head">
        <b>
          <Link to={`/symbol/${encodeURIComponent(plan.symbol)}`}>{plan.symbol}</Link>
        </b>
        {isHolding && <span className="sv-kind-chip">持仓盯盘</span>}
        <span className="muted">
          {isHolding
            ? `${directionCn(plan.direction)} · 只监督退出`
            : `${moduleCn(plan.module)} · ${directionCn(plan.direction)} · ${plan.entry_rule_id ?? "-"}`}
        </span>
        <span className={`sv-state ${plan.state}`}>{plan.state}</span>
        <span className="muted" style={{ fontSize: 11 }}>
          有效期至 {plan.valid_until || "-"}
          {plan.entered_on && ` · 入场日 ${plan.entered_on}`}
          {plan.exited_on && ` · 退出日 ${plan.exited_on}`}
        </span>
        <span style={{ flex: 1 }} />
        <button className="btn small" onClick={onAsk}>
          问 agent
        </button>
      </div>

      {isHolding ? (
        <div className="sv-playbook">
          <div className="sv-trigger">
            {plan.take_profit_price != null && (
              <>止盈 <b>{plan.take_profit_price}</b>　</>
            )}
            {plan.stop_price != null && <>止损 <b>{plan.stop_price}</b>　</>}
            {plan.watch_signal_rule_ids.length > 0 && (
              <>盯盘信号 <b>{plan.watch_signal_rule_ids.join(", ")}</b></>
            )}
          </div>
          <div>止盈预案：{plan.take_profit_plan_cn || "-"}</div>
          <div>止损预案：{plan.stop_plan_cn || "-"}</div>
        </div>
      ) : (
        <div className="sv-playbook">
          <div>假设：{plan.thesis_cn || "-"}</div>
          <div>失效标准：{plan.invalidation_criteria_cn || "-"}</div>
          <div>
            失效价 {plan.invalidation_price ?? "-"} · 目标B {plan.target_b_price ?? "-"} · R/R{" "}
            {plan.reward_risk_at_plan ?? "-"}
          </div>
        </div>
      )}

      {entryBlocked && (
        <div className="cp-error">
          本轮存在入场阻断条件，按规则不开新仓（规格 §13）；下列入场类提醒被压制。
        </div>
      )}

      {ordered.length > 0 && (
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          {ordered.map((a) => (
            <div key={a.code} style={{ marginBottom: 4 }}>
              <span>{SEVERITY_CN[a.severity] ?? a.severity}</span>{" "}
              <span>{a.next_step_cn || a.code}</span>
              <ProvenanceBadge
                items={[
                  {
                    label: a.next_step_cn || a.code,
                    rule_id: a.rule_id ?? null,
                    evidence_cn: Object.entries(a.evidence ?? {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join("；"),
                    research_proxy: true,
                    principle_source: a.principle_source ?? null,
                  },
                ]}
              />
            </div>
          ))}
        </div>
      )}

      {actions && actions.length > 0 && (
        <div className="sv-actions">
          {actions.map((item) => (
            <ActionRow key={item.action_id} plan={plan} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SupervisorPage() {
  const [askPlanId, setAskPlanId] = useState<string | null>(null);
  const [scanSymbol, setScanSymbol] = useState<string | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const { data: armed, isLoading: l1 } = useQuery({
    queryKey: ["plans", "armed"],
    queryFn: () => api.listPlans({ state: "armed" }),
  });
  const { data: entered, isLoading: l2 } = useQuery({
    queryKey: ["plans", "entered"],
    queryFn: () => api.listPlans({ state: "entered" }),
  });
  const { data: scan, refetch: scanRefetch, isFetching: scanFetching } = useQuery({
    queryKey: ["opportunityScan"],
    queryFn: () => api.opportunityScan(),
    enabled: false,  // 只在点开时拉
  });

  const plans = [...(entered ?? []), ...(armed ?? [])];

  return (
    <div className="page" style={{ padding: "14px 18px" }}>
      <h2 style={{ margin: "0 0 4px" }}>监督待办</h2>
      <p className="muted" style={{ fontSize: 12, margin: "0 0 14px" }}>
        活跃计划（entered / armed）与当日判定。待办的「已执行 / 推迟」与飞书回执写同一套状态机。
      </p>

      <div className="sv-scan">
        <button
          className="btn small sv-scan-toggle"
          onClick={() => {
            const next = !scanOpen;
            setScanOpen(next);
            if (next) scanRefetch();
          }}
        >
          {scanOpen ? "▼" : "▶"} 扫描自选买点
        </button>
        {scanOpen && (
          <>
            {scanFetching && <div className="muted" style={{ fontSize: 12 }}>扫描中…</div>}
            {scan && scan.items.length > 0 && (
              <table className="sv-scan-table">
                <thead>
                  <tr>
                    <th>标的</th><th>状态</th><th>最佳机会</th><th>R/R</th>
                    <th>缺什么</th><th>已有计划</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {scan.items.map((it) => (
                    <tr key={it.symbol}>
                      <td>
                        <Link to={`/symbol/${encodeURIComponent(it.symbol)}`}>
                          {it.display_name || it.symbol}
                        </Link>
                      </td>
                      <td>
                        <span
                          className="sv-scan-verdict"
                          style={{ background: VERDICT_COLOR[it.verdict] || "var(--text-faint)" }}
                        >
                          {it.verdict_cn}
                        </span>
                      </td>
                      <td>{it.best_scenario_cn ?? "-"}</td>
                      <td>
                        {it.reward_risk_computable ? it.reward_risk_ratio?.toFixed(1) : "-"}
                      </td>
                      <td className="muted" style={{ fontSize: 11 }}>
                        {it.missing_summary_cn || it.blocking_reasons.join("、") || "-"}
                      </td>
                      <td>{it.has_active_plan ? "是" : "否"}</td>
                      <td>
                        <button
                          className="btn small"
                          onClick={() => setScanSymbol(it.symbol)}
                        >
                          分析
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {scan && scan.items.length === 0 && !scanFetching && (
              <div className="muted" style={{ fontSize: 12, padding: "8px 0" }}>
                当前自选无系统定义的买点。
              </div>
            )}
          </>
        )}
      </div>

      {(l1 || l2) && <div className="loading">加载中…</div>}

      {!l1 && !l2 && plans.length === 0 && (
        <div className="sv-empty">
          还没有活跃计划。到{" "}
          <Link to="/">看盘页</Link> 选一个标的，点右上角「建立执行计划」。
        </div>
      )}

      {plans.map((plan) => (
        <PlanCard
          key={plan.plan_id}
          plan={plan}
          onAsk={() => setAskPlanId(plan.plan_id)}
        />
      ))}

      {askPlanId && (
        <AgentDrawer planId={askPlanId} onClose={() => setAskPlanId(null)} />
      )}

      {scanSymbol && (
        <BuyPointDrawer symbol={scanSymbol} onClose={() => setScanSymbol(null)} />
      )}
    </div>
  );
}
