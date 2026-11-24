import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./bakerReference.ts", import.meta.url).pathname],
  bundle: true, format: "esm", platform: "node", write: false });
const { computeBakerReference, bakerReference } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const baker = JSON.parse(readFileSync(new URL("../../../public/research/observation-library-20261026/baker.json", import.meta.url), "utf8"));

test("real Baker versions use their own full histories and latest levels", () => {
  const orth = computeBakerReference(baker, baker.latest.value, "orth");
  const raw = computeBakerReference(baker, baker.latest.rawValue, "raw");
  assert.equal(orth.sourceStart, "1965-07-31");
  assert.equal(orth.sourceEnd, "2025-12-31");
  assert.equal(orth.sourceCount, 726);
  assert.equal(orth.validCount, 725);
  assert.equal(raw.validCount, 726);
  assert.equal(orth.currentValue, 0.06564764678478241);
  assert.equal(raw.currentValue, 0.12571176886558533);
  assert.notEqual(orth.low, raw.low);
  assert.notEqual(orth.high, raw.high);
  assert.ok(orth.low < orth.high && raw.low < raw.high);
  assert.ok(orth.currentPercentile >= 0 && orth.currentPercentile <= 100);
  assert.ok(raw.currentPercentile >= 0 && raw.currentPercentile <= 100);
});

test("linear n-1 quantiles, zero and midrank ties are exact", () => {
  const points = Array.from({ length: 25 }, (_, index) => ({ date: `2020-01-${String(index + 1).padStart(2, "0")}`, value: index - 12 }));
  const reference = computeBakerReference(points, 0);
  assert.ok(Math.abs(reference.low + 7.2) < 1e-12);
  assert.ok(Math.abs(reference.high - 7.2) < 1e-12);
  assert.equal(reference.currentPercentile, 50);
  assert.equal(reference.state, "middle");
  assert.equal(computeBakerReference(points, reference.low).state, "cold");
  assert.equal(computeBakerReference(points, reference.high).state, "hot");
  assert.equal(computeBakerReference(points, -99).currentPercentile, 0);
  assert.equal(computeBakerReference(points, 99).currentPercentile, 100);
  const tied = Array.from({ length: 24 }, (_, index) => ({ date: `2020-${String(index + 1).padStart(2, "0")}`, value: index < 12 ? 0 : 1 }));
  assert.equal(computeBakerReference(tied, 0).currentPercentile, 25);
  assert.equal(computeBakerReference(tied, 1).currentPercentile, 75);
  assert.equal(bakerReference(points, 0).percentile, 50);
  assert.equal(bakerReference(points, 0).count, 25);
});

test("missing, non-finite, short or flat histories cannot become bands", () => {
  const points = Array.from({ length: 25 }, (_, index) => ({ date: String(index), value: index === 0 ? null : index === 1 ? NaN : index }));
  assert.equal(computeBakerReference(points, 12), null);
  assert.equal(computeBakerReference(Array.from({ length: 24 }, (_, index) => ({ date: String(index), value: 1 })), 1), null);
  assert.equal(computeBakerReference(Array.from({ length: 24 }, (_, index) => ({ date: String(index), value: index })), NaN), null);
  assert.equal(computeBakerReference([], 0), null);
  const enough = [...points, { date: "25", value: 0 }];
  assert.equal(computeBakerReference(enough, 0).validCount, 24);
  assert.equal(computeBakerReference(enough, 0).sourceCount, 26);
});

test("variant choice is independent of a zoomed point subset", () => {
  const full = computeBakerReference(baker, baker.latest.value, "orth");
  const zoomed = baker.series.slice(-60);
  assert.notDeepEqual(computeBakerReference(zoomed, baker.latest.value), full);
  assert.deepEqual(computeBakerReference(baker, baker.latest.value, "orth"), full);
});
