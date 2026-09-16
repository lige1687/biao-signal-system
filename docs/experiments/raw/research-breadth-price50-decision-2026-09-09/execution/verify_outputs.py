from pathlib import Path
from decimal import Decimal
import hashlib,json
import pandas as pd

D=Decimal
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
OLD=ROOT/'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12'

def load_bars(symbol):
 p=OLD/'inputs/bars'/f"{'sh' if symbol.startswith('5') else 'sz'}{symbol}-nominal.csv"
 d=pd.read_csv(p); d.date=pd.to_datetime(d.date); return d.set_index('date').sort_index()

def continuous(bars,actions,internal):
 cash={pd.Timestamp(a['effective_date']):float(a['cash']) for a in actions if a['symbol']==internal and a['type']=='cash_dividend'}
 ratio={pd.Timestamp(a['effective_date']):float(a['ratio']) for a in actions if a['symbol']==internal and a['type']=='split'}
 out={}; level=prev=None
 for day,row in bars.iterrows():
  c=float(row.close)
  if level is None: level=c
  else:
   ref=prev-cash.get(day,0)
   if day in ratio: ref/=ratio[day]
   level*=c/ref
  out[day]=level; prev=c
 return pd.Series(out)

def main():
 lock=json.load(open(HERE/'pre-run-lock.json'))
 hash_checks=[]
 for f in lock['files']:
  p=ROOT/f['path']; actual=hashlib.sha256(p.read_bytes()).hexdigest()
  hash_checks.append({'path':f['path'],'match':actual==f['sha256']})
 actions=json.load(open(OLD/'inputs/actions.json'))
 summaries=pd.read_csv(HERE/'results/summary.csv')
 annual_out=pd.read_csv(HERE/'results/annual.csv')
 periods_out=pd.read_csv(HERE/'results/periods.csv')
 checks=[]
 for s in summaries.itertuples():
  account=s.account_id; symbol=str(s.symbol).zfill(6); fee=D(str(s.fee_rate)); internal=('sh' if symbol.startswith('5') else 'sz')+symbol
  fee_dir=HERE/'results'/('fee-10bp' if s.fee_rate==.001 else 'fee-20bp')
  daily=pd.read_parquet(fee_dir/f'{account}-daily.parquet'); daily.date=pd.to_datetime(daily.date)
  trades=pd.read_csv(fee_dir/f'{account}-trades.csv'); trades.date=pd.to_datetime(trades.date)
  signals=pd.read_csv(fee_dir/f'{account}-signals.csv'); signals.date=pd.to_datetime(signals.date)
  bars_all=load_bars(symbol); bars=bars_all.loc['2018-07-05':'2026-06-30']
  cont=continuous(bars_all,actions,internal); sma=cont.dropna().rolling(50,min_periods=50).mean(); target=(cont>sma).astype(float); target[sma.isna()]=float('nan')
  states=pd.DataFrame({'close':cont,'sma50':sma,'target':target}).loc[bars.index]
  expected=states[states.target.notna() & states.target.ne(states.target.shift())]
  signal_ok=(len(expected)==len(signals) and all(abs(signals.iloc[i].target-expected.iloc[i].target)<1e-12 and signals.iloc[i].date==expected.index[i] and abs(signals.iloc[i].close-expected.iloc[i]['close'])<1e-10 and abs(signals.iloc[i].sma50-expected.iloc[i].sma50)<1e-10 for i in range(len(expected))))
  timing_ok=True; price_ok=True
  for tr in trades.itertuples():
   prior=signals[signals.date<tr.date]
   if prior.empty or float(prior.iloc[-1].target)!=(1.0 if tr.side=='buy' else 0.0): timing_ok=False
   if abs(float(bars_all.loc[tr.date].open)-tr.price)>1e-12: price_ok=False
  cash=D('1000000'); recv=D('0'); units=D('0'); rights={}; dues={}; last=D('0'); maxdiff=D('0')
  action_list=[a for a in actions if a['symbol']==internal]
  bytrade={d:list(g.itertuples()) for d,g in trades.groupby('date')}
  barmap={d:r for d,r in bars.iterrows()}
  for row in daily.itertuples():
   day=row.date
   for a in action_list:
    if pd.Timestamp(a['effective_date'])==day:
     if a['type']=='cash_dividend':
      amt=rights.get(a['event_id'],D('0'))*D(str(a['cash'])); dues[a['event_id']]=amt; recv+=amt
     elif a['type']=='split': units*=D(str(a['ratio']))
    if a['type']=='cash_dividend' and a.get('pay_date') and pd.Timestamp(a['pay_date'])==day:
     amt=dues.pop(a['event_id'],D('0')); recv-=amt; cash+=amt
   for tr in bytrade.get(day,[]):
    q=D(str(tr.qty)); n=D(str(tr.notional)); f=D(str(tr.fee))
    if tr.side=='buy': cash-=n+f; units+=q
    else: cash+=n-f; units-=q
    maxdiff=max(maxdiff,abs(f-n*fee))
   if day in barmap: last=D(str(barmap[day]['close']))
   for a in action_list:
    if a['type']=='cash_dividend' and a.get('record_date') and pd.Timestamp(a['record_date'])==day: rights[a['event_id']]=units
   vals=[abs(cash-D(str(row.cash))),abs(recv-D(str(row.receivable))),abs(units-D(str(row.units))),abs(last-D(str(row.mark))),abs(cash+recv+units*last-D(str(row.equity)))]
   maxdiff=max([maxdiff]+vals)
  values=[1000000.0]+daily.equity.astype(float).tolist(); peak=values[0]; mdd=0.0
  for v in values: peak=max(peak,v); mdd=min(mdd,v/peak-1)
  years=(pd.Timestamp('2026-06-30')-pd.Timestamp('2018-07-05')).days/365.25
  cagr=(float(daily.iloc[-1].equity)/1000000.0)**(1/years)-1
  intervals=[]; peak=1000000.0; peakday=pd.Timestamp('2018-07-04'); active=None
  for row in daily.itertuples():
   if row.equity>=peak:
    if active is not None: intervals.append((row.date-active).days); active=None
    peak=float(row.equity); peakday=row.date
   elif active is None: active=peakday
  if active is not None: intervals.append((daily.date.iloc[-1]-active).days)
  longest=max([0]+intervals)
  metric_ok=abs(cagr-s.cagr)<1e-12 and abs(mdd-s.max_drawdown)<1e-12 and longest==s.longest_recovery_days
  annual_expected=[]; prior=1000000.0
  for year,g in daily.groupby(daily.date.dt.year):
   end=float(g.iloc[-1].equity); annual_expected.append((int(year),prior,end,end/prior-1)); prior=end
  ao=annual_out[annual_out.account_id==account]
  annual_ok=len(ao)==len(annual_expected) and all(int(r.year)==x[0] and abs(r.start_equity-x[1])<1e-6 and abs(r.end_equity-x[2])<1e-6 and abs(r['return']-x[3])<1e-12 for (_,r),x in zip(ao.iterrows(),annual_expected))
  period_defs=[('2018-07-05—2019','2018-07-05','2019-12-31'),('2020—2024','2020-01-01','2024-12-31'),('2025—2026H1','2025-01-01','2026-06-30')]
  po=periods_out[periods_out.account_id==account]; period_expected=[]
  for label,a,b in period_defs:
   g=daily[(daily.date>=a)&(daily.date<=b)]; before=daily[daily.date<a]; base=float(before.iloc[-1].equity) if len(before) else 1000000.0; end=float(g.iloc[-1].equity); period_expected.append((label,base,end,end/base-1))
  period_ok=len(po)==3 and all(r.period==x[0] and abs(r.start_equity-x[1])<1e-6 and abs(r.end_equity-x[2])<1e-6 and abs(r['return']-x[3])<1e-12 for (_,r),x in zip(po.iterrows(),period_expected))
  passed=signal_ok and timing_ok and price_ok and maxdiff<D('0.000001') and metric_ok and annual_ok and period_ok
  checks.append({'account_id':account,'calendar_rows':len(daily),'signals':len(signals),'trades':len(trades),'signal_exact':signal_ok,'trade_after_matching_latest_signal':timing_ok,'trade_at_nominal_open':price_ok,'max_cash_units_equity_or_fee_diff':float(maxdiff),'summary_final_diff':abs(float(daily.iloc[-1].equity)-s.end_equity),'summary_cagr_drawdown_recovery_exact':metric_ok,'annual_exact':annual_ok,'periods_exact':period_ok,'passed':passed})
 out={'passed':all(x['match'] for x in hash_checks) and len(checks)==4 and all(x['passed'] for x in checks),'pre_run_hashes':hash_checks,'accounts':checks}
 (HERE/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
