import assert from "node:assert/strict";
import test from "node:test";
import { adjacentEventIndices, normalizeWindow, panWindow, recentMonthWindow, visibleDateRange, visibleYBounds, windowAroundDate, zoomWindow } from "./chart-navigation.ts";

test("zoom stays bounded and reset can restore the full window", () => {
  assert.deepEqual(zoomWindow({ start: 0, end: 100 }, 0.5), { start: 25, end: 75 });
  assert.deepEqual(zoomWindow({ start: 90, end: 100 }, 2), { start: 80, end: 100 });
  assert.deepEqual(normalizeWindow({ start: -5, end: 140 }), { start: 0, end: 100 });
});

test("panning preserves width and clamps at both ends", () => {
  assert.deepEqual(panWindow({ start: 25, end: 75 }, 0.5), { start: 50, end: 100 });
  assert.deepEqual(panWindow({ start: 25, end: 75 }, -1), { start: 0, end: 50 });
});

test("visible dates match rounded category bounds", () => {
  const dates = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"];
  assert.deepEqual(visibleDateRange(dates, { start: 50, end: 100 }), { start: "2025-01-03", end: "2025-01-07", count: 3 });
  assert.deepEqual(visibleDateRange(dates, { start: 41, end: 80 }), { start: "2025-01-03", end: "2025-01-06", count: 2 });
  assert.deepEqual(visibleDateRange([], { start: 0, end: 100 }), { start: null, end: null, count: 0 });
});

test("selected events remain visible when stepping beyond a zoomed window", () => {
  const dates = Array.from({length: 101}, (_, i) => String(i).padStart(3, "0"));
  assert.deepEqual(windowAroundDate(dates, "050", {start: 40, end: 60}), {start: 40, end: 60});
  assert.deepEqual(windowAroundDate(dates, "090", {start: 40, end: 60}), {start: 80, end: 100});
  assert.deepEqual(windowAroundDate(dates, "000", {start: 40, end: 60}, true), {start: 0, end: 60});
  assert.deepEqual(windowAroundDate(dates, "100", {start: 0, end: 100}, true), {start: 40, end: 100});
  assert.deepEqual(windowAroundDate([], "missing", {start: 0, end: 100}), {start: 0, end: 100});
});

test("empty intervals can navigate to the nearest event on either side", () => {
  const dates = ["2024-01-02", "2024-04-10", "2024-09-19"];
  assert.deepEqual(adjacentEventIndices(dates, undefined, "2024-05-01", "2024-07-01"), { previous: 1, next: 2 });
  assert.deepEqual(adjacentEventIndices(dates, dates[0], dates[0], dates[2]), { previous: -1, next: 1 });
  assert.deepEqual(adjacentEventIndices(dates, dates[2], dates[0], dates[2]), { previous: 1, next: -1 });
  assert.deepEqual(adjacentEventIndices([], undefined, null, null), { previous: -1, next: -1 });
});

test("month shortcuts clamp leap-year month ends and short histories", () => {
  const dates = ["2024-02-28", "2024-02-29", "2024-03-01", "2024-05-31"];
  assert.deepEqual(visibleDateRange(dates, recentMonthWindow(dates, 3)), { start: "2024-02-29", end: "2024-05-31", count: 3 });
  assert.deepEqual(recentMonthWindow(dates, 6), { start: 0, end: 100 });
  assert.deepEqual(recentMonthWindow([], 3), { start: 0, end: 100 });
});

test("local price bounds exclude off-screen extremes and ignore missing quotes", () => {
  assert.deepEqual(visibleYBounds([1000, 110, null, 120, 10], { start: 25, end: 75 }), { min: 109.2, max: 120.8 });
  assert.deepEqual(visibleYBounds([null, null], { start: 0, end: 100 }), { min: undefined, max: undefined });
  const flat = visibleYBounds([100, 100], { start: 0, end: 100 });
  assert.ok(flat.min < 100 && flat.max > 100);
});

test("momentum bounds keep zero visible in both positive and negative windows", () => {
  const positive = visibleYBounds([5, 10], { start: 0, end: 100 }, true);
  const negative = visibleYBounds([-10, -5], { start: 0, end: 100 }, true);
  assert.ok(positive.min <= 0 && positive.max > 10);
  assert.ok(negative.min < -10 && negative.max >= 0);
});
