import type { ErpBandPoint } from "./erpBands";
import type { ErpSigma } from "./erpSensitivity";

export type ErpRegimeKind = "upper" | "lower";

export type ErpRegimeSpan = {
  id: string;
  sigma: ErpSigma;
  kind: ErpRegimeKind;
  startDate: string;
  endDate: string;
  visualStartDate: string;
  visualEndDate: string;
  peakDate: string;
  peakValue: number;
  peakZ: number;
  pointsCount: number;
};

export type ErpRegimeEpisode = {
  id: string;
  kind: ErpRegimeKind;
  peakSigma: ErpSigma;
  crossingDate: string;
  startDate: string;
  endDate: string;
  peakDate: string;
  peakValue: number;
  peakZ: number;
  pointsCount: number;
};

export type ErpMarkAreaPair = [
  { xAxis: string; itemStyle: { color: string } },
  { xAxis: string },
];

const REGIME_FILL: Record<ErpRegimeKind, Record<ErpSigma, string>> = {
  upper: {
    1: "rgba(50, 124, 114, 0.06)",
    1.5: "rgba(50, 124, 114, 0.12)",
    2: "rgba(50, 124, 114, 0.24)",
  },
  lower: {
    1: "rgba(152, 103, 55, 0.06)",
    1.5: "rgba(152, 103, 55, 0.13)",
    2: "rgba(152, 103, 55, 0.26)",
  },
};

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function dayGap(a: string, b: string): number {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000);
}

function shiftDays(date: string, delta: number): string {
  const dt = new Date(`${date}T00:00:00Z`);
  dt.setUTCDate(dt.getUTCDate() + delta);
  return dt.toISOString().slice(0, 10);
}

function isBetterPeak(candidateZ: number, currentZ: number, kind: ErpRegimeKind): boolean {
  return kind === "upper" ? candidateZ > currentZ : candidateZ < currentZ;
}

function highestSigmaReached(peakZ: number, kind: ErpRegimeKind, sigmas: readonly ErpSigma[]): ErpSigma {
  const magnitude = kind === "upper" ? peakZ : -peakZ;
  const sorted = [...sigmas].sort((a, b) => b - a);
  for (const sigma of sorted) {
    if (magnitude >= sigma) return sigma;
  }
  return sorted[sorted.length - 1] ?? 1.5;
}

function extractSpansForTier(
  points: readonly ErpBandPoint[],
  sigma: ErpSigma,
  kind: ErpRegimeKind,
): ErpRegimeSpan[] {
  const spans: ErpRegimeSpan[] = [];
  let startIdx = -1;

  const closeSpan = (endIdx: number) => {
    if (startIdx < 0) return;
    let peakIdx = startIdx;
    for (let i = startIdx + 1; i <= endIdx; i++) {
      if (isBetterPeak(points[i].z!, points[peakIdx].z!, kind)) peakIdx = i;
    }
    const candidateNext = endIdx + 1 < points.length && points[endIdx + 1].value !== null ? points[endIdx + 1] : null;
    const nextRow = candidateNext && dayGap(points[endIdx].date, candidateNext.date) <= 14 ? candidateNext : null;
    const candidatePrev = startIdx > 0 ? points[startIdx - 1] : null;
    const prevRow = candidatePrev && dayGap(candidatePrev.date, points[startIdx].date) <= 14 ? candidatePrev : null;
    const startDate = points[startIdx].date;
    const endDate = points[endIdx].date;
    let visualStartDate = startDate;
    let visualEndDate = nextRow ? nextRow.date : endDate;
    if (visualStartDate === visualEndDate) {
      if (prevRow) visualStartDate = prevRow.date;
      else visualEndDate = shiftDays(endDate, 1);
    }
    spans.push({
      id: `${kind}:${sigma}:${startDate}:${endDate}`,
      sigma,
      kind,
      startDate,
      endDate,
      visualStartDate,
      visualEndDate,
      peakDate: points[peakIdx].date,
      peakValue: points[peakIdx].value!,
      peakZ: points[peakIdx].z!,
      pointsCount: endIdx - startIdx + 1,
    });
    startIdx = -1;
  };

  for (let i = 0; i < points.length; i++) {
    const row = points[i];
    const active = finiteNumber(row.value)
      && finiteNumber(row.z)
      && (kind === "upper" ? row.z >= sigma : row.z <= -sigma);
    if (active) {
      if (startIdx < 0) startIdx = i;
    } else {
      closeSpan(i - 1);
    }
  }
  closeSpan(points.length - 1);
  return spans;
}

