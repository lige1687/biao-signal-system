import { erpBands } from "../observation-library/erpBands";
import { erpCrossings } from "../observation-library/erpCrossings";
import type { ErpReference } from "../observation-library/erpReferenceData";
import type { BreadthReadingResponse } from "../market-style/breadthReadingTypes";
import type { AlertInput, AlertPoint } from "./model";

export type BreadthMarket = "CN_ALL_A" | "SP500";
export const BREADTH_METHOD = "breadth.observation@1.0.0";
export const breadthId = (market: BreadthMarket) => `${market}:B50:${BREADTH_METHOD}`;
export const ERP_ID = "erp-cn:3calendar-years:2sigma:weekly-reference@1";
export const marketLabel = (market: BreadthMarket) => market === "CN_ALL_A" ? "全A · 50日宽度" : "标普500 · 50日宽度";
const finite = (n: unknown): n is number => typeof n === "number" && Number.isFinite(n);

/** Reject a different universe or calculation contract instead of relabelling its result. */
export function parseBreadth(raw: unknown, market: BreadthMarket): BreadthReadingResponse {
  if (!raw || typeof raw !== "object") throw new Error("宽度资料缺失");
  const data = raw as BreadthReadingResponse;
  const o = data.observation;
  if (data.market_id !== market || !Array.isArray(data.history) || !data.history.length || !o || o.error
    || o.method_version !== BREADTH_METHOD || o.lookback_observations !== 1260 || o.min_observations !== 252
    || o.lower_quantile !== 0.1 || o.upper_quantile !== 0.9 || o.includes_current !== true
    || !Array.isArray(o.history) || !o.history.length || !o.latest
    || o.latest.date !== o.history[o.history.length - 1]?.date
    || o.latest.date !== data.history[data.history.length - 1]?.date
    || data.history.some((p, i) => !p || typeof p.date !== "string" || (i > 0 && p.date <= data.history[i - 1].date))
    || o.history.some((p, i) => !p || !p.horizons?.["50"] || typeof p.date !== "string"
      || (i > 0 && p.date <= o.history[i - 1].date))) throw new Error("宽度对象、日期或轨道口径不一致");
  return data;
}

export function breadthInput(market: BreadthMarket, data?: BreadthReadingResponse, loadError = false): AlertInput {
  const prices = new Map(data?.history.map(p => [p.date, p.breadth_50]) ?? []);
  return { id: breadthId(market), label: marketLabel(market), kind: "breadth",
    method: "50日宽度 · 近1260条记录P10/P90", historicalOnly: false, loadError,
    points: (data?.observation?.history ?? []).map(p => {
      const h = p.horizons["50"];
      const value = prices.get(p.date);
      const ready = h.status === "ready" && h.sample_count >= 252 && finite(value) && value >= 0 && value <= 100
        && finite(h.lower) && finite(h.upper) && h.lower >= 0 && h.upper <= 100 && h.lower <= h.upper;
      // These are the server's inclusive historical bands, not a new forecasting rule.
      const phase = !ready ? "unknown" : h.lower === h.upper ? "flat"
        : value! <= h.lower! ? "low" : value! >= h.upper! ? "high" : "middle";
      const consistent = ready && phase === h.position;
      return { date: p.date, value: finite(value) ? value : null,
        lower: ready ? h.lower : null, upper: ready ? h.upper : null,
        phase: consistent ? phase : "unknown", event: consistent ? h.event : "unknown" };
    }) };
}

export function erpInput(data?: ErpReference, loadError = false): AlertInput {
  const rows = erpBands(data?.points ?? []);
  const entries = new Map(erpCrossings(rows).map(p => [p.date, p.kind]));
  let previous: AlertPoint | null = null;
  const points: AlertPoint[] = rows.map(row => {
    const complete = finite(row.value) && finite(row.lower) && finite(row.upper);
    const phase: AlertPoint["phase"] = !complete ? "unknown" : row.lower === row.upper ? "flat"
      : row.value! > row.upper! ? "high" : row.value! < row.lower! ? "low" : "middle";
    const gap = previous ? (Date.parse(row.date) - Date.parse(previous.date)) / 86_400_000 : Infinity;
    const adjacent = previous !== null && previous.phase !== "unknown" && gap > 0 && gap <= 10;
    const entry = entries.get(row.date);
    const event: AlertPoint["event"] = !complete || !adjacent ? "unknown" : phase === "flat" ? "none"
      : entry === "upper" ? "enter_high" : entry === "lower" ? "enter_low"
      : phase === "high" ? "stay_high" : phase === "low" ? "stay_low"
      : previous!.phase === "high" ? "exit_high" : previous!.phase === "low" ? "exit_low" : "none";
    const point = { date: row.date, value: row.value, lower: row.lower, upper: row.upper, phase, event };
    previous = point;
    return point;
  });
  return { id: ERP_ID, label: "沪深300 · 股债利差", kind: "erp", method: "周频 · 3年均值±2σ",
    historicalOnly: data?.historicalOnly ?? true, loadError, points };
}

export const chartLink = (kind: "erp" | BreadthMarket) => kind === "erp"
  ? "/fundamentals?observation=erp-cn#fund-sec-market"
  : `/fundamentals?observation=breadth&market=${kind === "CN_ALL_A" ? "cn" : "us"}#fund-sec-market`;
