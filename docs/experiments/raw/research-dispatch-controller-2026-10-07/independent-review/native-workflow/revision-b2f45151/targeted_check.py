"""Targeted independent R1/R2 recheck against exact b2f45151 source bytes."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent
AUTHOR=Path('/Users/yongbiaoli/Desktop/lei-signal-lab/.codex/worktrees/native-workflow-integration-20261007')
COMMIT='b2f45151128baa1fe387cda85862d71cb01e1206'
SOURCE='src/lei_signal/research/native_risk_d_mae_workflow.py'
UNIT='tests/unit/test_native_risk_d_mae_workflow.py'
INTEGRATION='tests/integration/test_native_risk_d_mae_workflow.py'
READ_FILES=[SOURCE,UNIT,INTEGRATION,'src/lei_signal/research/question_contract.py','src/lei_signal/research/workflow_inputs.py','src/lei_signal/research/workflow.py']
EXPECTED={SOURCE:'941ab8e495724a1d3f68ce1d15f967d8e994855bc6ae45387f7f81c6529054af',UNIT:'ee967bba8186946db1da0d72c8aed37b0eebd4b8eab1f8adb7eda7cb15eba41e',INTEGRATION:'3343cf2d245c5fc026c4c60a94274cb4e405252a6153e98fa4a213f4a04fadd2','src/lei_signal/research/question_contract.py':'74c6d17a7d0e8735b3b842bab2896aa3bb7fb8dd7c263e86d488fa5dbb038cff','src/lei_signal/research/workflow_inputs.py':'f250e8dd0a357a5fa0814ae51008f43145a7ec5b377b10596c0fccc30ccf7e43','src/lei_signal/research/workflow.py':'3b1b277137d6bfa883b7f05f0e7cc52000d480aac4a15c89edb35659537d6784'}
def sha(data):return hashlib.sha256(data).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
checks=[]
def check(name,condition,**data):checks.append({'name':name,'passed':bool(condition),**data})
def reject(name,fn):
    try:fn()
    except Exception as error:check(name,True,error=type(error).__name__+': '+str(error));return
    check(name,False,error='invalid input accepted')
before={p:{'sha256':sha((AUTHOR/p).read_bytes()),'bytes':(AUTHOR/p).stat().st_size} for p in READ_FILES}
check('locked source bytes',all(before[p]['sha256']==EXPECTED[p] for p in READ_FILES))
head=subprocess.check_output(['git','-C',str(AUTHOR),'rev-parse','HEAD']).decode().strip()
check('author HEAD is review commit',head==COMMIT,head=head)
write(HERE/'before.json',{'author_head':head,'files':before})

base=HERE/'source-copy'
if base.exists():raise SystemExit('Refuse to overwrite source-copy')
base.mkdir()
old=json.loads((PRIOR/'before.json').read_text())['files']
for rel in old:
    if not rel.startswith(('src/','scripts/','configs/')):continue
    data=(AUTHOR/rel).read_bytes()
    target=base/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
for p in READ_FILES:
    if p.startswith('tests/'):
        target=HERE/'author-tests'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((AUTHOR/p).read_bytes())
for name in ('x.json','y.json','draft-x.json'):
    source=PRIOR/'sandbox/inputs'/name
    target=HERE/'fixture'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
sys.path.insert(0,str(base/'src'))
from lei_signal.research import native_risk_d_mae_workflow as n
from lei_signal.research import workflow as w
x=json.loads((HERE/'fixture/x.json').read_text())
y=json.loads((HERE/'fixture/y.json').read_text())
rows=n.prepare_x(x)
check('normal fixed structure',len(rows)==76 and sum(len(r['event_ids']) for r in rows)==84 and len({(r['asset'],r['lifecycle']) for r in rows})==33)
bad=copy.deepcopy(x);bad['cases'][0]['event_ids'].append(bad['cases'][0]['event_ids'][0])
check('counterexample is 85 occurrences 84 unique',sum(len(r['event_ids']) for r in bad['cases'])==85 and len({v for r in bad['cases'] for v in r['event_ids']})==84)
reject('same-row duplicate rejected',lambda:n.prepare_x(bad))
bad=copy.deepcopy(x);bad['cases'][1]['event_ids'][0]=bad['cases'][0]['event_ids'][0]
reject('cross-row duplicate still rejected',lambda:n.prepare_x(bad))
base_contract=json.loads((HERE/'fixture/draft-x.json').read_text())
for field,bad in [('real_X',0),('real_Y','false'),('real_fits',False),('market_requests',False),('paid_requests',False),('production',0)]:
    altered=copy.deepcopy(base_contract);altered['permissions'][field]=bad
    reject('strict permission '+field,lambda altered=altered:n.validate_contract(altered))

def root_for(label):
    root=HERE/('isolated-'+label)
    if root.exists():raise SystemExit('Refuse to overwrite '+str(root))
    root.mkdir()
    for name in ('src','scripts','configs'):shutil.copytree(base/name,root/name)
    (root/'inputs').mkdir()
    for name in ('x.json','y.json'):(root/'inputs'/name).write_bytes((HERE/'fixture'/name).read_bytes())
    return root
def run_pair(label,elapsed,expect_success):
    root=root_for(label)
    c=copy.deepcopy(base_contract)
    c['history']['family']='native-d-mae20-synthetic-independent-repair-'+label
    c['budget']['execution_seconds']=1.5
    write(root/'inputs/x-draft.json',c)
    n.freeze_workflow(root/'inputs/x-draft.json',root/'frozen-x',root)
    with patch.object(n.time,'monotonic',side_effect=[0.,.1,elapsed,elapsed]):
        n.execute_workflow(root/'frozen-x/contract.json',root/'x',root)
    check(label+' X receipt exists',(root/'x/receipt.json').exists())
    c['stage']='y'
    c['data'].update({'y_path':'inputs/y.json','y_sha256':sha((root/'inputs/y.json').read_bytes())})
    c['x_receipt']={'path':'x','sha256':sha((root/'x/receipt.json').read_bytes())}
    write(root/'inputs/y-draft.json',c)
    n.freeze_workflow(root/'inputs/y-draft.json',root/'frozen-y',root)
    error=None
    try:
        with patch.object(n.time,'monotonic',side_effect=[0.,.1,elapsed,elapsed]):
            n.execute_workflow(root/'frozen-y/contract.json',root/'y',root)
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    events=[json.loads(s) for s in w.family_ledger(root,c['history']['family']).read_text().splitlines()]
    starts=[e['stage'] for e in events if e['event']=='start']
    finishes=[e for e in events if e['event']=='finish']
    check(label+' exactly one start each',starts==['x','y'])
    check(label+' receipt publication',(root/'y/receipt.json').exists() is expect_success)
    check(label+' result publication',(root/'y/result.json').exists() is expect_success)
    check(label+' completed state',(root/'y/state.json').exists() is expect_success)
    if expect_success:
        check(label+' has two computed finishes',len(finishes)==2 and all(e['status']=='computed' for e in finishes))
        cmd=[sys.executable,'-B','-c',"from lei_signal.research.workflow import check_publication; print(check_publication('y')['execution'])"]
        p=subprocess.run(cmd,cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'src')},text=True,capture_output=True)
        check(label+' fresh process publication check',p.returncode==0 and p.stdout.strip()=='completed',exit_code=p.returncode,stderr=p.stderr)
    else:
        check(label+' pauses before result',error is not None and 'WorkflowPaused' in error and not (root/'y/result.json').exists(),error=error)
        check(label+' failure retained',len(finishes)==2 and finishes[-1]['status']=='failed_after_start' and (root/'y/failure.json').is_file())
        reject(label+' retry refused',lambda:n.execute_workflow(root/'frozen-y/contract.json',root/'y-retry',root))
    return {'label':label,'budget_seconds':1.5,'injected_elapsed_per_stage':elapsed,'recorded_finish_seconds':sum(e.get('seconds',0) for e in finishes),'success_expected':expect_success,'error':error,'journal':events}
scenarios=[run_pair('over',.9,False),run_pair('within',.5,True)]
after={p:{'sha256':sha((AUTHOR/p).read_bytes()),'bytes':(AUTHOR/p).stat().st_size} for p in READ_FILES}
head_after=subprocess.check_output(['git','-C',str(AUTHOR),'rev-parse','HEAD']).decode().strip()
check('author unchanged after review',before==after and head_after==head)
check('no generated bytecode',not list(HERE.rglob('__pycache__')))
write(HERE/'after.json',{'author_head':head_after,'files':after,'unchanged':before==after})
write(HERE/'targeted-results.json',{'base_commit':'f0c72d078a97b02ddf21595422747377fd6e09cd','review_commit':COMMIT,'checks':checks,'scenarios':scenarios,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'real_X':0,'real_Y':0,'fits':0,'market_requests':0,'paid_requests':0,'clock_note':'Injected deterministic readings; not real elapsed time or operating-system hard deadline.'})
print(json.dumps({'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'scenarios':[(s['label'],s['recorded_finish_seconds'],s['error']) for s in scenarios]}))
