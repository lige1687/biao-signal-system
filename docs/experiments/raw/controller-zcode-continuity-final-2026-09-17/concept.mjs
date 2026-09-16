import {detectUnsupportedExitRequest as f} from '/tmp/zcode-controller-agentUx.mjs';
import {writeFileSync} from 'node:fs';
const text='解释一下ATR止损回测是什么意思，不要求你执行';
const result={text,actual:f(text),expected:null,passed:f(text)===null};
writeFileSync(new URL('concept.json',import.meta.url),JSON.stringify(result,null,2));console.log(result);
