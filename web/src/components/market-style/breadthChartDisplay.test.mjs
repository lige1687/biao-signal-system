import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { createRequire } from "node:module";
import * as echarts from "echarts";

const bundle = await build({ entryPoints: [new URL("./breadthChartDisplay.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { backgroundRuns, gapText, BACKGROUND_STYLES } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

const dates = ["2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03"];
const readings = (codes, days = dates) => new Map(codes.flatMap((code, i) => code == null ? [] : [[days[i], {
  date: days[i], state: { code, label: "后端描述", summary: "后端原值", tone: "neutral" }, horizons: {},
}]]));

test("a single missing observation remains a one-day run with background disabled", () => {
  const days = dates.slice(0, 3);
  const source = readings(["expanding", "expanding", "expanding"], days);
  assert.deepEqual(backgroundRuns(days, [30, null, 40], source, false), [{ start: 1, end: 1, key: "missing" }]);
});

test("nonfinite and absent values stay missing even when the backend supplies a state", () => {
  const days = dates.slice(0, 5);
  assert.deepEqual(backgroundRuns(days, [0, null, NaN, Infinity], readings(Array(5).fill("expanding")), false), [
    { start: 1, end: 4, key: "missing" },
  ]);
});

test("date keys align states independently of map order and a valid zero is not a gap", () => {
  const source = new Map([
    [dates[2], { date: dates[2], state: { code: "contracting" } }],
    [dates[0], { date: dates[0], state: { code: "expanding" } }],
    ["2026-10-22", { date: "2026-10-22", state: { code: "recovering" } }],
  ]);
  assert.deepEqual(backgroundRuns(dates.slice(0, 3), [0, 20, 10], source, true), [
    { start: 0, end: 0, key: "rising" }, { start: 2, end: 2, key: "falling" },
  ]);
});

test("only supplied directional states receive color; mixed, flat and unknown remain unshaded", () => {
  const days = Array.from({ length: 10 }, (_, i) => `2026-10-${String(i + 1).padStart(2, "0")}`);
  const source = readings(["expanding", "improving", "contracting", "weakening", "recovering", "retreating", "mixed", "flat", "unknown", "new-code"], days);
  assert.deepEqual(backgroundRuns(days, Array(10).fill(50), source, true), [
    { start: 0, end: 1, key: "rising" }, { start: 2, end: 3, key: "falling" },
    { start: 4, end: 4, key: "recovering" }, { start: 5, end: 5, key: "retreating" },
  ]);
});

test("equal colors cannot bridge neutral, missing or unclassified observations", () => {
  const source = readings(["expanding", "improving", "mixed", "expanding", "expanding", "expanding", null, "expanding"]);
  assert.deepEqual(backgroundRuns(dates, [10, 20, 30, 40, null, 50, 60, 70], source, true), [
    { start: 0, end: 1, key: "rising" }, { start: 3, end: 3, key: "rising" },
    { start: 4, end: 4, key: "missing" }, { start: 5, end: 5, key: "rising" },
    { start: 7, end: 7, key: "rising" },
  ]);
});

test("an empty date cannot extend color across its position", () => {
  const days = [dates[0], "", dates[2]];
  assert.deepEqual(backgroundRuns(days, [10, 20, 30], readings(["expanding", "expanding", "expanding"], days), true), [
    { start: 0, end: 0, key: "rising" }, { start: 2, end: 2, key: "rising" },
  ]);
});

test("gap text describes a single internal missing observation without inventing a range", () => {
  assert.equal(gapText([{ start: 1, end: 1, key: "missing" }], dates),
    "宽度缺测 1 个观察日：2026-10-26（缺记录）");
});

test("gap text counts observations, distinguishes trailing gaps and ignores colored runs", () => {
  const days = dates.slice(0, 5);
  assert.equal(gapText([
    { start: 0, end: 0, key: "missing" }, { start: 1, end: 1, key: "rising" },
    { start: 3, end: 4, key: "missing" },
  ], days), "宽度缺测 3 个观察日：2026-10-23（缺记录）；2026-10-28—2026-10-29（尚未更新）");
  assert.equal(gapText([{ start: 0, end: 1, key: "missing" }], days),
    "宽度缺测 2 个观察日：2026-10-23—2026-10-26（缺记录）");
});

test("a one-day trailing gap says not updated and complete input has no gap notice", () => {
  assert.equal(gapText([{ start: 0, end: 0, key: "missing" }], [dates[0]]),
    "宽度缺测 1 个观察日：2026-10-23（尚未更新）");
  assert.equal(gapText([{ start: 0, end: 0, key: "rising" }], [dates[0]]), "");
  assert.equal(gapText([], []), "");
  assert.deepEqual(backgroundRuns([], [], new Map(), true), []);
});

test("background legend distinguishes participation states and makes repair/retreat more visible", () => {
  assert.deepEqual(Object.fromEntries(Object.entries(BACKGROUND_STYLES).map(([key, style]) => [key, style.label])), {
    rising: "参与回升", falling: "参与收缩", recovering: "低位修复", retreating: "高位回落", low: "历史低位 ≤ P10", high: "历史高位 ≥ P90", missing: "宽度缺测",
  });
  const alpha = (key) => Number(BACKGROUND_STYLES[key].fill.match(/,\s*([\d.]+)\)$/)?.[1]);
  assert.ok(alpha("recovering") > alpha("rising"));
  assert.ok(alpha("retreating") > alpha("falling"));
  assert.ok(alpha("missing") > 0 && alpha("missing") < 0.3);
});

test("historical background follows the selected supplied horizon without future filtering", () => {
  const source = new Map(dates.slice(0, 4).map((date, i) => [date, {date,
    state: {code: "expanding"}, horizons: {
      "20": {status: "ready", position: "high"},
      "50": {status: i === 3 ? "insufficient" : "ready", position: ["low", "middle", "high", "low"][i]},
    }}]));
  assert.deepEqual(backgroundRuns(dates.slice(0, 4), [10, 50, 90, 10], source, true, "levels", "50"), [
    {start: 0, end: 0, key: "low"}, {start: 2, end: 2, key: "high"},
  ]);
  assert.deepEqual(backgroundRuns(dates.slice(0, 4), [90, null, 90, 90], source, true, "levels", "20"), [
    {start: 0, end: 0, key: "high"}, {start: 1, end: 1, key: "missing"}, {start: 2, end: 3, key: "high"},
  ]);
  assert.deepEqual(backgroundRuns(dates.slice(0, 1), [10], source, true, "levels", "50"), [{start:0,end:0,key:"low"}]);
  assert.deepEqual(backgroundRuns(dates.slice(0, 1), [10], source, false, "levels", "50"), []);
});

test("background run identifiers must never change the price axis range", async () => {
  const chartBundle = await build({ entryPoints: [new URL("./BreadthComparison.tsx", import.meta.url).pathname],
    bundle: true, platform: "node", format: "cjs", packages: "external", loader: { ".css": "empty" }, write: false });
  const module = { exports: {} };
  new Function("require", "module", "exports", chartBundle.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 600, height: 300 });
  try {
    chart.setOption({ animation: false, xAxis: { type: "category", data: dates.slice(0, 3) },
      yAxis: { type: "value", scale: true }, series: [
        { type: "line", data: [3600, 3800, 3700] },
        module.exports.backgroundSeries([{ start: 0, end: 2, key: "rising" }], 0),
      ] });
    const extent = chart.getModel().getComponent("yAxis", 0).axis.scale.getExtent();
    assert.ok(extent[0] >= 3500, `background polluted price extent: ${extent}`);
    assert.ok(extent[1] <= 3900, `background polluted price extent: ${extent}`);
  } finally { chart.dispose(); }
});

async function loadChartModule() {
  const chartBundle = await build({ entryPoints: [new URL("./BreadthComparison.tsx", import.meta.url).pathname],
    bundle: true, platform: "node", format: "cjs", packages: "external", loader: { ".css": "empty" }, write: false });
  const module = { exports: {} };
  new Function("require", "module", "exports", chartBundle.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}

function zoomChartOption(backgroundSeries, { background = true, horizon = "50", track = true, compare = false } = {}) {
  const prices = dates.map((_, i) => 3600 + i * 20);
  return {
    animation: false,
    grid: [{ top: 20, height: 90 }, { top: 140, height: 90 }],
    xAxis: [0, 1].map((gridIndex) => ({ type: "category", data: dates, gridIndex, boundaryGap: false })),
    yAxis: [{ type: "value", scale: true, gridIndex: 0 }, { type: "value", min: 0, max: 100, gridIndex: 1 }],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], filterMode: "weakFilter", start: 0, end: 100 },
      { type: "slider", xAxisIndex: [0, 1], filterMode: "weakFilter", start: 0, end: 100 },
    ],
    series: [
      { type: "line", name: "price", data: prices },
      ...(compare ? ["20", "50", "200"] : [horizon]).map((period) => ({
        type: "line", name: period, xAxisIndex: 1, yAxisIndex: 1, data: dates.map((_, i) => 30 + i),
      })),
      ...(track ? [{ type: "line", name: "track", xAxisIndex: 1, yAxisIndex: 1, data: dates.map(() => 80) }] : []),
      ...(background ? [0, 1].map((axis) => backgroundSeries([{ start: 0, end: dates.length - 1, key: "rising" }], axis)) : []),
      { id: "reading-price-date", type: "line", data: [] },
    ],
  };
}

