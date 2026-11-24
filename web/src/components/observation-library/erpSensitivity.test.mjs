import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {build} from 'esbuild';
const bundle=await build({stdin:{contents:'export {withErpSigma} from "./src/components/observation-library/erpSensitivity.ts";export {erpBands} from "./src/components/observation-library/erpBands.ts";export {erpCrossings} from "./src/components/observation-library/erpCrossings.ts";',resolveDir:process.cwd()},bundle:true,platform:'node',format:'esm',write:false});
const {withErpSigma,erpBands,erpCrossings}=await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString('base64')}`);
const input=JSON.parse(readFileSync(new URL('../../../public/research/erp-bands/cn-reference.json',import.meta.url))).points;
const bands=erpBands(input.map(p=>({date:p.date,value:p.value})));
test('display first crossings match independent Python study at all three multipliers',()=>{
 for(const [k,n] of [[1,36],[1.5,24],[2,17]])assert.equal(erpCrossings(withErpSigma(bands,k)).length,n);
 assert.deepEqual(withErpSigma(bands,2),bands);
});
test('sensitivity changes preserve warmup nulls and do not mutate original alert bands',()=>{
 const before=structuredClone(bands);const loose=withErpSigma(bands,1);
 assert.equal(loose[0].upper,null);assert.deepEqual(bands,before);
 assert.equal(loose.at(-1).upper,loose.at(-1).middle+loose.at(-1).sigma);
});
