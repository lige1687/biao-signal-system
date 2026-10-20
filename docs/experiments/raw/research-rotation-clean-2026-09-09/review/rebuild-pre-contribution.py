"""Independent four-ETF rotation reconstruction. Never imports execution code."""
from __future__ import annotations
import csv,json,math,hashlib
from collections import defaultdict
from pathlib import Path
from datetime import date,timedelta
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; OUT=Path(__file__).resolve().parent
SYMS=['159915.SZ','510300.SH','512170.SH','512400.SH']
START=pd.Timestamp('2021-08-02'); END=pd.Timestamp('2026-06-30'); LOT=100
METHODS=['equal','momentum_top3','equal_sma200','momentum_top3_sma200']

def load():
 p=pd.read_csv(DATA/'prices.csv',parse_dates=['date']).sort_values(['date','symbol'])
 bars={s:g.set_index('date').sort_index() for s,g in p.groupby('symbol')}
 acts=json.loads((DATA/'actions.json').read_text())['events']
 return bars,acts

def economic_indices(bars,acts):
 """Causal total-return-like index; actions are applied only on/before each quote."""
 by=defaultdict(list)
 for a in acts: by[a['symbol']].append(a)
 out={}
 for s,d in bars.items():
  idx=[]; level=1.0; prev_date=None; prev_close=None
  for dt,row in d.iterrows():
   if prev_date is None: idx.append(level)
   else:
    ratio=1.0; units=1.0; cash=0.0
    for a in sorted(by[s],key=lambda x:x.get('effective_date') or x.get('ex_date') or '9999'):
     ed=a.get('effective_date') or a.get('ex_date')
     if ed and prev_date.date()<date.fromisoformat(ed)<=dt.date():
      if a['type']=='split': units*=float(a['split_ratio'])
      elif a['type']=='cash_dividend': cash+=units*float(a['cash_per_unit'])
    ratio=(units*float(row.close)+cash)/float(prev_close)
    level*=ratio; idx.append(level)
   prev_date=dt; prev_close=row.close
  out[s]=pd.Series(idx,index=d.index,name='economic_index')
 return out

def decisions(bars,econ):
 # Shanghai month completion = last union quote day in each month.
 union=sorted(set().union(*(set(x.index) for x in bars.values())))
 month_last={}
 for d in union:
  if d<=END: month_last[(d.year,d.month)]=d
 rows=[]
 for dt in month_last.values():
  if dt<pd.Timestamp('2021-07-30') or dt>=END: continue
  scores={}; trend={}; detail={}
  for s in SYMS:
   z=econ[s].loc[:dt]
   if len(z)>=253:
    score=float(z.iloc[-22]/z.iloc[-253]-1)
   else: score=None
   sma=float(z.iloc[-200:].mean()) if len(z)>=200 else None
   ok=sma is not None and float(z.iloc[-1])>=sma
   scores[s]=score; trend[s]=ok
   detail[s]={'bars_known':len(z),'latest_quote':str(z.index[-1].date()),'momentum_long_date':str(z.index[-253].date()) if len(z)>=253 else None,'momentum_skip_date':str(z.index[-22].date()) if len(z)>=253 else None,'score':score,'economic_index':float(z.iloc[-1]),'sma200':sma,'trend_ok':ok}
  ranked=sorted(SYMS,key=lambda s:(-(scores[s] if scores[s] is not None else -math.inf),s))
  for method in METHODS:
   chosen=SYMS if method.startswith('equal') else ranked[:3]
   base=1/len(chosen); weights={s:(base if s in chosen else 0.0) for s in SYMS}
   if method.endswith('_sma200'):
    weights={s:(w if trend[s] else 0.0) for s,w in weights.items()}
   rows.append({'decision_date':str(dt.date()),'method':method,'selected':chosen,'weights':weights,'details':detail})
 return rows

def blocked(a,s,dt):
 for x in a:
  if x['symbol']!=s or not x.get('halt'): continue
  h=x['halt']; ds=date.fromisoformat(h['start_date']); de=date.fromisoformat(h['end_date'])
  if ds<=dt.date()<=de and (h.get('blocks_open_buy') or h.get('blocks_open_sell')): return True
 return False