for (const [label, change] of [
  ["phase background", { background: false }], ["horizon", { horizon: "200" }],
  ["reference track", { track: false }], ["three-line comparison", { compare: true }],
]) {
  test(`${label} changes retain the current linked zoom and price axis`, async () => {
    const { createBreadthChartUpdater, backgroundSeries } = await loadChartModule();
    assert.equal(typeof createBreadthChartUpdater, "function", "chart updates must preserve zoom within the same market, price and time window");
    const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 600, height: 300 });
    try {
      const update = createBreadthChartUpdater(chart);
      update(zoomChartOption(backgroundSeries), "cn:sse:365");
      chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 1, start: 25, end: 75 });
      const before = [0, 1].map((i) => chart.getModel().getComponent("xAxis", i).axis.scale.getExtent().slice());
      const priceExtent = chart.getModel().getComponent("yAxis", 0).axis.scale.getExtent().slice();
      update(zoomChartOption(backgroundSeries, change), "cn:sse:365");
      assert.deepEqual(chart.getOption().dataZoom.map(({ start, end }) => [start, end]), [[25, 75], [25, 75]]);
      assert.deepEqual([0, 1].map((i) => chart.getModel().getComponent("xAxis", i).axis.scale.getExtent()), before);
      assert.deepEqual(chart.getModel().getComponent("yAxis", 0).axis.scale.getExtent(), priceExtent);
    } finally { chart.dispose(); }
  });
}

