import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./model.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { buildAlertSnapshot, eventLabel, parseSeen, serializeSeen } = await import(
  `data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

const point = (date, event = "none", phase = "middle", value = 1, lower = 0, upper = 2) =>
  ({ date, value, lower, upper, phase, event });
const input = (points, extra = {}) => ({ id: "erp-cn-v1", label: "股债收益差", kind: "erp",
  method: "沪深300周频3年轨道", historicalOnly: false, points, ...extra });
const now = "2026-11-02";

test("first visit reports only a fresh latest trigger; stay never repeats", () => {
  const old = point("2026-10-20", "enter_low", "low", -1);
  const current = point("2026-11-01", "enter_high", "high", 3);
  const snapshot = buildAlertSnapshot(input([old, current]), now);
  assert.equal(snapshot.quality, "ready");
  assert.deepEqual(snapshot.newEvents, [current]);
  assert.deepEqual(snapshot.lastEvent, current);
  assert.equal(snapshot.positionLabel, "上轨外·相对便宜");
  assert.deepEqual(buildAlertSnapshot(input([old, point("2026-11-01", "stay_high", "high", 3)]), now).newEvents, []);
});

test("same-date read cursor deduplicates and same-date revision is informational only", () => {
  const current = point("2026-11-01", "enter_high", "high", 3);
  const first = buildAlertSnapshot(input([current]), now);
  const seen = { date: current.date, fingerprint: first.fingerprint };
  assert.deepEqual(buildAlertSnapshot(input([current]), now, seen).newEvents, []);
  const revised = buildAlertSnapshot(input([point(current.date, "enter_high", "high", 3.5)]), now, seen);
  assert.equal(revised.revised, true);
  assert.deepEqual(revised.newEvents, []);
  assert.notEqual(revised.fingerprint, seen.fingerprint);
  assert.equal(buildAlertSnapshot(input([current], { method: "更新的方法版本" }), now, seen).revised, true);
});

test("later dates can carry two fresh entry or exit events, never old history or stays", () => {
  const rows = [point("2026-10-20", "enter_low", "low", -1),
    point("2026-10-27", "exit_low"), point("2026-10-29", "stay_high", "high", 3),
    point("2026-11-01", "enter_high", "high", 3)];
  const result = buildAlertSnapshot(input(rows), now, { date: "2026-10-20", fingerprint: "previous" });
  assert.deepEqual(result.newEvents.map(x => x.date), ["2026-10-27", "2026-11-01"]);
  assert.deepEqual(buildAlertSnapshot(input(rows), now).newEvents.map(x => x.date), ["2026-11-01"]);
});

test("missing values, rails, invalid calendar dates, future and unordered data cannot alert", () => {
  const bad = [point("2026-11-01", "enter_high", "high", null),
    point("2026-11-01", "enter_high", "high", Infinity),
    point("2026-11-01", "enter_high", "high", 3, null),
    point("2026-11-01", "enter_high", "high", 3, 3, 2),
    point("2026-11-03", "enter_high", "high", 3),
    point("2026-02-30", "enter_high", "high", 3)];
  for (const row of bad) {
    const snapshot = buildAlertSnapshot(input([row]), now);
    assert.equal(snapshot.quality, "missing");
    assert.deepEqual(snapshot.newEvents, []);
  }
  for (const rows of [[point("2026-11-01"), point("2026-11-01", "enter_high", "high", 3)],
    [point("2026-11-01"), point("2026-10-31", "enter_high", "high", 3)]]) {
    const snapshot = buildAlertSnapshot(input(rows), now);
    assert.equal(snapshot.quality, "missing");
    assert.equal(snapshot.latest, null);
    assert.deepEqual(snapshot.newEvents, []);
  }
});

test("historical, stale, rollback and failed fetch suppress alerts even with cached points", () => {
  const current = point("2026-11-01", "enter_high", "high", 3);
  const history = buildAlertSnapshot(input([current], { historicalOnly: true }), now);
  assert.equal(history.quality, "historical");
  assert.deepEqual(history.newEvents, []);
  assert.deepEqual(history.lastEvent, current);
  assert.equal(buildAlertSnapshot(input([], { historicalOnly: true }), now).quality, "missing");
  assert.equal(buildAlertSnapshot(input([point("2026-11-03", "enter_high", "high", 3)],
    { historicalOnly: true }), now).quality, "missing");
  assert.equal(buildAlertSnapshot(input([current], { loadError: true }), now).quality, "error");
  assert.equal(buildAlertSnapshot(input([], { historicalOnly: true, loadError: true }), now).quality, "error");
  assert.deepEqual(buildAlertSnapshot(input([current], { loadError: true }), now).newEvents, []);
  assert.equal(buildAlertSnapshot(input([point("2026-10-25", "enter_high", "high", 3)]), now).quality, "stale");
  const rollback = buildAlertSnapshot(input([current]), now, { date: "2026-11-02", fingerprint: "later" });
  assert.equal(rollback.quality, "stale");
  assert.match(rollback.qualityLabel, /早于/);
  assert.deepEqual(rollback.newEvents, []);
});

test("flat is displayable, and names describe supplier events without financial recomputation", () => {
  const flat = buildAlertSnapshot(input([point("2026-11-01", "none", "flat", 2, 2, 2)]), now);
  assert.equal(flat.quality, "ready");
  assert.equal(flat.positionLabel, "轨道重合");
  assert.deepEqual(flat.newEvents, []);
  const contradictory = buildAlertSnapshot(input([point("2026-11-01", "enter_high", "flat", 2, 2, 2)]), now);
  assert.equal(contradictory.quality, "missing");
  assert.deepEqual(contradictory.newEvents, []);
  assert.equal(contradictory.lastEvent, null);
  assert.equal(buildAlertSnapshot(input([point("2026-11-01", "enter_low", "low", -1)],
    { kind: "breadth" }), now).positionLabel, "历史低位");
  assert.equal(eventLabel("erp", "exit_high"), "回到上轨内");
  assert.equal(eventLabel("breadth", "enter_low"), "进入历史低位");
  assert.match(eventLabel("breadth", "stay_low"), /持续/);
});

test("contradictory phase and event pairs are missing rather than fresh crossings", () => {
  const invalid = [
    point("2026-11-01", "enter_high", "low", 3),
    point("2026-11-01", "enter_low", "high", -1),
    point("2026-11-01", "exit_high", "high", 1),
    point("2026-11-01", "exit_low", "low", 1),
    point("2026-11-01", "stay_high", "middle", 1),
    point("2026-11-01", "stay_low", "middle", 1),
    point("2026-11-01", "none", "high", 2, 2, 2),
    point("2026-11-01", "none", "flat", 1, 0, 2),
  ];
  for (const row of invalid) {
    const result = buildAlertSnapshot(input([row]), now);
    assert.equal(result.quality, "missing", JSON.stringify(row));
    assert.deepEqual(result.newEvents, []);
  }
  assert.equal(buildAlertSnapshot(input([point("2026-11-01", "exit_high")]), now).quality, "ready");
});

test("storage format filters corrupt versions, dates, types and individual cursors", () => {
  assert.deepEqual(parseSeen(null), {});
  assert.deepEqual(parseSeen("bad JSON"), {});
  assert.deepEqual(parseSeen('{"version":2,"seen":{"erp":{"date":"2026-11-01","fingerprint":"x"}}}'), {});
  assert.deepEqual(parseSeen('{"version":1,"seen":[]}'), {});
  const raw = JSON.stringify({ version: 1, seen: {
    erp: { date: "2026-11-01", fingerprint: "abc" },
    invalidDate: { date: "2026-02-30", fingerprint: "bad" },
    invalidType: { date: "2026-11-01", fingerprint: 3 },
  } });
  assert.deepEqual(parseSeen(raw), { erp: { date: "2026-11-01", fingerprint: "abc" } });
  assert.deepEqual(parseSeen(serializeSeen({ erp: { date: "2026-11-01", fingerprint: "abc" },
    bad: { date: "2026-02-30", fingerprint: "x" } })), { erp: { date: "2026-11-01", fingerprint: "abc" } });
});
