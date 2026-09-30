export type Source = { path: string; sha256: string; role?: string };
export type ResearchStage = "unresearched" | "calculation_only" | "historical" | "in_progress" | "insufficient" | "unbound";
export type ResearchResult = "not_evaluated" | "insufficient" | "no_help" | "conditional" | "supported" | "unknown";
export type FactorItem = {
  reference: string; id: string; version: string; name: string; object_type: string;
  category: string; purpose: string; scope: string; formula: string; unit: string;
  input: string; time: string; asset_classes: string[];
  calculation: { status: string; scope: string };
  research: { stage: ResearchStage; result: ResearchResult; summary: string; evidence_date: string | null };
  limitations: string[]; next_steps: string[]; experiment_ids: string[]; sources: Source[];
};
export type Experiment = {
  id: string; title: string; kind: string; run_status: string; review_status: string;
  review_summary: string; conclusion: string; result: string; baseline: string; costs: string;
  references: string[]; products: { code: string; name: string }[];
  period: { start: string | null; end: string | null };
  data_cutoff: string | null; run_at: string | null; reviewed_at: string | null;
  sample: { label: string; value: number | null; unit: string }[];
  metrics: { label: string; value: number | null; unit: string; meaning: string }[];
  result_tables: { title: string; columns: { key: string; label: string; unit: string }[]; rows: Record<string, string | number | null>[]; note: string }[];
  limitations: string[]; next_steps: string[]; sources: Source[];
};
export type Project = { id: string; title: string; stage: string; summary: string; review_status: string; references: string[]; evidence_date: string | null; sources: Source[]; limitations: string[]; next_steps: string[] };
export type Snapshot = {
  schema_version: "factor-research/1"; generated_at: string; registry_version: string;
  sources: Source[]; counts: { factor_objects: number; definition_versions: number; executed_experiments: number };
  limitations: string[]; items: FactorItem[]; experiments: Experiment[]; projects: Project[];
};
export type ReadingGuide = {
  references: string[]; plain_name: string; watch: string; read: string;
  context: string[]; pitfall: string; source_refs: string[]; verification_scope: string;
};
export type ReadingGuidance = { schema_version: "factor-reading/1"; note: string; guides: ReadingGuide[] };
export type GuideLookup = ReadonlyMap<string, ReadingGuide>;
export const emptyGuides: GuideLookup = new Map<string, ReadingGuide>();
export type MetricProfile = { id: string; title: string; references?: string[]; categories?: string[]; checks: { label: string; why: string }[] };
export type AccountMetricSpec = { id: string; label: string; meaning: string; source_labels: string[] };
export type MetricsGuidance = { schema_version: "factor-metrics/1"; note?: string; source_refs?: string[]; profiles: MetricProfile[]; account_metrics: AccountMetricSpec[] };
export type DossierSection = "overview" | "evidence" | "strategy" | "definition";
export type AssessmentTopicId = "purpose" | "data" | "effect" | "stability" | "robustness" | "implementation" | "incremental" | "governance";
export type AssessmentSources = { metric_labels?: string[]; sample_labels?: string[]; table_titles?: string[]; experiment_fields?: string[]; definition_fields?: string[] };
export type AssessmentCheck = { id: string; label: string; why: string; sources?: AssessmentSources };
export type AssessmentTopic = { id: AssessmentTopicId; title: string; question: string; section: DossierSection; checks: AssessmentCheck[]; missing: string[] };
export type AssessmentFramework = { schema_version: "factor-assessment/1"; note: string; source_refs: string[]; topics: AssessmentTopic[] };
export type DossierFact = { id: AssessmentTopicId; have: string[]; missing: string[]; label: string };
export type CheckEvidence = { kind: "definition" | "experiment" | "metric" | "sample" | "table"; label: string; experimentId?: string };

