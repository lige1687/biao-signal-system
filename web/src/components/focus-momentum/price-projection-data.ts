import type { RatesHistorySeries } from "../../types";
import type { FocusMomentumPoint } from "./data";

export type ProjectionRange = 1 | 3 | 5 | "all";
export interface NegativeSpan { start: string; end: string }
export interface ZeroCrossing {
  date: string;
  price: number;
  focusPercent: number;
  direction: "down" | "up";
}
export interface FocusPriceView {
  dates: string[];
  prices: Array<number | null>;
  focusPercent: Array<number | null>;
  negativeSpans: NegativeSpan[];
  zeroCrossings: ZeroCrossing[];
  priceSourceLast: string | null;
  modelLast: string | null;
  commonEnd: string | null;
  windowStart: string | null;
}

const validDate = (value: unknown): value is string =>
  typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  !Number.isNaN(Date.parse(`${value}T00:00:00Z`));
const validPrice = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value > 0;
const validFocus = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

function yearsBefore(date: string, years: number): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCFullYear(day.getUTCFullYear() - years);
  return day.toISOString().slice(0, 10);
}

/** Align on actual price dates only. A model reading never borrows a neighbouring day. */
export function buildFocusPriceView(
  priceSeries: RatesHistorySeries | undefined,
  modelSeries: FocusMomentumPoint[],
  modelAsOf: string,
  range: ProjectionRange,
): FocusPriceView {
  const empty: FocusPriceView = {
    dates: [], prices: [], focusPercent: [], negativeSpans: [], zeroCrossings: [],
    priceSourceLast: null, modelLast: null, commonEnd: null, windowStart: null,
  };
  const price = new Map<string, number | null>();
  priceSeries?.dates.forEach((date, index) => {
    if (!validDate(date)) return;
    const value = priceSeries.values[index];
    price.set(date, validPrice(value) ? value : null);
  });
  const model = new Map<string, number>();
  modelSeries.forEach((point) => {
    if (validDate(point.date) && validFocus(point.focus)) model.set(point.date, point.focus);
  });
  const priceDates = [...price.keys()].sort();
  const modelDates = [...model.keys()].sort();
  const priceSourceLast = priceDates[priceDates.length - 1] ?? null;
  const modelLast = modelDates[modelDates.length - 1] ?? null;
  let commonEnd: string | null = null;
  for (let index = priceDates.length - 1; index >= 0; index--) {
    const date = priceDates[index];
    if (date <= modelAsOf && validPrice(price.get(date)) && model.has(date)) {
      commonEnd = date;
      break;
    }
  }
  if (!commonEnd) return { ...empty, priceSourceLast, modelLast };

  const commonStart = priceDates.find((date) => date <= commonEnd! && validPrice(price.get(date)) && model.has(date))!;
  const cutoff = range === "all" ? null : yearsBefore(commonEnd, range);
  const alignedDates = [...new Set([...priceDates, ...modelDates])].sort().filter((date) => date >= commonStart && date <= commonEnd);
  const zeroCrossings: ZeroCrossing[] = [];
  let previousSign: -1 | 1 | null = null;
  for (const date of alignedDates) {
    const currentPrice = price.get(date);
    const focus = model.get(date);
    if (!validPrice(currentPrice) || focus === undefined) {
      previousSign = null;
      continue;
    }
    // An observed zero bridges two valid signs; a missing observation breaks the chain.
    const sign = focus > 0 ? 1 : focus < 0 ? -1 : 0;
    if (sign === 0) continue;
    if (previousSign !== null && sign !== previousSign) {
      zeroCrossings.push({ date, price: currentPrice, focusPercent: focus * 100,
        direction: sign < 0 ? "down" : "up" });
    }
    previousSign = sign;
  }
  const dates = alignedDates.filter((date) => !cutoff || date >= cutoff);
  const prices = dates.map((date) => price.get(date) ?? null);
  const focusPercent = dates.map((date, index) => {
    const value = model.get(date);
    return prices[index] !== null && value !== undefined ? value * 100 : null;
  });
  const negativeSpans: NegativeSpan[] = [];
  let start: string | null = null;
  for (let index = 0; index <= dates.length; index++) {
    if (index < dates.length && focusPercent[index] !== null && focusPercent[index]! < 0) {
      start ??= dates[index];
    } else if (start !== null) {
      negativeSpans.push({ start, end: dates[index - 1] });
      start = null;
    }
  }
  return {
    dates, prices, focusPercent, negativeSpans,
    zeroCrossings: zeroCrossings.filter((crossing) => !cutoff || crossing.date >= cutoff),
    priceSourceLast, modelLast, commonEnd, windowStart: dates[0] ?? null,
  };
}
