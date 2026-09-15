import assert from 'node:assert/strict';
import { taskStatusTextCn, phaseLabelCn, isTerminal } from '/tmp/lei-agent-tasks.mjs';

const base = { request_id: 'btr_x', session_id: 's1', question_id: 1, symbol: '510300.SS',
               method: 'A', exit_variant: 'a6_1_costbasis', run_id: 'run_1' };

// 五状态文案两两不同
const states = ['queued', 'running', 'completed', 'failed', 'interrupted'];
const texts = states.map(s => taskStatusTextCn({ ...base, status: s, error: s === 'completed' ? undefined : '数据不可用' }));
assert.equal(new Set(texts).size, 5, 'five states have five distinct texts');

// 完成态：给可用下一步，运行编号只作查档括号，不冒充结论
assert.match(texts[2], /已算好/);
assert.match(texts[2], /接着就这个标的提问/);
assert.match(texts[2], /run_1/);

// 失败态：不把失败写成"没有机会"，给可行动作
assert.match(texts[3], /没有成功/);
assert.match(texts[3], /失败不代表这个标的机会或风险有任何变化/);
assert.match(texts[3], /重新发起/);

// 中断态：说明只是回传断了，可恢复
assert.match(texts[4], /中断只是结果回传断了/);
assert.match(texts[4], /重新发起/);

// 排队/运行态是进行时，不带"中断"字样
assert.doesNotMatch(texts[0], /中断|失败/);
assert.doesNotMatch(texts[1], /中断|失败/);

// 中文打法名进文案，且不出现裸枚举
assert.match(texts[2], /上升趋势中的回调打法（A）/);
assert.match(texts[2], /收盘同时跌破20日指数均线与抵扣价时退出（退出1）/);

assert.equal(phaseLabelCn('queued'), '排队中');
assert.deepEqual(isTerminal('completed'), true);
assert.deepEqual(isTerminal('running'), false);

console.log('Agent tasks: five-state texts, terminal semantics, chinese naming passed.');
