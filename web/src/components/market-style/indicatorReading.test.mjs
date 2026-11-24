import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { readFileSync } from "node:fs";

const result = await build({ entryPoints: [new URL("./indicatorReading.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { recentDelta, historicalPosition } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const day = (n) => new Date(Date.UTC(2020, 0, 1 + n)).toISOString().slice(0, 10);

test("20-record comparison reports both dates and percentage-point difference", () => {
  const points = Array.from({ length: 21 }, (_, i) => ({ date: day(i), value: 2 + i * .01 }));
  const reading = recentDelta(points, 20);
  assert.equal(reading.previous.date, day(0));
  assert.equal(reading.current.date, day(20));
  assert.ok(Math.abs(reading.difference - .2) < 1e-10);
});

test("midrank excludes current and needs a complete prior window", () => {
  const points = Array.from({ length: 5 }, (_, i) => ({ date: day(i), value: i === 4 ? 2 : i + 1 }));
  assert.equal(historicalPosition(points, 4), 37.5);
  assert.equal(historicalPosition(points, 5), null);
});

test("missing, duplicated and unordered records cannot silently become comparisons", () => {
  const points = Array.from({ length: 21 }, (_, i) => ({ date: day(i), value: i }));
  assert.equal(recentDelta(points.map((p, i) => i === 10 ? { ...p, value: null } : p), 20), null);
  assert.equal(recentDelta(points.map((p, i) => i === 10 ? { ...p, date: day(9) } : p), 20), null);
  assert.equal(historicalPosition(points.map((p, i) => i === 10 ? { ...p, date: "bad" } : p), 20), null);
  assert.equal(historicalPosition(points.map((p, i) => i === 10 ? { ...p, date: "2020-02-30" } : p), 20), null);
});

test("calendar rollover is rejected even when dates stay ordered", () => {
  assert.equal(recentDelta([{ date: "2020-02-28", value: 1 }, { date: "2020-02-30", value: 2 }, { date: "2020-03-03", value: 3 }], 2), null);
});

test("dated local margin and focus snapshots produce the displayed comparisons", () => {
  const rates = JSON.parse(readFileSync(new URL("../../../../docs/experiments/raw/cross-market-risk-context-2026-11-02/rates-api-snapshot.json", import.meta.url)));
  const ratio = rates.series.margin_rzyezb.dates.map((date, i) => ({ date, value: rates.series.margin_rzyezb.values[i] }));
  const ratioDelta = recentDelta(ratio, 20);
  assert.equal(ratioDelta.previous.date, "2026-09-24");
  assert.equal(ratioDelta.current.value, 2.63);
  assert.ok(Math.abs(ratioDelta.difference + .02) < 1e-10);
  assert.ok(Math.abs(historicalPosition(ratio, 756) - 87.3015873015873) < 1e-10);

  const base = JSON.parse(readFileSync(new URL("../../../public/research/focus-momentum/observation.v1.json", import.meta.url)));
  const continuation = JSON.parse(readFileSync(new URL("../../../public/research/focus-momentum/continuation.v1.json", import.meta.url)));
  const focus = [...base.series, ...continuation.series].map((point) => ({ date: point.date, value: point.focus * 100 }));
  const focusDelta = recentDelta(focus, 20);
  assert.equal(focusDelta.previous.date, "2026-09-28");
  assert.ok(Math.abs(focusDelta.difference + 4.188696397030808) < 1e-10);
  assert.ok(Math.abs(historicalPosition(focus, 756) - 3.9682539682539684) < 1e-10);
});
