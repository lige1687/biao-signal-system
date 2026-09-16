import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import esbuild from 'esbuild';

// 买点①序号渲染回归：有系统候选 => 可点按钮；无候选/序号越界 => 普通文字（暗态），
// 不允许「点击无反应的假按钮」。真实 AgentMarkdown 组件 esbuild 打包 + SSR。
const root = path.resolve(import.meta.dirname);
const require = createRequire(path.join(root, 'package.json'));

const bundle = esbuild.buildSync({
  entryPoints: [path.join(root, 'src/components/AgentMarkdown.tsx')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external',
  jsx: 'automatic', write: false,
});
const tempFile = path.join(root, '__agent_markdown_component.cjs');
fs.writeFileSync(tempFile, bundle.outputFiles[0].text);
try {
  const Module = require('node:module');
  const cm = new Module(tempFile);
  cm.filename = tempFile;
  cm.paths = Module._nodeModulePaths(root);
  cm._compile(fs.readFileSync(tempFile, 'utf8'), tempFile);
  const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const AgentMarkdown = cm.exports.default;
  const render = (props) => renderToStaticMarkup(React.createElement(AgentMarkdown, props));
  const noop = () => undefined;

  // 1. 有候选覆盖序号 => 可点按钮，带定位提示
  let html = render({ text: '先看买点①，再看买点②。', onBp: noop, notableCount: 2 });
  assert.equal((html.match(/<button/g) || []).length, 2, 'locatable chips must be buttons');
  assert.ok(html.includes('点击在图上定位该买点'), 'button carries locate hint');
  assert.ok(!html.includes('bp-inline dim'), 'locatable chips must not be dimmed');

  // 2. 无候选 => 普通文字（暗态 span），没有任何按钮
  html = render({ text: '提到买点①但没有候选数据。', onBp: noop, notableCount: 0 });
  assert.equal((html.match(/<button/g) || []).length, 0, 'no candidates => no fake button');
  assert.ok(html.includes('<span class="bp-inline dim"'), 'plain dim span rendered');
  assert.ok(html.includes('无法定位'), 'span explains why it is not locatable');

  // 3. 序号超出候选数 => 越界的那个降级为文字，覆盖到的仍是按钮
  html = render({ text: '买点① 和 买点③。', onBp: noop, notableCount: 2 });
  assert.equal((html.match(/<button/g) || []).length, 1, 'only covered index is a button');
  assert.equal((html.match(/bp-inline dim/g) || []).length, 1, 'out-of-range index is plain text');

  // 4. 数字与中文序号写法同口径：买点1 / 买点二
  html = render({ text: '买点1 与 买点二。', onBp: noop, notableCount: 2 });
  assert.equal((html.match(/<button/g) || []).length, 2, 'arabic/chinese numerals both parse');

  // 5. 既有行内能力不回退：加粗 / 代码 / 价位链接
  html = render({
    text: '**重点** 与 `代码`，下方关键位 1.256。',
    onBp: noop, notableCount: 0,
    priceLevels: [{ role: '下方关键位', price: 1.256, kind: 'below', dist_pct: 2, from_cn: '底部构造' }],
    onPrice: noop,
  });
  assert.ok(html.includes('<strong>'), 'bold still renders');
  assert.ok(html.includes('md-code'), 'inline code still renders');
  assert.ok(html.includes('ar-price-link'), 'price link still renders');

  console.log('Agent markdown: bp chip locatable/plain degradation, numeral variants, inline regressions passed.');
} finally {
  fs.rmSync(tempFile, { force: true });
}