const definitionFields: Record<string, keyof FactorItem> = {
  reference: "reference", version: "version", object_type: "object_type", category: "category", purpose: "purpose",
  scope: "scope", formula: "formula", unit: "unit", input: "input", time: "time", calculation: "calculation",
  limitations: "limitations", next_steps: "next_steps", sources: "sources",
};
const experimentFields: Record<string, keyof Experiment> = {
  baseline: "baseline", costs: "costs", metrics: "metrics", sample: "sample", result_tables: "result_tables",
  products: "products", period: "period", data_cutoff: "data_cutoff", run_at: "run_at", reviewed_at: "reviewed_at",
  run_status: "run_status", review_status: "review_status", review_summary: "review_summary",
  limitations: "limitations", next_steps: "next_steps", sources: "sources",
};
const definitionFieldLabels: Record<string, string> = {
  reference: "精确身份", version: "版本", object_type: "对象类型", category: "用途类别", purpose: "定义用途",
  scope: "适用范围", formula: "公式", unit: "单位", input: "输入口径", time: "可用时间口径",
  calculation: "计算核对范围", limitations: "定义限制", next_steps: "后续工作", sources: "来源文件",
};
const experimentFieldLabels: Record<string, string> = {
  baseline: "固定对照", costs: "费用与成交口径", metrics: "数值指标", sample: "样本读数", result_tables: "结果原表",
  products: "研究产品", period: "观察期", data_cutoff: "资料截止日", run_at: "运行日期", reviewed_at: "复核日期",
  run_status: "运行状态", review_status: "复核状态", review_summary: "复核说明",
  limitations: "实验限制", next_steps: "后续工作", sources: "来源文件",
};
function hasRecordedValue(value: unknown): boolean {
  if (value == null || value === "") return false;
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.values(value).some(hasRecordedValue);
  return true;
}
function hasExperimentField(experiment: Experiment, field: string): boolean {
  if (field === "metrics") return experiment.metrics.some(metric => hasRecordedValue(metric.value));
  if (field === "sample") return experiment.sample.some(sample => hasRecordedValue(sample.value));
  if (field === "result_tables") return experiment.result_tables.some(table => table.rows.length > 0);
  const key = experimentFields[field];
  return Boolean(key && hasRecordedValue(experiment[key]));
}
const brief = (value: string, limit = 95) => value.length > limit ? `${value.slice(0, limit)}…` : value;
function definitionPreview(item: FactorItem, field: string): string {
  if (field === "input" || field === "formula") return "原文见定义与数据页";
  if (field === "sources") return `${item.sources.length} 项文件来源，指纹见定义与数据页`;
  if (field === "calculation") return brief(`${calculationLabels[item.calculation.status] ?? "核对情况未知"}；${item.calculation.scope}`);
  if (field === "object_type") return typeLabels[item.object_type] ?? item.object_type;
  if (field === "purpose") return purposeText(item.purpose);
  if (field === "limitations" || field === "next_steps") return brief((item[field] as string[]).join("；"));
  return brief(String(item[definitionFields[field]]));
}
function experimentPreview(experiment: Experiment, field: string): string {
  if (field === "period") return `${experiment.period.start ?? "起点未记录"} 至 ${experiment.period.end ?? "终点未记录"}`;
  if (field === "products") return brief(experiment.products.map(product => product.name && product.name !== product.code ? `${product.name}（${product.code}）` : product.code).join("、"));
  if (field === "metrics") return `${experiment.metrics.filter(metric => hasRecordedValue(metric.value)).length} 项有数值指标，见本实验原表`;
  if (field === "sample") return `${experiment.sample.filter(sample => hasRecordedValue(sample.value)).length} 项样本读数，见本实验原表`;
  if (field === "result_tables") return brief(experiment.result_tables.filter(table => table.rows.length).map(table => table.title).join("、"));
  if (field === "sources") return `${experiment.sources.length} 项来源，指纹见实验详情`;
  if (field === "run_status") return runLabels[experiment.run_status] ?? experiment.run_status;
  if (field === "review_status") return reviewLabels[experiment.review_status] ?? experiment.review_status;
  if (field === "limitations" || field === "next_steps") return brief((experiment[field] as string[]).join("；"));
  return brief(String(experiment[experimentFields[field]]));
}

