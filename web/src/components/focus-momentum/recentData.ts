import type { FocusMomentumObservation, FocusMomentumPoint } from "./data";

const dateValid = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v;
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Display continuation never changes the frozen research sample or its outcome tables. */
export function mergeFocusContinuation(base: FocusMomentumObservation, raw: unknown): FocusMomentumObservation {
  const c = raw as Record<string, unknown> | null;
  if (!c || c.schemaVersion !== 1 || c.definitionId !== base.definitionId || c.historicalAsOf !== base.asOf
    || c.overlapVerified !== true || (c.scope as { sampleSize?: number })?.sampleSize !== 300
    || (c.source as { manifestSha256?: string })?.manifestSha256 !== "5f3bd55994025442b5d7af416a8bd316f347b73ad61dcf134ac6040c9597cca6" || !dateValid(c.asOf) || c.asOf <= base.asOf || !Array.isArray(c.series) || !c.series.length) {
    throw new Error("焦点动量续接的范围或重叠校验不符");
  }
  let previous = base.asOf;
  const series = c.series.map((rawPoint): FocusMomentumPoint => {
    const p = rawPoint as FocusMomentumPoint;
    if (!dateValid(p.date) || p.date <= previous || p.date > (c.asOf as string)
      || ![p.focus, p.poolMomentum, p.breadth, p.concentration, p.top1Contribution].every(finite)
      || !Number.isInteger(p.qualifiedCount) || p.qualifiedCount < 100 || p.qualifiedCount > 300
      || p.focusCount !== Math.ceil(p.qualifiedCount * .05)
      || [p.breadth, p.concentration, p.top1Contribution].some(v => v < 0 || v > 1)) throw new Error("焦点动量续接日期或读数无效");
    previous = p.date;
    return p;
  });
  const latest = c.latest as FocusMomentumObservation["latest"];
  const last = series[series.length - 1];
  if (!latest || !Array.isArray(latest.members) || latest.members.length !== last.focusCount
    || new Set(latest.members).size !== latest.members.length || latest.members.some(m => typeof m !== "string")
    || Object.keys(last).some(key => latest[key as keyof FocusMomentumPoint] !== last[key as keyof FocusMomentumPoint])
    || last.date !== c.asOf || (latest.changeFocus !== null && !finite(latest.changeFocus))) throw new Error("焦点动量末值不符");
  return { ...base, asOf: c.asOf, series: [...base.series, ...series], latest,
    scope: { ...base.scope, label: "A股固定300股研究样本（非沪深300／非全A）" } };
}

