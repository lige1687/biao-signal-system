from pathlib import Path
import json
import pandas as pd
B=Path(__file__).resolve().parent; W=B.parent
sources={'original14':W.parent/'research-mixed-defense-2026-09-09'/'execution','representative11':W/'dedup-execution'}
rows=[]
for pool,src in sources.items():
 eq=pd.read_csv(src/'equity.csv');summary=json.loads((src/'summary.json').read_text())['accounts']
 for item in summary:
  g=eq[eq.account_id==item['account_id']].sort_values('date');end24=float(g[g.date=='2024-12-31'].equity.iloc[0]); final=float(g.iloc[-1].equity)
  # Peak begins at latest date at the previous high; counting elapsed natural days, not inclusive days.
  peak=1e6;peakdate=pd.Timestamp('2020-12-01');longest=0;lp=lr=None;under=False
  for d,x in zip(g.date,g.equity):
   day=pd.Timestamp(d)
   if x>=peak-1e-7:
    if under and (day-peakdate).days>longest:longest=(day-peakdate).days;lp=str(peakdate.date());lr=d
    peak=max(peak,x);peakdate=day;under=False
   else:under=True
  current=(pd.Timestamp(g.iloc[-1].date)-peakdate).days if under else 0
  if current>longest:longest=current;lp=str(peakdate.date());lr='not_recovered'
  rows.append(dict(pool=pool,**item,through2024_return=end24/1e6-1,through2024_cagr=(end24/1e6)**(365.2425/(pd.Timestamp('2024-12-31')-pd.Timestamp('2020-12-01')).days)-1,profit_early=end24-1e6,profit_late=final-end24,late_profit_share=(final-end24)/(final-1e6),longest_recovery_days=longest,longest_peak=lp,longest_recovery=lr,current_unrecovered_days=current))
pd.DataFrame(rows).to_csv(B/'pools-comparison.csv',index=False)
# Cross-check original period review independently, accounting tolerance only.
p=pd.read_csv(W/'period-review/period-results.csv');df=pd.DataFrame(rows)
for r in p.itertuples():
 x=df[(df.pool=='original14')&(df.account_id==r.account_id)].iloc[0]
 assert abs(x.profit_early-r.profit_through_2024)<1e-6
 assert abs(x.profit_late-r.profit_2025_to_2026_06)<1e-6
 assert x.longest_recovery_days==r.longest_unrecovered_days
print(df[df.method=='fast_reentry_exit'][['pool','fee','through2024_cagr','through2024_return','profit_late','late_profit_share','longest_recovery_days','longest_peak','longest_recovery']].to_string(index=False))
