import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import esbuild from 'esbuild';

// B 阶段三卡渲染回归（dca/sentiment/mindset，GPT ITERATION:6 冻结契约）：
// 真实 CopilotCards 组件（esbuild 打包 + react-dom/server 静态渲染）。
// 覆盖：① 三类 card_type 经 CopilotCardDispatcher 进入对应分支；
// ② 正常 payload 逐字段展示；③ 缺字段/null 降级文案真实出现；
// ④ 只读措辞（无买入/执行类动作语）；⑤ 既有 recommend/scout 分支不退化。
// 所有 payload 均为合成测试数据，不触网、不跑任何实验。
const root = path.resolve(import.meta.dirname);
const require = createRequire(path.join(root, 'package.json'));

const bundle = esbuild.buildSync({
  entryPoints: [path.join(root, 'src/components/copilot/CopilotCards.tsx')],
  bundle: true, platform: 'node', format: 'cjs', packages: 'external',
  jsx: 'automatic', write: false,
});
const tempFile = path.join(root, '__copilot_cards_component.cjs');
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
  const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
  const { CopilotCardDispatcher, DcaCardView, SentimentCardView, MindsetCardView,
    RecommendCardView, ScoutCardView } = cm.exports;

  const queryClient = new QueryClient();
  // renderToStaticMarkup 会在相邻文本节点间插 <!-- -->，剥离后断言纯文本。
  const render = (el) => renderToStaticMarkup(
    React.createElement(QueryClientProvider, { client: queryClient },
      React.createElement(MemoryRouter, null, el)),
  ).replace(/<!-- -->/g, '');

  // ---- ① 分发路由：三类 card_type 进入对应分支；未知类型保持既有兜底 ----
  const marker = (cardType, data) => render(
    React.createElement(CopilotCardDispatcher, {
      card: { card_type: cardType, data }, preview: null,
    }),
  );
  const routeDca = marker('dca', {});
  assert.match(routeDca, /定投状态板/, 'dca routes to DcaCardView');
  const routeSentiment = marker('sentiment', {});
  assert.match(routeSentiment, /市场情绪速览/, 'sentiment routes to SentimentCardView');
  const routeMindset = marker('mindset', {});
  assert.match(routeMindset, /认知\/心态卡片/, 'mindset routes to MindsetCardView');
  const routeUnknown = marker('trade_report_never_exists', {});
  assert.match(routeUnknown, /已收到功能结果，当前界面暂不支持此类型的展示。/,
    'unknown card_type keeps existing fallback');
  // 直接组件渲染与分发渲染内容一致（分发不是空壳）
  assert.equal(
    routeDca.includes('定投状态板'),
    render(React.createElement(DcaCardView, { data: {} })).includes('定投状态板'),
  );
  assert.equal(
    routeSentiment.includes('市场情绪速览'),
    render(React.createElement(SentimentCardView, { data: {} })).includes('市场情绪速览'),
  );
  assert.equal(
    routeMindset.includes('认知/心态卡片'),
    render(React.createElement(MindsetCardView, { data: {} })).includes('认知/心态卡片'),
  );

  // ---- ② dca 正常 payload：证据账本 + 中美宽度 + 标的逐状态 ----
  const dcaNormal = {
    evidence_available: true,
    evidence_version: 'v2-test',
    error_cn: null,
    states: [{
      symbol: 'TEST00001', name: '合成测试标的', as_of: '2026-09-18',
      close: 1.23, color: 'green',
      ma200_gap: -0.1234, dd2y: -0.234, tier: 'low',
      deep20: true, bottom_zone: false, b200: 43.3,
      state_status: 'ok', window_note: '',
    }],
    breadth: {
      cn: { value: 43.3, health: 'fresh', last_valid_at: '2026-09-18' },
      us: null,
    },
    hint_cn: '合成提示：状态只提示不判定（测试文案）',
  };
  const dcaNormalHtml = render(React.createElement(DcaCardView, { data: dcaNormal }));
  assert.match(dcaNormalHtml, /证据账本可用（版本 v2-test）/);
  assert.match(dcaNormalHtml, /A股宽度/);
  assert.match(dcaNormalHtml, /约 43\.3% 的个股在 200 日均线上方/);
  assert.match(dcaNormalHtml, /健康度：新鲜，截至 2026-09-18/);
  assert.match(dcaNormalHtml, /美股宽度/);
  assert.match(dcaNormalHtml, /数据不可用（健康度：未核实）/);
  assert.match(dcaNormalHtml, /标的逐状态/);
  assert.match(dcaNormalHtml, /1 个/);
  assert.match(dcaNormalHtml, /三色：绿灯（价在20日均线上方且向上）/);
  assert.match(dcaNormalHtml, /距年线 -12\.3%/);
  assert.match(dcaNormalHtml, /两年回撤 -23\.4%/);
  assert.match(dcaNormalHtml, /宽度档位 低位/);
  assert.match(dcaNormalHtml, /深超跌：触发/);
  assert.match(dcaNormalHtml, /底部区域：未触发/);
  assert.match(dcaNormalHtml, /合成提示：状态只提示不判定（测试文案）/);

  // ---- ③ dca 降级：账本不可用如实标注；null=不可判 ≠ 未触发；缺字段不猜 ----
  const dcaDown = {
    evidence_available: false,
    evidence_version: null,
    error_cn: '合成错误：证据账本缺失',
    states: [{
      symbol: 'TEST00002', name: '合成缺数据标的', as_of: '',
      close: null, color: null, ma200_gap: null, dd2y: null,
      tier: null, deep20: null, bottom_zone: null, b200: null,
      state_status: 'insufficient_data', window_note: '',
    }],
    breadth: {},
    hint_cn: null,
  };
  const dcaDownHtml = render(React.createElement(DcaCardView, { data: dcaDown }));
  assert.match(dcaDownHtml, /证据账本数据不可用：合成错误：证据账本缺失/);
  assert.match(dcaDownHtml, /状态无法计算/);
  assert.match(dcaDownHtml, /数据不可用（该标的行情数据不足，状态无法计算）/);
  assert.match(dcaDownHtml, /数据不可用（健康度：未核实）/);
  // 缺 hint_cn 不崩、不占位
  assert.doesNotMatch(dcaDownHtml, /undefined|null/);

  const dcaNulls = {
    evidence_available: true,
    states: [{
      symbol: 'TEST00003', name: '合成部分可判标的', as_of: '2026-09-18',
      close: 2.34, color: null, ma200_gap: null, dd2y: null,
      tier: null, deep20: null, bottom_zone: null, b200: null,
      state_status: 'degraded', window_note: '200日窗口缺 12 个收盘，年线/距年线不可判',
    }],
    breadth: { cn: { value: 43.3, health: 'stale' }, us: null },
    hint_cn: '合成提示（测试文案）',
  };
  const dcaNullsHtml = render(React.createElement(DcaCardView, { data: dcaNulls }));
  // null 必须读作「不可判/—」，绝不能显示成「未触发」
  assert.match(dcaNullsHtml, /深超跌：数据不可判/);
  assert.match(dcaNullsHtml, /底部区域：数据不可判/);
  assert.match(dcaNullsHtml, /三色：数据不可判/);
  assert.match(dcaNullsHtml, /距年线 —/);
  assert.match(dcaNullsHtml, /宽度档位 不可判/);
  assert.match(dcaNullsHtml, /（部分数据降级）/);
  assert.match(dcaNullsHtml, /200日窗口缺 12 个收盘，年线\/距年线不可判/);
  assert.match(dcaNullsHtml, /健康度：偏旧/);
  assert.doesNotMatch(dcaNullsHtml, /深超跌：未触发/);
  assert.doesNotMatch(dcaNullsHtml, /底部区域：未触发/);

  // ---- ④ sentiment 正常 payload：热度/两融叙事 + 标的标注，纯叙事 ----
  const sentimentNormal = {
    available: true,
    reason_cn: null,
    as_of: '2026-09-18',
    hot_boards: [{ name: '合成板块甲', state_cn: '散户情绪过热（92分位）' }],
    cold_boards: [{ name: '合成板块乙', state_cn: '散户情绪冰点（8分位）' }],
    margin: { regime_cn: '融资扩张期（合成文案）', chg_20d_pct: 1.23, rzye_yi: 18000 },
    symbol_note: '合成板块甲：散户情绪过热（92分位）',
    note_cn: '合成说明：情绪面只叙事不判定（测试文案）',
  };
  const sentimentHtml = render(React.createElement(SentimentCardView, { data: sentimentNormal }));
  assert.match(sentimentHtml, /市场情绪速览（叙事标注，不参与技术判定）/);
  assert.match(sentimentHtml, /过热板块：/);
  assert.match(sentimentHtml, /合成板块甲 · 散户情绪过热（92分位）/);
  assert.match(sentimentHtml, /冰点板块：/);
  assert.match(sentimentHtml, /合成板块乙 · 散户情绪冰点（8分位）/);
  assert.match(sentimentHtml, /融资环境/);
  assert.match(sentimentHtml, /融资扩张期（合成文案）（近20日融资余额变化 \+1\.2%）/);
  assert.match(sentimentHtml, /数据时点：2026-09-18/);
  assert.match(sentimentHtml, /标的情绪标注/);
  assert.match(sentimentHtml, /合成板块甲：散户情绪过热（92分位）/);
  assert.match(sentimentHtml, /合成说明：情绪面只叙事不判定（测试文案）/);
  assert.doesNotMatch(sentimentHtml, /情绪面数据不可用/);

  // ---- ⑤ sentiment 降级：缺数据明确不可用，不补猜、不虚构板块 ----
  const sentimentDown = {
    available: false, reason_cn: '板块快照缺失',
    as_of: null, hot_boards: null, cold_boards: null,
    margin: null, symbol_note: null, note_cn: null,
  };
  const sentimentDownHtml = render(React.createElement(SentimentCardView, { data: sentimentDown }));
  assert.match(sentimentDownHtml, /情绪面数据不可用：板块快照缺失/);
  assert.doesNotMatch(sentimentDownHtml, /过热板块|冰点板块|标的情绪标注|融资环境/);
  // 整个 data 为空对象（最坏缺字段）也不崩、如实不可用
  const sentimentEmptyHtml = render(React.createElement(SentimentCardView, { data: {} }));
  assert.match(sentimentEmptyHtml, /情绪面数据不可用。/);
  // 包可用但融资环境这一独立数据源失败：该行单独如实标注不可用
  const sentimentMarginNullHtml = render(React.createElement(SentimentCardView, {
    data: { available: true, hot_boards: [], cold_boards: [], margin: null },
  }));
  assert.match(sentimentMarginNullHtml, /当前没有处于过热或冰点状态的板块。/);
  assert.match(sentimentMarginNullHtml, /融资环境/);
  assert.match(sentimentMarginNullHtml, /数据不可用/);

  // ---- ⑥ mindset 正常 payload：text 必展示、quote 条件渲染、source 出处 ----
  const mindsetNormal = {
    available: true, count: 2, sha256: 'deadbeef',
    items: [
      { category: '合成类别一', text: '合成正文一（测试文案）', quote: '合成引用（测试）', source: '合成出处一' },
      { category: '合成类别二', text: '合成正文二（测试文案）', quote: '', source: '合成出处二' },
    ],
    note_cn: '合成说明：只作叙事与教育用途（测试文案）',
  };
  const mindsetHtml = render(React.createElement(MindsetCardView, { data: mindsetNormal }));
  assert.match(mindsetHtml, /认知\/心态卡片（只作叙事与教育用途，不参与判断）/);
  assert.match(mindsetHtml, /2 条/);
  assert.match(mindsetHtml, /合成类别一/);
  assert.match(mindsetHtml, /合成正文一（测试文案）/);
  assert.match(mindsetHtml, /「合成引用（测试）」/);
  assert.match(mindsetHtml, /出处：合成出处一/);
  assert.match(mindsetHtml, /合成正文二（测试文案）/);
  assert.match(mindsetHtml, /出处：合成出处二/);
  assert.match(mindsetHtml, /合成说明：只作叙事与教育用途（测试文案）/);
  // quote 只出现一次（空 quote 不占位）
  assert.equal((mindsetHtml.match(/合成引用（测试）/g) || []).length, 1,
    'quote renders only for the item that has it');
  assert.doesNotMatch(mindsetHtml, /「」/, 'empty quote renders no placeholder');

  // ---- ⑦ mindset 降级：空 items 用回落说明；缺 text 降级；库不可用回落 ----
  const mindsetEmptyHtml = render(React.createElement(MindsetCardView, {
    data: { available: true, items: [] },
  }));
  assert.match(mindsetEmptyHtml, /心态内容库暂时没有可用条目。/);
  const mindsetNoTextHtml = render(React.createElement(MindsetCardView, {
    data: { available: true, items: [{ category: '合成类别', text: null, source: '合成出处' }] },
  }));
  assert.match(mindsetNoTextHtml, /这条内容缺少正文，无法展示。/);
  const mindsetDownHtml = render(React.createElement(MindsetCardView, {
    data: { available: false },
  }));
  assert.match(mindsetDownHtml, /心态内容库不可用，本轮没有可展示的内容。/);

  // ---- ⑧ 只读措辞：三类卡不得出现买入/执行类动作语 ----
  for (const [name, html] of [
    ['dca', dcaNormalHtml], ['dca-degraded', dcaDownHtml],
    ['sentiment', sentimentHtml], ['sentiment-degraded', sentimentDownHtml],
    ['mindset', mindsetHtml], ['mindset-degraded', mindsetDownHtml],
  ]) {
    assert.doesNotMatch(html, /建议买|可以买|加仓|清仓|止损|止盈|立即执行/,
      `${name} must stay read-only (no action wording)`);
  }

  // ---- ⑨ 既有分支零退化：recommend / scout 仍按原样式渲染 ----
  const recommendHtml = render(React.createElement(RecommendCardView, {
    card: {
      run_date: '2026-09-18', generated_at: '2026-09-18T08:00:00',
      items: [], sectors: [], sentiment_status: '暂未接入',
      fundamental_note: '', disclaimer_cn: '合成免责声明（测试文案）',
    },
  }));
  assert.match(recommendHtml, /今日推荐 · 2026-09-18/);
  assert.match(recommendHtml, /今日无上榜标的。/);
  const scoutHtml = render(React.createElement(ScoutCardView, {
    data: { available: false, trend: [], ambush: [], sentiment: [], note_cn: '合成说明（测试文案）' },
  }));
  assert.match(scoutHtml, /最近机会扫描（每项带历史依据 · 叙事参考层）/);
  assert.match(scoutHtml, /当前三类机会均未激活/);

  console.log('Copilot cards SSR: dca/sentiment/mindset dispatch + normal/degraded payloads + '
    + 'read-only wording + recommend/scout regression passed.');
} finally {
  fs.rmSync(tempFile, { force: true });
}
