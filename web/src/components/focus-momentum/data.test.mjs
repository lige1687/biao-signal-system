import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseFocusMomentumObservation } from "./data.ts";

const saved = JSON.parse(readFileSync(new URL("../../../public/research/focus-momentum/observation.v1.json", import.meta.url), "utf8"));

test("saved historical observation matches the UI contract", () => {
  const data = parseFocusMomentumObservation(saved);
  assert.equal(data.current, null);
  assert.equal(data.asOf, data.series.at(-1).date);
  assert.equal(data.latest.members.length, data.latest.focusCount);
});

test("bad historical values cannot become a zero reading", () => {
  assert.throws(() => parseFocusMomentumObservation({ ...saved, current: { focus: 0 } }), /历史状态/);
  assert.throws(() => parseFocusMomentumObservation({ ...saved, latest: { ...saved.latest, focus: null } }), /数值无效/);
  assert.throws(() => parseFocusMomentumObservation({ ...saved, series: [{ ...saved.series[0], breadth: 2 }, ...saved.series.slice(1)] }), /比例超出范围/);
  assert.throws(() => parseFocusMomentumObservation({ ...saved, asOf: "2026-10-25" }), /不一致/);
});

test("mapping preserves aligned mature outcomes and its unconditional benchmark", () => {
  const { mapping } = parseFocusMomentumObservation(saved);
  assert.equal(mapping.horizonSessions, 20);
  assert.equal(mapping.targets[0].points.length, 560);
  assert.deepEqual(mapping.targets[0].points.map(p => p.date), mapping.targets[1].points.map(p => p.date));
  assert.equal(mapping.targets[0].points.at(-1).labelEnd, "2026-01-13");
  assert.equal(mapping.us.status, "unavailable");
  assert.ok(Math.abs(mapping.targets[0].baselineMean - 0.006399868638126265) < 1e-12);
});

test("mapping rejects misleading axes, dates, and baselines", () => {
  for (const mutate of [
    data => { data.mapping.targets[0].points[0].focus = 100; },
    data => { data.mapping.targets[0].points[0].labelEnd = data.mapping.targets[0].points[0].date; },
    data => { data.mapping.targets[0].baselineMean = 0.1; },
    data => { data.mapping.targets[0].points[0].forwardReturn = null; },
  ]) {
    const data = structuredClone(saved);
    mutate(data);
    assert.throws(() => parseFocusMomentumObservation(data), /映射|数值无效/);
  }
});
