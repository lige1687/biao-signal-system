// @ts-nocheck -- Executed by Node's TypeScript strip loader; browser tsconfig does not include Node types.
import test from "node:test";
import assert from "node:assert/strict";
import { historicalVolatility, priorVolatilityPercentile, volatilityHistory } from "./marketRiskMetrics.ts";

test("20 and 60 return windows require 21 and 61 consecutive closes", () => {
  const prices = Array.from({ length: 65 }, (_, i) => 100 * (1 + .005 * Math.sin(i)));
  const history = volatilityHistory(prices.map((_, i) => new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10)), prices);
  assert.equal(history[19].hv20, null);
  assert.ok(history[20].hv20 !== null);
  assert.equal(history[59].hv60, null);
  assert.ok(history[60].hv60 !== null);
  prices[35] = null as unknown as number;
  assert.equal(historicalVolatility(prices, 40, 20), null);
  assert.ok(historicalVolatility(prices, 62, 20) !== null);
});

test("ratio stays unknown for zero HV60", () => {
  const history = volatilityHistory(Array.from({ length: 62 }, (_, i) => new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10)), Array(62).fill(100));
  assert.equal(history[61].hv60, 0);
  assert.equal(history[61].ratio, null);
});

test("three-year midrank uses exactly 756 prior valid observations", () => {
  const history = Array.from({ length: 757 }, (_, i) => ({ date: String(i), hv20: i === 756 ? 5 : i % 2 ? 5 : 3, hv60: 10, ratio: .5 }));
  assert.equal(priorVolatilityPercentile(history, 755), null);
  assert.equal(priorVolatilityPercentile(history, 756), 75);
  history[12].hv20 = null as unknown as number;
  assert.equal(priorVolatilityPercentile(history, 756), null);
});

test("invalid, duplicate, or unordered price dates invalidate the whole volatility axis", () => {
  const closes = [100, 102, 99];
  for (const dates of [
    ["2026-01-01", "2026-01-01", "2026-01-03"],
    ["2026-01-01", "2026-01-03", "2026-01-02"],
    ["2026-01-01", "2026-02-30", "2026-03-01"],
    ["2026-01-01", "2026-1-02", "2026-01-03"],
  ]) assert.deepEqual(volatilityHistory(dates, closes), []);
});
