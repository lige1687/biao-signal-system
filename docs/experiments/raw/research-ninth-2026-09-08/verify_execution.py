"""Independent reference order/first-exit audit. Never imports account engine."""
from pathlib import Path
import json,gzip,math
from datetime import date
from bisect import bisect_right
import pandas as pd
P=Path(__file__).resolve().parent;E=P.parent/'research-eighth-2026-09-08';Q=E/'product-qualification'
def read(p):return json.loads(p.read_text())
params=read(Q/'execution-parameters.json');actions=read(Q/'actions.json')
prices={s:pd.read_csv(Q/'bars-helper-native'/f'{s}-nominal.csv').set_index('date').to_dict('index') for s in params['symbols']}
candidates={c['candidate_id']:c for c in read(P/'account-results/candidates.json')}
with gzip.open(E/'candidate-study/exit-observations.json.gz','rt') as f:observations=json.load(f)
with gzip.open(E/'candidate-study/candidates.json.gz','rt') as f:originals={c['candidate_id']:c for c in json.load(f)}
sessions=sorted({d for rows in prices.values() for d in rows});end=params['research_window'][1]
allowed={'target_unavailable','signal_reward_risk_below_3'}
def same(a,b):
 if a is None or b is None:assert a is b,(a,b)
 else:assert abs(a-b)<=1e-8*max(1,abs(a),abs(b)),(a,b)
def levels_at(s,levels,basis,d):
 values=dict(levels)
 for a in sorted(actions,key=lambda x:x['effective_date']):
  if a['symbol']!=s or not basis<a['effective_date']<=d:continue
  if a['type']=='split':factor=1/float(a['ratio'])
  else:
   prev=max(x for x in prices[s] if x<a['effective_date']);close=prices[s][prev]['close'];factor=(close-float(a['cash']))/close
  values={k:v*factor if v is not None else None for k,v in values.items()}
 return values
def unavailable(s,d):
 if d in params['blocked_dates'][s]:return 'known_open_unavailable'
 if d not in prices[s]:return 'missing_quote'
 prev=max(x for x in prices[s] if x<d);reference=prices[s][prev]['close']
 for a in sorted(actions,key=lambda x:x['effective_date']):
  if a['symbol']==s and prev<a['effective_date']<=d:reference=reference/float(a['ratio']) if a['type']=='split' else reference-float(a['cash'])
 limit=params['limits'][s]
 for effective,value in params['limit_changes'].get(s,[]):
  if effective<=d:limit=value
 return 'at_open_limit_conservative' if abs(prices[s][d]['open']-reference)>=reference*limit-.00051 else None
