// Build web/src/utils/agentUx.ts with esbuild to /tmp/controller-cfix-agentUx.mjs first.
import {detectUnsupportedExitRequest,atrDiscussionDraft} from '/tmp/controller-cfix-agentUx.mjs';
const draft=atrDiscussionDraft('515880.SS');
console.log(JSON.stringify({draft,intercepted_again:detectUnsupportedExitRequest(draft),concept_question:detectUnsupportedExitRequest('ATR止损是什么意思？我不要求回测')},null,2));
