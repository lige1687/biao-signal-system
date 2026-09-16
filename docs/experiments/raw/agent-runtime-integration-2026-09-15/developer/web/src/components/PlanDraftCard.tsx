import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { stableClientId } from "../utils/backtestTasks";
import type { CreatePlanPayload, PlanArtifact } from "../types";
import ReviewDrawer from "./ReviewDrawer";

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
 * 冻结产物依据（客户端不再自报 source_refs）；同编号换内容/归属 → 409。
 * 计划流程任务 P1/P2（2026-09-13 主控裁决）：
 * - P1：保存用的规则集版本来自服务端权威（/plans/ruleset-version），读取
 *   失败要求重试，不得以空版本提交；稳定编号不含版本（同一请求不因版本
 *   变化变成新业务）。
 * - P2：历史恢复经 `savedPlanId`（服务端 plan_draft 绑定）直接读取**该
 *   plan_id 的实际状态**——刷新/重开历史不再需要重新保存；卡片区分"当时
 *   讨论内容"与"计划当前状态"，并提供「补齐并核对」打开核对抽屉（同一
 *   plan_id 补齐→核对→明确确认）；确认失败仍可编辑重试。 */

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

const PLAN_STATE_CN: Record<string, string> = {
  draft: "草稿（可补齐/核对后确认）",
  armed: "已确认生效（待触发）",
  entered: "已确认生效（持仓监督中）",
  exited: "已退出",
  superseded: "已被新计划替代",
};

