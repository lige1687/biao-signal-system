import type { MetricReading } from "./metricData";
import { ERP_BAND_METHOD } from "./erpBands";

export const ERP_REFERENCE_URL = "/api/fundamentals/erp-cn-reference";
export const ERP_REFERENCE_QUERY_KEY = ["erpCn3YearReference", "live-v1"] as const;
export type ErpReference = {
  schemaVersion: 1; id: "erp-cn-3y-reference"; historicalOnly: boolean;
  frequency: "daily" | "weekly" | "monthly"; asOf: string;
  sourceName: string; sourceUrl: string; sourceSha256: string;
  note: string;
  points: { date: string; value: number | null; close: number | null }[];
};

export function parseErpReference(raw: unknown): ErpReference {
  if (!raw || typeof raw !== "object") throw new Error("股债参照资料缺失");
  const data = raw as ErpReference;
  const valid = (n: unknown) => n === null || (typeof n === "number" && Number.isFinite(n));
  if (data.schemaVersion !== 1 || data.id !== "erp-cn-3y-reference" || typeof data.historicalOnly !== "boolean"
    || !["daily", "weekly", "monthly"].includes(data.frequency) || !Array.isArray(data.points) || data.points.length < 37
    || data.points.some((p, i) => !/^\d{4}-\d{2}-\d{2}$/.test(p.date) || !Number.isFinite(Date.parse(p.date))
      || new Date(`${p.date}T00:00:00Z`).toISOString().slice(0, 10) !== p.date
      || (i > 0 && p.date <= data.points[i - 1].date) || !valid(p.value) || !valid(p.close))
    || data.asOf !== data.points[data.points.length - 1]?.date || !/^[a-f0-9]{64}$/.test(data.sourceSha256)
    || typeof data.sourceName !== "string" || typeof data.sourceUrl !== "string" || typeof data.note !== "string") {
    throw new Error("股债参照资料口径、日期或来源不完整");
  }
  const intervals = data.points.slice(1).map((p, i) => (Date.parse(p.date) - Date.parse(data.points[i].date)) / 86_400_000).sort((a, b) => a - b);
  if (data.frequency === "daily" && intervals[Math.floor(intervals.length / 2)] > 4) throw new Error("月末资料不能标为日频股债轨道");
  return data;
}

export function fromErpReference(data: ErpReference): MetricReading {
  const last = data.points[data.points.length - 1];
  const previous = data.points[data.points.length - 2];
  return {
    value: last.value, unit: "百分点", date: last.date, dateLabel: data.historicalOnly ? "历史资料截至" : "资料截至",
    change: last.value !== null && previous.value !== null ? last.value - previous.value : null,
    changeUnit: "百分点", comparisonPeriod: "前一观测",
    sourceName: data.sourceName, sourceUrl: data.sourceUrl,
    sourceVersion: data.historicalOnly ? "erp-cn-3y-reference/1 · 2026-11-01" : "erp-cn-live/1",
    status: data.historicalOnly ? `${data.frequency === "daily" ? "日频" : data.frequency === "weekly" ? "周频" : "月频"}历史参照；未自动更新。` : "自动跟随已公开交易日更新，轨道按周观察。",
    note: `100÷沪深300 PE_TTM − 中国10年国债收益率，单位百分点。${ERP_BAND_METHOD.definition}${ERP_BAND_METHOD.difference} ${data.note}`,
    points: data.points,
  };
}
