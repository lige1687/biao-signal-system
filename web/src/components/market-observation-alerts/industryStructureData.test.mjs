import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { build } from "esbuild";

const result = await build({ entryPoints: [new URL("./industryStructureData.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { parseIndustryStructure, isIndustrySnapshotOld } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const artifact = readFileSync(new URL("../../../public/research/industry-structure/cn.v1.json", import.meta.url), "utf8");
const source = JSON.parse(artifact);

test("CN-only display package keeps all 620 qualified windows and published end values", () => {
  const parsed = parseIndustryStructure(source);
  assert.equal(parsed.history.length, 620);
  assert.equal(parsed.history[0].date, "2024-04-11");
  assert.equal(parsed.asOf, "2026-11-02");
  assert.equal(parsed.latest.correlation.toFixed(3), "0.157");
  assert.equal(parsed.latest.dispersion5.toFixed(2), "1.97");
  assert.equal(parsed.latest.rankings.length, 10);
  assert.equal(parsed.definition.dispersionUnit, "百分点");
  assert.deepEqual(Object.keys(source), ["schemaVersion", "market", "scope", "asOf", "source", "definition", "history", "latest"]);
  assert.ok(!/\/Volumes\/|sha256|us-XLB|Yahoo|sources\s*:/i.test(artifact));
});

test("missing, duplicated or disordered days and mismatched latest reject the panel", () => {
  const clone = () => structuredClone(source);
  const missing = clone(); missing.history[4].correlation = null;
  assert.throws(() => parseIndustryStructure(missing));
  const duplicate = clone(); duplicate.history[4].date = duplicate.history[3].date;
  assert.throws(() => parseIndustryStructure(duplicate));
  const mismatch = clone(); mismatch.latest.dispersion5 = 3;
  assert.throws(() => parseIndustryStructure(mismatch));
  const badRank = clone(); badRank.latest.rankings[1].code = badRank.latest.rankings[0].code;
  assert.throws(() => parseIndustryStructure(badRank));
});

test("date status always distinguishes a historical snapshot from a current claim", () => {
  assert.equal(isIndustrySnapshotOld("2026-11-02", "2026-11-03"), false);
  assert.equal(isIndustrySnapshotOld("2026-11-02", "2026-11-10"), true);
  assert.equal(isIndustrySnapshotOld("2026-11-04", "2026-11-03"), true);
  assert.equal(isIndustrySnapshotOld("2026-02-30", "2026-11-03"), true);
});
