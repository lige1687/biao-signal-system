/** Step 3: 从 watch 落计划 (POST /api/watch/{id}/promote).
 *
 * 专用 modal -- 不复用现有 PlansPanel. 入口: WatchSubscriptionsPanel 的 [据此建计划].
 * 五项预案 + reason + valid_until 必填, 委托后端 confirm_plan 校验.
 * 默认 plan_kind=entry, auto_enter=true (用户 2026-08-09 决定: watch 命中已是触发).
 *
 * 字段预填规则 (后端还会做一次默认, 这里只做 UI 体验优化):
 *   module / direction          <- watch
 *   reason                      <- "watch 命中建计划: <text_cn>"
 *   entry_trigger_cn            <- watch.watch_text_cn
 *   invalidation_price          <- watch.level
 *   entry_price_ref             <- watch.triggered_price
 *   5 项 playbook               <- 空 (必须人写, 不能猜)
 *   valid_until                 <- 空 (必填)
 *   plan_kind / ruleset_version <- 不可改 (后端硬编码)
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { MODULE_CN } from "../modules";
import type { PromoteWatchRequest, WatchSubscription } from "../types";

const MODULES = ["A", "B", "C", "D"] as const;

/** 5 项交易假设: 写不出来 = 计划没想清楚, 提交时强制非空. */
const PLAYBOOK: {
  key: keyof Pick<
    PromoteWatchRequest,
    | "thesis_cn"
    | "invalidation_criteria_cn"
    | "drawdown_playbook_cn"
    | "take_profit_plan_cn"
    | "stop_plan_cn"
  >;
  label: string;
  hint: string;
}[] = [
  { key: "thesis_cn", label: "交易假设", hint: "为什么做这一笔" },
  { key: "invalidation_criteria_cn", label: "失效标准", hint: "什么情况说明逻辑错了" },
  { key: "drawdown_playbook_cn", label: "回撤预案", hint: "持仓中正常回撤如何应对" },
  { key: "take_profit_plan_cn", label: "止盈预案", hint: "什么逻辑进场就什么逻辑退出" },
  { key: "stop_plan_cn", label: "止损预案", hint: "结构止损 / 时间止损" },
];

