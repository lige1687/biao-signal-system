import type { ErpBandPoint } from "./erpBands";

export type ErpCrossing = { date: string; kind: "upper" | "lower"; value: number; upper: number; middle: number; lower: number };

/** A crossing needs two consecutive, fully observed weekly rows. The first usable band is not an event. */
export function erpCrossings(rows: readonly ErpBandPoint[]): ErpCrossing[] {
  const result: ErpCrossing[] = [];
  let previous: ErpBandPoint | null = null;
  for (const row of rows) {
    const valid = row.value !== null && row.upper !== null && row.middle !== null && row.lower !== null
      && [row.value, row.upper, row.middle, row.lower].every(Number.isFinite);
    if (!valid) { previous = null; continue; }
    const gapDays = previous ? (Date.parse(`${row.date}T00:00:00Z`) - Date.parse(`${previous.date}T00:00:00Z`)) / 86_400_000 : Infinity;
    if (previous && gapDays > 0 && gapDays <= 10) {
      const kind = previous.value! <= previous.upper! && row.value! > row.upper! ? "upper"
        : previous.value! >= previous.lower! && row.value! < row.lower! ? "lower" : null;
      if (kind) result.push({ date: row.date, kind, value: row.value!, upper: row.upper!, middle: row.middle!, lower: row.lower! });
    }
    previous = row;
  }
  return result;
}
