import { VALUATION_SOURCES, valuationMonthlyPoints } from "./marketReferenceBands";
import type {
  FocusMomentumObservation,
} from "../focus-momentum/data";
import type {
  FundamentalsOverview, MarketObservation, RatesHistoryResponse, RatesHistorySeries, RatesResponse,
  SentimentHistoryResponse, UsMacroResponse,
} from "../../types";

export type MetricPoint = { date: string; value: number | null };
export type MetricReading = {
  value: number | null;
  unit: string;
  date: string | null;
  dateLabel: string;
  change: number | null;
  changeUnit?: string;
  comparisonPeriod?: string | null;
  sourceName: string;
  sourceUrl?: string | null;
  sourceVersion: string;
  status: string;
  guide?: string;
  note: string;
  points: MetricPoint[];
  valuationFull?: boolean;
  alternative?: { label: string; value: number | null; points: MetricPoint[] };
  auxiliary?: { label: string; value: number | null; unit: string; date: string | null }[];
};

const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const observationStatus: Record<string, string> = {
  current: "来源已核；仍以资料日期为准",
  delayed: "资料有发布滞后；按资料日期观察",
  stale: "资料已陈旧；不当作当前市场读数",
  time_unverified: "首次发布时间未核；按资料日期观察",
  insufficient_history: "历史期数不足；仅作有限观察",
};
const values = (series?: RatesHistorySeries): MetricPoint[] => series && series.dates.length === series.values.length
  ? series.dates.map((date, index) => ({ date, value: valid(series.values[index]) ? series.values[index] : null })) : [];

export function fromObservation(item: MarketObservation | undefined, points: MetricPoint[] = []): MetricReading | null {
  if (!item) return null;
  const dated = typeof item.observation_date === "string" && item.observation_date.trim().length > 0;
  const readable = item.quality_status !== "missing" && dated;
  return {
    value: readable && valid(item.value) ? item.value : null, unit: item.unit,
    date: dated ? item.observation_date : null, dateLabel: "资料日期",
    change: readable && valid(item.change) ? item.change : null,
    changeUnit: item.change_unit ?? item.unit, comparisonPeriod: item.comparison_period,
    sourceName: item.source_name,
    sourceUrl: item.source_url, sourceVersion: item.definition_version,
    status: !readable ? "缺少有效资料日期或来源标记为缺失；无可核读数"
      : observationStatus[item.quality_status] ?? `资料状态未识别：${item.quality_status}`,
    note: [item.quality_reason, ...item.limitations].filter(Boolean).join("；"), points: readable ? points : [],
  };
}

export function fromFocus(data: FocusMomentumObservation): MetricReading {
  return {
    value: data.latest.focus * 100, unit: "%", date: data.latest.date, dateLabel: "历史样本截至",
    change: valid(data.latest.changeFocus) ? data.latest.changeFocus * 100 : null, changeUnit: "百分点",
    sourceName: "焦点股动量 · 固定300股研究样本", sourceVersion: data.definitionId,
    status: "仅历史研究样本；不是当前市场读数", note: `${data.scope.label}；过去20交易日回看。${data.scope.limitations.join("；")}`,
    points: data.series.map((row) => ({ date: row.date, value: row.focus * 100 })),
  };
}

