/* Bounded synthetic UI acceptance; no authority originals, market API or login data.
 * Inputs: LEI_READER_DIST, LEI_PLAYWRIGHT_MODULE (optional), LEI_BROWSER_EXECUTABLE,
 * LEI_READER_COMMIT. Existing dependencies only; never starts a research evaluator.
 */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.LEI_PLAYWRIGHT_MODULE || 'playwright');
const out = __dirname;
const dist = path.resolve(process.env.LEI_READER_DIST || 'web/dist');
const results = [];
const screenshots = [];
const requests = [];
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const summary = (id, state, guide = false) => ({
  id, title: `${id === 'technical-implementation' ? '实现规范' : guide ? '因子指南' : '技术体系'}（合成验收）`,
  file_name: `${id}.md`, role: '合成界面验收资料，不能作为技术原文或研究证据',
  path: `/synthetic-only/authority/${id}.md`, order: id === 'technical-system' ? 1 : 2,
  available: state !== 'missing', approved_sha256: 'a'.repeat(64), baseline_sha256: 'a'.repeat(64),
  currentSha256: state === 'missing' ? null : (state === 'changed' ? 'b' : 'a').repeat(64),
  approvalStatus: state === 'missing' ? 'missing' : state === 'changed' ? 'changed' : guide ? 'unchanged' : 'confirmed',
  confirmed_at: '2026-09-29', recorded_at: '2026-09-29', modifiedAt: state === 'missing' ? null : '2026-10-03T00:00:00Z',
});
const body = [
  '# 页面验收合成资料', '这不是技术原文，仅用于检查界面。',
  '## 章节二：长内容', '| 字段 | 合成值 |', '', '| --- | --- |', '', '| 示例 | 完整表格 |',
  '> 合成引用', '- 合成列表', '', '```text', 'x'.repeat(180), '```',
  ...Array.from({ length: 18 }, (_, i) => `第${i + 1}段：用于检查章节定位和正文行宽的合成段落。`),
  '### 章节三：结束', '[普通链接](https://example.invalid/fixture)',
  '<script>window.__unsafeExecuted = true</script>',
  '<img src="/unsafe-fixture-image" onerror="window.__unsafeExecuted=true">',
  '[危险链接](javascript:window.__unsafeExecuted=true)',
].join('\n\n');
const detail = (id, state, guide = false) => ({ ...summary(id, state, guide), markdown: body,
  headings: [{ id: 'fixture-overview', text: '页面验收合成资料', level: 1 },
    { id: 'fixture-long', text: '章节二：长内容', level: 2 },
    { id: 'fixture-last', text: '章节三：结束', level: 3 }],
});
async function check(name, fn) {
  const start = Date.now();
  try { const evidence = await fn(); results.push({ name, status: 'passed', duration_ms: Date.now() - start, evidence }); }
  catch (error) { results.push({ name, status: 'failed', duration_ms: Date.now() - start, error: String(error.stack || error) }); }
}
async function screenshot(page, name) {
  const file = `${name}.png`; await page.screenshot({ path: path.join(out, file), fullPage: false });
  const bytes = fs.readFileSync(path.join(out, file)); screenshots.push({ path: file, bytes: bytes.length, sha256: digest(bytes) });
}
async function main() {
  if (!fs.existsSync(path.join(dist, 'index.html'))) throw new Error('Required existing built dist is missing');
  const sourceCommit = process.env.LEI_READER_COMMIT;
  if (!/^[a-f0-9]{40}$/.test(sourceCommit || '')) throw new Error('Exact source commit is required');
  const sourceRoot = path.resolve(dist, '../..');
  const sourceFiles = execFileSync('git', ['ls-tree', '-r', '--name-only', sourceCommit, 'web/src', 'web/package.json', 'web/package-lock.json'], { encoding: 'utf8' }).trim().split('\n');
  if (!sourceFiles.length || !sourceFiles.includes('web/src/pages/StrategySystemPage.tsx')) throw new Error('Reader source closure is missing');
  for (const relative of sourceFiles) {
    const actual = fs.readFileSync(path.join(sourceRoot, relative));
    const expected = execFileSync('git', ['show', `${sourceCommit}:${relative}`], { maxBuffer: 8 * 1024 * 1024 });
    if (!actual.equals(expected)) throw new Error(`Source changed from committed version: ${relative}`);
  }
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(new URL(req.url, 'http://localhost').pathname).replace(/^\/+/, '');
    let file = path.resolve(dist, rel);
    if (!file.startsWith(dist + path.sep) && file !== dist) { res.writeHead(403); res.end(); return; }
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) file = path.join(dist, 'index.html');
    res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream'); res.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await chromium.launch({ executablePath: process.env.LEI_BROWSER_EXECUTABLE || undefined,
      headless: true, args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run'] });
    const browserVersion = browser.version();
    for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      const label = viewport.width === 1440 ? 'desktop' : 'narrow';
      const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
      let state = 'confirmed';
      await context.addInitScript(() => {
        window.__fixtureScrollCalls = [];
        const native = Element.prototype.scrollIntoView;
        Element.prototype.scrollIntoView = function(options) {
          window.__fixtureScrollCalls.push(options);
          return native.call(this, options);
        };
      });
      await context.route('**/*', async (route) => {
        const u = new URL(route.request().url());
        requests.push({ origin: u.origin === origin ? 'isolated-local' : 'blocked-external', path: u.pathname });
        if (u.origin !== origin) { await route.abort(); return; }
        if (u.pathname.startsWith('/api/')) {
          const guide = u.pathname.includes('/factor-guide');
          const ids = guide ? ['research-guide', 'candidate-registry'] : ['technical-system', 'technical-implementation'];
          const tail = u.pathname.split('/').filter(Boolean).at(-1);
          const listing = tail === 'strategy-documents' || tail === 'factor-guide';
          const payload = listing ? { documents: ids.map((id) => summary(id, state, guide)) }
            : state === 'missing' ? { detail: `源文件缺失：/synthetic-only/authority/${tail}.md` }
            : ids.includes(tail) ? detail(tail, state, guide) : { detail: '未知文档 ID' };
          await route.fulfill({ status: listing ? 200 : state === 'missing' || !ids.includes(tail) ? 404 : 200,
            contentType: 'application/json', body: JSON.stringify(payload) }); return;
        }
        if (u.pathname === '/unsafe-fixture-image') { await route.fulfill({ status: 404, body: '' }); return; }
        await route.continue();
      });
      const page = await context.newPage();
      await check(`${label}: confirmed rendering and sanitization`, async () => {
        await page.goto(`${origin}/strategy?doc=technical-system`);
        await page.locator('.strategy-markdown').waitFor();
        assert.equal(await page.locator('.strategy-markdown table').count(), 1);
        assert.equal(await page.locator('.strategy-markdown pre').count(), 1);
        assert.equal(await page.locator('.strategy-markdown blockquote').count(), 1);
        assert.equal(await page.locator('.strategy-markdown script,[onerror],[onclick],a[href^="javascript:"]').count(), 0);
        assert.equal(await page.evaluate(() => !!window.__unsafeExecuted), false);
        const geometry = await page.evaluate(() => ({ width: innerWidth, documentWidth: document.documentElement.scrollWidth }));
        assert.ok(geometry.documentWidth <= geometry.width + 1, JSON.stringify(geometry));
        await screenshot(page, `${label}-confirmed`);
        return { ...geometry, table: true, codeBlock: true, quote: true, dangerousHtmlRemoved: true };
      });
      await check(`${label}: chapter URL, refresh, reduced motion`, async () => {
        if (label === 'narrow') await page.locator('.strategy-mobile-toc > summary').click();
        const nav = page.locator(label === 'narrow' ? '.strategy-mobile-toc nav' : '.strategy-toc');
        await nav.getByRole('link', { name: '章节二：长内容', exact: true }).click();
        await page.waitForURL('**section=fixture-long');
        assert.equal(await page.evaluate(() => window.__fixtureScrollCalls.at(-1)?.behavior), 'auto');
        await page.reload(); await page.locator('#fixture-long').waitFor();
        await page.waitForFunction(() => document.querySelector('#fixture-long').getBoundingClientRect().top < innerHeight);
        const geometry = await page.evaluate(() => ({ headingTop: document.querySelector('#fixture-long').getBoundingClientRect().top,
          navBottom: document.querySelector('.top-nav').getBoundingClientRect().bottom, reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches }));
        assert.ok(geometry.headingTop >= geometry.navBottom - 2, JSON.stringify(geometry));
        assert.equal(geometry.reducedMotion, true);
        await screenshot(page, `${label}-chapter-restored`); return { urlQuery: new URL(page.url()).search, ...geometry };
      });
      await check(`${label}: keyboard focus`, async () => {
        await page.goto(`${origin}/strategy?doc=technical-system`); await page.locator('.strategy-markdown').waitFor();
        let found = false;
        for (let i = 0; i < 40; i++) { await page.keyboard.press('Tab');
          found = await page.evaluate(() => document.activeElement?.matches('.strategy-document-tabs button'));
          if (found) break;
        }
        assert.equal(found, true);
        const focus = await page.evaluate(() => { const e = document.activeElement; const s = getComputedStyle(e);
          return { tag: e.tagName, text: e.textContent, focusVisible: e.matches(':focus-visible'), outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth }; });
        assert.equal(focus.focusVisible, true); assert.notEqual(focus.outlineStyle, 'none'); assert.ok(parseFloat(focus.outlineWidth) > 0);
        await screenshot(page, `${label}-keyboard-focus`); return focus;
      });
      await check(`${label}: unconfirmed change warning`, async () => {
        state = 'changed'; await page.goto(`${origin}/strategy?doc=technical-system`); await page.locator('.strategy-markdown').waitFor();
        await page.getByRole('alert').filter({ hasText: '源文件已变化，尚未确认' }).waitFor();
        assert.ok((await page.locator('.strategy-provenance').innerText()).includes('b'.repeat(64)));
        await screenshot(page, `${label}-changed`); return { warning: 'visible', content: 'readable', currentFingerprint: 'b'.repeat(64) };
      });
      await check(`${label}: missing source and explicit retry recovery`, async () => {
        state = 'missing'; await page.goto(`${origin}/strategy?doc=technical-system`);
        await page.getByRole('button', { name: '重新读取', exact: true }).waitFor();
        assert.equal(await page.locator('.strategy-markdown').count(), 0);
        const alerts = await page.getByRole('alert').allTextContents();
        assert.ok(alerts.join('').includes('/synthetic-only/authority/technical-system.md'));
        await screenshot(page, `${label}-missing`);
        state = 'confirmed'; await page.getByRole('button', { name: '重新读取', exact: true }).click();
        await page.locator('.strategy-markdown').waitFor();
        assert.equal(await page.getByRole('button', { name: '重新读取', exact: true }).count(), 0);
        return { missingNoFallbackArticle: true, exactSyntheticPath: true, retryRestoredReader: true };
      });
      await check(`${label}: document and guide identity`, async () => {
        await page.getByRole('button', { name: '实现规范', exact: true }).click();
        await page.waitForURL('**doc=technical-implementation'); await page.locator('.strategy-markdown').waitFor();
        await page.getByRole('button', { name: '因子指南包', exact: true }).click();
        await page.waitForURL('**collection=factor-guide**'); await page.locator('#strategy-guide-document').waitFor();
        await page.locator('#strategy-guide-document').selectOption('candidate-registry');
        await page.waitForURL('**doc=candidate-registry**'); await page.reload();
        await page.locator('.strategy-markdown').waitFor();
        assert.equal(await page.locator('#strategy-guide-document').inputValue(), 'candidate-registry');
        assert.ok((await page.locator('.strategy-guide-intro').innerText()).includes('不代表已验证、已实现或获准交易'));
        return { documentIdPreserved: true, guideIdPreservedAfterRefresh: true, researchBoundaryVisible: true };
      });
      await context.close();
    }
    const assets = fs.readdirSync(path.join(dist, 'assets')).map((name) => {
      const b = fs.readFileSync(path.join(dist, 'assets', name)); return { path: `assets/${name}`, bytes: b.length, sha256: digest(b) };
    });
    const receipt = { checked_at: new Date().toISOString(), timezone: 'UTC', browser: browserVersion,
      source_commit: process.env.LEI_READER_COMMIT || 'unrecorded', source_verification: { matched_files: sourceFiles.length, method: 'byte comparison against exact git commit before browser launch', build_reused: true },
      scope: 'isolated published reader with explicit synthetic API; not real upstream, strategy originals, full-site or market research',
      results, screenshots, input_assets: assets, harness_sha256: digest(fs.readFileSync(__filename)),
      requests: { count: requests.length, apiResponsesSynthetic: true, externalAllowed: false },
      not_verified: ['true browser zoom 200%', 'real source files/upstream availability', 'full-site interactions', 'Linux/Windows', 'cold dependency install', 'live signal logic or online gains'],
      market_effect_runs: 0, model_fits: 0, paid_calls: 0,
    };
    fs.writeFileSync(path.join(out, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify({ passed: results.filter(x => x.status === 'passed').length, failed: results.filter(x => x.status === 'failed').length, browser: browserVersion }));
    for (const r of results.filter(x => x.status === 'failed')) console.log(r.name, r.error);
    if (results.some(x => x.status === 'failed')) process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}
main().catch(error => { fs.writeFileSync(path.join(out, 'startup-failure.json'), JSON.stringify({ error: String(error.stack || error), market_runs: 0 }, null, 2) + '\n'); console.error(error); process.exitCode = 1; });
