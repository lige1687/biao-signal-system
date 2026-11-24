import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./usErpMarkerGroups.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { groupUsErpMarkers } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

const dates = ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05"];
const event = (date, sigma = 1.5, kind = "upper") => ({ id: `${sigma}:${date}:${kind}`, date, sigma, kind,
  value: 8, upper: 7, middle: 5, lower: 3 });

test("span is anchored to the first member, never chained indefinitely", () => {
  const raw = [event(dates[3]), event(dates[1]), event(dates[2]), event(dates[0])];
  const groups = groupUsErpMarkers(raw, dates, 2);
  assert.deepEqual(groups.map(group => [group.representative.date, group.endDate, group.count]), [
    [dates[0], dates[2], 3], [dates[3], dates[3], 1],
  ]);
  assert.deepEqual(groups.flatMap(group => group.members.map(member => member.id)),
    [dates[0], dates[1], dates[2], dates[3]].map(date => `1.5:${date}:upper`));
});

test("opposite-kind event starts a new group even within the span", () => {
  const groups = groupUsErpMarkers([event(dates[0]), event(dates[1], 1.5, "lower"), event(dates[2])], dates, 3);
  assert.deepEqual(groups.map(group => [group.representative.kind, group.count]),
    [["upper", 1], ["lower", 1], ["upper", 1]]);
});

test("same-date thresholds are retained; representative prefers highest sigma only on earliest date", () => {
  const firstInner = event(dates[0], 1.5), firstOuter = event(dates[0], 2);
  const laterOuter = event(dates[1], 2);
  const groups = groupUsErpMarkers([laterOuter, firstInner, firstOuter], dates, 2);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].representative, firstOuter);
  assert.deepEqual(groups[0].members.map(member => member.id), [firstInner.id, firstOuter.id, laterOuter.id]);
  assert.equal(groups[0].count, 3);
  assert.equal(groups[0].endDate, dates[1]);
});

test("only supplied observation dates are eligible; no event is shifted to another date", () => {
  const absent = event("2026-10-01");
  const kept = event("2026-10-02");
  const groups = groupUsErpMarkers([absent, kept], dates.slice(1), 2);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].representative, kept);
  assert.deepEqual(groups[0].members.map(member => member.date), [kept.date]);
});

test("duplicate ids are deduplicated while original events and inputs stay unchanged", () => {
  const first = Object.freeze(event(dates[0]));
  const second = Object.freeze(event(dates[1], 2));
  const inputs = Object.freeze([second, first, first]);
  const axis = Object.freeze([...dates]);
  const before = structuredClone(inputs);
  const groups = groupUsErpMarkers(inputs, axis, 2);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].count, 2);
  assert.deepEqual(groups[0].members, [first, second]);
  assert.equal(groups[0].members[0], first);
  assert.deepEqual(inputs, before);
  assert.deepEqual(axis, dates);
});

test("empty and invalid spans fall back to one observation", () => {
  assert.deepEqual(groupUsErpMarkers([], dates, 2), []);
  const raw = [event(dates[0]), event(dates[1]), event(dates[2])];
  for (const invalid of [0, -2, NaN, Infinity, 1.5]) {
    assert.deepEqual(groupUsErpMarkers(raw, dates, invalid).map(group => group.count), [2, 1]);
  }
});
