import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";

const result = await build({ entryPoints: [new URL("./industryTimelineOptions.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { industryRange, industryRangeFromZoom, industryTimelineOption } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const source = JSON.parse(await readFile(new URL("../../../public/research/industry-structure/cn.v1.json", import.meta.url), "utf8"));

test("recent windows contain exactly the requested trading dates including the latest", () => {
  for (const days of [60, 120, "all"]) {
    const range = industryRange(source.history.length, days);
    assert.equal(range.end - range.start + 1, days === "all" ? source.history.length : days);
    assert.equal(source.history[range.end].date, source.asOf);
    const restored = industryRangeFromZoom(source.history.length, range.start / range.end * 100, 100);
    assert.deepEqual(restored, range);
  }
  assert.deepEqual(industryRange(21, 120), { start: 0, end: 20 });
});

test("both panels, pointer, wheel zoom and slider share the same dates and range", () => {
  const option = industryTimelineOption(source.history, 250);
  assert.deepEqual(option.xAxis[0].data, option.xAxis[1].data);
  assert.deepEqual(option.axisPointer.link[0].xAxisIndex, [0, 1]);
  for (const zoom of option.dataZoom) {
    assert.deepEqual(zoom.xAxisIndex, [0, 1]);
    assert.equal(zoom.startValue, source.history.length - 120);
    assert.equal(zoom.endValue, source.history.length - 1);
  }
  assert.deepEqual(option.series.map(series => [series.xAxisIndex, series.yAxisIndex]), [[0, 0], [1, 1]]);
  assert.equal(option.series[0].data.at(-1), source.latest.correlation);
  assert.equal(option.series[1].data.at(-1), source.latest.dispersion5);
});

test("custom zoom dates clamp and preserve order, while tooltip compares both metrics on one date", () => {
  assert.deepEqual(industryRangeFromZoom(101, 80, 20), { start: 20, end: 80 });
  assert.deepEqual(industryRangeFromZoom(101, -20, 140), { start: 0, end: 100 });
  const option = industryTimelineOption(source.history, 330);
  const label = option.tooltip.formatter([{ axisValue: source.asOf }]);
  assert.match(label, /0.157/);
  assert.match(label, /1.97 个百分点/);
  assert.match(label, /2026-11-02/);
});
