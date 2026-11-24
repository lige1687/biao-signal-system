import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";

const result = await build({ entryPoints: [new URL("./incrementObservationData.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { parseIncrementObservation, sessionReading, signed, SESSION_DIFFERENCE_COLOR } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const source = JSON.parse(await readFile(new URL("../../../public/research/market-increment-observations/cn.v1.json", import.meta.url), "utf8"));

test("actual snapshot retains separate dates, all history and reconciled institution amounts", () => {
  const p = parseIncrementObservation(source);
  assert.equal(p.session.points.length, 620);
  assert.equal(p.session.asof, "2026-11-02");
  assert.equal(p.institutional_disclosure.asof, "2026-11-03");
  assert.equal(p.institutional_disclosure.rows.length, 39);
  assert.equal(p.institutional_disclosure.coverage.convertible_rows_excluded, 1);
  assert.equal((p.institutional_disclosure.buy_yuan / 1e8).toFixed(2), "25.64");
  assert.equal((p.institutional_disclosure.sell_yuan / 1e8).toFixed(2), "45.16");
  assert.equal((p.institutional_disclosure.net_yuan / 1e8).toFixed(2), "-19.52");
  assert.equal(p.institutional_disclosure.retail_identity, null);
  assert.equal(sessionReading(p.session.latest), "两段均跌");
});

test("bad arithmetic, inconsistent dates and repeated institutions are rejected", () => {
  for (const mutate of [
    p => { p.session.points[0].diff20_pp += 1; },
    p => { p.session.points[1].date = p.session.points[0].date; },
    p => { p.session.latest.date = "2026-11-03"; },
    p => { p.session.latest.overnight20_pp = null; },
    p => { p.institutional_disclosure.rows[1] = p.institutional_disclosure.rows[0]; },
    p => { p.institutional_disclosure.net_yuan += 100; },
    p => { p.institutional_disclosure.coverage.unique_stocks = 40; },
    p => { p.institutional_disclosure.coverage.convertible_rows_excluded = 0; },
    p => { p.institutional_disclosure.asof = "2026-11-02"; },
    p => { p.institutional_disclosure.source_url = "javascript:alert(1)"; },
    p => { p.institutional_disclosure.retail_identity = "estimated retail"; },
  ]) {
    const copy = structuredClone(source); mutate(copy);
    assert.throws(() => parseIncrementObservation(copy));
  }
});

test("relative strength wording follows both legs even when their difference is positive", () => {
  const point = (o, d) => ({ date: "2026-11-02", overnight20_pp: o, intraday20_pp: d, diff20_pp: d - o });
  assert.equal(sessionReading(point(-5, -2)), "两段均跌");
  assert.equal(sessionReading(point(-2, -5)), "两段均跌");
  assert.equal(sessionReading(point(2, 5)), "两段均涨");
  assert.equal(sessionReading(point(5, 2)), "两段均涨");
  assert.equal(sessionReading(point(2, -5)), "隔夜涨、日内跌");
  assert.equal(sessionReading(point(-2, 5)), "隔夜跌、日内涨");
  assert.equal(sessionReading(point(0, 0)), "隔夜与日内均持平");
  assert.equal(sessionReading(point(0, 5)), "隔夜持平，日内上涨");
  assert.equal(sessionReading(point(0, -5)), "隔夜持平，日内下跌");
  assert.equal(sessionReading(point(5, 0)), "日内持平，隔夜上涨");
  assert.equal(sessionReading(point(-5, 0)), "日内持平，隔夜下跌");
  assert.equal(signed(-0.001), "-0.00");
  assert.equal(signed(0.001), "+0.00");
  assert.equal(signed(0), "0.00");
  assert.equal(signed(-0), "0.00");
});

test("difference uses neutral gray and missing legs are not assigned a rise/fall state", () => {
  assert.equal(SESSION_DIFFERENCE_COLOR, "#6b6b6b");
  for (const value of [null, undefined, {}, { overnight20_pp: null, intraday20_pp: 2 },
    { overnight20_pp: 1 }, { overnight20_pp: 1, intraday20_pp: NaN },
    { overnight20_pp: Infinity, intraday20_pp: 2 }]) {
    assert.equal(sessionReading(value), "隔夜与日内资料待补");
  }
});
