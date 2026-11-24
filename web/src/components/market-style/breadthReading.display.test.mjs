import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { build } from "esbuild";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const bundle = await build({ entryPoints: [new URL("./BreadthReading.tsx", import.meta.url).pathname],
  bundle: true, format: "cjs", platform: "node", packages: "external", write: false });
const compiled = { exports: {} };
new Function("require", "module", "exports", bundle.outputFiles[0].text)(createRequire(import.meta.url), compiled, compiled.exports);
const Reading = compiled.exports.default;
const render = (props = {}) => renderToStaticMarkup(React.createElement(Reading, {
  date: "2026-10-30", horizon: "50", onHorizonChange: () => {}, ...props,
}));
const stats = { lower: 10, median: 50, upper: 80, percentile: 0, delta_5: 0, sample_count: 300, status: "ready", position: "low", event: "stay_low" };
const reading = { date: "2026-10-30", horizons: { "20": stats, "50": stats, "200": stats },
  state: { code: "flat", label: "参与暂稳", summary: "上游提供的描述", tone: "neutral" } };

test("missing current date cannot inherit a prior state or render a zero reading", () => {
  const html = render();
  assert.match(html, /当日宽度缺失/);
  assert.match(html, /不能沿用此前读数/);
  assert.doesNotMatch(html, /0\.0%|上涨参与延续|低位修复<\/h3>/);
});

test("valid zeros remain visible and state is exactly the supplied backend description", () => {
  const html = render({ point: { breadth_20: 0, breadth_50: 0, breadth_200: null }, reading });
  assert.match(html, /0\.0%/);
  assert.match(html, /历史百分位 0\.0/);
  assert.match(html, /上游提供的描述/);
  assert.doesNotMatch(html, /已确认底部|买入|卖出/);
});

test("a warmup reading does not render invented bands", () => {
  const warmup = { ...stats, lower: null, median: null, upper: null, percentile: null, sample_count: 30, status: "insufficient", position: "unknown", event: "unknown" };
  const html = render({ point: { breadth_50: 20 }, reading: { ...reading, horizons: { ...reading.horizons, "50": warmup } } });
  assert.match(html, /历史不足 30\/252/);
  assert.doesNotMatch(html, /bc-track-values/);
});
