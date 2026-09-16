"""Predeclared prefix-invariance audit of unmodified A/C/D research proxies. No returns."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;E=P.parent/'research-eighth-2026-09-08';PACKAGE=P/'research-package'
sys.path.insert(0,str(PACKAGE/'src'));sys.path.insert(0,str(E/'product-qualification/price-helper'))
from price_basis import PriceBasis
from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events
from lei_signal.rules.two_b_reversal import detect_two_b_reversal_events
from lei_signal.rules.module_d_false_breakout import detect_module_d_events
from dataclasses import asdict
from enum import Enum
from datetime import datetime,timezone,timedelta
from collections import Counter
import json,gzip,hashlib
import pandas as pd
import numpy as np
START,END='2015-01-01','2026-06-30'
FUNCTIONS={'A':detect_first_ma_pullback_events,'C':detect_two_b_reversal_events,'D':detect_module_d_events}
FIELDS=['open','high','low','close','volume']
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(x):
 if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [plain(v) for v in x]
 if isinstance(x,Enum):return x.value
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 if isinstance(x,np.integer):return int(x)
 if hasattr(x,'isoformat'):return x.isoformat()
 return x
def save(p,x):p.write_text(json.dumps(plain(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def load_inputs():
 bars={s:pd.read_csv(E/'product-qualification/bars-helper-native'/f'{s}-nominal.csv').to_dict('records') for s in ['sh510300','sh513100','sh518880','sz159915']}
 actions=read(E/'product-qualification/actions.json');return bars,actions

def raw_asof(s,bars,actions,d):
 observed={s:[r for r in bars[s] if r['date']<=d]};known=[a for a in actions if a['symbol']==s and a['announcement_date']<=d]
 basis=PriceBasis(observed,known);rows=[]
 for r in observed[s]:
  value=basis.bar(s,r,d,'cash_proportional_v1');rows.append({'date':r['date'],**{f:float(value[f]) for f in FIELDS}})
 frame=pd.DataFrame(rows).set_index('date');frame.index=pd.to_datetime(frame.index);return frame

def events_for(raw,s):
 frame=classify_colors(compute_features(raw));out={}
 for name,fn in FUNCTIONS.items():
  missing=(fn.__module__,[k for k in ('open','high','low','close','volume','signal_color','ema20','sma20','close_lag20') if k not in frame])
  assert not missing[1],missing
  out[name]=[plain(asdict(e)) for e in fn(frame,s)]
 return out

def select(events,lo,hi):return {e['event_id']:e for e in events if lo<=e['available_date']<=hi}
def main():
 out=P/'history-diagnostic';assert not out.exists(),'Preserve prior attempt';out.mkdir()
 bars,actions=load_inputs();plan=[];dates_by_symbol={}
 for s in bars:
  dates=[r['date'] for r in bars[s] if START<=r['date']<=END];dates_by_symbol[s]=dates
  chosen=set()
  for year in range(2015,2027):
   ys=[d for d in dates if d.startswith(str(year))];chosen.update([ys[0],ys[-1]])
  boundaries=sorted({START}|{a['effective_date'] for a in actions if a['symbol']==s and START<=a['effective_date']<=END})
  for a in actions:
   if a['symbol']!=s or not START<=a['effective_date']<=END:continue
   before=[d for d in dates if d<a['effective_date']];after=[d for d in dates if d>=a['effective_date']]
   if before:chosen.add(before[-1])
   if after:chosen.add(after[0])
  for k,lo in enumerate(boundaries):
   hi=(pd.Timestamp(boundaries[k+1])-timedelta(days=1)).date().isoformat() if k+1<len(boundaries) else END
   plan.append(dict(symbol=s,start=lo,end=hi,cutoffs=sorted(d for d in chosen if lo<=d<=hi)))
 files=[Path(__file__),P/'protocol.md',P/'protocol-addendum-01.md',E/'product-qualification/actions.json',E/'product-qualification/price-helper/price_basis.py']+list((E/'product-qualification/bars-helper-native').glob('*.csv'))+[x for x in PACKAGE.rglob('*') if x.is_file()]
 assert sha(P/'protocol.md')==read(P/'protocol-lock.json')['sha256']
 for f,h in read(P/'source-lock.json')['files'].items():assert sha(Path(f))==h
 for f,h in read(P/'supplement-lock.json')['files'].items():assert sha(Path(f))==h
 save(out/'run-lock.json',dict(started_at_utc=datetime.now(timezone.utc).isoformat(),files={str(x):sha(x) for x in files},plan=plan,date_count=sum(len(x['cutoffs']) for x in plan),scope='raw event information qualification; no target filtering or returns'))
 all_events=[];checks=[];diffs=[];counts=[]
 for i,epoch in enumerate(plan):
  s,lo,hi=epoch['symbol'],epoch['start'],epoch['end'];raw=raw_asof(s,bars,actions,hi);full=events_for(raw,s)
  for name,events in full.items():
   retained=list(select(events,lo,hi).values());all_events.extend([dict(module=name,basis_epoch_start=lo,basis_epoch_end=hi,event=e) for e in retained])
   counts.append(dict(symbol=s,module=name,start=lo,end=hi,event_count=len(retained),confirmed_count=sum('confirmed' in e['evidence'].get('sub_rule','') for e in retained)))
  for d in epoch['cutoffs']:
   # With no intervening effective action, prefix rows are exactly the same unit basis.
   prefix_raw=raw_asof(s,bars,actions,d);pd.testing.assert_frame_equal(raw.loc[:d],prefix_raw,check_exact=True)
   trunc=events_for(prefix_raw,s)
   for name in FUNCTIONS:
    earlier=select(trunc[name],lo,d);later=select(full[name],lo,d);missing=sorted(set(earlier)-set(later));added=sorted(set(later)-set(earlier));changed=sorted(k for k in set(earlier)&set(later) if earlier[k]!=later[k])
    checks.append(dict(symbol=s,module=name,epoch_start=lo,epoch_end=hi,cutoff=d,prefix_events=len(earlier),full_history_events=len(later),removed_after_future=len(missing),added_after_future=len(added),changed_after_future=len(changed),matched=not(missing or added or changed)))
    for kind,ids in [('removed_after_future',missing),('added_after_future',added),('changed_after_future',changed)]:
     for eid in ids:diffs.append(dict(symbol=s,module=name,epoch_start=lo,epoch_end=hi,cutoff=d,kind=kind,event_id=eid,before=earlier.get(eid),after=later.get(eid)))
  save(out/'progress.json',dict(epochs_completed=i+1,epochs_total=len(plan),checks_completed=len(checks),differences_recorded=len(diffs)))
  print(s,lo,hi,'complete',len(checks),'checks',flush=True)
 with gzip.open(out/'raw-events.json.gz','wt') as f:json.dump(all_events,f,ensure_ascii=False,allow_nan=False)
 with gzip.open(out/'differences.json.gz','wt') as f:json.dump(diffs,f,ensure_ascii=False,allow_nan=False)
 pd.DataFrame(checks).to_csv(out/'prefix-checks.csv',index=False);pd.DataFrame(counts).to_csv(out/'event-counts.csv',index=False)
 summaries=[]
 for name in FUNCTIONS:
  rows=[x for x in checks if x['module']==name];ds=[x for x in diffs if x['module']==name]
  summaries.append(dict(module=name,checks=len(rows),passed=sum(x['matched'] for x in rows),failed=sum(not x['matched'] for x in rows),difference_records=len(ds),unique_affected_ids=len({x['event_id'] for x in ds}),unique_confirmed_affected_ids=len({x['event_id'] for x in ds if 'confirmed' in (x['before'] or x['after'])['evidence'].get('sub_rule','')}),raw_events=sum(x['event_count'] for x in counts if x['module']==name),raw_confirmed=sum(x['confirmed_count'] for x in counts if x['module']==name)))
 save(out/'summary.json',dict(status='diagnostic_completed',modules=summaries,all_checks=len(checks),unique_check_dates=sum(len(x['cutoffs']) for x in plan),raw_event_records=len(all_events),scope='fixed historical checkpoints; absence of difference is not all-date proof; events with failures are not qualified for return studies'))
 assert all(sha(Path(f))==h for f,h in read(out/'run-lock.json')['files'].items())
 save(out/'completion.json',dict(finished_at_utc=datetime.now(timezone.utc).isoformat(),epochs=len(plan),input_hashes_unchanged=True,no_return_simulation=True))
 print(summaries,flush=True)
if __name__=='__main__':main()
