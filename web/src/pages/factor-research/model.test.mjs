import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { transform } from "esbuild";

const source = await readFile(new URL("./model.ts", import.meta.url), "utf8");
const compiled = await transform(source, { loader: "ts", format: "esm" });
const model = await import(`data:text/javascript;base64,${Buffer.from(compiled.code).toString("base64")}`);
const item = (reference, extra = {}) => ({ id: reference.split("@")[0], reference, name: reference, category: "趋势", purpose: "观察道路", scope: "ETF", asset_classes: ["ETF"], research: { stage: "historical", result: "no_help" }, ...extra });

test("filters combine text, asset, category, stage and result without mutating items", () => {
  const items = [item("a@1"), item("a@2", { asset_classes: ["个股"] }), item("b@1", { category: "风险", research: { stage: "unbound", result: "unknown" } })];
  const query = { query: "A@1", asset: "ETF", category: "趋势", stage: "historical", result: "no_help" };
  assert.deepEqual(model.filterItems(items, query).map(x => x.reference), ["a@1"]);
  assert.equal(items.length, 3);
  assert.deepEqual(model.filterItems(items, { ...query, result: "supported" }), []);
});

test("registered use codes have plain-language display", () => {
  assert.equal(model.purposeText("ranking、description、research_signal"), "比较排序、描述现状、研究条件");
  assert.equal(model.purposeText("观察市场状态"), "观察市场状态");
});

test("old snapshot notice uses actual API date with seven calendar day boundary", () => {
  const now = new Date("2026-09-23T08:00:00+08:00");
  assert.equal(model.isOldSnapshot("2026-09-04", now), true);
  assert.equal(model.isOldSnapshot("2026-09-22", now), false);
  assert.equal(model.isOldSnapshot(null, now), null);
});

test("uncertain run and project states stay uncertain in the UI", () => {
  assert.equal(model.runLabels.unknown, "运行情况未核实");
  assert.equal(model.projectStageLabels.insufficient, "证据不足");
  assert.equal(model.limitationText("limited_frozen_sources"), "来源范围仅限已冻结材料");
  assert.equal(model.limitationText("其他限制"), "其他限制");
  assert.equal(model.stageLabels.unbound, "待接入证据");
  assert.equal(model.resultLabels.unknown, "结论未核明");
});

test("numbers preserve missing and distinguish difference points from returns", () => {
  assert.equal(model.formatValue(null, "fraction"), "未记录");
  assert.equal(model.formatValue(Number.NaN, "fraction"), "未记录");
  assert.equal(model.formatValue(0, "fraction"), "0.00 个百分点");
  assert.equal(model.formatValue(-0.0019735335, "fraction"), "-0.20 个百分点");
  assert.equal(model.formatValue(0.1234, "return_fraction"), "12.34%");
  assert.equal(model.formatValue(0.020823, "ratio"), "0.0208");
});

test("report links accept only report library root markdown", () => {
  assert.equal(model.safeReportHref("docs/experiments/factor-example-2026-09-23.md"), "/library?report=docs%2Fexperiments%2Ffactor-example-2026-09-23.md");
  for (const path of ["docs/experiments/raw/a.md", "docs/experiments/../x.md", "https://evil.test/x.md", "docs\\experiments\\x.md", "docs/experiments/x.md?y=1"]) assert.equal(model.safeReportHref(path), null);
});

test("URL changes preserve filters for back, refresh and deep links", () => {
  const first = new URLSearchParams("tab=catalog&q=momentum&asset=ETF");
  const detail = model.nextSearchParams(first, { factor: "mixed.momentum.raw@1.0.0" });
  assert.equal(detail.get("q"), "momentum");
  assert.equal(detail.get("factor"), "mixed.momentum.raw@1.0.0");
  assert.equal(first.get("factor"), null);
  const back = model.nextSearchParams(detail, { factor: null });
  assert.equal(back.get("factor"), null);
  assert.equal(back.get("asset"), "ETF");
});

test("counts deduplicate IDs, versions and only sourced completed experiments", () => {
  const items = [item("a@1"), item("a@2"), item("b@1")];
  const experiments = [{ id: "e1", run_status: "completed", sources: [{}] }, { id: "e1", run_status: "completed", sources: [{}] }, { id: "e2", run_status: "not_run", sources: [{}] }, { id: "e3", run_status: "completed", sources: [] }];
  assert.deepEqual(model.catalogCounts(items, experiments), { factor_objects: 2, definition_versions: 3, executed_experiments: 1 });
});

