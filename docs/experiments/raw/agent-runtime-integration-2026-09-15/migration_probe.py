import pathlib,subprocess,sys,json,tempfile,sqlite3
R=pathlib.Path.cwd();O=R/'docs/experiments/raw/agent-runtime-integration-2026-09-15';T=pathlib.Path(json.loads((O/'staging.json').read_text())['path'])
with tempfile.TemporaryDirectory() as td:
 db=str(pathlib.Path(td)/'old.db')
 old='''from lei_signal.storage.sqlite_store import connect
from lei_signal.copilot.chat_identity import enter_chat_request,chat_request_hash
c=connect(DB)
h=chat_request_hash(message="旧记录保留",context_kind="global",symbol=None)
enter_chat_request(c,client_request_id="migration-controller",request_hash=h,session_id=None,new_session_symbol=None,new_session_title="旧会话")
c.close()
'''
 for root,code in [(R,old),(T,'from lei_signal.storage.sqlite_store import connect\nc=connect(DB)\nc.close()\n')]:
  if root==T:
   c=sqlite3.connect(db);before=c.execute('SELECT * FROM agent_chat_requests').fetchall();cols=[x[1] for x in c.execute('PRAGMA table_info(agent_chat_requests)')];c.close()
  full='import sys\nsys.path.insert(0,'+repr(str(root/'src'))+')\nDB='+repr(db)+'\n'+code
  p=subprocess.run([sys.executable,'-c',full],capture_output=True,text=True);assert p.returncode==0,p.stderr
 c=sqlite3.connect(db);after=c.execute('SELECT '+','.join(cols)+' FROM agent_chat_requests').fetchall();newcols=[x[1] for x in c.execute('PRAGMA table_info(agent_chat_requests)')];newvals=c.execute('SELECT request_message,request_context_kind,request_symbol FROM agent_chat_requests').fetchall();c.close()
 assert before==after and newvals==[('','','')]
 print(json.dumps({'old_rows_preserved':before==after,'new_columns':sorted(set(newcols)-set(cols)),'legacy_identity_not_invented':newvals==[('','','')],'temporary_db_only':True},ensure_ascii=False,indent=2))
