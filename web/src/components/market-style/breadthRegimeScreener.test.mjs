import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  alignErpZToDates,
  buildCausalPercentilePoints,
  buildCausalRollingErpZ,
  buildErpChartRuleSpecs,
  buildScreenerRuleSpecs,
  classifyErpEpisodesWithBreadth,
  computeEpisodeOutcomeStats,
  evaluateBreadthScreener,
  evaluateErpChartScreener,
} from "./breadthRegimeScreener.ts";

function makeReading(date, b20Pos = "middle", b50Pos = "middle", b200Pos = "middle") {
  return {
    date,
    state: { code: "mixed", label: "观察", summary: "test", tone: "neutral" },
    horizons: {
      "20": { lower: 15, median: 50, upper: 85, percentile: 50, delta_5: 0, sample_count: 300, status: "ready", position: b20Pos, event: "none" },
      "50": { lower: 20, median: 52, upper: 78, percentile: 50, delta_5: 0, sample_count: 300, status: "ready", position: b50Pos, event: "none" },
      "200": { lower: 25, median: 55, upper: 80, percentile: 50, delta_5: 0, sample_count: 300, status: "ready", position: b200Pos, event: "none" },
    },
  };
}

describe("breadthRegimeScreener", () => {
  it("performs causal as-of alignment without future leakage or >10d stale bridging", () => {
    const dates = ["2026-10-09", "2026-10-12", "2026-10-16", "2026-10-30"];
    const erpBands = [
      { date: "2026-10-09", value: 6.1, z: 1.6 },
      { date: "2026-10-16", value: 6.3, z: 1.8 },
    ];
    const aligned = alignErpZToDates(dates, erpBands);
    assert.deepEqual(aligned, [
      { date: "2026-10-09", value: 6.1, z: 1.6 },
      { date: "2026-10-09", value: 6.1, z: 1.6 }, // within 3d
      { date: "2026-10-16", value: 6.3, z: 1.8 },
      null, // 14d gap exceeds 10d limit
    ]);
  });

  it("switches hist_low/hist_high to track the currently emphasized horizon", () => {
    const dates = ["2026-11-02", "2026-11-03", "2026-11-04"];
    const readings = new Map([
      ["2026-11-02", makeReading("2026-11-02", "low", "middle", "high")],
      ["2026-11-03", makeReading("2026-11-03", "middle", "low", "high")],
      ["2026-11-04", makeReading("2026-11-04", "middle", "high", "low")],
    ]);
    const breadth = [
      [12, 40, 50], // 20d
      [45, 18, 82], // 50d
      [84, 83, 21], // 200d
    ];
    const r20 = evaluateBreadthScreener({
      market: "cn", horizon: "20", dates, prices: [3000, 3010, 3020], breadth, readings, erpBands: [], activeIds: new Set(["hist_low", "hist_high"]),
    });
    assert.deepEqual(r20.byRule.hist_low.ranges, [["2026-11-02", "2026-11-02"]]);
    assert.deepEqual(r20.byRule.hist_high.ranges, []);

    const r200 = evaluateBreadthScreener({
      market: "cn", horizon: "200", dates, prices: [3000, 3010, 3020], breadth, readings, erpBands: [], activeIds: new Set(["hist_low", "hist_high"]),
    });
    assert.deepEqual(r200.byRule.hist_low.ranges, [["2026-11-04", "2026-11-04"]]);
    assert.deepEqual(r200.byRule.hist_high.ranges, [["2026-11-02", "2026-11-03"]]);
  });

  it("screens bull_pullback, washout_thrust, top_divergence and ERP×breadth cross regimes", () => {
    // Build 26 consecutive weekdays cleanly
    const dates = Array.from({ length: 26 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 9, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const prices = dates.map((_, i) => 4000 + i * 10);
    const b20 = dates.map(() => 40);
    const b50 = dates.map(() => 55);
    const b200 = dates.map(() => 65);
    const erpBands = dates.map((date) => ({ date, value: 4.5, z: 0.2 }));

    // Days 2..5: bull_pullback (B200>50, B20<=20) AND B50 <= 20 (low breadth) + high ERP
    for (let i = 2; i <= 5; i++) {
      b20[i] = 16;
      b50[i] = 18;
      erpBands[i] = { date: dates[i], value: 6.8, z: 1.7 };
    }
    // Day 7: washout_thrust (B20 crosses above B50 and >= +10pp over i-5=2 -> 16+10=26; set b20=35 > b50=25)
    // Also ERP >= +1.0, 5d change b20 35>16 & b50 25>18 => erp_cheap_turn!
    b20[7] = 35;
    b50[7] = 25;
    erpBands[7] = { date: dates[7], value: 6.2, z: 1.2 };

    // Day 24: top_divergence (price near 60d max, b50 < 50, b50[24] - b50[4] <= -8; wait at i=4 b50 was 18!)
    // Make sure i=25 has b50[5]=18 -> let's test top_divergence cleanly when i=25 & b50[5]=60, or put top_divergence on separate array:
    // Actually at i=24, b50[24-20] = b50[4] = 18, so put clean high B50=65 at i=4 would overwrite day 4 washout. Let's test top_divergence separately below.
    // Day 20..22: erp_rich_weak (ERP <= -1.5, B50 < 50, B50 < B50[i-5])
    b50[15] = 48;
    b50[20] = 38;
    erpBands[20] = { date: dates[20], value: -1.1, z: -1.6 };

    const readings = new Map(dates.map((d) => [d, makeReading(d)]));
    const res = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates,
      prices,
      breadth: [b20, b50, b200],
      readings,
      erpBands,
      activeIds: new Set(["bull_pullback", "washout_thrust", "erp_cheap_low", "erp_cheap_turn", "erp_rich_weak"]),
    });

    assert.deepEqual(res.byRule.bull_pullback.ranges, [[dates[2], dates[5]]]);
    assert.deepEqual(res.byRule.erp_cheap_low.ranges, [[dates[2], dates[5]]]);
    assert.ok(res.byRule.washout_thrust.ranges.some(([s]) => s === dates[7]));
    assert.ok(res.byRule.erp_cheap_turn.ranges.some(([s]) => s === dates[7]));
    assert.deepEqual(res.byRule.erp_rich_weak.ranges, [[dates[20], dates[20]]]);
    assert.ok(res.markers.some((m) => m.ruleId === "washout_thrust" && m.value[0] === dates[7]));

    const crossMatch = classifyErpEpisodesWithBreadth({
      episodes: [
        { id: "up1", kind: "upper", startDate: dates[2], endDate: dates[7] },
        { id: "dn1", kind: "lower", startDate: dates[20], endDate: dates[20] },
      ],
      market: "cn",
      breadthDates: dates,
      breadth: [b20, b50, b200],
      readings,
      erpBands,
    });
    assert.equal(crossMatch.counts.cheap_low, 1);
    assert.equal(crossMatch.counts.cheap_turn, 1);
    assert.equal(crossMatch.counts.rich_weak, 1);
  });

  it("requires >=20 valid price bars and price near 60d peak for top_divergence", () => {
    const dates = Array.from({ length: 25 }, (_, i) => `2026-10-${String(i + 1).padStart(2, "0")}`);
    const prices = dates.map((_, i) => 4000 + i * 15); // steady rising to peak 4360 at day 24
    const b20 = dates.map(() => 45);
    const b50 = dates.map((_, i) => (i <= 5 ? 62 : 42));
    const b200 = dates.map(() => 60);
    const readings = new Map(dates.map((d) => [d, makeReading(d)]));

    // At index 24: b50[24]=42 < 50, b50[4]=62 => diff=-20 <= -8, 25 valid prices, price==maxPrice => fires!
    const res = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates,
      prices,
      breadth: [b20, b50, b200],
      readings,
      erpBands: [],
      activeIds: new Set(["top_divergence"]),
    });
    assert.deepEqual(res.byRule.top_divergence.ranges, [[dates[20], dates[24]]]);

    // Missing price on day 24 must NOT trigger divergence
    const missingPrices = [...prices];
    missingPrices[24] = null;
    const resGap = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates,
      prices: missingPrices,
      breadth: [b20, b50, b200],
      readings,
      erpBands: [],
      activeIds: new Set(["top_divergence"]),
    });
    assert.deepEqual(resGap.byRule.top_divergence.ranges, [[dates[20], dates[23]]]);
  });

  it("evaluates Zweig thrust, Deemer surge, bull_pullback_turn and bear_rally_trap", () => {
    const dates = Array.from({ length: 20 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 5, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const prices = dates.map((_, i) => 3500 + i * 10);
    const b20 = dates.map(() => 45);
    const b50 = dates.map(() => 40);
    const b200 = dates.map(() => 58);

    // Days 1..2: sharp dip in bull base (b20=18 <= 22), day 3 turns up to 28 -> bull_pullback_turn!
    b20[1] = 18;
    b20[2] = 17;
    b20[3] = 28;
    // Day 8: within 12d of b20<=20 (day 2), b20 surges to 78 -> zweig_thrust!
    b20[8] = 78;
    // Day 0 had b50=25 <= 30, day 10 has b50=52 (+27pp >= +25pp) -> deemer_thrust!
    b50[0] = 25;
    b50[10] = 52;
    // Days 14..16: bear base (b200=28 < 35), day 14 b20=68 >= 65, day 16 b20=44 < 50 -> bear_rally_trap!
    b200[14] = 28;
    b200[15] = 28;
    b200[16] = 28;
    b20[14] = 68;
    b20[15] = 55;
    b20[16] = 44;

    const readings = new Map(dates.map((d) => [d, makeReading(d)]));
    const res = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates,
      prices,
      breadth: [b20, b50, b200],
      readings,
      erpBands: [],
      activeIds: new Set(["bull_pullback_turn", "zweig_thrust", "deemer_thrust", "bear_rally_trap"]),
    });

    assert.ok(res.byRule.bull_pullback_turn.ranges.some(([s]) => s === dates[3]));
    assert.deepEqual(res.byRule.zweig_thrust.ranges, [[dates[8], dates[8]]]);
    assert.deepEqual(res.byRule.deemer_thrust.ranges, [[dates[10], dates[10]]]);
    assert.deepEqual(res.byRule.bear_rally_trap.ranges, [[dates[16], dates[16]]]);
  });

  it("evaluates CN margin leverage combinations (preserving pre-window 3Y percentile) and US VIX/HY OAS combinations", () => {
    // Build 140 prior margin days (around 2.2%..2.6%) + 12 visible days
    const allDates = Array.from({ length: 152 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 0, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const marginRatio = allDates.map((date, i) => ({
      date,
      value: i < 140 ? 2.2 + (i % 20) * 0.02 : i === 146 ? 1.85 : i === 150 ? 2.95 : 2.35,
    }));
    const pctPts = buildCausalPercentilePoints(marginRatio, 756, 120);
    assert.ok(pctPts[146].value <= 5);
    assert.ok(pctPts[150].value >= 95);

    const visDates = allDates.slice(140);
    const prices = visDates.map((_, i) => 3200 + i * 5);
    const b20 = visDates.map(() => 35);
    const b50 = visDates.map(() => 30);
    const b200 = visDates.map(() => 45);
    const erpBands = visDates.map((date) => ({ date, value: 5.5, z: 1.0 }));
    const readings = new Map(visDates.map((d) => [d, makeReading(d)]));

    // Visible index 6 (allDates[146]): marginRatio=1.85 (P0 <= P20/P35), b50=18 (low), b20=28 >= b50 & > b20[1]=20 => cn_margin_washout & cn_triple_bottom!
    b20[1] = 20;
    b20[6] = 28;
    b50[6] = 18;
    // Visible index 10 (allDates[150]): marginRatio=2.95 (P100 >= P85), b50[5]=42 -> b50[10]=34 (-8pp <= -5), b20[10]=28 < b50[10] => cn_margin_crowded_div!
    b50[5] = 42;
    b50[10] = 34;
    b20[10] = 28;

    const cnRes = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates: visDates,
      prices,
      breadth: [b20, b50, b200],
      readings,
      erpBands,
      auxSeries: { marginRatio },
      activeIds: new Set(["cn_triple_bottom", "cn_margin_washout", "cn_margin_crowded_div"]),
    });
    assert.deepEqual(cnRes.byRule.cn_triple_bottom.ranges, [[visDates[6], visDates[6]]]);
    assert.deepEqual(cnRes.byRule.cn_margin_washout.ranges, [[visDates[6], visDates[6]]]);
    assert.deepEqual(cnRes.byRule.cn_margin_crowded_div.ranges, [[visDates[10], visDates[10]]]);

    // US VIX + HY OAS combinations
    const usVix = visDates.map((date, i) => ({
      date,
      value: i === 2 ? 24 : i === 4 ? 32 : i === 7 ? 26 : i === 11 ? 29 : 16,
    }));
    const usVixTerm = visDates.map((date, i) => ({
      date,
      value: i === 4 ? 1.06 : i === 7 ? 0.95 : 0.92,
    }));
    const usHyOas = visDates.map((date, i) => ({
      date,
      value: i === 11 ? 4.8 : 3.2,
    }));
    const usB20 = visDates.map(() => 45);
    const usB50 = visDates.map(() => 55);
    const usB200 = visDates.map(() => 62);
    // Index 2: VIX=24>=22, HY OAS=3.2<4.0, B200=62>50, B20=25<=30 -> us_vix_spike_credit_calm!
    usB20[2] = 25;
    // Index 7: peak VIX in last 10d was 32 (>=28), 26 <= 32*0.88 (28.16), b20[7]=50 > b20[4]=35 -> us_vix_panic_unwind!
    usB20[4] = 35;
    usB20[7] = 50;
    // Index 11: VIX=29>=25, HY OAS=4.8>=4.5, B50=32<40 -> us_credit_contagion!
    usB50[11] = 32;

    const usRes = evaluateBreadthScreener({
      market: "us",
      horizon: "50",
      dates: visDates,
      prices,
      breadth: [usB20, usB50, usB200],
      readings,
      erpBands: [],
      auxSeries: { vix: usVix, vixTerm: usVixTerm, hyOas: usHyOas },
      activeIds: new Set([
        "us_vix_spike_credit_calm",
        "us_vix_panic_unwind",
        "us_vix_term_unwind",
        "us_credit_contagion",
      ]),
    });
    assert.deepEqual(usRes.byRule.us_vix_spike_credit_calm.ranges, [[visDates[2], visDates[2]]]);
    assert.deepEqual(usRes.byRule.us_vix_panic_unwind.ranges, [
      [visDates[5], visDates[5]],
      [visDates[7], visDates[7]],
    ]);
    assert.ok(usRes.byRule.us_vix_term_unwind.ranges.some(([s, e]) => s <= visDates[7] && visDates[7] <= e));
    assert.deepEqual(usRes.byRule.us_credit_contagion.ranges, [[visDates[11], visDates[11]]]);
  });

  it("computes causal forward 20D/60D episode stats with cooldown deduplication and excludes incomplete tail bars", () => {
    // 70 bars: flat 100 except spike after bar 5
    const prices = Array.from({ length: 70 }, (_, i) => (i >= 25 ? 110 : i === 15 ? 95 : 100));
    const episodes = [
      { id: "e1", ruleId: "r", ruleLabel: "R", color: "#000", startDate: "d5", endDate: "d6", startIndex: 5, endIndex: 6, days: 2, startPrice: 100 },
      // Within 5-bar cooldown of e1 (startIndex 10 - endIndex 6 = 4 <= 5) -> merged into e1!
      { id: "e2", ruleId: "r", ruleLabel: "R", color: "#000", startDate: "d10", endDate: "d10", startIndex: 10, endIndex: 10, days: 1, startPrice: 100 },
      // Tail episode at index 58 -> < 20 bars remaining (58+20=78 >= 70), excluded from forward return!
      { id: "e3", ruleId: "r", ruleLabel: "R", color: "#000", startDate: "d58", endDate: "d59", startIndex: 58, endIndex: 59, days: 2, startPrice: 110 },
    ];
    const stats = computeEpisodeOutcomeStats(episodes, prices, 5);
    assert.equal(stats.rawEpisodeCount, 3);
    assert.equal(stats.dedupEpisodeCount, 2);
    assert.equal(stats.d20.sampleCount, 1); // Only entry at index 5 has 20 future bars
    assert.equal(Math.round(stats.d20.meanReturn * 100) / 100, 10); // 100 -> 110 = +10%
    assert.equal(stats.d20.winRate, 100);
    assert.equal(Math.round(stats.d20.avgMaxDrawdown * 100) / 100, -5); // dipped to 95 at bar 15
    assert.equal(stats.d60.sampleCount, 1); // 5 + 60 = 65 < 70
  });

  it("curates full-history 5 core rules (3 buy + 2 sell) and market-specific baseline rulers", () => {
    const cnSpecs = buildScreenerRuleSpecs("cn", "50");
    const cnCore = cnSpecs.filter((r) => r.tier === "core");
    const cnBaseline = cnSpecs.filter((r) => r.tier === "baseline");
    assert.equal(cnCore.length, 5);
    assert.equal(cnCore.filter((r) => r.intent === "bull").length, 3);
    assert.equal(cnCore.filter((r) => r.intent === "risk").length, 2);
    assert.deepEqual(
      cnCore.map((r) => r.id),
      ["dual_low_w3", "erp_cheap_w3", "erp_cheap_turn", "weak_base_rally_fade", "hot_retreat_break"],
    );
    assert.equal(cnBaseline.length, 5);
    assert.ok(cnBaseline.some((r) => r.id === "reversal_bottom"));

    const usSpecs = buildScreenerRuleSpecs("us", "50");
    const usCore = usSpecs.filter((r) => r.tier === "core");
    const usBaseline = usSpecs.filter((r) => r.tier === "baseline");
    assert.equal(usCore.length, 5);
    assert.equal(usCore.filter((r) => r.intent === "bull").length, 3);
    assert.equal(usCore.filter((r) => r.intent === "risk").length, 2);
    assert.deepEqual(
      usCore.map((r) => r.id),
      ["bull_pullback_turn", "reversal_bottom", "us_vix_panic_unwind", "weak_base_rally_fade", "bull_base_break"],
    );
    assert.equal(usBaseline.length, 7);
    assert.ok(usBaseline.find((r) => r.id === "us_vix_spike_credit_calm")?.coverageNote?.includes("2023-11"));
    assert.ok(usBaseline.find((r) => r.id === "us_credit_contagion")?.coverageNote?.includes("2023-11"));

    // Verify W3 dual_low_w3 (price > MA50 after dual-low) & climax_ma20_break (B50 >= 80 -> <50 & price < MA20)
    const w3Dates = Array.from({ length: 55 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 5, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const w3Prices = w3Dates.map((_, i) => (i === 52 ? 4100 : i === 54 ? 3900 : 4000));
    const wb20 = w3Dates.map(() => 45);
    const wb50 = w3Dates.map((_, i) => (i === 35 ? 18 : i === 40 ? 82 : i === 54 ? 42 : 55));
    const wb200 = w3Dates.map((_, i) => (i === 35 ? 16 : 55));
    const w3Readings = new Map(w3Dates.map((d) => [d, makeReading(d)]));
    const resW3 = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates: w3Dates,
      prices: w3Prices,
      breadth: [wb20, wb50, wb200],
      readings: w3Readings,
      erpBands: [],
      activeIds: new Set(["dual_low_w3", "climax_ma20_break"]),
    });
    assert.deepEqual(resW3.byRule.dual_low_w3.ranges, [[w3Dates[52], w3Dates[52]]]);
    assert.deepEqual(resW3.byRule.climax_ma20_break.ranges, [[w3Dates[54], w3Dates[54]]]);

    const dates = [
      "2026-11-10",
      "2026-11-11",
      "2026-11-12",
      "2026-11-13",
      "2026-11-16",
      "2026-11-17",
    ];
    const readings = new Map(dates.map((d) => [d, makeReading(d, "low", "low", "low")]));
    // Days 0..4: 双低出清 (B50<=20 & B200<=20), Day 5: 双低右侧拐头 (B20=29 > B50=21, +12pp vs day 0, B50 21 > 15)
    const resTurn = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates,
      prices: [3850, 3840, 3835, 3845, 3860, 3910],
      breadth: [
        [17, 16, 15, 18, 20, 29],
        [15, 14, 14, 15, 16, 21],
        [11, 10, 10, 11, 12, 14],
      ],
      readings,
      erpBands: [],
      activeIds: new Set(["reversal_bottom", "dual_low_turn"]),
    });
    assert.deepEqual(resTurn.byRule.reversal_bottom.ranges, [["2026-11-10", "2026-11-16"]]);
    assert.deepEqual(resTurn.byRule.dual_low_turn.ranges, [["2026-11-17", "2026-11-17"]]);

    const latestDualLow = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates: ["2026-11-16", "2026-11-17"],
      prices: [3900, 3850],
      breadth: [[18, 17], [15, 14], [11, 10]],
      readings: new Map([
        ["2026-11-16", makeReading("2026-11-16", "low", "low", "low")],
        ["2026-11-17", makeReading("2026-11-17", "low", "low", "low")],
      ]),
      erpBands: [],
      activeIds: new Set(),
    });
    assert.deepEqual(latestDualLow.latestActiveRuleIds, ["hist_low", "stage_bottom", "reversal_bottom"]);
  });

  it("splits bull and risk forward outcomes via outcomeByIntent when mixed rules are active", () => {
    const dates = Array.from({ length: 90 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 0, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    // Buy trigger around day 52 rallies +10% by day 72; sell trigger around day 60 drops -10% by day 80.
    const prices = dates.map((_, i) => {
      if (i < 52) return 100;
      if (i < 60) return 105;
      if (i < 72) return 96;
      if (i < 80) return 110;
      return 86.4;
    });
    const b20 = dates.map((_, i) => (i === 55 ? 85 : i === 60 ? 30 : 50));
    const b50 = dates.map((_, i) => (i === 35 ? 18 : i === 55 ? 70 : i === 60 ? 40 : 55));
    const b200 = dates.map((_, i) => (i === 35 ? 16 : 55));
    const readings = new Map(dates.map((d) => [d, makeReading(d)]));
    const mixed = evaluateBreadthScreener({
      market: "cn",
      horizon: "50",
      dates,
      prices,
      breadth: [b20, b50, b200],
      readings,
      erpBands: [],
      auxSeries: { fullPrice: dates.map((date, i) => ({ date, value: prices[i] })) },
      activeIds: new Set(["dual_low_w3", "hot_retreat_break"]),
    });
    assert.ok(mixed.activeIntents.includes("bull"));
    assert.ok(mixed.activeIntents.includes("risk"));
    assert.ok(mixed.outcomeByIntent.bull.dedupEpisodeCount >= 1);
    assert.ok(mixed.outcomeByIntent.risk.dedupEpisodeCount >= 1);
    assert.ok((mixed.outcomeByIntent.bull.d20.meanReturn ?? 0) > 0);
    assert.ok((mixed.outcomeByIntent.risk.d20.meanReturn ?? 0) < 0);
  });

  it("curates zero-gimmick core ERP combinations (CN: 2 buy + 1 sell, US: 2 buy + 2 sell) + 3 baseline rulers", () => {
    const cnSpecs = buildErpChartRuleSpecs("cn");
    assert.equal(cnSpecs.filter((r) => r.tier === "core" && r.intent === "bull").length, 2);
    assert.equal(cnSpecs.filter((r) => r.tier === "core" && r.intent === "risk").length, 1);
    assert.equal(cnSpecs.filter((r) => r.tier === "baseline").length, 3);

    const usSpecs = buildErpChartRuleSpecs("us");
    assert.equal(usSpecs.filter((r) => r.tier === "core" && r.intent === "bull").length, 2);
    assert.equal(usSpecs.filter((r) => r.tier === "core" && r.intent === "risk").length, 2);
    assert.equal(usSpecs.filter((r) => r.tier === "baseline").length, 3);

    const dates = Array.from({ length: 80 }, (_, i) => {
      const dt = new Date(Date.UTC(2026, 0, 1 + i));
      return dt.toISOString().slice(0, 10);
    });
    const prices = dates.map((_, i) => (i < 52 ? 100 : i < 72 ? 102 : 110.16));
    const breadthPoints = dates.map((date, i) => ({
      date,
      breadth_20: i === 35 ? 18 : 45,
      breadth_50: i === 35 ? 19 : 55,
    }));
    const erpBands = dates.map((date, i) => ({
      date,
      value: i === 52 ? 6.4 : i === 79 ? -1.1 : 5.1,
      z: i === 52 ? 1.3 : i === 79 ? -1.7 : 0.1,
    }));
    const readings = new Map(dates.map((d) => [d, makeReading(d)]));

    const out = evaluateErpChartScreener({
      market: "cn",
      priceDates: dates,
      prices,
      breadthPoints,
      readings,
      erpBands,
      activeIds: new Set(["erp_cheap_w3"]),
    });

    assert.equal(out.byRule.erp_cheap_w3.episodeCount, 1);
    assert.equal(out.markAreas.length, 1);
    assert.ok(out.markAreas[0][0].xAxis < out.markAreas[0][1].xAxis);
    assert.equal(out.outcome.d20.sampleCount, 1);
    assert.equal(Math.round(out.outcome.d20.meanReturn * 100) / 100, 8);
    assert.deepEqual(out.latestActiveRuleIds, ["raw_rich_15"]);
  });

  it("uses causal 1Y adaptive Z for US buy rules and overheated MA50/MA60 breaks for US risk rules", () => {
    const dates = [];
    const cur = new Date(Date.UTC(2024, 0, 2));
    while (dates.length < 340) {
      const dow = cur.getUTCDay();
      if (dow !== 0 && dow !== 6) dates.push(cur.toISOString().slice(0, 10));
      cur.setUTCDate(cur.getUTCDate() + 1);
    }
    const erpBands = dates.map((date, i) => ({
      date,
      value: i === 285
        ? -0.1
        : i >= 100 && i < 120
          ? -0.65
          : i >= 120 && i < 140
            ? -0.95
            : -0.8 + (i % 2 === 0 ? 0.01 : -0.01),
      z: i >= 320 ? -1.8 : -0.5,
    }));
    const z1y = buildCausalRollingErpZ(erpBands, 1, 180);
    const z1yMutated = buildCausalRollingErpZ(
      erpBands.map((row, idx) => (idx === erpBands.length - 1 ? { ...row, value: 99 } : row)),
      1,
      180,
    );
    assert.deepEqual(z1y.slice(0, -1), z1yMutated.slice(0, -1));
    assert.equal(z1y[100].z, null);
    assert.ok(z1y[285].z > 2.0, `expected 1Y adaptive z >= +1 on regime rebound, got ${z1y[285].z}`);

    const prices = dates.map((_, i) => {
      if (i < 275) return 5000;
      if (i < 285) return 4600;
      if (i < 322) return 5200;
      return 4850;
    });
    const breadthPoints = dates.map((date, i) => ({
      date,
      breadth_20: i === 315 ? 84 : 55,
      breadth_50: i === 280 ? 18 : i === 315 ? 70 : i >= 322 ? 42 : 55,
    }));
    const vix = dates.map((date, i) => ({
      date,
      value: i === 282 ? 32 : i === 285 ? 27 : 16,
    }));
    const readings = new Map(dates.map((d) => [d, makeReading(d)]));

    const out = evaluateErpChartScreener({
      market: "us",
      priceDates: dates,
      prices,
      breadthPoints,
      readings,
      erpBands,
      auxSeries: { vix, fullPrice: dates.map((date, i) => ({ date, value: prices[i] })) },
      activeIds: new Set(["us_erp_cheap_w3", "us_erp_vix_unwind", "us_erp_rich_weak", "us_erp_rich_div"]),
    });

    assert.equal(out.byRule.us_erp_cheap_w3.episodeCount, 1);
    assert.equal(out.byRule.us_erp_cheap_w3.episodes[0].startDate, dates[285]);
    assert.equal(out.byRule.us_erp_vix_unwind.episodeCount, 1);
    assert.equal(out.byRule.us_erp_vix_unwind.episodes[0].startDate, dates[285]);
    assert.equal(out.byRule.us_erp_rich_weak.episodeCount, 1);
    assert.equal(out.byRule.us_erp_rich_weak.episodes[0].startDate, dates[322]);
    assert.equal(out.byRule.us_erp_rich_div.episodeCount, 1);
    assert.equal(out.byRule.us_erp_rich_div.episodes[0].startDate, dates[322]);
    assert.ok(out.contextByDate.get(dates[285])?.erpZ1y > 2.0);

    const noOverheatOut = evaluateErpChartScreener({
      market: "us",
      priceDates: dates,
      prices,
      breadthPoints: dates.map((date, i) => ({
        date,
        breadth_20: 40,
        breadth_50: i >= 320 ? 35 : 52,
      })),
      readings,
      erpBands,
      auxSeries: { fullPrice: dates.map((date, i) => ({ date, value: prices[i] })) },
      activeIds: new Set(["us_erp_rich_weak", "us_erp_rich_div"]),
    });
    assert.equal(noOverheatOut.byRule.us_erp_rich_weak.episodeCount, 0);
    assert.equal(noOverheatOut.byRule.us_erp_rich_div.episodeCount, 0);
  });
});
