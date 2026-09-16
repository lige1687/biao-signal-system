import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { stableClientId } from "../utils/backtestTasks";
import type { CreatePlanPayload, PlanArtifact } from "../types";

type ConfirmErrBody = { detail?: { code?: string; message?: string } };

export function confirmErrCode(e: unknown): string | null {
  const body = (e as Error & { body?: ConfirmErrBody })?.body;
  return body?.detail?.code ?? null;
}

export interface PlanDraft {
  module: string;
  direction: string;
  entry_rule_id?: string | null;
  entry_trigger_cn?: string;
  invalidation_price?: number | null;
  valid_until?: string;
  thesis_cn?: string;
  invalidation_criteria_cn?: string;
  drawdown_playbook_cn?: string;
  take_profit_plan_cn?: string;
  stop_plan_cn?: string;
  target_b_price?: number | null;
}

/** 从 assistant 回复中解析 ```plan-draft {json}``` 代码块。
 * 03B-R3 S5：文本解析只作**旧格式兼容**——新回答一律用服务端计划产物
 * （turn.planArtifact）直渲染；旧记录来源不可考须标明。 */
export function parsePlanDraft(text: string): PlanDraft | null {
  const m = /```plan-draft\s*([\s\S]*?)```/.exec(text);
  if (!m) return null;
  try {
    return JSON.parse(m[1]) as PlanDraft;
  } catch {
    return null;
  }
}

const _FIELD_KEYS: Array<[keyof PlanDraft, string]> = [
  ["module", "module"],
  ["direction", "direction"],
  ["entry_rule_id", "entry_rule_id"],
  ["entry_trigger_cn", "entry_trigger_cn"],
  ["invalidation_price", "invalidation_price"],
  ["thesis_cn", "thesis_cn"],
  ["invalidation_criteria_cn", "invalidation_criteria_cn"],
  ["drawdown_playbook_cn", "drawdown_playbook_cn"],
  ["take_profit_plan_cn", "take_profit_plan_cn"],
  ["stop_plan_cn", "stop_plan_cn"],
  ["target_b_price", "target_b_price"],
];

/** 03B-R3 S5：服务端计划产物 → 计划卡字段。value 为空/待补 → null
 * （保存为待补草稿可以，确认由 04B 拒绝）。 */
export function planDraftFromArtifact(
  artifact: PlanArtifact,
): { draft: PlanDraft; sources: Record<string, string> } | null {
  if (!artifact?.fields) return null;
  const draft: Record<string, unknown> = {};
  const sources: Record<string, string> = {};
  const f = artifact.fields as Record<
    string,
    { value?: unknown; source?: string; note_cn?: string }
  >;
  for (const [key, fieldName] of _FIELD_KEYS) {
    const spec = f[fieldName];
    const v = spec?.value;
    (draft as Record<string, unknown>)[key] =
      v === null || v === undefined || v === "" ? null : v;
    sources[fieldName] = spec?.source || "";
  }
  return { draft: draft as unknown as PlanDraft, sources };
}

/** R7（03B-R1，2026-09-08）：「保存草稿」与「确认生效」分离——
 * 保存只调 createPlan（draft 待补合法）；用户另行明确确认才调现有确认
 * 接口（04B 拒绝逻辑生效：缺失效价 422 / 分析缺席 503 / 过期·版本 409）。
 * 确认失败时草稿保留（plan_id 可见），不重复建草稿。
 * 03B-R3 S5/S6：保存携带原问题/会话与稳定编号；服务端核对原问题归属并
 * 冻结产物依据（客户端不再自报 source_refs）；同编号换内容/归属 → 409。 */

export class ConfirmPlanError extends Error {
  readonly planId: string;
  constructor(planId: string, message: string) {
    super(message);
    this.name = "ConfirmPlanError";
    this.planId = planId;
  }
}

export class ConfirmUnavailableError extends Error {
  readonly planId: string;
  constructor(planId: string, message: string) {
    super(message);
    this.name = "ConfirmUnavailableError";
    this.planId = planId;
  }
}