allpositions=[];allorders=[];allfills=[]
for cfg in ['R0','R1']:
 R=P/'account-results'/cfg
 trades=pd.read_csv(R/'trades.csv').to_dict('records');daily=pd.read_csv(R/'daily.csv').set_index('date')
 orders=read(R/'orders.json');roundtrips=read(R/'roundtrips.json');order_map={o['order_id']:o for o in orders};exits={}
 for c in candidates.values():
  if c['config_id']!=cfg:continue
  orig=originals[c['source_candidate_id']]
  assert c['diagnostic_reference_only'] is True
  assert all(c[k]==v for k,v in orig.items() if k not in ['config_id','candidate_id'])
 for rt in roundtrips:
  s=rt['symbol'];entry=rt['entry_date'];trigger=None;reason=None
  levels={k:rt['initial_'+k] for k in ['stop','target','upper']}
  for d in sorted(x for x in prices[s] if entry<=x<=end):
   rebased=levels_at(s,levels,entry,d);cl=prices[s][d]['close'];obs=observations[s][d]
   if cl<rebased['stop']:reason='structure_stop'
   elif cl<obs['ema20'] and cl<obs['cost20']:reason='ema_cost_exit'
   else:continue
   trigger=d;break
  possible=[d for d in sessions if trigger is not None and trigger<d<=end and not unavailable(s,d)]
  expected_exit=possible[0] if possible else None
  assert rt['exit_date']==expected_exit,('exit_date',cfg,rt['position_id'],trigger,expected_exit,rt['exit_date'])
  exits[rt['position_id']]=trigger
  if expected_exit:
   sell=[t for t in trades if t['position_id']==rt['position_id'] and t['side']=='sell'];assert len(sell)==1 and sell[0]['reason']==reason
  allpositions.append(dict(config_id=cfg,position_id=rt['position_id'],first_exit_signal=trigger,exit_date=expected_exit,reason=reason,matched=True))
 for t in trades:
  s,d=t['symbol'],t['date'];assert unavailable(s,d) is None
  same(t['price'],prices[s][d]['open']);same(t['notional'],t['shares']*t['price']);same(t['fee'],t['notional']*.001)
  o=order_map[t['order_id']];assert o['status']=='filled'
  if t['side']=='buy':
   c=candidates[t['candidate_id']];assert c['signal_accepted'] is True or c['signal_reject_reason'] in allowed
   assert c['signal_ref']>c['stop']>0 and d==sessions[bisect_right(sessions,c['signal_date'])]
   lv=levels_at(s,{k:c[k] for k in ['stop','target','upper']},c['signal_date'],d)
   assert t['price']>lv['stop']>0
   same(lv['stop'],t['stop']);same(lv['target'],None if pd.isna(t['target']) else t['target']);assert t['shares']%100==0
  allfills.append(dict(config_id=cfg,order_id=t['order_id'],date=d,matched=True))
 expected_ids={c['candidate_id'] for c in candidates.values() if c['config_id']==cfg}
 buys=[o for o in orders if o['side']=='buy'];assert {o['candidate_id'] for o in buys}==expected_ids and len(buys)==len(expected_ids)
 for o in buys:
  c=candidates[o['candidate_id']];s,d=c['symbol'],c['signal_date'];reason=None;attempt=False
  if c['signal_accepted'] is False and c['signal_reject_reason'] not in allowed:reason=c['signal_reject_reason'] or 'signal_rejected'
  elif not c['stop'] or c['stop']<=0:reason='invalid_stop'
  elif not c['signal_ref'] or c['signal_ref']<=c['stop']:reason='nonpositive_signal_risk'
  positions=[rt for rt in roundtrips if rt['symbol']==s and rt['entry_date']<=d and (rt['exit_date'] is None or rt['exit_date']>d)]
  if not reason and positions:
   assert len(positions)==1;rt=positions[0];sig=exits[rt['position_id']]
   reason='pending_exit' if sig is not None and sig<=d else 'position_exists'
  idx=bisect_right(sessions,d);planned=sessions[idx] if idx<len(sessions) else None
  assert o['planned_date']==planned
  if not reason and planned is not None and planned<=end:
   attempt=True
   sold=any(t['symbol']==s and t['date']==planned and t['side']=='sell' for t in trades)
   held=any(rt['symbol']==s and rt['entry_date']<planned and (rt['exit_date'] is None or rt['exit_date']>planned) for rt in roundtrips)
   reason='same_day_sale' if sold else 'position_exists' if held else unavailable(s,planned)
   if not reason:
    op=prices[s][planned]['open'];lv=levels_at(s,{k:c[k] for k in ['stop','target','upper']},d,planned)
    if op<=lv['stop']:reason='nonpositive_open_risk'
    else:
     prior=max(x for x in daily.index if x<planned);available=float(daily.loc[prior,'cash_'+s])
     if date.fromisoformat(planned).weekday()==0:available+=250
     available+=sum(e['amount'] for e in read(R/'events.json') if e['date']==planned and e['symbol']==s and e['kind']=='dividend_paid')
     qty=math.floor(max(0,available)/(op*1.001)/100)*100
     if qty<=0:reason='insufficient_cash_or_risk_lot'
     else:assert o['shares']==qty,('quantity',cfg,o['order_id'],qty)
  expected_status='rejected' if reason else 'filled' if attempt else 'pending_at_end'
  assert o['status']==expected_status,(cfg,o['order_id'],expected_status,o['status'],reason)
  if reason:assert o['reason']==reason,(cfg,o['order_id'],reason,o['reason'])
  assert len(o['attempts'])==int(attempt)
  assert all(o['candidate_metadata'].get(k)==v for k,v in c.items())
  if 'original_candidate_id' in o['candidate_metadata']:assert o['candidate_metadata']['original_candidate_id']==c['source_candidate_id']
  allorders.append(dict(config_id=cfg,candidate_id=c['candidate_id'],expected_status=expected_status,expected_reason=reason,matched=True))
for name,rows in [('position-checks',allpositions),('order-checks',allorders),('fill-checks',allfills)]:pd.DataFrame(rows).to_csv(P/(name+'.csv'),index=False)
result=dict(status='passed',all_fills=len(allfills),all_original_candidate_orders=len(allorders),all_position_first_exits=len(allpositions),original_metadata_unchanged=True,engine_imported=False)
(P/'execution-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
