import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";

const output = await build({ entryPoints: [new URL("./concentrationReferenceMath.ts", import.meta.url).pathname],
  bundle: true, write: false, platform: "node", format: "esm" });
const { priorMonthReference, amountMA20 } = await import(`data:text/javascript;base64,${Buffer.from(output.outputFiles[0].text).toString("base64")}`);

const fixture = JSON.parse(await readFile(new URL("../../../public/research/microstructure-observations-20261108/equity.json", import.meta.url), "utf8"));
const packetPoints = (id) => fixture.cards.find((card) => card.id === id).points;
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} vs ${expected}`);
const monthly = () => Array.from({ length: 61 }, (_, index) => ({
  date: new Date(Date.UTC(2021, index, 25)).toISOString().slice(0, 10),
  value: index === 60 ? 30 : index,
}));

test("packet monthly references exclude October 2026 and match independent quantiles", () => {
  const points = packetPoints("cn-monthly-amount-top5");
  const expected = [
    [120, "2016-10", 119, 76.47058823529412, 40.61088188054348, 42.64618096555953, 44.64405903069018],
    [60, "2021-10", 60, 78.33333333333333, 40.04379457984373, 42.16141454482353, 43.82984839948228],
  ];
  assert.equal(points.at(-1).date, "2026-10-30");
  for (const [months, startMonth, sampleCount, rank, p80, p90, p95] of expected) {
    const reference = priorMonthReference(points, months);
    assert.equal(reference.startMonth, startMonth);
    assert.equal(reference.endMonth, "2026-09");
    assert.equal(reference.sampleCount, sampleCount);
    for (const [key, value] of Object.entries({ rank, p80, p90, p95 })) close(reference[key], value);
  }
});

test("uses calendar months, interpolates Type 7, and does not count ties below the current month", () => {
  const points = monthly();
  const result = priorMonthReference(points, 60);
  assert.equal(result.startMonth, "2021-01");
  assert.equal(result.endMonth, "2025-12");
  assert.equal(result.rank, 50);
  close(result.p80, 47.2);
  close(result.p90, 53.1);
  close(result.p95, 56.05);
  const changed = priorMonthReference([...points.slice(0, -1), { ...points.at(-1), value: 1_000 }], 60);
  assert.equal(changed.rank, 100);
  assert.equal(changed.p95, result.p95);
  assert.equal(priorMonthReference(points.map((point) => ({ ...point, value: 5 })), 60).rank, 0);
});

test("requires full calendar span and 90% coverage, never uses a stale latest value", () => {
  const points = monthly();
  assert.equal(priorMonthReference(points.slice(1), 60), null);
  assert.equal(priorMonthReference(points.map((point, index) => index >= 1 && index <= 6 ? { ...point, value: null } : point), 60).sampleCount, 54);
  assert.equal(priorMonthReference(points.filter((_, index) => index < 1 || index > 6), 60).sampleCount, 54);
  assert.equal(priorMonthReference(points.filter((_, index) => index < 1 || index > 7), 60), null);
  assert.equal(priorMonthReference([...points.slice(0, -1), { ...points.at(-1), value: null }], 60), null);
  assert.equal(priorMonthReference([], 60), null);
});

test("rejects duplicate calendar months and malformed chronological order", () => {
  const points = monthly();
  assert.equal(priorMonthReference([points[0], { ...points[0], date: "2021-01-26" }, ...points.slice(1)], 60), null);
  assert.equal(priorMonthReference([points[1], points[0], ...points.slice(2)], 60), null);
  assert.equal(priorMonthReference([{ ...points[0], date: "2021-01-32" }, ...points.slice(1)], 60), null);
});

test("packet daily references use 20 expected session rows and both match independent sums", () => {
  for (const [id, expected] of [["cn-daily-amount-top5", 42.21085413409806], ["cn-daily-amount-top10", 56.68311007454126]]) {
    const points = packetPoints(id);
    const values = amountMA20(points);
    assert.equal(values.length, points.length);
    assert.deepEqual(values.slice(0, 19), Array(19).fill(null));
    assert.equal(points.at(-20).date, "2026-10-12");
    assert.equal(points.at(-1).date, "2026-11-06");
    close(values.at(-1), expected);
  }
});

test("daily null gaps invalidate every window they touch and later rows never change earlier averages", () => {
  const points = Array.from({ length: 42 }, (_, index) => ({
    date: new Date(Date.UTC(2026, 8, index + 1)).toISOString().slice(0, 10),
    value: index === 20 ? null : index + 1,
  }));
  const values = amountMA20(points);
  assert.equal(values[19], 10.5);
  assert.deepEqual(values.slice(20, 40), Array(20).fill(null));
  assert.equal(values[40], 31.5);
  assert.equal(values[41], 32.5);
  assert.deepEqual(amountMA20(points.slice(0, 20)), values.slice(0, 20));
  assert.deepEqual(amountMA20([...points.slice(0, 20), points[19]]), [...values.slice(0, 20), null]);
});
