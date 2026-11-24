import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";
async function bundle(file) {
  const b = await build({ entryPoints: [new URL(file, import.meta.url).pathname], bundle: true, platform: "node", format: "esm", write: false });
  return import(`data:text/javascript;base64,${Buffer.from(b.outputFiles[0].text).toString("base64")}`);
}
const { parseBreadth, breadthInput, erpInput, chartLink } = await bundle("./adapters.ts");
const { buildAlertSnapshot, parseSeen } = await bundle("./model.ts");
const { acknowledge } = await bundle("./storage.ts");
const now = "2026-11-02";
function fixture() {
  const readings = [
    { date: "2026-10-29", horizons: { "50": { lower: 20, upper: 80, sample_count: 1260, status: "ready", position: "low", event: "stay_low" } } },
    { date: "2026-10-30", horizons: { "50": { lower: 20, upper: 80, sample_count: 1260, status: "ready", position: "middle", event: "exit_low" } } },
  ];
  return { market_id: "CN_ALL_A", history: [{ date: "2026-10-29", breadth_50: 19 }, { date: "2026-10-30", breadth_50: 21 }],
    observation: { method_version: "breadth.observation@1.0.0", lookback_observations: 1260, min_observations: 252,
      lower_quantile: .1, upper_quantile: .9, includes_current: true, history: readings, latest: readings[1] } };
}
test("breadth preserves its own universe, supplier event and same-date rails", () => {
  const s = buildAlertSnapshot(breadthInput("CN_ALL_A", parseBreadth(fixture(), "CN_ALL_A")), now);
  assert.equal(s.quality, "ready"); assert.equal(s.latest.value, 21); assert.equal(s.latest.lower, 20);
  assert.equal(s.newEvents[0].event, "exit_low");
  assert.throws(() => parseBreadth(fixture(), "SP500"));
});
test("unknown method, different quantiles/windows, dates and error packets fail closed", () => {
  for (const edit of [d => d.observation.method_version = "new", d => d.observation.lower_quantile = .2,
    d => d.observation.lookback_observations = 252, d => d.observation.includes_current = false,
    d => d.observation.latest = { ...d.observation.latest, date: "2026-10-31" },
    d => d.history.reverse(), d => d.observation.history.reverse(), d => d.observation.error = "failure"]) {
    const d = fixture(); edit(d); assert.throws(() => parseBreadth(d, "CN_ALL_A"));
  }
});
test("raw missing values, insufficient samples and position conflicts cannot create an event", () => {
  for (const edit of [d => d.history[1].breadth_50 = null, d => d.history[1].breadth_50 = 101,
    d => d.observation.history[1].horizons["50"].sample_count = 251,
    d => d.observation.history[1].horizons["50"].position = "high",
    d => d.observation.history[1].horizons["50"].event = "enter_high"]) {
    const d = fixture(); edit(d);
    const s = buildAlertSnapshot(breadthInput("CN_ALL_A", parseBreadth(d, "CN_ALL_A")), now);
    assert.equal(s.quality, "missing"); assert.equal(s.newEvents.length, 0);
  }
  const cached = breadthInput("CN_ALL_A", parseBreadth(fixture(), "CN_ALL_A"), true);
  assert.equal(buildAlertSnapshot(cached, now).quality, "error");
  assert.equal(buildAlertSnapshot(cached, now).newEvents.length, 0);
});
test("ERP actual reference retains 17 first crossings, reentries and historical-only boundary", async () => {
  const data = JSON.parse(await readFile(new URL("../../../public/research/erp-bands/cn-reference.json", import.meta.url), "utf8"));
  const input = erpInput(data);
  const entries = input.points.filter(p => ["enter_high", "enter_low"].includes(p.event));
  assert.equal(entries.length, 17);
  assert.ok(input.points.some(p => p.event === "exit_high"));
  assert.ok(input.points.some(p => p.event === "exit_low"));
  const snapshot = buildAlertSnapshot(input, now);
  assert.equal(snapshot.quality, "historical"); assert.equal(snapshot.newEvents.length, 0);
  assert.equal(snapshot.latest.date, "2026-10-30"); assert.equal(snapshot.latest.phase, "middle");
  assert.ok(Math.abs(snapshot.latest.value - 6.123209) < .000001);
  assert.equal(buildAlertSnapshot(erpInput(), now).quality, "missing");
});
test("seen survives reload, preserves other objects and an older tab cannot roll back", () => {
  const s = buildAlertSnapshot(breadthInput("CN_ALL_A", parseBreadth(fixture(), "CN_ALL_A")), now);
  const saved = acknowledge(null, [s]);
  assert.equal(buildAlertSnapshot(breadthInput("CN_ALL_A", fixture()), now, parseSeen(saved)[s.id]).newEvents.length, 0);
  const us = { ...s, id: "SP500:test" };
  const both = acknowledge(saved, [us]); assert.equal(Object.keys(parseSeen(both)).length, 2);
  const older = { ...s, latest: { ...s.latest, date: "2026-10-29" }, fingerprint: "older" };
  assert.equal(acknowledge(both, [older]), both);
  const revised = { ...s, fingerprint: "revision" };
  assert.equal(acknowledge(both, [revised]), both);
  for (const quality of ["historical", "stale", "missing", "error"]) {
    assert.deepEqual(parseSeen(acknowledge(null, [{ ...s, quality }])), {});
  }
});
test("each alert targets its matching existing price-and-indicator view", () => {
  assert.equal(chartLink("CN_ALL_A"), "/fundamentals?observation=breadth&market=cn#fund-sec-market");
  assert.equal(chartLink("SP500"), "/fundamentals?observation=breadth&market=us#fund-sec-market");
  assert.equal(chartLink("erp"), "/fundamentals?observation=erp-cn#fund-sec-market");
});
