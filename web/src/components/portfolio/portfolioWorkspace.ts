import type { SymbolDetail } from "../../types";

export type ReviewStatus = "action_required" | "waiting" | "incomplete" | "no_trigger";
export interface HoldingPlan {
  plan_id: string; symbol: string; state: string; reason: string;
  stop_plan_cn: string; take_profit_plan_cn: string; linked_at: string | null;
}
export interface WorkspaceHolding {
  holding_id: string; name: string; code: string | null; group_name: string;
  market_value: number; weight_pct: number; return_pct: number | null; holding_as_of: string;
  nav: { value: number; date: string; updated_at: string } | null;
  symbol: string | null; status: ReviewStatus; title_cn: string; reason_cn: string;
  next_step_cn: string; gaps: string[]; original_note?: string | null;
  alerts?: Array<{ code: string; next_step_cn: string; data_as_of: string; actionable_from: string; caveat_cn?: string }>;
  technical: { assessment: SymbolDetail["assessment"]; meta: Pick<SymbolDetail["meta"], "last_bar_date" | "cache_fallback_used" | "is_intraday_forming"> & { calendar_note_cn?: string; data_time?: string | null; provider?: string | null } } | null;
  plan: HoldingPlan | null; plan_candidates: HoldingPlan[];
}
export interface PortfolioWorkspace {
  generated_at: string; review_date: string; as_of: string; total_value: number;
  coverage: Record<"total" | "with_nav" | "with_technical" | "with_plan" | ReviewStatus, number>;
  items: WorkspaceHolding[]; note_cn?: string;
}

async function workspaceRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/portfolio/${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `读取失败（${response.status}）`);
  }
  return response.json();
}
export const workspaceApi = {
  get: () => workspaceRequest<PortfolioWorkspace>("workspace"),
  linkPlan: (holdingId: string, planId: string) => workspaceRequest<unknown>(
    `holdings/${encodeURIComponent(holdingId)}/plan`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plan_id: planId }),
    }),
};

export const REVIEW_LABELS: Record<ReviewStatus, string> = {
  action_required: "按计划处理", waiting: "等待条件确认", incomplete: "资料待补", no_trigger: "本轮无新触发",
};
