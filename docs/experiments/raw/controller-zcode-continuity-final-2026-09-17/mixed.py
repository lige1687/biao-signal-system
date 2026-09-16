import json,tempfile
from pathlib import Path
from lei_signal.api.routes.agent import _user_background
from lei_signal.plans.sessions import create_session,append_message,list_messages
from lei_signal.storage.sqlite_store import connect
out={}
with tempfile.TemporaryDirectory() as d:
 with connect(str(Path(d)/'probe.db')) as c:
  for name,texts in {'own_clear_after_friend':['我已经持有了','朋友还持有，但我已经清仓了'],'own_income_negated_spare':['我有一万闲钱','我没有闲钱，这是每月工资定投']}.items():
   sid=create_session(c,'515880.SS',name).session_id
   for text in texts:
    m=append_message(c,sid,'user',text,False,{})
    c.execute("INSERT INTO agent_messages(session_id,role,content,grounded,meta_json,created_at,question_id,message_kind) VALUES (?, 'assistant','合成回答',1,?,datetime('now'),?,'answer')",(sid,json.dumps({'resolved_symbol':'515880.SS'}),m.message_id));c.commit()
   out[name]={'inputs':texts,'background':_user_background(list_messages(c,sid,limit=20),'515880.SS')}
out['checks']={'own_clear_effective':not out['own_clear_after_friend']['background'].get('holding'),'income_not_spare':out['own_income_negated_spare']['background'].get('purpose')=='income_dca'}
Path(__file__).with_suffix('.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
