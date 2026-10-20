"""Controller: read frozen observations/starts; no new market run or old writes."""
import csv
import hashlib
import json
import math
import statistics as st
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RAW = ROOT / 'docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16'
RUN = RAW / 'run-01'
B1 = ROOT / 'docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16'
checks = []

def ck(ok, name):
    checks.append({'name': name, 'ok': bool(ok)})

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def csvrows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))

def close(a, b):
    return abs(a-b) <= 1e-12

rows = csvrows(B1 / 'run-02/observations.csv')
cal = read(B1 / 'run-02/input-package/calendar.json')
days = sorted(d for d,v in cal['days'].items() if v['is_trading_day'])
axis = [d for d in days if '2019-10-08' <= d <= '2025-12-31']
ck([r['session'] for r in rows] == axis, 'complete observed date keys')
legal = [all(r[k] == 'True' for k in ('flag_state_known','flag_main_legal','flag_mature')) for r in rows]
ck(all((r['in_comparison']=='True') == q for r,q in zip(rows,legal)), 'legal mask')

def stats(sub):
    vals = [float(r['main']) for r in sub]
    aux = [float(r['aux']) for r in sub if r['aux']]
    return dict(n=len(vals),mean=st.fmean(vals),median=st.median(vals),up=sum(v>0 for v in vals),down=sum(v<0 for v in vals),zero=sum(v==0 for v in vals),up_ratio=sum(v>0 for v in vals)/len(vals),aux_n=len(aux),aux_mean=st.fmean(aux),aux_worst=min(aux))

lr = [r for r,q in zip(rows,legal) if q]
def groups(sub):
    return [stats([r for r in sub if r['state']==s]) for s in ('true','false')]
def delta(sub):
    t,f = groups(sub)
    return t['mean']-f['mean']
fp = read(RUN/'stability.json')['full_period']
for side,values in zip(('true','false'),groups(lr)):
    for k,v in values.items():
        ck(close(fp[side][k],v),f'full {side} {k}')
years = sorted({r['session'][:4] for r in rows})
yr = csvrows(RUN/'yearly.csv')
loo = csvrows(RUN/'leave-one-year-out.csv')
ck([r['year'] for r in yr] == years, 'yearly keys')
ck([r['year'] for r in loo] == years, 'loo keys')
annual=[]
for y,out in zip(years,yr):
    sub=[r for r in lr if r['session'].startswith(y)]
    annual.append(delta(sub))
    for side,values in zip(('true','false'),groups(sub)):
        for k,v in values.items():
            ck(close(float(out[f'{side}_{k}']),v),f'{y} {side} {k}')
    ck(close(float(out['delta']),annual[-1]) and out['null_reason']=='',f'{y} delta/null')
for out in loo:
    sub=[r for r in lr if not r['session'].startswith(out['year'])]
    t,f=groups(sub)
    ck(close(float(out['delta']),delta(sub)),f"loo {out['year']} delta")
    ck(int(out['true_n'])==t['n'] and int(out['false_n'])==f['n'] and int(out['n'])==len(sub) and out['null_reason']=='',f"loo {out['year']} counts")
stab=read(RUN/'stability.json')['year_stability']
ck(close(stab['equal_weight_year_delta']['mean_delta'],st.fmean(annual)), 'equal year delta')
ck(stab['sign_counts']==dict(positive=2,negative=5,zero=0),'year signs')
pos={d:i for i,d in enumerate(days)}
sets=[set(zip(days[pos[r['e_date']]:pos[r['x_date']]],days[pos[r['e_date']]+1:pos[r['x_date']]+1])) for r in lr]
ov=read(RUN/'overlap.json')
ck(sum(map(len,sets))==ov['total_interval_refs'],'interval refs')
ck(len(set.union(*sets))==ov['unique_intervals'],'unique intervals')
ck(all(len(a&b)==20 for a,b in zip(sets,sets[1:])),'adjacent shared20')

