import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const result = await build({ entryPoints: [new URL("./conditionalReading.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { conditionalReading, marketReading, marketConnections } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);

test("low breadth plus ordinary non-expanding volatility yields a qualified explanation", () => {
  const reading = conditionalReading({ breadth50: 21, breadthLow: 24, hvRatio: .9, hvPercentile: 50 });
  assert.equal(reading.length, 1);
  assert.match(reading[0], /上涨支撑偏弱/);
});

test("expanding short volatility below local high rail and falling financing remain separate", () => {
  const reading = conditionalReading({ hvRatio: 1.1, hvPercentile: 65, financingChange: -100 });
  assert.equal(reading.length, 2);
  assert.match(reading[0], /短期波动高于中期/);
  assert.match(reading[1], /融资余额在下降/);
});

test("unknown breadth or percentile cannot be treated as neutral evidence", () => {
  assert.deepEqual(conditionalReading({ breadth50: 20, breadthLow: 24, hvRatio: .8 }), []);
  assert.deepEqual(conditionalReading({ breadth50: 20, breadthLow: null, hvRatio: .8, hvPercentile: 40 }), []);
});

test("high financing ratio with falling balance is not labelled increasing leverage", () => {
  const r = marketReading({ market: "cn", breadth50: 11.37, breadthLow: 18.63,
    hvPercentile: 53.17, hvRatio: .986, financingPercentile: 87.3, financingChange: -2925.78 });
  assert.match(r.headline, /参与面低迷、融资收缩/);
  assert.match(r.meaning, /上涨支撑不足/);
  assert.match(r.conflict, /近期融资债务在收缩/);
});

test("majority participation and low ERP describe a conflict, not an unconditional bullish state", () => {
  const r = marketReading({ market: "us", breadth50: 62, erp: -.98, erpLow: -.84, hyChange20: .02 });
  assert.match(r.headline, /估值缓冲偏薄/);
  assert.match(r.conflict, /走阔幅度及持续时间/);
  assert.match(r.watch, /两者同时恶化/);
});

test("unknown or non-finite data must not establish benign volatility or high leverage", () => {
  const unknown = marketReading({ market: "cn", breadth50: NaN, financingPercentile: 90 });
  assert.match(unknown.headline, /资料待补/);
  const weak = marketReading({ market: "cn", breadth50: 11, breadthLow: 18 });
  assert.doesNotMatch(weak.meaning, /尚未进入自身历史高位/);
  assert.doesNotMatch(weak.conflict, /余额正在下降/);
});

test("weak participation with high and expanding volatility does not claim panic completion", () => {
  const r = marketReading({ market: "cn", breadth50: 10, breadthLow: 20, hvPercentile: 90, hvRatio: 1.5 });
  assert.match(r.meaning, /两项压力叠加/);
});

test("a rebound within the low breadth zone retains the improvement rather than claiming continued deterioration", () => {
  const r = marketReading({ market: "cn", breadth50: 15, breadthLow: 20, breadthChange20: 3 });
  assert.match(r.meaning, /已有回升/);
});


test("connections separate historical volatility level from the short/long ratio", () => {
  const base = { market: "cn", breadth50: 11, breadthLow: 18, hv20: 13 };
  const middle = marketConnections({ ...base, hvPercentile: 53, hvRatio: .99 });
  assert.equal(middle.chains[0].id, "participation-volatility");
  assert.match(middle.chains[0].facts[1].text, /历史分位53.00%/);
  assert.doesNotMatch(middle.chains[0].meaning, /阴跌|放量|已经出清/);
  const high = marketConnections({ ...base, hvPercentile: 95, hvRatio: .8 });
  assert.match(high.chains[0].meaning, /仍在高位/);
  assert.doesNotMatch(high.chains[0].meaning, /从高位回落/);
});

test("credit conflict is conditional on participation direction, never just its level", () => {
  const base = { market: "us", breadth50: 62, hyChange20: .34, hyDate: "2026-10-30" };
  assert.equal(marketConnections(base).chains.some(x => x.id === "participation-credit"), false);
  const up = marketConnections({ ...base, breadthChange20: 37.8 });
  const down = marketConnections({ ...base, breadthChange20: -10 });
  assert.match(up.chains[0].meaning, /股市修复与信用压力并存/);
  assert.match(down.chains[0].meaning, /两项压力同向/);
  assert.match(up.chains[0].facts[1].text, /34.00基点/);
});

test("high leverage level and falling balance do not imply denominator cause or inflow", () => {
  const reading = marketConnections({ market: "cn", financingRatio: 2.58, financingPercentile: 90,
    financingChange: -100, financingBalanceChangePct: -10.81, financingRatioChange: -.1,
    financingPreviousDate: "2026-09-28", financingDate: "2026-11-02", financingBalanceDate: "2026-11-02" });
  const chain = reading.chains.find(x => x.id === "leverage-stock-flow");
  assert.match(chain.meaning, /近期融资使用减少/);
  assert.doesNotMatch(chain.meaning, /导致|缩水|实为流出/);
  assert.match(chain.facts[0].text, /2026-09-28/);
  assert.doesNotMatch(chain.facts[1].text, /2026-09-28/); // the other source has no verified comparison date
});

test("missing observations never make a valid combination or a fabricated number", () => {
  const reading = marketConnections({ market: "us", breadth50: NaN, hv20: 10, hvRatio: 1,
    hvPercentile: undefined, vix: 20, vixHigh: 19, erp: null });
  assert.deepEqual(reading.chains, []);
  assert.match(reading.headline, /资料待补/);
});

test("valuation in its reference range is not promoted to an extreme cheap opportunity", () => {
  const reading = marketConnections({ market: "cn", breadth50: 11.37, breadthLow: 18.63,
    erp: 6.12, erpLow: 4.78, erpHigh: 7.02 });
  assert.match(reading.chains[0].facts[1].text, /4.78～7.02/);
  assert.match(reading.chains[0].meaning, /历史中间区/);
  assert.doesNotMatch(reading.chains[0].meaning, /近高位|黄金坑/);
});

test("VIX and historical volatility retain separate dates and do not predict a direction", () => {
  const reading = marketConnections({ market: "us", hv20: 10.14, hvRatio: 1.08, hvPercentile: 27.65,
    hvDate: "2026-10-29", vix: 21.15, vixHigh: 20.48, vixDate: "2026-11-02" });
  const chain = reading.chains.find(x => x.id === "realized-expected-volatility");
  assert.deepEqual(chain.facts.map(x => x.date), ["2026-10-29", "2026-11-02"]);
  assert.match(chain.meaning, /未来起伏较大/);
  assert.doesNotMatch(chain.meaning, /超前|必然|即将下跌/);
});
