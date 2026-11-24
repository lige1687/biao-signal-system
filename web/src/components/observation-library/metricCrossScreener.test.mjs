import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { build } from "esbuild";

const bundle = await build({
  entryPoints: [new URL("./metricCrossScreener.ts", import.meta.url).pathname],
  bundle: true,
  platform: "node",
  format: "esm",
  write: false,
});
const {
  buildMetricComboRuleSpecs,
  evaluateMetricComboScreener,
  isComboSupportedMetric,
} = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

describe("metricCrossScreener", () => {
  it("exposes concise core rules (2–4) and baseline rulers across all 11 supported metrics", () => {
    const ids = [
      "cn-margin-buy",
      "cn-margin-balance",
      "vix",
      "hy-oas",
      "vxn",
      "aaii",
      "naaim",
      "nfci",
      "ofr-fsi",
      "hs300-pe",
      "sp500-cape",
    ];
    for (const id of ids) {
      assert.equal(isComboSupportedMetric(id), true);
      const { rules } = buildMetricComboRuleSpecs(id);
      const core = rules.filter((r) => r.tier === "core");
      assert.ok(core.length >= 2 && core.length <= 4, `${id} core count=${core.length}`);
    }
    assert.equal(isComboSupportedMetric("pmi-cn"), false);
  });

  it("evaluates VIX and HY OAS cross-asset combinations and computes causal 20D/60D outcomes", () => {
    const dates = Array.from({ length: 35 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 2, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const prices = dates.map((_, i) => (i >= 15 ? 5250 : 5000)); // +5% after bar 15
    const vixVals = dates.map((_, i) => (i === 2 ? 32 : i === 6 ? 25 : i === 10 ? 24 : 16));
    const vixTerm = dates.map((date, i) => ({ date, value: i === 2 ? 1.05 : i === 6 ? 0.94 : 0.92 }));
    const hyPts = dates.map((date, i) => ({ date, value: i <= 3 ? 3.8 : i === 6 ? 3.55 : 3.3 }));
    const breadth = dates.map((date, i) => ({
      date,
      breadth_20: i === 3 ? 26 : i === 6 ? 42 : i === 10 ? 25 : 50,
      breadth_50: 55,
      breadth_200: 62,
    }));

    const vixEval = evaluateMetricComboScreener({
      id: "vix",
      frequency: "daily",
      dates,
      prices,
      metricValues: vixVals,
      breadthPoints: breadth,
      vixTermPoints: vixTerm,
      hyOasPoints: hyPts,
      activeIds: new Set(["vix_panic_unwind", "vix_term_unwind", "vix_spike_credit_calm"]),
    });

    assert.ok(vixEval.byRule.vix_panic_unwind.ranges.some(([s]) => s === dates[6]));
    assert.ok(vixEval.byRule.vix_term_unwind.ranges.length >= 1);
    assert.deepEqual(vixEval.byRule.vix_spike_credit_calm.ranges, [[dates[10], dates[10]]]);
    assert.ok(vixEval.outcome.h1.sampleCount >= 1);
    assert.equal(vixEval.outcome.h1.winRate, 100);

    const hyEval = evaluateMetricComboScreener({
      id: "hy-oas",
      frequency: "daily",
      dates,
      prices,
      metricValues: hyPts.map((p) => p.value),
      breadthPoints: breadth,
      vixPoints: dates.map((date, i) => ({ date, value: vixVals[i] })),
      activeIds: new Set(["hy_peak_ease", "hy_calm_vix_dip"]),
    });

    assert.ok(hyEval.byRule.hy_peak_ease.ranges.some(([s]) => s === dates[6]));
    assert.deepEqual(hyEval.byRule.hy_calm_vix_dip.ranges, [[dates[10], dates[10]]]);
  });

  it("evaluates CN margin buy/balance combinations and adapts horizons for weekly/monthly metrics", () => {
    const allDates = Array.from({ length: 150 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 0, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const fullMarginBal = allDates.map((date, i) => ({
      date,
      value: i < 125 ? 2.1 + (i % 10) * 0.02 : i === 132 ? 1.85 : i === 145 ? 2.65 : 2.25,
    }));
    const fullPrices = allDates.map((date, i) => ({
      date,
      value: i === 145 ? 3200 : 3300,
    }));
    const visDates = allDates.slice(125);
    const prices = visDates.map((d) => fullPrices.find((p) => p.date === d).value);
    const breadth = visDates.map((date, i) => ({
      date,
      breadth_20: i === 15 ? 74 : i === 20 ? 42 : 32,
      breadth_50: i === 7 ? 19 : 35,
      breadth_200: i === 7 ? 16 : 42,
    }));
    const erpBands = visDates.map((date) => ({ date, value: 5.9, z: 1.1 }));

    const balEval = evaluateMetricComboScreener({
      id: "cn-margin-balance",
      frequency: "daily",
      dates: visDates,
      prices,
      fullPricePoints: fullPrices,
      metricValues: visDates.map((d) => fullMarginBal.find((p) => p.date === d).value),
      breadthPoints: breadth,
      erpBands,
      marginRatioPoints: fullMarginBal,
      activeIds: new Set(["mbal_washout_ice", "mbal_overhang_fade"]),
    });
    assert.equal(balEval.rules.filter((r) => r.tier === "core").length, 2);
    assert.deepEqual(balEval.byRule.mbal_washout_ice.ranges, [[visDates[7], visDates[7]]]);
    assert.deepEqual(balEval.byRule.mbal_overhang_fade.ranges, [[visDates[20], visDates[20]]]);

    const buyEval = evaluateMetricComboScreener({
      id: "cn-margin-buy",
      frequency: "daily",
      dates: ["2026-11-17", "2026-11-18"],
      prices: [3920, 3900],
      metricValues: [6.4, 6.3],
      breadthPoints: [
        { date: "2026-11-17", breadth_20: 15, breadth_50: 13, breadth_200: 10 },
        { date: "2026-11-18", breadth_20: 14.7, breadth_50: 12.2, breadth_200: 9.1 },
      ],
      activeIds: new Set(["mb_dual_low_ice"]),
    });
    assert.deepEqual(buyEval.byRule.mb_dual_low_ice.ranges, [["2026-11-17", "2026-11-18"]]);
    assert.ok(buyEval.latestActiveRuleIds.includes("mb_dual_low_ice"));

    // Weekly AAII horizon adaptation
    const wkDates = Array.from({ length: 16 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 0, 2 + i * 7));
      return dt.toISOString().slice(0, 10);
    });
    const wkEval = evaluateMetricComboScreener({
      id: "aaii",
      frequency: "weekly",
      dates: wkDates,
      prices: wkDates.map((_, i) => (i >= 6 ? 110 : 100)),
      metricValues: wkDates.map((_, i) => (i === 2 ? -22 : 5)),
      breadthPoints: wkDates.map((date, i) => ({ date, breadth_20: i === 2 ? 42 : 35, breadth_50: 50 })),
      activeIds: new Set(["aaii_bear_turn"]),
    });
    assert.deepEqual(wkEval.horizonLabels, ["后 4 周", "后 12 周"]);
    assert.deepEqual(wkEval.byRule.aaii_bear_turn.ranges, [[wkDates[2], wkDates[2]]]);
    assert.equal(wkEval.outcome.h1.winRate, 100);
  });
});