unc=read(RUN/'uncertainty.json')['resampling']
for L in (63,126):
    starts=np.load(RUN/f'resampling-L{L}-starts.npy',allow_pickle=False)
    ck(np.array_equal(starts,np.random.Generator(np.random.PCG64(20260916)).integers(0,len(rows),size=(2000,math.ceil(len(rows)/L)))),f'L{L} fixed-seed origins')
    reps=csvrows(RUN/f'resampling-L{L}-replicates.csv')
    ck(len(reps)==2000,f'L{L} reps keys')
    ds=[]
    for j,startrow in enumerate(starts):
        vals={True:[],False:[]}
        for k in range(len(rows)):
            ix=(int(startrow[k//L])+k%L)%len(rows)
            if legal[ix]: vals[rows[ix]['state']=='true'].append(float(rows[ix]['main']))
        d=st.fmean(vals[True])-st.fmean(vals[False]); ds.append(d)
        out=reps[j]
        ck(int(out['rep'])==j and int(out['true_n'])==len(vals[True]) and int(out['false_n'])==len(vals[False]) and out['reason']=='' and close(float(out['delta']),d),f'L{L} replicate{j}')
    ds.sort()
    for q,key in ((.025,'quantile_lower'),(.975,'quantile_upper')):
        x=q*(len(ds)-1); i=math.floor(x)
        val=ds[i]+(x-i)*(ds[i+1]-ds[i])
        ck(close(unc[f'L{L}'][key],val),f'L{L} {key}')

protocol=read(RAW/'protocol-v1.0.0.json')
ck(sha(RAW/'protocol-v1.0.0.json')=='769a350160ef9f3da896df9c048b4b4ff664d64a4b1ab88cdf7dfb54adb88db1','protocol sha')
for rel,h in protocol['code_identity'].items():
    ck(sha(ROOT/rel)==h and sha(RAW/'freeze/1.0.0/code-snapshot'/rel.replace('/','__'))==h,'code '+rel)
ident=protocol['input_identity']
for key,v in ident.items():
    if key.endswith('_path'):
        ck(sha(ROOT/ident['base_dir']/v)==ident[key[:-5]+'_sha256'],'input '+key)
base=read(RAW/'baseline/freeze-baseline.json')['files']
for e in base: ck(sha(ROOT/e['path'])==e['sha256'],'protected '+e['path'])
manifest=read(RUN/'manifest.json')
ck(set(manifest['files'])=={str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file() and p != RUN/'manifest.json'},'manifest exact keys')
for rel,meta in manifest['files'].items(): ck(sha(RUN/rel)==meta['sha256'],'output '+rel)

# Synthetic counterexamples; never call the real analysis entry point.
from lei_signal.research.factor_evidence.contract import validate_protocol
from lei_signal.research.factor_evidence.observations import validate_observations
from lei_signal.research.factor_evidence.stability import overlap_audit
from lei_signal.research.factor_evidence.resampling import paired_block_deltas
from lei_signal.research.factor_evidence.runner import run_analysis
issues={}
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    changed=json.loads(json.dumps(protocol)); changed['object_ref']='wrong.object@9'; changed['use']='production'
    p=tmp/'protocol-v1.0.0.json'; p.write_text(json.dumps(changed))
    try: validate_protocol(p,ROOT); issues['wrong_object_and_use_accepted']=True
    except ValueError: issues['wrong_object_and_use_accepted']=False
    dates=pd.bdate_range('2020-01-02',periods=35).strftime('%Y-%m-%d').tolist()
    schedule=pd.DataFrame({'session':dates,'in_window':[i<8 for i in range(35)]})
    frame=pd.DataFrame([dict(symbol='SYN',session=dates[i],state=bool(i%2),main=.01*(1 if i%2 else -1),aux=0.,legal=i!=1,legal_reason=None if i!=1 else 'excluded',e_date=dates[i+1],x_date=dates[i+22]) for i in range(8)])
    frame,audit=validate_observations(frame,schedule)
    overlap=overlap_audit(frame,schedule,dates[0],23)
    issues['overlap_excluded_row_count']={'legal':audit['counts']['legal'],'audited':overlap['rows_audited']}
    params=json.loads(json.dumps(protocol['fixed_params'])); params['resampling'].update(block_lengths=[2,4],reps=4,min_valid_reps=1)
    out=tmp/'synthetic'
    run_analysis(frame,schedule,params,out_dir=out,source_meta={'protocol_path':p,'protocol_sha256':sha(p),'hashes_verified':0})
    card=read(out/'evidence-card.json')
    issues['synthetic_provenance']={'actual_symbol':'SYN','card_symbol':card['symbol'],'input':card['input'],'method':card['method']}
    try:
        paired_block_deltas(frame.iloc[:0],2,4,1)
        issues['empty']='returned'
    except Exception as e: issues['empty']=type(e).__name__+': '+str(e)
    short=params.copy()
    one=frame.copy(); one['state']=True
    try:
        run_analysis(one,schedule,params,out_dir=tmp/'one',source_meta={'protocol_path':p})
        issues['one_group_runner']='returned'
    except Exception as e: issues['one_group_runner']=type(e).__name__+': '+str(e)
    example=(ROOT/'docs/research/factor-evidence-reliability-usage.md').read_text().split('```python\n')[1].split('```')[0]
    try: exec(compile(example,'usage-example','exec'),{}); issues['usage_example']='passed'
    except Exception as e: issues['usage_example']=type(e).__name__+': '+str(e)

result={'checks':len(checks),'failures':[v for v in checks if not v['ok']],'protected_count':len(base),'full_delta':delta(lr),'equal_year_delta':st.fmean(annual),'counterexamples':issues,'no_new_market_run':True}
with (HERE/'results.json').open('x') as f: json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False,indent=2))
