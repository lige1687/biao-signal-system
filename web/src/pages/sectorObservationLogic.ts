import type { SectorTrendRow } from "../types";

export type SectorSortValue = number | null | undefined;

/** Sort numeric observations in the requested direction while always keeping missing values last. */
export function compareObservationValues(
  left: SectorSortValue,
  right: SectorSortValue,
  ascending: boolean,
): number {
  const leftMissing = left == null || !Number.isFinite(left);
  const rightMissing = right == null || !Number.isFinite(right);
  if (leftMissing || rightMissing) {
    if (leftMissing && rightMissing) return 0;
    return leftMissing ? 1 : -1;
  }
  const delta = left - right;
  return ascending ? delta : -delta;
}

/** An empty stage with populated checks/basis is unclassified; no usable evidence means insufficient data. */
export function stageMissingLabel(row: Pick<SectorTrendRow, "stage" | "stage_basis">): string {
  if (row.stage) return "";
  const basis = (row.stage_basis ?? []).join("；");
  if (/样本不足|尚不可用|未成形|资料不足/.test(basis)) return "资料不足";
  if (/未落入任一明确阶段/.test(basis)) return "未归入阶段";
  return "阶段资料待核";
}

export function stageMissingReason(row: Pick<SectorTrendRow, "stage_basis" | "checkpoints">): string {
  const basis = (row.stage_basis ?? []).filter(Boolean);
  if (basis.some((item) => /样本不足|尚不可用|未成形|资料不足|未落入任一明确阶段/.test(item))) {
    return basis.join("；");
  }
  const unmet = (row.checkpoints ?? []).filter((item) => !item.met).map((item) => item.label).filter(Boolean);
  return unmet.length ? unmet.join("；") : "后端未提供可确认阶段状态的明确依据";
}

/** Keep cross-sectional ranks comparable only within the existing sector level. */
export function compareSectorRankRows(
  left: Pick<SectorTrendRow, "level" | "rs_pctile" | "rs_pctile_delta_20">,
  right: Pick<SectorTrendRow, "level" | "rs_pctile" | "rs_pctile_delta_20">,
  key: "rs_pctile" | "rs_pctile_delta_20",
  ascending: boolean,
): number {
  if (left.level !== right.level) return left.level - right.level;
  return compareObservationValues(left[key], right[key], ascending);
}
