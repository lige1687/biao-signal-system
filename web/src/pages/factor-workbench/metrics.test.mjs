import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";

const built = await build({ entryPoints: [new URL("./metrics.ts", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm" });
const m = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
const publicRoot = new URL("../../../public/", import.meta.url);
const readPublic = url => readFile(new URL(`.${url}`, publicRoot));
const originalFetch = globalThis.fetch;
const responseFor = async (url, tamper = false) => {
  const bytes = await readPublic(url);
  const body = tamper && String(url).endsWith("metrics.json") ? Buffer.concat([bytes, Buffer.from(" ")]) : bytes;
  return new Response(body, { headers: { "content-type": "application/json" } });
};

test("manifest checksum and source identity gate the published metric artifact", async () => {
  globalThis.fetch = url => responseFor(url);
  try {
    const metrics = await m.loadWorkbenchMetrics();
    assert.ok(metrics.icRecords.length > 0 && metrics.irRecords.length > 0 && metrics.correlations.length > 0);
    const manifest = JSON.parse(await readPublic("/research/factor-workbench-20261024/manifest.json"));
    assert.deepEqual(metrics.sources, manifest.sources);
  } finally { globalThis.fetch = originalFetch; }
});

test("one-byte metrics change is rejected before parsing or display", async () => {
  globalThis.fetch = url => responseFor(url, true);
  try { await assert.rejects(m.loadWorkbenchMetrics(), /指纹不一致/); }
  finally { globalThis.fetch = originalFetch; }
});

test("a changed source catalog cannot silently reuse an older metric artifact", async () => {
  globalThis.fetch = async url => String(url).endsWith("catalog.json") ? new Response(Buffer.concat([await readPublic(url), Buffer.from(" ")]), { headers: { "content-type": "application/json" } }) : responseFor(url);
  try { await assert.rejects(m.loadWorkbenchMetrics(), /资金资料已更新/); }
  finally { globalThis.fetch = originalFetch; }
});

test("identity and cost matching keeps IC formation range separate from account range", async () => {
  const metrics = JSON.parse(await readPublic("/research/factor-workbench-20261024/metrics.json"));
  const ic = metrics.icRecords.find(row => row.datasetId === "fixed2014_300_legacy" && row.periodId === "all");
  const ir = metrics.irRecords.find(row => row.datasetId === ic.datasetId && row.factorId === ic.factorId && row.poolId === ic.poolId && row.periodId === ic.periodId && row.feeBps === 25);
  assert.ok(ic && ir);
  assert.notDeepEqual(ic.range, ir.range);
  const selection = { dataset: ic.datasetId, curveFactor: ic.factorId, pool: ic.poolId, period: ic.periodId, fee: "25" };
  const found = m.matchingMetrics(metrics, selection, ir.range);
  assert.equal(found.ic, ic);
  assert.equal(found.ir, ir);
  assert.equal(m.matchingMetrics(metrics, { ...selection, fee: "0" }, ir.range).ir?.feeBps, 0);
  assert.equal(m.matchingMetrics(metrics, { ...selection, pool: "wrong" }, ir.range).ir, undefined);
  assert.equal(m.matchingMetrics(metrics, { ...selection, period: "early" }, ir.range).ir, undefined);
});

test("source links accept exact research and methods, reject traversal and other websites", () => {
  assert.equal(m.sourceHref("/research/factor-workbench-20261024/metrics.json"), "/research/factor-workbench-20261024/metrics.json");
  assert.equal(m.sourceHref("docs/experiments/example.md"), "/library?report=docs%2Fexperiments%2Fexample.md");
  assert.equal(m.sourceHref("https://github.com/microsoft/qlib/blob/main/qlib/contrib/evaluate.py"), "https://github.com/microsoft/qlib/blob/main/qlib/contrib/evaluate.py");
  assert.equal(m.sourceHref("https://github.com/quantopian/alphalens/blob/master/alphalens/performance.py"), "https://github.com/quantopian/alphalens/blob/master/alphalens/performance.py");
  assert.equal(m.sourceHref("/research/../private.json"), null);
  assert.equal(m.sourceHref("https://example.com/fake"), null);
});
