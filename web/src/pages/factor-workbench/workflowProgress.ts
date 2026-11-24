export const STAGE_IDS = ["meaning", "universe", "data", "definition", "test", "validation", "increment", "decision"] as const;
export type StageId = typeof STAGE_IDS[number];
export type Integrity = "verified" | "changed" | "missing";
export type CaseKind = "factor" | "strategy" | "data" | "reference" | "benchmark";
export type RecordType = "reviewed_research" | "registered_object" | "registered_reference" | "external_reference";
export interface ProgressSource {
  id: string; title: string; path: string; sha256: string; sourceDate: string; locator: string;
  reportPath?: string; status: Integrity; actualSha256?: string;
}
export interface ProgressStage {
  id: StageId; title: string; status: "done" | "partial" | "blocked" | "not_evaluated" | "not_applicable" | "unknown";
  summary: string; missing?: string; nextAction?: string; sourceIds: string[];
}
export interface ProgressCase {
  id: string; kind: CaseKind; title: string; researchVersion: string; definitionRefs: string[];
  recordType?: RecordType; catalogKey?: string; objectType?: string; relatedCaseIds?: string[]; legacyCatalogUrl?: string;
  purpose: string; universe: string; period: string; datasetId?: string; factorId?: string; poolIds: string[];
  execution: { state: "completed" | "blocked" | "paused" | "unknown"; label: string };
  conclusion: { state: "limited" | "unsupported" | "inconclusive" | "not_evaluated" | "unknown"; text: string };
  bottleneck: { scope: "本轮" | "扩大用途"; kind: "data" | "validation" | "definition" | "scope" | "none"; title: string; detail: string; nextAction: string; dependency: string; sourceIds: string[] };
  currentStageId: StageId; stages: ProgressStage[];
  timeline: { date: string; label: string; sourceIds: string[] }[];
  evidenceAsOf: string; sourceIds: string[]; integrity: Integrity; limitations: string[];
}
export interface WorkflowProgressData {
  schemaVersion: 1; reviewedAt: string; checkedAt: string; projectionNote: string;
  catalog?: { total: number; registeredObjects: number; registeredReferences: number; externalReferences: number; reviewedResearchCases: number; linkedObjects: number; issues: string[] };
  sources: ProgressSource[]; cases: ProgressCase[];
  intake?: { reviewedThrough: string; checkedAt: string; items: { path: string; title: string; date: string; category: string; status: "pending_review" }[] };
}