/** Reuse the existing dated ERP history, including a missing final observation. */
export function fromErpHistory(data: RatesHistoryResponse | undefined, id: "erp-cn" | "erp-us"): MetricReading | null {
  const cn = id === "erp-cn";
  const series = data?.series?.[cn ? "erp_cn" : "erp_us"];
  const points = values(series);
  if (!points.length || points.some((point, i) => !/^\d{4}-\d{2}-\d{2}$/.test(point.date)
    || (i > 0 && point.date <= points[i - 1].date))) return null;
  const last = points[points.length - 1];
  const previous = points[points.length - 2];
  return {
    value: last.value, unit: "百分点", date: last.date, dateLabel: "历史资料截至",
    change: valid(last.value) && valid(previous?.value) ? last.value - previous.value : null,
    changeUnit: "百分点", comparisonPeriod: "前一观测",
    sourceName: cn ? "现有沪深300 PE_TTM 与中国10年国债序列" : "现有标普500盈利收益率与美国10年国债序列",
    sourceVersion: `fundamentals.ratesHistory · ${cn ? "erp_cn" : "erp_us"}`,
    status: "观察股票相对债券的估值；未验证为阶段顶底信号。",
    note: `${cn ? "100÷沪深300 PE_TTM" : "标普500盈利收益率"} − ${cn ? "中国" : "美国"}10年国债收益率。两端用百分比，差值用百分点；扩大可能来自股价、盈利或利率变化，不是预期投资回报。${cn ? "此旧接口的沪深300估值实际为月末记录，不是日频输入；三年轨道另用已核资料。" : "盈利端月度历史按已观测日期向后使用，日线不代表每日新增盈利资料。美股轨道采用此前三年均值及1.5/2倍标准差，作为本地相对估值观察；历史检验中上轨样本少，下轨1.5σ风险关联不稳，2σ未见增量。"}`,
    points,
  };
}

export function fromValuation(data: RatesResponse | undefined, id: "hs300-pe" | "sp500-cape", history?: RatesHistorySeries, full = false): MetricReading | null {
  const val = id === "hs300-pe" ? data?.valuation.cn_pe : data?.valuation.us_cape;
  const cape = id === "sp500-cape";
  const points = valuationMonthlyPoints(values(history).map(point => cape ? { ...point, date: point.date.slice(0, 7) } : point));
  const latest = points[points.length - 1];
  if (!val && !latest) return null;
  const source = VALUATION_SOURCES[id];
  return {
    value: latest ? latest.value : val?.value ?? null, unit: "倍",
    date: latest?.date ?? (cape ? val?.as_of.slice(0, 7) : val?.as_of) ?? null,
    dateLabel: cape ? "所属月" : "资料日期", change: null,
    sourceName: cape ? source.source : `${source.source}（经 akshare）`, sourceUrl: source.url,
    sourceVersion: cape ? "Shiller CAPE" : "沪深300 PE_TTM",
    status: cape ? "月频历史；首次发布日期未知" : "沪深300指数滚动市盈率",
    note: cape ? "用过去十年经通胀调整的盈利均值计算；月份是资料所属期。"
      : "每月取同源最后读数；当月显示截至所示日期的最新读数。",
    points, valuationFull: full,
  };
}

export function fromCnPmi(data: FundamentalsOverview | undefined, history?: RatesHistorySeries): MetricReading | null {
  const pmi = data?.macro.find((item) => item.key === "pmi");
  if (!pmi) return null;
  return {
    value: valid(pmi.value) ? pmi.value : null, unit: "指数点", date: pmi.period, dateLabel: "所属期",
    change: null, sourceName: "中国制造业 PMI · 国家统计局/东财转发", sourceVersion: "现有 fundamentals.overview",
    status: "月度所属期；首次公开时间未在此核对", note: pmi.note_cn, points: values(history),
  };
}

export function fromUsMacro(data: UsMacroResponse | undefined, key: "wei" | "hy_oas" | "dgorder_yoy", withPoints: boolean): MetricReading | null {
  const item = data?.items.find((row) => row.key === key);
  if (!item) return null;
  const source = key === "wei" ? "纽约联储 WEI / FRED" : key === "hy_oas" ? "ICE BofA 高收益债利差 / FRED" : "美国耐用品订单同比 / FRED";
  return {
    value: valid(item.value) ? item.value : null, unit: "%", date: item.date,
    dateLabel: key === "dgorder_yoy" ? "所属月" : "资料日期", change: null,
    sourceName: source, sourceVersion: "现有 fundamentals.usMacro",
    status: key === "dgorder_yoy" ? "美国 PMI 原读数未接通；此值是不同指标" : "以资料日期为准；接口可能更新或修订",
    note: key === "hy_oas" ? "高收益债相对国债的额外收益率；未建立固定顶底线。FRED自2026年4月起仅公开近三年。" : item.note_cn, points: withPoints ? values(data?.series[key]) : [],
  };
}

