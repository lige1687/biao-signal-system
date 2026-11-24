export type IndustryHistoryPoint = {
  date: string; correlation: number; dispersion5: number; up20_count: number; mean_return20: number;
};
export type IndustryRanking = { code: string; name: string; return20: number };
export type IndustryStructureSnapshot = {
  schemaVersion: 1; market: "cn"; scope: string; asOf: string;
  source: { name: string; classificationUrl: string; priceName: string };
  definition: { correlation: string; dispersion5: string; dispersionUnit: "百分点"; returnWindow: string };
  history: IndustryHistoryPoint[];
  latest: IndustryHistoryPoint & {
    correlationChange5: number; correlationPastPercentile: number;
    dispersion5Change5: number; dispersion5PastPercentile: number;
    rankings: IndustryRanking[];
  };
};

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const day = (value: unknown): value is string => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)
  && !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const percentile = (value: unknown) => finite(value) && value >= 0 && value <= 100;

/** Display parser: refuse partial/reordered panels rather than present an apparently current curve. */
export function parseIndustryStructure(raw: unknown): IndustryStructureSnapshot {
  if (!record(raw) || raw.schemaVersion !== 1 || raw.market !== "cn" || !day(raw.asOf) || !text(raw.scope)
    || !record(raw.source) || !text(raw.source.name) || !text(raw.source.priceName)
    || raw.source.classificationUrl !== "https://www.szse.cn/disclosure/notice/general/t20070611_499843.html"
    || !record(raw.definition) || !text(raw.definition.correlation) || !text(raw.definition.dispersion5)
    || raw.definition.dispersionUnit !== "百分点" || !text(raw.definition.returnWindow)
    || !Array.isArray(raw.history) || raw.history.length < 21 || !record(raw.latest)) throw new Error("行业观察资料不完整");
  let previous = "";
  for (const point of raw.history) {
    if (!record(point) || !day(point.date) || point.date <= previous || point.date > raw.asOf
      || !finite(point.correlation) || point.correlation < -1 || point.correlation > 1
      || !finite(point.dispersion5) || point.dispersion5 < 0
      || !Number.isInteger(point.up20_count) || (point.up20_count as number) < 0 || (point.up20_count as number) > 10
      || !finite(point.mean_return20)) throw new Error("行业历史序列无效");
    previous = point.date;
  }
  const latest = raw.latest;
  const last = raw.history[raw.history.length - 1] as Record<string, unknown>;
  if (latest.date !== raw.asOf || latest.date !== last.date
    || latest.correlation !== last.correlation || latest.dispersion5 !== last.dispersion5
    || latest.up20_count !== last.up20_count || latest.mean_return20 !== last.mean_return20
    || !finite(latest.correlationChange5) || !finite(latest.dispersion5Change5)
    || !percentile(latest.correlationPastPercentile) || !percentile(latest.dispersion5PastPercentile)
    || !Array.isArray(latest.rankings) || latest.rankings.length !== 10) throw new Error("行业末值不匹配");
  const codes = new Set<string>();
  for (const item of latest.rankings) {
    if (!record(item) || !text(item.code) || !text(item.name) || !finite(item.return20) || codes.has(item.code)) throw new Error("行业排行无效");
    codes.add(item.code);
  }
  return raw as IndustryStructureSnapshot;
}

export function isIndustrySnapshotOld(asOf: string, today: string, maxDays = 7): boolean {
  if (!day(asOf) || !day(today) || asOf > today) return true;
  return (Date.parse(`${today}T00:00:00Z`) - Date.parse(`${asOf}T00:00:00Z`)) / 86_400_000 > maxDays;
}
