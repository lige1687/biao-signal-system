import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "../../../web/node_modules/esbuild/lib/main.js";

const root = new URL("../../../web/", import.meta.url);
const result = await build({ entryPoints: [new URL("src/components/market-observation-alerts/relativeObservationData.ts", root).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { parseRelativeObservationSnapshot: parse, relativeObservationReading: reading } = await import(
  `data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const fixture = JSON.parse(await readFile(new URL("public/research/relative-market-observations-20261108/data.json", root)));

test("real observations preserve all points and use 20 common sessions, not calendar days", () => {
  const data = parse(fixture);
  assert.equal(data.cards.reduce((sum, card) => sum + card.points.length, 0), 2836);
  const latest = Object.fromEntries(data.cards.map(card => [card.id, reading(card)]));
  assert.equal(latest["cn-style-relative"].value, "0.6426倍");
  assert.equal(latest["cn-style-relative"].comparison, "下降 3.14%");
  assert.equal(latest["us-semiconductor-relative"].comparison, "下降 11.95%");
  assert.equal(latest["us-equal-weight-relative"].comparison, "上升 7.38%");
  assert.equal(latest["vix-term-structure"].value, "1.042倍");
  assert.equal(latest["vix-term-structure"].headline, "短期隐含波动率高于3个月");
  for (const row of Object.values(latest)) assert.equal(row.prior.date, "2026-10-09");
});

for (const [name, corrupt] of [
  ["missing card", d => d.cards.pop()],
  ["duplicate card", d => d.cards[0] = d.cards[1]],
  ["reversed dates", d => d.cards[0].points.reverse()],
  ["duplicate date", d => d.cards[0].points[1].date = d.cards[0].points[0].date],
  ["zero denominator", d => d.cards[0].points[70].denominator = 0],
  ["nonfinite ratio", d => d.cards[0].points[70].ratio = Infinity],
  ["ratio inconsistent with prices", d => d.cards[0].points[70].ratio *= 2],
  ["incorrect mean", d => d.cards[0].points[70].ma60 *= 2],
  ["incorrect numerator identity", d => d.cards[0].numerator.symbol = "000852"],
  ["future dated observation", d => d.imported_at = "2026-01-01T00:00:00Z"],
  ["unsafe source link", d => d.cards[0].sources[0].url = "javascript:alert(1)"],
]) test(`rejects ${name}`, () => {
  const data = structuredClone(fixture); corrupt(data); assert.throws(() => parse(data));
});
