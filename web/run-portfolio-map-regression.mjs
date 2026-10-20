import assert from 'node:assert/strict';
import { bareCode, suffixOf, exchangeFundSuffix, classifySymbol, nameContains, mapHoldingsToSymbols } from '/tmp/lei-portfolio-symbols.mjs';

assert.equal(bareCode('515880.SS'), '515880');
assert.equal(bareCode('^IXIC'), '^IXIC');
assert.equal(suffixOf('ABC.L'), 'L');
assert.equal(suffixOf('QQQ'), '');

// 代码段判定：只有场内基金段有市场含义
assert.equal(exchangeFundSuffix('515880'), 'SS');
assert.equal(exchangeFundSuffix('512890'), 'SS');
assert.equal(exchangeFundSuffix('159915'), 'SZ');
assert.equal(exchangeFundSuffix('161125'), 'SZ'); // LOF 段属深市场内段
assert.equal(exchangeFundSuffix('000300'), null, '指数段不是场内基金标识');
assert.equal(exchangeFundSuffix('017641'), null, '场外基金代码段不是行情标识');
assert.equal(exchangeFundSuffix('600519'), null, '股票段不是场内基金标识');

// 来源身份分类：标识符自证才可信，字母代码/指数/板块/错配一律不足
assert.equal(classifySymbol('515880.SS'), 'cn_exchange_fund');
assert.equal(classifySymbol('159915.SZ'), 'cn_exchange_fund');
assert.equal(classifySymbol('515880.SZ'), 'insufficient', '段-后缀错配身份不足');
assert.equal(classifySymbol('000300.SS'), 'insufficient', '指数段身份不足');
assert.equal(classifySymbol('SOXX'), 'insufficient', '普通自选字母代码不自动视为美股ETF');
assert.equal(classifySymbol('TH881121.SECTOR'), 'insufficient', '板块身份不足');

// 同人核对：整段包含，多出部分不得含身份标记
assert.ok(nameContains('通信ETF国泰', '通信ETF国泰'));
assert.ok(nameContains('红利低波ETF', '红利低波ETF华泰柏瑞'), '多出仅公司名算同一产品');
assert.ok(!nameContains('通信ETF国泰', '通信ETF国泰(QDII)A'), '括号身份不同不算同一产品');
assert.ok(!nameContains('国泰通信ETF联接A', '通信ETF国泰'), '联接与ETF语序不同不算包含');

const sources = [
  { symbol: '515880.SS', name: '通信ETF国泰', identity: 'cn_exchange_fund' },
  { symbol: '512890.SS', name: '红利低波ETF华泰柏瑞', identity: 'cn_exchange_fund' },
  { symbol: '000300.SS', name: '沪深300', identity: 'insufficient' }, // 指数组
  { symbol: 'QQQ', name: '纳指100 QQQ', identity: 'us_etf_catalog' },
];
const H = (id, name, code) => ({ holding_id: id, name, code });

// 正例：代码+市场+产品类型一致且名称互相包含 -> 可映射
let m = mapHoldingsToSymbols([H('a', '通信ETF国泰', '515880')], sources);
assert.equal(m.get('a')?.symbol, '515880.SS');
m = mapHoldingsToSymbols([H('a2', '红利低波ETF', '512890')], sources);
assert.equal(m.get('a2')?.symbol, '512890.SS', '多出仅公司名的简称可映射');

// 反例1（同码不同产品）：代码撞上但名称完全不含 -> 不映射
m = mapHoldingsToSymbols([H('b', '南方有色金属ETF', '515880')], sources);
assert.equal(m.has('b'), false, 'same code different product must stay unmapped');

// 反例2（通用名称片段重叠）：有共同词但互不包含 -> 不映射
m = mapHoldingsToSymbols([H('c', '国泰通信ETF联接A', '515880')], sources);
assert.equal(m.has('c'), false, '联接基金不能因名称相似映射到ETF');

// 反例3（括号内身份信息不同）：(QDII)A 与无括号不是同一产品 -> 不映射
m = mapHoldingsToSymbols([H('d', '通信ETF国泰(QDII)A', '515880')], sources);
assert.equal(m.has('d'), false, 'bracket identity differs => not the same product');

// 反例4（场外/指数代码段）：不是场内标识 -> 不映射（即使名称包含）
m = mapHoldingsToSymbols([H('e', '通信ETF国泰', '017641')], [
  { symbol: '017641.SZ', name: '通信ETF国泰联接', identity: 'insufficient' },
]);
assert.equal(m.has('e'), false, 'off-exchange fund code is not a quote identifier');
m = mapHoldingsToSymbols([H('f', '沪深300', '000300')], sources);
assert.equal(m.has('f'), false, 'index code segment must not map');

// 反例5（纯名称相等/相似）：名称不是证据 -> 不映射
m = mapHoldingsToSymbols([H('g', '沪深300', null)], sources);
assert.equal(m.has('g'), false, 'name alone never maps');
m = mapHoldingsToSymbols([H('h', '通信ETF国泰', '512890')], sources);
assert.equal(m.has('h'), false, 'different code + same-ish name never maps');

// 反例6（复现案例：ABC / ABC.L）：目录身份但来源带市场后缀 -> 不跨市场匹配
m = mapHoldingsToSymbols([H('probe', 'US product', 'ABC')], [
  { symbol: 'ABC.L', name: 'Different market product', identity: 'us_etf_catalog' },
]);
assert.equal(m.has('probe'), false, 'must not strip market suffix to match across markets');

// 反例7（普通自选身份不足）：自选里的字母代码不是美股 ETF 身份证明
m = mapHoldingsToSymbols([H('i', 'US product', 'ABC')], [
  { symbol: 'ABC', name: 'Some watchlist product', identity: 'insufficient' },
]);
assert.equal(m.has('i'), false, 'plain watchlist entry is not US-ETF identity');

// 反例8（同码多来源）-> 歧义不映射
m = mapHoldingsToSymbols(
  [H('j', '纳指ETF', 'QQQ')],
  [...sources, { symbol: 'QQQ2', name: '纳指100 QQQ', identity: 'us_etf_catalog' }, { symbol: 'QQQ', name: '另一目录QQQ', identity: 'us_etf_catalog' }],
);
assert.equal(m.has('j'), false, 'ambiguous duplicate code must stay unmapped');

// 正例（美股目录 ticker）：目录身份明确 + 无后缀 + 代码相等 -> 可映射
m = mapHoldingsToSymbols([H('k', 'Invesco纳指QQQ', 'QQQ')], sources);
assert.equal(m.get('k')?.symbol, 'QQQ');

console.log('Portfolio symbol mapping: source-identity model, cross-market suffix guard, insufficient-identity and all earlier counterexamples passed.');