export function fromSurveyHistory(data: SentimentHistoryResponse | undefined, id: "aaii" | "naaim"): MetricPoint[] {
  return data?.observations.map((row) => ({
    date: row.survey_week,
    value: id === "aaii" ? (valid(row.bull_bear) ? row.bull_bear : null)
      : (valid(row.exposure_index) ? row.exposure_index : null),
  })) ?? [];
}

export interface ReusedSeries {
  schemaVersion: 1; historicalOnly: true;
  series: Record<string, { unit: string; frequency: string; sourceName: string; sourceUrl: string;
    sourceVersion: string; sourceSha256: string; points: (MetricPoint & { cashCredit?: number | null; securitiesCredit?: number | null })[];
    latest: MetricPoint & { cashCredit?: number | null; securitiesCredit?: number | null };
    previous: MetricPoint }>;
}

export function parseReused(raw: unknown): ReusedSeries {
  if (!raw || typeof raw !== "object") throw new Error("静态历史资料结构无效");
  const data = raw as ReusedSeries;
  if (data.schemaVersion !== 1 || data.historicalOnly !== true) throw new Error("静态历史资料版本不符");
  for (const id of ["ofr-fsi", "finra-margin"]) {
    const series = data.series?.[id];
    if (!series || !Array.isArray(series.points) || !series.points.length || !series.points.every((p) =>
      typeof p.date === "string" && valid(p.value)) || !series.latest || !valid(series.latest.value)
      || series.latest.date !== series.points[series.points.length - 1].date || typeof series.sourceSha256 !== "string") {
      throw new Error(`${id} 静态资料不完整`);
    }
  }
  for (const id of ["nfci", "vxn"]) {
    const series = data.series?.[id];
    const minPoints = id === "nfci" ? 100 : 250;
    if (!series || !Array.isArray(series.points) || series.points.length < minPoints
      || !series.points.every((p, index) => typeof p.date === "string" && valid(p.value)
        && (index === 0 || p.date > series.points[index - 1].date))
      || !series.latest || !valid(series.latest.value)
      || series.latest.date !== series.points[series.points.length - 1].date
      || typeof series.sourceSha256 !== "string" || !series.sourceSha256) {
      throw new Error(`${id} 静态历史序列不完整`);
    }
  }
  return data;
}

export function fromReused(data: ReusedSeries, id: "ofr-fsi" | "finra-margin" | "nfci" | "vxn", compact: boolean): MetricReading {
  const item = data.series[id];
  if (id === "nfci") return {
    value: item.latest.value, unit: item.unit, date: item.latest.date, dateLabel: "资料日期",
    change: valid(item.latest.value) && valid(item.previous.value) ? item.latest.value - item.previous.value : null,
    changeUnit: item.unit, comparisonPeriod: "前1周", sourceName: item.sourceName,
    sourceUrl: item.sourceUrl, sourceVersion: item.sourceVersion,
    status: "近两年周频历史快照；历史会修订，不自动更新",
    note: "芝加哥联储周频金融条件相对长期平均的标准化位置；负值表示条件相对宽松，零线为长期平均。",
    points: compact ? [] : item.points,
  };
  if (id === "vxn") return {
    value: item.latest.value, unit: item.unit, date: item.latest.date, dateLabel: "资料日期",
    change: valid(item.latest.value) && valid(item.previous.value) ? item.latest.value - item.previous.value : null,
    changeUnit: item.unit, comparisonPeriod: "前一交易日", sourceName: item.sourceName,
    sourceUrl: item.sourceUrl, sourceVersion: item.sourceVersion,
    status: "近两年日频历史快照；不自动更新",
    note: "VXN是纳指100期权隐含波动，不是VIX；数值越高表示期权市场预计波动越大，没有涨跌方向。",
    points: compact ? [] : item.points,
  };
  return {
    value: item.latest.value, unit: item.unit, date: id === "finra-margin" ? item.latest.date.slice(0, 7) : item.latest.date,
    dateLabel: id === "finra-margin" ? "所属月" : "资料日期",
    change: valid(item.previous.value) && valid(item.latest.value) ? item.latest.value - item.previous.value : null,
    changeUnit: item.unit, sourceName: item.sourceName, sourceUrl: item.sourceUrl,
    sourceVersion: item.sourceVersion, status: "已核本地历史副本；不自动更新",
    note: id === "finra-margin" ? "客户证券保证金账户借记余额。金额不是净流入；2010年前后现金分列口径改变。" : "金融压力合成指标；正负表示相对其标准化基准的位置，并非涨跌预测。",
    points: compact ? [] : item.points,
    auxiliary: id === "finra-margin" ? [
      { label: "现金账户闲置资金", value: item.latest.cashCredit ?? null, unit: item.unit, date: item.latest.date.slice(0, 7) },
      { label: "证券保证金账户闲置资金", value: item.latest.securitiesCredit ?? null, unit: item.unit, date: item.latest.date.slice(0, 7) },
    ] : undefined,
  };
}

