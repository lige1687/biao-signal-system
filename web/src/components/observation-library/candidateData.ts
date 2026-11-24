import type { MetricReading } from "./metricData";

export const CANDIDATE_URL = "/research/observation-candidates/history.v1.json";
export const CANDIDATE_QUERY_KEY = ["observationCandidatesHistoryV1"] as const;
export const HISTORICAL_CANDIDATE_IDS = ["downside-price-impact", "salience-str"] as const;
export type HistoricalCandidateId = typeof HISTORICAL_CANDIDATE_IDS[number];
type Point = { date: string; value: number | null; n: number; universeN: number };
type Series = { definitionId: string; label: string; unit: string; meaning: string;
  reading: string; definition: string; limitations: string[]; points: Point[] };
export interface CandidateHistory {
  schemaVersion: 1; historicalOnly: true; current: null; asOf: string; sourceThrough: string;
  sourceSha256: string; sourceName: string; sourceUrl: string; scopeLabel: string;
  limitations: string[]; series: Record<HistoricalCandidateId, Series>;
}
const day = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(v)) && new Date(`${v}T00:00:00Z`).toISOString().slice(0, 10) === v;
const count = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v) && v >= 0;
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const text = (v: unknown): v is string => typeof v === "string" && v.trim().length > 0;
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);

/** Reject undated, unit-mismatched or silently truncated observation packages. */
export function parseCandidateHistory(raw: unknown): CandidateHistory {
  if (!raw || typeof raw !== "object") throw new Error("观察资料结构无效");
  const d = raw as CandidateHistory;
  if (d.schemaVersion !== 1 || d.historicalOnly !== true || d.current !== null
    || !day(d.asOf) || !day(d.sourceThrough) || d.asOf > d.sourceThrough
    || !/^[a-f0-9]{64}$/.test(d.sourceSha256) || ![d.sourceName, d.sourceUrl, d.scopeLabel].every(text)
    || !strings(d.limitations) || !d.series) throw new Error("观察资料版本、日期或来源无效");
  for (const id of HISTORICAL_CANDIDATE_IDS) {
    const s = d.series[id];
    if (!s || ![s.definitionId, s.label, s.meaning, s.reading, s.definition].every(text)
      || s.unit !== (id === "downside-price-impact" ? "百分点/亿元" : "百分点")
      || !strings(s.limitations) || !Array.isArray(s.points) || s.points.length < 2) throw new Error("观察指标定义或单位无效");
    s.points.forEach((p, i) => {
      if (!p || !day(p.date) || (i > 0 && p.date <= s.points[i - 1].date)
        || !count(p.n) || !count(p.universeN) || p.n > p.universeN
        || (p.value !== null && (!finite(p.value) || p.n === 0 || (id === "downside-price-impact" && p.value < 0)))) {
        throw new Error("观察序列日期、数值或样本数无效");
      }
    });
    if (s.points[s.points.length - 1].date !== d.asOf) throw new Error("观察序列末日与资料日期不一致");
  }
  const a = d.series[HISTORICAL_CANDIDATE_IDS[0]].points;
  const b = d.series[HISTORICAL_CANDIDATE_IDS[1]].points;
  if (a.length !== b.length || a.some((p, i) => p.date !== b[i].date)) throw new Error("观察序列交易日期不一致");
  return d;
}

export function fromCandidateHistory(d: CandidateHistory, id: HistoricalCandidateId): MetricReading {
  const s = d.series[id], last = s.points[s.points.length - 1], prev = s.points[s.points.length - 2];
  return {
    value: last.value, unit: s.unit, date: last.date, dateLabel: "历史资料截至",
    change: last.value !== null && prev.value !== null ? last.value - prev.value : null,
    comparisonPeriod: "前一交易日", sourceName: d.sourceName, sourceUrl: d.sourceUrl,
    sourceVersion: s.definitionId, guide: s.reading,
    status: `${last.value === null ? "末日读数缺失；" : ""}有效${last.n.toLocaleString()} / 候选${last.universeN.toLocaleString()}只；已存历史，未自动更新。`,
    note: [s.definition, d.scopeLabel, ...d.limitations, ...s.limitations].join("；"),
    points: s.points.map(({ date, value }) => ({ date, value })),
  };
}

export const SMALLCAP_URL = "/research/observation-candidates/smallcap-snapshot.v1.json";
export const SMALLCAP_QUERY_KEY = ["observationSmallcapSnapshotV1"] as const;
export interface SmallcapSnapshot {
  schemaVersion: 1; historicalOnly: true; current: null; asOf: string; sourceSha256: string;
  definitionId: "observation.cn_smallcap_turnover_snapshot.v1";
  requestedN: number; n: number; k: number; smallMedian: number; allMedian: number;
  ratio: number | null; scopeLabel: string; limitations: string[];
}
export function parseSmallcapSnapshot(raw: unknown): SmallcapSnapshot {
  if (!raw || typeof raw !== "object") throw new Error("换手快照结构无效");
  const d = raw as SmallcapSnapshot;
  if (d.schemaVersion !== 1 || d.historicalOnly !== true || d.current !== null
    || d.definitionId !== "observation.cn_smallcap_turnover_snapshot.v1" || !day(d.asOf)
    || !/^[a-f0-9]{64}$/.test(d.sourceSha256) || !count(d.requestedN) || !count(d.n) || !count(d.k)
    || d.n < 5 || d.n > d.requestedN || d.k !== Math.ceil(d.n * .2)
    || !finite(d.smallMedian) || d.smallMedian < 0 || !finite(d.allMedian) || d.allMedian < 0
    || (d.allMedian === 0 ? d.ratio !== null : !finite(d.ratio) || Math.abs(d.ratio - d.smallMedian / d.allMedian) > 1e-9)
    || !text(d.scopeLabel) || !strings(d.limitations)) throw new Error("换手快照日期、口径或数值无效");
  return d;
}
export function fromSmallcapSnapshot(d: SmallcapSnapshot): MetricReading {
  return { value: d.ratio, unit: "倍", date: d.asOf, dateLabel: "同日快照",
    change: null, sourceName: "腾讯公开行情 · 本地样本统计", sourceUrl: "https://gu.qq.com/",
    sourceVersion: d.definitionId, guide: "高于1表示小市值组的典型换手率高于同池整体；只看交易活跃程度，不代表资金净流入或买卖机会。",
    status: `同日有效${d.n.toLocaleString()} / 请求${d.requestedN.toLocaleString()}只；小盘组${d.k.toLocaleString()}只。含2条早间无成交报价，未自动更新。`,
    note: `按总市值从小到大取样本底部20%（向上取整），比较两组换手率中位数之比。${d.scopeLabel}；${d.limitations.join("；")}`,
    points: [], auxiliary: [
      { label: "小盘组换手率中位数", value: d.smallMedian, unit: "%", date: d.asOf },
      { label: "同池整体换手率中位数", value: d.allMedian, unit: "%", date: d.asOf },
    ] };
}
