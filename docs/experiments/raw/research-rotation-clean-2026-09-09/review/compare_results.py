from pathlib import Path
import pandas as pd,json,hashlib
B=Path(__file__).resolve().parents[1]; R=B/'review'; E=B/'execution'
sm=json.loads((R/'independent-summary.json').read_text()); exsm=json.loads((E/'summary.json').read_text())['accounts']
rows=[]; failures=[]; totals={'daily_rows':0,'trade_rows':0,'annual_rows':0,'signal_month_rows':0,'action_rows':0,'contribution_rows':0}
for x in sm:
 method=x['method']; fee=x['fee']; bp=int(fee*10000); aid=f'{method}-fee{fee:.3f}'
 y=next(z for z in exsm if z['account_id']==aid)
 rec={'account_id':aid,'independent_account':x['account']}
 for a,b,name in [(x['ending_equity'],y['final'],'final'),(x['cagr'],y['cagr'],'cagr'),(x['max_drawdown'],y['max_drawdown'],'max_drawdown'),(x['average_exposure'],y['average_exposure'],'average_exposure')]: rec[name+'_abs_diff']=abs(a-b)
 # daily money/units
 a=pd.read_csv(R/f'{method}-fee{bp}bp-daily.csv'); b=pd.read_csv(E/'equity.csv'); b=b[b.account_id==aid]
 totals['daily_rows']+=len(a)
 pairs=[('equity','equity'),('cash','cash'),('receivables','receivable')]+[(f'units_{s}',f'units_{s[:6]}') for s in ['159915.SZ','510300.SH','512170.SH','512400.SH']]
 rec['daily_rows']=len(a); rec['daily_max_abs_diff']={aa:float((a[aa]-b[bb].to_numpy()).abs().max()) for aa,bb in pairs}
 # trades unordered within day
 a=pd.read_csv(R/f'{method}-fee{bp}bp-trades.csv'); a.symbol=a.symbol.str[:6]; a=a.rename(columns={'units':'qty'}); a['n']=a.groupby(['date','symbol','side']).cumcount()
 b=pd.read_csv(E/'trades.csv'); b=b[b.account_id==aid].copy(); b.symbol=b.symbol.astype(str); b['reason']=b['reason'].replace({'stop':'daily_sma200_exit'}); b['n']=b.groupby(['date','symbol','side']).cumcount()
 m=a.merge(b,on=['date','symbol','side','n'],how='outer',suffixes=('_i','_e'),indicator=True)
 bad=m[(m._merge!='both')|(abs(m.qty_i-m.qty_e)>1e-8)|(abs(m.price_i-m.price_e)>1e-12)|(abs(m.fee_i-m.fee_e)>1e-8)]
 reason_bad=m[(m._merge=='both')&(m.reason_i!=m.reason_e)]
 rec['trade_rows']=len(a); rec['trade_differences']=len(bad); rec['reason_label_differences']=len(reason_bad); totals['trade_rows']+=len(a)
 # annual
 eb=pd.read_csv(E/'annual.csv'); eb=eb[eb.account_id==aid]
 rec['annual_max_abs_diff']=max(abs(z['return']-float(eb[eb.year==z['year']].return_.iloc[0])) for z in x['annual']); totals['annual_rows']+=len(x['annual'])
 # contributions
 pb=pd.read_csv(E/'per_symbol.csv'); pb=pb[pb.account_id==aid]
 dif={s:abs(v-float(pb[pb.symbol.astype(str)==s[:6]].net_pnl.iloc[0])) for s,v in x['symbol_contribution'].items()}; rec['contribution_max_abs_diff']=max(dif.values()); totals['contribution_rows']+=4
 rows.append(rec)
# Decision signals: compare monthly rows only, both fees must match independent method decision.
decs=json.loads((R/'independent-decisions.json').read_text()); sig=pd.read_csv(E/'signals.csv'); sig=sig[sig.trend_states!='daily_below_sma200']
for _,r in sig.iterrows():
 d=next(x for x in decs if x['method']==r['config'] and x['decision_date']==r['decision_date'])
 sels=r['selected'].split('|') if isinstance(r['selected'],str) else []
 # equal execution preserves protocol symbol order; top3 uses rank order. Compare sets plus exact rank derived independently.
 if set(sels)!={s[:6] for s in d['selected']}: failures.append({'kind':'selected','account':r.account_id,'date':r.decision_date})
 scores=json.loads(r.scores); weights=json.loads(r.weights)
 for s,z in d['details'].items():
  if abs(scores[s[:6]]-z['score'])>1e-12: failures.append({'kind':'score','account':r.account_id,'date':r.decision_date,'symbol':s})
 for s,w in d['weights'].items():
  if abs(weights[s[:6]]-w)>1e-12: failures.append({'kind':'weight','account':r.account_id,'date':r.decision_date,'symbol':s})
totals['signal_month_rows']=len(sig)
# Action financial records compare by account/event/date/type/amount.
maptype={'entitlement':'entitlement','receivable':'receivable','dividend_cash':'cash_paid'}
ours=[]
for method in ['equal','momentum_top3','equal_sma200','momentum_top3_sma200']:
 for fee,bp in [(.001,10),(.002,20)]:
  aid=f'{method}-fee{fee:.3f}'
  ev=json.loads((R/f'{method}-fee{bp}bp-events.json').read_text())
  for z in ev:
   if z['type'] in maptype: ours.append((aid,z['date'],z['event_id'],maptype[z['type']],round(z['amount'],8)))
eva=pd.read_csv(E/'actions.csv'); theirs=[(r.account_id,r.date,r.event_id,r.event,round(float(r.amount),8)) for r in eva.itertuples() if r.event!='split']
action_diff=len(set(ours)^set(theirs)); totals['action_rows']=len(ours)
# input/result lock
locked=[]
for p in sorted(list((B/'data').glob('*'))+list((B/'execution').glob('*.csv'))+[B/'execution/summary.json',B/'execution/post-run-verification.json']):
 locked.append({'path':str(p.relative_to(B)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
passed=(not failures and action_diff==0 and all(r['trade_differences']==0 and max(r['daily_max_abs_diff'].values())<1e-7 and r['annual_max_abs_diff']<1e-12 and r['contribution_max_abs_diff']<1e-7 and r['final_abs_diff']<1e-7 and max(r[k] for k in ['cagr_abs_diff','max_drawdown_abs_diff','average_exposure_abs_diff'])<1e-12 for r in rows))
result={'passed':passed,'scope':totals,'accounts':rows,'decision_failures':failures,'action_symmetric_difference':action_diff,'result_inputs':locked,'reason_label_note':'Four trend-account fills can be simultaneously caused by the prior daily below-SMA signal and the month-end zero target; independent output labels daily_sma200_exit while execution labels monthly. Dates, units, prices, fees and cash are identical.','limitations':['Independent ledger uses the frozen four-product list; it does not validate a point-in-time full ETF universe.','Daily bars cannot establish intraday liquidity beyond the frozen missing/zero/known-halt/one-price checks.']}
(R/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':passed,'scope':totals,'decision_failures':len(failures),'action_diff':action_diff},indent=2))
