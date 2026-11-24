import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { readFile } from 'node:fs/promises';
import { transform } from 'esbuild';
import { build } from 'esbuild';

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const result = await build({
  absWorkingDir: webDir,
  entryPoints: ['src/pages/sectorObservationLogic.ts'],
  bundle: true,
  platform: 'node',
  format: 'esm',
  write: false,
  external: ['../types'],
});
const source = result.outputFiles[0].text.replace(/import[^;]+;\s*/g, '');
const pageSource = await readFile(path.join(webDir, 'src/pages/SectorsPage.tsx'), 'utf8');
await transform(pageSource, { loader: 'tsx', format: 'esm' });
for (const copy of ['小单与超大单差额排名', '供应商按订单规模', '最新交易日尚未核实', '涨跌家数缺失', '50 仅表示排名中间位置', 'RS排名资料不足']) assert.ok(pageSource.includes(copy), `missing expected copy: ${copy}`);
for (const staleCopy of ['散户热度榜', '散户买入最集中', '情绪冰点', '数据累积中', '当前接口未提供数据新鲜度状态']) assert.ok(!pageSource.includes(staleCopy), `stale user-facing copy remains: ${staleCopy}`);
const {
  compareObservationValues,
  compareSectorRankRows,
  stageMissingLabel,
  stageMissingReason,
} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

for (const ascending of [true, false]) {
  const sorted = [null, 20, 100].sort((a, b) => compareObservationValues(a, b, ascending));
  assert.deepEqual(sorted, ascending ? [20, 100, null] : [100, 20, null]);
  const stageRanks = [null, 1, 4].sort((a, b) => compareObservationValues(a, b, ascending));
  assert.deepEqual(stageRanks, ascending ? [1, 4, null] : [4, 1, null]);
}

const emptyWithSampleReason = { stage: null, stage_basis: ['样本不足（命中成分股 < 5 只）'], checkpoints: [], hit_count: 3 };
const emptyWithSmaReason = { stage: null, stage_basis: ['SMA60 尚不可用（样本不足）'], checkpoints: [], hit_count: 30 };
const explicitUnclassified = { stage: null, stage_basis: ['未落入任一明确阶段（价格/均线/RS 组合中性）'], checkpoints: [], hit_count: 30 };
const ambiguous = { stage: null, stage_basis: [], checkpoints: [{ key: 'price', label: '价格需高于SMA60', met: false, detail: null }], hit_count: 30 };
assert.equal(stageMissingLabel(emptyWithSampleReason), '资料不足');
assert.equal(stageMissingLabel(emptyWithSmaReason), '资料不足');
assert.equal(stageMissingLabel(explicitUnclassified), '未归入阶段');
assert.equal(stageMissingLabel(ambiguous), '阶段资料待核');
assert.match(stageMissingReason(emptyWithSampleReason), /样本不足/);
assert.match(stageMissingReason(ambiguous), /价格需高于SMA60/);

const levelRows = [
  { level: 2, rs_pctile: 99, rs_pctile_delta_20: null },
  { level: 1, rs_pctile: 30, rs_pctile_delta_20: 2 },
].sort((a, b) => compareSectorRankRows(a, b, 'rs_pctile', false));
assert.deepEqual(levelRows.map((row) => row.level), [1, 2]);
console.log('sector observation regression passed: numeric/stage missing-last, missing-stage reasons, and level-grouped RS ordering');
