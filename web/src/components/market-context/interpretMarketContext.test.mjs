import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./interpretMarketContext.ts", import.meta.url).pathname],
  bundle: true, format: "esm", platform: "node", write: false });
const { interpretMarketContext } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const date = "2026-10-30";
const signal = (value, extra = {}) => ({ value, asOf: date, publishedAt: date, source: "synthetic test", universe: "SP500",
  frequency: "daily", quality: "verified", ...extra });
const context = (signals = {}, extra = {}) => interpretMarketContext({ market: "us", asOf: date, anchorUniverse: "SP500", signals, ...extra });
const candidate = (result, id) => result.candidates.find(row => row.id === id);

test("missing inputs never create a complete candidate or a fictitious fact", () => {
  const result = context();
  assert.ok(result.candidates.every(row => row.status === "unknown" && row.facts.length === 0));
  assert.ok(result.layers.every(row => row.facts.length === 0 && row.missing.length > 0));
});

test("cross-pool, late and monthly observations remain background, not synchronous confirmation", () => {
  const result = context({
    trend: signal(1),
    breadth50: signal(35, { previous: 28, universe: "CN_ALL_A" }),
    hyOasChange20d: signal(-0.1, { publishedAt: "2026-11-02" }),
    financingFlow: signal(10, { frequency: "monthly" }),
  });
  const rising = candidate(result, "rising_broad");
  assert.equal(rising.status, "partial");
  assert.deepEqual(rising.facts, ["原趋势向上"]);
  assert.match(rising.missing.join(" "), /跨池背景|之后才可知/);
  assert.match(result.layers.find(row => row.id === "leverage").facts.join(" "), /monthly资料，不作日频同池确认/);
});

test("opposing trend and participation cannot both be called broadening", () => {
  const result = context({ trend: signal(1), breadth50: signal(55, { previous: 60 }) });
  assert.equal(candidate(result, "rising_broad").status, "conflicted");
  assert.equal(candidate(result, "rising_narrow_crowded").status, "partial");
  assert.match(candidate(result, "rising_narrow_crowded").missing.join(" "), /换手|融资买入/);
});

test("falling volatility with low breadth is only partial; rolling-window counterexample remains", () => {
  const result = context({
    breadth50: signal(18, { previous: 16, percentile: 10 }),
    erp: signal(3.2, { previous: 3.1, percentile: 90 }),
    hv20: signal(26, { previous: 33, unit: "%", comparison: "较前5日" }),
    hv20Percentile: signal(90),
    hyOasChange20d: signal(-0.1),
  });
  const repair = candidate(result, "low_repair");
  assert.equal(repair.status, "partial");
  assert.match(repair.counterevidence.join(" "), /滚出窗口/);
  assert.match(repair.missing.join(" "), /盈利预期|原趋势/);
  assert.doesNotMatch(repair.interpretation, /底部已确认|买入/);
});

test("qualified pressure has priority as risk observation and never proposes automatic action", () => {
  const result = context({
    trend: signal(-1), breadth50: signal(21, { previous: 30 }),
    hv20: signal(31, { previous: 25, unit: "%" }), hv20Percentile: signal(90, { previous: 70 }),
    hyOasChange20d: signal(0.4, { universe: "US_CREDIT", scope: "market_context", market: "us" }),
    financingFlow: signal(8, { percentile: 75 }), financingBalanceChange20d: signal(-4),
  });
  const pressure = candidate(result, "falling_funding_pressure");
  assert.equal(pressure.status, "supported");
  assert.equal(result.candidates[0].id, "falling_funding_pressure");
  assert.equal(candidate(result, "rising_broad").status, "conflicted");
  assert.match(pressure.counterevidence.join(" "), /主动还款/);
  assert.doesNotMatch(JSON.stringify(result), /自动减仓|自动止损|必然下跌/);
  assert.match(result.limitations.join(" "), /不触发仓位/);
});

test("current provisional facts stay visible but cannot complete a candidate", () => {
  const result = context({
    trend: signal(1, { publishedAt: undefined, quality: "provisional" }),
    breadth50: signal(60, { previous: 50, unit: "%", comparison: "较前5日" }),
    hyOasChange20d: signal(-0.1, { universe: "US_CREDIT", scope: "market_context", market: "us",
      asOf: "2026-10-29", publishedAt: "2026-10-30" }),
  });
  assert.match(result.layers.find(row => row.id === "participation").facts.join(" "), /原趋势方向 向上.*首次可知时间未核/);
  assert.match(result.layers.find(row => row.id === "participation").facts.join(" "), /较前5日上升/);
  assert.equal(candidate(result, "rising_broad").status, "partial");
  assert.match(candidate(result, "rising_broad").missing.join(" "), /尚未核准|首次可知时间未核|慢变量/);
});

