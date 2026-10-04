"""Candidate member/price support only. No market factor or returns fitted."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent;R=H.parents[3];P=R/'tests/fixtures/market_context/component_bars'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def members(data,date):
 out=set(data['current'])
 for e in sorted(data['changes'],key=lambda x:x['date'],reverse=True):
  if e['date']>date:
   if e['added']:out.discard(e['added'])
   if e['removed']:out.add(e['removed'])
 return sorted(out)
# Simple boundary examples: included change date vs preceding date; no upstream execution.
fake={'current':['B','C'],'changes':[{'date':'2020-01-03','added':'B','removed':'A'}]}
assert members(fake,'2020-01-02')==['A','C'];assert members(fake,'2020-01-03')==['B','C'];assert members(fake,'2020-01-04')==['B','C']
x=json.loads((H/'membership-source.json').read_text());manifest=json.loads((R/'tests/fixtures/market_context/manifest.json').read_text());dates=['2025-04-04','2025-04-07','2025-04-08','2025-04-10'];current=set(x['current']);cache={};inputs={};reports=[]
for day in dates:
 universe=members(x,day);rows=[]
 for sym in universe:
  # Exact listed symbol first; dot-to-hyphen only Yahoo notation, no rename merge.
  paths=[q for q in dict.fromkeys([P/(sym+'.parquet'),P/(sym.replace('.','-')+'.parquet')]) if q.exists()]
  row={'symbol':sym,'path':None,'reason':None,'support20':False,'support50':False}
  if len(paths)!=1:row['reason']='missing_file' if len(paths)==0 else 'ambiguous_symbol_files';rows.append(row);continue
  p=paths[0];row['path']=str(p.relative_to(R))
  if p not in cache:
   f=pd.read_parquet(p,columns=['date','close']);f.date=pd.to_datetime(f.date);cache[p]=f;inputs[str(p.relative_to(R))]={'bytes':p.stat().st_size,'sha256':sha(p),'first':str(f.date.min().date()),'last':str(f.date.max().date())}
  f=cache[p];past=f[f.date<=pd.Timestamp(day)];row['reason']='date_absent' if not (f.date==pd.Timestamp(day)).any() else None
  if not f.date.is_unique or not f.date.is_monotonic_increasing:row['reason']='duplicate_or_unsorted'
  if row['reason'] is None:
   for n in [20,50]:
    z=past.tail(n).close.to_numpy();row['support'+str(n)]=bool(len(z)==n and np.isfinite(z).all() and (z>0).all())
   if not row['support50']:row['reason']='missing_or_invalid_window'
  rows.append(row)
 reports.append({'date':day,'candidate_members':len(universe),'not_in_current':sorted(set(universe)-current),'current_not_historical':sorted(current-set(universe)),'quote_file_count':sum(r['path'] is not None for r in rows),'support20':sum(r['support20'] for r in rows),'support50':sum(r['support50'] for r in rows),'exceptions':[r for r in rows if r['reason'] is not None],'members_sha256':hashlib.sha256(('\n'.join(universe)+'\n').encode()).hexdigest()})
# Per-security metadata permits identifying exact missing dependencies, no market values.
dump(H/'price-file-manifest.json',{'files':inputs,'fixture_manifest':{'path':'tests/fixtures/market_context/manifest.json','sha256':sha(R/'tests/fixtures/market_context/manifest.json'),'generated_at':manifest['generated_at'],'source_kind':manifest['source_kind']},'not_delivered':True})
result={'scope':'candidate input support, not qualified historical breadth or efficacy','upstream_commit':json.loads((H/'upstream-commit.json').read_text())['sha'],'current_members':len(current),'event_count':len(x['changes']),'dates':reports,'synthetic_boundary_checks':3,'qualified_for_original_E':False,'missing_qualifications':['actual event effective dates vs announcements','security identity and reused/renamed tickers','delisted prices or missing windows','corporate actions/adjustment vintage','original acquisition and source publication time','actual exchange-calendar/window completeness','price-source use/license qualifications'],'manifest_generation_before_latest_bar':any(v['last']>manifest['generated_at'][:10] for v in inputs.values()),'market_fits':0,'returns_computed':False,'breadth_values_computed':False}
dump(H/'chain-support.json',result);print(json.dumps({k:result[k] for k in ['current_members','event_count','manifest_generation_before_latest_bar']}));print(json.dumps([{k:r[k] for k in ['date','candidate_members','quote_file_count','support20','support50','exceptions']} for r in reports],ensure_ascii=False))