test("one object card keeps every version and shows the newest matching version", () => {
  const versions = [item("trend.x@1.9.0", { version: "1.9.0", name: "旧定义" }), item("trend.x@1.10.0", { version: "1.10.0", name: "新定义" }), item("other@1.0.0", { version: "1.0.0" })];
  const all = model.groupCatalog(versions, model.emptyFilters);
  assert.equal(all.length, 2);
  assert.equal(all.find(x => x.id === "trend.x").item.reference, "trend.x@1.10.0");
  assert.deepEqual(all.find(x => x.id === "trend.x").versions.map(x => x.version), ["1.10.0", "1.9.0"]);
  const old = model.groupCatalog(versions, { ...model.emptyFilters, query: "旧定义" });
  assert.equal(old.length, 1);
  assert.equal(old[0].item.reference, "trend.x@1.9.0");
  assert.deepEqual(old[0].matchingVersions.map(x => x.reference), ["trend.x@1.9.0"]);
  assert.equal(model.compareVersions("2.0.0", "1.10.0") > 0, true);
});

test("category counts use object IDs and Chinese width names are searchable", () => {
  const width = item("breadth.all_a.b50.common@1.0.0", { version: "1.0.0", name: "all_a B50共同分母（比例）", category: "宽度" });
  const anotherVersion = { ...width, reference: "breadth.all_a.b50.common@2.0.0", version: "2.0.0" };
  assert.equal(model.categoryObjectCounts([width, anotherVersion]).宽度, 1);
  assert.equal(model.readableFactorName(width), "全A 站上50日均线共同分母（比例）");
  assert.equal(model.filterItems([width], { ...model.emptyFilters, query: "全A" }).length, 1);
});

test("sorting uses evidence stage or readable name, without changing research result", () => {
  const historical = item("z@1.0.0", { version: "1.0.0", name: "历史", research: { stage: "historical", result: "no_help", evidence_date: "2026-09-01" } });
  const unbound = item("a@1.0.0", { version: "1.0.0", name: "未绑定", research: { stage: "unbound", result: "unknown", evidence_date: null } });
  const groups = model.groupCatalog([unbound, historical], model.emptyFilters);
  assert.deepEqual(model.sortCatalog(groups, "evidence").map(x => x.id), ["z", "a"]);
  assert.deepEqual(model.sortCatalog(groups, "date").map(x => x.id), ["z", "a"]);
  assert.deepEqual(model.sortCatalog(groups, "name").map(x => x.id), ["z", "a"]);
  assert.equal(historical.research.result, "no_help");
});

test("pagination clamps stale URL page and retains twelve objects per page", () => {
  const rows = Array.from({ length: 25 }, (_, index) => ({ id: `x${index}` }));
  assert.deepEqual([model.paginateCatalog(rows, 1).rows.length, model.paginateCatalog(rows, 2).rows.length, model.paginateCatalog(rows, 3).rows.length], [12, 12, 1]);
  assert.equal(model.paginateCatalog(rows, 999).page, 3);
  assert.equal(model.paginateCatalog(rows, Number.NaN).page, 1);
  assert.equal(model.paginateCatalog([], 9).pages, 1);
});

test("view, sort, page, and exact version survive URL round trip", () => {
  const query = model.nextSearchParams(new URLSearchParams("tab=catalog&q=%E5%85%A8A"), { sort: "name", view: "list", page: "2", factor: "trend.x@1.0.0" });
  const restored = new URLSearchParams(query.toString());
  assert.deepEqual([restored.get("tab"), restored.get("q"), restored.get("sort"), restored.get("view"), restored.get("page"), restored.get("factor")], ["catalog", "全A", "name", "list", "2", "trend.x@1.0.0"]);
  const reset = model.nextSearchParams(restored, { q: "动量", page: null, factor: null });
  assert.equal(reset.get("page"), null);
  assert.equal(reset.get("view"), "list");
});