test("China funding uses qualified DR policy context rather than US credit", () => {
  const asOf = "2026-11-02";
  const cn = (value, extra = {}) => signal(value, { asOf, publishedAt: asOf, universe: "CSI300", ...extra });
  const result = interpretMarketContext({ market: "cn", asOf, anchorUniverse: "CSI300", signals: {
    trend: cn(-1), breadth50: cn(18, { previous: 25 }), hv20: cn(30, { previous: 24 }),
    dr007OmoSpread: cn(0.2, { scope: "market_context", market: "cn", universe: "CN_INTERBANK",
      policyReference: { rate: 1.3, effectiveOn: asOf, verifiedFor: asOf, basis: "synthetic same-day policy", verified: true } }),
  } });
  const pressure = candidate(result, "falling_funding_pressure");
  assert.equal(pressure.status, "partial");
  assert.match(pressure.facts.join(" "), /银行间资金价差高于政策参照/);
  assert.doesNotMatch(pressure.missing.join(" "), /HY OAS/);
  assert.match(pressure.missing.join(" "), /融资买入占比/);
});

test("DR007 spread requires a verified policy reference for the applicable regime", () => {
  const asOf = "2026-11-02";
  const base = signal(0.12, { asOf, publishedAt: asOf, universe: "CN_INTERBANK" });
  const withoutPolicy = interpretMarketContext({ market: "cn", asOf, anchorUniverse: "CN_INTERBANK",
    signals: { dr007OmoSpread: base } });
  assert.match(withoutPolicy.layers.find(row => row.id === "stress").missing.join(" "), /招标机制未核/);
  assert.doesNotMatch(withoutPolicy.layers.find(row => row.id === "stress").facts.join(" "), /DR007/);
  const withPolicy = interpretMarketContext({ market: "cn", asOf, anchorUniverse: "CN_INTERBANK",
    signals: { dr007OmoSpread: { ...base, policyReference: { rate: 1.3, effectiveOn: asOf, verifiedFor: asOf,
      basis: "synthetic verified reference for test", verified: true } } } });
  assert.match(withPolicy.layers.find(row => row.id === "stress").facts.join(" "), /政策参照1.3/);
});

test("low repair requires high HV position, actual HV decline and ratio falling from above one", () => {
  const signals = {
    trend: signal(1), breadth50: signal(18, { previous: 16, percentile: 10 }),
    erp: signal(3.2, { percentile: 90 }), hv20: signal(29, { previous: 35, unit: "%" }),
    hv20Percentile: signal(88), hv20Hv60Ratio: signal(1.08, { previous: 1.21 }),
    hyOasChange20d: signal(-0.1), earningsRevisionBreadth: signal(4, { unit: "个百分点" }),
  };
  assert.equal(candidate(context(signals), "low_repair").status, "supported");
  const noRatioComparison = candidate(context({ ...signals, hv20Hv60Ratio: signal(1.08) }), "low_repair");
  assert.equal(noRatioComparison.status, "partial");
  assert.match(noRatioComparison.missing.join(" "), /HV20\/HV60缺少可比前值/);
  assert.equal(candidate(context({ ...signals, hv20Percentile: signal(70) }), "low_repair").status, "conflicted");
});

test("rising narrow and crowded needs financing balance growth, not only high financing flow", () => {
  const signals = {
    trend: signal(1), breadth50: signal(55, { previous: 63 }), erp: signal(2, { previous: 2.3 }),
    turnoverPercentile: signal(88, { percentile: 88 }), financingFlow: signal(12, { percentile: 90 }),
    earningsRevisionBreadth: signal(2),
  };
  assert.equal(candidate(context(signals), "rising_narrow_crowded").status, "partial");
  assert.match(candidate(context(signals), "rising_narrow_crowded").missing.join(" "), /融资余额20日变化/);
  assert.equal(candidate(context({ ...signals, financingBalanceChange20d: signal(-2) }), "rising_narrow_crowded").status, "conflicted");
  assert.equal(candidate(context({ ...signals, financingBalanceChange20d: signal(2) }), "rising_narrow_crowded").status, "supported");
});

test("known net earnings downgrades oppose low repair and rising broadening", () => {
  const base = {
    trend: signal(1), breadth50: signal(18, { previous: 16, percentile: 10 }),
    erp: signal(3.2, { percentile: 90 }), hv20: signal(29, { previous: 35 }),
    hv20Percentile: signal(88), hv20Hv60Ratio: signal(1.08, { previous: 1.21 }),
    hyOasChange20d: signal(-0.1),
  };
  const repair = candidate(context({ ...base, earningsRevisionBreadth: signal(-6, { unit: "个百分点" }) }), "low_repair");
  assert.equal(repair.status, "conflicted");
  assert.match(repair.counterevidence.join(" "), /-6个百分点.*净下修/);
  const broad = candidate(context({ trend: signal(1), breadth50: signal(65, { previous: 55 }),
    hyOasChange20d: signal(-0.1), earningsRevisionBreadth: signal(-3) }), "rising_broad");
  assert.equal(broad.status, "conflicted");
  assert.match(broad.counterevidence.join(" "), /-3.*净下修/);
  const unknown = candidate(context({ ...base }), "low_repair");
  assert.equal(unknown.status, "partial");
  assert.match(unknown.missing.join(" "), /盈利预期修正广度缺少有效读数/);
});
