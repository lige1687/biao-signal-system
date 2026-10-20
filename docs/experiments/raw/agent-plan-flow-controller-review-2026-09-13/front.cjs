const fs=require('fs'),vm=require('vm'),path=require('path');
const dev='/Users/yongbiaoli/lei-agent-ux-20260913';
const ts=require(dev+'/web/node_modules/typescript');
function declarations(file){const s=ts.createSourceFile(file,fs.readFileSync(dev+'/web/src/components/'+file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),o={};function visit(n){if(ts.isVariableDeclaration(n)&&ts.isIdentifier(n.name)&&n.initializer)o[n.name.text]=n.initializer.getText(s);ts.forEachChild(n,visit)}visit(s);return o;}
function run(code,ctx){return vm.runInNewContext(ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText,ctx);}
(async()=>{
const form=declarations('CreatePlanDialog.tsx');const calls=[];
const ctx={exitPlaybookReady:true,validUntil:'2099-12-31',hasTrigger:true,createHolding:{isPending:false},saveEdit:{isPending:false},rulesetVersion:null,isEdit:false,setError:()=>{},symbol:'SYNTHETIC',direction:'long',module:'A',reason:'test',playbook:{take_profit_plan_cn:'take',stop_plan_cn:'stop'},takeProfitPrice:'12',stopPrice:'8',watchSignals:[],toNum:s=>s?Number(s):null,api:{createHoldingWatch:p=>calls.push(p)},useMutation:c=>({mutate:()=>c.mutationFn()}),queryClient:{invalidateQueries:()=>{}}};
const enabled=run(form.canSubmitHolding,ctx);
ctx.createHolding=run(form.createHolding,ctx);run('('+form.submitHolding+')()',ctx);
const card=declarations('PlanDraftCard.tsx'); const payloads=[];const c={draft:{module:'A',direction:'long'},symbol:'SYNTHETIC',clientRequestId:'fixed-request',sessionId:'s',questionId:1,planId:null,setSavedLocally:()=>{},queryClient:{invalidateQueries:()=>{}},useMutation:x=>x,api:{createPlan:async p=>{payloads.push(p);throw new Error('response lost after commit')}},rulesetVersion:'2.1.0'};
c.buildPayload=run(card.buildPayload,c);const save=run(card.save,c);try{await save.mutationFn()}catch{} c.rulesetVersion='3.0.0';try{await save.mutationFn()}catch{}
const review=declarations('ReviewDrawer.tsx');let error='';const rc={api:{},queryClient:{},planId:'p',onClose:()=>{},setError:s=>{error=s},refetch:()=>{},useMutation:x=>x};const cf=run(review.confirm,rc);cf.onError({body:{detail:{code:'RULESET_VERSION_CHANGED',message:'版本已变，请复核后重建草稿'}}});
const result={holding_without_version:{enabled,requests:calls},retry_versions:payloads.map(x=>({id:x.client_request_id,version:x.ruleset_version})),version_error:error};
fs.writeFileSync(path.join(__dirname,'front-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})();
