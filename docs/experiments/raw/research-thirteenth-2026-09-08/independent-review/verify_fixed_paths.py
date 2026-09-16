"""New independent Decimal paths for every original actual A entry; no re-entry.
Start with original purchase outlay, buy fixed original quantity, keep sale proceeds at zero interest.
"""
from verify_accounts import *
import gzip

def run_fixed_paths():
 fixed_snap=REVIEW/'fixed-inputs'
 if not fixed_snap.exists():
  fixed_snap.mkdir()
  pairs=[];old=ROOT.parent/'research-twelfth-2026-09-08/precision-account-results'
  for cfg in CONFIGS:
   for f in ('trades.csv','roundtrips.json'):pairs.append((old/cfg/f,Path('twelfth-baseline')/cfg/f))
  for p in (REVIEW/'observation-inputs').glob('*'):
   if p.name in ('actions.json','execution-parameters.json'):pairs.append((p,Path('product-qualification')/p.name))
   elif p.suffix=='.csv':pairs.append((p,Path('product-qualification/bars-helper-native')/p.name))
  manifest=[]
  for source,rel in pairs:
   dest=fixed_snap/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
   manifest.append(dict(source=str(source.resolve()),file=str(rel),sha256=sha(source)))
  save(REVIEW/'fixed-inputs-lock.json',manifest)
 lock=jload(REVIEW/'fixed-inputs-lock.json')
 assert all(sha(Path(x['source']))==sha(fixed_snap/x['file'])==x['sha256'] for x in lock)
 params=jload(fixed_snap/'product-qualification/execution-parameters.json');end=params['research_window'][1]
 actions=sorted(jload(fixed_snap/'product-qualification/actions.json'),key=lambda a:(a['effective_date'],a['event_id']))
 road=json.load(gzip.open(REVIEW/'observations-independent.json.gz','rt'))
 bars={s:{r['date']:r for r in readcsv(fixed_snap/'product-qualification/bars-helper-native'/f'{s}-nominal.csv')} for s in params['symbols']}
 sources=[]
 for cfg in CONFIGS:
  f=fixed_snap/'twelfth-baseline'/cfg;trips=jload(f/'roundtrips.json');byid={p['position_id']:p for p in trips}
  for b in readcsv(f/'trades.csv'):
   if b['side']=='buy':sources.append((cfg,b,byid[b['position_id']]))
 assert len(sources)==17
 results=[];all_daily=[];all_attempts=[];checks=[]
 for cfg,b,original in sources:
  symbol=b['symbol'];quotes=bars[symbol];entry=b['date'];entry_q=num(b['shares']);entry_px=num(b['price']);outlay=entry_q*entry_px*(1+FEE)
  assert entry_px==num(quotes[entry]['open'])
  for variant in ('S','T'):
   qty=ZERO;cash=outlay;accrued=ZERO;paid=ZERO;rights={};receivables={};mark=num(quotes[max(d for d in quotes if d<entry)]['close']);mark_date=max(d for d in quotes if d<entry)
   stop=num(b['stop']);pending=None;first_reason=None;first_signal=None;exitday=None;sellfee=ZERO;sellnotional=ZERO
   d=date.fromisoformat(entry)
   while str(d)<=end:
    day=str(d);reference=mark
    for a in actions:
     if a['symbol']!=symbol:continue
     eid=a['event_id']
     if a['effective_date']==day:
      assert a['announcement_date']<day
      if a['type']=='split':
       ratio=num(a['ratio']);qty*=ratio;mark/=ratio;reference/=ratio
       if day>entry:stop/=ratio
      else:
       c=num(a['cash']);factor=(reference-c)/reference;mark-=c;reference-=c
       if day>entry:stop*=factor
       owed=rights.get(eid,ZERO)*c;receivables[eid]=owed;accrued+=owed
     if a['type']=='cash_dividend' and a['pay_date']==day:
      owed=receivables.pop(eid,ZERO);cash+=owed;paid+=owed
    def unavailable():
     if day in params['blocked_dates'][symbol]:return 'known_open_unavailable'
     if day not in quotes:return 'missing_quote'
     limit=num(params['limits'][symbol])
     for effective,value in params['limit_changes'].get(symbol,[]):
      if effective<=day:limit=num(value)
     if abs(num(quotes[day]['open'])-reference)>=reference*limit-D('.00051'):return 'at_open_limit_conservative'
     return None
    if pending is not None:
     assert day>pending
     why=unavailable();all_attempts.append(dict(config=cfg,position_id=b['position_id'],variant=variant,date=day,reason=why or 'filled'))
     if why is None:
      sellnotional=qty*num(quotes[day]['open']);sellfee=sellnotional*FEE;cash+=sellnotional-sellfee;qty=ZERO;exitday=day;pending=None
    if day==entry:
     assert unavailable() is None;qty=entry_q;cash-=outlay
    if day in quotes:mark=num(quotes[day]['close']);mark_date=day
    for a in actions:
     if a['symbol']==symbol and a['type']=='cash_dividend' and a['record_date']==day:rights[a['event_id']]=qty
    if qty and pending is None and day in quotes:
     structure=mark<stop;road_exit=road[symbol][day]['road_exit']
     reason='structure_stop' if structure else 'ema_cost_exit' if variant=='T' and road_exit else None
     if reason:pending=day;first_signal=day;first_reason=reason
    ar=sum(receivables.values(),ZERO);wealth=cash+qty*mark+ar
    all_daily.append(dict(config=cfg,position_id=b['position_id'],variant=variant,date=day,shares=qty,cash=cash,market_value=qty*mark,receivable=ar,wealth=wealth,net_pnl=wealth-outlay,stop=stop,first_exit_signal=first_signal,exit_date=exitday))
    d+=timedelta(days=1)
   row=dict(config=cfg,position_id=b['position_id'],candidate_id=b['candidate_id'],symbol=symbol,variant=variant,entry_date=entry,entry_price=entry_px,original_shares=entry_q,entry_notional=entry_q*entry_px,buy_fee=entry_q*entry_px*FEE,entry_outlay=outlay,first_exit_signal=first_signal,exit_reason=first_reason,exit_date=exitday,closed=bool(exitday),exit_notional=sellnotional,sell_fee=sellfee,dividend_accrued=accrued,dividend_paid=paid,shares=qty,market_value=qty*mark,cash=cash,receivable=ar,ending_wealth=wealth,net_pnl=wealth-outlay,net_return=(wealth-outlay)/outlay,valuation_date=exitday or mark_date)
   if variant=='S':
    for key in ('entry_notional','buy_fee','sell_fee','exit_notional','dividend_accrued','dividend_paid','shares','market_value','net_pnl','net_return'):
     diff=abs(num(original[key])-row[key]);checks.append(dict(config=cfg,position_id=b['position_id'],field=key,reported=original[key],independent=row[key],difference=diff));assert diff<TOL,(cfg,b['position_id'],key,diff)
    for key in ('exit_date','closed','entry_date','valuation_date'):assert original[key]==row[key],(cfg,b['position_id'],key)
   results.append(row)
 writecsv(REVIEW/'fixed-paths-independent.csv',results);writecsv(REVIEW/'fixed-daily-independent.csv',all_daily);writecsv(REVIEW/'fixed-attempts-independent.csv',all_attempts);writecsv(REVIEW/'fixed-baseline-checks.csv',checks)
 save(REVIEW/'fixed-paths-independent.json',results)
 save(REVIEW/'fixed-path-results.json',dict(status='independently_rebuilt_waiting_executor_comparison',original_entries=len(sources),paths=len(results),daily_rows=len(all_daily),baseline_numeric_checks=len(checks),S_net_pnl=sum(r['net_pnl'] for r in results if r['variant']=='S'),T_net_pnl=sum(r['net_pnl'] for r in results if r['variant']=='T'),new_code_scope='Entire fixed original-quantity holding and post-sale zero-interest cash path; initial stop and road observations use independently rebuilt values; no account engine imported.'))
 print('Original 17 entries independently rebuilt:',len(all_daily),'daily paths; baseline numeric checks',len(checks))
if __name__=='__main__':run_fixed_paths()