export default function PlanDraftCard({
  draft,
  symbol,
  questionId,
  sessionId,
  artifact,
  legacy,
  savedPlanId,
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
  /** P2：历史接口 plan_draft 绑定的 plan_id——该问题此前已保存过计划。
   * 提供时卡片直接读取该计划的当前状态，不以再次 POST 保存作为恢复。 */
  savedPlanId?: string | null;
}) {
  const queryClient = useQueryClient();
  const [savedLocally, setSavedLocally] = useState<string | null>(null);
  // C2（2026-09-13 主控复核）：首次点保存时冻结**完整请求**（含当时采用的
  // 版本）。响应丢失（网络中断/刷新）后结果未知，重试复用同一请求——服务端
  // 按 (session, client_request_id) 幂等返回原 plan_id，不会用新版本覆盖旧
  // 编号（否则 409 DRAFT_REQUEST_CONFLICT，用户取不回可能已落库的草稿）。
  // 服务端明确拒绝（422/409 校验类）才清空快照，允许真正的新业务。
  const [pendingSave, setPendingSave] = useState<CreatePlanPayload | null>(null);
  const pendingSaveRef = useRef<CreatePlanPayload | null>(null);
  const planId = savedPlanId ?? savedLocally;
  const [reviewOpen, setReviewOpen] = useState(false);

  // P2：已保存计划的实际状态（区分"当时讨论内容"与"计划现状"）
  const savedPlan = useQuery({
    queryKey: ["plan", planId],
    queryFn: () => api.getPlan(planId!),
    enabled: !!planId,
    retry: 1,
  });
  const planState: string | null = savedPlan.data?.state ?? null;

  // P1：规则集版本唯一权威来源（服务端）；失败重试，不空版本提交
  const ruleset = useQuery({
    queryKey: ["rulesetVersion"],
    queryFn: api.rulesetVersion,
    staleTime: 60_000,
    retry: 1,
  });
  const rulesetVersion = ruleset.data?.ruleset_version ?? null;

  const missingInvalidation = draft.invalidation_price == null;
  // 03B-R3 S5：模块/方向待补（系统无建议且用户未明确）→ 不可保存，如实提示
  const missingModule = !draft.module || !draft.direction;
  const sources = artifact ? planDraftFromArtifact(artifact)?.sources ?? {} : {};
  // 稳定保存编号：同问题+同内容 → 同编号 → 服务端幂等返回同 plan_id。
  // P1：编号输入**不含规则集版本**——同一请求不因版本变化变成新业务。
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

  const buildPayload = (version: string): CreatePlanPayload => ({
    symbol,
    module: draft.module,
    direction: draft.direction,
    ruleset_version: version,
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

  // 第一步：保存草稿（只 create，不确认）。P1：版本未读到 = 明确报错可重试，
  // 不静默用空版本（空版本确认时必被 RULESET_VERSION_CHANGED 拒绝）。
  const save = useMutation({
    mutationFn: async () => {
      if (planId) return planId;
      const payload = pendingSaveRef.current ?? (() => {
        if (!rulesetVersion) {
          throw new Error("规则集版本尚未读取成功——请稍后重试，不能以空版本创建");
        }
        const frozen = buildPayload(rulesetVersion);
        pendingSaveRef.current = frozen;
        setPendingSave(frozen);
        return frozen;
      })();
      try {
        const plan = await api.createPlan(payload);
        // 明确成功：快照使命完成
        pendingSaveRef.current = null;
        setPendingSave(null);
        setSavedLocally(plan.plan_id);
        return plan.plan_id;
      } catch (err) {
        const code = confirmErrCode(err);
        if (code === "DRAFT_REQUEST_CONFLICT") {
          // 同编号曾被用于不同内容（含版本变化）：停用旧快照，如实引导
          pendingSaveRef.current = null;
          setPendingSave(null);
          throw new Error(
            "检测到同一保存编号曾被用于不同内容（可能是响应丢失后规则版本发生了变化）。"
            + "原草稿仍在库、未丢失；请刷新页面后按当前依据重新发起保存。");
        }
        if (code) {
          // 服务端确定性拒绝（校验/归属类）：请求未落库，可清快照重新发起
          pendingSaveRef.current = null;
          setPendingSave(null);
        }
        throw err;
      }
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
        const code = confirmErrCode(err);
        const raw = err instanceof Error ? err.message : String(err);
        if (code === "ANALYSIS_UNAVAILABLE") {
          throw new ConfirmUnavailableError(planId, raw);
        }
        // C3：版本冲突不能指向原地编辑（普通编辑不改版本，会循环 409）
        const hint = code === "RULESET_VERSION_CHANGED"
          ? "——请按当前依据重新核对并另建新草稿（本计划保留，不会自动更新版本）；可从讨论或「建立执行计划」入口发起。"
          : "——可点「补齐并核对」修改本草稿后重试（不需要新建计划）。";
        throw new ConfirmPlanError(planId, raw + hint);
      }
      return planId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
      queryClient.invalidateQueries({ queryKey: ["plan", planId] });
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
  const savedPlanIdShown = planId ?? (confirm.error instanceof ConfirmPlanError ? confirm.error.planId : null) ??
    (confirm.error instanceof ConfirmUnavailableError ? confirm.error.planId : null);
  const srcLabel = (k: string) => {
    const s = sources[k] || "";
    if (!s) return "";
    if (s.startsWith("pending")) return "（待补）";
    if (s === "suggested_plan") return "（系统建议）";
    if (s === "message") return "（你明确给出）";
    return `（${s}）`;
  };
  const alreadySaved = !!planId;
  const planActive = planState === "armed" || planState === "entered";
  const closeReview = () => {
    setReviewOpen(false);
    if (planId) queryClient.invalidateQueries({ queryKey: ["plan", planId] });
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
      {/* P2：当时讨论内容（上方字段）与这张计划当前状态分开显示 */}
      {alreadySaved && (
        <div style={{ fontSize: 12, marginTop: 4 }}>
          <span className="muted">这张计划当前状态：</span>
          {savedPlan.isLoading && <span>正在读取…</span>}
          {savedPlan.isError && (
            <span className="cp-error">
              绑定 plan_id {planId} 读取失败（可能已删除）——{String(savedPlan.error)}
            </span>
          )}
          {planState && <strong>{PLAN_STATE_CN[planState] ?? planState}</strong>}
          <span className="muted" style={{ fontSize: 10.5 }}>（以服务端为准，历史字段是当时讨论内容）</span>
        </div>
      )}
      {missingModule && (
        <div className="cp-error" style={{ marginTop: 6 }}>
          系统无合法入场候选预填且你未明确模块/方向——请先说明（如「按模块A整理成计划」），暂不能保存。
        </div>
      )}
      {missingInvalidation && (
        <div className="cp-error" style={{ marginTop: 6 }}>
          待补项：失效价缺失——保存为待补草稿可以，但确认会被拒绝（04B 边界）。
        </div>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        {!alreadySaved && (
          <button
            className="btn small primary"
            disabled={save.isPending || save.isSuccess || missingModule
              || (!rulesetVersion && !pendingSave)}
            title={save.isSuccess
              ? `草稿已保存（plan_id: ${planId}）`
              : pendingSave
                ? "上次保存结果未知——点击核对原请求，不会重复创建"
                : !rulesetVersion
                  ? "规则集版本尚未读取成功，不能以空版本创建"
                  : "仅保存草稿，不确认生效"}
            onClick={() => save.mutate()}
          >
            {save.isPending ? "保存中…" : save.isSuccess ? "草稿已保存"
              : pendingSave ? "核对保存结果" : "保存草稿"}
          </button>
        )}
        {!planActive && (
          <button
            className="btn small"
            disabled={!planId || confirm.isPending || confirm.isSuccess}
            title={planId ? "确认后进入监督（走既有确认接口与 04B 拒绝边界）" : "请先保存草稿"}
            onClick={() => confirm.mutate()}
          >
            {confirm.isPending ? "确认中…" : confirm.isSuccess ? "已确认生效" : "确认生效"}
          </button>
        )}
        {/* P2：保存后/历史恢复的草稿 → 同一 plan_id 的补齐并核对入口 */}
        {alreadySaved && planState === "draft" && (
          <button
            className="btn small"
            onClick={() => setReviewOpen(true)}
            title={`打开 ${planId} 的补齐与核对抽屉（编辑同一张计划，不新建）`}
          >
            补齐并核对
          </button>
        )}
      </div>
      {!alreadySaved && !rulesetVersion && (
        <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
          {ruleset.isLoading
            ? "正在读取规则集版本…"
            : "规则集版本读取失败，暂不能保存。"}
          {ruleset.isError && (
            <button type="button" className="btn small" style={{ marginLeft: 6 }} onClick={() => ruleset.refetch()}>
              重新读取
            </button>
          )}
        </div>
      )}
      {save.error && !planId && (
        <div className="cp-error">
          {pendingSave
            ? "暂不能确认是否保存成功（如网络中断）。可再次点「核对保存结果」——系统按原请求核对，不会重复创建。"
            : `保存失败：${save.error instanceof Error ? save.error.message : String(save.error)}（未落库，可重试）`}
        </div>
      )}
      {savedPlanIdShown && (
        <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
          plan_id: {savedPlanIdShown}（草稿在库；{planState === "draft" ? "可点「补齐并核对」继续处理" : "状态见上方"})
        </div>
      )}
      {confirm.error instanceof ConfirmUnavailableError && (
        <div className="cp-error">
          暂时无法核实（草稿已保留，不会丢失）：{confirm.error.message}。可稍后重试确认。
        </div>
      )}
      {confirm.error instanceof ConfirmPlanError && (
        <div className="cp-error">
          草稿已保存但未激活。{confirm.error.message}
        </div>
      )}
      {(confirm.isSuccess || planActive) && (
        <div className="cp-hint">已确认生效，见「监督待办」页。</div>
      )}
      {reviewOpen && planId && (
        <ReviewDrawer planId={planId} onClose={closeReview} />
      )}
    </div>
  );
}
