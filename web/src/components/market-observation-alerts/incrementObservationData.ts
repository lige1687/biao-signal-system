export type SessionPoint = { date: string; overnight20_pp: number; intraday20_pp: number; diff20_pp: number };
export type InstitutionRow = { code: string; name: string; buy_yuan: number; sell_yuan: number; net_yuan: number; reasons: string[]; market: string; source_url: string };
export type IncrementObservationSnapshot = {
  schema: "market-increment-observations/1";
  session: {
    id: string; name: string; asof: string; source: string; source_url: string;
    snapshot: true; automatic_refresh: false; definition: string; interpretation: string;
    identity_status: string; limitations: string[]; latest: SessionPoint; points: SessionPoint[];
  };
  institutional_disclosure: {
    id: string; name: string; asof: string; source: string; source_url: string; exchange_scope_url: string;
    snapshot: true; automatic_refresh: false;
    coverage: { raw_disclosure_rows: number; convertible_rows_excluded: number; multi_day_rows_excluded: number; single_day_rows: number;
      duplicate_reason_rows_removed: number; ambiguous_stocks_excluded: unknown[]; unique_stocks: number };
    buy_yuan: number; sell_yuan: number; net_yuan: number; rows: InstitutionRow[];
    retail_identity: null; limitations: string[];
  };
};

const record = (x: unknown): x is Record<string, unknown> => !!x && typeof x === "object" && !Array.isArray(x);
const finite = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);
const text = (x: unknown): x is string => typeof x === "string" && x.trim().length > 0;
const day = (x: unknown): x is string => text(x) && /^\d{4}-\d{2}-\d{2}$/.test(x)
  && Number.isFinite(Date.parse(`${x}T00:00:00Z`)) && new Date(`${x}T00:00:00Z`).toISOString().slice(0, 10) === x;
const close = (a: number, b: number, tolerance = 1e-8) => Math.abs(a - b) <= tolerance;
const strings = (x: unknown) => Array.isArray(x) && x.every(text);
const count = (x: unknown): x is number => finite(x) && Number.isInteger(x) && x >= 0;
function trustedLink(value: unknown, hosts: readonly string[]): boolean {
  if (!text(value)) return false;
  try { const url = new URL(value); return url.protocol === "https:" && hosts.includes(url.hostname) && !url.username && !url.password; }
  catch { return false; }
}
const sessionPoint = (x: unknown): x is SessionPoint => record(x) && day(x.date)
  && finite(x.overnight20_pp) && finite(x.intraday20_pp) && finite(x.diff20_pp)
  && close(x.intraday20_pp - x.overnight20_pp, x.diff20_pp);

