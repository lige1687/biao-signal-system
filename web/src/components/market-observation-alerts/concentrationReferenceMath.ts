import type { MicroPoint } from "./microstructureData";

interface MonthReference {
  startMonth: string;
  endMonth: string;
  sampleCount: number;
  rank: number;
  p80: number;
  p90: number;
  p95: number;
}

function validDay(date: string): boolean {
  const timestamp = Date.parse(date);
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(timestamp)
    && new Date(timestamp).toISOString().slice(0, 10) === date;
}

function monthIndex(date: string): number {
  return Number(date.slice(0, 4)) * 12 + Number(date.slice(5, 7)) - 1;
}

function formatMonth(index: number): string {
  const year = String(Math.floor(index / 12)).padStart(4, "0");
  const month = String(index % 12 + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function quantile(sorted: readonly number[], probability: number): number {
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position);
  return sorted[lower] + (position - lower) * (sorted[Math.ceil(position)] - sorted[lower]);
}

export function priorMonthReference(points: readonly MicroPoint[], months: 120 | 60): MonthReference | null {
  const latest = points[points.length - 1];
  if (!latest || latest.value === null || !Number.isFinite(latest.value) || !validDay(latest.date)) return null;
  const currentMonth = monthIndex(latest.date);
  const startMonth = currentMonth - months;
  const sample: number[] = [];
  let previous = -Infinity;

  for (const point of points) {
    if (!validDay(point.date)) return null;
    const month = monthIndex(point.date);
    if (month <= previous) return null;
    previous = month;
    if (month >= startMonth && month < currentMonth && point.value !== null && Number.isFinite(point.value)) {
      sample.push(point.value);
    }
  }
  if (monthIndex(points[0].date) > startMonth || sample.length < Math.ceil(months * 0.9)) return null;

  const currentValue = latest.value;
  const rank = 100 * sample.filter((value) => value < currentValue).length / sample.length;
  sample.sort((a, b) => a - b);
  return {
    startMonth: formatMonth(startMonth), endMonth: formatMonth(currentMonth - 1),
    sampleCount: sample.length, rank,
    p80: quantile(sample, 0.8), p90: quantile(sample, 0.9), p95: quantile(sample, 0.95),
  };
}

/** Packet rows are the expected session axis. Missing observations must occupy their null row. */
export function amountMA20(points: readonly MicroPoint[]): (number | null)[] {
  const window: number[] = [];
  let previous = "";
  return points.map(({ date, value }) => {
    if (!validDay(date) || date <= previous) {
      window.length = 0;
      return null;
    }
    previous = date;
    if (value === null || !Number.isFinite(value)) {
      window.length = 0;
      return null;
    }
    window.push(value);
    if (window.length > 20) window.shift();
    return window.length === 20 ? window.reduce((sum, amount) => sum + amount, 0) / 20 : null;
  });
}
