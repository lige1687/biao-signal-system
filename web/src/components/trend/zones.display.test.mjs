import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./zones.ts", import.meta.url).pathname],
  bundle: true, format: "esm", platform: "node", write: false });
const zones = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

test("unqualified opportunity and risk levels no longer render action-coloured zones or lines", () => {
  for (const [key, levels] of Object.entries(zones.ZONES)) {
    assert.ok(levels.length > 0, `${key} must remain readable by existing callers`);
    assert.ok(levels.every((level) => level.tone === "neutral"), `${key} must be descriptive`);
  }
  for (const key of ["us_10y", "cn_10y", "vix", "margin_rzyezb", "margin_rzrqye", "hy_oas", "cape_us", "pe_cn", "icwa", "ccwa"]) {
    assert.deepEqual(zones.MARKLINES[key], [], `${key} has no verified fixed level`);
  }
  for (const key of ["us_10y", "cn_10y", "margin_rzyezb"]) assert.deepEqual(zones.OVERLAY_MARKLINES[key], []);
  assert.deepEqual(zones.MARKLINES.erp_cn.map((line) => line.y), [0]);
  assert.deepEqual(zones.MARKLINES.erp_us.map((line) => line.y), [0]);
  assert.deepEqual(zones.MARKLINES.pmi.map((line) => line.y), [50]);
  assert.deepEqual(zones.MARKLINES.breadth.map((line) => line.y), [50]);
  assert.match(zones.SOURCE_NOTES.vix, /不表示方向|未验证为方向/);
  assert.match(zones.SOURCE_NOTES.hy_oas, /无已验证固定交易线/);
});

test("PMI 50, zero growth and spread zero retain only their defined meaning", () => {
  assert.equal(zones.findZone(49.9, zones.PMI_ZONES).label, "PMI低于50");
  assert.equal(zones.findZone(50, zones.PMI_ZONES).label, "PMI等于50");
  assert.equal(zones.findZone(50.1, zones.PMI_ZONES).label, "PMI高于50");
  assert.equal(zones.findZone(-0.1, zones.CN_US_SPREAD_ZONES).label, "中债收益率低于美债");
  assert.equal(zones.findZone(0, zones.CN_US_SPREAD_ZONES).label, "中美10年收益率相等");
  assert.equal(zones.findZone(0, zones.PAYEMS_YOY_ZONES).label, "非农就业人数同比持平");
  assert.equal(zones.findZone(null, zones.PMI_ZONES).label, "暂无有效读数");
});

test("six legacy breadth queries keep numeric truth conditions without predictive metadata", () => {
  assert.deepEqual(zones.BREADTH_HIGHLIGHT_RULES.map((rule) => rule.key),
    ["stage_top", "stage_bottom", "reversal_top", "reversal_bottom", "bull_base", "bear_base"]);
  assert.ok(zones.BREADTH_HIGHLIGHT_RULES.every((rule) => !/顶部|底部|反转|牛市|熊市|机会|警戒/.test(rule.full)));
  assert.equal(zones.evalBreadthRule("stage_top", "CN", null, 80, null), true);
  assert.equal(zones.evalBreadthRule("stage_top", "US", null, 80, null), false);
  assert.equal(zones.evalBreadthRule("stage_top", "US", null, 85, null), true);
  assert.equal(zones.evalBreadthRule("stage_bottom", "CN", null, 20, null), true);
  assert.equal(zones.evalBreadthRule("stage_bottom", "US", null, 20, null), false);
  assert.equal(zones.evalBreadthRule("stage_bottom", "US", null, 15, null), true);
  assert.equal(zones.evalBreadthRule("reversal_top", "CN", null, 80, 79.9), false);
  assert.equal(zones.evalBreadthRule("reversal_top", "CN", null, 80, 80), true);
  assert.equal(zones.evalBreadthRule("reversal_bottom", "US", null, 15, 15), true);
  assert.equal(zones.evalBreadthRule("bull_base", "US", null, null, 50), false);
  assert.equal(zones.evalBreadthRule("bull_base", "US", null, null, 50.01), true);
  assert.equal(zones.evalBreadthRule("bear_base", "CN", null, null, 49.99), true);
  assert.deepEqual(zones.computeHighlightBands(new Set(), "CN", ["2026-01-01"], [0], [80], [80]), []);
  assert.deepEqual(zones.computeHighlightBands(new Set(["stage_top"]), "US", ["2026-01-01"], [0], [85], [0])[0].ranges,
    [["2026-01-01", "2026-01-01"]]);
});

test("joint AND conditions include boundaries and break ranges at either missing period", () => {
  for (const [market, low, high] of [["CN", 20, 80], ["US", 15, 85]]) {
    assert.equal(zones.evalBreadthRule("reversal_bottom", market, null, low, low), true);
    assert.equal(zones.evalBreadthRule("reversal_bottom", market, null, low - 1, low + 1), false);
    assert.equal(zones.evalBreadthRule("reversal_top", market, null, high, high), true);
    assert.equal(zones.evalBreadthRule("reversal_top", market, null, high + 1, high - 1), false);
    for (const key of ["reversal_top", "reversal_bottom"]) {
      assert.equal(zones.evalBreadthRule(key, market, null, low, null), false);
      assert.equal(zones.evalBreadthRule(key, market, null, null, high), false);
    }
    const days = ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"];
    const bands = zones.computeHighlightBands(new Set(["reversal_bottom"]), market, days,
      Array(5).fill(null), [low, low - 1, low, low, low], [low, low - 1, null, low, low]);
    assert.deepEqual(bands[0].ranges, [[days[0], days[1]], [days[3], days[4]]]);
  }
});
