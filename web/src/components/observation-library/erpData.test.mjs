import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./metricData.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { fromErpHistory } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const series = (values) => ({ dates: ["2026-10-29", "2026-10-30"], values });

test("ERP uses each existing market series without recomputing from prices or relabelling percentiles", () => {
  const input = { series: { erp_cn: series([4.7, 4.8]), erp_us: series([-1.2, -1.1]), pe_cn: series([12, 13]) } };
  const cn = fromErpHistory(input, "erp-cn");
  const us = fromErpHistory(input, "erp-us");
  assert.equal(cn.value, 4.8);
  assert.equal(us.value, -1.1);
  assert.equal(cn.unit, "百分点");
  assert.equal(cn.date, "2026-10-30");
  assert.match(cn.note, /100÷沪深300 PE_TTM/);
  assert.match(us.note, /月度历史/);
  assert.doesNotMatch(us.status, /低估|机会区|高估|风险区/);
});

test("ERP keeps zero, null final rows and date gaps; missing market cannot borrow the other series", () => {
  assert.equal(fromErpHistory({ series: { erp_cn: series([1, 0]) } }, "erp-cn").value, 0);
  const missing = fromErpHistory({ series: { erp_cn: series([1, null]) } }, "erp-cn");
  assert.equal(missing.value, null);
  assert.equal(missing.change, null);
  assert.equal(missing.date, "2026-10-30");
  assert.deepEqual(missing.points.map((point) => point.value), [1, null]);
  assert.equal(fromErpHistory({ series: { erp_cn: series([1, 2]) } }, "erp-us"), null);
  assert.equal(fromErpHistory({ series: { erp_cn: { dates: ["2026-10-30"], values: [1, 2] } } }, "erp-cn"), null);
  assert.equal(fromErpHistory({ series: { erp_cn: { dates: ["2026-10-30", "2026-10-29"], values: [1, 2] } } }, "erp-cn"), null);
});
