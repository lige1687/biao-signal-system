import assert from "node:assert/strict";
import test from "node:test";
import { buildFocusPriceView } from "./price-projection-data.ts";

const price = (dates, values) => ({ label: "index", unit: "points", dates, values });
const model = (dates, focuses) => dates.map((date, index) => ({ date, focus: focuses[index] }));

test("uses exact same day and keeps missing model as null", () => {
  const result = buildFocusPriceView(
    price(["2025-01-02", "2025-01-03", "2025-01-06"], [100, 101, 102]),
    model(["2025-01-02", "2025-01-06"], [-0.02, 0.03]), "2025-01-06", "all");
  assert.deepEqual(result.dates, ["2025-01-02", "2025-01-03", "2025-01-06"]);
  assert.deepEqual(result.focusPercent, [-2, null, 3]);
  assert.deepEqual(result.negativeSpans, [{ start: "2025-01-02", end: "2025-01-02" }]);
});

test("common end stays at model overlap, not latest price", () => {
  const result = buildFocusPriceView(
    price(["2025-12-30", "2025-12-31", "2026-10-23"], [4000, 4010, 4500]),
    model(["2025-12-30", "2025-12-31"], [0.01, 0.02]), "2025-12-31", 1);
  assert.equal(result.priceSourceLast, "2026-10-23");
  assert.equal(result.modelLast, "2025-12-31");
  assert.equal(result.commonEnd, "2025-12-31");
  assert.deepEqual(result.dates, ["2025-12-30", "2025-12-31"]);
});

test("negative intervals split on missing model and invalid price", () => {
  const result = buildFocusPriceView(
    price(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08"], [100, 101, 102, 0, 104]),
    model(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08"], [-0.01, -0.02, 0.01, -0.03, -0.04]),
    "2025-01-08", "all");
  assert.deepEqual(result.prices, [100, 101, 102, null, 104]);
  assert.deepEqual(result.focusPercent, [-1, -2, 1, null, -4]);
  assert.deepEqual(result.negativeSpans, [
    { start: "2025-01-02", end: "2025-01-03" },
    { start: "2025-01-08", end: "2025-01-08" },
  ]);
});

test("bad price cannot create a common valid endpoint", () => {
  const result = buildFocusPriceView(price(["2025-01-02"], [Number.NaN]), model(["2025-01-02"], [-0.01]), "2025-01-02", "all");
  assert.equal(result.commonEnd, null);
  assert.deepEqual(result.dates, []);
});

test("all history starts at first jointly valid observation and preserves interior gaps", () => {
  const result = buildFocusPriceView(
    price(["2005-04-08", "2015-01-02", "2015-01-05", "2015-01-06", "2025-12-31"], [100, 0, 105, 106, 200]),
    model(["2015-01-02", "2015-01-05", "2025-12-31"], [0.01, -0.02, 0.03]), "2025-12-31", "all");
  assert.equal(result.windowStart, "2015-01-05");
  assert.deepEqual(result.dates, ["2015-01-05", "2015-01-06", "2025-12-31"]);
  assert.deepEqual(result.focusPercent, [-2, null, 3]);
});

test("strict sign changes mark the same-day price and zero bridges without repeat events", () => {
  const dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10"];
  const result = buildFocusPriceView(price(dates, [100, 101, 102, 103, 104, 105, 106]),
    model(dates, [0.02, 0, -0.01, -0.03, 0, 0.01, 0.02]), dates.at(-1), "all");
  assert.deepEqual(result.zeroCrossings, [
    { date: "2025-01-06", price: 102, focusPercent: -1, direction: "down" },
    { date: "2025-01-09", price: 105, focusPercent: 1, direction: "up" },
  ]);
});

test("missing model or invalid price breaks crossing evidence", () => {
  const dates = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09"];
  const result = buildFocusPriceView(price(dates, [100, 101, 102, 0, 104, 105]),
    model(dates.filter(d => d !== "2025-01-03"), [0.02, -0.01, 0.02, -0.02, 0.01]), dates.at(-1), "all");
  assert.deepEqual(result.zeroCrossings, [
    { date: "2025-01-09", price: 105, focusPercent: 1, direction: "up" },
  ]);
});

test("range boundary does not invent a first crossing but retains a genuine crossing inside", () => {
  const dates = ["2024-01-01", "2024-01-02", "2025-01-02", "2025-01-03", "2026-01-02"];
  const result = buildFocusPriceView(price(dates, [100, 101, 102, 103, 104]),
    model(dates, [0.01, -0.01, -0.02, 0.02, 0.01]), "2026-01-02", 1);
  assert.equal(result.windowStart, "2025-01-02");
  assert.deepEqual(result.zeroCrossings, [
    { date: "2025-01-03", price: 103, focusPercent: 2, direction: "up" },
  ]);
  const edge = buildFocusPriceView(price(dates, [100, 101, 102, 103, 104]),
    model(dates, [0.01, 0.01, -0.02, -0.02, -0.02]), "2026-01-02", 1);
  assert.deepEqual(edge.zeroCrossings, [
    { date: "2025-01-02", price: 102, focusPercent: -2, direction: "down" },
  ]);
});

test('an entirely missing price date also breaks crossing evidence',()=>{
 const v=buildFocusPriceView(price(['2025-01-02','2025-01-06'],[100,102]),model(['2025-01-02','2025-01-03','2025-01-06'],[.1,-.1,-.2]),'2025-01-06','all');
 assert.deepEqual(v.prices,[100,null,102]);assert.deepEqual(v.zeroCrossings,[]);
});
