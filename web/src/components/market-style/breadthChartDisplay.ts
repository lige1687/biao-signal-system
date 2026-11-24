import type { BreadthHorizon, BreadthReadingPoint } from "./breadthReadingTypes";

export type BackgroundKey = "rising" | "falling" | "recovering" | "retreating" | "low" | "high" | "missing";
export type BackgroundMode = "levels" | "phases";
export const BACKGROUND_STYLES: Record<BackgroundKey, { label: string; fill: string; color: string }> = {
  rising: { label: "参与回升", fill: "rgba(13, 148, 136, 0.16)", color: "#0f766e" },
  falling: { label: "参与收缩", fill: "rgba(217, 119, 6, 0.16)", color: "#b45309" },
  recovering: { label: "低位修复", fill: "rgba(13, 148, 136, 0.28)", color: "#0f766e" },
  retreating: { label: "高位回落", fill: "rgba(217, 119, 6, 0.28)", color: "#b45309" },
  low: { label: "历史低位 ≤ P10", fill: "rgba(13, 148, 136, 0.22)", color: "#0f766e" },
  high: { label: "历史高位 ≥ P90", fill: "rgba(217, 119, 6, 0.22)", color: "#b45309" },
  missing: { label: "宽度缺测", fill: "rgba(100, 116, 139, 0.22)", color: "#64748b" },
};
export interface BackgroundRun { start: number; end: number; key: BackgroundKey }

const STATE_KEYS = new Map<string, BackgroundKey>([
  ["expanding", "rising"], ["improving", "rising"],
  ["contracting", "falling"], ["weakening", "falling"],
  ["recovering", "recovering"], ["retreating", "retreating"],
]);

/** Display supplied states on their exact dates; missing data remain visible with color disabled. */
export function backgroundRuns(
  dates: readonly string[], values: readonly (number | null)[],
  readings: ReadonlyMap<string, BreadthReadingPoint>, enabled: boolean,
  mode: BackgroundMode = "phases", horizon: BreadthHorizon = "50",
): BackgroundRun[] {
  const runs: BackgroundRun[] = [];
  dates.forEach((date, index) => {
    if (!date) return;
    const value = values[index];
    const reading = readings.get(date);
    const position = reading?.horizons?.[horizon];
    const key = typeof value !== "number" || !Number.isFinite(value) ? "missing"
      : !enabled ? undefined : mode === "phases" ? STATE_KEYS.get(reading?.state.code ?? "")
      : position?.status === "ready" && (position.position === "low" || position.position === "high") ? position.position : undefined;
    if (!key) return;
    const previous = runs[runs.length - 1];
    if (previous?.key === key && previous.end === index - 1) previous.end = index;
    else runs.push({ start: index, end: index, key });
  });
  return runs;
}

/** Count displayed observations, not elapsed calendar days. */
export function gapText(runs: readonly BackgroundRun[], dates: readonly string[]): string {
  const missing = runs.filter((run) => run.key === "missing");
  if (!missing.length) return "";
  const count = missing.reduce((total, run) => total + run.end - run.start + 1, 0);
  const ranges = missing.map(({ start, end }) => {
    const range = start === end ? dates[start] : `${dates[start]}—${dates[end]}`;
    return `${range}（${end === dates.length - 1 ? "尚未更新" : "缺记录"}）`;
  });
  return `宽度缺测 ${count} 个观察日：${ranges.join("；")}`;
}
