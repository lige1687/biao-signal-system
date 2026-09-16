import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createServer } from '/Users/yongbiaoli/lei-signal-integration-20260909/web/node_modules/vite/dist/node/index.js';
import { chromium } from '/Users/yongbiaoli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';

const ROOT = '/Users/yongbiaoli/lei-signal-integration-20260909';
const OUT = path.dirname(fileURLToPath(import.meta.url));
const PY = '/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3';
const results = { protocol: 'experiment-backtest-principles@v1.0',
  fixture: { target_b_price: 120, real_advice: false } };
const posts = [];
const streamBodies = [];
let resolveRequests = 0;
const errors = [];
let backend, server, browser;

async function waitPort(file) {
  const start = Date.now();
  while (Date.now() - start < 30000) {
    if (fs.existsSync(file)) {
      const port = Number(fs.readFileSync(file, 'utf8').trim());
      const ok = await new Promise(resolve => {
        const socket = net.connect({ host: '127.0.0.1', port }, () => { socket.destroy(); resolve(true); });
        socket.on('error', () => resolve(false));
        setTimeout(() => { socket.destroy(); resolve(false); }, 400);
      });
      if (ok) return port;
    }
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error('backend timeout');
}

async function freePort() {
  return await new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const port = probe.address().port;
      probe.close(error => error ? reject(error) : resolve(port));
    });
  });
}

const getPlanId = text => /plan_id: ([\w-]+)/.exec(text)?.[1] || null;
async function save(page, card) {
  const display = await card.innerText();
  await card.getByRole('button', { name: '保存草稿', exact: true }).click();
  await card.getByText(/plan_id: /).waitFor({ timeout: 30000 });
  const id = getPlanId(await card.innerText());
  const stored = await page.evaluate(async id => (await fetch(`/api/plans/${encodeURIComponent(id)}`)).json(), id);
  return { display, id, stored_target: stored.target_b_price };
}

async function workspaceSend(page, text) {
  await page.locator('#agent-question').fill(text);
  await page.getByRole('button', { name: /发送/ }).click();
  await page.getByRole('button', { name: /发送/ }).waitFor();
}

