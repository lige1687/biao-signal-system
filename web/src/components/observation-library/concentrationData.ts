import type { MetricReading } from "./metricData";

export const CONCENTRATION_URL = "/api/fundamentals/turnover-concentration";
export const CONCENTRATION_QUERY_KEY = ["turnoverConcentrationMonthlyV2Live"] as const;

export interface ConcentrationPoint {
  date: string;
  value: number | null;
  n: number;
  k: number;
  missingDays: number;
  invalidRows: number;
  amountConflicts: number;
  extraCalendarDays: number;
  sourceMissingDates: number;
}
export interface ConcentrationObservation {
  schemaVersion: 1;
  definitionId: "observation.cn_supplier_amount_monthly_top5pct.v2";
  historicalOnly: true;
  current: null;
  pendingMonth?: string;
  pendingReason?: string;
  asOf: string;
  sourceThrough: string;
  sourceSha256: string;
  sourceUrl: string;
  points: ConcentrationPoint[];
}

const count = (n: unknown): n is number => typeof n === "number" && Number.isSafeInteger(n) && n >= 0;
const day = (s: unknown): s is string => typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s)
  && !Number.isNaN(Date.parse(`${s}T00:00:00Z`)) && new Date(`${s}T00:00:00Z`).toISOString().slice(0, 10) === s;

export function parseConcentration(raw: unknown): ConcentrationObservation {
  if (!raw || typeof raw !== "object") throw new Error("成交额集中度资料结构无效");
  const data = raw as ConcentrationObservation;
  if (data.schemaVersion !== 1 || data.definitionId !== "observation.cn_supplier_amount_monthly_top5pct.v2"
    || data.historicalOnly !== true || data.current !== null || !day(data.asOf) || !day(data.sourceThrough)
    || !/^[a-f0-9]{64}$/.test(data.sourceSha256) || typeof data.sourceUrl !== "string"
    || !Array.isArray(data.points) || !data.points.length) throw new Error("成交额集中度版本或来源无效");
  data.points.forEach((p, i) => {
    if (!p || !day(p.date) || !count(p.n) || !count(p.k) || p.k !== Math.ceil(p.n * .05)
      || ![p.missingDays, p.invalidRows, p.amountConflicts, p.extraCalendarDays, p.sourceMissingDates].every(count)
      || (p.value !== null && (typeof p.value !== "number" || !Number.isFinite(p.value) || p.value < 0 || p.value > 1
        || p.n === 0 || p.missingDays + p.invalidRows + p.amountConflicts + p.extraCalendarDays + p.sourceMissingDates > 0))) {
      throw new Error("成交额集中度月份数值或覆盖状态无效");
    }
    if (i > 0) {
      const prev = data.points[i - 1].date;
      const monthIndex = (d: string) => Number(d.slice(0, 4)) * 12 + Number(d.slice(5, 7));
      if (monthIndex(p.date) - monthIndex(prev) !== 1) throw new Error("成交额集中度必须保留连续月份，缺失月份用空值");
    }
  });
  if (data.asOf !== data.points[data.points.length - 1].date || data.sourceThrough < data.asOf) {
    throw new Error("成交额集中度资料日期不一致");
  }
  return data;
}

export function fromConcentration(data: ConcentrationObservation): MetricReading {
  const last = data.points[data.points.length - 1];
  const previous = data.points[data.points.length - 2];
  const validMonths = data.points.filter((p) => p.value !== null).length;
  return {
    value: last.value === null ? null : last.value * 100,
    unit: "%", date: last.date.slice(0, 7), dateLabel: "最后已核完整月",
    change: last.value !== null && previous?.value != null ? (last.value - previous.value) * 100 : null,
    changeUnit: "百分点", comparisonPeriod: "上月",
    sourceName: "BaoStock 沪深A股原始成交额 · 本地月度统计", sourceUrl: data.sourceUrl,
    sourceVersion: `${data.definitionId} · 原始资料截至${data.sourceThrough}`,
    status: data.pendingMonth ? `${data.pendingMonth}停牌与退市资料未齐，暂不判断；下方显示最后已核月份。` : last.value === null ? "该月输入不完整，读数未知；不回退为上一期数值。"
      : `该月${last.n}只股票，取成交额前${last.k}只；已存历史，不自动更新。`,
    note: `每股自然月成交额求和，按月内有合法行情记录的股票数取前5%（向上取整），除以同池总成交额。供应商覆盖沪深A股，含ST与期间上市、退出股票，不含北交所和B股；不是官方完整历史名单或作者原式复刻。明确停牌状态按零成交处理，无行情行仍为未知。${data.points.length}个月中${validMonths}个月可用，其余保留断线；整月值须月末后才能得到。中银证券强调集中度需结合市场成交额；本地月度分位只作高低参照。`,
    points: data.points.map((p) => ({ date: p.date, value: p.value === null ? null : p.value * 100 })),
  };
}
