import { request } from "./client";

export type GoalKind = "directional" | "concrete";
export type GoalStatus = "planned" | "awaiting_approval" | "approved" | "in_progress" | "review" | "done" | "paused" | "dropped";
export type GoalAction = "note" | "request_approval" | "authorize" | "revoke" | "start" | "pause" | "submit_review" | "accept" | "drop" | "reopen";
export type Milestone = { id: string; title: string; done: boolean };
export type GoalLink = { label: string; url: string };
export type GoalContent = {
  title: string; purpose: string; parent_id: string | null; priority: "high" | "medium" | "low";
  owner: string; target_date: string | null; next_action: string; evidence: string;
  milestones: Milestone[]; links: GoalLink[];
};
export type UpgradeGoal = GoalContent & {
  id: string; kind: GoalKind; status: GoalStatus; version: number;
  created_at: string; updated_at: string;
  authorization: { granted: boolean; scope: string; at: string | null };
  progress?: { done: number; total: number };
  history: { at: string; action: string; note: string; scope?: string; from_status?: GoalStatus;
    to_status?: GoalStatus; before?: Record<string, unknown>; after?: Record<string, unknown> }[];
};
export type UpgradeList = { items: UpgradeGoal[]; generated_at: string };
export const upgradesApi = {
  list: () => request<UpgradeList>("/upgrades"),
  create: (data: GoalContent & { kind: GoalKind }) => request<UpgradeGoal>("/upgrades", { method: "POST", body: JSON.stringify(data) }),
  patch: (id: string, version: number, data: Partial<GoalContent>) => request<UpgradeGoal>(`/upgrades/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ version, ...data }) }),
  action: (id: string, version: number, action: GoalAction, note: string, scope = "") => request<UpgradeGoal>(`/upgrades/${encodeURIComponent(id)}/actions`, { method: "POST", body: JSON.stringify({ version, action, note, scope }) }),
};
