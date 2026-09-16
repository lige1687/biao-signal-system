import json,tempfile
from pathlib import Path
from lei_signal.api.routes.agent import _user_background
from lei_signal.plans.sessions import create_session,append_message,list_messages
from lei_signal.storage.sqlite_store import connect
from lei_signal.copilot.resolve import detect_fact_correction
out={}
with tempfile.TemporaryDirectory() as d:
 with connect(str(Path(d)/'probe.db')) as c:
  for name,texts in {'negated_clear':['我已经持有了','我没有清仓'],'friend_clear':['我已经持有了','朋友清仓了'],'friend_purpose':['朋友有一万元闲钱']}.items():
   sid=create_session(c,'515880.SS',name).session_id
   for text in texts:
    m=append_message(c,sid,'user',text,False,{})
    c.execute("INSERT INTO agent_messages(session_id,role,content,grounded,meta_json,created_at,question_id,message_kind) VALUES (?, 'assistant','合成回答',1,?,datetime('now'),?,'answer')",(sid,json.dumps({'resolved_symbol':'515880.SS'}),m.message_id));c.commit()
   out[name]={'inputs':texts,'background':_user_background(list_messages(c,sid,limit=20),'515880.SS')}
out['checks']={'negated_clear_preserves':out['negated_clear']['background'].get('holding') is True,'friend_clear_preserves':out['friend_clear']['background'].get('holding') is True,'friend_purpose_not_mine':not out['friend_purpose']['background']}
Path(__file__).with_suffix('.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
