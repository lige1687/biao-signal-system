import assert from 'node:assert/strict';
import {
  subjectLabel, moduleCn, exitCn, compatCn, expectancyCn, noteCn, EXIT_HINT_CN_SIMPLE,
  detectUnsupportedExitRequest, SUPPORTED_EXITS_CN,
  atrDiscussionDraft, validExitsFor, resolveExitAfterModuleChange,
  windowLabelFromComparisonConfig,
} from '/tmp/lei-agent-ux.mjs';

// R1 独立对照（主控四行表）：退出1 引擎条件是"同时"——
// (close<ema20)&(close<close_lag20)（engine.py::prepare_frame），
// 不是"任一跌破"。先证明两种语义在这组数据上结论不同（文案必须能区分），
// 再核对展示文案确实用"同时"且不含"或/任一"。
const EXIT1_ROWS = [ // [close, ema20, lag20]
  [105, 100, 100], [95, 100, 90], [95, 90, 100], [85, 100, 90],
];
const engineBoth = ([c, e, l]) => (c < e) && (c < l);
const misreadAny = ([c, e, l]) => (c < e) || (c < l);
assert.deepEqual(EXIT1_ROWS.map(engineBoth), [false, false, false, true], 'engine truth column');
assert.deepEqual(EXIT1_ROWS.map(misreadAny), [false, true, true, true], '"任一" misreading differs from engine on rows 2/3 — wording must say 同时');
assert.match(EXIT_HINT_CN_SIMPLE.a6_1_costbasis, /同时低于20日指数均线（EMA20）和20个交易日前的收盘价/);
assert.match(EXIT_HINT_CN_SIMPLE.a6_1_costbasis, /下一交易日开盘退出/);
assert.match(EXIT_HINT_CN_SIMPLE.a6_1_costbasis, /初始结构止损仍独立生效/);
assert.doesNotMatch(EXIT_HINT_CN_SIMPLE.a6_1_costbasis, /任一|，或 /);

// 中文映射：准确对应引擎既有选项；未知值原样兜底（不发明能力）
assert.equal(moduleCn('A'), '上升趋势中的回调打法（A）');
assert.equal(moduleCn('B'), '横盘整理后突破密集区的打法（B）');
assert.equal(moduleCn('X'), '模块X', 'unknown module falls back to raw code');
assert.equal(moduleCn(null), '未指定');
// U4：退出名称按引擎实际条件表述（A6①抵扣价 / A6②顶部构造+关键性波动 /
// A6③仅初始结构止损 / B3双条件），不用含糊的"成本区"，不承诺相对结果
assert.equal(exitCn('a6_1_costbasis'), '收盘同时跌破20日指数均线与抵扣价时退出（退出1）');
assert.equal(exitCn('b3_dual'), 'B 专用双条件退出（跌回密集区上沿＋20日线组下弯）（退出B）');
assert.equal(exitCn('not_a_variant'), 'not_a_variant', 'unknown exit is not renamed into a fake option');
assert.equal(exitCn(undefined), '未指定');

// 兼容性映射：exact/unknown → 中文说法，不输出英文枚举
assert.equal(compatCn('exact'), '适用于这次问题');
assert.equal(compatCn('unknown'), '暂不能确定是否适用');
assert.equal(compatCn('incompatible'), '与这次问题不一致（仅作参考）');
assert.equal(compatCn(''), '暂不能确定是否适用', 'missing compatibility must not read as applicable');

// R 的说法：倍数而非收益率；数值原样
assert.match(expectancyCn(0.21), /0\.21 倍风险金额/);
assert.doesNotMatch(expectancyCn(0.21), /%|收益率/);
assert.equal(expectancyCn(null), '每笔平均 -');

// note 显示映射：exact/unknown 工程枚举不直达用户（U4）
assert.doesNotMatch(noteCn('旧表兼容性 unknown，只有 exact 支持本问题'), /exact|unknown/);
assert.match(noteCn('只有 exact 支持本问题'), /只有与这次问题完全一致的结果才支持本问题/);

// 不支持项检测：只拦 ATR 止损说法，普通讨论不拦
assert.equal(detectUnsupportedExitRequest('换成 ATR 止损再补测对比一下'), 'ATR 止损');
assert.equal(detectUnsupportedExitRequest('用atr止损试试'), 'ATR 止损');
assert.equal(detectUnsupportedExitRequest('补测 模块A 退出2'), null);
assert.equal(detectUnsupportedExitRequest('帮我用结构止损跑一次'), null);

// 支持清单（拦截文案与面板共用）：不含 ATR，不用"成本区"含糊词（U4）
for (const term of ['同时跌破20日指数均线与抵扣价', '关键性波动', '初始结构止损']) {
  assert.ok(SUPPORTED_EXITS_CN.includes(term), `supported list mentions ${term}`);
}
assert.ok(!SUPPORTED_EXITS_CN.includes('ATR'));
assert.ok(!SUPPORTED_EXITS_CN.includes('成本区'));

// U1：ATR 拦截后的讨论草稿不得再触发后端补测意图
// （触发词来自 src/lei_signal/copilot/resolve.py::_BACKTEST_RE；
//   若后端词表变化，请同步这里并说明）
const BACKTEST_TRIGGER = /补测|回测|测一下|复跑|重新测|再测|跑一次回测/;
for (const sym of ['510300.SS', null]) {
  const draft = atrDiscussionDraft(sym);
  assert.ok(!BACKTEST_TRIGGER.test(draft), `draft must avoid trigger words: ${draft}`);
  assert.match(draft, /ATR/);
  assert.match(draft, /只讨论思路/);
}

// U2：某打法下合法退出清单（b3_dual 仅 B）
const ALL = ['a6_1_costbasis', 'a6_2_top_plus_keywave', 'a6_3_structure_stop', 'b3_dual'];
assert.deepEqual(validExitsFor('B', ALL), ALL);
assert.deepEqual(validExitsFor('A', ALL), ALL.slice(0, 3));
assert.deepEqual(validExitsFor(null, ALL), ALL.slice(0, 3));
// 切打法后失效退出立即回落合法默认，绝不发送隐藏旧选项
assert.equal(resolveExitAfterModuleChange('b3_dual', 'A', ALL, 'a6_1_costbasis'), 'a6_1_costbasis');
assert.equal(resolveExitAfterModuleChange('a6_2_top_plus_keywave', 'A', ALL, 'a6_1_costbasis'), 'a6_2_top_plus_keywave', 'still-valid exit is kept');
assert.equal(resolveExitAfterModuleChange(null, 'B', ALL, 'b3_dual'), 'b3_dual');

// U2：窗口如实显示——有冻结窗口写"沿用"，没有则区分说明
assert.equal(
  windowLabelFromComparisonConfig({ window: { start: '2020-06-02', end: '2026-08-06', source: 'message' }, window_state: 'verified' }),
  '沿用原问题窗口 2020-06-02 ~ 2026-08-06',
);
assert.match(windowLabelFromComparisonConfig({ window: null, window_state: 'unverified' }), /没有可核实的窗口选择/);
assert.equal(windowLabelFromComparisonConfig(undefined), null, 'no config at all reads as absent, not fabricated');

console.log('Agent UX phase1+rework: mappings, engine-accurate exit texts, R phrasing, ATR draft safety, exit/module consistency, window label passed.');

assert.equal(subjectLabel("515880.SS", "通信ETF"), "通信ETF（515880.SS）");
assert.equal(subjectLabel("515880.SS", "515880.SS"), "名称待核实（515880.SS）");
