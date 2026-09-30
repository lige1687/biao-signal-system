import assert from "node:assert/strict";
import { createRequire, Module } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { build } from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const entry = resolve(here, "../src/components/MarketObservationCards.tsx");
const compiled = await build({
  entryPoints: [entry], bundle: true, platform: "node", format: "cjs",
  write: false, external: ["react", "react/jsx-runtime"], loader: { ".css": "empty" },
});
const compiledModule = new Module(entry);
compiledModule.filename = entry;
compiledModule.paths = Module._nodeModulePaths(dirname(entry));
compiledModule.require = createRequire(entry);
compiledModule._compile(compiled.outputFiles[0].text, entry);
const MarketObservationCards = compiledModule.exports.default;

const base = {
  market: "us", universe: "测试范围", comparison_period: "较上期", published_at: null,
  publication_precision: "unknown", fetched_at: null, source_name: "测试来源",
  source_url: null, source_access: "unverified", definition_version: "test/1",
  history_start: null, history_end: null, observation_count: null, valid_count: null,
  eligible_count: null, reading: "只描述已记录的资料", limitations: [], evidence_refs: [],
};
const response = {
  market: "us", generated_at: "2026-09-30T00:00:00Z", errors: [],
  items: [
    { ...base, metric_id: "unverified", label: "时间未核实", value: 4.2, unit: "%",
      change: 0.3, change_unit: "百分点", observation_date: "2026-09-20",
      quality_status: "time_unverified", quality_reason: "首次发布时间未核实" },
    { ...base, metric_id: "stale", label: "过期资料", value: 18, unit: "指数点",
      change: -2, change_unit: "指数点", observation_date: "2026-08-01",
      quality_status: "stale", quality_reason: "已过期" },
    { ...base, metric_id: "missing", label: "资料缺失", value: null, unit: "%",
      change: null, change_unit: "百分点", observation_date: null,
      quality_status: "missing", quality_reason: "来源没有合格读数" },
  ],
};
const html = renderToStaticMarkup(createElement(MarketObservationCards, { response, title: "观察" }));
assert.match(html, /时间未核实[\s\S]*?4\.2%[\s\S]*?\+0\.3百分点[\s\S]*?截至2026-09-20的历史读数/);
assert.match(html, /过期资料[\s\S]*?18指数点[\s\S]*?截至2026-08-01的历史读数/);
assert.match(html, /资料缺失[\s\S]*?<div class="observation-value">—<\/div>[\s\S]*?来源没有合格读数/);
assert.doesNotMatch(html, /资料缺失[\s\S]*?<div class="observation-value">0%<\/div>/);
console.log("✓ 市场观察卡真实渲染：历史值、缺失值、百分点变化均符合预期");
