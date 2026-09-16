// 三轮收口 G1 修后复跑（agent-continuity-zcode-closeout-r2-2026-09-17）。
// 与主控 raw/controller-zcode-continuity-2026-09-17/atr-probe.mjs 同逻辑，
// 但产物只写本目录（主控原始失败证据保持原样不覆盖）：
// 修后主控三例应全部通过（混合问法拦截、纯概念放行）。
import {build} from '../../../../web/node_modules/esbuild/lib/main.js';
import {writeFileSync} from 'node:fs';
await build({entryPoints:['web/src/utils/agentUx.ts'],bundle:true,platform:'node',format:'esm',outfile:'/tmp/zcode-r2-agentUx.mjs'});
const {detectUnsupportedExitRequest:f}=await import('/tmp/zcode-r2-agentUx.mjs');
const cases=['请解释一下用ATR止损回测，比较收益','先聊聊，再帮我用ATR止损补测','ATR止损是什么意思？我不要求回测'];
const results=cases.map((text,i)=>({text,actual:f(text),passed:i===2?f(text)===null:f(text)!==null}));
writeFileSync(new URL('atr-rerun-results.json',import.meta.url),JSON.stringify(results,null,2));console.log(results);
