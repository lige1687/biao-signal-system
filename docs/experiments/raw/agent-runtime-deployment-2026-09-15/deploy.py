"""User authorized coordinated runtime update; never logs credentials."""
import pathlib,json,subprocess,sys,os,sqlite3,time
R=pathlib.Path.cwd();O=R/'docs/experiments/raw/agent-runtime-deployment-2026-09-15';P=R/'docs/experiments/raw/agent-runtime-integration-2026-09-15';record=[]
info=json.loads((O/'database-before.json').read_text());assert info['quick_check']=='ok' and pathlib.Path(info['backup']).is_file()
uid=os.getuid();labels=['com.lei.frontend','com.lei.backend'];plists={x:str(pathlib.Path.home()/'Library/LaunchAgents'/f'{x}.plist') for x in labels}
def run(args,timeout=35):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);record.append({'command':args,'returncode':p.returncode,'stdout':p.stdout[-1500:],'stderr':p.stderr[-1500:]});(O/'deployment-actions.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));return p
assert run([sys.executable,str(P/'file-action.py'),'--check']).returncode==0
stopped=[];applied=False
try:
 for label in labels:
  p=run(['launchctl','bootout',f'gui/{uid}/{label}']);assert p.returncode==0,p.stderr;stopped.append(label)
 assert run([sys.executable,str(P/'file-action.py'),'--apply']).returncode==0
 applied=True
 # Upgrade explicitly using the service's existing interpreter, path is from verified config.
 code='import sys;sys.path.insert(0,"src");from lei_signal.storage.sqlite_store import connect;c=connect('+repr(info['database'])+');print([x[1] for x in c.execute("PRAGMA table_info(agent_chat_requests)")]);c.close()'
 p=run(['/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3','-c',code],timeout=55)
 assert p.returncode==0,p.stderr
except Exception:
 if applied:run([sys.executable,str(P/'file-action.py'),'--rollback'])
 raise
finally:
 # Always restore launchd-managed services; do not alter their saved configurations.
 for label in reversed(stopped):
  run(['launchctl','bootstrap',f'gui/{uid}',plists[label]])
print(json.dumps({'files_applied':applied,'actions':str(O/'deployment-actions.json')}))
