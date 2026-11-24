import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";

const built = await build({ entryPoints: [new URL("./factorCurvesModel.ts", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm" });
const m = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
const root = new URL("../../../public", import.meta.url);
const fetcher = async url => new Response(await readFile(new URL(`.${url}`, root.href + "/")), { headers: { "content-type": "application/json" } });
const doc = await m.loadCurveLibrary(undefined, fetcher);
const dataset = doc.datasets.find(d => d.id === "fixed2014_300_legacy");
const rawCatalog = JSON.parse(await readFile(new URL("./research/factor-curve-library-20261022/catalog.json", root.href + "/"), "utf8"));
const source = JSON.parse(await readFile(new URL("./research/factor-curve-library-20261022/legacy-summary.json", root.href + "/"), "utf8"));
const defaults = m.defaultSelection(doc, new URLSearchParams({dataset: dataset.id}));

test("published catalog preserves exact sample identity, unavailable scopes and all saved streams", () => {
  assert.equal(dataset.market, "A股");
  assert.match(dataset.universeLabel, /不是沪深300/);
  assert.equal(dataset.factors.filter(f => f.available).length, 4);
  assert.equal(dataset.factors.filter(f => !f.available).length, rawCatalog.pendingFactors.filter(f => !dataset.factors.some(v => v.available && v.id === f.id)).length);
  assert.equal(doc.datasets.filter(d => !d.available).length, rawCatalog.unavailableUniverses.length);
  assert.equal(Object.keys(dataset.streams).length, 84);
  assert.deepEqual(dataset.streams, source.streams);
  assert.equal(defaults.fee, "25");
});

test("64 real factor/pool/cost/period combinations bind all six correct streams and daily metrics", () => {
  let checked = 0;
  for (const f of dataset.factors.filter(f => f.available)) for (const pool of dataset.pools) for (const fee of dataset.fees_bps) for (const period of Object.keys(dataset.periods)) {
    const choice = { ...defaults, curveFactor: f.id, pool: pool.id, fee: String(fee), period };
    const selected = m.selectCurves(doc, choice);
    assert.equal(selected.series.length, 6);
    for (const series of selected.series) {
      const key = series.id === "pool" ? `${pool.id}__pool__fee${fee}` : `${pool.id}__${f.id}__${series.id}__fee${fee}`;
      assert.deepEqual(series.metrics, source.streams[key].period[period]);
      const points = source.streams[key].points;
      const [start, end] = source.periods[period];
      const prior = points.filter(p => p[0].slice(0, 7) < start).at(-1);
      const raw = points.filter(p => p[0].slice(0, 7) >= start && p[0].slice(0, 7) <= end);
      assert.equal(series.points.length, raw.length + 1);
      assert.equal(series.points[0].value, 0);
      assert.equal(series.points.at(-1).value, (raw.at(-1)[1] / prior[1] - 1) * 100);
      assert.equal(series.points.at(-1).drawdown, raw.at(-1)[4] * 100);
      assert.equal(series.points.at(-1).unknownMax, raw.at(-1)[5] * 100);
    }
    checked++;
  }
  assert.equal(checked, 64);
});

test("environment selection only adds original intervals and conditional statistics, never splices capital", () => {
  const all = m.selectCurves(doc, defaults);
  for (const regime of ["strong", "weak"]) {
    const selected = m.selectCurves(doc, { ...defaults, regime });
    assert.deepEqual(selected.series, all.series);
    assert.ok(selected.regime.intervals.length > 0);
    assert.match(selected.regime.regimeDefinition, /上月末/);
  }
  const key = `${defaults.pool}__${defaults.curveFactor}__G5__fee${defaults.fee}`;
  assert.equal(dataset.regimeStatistics[key].all.strong.months, 75);
  assert.equal(dataset.regimeStatistics[key].all.weak.months, 57);
  assert.throws(() => m.selectCurves(doc, { ...defaults, regime: "unknown" }), /没有该类环境/);
});

test("unknown valuation edges stay dashed without a solid bridge; absent prices remain gaps", () => {
  const point = (date, value, unknownMax = 0) => ({ date, value, unknownMax, unknown: 0, cash: 0, drawdown: 0 });
  const points = [point("a", 0), point("b", 1), point("c", 2, 10), point("d", 3), point("e", 4)];
  const segments = m.priceSegments(points);
  assert.deepEqual(segments.map(s => s.uncertain), [false, true, false]);
  assert.deepEqual(segments[0].values, [0, 1, null, null, null]);
  assert.deepEqual(segments[2].values, [null, null, null, 3, 4]);
  assert.equal(m.priceSegments([point("a", 0), point("b", null), point("c", 2)]).length, 0);
  assert.equal(m.priceSegments([point("a", 0), point("b", 1, null)])[0].uncertain, true);
});

test("missing benchmark, unavailable market, unsupported fees and missing starting quotes never fall back", () => {
  for (const patch of [{ dataset: "sp500" }, { curveFactor: "momentum20" }, { fee: "100" }, { pool: "csi300" }, { period: "unseen" }]) assert.throws(() => m.selectCurves(doc, { ...defaults, ...patch }));
  const copy = structuredClone(doc);
  delete copy.datasets[0].streams[`${defaults.pool}__pool__fee${defaults.fee}`];
  assert.throws(() => m.selectCurves(copy, defaults), /共同池基准/);
  const noAnchor = structuredClone(doc);
  noAnchor.datasets[0].streams[`${defaults.pool}__${defaults.curveFactor}__G1__fee${defaults.fee}`].points[0][1] = null;
  assert.throws(() => m.selectCurves(noAnchor, defaults), /起始报价/);
});

test("daily risk metrics are read from source rather than rebuilt from monthly chart points", () => {
  const copy = structuredClone(doc);
  const key = `${defaults.pool}__${defaults.curveFactor}__G5__fee${defaults.fee}`;
  copy.datasets[0].streams[key].period.all.max_drawdown = -.987654;
  const selected = m.selectCurves(copy, defaults);
  assert.equal(m.metricNumber(selected.series[4].metrics, "max_drawdown"), -.987654);
  assert.equal(m.percent(null), "未提供");
  assert.equal(m.percentagePoints(.001), "+0.10个百分点");
});

test("SPA responses and summary fingerprint mismatches are rejected", async () => {
  await assert.rejects(m.loadCurveLibrary(undefined, async () => new Response("<html>SPA</html>", { headers: { "content-type": "text/html" } })), /不是研究JSON/);
  await assert.rejects(m.loadCurveLibrary(undefined, async url => {
    if (String(url).endsWith("legacy-summary.json")) return new Response("{}", { headers: { "content-type": "application/json" } });
    return fetcher(url);
  }), /指纹/);
});

test("environment retrieval failure keeps verified fund lines and disables just environment selection", async () => {
  const copy = await m.loadCurveLibrary(undefined, async url => String(url).endsWith("legacy-regimes.json") ? new Response("missing", { status: 404, headers: { "content-type": "application/json" } }) : fetcher(url));
  const current = m.selectCurves(copy, m.defaultSelection(copy, new URLSearchParams({dataset: dataset.id})));
  assert.equal(current.series.length, 6);
  assert.ok(current.dataset.regimes.some(g => !g.available && /404/.test(g.unavailableReason)));
});

test("extension uses its own 119-month calendar, all 204 streams and optional residual/risk opponents", async () => {
  const extension = doc.datasets.find(d => d.id === "fixed2014_300_extension");
  assert.ok(extension);
  const raw = JSON.parse(await readFile(new URL("./research/factor-curve-library-20261022/new-summary.json", root.href + "/"), "utf8"));
  assert.deepEqual(extension.streams, raw.streams);
  assert.equal(Object.keys(extension.streams).length, 204);
  assert.equal(m.defaultSelection(doc, new URLSearchParams()).dataset, extension.id);
  assert.equal(m.defaultSelection(doc, new URLSearchParams("curveFactor=high52&pool=green_only")).dataset, dataset.id);
  assert.equal(m.defaultSelection(doc, new URLSearchParams("curveFactor=lowvol")).dataset, dataset.id);
  let count = 0;
  for (const factor of extension.factors.filter(f => f.available)) for (const pool of extension.pools) for (const fee of extension.fees_bps) for (const period of Object.keys(extension.periods)) {
    const selection = m.defaultSelection(doc, new URLSearchParams({dataset: extension.id, curveFactor: factor.id, pool: pool.id, fee: String(fee), period}));
    const selected = m.selectCurves(doc, selection);
    assert.equal(selected.series.length, 6);
    for (const series of selected.series) {
      const key = series.id === "pool" ? `${pool.id}__pool__fee${fee}` : `${pool.id}__${factor.id}__${series.id}__fee${fee}`;
      assert.deepEqual(series.metrics, raw.streams[key].period[period]);
      assert.equal(series.points[0].value, 0);
    }
    if (period === "all") assert.equal(selected.series[0].points.length, 120);
    count++;
  }
  assert.equal(count, 160);
  for (const [factor, opponent] of [["residual", "scaled_momentum"], ["downside", "lowvol"]]) {
    const selection = m.defaultSelection(doc, new URLSearchParams({dataset: extension.id, curveFactor: factor}));
    const row = m.comparisonRows(extension, selection).find(r => r.key === opponent);
    assert.ok(row);
    assert.deepEqual(row.item, raw.increments[`${selection.pool}__${factor}__all__vs_${opponent}`]);
  }
  assert.equal(extension.regimeStatistics.all_qualified__momentum20__G5__fee25.all.strong.months, 67);
  assert.equal(extension.regimeStatistics.all_qualified__momentum20__G5__fee25.all.weak.months, 52);
});

test("optional diagnostics preserve precomputed means, nulls and partial annual coverage without rebuilding returns", () => {
  const extension = structuredClone(doc.datasets.find(d => d.id === "fixed2014_300_extension"));
  const choice = m.defaultSelection(doc, new URLSearchParams({dataset: extension.id, curveFactor: "momentum20"}));
  const row = (month, excessReturn) => ({month, return:.01, benchmarkReturn:.02, excessReturn, cashEnd:.2, unknownEnd:null, unknownMax:.3, turnover:1.5, fees:12});
  const key = "all_qualified__momentum20__G5__fee25";
  const raw = {schemaVersion:1,datasetId:extension.id,sourceSummarySha256:"fixed-test-hash",kind:"account_diagnostics_not_predictive_ic",description:"synthetic contract check only",units:{return:"fraction"},groupMeans:{all_qualified__momentum20__fee25:{all:{G1:.02,G2:.03,G3:null,G4:.01,G5:-.01}}},series:{[key]:{monthly:[row("2016-02",null),row("2016-03",-.01),row("2017-01",.03)],annual:[{year:2016,months:2,completeYear:false,return:.021,benchmarkReturn:.04,difference:-.019},{year:2017,months:1,completeYear:false,return:.01,benchmarkReturn:.02,difference:-.01}]}},capabilities:[{id:"rank_ic",status:"unavailable",reason:"No individual prediction outcomes"}]};
  extension.diagnostics = m.parseDiagnostics(raw,extension.id,"fixed-test-hash");
  const view = m.diagnosticView(extension,choice);
  assert.deepEqual(view.groups.map(g=>g.id),["G1","G2","G3","G4","G5"]);
  assert.equal(view.groups[2].mean,null);
  assert.equal(view.monthly[0].excessReturn,null);
  assert.equal(view.annual[0].return,.021);
  assert.equal(view.annual[0].completeYear,false);
  extension.periods.partial=["2016-03","2016-03"];
  extension.diagnostics.groupMeans.all_qualified__momentum20__fee25.partial={G1:null,G2:null,G3:null,G4:null,G5:null};
  const partial=m.diagnosticView(extension,{...choice,period:"partial"});
  assert.equal(partial.monthly.length,1);
  assert.equal(partial.annual.length,0);
  assert.equal(view.data.capabilities[0].status,"unavailable");
  assert.throws(()=>m.parseDiagnostics(raw,"another-dataset","fixed-test-hash"),/未绑定/);
  assert.throws(()=>m.parseDiagnostics(raw,extension.id,"changed-hash"),/未绑定/);
});

test("both published diagnostics bind all 224 period combinations to the right pool and cost", async () => {
  let combinations = 0;
  for (const dataset of doc.datasets.filter(d => d.available)) {
    assert.ok(dataset.diagnostics, dataset.diagnosticsError);
    const entry = rawCatalog.datasets.find(d => d.id === dataset.id);
    const raw = JSON.parse(await readFile(new URL(`.${entry.diagnostics.dataUrl}`, root.href + "/"), "utf8"));
    for (const f of dataset.factors.filter(f => f.available)) for (const pool of dataset.pools) for (const fee of dataset.fees_bps) for (const period of Object.keys(dataset.periods)) {
      const selection = m.defaultSelection(doc, new URLSearchParams({dataset:dataset.id,curveFactor:f.id,pool:pool.id,fee:String(fee),period}));
      const view = m.diagnosticView(dataset,selection);
      assert.ok(view);
      const groupKey = `${pool.id}__${f.id}__fee${fee}`;
      assert.deepEqual(view.groups.map(g=>g.mean),["G1","G2","G3","G4","G5"].map(g=>raw.groupMeans[groupKey][period][g]));
      const key = `${pool.id}__${f.id}__G5__fee${fee}`;
      const [start,end] = dataset.periods[period];
      assert.deepEqual(view.monthly,raw.series[key].monthly.filter(m=>m.month>=start&&m.month<=end));
      assert.deepEqual(m.diagnosticView(dataset,{...selection,regime:"weak"}).monthly,view.monthly);
      for(const row of view.annual) assert.deepEqual(row,raw.series[key].annual.find(y=>y.year===row.year));
      combinations++;
    }
  }
  assert.equal(combinations,224);
  const extension=doc.datasets.find(d=>d.id==="fixed2014_300_extension");
  const v=m.diagnosticView(extension,m.defaultSelection(doc,new URLSearchParams({dataset:extension.id,curveFactor:"momentum20"})));
  assert.equal(v.annual[0].months,11);
  assert.equal(v.annual[0].completeYear,false);
});

const assessmentFixture = () => ({schemaVersion:1,kind:"factor_predictive_and_account_metrics",datasetId:dataset.id,sourceSummarySha256:rawCatalog.datasets[0].summarySha256,
rankIC:[{factorId:"cool",poolId:"all",periodId:"all",range:dataset.periods.all,horizon:"未来20交易日",sourceManifestSha256:"a".repeat(64),labelDefinition:"合成测试标签",scoreDirection:"原方向",nPeriods:2,minAssets:3,medianAssets:3,coverage:.75,mean:.1,uncertainty:{lower:-.2,upper:.3,method:"合成范围"},points:[["2015-02-01",.2,3,4],["2015-03-01",null,0,4],["2015-04-01",0,3,4]],limitations:"全部合成测试"}],
sharpe:[{streamId:"all__cool__G5__fee25",periodId:"all",range:dataset.periods.all,value:0,frequency:"daily",observations:100,annualization:252,riskFree:{kind:"zero_assumption",description:"测试零参考",source:"",sourceDate:""},feeBps:25,feesDeducted:true,method:"测试定义",limitations:"合成测试"}]});
test("optional assessment preserves zero and null without borrowing a period, pool or fee",()=>{
 const f=assessmentFixture();const d={...dataset,assessment:m.parseAssessment(f,dataset.id,f.sourceSummarySha256)};const s={dataset:dataset.id,curveFactor:"cool",pool:"all",fee:"25",period:"all",regime:"all"};
 assert.equal(m.assessmentView(d,s).rankIC[0].points[1][1],null);assert.equal(m.assessmentView(d,s).sharpe[0].value,0);
 assert.equal(m.assessmentView(d,{...s,fee:"0"}).sharpe.length,0);assert.equal(m.assessmentView(d,{...s,pool:"green_only"}).rankIC.length,0);assert.equal(m.assessmentView(d,{...s,period:"early"}).rankIC.length,0);assert.equal(m.assessmentView({...d,assessment:undefined},s).sharpe.length,0);
});
test("assessment rejects false provenance, invalid coverage, repeated dates and mismatched fees",()=>{
 const changes=[f=>f.datasetId="other",f=>f.sourceSummarySha256="wrong",f=>f.rankIC[0].sourceManifestSha256="",f=>f.rankIC[0].nPeriods=3,f=>f.rankIC[0].coverage=1.2,f=>f.rankIC[0].minAssets=2,f=>f.rankIC[0].medianAssets=4,f=>f.rankIC[0].points[1][0]=f.rankIC[0].points[0][0],f=>f.rankIC[0].points[0][1]=2,f=>f.rankIC[0].points[0][2]=5,f=>f.rankIC.push(f.rankIC[0]),f=>f.sharpe[0].feeBps=0,f=>f.sharpe[0].riskFree.kind="sourced",f=>delete f.sharpe[0].frequency];
 for(const change of changes){const f=assessmentFixture();const h=f.sourceSummarySha256;change(f);assert.throws(()=>m.parseAssessment(f,dataset.id,h));}
});

test("formation dates stay in their own months while evaluation range binds the account selector",()=>{
 const f=assessmentFixture();const r=f.rankIC[0];r.range=["2014-12","2025-11"];r.evaluationRange=dataset.periods.all;r.points[0][0]="2014-12-31";
 const a=m.parseAssessment(f,dataset.id,f.sourceSummarySha256);const d={...dataset,assessment:a};const s={curveFactor:"cool",pool:"all",fee:"25",period:"all"};
 assert.equal(m.assessmentView(d,s).rankIC[0].points[0][0],"2014-12-31");r.evaluationRange=["2016-01","2025-12"];assert.equal(m.assessmentView(d,s).rankIC.length,0);
});

test("bad optional assessment preserves existing verified curves and explains the failure",async()=>{
 const mock=async url=>{
  if(url===m.CURVE_DATA_URL){const c=structuredClone(rawCatalog);c.datasets[0].assessment={status:"available",dataUrl:"/research/test-assessment.json",sha256:"a".repeat(64)};return new Response(JSON.stringify(c),{headers:{"content-type":"application/json"}});}
  if(url==="/research/test-assessment.json")return new Response("<html>fallback</html>",{headers:{"content-type":"text/html"}});
  return fetcher(url);
 };
 const loaded=await m.loadCurveLibrary(undefined,mock);const d=loaded.datasets.find(x=>x.id===dataset.id);
 assert.equal(d.assessment,undefined);assert.ok(d.assessmentError);assert.equal(Object.keys(d.streams).length,Object.keys(dataset.streams).length);
});

test("published extension Sharpe records stay bound to all 160 factor, pool, fee and period choices",async()=>{
 const data=await m.loadCurveLibrary(undefined,fetcher);const d=data.datasets.find(x=>x.id==="fixed2014_300_extension");assert.ok(d.assessment,d.assessmentError);
 assert.equal(d.assessment.sharpe.length,816);assert.equal(d.assessment.rankIC.length,80);let checked=0;
 for(const factor of d.factors.filter(x=>x.available))for(const pool of d.pools)for(const fee of d.fees_bps)for(const period of Object.keys(d.periods)){
  const s={dataset:d.id,curveFactor:factor.id,pool:pool.id,fee:String(fee),period,regime:"all"};const view=m.assessmentView(d,s);assert.equal(view.rankIC.length,1);assert.equal(view.sharpe.length,2);assert.ok(view.sharpe[0].streamId.includes("__G5__"));assert.ok(view.sharpe[1].streamId.includes("__pool__"));
  for(const r of view.sharpe){assert.equal(r.frequency,"monthly");assert.equal(r.riskFree.kind,"zero_assumption");assert.equal(r.feeBps,fee);assert.deepEqual(r.range,d.periods[period]);assert.ok(r.method.includes("√12"));}checked++;
 }assert.equal(checked,160);
});

test("published legacy RankIC retains formation dates, exact coverage and all 64 account selections",async()=>{
 const raw=JSON.parse(await readFile(new URL('./research/momentum-three-universe-20261022/legacy-assessment.json',root.href+'/'),'utf8'));
 const a=m.parseAssessment(raw,dataset.id,rawCatalog.datasets[0].summarySha256);assert.equal(a.rankIC.length,32);assert.equal(a.sharpe.length,336);const d={...dataset,assessment:a};let checked=0;
 for(const factor of d.factors.filter(x=>x.available))for(const pool of d.pools)for(const fee of d.fees_bps)for(const period of Object.keys(d.periods)){
  const view=m.assessmentView(d,{curveFactor:factor.id,pool:pool.id,fee:String(fee),period});assert.equal(view.rankIC.length,1);assert.equal(view.sharpe.length,2);assert.ok(view.sharpe[0].streamId.includes("__G5__"));assert.ok(view.sharpe[1].streamId.includes("__pool__"));
  const r=view.rankIC[0];assert.deepEqual(r.evaluationRange,d.periods[period]);assert.equal(r.nPeriods,r.points.filter(p=>p[1]!==null).length);assert.ok(r.points[0][0].slice(0,7)<r.evaluationRange[0]);checked++;
 }assert.equal(checked,64);
 const r=a.rankIC.find(x=>x.factorId==='momentum'&&x.poolId==='all_qualified'&&x.periodId==='all');assert.equal(r.points[0][0],'2014-12-31');assert.equal(r.minAssets,224);assert.ok(Math.abs(r.mean-(-.014950830922937412))<1e-12);
});

test("universe candidate status is display-only and legacy labels remain optional",async()=>{
 const current=await m.loadCurveLibrary(undefined,fetcher);const unavailable=current.datasets.filter(d=>!d.available);assert.equal(unavailable.length,4);
 for(const d of unavailable){const raw=rawCatalog.unavailableUniverses.find(u=>u.id===d.id);assert.equal(d.statusLabel,raw.statusLabel);assert.equal(d.unavailableReason,raw.reason);assert.equal(d.available,false);assert.equal(Object.keys(d.streams).length,0);}
 const legacyFetch=async url=>{if(url===m.CURVE_DATA_URL){const c=structuredClone(rawCatalog);for(const u of c.unavailableUniverses)delete u.statusLabel;return new Response(JSON.stringify(c),{headers:{'content-type':'application/json'}});}return fetcher(url);};
 const legacy=await m.loadCurveLibrary(undefined,legacyFetch);assert.ok(legacy.datasets.filter(d=>!d.available).every(d=>d.statusLabel===undefined&&d.unavailableReason));
});

const returnFixture=()=>{
 const point=(date,value,unknown=0,unknownMax=0)=>({date,value,unknown,unknownMax,cash:0,drawdown:-7});
 return [{id:'G5',label:'G5',color:'green',metrics:{return:.2},points:[point('2020-01-31',0),point('2020-02-29',12),point('2020-03-31',20),point('2020-04-30',-10)]},{id:'pool',label:'共同池基准',color:'black',metrics:{return:.15},points:[point('2020-01-31',0),point('2020-02-29',10),point('2020-03-31',15),point('2020-04-30',-5)]}];
};
test('relative cumulative returns are percentage-point differences, default on, without rebuilding risk',()=>{
 assert.equal(m.defaultReturnMode(new URLSearchParams()),'excess');assert.equal(m.defaultReturnMode(new URLSearchParams('returnView=absolute')),'absolute');assert.equal(m.defaultReturnMode(new URLSearchParams('returnView=bad')),'excess');
 const raw=returnFixture(),before=structuredClone(raw),view=m.returnDisplay(raw,'excess');assert.deepEqual(view.series[0].points.map(p=>p.value),[0,2,5,-5]);assert.deepEqual(view.series[1].points.map(p=>p.value),[0,0,0,0]);
 assert.equal(view.series[0].points[2].absoluteValue,20);assert.equal(view.series[0].points[2].benchmarkValue,15);assert.equal(view.series[0].points[2].drawdown,-7);assert.deepEqual(raw,before);
 const absolute=m.returnDisplay(raw,'absolute');assert.deepEqual(absolute.series[0].points.map(p=>p.value),[0,12,20,-10]);assert.equal(absolute.series[0].points[2].excessValue,5);
});
test('relative chart never fills missing dates or prices, including the benchmark zero line',()=>{
 const raw=returnFixture();raw[1].points.splice(1,1);raw[0].points.splice(1,1);raw[1].points[1].value=null;
 const view=m.returnDisplay(raw,'excess');assert.equal(view.dates.includes('2020-02-29'),false);assert.ok(m.priceSegments(view.series[0].points,true).every(s=>s.values[0]===null));assert.equal(view.series[0].points.find(p=>p.date==='2020-03-31').value,null);assert.equal(view.series[1].points.find(p=>p.date==='2020-03-31').value,null);
 const gap=returnFixture();gap.forEach(s=>s.points.splice(1,1));const gapPoints=m.returnDisplay(gap,'excess').series[0].points;assert.ok(m.priceSegments(gapPoints,true).every(s=>s.values[0]===null));assert.ok(m.priceSegments(gapPoints).some(s=>s.values[0]!==null));
 const different=returnFixture();different[1].points.splice(1,1);const missing=m.returnDisplay(different,'excess');const p=missing.series[0].points.find(p=>p.date==='2020-02-29');assert.equal(p.value,null);assert.equal(p.absoluteValue,12);assert.equal(p.benchmarkValue,null);
 const missingGroup=returnFixture();missingGroup[0].points.splice(1,1);const g=m.returnDisplay(missingGroup,'excess').series[0].points[1];assert.equal(g.absoluteValue,null);assert.equal(g.drawdown,null);
});
test('different normalization dates reject excess instead of silently selecting a later start',()=>{
 const raw=returnFixture();raw[1].points[0].date='2020-01-30';assert.throws(()=>m.returnDisplay(raw,'excess'),/相同起始日/);assert.doesNotThrow(()=>m.returnDisplay(raw,'absolute'));
 assert.throws(()=>m.returnDisplay(raw.filter(s=>s.id!=='pool'),'excess'),/同池基准/);
});
test('benchmark uncertainty and unknown normalization anchors propagate without altering source numbers',()=>{
 for(const which of [0,1])for(const field of ['unknown','unknownMax']){
  const raw=returnFixture();raw[which].points[0][field]=null;const view=m.returnDisplay(raw,'excess');assert.ok(view.series[0].points.every(p=>p.comparisonUncertain));
 }
 for(const which of [0,1]){const raw=returnFixture();raw[which].points[0].unknown=3;const view=m.returnDisplay(raw,'excess');assert.ok(view.series[0].points.every(p=>p.comparisonUncertain));}
 const raw=returnFixture();raw[1].points[1].unknownMax=4;const view=m.returnDisplay(raw,'excess'),g=view.series[0];assert.equal(g.points[1].unknownMax,0);assert.equal(g.points[1].benchmarkUnknownMax,4);assert.equal(g.points[1].comparisonUncertain,true);assert.equal(g.points[3].comparisonUncertain,false);
 const segments=m.priceSegments(g.points.map(p=>({...p,unknownMax:p.comparisonUncertain?null:p.unknownMax})));assert.deepEqual(segments.map(s=>s.uncertain),[true,false]);
});
test('all 224 saved selections reproduce raw NAV differences and preserve original account drawdowns',()=>{
 let combinations=0,points=0;
 for(const d of doc.datasets.filter(d=>d.available))for(const f of d.factors.filter(f=>f.available))for(const pool of d.pools)for(const fee of d.fees_bps)for(const period of Object.keys(d.periods)){
  const selected=m.selectCurves(doc,{dataset:d.id,curveFactor:f.id,pool:pool.id,fee:String(fee),period,regime:'all'});const view=m.returnDisplay(selected.series,'excess');const b=d.streams[`${pool.id}__pool__fee${fee}`].points;const anchor=b.filter(p=>p[0].slice(0,7)<d.periods[period][0]).at(-1);
  for(const group of view.series){const key=group.id==='pool'?`${pool.id}__pool__fee${fee}`:`${pool.id}__${f.id}__${group.id}__fee${fee}`;const original=d.streams[key].points;const g0=original.filter(p=>p[0].slice(0,7)<d.periods[period][0]).at(-1);assert.equal(g0[0],anchor[0]);
   for(const p of group.points){const g=original.find(q=>q[0]===p.date),baseline=b.find(q=>q[0]===p.date);const expected=g?.[1]===null||baseline?.[1]===null||!g||!baseline?null:((g[1]/g0[1]-1)-(baseline[1]/anchor[1]-1))*100;
    if(expected===null)assert.equal(p.value,null);else assert.ok(Math.abs(p.value-expected)<1e-10);assert.equal(p.drawdown,selected.series.find(s=>s.id===group.id).points.find(q=>q.date===p.date)?.drawdown??null);points++;
   }
  }combinations++;
 }assert.equal(combinations,224);assert.ok(points>50000);
});

test('versioned eighty-record RankIC delivery preserves frozen baseline and all existing Sharpe fields',async()=>{
 const loaded=await m.loadCurveLibrary(undefined,fetcher);const d=loaded.datasets.find(x=>x.id==='fixed2014_300_extension');assert.ok(d.assessment,d.assessmentError);const current=d.assessment;
 const frozen=JSON.parse(await readFile(new URL('./research/momentum-three-universe-20261022/new-assessment.json',root.href+'/'),'utf8'));assert.equal(frozen.rankIC.length,0);assert.equal(m.parseAssessment(frozen,d.id,rawCatalog.datasets.find(x=>x.id===d.id).summarySha256).rankIC.length,0);
 assert.deepEqual(Object.fromEntries(Object.entries(current).filter(([key])=>key!=='rankIC')),Object.fromEntries(Object.entries(frozen).filter(([key])=>key!=='rankIC')));assert.equal(current.rankIC.length,80);assert.equal(current.rankIC.reduce((n,r)=>n+r.points.length,0),4760);
 const p=current.rankIC.find(r=>r.factorId==='ppo'&&r.poolId==='green_only'&&r.periodId==='all');assert.ok(Math.abs(p.mean-(-.08326208264069893))<1e-12);assert.equal(p.nPeriods,108);assert.equal(p.minAssets,30);assert.equal(p.medianAssets,88);assert.deepEqual(p.evaluationRange,['2016-02','2025-12']);
 const low=current.rankIC.find(r=>r.factorId==='lowvol'&&r.poolId==='green_only'&&r.periodId==='all');assert.ok(Math.abs(low.mean-.133552134006211)<1e-12);
});
