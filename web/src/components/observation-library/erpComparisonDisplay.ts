import type { ErpBandPoint } from "./erpBands";
import { erpCrossings, type ErpCrossing } from "./erpCrossings";
import { withErpSigma, type ErpSigma } from "./erpSensitivity";

export type ComparedErpEvent = ErpCrossing & { sigma: ErpSigma; id: string };
export const DEFAULT_ERP_SIGMAS: readonly ErpSigma[] = [1.5, 2];

export function hasErpPriceHistory(values: readonly (number | null)[], price: readonly (number | null)[]) {
  return values.filter((value, i) => typeof value === "number" && Number.isFinite(value)
    && typeof price[i] === "number" && Number.isFinite(price[i])).length >= 2;
}

/** Keep distinct thresholds even when a weekly jump crosses both on the same date. */
export function comparedErpEvents(rows: readonly ErpBandPoint[], sigmas: readonly ErpSigma[]): ComparedErpEvent[] {
  return [...new Set(sigmas)].flatMap(sigma => erpCrossings(withErpSigma(rows, sigma))
    .map(event => ({ ...event, sigma, id: `${sigma}:${event.date}:${event.kind}` })))
    .sort((a, b) => a.date.localeCompare(b.date) || a.sigma - b.sigma);
}

/** Price must exist in the supplied aligned week; never move a marker to another week. */
export function erpEventMarkers(events: readonly ComparedErpEvent[], dates: readonly string[], values: readonly (number | null)[]) {
  const positions = new Map(dates.map((date, i) => [date, i]));
  return events.flatMap(event => {
    const i = positions.get(event.date);
    const value = i === undefined ? null : values[i];
    return typeof value === "number" && Number.isFinite(value)
      ? [{ value: [event.date, value] as [string, number], eventId: event.id }] : [];
  });
}

/** Home data supplies the existing ±2σ boundaries; derive inner rails from that same window. */
export function innerErpRails(row: { upper: number | null; lower: number | null }) {
  if (row.upper === null || row.lower === null || !Number.isFinite(row.upper) || !Number.isFinite(row.lower)
    || row.upper < row.lower) return { upper: null, lower: null };
  const middle = (row.upper + row.lower) / 2;
  const width = (row.upper - row.lower) * 0.375;
  return { upper: middle + width, lower: middle - width };
}
