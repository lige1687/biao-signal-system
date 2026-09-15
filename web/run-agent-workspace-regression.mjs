import assert from 'node:assert/strict';
import { readAgentEvents, shouldFollowOutput, replyPreview } from '/tmp/biao-agent-workspace-logic.mjs';

const bytes = new TextEncoder().encode('event: token\r\ndata: {"t":"中文"}\r\n\r\nevent: done\ndata: {"session_id":"s1"}\n\n');
const chunks = new ReadableStream({ start(c) { for (const byte of bytes) c.enqueue(new Uint8Array([byte])); c.close(); } });
const events = [];
for await (const e of readAgentEvents(chunks)) events.push(e);
assert.deepEqual(events, [{event:'token',data:{t:'中文'}},{event:'done',data:{session_id:'s1'}}]);
assert.equal(chunks.locked, false, 'reader releases its lock');
const lastFrame = new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('event: done\ndata: {"grounded":true}'));c.close();}});
const end = []; for await (const e of readAgentEvents(lastFrame)) end.push(e);
assert.equal(end[0].event,'done','last frame without trailing newline is retained');
const malformed = new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('event: token\ndata: {bad}\n\n'));c.close();}});
await assert.rejects(async()=>{for await(const e of readAgentEvents(malformed)) void e;});
assert.equal(shouldFollowOutput(200,400,1200),false,'reading older content must not jump to bottom');
assert.equal(shouldFollowOutput(775,400,1200),true);
assert.deepEqual(replyPreview('首段结论。\n\n## 依据\n- 条件一'),{lead:'首段结论。',rest:'## 依据\n- 条件一'});
assert.deepEqual(replyPreview('## 条件\n- 第一条'),{lead:'',rest:'## 条件\n- 第一条'},'do not turn a heading into a fabricated summary');
console.log('Agent workspace: stream, reader cleanup, scrolling and exact-text preview checks passed.');
