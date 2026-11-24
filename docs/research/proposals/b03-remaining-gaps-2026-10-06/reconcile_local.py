from pathlib import Path
from collections import Counter
from decimal import Decimal
import csv, hashlib, json, math, shutil
import pandas as pd
import pyarrow.parquet as pq

BASE=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
TMP=Path('/tmp/lei-b03-plan.1ZD5Kk')
A=TMP/'audit-input'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
manifest=json.loads((A/'FILE-HASHES.json').read_text())
for x in manifest['files']:
    p=A/x['path']; assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'], x['path']
queue=json.loads((A/'original-gap-queue-frozen.json').read_text())
assert sha(A/'original-gap-queue-frozen.json')=='86efbc695762692dd4dff168e5bfa922a180549853586f677205a8b46e294578'
parts={x['symbol_code']:x for x in queue['partitions']}
Q=json.loads((BASE/'docs/experiments/raw/stock-week-month-qualification-2026-10-05/qualification.json').read_text())
sources=[]
for k in ['membership','wide_close']:
    x=Q['sources'][k];p=Path(x['path']);p=p if p.is_absolute() else BASE/p
    assert sha(p)==x['sourcehash'], k
    sources.append({'kind':k,'path':str(p),'sha256':x['sourcehash'],'bytes':p.stat().st_size})
mp,cp=map(lambda x:Path(x['path']),sources)
m=pd.read_parquet(mp)
m['date']=pd.to_datetime(m['date']).dt.strftime('%Y-%m-%d')
m['symbol']=m['symbol'].astype(str).str.zfill(6)
m=m[(m['date']>='2022-01-04')&(m['date']<='2026-06-30')]
assert len(m)==325500 and m['date'].nunique()==1085 and m['symbol'].nunique()==439
schema=pq.read_schema(cp).names
cols=['date']+[s for s in parts if s in schema]
c=pd.read_parquet(cp,columns=cols)
if 'date' in c.columns:c=c.set_index('date')
c.index=pd.to_datetime(c.index).strftime('%Y-%m-%d')
gaps=set()
for date,symbol in m[m['symbol'].isin(parts)][['date','symbol']].itertuples(index=False,name=None):
    v=c.at[date,symbol] if symbol in c.columns and date in c.index else float('nan')
    if pd.isna(v) or not math.isfinite(float(v)) or float(v)<=0:gaps.add((symbol,date))
assert len(gaps)==1944
assert Counter(s for s,d in gaps)==Counter({s:p['missing_candidate_member_records'] for s,p in parts.items()})
observations={};windows=[];files=[]
for batch,rel in [('B01','baostock-bounded-air-probe-2026-10-05'),('B02','b02-targeted-gap-batch-2026-10-05')]:
    run=BASE/'docs/experiments/raw'/rel/'run-01'
    qm=run/'query-manifest.json';d=json.loads(qm.read_text())
    files.append({'batch':batch,'path':str(qm),'bytes':qm.stat().st_size,'sha256':sha(qm)})
    for q in d['queries']:
        if q['kind']!='daily_raw':continue
        assert q['status']=='success' and q['response_completed_and_decoded']
        par=q['params'];s=par['code'].split('.')[1]
        windows.append({'batch':batch,'symbol':s,'start':par['start_date'],'end':par['end_date']})
        pinfo=q['normalized_payload'];p=run/pinfo['path']
        assert p.stat().st_size==pinfo['bytes'] and sha(p)==pinfo['sha256']
        files.append({'batch':batch,'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
        for row in json.loads(p.read_text())['records']:
            key=(s,row['date']);assert key not in observations
            assert row['code']==par['code'] and row['adjustflag']=='3'
            vals={k:Decimal(row[k]) for k in ['open','high','low','close']}
            assert all(v.is_finite() and v>0 for v in vals.values())
            assert vals['low']<=min(vals['open'],vals['close'])<=max(vals['open'],vals['close'])<=vals['high']
            if row['tradestatus']=='0': assert row['volume']=='' and row['amount']==''
            else: assert row['tradestatus']=='1'
            observations[key]=row
assert len(observations)==1787
classified={}
for key in gaps:
    s,date=key;row=observations.get(key)
    if row:status='normal_raw_observation' if row['tradestatus']=='1' else 'provider_placeholder'
    else:status='queried_no_return' if any(w['symbol']==s and w['start']<=date<=w['end'] for w in windows) else 'never_queried'
    classified[key]=status
counts=Counter(classified.values())
assert counts=={'normal_raw_observation':1601,'provider_placeholder':106,'never_queried':233,'queried_no_return':4},counts
ledger=list(csv.DictReader((A/'remaining-keys-exact.csv').open()))
expected={(x['symbol'],x['date']):x['status'] for x in ledger}
actual={k:v for k,v in classified.items() if v in ['never_queried','queried_no_return']}
assert expected==actual and len(expected)==237
plans=json.loads((A/'unreleased-233-key-plan.json').read_text())['partitions']
planned={(p['symbol'],date) for p in plans for date in p['exact_dates']}
assert planned=={k for k,v in actual.items() if v=='never_queried'}
assert len(plans)==31 and sum(len(p['exact_dates']) for p in plans)==233
strategy=[]
for x in Q['strategy_sources']:
    p=Path(x['path']);v=sha(p);assert v==x['sourcehash'];strategy.append({'path':str(p),'sha256':v})
result={'schema':'b03-existing-data-reconciliation/1.0','status':'passed_read_only','source_library_id':'libfile_457a3c87e3d88191b8b8fc59d449fbbe','source_library_version':0,'source_package_sha256':'3ed11716738a46f4b544a2551048fb178b2e7bf885a012162021592a756fa9e7','sources':sources,'strategy_sources':strategy,'batch_query_and_normalized_files':files,'candidate_counts':{'codes':439,'dates':1085,'rows':325500},'old_gap_classification':dict(counts),'all_raw_unique_keys':len(observations),'never_queried_codes':len(plans),'never_queried_exact_keys':233,'queried_no_return_exact_keys':4,'exact_remaining_ledger_matches':True,'new_provider_calls':0,'main_table_repairs':0,'feature_label_fits':0,'free_disk_bytes':shutil.disk_usage(BASE).free,'qualification_limits':['No raw/qfq cross-scale comparison or splicing','No official historical membership or action/terminal-value qualification','No new feature or target qualification']}
(TMP/'local-reconciliation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','old_gap_classification','never_queried_codes','all_raw_unique_keys','free_disk_bytes']},ensure_ascii=False))