test("reading guides bind only exact versions, including both versions of one object", async () => {
  const document = JSON.parse(await readFile(new URL("./reading-guidance.json", import.meta.url), "utf8"));
  const snapshot = JSON.parse(await readFile(new URL("./catalog.generated.json", import.meta.url), "utf8"));
  const lookup = model.indexGuides(document);
  assert.equal(document.schema_version, "factor-reading/1");
  assert.equal(lookup.size, snapshot.items.length);
  for (const card of snapshot.items) assert.ok(lookup.has(card.reference), `missing ${card.reference}`);
  const old = lookup.get("trend.cost_basis_distance20@1.0.0");
  const newer = lookup.get("trend.cost_basis_distance20@2.0.0");
  assert.ok(old && newer);
  assert.notEqual(old, newer);
  assert.equal(lookup.get("trend.cost_basis_distance20@3.0.0"), undefined);
});

test("guide text and plain name are searchable without borrowing a newer version", () => {
  const old = item("x@1.0.0", { version: "1.0.0", name: "技术旧名" });
  const newer = item("x@2.0.0", { version: "2.0.0", name: "技术新名" });
  const lookup = model.indexGuides({ schema_version: "factor-reading/1", note: "", guides: [
    { references: ["x@1.0.0"], plain_name: "旧版白话名", watch: "观察旧定义", read: "旧版读法", context: [], pitfall: "旧版误读", source_refs: [], verification_scope: "定义阅读" },
    { references: ["x@2.0.0"], plain_name: "新版白话名", watch: "观察新定义", read: "新版读法", context: [], pitfall: "新版误读", source_refs: [], verification_scope: "定义阅读" },
  ] });
  assert.deepEqual(model.groupCatalog([old, newer], { ...model.emptyFilters, query: "旧版读法" }, lookup).map(x => x.item.reference), ["x@1.0.0"]);
  assert.deepEqual(model.groupCatalog([old, newer], { ...model.emptyFilters, query: "新版白话名" }, lookup).map(x => x.item.reference), ["x@2.0.0"]);
  assert.equal(model.displayFactorName(old, lookup), "旧版白话名");
  assert.equal(model.displayFactorName(old, model.emptyGuides), "技术旧名");
  assert.deepEqual(model.filterItems([old, newer], { ...model.emptyFilters, query: "x@1.0.0" }, lookup).map(x => x.reference), ["x@1.0.0"]);
});

test("visual tones come only from exact category and status enumerations", () => {
  assert.equal(model.categoryTone("风险"), "risk");
  assert.equal(model.categoryTone("未知类别"), "neutral");
  assert.equal(model.stageTone("historical"), "history");
  assert.equal(model.stageTone("unbound"), "quiet");
  assert.equal(model.resultTone("no_help"), "attention");
  assert.equal(model.resultTone("unknown"), "quiet");
  assert.equal(model.reviewTone("partial"), "attention");
  assert.equal(model.reviewTone("reviewed"), "history");
});

test("metric profiles prefer exact definition version over category guidance", () => {
  const guidance = { schema_version: "factor-metrics/1", profiles: [
    { id: "category", title: "风险通用", categories: ["风险"], checks: [] },
    { id: "account", title: "账户占比", references: ["risk.weight@1.0.0"], checks: [] },
  ], account_metrics: [] };
  assert.equal(model.metricProfileFor(item("risk.weight@1.0.0", { category: "风险" }), guidance).id, "account");
  assert.equal(model.metricProfileFor(item("risk.weight@2.0.0", { category: "风险" }), guidance).id, "category");
});

test("linked evidence and card preview never borrow another definition version", () => {
  const target = item("x@1.0.0", { experiment_ids: ["old", "new"] });
  const experiments = [
    { id: "old", references: ["x@1.0.0"], run_status: "completed", kind: "predictive_study", metrics: [{ label: "相关", value: 0, unit: "ratio" }] },
    { id: "new", references: ["x@2.0.0"], run_status: "completed", kind: "predictive_study", metrics: [{ label: "相关", value: 0.9, unit: "ratio" }] },
  ];
  assert.deepEqual(model.linkedExperiments(target, experiments).map(x => x.id), ["old"]);
  assert.deepEqual(model.cardMetricEvidence(target, experiments).map(x => x.metric.value), [0]);
  assert.equal(model.formatValue(0, "ratio"), "0.0000");
  assert.equal(model.formatValue(null, "return_fraction"), "未记录");
  assert.equal(model.formatValue(12.5, "currency_CNY"), "12.5 currency_CNY");
});

