/** Read-only presentation of research-owned account results. Fractions stay fractions in the contract. */
export type CurvePoint = [string, number | null, number | null, number | null, number | null, number | null];
export type CurveMetrics = Record<string, number | null | Record<string, number>>;
export interface CurveStream { points: CurvePoint[]; period: Record<string, CurveMetrics>; orders?: number; filled?: number; blocked?: number; drawdown_points?: Record<string, [string, number | null][]> }
export interface CurveFactor { id: string; name: string; available: boolean; formula?: string; purpose?: string; primaryUse?: string; preference?: string; group5Meaning?: string; scope?: string; unavailableReason?: string | null }
export interface CurveRegime { id: string; regimeLabel: string; regimeDefinition?: string | null; available: boolean; unavailableReason?: string | null; intervals: { start: string; end: string }[] }
export type RegimeMetrics = Record<string, number | null | string[]>;
export interface MonthlyDiagnostic { month: string; return: number | null; benchmarkReturn: number | null; excessReturn: number | null; cashEnd: number | null; unknownEnd: number | null; unknownMax: number | null; turnover: number | null; fees: number | null }
export interface AnnualDiagnostic { year: number; months: number; completeYear: boolean; return: number | null; benchmarkReturn: number | null; difference: number | null }
export interface CurveDiagnostics { schemaVersion: 1; datasetId: string; sourceSummarySha256: string; kind: "account_diagnostics_not_predictive_ic"; description: string; units: string | Record<string, unknown>; groupMeans: Record<string, Record<string, Record<string, number | null>>>; series: Record<string, { monthly: MonthlyDiagnostic[]; annual: AnnualDiagnostic[] }>; capabilities: { id: string; status: string; reason: string }[] }
export interface CurveDataset {
  id: string; name: string; market: string; universeId: string; universeLabel: string;
  available: boolean; unavailableReason?: string | null; statusLabel?: string; availableRanges?: { start: string; end: string };
  sample_note?: string; source_report?: string; history_role?: string; source_manifest_sha256?: string;
  method?: string; drawdown_basis?: string; factors: CurveFactor[];
  pools: { id: string; label: string }[]; fees_bps: number[];
  regimes: CurveRegime[]; periods: Record<string, [string, string]>;
  streams: Record<string, CurveStream>; increments?: Record<string, Record<string, unknown>>;
  regimeStatistics?: Record<string, Record<string, Record<string, RegimeMetrics>>>;
  regimeSourceNote?: string;
  diagnostics?: CurveDiagnostics; diagnosticsError?: string;
  assessment?: CurveAssessment; assessmentError?: string;
}
export interface CurveDocument { schema_version: "factor-curve-view/1"; generated_at?: string; datasets: CurveDataset[] }
export interface CurveSelection { dataset: string; curveFactor: string; pool: string; fee: string; period: string; regime: string }
export interface DisplayPoint { date: string; value: number | null; drawdown: number | null; unknown: number | null; cash: number | null; unknownMax: number | null }
export interface DisplaySeries { id: string; label: string; color: string; points: DisplayPoint[]; metrics: CurveMetrics | undefined }
export const CURVE_DATA_URL = "/research/factor-curve-library-20261022/catalog.json";
export const CURVE_QUERY_KEYS = ["dataset", "curveFactor", "pool", "fee", "period", "regime"] as const;
export const GROUP_COLORS = ["#84919d", "#a5753b", "#628f9d", "#4c6ca7", "#167461", "#192a36"];
const object = (v: unknown): v is Record<string, unknown> => Boolean(v) && typeof v === "object" && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string" && v.trim().length > 0;
const finiteOrNull = (v: unknown) => v === null || typeof v === "number" && Number.isFinite(v);
const day = /^\d{4}-\d{2}-\d{2}$/;
const month = /^\d{4}-\d{2}$/;

