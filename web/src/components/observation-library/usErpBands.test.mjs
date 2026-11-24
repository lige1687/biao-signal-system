import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./usErpBands.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { usErpBands, usErpEvents } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

const day = (date, offset) => new Date(Date.parse(`${date}T00:00:00Z`) + offset * 86_400_000).toISOString().slice(0, 10);
const history = (start, count, value = index => index % 2 === 0 ? 0 : 2) =>
  Array.from({ length: count }, (_, index) => ({ date: day(start, index), value: value(index) }));
const row = (date, value, sigma = 1) => ({ date, value, middle: 5, sigma,
  upper: 5 + 2 * sigma, lower: 5 - 2 * sigma, z: sigma ? (value - 5) / sigma : null, n: 500 });

test("prior three-calendar-year window includes cutoff, excludes current, and uses population sigma", () => {
  const points = [...history("2023-01-01", 500), { date: "2026-01-01", value: 3 }];
  const result = usErpBands(points);
  const last = result.at(-1);
  assert.equal(last.n, 500);
  assert.equal(last.middle, 1);
  assert.equal(last.sigma, 1);
  assert.equal(last.upper, 3);
  assert.equal(last.lower, -1);
  assert.equal(last.z, 2);
  assert.equal(result[499].middle, null);
  assert.deepEqual(usErpBands([...points, { date: "2026-01-02", value: 100 }]).slice(0, -1), result);
  assert.equal(usErpBands([...points.slice(0, -1), { date: "2026-01-01", value: 100 }]).at(-1).middle, 1);
  assert.equal(usErpBands(points).at(-1).n, 500);
});

test("January cutoff and leap-day February 28 mapping keep calendar boundaries", () => {
  const jan = [...history("2023-01-01", 500), { date: "2026-01-02", value: 3 }];
  assert.equal(usErpBands(jan).at(-1).middle, null); // Jan 1 is outside; only 499 prior records.
  const leap = [...history("2021-02-28", 500), { date: "2024-02-29", value: 3 }];
  assert.equal(usErpBands(leap).at(-1).n, 500);
  assert.equal(usErpBands(leap).at(-1).middle, 1);
  assert.equal(usErpBands(leap.slice(1)).at(-1).middle, null);
});

test("missing, duplicate, unsorted, and nonfinite inputs fail or blank explicitly", () => {
  const prior = history("2023-01-01", 500);
  const target = { date: "2026-01-01", value: 3 };
  assert.equal(usErpBands([...prior.slice(0, 20), { ...prior[20], value: null }, ...prior.slice(21), target]).at(-1).upper, null);
  assert.equal(usErpBands([...prior, { ...target, value: null }]).at(-1).upper, null);
  assert.throws(() => usErpBands([...prior, prior.at(-1)]));
  assert.throws(() => usErpBands([prior[1], prior[0]]));
  assert.throws(() => usErpBands([{ date: "2026-02-30", value: 1 }]));
  assert.throws(() => usErpBands([{ date: "2026-01-01", value: Infinity }]));
});

test("500 records guard and zero variance leave no fabricated extreme", () => {
  const short = [...history("2023-01-01", 499), { date: "2026-01-01", value: 3 }];
  assert.equal(usErpBands(short).at(-1).upper, null);
  const flat = usErpBands([...history("2023-01-01", 500, () => 1), { date: "2026-01-01", value: 3 }]).at(-1);
  assert.equal(flat.upper, 1);
  assert.equal(flat.lower, 1);
  assert.equal(flat.z, null);
  assert.deepEqual(usErpEvents([row("2026-01-01", 1, 0), { ...flat, date: "2026-01-02" }], [1.5, 2]), []);
});

test("same-day crossings retain each sigma; equality alone and first valid row do not cross", () => {
  const events = usErpEvents([row("2026-10-09", 5), row("2026-10-16", 7.5)], [1.5, 2, 2]);
  assert.deepEqual(events.map(event => event.id), ["1.5:2026-10-16:upper", "2:2026-10-16:upper"]);
  assert.deepEqual(events.map(event => event.upper), [6.5, 7]);
  assert.deepEqual(usErpEvents([row("2026-10-16", 7.5)], [2]), []);
  assert.deepEqual(usErpEvents([row("2026-10-09", 7), row("2026-10-16", 7)], [2]), []);
  assert.deepEqual(usErpEvents([row("2026-10-09", 4), row("2026-10-16", 2.5)], [1.5, 2]).map(event => event.kind), ["lower", "lower"]);
});

test("missing values, unresolved bands, and gaps over seven days reset crossing state", () => {
  assert.deepEqual(usErpEvents([row("2026-10-02", 5), { ...row("2026-10-09", 5), value: null }, row("2026-10-16", 8)], [2]), []);
  assert.deepEqual(usErpEvents([row("2026-10-02", 5), { ...row("2026-10-09", 5), middle: null }, row("2026-10-16", 8)], [2]), []);
  assert.deepEqual(usErpEvents([row("2026-10-02", 5), row("2026-10-10", 8)], [2]), []);
  assert.equal(usErpEvents([row("2026-10-09", 5), row("2026-10-16", 8)], [2]).length, 1);
});
