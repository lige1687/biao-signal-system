"""Bounded independent candidate review. No root generator calls and no returns."""
from pathlib import Path
import sys,json,gzip,hashlib,dataclasses
from decimal import Decimal,localcontext
from datetime import datetime,timezone,timedelta
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent;E=P.parent;sys.dont_write_bytecode=True
sys.path.insert(0,str(E/'b-research-fix/research-package/src'))
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.dense_breakout import detect_dense_breakout_events,_make_event,SUB_RULE_CONFIRMED
from lei_signal.rules.reward_risk_filter import compute_reward_risk
from lei_signal.domain.rules_config import get_rule
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str,allow_nan=False)+'\n')
def gz(n):
 with gzip.open(E/'candidate-study'/n,'rt') as f:return json.load(f)
candidates=gz('candidates.json.gz');events=gz('B-events.json.gz');actions=json.loads((E/'product-qualification/actions.json').read_text())
raw={s:pd.read_csv(E/'product-qualification/bars-helper-native'/f'{s}-nominal.csv',dtype={'date':str}) for s in ['sh510300','sh513100','sh518880','sz159915']}
assert not ({a['symbol'] for a in actions if a['type']=='split'} & {a['symbol'] for a in actions if a['type']=='cash_dividend'})
manifest=json.loads((P/'input-manifest.json').read_text())
assert all(sha(Path(x['path']))==x['sha256'] for x in manifest['files'])
write('run-before.json',{'time_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'inputs_match':True})
frame_cache={};basis_audit=[]
def independent_frame(symbol,day):
 key=(symbol,day)
 if key in frame_cache:return frame_cache[key]
 bars=raw[symbol];prefix=bars[bars.date<=day].copy();use=[a for a in actions if a['symbol']==symbol and a['announcement_date']<=day and a['effective_date']<=day]
 use.sort(key=lambda a:(a['effective_date'],a['event_id']))
 rows=[]
 with localcontext() as ctx:
  ctx.prec=40
  for row in prefix.to_dict('records'):
   factor=Decimal(1);volume_factor=Decimal(1)
   for a in use:
    if row['date']>=a['effective_date']:continue
    if a['type']=='split':factor/=Decimal(str(a['ratio']));volume_factor*=Decimal(str(a['ratio']))
    elif a['type']=='cash_dividend':
     prev=bars[bars.date<a['effective_date']].iloc[-1];c=Decimal(str(prev['close']));d=Decimal(str(a['cash']));assert c>d;factor*=(c-d)/c
    else:raise ValueError(a['type'])
   out={'date':row['date'],**{k:float(Decimal(str(row[k]))*factor) for k in ['open','high','low','close']},'volume':float(Decimal(str(row['volume']))*volume_factor)};rows.append(out)
 f=pd.DataFrame(rows).set_index('date');f.index=pd.to_datetime(f.index);f=compute_features(f);frame_cache[key]=f
 basis_audit.append({'symbol':symbol,'as_of':day,'rows':len(f),'last_row':f.index[-1].date().isoformat(),'included_actions':[a['event_id'] for a in use],'source_prices_sha256':sha(E/'product-qualification/bars-helper-native'/f'{symbol}-nominal.csv')})
 return f

def nearest_high(frame):
 left=int(get_rule('swing_pivots').param('left',3));right=int(get_rule('swing_pivots').param('right',3));assert left==right==3
 asof=frame.index[-1].date();earliest=asof-timedelta(days=round(365.25*float(get_rule('resistance_b1').param('lookback_years',2))));close=float(frame.close.iloc[-1]);choices=[]
 for i in range(left,len(frame)-right):
  if frame.index[i].date()<earliest:continue
  center=float(frame.high.iloc[i]);others=[float(frame.high.iloc[j]) for j in range(i-left,i+right+1) if i!=j]
  if center>close and all(center>v for v in others):choices.append({'target':center,'pivot_date':frame.index[i].date().isoformat(),'confirmed_at':frame.index[i+right].date().isoformat(),'index':i})
 return max(choices,key=lambda x:(x['pivot_date'],x['index'])) if choices else None

def near(a,b):return (a is None and b is None) or (a is not None and b is not None and abs(float(a)-float(b))<=1e-11)
counts=[]
for cfg in sorted({c['config_id'] for c in candidates}):
 for symbol in sorted({c['symbol'] for c in candidates if c['config_id']==cfg}):
  rows=[c for c in candidates if c['config_id']==cfg and c['symbol']==symbol];reasons={}
  for c in rows:
   k=c['signal_reject_reason'] or 'accepted';reasons[k]=reasons.get(k,0)+1
  counts.append({'config_id':cfg,'symbol':symbol,'raw':len(rows),'accepted':sum(c['signal_accepted'] for c in rows),'reasons':reasons})
p0=[c for c in candidates if c['config_id']=='P0'];p1=[c for c in candidates if c['config_id']=='P1'];by0={(c['symbol'],c['signal_date']):c for c in p0};by1={(c['symbol'],c['signal_date']):c for c in p1}
ignore={'config_id','candidate_id'}
p01_equal=set(by0)==set(by1) and all({k:v for k,v in by0[key].items() if k not in ignore}=={k:v for k,v in by1[key].items() if k not in ignore} for key in by0)
finite=sorted([c for c in p0 if c['signal_rr'] is not None],key=lambda c:(-c['signal_rr'],c['symbol'],c['signal_date']))
selected={c['candidate_id']:c for c in finite[:10]}
for s in sorted(raw):
 rows=[c for c in finite if c['symbol']==s]
 if rows:selected[rows[0]['candidate_id']]=rows[0]
for source in ['volume_profile','range_high',None]:
 rows=[c for c in p0 if c['target_source']==source]
 if rows:
  c=min(rows,key=lambda c:(c['signal_date'],c['symbol']));selected[c['candidate_id']]=c
brows=[c for c in candidates if c['config_id'] in ['P2','P3','P4','P7']]
selected_all=brows+list(selected.values());assert len(selected_all)<=40
b_event_review=[];by_b={}
for e in events:
 f=independent_frame(e['symbol'],e['signal_date']);all_ev=detect_dense_breakout_events(f,e['symbol']);matches=[x for x in all_ev if x.event_id==e['event_id'] and x.evidence.get('sub_rule')==SUB_RULE_CONFIRMED and x.evidence.get('variant')=='breakout'];assert len(matches)==1
 actual=matches[0];watch=next(x for x in all_ev if x.lifecycle_id==actual.lifecycle_id and x.evidence.get('sub_rule')=='dense_breakout_watch');wi=f.index.get_loc(pd.Timestamp(watch.available_date));before=f.iloc[wi:-1];assert len(before)>0
 high=float(before.high.max());low=float(before.low.min());manual=nearest_high(f)
 passed=(actual.available_date.isoformat()==e['signal_date'] and actual.evidence==e['evidence'] and near(high,e['evidence']['breakout_reference']) and near(low,e['evidence']['stop_price']) and float(f.close.iloc[-1])>high)
 b_event_review.append({'symbol':e['symbol'],'date':e['signal_date'],'event_id':e['event_id'],'watch_date':watch.available_date.isoformat(),'watch_to_yesterday_bars':len(before),'manual_upper':high,'manual_stop':low,'signal_close':float(f.close.iloc[-1]),'nearest_confirmed_high':manual,'matches':passed})
 by_b[(e['symbol'],e['signal_date'])]=actual
checks=[]
for c in selected_all:
 f=independent_frame(c['symbol'],c['signal_date']);pos=len(f)-1
 if c['config_id'] in ['P2','P3','P4','P7']:
  event=by_b[(c['symbol'],c['signal_date'])];event=dataclasses.replace(event,evidence={**event.evidence,'stop_price':c['stop']})
 else:event=_make_event(spec=get_rule('dense_breakout'),symbol=c['symbol'],day=f.index[-1].date(),lifecycle_id='independent-common-target-check',sub_rule=SUB_RULE_CONFIRMED,variant='breakout',reference=float(c['signal_ref']),close=float(f.close.iloc[-1]),zone_low=c['stop'],stop_price=c['stop'])
 rr=compute_reward_risk(f,event,confirmed_pivots(f),gaps=None)
 manual=nearest_high(f);expected_stop=float(f.close.iloc[-61:-1].min()) if c['config_id'] in ['P0','P2'] else by_b[(c['symbol'],c['signal_date'])].evidence['stop_price']
 expected_accept=rr.reward_risk is not None and rr.reward_risk>=3
 target_source_match=(c['target'] is None and rr.target_b is None) or rr.target_source==c['target_source']
 manual_ok=True
 if c['target_source']=='swing_high':manual_ok=manual is not None and near(manual['target'],c['target']) and manual['pivot_date']==c['target_source_date'] and manual['confirmed_at']==c['target_confirmed_at']
 predicate_ok=True
 if c['config_id']=='P0':predicate_ok=float(f.close.iloc[-1])>float(f.close.iloc[-61:-1].max())
 ok=near(rr.entry_price,c['signal_ref']) and near(c['stop'],expected_stop) and near(rr.target_b,c['target']) and near(rr.reward_risk,c['signal_rr']) and expected_accept==c['signal_accepted'] and target_source_match and manual_ok and predicate_ok
 checks.append({'candidate_id':c['candidate_id'],'config_id':c['config_id'],'symbol':c['symbol'],'signal_date':c['signal_date'],'entry_ref':c['signal_ref'],'stop':c['stop'],'target':c['target'],'target_source':c['target_source'],'signal_rr':c['signal_rr'],'signal_accepted':c['signal_accepted'],'direct_compute_reward_risk':dataclasses.asdict(rr),'independent_nearest_high':manual,'independent_stop':expected_stop,'raw_predicate_matches':predicate_ok,'matches':ok})
write('all-counts.json',counts);write('B-six-events.json',b_event_review);write('selected-target-checks.json',checks);write('ordinary-breakout-nearest.json',list(selected.values()));write('price-prefix-audit.json',basis_audit)
pd.DataFrame([{k:v for k,v in x.items() if not isinstance(v,(dict,list))} for x in checks]).to_csv(P/'selected-target-checks.csv',index=False)
# Counts recomputed from full raw JSON, rather than trusting the summary.
main_summary=json.loads((E/'candidate-study/summary.json').read_text());compare=[{'config_id':x['config_id'],'symbol':x['symbol'],'raw':x['raw'],'signal_accepted':x['accepted']} for x in counts];summary_match=sorted(compare,key=lambda x:(x['config_id'],x['symbol']))==sorted(main_summary['by_config_symbol'],key=lambda x:(x['config_id'],x['symbol']))
sourcebad=[x['path'] for x in manifest['files'] if sha(Path(x['path']))!=x['sha256']]
result={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'all_candidate_rows':len(candidates),'unique_candidate_ids':len({c['candidate_id'] for c in candidates}),'B_unique_events':len(events),'B_event_all_match':all(x['matches'] for x in b_event_review),'target_rows_checked':len(checks),'target_rows_all_match':all(x['matches'] for x in checks),'ordinary_breakout_rows_per_config':len(p0),'ordinary_breakout_no_target':sum(c['target'] is None for c in p0),'ordinary_breakout_below3':sum(c['signal_rr'] is not None and c['signal_rr']<3 for c in p0),'ordinary_breakout_accepted':sum(c['signal_accepted'] for c in p0),'ordinary_breakout_max_rr':finite[0]['signal_rr'],'P0_P1_all_equal_except_config_id':p01_equal,'recomputed_counts_match_main_summary':summary_match,'source_changes':sourcebad,'new_strategy_runs':0,'performance_verdict':None}
result['passed']=all([result['B_event_all_match'],result['target_rows_all_match'],summary_match,p01_equal,not sourcebad])
write('summary.json',result)
print(json.dumps(result,ensure_ascii=False))
