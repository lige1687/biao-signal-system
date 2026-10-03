"""Bounded orchestration of existing shared workflow CLI; no alternative evaluator."""
from pathlib import Path
import json, os, subprocess, time
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'trial-plan.json').read_text())
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
records=[]
for phase in ['freeze','execute']:
    for item in plan['planned_experiments']:
        name=item['candidate'];mode=item['mode']; frozen=HERE/f'freeze-{mode}'
        target=frozen if phase=='freeze' else HERE/f'run-{mode}'
        if target.exists(): raise RuntimeError(f'refuse existing outputs {target}')
        cmd=['python3','scripts/run_factor_lab.py', '--workflow-draft' if phase=='freeze' else '--workflow-contract',str(ROOT/item['draft']) if phase=='freeze' else str(frozen/'contract.json'),'--out',str(target)]
        start=time.monotonic(); print(f'{phase} {name} {mode}',flush=True)
        rr=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        record={'phase':phase,'candidate':name,'mode':mode,'command':cmd,'exit_code':rr.returncode,'seconds':time.monotonic()-start,'stdout':rr.stdout,'stderr':rr.stderr}
        records.append(record)
        (HERE/'batch-execution-log.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        if rr.returncode: print(rr.stderr or rr.stdout,flush=True);raise SystemExit(rr.returncode)
        if phase=='execute':
            item['status']='computed';item['run_path']=str(target.relative_to(ROOT));item['actual_fits']=json.loads((target/'result.json').read_text())['execution']['fits']
            plan['real_fits_used']=sum(x.get('actual_fits',0) for x in plan['planned_experiments'])
            assert plan['real_fits_used']<=8
            (HERE/'trial-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        print(f'{phase} completed {name} {mode}',flush=True)
print('two experiments computed; awaiting controller numerical review, not yet published',flush=True)
