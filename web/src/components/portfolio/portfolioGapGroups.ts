import type { WorkspaceHolding } from "./portfolioWorkspace";

/** Group only the literal gaps returned for each holding; no cause is inferred. */
export function groupPortfolioGaps(items: Pick<WorkspaceHolding, "holding_id" | "name" | "code" | "gaps">[]) {
  const groups = new Map<string, typeof items>();
  for (const item of items) {
    for (const gap of new Set(item.gaps.filter(Boolean))) {
      const affected = groups.get(gap) ?? [];
      affected.push(item);
      groups.set(gap, affected);
    }
  }
  return [...groups].map(([gap, affected]) => ({ gap, affected }))
    .sort((a, b) => b.affected.length - a.affected.length || a.gap.localeCompare(b.gap, "zh-CN"));
}
