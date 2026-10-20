import {
  MARKLINES,
  SOURCE_NOTES,
  ZONES,
  findZone,
  type MarkLine,
} from "./zones";
import type { LineSeries } from "./TrendChart";

/** 组装单指标趋势抽屉配置（利率/宏观通用）。抽自 FundamentalsPage，纯重构。 */
export function buildDrawer(p: {
  title: string;
  cur: number | null;
  unit: string;
  label: string;
  dates: string[];
  values: (number | null)[];
  key: string;
  periodLabel: string;
  curDisplay?: string;
  footnote?: string;
}): {
  title: string;
  subtitle?: string;
  dates: string[];
  series: LineSeries[];
  unit: string;
  markLines?: MarkLine[];
  zones?: readonly import("./zones").ZoneLevel[];
  footnote?: string;
} {
  const zones = ZONES[p.key] ?? [];
  const zone = findZone(p.cur, zones);
  const curStr =
    p.curDisplay ?? (p.cur == null ? "-" : `${p.cur.toFixed(2)}${p.unit}`);
  return {
    title: p.title,
    subtitle: `当前 ${curStr} · ${zone.label}（近 ${p.dates.length} ${p.periodLabel}）`,
    dates: p.dates,
    series: [{ name: p.label, values: p.values, color: "#2563eb" }],
    unit: p.unit,
    markLines: MARKLINES[p.key] ?? [],
    zones,
    footnote: p.footnote ?? SOURCE_NOTES[p.key],
  };
}
