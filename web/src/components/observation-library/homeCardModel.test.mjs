import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
const bundle = await build({ entryPoints: [new URL("./homeCardModel.ts", import.meta.url).pathname], bundle: true,
  format: "esm", platform: "node", write: false });
const { summarizeHomeSeries } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const today = "2026-11-02";
test("a missing latest observation never borrows an older number or delta", () => {
  const rows = [{ date: "2026-10-29", value: 20 }, { date: "2026-10-30", value: null }];
  const view = summarizeHomeSeries("vix", rows, today);
  assert.equal(view.date, "2026-10-30");
  assert.equal(view.value, null);
  assert.equal(view.change, null);
  assert.deepEqual(view.points, rows);
});
test("changes have an explicit comparison date and never bridge missing periods", () => {
  const rows = [{ date: "2026-08", value: 40 }, { date: "2026-09", value: 42 }];
  const view = summarizeHomeSeries("turnover-concentration", rows, today);
  assert.equal(view.change, 2);
  assert.equal(view.previousDate, "2026-08");
  assert.equal(summarizeHomeSeries("baker-wurgler", rows, today).change, null);
  assert.equal(summarizeHomeSeries("vix", [{ date: "2026-10-29", value: null }, { date: "2026-10-30", value: 20 }], today).change, null);
});
test("out of order, duplicate, invalid and future dates are not silently plotted", () => {
  for (const rows of [
    [{ date: "2026-10-30", value: 1 }, { date: "2026-10-29", value: 2 }],
    [{ date: "2026-10-30", value: 1 }, { date: "2026-10-30", value: 2 }],
    [{ date: "2026-02-30", value: 1 }], [{ date: "2026-11-03", value: 1 }],
  ]) {
    const view = summarizeHomeSeries("vix", rows, today);
    assert.equal(view.invalid, true);
    assert.equal(view.value, null);
    assert.deepEqual(view.points, []);
  }
});
test("nonfinite values stay missing; empty sources are not zero", () => {
  assert.equal(summarizeHomeSeries("vix", [], today).value, null);
  assert.equal(summarizeHomeSeries("vix", [{ date: "2026-10-30", value: Infinity }], today).value, null);
});
