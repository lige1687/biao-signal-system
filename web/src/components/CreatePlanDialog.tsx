import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { CreatePlanPayload, TradeOpportunity } from "../types";

/** 从当前 assessment 机会预填的入场字段（缺则空，让人填，不算法新数值）。 */
export type PlanPrefill = Partial<
  Pick<
    CreatePlanPayload,
    | "module"
    | "direction"
    | "entry_rule_id"
    | "entry_lifecycle_id"
    | "entry_trigger_cn"
    | "entry_price_ref"
    | "invalidation_price"
    | "target_b_price"
    | "reward_risk_at_plan"
  >
>;

/**
 * 从活跃交易机会推导预填。只取无歧义字段：
 * - direction / lifecycle_id / entry_rule_id / target_b(B1) / invalidation(structure C 点)
 * entry_price_ref 不预填（无明确来源，留给人填，不算法新数值）。
 */
export function prefillFromOpportunity(opp: TradeOpportunity | null): PlanPrefill {
  if (!opp) return {};
  return {
    direction: opp.direction,
    entry_lifecycle_id: opp.lifecycle_id,
    entry_rule_id: opp.supporting_event?.rule_id ?? null,
    entry_trigger_cn: opp.supporting_event?.rule_cn ?? opp.state_cn ?? null,
    target_b_price: opp.b1_price,
    invalidation_price: opp.structure?.c_price ?? null,
  };
}

const MODULES = ["A", "B", "C", "D"] as const;
const RULESET = "1.3.0";

/** 五项交易假设：写不出来=计划没想清楚，提交时强制非空。 */
const PLAYBOOK: { key: keyof CreatePlanPayload; label: string; hint: string }[] = [
  { key: "thesis_cn", label: "交易假设", hint: "为什么做这一笔" },
  { key: "invalidation_criteria_cn", label: "失效标准", hint: "什么情况说明逻辑错了" },
  { key: "drawdown_playbook_cn", label: "回撤预案", hint: "持仓中正常回撤如何应对" },
  { key: "take_profit_plan_cn", label: "止盈预案", hint: "什么逻辑进场就什么逻辑退出" },
  { key: "stop_plan_cn", label: "止损预案", hint: "结构止损 / 时间止损" },
];

/** 持仓盯盘只必填这两项（已在场内，入场理由不必再论证）。 */
const EXIT_PLAYBOOK_KEYS = ["take_profit_plan_cn", "stop_plan_cn"];

/** 常用盯盘信号：只列系统已注册且语义清楚的 rule_id。 */
const WATCH_SIGNALS: { id: string; label: string }[] = [
  { id: "lei_color", label: "LEI 颜色转换（灰转绿 / 转黑）" },
  { id: "dual_ma_bull_confirmed", label: "双均线共同确认（转强）" },
  { id: "exit_ema20_costbasis", label: "A6① 抵扣价退出（跌破 EMA20+抵扣价）" },
  { id: "top_structure", label: "顶部结构确认" },
  { id: "key_wave_black", label: "关键性波动转黑" },
];

