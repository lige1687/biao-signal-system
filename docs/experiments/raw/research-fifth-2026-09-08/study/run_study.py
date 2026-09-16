from pathlib import Path
from datetime import datetime,timezone,date
import json,csv,math,hashlib
from cash_engine import simulate
P=Path(__file__).resolve().parent;OLD=P.parent.parent/'research-fourth-2026-09-08'

def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def csvout(p,rows):
 if not rows:return
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def drawdown(values,dates):
 peak=values[0];peakday=dates[0];worst=0;worstpeak=peakday;trough=peakday
 for v,d in zip(values,dates):
  if v>=peak:peak=v;peakday=d
  dd=1-v/peak
  if dd>worst:worst=dd;worstpeak=peakday;trough=d
 peakvalue=values[dates.index(worstpeak)]
 recover=next((d for v,d in zip(values,dates) if d>trough and v>=peakvalue),None) if worst else worstpeak
 until=recover or dates[-1]
 return dict(max_drawdown=worst,peak_date=worstpeak,trough_date=trough,recovery_date=recover,days_peak_to_recovery_or_end=(date.fromisoformat(until)-date.fromisoformat(worstpeak)).days)
def xirr(flows,final,end):
 origin=date.fromisoformat(flows[0]['date']);cash=[(-f['amount'],(date.fromisoformat(f['date'])-origin).days/365.25) for f in flows]+[(final,(date.fromisoformat(end)-origin).days/365.25)]
 def f(rate):return sum(amt/(1+rate)**t for amt,t in cash)
 lo,hi=-.9999,100.0
 assert f(lo)*f(hi)<0,'Could not bracket cashflow return'
 for _ in range(180):
  mid=(lo+hi)/2
  if f(mid)>0:lo=mid
  else:hi=mid
 return (lo+hi)/2

def summarize(r,fee,start):
 ds=[d for d in r['daily'] if d['total_funding']>0];last=ds[-1];tr=r['trades'];nav=[1]+[d['nav'] for d in ds];dates=[start]+[d['date'] for d in ds]
 out=dict(contributed=last['total_funding'],final_equity=last['equity'],profit=last['equity']-last['total_funding'],final_cash=last['cash'],final_receivable=last['receivable'],final_holdings_value=last['assets'],hypothetical_net_liquidation=last['equity']-last['assets']*fee,fees=sum(t['fee'] for t in tr),buy_count=sum(t['side']=='buy' for t in tr),sell_count=sum(t['side']=='sell' for t in tr),contribution_count=len(r['flows']),dividends_received=sum(e['amount'] for e in r['events'] if e['kind']=='dividend_paid'),cash_interest=sum(d['interest'] for d in ds),worst_loss_vs_contributions=max(0,max(1-d['equity']/d['total_funding'] for d in ds)),mean_cash_fraction=sum(d['cash']/d['equity'] for d in ds)/len(ds),nav_total_return=last['nav']-1,cashflow_annual_return=xirr(r['flows'],last['equity'],last['date']),rebalance_count=sum(e['kind']=='rebalance' for e in r['events']),limit_deferrals=sum(e.get('reason')=='at_open_limit_conservative' for e in r['events']),known_open_deferrals=sum(e.get('reason')=='known_open_unavailable' for e in r['events']))
 out.update(drawdown(nav,dates));return out

def main():
 protocol=json.loads((P/'protocol-lock.json').read_text());assert sha(P/'protocol.md')==protocol['sha256']
 qual=json.loads((P/'qualification.json').read_text());assert qual['qualified_for_bounded_research'];start,end=qual['window']
 for f in qual['sources']:assert sha(Path(f['path']))==f['sha256']
 for f in qual['pdf_checks']:assert sha(Path(f['path']))==f['sha256']
 prices={s:{r['date']:{k:float(r[k]) for k in ('open','close')} for r in read(OLD/'prices'/f'{s}-nominal.csv')} for s in ['sh510300','sz159915','sh518880','sh513100']}
 ev=[dict(e,symbol='sh510300') for e in json.loads((OLD/'events/510300/events.json').read_text())['events']]
 ev.append(dict(symbol='sh513100',type='split',event_id='513100-split-2022-01-13',record_date='2022-01-12',ex_date='2022-01-13',ratio=5))
 # Cash events earlier than each window never add holdings or entitlements; accounts start empty.
 changes={'sz159915':[('2020-08-24',.2)]};blocked={'sz159915':['2021-02-08','2021-02-09'],'sh513100':['2022-01-13']}
 scenarios=[('base',1000,.001,0),('budget10000',10000,.001,0),('fee1',1000,.0001,0),('cash2',1000,.001,.02)]
 windows=[('full',start,end,scenarios)]
 for key,a,b in [('early',start,'2019-12-31'),('middle','2020-01-01','2022-12-31'),('recent','2023-01-01',end)]:
  if start<=a<=b<=end:windows.append((key,a,b,scenarios[:1]))
 lock=dict(at=datetime.now(timezone.utc).isoformat(),window=[start,end],protocol_sha256=protocol['sha256'],protocol_frozen_at=protocol['at'],qualification_sha256=sha(P/'qualification.json'),engine_sha256=sha(P/'cash_engine.py'),runner_sha256=sha(Path(__file__)),planned_runs=sum(len(w[3])*3 for w in windows),windows=[dict(id=k,start=a,end=b,scenarios=[s[0] for s in sc]) for k,a,b,sc in windows],limit_changes=changes,blocked_dates=blocked,events=ev)
 assert lock['planned_runs']<=21
 dump(P/'run-lock.json',lock)
 summary=[]
 for win,a,b,scenarios in windows:
  for scenario,weekly,fee,cash_rate in scenarios:
   flows=None
   for arm in ('quarterly','hold','single'):
    subset={s:q for s,q in prices.items() if arm!='single' or s=='sh510300'}
    r=simulate(subset,ev,start=a,end=b,weekly=weekly,fee=fee,cash_rate=cash_rate,rebalance=arm=='quarterly',limits={s:.1 for s in subset},limit_changes=changes,blocked_dates=blocked)
    if flows is None:flows=r['flows']
    else:assert flows==r['flows']
    folder=P/'results'/f'{win}-{scenario}-{arm}';folder.mkdir(parents=True,exist_ok=True)
    for key in ['daily','trades','flows']:csvout(folder/f'{key}.csv',r[key])
    dump(folder/'events.json',r['events'])
    summary.append(dict(window=win,start=a,end=b,scenario=scenario,arm=arm,weekly=weekly,fee=fee,cash_rate=cash_rate,**summarize(r,fee,a)))
 dump(P/'summary.json',summary);csvout(P/'summary.csv',summary)
 print(json.dumps(summary[:3],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
