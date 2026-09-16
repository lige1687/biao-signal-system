// 三轮收口（r3 复核）修后复跑：与主控 mixed.mjs 同逻辑，但从**当前源码**
// 重新打包，产物只写本目录（主控原件不动）。
// 修后：「先解释ATR止损，不用比较，直接帮我回测」必须拦截（非 null）。
import {build} from '../../../../web/node_modules/esbuild/lib/main.js';
import {writeFileSync} from 'node:fs';
await build({entryPoints:['web/src/utils/agentUx.ts'],bundle:true,platform:'node',format:'esm',outfile:'/tmp/zcode-r3-agentUx.mjs'});
const {detectUnsupportedExitRequest:f}=await import('/tmp/zcode-r3-agentUx.mjs');
const cases=[
  {text:'先解释ATR止损，不用比较，直接帮我回测',expect:'intercept'},
  {text:'不用比较，也不回测，ATR止损是什么意思',expect:'pass'},
  {text:'请解释一下用ATR止损回测，比较收益',expect:'intercept'},
  {text:'ATR止损是什么意思？我不要求回测',expect:'pass'},
];
const results=cases.map(({text,expect})=>{
  const actual=f(text);
  const passed=expect==='intercept'?actual!==null:actual===null;
  return {text,expect,actual,passed};
});
writeFileSync(new URL('atr-mixed-rerun-results.json',import.meta.url),JSON.stringify(results,null,2));
console.log(results);
