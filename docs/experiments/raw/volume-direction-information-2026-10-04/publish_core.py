"""Publish accepted main comparisons through existing CLI, reuse all predictions."""
from pathlib import Path
import json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'));records=[]
for n in ['main','solo']:
 old=HERE/f'run-{n}';out=HERE/f'accepted-{n}'
 if out.exists():raise RuntimeError('refuse existing accepted output')
 cmd=['python3','scripts/run_factor_lab.py','--workflow-contract',str(old/'contract.json'),'--out',str(out),'--reuse-predictions',str(old),'--register-report']
 print('register '+n,flush=True);start=time.monotonic();r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
 records.append({'candidate':n,'command':cmd,'seconds':time.monotonic()-start,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 (HERE/'publication-log.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 if r.returncode: print(r.stderr or r.stdout,flush=True);raise SystemExit(r.returncode)
 result=json.loads((out/'result.json').read_text());assert result['execution']['fits']==0
 print('registered '+n+'; zero new fits',flush=True)
