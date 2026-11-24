import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./projectionAlignment.ts", import.meta.url).pathname],
  bundle: true, format: "esm", platform: "node", write: false });
const { alignProjection } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

test("daily keeps trading-date axis and exact same-day values only", () => {
  const price = { dates: ["2026-01-05", "2026-01-02", "2026-01-06", "2026-01-05"], values: [101, 100, 0, null] };
  const metric = [{ date: "2026-01-06", value: 0 }, { date: "2026-01-02", value: 2 }, { date: "2026-01-06", value: null }];
  assert.deepEqual(alignProjection(price, metric, "daily", null), {
    dates: ["2026-01-02", "2026-01-05", "2026-01-06"],
    price: [100, null, 0], values: [2, null, null],
    priceDates: ["2026-01-02", null, "2026-01-06"],
    metricDates: ["2026-01-02", null, "2026-01-06"],
  });
  assert.deepEqual(alignProjection({ dates: ["2026-01-02", "2026-01-03"], values: [1, 2] },
    [{ date: "2026-01-02", value: 4 }], "daily", null).dates, ["2026-01-02"]);
});

test("weekly uses only most recent valid prior close within six calendar days", () => {
  const result = alignProjection(
    { dates: ["2026-01-09", "2026-01-12", "2026-01-19", "2026-01-23"], values: [0, 12, null, 23] },
    [{ date: "2026-01-11", value: 5 }, { date: "2026-01-18", value: null },
      { date: "2026-01-19", value: 8 }, { date: "2026-01-22", value: 9 }, { date: "2026-01-23", value: 10 }],
    "weekly", null,
  );
  assert.deepEqual(result.dates, ["2026-01-11", "2026-01-18", "2026-01-19", "2026-01-22", "2026-01-23"]);
  assert.deepEqual(result.price, [0, 12, null, null, 23]);
  assert.deepEqual(result.priceDates, ["2026-01-09", "2026-01-12", null, null, "2026-01-23"]);
  assert.deepEqual(result.values, [5, null, 8, 9, 10]);
  assert.deepEqual(result.metricDates, result.dates);
});

test("monthly fills full overlapping month axis, keeps absent model month null and actual close date", () => {
  const result = alignProjection(
    { dates: ["2026-01-30", "2026-02-26", "2026-02-27", "2026-03-30", "2026-04-01"], values: [10, 20, 21, 30, 40] },
    [{ date: "2026-01-31", value: 1 }, { date: "2026-03-31", value: 0 }, { date: "2026-04-30", value: 4 }],
    "monthly", null,
  );
  assert.deepEqual(result.dates, ["2026-01", "2026-02", "2026-03", "2026-04"]);
  assert.deepEqual(result.values, [1, null, 0, 4]);
  assert.deepEqual(result.metricDates, ["2026-01-31", null, "2026-03-31", "2026-04-30"]);
  assert.deepEqual(result.price, [10, 21, 30, null]);
  assert.deepEqual(result.priceDates, ["2026-01-30", "2026-02-27", "2026-03-30", null]);
});

test("calendar-complete weekend month-end may use prior Friday; unfinished weekday month cannot", () => {
  const complete = alignProjection({ dates: ["2026-10-30"], values: [3] }, [{ date: "2026-10-31", value: 1 }], "monthly", null);
  assert.deepEqual(complete.price, [3]);
  assert.deepEqual(complete.priceDates, ["2026-10-30"]);
  const incomplete = alignProjection({ dates: ["2026-09-29"], values: [3] }, [{ date: "2026-09-30", value: 1 }], "monthly", null);
  assert.deepEqual(incomplete.price, [null]);
  assert.deepEqual(incomplete.priceDates, [null]);
});

test("monthly duplicate observations choose the latest date but preserve an explicit null", () => {
  const result = alignProjection(
    { dates: ["2026-01-27", "2026-01-30", "2026-02-27"], values: [1, 2, 3] },
    [{ date: "2026-02", value: 4 }, { date: "2026-01-20", value: 7 },
      { date: "2026-01-31", value: null }, { date: "2026-02", value: 0 }], "monthly", null,
  );
  assert.deepEqual(result.dates, ["2026-01", "2026-02"]);
  assert.deepEqual(result.values, [null, 0]);
  assert.deepEqual(result.metricDates, ["2026-01-31", "2026-02"]);
  assert.deepEqual(result.priceDates, ["2026-01-30", "2026-02-27"]);
});

test("monthly final price row null blocks earlier valid close in past and latest months", () => {
  const result = alignProjection(
    { dates: ["2026-01-30", "2026-01-31", "2026-02-27", "2026-03-30", "2026-03-31"],
      values: [10, null, 0, 30, null] },
    [{ date: "2026-01-31", value: 1 }, { date: "2026-02-28", value: 2 }, { date: "2026-03-31", value: 3 }],
    "monthly", null,
  );
  assert.deepEqual(result.dates, ["2026-01", "2026-02", "2026-03"]);
  assert.deepEqual(result.price, [null, 0, null]);
  assert.deepEqual(result.priceDates, [null, "2026-02-27", null]);
  assert.deepEqual(result.values, [1, 2, 3]);
});

test("stale metric truncates later price dates and years cut from common end", () => {
  const price = { dates: ["2024-01-01", "2025-01-01", "2026-01-01", "2026-02-01"], values: [1, 2, 3, 4] };
  const metric = [{ date: "2024-01-01", value: 1 }, { date: "2025-01-01", value: 2 }, { date: "2026-01-01", value: 3 }];
  assert.deepEqual(alignProjection(price, metric, "daily", 1).dates, ["2025-01-01", "2026-01-01"]);
  assert.deepEqual(alignProjection(price, metric, "daily", null).dates.at(-1), "2026-01-01");
  const monthly = alignProjection({ dates: ["2024-01-31", "2025-01-31", "2026-01-30", "2026-02-02"], values: [1, 2, 3, 4] },
    [{ date: "2024-01-31", value: 1 }, { date: "2025-01-31", value: 2 }, { date: "2026-01-31", value: 3 }], "monthly", 1);
  assert.equal(monthly.dates[0], "2025-01");
  assert.equal(monthly.dates.at(-1), "2026-01");
});

test("empty, invalid and nonfinite rows do not fabricate values", () => {
  assert.deepEqual(alignProjection({ dates: [], values: [] }, [], "monthly", null).dates, []);
  const result = alignProjection({ dates: ["bad", "2026-01-02", "2026-01-03"], values: [1, NaN, 0] },
    [{ date: "bad", value: 2 }, { date: "2026-01-03", value: Infinity }], "daily", null);
  assert.deepEqual(result.dates, ["2026-01-03"]);
  assert.deepEqual(result.price, [0]);
  assert.deepEqual(result.values, [null]);
});