try {
  const portDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lei-stage-browser-'));
  const portFile = path.join(portDir, 'port');
  backend = spawn(PY, [path.join(OUT, 'e2e_backend.py'), '--port-file', portFile],
    { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  let backendOutput = '';
  backend.stdout.on('data', b => { backendOutput += String(b); });
  backend.stderr.on('data', b => { backendOutput += String(b); });
  const backendPort = await waitPort(portFile);
  results.backend = { port: backendPort, expected_import_root: ROOT,
    import_root_seen: backendOutput.includes(`"import_root": "${ROOT}"`) };

  const requestedWebPort = await freePort();
  server = await createServer({ root: path.join(ROOT, 'web'), configFile: false,
    plugins: [(await import(`${ROOT}/web/node_modules/@vitejs/plugin-react/dist/index.js`)).default()],
    cacheDir: path.join(os.tmpdir(), 'lei-stage-browser-vite'), clearScreen: false,
    server: { host: '127.0.0.1', port: requestedWebPort, strictPort: true,
      proxy: { '/api': { target: `http://127.0.0.1:${backendPort}`, changeOrigin: true } } } });
  await server.listen();
  const webPort = server.httpServer.address().port;
  results.ports = { backend: backendPort, web: webPort,
    avoids_real_ports: ![8000, 5173].includes(backendPort) && ![8000, 5173].includes(webPort) };

  browser = await chromium.launch({ headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
  page.on('pageerror', e => errors.push(String(e)));
  page.on('request', req => {
    if (req.url().includes('/api/plans') && req.method() === 'POST') {
      try { posts.push(JSON.parse(req.postData() || '{}')); } catch { /* ignore */ }
    }
    if (req.url().includes('/api/agent/chat/stream') && req.method() === 'POST') {
      try { streamBodies.push(JSON.parse(req.postData() || '{}')); } catch { /* ignore */ }
    }
  });

  // 新增回归：让 resolve 人为等待，连续提交两次；页面锁应只允许一条 resolve
  // 和一条后续聊天请求。只延迟本机隔离请求，不更改产品代码。
  await page.route('**/api/copilot/resolve', async route => {
    resolveRequests += 1;
    await new Promise(r => setTimeout(r, 700));
    await route.continue();
  });

  await page.goto(`http://127.0.0.1:${webPort}/agent`);
  await page.locator('#agent-question').fill('000001.SS 最近如何');
  await page.locator('#agent-question').press('Enter');
  await page.locator('#agent-question').press('Enter');
  await page.locator('.plan-draft-card, .ar-answer:not(.is-working)').last()
    .waitFor({ timeout: 120000 });
  results.submit_lock = {
    delayed_resolve_ms: 700,
    resolve_requests: resolveRequests,
    stream_requests: streamBodies.length,
    one_request_only: resolveRequests === 1 && streamBodies.length === 1,
    stream_client_request_id_nonempty:
      typeof streamBodies[0]?.client_request_id === 'string'
      && streamBodies[0].client_request_id.length > 0,
  };
  await page.getByRole('button', { name: '新对话', exact: true }).click();
  await workspaceSend(page, '000001.SS 按模块A整理成计划');
  let card = page.locator('.plan-draft-card').first();
  await card.waitFor({ timeout: 120000 });
  const a = await save(page, card);
  await page.screenshot({ path: path.join(OUT, 'workspace-target-120.png'), fullPage: true });
  await page.reload();
  await page.locator('.ar-history-item').first().waitFor({ timeout: 30000 });
  await page.locator('.ar-history-item').first().click();
  card = page.locator('.plan-draft-card').first();
  await card.waitFor({ timeout: 30000 });
  await card.getByRole('button', { name: '保存草稿', exact: true }).click().catch(() => undefined);
  await card.getByText(/plan_id: /).waitFor({ timeout: 30000 });
  const a2 = getPlanId(await card.innerText());
  results.workspace = { display_120: a.display.includes('目标价(B)：120'),
    server_source: a.display.includes('系统建议'), post_120: posts[0]?.target_b_price === 120,
    stored_120: a.stored_target === 120, plan_id: a.id, reopened_plan_id: a2,
    same_plan_after_reload: a.id === a2 };

  await page.goto(`http://127.0.0.1:${webPort}/symbol/000001.SS`);
  await page.evaluate(async () => { (await import('/src/App.tsx')).agentConsoleStore.openConsole(null); });
  const consoleRoot = page.locator('.agent-console');
  await consoleRoot.waitFor({ timeout: 30000 });
  await consoleRoot.locator('textarea, input').fill('000001.SS 按模块A整理成计划');
  await consoleRoot.getByRole('button', { name: '发送', exact: true }).click();
  const consoleCard = consoleRoot.locator('.plan-draft-card').first();
  await consoleCard.waitFor({ timeout: 120000 });
  const c = await save(page, consoleCard);
  await page.screenshot({ path: path.join(OUT, 'symbol-console-target-120.png'), fullPage: true });
  const cPost = posts.at(-1);

  await page.goto(`http://127.0.0.1:${webPort}/agent`);
  await page.locator('.ar-history-item').first().waitFor({ timeout: 30000 });
  await page.locator('.ar-history-item').first().click();
  const reopened = page.locator('.plan-draft-card').first();
  await reopened.waitFor({ timeout: 30000 });
  await reopened.getByRole('button', { name: '保存草稿', exact: true }).click().catch(() => undefined);
  await reopened.getByText(/plan_id: /).waitFor({ timeout: 30000 });
  const c2 = getPlanId(await reopened.innerText());
  results.symbol_console = { display_120: c.display.includes('目标价(B)：120'),
    server_source: c.display.includes('系统建议'), post_120: cPost?.target_b_price === 120,
    stored_120: c.stored_target === 120, plan_id: c.id, reopened_plan_id: c2,
    same_plan_after_workspace_history_reopen: c.id === c2,
    reopened_display_120: (await reopened.innerText()).includes('目标价(B)：120') };

  // 顺带检查任务卡入口是否存在；不触发完整回测。真正状态链仅在稳定后且成本可控时另记。
  results.backtest_task_card = { checked: true,
    request_not_started: true,
    note: '限定验收不运行完整回测；仅保留两入口计划链为必验项。' };
  results.posts = posts.map(p => ({ target_b_price: p.target_b_price,
    source_question_id: p.source_question_id, client_request_id: p.client_request_id }));
  results.errors = errors;
  results.all_pass = results.backend.import_root_seen && results.ports.avoids_real_ports
    && results.submit_lock.one_request_only
    && results.submit_lock.stream_client_request_id_nonempty
    && ['workspace', 'symbol_console'].every(k => Object.entries(results[k])
      .filter(([name, value]) => typeof value === 'boolean' && name !== 'request_not_started')
      .every(([, value]) => value)) && errors.length === 0;
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
  process.exitCode = results.all_pass ? 0 : 1;
} catch (error) {
  errors.push(String(error)); results.errors = errors;
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 2));
  console.error(error); process.exitCode = 1;
} finally {
  await browser?.close().catch(() => undefined);
  await server?.close().catch(() => undefined);
  backend?.kill();
}
