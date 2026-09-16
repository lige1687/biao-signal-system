"""Independent signal reconstruction and ledger replay for frozen full pool."""
from pathlib import Path
from collections import defaultdict
import pandas as pd,numpy as np,json,hashlib,math
B=Path(__file__).resolve().parents[1]; D=B/'full-pool-preparation'; X=B/'full-execution'; O=B/'full-review'
P=json.loads((B/'full-protocol.json').read_text()); START=pd.Timestamp(P['start']);END=pd.Timestamp(P['end'])

def inputs():
 p=pd.read_csv(D/'prices.csv',parse_dates=['date']); p.symbol=p.symbol.str[:6]; p=p.sort_values(['symbol','date'])
 a=json.loads((D/'action-sources/normalized-actions.json').read_text())['events']; return p,a

def indicators(p,a):
 by=defaultdict(list)
 for x in a: by[x['symbol']].append(x)
 rows=[]
 for s,g in p.groupby('symbol'):
  level=1.; prev=None; pc=None; vals=[]
  for r in g.itertuples():
   if prev is not None:
    units=1.;cash=0.
    for x in sorted(by[s],key=lambda q:q.get('effective_date') or '9999'):
     ed=x.get('effective_date')
     if ed and prev.date()<pd.Timestamp(ed).date()<=r.date.date():
      if x['type']=='split':units*=float(x['split_ratio'])
      elif x['type']=='cash_dividend':cash+=units*float(x['cash_per_unit'])
    level*=((units*r.close+cash)/pc)
   vals.append(level);prev=r.date;pc=r.close
  z=pd.DataFrame({'date':g.date.to_numpy(),'symbol':s,'idx':vals}); z['ret']=z.idx.pct_change();z['rv20']=z.ret.rolling(20).std(ddof=1);z['sma200']=z.idx.rolling(200).mean();rows.append(z)
 return pd.concat(rows,ignore_index=True)

def decisions(p,z,pool):
 syms=P['pools'][pool]; union=sorted(p[(p.symbol.isin(syms))&(p.date<=END)].date.unique()); ml={}
 for d in union: ml[(d.year,d.month)]=d
 out=[]
 for dt in ml.values():
  if dt<pd.Timestamp('2020-11-30') or dt>=END:continue
  elig=[];score={};vrank={}
  for s in syms:
   q=z[(z.symbol==s)&(z.date<=dt)]
   raw=p[(p.symbol==s)&(p.date<=dt)]
   if len(raw)<273 or raw.date.iloc[-1]!=dt:continue
   elig.append(s);score[s]=float(q.idx.iloc[-22]/q.idx.iloc[-253]-1)
   rv=q.rv20.dropna(); hist=rv.iloc[-756:]
   if len(hist)>=252:
    cur=hist.iloc[-1]; less=(hist<cur).sum();equal=(hist==cur).sum();vrank[s]=float((less+(equal+1)/2)/len(hist))
   else:vrank[s]=None
  ranked=sorted(elig,key=lambda s:(-score[s],s)); candidates=[s for s in ranked if vrank[s] is None or vrank[s]<.8];top=candidates[:3]
  for cfg in P['configs']:
   chosen=elig if cfg.startswith('equal') else top
   w={s:(1/len(chosen) if s in chosen else 0.) for s in syms} if chosen else {s:0. for s in syms}
   out.append({'pool':pool,'config':cfg,'decision_date':str(dt.date()),'eligible':elig,'ranked':ranked,'candidates':candidates,'selected':chosen,'scores':score,'vol_rank':vrank,'weights':w})
 return out

def main():
 p,a=inputs();z=indicators(p,a); ds=decisions(p,z,'full14')+decisions(p,z,'industry7');(O/'independent-decisions.json').write_text(json.dumps(ds,ensure_ascii=False,indent=2)+'\n')
 if not (X/'summary.json').exists(): print('prepared',len(ds));return
 sig=pd.read_csv(X/'signals.csv'); failures=[]; checked=0
 for r in sig.itertuples():
  if str(getattr(r,'trend_states',''))=='daily_below_sma200':continue
  d=next((x for x in ds if x['pool']==str(r.account_id).split('-')[0] and x['config']==r.config and x['decision_date']==r.decision_date),None)
  if not d: failures.append({'type':'missing_decision','account':r.account_id,'date':r.decision_date});continue
  checked+=1
  selected=str(r.selected).split('|') if pd.notna(r.selected) and str(r.selected) else []
  if selected!=d['selected']:failures.append({'type':'selected','account':r.account_id,'date':r.decision_date,'independent':d['selected'],'execution':selected})
 # Replay execution fills independently for exact cash/units and all corporate actions.
 tr=pd.read_csv(X/'trades.csv'); eq=pd.read_csv(X/'equity.csv'); action_by=defaultdict(list)
 for x in a:
  for k in ['record_date','effective_date','pay_date']:
   if x.get(k):action_by[x[k]].append((k,x))
 ledger_fail=[]; replay_rows=0
 for aid,g in eq.groupby('account_id'):
  cash=1e6;rec=0.;pool=str(aid).split('-')[0]; units={s:0. for s in P['pools'][pool]};ent={};dues={};last={}; tg=tr[tr.account_id==aid]
  prices={(str(r.date.date()),r.symbol):r for r in p[p.symbol.isin(units)].itertuples()}
  for r in g.itertuples():
   day=r.date
   for k,x in action_by.get(day,[]):
    s=x['symbol']
    if s not in units:continue
    if x['type']=='split' and k=='effective_date':
     units[s]*=float(x['split_ratio']);
     if s in last:last[s]/=float(x['split_ratio'])
    elif x['type']=='cash_dividend' and k=='record_date':pass
    elif x['type']=='cash_dividend' and k=='effective_date':
     amt=ent.get(x['event_id'],units[s])*float(x['cash_per_unit']);dues[x['event_id']]=(s,amt);rec+=amt
    elif x['type']=='cash_dividend' and k=='pay_date':
     _,amt=dues.pop(x['event_id'],(s,0.));rec-=amt;cash+=amt
   for t in tg[tg.date==day].itertuples():
    if t.side=='buy':cash-=t.notional+t.fee;units[str(t.symbol)]+=t.qty
    else:cash+=t.notional-t.fee;units[str(t.symbol)]-=t.qty
   # Rights are fixed at record-date close, after that day's open fills.
   for k,x in action_by.get(day,[]):
    if x['type']=='cash_dividend' and k=='record_date' and x['symbol'] in units: ent[x['event_id']]=units[x['symbol']]
   for s in units:
    q=prices.get((day,s));
    if q:last[s]=q.close
   val=cash+rec+sum(units[s]*last.get(s,0.) for s in units);replay_rows+=1
   if abs(val-r.equity)>1e-7 or abs(cash-r.cash)>1e-7 or abs(rec-r.receivable)>1e-7:ledger_fail.append({'account':aid,'date':day,'equity_diff':val-r.equity})
 result={'passed':not failures and not ledger_fail,'monthly_signals_checked':checked,'signal_failures':failures,'ledger_rows_checked':replay_rows,'ledger_failures':ledger_fail}
 (O/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['passed'],checked,replay_rows,len(failures),len(ledger_fail))
if __name__=='__main__':main()
