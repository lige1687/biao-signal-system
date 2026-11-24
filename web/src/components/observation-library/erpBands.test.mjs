import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./erpBands.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { erpBands, erpBandPosition, bandDistance } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const points = [0, 1, 2, 3].map((value) => ({ date: `${2020 + value}-01-01`, value }));

test("three calendar years exclude the left boundary, include today, and use population sigma", () => {
  const bands = erpBands(points);
  assert.equal(bands[2].middle, null);
  const row = bands[3];
  assert.equal(row.n, 3);
  assert.equal(row.middle, 2);
  assert.ok(Math.abs(row.sigma - Math.sqrt(2 / 3)) < 1e-12);
  assert.ok(Math.abs(row.upper - (2 + 2 * Math.sqrt(2 / 3))) < 1e-12);
  assert.equal(erpBandPosition(row), "中轨上方");
  assert.equal(bandDistance(row, "upper"), "距上轨 0.63 个百分点");
});

test("future observations cannot change past bands; a displayed crop must retain full-history warmup", () => {
  const before = erpBands(points);
  assert.deepEqual(erpBands([...points, { date: "2024-01-01", value: 100 }]).slice(0, 4), before);
  assert.notEqual(before.slice(3)[0].middle, null);
  assert.equal(erpBands(points.slice(3))[0].middle, null);
});

test("nulls are neither zero-filled nor silently removed from a statistical window", () => {
  const missing = points.map((p, i) => ({ ...p, value: i === 2 ? null : p.value }));
  assert.equal(erpBands(missing)[3].upper, null);
  assert.equal(erpBands([...points, { date: "2024-01-01", value: null }]).at(-1).value, null);
  assert.equal(erpBandPosition(undefined), "轨道历史不足");
});

test("flat series have valid coincident bands and no spurious cheap/expensive or infinite Z", () => {
  const flat = erpBands(points.map((p) => ({ ...p, value: 0 }))).at(-1);
  assert.equal(flat.upper, 0);
  assert.equal(flat.lower, 0);
  assert.equal(flat.z, null);
  assert.equal(erpBandPosition(flat), "窗口内无波动");
});

test("invalid and duplicate dates fail closed; leap-day window is calendar based", () => {
  assert.throws(() => erpBands([...points, points[3]]));
  assert.throws(() => erpBands([{ date: "2026-02-30", value: 1 }]));
  assert.throws(() => erpBands([{ date: "2026-01-01", value: Infinity }]));
  const leap = erpBands([{ date: "2021-02-28", value: 99 }, { date: "2021-03-01", value: 1 }, { date: "2024-02-29", value: 3 }]).at(-1);
  assert.equal(leap.middle, 2);
  assert.equal(leap.n, 2);
});

test("distance is explicit, with no invented near-band threshold", () => {
  const row = { date: "2026-10-30", value: 5, middle: 2, upper: 4, lower: 0, sigma: 1, z: 3, n: 700 };
  assert.match(erpBandPosition(row), /达到上轨/);
  assert.equal(bandDistance(row, "upper"), "超出上轨 1.00 个百分点");
  assert.match(erpBandPosition({ ...row, value: -1 }), /达到下轨/);
});