export function checkEvidence(item: FactorItem, experiments: Experiment[], check: AssessmentCheck): CheckEvidence[] {
  const source = check.sources;
  if (!source) return [];
  const found: CheckEvidence[] = [];
  for (const field of source.definition_fields ?? []) {
    if (!Object.prototype.hasOwnProperty.call(definitionFields, field)) continue;
    const key = definitionFields[field];
    if (hasRecordedValue(item[key])) found.push({ kind: "definition", label: `正式定义 · ${definitionFieldLabels[field]}：${definitionPreview(item, field)}` });
  }
  for (const experiment of linkedExperiments(item, experiments)) {
    for (const field of source.experiment_fields ?? []) {
      if (!Object.prototype.hasOwnProperty.call(experimentFields, field) || !hasExperimentField(experiment, field)) continue;
      found.push({ kind: "experiment", label: `${experiment.title} · ${experimentFieldLabels[field]}：${experimentPreview(experiment, field)}`, experimentId: experiment.id });
    }
    for (const metric of experiment.metrics) if ((source.metric_labels ?? []).includes(metric.label) && hasRecordedValue(metric.value)) found.push({ kind: "metric", label: `${experiment.title}：${metric.label} ${formatValue(metric.value, metric.unit)}`, experimentId: experiment.id });
    for (const sample of experiment.sample) if ((source.sample_labels ?? []).includes(sample.label) && hasRecordedValue(sample.value)) found.push({ kind: "sample", label: `${experiment.title}：${sample.label} ${formatValue(sample.value, sample.unit)}`, experimentId: experiment.id });
    for (const table of experiment.result_tables) if ((source.table_titles ?? []).includes(table.title) && table.rows.length > 0) found.push({ kind: "table", label: `${experiment.title}：${table.title}（${table.rows.length} 行原表）`, experimentId: experiment.id });
  }
  return found;
}

export function dossierSection(raw: string | null): DossierSection {
  return raw === "evidence" || raw === "strategy" || raw === "definition" ? raw : "overview";
}

export function dossierFacts(item: FactorItem, experiments: Experiment[], hasReadingGuide: boolean): DossierFact[] {
  const linked = linkedExperiments(item, experiments);
  const periodTables = linked.reduce((count, experiment) => count + experiment.result_tables.filter(table => table.rows.length > 0 && table.columns.some(column => column.key === "period" || column.key === "year")).length, 0);
  const metrics = linked.reduce((count, experiment) => count + experiment.metrics.filter(metric => metric.value !== null && Number.isFinite(metric.value)).length, 0);
  const samples = linked.reduce((count, experiment) => count + experiment.sample.length, 0);
  const account = linked.filter(experiment => experiment.run_status === "completed" && (experiment.kind === "strategy_backtest" || experiment.kind === "portfolio_comparison"));
  const comparisons = linked.filter(experiment => experiment.kind === "portfolio_comparison");
  return [
    { id: "purpose", have: [`定义用途：${purposeText(item.purpose)}；类别：${item.category}；类型：${typeLabels[item.object_type] ?? item.object_type}`, ...(hasReadingGuide ? ["本版本已有通俗读法与误读提示"] : [])], missing: hasReadingGuide ? ["用途解释不等于效果验证"] : ["本版本通俗读法待补；用途解释不等于效果验证"], label: hasReadingGuide ? "有定义与读法" : "有定义口径" },
    { id: "data", have: [`${item.input || item.time ? "已登记输入与何时可用的定义口径，原文见定义与数据" : "输入与时间口径未记录"}`, ...(samples ? [`关联实验原表提供 ${samples} 项样本读数，需分别查看分母和单位`] : [])], missing: ["定义要求与样本读数不能直接证明历史资料当时可用或覆盖完整"], label: samples ? "有定义与样本读数" : item.input || item.time ? "有定义口径" : "待接入数据口径" },
    { id: "effect", have: [`权威研究状态：${stageLabels[item.research.stage] ?? "阶段未核明"}；结论：${resultLabels[item.research.result] ?? "结论未核明"}`, ...(metrics ? [`${linked.length} 项精确版本关联实验提供 ${metrics} 个数值指标，效果须按各实验原结论阅读`] : [])], missing: metrics ? ["这些数值不能单独证明可交易收益"] : ["本版本暂无已接入量化效果数值"], label: metrics ? "有实验数值" : "待接入效果数值" },
    { id: "stability", have: periodTables ? [`已接入 ${periodTables} 张原实验逐期结果表；逐期表本身不裁定稳定`] : ["本版本未接入有实际时期行的结果表"], missing: ["逐期原表不等于逐产品或市场阶段稳定性的结论"], label: periodTables ? "有逐期原表" : "待接入逐期资料" },
    { id: "robustness", have: linked.length ? [`${linked.length} 项关联实验保留复核状态与原限制说明`] : item.limitations.length ? ["定义保留自身限制与后续事项"] : ["本版本暂无关联实验复核摘要"], missing: ["复核状态和原限制说明不代替未参与选择资料或参数变化的专项检验"], label: "专项检验待逐项核" },
    { id: "implementation", have: account.length ? [`${account.length} 项已运行完整策略或组合实验可逐项查看原指标`] : ["本版本尚无已接入的完整账户结果"], missing: ["账户净收益、跌幅、恢复、换手、费用与可成交性须按同一完整实验逐项核对；价格研究不能替代"], label: account.length ? "有账户实验" : "待接入账户回测" },
    { id: "incremental", have: comparisons.length ? [`${comparisons.length} 项组合对照实验已关联；其类型不代表增量效果全部完成`] : ["本版本未关联组合对照实验"], missing: ["组合实验类型不代表重复信息、增量净值与执行代价都已核清"], label: comparisons.length ? "有组合实验记录" : "待接入组合证据" },
    { id: "governance", have: [`精确版本 ${item.reference}；${linked.length} 项关联实验；${item.sources.length} 项定义来源`, ...(item.research.evidence_date ? [`研究证据日期 ${item.research.evidence_date}`] : [])], missing: ["运行和复核状态须逐项查看；来源存在不代表研究通过"], label: item.sources.length ? "有版本与来源" : "有版本，来源待接入" },
  ];
}