export function parseDiagnostics(v: unknown, datasetId: string, summaryHash: string): CurveDiagnostics {
  if (!object(v) || v.schemaVersion !== 1 || v.datasetId !== datasetId || v.sourceSummarySha256 !== summaryHash || v.kind !== "account_diagnostics_not_predictive_ic" || !object(v.groupMeans) || !object(v.series) || !Array.isArray(v.capabilities)) throw new Error("专业诊断未绑定当前研究样本或当前资金版本。");
  for (const stream of Object.values(v.series)) {
    if (!object(stream) || !Array.isArray(stream.monthly) || !Array.isArray(stream.annual)) throw new Error("专业诊断缺少逐月或年度记录。");
    let prior = "";
    for (const row of stream.monthly) {
      if (!object(row) || !month.test(String(row.month)) || String(row.month) <= prior || !["return", "benchmarkReturn", "excessReturn", "cashEnd", "unknownEnd", "unknownMax", "turnover", "fees"].every(k => finiteOrNull(row[k]))) throw new Error("专业诊断月份或缺值格式不可用。");
      prior = String(row.month);
    }
    for (const row of stream.annual) if (!object(row) || typeof row.year !== "number" || typeof row.months !== "number" || typeof row.completeYear !== "boolean" || !["return", "benchmarkReturn", "difference"].every(k => finiteOrNull(row[k]))) throw new Error("年度诊断缺少真实月份数或完整年度标记。");
  }
  return v as unknown as CurveDiagnostics;
}

async function readPublicJson(url: string, signal?: AbortSignal, expectedHash?: string, fetcher: typeof fetch = fetch): Promise<unknown> {
  if (!url.startsWith("/research/") || url.includes("..") || url.includes("\\")) throw new Error("研究资料地址不在已登记的公开资料目录。");
  let response: Response;
  try { response = await fetcher(url, { signal, cache: "no-cache" }); }
  catch (error) { if (signal?.aborted) throw error; throw new Error("研究资料暂时无法读取，请确认本机服务可用后重试。"); }
  if (!response.ok) throw new Error(`研究资料暂不可用（HTTP ${response.status}）。`);
  if (!response.headers.get("content-type")?.toLowerCase().includes("application/json")) throw new Error("页面返回的不是研究JSON资料，资金线暂不展示。");
  const bytes = await response.arrayBuffer();
  if (expectedHash) {
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    const actual = Array.from(new Uint8Array(digest), v => v.toString(16).padStart(2, "0")).join("");
    if (actual !== expectedHash) throw new Error("资金资料指纹与目录记录不一致，暂不展示这批曲线。");
  }
  try { return JSON.parse(new TextDecoder().decode(bytes)) as unknown; }
  catch { throw new Error("研究资料无法解析，资金线暂不展示。"); }
}

