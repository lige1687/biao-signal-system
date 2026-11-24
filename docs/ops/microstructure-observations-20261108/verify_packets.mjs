import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {build} from '../../../web/node_modules/esbuild/lib/main.js';
const root = new URL('../../../',import.meta.url);
const artifact = await build({entryPoints:[new URL('web/src/components/market-observation-alerts/microstructureData.ts',root).pathname],bundle:true,write:false,platform:'node',format:'esm'});
const {parseMicrostructure,reading,selectedMicro} = await import(`data:text/javascript;base64,${Buffer.from(artifact.outputFiles[0].contents).toString('base64')}`);
const files={};const cards=[];const unavailable=[];
for(const branch of ['funding','equity','derivatives']){
 const file=new URL(`web/public/research/microstructure-observations-20261108/${branch}.json`,root);
 const raw=await readFile(file);const packet=parseMicrostructure(JSON.parse(raw));
 files[branch]={sha256:createHash('sha256').update(raw).digest('hex'),cards:packet.cards.length,unavailable:packet.unavailable.length};
 cards.push(...packet.cards);unavailable.push(...packet.unavailable);
}
const ids=[...cards,...unavailable].map(c=>c.id);assert.equal(new Set(ids).size,ids.length,'all packets must use unique ids');
for(const c of cards){
 assert.deepEqual(selectedMicro(cards,c.market,[c.id]),[c]);
 assert.equal(reading(c).date,c.points[c.points.length-1].date);
 if(c.unit==='相关系数')assert.ok(c.points.every(p=>p.value===null||p.value>=-1&&p.value<=1));
}
const catalog=JSON.parse(await readFile(new URL('web/public/research/microstructure-observations-20261108/catalog.json',root)));
assert.deepEqual(new Set(catalog.indicators.map(c=>c.id)),new Set(ids));
assert.equal(catalog.indicators.filter(i=>i.status==='ready').length,cards.filter(c=>c.points.some(p=>p.value!==null)).length);
const result={verifiedAt:new Date().toISOString(),files,cards:cards.length,unavailable:unavailable.length,
 latest:cards.map(c=>({id:c.id,...reading(c)}))};
await writeFile(new URL('packet-verification.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({files,cards:cards.length,unavailable:unavailable.length}));