/** Reject inconsistent dates, duplicate stocks and arithmetic mismatches before rendering. */
export function parseIncrementObservation(raw: unknown): IncrementObservationSnapshot {
  if (!record(raw) || raw.schema !== "market-increment-observations/1" || !record(raw.session) || !record(raw.institutional_disclosure)) throw new Error("观察资料不完整");
  const s = raw.session;
  if (!day(s.asof) || !text(s.source) || !trustedLink(s.source_url, ["web.ifzq.gtimg.cn"])
    || s.snapshot !== true || s.automatic_refresh !== false || !text(s.definition) || !strings(s.limitations)
    || !sessionPoint(s.latest) || !Array.isArray(s.points) || s.points.length < 21) throw new Error("隔夜与日内资料不完整");
  let prev = "";
  for (const p of s.points) {
    if (!sessionPoint(p) || p.date <= prev || p.date > s.asof) throw new Error("隔夜与日内历史日期或数值不匹配");
    prev = p.date;
  }
  const last = s.points[s.points.length - 1] as SessionPoint;
  if (last.date !== s.asof || s.latest.date !== last.date
    || !(["overnight20_pp", "intraday20_pp", "diff20_pp"] as const).every(key => s.latest && (s.latest as SessionPoint)[key] === last[key])) throw new Error("隔夜与日内末值不匹配");
  const i = raw.institutional_disclosure;
  if (!day(i.asof) || !text(i.source) || !trustedLink(i.source_url, ["emdata.eastmoney.com"])
    || !trustedLink(i.exchange_scope_url, ["www.sse.com.cn"]) || i.snapshot !== true || i.automatic_refresh !== false
    || i.retail_identity !== null || !strings(i.limitations) || !record(i.coverage) || !Array.isArray(i.rows)
    || !finite(i.buy_yuan) || !finite(i.sell_yuan) || !finite(i.net_yuan) || i.buy_yuan < 0 || i.sell_yuan < 0) throw new Error("机构席位资料不完整");
  const c = i.coverage;
  if (![c.raw_disclosure_rows, c.convertible_rows_excluded, c.multi_day_rows_excluded, c.single_day_rows, c.duplicate_reason_rows_removed, c.unique_stocks].every(count)
    || !Array.isArray(c.ambiguous_stocks_excluded) || c.ambiguous_stocks_excluded.length !== 0
    || c.raw_disclosure_rows !== (c.convertible_rows_excluded as number) + (c.multi_day_rows_excluded as number) + (c.single_day_rows as number)
    || c.single_day_rows !== (c.duplicate_reason_rows_removed as number) + (c.unique_stocks as number)
    || c.unique_stocks !== i.rows.length || !i.rows.length) throw new Error("机构席位覆盖数量不匹配");
  const codes = new Set<string>(); let buy = 0; let sell = 0; let net = 0;
  for (const row of i.rows) {
    if (!record(row) || !text(row.code) || !/^\d{6}$/.test(row.code) || codes.has(row.code) || !text(row.name)
      || !finite(row.buy_yuan) || !finite(row.sell_yuan) || !finite(row.net_yuan) || row.buy_yuan < 0 || row.sell_yuan < 0
      || !close(row.buy_yuan - row.sell_yuan, row.net_yuan, 0.02) || !strings(row.reasons)
      || !trustedLink(row.source_url, ["data.eastmoney.com"])) throw new Error("机构席位明细重复或金额不匹配");
    const sourcePath = new URL(row.source_url as string).pathname;
    if (sourcePath !== `/stock/lhb,${i.asof},${row.code}.html`) throw new Error("机构明细日期不匹配");
    codes.add(row.code); buy += row.buy_yuan; sell += row.sell_yuan; net += row.net_yuan;
  }
  if (!close(buy, i.buy_yuan, 0.02) || !close(sell, i.sell_yuan, 0.02) || !close(net, i.net_yuan, 0.02)
    || !close(i.buy_yuan - i.sell_yuan, i.net_yuan, 0.02)) throw new Error("机构席位合计不匹配");
  return raw as IncrementObservationSnapshot;
}

export function signed(value: number, digits = 2): string {
  return `${value > 0 ? "+" : value < 0 ? "-" : ""}${Math.abs(value).toFixed(digits)}`;
}

/** The difference identifies a series, not an opportunity or risk state. */
export const SESSION_DIFFERENCE_COLOR = "#6b6b6b";

/** Describe 20-day sums; missing observations remain unclassified. */
export function sessionReading(p: { overnight20_pp?: number | null; intraday20_pp?: number | null } | null | undefined): string {
  if (!p || !finite(p.overnight20_pp) || !finite(p.intraday20_pp)) return "隔夜与日内资料待补";
  const o = p.overnight20_pp, d = p.intraday20_pp;
  if (o < 0 && d < 0) return "两段均跌";
  if (o > 0 && d > 0) return "两段均涨";
  if (o < 0 && d > 0) return "隔夜跌、日内涨";
  if (o > 0 && d < 0) return "隔夜涨、日内跌";
  if (o === 0 && d === 0) return "隔夜与日内均持平";
  return o === 0 ? `隔夜持平，日内${d > 0 ? "上涨" : "下跌"}` : `日内持平，隔夜${o > 0 ? "上涨" : "下跌"}`;
}