/** Thin adapter over the research owner's versioned catalog and untouched saved summary. */
export async function loadCurveLibrary(signal?: AbortSignal, fetcher: typeof fetch = fetch): Promise<CurveDocument> {
  const raw = await readPublicJson(CURVE_DATA_URL, signal, undefined, fetcher);
  if (!object(raw) || raw.schemaVersion !== 1 || !Array.isArray(raw.datasets)) throw new Error("研究目录版本与当前页面不兼容。");
  const pendingFactors = Array.isArray(raw.pendingFactors) ? raw.pendingFactors : [];
  const datasets: CurveDataset[] = await Promise.all(raw.datasets.map(async (entry: unknown) => {
    if (!object(entry) || !text(entry.id) || !text(entry.name) || !text(entry.market) || !text(entry.dataUrl) || !text(entry.summarySha256) || !Array.isArray(entry.factors) || !Array.isArray(entry.stockPools)) throw new Error("研究目录缺少准确样本身份或来源指纹。");
    const summary = await readPublicJson(entry.dataUrl, signal, entry.summarySha256, fetcher);
    if (!object(summary) || !object(summary.streams) || !object(summary.periods)) throw new Error("原研究资金记录缺少流或历史分期。");
    const regimes: CurveRegime[] = [{ id: "all", regimeLabel: "全部环境", available: true, intervals: [] }];
    let regimeStatistics: CurveDataset["regimeStatistics"];
    let regimeSourceNote: string | undefined;
    let diagnostics: CurveDiagnostics | undefined;
    let diagnosticsError: string | undefined;
    let assessment: CurveAssessment | undefined;
    let assessmentError: string | undefined;
    if (object(entry.assessment)) {
      if (entry.assessment.status === "available" && text(entry.assessment.dataUrl) && text(entry.assessment.sha256)) {
        try { assessment = parseAssessment(await readPublicJson(entry.assessment.dataUrl, signal, entry.assessment.sha256, fetcher), entry.id, entry.summarySha256); }
        catch (error) { if (signal?.aborted) throw error; assessmentError = error instanceof Error ? error.message : "预测与风险收益资料暂不可用。"; }
      } else assessmentError = typeof entry.assessment.reason === "string" ? entry.assessment.reason : "预测与风险收益资料尚未接入。";
    }
    if (Array.isArray(entry.regimes)) {
      for (const g of entry.regimes) if (object(g) && g.id !== "all") regimes.push(g as unknown as CurveRegime);
    } else {
      const regime = object(entry.regime) ? entry.regime : {};
      if (regime.status === "available" && text(regime.dataUrl) && text(regime.sha256)) {
        try {
          const result = await readPublicJson(regime.dataUrl, signal, regime.sha256, fetcher);
          if (!object(result) || result.schemaVersion !== 1 || !text(result.definition) || !object(result.labels) || !Array.isArray(result.episodes) || !object(result.statistics)) throw new Error("环境定义或条件统计格式不可用。");
          const labels = result.labels;
          const counts = object(result.counts) ? result.counts : {};
          for (const [id, label] of Object.entries(labels)) {
            if (!text(label)) continue;
            const intervals = result.episodes.filter((ep: unknown) => object(ep) && ep.state === id).map((ep: unknown) => {
              if (!object(ep) || !month.test(String(ep.startMonth)) || !month.test(String(ep.endMonth))) throw new Error("市场环境分段日期不可用。");
              const [year, m] = String(ep.endMonth).split("-").map(Number);
              return { start: `${ep.startMonth}-01`, end: new Date(Date.UTC(year, m, 0)).toISOString().slice(0, 10) };
            });
            regimes.push({ id, regimeLabel: label, regimeDefinition: result.definition, available: Number(counts[id]) > 0 && intervals.length > 0, unavailableReason: "这批历史没有该类环境月份。", intervals });
          }
          regimeStatistics = result.statistics as CurveDataset["regimeStatistics"];
          regimeSourceNote = Array.isArray(regime.limitations) ? regime.limitations.filter(v => typeof v === "string").join(" ") : undefined;
        } catch (error) {
          if (signal?.aborted) throw error;
          regimes.push({ id: "pending", regimeLabel: "市场环境资料读取失败", available: false, unavailableReason: error instanceof Error ? error.message : "环境资料暂不可用。", intervals: [] });
        }
      } else regimes.push({ id: "pending", regimeLabel: "牛熊环境", available: false, unavailableReason: typeof regime.reason === "string" ? regime.reason : "市场环境定义与条件统计尚未接入。", intervals: [] });
    }
    const factors = entry.factors.map((f: unknown): CurveFactor => {
      if (!object(f) || !text(f.id) || !text(f.label)) throw new Error("研究目录的因子身份不可用。");
      return { id: f.id, name: f.label, available: true, formula: typeof f.formula === "string" ? f.formula : undefined, purpose: typeof f.primaryUse === "string" ? f.primaryUse : undefined, group5Meaning: typeof f.group5Meaning === "string" ? f.group5Meaning : undefined, preference: `G1 到 G5 按原定义从低到高排列；G5：${typeof f.group5Meaning === "string" ? f.group5Meaning : "方向尚未提供"}。分数高低不代表收益高低。` };
    });
    if (object(entry.diagnostics) && entry.diagnostics.status === "available" && text(entry.diagnostics.dataUrl) && text(entry.diagnostics.sha256)) {
      try { diagnostics = parseDiagnostics(await readPublicJson(entry.diagnostics.dataUrl, signal, entry.diagnostics.sha256, fetcher), entry.id, entry.summarySha256); }
      catch (error) { if (signal?.aborted) throw error; diagnosticsError = error instanceof Error ? error.message : "专业诊断暂不可用。"; }
    }
    for (const f of pendingFactors) if (object(f) && text(f.id) && text(f.label) && text(f.reason) && !factors.some(v => v.id === f.id)) factors.push({ id: f.id, name: f.label, available: false, unavailableReason: f.reason });
    return {
      id: entry.id, name: entry.name, market: entry.market, universeId: typeof entry.universeId === "string" ? entry.universeId : entry.id,
      universeLabel: typeof entry.universeDescription === "string" ? entry.universeDescription : entry.name, available: true,
      sample_note: typeof entry.universeDescription === "string" ? entry.universeDescription : undefined,
      source_report: typeof entry.sourceReportPath === "string" ? entry.sourceReportPath : undefined,
      history_role: entry.historySeen === true ? "已看历史；独立新验证尚未完成" : "验证身份以原报告为准",
      source_manifest_sha256: typeof summary.source_manifest_sha256 === "string" ? summary.source_manifest_sha256 : undefined,
      method: [entry.accountDescription, ...(Array.isArray(entry.limitations) ? entry.limitations : []), summary.method].filter(v => typeof v === "string").join(" "),
      drawdown_basis: "跌幅点为当月最深日回撤，沿原连续账户历史高点；分期不重设高点。",
      factors, pools: entry.stockPools as CurveDataset["pools"],
      fees_bps: [...new Set(Object.keys(summary.streams).map(key => key.match(/__fee(\d+)$/)?.[1]).filter((v): v is string => v !== undefined).map(Number))].sort((a, b) => a - b),
      regimes, periods: summary.periods as CurveDataset["periods"], streams: summary.streams as CurveDataset["streams"],
      increments: object(summary.increments) ? summary.increments as CurveDataset["increments"] : undefined, regimeStatistics, regimeSourceNote, diagnostics, diagnosticsError, assessment, assessmentError,
    };
  }));
  if (Array.isArray(raw.unavailableUniverses)) for (const u of raw.unavailableUniverses) if (object(u) && text(u.id) && text(u.label) && text(u.reason)) datasets.push({ id: u.id, name: u.label, market: "资料未接入", universeId: u.id, universeLabel: u.label, available: false, unavailableReason: u.reason, statusLabel: text(u.statusLabel) ? u.statusLabel : undefined, factors: [], pools: [], fees_bps: [], regimes: [], periods: {}, streams: {} });
  return parseCurveDocument({ schema_version: "factor-curve-view/1", generated_at: raw.generatedAt, datasets });
}

