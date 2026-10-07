"""Deterministic accounting test; synthetic elapsed clocks, no actual waiting."""
from pathlib import Path
import sys, json, hashlib, shutil
from unittest.mock import patch
OUT=Path(__file__).resolve().parent
source=OUT/'sandbox'; root=OUT/'budget-sandbox'
if root.exists():raise SystemExit('refuse overwrite')
root.mkdir()
for name in ['src','scripts','configs']:
    shutil.copytree(source/name,root/name)
sys.path.insert(0,str(root/'src'))
from lei_signal.research import native_risk_d_mae_workflow as n
from lei_signal.research import workflow as w
(root/'inputs').mkdir()
for name in ['x.json','y.json']:
    (root/'inputs'/name).write_bytes((source/'inputs'/name).read_bytes())
c=json.loads((source/'inputs/draft-x.json').read_text())
c['budget']['execution_seconds']=1.5
c['history']['family']='native-d-mae20-synthetic-budget-independent'
def put(path,v):path.write_text(json.dumps(v,indent=2)+'\n')
put(root/'inputs/x-draft.json',c)
n.freeze_workflow(root/'inputs/x-draft.json',root/'frozen-x',root)
# Four elapsed readings per successful run: start, admission, completion, finish.
with patch.object(n.time,'monotonic',side_effect=[0.0,.1,.9,.9]):
    n.execute_workflow(root/'frozen-x/contract.json',root/'x',root)
c['stage']='y';c['data'].update(y_path='inputs/y.json',y_sha256=hashlib.sha256((root/'inputs/y.json').read_bytes()).hexdigest())
c['x_receipt']={'path':'x','sha256':hashlib.sha256((root/'x/receipt.json').read_bytes()).hexdigest()}
put(root/'inputs/y-draft.json',c)
n.freeze_workflow(root/'inputs/y-draft.json',root/'frozen-y',root)
error=None
try:
    with patch.object(n.time,'monotonic',side_effect=[0.0,.1,.9,.9]):
        n.execute_workflow(root/'frozen-y/contract.json',root/'y',root)
except Exception as exc:error=type(exc).__name__+': '+str(exc)
events=[json.loads(s) for s in w.family_ledger(root,c['history']['family']).read_text().splitlines()]
result={'budget_seconds':1.5,'synthetic_elapsed_seconds_per_stage':.9,'total_recorded_seconds':sum(e.get('seconds',0) for e in events if e['event']=='finish'),'Y_completed':(root/'y/state.json').is_file(),'error':error,'real_execution_seconds_not_claimed':True,'expected':'cumulative budget should pause before publishing Y','passed':not (root/'y/state.json').is_file()}
put(OUT/'budget-check.json',result)
print(json.dumps(result))
