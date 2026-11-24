import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
const { MemoryRouter } = require('react-router-dom');
const here = path.dirname(fileURLToPath(import.meta.url));
const compiled = await build({
  stdin: { contents: 'export { default as Overview } from "./index.tsx"; export { default as MiniTrend } from "./MiniTrend.tsx"; export { INDICATOR_BY_ID } from "./indicatorCatalog.ts"; export { INDICATOR_META_CONFIG } from "../market-observation-panel/model.ts";', resolveDir: here, loader: 'ts' },
  bundle: true, write: false, platform: 'node', format: 'cjs',
  external: ['react', 'react-dom', 'react-dom/server', 'react-router-dom', '@tanstack/react-query'],
  loader: { '.css': 'empty' }, logLevel: 'silent',
});
const modulePath = path.join(here, '__compact_overview_test__.cjs');
const bundled = new Module(modulePath);
bundled.filename = modulePath;
bundled.paths = Module._nodeModulePaths(here);
bundled._compile(compiled.outputFiles[0].text, modulePath);
const { Overview, MiniTrend, INDICATOR_BY_ID, INDICATOR_META_CONFIG } = bundled.exports;

test('saved home selection stays intact and is the first, default view', () => {
  const saved = '["us-cor3m","breadth-us"]';
  const values = new Map([['ws.marketOverviewCards.v2', saved]]);
  globalThis.localStorage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const html = renderToStaticMarkup(React.createElement(QueryClientProvider, { client: queryClient },
    React.createElement(MemoryRouter, null, React.createElement(Overview))));
  assert.match(html, /aria-pressed="true">首页常看 · 2<\/button><button aria-pressed="false">中美总览/);
  assert.match(html, /data-overview-card="us-cor3m"/);
  assert.match(html, /data-overview-card="breadth-us"/);
  assert.doesNotMatch(html, /data-overview-card="erp-cn"/);
  assert.equal(values.get('ws.marketOverviewCards.v2'), saved);
});

test('new research cards are in the existing indicator catalog', () => {
  for (const id of ['star-breadth', 'star-weighted-breadth', 'sector-breadth']) {
    assert.equal(INDICATOR_BY_ID.get(id)?.category, 'participation');
    assert.equal(INDICATOR_BY_ID.get(id)?.market, 'cn');
  }
  assert.equal(INDICATOR_BY_ID.get('sector-margin-share')?.category, 'funding');
  assert.equal(INDICATOR_BY_ID.get('earnings-revision-samples')?.category, 'economy');
  assert.equal(INDICATOR_BY_ID.get('sector-margin-share')?.readable, true);
  assert.equal(INDICATOR_BY_ID.get('earnings-revision-samples')?.readable, true);
});

test('compact percentage chart exposes an honest zero-to-100 scale', () => {
  const html = renderToStaticMarkup(React.createElement(MiniTrend, {
    dates: ['2026-11-10', '2026-11-11'],
    lines: [{ name: '宽度', color: '#28629e', values: [35, 65] }],
    percent: true, showScale: true, label: '样本宽度',
  }));
  assert.match(html, />100%<\/text>/);
  assert.match(html, />0%<\/text>/);
});

test('COR3M descriptions identify the 50-stock option universe', () => {
  assert.match(INDICATOR_BY_ID.get('us-cor3m').meaning, /50只/);
  assert.match(INDICATOR_META_CONFIG['us-cor3m'].human_reminder, /50只/);
});
