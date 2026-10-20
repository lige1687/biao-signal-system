import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import esbuild from 'esbuild';

// U4 返修验证：真实 EvidenceCardView 组件（esbuild 打包 + react-dom/server 渲染）。
// 合成证据卡明确标注为测试数据；不跑任何收益实验。
const root = path.resolve(import.meta.dirname);
const require = createRequire(path.join(root, 'package.json'));

const bundle = esbuild.buildSync({
  entryPoints: [path.join(root, 'src/components/EvidenceCardView.tsx')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external',
  jsx: 'automatic', write: false,
});
const tempFile = path.join(root, '__evidence_card_component.cjs');
fs.writeFileSync(tempFile, bundle.outputFiles[0].text);
try {
  const Module = require('node:module');
  const cm = new Module(tempFile);
  cm.filename = tempFile;
  cm.paths = Module._nodeModulePaths(path.join(root, 'web'));
  cm._compile(fs.readFileSync(tempFile, 'utf8'), tempFile);
  const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const { MemoryRouter } = require('react-router-dom');
  const EvidenceCardView = cm.exports.default;

  // 合成支持卡：含附带说明（window_note_cn / differences_cn）+ R 值
  const supportingCard = {
    facts: { symbol: 'TEST-SUPPORT', as_of: '2026-08-06', verdict_cn: '合成卡（测试注入）' },
    history_and_scope: {
      note_cn: '旧胜率表只有 exact 支持本问题（合成说明）',
      comparison_config: { window: { start: '2020-06-02', end: '2026-08-06' }, window_state: 'verified' },
      matched_runs: [{
        request_id: 'req-s1', run_id: 'run-support', supports_question: true,
        module: 'A', exit_variant: 'a6_1_costbasis', compatibility: 'exact',
        differences_cn: ['合成差异说明：窗口不同'], window_note_cn: '合成窗口说明：2020-06-02 起',
        summary: { trade_count: 24, win_rate: 0.58, expectancy_r: 0.21 },
      }],
    },
    pending_conditions: [],
  };
  // 合成不匹配卡
  const referencingCard = {
    facts: { symbol: 'TEST-REF', as_of: '2026-08-06' },
    history_and_scope: {
      matched_runs: [{
        request_id: 'req-r1', run_id: 'run-ref', supports_question: false,
        module: 'B', exit_variant: 'b3_dual', compatibility: 'incompatible',
        differences_cn: ['合成差异：模块不一致'], summary: null,
      }],
    },
  };

  const render = (card, props = {}) => renderToStaticMarkup(
    React.createElement(MemoryRouter, null,
      React.createElement(EvidenceCardView, { card, ...props })),
  );

  // 支持卡：首层中文结论 + R 解释；附带说明在折叠区内（默认收起）
  const supportHtml = render(supportingCard);
  assert.match(supportHtml, /适用于这次问题/);
  assert.match(supportHtml, /上升趋势中的回调打法（A）/);
  assert.match(supportHtml, /0\.21 倍风险金额/);
  assert.match(supportHtml, /R＝每笔预定风险金额的倍数/);
  assert.match(supportHtml, /合成差异说明：窗口不同/);
  assert.match(supportHtml, /合成窗口说明：2020-06-02 起/);
  assert.match(supportHtml, /<details class="evidence-card-details">/, 'supporting notes collapsed by default');
  // 首屏正文不出现工程枚举（U4：note 显示映射）
  assert.doesNotMatch(supportHtml, /只有 exact 支持本问题/);

  // 不匹配卡：中文兼容性说法 + 详情区
  const refHtml = render(referencingCard);
  assert.match(refHtml, /与这次问题不一致（仅作参考）/);
  assert.match(refHtml, /B 专用双条件退出（跌回密集区上沿＋20日线组下弯）（退出B）/);

  // U4 验收：forceDetailsOpen 真展开（details 带 open 属性）
  const openHtml = render(supportingCard, { forceDetailsOpen: true });
  assert.match(openHtml, /<details class="evidence-card-details"( open=""| open)>/, 'forceDetailsOpen expands details');
  const openRefHtml = render(referencingCard, { forceDetailsOpen: true });
  assert.match(openRefHtml, /<details class="evidence-card-details"( open=""| open)>/);

  console.log('Evidence card SSR: supporting notes retained, chinese mapping, forceDetailsOpen passed.');
} finally {
  fs.rmSync(tempFile, { force: true });
}
