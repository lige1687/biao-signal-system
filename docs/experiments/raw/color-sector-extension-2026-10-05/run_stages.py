import os,sys,subprocess,json,datetime,shutil
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[3]
mode=sys.argv[1];stage=sys.argv[2];records=[]
env={**os.environ,'PYTHONPATH':'src','DYLD_LIBRARY_PATH':'/opt/homebrew/lib/python3.11/site-packages/torch/lib'}
py=root/'docs/experiments/raw/color-gray-path-2026-10-04/.venv.local/bin/python'
for group in ['continuous']:
 for branch in ['ridge-forward_return','ridge-mae','lightgbm-forward_return','lightgbm-mae']:
  d=here/group/branch;inp=d/'draft.json' if mode=='freeze' else d/'freeze-02'/'contract.json';out=d/stage
  if out.exists():raise RuntimeError('Refuse overwrite '+str(out))
  free=shutil.disk_usage(root).free
  if free<40*1024*1024:raise RuntimeError('Insufficient room for bounded output and checkpoint: '+str(free))
  cmd=[str(py),'scripts/run_factor_lab.py','--workflow-draft' if mode=='freeze' else '--workflow-contract',str(inp),'--out',str(out)]
  log=d/(stage+'.log')
  with log.open('x') as f:p=subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
  record={'group':group,'branch':branch,'mode':mode,'out':str(out.relative_to(root)),'returncode':p.returncode,'time':datetime.datetime.now().astimezone().isoformat(),'command':cmd}
  if (out/'result.json').exists():record['execution']=json.loads((out/'result.json').read_text()).get('execution')
  records.append(record);(here/(stage+'-ledger.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print(group,branch,p.returncode,flush=True)
  if p.returncode:print(log.read_text()[-6000:]);sys.exit(p.returncode)
