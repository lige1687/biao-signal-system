import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';

const output = await build({
  entryPoints: [fileURLToPath(new URL('./src/features/market-understanding/dashboard-model.ts', import.meta.url))],
  bundle: true, platform: 'node', format: 'esm', write: false,
});
const model = await import(`data:text/javascript;base64,${Buffer.from(output.outputFiles[0].text).toString('base64')}`);
const { metrics, endpoints, decodeHistory, lastReading, windowSeries, referencesFor, formatValue, periodLabel, loadHistory } = model;
let checks = 0;
async function test(name, fn) { await fn(); checks++; console.log(`PASS ${name}`); }
const today = '2026-10-03';
const fixture = (endpoint, overrides = {}) => ({
  as_of: '2026-10-03', errors: [],
  series: Object.fromEntries(metrics.filter(m => m.endpoint === endpoint).map(m => [m.key, {
    label: m.title, unit: m.apiUnit, dates: ['2026-09-01', '2026-10-01'], values: [1, 2],
  }])), ...overrides,
});
const changed = (endpoint, key, patch) => {
  const raw = fixture(endpoint);
  raw.series[key] = {...raw.series[key], ...patch};
  return raw;
};

await test('exactly 24 unique indicators with no foreign-only leakage', () => {
  assert.equal(metrics.length, 24);
  assert.equal(new Set(metrics.map(m => m.key)).size, 24);
  for (const market of ['cn', 'us']) {
    const shown = metrics.filter(m => m.market.includes(market));
    assert.ok(shown.length > 0);
    assert.ok(shown.every(m => m.market.includes(market)));
    assert.ok(shown.every(m => !m.market.some(x => x !== market) || m.key === 'cn_us_spread_10y'));
  }
  assert.deepEqual(metrics.find(m => m.key === 'cn_us_spread_10y').market, ['cn', 'us']);
  assert.deepEqual(metrics.filter(m=>m.market.includes('cn')).map(m=>m.key).sort(),['cn_10y','cn_us_spread_10y','margin_rzrqye','margin_rzyezb','erp_cn','pe_cn','pmi','cpi','ppi'].sort());
  assert.deepEqual(metrics.filter(m=>m.market.includes('us')).map(m=>m.key).sort(),['us_10y','cn_us_spread_10y','vix','erp_us','cape_us','hy_oas','icwa','ccwa','payems_yoy','wei','hsales','cshpi_yoy','altsa','dgorder_yoy','cpiaucsl_yoy','ppiaco_yoy'].sort());
});

await test('each metric is routed to the existing endpoint with the expected source unit', () => {
  assert.deepEqual(endpoints, {
    rates: '/api/fundamentals/rates-history?lookback_days=1095',
    macro: '/api/fundamentals/macro-history?page_size=60',
    usMacro: '/api/fundamentals/us-macro',
  });
  for (const m of metrics) {
    assert.ok(['rates', 'macro', 'usMacro'].includes(m.endpoint), m.key);
    assert.ok(decodeHistory(fixture(m.endpoint), m.endpoint, today).series[m.key], m.key);
  }
  assert.equal(metrics.find(m => m.key === 'margin_rzrqye').apiUnit, '亿');
  assert.equal(metrics.find(m => m.key === 'margin_rzyezb').apiUnit, '%');
  assert.equal(metrics.find(m => m.key === 'vix').apiUnit, '');
  assert.equal(metrics.find(m => m.key === 'pmi').apiUnit, '');
  assert.equal(metrics.find(m => m.key === 'hsales').apiUnit, '千套');
  assert.equal(metrics.find(m => m.key === 'altsa').apiUnit, '百万辆');
});

await test('loader selects only its endpoint and sends the supplied abort signal', async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push([url, options.signal]);
    const endpoint = Object.entries(endpoints).find(([, path]) => path === url)?.[0];
    return {ok: true, json: async () => fixture(endpoint)};
  };
  try {
    const signal = new AbortController().signal;
    for (const endpoint of ['rates', 'macro', 'usMacro']) await loadHistory(endpoint, signal);
    assert.deepEqual(calls.map(x => x[0]), Object.values(endpoints));
    assert.ok(calls.every(x => x[1] === signal));
  } finally { globalThis.fetch = oldFetch; }
});

await test('missing key and empty series do not borrow a neighboring reading', () => {
  const raw = fixture('macro');
  delete raw.series.pmi;
  raw.series.cpi = {...raw.series.cpi, dates: [], values: []};
  const decoded = decodeHistory(raw, 'macro', today);
  assert.equal(lastReading(decoded.series.pmi), null);
  assert.equal(lastReading(decoded.series.cpi), null);
  assert.match(decoded.series.pmi.notice, /未返回/);
});

await test('wrong unit or unequal array lengths block the entire affected series', () => {
  for (const [key, patch] of [['pmi', {unit:'%'}], ['cpi', {values:[1]}]]) {
    const decoded = decodeHistory(changed('macro', key, patch), 'macro', today);
    assert.deepEqual(decoded.series[key].dates, []);
    assert.match(decoded.series[key].notice, /不匹配/);
    assert.equal(decoded.series.ppi.dates.length, 2);
  }
});

