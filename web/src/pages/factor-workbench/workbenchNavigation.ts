import { defaultSelection, type CurveDocument, type CurveSelection } from "../factor-research/factorCurvesModel";

/** Transfer an object while keeping every research condition it supports. */
export function diagnosticParams(doc: CurveDocument, current: URLSearchParams, target: { datasetId: string; factorId: string; poolId: string }) {
  const next = new URLSearchParams(current);
  next.set("dataset", target.datasetId);
  next.set("curveFactor", target.factorId);
  const dataset = doc.datasets.find(item => item.id === target.datasetId);
  const defaults = defaultSelection(doc, new URLSearchParams({ dataset: target.datasetId }));
  const supported: Partial<Record<keyof CurveSelection, (value: string) => boolean>> = {
    pool: value => Boolean(dataset?.pools.some(item => item.id === value)),
    fee: value => Boolean(dataset?.fees_bps.includes(Number(value))),
    period: value => Boolean(dataset?.periods[value]),
    regime: value => Boolean(dataset?.regimes.some(item => item.id === value && item.available)),
  };
  for (const [key, accepts] of Object.entries(supported)) {
    const value = next.get(key);
    if (!value || !accepts(value)) next.set(key, key === "pool" ? target.poolId : defaults[key as keyof CurveSelection]);
  }
  next.set("wb", "study");
  return next;
}
