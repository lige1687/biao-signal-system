// Independent controller checks. Executes actual submitted functions with local I/O substitutes.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root='/Users/yongbiaoli/lei-agent-ux-20260913';
const req=require('node:module').createRequire(root+'/web/package.json');
const ts=req('typescript');
const files=['web/src/pages/AgentWorkspacePage.tsx','web/src/components/AgentConsole.tsx','web/src/components/agent/BacktestSetupPanel.tsx','web/src/utils/agentUx.ts'];
const hashes=()=>Object.fromEntries(files.map(f=>[f,crypto.createHash('sha256').update(fs.readFileSync(root+'/'+f)).digest('hex')]));
const before=hashes(); const results=[];
function extract(file,name,env){
 const text=fs.readFileSync(root+'/'+file,'utf8');const ast=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);let found;
 function walk(n){if(ts.isVariableDeclaration(n)&&n.name.getText(ast)===name)found=n.initializer;ts.forEachChild(n,walk)}walk(ast);
 if(!found)throw Error(name+' not found');
 const js=ts.transpileModule('const subject = '+found.getText(ast)+';', {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
 return new Function(...Object.keys(env),js+';return subject;')(...Object.values(env));
}
(async()=>{
for(const file of files.slice(0,2)){
 let turns=[];const env={api:{agentChat:async()=>({session_id:'s1',question_id:71,resolved_symbol:'510300.SS',reply:'合成回答'})},sessionId:'s1',symbol:'510300.SS',crypto,
 setSessionId:()=>{},setSymbol:()=>{},setTurns:fn=>{turns=fn(turns)},generationRef:{current:1},parseBacktestModule:()=>null};
 await extract(file,'handleBacktest',env)('帮我补测一下',{resolved_symbol:'510300.SS'},1);
 results.push({id:'U1-direct-'+(file.includes('Workspace')?'workspace':'console'),expected:'Open Chinese setup, no module-code instruction',old_module_prompt:turns.some(t=>t.text?.includes('请说明要补测的模块')),turns:turns.map(t=>t.text),verdict:turns.some(t=>t.text?.includes('请说明要补测的模块'))?'FAIL':'PASS'});
}
for(const file of files.slice(0,2)){
 let turns=[],finish;const setup={symbol:'510300.SS',sessionId:'s1',questionId:71};
 const ref={current:1};const env={setupPanel:setup,panelSubmitting:false,setPanelSubmitting:()=>{},setSetupPanel:()=>{},patch:()=>{},generationRef:ref,epochRef:ref,crypto,api:{copilotBacktestRequest:()=>new Promise(r=>finish=r)},trackTask:()=>{},pollTask:()=>{},onTaskStatus:()=>{},moduleCn:x=>x,exitCn:x=>x,phaseLabelCn:x=>x,setTurns:fn=>{turns=fn(turns)}};
 const subject=extract(file,'submitSetup',env);
 const promise=file.includes('Workspace') ? subject({id:'old',setupPanel:setup},'A','a6_1_costbasis') : subject('A','a6_1_costbasis');
 ref.current=2;turns=[{who:'you',text:'新会话：518880'}];
 finish({request_id:'old-task',session_id:'s1',question_id:71,symbol:'510300.SS',method:'A',exit_variant:'a6_1_costbasis',status:'queued'});await promise;
 results.push({id:'U3-late-'+(file.includes('Workspace')?'workspace':'console'),expected:'Old task response must not append into new conversation',new_conversation_turns:turns.map(t=>t.text),verdict:turns.length===1?'PASS':'FAIL'});
}
// Actual component SSR, cached authoritative capabilities deliberately exclude the preselected A.
const esbuild=req('esbuild');const bundle=esbuild.buildSync({entryPoints:[root+'/web/src/components/agent/BacktestSetupPanel.tsx'],bundle:true,platform:'node',format:'cjs',packages:'external',write:false});
const Module=require('node:module');const cm=new Module(root+'/web/__controller_component.cjs');cm.filename=root+'/web/__controller_component.cjs';cm.paths=Module._nodeModulePaths(root+'/web');cm._compile(bundle.outputFiles[0].text,cm.filename);
const React=req('react'),{renderToStaticMarkup}=req('react-dom/server'),{QueryClient,QueryClientProvider}=req('@tanstack/react-query');
const query=new QueryClient({defaultOptions:{queries:{retry:false}}});query.setQueryData(['backtestOptions'],{modules:[{value:'B'}],exit_variants:[{value:'b3_dual'}],defaults:{exit_variant:'b3_dual'}});
const html=renderToStaticMarkup(React.createElement(QueryClientProvider,{client:query},React.createElement(cm.exports.default,{setup:{symbol:'510300.SS',sessionId:'s1',questionId:71,defaultModule:'A'},onSubmit:()=>{}})));
const button=html.match(/<button[^>]*>创建这次补测<\/button>/)?.[0];
results.push({id:'U2-invalid-preselection',expected:'Only valid visible capabilities may be submitted',button,verdict:button?.includes('disabled')?'PASS':'FAIL'});
results.push({id:'source-integrity',verdict:JSON.stringify(before)===JSON.stringify(hashes())?'PASS':'FAIL',hashes:before});
console.log(JSON.stringify(results,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
