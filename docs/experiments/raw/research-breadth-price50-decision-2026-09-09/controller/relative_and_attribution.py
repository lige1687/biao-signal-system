from pathlib import Path
import pandas as pd, numpy as np, json, hashlib
R=Path(__file__).resolve().parents[5];W=Path(__file__).resolve().parents[1];OLD=R/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09';OUT=W/'comparison';OUT.mkdir(exist_ok=True)
INITIAL=1e6
candidates=[('159915','all_a','W3'),('510300','csi300','W0'),('510300','all_a','W3')]
def get(account):
 fee=account.split('-')[-1];base=(W/'execution/results' if '-P50-' in account else OLD/'results')/f'fee-{fee}'
 d=pd.read_parquet(base/f'{account}-daily.parquet').set_index('date');d.index=pd.to_datetime(d.index)
 t=pd.read_csv(base/f'{account}-trades.csv');t['date']=pd.to_datetime(t.date)
 pre='sh' if account.startswith('5') else 'sz';bars=pd.read_csv(R/f'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/bars/{pre}{account[:6]}-nominal.csv').set_index('date');bars.index=pd.to_datetime(bars.index)
 qty=t.assign(signed=t.qty*np.where(t.side=='buy',1,-1)).groupby('date').signed.sum().reindex(d.index,fill_value=0)
 fees=t.groupby('date').fee.sum().reindex(d.index,fill_value=0)
 prevu=d.units.shift(1,fill_value=0);prevmark=d.mark.shift(1,fill_value=0);preu=d.units-qty
 op=bars.open.reindex(d.index);quote=d.is_quote_day.astype(bool)
 overnight=(preu*op-prevu*prevmark).where(quote,0)
 intraday=(d.units*(d.mark-op)).where(quote,d.units*d.mark-prevu*prevmark)
 div=d.receivable.diff().fillna(d.receivable.iloc[0])+d.dividends_received.diff().fillna(d.dividends_received.iloc[0])
 delta=d.equity.diff().fillna(d.equity.iloc[0]-INITIAL)
 err=(overnight+intraday+div-fees-delta).abs().max();assert err<1e-6,(account,err)
 return d,pd.DataFrame({'overnight':overnight,'intraday':intraday,'dividends':div,'fees':-fees,'pre_units':preu,'post_units':d.units},index=d.index),float(err)
def intervals(s):
 peak=1.;peakday=s.index[0]-pd.Timedelta(days=1);active=None;records=[]
 for day,v in s.items():
  if v>=peak:
   if active: active.update(recovery=str(day.date()),days=(day-active['peak_ts']).days,unrecovered=False);records.append(active);active=None
   peak=v;peakday=day
  else:
   dd=v/peak-1
   if active is None:active={'peak_ts':peakday,'peak_date':str(peakday.date()),'worst_relative_drawdown':dd,'trough':str(day.date())}
   elif dd<active['worst_relative_drawdown']:active.update(worst_relative_drawdown=dd,trough=str(day.date()))
 if active:active.update(recovery=None,days=(s.index[-1]-active['peak_ts']).days,unrecovered=True);records.append(active)
 for x in records:x.pop('peak_ts')
 return records
rows=[];details=[];money=[];checks=[];intervalrows=[];daily_contributions=[]
for symbol,source,method in candidates:
 for fee in ['10bp','20bp']:
  aid=f'{symbol}-{source}-{method}-{fee}';a,ac,ae=get(aid)
  for base in (['B1','B0','P50'] if (W/'execution/results/summary.csv').exists() else ['B1','B0']):
   bid=f'{symbol}-'+('price50' if base=='P50' else 'baseline')+f'-{base}-{fee}';b,bc,be=get(bid);assert a.index.equals(b.index)
   rel=a.equity/b.equity;peak=rel.cummax().clip(lower=1);dd=rel/peak-1;ints=intervals(rel);longest=max(ints,key=lambda x:x['days']) if ints else {'days':0,'unrecovered':False}
   end=ints[-1] if ints and ints[-1]['unrecovered'] else {'days':0}
   rows.append({'candidate':aid,'benchmark':bid,'end_relative_nav':rel.iloc[-1],'worst_relative_drawdown':dd.min(),'longest_relative_recovery_days':longest['days'],'longest_unrecovered':longest['unrecovered'],'end_unrecovered_days':end['days'],'end_absolute_profit_difference':a.equity.iloc[-1]-b.equity.iloc[-1]})
   details.append(pd.DataFrame({'date':a.index,'candidate':aid,'benchmark':bid,'relative_nav':rel.values,'relative_drawdown':dd.values}))
   intervalrows.extend([dict(candidate=aid,benchmark=bid,**x) for x in ints])
   pair=[]
   for component,unitcol in [('overnight','pre_units'),('intraday','post_units')]:
    group=np.select([(ac[unitcol]>0)&(bc[unitcol]>0),(ac[unitcol]>0)&(bc[unitcol]==0),(ac[unitcol]==0)&(bc[unitcol]>0)],['both_hold','only_width','only_price'],default='both_cash')
    f=pd.DataFrame({'group':group,'a':ac[component],'b':bc[component]}); daily_contributions.append(pd.DataFrame({'date':a.index,'candidate':aid,'benchmark':bid,'component':component,'holding_group':group,'candidate_pnl':ac[component].values,'benchmark_pnl':bc[component].values,'difference':(ac[component]-bc[component]).values}));g=f.groupby('group')[['a','b']].sum()
    for k,x in g.iterrows():pair.append({'candidate':aid,'benchmark':bid,'component':component,'holding_group':k,'candidate_pnl':x.a,'benchmark_pnl':x.b,'difference':x.a-x.b})
   for component in ['dividends','fees']:
    daily_contributions.append(pd.DataFrame({'date':a.index,'candidate':aid,'benchmark':bid,'component':component,'holding_group':'separate','candidate_pnl':ac[component].values,'benchmark_pnl':bc[component].values,'difference':(ac[component]-bc[component]).values}));aa=ac[component].sum();bb=bc[component].sum();pair.append({'candidate':aid,'benchmark':bid,'component':component,'holding_group':'separate','candidate_pnl':aa,'benchmark_pnl':bb,'difference':aa-bb})
   gap=sum(x['difference'] for x in pair)-(a.equity.iloc[-1]-b.equity.iloc[-1]);assert abs(gap)<1e-6
   money.extend(pair);checks.append({'candidate':aid,'benchmark':bid,'max_daily_identity_error':max(ae,be),'pair_reconciliation_error':gap})
pd.DataFrame(rows).to_csv(OUT/'relative-summary.csv',index=False);pd.concat(details).to_csv(OUT/'relative-daily.csv',index=False);pd.DataFrame(intervalrows).to_csv(OUT/'relative-intervals.csv',index=False);pd.DataFrame(money).to_csv(OUT/'holding-difference-attribution.csv',index=False)
(OUT/'checks.json').write_text(json.dumps({'passed':True,'principles_version':'v1.0','checks':checks,'boundary':'Accounting of actual holding differences, not causal alpha; full account cash remains included.'},indent=2)+'\n')
z=pd.concat(daily_contributions);z.to_parquet(OUT/'holding-difference-daily.parquet',index=False);z['period']=np.select([z.date<pd.Timestamp('2020-01-01'),z.date<pd.Timestamp('2025-01-01')],['2018-2019','2020-2024'],default='2025-2026H1');z.groupby(['candidate','benchmark','period','component','holding_group'])[['candidate_pnl','benchmark_pnl','difference']].sum().reset_index().to_csv(OUT/'holding-difference-phases.csv',index=False);print(f'{len(rows)} fixed pairs reconciled')
