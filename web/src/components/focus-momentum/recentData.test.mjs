import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {mergeFocusContinuation} from './recentData.ts';
const base=JSON.parse(readFileSync(new URL('../../../public/research/focus-momentum/observation.v1.json',import.meta.url)));
const recent=JSON.parse(readFileSync(new URL('../../../public/research/focus-momentum/continuation.v1.json',import.meta.url)));
test('continuation preserves old points and outcome study, with a distinct later cutoff',()=>{
 const merged=mergeFocusContinuation(base,recent);
 assert.equal(merged.asOf,'2026-11-02');assert.equal(merged.series.length,2873);
 assert.deepEqual(merged.series.slice(0,base.series.length),base.series);
 assert.deepEqual(merged.research,base.research);assert.deepEqual(merged.mapping,base.mapping);
 assert.equal(base.asOf,'2025-12-31');assert.equal(merged.latest.qualifiedCount,256);
});
test('pool changes, unverified overlap, duplicate dates and bad last reading fail closed',()=>{
 for(const invalid of [{...recent,overlapVerified:false},{...recent,scope:{sampleSize:5224}},
 {...recent,source:{manifestSha256:'another pool'}},{...recent,series:[recent.series[0],...recent.series]},
 {...recent,latest:{...recent.latest,focus:0}}])assert.throws(()=>mergeFocusContinuation(base,invalid));
});