await test('invalid numbers, impossible dates, duplicate dates and descending dates are blocked', () => {
  for (const patch of [
    {values:[1, Infinity]}, {values:[NaN, 2]}, {values:['1', 2]},
    {dates:['2026-02-30', '2026-10-01']},
    {dates:['2026-09-01', '2026-09-01']},
    {dates:['2026-10-01', '2026-09-01']},
  ]) {
    const decoded = decodeHistory(changed('macro', 'pmi', patch), 'macro', today);
    assert.equal(lastReading(decoded.series.pmi), null, JSON.stringify(patch));
    assert.match(decoded.series.pmi.notice, /异常/);
  }
});

await test('future periods are excluded and cannot become the latest reading', () => {
  const decoded = decodeHistory(changed('macro', 'pmi', {
    dates:['2026-09-01','2026-10-01','2026-11-01'], values:[49,50,99],
  }), 'macro', today);
  assert.deepEqual(decoded.series.pmi.dates, ['2026-09-01','2026-10-01']);
  assert.equal(lastReading(decoded.series.pmi).value, 50);
  assert.match(decoded.series.pmi.notice, /未来/);
});

await test('null is missing while numeric zero remains a real reading', () => {
  const decoded = decodeHistory(changed('macro', 'cpi', {
    dates:['2026-07-01','2026-08-01','2026-09-01','2026-10-01'], values:[1,null,0,null],
  }), 'macro', today);
  assert.deepEqual(lastReading(decoded.series.cpi), {
    value:0, date:'2026-09-01', change:-1, previousDate:'2026-07-01', trailingMissing:true,
  });
  assert.equal(formatValue(0,'%'), '0%');
});

await test('each reading uses its own latest date, never the response-wide as_of', () => {
  const raw = changed('macro', 'pmi', {dates:['2026-07-01','2026-08-01'], values:[49,51]});
  raw.as_of = today;
  const decoded = decodeHistory(raw, 'macro', today);
  assert.equal(lastReading(decoded.series.pmi).date, '2026-08-01');
  assert.equal(periodLabel(lastReading(decoded.series.pmi).date, '月'), '2026-08 所属月');
  assert.equal(periodLabel('2026-09-24', '周'), '2026-09-24 所属周');
});

await test('monthly windows use calendar years and include the boundary month', () => {
  const s = {dates:['2023-01-01','2023-02-01','2024-01-01','2024-02-01'],values:[1,2,3,4],notice:''};
  assert.deepEqual(windowSeries(s, 1).dates, ['2023-02-01','2024-01-01','2024-02-01']);
  assert.deepEqual(windowSeries(s, 3).dates, s.dates);
  assert.deepEqual(windowSeries(s, 'all').dates, s.dates);
});

await test('leap-day year subtraction clamps to February 28', () => {
  const s = {dates:['2023-02-27','2023-02-28','2024-02-29'],values:[1,2,3],notice:''};
  assert.deepEqual(windowSeries(s, 1).dates, ['2023-02-28','2024-02-29']);
});

await test('change compares the previous valid value, including an earlier zero', () => {
  const s = {dates:['2026-01-01','2026-02-01','2026-03-01','2026-04-01'],values:[0,null,2,null],notice:''};
  assert.deepEqual(lastReading(s), {value:2,date:'2026-03-01',change:2,previousDate:'2026-01-01',trailingMissing:true});
  assert.equal(lastReading({...s, values:[null,null,2,null]}).change, null);
});

await test('historical reference lines disclose their fixed basis and never become trading rules', () => {
  for (const key of ['erp_cn','erp_us','cape_us','pe_cn']) {
    const refs = referencesFor(key);
    assert.ok(refs.some(x => x.kind === '历史分位参考'), key);
    assert.ok(refs.filter(x => x.kind === '历史分位参考').every(x => /固定标定|未随当前窗口重算/.test(x.basis)), key);
  }
  assert.ok(referencesFor('pmi').some(x => x.y === 50 && x.kind === '定义线'));
  assert.ok(referencesFor('cpiaucsl_yoy').some(x => x.y === 2 && x.kind === '原页面参考' && !/联储目标|PCE目标/.test(x.label + x.basis)));
  assert.deepEqual(referencesFor('margin_rzrqye'), []);
  assert.ok(metrics.find(m => m.key === 'margin_rzrqye').reading.includes('不画风险阈值'));
});

await test('malformed envelope is rejected while provider errors remain a count', () => {
  assert.throws(() => decodeHistory({series:null,errors:[]}, 'macro', today), /格式/);
  assert.throws(() => decodeHistory({series:{},errors:null}, 'macro', today), /格式/);
  assert.equal(decodeHistory(fixture('macro',{errors:['provider detail']}),'macro',today).errors,1);
});

console.log(`${checks} market dashboard boundary checks passed; synthetic data only.`);
