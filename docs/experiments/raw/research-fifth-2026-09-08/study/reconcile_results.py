"""Independent ledger reconstruction, using original prices and action definitions."""
from pathlib import Path
import csv,json,math
from collections import defaultdict
from datetime import date,timedelta
P=Path(__file__).resolve().parent;OLD=P.parent.parent/'research-fourth-2026-09-08'
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def near(a,b,label):
 assert abs(a-b)<max(1e-6,abs(b)*1e-10),(label,a,b)
prices={s:{r['date']:r for r in read(OLD/'prices'/f'{s}-nominal.csv')} for s in ['sh510300','sz159915','sh518880','sh513100']}
events=json.loads((OLD/'events/510300/events.json').read_text())['events']
summary=json.loads((P/'summary.json').read_text());out=[];attributions=[];flow_signatures={}
for x in summary:
 key=f"{x['window']}-{x['scenario']}-{x['arm']}";folder=P/'results'/key
 ds=read(folder/'daily.csv');ts=read(folder/'trades.csv');fs=read(folder/'flows.csv')
 syms=[k[6:] for k in ds[0] if k.startswith('units_')];tx=defaultdict(list)
 for t in ts:tx[t['date']].append(t)
 cash=0;hold={s:0 for s in syms};mark={s:float(prices[s][max(d for d in prices[s] if d<x['start'])]['close']) for s in syms};rights={};recv=0;fundunits=0;nav=1;peak=1;mdd=0;dividends=0;paid_by_symbol=defaultdict(float)
 flow={f['date']:float(f['amount']) for f in fs};expected={};day=date.fromisoformat(x['start'])
 while day<=date.fromisoformat(x['end']):
  if day.weekday()==0:expected[day.isoformat()]=x['weekly']
  day+=timedelta(days=1)
 assert flow==expected and len(flow)==len(fs)
 group=(x['window'],x['scenario']);signature=list(flow.items())
 if group in flow_signatures:assert signature==flow_signatures[group]
 else:flow_signatures[group]=signature
 for row in ds:
  d=row['date'];priorhold=hold.copy()
  if d=='2022-01-13' and 'sh513100' in syms:
   hold['sh513100']*=5;priorhold['sh513100']*=5;mark['sh513100']/=5
  for e in events if 'sh510300' in syms else []:
   if d==e['ex_date']:
    recv+=rights.get(e['event_id'],0)*e['cash_per_share'];mark['sh510300']-=e['cash_per_share']
   if d==e['pay_date']:
    amount=rights.get(e['event_id'],0)*e['cash_per_share'];cash+=amount;recv-=amount;dividends+=amount;paid_by_symbol['sh510300']+=amount
  incoming=flow.get(d,0);cash+=incoming;fundunits+=incoming/nav;sides=defaultdict(set)
  for t in tx[d]:
   s=t['symbol'];qty=int(t['shares']);px=float(t['price']);fee=float(t['fee']);side=t['side'];sides[s].add(side)
   assert qty>0 and qty%100==0;assert d in prices[s]
   near(px,float(prices[s][d]['open']),'open price');near(fee,qty*px*x['fee'],'fee')
   assert not (s=='sz159915' and d in ['2021-02-08','2021-02-09'])
   assert not (s=='sh513100' and d=='2022-01-13')
   limit=.2 if s=='sz159915' and d>='2020-08-24' else .1
   assert abs(px-mark[s])<mark[s]*limit-.00051
   if side=='buy':hold[s]+=qty;cash-=qty*px+fee
   else:
    assert qty<=priorhold[s];hold[s]-=qty;cash+=qty*px-fee
   assert cash>=-1e-7 and hold[s]>=0
  assert all(len(v)==1 for v in sides.values())
  interest=cash*((1+x['cash_rate'])**(1/365)-1);near(interest,float(row['interest']),'interest');cash+=interest
  for e in events if 'sh510300' in syms else []:
   if d==e['record_date']:rights[e['event_id']]=hold['sh510300']
  for s in syms:
   if d in prices[s]:mark[s]=float(prices[s][d]['close'])
   near(mark[s],float(row['mark_'+s]),'mark');near(hold[s],float(row['units_'+s]),'units')
  eq=cash+recv+sum(hold[s]*mark[s] for s in syms)
  if fundunits:nav=eq/fundunits
  near(eq,float(row['equity']),'equity');near(cash,float(row['cash']),'cash');near(recv,float(row['receivable']),'receivable');near(nav,float(row['nav']),'nav')
  peak=max(peak,nav);mdd=max(mdd,1-nav/peak)
 near(eq,x['final_equity'],'final equity');near(dividends,x['dividends_received'],'dividends');near(mdd,x['max_drawdown'],'drawdown')
 # Independently check reported cashflow rate balances discounted paid-in money and final marked assets.
 rate=x['cashflow_annual_return'];origin=date.fromisoformat(fs[0]['date'])
 npv=sum(-float(f['amount'])/(1+rate)**((date.fromisoformat(f['date'])-origin).days/365.25) for f in fs)+eq/(1+rate)**((date.fromisoformat(x['end'])-origin).days/365.25)
 assert abs(npv)<1e-5
 profit=0
 for s in syms:
  st=[t for t in ts if t['symbol']==s];buy=sum(float(t['notional']) for t in st if t['side']=='buy');sell=sum(float(t['notional']) for t in st if t['side']=='sell');fees=sum(float(t['fee']) for t in st)
  pnl=hold[s]*mark[s]+sell-buy-fees+paid_by_symbol[s];profit+=pnl
  attributions.append(dict(run=key,symbol=s,bought=buy,sold=sell,fees=fees,dividends=paid_by_symbol[s],final_value=hold[s]*mark[s],net_profit=pnl))
 near(profit+x['cash_interest'],x['profit'],'profit attribution')
 out.append(dict(run=key,days=len(ds),trades=len(ts),all_balances_rebuilt=True,execution_dates_and_limits_checked=True,external_flows_checked=True,cashflow_return_equation_checked=True))
(P/'reconciliation.json').write_text(json.dumps(out,indent=2));(P/'fund-attribution.json').write_text(json.dumps(attributions,indent=2))
print(json.dumps(dict(runs=len(out),daily_records=sum(r['days'] for r in out),transactions=sum(r['trades'] for r in out),all_passed=True),indent=2))
