"""Independent Decimal ledger from source bars/actions/funding/trades; never imports engine."""
from pathlib import Path
from decimal import Decimal as D, getcontext, ROUND_FLOOR
from datetime import date, timedelta, datetime, timezone
from collections import defaultdict
from bisect import bisect_left
import csv, json, hashlib, shutil, sys
getcontext().prec=40
BASE=Path(__file__).resolve().parent; ROOT=BASE.parent; EIGHTH=ROOT.parent/"research-eighth-2026-09-08"
CONFIGS=["A20E","A20J","A60E","A60J","A120E","A120J","C1","C2","C3","D","REF_BREAKOUT","REF_ROAD"]
ZERO=D(0); FEE=D('.001'); TOL=D('.00001')
def num(x):return D(str(x))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jload(p):return json.loads(p.read_text())
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n')
def readcsv(p):return list(csv.DictReader(p.open()))
def writecsv(p,rows):
 if not rows:p.write_text('');return
 fields=list(dict.fromkeys(k for row in rows for k in row))
 with p.open('w') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def freeze():
 target=BASE/'accepted';assert not target.exists(),'Accepted evidence exists; do not overwrite.'
 required=[ROOT/'account-results'/cfg/f for cfg in CONFIGS for f in ['daily.csv','trades.csv','orders.json','events.json','roundtrips.json']]
 required += [ROOT/'account-results'/f for f in ['candidates.json','summary.json','completion.json']]
 assert all(p.exists() for p in required),'Account outputs not ready'
 pairs=[(p,p.relative_to(ROOT)) for p in (ROOT/'account-results').rglob('*') if p.is_file()]
 pairs += [(ROOT/f,Path(f)) for f in ['configurations.json','initial-lock.json']]
 pairs += [(EIGHTH/'candidate-study/candidates.json.gz',Path('original-eighth-candidates.json.gz')),(ROOT.parent/'research-eleventh-2026-09-08/history-diagnostic/raw-events.json.gz',Path('original-eleventh-events.json.gz'))]
 pairs += [(ROOT/'protocol.md',Path('protocol.md'))]
 pairs += [(p,p.relative_to(ROOT)) for p in ROOT.glob('*.py')]
 for folder in ['adapter','cash-engine']:
  pairs += [(p,p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 pairs += [(p,Path('product-qualification')/p.relative_to(EIGHTH/'product-qualification')) for p in (EIGHTH/'product-qualification').glob('*.json')]
 pairs += [(p,Path('product-qualification')/p.relative_to(EIGHTH/'product-qualification')) for p in (EIGHTH/'product-qualification/bars-helper-native').glob('*.csv')]
 manifest=[]
 for source,rel in pairs:
  dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);data=source.read_bytes();dest.write_bytes(data)
  manifest.append(dict(source=str(source.resolve()),file=str(rel),sha256=sha(source),bytes=len(data)))
 save(BASE/'accepted-inputs.json',dict(accepted_at_utc=datetime.now(timezone.utc).isoformat(),files=manifest))

def run():
 snap=BASE/'accepted';lock=jload(BASE/'accepted-inputs.json')
 for x in lock['files']:assert sha(snap/x['file'])==x['sha256']
 product=snap/'product-qualification';params=jload(product/'execution-parameters.json');symbols=sorted(params['symbols'])
 bars={s:{r['date']:r for r in readcsv(product/'bars-helper-native'/f'{s}-nominal.csv')} for s in symbols}
 dates={s:sorted(v) for s,v in bars.items()};actions=jload(product/'actions.json')
 start,end=map(date.fromisoformat,params['research_window']);days=[];d=start
 while d<=end:days.append(str(d));d+=timedelta(days=1)
 candidate_rows=jload(snap/'account-results/candidates.json'); candidates={r['candidate_id']:r for r in candidate_rows}; assert len(candidates)==len(candidate_rows)
 summary=[];all_diffs=[];execution_issues=[];all_trip_checks=[];all_event_checks=[]
 def add_issue(config,kind,**kw):execution_issues.append(dict(config=config,kind=kind,**kw))
 def levels(c,day):
  values={f:num(c[f]) if c.get(f) else None for f in ('stop','target','upper')}
  for a in sorted(actions,key=lambda a:(a['effective_date'],a['event_id'])):
   if a['symbol']!=c['symbol'] or not c['signal_date']<a['effective_date']<=day or a['announcement_date']>=day:continue
   if a['type']=='split':factor=1/num(a['ratio'])
   else:
    idx=bisect_left(dates[c['symbol']],a['effective_date'])-1;ref=num(bars[c['symbol']][dates[c['symbol']][idx]]['close']);factor=(ref-num(a['cash']))/ref
   values={f:v*factor if v is not None else None for f,v in values.items()}
  return values
 for config in CONFIGS:
  folder=snap/'account-results'/config;reported=readcsv(folder/'daily.csv');trades=readcsv(folder/'trades.csv');orders=jload(folder/'orders.json');event_report=jload(folder/'events.json');trip_report=jload(folder/'roundtrips.json')
  assert [r['date'] for r in reported]==days,(config,'daily date coverage')
  by_day=defaultdict(list)
  for t in trades:by_day[t['date']].append(t)
  cash={s:ZERO for s in symbols};qty={s:ZERO for s in symbols};fees={s:ZERO for s in symbols};funding={s:ZERO for s in symbols};prev_wealth={s:ZERO for s in symbols}
  mark={};mark_date={};active={s:None for s in symbols};trips={};rights={};receivables={};records=[];expected_events=[];account_units=ZERO;nav=D(1);peak=D(1);maxerr=ZERO;numeric_comparisons=0;text_comparisons=0
  for s in symbols:
   before=max(x for x in bars[s] if x<str(start));mark[s]=num(bars[s][before]['close']);mark_date[s]=before
  def rec(s):return sum((a['amount'] for a in receivables.values() if a['symbol']==s),ZERO)
  for day,row_main in zip(days,reported):
   day_prior_wealth=prev_wealth.copy();reference=mark.copy()
   for a in sorted(actions,key=lambda a:(a['effective_date'],a['event_id'])):
    s=a['symbol'];eid=a['event_id']
    if a['effective_date']==day:
     if a['type']=='split':
      old=qty[s];qty[s]*=num(a['ratio']);mark[s]/=num(a['ratio']);reference[s]/=num(a['ratio'])
      expected_events.append(dict(date=day,kind='split',symbol=s,event_id=eid,old_shares=old,new_shares=qty[s],factor=1/num(a['ratio']),amount=ZERO))
     else:
      mark[s]-=num(a['cash']);reference[s]-=num(a['cash']);entitlement=rights.get(eid,dict(shares=ZERO,position_id=None));money=entitlement['shares']*num(a['cash']);pid=entitlement['position_id'];receivables[eid]=dict(amount=money,symbol=s,position_id=pid)
      if pid:trips[pid]['dividend_accrued']+=money
      expected_events.append(dict(date=day,kind='dividend_receivable',symbol=s,event_id=eid,amount=money,entitled_shares=entitlement['shares'],position_id=pid))
    if a['type']=='cash_dividend' and a['pay_date']==day:
     owed=receivables.pop(eid,dict(amount=ZERO,position_id=None));cash[s]+=owed['amount']
     if owed['position_id']:trips[owed['position_id']]['dividend_paid']+=owed['amount']
     expected_events.append(dict(date=day,kind='dividend_paid',symbol=s,event_id=eid,amount=owed['amount']))
   deposit=D(1000) if date.fromisoformat(day).weekday()==0 else ZERO
   if deposit:
    account_units+=deposit/nav
    for s in symbols:cash[s]+=D(250);funding[s]+=D(250)
    expected_events.append(dict(date=day,kind='deposit',symbol='all',amount=deposit))
   available={}
   for s in symbols:
    limit=D('.2') if s=='sz159915' and day>='2020-08-24' else D('.1')
    available[s]=(day in bars[s] and day not in params['blocked_dates'][s] and abs(num(bars[s][day]['open'])-reference[s])<reference[s]*limit-D('.00051'))
   actual=by_day.get(day,[]);bought_today=set();sold_today=set();passive_cash_before=cash.copy()
   if any(t['side']=='sell' for t in actual) and any(t['side']=='buy' for t in actual):
    sides=[t['side'] for t in actual];assert sides==sorted(sides,key=lambda x:0 if x=='sell' else 1),(config,day,'sales after buys')
   for t in actual:
    s=t['symbol'];q=num(t['shares']);px=num(t['price']);notional=q*px;cost=notional*FEE;pid=t['position_id']
    assert available[s],(config,day,s,'filled when blocked or at limit')
    assert px==num(bars[s][day]['open']),(config,day,'not nominal open')
    assert abs(num(t['notional'])-notional)<TOL and abs(num(t['fee'])-cost)<TOL
    if t['side']=='buy':
     assert q>0 and q%D(100)==0 and s not in sold_today
     cash_qty=(cash[s]/(px*(1+FEE))/100).to_integral_value(rounding=ROUND_FLOOR)*100
     expected_qty=cash_qty
     if config!='P6':
      assert qty[s]==0 and active[s] is None
      c=candidates[t['candidate_id']];assert c['signal_date']<day and c['signal_accepted'] is True
      values=levels(c,day)
      for field in ('stop','target'):
       assert values[field] is not None and abs(num(t[field])-values[field])<TOL,(config,day,'level',field)
      assert px>values['stop']>0 and (values['target']-px)/(px-values['stop'])>=D(3)-D('1e-10')
      assert num(c['signal_ref'])>num(c['stop'])>0
      assert (num(c['target'])-num(c['signal_ref']))/(num(c['signal_ref'])-num(c['stop']))>=D(3)-D('1e-10')
      if config in CONFIGS:
       risk=day_prior_wealth[s]*D('.01');assert abs(num(t['risk_budget'])-risk)<TOL
       expected_qty=min(cash_qty,(risk/(px-values['stop'])/100).to_integral_value(rounding=ROUND_FLOOR)*100)
      assert abs(num(t['previous_product_equity'])-day_prior_wealth[s])<TOL
     assert q==expected_qty,(config,day,'buy quantity',q,expected_qty)
     if pid not in trips:
      assert active[s] is None
      trips[pid]=dict(position_id=pid,symbol=s,entry_date=day,entry_notional=ZERO,buy_fee=ZERO,sell_fee=ZERO,exit_notional=ZERO,dividend_accrued=ZERO,dividend_paid=ZERO,closed=False,exit_date=None,entry_price=px)
     else:assert config=='P6' and active[s]==pid
     trips[pid]['entry_notional']+=notional;trips[pid]['buy_fee']+=cost;active[s]=pid;cash[s]-=notional+cost;qty[s]+=q;bought_today.add(s)
    else:
     assert t['side']=='sell' and config!='P6' and q==qty[s] and active[s]==pid and s not in bought_today
     assert trips[pid]['entry_date']<day
     cash[s]+=notional-cost;qty[s]=ZERO;active[s]=None;sold_today.add(s);trips[pid].update(closed=True,exit_date=day,exit_notional=notional,sell_fee=cost)
    fees[s]+=cost;assert cash[s]>=-TOL
   if config=='P6':
    for s in symbols:
     expected_q=(passive_cash_before[s]/(num(bars[s][day]['open'])*(1+FEE))/100).to_integral_value(rounding=ROUND_FLOOR)*100 if available[s] else ZERO
     bought=sum((num(t['shares']) for t in actual if t['symbol']==s and t['side']=='buy'),ZERO)
     assert bought==expected_q,(day,s,'passive missed/additional buy',bought,expected_q)
   for s in symbols:
    if day in bars[s]:mark[s]=num(bars[s][day]['close']);mark_date[s]=day
   for a in actions:
    if a['type']=='cash_dividend' and a['record_date']==day:
     s=a['symbol'];rights[a['event_id']]=dict(shares=qty[s],position_id=active[s]);expected_events.append(dict(date=day,kind='dividend_recorded',symbol=s,event_id=a['event_id'],shares=qty[s],position_id=active[s]))
   total_cash=sum(cash.values());assets=sum(qty[s]*mark[s] for s in symbols);ar=sum((x['amount'] for x in receivables.values()),ZERO);wealth=total_cash+assets+ar
   if account_units:nav=wealth/account_units
   peak=max(peak,nav)
   row=dict(date=day,config_id=config,equity=wealth,assets=assets,cash=total_cash,receivable=ar,total_funding=sum(funding.values()),deposit=deposit,account_units=account_units,nav=nav,drawdown=nav/peak-1,fees=sum(fees.values()),stale_symbols=','.join(s for s in symbols if mark_date[s]!=day),accounting_difference=wealth-assets-total_cash-ar)
   for s in symbols:
    prev_wealth[s]=cash[s]+qty[s]*mark[s]+rec(s)
    row.update({f'units_{s}':qty[s],f'cash_{s}':cash[s],f'mark_{s}':mark[s],f'mark_date_{s}':mark_date[s],f'receivable_{s}':rec(s),f'equity_{s}':prev_wealth[s],f'previous_equity_{s}':day_prior_wealth[s],f'funding_{s}':funding[s],f'fees_{s}':fees[s]})
   for key,value in row.items():
    if isinstance(value,D):
     numeric_comparisons+=1
     difference=num(row_main[key])-value;maxerr=max(maxerr,abs(difference))
     if abs(difference)>TOL:all_diffs.append(dict(config=config,date=day,field=key,reported=row_main[key],independent=value,difference=difference))
    elif str(value)!=row_main[key]:all_diffs.append(dict(config=config,date=day,field=key,reported=row_main[key],independent=value,difference='text mismatch'))
   row['maximum_numeric_difference']=max(abs(num(row_main[k])-v) for k,v in row.items() if isinstance(v,D));records.append(row)
  # Compare event identities and all independently calculated financial fields.
  def ek(e):return (e['date'],e['kind'],e.get('symbol'),e.get('event_id'))
  expected_by={ek(e):e for e in expected_events};actual_by={ek(e):e for e in event_report};assert set(expected_by)==set(actual_by),(config,'event identities')
  for key,expected in expected_by.items():
   actual=actual_by[key];diff=ZERO
   for field,value in expected.items():
    if isinstance(value,D):diff=max(diff,abs(num(actual[field])-value))
    else:assert actual[field]==value,(config,'event attribution',key,field)
   all_event_checks.append(dict(config=config,date=key[0],kind=key[1],symbol=key[2],event_id=key[3],max_numeric_difference=diff));assert diff<TOL
  assert set(trips)=={r['position_id'] for r in trip_report}
  for reported_trip in trip_report:
   pid=reported_trip['position_id'];t=trips[pid];s=t['symbol'];t['shares']=ZERO if t['closed'] else qty[s];t['market_value']=t['shares']*mark[s];t['valuation_date']=t['exit_date'] if t['closed'] else mark_date[s]
   t['net_pnl']=t['exit_notional']+t['market_value']+t['dividend_accrued']-t['entry_notional']-t['buy_fee']-t['sell_fee'];t['net_return']=t['net_pnl']/(t['entry_notional']+t['buy_fee'])
   diff=ZERO
   for field,value in t.items():
    if isinstance(value,D):diff=max(diff,abs(num(reported_trip[field])-value))
    else:assert reported_trip[field]==value,(config,pid,field,reported_trip[field],value)
   assert diff<TOL,(config,pid,'roundtrip amount');all_trip_checks.append(dict(config=config,**t,max_numeric_difference=diff))
  out=BASE/'reconciliation'/config;out.mkdir(parents=True,exist_ok=True);writecsv(out/'daily-independent.csv',records)
  summary.append(dict(config=config,days=len(records),numeric_daily_fields_checked=numeric_comparisons,trades=len(trades),events=len(expected_events),roundtrips=len(trips),open_positions=sum(not t['closed'] for t in trips.values()),last_equity=wealth,last_cash=total_cash,last_receivable=ar,total_funding=sum(funding.values()),fees=sum(fees.values()),last_nav=nav,max_drawdown=min(r['drawdown'] for r in records),max_numeric_difference=maxerr,excess_tolerance_differences=sum(x['config']==config for x in all_diffs)))
 writecsv(BASE/'field-differences.csv',all_diffs);writecsv(BASE/'roundtrips-independent.csv',all_trip_checks);writecsv(BASE/'events-reconciliation.csv',all_event_checks)
 save(BASE/'results.json',dict(status='passed' if not all_diffs else 'failed',tolerance_currency_and_numeric=TOL,configurations=summary,field_differences=len(all_diffs),execution_issues=execution_issues,not_reviewed='candidate generation and order/exit verification are separate from this ledger check'))
 save(BASE/'input-integrity-after.json',dict(files=len(lock['files']),all_unchanged=all(sha(Path(x['source']))==x['sha256'] and sha(snap/x['file'])==x['sha256'] for x in lock['files'])))
 assert jload(BASE/'input-integrity-after.json')['all_unchanged'],'Accepted source changed during review'
 print(json.dumps({'status':'passed' if not all_diffs else 'failed','configs':len(summary),'days':sum(x['days'] for x in summary),'trades':sum(x['trades'] for x in summary),'field_differences':len(all_diffs)},ensure_ascii=False))
 if all_diffs:raise SystemExit(1)

if __name__=='__main__':
 if '--freeze' in sys.argv:freeze()
 try:run()
 except Exception as e:
  import traceback
  save(BASE/'failed-attempt.json',dict(at=datetime.now(timezone.utc).isoformat(),error=repr(e),traceback=traceback.format_exc()));raise