export function parseCurveDocument(input: unknown): CurveDocument {
  if (!object(input) || input.schema_version !== "factor-curve-view/1" || !Array.isArray(input.datasets) || !input.datasets.length) throw new Error("曲线资料格式与当前页面不兼容。");
  const ids = new Set<string>();
  for (const d of input.datasets) {
    if (!object(d) || !text(d.id) || ids.has(d.id) || !text(d.name) || !text(d.market) || !text(d.universeId) || !text(d.universeLabel) || typeof d.available !== "boolean") throw new Error("研究样本身份不完整或重复。");
    ids.add(d.id);
    if (!d.available) { if (!text(d.unavailableReason)) throw new Error("未接入样本缺少原因。"); continue; }
    if (!Array.isArray(d.factors) || !d.factors.length || !Array.isArray(d.pools) || !d.pools.length || !Array.isArray(d.fees_bps) || !d.fees_bps.length || !object(d.periods) || !object(d.streams)) throw new Error("研究样本缺少因子、费用或资金记录。");
    for (const f of d.factors) if (!object(f) || !text(f.id) || !text(f.name) || typeof f.available !== "boolean" || !f.available && !text(f.unavailableReason)) throw new Error("因子身份或资料状态不完整。");
    for (const p of d.pools) if (!object(p) || !text(p.id) || !text(p.label)) throw new Error("股票池身份不完整。");
    if (d.fees_bps.some((v: unknown) => typeof v !== "number" || !Number.isFinite(v) || v < 0)) throw new Error("费用单位或数值不可用。");
    for (const range of Object.values(d.periods)) if (!Array.isArray(range) || range.length !== 2 || !month.test(String(range[0])) || !month.test(String(range[1])) || range[0] > range[1]) throw new Error("历史分期日期不可用。");
    if (!Array.isArray(d.regimes) || !d.regimes.some((g: unknown) => object(g) && g.id === "all" && g.available === true)) throw new Error("市场环境资料缺少完整时间轴。");
    for (const g of d.regimes) {
      if (!object(g) || !text(g.id) || !text(g.regimeLabel) || typeof g.available !== "boolean" || !Array.isArray(g.intervals)) throw new Error("市场环境身份不可用。");
      if (g.available && g.id !== "all" && (!text(g.regimeDefinition) || !g.intervals.length)) throw new Error("市场环境缺少定义或日期区间。");
      for (const interval of g.intervals) if (!object(interval) || !day.test(String(interval.start)) || !day.test(String(interval.end)) || String(interval.start) > String(interval.end)) throw new Error("市场环境区间不可用。");
    }
    for (const stream of Object.values(d.streams)) {
      if (!object(stream) || !Array.isArray(stream.points) || !object(stream.period)) throw new Error("资金记录格式不可用。");
      let previous = "";
      for (const p of stream.points) {
        if (!Array.isArray(p) || p.length !== 6 || !day.test(String(p[0])) || String(p[0]) <= previous || !p.slice(1).every(finiteOrNull)) throw new Error("资金日期、缺值或点序列不可用。");
        previous = p[0] as string;
      }
    }
  }
  return input as unknown as CurveDocument;
}

