import {build} from '../../../../web/node_modules/esbuild/lib/main.js';
import {writeFileSync} from 'node:fs';
await build({entryPoints:['web/src/utils/agentUx.ts'],bundle:true,platform:'node',format:'esm',outfile:'/tmp/zcode-controller-agentUx.mjs'});
const {detectUnsupportedExitRequest:f}=await import('/tmp/zcode-controller-agentUx.mjs');
const cases=['请解释一下用ATR止损回测，比较收益','先聊聊，再帮我用ATR止损补测','ATR止损是什么意思？我不要求回测'];
const results=cases.map((text,i)=>({text,actual:f(text),passed:i===2?f(text)===null:f(text)!==null}));
writeFileSync(new URL('atr-results.json',import.meta.url),JSON.stringify(results,null,2));console.log(results);