/** Extract contiguous upper (cheap) and lower (expensive) regime spans across active sigmas. */
export function extractErpRegimeSpans(
  points: readonly ErpBandPoint[],
  sigmas: readonly ErpSigma[],
): ErpRegimeSpan[] {
  const ordered = [...new Set(sigmas)].sort((a, b) => a - b) as ErpSigma[];
  const out: ErpRegimeSpan[] = [];
  for (const sigma of ordered) {
    out.push(...extractSpansForTier(points, sigma, "upper"));
    out.push(...extractSpansForTier(points, sigma, "lower"));
  }
  return out;
}

/** Build ECharts markArea pairs clipped to [minDate, maxDate] so partial edge intervals render cleanly. */
export function buildErpRegimeMarkAreas(
  spans: readonly ErpRegimeSpan[],
  minDate: string | undefined,
  maxDate: string | undefined,
): ErpMarkAreaPair[] {
  if (!minDate || !maxDate || minDate > maxDate) return [];
  const pairs: ErpMarkAreaPair[] = [];
  for (const span of spans) {
    if (span.visualEndDate < minDate || span.visualStartDate > maxDate) continue;
    const start = span.visualStartDate < minDate ? minDate : span.visualStartDate;
    const end = span.visualEndDate > maxDate ? maxDate : span.visualEndDate;
    if (start >= end) continue;
    pairs.push([
      { xAxis: start, itemStyle: { color: REGIME_FILL[span.kind][span.sigma] } },
      { xAxis: end },
    ]);
  }
  return pairs;
}

/** Merge nearby same-direction outer spans into human-readable episodes for navigation dropdowns. */
export function buildErpRegimeEpisodes(
  points: readonly ErpBandPoint[],
  sigmas: readonly ErpSigma[],
  isWeekly = false,
): ErpRegimeEpisode[] {
  if (!sigmas.length) return [];
  const ordered = [...new Set(sigmas)].sort((a, b) => a - b) as ErpSigma[];
  const outerSigma = ordered[0];
  const maxGapDays = isWeekly ? 14 : 5;

  const raw = [
    ...extractSpansForTier(points, outerSigma, "upper"),
    ...extractSpansForTier(points, outerSigma, "lower"),
  ].sort((a, b) => a.startDate.localeCompare(b.startDate));

  const merged: { kind: ErpRegimeKind; spans: ErpRegimeSpan[] }[] = [];
  for (const span of raw) {
    const prev = merged.length > 0 ? merged[merged.length - 1] : null;
    if (prev && prev.kind === span.kind && dayGap(prev.spans[prev.spans.length - 1].endDate, span.startDate) <= maxGapDays) {
      prev.spans.push(span);
    } else {
      merged.push({ kind: span.kind, spans: [span] });
    }
  }

  return merged.map(({ kind, spans }) => {
    const startDate = spans[0].startDate;
    const endDate = spans[spans.length - 1].endDate;
    let peakSpan = spans[0];
    let totalCount = 0;
    for (const span of spans) {
      totalCount += span.pointsCount;
      if (isBetterPeak(span.peakZ, peakSpan.peakZ, kind)) peakSpan = span;
    }
    const peakSigma = highestSigmaReached(peakSpan.peakZ, kind, ordered);
    let crossingDate = peakSpan.peakDate;
    for (const row of points) {
      if (row.date < startDate) continue;
      if (row.date > endDate) break;
      if (finiteNumber(row.z) && (kind === "upper" ? row.z >= peakSigma : row.z <= -peakSigma)) {
        crossingDate = row.date;
        break;
      }
    }
    return {
      id: `${kind}:${startDate}:${endDate}`,
      kind,
      peakSigma,
      crossingDate,
      startDate,
      endDate,
      peakDate: peakSpan.peakDate,
      peakValue: peakSpan.peakValue,
      peakZ: peakSpan.peakZ,
      pointsCount: totalCount,
    };
  });
}

/** Drop null/NaN points on time axes so missing bond-market holidays do not break chart lines. */
export function denseTimePoints(
  dates: readonly string[],
  values: readonly (number | null | undefined)[],
): [string, number][] {
  const out: [string, number][] = [];
  for (let i = 0; i < dates.length; i++) {
    const v = values[i];
    if (finiteNumber(v)) out.push([dates[i], v]);
  }
  return out;
}

/** Format axisPointer raw time values strictly as YYYY-MM-DD (no 00:00:00 suffix). */
export function formatAxisPointerDate(raw: unknown): string {
  if (typeof raw === "number" && Number.isFinite(raw)) {
    return new Date(raw).toISOString().slice(0, 10);
  }
  if (typeof raw === "string") {
    return raw.slice(0, 10);
  }
  return "";
}
