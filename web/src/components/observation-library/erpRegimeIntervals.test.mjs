import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildErpRegimeEpisodes,
  buildErpRegimeMarkAreas,
  denseTimePoints,
  extractErpRegimeSpans,
  formatAxisPointerDate,
} from "./erpRegimeIntervals.ts";

function pt(date, value, z, middle = 0, sigma = 1) {
  return {
    date,
    value,
    middle,
    sigma,
    upper: middle + 2 * sigma,
    lower: middle - 2 * sigma,
    z,
    n: 100,
  };
}

describe("erpRegimeIntervals", () => {
  it("extracts contiguous 1.5σ and nested 2σ spans without splitting on omitted bond holidays", () => {
    // 2026-10-12 (Monday bond holiday) is absent from source series; Oct 9 -> Oct 13 stay contiguous.
    const series = [
      pt("2026-10-07", -1.0, -1.0),
      pt("2026-10-08", -1.6, -1.6),
      pt("2026-10-09", -2.1, -2.1),
      pt("2026-10-13", -2.2, -2.2),
      pt("2026-10-14", -1.7, -1.7),
      pt("2026-10-15", -1.1, -1.1),
      pt("2026-10-20", 1.8, 1.8),
      pt("2026-10-21", 1.2, 1.2),
    ];

    const spans = extractErpRegimeSpans(series, [1.5, 2]);
    assert.equal(spans.length, 3);

    const lower15 = spans.find((s) => s.kind === "lower" && s.sigma === 1.5);
    assert.deepEqual(
      { start: lower15.startDate, end: lower15.endDate, vEnd: lower15.visualEndDate, n: lower15.pointsCount },
      { start: "2026-10-08", end: "2026-10-14", vEnd: "2026-10-15", n: 4 },
    );

    const lower20 = spans.find((s) => s.kind === "lower" && s.sigma === 2);
    assert.deepEqual(
      { start: lower20.startDate, end: lower20.endDate, vEnd: lower20.visualEndDate, peakZ: lower20.peakZ },
      { start: "2026-10-09", end: "2026-10-13", vEnd: "2026-10-14", peakZ: -2.2 },
    );

    const upper15 = spans.find((s) => s.kind === "upper" && s.sigma === 1.5);
    assert.equal(upper15.visualStartDate, "2026-10-20");
    assert.equal(upper15.visualEndDate, "2026-10-21");
  });

  it("gives single trailing-day regime touches visible width without exceeding series maxDate", () => {
    const series = [
      pt("2026-11-16", -1.0, -1.0),
      pt("2026-11-17", -1.7, -1.7),
    ];
    const spans = extractErpRegimeSpans(series, [1.5]);
    assert.equal(spans.length, 1);
    assert.equal(spans[0].visualStartDate, "2026-11-16");
    assert.equal(spans[0].visualEndDate, "2026-11-17");

    const areas = buildErpRegimeMarkAreas(spans, "2026-11-16", "2026-11-17");
    assert.equal(areas.length, 1);
    assert.equal(areas[0][0].xAxis, "2026-11-16");
    assert.equal(areas[0][1].xAxis, "2026-11-17");
  });

  it("clips markAreas cleanly to visible viewport window boundaries", () => {
    const series = [
      pt("2020-03-20", 2.4, 2.4),
      pt("2020-03-25", 2.2, 2.2),
      pt("2026-11-01", -1.8, -1.8),
      pt("2026-11-10", -1.2, -1.2),
    ];
    const spans = extractErpRegimeSpans(series, [1.5, 2]);
    const areas = buildErpRegimeMarkAreas(spans, "2021-11-17", "2026-11-17");
    // Only the 2026-11 interval falls in viewport; clipped safely.
    assert.equal(areas.length, 1);
    assert.equal(areas[0][0].xAxis, "2026-11-01");
    assert.equal(areas[0][1].xAxis, "2026-11-10");
  });

  it("merges brief intraday dips into clean episodes and computes peakSigma", () => {
    const series = [
      pt("2026-08-26", -1.6, -1.6),
      pt("2026-08-27", -2.2, -2.2),
      pt("2026-08-28", -1.45, -1.45), // 1 trading day shallow breather
      pt("2026-08-31", -1.9, -1.9),
      pt("2026-09-01", -1.0, -1.0),
    ];
    const episodes = buildErpRegimeEpisodes(series, [1.5, 2], false);
    assert.equal(episodes.length, 1);
    assert.equal(episodes[0].startDate, "2026-08-26");
    assert.equal(episodes[0].endDate, "2026-08-31");
    assert.equal(episodes[0].peakSigma, 2);
    assert.equal(episodes[0].crossingDate, "2026-08-27");
  });

  it("filters nulls out of time-axis line series and formats axisPointer dates without timestamps", () => {
    assert.deepEqual(
      denseTimePoints(["2026-10-09", "2026-10-12", "2026-10-13"], [-0.95, null, -0.98]),
      [["2026-10-09", -0.95], ["2026-10-13", -0.98]],
    );
    assert.equal(formatAxisPointerDate(Date.UTC(2026, 7, 12, 0, 0, 0)), "2026-08-12");
    assert.equal(formatAxisPointerDate("2026-08-12 00:00:00"), "2026-08-12");
  });
});