export function metricProfileFor(item: FactorItem, guidance: MetricsGuidance): MetricProfile | null {
  if (guidance.schema_version !== "factor-metrics/1") return null;
  return guidance.profiles.find(profile => profile.references?.includes(item.reference))
    ?? guidance.profiles.find(profile => profile.categories?.includes(item.category)) ?? null;
}

export function linkedExperiments(item: FactorItem, experiments: Experiment[]): Experiment[] {
  return item.experiment_ids.flatMap(id => {
    const experiment = experiments.find(candidate => candidate.id === id && candidate.references.includes(item.reference));
    return experiment ? [experiment] : [];
  });
}

export function cardMetricEvidence(item: FactorItem, experiments: Experiment[], limit = 2): { experiment: Experiment; metric: Experiment["metrics"][number] }[] {
  return linkedExperiments(item, experiments)
    .filter(experiment => experiment.run_status === "completed")
    .flatMap(experiment => experiment.metrics.filter(metric => metric.value !== null && Number.isFinite(metric.value)).map(metric => ({ experiment, metric })))
    .slice(0, Math.max(0, limit));
}

export type AccountMetricRow = { spec: AccountMetricSpec; metric: Experiment["metrics"][number] | null; status: "available" | "not_reported" | "no_backtest" | "not_calculated" | "not_completed" };
export function accountMetricRows(specs: AccountMetricSpec[], experiment: Experiment | null, reference?: string): AccountMetricRow[] {
  const accountKind = experiment?.kind === "strategy_backtest" || experiment?.kind === "portfolio_comparison";
  const matchingVersion = Boolean(!reference || experiment?.references.includes(reference));
  const eligible = Boolean(experiment && accountKind && experiment.run_status === "completed" && matchingVersion);
  const missing: AccountMetricRow["status"] = !experiment || !matchingVersion ? "no_backtest" : !accountKind ? "not_calculated" : experiment.run_status !== "completed" ? "not_completed" : "not_reported";
  return specs.map(spec => {
    const metric = eligible ? experiment!.metrics.find(candidate => spec.source_labels.includes(candidate.label) && candidate.value !== null && Number.isFinite(candidate.value)) ?? null : null;
    return { spec, metric, status: metric ? "available" : eligible ? "not_reported" : missing };
  });
}

export function indexGuides(document: ReadingGuidance): GuideLookup {
  if (document.schema_version !== "factor-reading/1" || !Array.isArray(document.guides)) throw new Error("阅读说明格式不受支持");
  const lookup = new Map<string, ReadingGuide>();
  for (const guide of document.guides) {
    if (!Array.isArray(guide.references)) continue;
    for (const reference of guide.references) {
      if (typeof reference !== "string" || !/^[\w.-]+@\d+\.\d+\.\d+(?:-[\w.-]+)?$/.test(reference)) continue;
      if (lookup.has(reference)) throw new Error(`阅读说明重复绑定：${reference}`);
      lookup.set(reference, guide);
    }
  }
  return lookup;
}