test("account values require a completed account experiment and exact metric label", () => {
  const specs = [{ id: "net", label: "净年化", meaning: "账户", source_labels: ["完整账户扣费后年化收益"] }];
  const base = { references: ["x@1.0.0"], run_status: "completed", metrics: [{ label: "完整账户扣费后年化收益", value: 0, unit: "return_fraction" }] };
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "strategy_backtest" }, "x@1.0.0")[0].status, "available");
  assert.equal(model.formatValue(model.accountMetricRows(specs, { ...base, kind: "strategy_backtest" }, "x@1.0.0")[0].metric.value, "return_fraction"), "0.00%");
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "price_description" }, "x@1.0.0")[0].status, "not_calculated");
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "predictive_study" }, "x@1.0.0")[0].metric, null);
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "strategy_backtest" }, "x@2.0.0")[0].status, "no_backtest");
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "strategy_backtest", run_status: "running" }, "x@1.0.0")[0].status, "not_completed");
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "strategy_backtest", metrics: [{ label: "年化收益", value: 0.2, unit: "return_fraction" }] }, "x@1.0.0")[0].status, "not_reported");
  assert.equal(model.accountMetricRows(specs, { ...base, kind: "strategy_backtest", metrics: [{ label: "完整账户扣费后年化收益", value: null, unit: "return_fraction" }] }, "x@1.0.0")[0].status, "not_reported");
  assert.equal(model.accountMetricRows(specs, null, "x@1.0.0")[0].status, "no_backtest");
});

test("dossier section survives URLs and resets when the selected version changes", () => {
  const detail = model.nextSearchParams(new URLSearchParams("tab=catalog&factor=x%401.0.0&q=%E5%8A%A8%E9%87%8F"), { section: "strategy" });
  assert.equal(model.dossierSection(new URLSearchParams(detail.toString()).get("section")), "strategy");
  assert.equal(model.dossierSection("unexpected"), "overview");
  const newer = model.nextSearchParams(detail, { factor: "x@2.0.0", section: null });
  assert.equal(model.dossierSection(newer.get("section")), "overview");
  assert.equal(newer.get("q"), "动量");
});

test("exact source selectors preserve zero and never borrow another version or null-only values", () => {
  const selected = item("x@1.0.0", { version: "1.0.0", experiment_ids: ["old", "new"], input: "价格", time: "收盘后", sources: [] });
  const experiments = [
    { id: "old", title: "旧版研究", references: ["x@1.0.0"], metrics: [{ label: "净年化", value: 0, unit: "return_fraction" }, { label: "空值", value: null, unit: "ratio" }], sample: [{ label: "样本", value: 0, unit: "count" }], result_tables: [{ title: "按观察年", columns: [{ key: "year" }], rows: [{ year: "2021" }] }], products: [], period: { start: "2021-01-01", end: "2021-12-31" }, review_status: "partial", sources: [] },
    { id: "new", title: "新版研究", references: ["x@2.0.0"], metrics: [{ label: "新版专属", value: 0.9, unit: "ratio" }], sample: [], result_tables: [{ title: "新版表", columns: [], rows: [{}] }], products: [], period: {}, sources: [] },
  ];
  const check = { id: "test", label: "数值与来源", why: "需要核对", sources: { metric_labels: ["净年化", "空值", "新版专属"], sample_labels: ["样本"], table_titles: ["按观察年", "新版表"], definition_fields: ["input", "sources", "__proto__"], experiment_fields: ["period", "review_status", "__proto__"] } };
  const evidence = model.checkEvidence(selected, experiments, check);
  assert.ok(evidence.some(entry => entry.kind === "metric" && entry.label.includes("0.00%")));
  assert.ok(evidence.some(entry => entry.kind === "sample" && entry.label.includes("0")));
  assert.ok(evidence.some(entry => entry.kind === "table" && entry.label.includes("按观察年")));
  assert.ok(evidence.some(entry => entry.label.includes("观察期：2021-01-01 至 2021-12-31")));
  assert.ok(evidence.every(entry => !entry.label.includes("新版") && !entry.label.includes("空值") && !entry.label.includes("__proto__")));
  assert.ok(evidence.every(entry => !("passed" in entry)));
  assert.deepEqual(model.checkEvidence(selected, experiments, { id: "missing", label: "专项", why: "", sources: { metric_labels: ["新版专属"], table_titles: ["新版表"] } }), []);
});

