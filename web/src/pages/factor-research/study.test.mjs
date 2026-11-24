import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { build } from "esbuild";

const built = await build({ entryPoints: [new URL("./StudyConclusion.tsx", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm", jsx: "automatic" });
const { default: StudyConclusion } = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
const study = (changes = {}) => ({
  id: "study-a", title: "涨跌信息研究", kind: "predictive_study", conclusion: "限定范围有帮助", result: "supported",
  run_status: "completed", review_status: "reviewed", review_summary: "有限复核，不能用于交易",
  products: [{ code: "A", name: "产品甲" }], period: { start: "2024-01-01", end: "2024-12-31" },
  target_horizon: "20日", data_cutoff: "2024-12-31", reviewed_at: "2025-02-01",
  limitations: ["甲的主要限制", "甲的第二限制"],
  sources: [{ path: "docs/experiments/original-a.md", sha256: "a".repeat(64), role: "report" }], ...changes,
});
const render = experiment => renderToStaticMarkup(createElement(StudyConclusion, { experiment, onOpen() {} }));

test("opposite conclusions retain their own products, periods, horizon, cutoff and full limits", () => {
  const first = render(study());
  const second = render(study({ id: "study-b", title: "风险信息研究", conclusion: "没有帮助且风险更差", result: "no_help",
    products: [{ code: "B", name: "产品乙" }], period: { start: "2025-01-01", end: "2025-06-30" },
    target_horizon: "60日", data_cutoff: "2025-06-30", limitations: ["乙的主要限制", "乙的第二限制"] }));
  for (const text of ["限定范围有帮助", "产品甲", "2024-01-01", "20日", "2024-12-31", "甲的主要限制", "甲的第二限制", "2025-02-01"]) assert.ok(first.includes(text), text);
  for (const text of ["没有帮助且风险更差", "产品乙", "2025-01-01", "60日", "2025-06-30", "乙的主要限制", "乙的第二限制"]) assert.ok(second.includes(text), text);
  assert.ok(!first.includes("产品乙") && !first.includes("乙的主要限制"));
  assert.ok(!second.includes("产品甲") && !second.includes("甲的主要限制"));
  assert.ok(first.includes("/library?report="));
});

test("unfinished evidence stays visible with unknown scope rather than a completed claim", () => {
  const html = render(study({ id: "pending", run_status: "running", review_status: "pending", conclusion: "",
    products: [], period: { start: null, end: null }, data_cutoff: null, target_horizon: undefined, reviewed_at: null, limitations: [], sources: [] }));
  for (const text of ["pending", "尚未记录结论", "运行中", "待复核", "资料截至", "未核实", "原接入资料未单列"]) assert.ok(html.includes(text), text);
  assert.ok(!html.includes("限定范围有帮助") && !html.includes("2024-12-31") && !html.includes("已运行"));
});

test("correction retains original conclusion and exposes its status and own source", () => {
  const html = render(study({ correction: { status: "superseded", note: "原结论经资料更正，不再采用", sources: [{ path: "docs/experiments/correction-a.md", sha256: "b".repeat(64) }] }, source_note: "首次核对公式有误，错误记录保留" }));
  for (const text of ["限定范围有帮助", "原结果已被更正替代", "更正状态", "原结论经资料更正，不再采用", "correction-a.md", "original-a.md", "错误记录保留"]) assert.ok(html.includes(text), text);
});

test("unsafe report paths cannot become reading links", () => {
  const html = render(study({ sources: [{ path: "javascript:alert(1)", sha256: "c".repeat(64) }, { path: "docs/experiments/../secret.md", sha256: "d".repeat(64) }] }));
  assert.ok(!html.includes('href="javascript:') && !html.includes('href="/library'));
});
