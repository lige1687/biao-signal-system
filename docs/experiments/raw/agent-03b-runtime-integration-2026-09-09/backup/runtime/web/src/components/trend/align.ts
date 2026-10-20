/** 时序对齐工具（抽自 FundamentalsPage，纯重构）。 */

/** 把序列按目标日历对齐（交易日历不完全重合的日期填 null）。 */
export function alignTo(
  dates: string[],
  s?: { dates: string[]; values: number[] },
): (number | null)[] {
  if (!s || s.dates.length === 0) return dates.map(() => null);
  const m = new Map(s.dates.map((d, i) => [d, s.values[i]]));
  return dates.map((d) => m.get(d) ?? null);
}

/** 合并多序列的日期并集并升序排序。 */
export function unionDates(...series: { dates: string[] }[]): string[] {
  const set = new Set<string>();
  for (const s of series) for (const d of s.dates) set.add(d);
  return [...set].sort();
}
