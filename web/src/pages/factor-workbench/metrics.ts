export interface ICRecord {
  datasetId: string; factorId: string; poolId: string; periodId: string;
  range: [string, string]; nPeriods: number; mean: number | null; icir: number | null;
  icirReason?: string | null; coverage: number | null; labelDefinition: string; horizon: string;
  uncertainty?: { lower?: number | null; upper?: number | null; method?: string } | string | null;
  points: [string, number | null, number, number][];
  rolling: [string, number | null, number | null][];
  limitations: string[];
}
export interface IRRecord {
  datasetId: string; factorId: string; poolId: string; periodId: string; feeBps: number;
  range: [string, string]; nPeriods: number; ir: number | null; trackingError: number | null;
  trackingErrorFrequency?: "monthly"; irAnnualization?: number;
  meanExcess: number | null; reason?: string | null; unknownMax: number | null; feeLabel: string;
  points: [string, number | null, number | null][]; limitations: string[];
}
export interface CorrelationRecord {
  datasetId: string; poolId: string; periodId: string; feeBps: number;
  factorIds: string[]; matrix: (number | null)[][]; counts: number[][];
  kind: "g5_monthly_return"; limitations: string[];
}
export interface WorkbenchMetrics {
  schemaVersion: 1; generatedAt: string;
  sources: { path: string; sha256: string }[];
  icRecords: ICRecord[]; irRecords: IRRecord[]; correlations: CorrelationRecord[];
  methods: unknown; missingCapabilities: unknown;
}

interface WorkbenchManifest { schemaVersion: 1; generatorVersion: 1; dataUrl: string; sha256: string; sources: { path: string; sha256: string }[] }
const METRICS_URL = "/research/factor-workbench-20261024/metrics.json";
const MANIFEST_URL = "/research/factor-workbench-20261024/manifest.json";
const hex64 = /^[a-f0-9]{64}$/;
const isSource = (v: unknown): v is { path: string; sha256: string } => Boolean(v && typeof v === "object" && typeof (v as {path?: unknown}).path === "string" && hex64.test(String((v as {sha256?: unknown}).sha256)));
async function readJsonResponse(url: string, signal?: AbortSignal): Promise<Response> {
  let response: Response;
  try { response = await fetch(url, { signal, cache: "no-cache" }); }
  catch (error) { if (signal?.aborted) throw error; throw new Error("专业指标或来源清单暂无法读取，请稍后重试。"); }
  if (!response.ok) throw new Error(`专业指标或来源清单暂不可用（HTTP ${response.status}）。`);
  if (!response.headers.get("content-type")?.toLowerCase().includes("application/json")) throw new Error("专业指标返回的不是研究 JSON。");
  return response;
}
async function sha256(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("");
}