test("period table availability never claims stability or treats arbitrary tables as yearly", () => {
  const selected = item("x@1.0.0", { version: "1.0.0", input: "", time: "", purpose: "ranking", object_type: "feature", sources: [], experiment_ids: ["e"], limitations: [], research: { stage: "historical", result: "no_help", evidence_date: "2026-01-01" } });
  const base = { id: "e", title: "研究", references: ["x@1.0.0"], metrics: [], sample: [], kind: "predictive_study", run_status: "completed", review_status: "partial", result_tables: [{ title: "结果", columns: [{ key: "group" }], rows: [{ group: "A" }] }], limitations: [] };
  const before = model.dossierFacts(selected, [base], false).find(fact => fact.id === "stability");
  assert.equal(before.label, "待接入逐期资料");
  const after = model.dossierFacts(selected, [{ ...base, result_tables: [{ title: "逐年", columns: [{ key: "year" }], rows: [{ year: "2021" }] }] }], false).find(fact => fact.id === "stability");
  assert.equal(after.label, "有逐期原表");
  assert.ok(after.have[0].includes("不裁定稳定"));
});

test("assessment framework has eight dimensions and distinct exact check identities", async () => {
  const framework = JSON.parse(await readFile(new URL("./assessment-framework.json", import.meta.url), "utf8"));
  assert.equal(framework.schema_version, "factor-assessment/1");
  assert.deepEqual(framework.topics.map(topic => topic.id), ["purpose", "data", "effect", "stability", "robustness", "implementation", "incremental", "governance"]);
  const checks = framework.topics.flatMap(topic => topic.checks);
  assert.equal(new Set(checks.map(check => check.id)).size, checks.length);
  assert.equal(checks.length, 39);
});

test("historical result enums become bounded, readable conclusions", () => {
  const expected = [
    ["no_help", "本次研究未发现帮助", "attention"],
    ["conditional", "仅在部分条件下有线索", "attention"],
    ["supported", "已研究范围内有支持", "history"],
    ["insufficient", "证据不足，暂不能判断", "attention"],
    ["not_evaluated", "效果暂不能判断", "quiet"],
    ["unknown", "效果暂不能判断", "quiet"],
  ];
  for (const [result, headline, tone] of expected) {
    const actual = model.factorOutcome(item("x@1.0.0", { research: { stage: "historical", result, summary: "任意原文" } }));
    assert.equal(actual.headline, headline);
    assert.equal(actual.tone, tone);
    assert.ok(actual.explanation.length > 5);
    assert.ok(!actual.explanation.includes("任意原文"));
  }
});

test("nonhistorical stages gate conflicting positive and negative result labels", () => {
  const stages = [
    ["unresearched", "尚未做历史研究"],
    ["calculation_only", "只验证了计算，效果未知"],
    ["unbound", "暂缺可展示的研究结论"],
    ["in_progress", "研究中，尚无结论"],
    ["insufficient", "证据不足，暂不能判断"],
  ];
  for (const [stage, headline] of stages) {
    for (const result of ["supported", "no_help"]) {
      const actual = model.factorOutcome(item("x@1.0.0", { research: { stage, result } }));
      assert.equal(actual.headline, headline);
      assert.notEqual(actual.tone, "history");
    }
  }
  const unresearched = model.factorOutcome(item("x@1.0.0", { research: { stage: "unresearched", result: "no_help" } }));
  assert.ok(unresearched.explanation.includes("无法判断"));
  assert.ok(!unresearched.explanation.includes("无效"));
});

test("unknown stage and result fall back without inventing an outcome", () => {
  const unknownStage = model.factorOutcome(item("x@1.0.0", { research: { stage: "future_stage", result: "supported" } }));
  const unknownResult = model.factorOutcome(item("x@1.0.0", { research: { stage: "historical", result: "future_result" } }));
  assert.equal(unknownStage.headline, "效果暂不能判断");
  assert.equal(unknownResult.headline, "效果暂不能判断");
  assert.equal(unknownStage.tone, "quiet");
});
