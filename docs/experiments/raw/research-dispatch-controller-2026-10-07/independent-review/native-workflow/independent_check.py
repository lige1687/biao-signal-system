"""Independent synthetic integration review. Writes only alongside this script.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B independent_check.py
No archived study import, market files, fitting, network, or author writes.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
from datetime import date, timedelta, datetime, timezone

OUT = Path(__file__).resolve().parent
AUTHOR = Path('/Users/yongbiaoli/Desktop/lei-signal-lab/.codex/worktrees/native-workflow-integration-20261007')
COMMIT = 'f0c72d078a97b02ddf21595422747377fd6e09cd'
OLD = '8a4a6f064341f39a2ed2420f102e88a451a04f1c'
RAW = 'docs/experiments/raw/native-workflow-integration-2026-10-07/'
ROOT = OUT / 'sandbox'
checks, commands, before = [], [], {}

def sha(b): return hashlib.sha256(b).hexdigest()
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    return sha(path.read_bytes())
def check(name, condition, **details):
    checks.append(dict(name=name, passed=bool(condition), **details))
def git(*args):
    return subprocess.check_output(['git','-C',str(AUTHOR),*args])
def copy_source(rel):
    source = AUTHOR / rel
    assert source.resolve().is_relative_to(AUTHOR.resolve())
    b=source.read_bytes(); before[rel]={'sha256':sha(b),'bytes':len(b)}
    p=ROOT / rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
    return p

if ROOT.exists(): raise SystemExit('Refuse overwrite: sandbox already exists')
ROOT.mkdir()
modules = set()
def module_copy(name):
    if not name.startswith('lei_signal') or name in modules: return
    modules.add(name)
    parts=name.split('.')
    for n in range(1,len(parts)):
        module_copy('.'.join(parts[:n]))
    rel='src/'+name.replace('.','/')+'.py'
    if not (AUTHOR/rel).is_file(): rel='src/'+name.replace('.','/')+'/__init__.py'
    if not (AUTHOR/rel).is_file(): return
    p=copy_source(rel)
    # Only unconditional top-level local imports, not unrelated lazy adapters.
    for node in ast.parse(p.read_text()).body:
        if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('lei_signal'):
            module_copy(node.module)
            for alias in node.names: module_copy(node.module+'.'+alias.name)
        if isinstance(node,ast.Import):
            for alias in node.names: module_copy(alias.name)
for name in ['workflow','workflow_inputs','native_risk_d_mae_workflow']:
    module_copy('lei_signal.research.'+name)
copy_source('scripts/run_factor_lab.py')
copy_source('configs/strategy-documents.v1.json')
six=['src/lei_signal/research/'+s+'.py' for s in ['native_risk_d_mae_workflow','question_contract','workflow_inputs','workflow']]+['tests/unit/test_native_risk_d_mae_workflow.py','tests/integration/test_native_risk_d_mae_workflow.py']
for rel in six:
    b=(AUTHOR/rel).read_bytes(); before[rel]={'sha256':sha(b),'bytes':len(b)}
    if rel.startswith('tests/'):
        p=OUT/'author-snapshots/current'/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
    try:
        committed=git('show',COMMIT+':'+rel)
        check('requested_commit_bytes:'+rel,committed==b)
    except subprocess.CalledProcessError:
        check('shared_file_delivered_as_patch:'+rel,rel in six[1:4])
for rel in [six[0],six[-1]]:
    b=git('show',OLD+':'+rel); p=OUT/'author-snapshots'/OLD/rel
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
for name in ['implementation-checks.json','implementation-start.json','baseline-dependencies.json','test-fixture-source.json','shared-entry-patch-manifest.json','shared-entry-changes.patch','permission-type-recheck.json','native-contract-mapping.json']:
    rel=RAW+name;b=(AUTHOR/rel).read_bytes();before[rel]={'sha256':sha(b),'bytes':len(b)}
    p=OUT/'author-snapshots'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
write(OUT/'before.json',{'time':datetime.now(timezone.utc).isoformat(),'head':git('rev-parse','HEAD').decode().strip(),'review_commit':COMMIT,'files':before})
manifest=json.loads((AUTHOR/RAW/'shared-entry-patch-manifest.json').read_text())
# Reverse the additions in an isolated copy, verify exact baseline, reapply.
patchroot=OUT/'patch-check';patchroot.mkdir()
for rel in six[1:4]:
    p=patchroot/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
patch=OUT/'author-snapshots/shared-entry-changes.patch'
def apply_patch(reverse=False):
    args=['git','apply','--unidiff-zero']+(['--reverse'] if reverse else [])+[str(patch)]
    r=subprocess.run(args,cwd=patchroot,env={**os.environ,'GIT_CEILING_DIRECTORIES':str(OUT)},capture_output=True,text=True)
    commands.append({'command':args,'cwd':str(patchroot),'exit_code':r.returncode,'stderr':r.stderr})
    return r.returncode==0
check('patch_reverse_applies',apply_patch(True))
expected_base=['ed4a44fbb3fbf6c7b986bd2fb9261f98f15cf33b604f04b84e7ceb4e2fffcb97','43a0683c13132fa34c73d4ce618d37746b5a8aa8da89e2967d132f59bee777ad','967d92adc77a18c42f16fda27c80eb5a136eadd72e4918515302003216a43cb6']
for rel,h in zip(six[1:4],expected_base): check('patch_baseline_hash:'+rel,sha((patchroot/rel).read_bytes())==h)
check('patch_forward_applies',apply_patch())
for rel in six[1:4]:check('patch_reconstructs:'+rel,(patchroot/rel).read_bytes()==(ROOT/rel).read_bytes())

sys.path.insert(0,str(ROOT/'src'))
from lei_signal.research import native_risk_d_mae_workflow as n
ASSETS=('510050.SS','510300.SS','510500.SS','512400.SS','512800.SS','588000.SS')
days=[];d=date(2026,1,1)
while d<=date(2026,7,31):
    if d.weekday()<5:days.append(d.isoformat())
    d+=timedelta(days=1)
cases=[];windows={};prices={};serial=0
for a,(count,groups) in enumerate(zip((15,17,12,5,26,1),(6,6,5,3,12,1))):
    asset=ASSETS[a]
    prices[asset]={day:{'close':100+a*10+(i%17)*.7-(i%7)*1.1,'status':'quoted','action_known':True} for i,day in enumerate(days)}
    for j in range(count):
        cid='review-'+str(serial);signal=days[j+4] if a<5 else '2026-06-16'
        A=101+j+a;atr=1.4+j*.03;D=.5+(j%5)*.2; C=A-D*atr
        aliases=['event-'+str(serial)]+(['extra-'+str(serial)] if serial<8 else [])
        cases.append(dict(case_id=cid,asset=asset,signal_date=signal,lifecycle='group-'+str(j%groups),event_ids=aliases,A=A,C=C,ATR20_SMA=atr,D=D))
        future=days[days.index(signal)+1:days.index(signal)+22];mature=future[-1]<='2026-06-26'
        windows[cid]=dict(asset=asset,signal_date=signal,label_start=future[0],label_end=future[-1] if mature else None,calendar_mature_by_20260626=mature)
        serial+=1
x=dict(schema_version='native-d-mae-x/1.0',artificial_only=True,cases=cases)
y=dict(schema_version='native-d-mae-y/1.0',artificial_only=True,cutoff='2026-06-26',windows=windows,retained_dates={a:days[:] for a in ASSETS},prices=prices)
xs=write(ROOT/'inputs/x.json',x)

def contract(stage='x', ysha=None, family='native-d-mae20-synthetic-independent-review'):
    c=dict(schema_version=n.SCHEMA,study_id='frozen_d_close_mae20',stage=stage,feature={'kind':n.FEATURE_KIND},target=dict(kind='mae',start_offset=1,end_offset=21,entry_field='close',path_field='close',unit='percentage_point',cutoff='2026-06-26'),comparison=dict(candidate='D',benchmark='V',evaluator='signed_spearman_equal_asset_fixed_groups/1.0',deletion_groups=33,fits=0),data=dict(mode='synthetic',artificial_only=True,x_path='inputs/x.json',x_sha256=xs),sources=dict(design_sha256=n.DESIGN_SHA,synthetic_math_sha256=n.STUDY_SHA),history={'family':family},budget=dict(execution_seconds=120,stage_runs=2),permissions=dict(real_X=False,real_Y=False,real_fits=0,market_requests=0,paid_requests=0,production=False),publication=dict(conclusion='synthetic_engineering_only',register_report=False))
    if stage=='y':
        c['data'].update(y_path='inputs/y.json',y_sha256=ysha)
        c['x_receipt']=dict(path='runs/x',sha256=sha((ROOT/'runs/x/receipt.json').read_bytes()))
    return c
def rejects(name,fn):
    try:fn()
    except Exception as exc:check(name,True,error=type(exc).__name__+': '+str(exc));return
    check(name,False,error='accepted invalid input')
def call(*args,expect=0):
    cmd=[sys.executable,'-B',str(ROOT/'scripts/run_factor_lab.py'),*args]
    r=subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')},text=True,capture_output=True)
    commands.append(dict(command=cmd,cwd=str(ROOT),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
    check('CLI '+' '.join(args), r.returncode==expect,exit_code=r.returncode)
    return r
for field in ['real_X','real_Y','production']:
    for value in [0,0.0,'false',None]:
        c=contract();c['permissions'][field]=value
        rejects('permission '+field+' '+repr(value),lambda c=c:n.validate_contract(c))
for field in ['real_fits','market_requests','paid_requests']:
    for value in [False,0.0,'0',None]:
        c=contract();c['permissions'][field]=value
        rejects('permission '+field+' '+repr(value),lambda c=c:n.validate_contract(c))
c=contract();c['publication']['register_report']=0
rejects('publication bool exact',lambda:n.validate_contract(c))
for value in [None,0,'false',False,1]:
    check('action_known '+repr(value),n.path_close({'close':100,'action_known':value}) is None)
rejects('nonfinite V',lambda:n.volatility_scale(1e308,1e308))
rows=n.prepare_x(x);paths,unknown=n.validate_y_paths(rows,y);result=n.evaluate_y(rows,paths,unknown)
check('76/84/33/75/one identity',len(rows)==76 and sum(len(r['event_ids']) for r in rows)==84 and len(paths)==75 and unknown=='review-75' and len(result['statistics']['leave_one_lifecycle'])==33)
# Same-row duplicate is intentionally distinct from cross-row duplicate.
bad=copy.deepcopy(x);bad['cases'][0]['event_ids'].append(bad['cases'][0]['event_ids'][0])
rejects('duplicate alias within one case must reject',lambda:n.prepare_x(bad))
accepted=n.prepare_x(bad)
write(OUT/'duplicate-alias-counterexample.json',dict(case=bad['cases'][0],accepted_event_occurrences=sum(len(r['event_ids']) for r in accepted),accepted_unique_events=len({v for r in accepted for v in r['event_ids']})))
bad=copy.deepcopy(x);bad['cases'][1]['event_ids'].append(bad['cases'][0]['event_ids'][0])
rejects('cross-case duplicate alias rejects',lambda:n.prepare_x(bad))
# Each of 21 positions separately fails the entire saved path qualification.
first=cases[0];future=paths[first['case_id']]['dates']
for i,day in enumerate(future):
    bad=copy.deepcopy(y);del bad['prices'][first['asset']][day]
    rejects('missing future position '+str(i+1),lambda bad=bad:n.validate_y_paths(rows,bad))
bad=copy.deepcopy(y);bad['prices'][first['asset']][future[7]]['status']='halted'
rejects('halt at position8',lambda:n.validate_y_paths(rows,bad))
bad=copy.deepcopy(y);bad['windows'][first['case_id']]['asset']=ASSETS[1]
rejects('Y member swap rejects',lambda:n.validate_y_paths(rows,bad))
def ranks(values): return [1+sum(b<a for b in values)+(sum(b==a for b in values)-1)/2 for a in values]
def rho(a,b):
    if len(a)<2:return None
    a=ranks(a);b=ranks(b);am=sum(a)/len(a);bm=sum(b)/len(b)
    aa=sum((v-am)**2 for v in a);bb=sum((v-bm)**2 for v in b)
    return sum((v-am)*(w-bm) for v,w in zip(a,b))/math.sqrt(aa*bb) if aa*bb else None
errors=[];comparisons=0
allrows=result['rows'];fixed=result['statistics']['primary']['fixed_assets']
for deleted,st in [(None,result['statistics'])]+[((r['deleted_asset'],r['deleted_lifecycle']),r) for r in result['statistics']['leave_one_lifecycle']]:
    subset=[r for r in allrows if (r['asset'],r['lifecycle'])!=deleted]
    expected={}
    for a in ASSETS:
        r=[r for r in subset if r['asset']==a and r['Y'] is not None]
        expected[a]=(rho([v['D'] for v in r],[v['Y'] for v in r]),rho([v['V'] for v in r],[v['Y'] for v in r]))
        for k,v in zip(('rho_D_Y','rho_V_Y'),expected[a]):
            actual=st['per_asset'][a][k];comparisons+=1
            if v is None:check(str(deleted)+a+k,actual is None)
            else:errors.append(abs(actual-v))
    summary=st['primary'] if deleted is None else st['fixed_asset_summary']
    check('fixed assets '+str(deleted),summary['fixed_assets']==fixed)
    for j,k in enumerate(('rho_D_Y','rho_V_Y')):
        vals=[expected[a][j] for a in fixed];v=None if any(z is None for z in vals) else sum(vals)/len(vals)
        actual=summary[k];comparisons+=1
        if v is None:check('uncomputable remains null '+str(deleted)+k,actual is None)
        else:errors.append(abs(v-actual))
check('independent full+33 summary numeric',max(errors)<1e-12,comparisons=comparisons,max_error=max(errors))
write(OUT/'independent-artificial-statistics.json',result)

# X runs while there is no Y file anywhere in sandbox inputs.
write(ROOT/'inputs/draft-x.json',contract())
call('--review-workflow-contract','inputs/draft-x.json')
call('--workflow-draft','inputs/draft-x.json','--out','runs/frozen-x')
call('--workflow-contract','runs/frozen-x/contract.json','--out','runs/x')
check('X has no Y file',not (ROOT/'inputs/y.json').exists())
xresult=json.loads((ROOT/'runs/x/result.json').read_text())
check('X only result no labels',all('Y' not in r and 'closes' not in r for r in xresult['rows']))
# A bad batch must not create a Y freeze or a Y start.
bad=copy.deepcopy(y);bad['prices'][first['asset']][future[7]]['status']='halted'
ys=write(ROOT/'inputs/y.json',bad);write(ROOT/'inputs/bad-y.json',contract('y',ys))
r=call('--workflow-draft','inputs/bad-y.json','--out','runs/bad-frozen-y',expect=1)
check('bad Y never froze',not (ROOT/'runs/bad-frozen-y/contract.json').exists())
ys=write(ROOT/'inputs/y.json',y);write(ROOT/'inputs/draft-y.json',contract('y',ys))
call('--workflow-draft','inputs/draft-y.json','--out','runs/frozen-y')
call('--workflow-contract','runs/frozen-y/contract.json','--out','runs/y')
saved=json.loads((ROOT/'runs/y/result.json').read_text())
check('CLI equals independent fixture result',saved==result)
def fresh_check(name,expect_success):
    cmd=[sys.executable,'-B','-c',"from lei_signal.research.workflow import check_publication; print(check_publication('runs/y'))"]
    r=subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'},text=True,capture_output=True)
    commands.append(dict(command=cmd,cwd=str(ROOT),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
    check(name,(r.returncode==0)==expect_success)
fresh_check('fresh process verifies receipt',True)
call('--workflow-contract','runs/frozen-y/contract.json','--out','runs/y-repeat',expect=3)
ledger=next((ROOT/'docs/experiments/raw/research-workflow-ledgers-2026-09-29').glob('*/attempts.jsonl'))
events=[json.loads(v) for v in ledger.read_text().splitlines()]
check('exact two starts',[(v['stage']) for v in events if v['event']=='start']==['x','y'])
write(OUT/'ledger-observation.json',events)
original=(ROOT/'runs/y/result.json').read_bytes();write(ROOT/'runs/y/result.json',{})
fresh_check('tampered result rejected',False)
(ROOT/'runs/y/result.json').write_bytes(original)
c=contract();c['data']['mode']='real';write(ROOT/'inputs/real.json',c)
call('--review-workflow-contract','inputs/real.json',expect=3)
# Capture all author read sources, verify no mutation; old/new revision is explicit.
after={rel:{'sha256':sha((AUTHOR/rel).read_bytes()),'bytes':(AUTHOR/rel).stat().st_size} for rel in before}
check('author exact bytes unchanged during review',before==after)
check('no sandbox pycache',not list(ROOT.rglob('__pycache__')))
write(OUT/'after.json',dict(time=datetime.now(timezone.utc).isoformat(),head=git('rev-parse','HEAD').decode().strip(),files=after,unchanged=before==after))
write(OUT/'independent-checks.json',dict(review_commit=COMMIT,previous_commit=OLD,checks=checks,commands=commands,passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),real_X=0,real_Y=0,real_V=0,fits=0,market_requests=0,paid_requests=0))
print(json.dumps({'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'source_files':len(before),'numeric_comparisons':comparisons,'max_error':max(errors)}))
