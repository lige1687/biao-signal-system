import { linkedExperiments, type Experiment, type FactorItem } from "./model";

export type FactorView = "overview" | "catalog" | "experiments" | "legacy";

export function factorView(params: URLSearchParams): FactorView {
  if (params.get("factor")) return "catalog";
  if (params.get("experiment") || params.get("project")) return "experiments";
  const tab = params.get("tab");
  if (tab === "overview" || tab === "catalog" || tab === "experiments" || tab === "legacy") return tab;
  return ["q", "asset", "category", "stage", "result", "page", "sort", "view"]
    .some(key => Boolean(params.get(key))) ? "catalog" : "overview";
}

export function catalogAction(item: FactorItem, experiments: Experiment[]): string {
  if (linkedExperiments(item, experiments).some(experiment => experiment.run_status === "completed")) return "查看证据";
  return item.research.stage === "in_progress" ? "查看进展" : "查看定义";
}
