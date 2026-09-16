from pathlib import Path
import pandas as pd,json
B=Path(__file__).resolve().parents[1];X=B/'execution';s=json.loads((X/'summary.json').read_text())['accounts'];a=pd.read_csv(X/'annual.csv');e=pd.read_csv(X/'equity.csv',parse_dates=['date']);t=pd.read_csv(X/'trades.csv',dtype={'symbol':str});d=pd.read_csv(X/'reentry_diagnostics.csv',dtype={'symbol':str})
comp=[]
for fee in [.001,.002]:
 m={r['method']:r for r in s if r['fee']==fee}
 for new,ref in [('fast_reentry_exit','monthly_reentry_exit'),('monthly_reentry_exit','no_exit_75'),('fast_reentry_exit','no_exit_75'),('fast_reentry_exit','no_exit_100')]:
  comp.append({'fee':fee,'new':new,'reference':ref,'cagr_difference_pp':100*(m[new]['cagr']-m[ref]['cagr']),'drawdown_reduction_pp':100*(m[new]['max_drawdown']-m[ref]['max_drawdown']),'exposure_difference_pp':100*(m[new]['average_exposure']-m[ref]['average_exposure']),'fee_difference':m[new]['fees']-m[ref]['fees'],'terminal_difference':m[new]['final']-m[ref]['final']})
pd.DataFrame(comp).to_csv(B/'controller/comparisons.csv',index=False)
annual=[]
for fee in [.001,.002]:
 fs=f'fee{fee:.3f}';q=a[a.account_id=='fast_reentry_exit-'+fs].set_index('year');r=a[a.account_id=='monthly_reentry_exit-'+fs].set_index('year')
 for y in q.index:annual.append({'fee':fee,'year':int(y),'fast_return':q.loc[y,'return_'],'monthly_return':r.loc[y,'return_'],'difference_pp':100*(q.loc[y,'return_']-r.loc[y,'return_']),'fast_fees':q.loc[y,'fees'],'monthly_fees':r.loc[y,'fees'],'partial':bool(q.loc[y,'partial'])})
pd.DataFrame(annual).to_csv(B/'controller/annual-reentry-difference.csv',index=False)
closed=[]
for r in d[d.end_reason=='stop'].itertuples():
 buy=t[(t.account_id==r.account_id)&(t.symbol==r.symbol)&(t.date==r.reentry_date)&(t.reason=='fast_reentry')&(t.side=='buy')].iloc[0];sell=t[(t.account_id==r.account_id)&(t.symbol==r.symbol)&(t.date==r.boundary_date)&(t.reason=='stop')&(t.side=='sell')].iloc[0];assert abs(buy.qty-sell.qty)<1e-9
 closed.append({'account_id':r.account_id,'symbol':r.symbol,'reentry_date':r.reentry_date,'stop_date':r.boundary_date,'holding_sessions':r.actual_sessions_to_stop,'buy_outlay':buy.notional+buy.fee,'sell_proceeds':sell.notional-sell.fee,'cash_difference':sell.notional-sell.fee-buy.notional-buy.fee,'meaning':'same-list-period full stop sale proceeds less reentry cost; not aggregate strategy incremental attribution; distributions separate'})
pd.DataFrame(closed).to_csv(B/'controller/same-month-closed-reentries.csv',index=False)
peaks=[]
for aid,g in e.groupby('account_id'):
 g=g.reset_index(drop=True);peak=g.equity.cummax().clip(lower=1e6);dd=g.equity/peak-1;tr=int(dd.idxmin());before=g.iloc[:tr+1];pk=before[before.equity==float(peak.iloc[tr])];peaks.append({'account_id':aid,'peak_date':str(pk.iloc[-1].date.date()) if len(pk) else 'initial','trough_date':str(g.iloc[tr].date.date()),'drawdown':float(dd.iloc[tr])})
pd.DataFrame(peaks).to_csv(B/'controller/drawdown-dates.csv',index=False)
print(pd.DataFrame(comp).round(4).to_string(index=False));cl=pd.DataFrame(closed);print(cl.groupby('account_id').agg(count=('cash_difference','size'),cash_difference=('cash_difference','sum')))
print('Nov2021',cl[(cl.account_id=='fast_reentry_exit-fee0.001')&cl.reentry_date.str.startswith('2021-11')][['symbol','reentry_date','cash_difference']].to_string(index=False))
