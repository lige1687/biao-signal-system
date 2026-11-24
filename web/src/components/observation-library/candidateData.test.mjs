import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";
const b = await build({ entryPoints: [new URL("./candidateData.ts", import.meta.url).pathname], bundle: true,
  format: "esm", platform: "node", write: false });
const { parseCandidateHistory, fromCandidateHistory, parseSmallcapSnapshot, fromSmallcapSnapshot } =
  await import(`data:text/javascript;base64,${Buffer.from(b.outputFiles[0].text).toString("base64")}`);
const history = JSON.parse(await readFile(new URL("../../../public/research/observation-candidates/history.v1.json", import.meta.url)));

test("real history binds dates, units and coverage; missing final value stays missing", () => {
  const d = parseCandidateHistory(history);
  const points = d.series["downside-price-impact"].points;
  assert.equal(points.length, 2623);
  assert.equal(points.filter(p => p.value !== null).length, 2604);
  assert.equal(fromCandidateHistory(d, "downside-price-impact").date, "2026-10-23");
  const missing = structuredClone(d);
  missing.series["downside-price-impact"].points.at(-1).value = null;
  const reading = fromCandidateHistory(parseCandidateHistory(missing), "downside-price-impact");
  assert.equal(reading.value, null);
  assert.equal(reading.change, null);
  assert.equal(reading.date, "2026-10-23");
});

test("reject wrong units, dates, coverage and current claims", () => {
  for (const mutate of [d => { d.current = 1; }, d => { d.asOf = "2026-02-30"; },
    d => { d.series["salience-str"].unit = "%"; },
    d => { d.series["salience-str"].points.at(-1).n = 999999; },
    d => { d.series["salience-str"].points.pop(); },
    d => { d.series["downside-price-impact"].points.at(-1).value = -1; }]) {
    const d = structuredClone(history); mutate(d); assert.throws(() => parseCandidateHistory(d));
  }
});

test("snapshot ratio uses two medians and cannot invent a history or change", () => {
  const raw = { schemaVersion: 1, historicalOnly: true, current: null, asOf: "2026-10-30",
    sourceSha256: "a".repeat(64), definitionId: "observation.cn_smallcap_turnover_snapshot.v1",
    requestedN: 10, n: 10, k: 2, smallMedian: 3, allMedian: 2, ratio: 1.5,
    scopeLabel: "sample", limitations: ["snapshot"] };
  const reading = fromSmallcapSnapshot(parseSmallcapSnapshot(raw));
  assert.deepEqual(reading.points, []); assert.equal(reading.change, null);
  assert.equal(reading.value, 1.5);
  assert.throws(() => parseSmallcapSnapshot({ ...raw, ratio: 150 }));
  assert.equal(parseSmallcapSnapshot({ ...raw, allMedian: 0, ratio: null }).ratio, null);
});
