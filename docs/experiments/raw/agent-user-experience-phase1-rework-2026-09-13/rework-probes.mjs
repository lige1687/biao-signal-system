// U1—U3 返修等价探针（2026-09-13 执行者）。
// 与主控 probes.cjs 同一提取与判定方式（TS AST 提取真实函数 + 透明 env），
// 差异仅为 env 需要补上返修新增的标识：setupBusyRef（同步忙锁）、
// requestBacktestTask / taskCreatedTextCn（共享提交函数）、
// windowLabelFromComparisonConfig（U2 窗口展示）。mock 全部透明可查。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
(async () => {
const root = '/Users/yongbiaoli/lei-agent-ux-20260913';
const req = createRequire(root + '/web/package.json');
const ts = req('typescript');
const files = ['web/src/pages/AgentWorkspacePage.tsx', 'web/src/components/AgentConsole.tsx'];
const hashes = () => Object.fromEntries(files.concat(['web/src/components/agent/BacktestSetupPanel.tsx', 'web/src/utils/agentUx.ts'])
  .map(f => [f, crypto.createHash('sha256').update(fs.readFileSync(root + '/' + f)).digest('hex')]));
const before = hashes();
const results = [];

function extract(file, name, env) {
  const text = fs.readFileSync(root + '/' + file, 'utf8');
  const ast = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let found;
  function walk(n) { if (ts.isVariableDeclaration(n) && n.name.getText(ast) === name) found = n.initializer; ts.forEachChild(n, walk); }
  walk(ast);
  if (!found) throw Error(name + ' not found');
  const js = ts.transpileModule('const subject = ' + found.getText(ast) + ';', { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
  return new Function(...Object.keys(env), js + ';return subject;')(...Object.values(env));
}

// —— 共享提交函数的真实实现（从 backtestTasks.ts 源码同源提取，此处等价内联）——
const sharedRequestBacktestTask = (api, trackTask) => async (p) => {
  const task = await api.copilotBacktestRequest({
    session_id: p.sessionId, question_id: p.questionId,
    client_request_id: `cli_${p.sessionId}_${p.questionId}_${p.symbol}_${p.module}_${p.exitVariant}`,
    symbol: p.symbol, module: p.module, exit_variant: p.exitVariant,
  });
  trackTask({ requestId: task.request_id, sessionId: task.session_id, questionId: task.question_id, symbol: task.symbol });
  return task;
};
const taskCreatedTextCn = (t) => `已创建补测任务（${t.symbol} · ${t.method} · ${t.exit_variant} · ${t.status}）。完成后结果自动回到原问题的依据卡里，不用盯在这里。`;
const windowLabelFromComparisonConfig = () => null; // 透明：本组探针不测窗口文案

// ---- U1：直接输入"帮我补测一下" → 打开中文面板，无模块码追问 ----
for (const file of files) {
  const which = file.includes('Workspace') ? 'workspace' : 'console';
  let turns = [];
  const env = {
    api: { agentChat: async () => ({ session_id: 's1', question_id: 71, resolved_symbol: '510300.SS', reply: '合成回答', evidence_card: null, plan_artifact: null, grounded: true, next_steps: [] }) },
    sessionId: 's1', symbol: '510300.SS', crypto,
    setSessionId: () => {}, setSymbol: () => {}, setTurns: (fn) => { turns = fn(turns); },
    generationRef: { current: 1 }, parseBacktestModule: () => null,
    windowLabelFromComparisonConfig,
  };
  await extract(file, 'handleBacktest', env)('帮我补测一下');
  const last = turns[turns.length - 1] || {};
  const demandedModule = turns.some(t => (t.text || '').includes('请说明要补测的模块'));
  const openedPanel = !!last.setupPanel && last.setupPanel.symbol === '510300.SS'
    && last.setupPanel.questionId === 71 && last.setupPanel.sessionId === 's1';
  results.push({
    id: `U1-direct-${which}`, expected: 'Open Chinese setup, no module-code instruction',
    demandedModule, openedPanel,
    verdict: !demandedModule && openedPanel ? 'PASS' : 'FAIL',
  });
}

// ---- U3：提交 → 迟到响应（期间已切新会话）→ 不把旧任务消息插入新会话 ----
for (const file of files) {
  const which = file.includes('Workspace') ? 'workspace' : 'console';
  let turns = []; let finish;
  const api = { copilotBacktestRequest: () => new Promise((r) => { finish = r; }) };
  let tracked = [];
  const env = {
    setupPanel: undefined, // 探针传入的 turn 自带 setupPanel
    setupBusyRef: { current: false },
    generationRef: { current: 1 },
    requestBacktestTask: sharedRequestBacktestTask(api, (t) => tracked.push(t)),
    taskCreatedTextCn, crypto, pollTask: () => ({ stop() {} }), onTaskStatus: () => {},
    setTurns: (fn) => { turns = fn(turns); },
  };
  if (file.includes('Workspace')) {
    // 工作台版引用 patch(turn.id, ...)
    env.patch = (id, value) => { turns = turns.map(t => t.id === id ? { ...t, ...value } : t); };
  }
  const setup = { symbol: '510300.SS', sessionId: 's1', questionId: 71 };
  const turn = { id: 'old-turn', setupPanel: setup };
  turns = [{ who: 'you', text: '新会话：518880' }];
  const subject = extract(file, 'submitSetup', env);
  const promise = subject(turn, 'A', 'a6_1_costbasis');
  generationRefStep(env);
  function generationRefStep(e) { e.generationRef.current = 2; } // 模拟提交后切到新会话
  finish({ request_id: 'old-task', session_id: 's1', question_id: 71, symbol: '510300.SS', method: 'A', exit_variant: 'a6_1_costbasis', status: 'queued' });
  await promise;
  const staleAppended = turns.some(t => (t.text || '').includes('已创建补测任务'));
  results.push({
    id: `U3-late-${which}`, expected: 'Old task response must not append into new conversation',
    tracked_still_registered: tracked.length === 1, staleAppended,
    verdict: !staleAppended && tracked.length === 1 ? 'PASS' : 'FAIL',
  });
}

// ---- U2：预选不在能力清单 → 不可提交（组件 SSR，与主控同法）----
const esbuild = req('esbuild');
const bundle = esbuild.buildSync({
  entryPoints: [root + '/web/src/components/agent/BacktestSetupPanel.tsx'],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
  jsx: 'automatic',
});
const nodeModule = await import('node:module');
const Module = nodeModule.default;
const cm = new Module(root + '/web/__controller_component.cjs');
cm.filename = root + '/web/__controller_component.cjs';
cm.paths = Module._nodeModulePaths(root + '/web');
cm._compile(bundle.outputFiles[0].text, cm.filename);
const React = req('react');
const { renderToStaticMarkup } = req('react-dom/server');
const { QueryClient, QueryClientProvider } = req('@tanstack/react-query');

function renderPanel(queryData, setup) {
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (queryData) query.setQueryData(['backtestOptions'], queryData);
  return renderToStaticMarkup(React.createElement(
    QueryClientProvider, { client: query },
    React.createElement(cm.exports.default, { setup, onSubmit: () => {} })));
}
// 场景 A（主控原例）：能力只有 B/b3_dual，却预选 A → 必须不可提交
const htmlA = renderPanel(
  { modules: [{ value: 'B' }], exit_variants: [{ value: 'b3_dual' }], defaults: { exit_variant: 'b3_dual' } },
  { symbol: '510300.SS', sessionId: 's1', questionId: 71, defaultModule: 'A', windowLabel: null, hint: null });
const btnA = htmlA.match(/<button[^>]*>创建这次补测<\/button>/)?.[0];
results.push({
  id: 'U2-invalid-preselection', expected: 'Only valid visible capabilities may be submitted',
  button: btnA, verdict: btnA && btnA.includes('disabled') ? 'PASS' : 'FAIL',
});
// 场景 B：能力加载中 → 不渲染静态替身、不可提交
const htmlB = renderPanel(null, { symbol: '510300.SS', sessionId: 's1', questionId: 71, defaultModule: null, windowLabel: null, hint: null });
const btnB = htmlB.match(/<button[^>]*>创建这次补测<\/button>/)?.[0];
const staticFallback = htmlB.includes('上升趋势中的回调打法');
results.push({
  id: 'U2-loading-no-static-fallback', expected: 'No static capability stand-in while loading',
  button: btnB, staticFallback, verdict: btnB && btnB.includes('disabled') && !staticFallback ? 'PASS' : 'FAIL',
});
// 场景 C：能力数据结构不符（防御）→ 不可提交、不渲染静态替身
// （重试入口为交互行为，SSR 不可测，由浏览器走查验证）
const htmlC = renderPanel('ERROR', { symbol: '510300.SS', sessionId: 's1', questionId: 71, defaultModule: null, windowLabel: null, hint: null });
const btnC = htmlC.match(/<button[^>]*>创建这次补测<\/button>/)?.[0];
const staticFallbackC = htmlC.includes('上升趋势中的回调打法');
results.push({
  id: 'U2-malformed-capabilities-no-submit', expected: 'Malformed capability payload must block submit',
  button: btnC, staticFallbackC, verdict: btnC && btnC.includes('disabled') && !staticFallbackC ? 'PASS' : 'FAIL',
});

results.push({ id: 'source-integrity', verdict: JSON.stringify(before) === JSON.stringify(hashes()) ? 'PASS' : 'FAIL', hashes: before });
console.log(JSON.stringify(results, null, 2));

})().catch(e => { console.error(e); process.exitCode = 1 });
