from pathlib import Path
import pandas as pd, numpy as np, json
W=Path(__file__).resolve().parents[1];R=Path(__file__).resolve().parents[5];O=R/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/results';N=W/'execution/results';out=W/'comparison'
frames=[];phase=[];checks=[];profits=[]
acts=json.loads((R/'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/actions.json').read_text())
for source in [O,N]:
 summ=pd.read_csv(source/'summary.csv',dtype={'symbol':str});frames.append(summ)
 for s in summ.itertuples():
  stem=source/('fee-10bp' if s.fee_rate==.001 else 'fee-20bp');d=pd.read_parquet(stem/f'{s.account_id}-daily.parquet');d.date=pd.to_datetime(d.date);t=pd.read_csv(stem/f'{s.account_id}-trades.csv');t.date=pd.to_datetime(t.date)
  for label,a,b in [('2018-2019','2018-07-05','2019-12-31'),('2020-2024','2020-01-01','2024-12-31'),('2025-2026H1','2025-01-01','2026-06-30')]:
   z=d[d.date.between(a,b)];before=d[d.date<pd.Timestamp(a)];initial=before.equity.iloc[-1] if len(before) else 1e6;peak=z.equity.cummax().clip(lower=initial)
   phase.append({'account_id':s.account_id,'period':label,'start_equity':initial,'end_equity':z.equity.iloc[-1],'cumulative_return':z.equity.iloc[-1]/initial-1,'local_max_drawdown':(z.equity/peak-1).min(),'average_exposure':z[z.is_quote_day].weight.mean(),'fees':t[t.date.between(a,b)].fee.sum()})
  if source==N:
   eq=np.r_[1e6,d.equity.values];cagr=(eq[-1]/1e6)**(365.25/(d.date.iloc[-1]-d.date.iloc[0]).days)-1;dd=(eq/np.maximum.accumulate(eq)-1).min()
   peak=1e6;peakday=d.date.iloc[0]-pd.Timedelta(days=1);longest=0;prev_under=False
   for x in d.itertuples():
    if x.equity>=peak:
     if x.equity>peak or x.date==peakday:pass
     if peakday<x.date:longest=max(longest,(x.date-peakday).days if prev_under else 0)
     peak=x.equity;peakday=x.date;prev_under=False
    else:longest=max(longest,(x.date-peakday).days);prev_under=True
   assert abs(cagr-s.cagr)<1e-12 and abs(dd-s.max_drawdown)<1e-12 and longest==s.longest_recovery_days
   checks.append({'account':s.account_id,'cagr_error':cagr-s.cagr,'drawdown_error':dd-s.max_drawdown,'recovery_days':longest})
   units=0.;basis=0.;realized=0.
   internal=('sh' if s.symbol.startswith('5') else 'sz')+s.symbol;splits={pd.Timestamp(a['effective_date']):float(a['ratio']) for a in acts if a['symbol']==internal and a['type']=='split'}
   grouped={day:g for day,g in t.groupby('date')}
   for day in d.date:
    units*=splits.get(day,1.)
    for z in grouped.get(day,pd.DataFrame()).itertuples():
     if z.side=='buy':units+=z.qty;basis+=z.notional
     else:
      removed=basis*z.qty/units;realized+=z.notional-removed;basis-=removed;units-=z.qty
   last=d.iloc[-1];unrealized=last.units*last.mark-basis;div=last.dividends_received+last.receivable;fees=t.fee.sum();profit=realized+unrealized+div-fees;err=profit-(last.equity-1e6);assert abs(err)<1e-6 and abs(units-last.units)<1e-6
   profits.append({'account':s.account_id,'realized_price_pnl':realized,'terminal_unrealized_price_pnl':unrealized,'earned_dividends':div,'fees':fees,'net_profit':profit,'cash':last.cash,'receivable':last.receivable,'market_value':last.units*last.mark,'reconciliation_error':err})
pd.concat(frames).to_csv(out/'all-40-summary.csv',index=False);pd.DataFrame(phase).to_csv(out/'all-40-fixed-phases.csv',index=False);pd.DataFrame(profits).to_csv(out/'new-4-profit-attribution.csv',index=False);(out/'new-metric-review.json').write_text(json.dumps({'passed':True,'accounts':checks},indent=2)+'\n');print('40 accounts summarized; new4 metrics and cost basis independently checked')
