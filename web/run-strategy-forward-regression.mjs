import assert from "node:assert/strict";
import { build } from "esbuild";

const bundled = await build({ entryPoints: [new URL("./src/components/strategy-forward/viewModel.ts", import.meta.url).pathname], bundle: true, platform: "node", format: "esm", write: false });
const model = await import(`data:text/javascript;base64,${Buffer.from(bundled.outputFiles[0].text).toString("base64")}`);
const account = (id, series = [], status = "observing") => ({ id, name: id, kind: "buy_hold", role: "passive_baseline", status, reasons: [], rules: {}, frozen_at: null, started_at: null, first_decision_at: null, first_fill_at: null, metrics: { cumulative_return_pct: null, annualized_return_pct: null, sharpe: null, max_drawdown_pct: null, observations: 0, reason: "no_valid_eod_valuation" }, series, holdings: [], orders: [] });
const point = (date, nav, overrides = {}) => ({ date, nav, valid: true, stale: false, equity: 100000, cash: 100000, receivable: 0, market_value: 0, drawdown_pct: 0, exposure_pct: 0, fees: 0, source_time: `${date}T15:00:00+08:00`, provisional: false, ...overrides });
const dashboard = (accounts, decisions = []) => ({ schema_version: 1, generated_at: "2026-10-20T16:00:00+08:00", range: "since_start", run: { status: "not_started" }, accounts, decisions, health: [], sources: [], pending: [] });

const blocked = account("lei-original-a", [point("2026-10-20", 1)], "blocked");
const empty = dashboard([account("cash-reference-v1"), blocked]);
assert.deepEqual(model.plottedAccounts(empty, ["cash-reference-v1"]), []);
assert.equal(model.metricText(null, "no_valid_eod_valuation"), "尚无有效收盘估值");
assert.equal(model.accountStatus("blocked"), "规则待补");
assert.deepEqual(model.plottedAccounts(empty, ["lei-original-a"]), []);

const valid = account("baseline", [point("2026-10-20", 1), point("2026-10-21", 1.02), point("2026-10-22", 1.03, { stale: true })]);
const later = account("cash", [point("2026-10-21", 1), point("2026-10-23", null)]);
const live = dashboard([valid, later]);
assert.deepEqual(model.plotDates(model.plottedAccounts(live, ["baseline", "cash"])), ["2026-10-20", "2026-10-21"]);
assert.deepEqual(model.chartValues(valid, ["2026-10-20", "2026-10-21", "2026-10-22"], "nav"), [1, 1.02, null]);
assert.deepEqual(model.chartValues(later, ["2026-10-20", "2026-10-21"], "nav"), [null, 1]);
assert.equal(model.firstUsableDay(live, ["baseline", "cash"]), "2026-10-23");
assert.equal(model.metricText(null, "insufficient_duration_or_variation"), "观察时间不足或波动为零");
assert.equal(model.metricText(0, null), "0%");

const sameDay = dashboard([valid], [{ id: "1", at: "2026-10-21T15:00:00+08:00", account_id: "baseline", kind: "wait", payload: {} }, { id: "2", at: "2026-10-21T15:00:00+08:00", account_id: "cash", kind: "wait", payload: {} }]);
assert.equal(model.dayDecisions(sameDay, "2026-10-21", ["baseline"]).length, 1);
assert.equal(model.dayDecisions(sameDay, "2026-10-20", ["baseline"]).length, 0);
const preValuation = dashboard([account("baseline")], [
  { id: "queued", at: "2026-10-20T08:00:00Z", account_id: "baseline", kind: "order_queued", payload: { order_id: "opaque" } },
  { id: "global-wait", at: "2026-10-20T08:01:00Z", account_id: null, kind: "waiting", payload: { reasons: ["stale_quote"] } },
]);
assert.deepEqual(model.availableDays(preValuation, ["baseline"]), ["2026-10-20"]);
assert.equal(model.firstUsableDay(preValuation, ["baseline"]), "2026-10-20");
assert.equal(model.dayDecisions(preValuation, "2026-10-20", ["baseline"]).length, 2);
assert.equal(model.dayInShanghai("2026-10-19T16:30:00Z"), "2026-10-20");
assert.equal(model.eventText("order_queued"), "订单已排队");
assert.equal(model.orderStatusText("partial"), "部分成交");
assert.deepEqual(model.decisionReasons({ reasons: ["stale_quote", "stale_quote"] }), ["报价到达或使用时已过期"]);
assert.equal(model.runnerView({ runner: null }, "2026-10-20T08:00:00Z").label, "未记录持续运行");
assert.equal(model.runnerView({ runner: { status: "waiting", heartbeat_at: "2026-10-20T07:59:40Z" } }, "2026-10-20T08:00:00Z").tone, "is-live");
assert.equal(model.runnerView({ runner: { status: "waiting", heartbeat_at: "2026-10-20T07:55:00Z" } }, "2026-10-20T08:00:00Z").tone, "is-alert");
assert.equal(model.runnerView({ runner: { status: "error", last_error: "quote failed" } }, "2026-10-20T08:00:00Z").label, "持续运行报错");
assert.equal(model.runnerView({ runner: { status: "waiting", pid_alive: false, heartbeat_at: "2026-10-20T07:59:40Z" } }, "2026-10-20T08:00:00Z").tone, "is-alert");
assert.equal(model.displayNumber(4.002, " 元", 6), "4.002 元");
const missingDay = account("baseline", [point("2026-10-20", 1), point("2026-10-22", 1.03)]);
const gapDates = model.plotDates([missingDay]);
assert.deepEqual(gapDates, ["2026-10-20", "2026-10-21", "2026-10-22"]);
assert.deepEqual(model.chartValues(missingDay, gapDates, "nav"), [1, null, 1.03]);
const common = dashboard([account("baseline", [point("2026-10-21", 1)]), account("cash", [point("2026-10-21", 1)])]);
common.range = "common";
assert.deepEqual(model.plotDates(model.plottedAccounts(common, ["baseline", "cash"])), ["2026-10-21"]);
console.log("strategy forward view-model regression: passed");