export default function PlanDraftCard({
  draft,
  symbol,
  questionId,
  sessionId,
  artifact,
  legacy,
}: {
  draft: PlanDraft;
  /** 卡片归属标的：产生该草稿的那一轮对话的对象（不是当前页面选中） */
  symbol: string;
  /** 产生该草稿的原问题 ID（服务端绑定 + 稳定编号来源） */
  questionId?: number | null;
  sessionId?: string | null;
  /** 03B-R3 S5：服务端计划产物（存在时显示字段来源，保存携带产物身份） */
  artifact?: PlanArtifact | null;
  /** 旧格式（文本解析、来源不可考）标记 */
  legacy?: boolean;
}) {
  const queryClient = useQueryClient();
  const [planId, setPlanId] = useState<string | null>(null);
  const missingInvalidation = draft.invalidation_price == null;
  // 03B-R3 S5：模块/方向待补（系统无建议且用户未明确）→ 不可保存，如实提示
  const missingModule = !draft.module || !draft.direction;
  const sources = artifact ? planDraftFromArtifact(artifact)?.sources ?? {} : {};
  // 稳定保存编号：同问题+同内容 → 同编号 → 服务端幂等返回同 plan_id
  const clientRequestId = stableClientId([
    "plan-draft",
    questionId ?? "no-question",
    symbol,
    draft.module,
    draft.direction,
    draft.invalidation_price ?? "none",
    draft.valid_until ?? "",
    draft.thesis_cn ?? "",
    artifact?.artifact_id ?? "",
  ]);

  const buildPayload = (rulesetVersion: string): CreatePlanPayload => ({
    symbol,
    module: draft.module,
    direction: draft.direction,
    ruleset_version: rulesetVersion,
    reason: "对话式建计划（agent 引导）",
    entry_rule_id: draft.entry_rule_id ?? null,
    entry_trigger_cn: draft.entry_trigger_cn ?? "",
    entry_price_ref: null,
    invalidation_price: draft.invalidation_price ?? null,
    valid_until: draft.valid_until ?? "",
    thesis_cn: draft.thesis_cn ?? "",
    invalidation_criteria_cn: draft.invalidation_criteria_cn ?? "",
    drawdown_playbook_cn: draft.drawdown_playbook_cn ?? "",
    take_profit_plan_cn: draft.take_profit_plan_cn ?? "",
    stop_plan_cn: draft.stop_plan_cn ?? "",
    target_b_price: draft.target_b_price ?? null,
    client_request_id: clientRequestId,
    source_session_id: sessionId ?? null,
    source_question_id: questionId ?? null,
  });

  // 第一步：保存草稿（只 create，不确认）
  const save = useMutation({
    mutationFn: async () => {
      if (planId) return planId;
      let rulesetVersion = "";
      try {
        rulesetVersion = (await api.buyPointReview(symbol)).ruleset_version || "";
      } catch {
        rulesetVersion = "";
      }
      const plan = await api.createPlan(buildPayload(rulesetVersion));
      setPlanId(plan.plan_id);
      return plan.plan_id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
    },
  });

  // 第二步：确认生效（走现有确认接口；04B 拒绝逻辑生效）
  const confirm = useMutation({
    mutationFn: async () => {
      if (!planId) throw new Error("草稿尚未保存");
      try {
        await api.confirmPlan(planId);
      } catch (err) {
        if (confirmErrCode(err) === "ANALYSIS_UNAVAILABLE") {
          throw new ConfirmUnavailableError(
            planId, err instanceof Error ? err.message : String(err));
        }
        throw new ConfirmPlanError(
          planId, err instanceof Error ? err.message : String(err));
      }
      return planId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
    },
  });

  const rows: Array<[string, string]> = [
    ["模块/方向", `${draft.module} · ${draft.direction}`],
    ["入场理由", draft.entry_rule_id ?? "-"],
    ["失效价", draft.invalidation_price != null ? String(draft.invalidation_price) : "未给出（待补草稿）"],
    ["有效期至", draft.valid_until ?? "-"],
    ["入场条件", draft.entry_trigger_cn ?? "-"],
    ["认错退出条件", draft.invalidation_criteria_cn ?? "-"],
    ["回撤预案", draft.drawdown_playbook_cn ?? "-"],
    ["止盈/退出方法", draft.take_profit_plan_cn ?? "-"],
    ["止损预案", draft.stop_plan_cn ?? "-"],
    ["目标价(B)", draft.target_b_price != null ? String(draft.target_b_price) : "未给出（待补）"],
  ];
  const savedPlanId = planId ?? (confirm.error instanceof ConfirmPlanError ? confirm.error.planId : null) ??
    (confirm.error instanceof ConfirmUnavailableError ? confirm.error.planId : null);
  const srcLabel = (k: string) => {
    const s = sources[k] || "";
    if (!s) return "";
    if (s.startsWith("pending")) return "（待补）";
    if (s === "suggested_plan") return "（系统建议）";
    if (s === "message") return "（你明确给出）";
    return `（${s}）`;
  };

  return (
    <div className="plan-draft-card">
      <div className="cp-label">
        计划草稿 · {symbol}（保存后仍需确认）
        {questionId ? ` · 原问题 #${questionId}` : ""}
        {artifact ? " · 服务端产物" : legacy ? " · 旧格式（来源不可考）" : ""}
      </div>
      {rows.map(([k, v]) => (
        <div key={k} style={{ fontSize: 12 }}>
          <span className="muted">{k}：</span>
          {v}
          {artifact && <span className="muted" style={{ fontSize: 10.5 }}>{srcLabel(k)}</span>}
        </div>
      ))}
      {missingModule && (
        <div className="cp-error" style={{ marginTop: 6 }}>
          系统无建议且你未明确模块/方向——请先说明（如「按模块A整理成计划」），暂不能保存。
        </div>
      )}
      {missingInvalidation && (
        <div className="cp-error" style={{ marginTop: 6 }}>
          待补项：失效价缺失——保存为待补草稿可以，但确认会被拒绝（04B 边界）。
        </div>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <button
          className="btn small primary"
          disabled={save.isPending || save.isSuccess || missingModule}
          title={save.isSuccess ? `草稿已保存（plan_id: ${planId}）` : "仅保存草稿，不确认生效"}
          onClick={() => save.mutate()}
        >
          {save.isPending ? "保存中…" : save.isSuccess ? "草稿已保存" : "保存草稿"}
        </button>
        <button
          className="btn small"
          disabled={!planId || confirm.isPending || confirm.isSuccess}
          title={planId ? "确认后进入监督（走既有确认接口与 04B 拒绝边界）" : "请先保存草稿"}
          onClick={() => confirm.mutate()}
        >
          {confirm.isPending ? "确认中…" : confirm.isSuccess ? "已确认生效" : "确认生效"}
        </button>
      </div>
      {save.error && !planId && (
        <div className="cp-error">
          保存失败：{save.error instanceof Error ? save.error.message : String(save.error)}
          （未落库，可重试）
        </div>
      )}
      {savedPlanId && (
        <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
          plan_id: {savedPlanId}（草稿在库；到「监督待办」页或标的详情页处理）
        </div>
      )}
      {confirm.error instanceof ConfirmUnavailableError && (
        <div className="cp-error">
          暂时无法核实（草稿已保留，不会丢失）：{confirm.error.message}。可稍后重试确认。
        </div>
      )}
      {confirm.error instanceof ConfirmPlanError && (
        <div className="cp-error">
          草稿已保存但未激活：到监督待办页处理，或从标的详情页的表单继续。
          <span className="muted">原因：{confirm.error.message}</span>
        </div>
      )}
      {confirm.isSuccess && (
        <div className="cp-hint">已确认生效，见「监督待办」页。</div>
      )}
    </div>
  );
}