export function defaultSelection(doc: CurveDocument, params: URLSearchParams): CurveSelection {
  const available = doc.datasets.filter(v => v.available);
  // Earlier curve links had no dataset key. Preserve their first matching source;
  // new interactions always write dataset explicitly, while a fresh page shows the latest batch.
  const legacyLink = !params.get("dataset") && params.get("curveFactor") ? available.find(v => v.factors.some(f => f.available && f.id === params.get("curveFactor"))) : undefined;
  const d = doc.datasets.find(v => v.id === params.get("dataset")) ?? legacyLink ?? available[available.length - 1];
  return {
    dataset: params.get("dataset") || d?.id || "",
    curveFactor: params.get("curveFactor") || d?.factors?.find(v => v.available)?.id || "",
    pool: params.get("pool") || d?.pools?.[0]?.id || "",
    fee: params.get("fee") || String(d?.fees_bps?.includes(25) ? 25 : d?.fees_bps?.[0] ?? ""),
    period: params.get("period") || (d?.periods?.all ? "all" : Object.keys(d?.periods ?? {})[0] || ""),
    regime: params.get("regime") || "all",
  };
}

export function selectCurves(doc: CurveDocument, selection: CurveSelection) {
  const d = doc.datasets.find(v => v.id === selection.dataset);
  if (!d?.available) throw new Error(d?.unavailableReason || "链接指定的研究样本尚未接入。");
  const f = d.factors.find(v => v.id === selection.curveFactor);
  if (!f?.available) throw new Error(f?.unavailableReason || "链接指定的因子尚无资金线。");
  if (!d.pools.some(p => p.id === selection.pool) || !d.fees_bps.includes(Number(selection.fee))) throw new Error("这个股票池与费用组合尚无对应资金线。");
  const range = d.periods[selection.period];
  if (!range) throw new Error("链接指定的历史分期尚未接入。");
  const regime = d.regimes.find(v => v.id === selection.regime);
  if (!regime?.available) throw new Error(regime?.unavailableReason || "链接指定的市场环境尚未接入。");
  const series: DisplaySeries[] = ["G1", "G2", "G3", "G4", "G5", "pool"].map((group, index) => {
    const key = group === "pool" ? `${selection.pool}__pool__fee${selection.fee}` : `${selection.pool}__${f.id}__${group}__fee${selection.fee}`;
    const stream = d.streams[key];
    if (!stream) throw new Error(`当前组合缺少${group === "pool" ? "共同池基准" : group}资金线，暂不能比较。`);
    const prior = [...stream.points].reverse().find(p => p[0].slice(0, 7) < range[0]);
    const selected = stream.points.filter(p => p[0].slice(0, 7) >= range[0] && p[0].slice(0, 7) <= range[1]);
    if (!prior || prior[1] === null || prior[1] <= 0 || !selected.length) throw new Error("该分期缺少起始报价或实际记录，无法归一展示。");
    const base = prior[1];
    const drawdowns = stream.drawdown_points?.[selection.period];
    const drawdownMap = drawdowns ? new Map(drawdowns) : null;
    return { id: group, label: group === "pool" ? "共同池基准" : group, color: GROUP_COLORS[index], metrics: stream.period[selection.period], points: [prior, ...selected].map(p => {
      const dd = drawdownMap ? drawdownMap.get(p[0]) ?? null : p[4];
      return { date: p[0], value: p[1] === null ? null : (p[1] / base - 1) * 100, drawdown: dd === null ? null : dd * 100, unknown: p[2] === null ? null : p[2] * 100, cash: p[3] === null ? null : p[3] * 100, unknownMax: p[5] === null ? null : p[5] * 100 };
    }) };
  });
  return { dataset: d, factor: f, range, regime, series, drawdownRebased: series.every(s => Boolean(d.streams[s.id === "pool" ? `${selection.pool}__pool__fee${selection.fee}` : `${selection.pool}__${f.id}__${s.id}__fee${selection.fee}`]?.drawdown_points?.[selection.period])) };
}

