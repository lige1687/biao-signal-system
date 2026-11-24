import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";
const bundle = await build({ entryPoints: [new URL("./erpReferenceData.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { parseErpReference, fromErpReference } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

test("published ERP reference retains the qualified dates, units and latest historical identity", async () => {
  const raw = JSON.parse(await readFile(new URL("../../../public/research/erp-bands/cn-reference.json", import.meta.url), "utf8"));
  const data = parseErpReference(raw);
  const reading = fromErpReference(data);
  assert.equal(reading.unit, "百分点");
  assert.equal(reading.date, raw.asOf);
  assert.equal(reading.value, raw.points.at(-1).value);
  assert.match(reading.status, /未自动更新/);
  assert.throws(() => parseErpReference({ ...raw, asOf: "1900-01-01" }));
  assert.throws(() => parseErpReference({ ...raw, sourceSha256: "unverified" }));
  const nullLast = { ...raw, points: raw.points.map((p, i) => i === raw.points.length - 1 ? { ...p, value: null } : p) };
  assert.equal(fromErpReference(parseErpReference(nullLast)).value, null);
  assert.equal(fromErpReference(parseErpReference(nullLast)).change, null);
});

test("month-end observations cannot masquerade as daily band inputs", () => {
  const points = Array.from({ length: 60 }, (_, i) => ({ date: new Date(Date.UTC(2020, i, 28)).toISOString().slice(0, 10), value: 5, close: 4000 }));
  const base = { schemaVersion: 1, id: "erp-cn-3y-reference", historicalOnly: true, frequency: "monthly", asOf: points.at(-1).date,
    sourceName: "test fixture only", sourceUrl: "", sourceSha256: "0".repeat(64), note: "", points };
  assert.equal(parseErpReference(base).frequency, "monthly");
  assert.throws(() => parseErpReference({ ...base, frequency: "daily" }), /月末资料不能标为日频/);
});