def simulate(method,fee,bars,acts,econ,decs):
 dates=[]; cur=START
 while cur<=END: dates.append(cur); cur+=pd.Timedelta(days=1)
 units={s:0.0 for s in SYMS}; cash=1_000_000.0; recv=[]; ent={}; last={}
 pending={}; pending_reason={}; daily=[]; trades=[]; events=[]
 decmap={pd.Timestamp(x['decision_date']):x for x in decs if x['method']==method}
 # decision at 2021-07-30 must be active at first open
 pre=max((d for d in decmap if d<START),default=None)
 if pre is not None:
  pending.update(decmap[pre]['weights']); pending_reason.update({s:'monthly' for s in SYMS})
 bydate=defaultdict(list)
 for a in acts:
  for k in ['record_date','ex_date','pay_date','effective_date']:
   if a.get(k): bydate[pd.Timestamp(a[k])].append((k,a))
 for dt in dates:
  # calendar actions; dedupe effective/ex for dividends by event step
  for k,a in bydate.get(dt,[]):
   s=a['symbol']
   if a['type']=='split' and k=='effective_date':
    units[s]*=float(a['split_ratio']); events.append({'date':str(dt.date()),'type':'split','symbol':s,'ratio':float(a['split_ratio'])})
   elif a['type']=='cash_dividend' and k=='record_date': ent[a['event_id']]=units[s]
   elif a['type']=='cash_dividend' and k=='ex_date':
    amt=ent.get(a['event_id'],0)*float(a['cash_per_unit']); recv.append([a['event_id'],s,pd.Timestamp(a['pay_date']),amt]); events.append({'date':str(dt.date()),'type':'receivable','symbol':s,'amount':amt})
  for r in list(recv):
   if r[2]==dt: cash+=r[3]; events.append({'date':str(dt.date()),'type':'dividend_cash','symbol':r[1],'amount':r[3]}); recv.remove(r)
  # execute all pending symbols having a valid, permitted open. Mark opening equity with opens where present.
  available=[s for s in SYMS if dt in bars[s].index and float(bars[s].loc[dt,'open'])>0 and float(bars[s].loc[dt,'volume'])>0 and not blocked(acts,s,dt)]
  if pending and available:
   marks={s:(float(bars[s].loc[dt,'open']) if s in available else last.get(s,0.0)) for s in SYMS}
   eq=cash+sum(units[s]*marks[s] for s in SYMS)+sum(r[3] for r in recv)
   todo=[s for s in available if s in pending]
   # sell first
   for s in sorted(todo):
    px=marks[s]; target=math.floor((pending[s]*eq/px)/LOT)*LOT
    if units[s]>target:
     qty=units[s]-target; value=qty*px; f=value*fee; cash+=value-f; units[s]-=qty
     trades.append({'date':str(dt.date()),'symbol':s,'side':'sell','units':qty,'price':px,'fee':f,'reason':pending_reason[s]})
   # desired buys, proportionally scale if cash insufficient
   wants={}
   for s in sorted(todo):
    px=marks[s]; target=math.floor((pending[s]*eq/px)/LOT)*LOT
    if target>units[s]: wants[s]=target-units[s]
   need=sum(q*marks[s]*(1+fee) for s,q in wants.items())
   scale=min(1.0,cash/need) if need else 1.0
   for s,q in wants.items():
    px=marks[s]; qty=math.floor(q*scale/LOT)*LOT; value=qty*px; f=value*fee
    if qty and value+f<=cash+1e-7:
     cash-=value+f; units[s]+=qty; trades.append({'date':str(dt.date()),'symbol':s,'side':'buy','units':qty,'price':px,'fee':f,'reason':pending_reason[s]})
   for s in todo: pending.pop(s,None); pending_reason.pop(s,None)
  # close marks and signals
  for s in SYMS:
   if dt in bars[s].index: last[s]=float(bars[s].loc[dt,'close'])
  if dt in decmap:
   pending.update(decmap[dt]['weights']); pending_reason.update({s:'monthly' for s in SYMS})
  if method.endswith('_sma200'):
   for s in SYMS:
    if units[s]>0 and dt in econ[s].index:
     z=econ[s].loc[:dt]
     if len(z)>=200 and float(z.iloc[-1])<float(z.iloc[-200:].mean()):
      pending[s]=0.0; pending_reason[s]='daily_sma200_exit'
  equity=cash+sum(units[s]*last.get(s,0) for s in SYMS)+sum(r[3] for r in recv)
  daily.append({'date':str(dt.date()),'cash':cash,'receivables':sum(r[3] for r in recv),'equity':equity,**{f'units_{s}':units[s] for s in SYMS},**{f'mark_{s}':last.get(s) for s in SYMS}})
 return daily,trades,events

def metrics(daily):
 d=pd.DataFrame(daily); e=d.equity.astype(float); peak=pd.concat([pd.Series([1_000_000.]),e],ignore_index=True).cummax().iloc[1:]
 dd=float((e.to_numpy()/peak.to_numpy()-1).min()); days=(pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days
 cagr=float((e.iloc[-1]/1_000_000)**(365.2425/days)-1)
 annual=[]
 d['year']=d.date.str[:4]
 prev=1_000_000
 for y,g in d.groupby('year'):
  end=float(g.equity.iloc[-1]); annual.append({'year':int(y),'return':end/prev-1,'end_equity':end}); prev=end
 return {'ending_equity':float(e.iloc[-1]),'total_return':float(e.iloc[-1]/1_000_000-1),'cagr':cagr,'max_drawdown':dd,'annual':annual}

def main():
 bars,acts=load(); econ=economic_indices(bars,acts); decs=decisions(bars,econ)
 (OUT/'independent-decisions.json').write_text(json.dumps(decs,ensure_ascii=False,indent=2)+'\n')
 sums=[]
 for method in METHODS:
  for fee in [.001,.002]:
   daily,trades,events=simulate(method,fee,bars,acts,econ,decs); key=f'{method}-fee{int(fee*10000)}bp'
   pd.DataFrame(daily).to_csv(OUT/f'{key}-daily.csv',index=False)
   pd.DataFrame(trades).to_csv(OUT/f'{key}-trades.csv',index=False)
   (OUT/f'{key}-events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
   sums.append({'account':key,'method':method,'fee':fee,'trade_count':len(trades),**metrics(daily)})
 (OUT/'independent-summary.json').write_text(json.dumps(sums,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__': main()
