import json, tempfile, hashlib
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lei_signal.plans import llm
from lei_signal.api.routes import agent
from lei_signal.storage.sqlite_store import connect

DEV=Path('/Users/yongbiaoli/lei-agent-ux-20260913')
files=['src/lei_signal/plans/llm.py','src/lei_signal/api/routes/agent.py','web/src/pages/AgentWorkspacePage.tsx','web/src/components/AgentConsole.tsx']
def hashes(): return {f:hashlib.sha256((DEV/f).read_bytes()).hexdigest() for f in files}
before=hashes()
class Response:
 status_code=200; encoding='utf-8'; text=''
 def __init__(self, lines): self.lines=lines
 def __enter__(self): return self
 def __exit__(self,*args): pass
 def iter_lines(self,**kwargs): yield from self.lines
cfg=llm.ArkConfig(api_key='test-only',style=llm.STYLE_ANTHROPIC)
base=['data: '+json.dumps(x) for x in [{'type':'content_block_start','content_block':{'type':'text'}},{'type':'content_block_delta','delta':{'type':'text_delta','text':'半句话'}}]]
results={}
for case,tail in [('clean_eof',[]),('provider_error',['data: '+json.dumps({'type':'error','error':{'type':'overloaded_error'}})]),('normal',['data: '+json.dumps({'type':'message_stop'})])]:
 with patch.object(llm.requests,'post',return_value=Response(base+tail)):
  pieces=list(llm.chat_discussion_stream({},[],'test',cfg))
 results[case]={'text':''.join(x for x in pieces if isinstance(x,str)),'interrupted':any(x is llm.STREAM_INTERRUPTED for x in pieces)}
def events(text):
 out=[]
 for frame in text.split('\n\n'):
  lines=frame.splitlines(); e=next((x[7:] for x in lines if x.startswith('event: ')),None); d=next((x[6:] for x in lines if x.startswith('data: ')),None)
  if e and d: out.append((e,json.loads(d)))
 return out
calls=[]
def broken(*args):
 calls.append(1)
 yield '按系统资料，先观察。'
 yield llm.STREAM_INTERRUPTED
with tempfile.TemporaryDirectory() as td:
 db=str(Path(td)/'case.db'); connect(db).close()
 app=FastAPI(); app.state.analysis_service=None; app.state.plans_db_path=db; app.state.watchlist_db_path=db; app.include_router(agent.router)
 with patch.object(llm,'load_ark_config',return_value=cfg), patch.object(llm,'chat_discussion_stream',broken), TestClient(app) as client:
  body={'context_kind':'global','message':'先观察什么','client_request_id':'controller-interrupted-1'}
  first=events(client.post('/api/agent/chat/stream',json=body).text)
  done=next(d for e,d in first if e=='done')
  replay=events(client.post('/api/agent/chat/stream',json=body).text)
  conn=connect(db)
  rows=[dict(x) for x in conn.execute("SELECT content,grounded,meta_json FROM agent_messages WHERE role='assistant'")]
  claims=[dict(x) for x in conn.execute('SELECT * FROM agent_chat_requests')]
  conn.close()
  results['history_retry']={'first_done':done,'stored_answers':rows,'claims':claims,'retry_events':replay,'model_calls':len(calls)}
results['source_before']=before; results['source_unchanged']=before==hashes()
print(json.dumps(results,ensure_ascii=False,indent=2))
