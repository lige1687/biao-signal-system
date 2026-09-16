import json,tempfile
from pathlib import Path
from lei_signal.api.routes.agent import _user_background
from lei_signal.plans.sessions import create_session,append_message,list_messages
from lei_signal.storage.sqlite_store import connect
out={}
with tempfile.TemporaryDirectory() as d:
 with connect(str(Path(d)/'probe.db')) as c:
  for name,texts in {'friend_continuation':['我已经持有了','朋友昨天操作了，已经清仓'],'friend_purpose_continuation':['朋友有一万元闲钱，每月定投'],'hypothetical_continuation':['如果以后有钱，每月定投']}.items():
   sid=create_session(c,'515880.SS',name).session_id
   for text in texts:
    m=append_message(c,sid,'user',text,False,{})
    c.execute("INSERT INTO agent_messages(session_id,role,content,grounded,meta_json,created_at,question_id,message_kind) VALUES (?, 'assistant','合成回答',1,?,datetime('now'),?,'answer')",(sid,json.dumps({'resolved_symbol':'515880.SS'}),m.message_id));c.commit()
   out[name]={'inputs':texts,'background':_user_background(list_messages(c,sid,limit=20),'515880.SS')}
out['checks']={'friend_does_not_clear_me':out['friend_continuation']['background'].get('holding') is True,'friend_purpose_not_mine':not out['friend_purpose_continuation']['background'],'hypothesis_not_fact':not out['hypothetical_continuation']['background']}
Path(__file__).with_suffix('.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
