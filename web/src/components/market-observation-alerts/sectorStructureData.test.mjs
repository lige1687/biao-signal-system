import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const out = await build({ entryPoints: [path.join(here, 'SectorStructureCard.tsx')], bundle: true, write: false,
  platform: 'node', format: 'cjs', external: ['react', 'react-dom', '@tanstack/react-query'], loader: { '.css': 'empty' }, logLevel: 'silent' });
const mod = new Module(path.join(here, '__sector_test__.cjs'));
mod.filename = path.join(here, '__sector_test__.cjs'); mod.paths = Module._nodeModulePaths(here);
mod._compile(out.outputFiles[0].text, mod.filename);
const { isSectorStructure, SectorBreadthView } = mod.exports;
const earningsOut = await build({ entryPoints: [path.join(here, 'EarningsRevisionSampleCard.tsx')], bundle: true, write: false,
  platform: 'node', format: 'cjs', external: ['react', 'react-dom', '@tanstack/react-query'], loader: { '.css': 'empty' }, logLevel: 'silent' });
const earningsMod = new Module(path.join(here, '__earnings_sample_test__.cjs'));
earningsMod.filename = path.join(here, '__earnings_sample_test__.cjs'); earningsMod.paths = Module._nodeModulePaths(here);
earningsMod._compile(earningsOut.outputFiles[0].text, earningsMod.filename);
const { isEarningsRevisionSamples, EarningsSampleView } = earningsMod.exports;
const earnings = JSON.parse(readFileSync(path.join(here, '../../../public/research/earnings-revisions-20261115.json'), 'utf8'));
const snapshot = JSON.parse(readFileSync(path.join(here, '../../../public/research/sector-structure-20261115.json'), 'utf8'));

test('qualified industry windows display their effective stock counts and honest chart scale', () => {
  assert.equal(isSectorStructure(snapshot), true);
  const html = renderToStaticMarkup(React.createElement(SectorBreadthView, { board: snapshot.boards[0], asOf: snapshot.asOf }));
  assert.match(html, /77\/182只/); assert.match(html, /21\/179只/); assert.match(html, /19\/164只/);
  assert.match(html, /42\.3%/); assert.match(html, /2026-11-13/);
  assert.match(html, />100%<\/text>/); assert.match(html, />0%<\/text>/);
  assert.match(html, /固定名单回看/);
});

test('misdated observations and missing-stock denominator corruption are rejected', () => {
  const badDate = structuredClone(snapshot); badDate.asOf = '2026-11-12';
  assert.equal(isSectorStructure(badDate), false);
  const badCount = structuredClone(snapshot); badCount.boards[0].breadth.observations.at(-1).windows['200'].missing = 0;
  assert.equal(isSectorStructure(badCount), false);
  const badPct = structuredClone(snapshot); badPct.boards[0].breadth.observations.at(-1).windows['20'].percent = 0;
  assert.equal(isSectorStructure(badPct), false);
});

test('disclosed margin requires a complete denominator and an explicit partial-numerator definition', () => {
  const data = structuredClone(snapshot);
  data.boards[0].margin = { basis: 'disclosed-buy/full-sector-turnover', points: [{ date: '2026-11-13', buyAmount: 10, turnoverAmount: 100, percent: 10,
    reportedCount: 9, denominatorCount: 182, total: data.boards[0].memberCount }] };
  assert.equal(isSectorStructure(data), false);
  data.boards[0].margin.points[0].denominatorCount = 183;
  assert.equal(isSectorStructure(data), true);
  data.boards[0].margin.points[0].percent = 0;
  assert.equal(isSectorStructure(data), false);
  data.boards[0].margin.points[0].percent = 10;
  data.boards[0].margin.basis = 'full-sector-margin';
  assert.equal(isSectorStructure(data), false);
});

test('earnings versions keep target, team identity, profit units and source conflict visible', () => {
  assert.equal(isEarningsRevisionSamples(earnings), true);
  const html = renderToStaticMarkup(React.createElement(EarningsSampleView, { data: earnings, code: '688008' }));
  assert.match(html, /2027年/); assert.match(html, /49\.09/); assert.match(html, /54\.60/);
  assert.match(html, /股本数字存在不一致/); assert.match(html, /全指数修正广度及首次可得时间未知/);
  const wrongTarget = structuredClone(earnings); wrongTarget.comparisons[0].from.target = '2026E';
  assert.equal(isEarningsRevisionSamples(wrongTarget), false);
  const changedTeam = structuredClone(earnings); changedTeam.comparisons[0].to.analystIds = ['different-team'];
  assert.equal(isEarningsRevisionSamples(changedTeam), false);
});
