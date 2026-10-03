"""Execute only remaining already frozen variants; retain all failed folders."""
from pathlib import Path
import json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'));plan=json.loads((HERE/'trial-plan.json').read_text());records=[]
for item in plan['planned_experiments']:
 if item['status']=='computed':continue
 name=item['candidate'];mode=item['mode'];frozen=HERE/f'freeze-v3-{name}-{mode}'
 base=HERE/f'run-{name}-{mode}';out=HERE/f'run-repaired-{name}-{mode}' if base.exists() else base
 if out.exists():raise RuntimeError('refuse existing outputs '+str(out))
 cmd=['python3','scripts/run_factor_lab.py','--workflow-contract',str(frozen/'contract.json'),'--out',str(out)]
 print(f'execute {name} {mode}',flush=True);start=time.monotonic();rr=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
 records.append({'phase':'execute','candidate':name,'mode':mode,'command':cmd,'exit_code':rr.returncode,'seconds':time.monotonic()-start,'stdout':rr.stdout,'stderr':rr.stderr})
 (HERE/'remaining-execution-log.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 if rr.returncode:print(rr.stderr or rr.stdout,flush=True);raise SystemExit(rr.returncode)
 item['status']='computed';item['run_path']=str(out.relative_to(ROOT));item['actual_fits']=json.loads((out/'result.json').read_text())['execution']['fits']
 plan['real_fits_used']=sum(x.get('actual_fits',0) for x in plan['planned_experiments']);assert plan['real_fits_used']<=24
 (HERE/'trial-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n');print(f'completed {name} {mode}',flush=True)
print('all six comparisons computed',flush=True)