for (const scope of ["us:sp500:365", "cn:hs300:365", "cn:sse:1095"]) {
  test(`changing the chart scope to ${scope} resets the linked zoom`, async () => {
    const { createBreadthChartUpdater, backgroundSeries } = await loadChartModule();
    assert.equal(typeof createBreadthChartUpdater, "function");
    const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 600, height: 300 });
    try {
      const update = createBreadthChartUpdater(chart);
      update(zoomChartOption(backgroundSeries), "cn:sse:365");
      chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 0, start: 25, end: 75 });
      update(zoomChartOption(backgroundSeries), scope);
      assert.deepEqual(chart.getOption().dataZoom.map(({ start, end }) => [start, end]), [[0, 100], [0, 100]]);
    } finally { chart.dispose(); }
  });
}

test("hover marker updates retain the linked zoom", async () => {
  const { createBreadthChartUpdater, backgroundSeries } = await loadChartModule();
  assert.equal(typeof createBreadthChartUpdater, "function");
  const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 600, height: 300 });
  try {
    const update = createBreadthChartUpdater(chart);
    update(zoomChartOption(backgroundSeries), "cn:sse:365");
    chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 0, start: 25, end: 75 });
    chart.setOption({ series: [{ id: "reading-price-date", markLine: { data: [{ xAxis: dates[3] }] } }] });
    assert.deepEqual(chart.getOption().dataZoom.map(({ start, end }) => [start, end]), [[25, 75], [25, 75]]);
  } finally { chart.dispose(); }
});

test("joint projection marks each visible range at its same-day price and shows either-period gaps", async () => {
  const { jointProjection } = await loadChartModule();
  const view = { dates: dates.slice(0, 6), price: [100, 101, 102, null, 104, 105],
    breadth: [Array(6).fill(null), [20, 19, 18, 80, 81, 82], [20, null, 19, 80, 81, null]],
    bands: [
      {key: "reversal_bottom", color: "#506f91", ranges: [[dates[0], dates[0]], [dates[2], dates[2]]]},
      {key: "reversal_top", color: "#8d6f60", ranges: [[dates[3], dates[4]]]},
      {key: "stage_bottom", color: "gray", ranges: [[dates[0], dates[2]]]},
    ] };
  const projected = jointProjection(view);
  assert.deepEqual(projected.values, [20, null, 18, 80, 81, null]);
  assert.deepEqual(projected.markers.map(({name, value}) => ({name, value})), [
    {name: "双低", value: [dates[0], 100]}, {name: "双低", value: [dates[2], 102]},
  ]);
  assert.deepEqual(backgroundRuns(view.dates, projected.values, new Map(), false), [
    {start: 1, end: 1, key: "missing"}, {start: 5, end: 5, key: "missing"},
  ]);
  // A high range that starts without a valid price must not slide to the following day.
  assert.ok(!projected.markers.some(({value}) => value[0] === dates[4]));
});

test("jumpToLatestWindow snaps zoomed viewport to rightmost edge while preserving zoom span", async () => {
  const { jumpToLatestWindow, panWindowByPixels } = await loadChartModule();
  assert.deepEqual(jumpToLatestWindow({ start: 15, end: 35 }), { start: 80, end: 100 });
  assert.deepEqual(jumpToLatestWindow({ start: 0, end: 100 }), { start: 0, end: 100 });
  const pannedRight = panWindowByPixels({ start: 20, end: 40 }, 300, 600);
  assert.deepEqual(pannedRight, { start: 30, end: 50 });
  const clampedRight = panWindowByPixels({ start: 85, end: 95 }, 600, 600);
  assert.deepEqual(clampedRight, { start: 90, end: 100 });
  assert.deepEqual(panWindowByPixels({ start: 0, end: 100 }, 200, 600), { start: 0, end: 100 });
});
