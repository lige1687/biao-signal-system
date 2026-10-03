import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
async function load(path) {
  const out=await build({entryPoints:[fileURLToPath(new URL(path,import.meta.url))],bundle:true,platform:'node',format:'esm',write:false});
  return import(`data:text/javascript;base64,${Buffer.from(out.outputFiles[0].text).toString('base64')}`);
}
const nav=await load('./src/features/market-understanding/navigation.ts');
const model=await load('./src/features/market-understanding/dashboard-model.ts');
const tones=await load('./src/features/market-understanding/reference-reading.ts');
let count=0;
function test(name,fn){fn();count++;console.log(`PASS ${name}`);}
test('five old sections and all legacy deep links preserve destination and query',()=>{
 const old=['fund-sec-market','fund-sec-rates','fund-sec-overlay','fund-sec-macro','fund-sec-usmacro'];
 assert.deepEqual(nav.marketSections.map(s=>s.id),['overview',...old]);
 for(const id of old){assert.equal(nav.legacyFundamentalsTarget('?context=example',`#${id}`),`/market-understanding?context=example#${id}`);assert.equal(nav.marketSectionFromHash(`#${id}`),id);}
 assert.equal(nav.legacyFundamentalsTarget('',''),'/market-understanding#fund-sec-market');
 assert.equal(nav.marketSectionFromHash(''),'overview');
 assert.equal(nav.marketSectionFromHash('#not-a-tab'),'overview');
 assert.equal(nav.legacyFundamentalsTarget('','#not-a-tab'),'/market-understanding#fund-sec-market');
});
test('every plotted reference has readable meaning, color and original threshold identity',()=>{
 for(const m of model.metrics)for(const r of model.referencesFor(m.key)){
  assert.ok(r.explanation.length>15,m.key);assert.ok(r.label.includes(r.y.toLocaleString('zh-CN')),m.key);
  assert.equal(r.color,tones.referenceColors[r.tone]);assert.ok(['定义线','原页面参考','历史分位参考'].includes(r.kind));
 }
});
test('opportunity direction reverses between valuation and yield compensation',()=>{
 const pe=model.referencesFor('pe_cn'),cape=model.referencesFor('cape_us'),erp=model.referencesFor('erp_cn');
 assert.equal(pe[0].tone,'opportunity');assert.match(pe[0].label,/≤/);assert.equal(pe[2].tone,'risk');assert.match(pe[2].label,/≥/);
 assert.equal(cape[0].tone,'opportunity');assert.equal(erp[2].tone,'opportunity');assert.match(erp[2].label,/≥/);assert.equal(erp[0].tone,'risk');
});
test('volatility, leverage and definitions do not silently become buy signals',()=>{
 const high=model.referencesFor('vix')[2];assert.equal(high.tone,'risk');assert.match(high.explanation,/机会观察/);assert.match(high.explanation,/不能直接抄底/);
 assert.equal(model.referencesFor('margin_rzyezb')[0].tone,'context');assert.deepEqual(model.referencesFor('margin_rzrqye'),[]);
 assert.equal(model.referencesFor('pmi')[0].tone,'context');assert.match(model.referencesFor('pmi')[0].explanation,/高于50.*低于50/);
 assert.ok(!model.referencesFor('cpiaucsl_yoy').some(r=>/联储目标|PCE目标/.test(r.label)));
});
test('merged content keeps old modules and fixes CPI display without changing shared threshold numbers',()=>{
 const old=readFileSync(new URL('./src/pages/FundamentalsPage.tsx',import.meta.url),'utf8');
 for(const component of ['MarketSection','EtfStrengthSection','SentimentViews','RatesSection','PositionBandCard','CorrelationMapCard','OverlaySection','MacroSection','UsMacroSection'])assert.ok(old.includes(`<${component}`),component);
 for(const s of nav.marketSections.filter(s=>s.id!=='overview'))assert.ok(old.includes(`id: "${s.id}"`));
 assert.ok(old.includes("zones: [], markLines: referencesFor(it.key)"));
 const top=readFileSync(new URL('./src/components/TopNav.tsx',import.meta.url),'utf8');assert.ok(!top.includes('to: "/fundamentals"'));assert.ok(top.includes('to: "/market-understanding"'));
});
console.log(`${count} market integration checks passed; synthetic inputs, no financial experiment.`);
