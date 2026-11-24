import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";
const built = await build({ entryPoints: [new URL("./workbenchNavigation.ts", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm" });
const m = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
const doc = {datasets:[{id:"d",available:true,factors:[{id:"a",available:true},{id:"b",available:true}],pools:[{id:"all"},{id:"liquid"}],fees_bps:[0,25],periods:{all:["2015","2025"],late:["2020","2025"]},regimes:[{id:"all",available:true}]}]};
test("progress-to-diagnostics retains current pool, fees, period, and progress position", () => {
  const params = new URLSearchParams("dataset=d&curveFactor=a&pool=liquid&fee=0&period=late&regime=all&wpCase=one&wpStage=data");
  const next = m.diagnosticParams(doc, params, {datasetId:"d",factorId:"b",poolId:"all"});
  assert.equal(next.get("curveFactor"),"b");
  for (const key of ["pool","fee","period","regime","wpCase","wpStage"]) assert.equal(next.get(key),params.get(key));
  assert.equal(next.get("wb"),"study");
});
test("only unsupported conditions fall back on object transfer", () => {
  const next = m.diagnosticParams(doc,new URLSearchParams("pool=missing&fee=100&period=absent&regime=bad"),{datasetId:"d",factorId:"a",poolId:"all"});
  assert.equal(next.get("fee"),"25"); assert.equal(next.get("period"),"all"); assert.equal(next.get("pool"),"all"); assert.equal(next.get("regime"),"all");
});
