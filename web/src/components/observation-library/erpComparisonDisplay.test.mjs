import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
const bundle = await build({ stdin: { contents: 'export * from "./src/components/observation-library/erpComparisonDisplay.ts";', resolveDir: process.cwd() }, bundle: true, platform: 'node', format: 'esm', write: false });
const { comparedErpEvents, erpEventMarkers, innerErpRails, hasErpPriceHistory } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString('base64')}`);
const row = (date, value) => ({ date, value, middle: 5, sigma: 1, upper: 7, lower: 3, n: 150, z: value - 5 });
test('a jump across both thresholds keeps both events independently selectable', () => {
  const rows = [row('2026-10-09', 5), row('2026-10-16', 7.5)];
  const before = structuredClone(rows);
  const events = comparedErpEvents(rows, [1.5, 2, 2]);
  assert.deepEqual(events.map(e => e.id), ['1.5:2026-10-16:upper', '2:2026-10-16:upper']);
  assert.deepEqual(events.map(e => e.upper), [6.5, 7]);
  assert.deepEqual(rows, before);
});
test('shallower observation can occur before the extreme event; equality alone is not a crossing', () => {
  const events = comparedErpEvents([row('2026-10-02', 5), row('2026-10-09', 6.5), row('2026-10-16', 6.8), row('2026-10-23', 7.1)], [1.5, 2]);
  assert.deepEqual(events.map(e => [e.sigma, e.date]), [[1.5, '2026-10-16'], [2, '2026-10-23']]);
});
test('missing observations or a missing week never manufacture crossings', () => {
  assert.deepEqual(comparedErpEvents([row('2026-10-02', 5), { ...row('2026-10-09', 5), value: null }, row('2026-10-16', 8)], [1.5, 2]), []);
  assert.deepEqual(comparedErpEvents([row('2026-10-02', 5), row('2026-10-16', 8)], [1.5, 2]), []);
});
test('markers preserve both identities on the same price date, and omit unpriced weeks', () => {
  const events = comparedErpEvents([row('2026-10-09', 5), row('2026-10-16', 2.5)], [1.5, 2]);
  const markers = erpEventMarkers(events, ['2026-10-09', '2026-10-16'], [4000, 3900]);
  assert.equal(markers.length, 2);
  assert.deepEqual(markers.map(m => m.value), [['2026-10-16', 3900], ['2026-10-16', 3900]]);
  assert.equal(new Set(markers.map(m => m.eventId)).size, 2);
  assert.deepEqual(erpEventMarkers(events, ['2026-10-09', '2026-10-16'], [4000, null]), []);
  assert.deepEqual(erpEventMarkers(events, ['2026-10-17'], [3900]), []);
});
test('mini inner rails use the same supplied 2-sigma window and preserve unknowns', () => {
  assert.deepEqual(innerErpRails({ lower: 3, upper: 7 }), { lower: 3.5, upper: 6.5 });
  assert.deepEqual(innerErpRails({ lower: null, upper: 7 }), { lower: null, upper: null });
  assert.deepEqual(innerErpRails({ lower: 8, upper: 7 }), { lower: null, upper: null });
});

test('comparison requires two joint finite observations, not just a priced date axis', () => {
  assert.equal(hasErpPriceHistory([null, null], [3000, 3010]), false);
  assert.equal(hasErpPriceHistory([5, null], [null, 3010]), false);
  assert.equal(hasErpPriceHistory([5, 6], [3000, 3010]), true);
  assert.equal(hasErpPriceHistory([5, 6], [3000, NaN]), false);
});