export function displayFactorName(item: FactorItem, guides: GuideLookup = emptyGuides): string {
  return guides.get(item.reference)?.plain_name?.trim() || readableFactorName(item);
}
export type Filters = { query: string; asset: string; category: string; stage: string; result: string };
export const emptyFilters: Filters = { query: "", asset: "", category: "", stage: "", result: "" };
export const stageLabels: Record<ResearchStage, string> = {
  unresearched: "明确未研究", calculation_only: "仅核对计算", historical: "已有历史研究",
  in_progress: "研究进行中", insufficient: "证据不足", unbound: "待接入证据",
};
export const resultLabels: Record<ResearchResult, string> = {
  not_evaluated: "尚未评价效果", insufficient: "证据不足", no_help: "本次未见帮助",
  conditional: "有条件线索", supported: "限定范围内支持", unknown: "结论未核明",
};
export const typeLabels: Record<string, string> = {
  feature: "数值描述", state_signal: "状态条件", risk_metric: "风险指标", factor_return: "收益序列",
};
export const kindLabels: Record<string, string> = {
  calculation_check: "计算核对", price_description: "历史价格描述", predictive_study: "历史关系研究",
  strategy_backtest: "完整策略回测", portfolio_comparison: "组合对照",
};
export const reviewLabels: Record<string, string> = { draft: "草稿", pending: "待复核", partial: "限定复核", reviewed: "已复核" };
export const runLabels: Record<string, string> = { not_run: "尚未运行", running: "运行中", completed: "已运行", failed: "运行失败", unknown: "运行情况未核实" };
export const calculationLabels: Record<string, string> = { verified: "已有计算核对", exists: "已有定义或实现", draft: "草稿", unknown: "核对情况未知" };
export const projectStageLabels: Record<string, string> = { in_progress: "进行中", draft: "方案草稿", pending: "待启动", completed: "已结束", insufficient: "证据不足" };
export type DisplayTone = "history" | "neutral" | "quiet" | "attention";
export type FactorOutcome = { headline: string; explanation: string; tone: DisplayTone };

export function factorOutcome(item: FactorItem): FactorOutcome {
  const stage = item.research?.stage;
  const result = item.research?.result;
  // A result label can describe historical effectiveness only when the authoritative stage is historical.
  switch (stage) {
    case "unresearched":
      return { headline: "尚未做历史研究", explanation: "还没有对应的历史研究结果，暂时无法判断是否有帮助。", tone: "quiet" };
    case "calculation_only":
      return { headline: "只验证了计算，效果未知", explanation: "计算核对不能回答它在实际研究用途上是否有帮助。", tone: "neutral" };
    case "unbound":
      return { headline: "暂缺可展示的研究结论", explanation: "本页尚无对应这个精确版本的结论，不能据此判断有效或无效。", tone: "quiet" };
    case "in_progress":
      return { headline: "研究中，尚无结论", explanation: "这项研究还在进行，目前不能判断它是否有帮助。", tone: "attention" };
    case "insufficient":
      return { headline: "证据不足，暂不能判断", explanation: "现有证据还不足以回答它是否有帮助。", tone: "attention" };
    case "historical":
      switch (result) {
        case "no_help":
          return { headline: "本次研究未发现帮助", explanation: "在已研究的范围内没有看到帮助，不代表所有时期和产品都无效。", tone: "attention" };
        case "conditional":
          return { headline: "仅在部分条件下有线索", explanation: "已研究结果只显示有条件的线索，不能推广到所有情况。", tone: "attention" };
        case "supported":
          return { headline: "已研究范围内有支持", explanation: "已有历史结果支持所研究的用途，不代表其他范围或完整账户也成立。", tone: "history" };
        case "insufficient":
          return { headline: "证据不足，暂不能判断", explanation: "已有历史研究材料，但证据还不足以判断是否有帮助。", tone: "attention" };
        default:
          return { headline: "效果暂不能判断", explanation: "已有历史研究记录，但登记结果还不能说明是否有帮助。", tone: "quiet" };
      }
    default:
      return { headline: "效果暂不能判断", explanation: "当前研究阶段未核明，不能据此判断是否有帮助。", tone: "quiet" };
  }
}

