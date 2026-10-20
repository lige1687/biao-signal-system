"""Compare frozen source records and emitted candidates without importing adapter."""
from verify_accounts import *
import gzip
from collections import Counter

def gz(path):
 with gzip.open(path,'rt') as f:return json.load(f)

def run_sources():
 snap=BASE/'accepted'; original=gz(snap/'original-eleventh-events.json.gz');copied=gz(snap/'adapter/all-source-events.json.gz')
 assert original==copied and len(original)==2174
 rows=jload(snap/'account-results/candidates.json');adapter=gz(snap/'adapter/candidates.json.gz');assert rows==adapter
 expected={};mapping={'P0':'REF_BREAKOUT','P5':'REF_ROAD'};checks=[];maxerr=ZERO;boundary_exceptions=[]
 for r in original:
  e=r['event'];v=e['evidence'];m=r['module'];sub=v.get('sub_rule','');cfg=None
  if m=='A' and sub=='first_ma_pullback_confirmed':
   assert v['entry_variant'] in {'early','confirmed'} and v['ma_period'] in {20,60,120}
   cfg='A'+str(v['ma_period'])+('E' if v['entry_variant']=='early' else 'J')
  elif m=='C' and sub.endswith('_confirmed'):
   assert v['version'] in {'v1','v2','v3'};cfg={'two_b_reversal_v1_confirmed':'C1','two_b_reversal_v2_confirmed':'C2','two_b_reversal_v3_confirmed':'C3'}[sub]
  elif m=='D' and sub=='module_d_long_confirmed':cfg='D'
  if cfg:
   cid=cfg+':'+e['event_id'];assert cid not in expected;expected[cid]=(cfg,r)
 assert len(expected)==891
 acd=[c for c in rows if c['config_id'] not in mapping.values()]
 assert len(acd)==len(expected) and {c['candidate_id'] for c in acd}==set(expected)
 for c in acd:
  cfg,r=expected[c['candidate_id']];e=r['event'];v=e['evidence'];d=e['available_date']
  assert c['config_id']==cfg and c['source_candidate_id']==e['event_id']
  assert c['source_event_record']==r and c['source_event']==e
  assert c['metadata']['source_event_record']==r and c['metadata']['source_event']==e
  assert c['symbol']==e['symbol'] and c['signal_date']==d and c['basis_as_of']==d
  assert c['stop']==v.get('stop_price') and c['metadata']['original_stop']==v.get('stop_price')
  for f in ('lifecycle_id','rule_version'):assert c[f]==e.get(f)
  for f in ('touch_date','a3_structure_id'):assert c[f]==v.get(f) and c['metadata'][f]==v.get(f)
  ref=num(c['signal_ref']);diff=abs(ref-num(v['close']));maxerr=max(maxerr,diff);assert diff<D('1e-12')
  stop=num(c['stop']) if c['stop'] is not None else None;target=num(c['target']) if c['target'] is not None else None
  if stop is None or not 0<stop<ref:reason='invalid_structure_risk';rr=None
  elif target is None or target<=ref:reason='target_unavailable';rr=None
  else:
   rr=(target-ref)/(ref-stop);reason=None if rr>=3 else 'signal_reward_risk_below_3'
  if c['signal_accepted'] is not (reason is None) or c['signal_reject_reason']!=reason:
   assert rr==D(3) and c['signal_accepted'] is False and c['signal_reject_reason']=='signal_reward_risk_below_3'
   assert D(3)-D('1e-12')<num(c['signal_rr'])<D(3)
   orders=jload(snap/'account-results'/cfg/'orders.json');order=next(o for o in orders if o.get('candidate_id')==c['candidate_id'])
   quote=next(r for r in readcsv(snap/'product-qualification/bars-helper-native'/f"{c['symbol']}-nominal.csv") if r['date']==order['planned_date'])
   known_actions=jload(snap/'product-qualification/actions.json')
   assert not any(a['symbol']==c['symbol'] and d<a['effective_date']<=order['planned_date'] for a in known_actions)
   assert num(quote['open'])<=stop
   boundary_exceptions.append(dict(candidate_id=c['candidate_id'],config=cfg,symbol=c['symbol'],signal_date=d,signal_ref=ref,stop=stop,target=target,decimal_reward_risk=rr,reported_binary_float_reward_risk=c['signal_rr'],actual_signal_rejection=c['signal_reject_reason'],planned_date=order['planned_date'],next_open=quote['open'],independent_next_open_reason='nonpositive_open_risk',account_fill_impact='none: next open would independently fail positive-risk requirement'))
  if rr is None:assert c['signal_rr'] is None
  else:diff=abs(num(c['signal_rr'])-rr);maxerr=max(maxerr,diff);assert diff<TOL
  if target is not None:
   assert c['target_source'] is not None
   assert c['target_confirmed_at']<=d and c['target_source_date']<=d
  checks.append(dict(candidate_id=c['candidate_id'],config=cfg,source_id=e['event_id'],kind='confirmed_source_event',signal_date=d,signal_accepted=c['signal_accepted']))
 old=gz(snap/'original-eighth-candidates.json.gz');refs={c['candidate_id']:c for c in old if c['config_id'] in mapping}
 supplied=[c for c in rows if c['config_id'] in mapping.values()]
 assert len(refs)==len(supplied)==1742
 assert {c['source_candidate_id'] for c in supplied}==set(refs)
 for c in supplied:
  source=refs[c['source_candidate_id']]
  assert c['config_id']==mapping[source['config_id']] and c['candidate_id']==c['config_id']+':'+source['candidate_id']
  assert c['source_config_id']==source['config_id'] and c['metadata']['source_candidate']==source
  for f,value in source.items():
   if f not in {'candidate_id','config_id'}:assert c[f]==value,(c['candidate_id'],'mutated original reference field',f)
  checks.append(dict(candidate_id=c['candidate_id'],config=c['config_id'],source_id=c['source_candidate_id'],kind='original_reference_candidate',signal_date=c['signal_date'],signal_accepted=c['signal_accepted']))
 assert len(rows)==len(checks)==2633
 writecsv(BASE/'candidate-source-checks.csv',checks)
 save(BASE/'source-results.json',dict(status='conditional_numeric_boundary_exceptions' if boundary_exceptions else 'passed',numeric_boundary_exceptions=boundary_exceptions,full_source_events=len(original),confirmed_source_candidates=len(acd),original_reference_candidates=len(supplied),total_candidates=len(rows),per_config=dict(Counter(c['config_id'] for c in rows)),max_numeric_difference=maxerr,not_reviewed='Independent recreation of A/C/D signal detector and target-selection algorithm; source mapping and declared target dates/qualification are verified, full target-prefix checks are in adapter evidence.'))
 print('Source records and candidate coverage passed:',len(rows))

if __name__=='__main__':
 try:run_sources()
 except Exception as e:
  import traceback
  save(BASE/'sources-failed-attempt.json',dict(error=repr(e),traceback=traceback.format_exc()));raise
