import {detectUnsupportedExitRequest as f} from '/tmp/zcode-controller-agentUx.mjs';
import {writeFileSync} from 'node:fs';
const text='先解释ATR止损，不用比较，直接帮我回测';
const result={text,actual:f(text),passed:f(text)!==null};
writeFileSync(new URL('mixed-atr.json',import.meta.url),JSON.stringify(result,null,2));console.log(result);