export default function CreatePlanDialog({
  symbol,
  prefill,
  onClose,
}: {
  symbol: string;
  prefill: PlanPrefill;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  // 两种模式：entry=完整入场计划（五项预案）；holding=持仓盯盘（已在场内，只盯退出）
  const [mode, setMode] = useState<"entry" | "holding">("entry");
  const [module, setModule] = useState(prefill.module ?? "A");
  const [direction, setDirection] = useState(prefill.direction ?? "long");
  const [entryRuleId, setEntryRuleId] = useState(prefill.entry_rule_id ?? "");
  const [lifecycleId, setLifecycleId] = useState(prefill.entry_lifecycle_id ?? "");
  const [entryTriggerCn, setEntryTriggerCn] = useState(prefill.entry_trigger_cn ?? "");
  const [entryPriceRef, setEntryPriceRef] = useState(
    prefill.entry_price_ref != null ? String(prefill.entry_price_ref) : "",
  );
  const [invalidationPrice, setInvalidationPrice] = useState(
    prefill.invalidation_price != null ? String(prefill.invalidation_price) : "",
  );
  const [targetBPrice, setTargetBPrice] = useState(
    prefill.target_b_price != null ? String(prefill.target_b_price) : "",
  );
  const [rewardRisk, setRewardRisk] = useState(
    prefill.reward_risk_at_plan != null ? String(prefill.reward_risk_at_plan) : "",
  );
  const [validUntil, setValidUntil] = useState("");
  const [reason, setReason] = useState("");
  const [playbook, setPlaybook] = useState<Record<string, string>>({
    thesis_cn: "",
    invalidation_criteria_cn: "",
    drawdown_playbook_cn: "",
    take_profit_plan_cn: "",
    stop_plan_cn: "",
  });
  const [error, setError] = useState("");
  // 持仓盯盘专用
  const [takeProfitPrice, setTakeProfitPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [watchSignals, setWatchSignals] = useState<string[]>([]);

  const create = useMutation({
    mutationFn: async () => {
      const toNum = (s: string) => (s.trim() ? Number(s) : null);
      const payload: CreatePlanPayload = {
        symbol,
        module,
        direction,
        ruleset_version: RULESET,
        reason: reason.trim(),
        valid_until: validUntil.trim(),
        entry_rule_id: entryRuleId.trim() || null,
        entry_lifecycle_id: lifecycleId.trim() || null,
        entry_trigger_cn: entryTriggerCn.trim() || null,
        entry_price_ref: toNum(entryPriceRef),
        invalidation_price: toNum(invalidationPrice),
        target_b_price: toNum(targetBPrice),
        reward_risk_at_plan: toNum(rewardRisk),
        thesis_cn: playbook.thesis_cn.trim(),
        invalidation_criteria_cn: playbook.invalidation_criteria_cn.trim(),
        drawdown_playbook_cn: playbook.drawdown_playbook_cn.trim(),
        take_profit_plan_cn: playbook.take_profit_plan_cn.trim(),
        stop_plan_cn: playbook.stop_plan_cn.trim(),
      };
      const plan = await api.createPlan(payload);
      await api.confirmPlan(plan.plan_id);
      return plan;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
      onClose();
    },
    onError: (e: unknown) =>
      setError(e instanceof Error ? e.message : String(e)),
  });

  const playbookReady = PLAYBOOK.every((p) => playbook[p.key].trim());
  const canSubmit =
    playbookReady && validUntil.trim() && !create.isPending;

  const submit = () => {
    if (!playbookReady) {
      setError("五项交易假设必须全部填写--写不出来说明计划没想清楚。");
      return;
    }
    if (!validUntil.trim()) {
      setError("请填写有效期 valid_until。");
      return;
    }
    setError("");
    create.mutate();
  };

  const createHolding = useMutation({
    mutationFn: () => {
      const toNum = (s: string) => (s.trim() ? Number(s) : null);
      return api.createHoldingWatch({
        symbol,
        direction,
        ruleset_version: RULESET,
        valid_until: validUntil.trim(),
        take_profit_plan_cn: playbook.take_profit_plan_cn.trim(),
        stop_plan_cn: playbook.stop_plan_cn.trim(),
        take_profit_price: toNum(takeProfitPrice),
        stop_price: toNum(stopPrice),
        watch_signal_rule_ids: watchSignals,
        module,
        reason: reason.trim(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
      onClose();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
  });

  // 持仓盯盘：两项退出预案 + 有效期 + 至少一个触发条件
  const exitPlaybookReady = Boolean(
    playbook.take_profit_plan_cn.trim() && playbook.stop_plan_cn.trim(),
  );
  const hasTrigger = Boolean(
    takeProfitPrice.trim() || stopPrice.trim() || watchSignals.length > 0,
  );
  const canSubmitHolding =
    exitPlaybookReady &&
    Boolean(validUntil.trim()) &&
    hasTrigger &&
    !createHolding.isPending;

  const submitHolding = () => {
    if (!exitPlaybookReady) {
      setError("止盈预案与止损预案必须写明，否则价位到了仍会临场改主意。");
      return;
    }
    if (!validUntil.trim()) {
      setError("请填写有效期 valid_until。");
      return;
    }
    if (!hasTrigger) {
      setError("至少设置一个触发条件：止盈价 / 止损价 / 盯盘信号。");
      return;
    }
    setError("");
    createHolding.mutate();
  };

  const toggleSignal = (id: string) =>
    setWatchSignals((cur) =>
      cur.includes(id) ? cur.filter((s) => s !== id) : [...cur, id],
    );

  const field = (label: string, node: React.ReactNode, hint?: string) => (
    <label className="cp-field">
      <span className="cp-label">{label}</span>
      {node}
      {hint && <span className="cp-hint">{hint}</span>}
    </label>
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card cp-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{mode === "entry" ? "建立执行计划" : "持仓盯盘提醒"} · {symbol}</h2>
          <button className="btn small" onClick={onClose}>关闭</button>
        </div>

        <div className="add-tabs">
          <button
            className={`add-tab ${mode === "entry" ? "on" : ""}`}
            onClick={() => { setMode("entry"); setError(""); }}
          >
            入场计划
          </button>
          <button
            className={`add-tab ${mode === "holding" ? "on" : ""}`}
            onClick={() => { setMode("holding"); setError(""); }}
          >
            持仓盯盘（已有仓位）
          </button>
        </div>

        {mode === "entry" ? (
          <p className="cp-intro">
            入场相关字段已从当前信号预填（仅取系统已算出的数值，不预算法新数）；
            <b>五项交易假设</b>需逐项写明，缺一不可。
          </p>
        ) : (
          <p className="cp-intro">
            已在场内，不必再论证入场理由。设好<b>止盈价 / 止损价 / 盯盘信号</b>
            （至少一个），监督员会在每日收盘后与<b>当日 14:45</b> 各判定一次，
            到点才推送。<b>止盈与止损预案</b>仍须写明，否则价位到了仍会临场改主意。
          </p>
        )}

        <div className="cp-row">
          {field(
            "模块",
            <select value={module} onChange={(e) => setModule(e.target.value)}>
              {MODULES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>,
          )}
          {field(
            "方向",
            <select value={direction} onChange={(e) => setDirection(e.target.value)}>
              <option value="long">long</option>
              <option value="short">short</option>
            </select>,
          )}
          {field("有效期 valid_until", (
            <input value={validUntil} onChange={(e) => setValidUntil(e.target.value)}
              placeholder="如 2026-12-31" />
          ))}
        </div>

        {mode === "holding" && (
          <>
            <h3 className="cp-section">退出触发条件（至少一个）</h3>
            <div className="cp-row">
              {field("止盈价", (
                <input value={takeProfitPrice}
                  onChange={(e) => setTakeProfitPrice(e.target.value)}
                  inputMode="decimal" placeholder={direction === "long" ? "涨到此价提醒" : "跌到此价提醒"} />
              ), direction === "long" ? "做多：收盘 >= 此价即提醒" : "做空：收盘 <= 此价即提醒")}
              {field("止损价", (
                <input value={stopPrice} onChange={(e) => setStopPrice(e.target.value)}
                  inputMode="decimal" placeholder={direction === "long" ? "跌破此价提醒" : "涨破此价提醒"} />
              ), direction === "long" ? "做多：收盘 <= 此价即提醒（阻断级）" : "做空：收盘 >= 此价即提醒（阻断级）")}
            </div>
            <label className="cp-field">
              <span className="cp-label">盯盘信号（可多选）</span>
              <div className="cp-signals">
                {WATCH_SIGNALS.map((s) => (
                  <label key={s.id} className="cp-signal">
                    <input
                      type="checkbox"
                      checked={watchSignals.includes(s.id)}
                      onChange={() => toggleSignal(s.id)}
                    />
                    <span>{s.label}</span>
                    <code>{s.id}</code>
                  </label>
                ))}
              </div>
              <span className="cp-hint">
                这些信号当日出现在系统事件里即提醒。只能选系统已注册的规则，不自造信号。
              </span>
            </label>
          </>
        )}

        {mode === "entry" && (
          <>
            <div className="cp-row">
              {field("入场 rule_id", (
                <input value={entryRuleId} onChange={(e) => setEntryRuleId(e.target.value)}
                  placeholder="如 first_ma_pullback" />
              ))}
              {field("入场 lifecycle_id", (
                <input value={lifecycleId} onChange={(e) => setLifecycleId(e.target.value)}
                  placeholder="信号生命周期 id" />
              ))}
            </div>

            <div className="cp-row">
              {field("入场触发说明", (
                <input value={entryTriggerCn} onChange={(e) => setEntryTriggerCn(e.target.value)}
                  placeholder="一句话说明触发" />
              ))}
              {field("盈亏比 R/R", (
                <input value={rewardRisk} onChange={(e) => setRewardRisk(e.target.value)}
                  inputMode="decimal" placeholder="如 3.0" />
              ))}
            </div>

            <div className="cp-row">
              {field("入场参考价", (
                <input value={entryPriceRef} onChange={(e) => setEntryPriceRef(e.target.value)}
                  inputMode="decimal" placeholder="系统未给出则留空" />
              ))}
              {field("失效价", (
                <input value={invalidationPrice} onChange={(e) => setInvalidationPrice(e.target.value)}
                  inputMode="decimal" placeholder="如结构 C 点" />
              ))}
              {field("目标 B 价", (
                <input value={targetBPrice} onChange={(e) => setTargetBPrice(e.target.value)}
                  inputMode="decimal" placeholder="如 B1 阻力" />
              ))}
            </div>
          </>
        )}

        <div className="cp-row reason">
          {field(mode === "entry" ? "建计划理由" : "备注（选填）", (
            <input value={reason} onChange={(e) => setReason(e.target.value)}
              placeholder={mode === "entry" ? "为什么现在建这个计划" : "如：底仓已建于上周"} />
          ))}
        </div>

        <h3 className="cp-section">
          {mode === "entry" ? "五项交易假设（必填）" : "退出预案（必填）"}
        </h3>
        <div className="cp-playbook">
          {(mode === "entry"
            ? PLAYBOOK
            : PLAYBOOK.filter((p) => EXIT_PLAYBOOK_KEYS.includes(p.key as string))
          ).map((p) => (
            <label className="cp-field" key={p.key}>
              <span className="cp-label">{p.label}</span>
              <textarea
                rows={2}
                value={playbook[p.key]}
                onChange={(e) => setPlaybook({ ...playbook, [p.key]: e.target.value })}
                placeholder={p.hint}
              />
              <span className="cp-hint">{p.hint}</span>
            </label>
          ))}
        </div>

        {error && <div className="cp-error">{error}</div>}

        <div className="cp-actions">
          <button
            className="btn"
            onClick={onClose}
            disabled={create.isPending || createHolding.isPending}
          >
            取消
          </button>
          {mode === "entry" ? (
            <button className="btn primary" onClick={submit} disabled={!canSubmit}>
              {create.isPending ? "提交中…" : "建立并确认（armed）"}
            </button>
          ) : (
            <button
              className="btn primary"
              onClick={submitHolding}
              disabled={!canSubmitHolding}
            >
              {createHolding.isPending ? "提交中…" : "开始盯盘（entered）"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
