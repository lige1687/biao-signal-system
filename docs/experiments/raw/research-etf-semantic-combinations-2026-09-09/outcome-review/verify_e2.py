"""Independent exit and cash-result checks; does not import the execution engine."""
from pathlib import Path
from decimal import Decimal as D
import csv,gzip,json,hashlib

HERE=Path(__file__).resolve().parent; BATCH=HERE.parent; EX=BATCH/'execution'; OUT=EX/'attempt-e2'; IN=EX/'inputs'; END='2026-06-30'
def jl(p):return json.loads(Path(p).read_text())
def rows(p):return list(csv.DictReader(Path(p).open()))
def dec(x):return D(str(x))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 lock=jl(HERE/'e2-review-lock.json')
 for p,h in lock['files'].items():
  if Path(p).resolve()!=Path(__file__).resolve():assert sha(p)==h,p
 revision=jl(HERE/'e2-revision-lock.json');assert sha(__file__)==revision['verifier']
 bars={}
 for s in ('sh510300','sz159915'):
  xs=rows(IN/f'bars/{s}-nominal.csv');bars[s]={x['date']:{k:dec(x[k]) for k in ('open','high','low','close')} for x in xs}
 actions=jl(IN/'actions.json'); actions_by={s:{} for s in bars}
 for a in actions:
  if a['symbol'] in bars:actions_by[a['symbol']].setdefault(a['effective_date'],[]).append(a)
 with gzip.open(IN/'exit-observations.json.gz','rt') as f:obs=json.load(f)
 cfg=jl(IN/'execution-config.json')

 def unavailable(s,day):
  if day in cfg['blocked_dates'][s]:return True
  if day not in bars[s]:return True
  earlier=[d for d in bars[s] if d<day]
  if not earlier:return True
  ref=bars[s][max(earlier)]['close']
  for a in actions_by[s].get(day,[]):
   if a['type']=='cash_dividend':ref-=dec(a['cash'])
   else:ref/=dec(a['ratio'])
  limit=dec(cfg['limits'][s])
  changes=cfg['limit_changes'][s]
  for effective,value in sorted(changes.items() if isinstance(changes,dict) else changes):
   if effective<=day:limit=dec(value)
  return abs(bars[s][day]['open']-ref)>=ref*limit-D('.00051')

 def check_folder(folder):
  trades=rows(folder/'trades.csv'); rts=jl(folder/'roundtrips.json');orders=jl(folder/'orders.json')
  out=[]
  for rt in rts:
   ts=[t for t in trades if t['position_id']==rt['position_id']];buy=next(t for t in ts if t['side']=='buy');sell=next((t for t in ts if t['side']=='sell'),None)
   s=rt['symbol'];entry=rt['entry_date'];fee=dec(buy['fee'])/dec(buy['notional']);shares=dec(buy['shares']);stop=dec(buy['stop']);target=dec(buy['target'])
   candidate=next(o for o in orders if o['side']=='buy' and o.get('candidate_id')==rt['candidate_id'])
   assert entry>candidate['signal_date'] and dec(buy['price'])==bars[s][entry]['open']
   first_entry=next(d for d in sorted(bars[s]) if d>candidate['signal_date'] and not unavailable(s,d))
   assert entry==first_entry
   expected_reason=expected_signal=None;div=D(0);entry_black=False;seen_green=False;seen_green_date=None
   for day in sorted(d for d in bars[s] if entry<=d<=END):
    for a in sorted(actions_by[s].get(day,[]),key=lambda x:x['event_id']):
     if a['type']=='cash_dividend':
      amount=dec(a['cash']); prior=max(d for d in bars[s] if d<day);factor=(bars[s][prior]['close']-amount)/bars[s][prior]['close'];stop*=factor;target*=factor
      if entry<=a['record_date'] and (sell is None or a['record_date']<sell['date']):div+=shares*amount
     else:
      ratio=dec(a['ratio']);shares*=ratio;stop/=ratio;target/=ratio
    close=bars[s][day]['close'];o=obs[s][day];black=close<dec(o['ema20']) and close<dec(o['cost20'])
    if day==entry:entry_black=black
    reason='structure_stop' if close<stop else ('known_target_reached' if close>=target else None)
    if reason is None:
     green=close>dec(o['ema20']) and close>dec(o['cost20'])
     if green:
      seen_green=True;seen_green_date=seen_green_date or day
     elif seen_green and black:reason='black_after_post_entry_green'
    if reason:
     expected_reason,expected_signal=reason,day;break
   sell_order=next((o for o in orders if o['side']=='sell' and o.get('position_id')==rt['position_id']),None)
   assert sell_order and sell_order['reason']==expected_reason and sell_order['signal_date']==expected_signal
   first_exit=next(d for d in sorted(bars[s]) if d>expected_signal and not unavailable(s,d));assert sell and sell['date']==first_exit and dec(sell['price'])==bars[s][first_exit]['open']
   pnl=dec(sell['price'])*dec(sell['shares'])+div-dec(buy['price'])*dec(buy['shares'])-dec(buy['fee'])-dec(sell['fee'])
   ret=pnl/(dec(buy['notional'])+dec(buy['fee']))
   assert abs(pnl-dec(rt['net_pnl']))<D('1e-8') and abs(ret-dec(rt['net_return']))<D('1e-12') and abs(div-dec(rt['dividend_accrued']))<D('1e-8')
   out.append({'folder':folder.name,'candidate_id':rt['candidate_id'],'entry_date':entry,'entry_close_black':entry_black,'seen_green_before_exit':seen_green,'first_seen_green_date':seen_green_date,'exit_signal_on_entry_day':expected_signal==entry,'exit_signal_date':expected_signal,'exit_reason':expected_reason,'exit_date':sell['date'],'dividend':float(div),'net_pnl':float(pnl),'net_return':float(ret)})
  return out

 account=[]
 for folder in sorted((OUT/'accounts').iterdir()):
  if jl(folder/'roundtrips.json'):account+=check_folder(folder)
 fixed=[];not_entered=[]
 for folder in sorted((OUT/'fixed-opportunities').iterdir()):
  if jl(folder/'roundtrips.json'):fixed+=check_folder(folder)
  else:
   os=jl(folder/'orders.json');buy=next(o for o in os if o['side']=='buy');assert buy['status']=='rejected';not_entered.append({'folder':folder.name,'reason':buy['reason']})
 result={'status':'passed','coverage':{'nonempty_complete_account_positions':len(account),'entered_fixed_paths':len(fixed),'not_entered_fixed_paths':len(not_entered)},'reason_counts':{},'entry_black':{'complete_positions':sum(x['entry_close_black'] for x in account),'complete_entry_day_exit_signals':sum(x['exit_signal_on_entry_day'] for x in account),'fixed_paths':sum(x['entry_close_black'] for x in fixed),'fixed_entry_day_exit_signals':sum(x['exit_signal_on_entry_day'] for x in fixed)},'maximum_tolerances':{'pnl':'1e-8','net_return':'1e-12','dividend':'1e-8'},'checks':{'entry_first_allowed_open':True,'exit_signal_priority_structure_then_target_then_post_entry_green_then_black':True,'exit_first_allowed_open_after_signal':True,'corporate_action_levels_and_dividend':True,'actual_price_shares_fees_net_return':True},'complete_positions':account,'fixed_paths':fixed,'not_entered':not_entered}
 from collections import Counter
 result['reason_counts']={'complete':dict(Counter(x['exit_reason'] for x in account)),'fixed':dict(Counter(x['exit_reason'] for x in fixed)),'fixed_not_entered':dict(Counter(x['reason'] for x in not_entered))}
 (HERE/'e2-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 for p,h in lock['files'].items():
  if Path(p).resolve()!=Path(__file__).resolve():assert sha(p)==h,p
 assert sha(__file__)==revision['verifier']
if __name__=='__main__':main()