export interface BakerSeries {
  schemaVersion: 1; id: "baker-wurgler"; historicalOnly: true; unit: string; asOf: string;
  sourceName: string; sourceUrl: string; sourceSha256: string; version: string; definition: string;
  publicationTiming: string; limitations: string[];
  series: { date: string; value: number | null; rawValue?: number | null }[];
  latest: { date: string; value: number | null; rawValue?: number | null; change: null };
}

export function parseBaker(raw: unknown): BakerSeries {
  if (!raw || typeof raw !== "object") throw new Error("Baker 资料结构无效");
  const data = raw as BakerSeries;
  if (data.schemaVersion !== 1 || data.id !== "baker-wurgler" || data.historicalOnly !== true
    || data.latest?.change !== null || !valid(data.latest?.value) || !Array.isArray(data.series)
    || !data.series.length || data.latest.date !== data.series[data.series.length - 1].date
    || data.series[data.series.length - 1].value !== data.latest.value
    || !data.series.every((p) => typeof p.date === "string" && (p.value === null || valid(p.value))
      && (p.rawValue === undefined || p.rawValue === null || valid(p.rawValue)))
    || typeof data.sourceSha256 !== "string" || !Array.isArray(data.limitations)) {
    throw new Error("Baker 资料版本或末值不符");
  }
  return data;
}

export function fromBaker(data: BakerSeries, compact: boolean, variant: "orth" | "raw" = "orth"): MetricReading {
  const raw = variant === "raw";
  return {
    value: raw ? data.latest.rawValue ?? null : data.latest.value,
    unit: data.unit, date: data.latest.date.slice(0, 7), dateLabel: "所属月", change: null,
    sourceName: data.sourceName, sourceUrl: data.sourceUrl, sourceVersion: data.version,
    status: `${raw ? "SENT 原始综合水平" : "默认 SENT_ORTH 宏观调整后水平"}；仅历史资料，不能读作今日值或相邻月情绪变化`,
    note: `${data.definition} ${data.publicationTiming} ${data.limitations.join("；")}`,
    points: compact ? [] : data.series.map((p) => ({ date: p.date, value: raw ? p.rawValue ?? null : p.value })),
    alternative: compact ? undefined : { label: raw ? "SENT_ORTH · 宏观调整后" : "SENT · 原始综合水平",
      value: raw ? data.latest.value : data.latest.rawValue ?? null,
      points: data.series.map((p) => ({ date: p.date, value: raw ? p.value : p.rawValue ?? null })) },
  };
}

export function formatValue(value: number | null, unit: string): string {
  if (!valid(value)) return "暂无可核读数";
  const formatted = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: unit === "百万美元" ? 0 : 3 }).format(value);
  return `${formatted} ${unit}`.trim();
}
