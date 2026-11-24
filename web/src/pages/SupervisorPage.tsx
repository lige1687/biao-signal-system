import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { agentConsoleStore } from "../App";
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
  actionable: "var(--biao-green)",
  blocked: "var(--warn)",
  waiting: "var(--text-faint)",
  none: "var(--text-faint)",
};

/** 只展示查询状态；旧记录不代表当前提醒已核对。 */
function QueryAvailability({ label, query, note }: {
  label: string;
  query: {
    data: unknown; isPending: boolean; isError: boolean; isFetching: boolean;
    error: unknown; dataUpdatedAt: number; refetch: () => unknown;
  };
  note?: string;
}) {
  const cached = query.data !== undefined;
  const cacheNote = cached
    ? `显示上次成功读取的记录${query.dataUpdatedAt ? `（读取于 ${new Date(query.dataUpdatedAt).toLocaleString("zh-CN", { hour12: false })}）` : ""}；当前资料尚未更新。`
    : "";
  if (query.isError) return <div className="cp-error" role="alert">
    {label}读取失败：{query.error instanceof Error ? query.error.message : "请稍后重试"}。{cacheNote}{note}
    <button className="btn small" disabled={query.isFetching} onClick={() => void query.refetch()}>重新读取{label}</button>
  </div>;
  if (query.isPending || query.isFetching) return <div className="muted" role="status">
    {label}{cached ? "正在更新…" : "加载中…"}{cacheNote}{note}
  </div>;
  return null;
}

