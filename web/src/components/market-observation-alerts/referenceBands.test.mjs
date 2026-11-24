import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const result = await build({ entryPoints: [new URL("./referenceBands.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { priorReferenceBands } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const day = (n) => new Date(Date.UTC(2020, 0, 1 + n)).toISOString().slice(0, 10);

test("prior-only rails use the preceding observations, never the current spike", () => {
  const points = Array.from({ length: 6 }, (_, i) => ({ date: day(i), value: i === 5 ? 100 : i }));
  const bands = priorReferenceBands(points, 5, 5);
  assert.equal(bands.low[4], null);
  assert.equal(bands.latest.low, 0.6);
  assert.equal(bands.latest.high, 3.4);
});

test("a missing observation, repeated date or insufficient window suppresses rails", () => {
  const points = Array.from({ length: 6 }, (_, i) => ({ date: day(i), value: i }));
  assert.equal(priorReferenceBands(points, 7).latest.low, null);
  assert.equal(priorReferenceBands(points.map((p, i) => i === 3 ? { ...p, value: null } : p), 5, 5).latest.low, null);
  assert.equal(priorReferenceBands(points.map((p, i) => i === 3 ? { ...p, date: day(2) } : p), 5, 5).latest.low, null);
});

test("current value must be valid; rails keep the aligned plot length", () => {
  const points = Array.from({ length: 10 }, (_, i) => ({ date: day(i), value: i }));
  const bands = priorReferenceBands(points.map((p, i) => i === 9 ? { ...p, value: null } : p), 5, 5, 3);
  assert.equal(bands.low.length, points.length);
  assert.equal(bands.latest.high, null);
  assert.equal(bands.low[6], null);
  assert.ok(bands.low[7] !== null);
});
