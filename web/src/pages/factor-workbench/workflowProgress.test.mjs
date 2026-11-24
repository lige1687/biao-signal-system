import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";

const built = await build({ entryPoints: [new URL("./workflowProgress.ts", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm" });
const m = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
const sha = "a".repeat(64);
const source = { id: "report", title: "原报告", path: "docs/experiments/report.md", sha256: sha, sourceDate: "2026-10-20", locator: "§1", status: "verified" };
const stages = m.STAGE_IDS.map(id => ({ id, title: id, status: "done", summary: "已有记录", sourceIds: ["report"] }));
const progressCase = { id: "one", kind: "factor", title: "示例", researchVersion: "v1", definitionRefs: ["factor@1"], purpose: "验证低频决定", universe: "固定范围", period: "2020-2025", datasetId: "dataset-a", factorId: "factor-a", poolIds: ["pool-a"], execution: { state: "completed", label: "已结案" }, conclusion: { state: "unsupported", text: "未发现改善" }, bottleneck: { scope: "扩大用途", kind: "data", title: "数据缺口", detail: "需新证据", nextAction: "满足条件后补充", dependency: "历史成员", sourceIds: ["report"] }, currentStageId: "decision", stages, timeline: [{ date: "2026-10-20", label: "归档", sourceIds: ["report"] }], evidenceAsOf: "2026-10-20", sourceIds: ["report"], integrity: "verified", limitations: ["固定范围"] };
const fixture = { schemaVersion: 1, reviewedAt: "2026-10-24T09:00:00+08:00", checkedAt: "2026-10-24T09:01:00+08:00", projectionNote: "人工投影", sources: [source], cases: [progressCase] };

test("progress navigation preserves diagnostic context and validates query state", () => {
  const original = new URLSearchParams("dataset=a&pool=liquid&fee=10&period=oos&wpScope=catalog");
  const next = m.updateProgressQuery(original, { wpCase: "one", wpStage: "data", wpQ: "动量" });
  assert.equal(next.get("fee"), "10");
  assert.equal(next.get("pool"), "liquid");
  assert.equal(m.progressQuery(next).stageId, "data");
  assert.equal(m.progressQuery(next).query, "动量");
  assert.equal(m.progressQuery(new URLSearchParams("wpKind=bad&wpScope=bad&wpPage=-1")).scope, "reviewed");
  assert.equal(m.progressQuery(new URLSearchParams("wpPage=-1")).page, 1);
});

test("new report inbox remains pending and rejects unsafe evidence paths", () => {
  const intake = { reviewedThrough: "2026-10-24", checkedAt: fixture.checkedAt, items: [{ path: "docs/experiments/new-2026-10-25.md", title: "新研究", date: "2026-10-25", category: "模块与信号", status: "pending_review" }] };
  assert.equal(m.parseWorkflowProgress({ ...fixture, intake }).cases[0].conclusion.state, "unsupported");
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, intake: { ...intake, items: [{ ...intake.items[0], path: "docs/experiments/../private" }] } }), /待关联/);
});

test("parses complete eight-stage record with separate execution and conclusion", () => {
  const data = m.parseWorkflowProgress(fixture);
  assert.equal(data.cases[0].execution.state, "completed");
  assert.equal(data.cases[0].conclusion.state, "unsupported");
  assert.equal(m.caseNeedsRecheck(data.cases[0], data.sources), false);
  assert.equal(m.selectProgressCase(data.cases, { datasetId: "dataset-a", factorId: "factor-a" }).id, "one");
});

test("rejects unknown evidence and incomplete or duplicate stages", () => {
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, cases: [{ ...progressCase, sourceIds: ["unknown"] }] }), /不完整/);
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, cases: [{ ...progressCase, stages: stages.slice(1) }] }), /八个研究阶段/);
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, cases: [{ ...progressCase, stages: [...stages.slice(0, 7), stages[0]] }] }), /八个研究阶段/);
});

test("changed or missing source invalidates current case and stage display", () => {
  for (const status of ["changed", "missing"]) {
    const sources = [{ ...source, status }];
    assert.equal(m.caseNeedsRecheck(progressCase, sources), true);
    assert.equal(m.stageNeedsRecheck(stages[0], sources, false), true);
  }
  assert.equal(m.caseNeedsRecheck({ ...progressCase, integrity: "changed" }, [source]), true);
});

test("selection uses both dataset and factor; no match falls back to first", () => {
  const second = { ...progressCase, id: "two", datasetId: "dataset-b", factorId: "factor-b" };
  assert.equal(m.selectProgressCase([progressCase, second], { datasetId: "dataset-b", factorId: "factor-b" }).id, "two");
  assert.equal(m.selectProgressCase([progressCase, second], { datasetId: "dataset-b", factorId: "factor-a" }).id, "one");
  assert.equal(m.selectProgressCase([], { datasetId: "dataset-b", factorId: "factor-b" }), undefined);
});

test("accepts the complete catalog identity while keeping older records valid", () => {
  const catalogCase = { ...progressCase, id: "catalog:factor@2", kind: "benchmark", recordType: "registered_object", catalogKey: "factor@2", objectType: "benchmark", relatedCaseIds: ["one"], sourceIds: ["report"] };
  const catalog = { total: 1, registeredObjects: 1, registeredReferences: 0, externalReferences: 0, reviewedResearchCases: 1, linkedObjects: 1, issues: [] };
  const data = m.parseWorkflowProgress({ ...fixture, cases: [progressCase, catalogCase], catalog });
  assert.equal(data.catalog.total, 1);
  assert.equal(m.isCatalogRecord(data.cases[0]), false);
  assert.equal(m.isCatalogRecord(data.cases[1]), true);
  assert.deepEqual(m.filterProgressCases(data.cases, "factor@2", "all", "catalog").map(c => c.id), [catalogCase.id]);
  assert.equal(m.filterProgressCases(data.cases, "", "all", "reviewed").length, 1);
});

test("rejects malformed catalog fields and broken exact related IDs", () => {
  const catalogCase = { ...progressCase, id: "catalog:factor@2", recordType: "registered_object", catalogKey: "factor@2", relatedCaseIds: ["one"] };
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, catalog: { total: "2" } }), /目录覆盖统计/);
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, cases: [{ ...catalogCase, relatedCaseIds: ["missing"] }] }), /相关研究编号/);
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, cases: [{ ...catalogCase, relatedCaseIds: "one" }] }), /不完整/);
  assert.throws(() => m.parseWorkflowProgress({ ...fixture, cases: [{ ...catalogCase, legacyCatalogUrl: "https://example.com/factors" }] }), /不完整/);
  assert.equal(m.parseWorkflowProgress({ ...fixture, cases: [{ ...catalogCase, legacyCatalogUrl: "/factors?tab=catalog&factor=factor%402" }, progressCase] }).cases[0].legacyCatalogUrl, "/factors?tab=catalog&factor=factor%402");
});

test("filters by exact identity fields and leaves pagination capacity bounded", () => {
  const cases = Array.from({ length: 593 }, (_, index) => ({ ...progressCase, id: `catalog:${index}`, recordType: "external_reference", catalogKey: `ref:${index}`, title: `参考 ${index}` }));
  assert.equal(m.filterProgressCases(cases, "ref:592", "reference", "catalog").length, 0);
  assert.equal(m.filterProgressCases(cases, "ref:592", "all", "catalog")[0].id, "catalog:592");
  assert.equal(m.PAGE_SIZE, 20);
  assert.equal(Math.ceil(cases.length / m.PAGE_SIZE), 30);
});