const object = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const str = (value: unknown): value is string => typeof value === "string";
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(str);
const sourceIds = (value: unknown, known: Set<string>): value is string[] => strings(value) && value.every(id => known.has(id));
const inSet = <T extends string>(value: unknown, options: readonly T[]): value is T => options.includes(value as T);
const date = (value: unknown): value is string => str(value) && /^\d{4}-\d{2}-\d{2}$/.test(value);
const iso = (value: unknown): value is string => str(value) && !Number.isNaN(Date.parse(value));
const count = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 0;
const legacyUrl = (value: unknown): value is string => str(value) && /^\/factors(?:\?[^#]*)?$/.test(value);
export const isCatalogRecord = (c: ProgressCase) => c.recordType != null && c.recordType !== "reviewed_research";
export const PAGE_SIZE = 20;
export type EvidenceScope = "all" | "reviewed" | "catalog";
export function filterProgressCases(cases: ProgressCase[], query: string, kind: "all" | CaseKind, scope: EvidenceScope): ProgressCase[] {
  const needle = query.trim().toLocaleLowerCase();
  return cases.filter(c => (kind === "all" || c.kind === kind) && (scope === "all" || (scope === "catalog" ? isCatalogRecord(c) : !isCatalogRecord(c))) &&
    (!needle || [c.id, c.catalogKey, c.objectType, c.title, c.purpose, c.universe, c.researchVersion, c.datasetId, c.factorId, ...c.definitionRefs].some(value => value?.toLocaleLowerCase().includes(needle))));
}

export function parseWorkflowProgress(value: unknown): WorkflowProgressData {
  if (!object(value) || value.schemaVersion !== 1 || !iso(value.reviewedAt) || !iso(value.checkedAt) || !str(value.projectionNote) || !Array.isArray(value.sources) || !Array.isArray(value.cases)) throw new Error("研究进度资料格式不完整，请重新读取。");
  const sources = value.sources;
  if (value.intake != null && (!object(value.intake) || !date(value.intake.reviewedThrough) || !iso(value.intake.checkedAt) || !Array.isArray(value.intake.items) || !value.intake.items.every(item => object(item) && str(item.path) && item.path.startsWith("docs/experiments/") && !item.path.includes("..") && str(item.title) && date(item.date) && str(item.category) && item.status === "pending_review"))) throw new Error("待关联研究资料不完整，请重新读取。");
  if (value.catalog != null && (!object(value.catalog) || !count(value.catalog.total) || !count(value.catalog.registeredObjects) || !count(value.catalog.registeredReferences) || !count(value.catalog.externalReferences) || !count(value.catalog.reviewedResearchCases) || !count(value.catalog.linkedObjects) || !strings(value.catalog.issues))) throw new Error("目录覆盖统计不完整，请重新读取。");
  if (!sources.every(s => object(s) && str(s.id) && str(s.title) && str(s.path) && /^[a-f0-9]{64}$/.test(String(s.sha256)) && date(s.sourceDate) && str(s.locator) && (!s.reportPath || str(s.reportPath)) && inSet(s.status, ["verified", "changed", "missing"]))) throw new Error("研究进度来源资料不完整，请重新读取。");
  const known = new Set(sources.map(s => s.id as string));
  if (known.size !== sources.length) throw new Error("研究进度来源编号重复，请重新核对。");
  const caseIds = new Set<string>();
  for (const c of value.cases) {
    if (!object(c) || !str(c.id) || !inSet(c.kind, ["factor", "strategy", "data", "reference", "benchmark"]) || !str(c.title) || !str(c.researchVersion) || !strings(c.definitionRefs) || (c.recordType != null && !inSet(c.recordType, ["reviewed_research", "registered_object", "registered_reference", "external_reference"])) || (c.catalogKey != null && !str(c.catalogKey)) || (c.objectType != null && !str(c.objectType)) || (c.relatedCaseIds != null && !strings(c.relatedCaseIds)) || (c.legacyCatalogUrl != null && !legacyUrl(c.legacyCatalogUrl)) || !str(c.purpose) || !str(c.universe) || !str(c.period) || (c.datasetId != null && !str(c.datasetId)) || (c.factorId != null && !str(c.factorId)) || !strings(c.poolIds) || !object(c.execution) || !inSet(c.execution.state, ["completed", "blocked", "paused", "unknown"]) || !str(c.execution.label) || !object(c.conclusion) || !inSet(c.conclusion.state, ["limited", "unsupported", "inconclusive", "not_evaluated", "unknown"]) || !str(c.conclusion.text) || !object(c.bottleneck) || !inSet(c.bottleneck.scope, ["本轮", "扩大用途"]) || !inSet(c.bottleneck.kind, ["data", "validation", "definition", "scope", "none"]) || !str(c.bottleneck.title) || !str(c.bottleneck.detail) || !str(c.bottleneck.nextAction) || !str(c.bottleneck.dependency) || !sourceIds(c.bottleneck.sourceIds, known) || !inSet(c.currentStageId, STAGE_IDS) || !Array.isArray(c.stages) || !Array.isArray(c.timeline) || !date(c.evidenceAsOf) || !sourceIds(c.sourceIds, known) || !inSet(c.integrity, ["verified", "changed", "missing"]) || !strings(c.limitations)) throw new Error("研究对象身份或状态资料不完整，请重新读取。");
    if (caseIds.has(c.id)) throw new Error("研究对象编号重复，请重新核对。");
    caseIds.add(c.id);
    const stages = c.stages as unknown[];
    if (stages.length !== STAGE_IDS.length || !STAGE_IDS.every(id => stages.some(s => object(s) && s.id === id)) || !stages.every(s => object(s) && inSet(s.id, STAGE_IDS) && str(s.title) && inSet(s.status, ["done", "partial", "blocked", "not_evaluated", "not_applicable", "unknown"]) && str(s.summary) && (s.missing == null || str(s.missing)) && (s.nextAction == null || str(s.nextAction)) && sourceIds(s.sourceIds, known))) throw new Error("八个研究阶段资料不完整，请重新读取。");
    if (!c.timeline.every(t => object(t) && date(t.date) && str(t.label) && sourceIds(t.sourceIds, known))) throw new Error("研究事件资料不完整，请重新读取。");
  }
  for (const c of value.cases as ProgressCase[]) {
    if (c.relatedCaseIds?.some(id => !caseIds.has(id))) throw new Error("相关研究编号未找到，请重新核对。");
  }
  return value as unknown as WorkflowProgressData;
}

export function progressQuery(params: URLSearchParams) {
  const kind = params.get("wpKind") ?? "all";
  const scope = params.get("wpScope") ?? "reviewed";
  return {
    query: params.get("wpQ") ?? "",
    kind: (["all", "factor", "strategy", "data", "reference", "benchmark"].includes(kind) ? kind : "all") as "all" | CaseKind,
    scope: (["all", "reviewed", "catalog"].includes(scope) ? scope : "reviewed") as EvidenceScope,
    page: Math.max(1, Math.floor(Number(params.get("wpPage"))) || 1),
    selectedId: params.get("wpCase"), stageId: params.get("wpStage"),
    attention: params.get("wpAttention") === "1",
  };
}

export function updateProgressQuery(params: URLSearchParams, changes: Record<string, string | null>) {
  const next = new URLSearchParams(params);
  Object.entries(changes).forEach(([key, value]) => { if (value) next.set(key, value); else next.delete(key); });
  return next;
}

export function handoffText(c: ProgressCase, sources: ProgressSource[]): string {
  return [c.title, `对象版本：${c.definitionRefs.join("、") || c.researchVersion}`,
    `研究范围：${c.universe}；${c.period}`, `卡点：${c.bottleneck.title}`, c.bottleneck.detail,
    `下一动作：${c.bottleneck.nextAction}`, `依赖：${c.bottleneck.dependency}`,
    "负责人/已有任务：尚未绑定，请核对现有任务后认领，避免重复研究。",
    "交付验收：提供能回答上述卡点的可定位证据，记录适用范围、资料日期与限制；经审阅后更新阶段，不自动采用。",
    ...sources.filter(s => c.bottleneck.sourceIds.includes(s.id)).map(s => `原依据：${s.path} · ${s.locator}`)].join("\n");
}

export async function loadWorkflowProgress(signal?: AbortSignal): Promise<WorkflowProgressData> {
  const response = await fetch("/api/factor-workbench/progress", { signal, cache: "no-cache" });
  if (!response.ok) throw new Error(`研究进度暂不可用（HTTP ${response.status}）。`);
  if (!response.headers.get("content-type")?.toLowerCase().includes("application/json")) throw new Error("研究进度返回的不是 JSON 资料。");
  return parseWorkflowProgress(await response.json());
}

export function selectProgressCase(cases: ProgressCase[], selection?: { datasetId: string; factorId: string }): ProgressCase | undefined {
  return cases.find(c => selection && c.datasetId === selection.datasetId && c.factorId === selection.factorId) ?? cases[0];
}

export function caseNeedsRecheck(c: ProgressCase, sources: ProgressSource[]): boolean {
  if (c.integrity !== "verified") return true;
  const ids = new Set([...c.sourceIds, ...c.bottleneck.sourceIds, ...c.stages.flatMap(s => s.sourceIds), ...c.timeline.flatMap(t => t.sourceIds)]);
  return sources.some(s => ids.has(s.id) && s.status !== "verified");
}

export function stageNeedsRecheck(stage: ProgressStage, sources: ProgressSource[], caseStale: boolean): boolean {
  return caseStale || sources.some(s => stage.sourceIds.includes(s.id) && s.status !== "verified");
}