export type CategoryTone = "relative" | "trend" | "pullback" | "risk" | "breadth" | "neutral";
export function categoryTone(category: string): CategoryTone {
  const tones: Record<string, CategoryTone> = { 相对强弱: "relative", 趋势: "trend", 回调位置: "pullback", 风险: "risk", 宽度: "breadth" };
  return tones[category] ?? "neutral";
}
export function stageTone(stage: string): DisplayTone {
  if (stage === "historical") return "history";
  if (stage === "in_progress" || stage === "insufficient") return "attention";
  if (stage === "calculation_only") return "neutral";
  return "quiet";
}
export function resultTone(result: string): DisplayTone {
  if (result === "supported") return "history";
  if (result === "insufficient" || result === "no_help" || result === "conditional") return "attention";
  return "quiet";
}
export function reviewTone(status: string): DisplayTone {
  if (status === "reviewed") return "history";
  if (status === "partial" || status === "pending") return "attention";
  return "quiet";
}
const limitationLabels: Record<string, string> = { limited_frozen_sources: "来源范围仅限已冻结材料" };
export function limitationText(value: string): string { return limitationLabels[value] ?? value; }
export function statusText(raw: string, labels: Record<string, string>): string {
  return labels[raw] ?? `未知（原记录：${raw || "空"}）`;
}
export function isOldSnapshot(dataAsOf: string | null | undefined, now = new Date()): boolean | null {
  if (!dataAsOf || !/^\d{4}-\d{2}-\d{2}$/.test(dataAsOf)) return null;
  const at = new Date(`${dataAsOf}T00:00:00+08:00`);
  if (!Number.isFinite(at.getTime())) return null;
  return now.getTime() - at.getTime() > 7 * 24 * 60 * 60 * 1000;
}
export function formatGeneratedAt(raw: string): string {
  const time = new Date(raw);
  if (!Number.isFinite(time.getTime())) return raw || "未记录";
  return new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(time);
}
const useLabels: Record<string, string> = {
  description: "描述现状", ranking: "比较排序", research_signal: "研究条件",
  attribution: "解释收益或风险", comparison: "作为对照", diagnostic: "核对算法或资料",
};
export function purposeText(value: string): string {
  const pieces = value.split(/[、,，]/).map(x => x.trim()).filter(Boolean);
  if (pieces.length && pieces.every(x => useLabels[x])) return pieces.map(x => useLabels[x]).join("、");
  return value;
}

export function filterItems(items: FactorItem[], filters: Filters, guides: GuideLookup = emptyGuides): FactorItem[] {
  const q = filters.query.trim().toLocaleLowerCase("zh-CN");
  return items.filter(item =>
    (!filters.asset || item.asset_classes.includes(filters.asset)) &&
    (!filters.category || item.category === filters.category) &&
    (!filters.stage || item.research.stage === filters.stage) &&
    (!filters.result || item.research.result === filters.result) &&
    (!q || [item.name, displayFactorName(item, guides), readableFactorName(item), item.reference, item.purpose, item.scope, item.category,
      guides.get(item.reference)?.watch, guides.get(item.reference)?.read, ...(guides.get(item.reference)?.context ?? []), guides.get(item.reference)?.pitfall]
      .filter(Boolean).join(" ").toLocaleLowerCase("zh-CN").includes(q))
  );
}

export type CatalogGroup = { id: string; item: FactorItem; versions: FactorItem[]; matchingVersions: FactorItem[] };
export type CatalogSort = "evidence" | "date" | "name";

export function compareVersions(a: string, b: string): number {
  const parse = (v: string) => /^(\d+)\.(\d+)\.(\d+)(?:-([\w.-]+))?$/.exec(v);
  const av = parse(a), bv = parse(b);
  if (!av || !bv) return a.localeCompare(b, "zh-CN", { numeric: true });
  for (let i = 1; i <= 3; i++) {
    const d = Number(av[i]) - Number(bv[i]);
    if (d) return d;
  }
  if (!av[4] && bv[4]) return 1;
  if (av[4] && !bv[4]) return -1;
  return (av[4] ?? "").localeCompare(bv[4] ?? "", "zh-CN", { numeric: true });
}