/** Split by edge, not point: adjacent known runs must never bridge a missing-price segment. */
export function priceSegments(points: DisplayPoint[], breakMonthlyGaps = false) {
  const result: { uncertain: boolean; values: (number | null)[] }[] = [];
  let current: typeof result[number] | undefined;
  for (let i = 1; i < points.length; i++) {
    const monthIndex = (date: string) => Number(date.slice(0, 4)) * 12 + Number(date.slice(5, 7));
    if (points[i - 1].value === null || points[i].value === null || breakMonthlyGaps && monthIndex(points[i].date) - monthIndex(points[i - 1].date) > 1) { current = undefined; continue; }
    const uncertain = points[i].unknownMax === null || points[i - 1].unknownMax === null || points[i].unknownMax! > 1e-10 || points[i - 1].unknownMax! > 1e-10;
    if (!current || current.uncertain !== uncertain) {
      current = { uncertain, values: Array(points.length).fill(null) as (number | null)[] };
      result.push(current);
    }
    current.values[i - 1] = points[i - 1].value;
    current.values[i] = points[i].value;
  }
  return result;
}

export function metricNumber(metrics: CurveMetrics | undefined, key: string): number | null {
  const v = metrics?.[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}
export function percent(v: number | null | undefined, signed = false) {
  return v === null || v === undefined || !Number.isFinite(v) ? "未提供" : `${signed && v > 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}
export function percentagePoints(v: number | null | undefined) {
  return v === null || v === undefined || !Number.isFinite(v) ? "未提供" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(2)}个百分点`;
}
export const feeLabel = (bps: number) => bps === 0 ? "不计费用" : `${(bps / 100).toFixed(2)}% / 每次买或卖`;
export function comparisonRows(dataset: CurveDataset, selection: CurveSelection) {
  const labels: Record<string, string> = { pool: "共同池", momentum: "中期动量 G5", scaled_momentum: "波动缩放动量", lowvol: "60日低波动" };
  return Object.entries(labels).map(([key, label]) => ({ key, label, item: dataset.increments?.[`${selection.pool}__${selection.curveFactor}__${selection.period}__vs_${key}`] })).filter((row): row is { key: string; label: string; item: Record<string, unknown> } => Boolean(row.item));
}
export function diagnosticView(dataset: CurveDataset, selection: CurveSelection) {
  const data = dataset.diagnostics;
  const range = dataset.periods[selection.period];
  if (!data || !range) return null;
  const groupKey = `${selection.pool}__${selection.curveFactor}__fee${selection.fee}`;
  const stream = data.series[`${selection.pool}__${selection.curveFactor}__G5__fee${selection.fee}`];
  const means = data.groupMeans[groupKey]?.[selection.period];
  if (!stream || !means) return null;
  const monthly = stream.monthly.filter(r => r.month >= range[0] && r.month <= range[1]);
  // Counts only select precomputed annual records wholly covered by this window.
  // A partial calendar year is labelled; its return is never annualised here.
  const annual = stream.annual.filter(r => monthly.filter(m => Number(m.month.slice(0, 4)) === r.year).length === r.months && r.months > 0);
  return { data, monthly, annual, groups: ["G1", "G2", "G3", "G4", "G5"].map(id => ({ id, mean: typeof means[id] === "number" ? means[id] : null })) };
}


/** Optional research-owned precomputed metrics; never inferred from sparse account curves. */
export interface RankICRecord {
  factorId: string; poolId: string; periodId: string; range: [string, string]; evaluationRange?: [string, string]; horizon: string;
  sourceManifestSha256: string; labelDefinition: string; scoreDirection: string;
  nPeriods: number; minAssets: number; medianAssets: number; coverage: number;
  mean: number | null; uncertainty: { lower: number | null; upper: number | null; method: string };
  points: [string, number | null, number, number][];
  limitations: string;
}
export interface SharpeRecord {
  streamId: string; periodId: string; range: [string, string]; value: number | null;
  frequency: "daily" | "weekly" | "monthly"; observations: number; annualization: number;
  riskFree: { kind: "zero_assumption" | "sourced"; description: string; source: string; sourceDate: string };
  feeBps: number; feesDeducted: boolean; method: string; limitations: string;
}
export interface CurveAssessment { schemaVersion: 1; kind: "factor_predictive_and_account_metrics"; datasetId: string; sourceSummarySha256: string; rankIC: RankICRecord[]; sharpe: SharpeRecord[] }
export function parseAssessment(v: unknown, datasetId: string, summaryHash: string): CurveAssessment {
  const fail = () => { throw new Error("预测与风险收益资料身份、覆盖或计算口径不完整，未展示指标。"); };
  const count = (n: unknown) => typeof n === "number" && Number.isInteger(n) && n >= 0;
  const fraction = (n: unknown) => typeof n === "number" && Number.isFinite(n) && n >= 0 && n <= 1;
  const correlation = (n: unknown) => n === null || typeof n === "number" && Number.isFinite(n) && Math.abs(n) <= 1;
  const range = (r: unknown) => Array.isArray(r) && r.length === 2 && r.every(x => typeof x === "string" && month.test(x)) && r[0] <= r[1];
  if (!object(v) || v.schemaVersion !== 1 || v.kind !== "factor_predictive_and_account_metrics" || v.datasetId !== datasetId || v.sourceSummarySha256 !== summaryHash || !Array.isArray(v.rankIC) || !Array.isArray(v.sharpe)) return fail();
  const keys = new Set<string>();
  for (const r of v.rankIC) {
    if (!object(r) || !text(r.factorId) || !text(r.poolId) || !text(r.periodId) || !range(r.range) || r.evaluationRange !== undefined && !range(r.evaluationRange) || !text(r.horizon) || typeof r.sourceManifestSha256 !== "string" || !/^[a-f0-9]{64}$/.test(r.sourceManifestSha256) || !text(r.labelDefinition) || !text(r.scoreDirection) || !text(r.limitations) || !count(r.nPeriods) || !count(r.minAssets) || !finiteOrNull(r.medianAssets) || typeof r.medianAssets !== "number" || r.medianAssets < (r.minAssets as number) || !fraction(r.coverage) || !correlation(r.mean) || !object(r.uncertainty) || !correlation(r.uncertainty.lower) || !correlation(r.uncertainty.upper) || !text(r.uncertainty.method) || !Array.isArray(r.points)) return fail();
    if (typeof r.uncertainty.lower === "number" && typeof r.uncertainty.upper === "number" && r.uncertainty.lower > r.uncertainty.upper) return fail();
    const key = JSON.stringify([r.factorId, r.poolId, r.periodId, r.horizon]); if (keys.has(key)) return fail(); keys.add(key);
    let previous = ""; let valid = 0; const assetCounts: number[] = [];
    for (const point of r.points) {
      if (!Array.isArray(point) || point.length !== 4 || !day.test(String(point[0])) || point[0] <= previous || point[0].slice(0, 7) < (r.range as string[])[0] || point[0].slice(0, 7) > (r.range as string[])[1] || !correlation(point[1]) || !count(point[2]) || !count(point[3]) || point[2] > point[3]) return fail();
      previous = point[0]; if (point[1] !== null) { if (point[2] < 2) return fail(); valid++; assetCounts.push(point[2]); }
    }
    if (valid !== r.nPeriods || valid === 0 && r.mean !== null) return fail();
    assetCounts.sort((a, b) => a - b);
    if (valid > 0 && (r.minAssets !== assetCounts[0] || r.medianAssets !== (assetCounts[Math.floor((valid - 1) / 2)] + assetCounts[Math.floor(valid / 2)]) / 2)) return fail();
  }
  for (const r of v.sharpe) {
    if (!object(r) || !text(r.streamId) || !text(r.periodId) || !range(r.range) || !finiteOrNull(r.value) || !["daily", "weekly", "monthly"].includes(String(r.frequency)) || !count(r.observations) || typeof r.annualization !== "number" || !Number.isFinite(r.annualization) || r.annualization <= 0 || !object(r.riskFree) || !["zero_assumption", "sourced"].includes(String(r.riskFree.kind)) || !text(r.riskFree.description) || typeof r.riskFree.source !== "string" || typeof r.riskFree.sourceDate !== "string" || (r.riskFree.kind === "sourced" && (!text(r.riskFree.source) || !day.test(r.riskFree.sourceDate))) || typeof r.feeBps !== "number" || !Number.isFinite(r.feeBps) || r.feeBps < 0 || typeof r.feesDeducted !== "boolean" || !text(r.method) || !text(r.limitations)) return fail();
    if (r.value !== null && (r.observations as number) < 2) return fail();
    const key = JSON.stringify([r.streamId, r.periodId]); if (keys.has(key)) return fail(); keys.add(key);
    if (!r.streamId.endsWith(`__fee${r.feeBps}`)) return fail();
  }
  return v as unknown as CurveAssessment;
}
export function assessmentView(dataset: CurveDataset, selection: CurveSelection) {
  const range = dataset.periods[selection.period];
  const matches = (r: {periodId: string; range: [string, string]}) => r.periodId === selection.period && range && r.range[0] === range[0] && r.range[1] === range[1];
  return {
    rankIC: dataset.assessment?.rankIC.filter(r => r.factorId === selection.curveFactor && r.poolId === selection.pool && matches({periodId: r.periodId, range: r.evaluationRange ?? r.range})) ?? [],
    sharpe: dataset.assessment?.sharpe.filter(r => matches(r) && r.feeBps === Number(selection.fee) && (r.streamId === `${selection.pool}__${selection.curveFactor}__G5__fee${selection.fee}` || r.streamId === `${selection.pool}__pool__fee${selection.fee}`)).sort((a, b) => Number(a.streamId.includes("__pool__")) - Number(b.streamId.includes("__pool__"))) ?? [],
  };
}


export type CurveReturnMode = "excess" | "absolute";
export const defaultReturnMode = (params: URLSearchParams): CurveReturnMode => params.get("returnView") === "absolute" ? "absolute" : "excess";
export interface ReturnDisplayPoint extends DisplayPoint {
  absoluteValue: number | null; benchmarkValue: number | null; excessValue: number | null;
  comparisonUncertain: boolean; benchmarkUnknown: number | null; benchmarkUnknownMax: number | null;
}
/** Deterministic display only: cumulative return difference, never a reinvested excess account. */
export function returnDisplay(series: DisplaySeries[], mode: CurveReturnMode) {
  const benchmark = series.find(s => s.id === "pool");
  if (!benchmark?.points.length) throw new Error("同池基准报价未提供，该基准超额未评价。");
  const dates = [...new Set(series.flatMap(s => s.points.map(p => p.date)))].sort();
  const baseline = new Map(benchmark.points.map(p => [p.date, p]));
  const b0 = benchmark.points[0];
  const unknownAnchor = (p: DisplayPoint) => p.unknown === null || p.unknownMax === null || p.unknown > 1e-10;
  const output = series.map(s => {
    const g0 = s.points[0];
    const sameAnchor = Boolean(g0 && g0.date === b0.date && g0.value === 0 && b0.value === 0);
    if (mode === "excess" && !sameAnchor) throw new Error(`${s.label}与同池基准缺少相同起始日，该基准超额未评价；可查看各自绝对收益。`);
    const byDate = new Map(s.points.map(p => [p.date, p]));
    const anchorUncertain = !sameAnchor || unknownAnchor(g0) || unknownAnchor(b0);
    const points: ReturnDisplayPoint[] = dates.map(date => {
      const p = byDate.get(date); const b = baseline.get(date);
      const absoluteValue = p?.value ?? null; const benchmarkValue = b?.value ?? null;
      const excessValue = sameAnchor && absoluteValue !== null && benchmarkValue !== null ? absoluteValue - benchmarkValue : null;
      const comparisonUncertain = anchorUncertain || !p || !b || p.unknown === null || b.unknown === null || p.unknownMax === null || b.unknownMax === null || p.unknown > 1e-10 || b.unknown > 1e-10 || p.unknownMax > 1e-10 || b.unknownMax > 1e-10;
      return { date, value: mode === "excess" ? excessValue : absoluteValue, absoluteValue, benchmarkValue, excessValue,
        drawdown: p?.drawdown ?? null, unknown: p?.unknown ?? null, cash: p?.cash ?? null, unknownMax: p?.unknownMax ?? null,
        comparisonUncertain, benchmarkUnknown: b?.unknown ?? null, benchmarkUnknownMax: b?.unknownMax ?? null };
    });
    return { ...s, points };
  });
  const lastDate = dates[dates.length - 1];
  return { series: output, dates, lastDate, lastG5: output.find(s => s.id === "G5")?.points.find(p => p.date === lastDate) ?? null };
}
