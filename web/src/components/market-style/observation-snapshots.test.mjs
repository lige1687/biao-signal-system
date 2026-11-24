import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const compiled = await build({
  stdin: { contents: 'export { isStarWeightedBreadth, StarWeightedBreadthView } from "./StarWeightedBreadthSnapshot.tsx"; export { StarBreadthView } from "./StarBreadthSnapshot.tsx"; export { isSocialFinancingYoy, socialYoyLineSegments, SocialFinancingYoyView } from "./SocialFinancingSnapshot.tsx";', resolveDir: here, loader: 'ts' },
  bundle: true, write: false, platform: 'node', format: 'cjs', external: ['react', 'react-dom', 'react-dom/server'], loader: { '.css': 'empty' }, logLevel: 'silent',
});
const bundled = new Module(path.join(here, '__observation_snapshots_test__.cjs'));
bundled.filename = path.join(here, '__observation_snapshots_test__.cjs');
bundled.paths = Module._nodeModulePaths(here);
bundled._compile(compiled.outputFiles[0].text, bundled.filename);
const { isStarWeightedBreadth, StarWeightedBreadthView, StarBreadthView, isSocialFinancingYoy, socialYoyLineSegments, SocialFinancingYoyView } = bundled.exports;
const breadth = JSON.parse(readFileSync(path.join(here, '../../../public/research/star-breadth-20261115.json'), 'utf8'));
const weighted = JSON.parse(readFileSync(path.join(here, '../../../public/research/star-weighted-breadth-20261030.json'), 'utf8'));
const social = JSON.parse(readFileSync(path.join(here, '../../../public/research/social-financing-yoy-20261115.json'), 'utf8'));
const copy = (value) => structuredClone(value);

test('each weighted period shows two dated indices, effective denominators and four scaled bars', () => {
  assert.equal(isStarWeightedBreadth(weighted), true);
  for (const period of [20, 50, 200]) {
    const html = renderToStaticMarkup(React.createElement(StarWeightedBreadthView, { data: weighted, initialPeriod: period }));
    assert.equal((html.match(/class="star-weighted-row"/g) || []).length, 2, `${period}日行数`);
    assert.equal((html.match(/class="star-weighted-bar"/g) || []).length, 4, `${period}日条数`);
    assert.match(html, new RegExp(`aria-pressed="true">${period}日`));
    assert.match(html, /科创50单日对照/);
    assert.match(html, /科创100单日对照/);
    assert.match(html, /fill="#2563eb"/);
    assert.match(html, /fill="#28806e"/);
    assert.equal((html.match(/<span>0<\/span><span>50<\/span><span>100%<\/span>/g) || []).length, 4);
    assert.match(html, /2026-10-30/);
    assert.match(html, /2026-11-11/);
    assert.match(html, /2026-11-15/);
    for (const index of weighted.indices) {
      const r = index.readings.find(item => item.period === period);
      assert.ok(r);
      assert.ok(html.includes(`${r.above}/${r.eligible} 只有效`));
      assert.ok(html.includes(`${r.aboveWeightPct.toFixed(3)} / ${r.eligibleWeightPct.toFixed(3)}% 有效权重`));
    }
  }
  const defaultHtml = renderToStaticMarkup(React.createElement(StarWeightedBreadthView, { data: weighted }));
  assert.match(defaultHtml, /aria-pressed="true">50日/);
});


test('fixed-member breadth charts expose dates, eligible counts and a zero-to-100 axis', () => {
  const html = renderToStaticMarkup(React.createElement(StarBreadthView, { data: breadth }));
  assert.equal((html.match(/<svg /g) || []).length, 2);
  assert.match(html, /2026-11-13 收盘/);
  assert.match(html, /2026-11-11 固定名单/);
  assert.match(html, /25\/50 只有效/);
  assert.ok(html.indexOf('25/50 只有效') < html.indexOf('<svg '));
  assert.match(html, /10\/97 只有效/);
  assert.equal((html.match(/>100%<\/text>/g) || []).length, 2);
  assert.equal((html.match(/>0%<\/text>/g) || []).length, 2);
  assert.match(html, /stroke="#ea580c"/);
  assert.match(html, /stroke="#2563eb"/);
  assert.match(html, /stroke="#7c3aed"/);
  assert.match(html, /最低 6\.0%/);
  assert.match(html, /最高 42\.9%/);
  assert.match(html, /stroke="#398579" stroke-dasharray="6 4"/);
  assert.match(html, /stroke="#a3825c" stroke-dasharray="6 4"/);
});

test('home card layouts stack the two indices and give weighted bars a full track', () => {
  const css = readFileSync(path.join(here, 'star-breadth.css'), 'utf8');
  assert.match(css, /\.star-breadth-card \.star-breadth-grid, \.star-weighted-card \.star-weighted-grid \{ grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /\.star-weighted-card \.star-weighted-pair \{ grid-template-columns: minmax\(0, 1fr\)/);
  assert.doesNotMatch(css, /white-space:\s*nowrap/);
});

test('weighted comparison refuses a wrong date or invalid denominator', () => {
  const wrongDate = copy(weighted);
  wrongDate.membershipDate = '2026-10-30';
  assert.equal(isStarWeightedBreadth(wrongDate), false);
  const invalid = copy(weighted);
  invalid.indices[1].readings[2].eligibleWeightPct = 0;
  assert.equal(isStarWeightedBreadth(invalid), false);
});

test('social chart keeps missing months empty and uses a zero baseline', () => {
  assert.equal(isSocialFinancingYoy(social), true);
  assert.deepEqual(social.rows.slice(10).map((row) => row.otherYoyEstimate), [null, null]);
  const segments = socialYoyLineSegments(social.rows);
  assert.equal(segments.length, 1);
  assert.equal(segments[0].length, 10);
  const html = renderToStaticMarkup(React.createElement(SocialFinancingYoyView, { data: social }));
  assert.match(html, /5\.24%/);
  assert.match(html, /7\.2%/);
  assert.match(html, /14\.4%/);
  assert.match(html, />0%<\/text>/);
  assert.match(html, /11—12月暂无数据/);
  const invalid = copy(social);
  invalid.rows[10].otherYoyEstimate = 0;
  assert.equal(isSocialFinancingYoy(invalid), false);
});
