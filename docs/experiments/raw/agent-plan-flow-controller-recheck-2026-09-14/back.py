import sys,json,tempfile,hashlib
from pathlib import Path
DEV=Path('/Users/yongbiaoli/lei-agent-ux-20260913');sys.path.insert(0,str(DEV/'src'));OUT=Path(__file__).parent
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lei_signal.api.routes import plans
from lei_signal.storage.sqlite_store import connect
from lei_signal.plans.sessions import create_session,append_message
from lei_signal.plans.store import get_plan
files=['src/lei_signal/api/routes/plans.py','web/src/components/PlanDraftCard.tsx','web/src/components/CreatePlanDialog.tsx','web/src/components/ReviewDrawer.tsx']
h=lambda:{f:hashlib.sha256((DEV/f).read_bytes()).hexdigest() for f in files}
before=h();out={}
with tempfile.TemporaryDirectory() as t:
 db=Path(t)/'db.sqlite';conn=connect(db);s=create_session(conn,'SYNTHETIC','合成');q=append_message(conn,s.session_id,'user','合成计划',True,{'discussion_v1':{'symbol':'SYNTHETIC'}})
 app=FastAPI();app.state.plans_db_path=str(db);app.include_router(plans.router)
 with TestClient(app) as client:
  b=dict(symbol='SYNTHETIC',module='A',direction='long',reason='合成',ruleset_version='2.1.0',client_request_id='same-save-request',source_session_id=s.session_id,source_question_id=q.message_id)
  first=client.post('/api/plans',json=b);assert first.status_code==201,first.text
  same=client.post('/api/plans',json=b);assert same.status_code==201 and same.json()['plan_id']==first.json()['plan_id']
  b['ruleset_version']='3.0.0'; retry=client.post('/api/plans',json=b);assert retry.status_code==409,retry.text
  out={'initial':first.status_code,'unchanged_retry':same.status_code,'changed_version_retry':retry.status_code,'detail':retry.json(),'original_version':get_plan(conn,first.json()['plan_id']).ruleset_version,'plan_count':conn.execute('select count(*) from trade_plans').fetchone()[0]}
 conn.close()
assert before==h();out['source_unchanged']=True;out['hashes']=before
(OUT/'back-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