export function groupCatalog(items: FactorItem[], filters: Filters, guides: GuideLookup = emptyGuides): CatalogGroup[] {
  const matched = new Set(filterItems(items, filters, guides).map(item => item.reference));
  const all = new Map<string, FactorItem[]>();
  for (const item of items) all.set(item.id, [...(all.get(item.id) ?? []), item]);
  return [...all.entries()].flatMap(([id, cards]) => {
    const versions = [...cards].sort((a, b) => compareVersions(b.version, a.version));
    const matchingVersions = versions.filter(item => matched.has(item.reference));
    return matchingVersions.length ? [{ id, item: matchingVersions[0], versions, matchingVersions }] : [];
  });
}

const evidenceOrder: Record<ResearchStage, number> = {
  historical: 5, in_progress: 4, insufficient: 3, calculation_only: 2,
  unresearched: 1, unbound: 0,
};
export function sortCatalog(groups: CatalogGroup[], mode: CatalogSort, guides: GuideLookup = emptyGuides): CatalogGroup[] {
  return [...groups].sort((a, b) => {
    const byName = displayFactorName(a.item, guides).localeCompare(displayFactorName(b.item, guides), "zh-CN") || a.id.localeCompare(b.id);
    if (mode === "name") return byName;
    const byDate = (b.item.research.evidence_date ?? "").localeCompare(a.item.research.evidence_date ?? "");
    if (mode === "date") return byDate || byName;
    return (evidenceOrder[b.item.research.stage] - evidenceOrder[a.item.research.stage]) || byDate || byName;
  });
}

export function paginateCatalog(groups: CatalogGroup[], requestedPage: number, pageSize = 12) {
  const pages = Math.max(1, Math.ceil(groups.length / pageSize));
  const page = Number.isSafeInteger(requestedPage) ? Math.min(pages, Math.max(1, requestedPage)) : 1;
  return { page, pages, total: groups.length, rows: groups.slice((page - 1) * pageSize, page * pageSize) };
}

export function categoryObjectCounts(items: FactorItem[]): Record<string, number> {
  const groups = groupCatalog(items, emptyFilters);
  const counts: Record<string, number> = {};
  for (const group of groups) counts[group.item.category] = (counts[group.item.category] ?? 0) + 1;
  return counts;
}

export function readableFactorName(item: FactorItem): string {
  if (!item.id.startsWith("breadth.")) return item.name;
  return item.name.replace(/^all_a\b/, "全A").replace(/^csi300\b/, "沪深300").replace(/^chinext\b/, "创业板")
    .replace(/B50/g, "站上50日均线").replace(/B200/g, "站上200日均线");
}

export function formatValue(value: number | string | null, unit: string): string {
  if (value == null || value === "" || (typeof value === "number" && !Number.isFinite(value))) return "未记录";
  if (typeof value === "string") return value;
  if (unit === "fraction") return `${(value * 100).toFixed(2)} 个百分点`;
  if (unit === "return_fraction" || unit === "percent_fraction") return `${(value * 100).toFixed(2)}%`;
  if (unit === "percent") return `${value.toFixed(2)}%`;
  if (unit === "ratio" || unit === "IC" || unit === "rank_ic" || unit === "none") return value.toFixed(4);
  if (unit === "integer" || unit === "count" || unit === "day" || unit === "days") return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(value) + (unit === "day" || unit === "days" ? " 日" : "");
  return `${Number(value.toFixed(4))}${unit ? ` ${unit}` : ""}`;
}

export function safeReportHref(path: string): string | null {
  if (!/^docs\/experiments\/[^/\\]+\.md$/.test(path) || path.includes("..") || /[?#]/.test(path)) return null;
  return `/library?report=${encodeURIComponent(path)}`;
}

export function nextSearchParams(current: URLSearchParams, changes: Record<string, string | null>): URLSearchParams {
  const next = new URLSearchParams(current);
  for (const [key, value] of Object.entries(changes)) {
    if (value) next.set(key, value);
    else next.delete(key);
  }
  return next;
}

export function catalogCounts(items: FactorItem[], experiments: Experiment[]) {
  return {
    factor_objects: new Set(items.map(item => item.id)).size,
    definition_versions: new Set(items.map(item => item.reference)).size,
    executed_experiments: new Set(experiments.filter(e => e.run_status === "completed" && e.sources.length > 0).map(e => e.id)).size,
  };
}
