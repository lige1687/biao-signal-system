"""Compare completed fixed-path outputs to already-saved independent Decimal results."""
from verify_accounts import *
import gzip

def run():
 expected=jload(REVIEW/'fixed-paths-independent.json');reported=jload(SNAP/'execution/fixed-17-paths.json')
 key=lambda r:(r.get('config',r.get('config_id')),r['position_id'],r.get('variant',r.get('method')))
 em={key(r):r for r in expected};am={key(r):r for r in reported};assert len(em)==len(am)==34 and set(em)==set(am)
 daily=defaultdict(dict)
 for r in readcsv(REVIEW/'fixed-daily-independent.csv'):daily[key(r)][r['date']]=r
 attempts=defaultdict(list)
 for r in readcsv(REVIEW/'fixed-attempts-independent.csv'):attempts[key(r)].append(dict(date=r['date'],reason=r['reason']))
 actions=jload(SNAP/'product-qualification/actions.json');road=json.load(gzip.open(REVIEW/'observations-independent.json.gz','rt'))
 checks=[];event_checks=[];maxerr=ZERO
 def numeric(k,field,actual,value):
  nonlocal maxerr
  diff=abs(num(actual)-num(value));maxerr=max(maxerr,diff);assert diff<TOL,(k,field,actual,value,diff)
  checks.append(dict(config=k[0],position_id=k[1],variant=k[2],field=field,reported=actual,independent=value,difference=diff))
 for k,r in em.items():
  a=am[k];d=daily[k];s=r['symbol'];end='2026-06-30';entry=r['entry_date'];exitdate=r['exit_date']
  for field,source in {'candidate_id':'candidate_id','symbol':'symbol','entry_date':'entry_date','exit_date':'exit_date','exit_signal_date':'first_exit_signal','exit_reason':'exit_reason'}.items():assert a[field]==r[source],(k,field,a[field],r[source])
  for field,source in {'entry_price':'entry_price','initial_shares':'original_shares','final_shares':'shares','entry_notional':'entry_notional','buy_fee':'buy_fee','sell_fee':'sell_fee','dividends':'dividend_accrued','exit_notional':'exit_notional','terminal_market_value':'market_value','terminal_value_from_entry_cash':'net_pnl','net_pnl':'net_pnl'}.items():numeric(k,field,a[field],r[source])
  numeric(k,'baseline_net_pnl',a['baseline_net_pnl'],em[(k[0],k[1],'S')]['net_pnl'])
  numeric(k,'initial_stop',a['initial_stop'],d[entry]['stop']);numeric(k,'final_stop',a['final_stop'],d[exitdate or end]['stop'])
  if exitdate:numeric(k,'exit_price',a['exit_price'],next(q['open'] for q in readcsv(SNAP/'product-qualification/bars-helper-native'/f'{s}-nominal.csv') if q['date']==exitdate))
  else:assert a['exit_price'] is None
  assert a['exit_attempts']==attempts[k],(k,'exit attempts mismatch')
  events={(e['date'],e['kind'],e.get('event_id')):e for e in a['events']};assert len(events)==len(a['events'])
  wanted={}
  for action in actions:
   if action['symbol']!=s:continue
   eid=action['event_id'];effective=action['effective_date']
   if action['type']=='split':
    if entry<=effective<=end:
     prior=(date.fromisoformat(effective)-timedelta(days=1)).isoformat();oldq=num(d[prior]['shares']) if prior in d else ZERO
     frozen_day=min(effective,exitdate) if exitdate else effective
     wanted[(effective,'split',eid)]={'shares_after':oldq*num(action['ratio']),'stop_after':num(d[frozen_day]['stop'])}
   else:
    recday=action['record_date'];payday=action['pay_date'];q=num(d[recday]['shares']) if recday in d else ZERO;money=q*num(action['cash'])
    if entry<=recday<=end:wanted[(recday,'dividend_recorded',eid)]={'shares':q}
    if entry<=effective<=end:
     frozen_day=min(effective,exitdate) if exitdate else effective
     wanted[(effective,'dividend_receivable',eid)]={'amount':money,'entitled_shares':q,'stop_after':num(d[frozen_day]['stop'])}
    if entry<=payday<=end:wanted[(payday,'dividend_paid',eid)]={'amount':money}
  if r['first_exit_signal']:
   signal=r['first_exit_signal'];wanted[(signal,'exit_signal',None)]={'reason':r['exit_reason'],'close':num(road[s][signal]['close']),'stop':num(d[signal]['stop'])}
  if exitdate:
   prev=(date.fromisoformat(exitdate)-timedelta(days=1)).isoformat();sold=num(d[prev]['shares'])
   for action in actions:
    if action['symbol']==s and action['type']=='split' and action['effective_date']==exitdate:sold*=num(action['ratio'])
   wanted[(exitdate,'sell',None)]={'reason':r['exit_reason'],'shares':sold,'price':num(r['exit_notional'])/sold,'fee':num(r['sell_fee'])}
  assert set(events)==set(wanted),(k,'event identities missing/extra',set(events)^set(wanted))
  for ek,fields in wanted.items():
   e=events[ek]
   for field,val in fields.items():
    if isinstance(val,D):numeric(k,'event:'+str(ek)+':'+field,e[field],val)
    else:assert e[field]==val
   event_checks.append(dict(config=k[0],position_id=k[1],variant=k[2],date=ek[0],kind=ek[1],event_id=ek[2],fields_checked=len(fields)))
 writecsv(REVIEW/'fixed-executor-checks.csv',checks);writecsv(REVIEW/'fixed-event-checks.csv',event_checks)
 result=jload(REVIEW/'fixed-path-results.json');result.update(status='passed',executor_paths_compared=len(am),executor_numeric_checks=len(checks),executor_events_compared=len(event_checks),executor_exit_attempts_compared=sum(map(len,attempts.values())),maximum_numeric_difference=maxerr)
 save(REVIEW/'fixed-path-results.json',result);print(json.dumps(result,default=str))
if __name__=='__main__':
 try:run()
 except Exception as e:
  import traceback
  save(REVIEW/'fixed-comparison-failed-attempt.json',dict(error=repr(e),traceback=traceback.format_exc()));raise
