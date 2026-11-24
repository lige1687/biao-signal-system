import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
const result = await build({ entryPoints: [new URL("./erpTrendObservation.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { erpPositionObservation, erpTrendObservation, erpResearchMapping } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);
const series = values => values.map((value, i) => ({ date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10), value }));

test("constant prices separate a zero score from genuine bearish direction via the flat-band state", () => {
  const rows = series(Array(125).fill(100));
  const result = erpTrendObservation(rows, rows.at(-1).date);
  assert.equal(result.score, 0);
  assert.equal(result.spread, 0);
  assert.equal(result.slope, 0);
  assert.equal(result.bandState, "mixed");
});
test("rising prices have independent hand-calculated moving averages and all three conditions", () => {
  const rows = series(Array.from({ length: 125 }, (_, i) => 100 + i));
  const result = erpTrendObservation(rows, rows.at(-1).date);
  assert.equal(result.ma20, 214.5);
  assert.equal(result.ma60, 194.5);
  assert.equal(result.ma120, 164.5);
  assert.equal(result.score, 3);
  assert.equal(result.bandState, "bull");
  assert.ok(Math.abs(result.slope - (194.5 / 189.5 - 1) * 252 / 5) < 1e-12);
});
test("missing prices, stale data and warmup never manufacture a market state", () => {
  const rows = series(Array(125).fill(100));
  assert.equal(erpTrendObservation(rows.slice(1), rows.at(-1).date), null);
  assert.equal(erpTrendObservation(rows, "2026-06-01"), null);
  assert.equal(erpTrendObservation(rows.map((row, i) => i === 50 ? { ...row, value: null } : row), rows.at(-1).date), null);
});
test("future price changes do not affect an earlier dated observation", () => {
  const rows = series(Array.from({ length: 140 }, (_, i) => 100 + i));
  const asOf = rows[124].date;
  assert.deepEqual(erpTrendObservation(rows, asOf), erpTrendObservation(rows.map((row, i) => i > 124 ? { ...row, value: 1e9 } : row), asOf));
});
test("ERP percentile shares the exact rolling window, with midpoint rank for ties", () => {
  const rows = [99, 1, 2, 3].map((value, i) => ({ date: `${2020 + i}-01-01`, value }));
  const result = erpPositionObservation(rows);
  assert.equal(result.n, 3);
  assert.equal(result.mean, 2);
  assert.ok(Math.abs(result.percentile - 5 / 6 * 100) < 1e-12);
  assert.equal(erpPositionObservation(rows.slice(1)), null);
});
test("research mapping preserves matrix edges while continuous weights do not jump at 1.5 sigma", () => {
  assert.equal(erpResearchMapping(-1.5, "mixed").step, 5);
  assert.equal(erpResearchMapping(-1, "mixed").step, 40);
  assert.equal(erpResearchMapping(1.5 - 1e-8, "bear").step, 10);
  assert.equal(erpResearchMapping(1.5, "bear").step, 40);
  assert.ok(Math.abs(erpResearchMapping(1.5 - 1e-8, "bear").continuous - erpResearchMapping(1.5, "bear").continuous) < 1e-5);
  assert.equal(erpResearchMapping(0, "mixed").continuous, 40);
  assert.equal(erpResearchMapping(50, "bull").continuous, 100);
  assert.equal(erpResearchMapping(-50, "bear").continuous, 0);
  assert.equal(erpResearchMapping(null, "mixed"), null);
});