export async function loadWorkbenchMetrics(signal?: AbortSignal): Promise<WorkbenchMetrics> {
  const manifestResponse = await readJsonResponse(MANIFEST_URL, signal);
  const rawManifest: unknown = await manifestResponse.json();
  const manifest = rawManifest as Partial<WorkbenchManifest>;
  if (!manifest || manifest.schemaVersion !== 1 || manifest.generatorVersion !== 1 || manifest.dataUrl !== METRICS_URL || typeof manifest.sha256 !== "string" || !hex64.test(manifest.sha256) || !Array.isArray(manifest.sources) || !manifest.sources.every(isSource)) throw new Error("专业指标来源清单身份或指纹不完整，暂不展示指标。");
  const catalogSource = manifest.sources.find(source => source.path === "web/public/research/factor-curve-library-20261022/catalog.json");
  if (!catalogSource) throw new Error("专业指标缺少对应资金目录的指纹。");
  const catalogResponse = await readJsonResponse("/research/factor-curve-library-20261022/catalog.json", signal);
  if (await sha256(await catalogResponse.arrayBuffer()) !== catalogSource.sha256) throw new Error("资金资料已更新，专业指标仍是旧版本；请重新生成后查看。");
  const response = await readJsonResponse(METRICS_URL, signal);
  const bytes = await response.arrayBuffer();
  if (await sha256(bytes) !== manifest.sha256) throw new Error("专业指标文件与来源清单指纹不一致，暂不展示指标。");
  let data: unknown;
  try { data = JSON.parse(new TextDecoder().decode(bytes)); }
  catch { throw new Error("专业指标无法解析，暂不展示指标。"); }
  if (!data || typeof data !== "object") throw new Error("专业指标格式不可用。");
  const m = data as Partial<WorkbenchMetrics>;
  if (m.schemaVersion !== 1 || typeof m.generatedAt !== "string" || !Array.isArray(m.icRecords) || !Array.isArray(m.irRecords) || !Array.isArray(m.correlations) || !Array.isArray(m.sources) || !m.sources.every(isSource) || JSON.stringify(m.sources) !== JSON.stringify(manifest.sources)) throw new Error("专业指标版本或来源信息与清单不一致，暂不展示指标。");
  if (!m.icRecords.every(r => r && typeof r.datasetId === "string" && typeof r.factorId === "string" && Array.isArray(r.points) && Array.isArray(r.rolling) && Array.isArray(r.limitations)) || !m.irRecords.every(r => r && typeof r.datasetId === "string" && typeof r.feeBps === "number" && Array.isArray(r.points) && Array.isArray(r.limitations)) || !m.correlations.every(r => r && r.kind === "g5_monthly_return" && Array.isArray(r.matrix) && Array.isArray(r.counts))) throw new Error("专业指标记录格式不完整，暂不展示指标。");
  return m as WorkbenchMetrics;
}

export function matchingMetrics(metrics: WorkbenchMetrics | undefined, selection: { dataset: string; curveFactor: string; pool: string; period: string; fee: string }, range?: [string, string]) {
  const sameIdentity = (r: { datasetId: string; factorId: string; poolId: string; periodId: string }) =>
    r.datasetId === selection.dataset && r.factorId === selection.curveFactor && r.poolId === selection.pool && r.periodId === selection.period;
  const sameAccountRange = (r: { range: [string, string] }) => Boolean(range && r.range?.[0] === range[0] && r.range?.[1] === range[1]);
  return {
    // IC's formation/result coverage may start before the account period's first month.
    ic: metrics?.icRecords.find(sameIdentity),
    ir: metrics?.irRecords.find(r => sameIdentity(r) && sameAccountRange(r) && r.feeBps === Number(selection.fee)),
    correlation: metrics?.correlations.find(r => r.datasetId === selection.dataset && r.poolId === selection.pool && r.periodId === selection.period && r.feeBps === Number(selection.fee)),
  };
}

export const metric = (value: number | null | undefined, decimals = 3) => value == null || !Number.isFinite(value) ? "未评价" : value.toFixed(decimals);
export const pct = (value: number | null | undefined, decimals = 2) => value == null || !Number.isFinite(value) ? "未评价" : `${(value * 100).toFixed(decimals)}%`;

export function sourceHref(path: string): string | null {
  if (path.startsWith("https://")) {
    try { const url = new URL(path); return url.hostname === "github.com" && (url.pathname === "/quantopian/alphalens/blob/master/alphalens/performance.py" || url.pathname === "/microsoft/qlib/blob/main/qlib/contrib/evaluate.py") && !url.search && !url.hash ? url.href : null; }
    catch { return null; }
  }
  if (path.includes("..") || path.includes("\\") || !/^[\w./-]+$/.test(path)) return null;
  if (path.startsWith("docs/")) return `/library?report=${encodeURIComponent(path)}`;
  if (path.startsWith("web/public/research/")) return path.slice("web/public".length);
  if (path.startsWith("/research/") && !path.startsWith("//")) return path;
  return null;
}
