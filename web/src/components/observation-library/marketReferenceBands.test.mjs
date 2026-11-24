import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const result = await build({entryPoints:[new URL("./marketReferenceBands.ts", import.meta.url).pathname], bundle:true, platform:"node", format:"esm", write:false});
const {marketReferenceBands, valuationMonthlyPoints} = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);
const month = (i) => `${2000 + Math.floor(i/12)}-${String(1 + i%12).padStart(2,"0")}`;
const history = Array.from({length:241}, (_, i) => ({date:month(i), value:i+1}));

test("ten calendar years of earlier months only, plus P10/P90 and independent 15-year check", () => {
  const a = marketReferenceBands("hs300-pe", history, true);
  assert.equal(a.rows[119].lower, null);
  assert.equal(a.latest.n, 120);
  assert.ok(Math.abs(a.latest.lower - 144.8) < 1e-10);
  assert.ok(Math.abs(a.latest.upper - 216.2) < 1e-10);
  assert.ok(Math.abs(a.latest.lowExtreme - 132.9) < 1e-10);
  assert.ok(Math.abs(a.latest.highExtreme - 228.1) < 1e-10);
  assert.equal(a.latest.percentile, 100);
  assert.equal(a.sensitivity.n, 180);
  assert.ok(Math.abs(a.sensitivity.upper - 204.2) < 1e-10);
  assert.ok(Math.abs(a.longHistory.upper - 228.05) < 1e-10);
  assert.equal(a.longHistory.full, true);
  assert.deepEqual(marketReferenceBands("sp500-cape", [...history, {date:"2020-02",value:2}]).rows.slice(0,241), a.rows);
});

test("same-month and missing inputs never create extra observations or a shorter window", () => {
  const input = [
    {date:"2019-03-27", value:15}, {date:"2019-02-27", value:10},
    {date:"2019-02-28", value:12}, {date:"2019-05-13", value:14},
  ];
  assert.deepEqual(valuationMonthlyPoints(input), [
    {date:"2019-02-28", value:12},{date:"2019-03-27", value:15},{date:"2019-04", value:null},{date:"2019-05-13", value:14},
  ]);
  const sparse = history.filter((_,i) => i < 121 || i > 135);
  assert.equal(marketReferenceBands("nasdaq100-pe", sparse).latest.lower, null);
  const stale = [{date:"2026-09",value:35.09}];
  assert.equal(marketReferenceBands("nasdaq100-pe", stale).latest.percentile, null);
  assert.equal(marketReferenceBands("nasdaq100-pe", stale).longHistory, null);
  const ties = history.map(p=>({...p,value:12}));
  assert.equal(marketReferenceBands("hs300-pe", ties).latest.percentile, 50);
  assert.equal(marketReferenceBands("hs300-pe", ties).position, "位于高低参照之间");
});

test("concentration keeps the original expanding P10/P90 reference", () => {
  const result = marketReferenceBands("turnover-concentration", history.slice(0,25));
  assert.equal(result.rows[23].lower, null);
  assert.ok(Math.abs(result.latest.lower - 3.3) < 1e-10);
  assert.ok(Math.abs(result.latest.upper - 21.7) < 1e-10);
  assert.equal(marketReferenceBands("vix",history), null);
});