export default function PromotePlanDialog({
  watch,
  onClose,
}: {
  watch: WatchSubscription;
  onClose: () => void;
}) {
  const qc = useQueryClient();

  // 预填 (用户可改)
  const [module, setModule] = useState(watch.module);
  const [direction, setDirection] = useState(watch.direction);
  const [validUntil, setValidUntil] = useState("");
  const [reason, setReason] = useState(
    `watch 命中建计划: ${watch.watch_text_cn}`,
  );
  const [entryTriggerCn, setEntryTriggerCn] = useState(watch.watch_text_cn);
  const [invalidationPrice, setInvalidationPrice] = useState(
    watch.level != null ? String(watch.level) : "",
  );
  const [entryPriceRef, setEntryPriceRef] = useState(
    watch.triggered_price != null ? String(watch.triggered_price) : "",
  );
  const [targetBPrice, setTargetBPrice] = useState("");
  const [rr, setRr] = useState("");
  const [playbook, setPlaybook] = useState<Record<string, string>>({
    thesis_cn: "",
    invalidation_criteria_cn: "",
    drawdown_playbook_cn: "",
    take_profit_plan_cn: "",
    stop_plan_cn: "",
  });
  const [error, setError] = useState<string | null>(null);

  const promote = useMutation({
    mutationFn: (body: PromoteWatchRequest) =>
      api.promoteWatch(watch.watch_id, body),
    onSuccess: () => {
      // 三个 query 一起 invalidate: watch panel + plans list + 红点.
      qc.invalidateQueries({ queryKey: ["watches", "all"] });
      qc.invalidateQueries({ queryKey: ["plans"] });
      qc.invalidateQueries({ queryKey: ["plansSummary"] });
      onClose();
    },
    onError: (e: Error) => {
      // 后端 400/409/404 都走 request<T> 的 body.detail 解析, e.message 即为中文 detail.
      setError(e.message || "提交失败");
    },
  });

  function submit() {
    setError(null);
    // 客户端二次校验: 必填项空着直接挡, 不浪费一次后端调用.
    if (!validUntil.trim()) return setError("valid_until 必填 (YYYY-MM-DD)");
    if (!reason.trim()) return setError("reason 必填");
    const missing = PLAYBOOK.filter((f) => !playbook[f.key].trim()).map(
      (f) => f.label,
    );
    if (missing.length) return setError(`五项预案必填, 缺: ${missing.join(", ")}`);

    const toNumOrNull = (s: string): number | null => {
      const v = parseFloat(s);
      return Number.isFinite(v) ? v : null;
    };
    promote.mutate({
      module,
      direction,
      valid_until: validUntil.trim(),
      reason: reason.trim(),
      entry_trigger_cn: entryTriggerCn.trim() || null,
      entry_price_ref: toNumOrNull(entryPriceRef),
      invalidation_price: toNumOrNull(invalidationPrice),
      target_b_price: toNumOrNull(targetBPrice),
      reward_risk_at_plan: toNumOrNull(rr),
      thesis_cn: playbook.thesis_cn.trim(),
      invalidation_criteria_cn: playbook.invalidation_criteria_cn.trim(),
      drawdown_playbook_cn: playbook.drawdown_playbook_cn.trim(),
      take_profit_plan_cn: playbook.take_profit_plan_cn.trim(),
      stop_plan_cn: playbook.stop_plan_cn.trim(),
      auto_enter: true, // 永远 true: watch 命中已是触发
    });
  }

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-card cp-card">
        <div className="modal-head">
          <h2>据此建计划 — {watch.symbol}</h2>
          <button className="btn small" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="cp-intro muted">
          来源: watch 命中 · {watch.direction === "long" ? "多" : "空"} ·{" "}
          {watch.module} · 14:45 价{" "}
          {watch.triggered_price?.toFixed(2) ?? "?"}
          <br />
          触发原因: {watch.triggered_reason_cn ?? watch.watch_text_cn}
        </div>

        <div className="cp-section">
          <div className="cp-row">
            <label className="cp-field">
              <span className="cp-label">模块 / 方向</span>
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  value={module}
                  onChange={(e) => setModule(e.target.value)}
                  style={{ flex: 1 }}
                >
                  {MODULES.map((m) => (
                    <option key={m} value={m}>
                      {m} · {MODULE_CN[m] ?? m}
                    </option>
                  ))}
                </select>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value)}
                  style={{ flex: 1 }}
                >
                  <option value="long">long · 做多</option>
                  <option value="short">short · 做空</option>
                </select>
              </div>
            </label>
          </div>

          <div className="cp-row">
            <label className="cp-field">
              <span className="cp-label">有效期 (valid_until) *</span>
              <input
                type="text"
                placeholder="YYYY-MM-DD"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
              />
            </label>
            <label className="cp-field">
              <span className="cp-label">制定原因 (reason) *</span>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
          </div>

          <div className="cp-row">
            <label className="cp-field">
              <span className="cp-label">入场触发描述 (entry_trigger_cn)</span>
              <input
                type="text"
                value={entryTriggerCn}
                onChange={(e) => setEntryTriggerCn(e.target.value)}
              />
              <span className="cp-hint">默认照抄 watch 描述, 可改</span>
            </label>
          </div>

          <div className="cp-row">
            <label className="cp-field">
              <span className="cp-label">入场参照价 (entry_price_ref)</span>
              <input
                type="number"
                step="0.01"
                value={entryPriceRef}
                onChange={(e) => setEntryPriceRef(e.target.value)}
              />
              <span className="cp-hint">默认 14:45 命中价</span>
            </label>
            <label className="cp-field">
              <span className="cp-label">止损位 (invalidation_price)</span>
              <input
                type="number"
                step="0.01"
                value={invalidationPrice}
                onChange={(e) => setInvalidationPrice(e.target.value)}
              />
              <span className="cp-hint">默认 watch.level</span>
            </label>
          </div>

          <div className="cp-row">
            <label className="cp-field">
              <span className="cp-label">目标价 (target_b_price)</span>
              <input
                type="number"
                step="0.01"
                value={targetBPrice}
                onChange={(e) => setTargetBPrice(e.target.value)}
              />
              <span className="cp-hint">可空</span>
            </label>
            <label className="cp-field">
              <span className="cp-label">盈亏比 (R/R)</span>
              <input
                type="number"
                step="0.01"
                value={rr}
                onChange={(e) => setRr(e.target.value)}
              />
              <span className="cp-hint">可空</span>
            </label>
          </div>
        </div>

        <div className="cp-section">
          <div className="cp-section-title">五项交易假设 (armed 必填) *</div>
          {PLAYBOOK.map((f) => (
            <label key={f.key} className="cp-field cp-playbook">
              <span className="cp-label">{f.label}</span>
              <span className="cp-hint">{f.hint}</span>
              <textarea
                rows={2}
                value={playbook[f.key]}
                onChange={(e) =>
                  setPlaybook((prev) => ({ ...prev, [f.key]: e.target.value }))
                }
              />
            </label>
          ))}
        </div>

        {error && <div className="cp-error">{error}</div>}

        <div className="cp-actions">
          <button className="btn" onClick={onClose} disabled={promote.isPending}>
            取消
          </button>
          <button
            className="btn primary"
            onClick={submit}
            disabled={promote.isPending}
          >
            {promote.isPending ? "提交中..." : "确认建计划并入场"}
          </button>
        </div>
      </div>
    </div>
  );
}