/** 单条待办：已执行 / 推迟（推迟需原因 + 系统可计算的恢复条件）。 */
export function ActionRow({ plan, item }: { plan: Plan; item: ActionItem }) {
  const queryClient = useQueryClient();
  const [deferring, setDeferring] = useState(false);
  const [confirmingDone, setConfirmingDone] = useState(false);
  const [dateKnown, setDateKnown] = useState(false);
  const [actionDate, setActionDate] = useState("");
  const doneSubmitting = useRef(false);
  const attemptedDate = useRef<string | null | undefined>(undefined);
  const [reason, setReason] = useState("");
  const [resumeMode, setResumeMode] = useState("");
  const [price, setPrice] = useState("");
  const [priceOp, setPriceOp] = useState(">=");
  const [ruleId, setRuleId] = useState("");
  const [resumeRaw, setResumeRaw] = useState("");
  const [error, setError] = useState("");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["planActions", plan.plan_id] });
    queryClient.invalidateQueries({ queryKey: ["plans"] });
    queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
  };

  const done = useMutation({
    mutationFn: (actualDate: string | null) => api.doneAction(plan.plan_id, item.action_id, { actual_action_date: actualDate }),
    onSuccess: invalidate,
    onError: (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    onSettled: () => { doneSubmitting.current = false; },
  });

  const defer = useMutation({
    mutationFn: () => {
      let predicate: Record<string, unknown>;
      if (resumeMode === "price") {
        const value = Number(price);
        if (!price.trim() || !Number.isFinite(value) || value <= 0) throw new Error("请填写有效的恢复价格");
        predicate = { field: "close", op: priceOp, ref: value };
      } else if (resumeMode === "ema20") {
        predicate = { field: "close", op: ">=", ref: "ema20" };
      } else if (resumeMode === "tradable") {
        predicate = { field: "tradability.tradable", op: "==", ref: true };
      } else if (resumeMode === "rule") {
        if (!ruleId.trim()) throw new Error("请选择或填写已注册的事件规则");
        predicate = { rule_id: ruleId.trim() };
      } else if (resumeMode === "advanced") {
        try {
          predicate = JSON.parse(resumeRaw);
        } catch {
          throw new Error("高级恢复条件必须是合法 JSON");
        }
        if (!predicate || Array.isArray(predicate) || typeof predicate !== "object") {
          throw new Error("高级恢复条件必须是 JSON 对象");
        }
      } else {
        throw new Error("请选择恢复条件");
      }
      return api.deferAction(plan.plan_id, item.action_id, {
        reason_cn: reason.trim(),
        resume_on: predicate,
      });
    },
    onSuccess: () => {
      setDeferring(false);
      setReason("");
      setResumeMode("");
      setPrice("");
      setRuleId("");
      setResumeRaw("");
      invalidate();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
  });

  const busy = done.isPending || defer.isPending;
  const recorded = done.data ?? item;
  const handleDone = () => {
    if (busy || doneSubmitting.current || item.completion_evidence_supported !== true) return;
    const actualDate = dateKnown ? actionDate : null;
    if (attemptedDate.current !== undefined && attemptedDate.current !== actualDate) {
      setError("上次提交结果未确认，日期已修改。请先刷新核对完成记录；相同内容可重试，不要另填日期重复确认。");
      return;
    }
    if (actualDate !== null) {
      const parsed = new Date(`${actualDate}T00:00:00Z`);
      const todayShanghai = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      if (!/^\d{4}-\d{2}-\d{2}$/.test(actualDate) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== actualDate || actualDate > todayShanghai) {
        setError("请填写有效的动作日期，不能晚于今天（上海时间）；不知道日期可选择未知。");
        return;
      }
    }
    setError("");
    attemptedDate.current = actualDate;
    doneSubmitting.current = true;
    done.mutate(actualDate);
  };
  if (recorded.state === "done") return (
    <div className="sv-action-row" role="status">
      <span>{KIND_CN[recorded.kind] ?? recorded.kind} · 已完成</span>
      <span>最早可处理日：{recorded.due_from || "未知"}</span>
      <span>用户声明动作日期：{recorded.actual_action_date || "未知"}</span>
      <span>首次录入：{recorded.done_recorded_at || "未知（旧记录未留存）"}</span>
    </div>
  );

  return (
    <div>
      <div className="sv-action-row">
        <span className="kind">{KIND_CN[item.kind] ?? item.kind}</span>
        <span className="muted">{item.source_alert_code}</span>
        {item.nag_count > 0 && <span className="nag">催办第 {item.nag_count} 次</span>}
        <span className="due">最早可处理日 {item.due_from ?? "未知"}</span>
        <button className="btn small" disabled={busy || item.completion_evidence_supported !== true} onClick={() => { setError(""); setConfirmingDone((value) => !value); }}>
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
      {item.completion_evidence_supported !== true && <p className="muted">当前服务暂不支持留存动作日期和首次录入，暂不能确认已执行。</p>}
      {confirmingDone && (
        <div className="sv-defer-inline">
          <label>动作日期
            <select aria-label="动作日期是否已知" value={dateKnown ? "known" : "unknown"} disabled={busy} onChange={(e) => setDateKnown(e.target.value === "known")}>
              <option value="unknown">未知（不代填今天）</option>
              <option value="known">我知道动作日期</option>
            </select>
          </label>
          {dateKnown && <label>用户声明动作日期<input aria-label="用户声明动作日期" type="date" value={actionDate} disabled={busy} onChange={(e) => setActionDate(e.target.value)} /></label>}
          <span className="muted">最早可处理日不是实际动作日期。首次确认记录后不能直接改写日期。</span>
          <button className="btn small primary" disabled={busy || item.completion_evidence_supported !== true} onClick={handleDone}>{done.isPending ? "正在记录…" : "确认已执行"}</button>
        </div>
      )}
      {deferring && (
        <div className="sv-defer-inline">
          <label>推迟原因<input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="推迟原因（必填）"
          /></label>
          <label>何时重新提醒
            <select value={resumeMode} onChange={(e) => setResumeMode(e.target.value)}>
              <option value="">请选择，不代填交易条件</option>
              <option value="price">收盘价达到指定价格</option>
              <option value="ema20">收盘价重新站上 EMA20</option>
              <option value="tradable">标的重新可交易</option>
              <option value="rule">已有事件规则再次出现</option>
              <option value="advanced">高级条件（JSON）</option>
            </select>
          </label>
          {resumeMode === "price" && <div className="sv-resume-fields">
            <label>价格方向<select value={priceOp} onChange={(e) => setPriceOp(e.target.value)}>
              <option value=">=">收盘价大于或等于</option>
              <option value="<=">收盘价小于或等于</option>
            </select></label>
            <label>价格<input type="number" min="0" step="any" value={price}
              onChange={(e) => setPrice(e.target.value)} placeholder="填写价格" /></label>
          </div>}
          {resumeMode === "rule" && <label>事件规则
            <input list={`resume-rules-${item.action_id}`} value={ruleId}
              onChange={(e) => setRuleId(e.target.value)} placeholder="选择或填写已注册 rule_id" />
            <datalist id={`resume-rules-${item.action_id}`}>
              {[plan.entry_rule_id, ...plan.watch_signal_rule_ids].filter(Boolean).map((id) =>
                <option key={id} value={id ?? ""} />)}
            </datalist>
          </label>}
          {resumeMode === "advanced" && <label>高级恢复条件 JSON
            <textarea value={resumeRaw} onChange={(e) => setResumeRaw(e.target.value)}
              placeholder='例如 {"field":"close","op":">=","ref":"ema20"}' />
          </label>}
          <span className="cp-hint">
            恢复条件只在系统数据满足时重新提醒；目前不支持按日期或手动恢复。事件规则须已在系统注册。
          </span>
          <div>
            <button
              className="btn small primary"
              disabled={busy || !reason.trim() || !resumeMode}
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

export function PlanCard({ plan, onAsk, focused = false }: { plan: Plan; onAsk: () => void; focused?: boolean }) {
  const alertsQuery = useQuery({
    queryKey: ["planAlerts", plan.plan_id],
    queryFn: () => api.planAlerts(plan.plan_id),
  });
  const actionsQuery = useQuery({
    queryKey: ["planActions", plan.plan_id],
    queryFn: () => api.planActions(plan.plan_id),
  });

  const actions = actionsQuery.data;
  const openActions = (actions ?? []).filter((item) => item.state === "open");
  const recentDone = (actions ?? []).filter((item) => item.state === "done")
    .sort((a, b) => (b.done_recorded_at || "").localeCompare(a.done_recorded_at || "")).slice(0, 5);
  const ordered: PlanAlert[] = [...(alertsQuery.data ?? [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  const entryBlocked = ordered.some(
    (a) => a.severity === "block" && a.code.startsWith("ENTRY_"),
  );
  const isHolding = plan.plan_kind === "holding_watch";

  return (
    <div className={`sv-plan-card${focused ? " sv-focused-plan" : ""}`} id={`plan-${plan.plan_id}`}>
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
          {plan.entered_on && ` · 存档入场日期 ${plan.entered_on}（来源未核实）`}
          {plan.exited_on && ` · 存档退出日期 ${plan.exited_on}（来源未核实）`}
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

      <QueryAvailability label="计划提醒" query={alertsQuery} note="尚未核对当前提醒，不能据此认为没有风险。" />
      <QueryAvailability label="计划待办" query={actionsQuery} />

      {entryBlocked && (
        <div className="cp-error">
          {alertsQuery.isError || alertsQuery.isFetching
            ? "上次记录存在入场阻断提示；当前提醒尚未更新，请核对后使用。"
            : "本轮存在入场阻断条件，按规则不开新仓（规格 §13）；下列入场类提醒被压制。"}
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
                    research_proxy: a.logic_provenance === "research_proxy",
                    principle_source: a.principle_source ?? null,
                  },
                ]}
              />
            </div>
          ))}
        </div>
      )}

      {openActions.length > 0 && (
        <div className="sv-actions">
          {openActions.map((item) => (
            <ActionRow key={item.action_id} plan={plan} item={item} />
          ))}
        </div>
      )}
      {recentDone.length > 0 && (
        <div className="sv-actions">
          <h4>最近完成记录（最多5条）</h4>
          {recentDone.map((item) => <ActionRow key={item.action_id} plan={plan} item={item} />)}
        </div>
      )}
    </div>
  );
}

export default function SupervisorPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const focusedSymbol = searchParams.get("symbol")?.trim() ?? "";
  const [scanSymbol, setScanSymbol] = useState<string | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const armedQuery = useQuery({
    queryKey: ["plans", "armed"],
    queryFn: () => api.listPlans({ state: "armed" }),
  });
  const enteredQuery = useQuery({
    queryKey: ["plans", "entered"],
    queryFn: () => api.listPlans({ state: "entered" }),
  });
  const scanQuery = useQuery({
    queryKey: ["opportunityScan"],
    queryFn: () => api.opportunityScan(),
    enabled: false,  // 只在点开时拉
  });

  const scan = scanQuery.data;
  const plans = [...(enteredQuery.data ?? []), ...(armedQuery.data ?? [])];
  const shownPlans = focusedSymbol
    ? plans.filter((plan) => plan.symbol.toUpperCase() === focusedSymbol.toUpperCase())
    : plans;
  const listsReady = armedQuery.isSuccess && enteredQuery.isSuccess
    && !armedQuery.isFetching && !enteredQuery.isFetching;

  return (
    <div className="page">
      <div className="pg-head">
        <div className="pg-head-title">
          <h1>计划待办</h1>
          <span className="pg-head-sub">
            活跃计划（持仓中 / 等待触发）与当日判定，与飞书回执同步。
          </span>
        </div>
        <div className="pg-head-kv">
          <span className="pg-kv"><span className="k">活跃计划</span><b>{listsReady ? plans.length : "加载中"}</b></span>
        </div>
      </div>

      <div className="sv-scan">
        <button
          className="btn small sv-scan-toggle"
          onClick={() => {
            const next = !scanOpen;
            setScanOpen(next);
            if (next) void scanQuery.refetch();
          }}
        >
          {scanOpen ? "▼" : "▶"} 扫描自选买点
        </button>
        {scanOpen && (
          <>
            <QueryAvailability label="买点扫描" query={scanQuery} />
            {scan && scan.items.length > 0 && (
              <table className="sv-scan-table">
                <thead>
                  <tr>
                    <th>标的</th><th>状态</th><th>最佳机会</th><th>盈亏比</th>
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
            {scanQuery.isSuccess && scan && scan.items.length === 0 && !scanQuery.isFetching && (
              <div className="muted" style={{ fontSize: 12, padding: "8px 0" }}>
                当前自选无系统定义的买点。
              </div>
            )}
          </>
        )}
      </div>

      <QueryAvailability label="待入场计划" query={armedQuery} />
      <QueryAvailability label="持仓中计划" query={enteredQuery} />

      {focusedSymbol && <div className="sv-focus-filter" role="status">
        正在查看 {focusedSymbol} 的计划与待办（{listsReady ? shownPlans.length : "读取中"} 条）
        <button className="btn small" onClick={() => setSearchParams({})}>查看全部</button>
      </div>}

      {listsReady && shownPlans.length === 0 && (
        <div className="sv-empty">
          {focusedSymbol
            ? <>当前没有 {focusedSymbol} 的活跃计划。<button className="btn small" onClick={() => setSearchParams({})}>查看全部计划</button></>
            : <>还没有活跃计划。到 <Link to="/">看盘页</Link> 选一个标的，点右上角「建立执行计划」。</>}
        </div>
      )}

      {shownPlans.map((plan) => (
        <PlanCard
          key={plan.plan_id}
          plan={plan}
          focused={Boolean(focusedSymbol)}
          onAsk={() => agentConsoleStore.openConsole(plan.symbol)}
        />
      ))}

      {scanSymbol && (
        <BuyPointDrawer symbol={scanSymbol} onClose={() => setScanSymbol(null)} />
      )}
    </div>
  );
}
