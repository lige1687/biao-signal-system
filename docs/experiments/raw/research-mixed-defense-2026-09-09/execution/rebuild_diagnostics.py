"""Rebuild reentry diagnostics from frozen result tables; never reruns returns."""
from pathlib import Path
import pandas as pd

P=Path(__file__).resolve().parent
DATA=P.parent.parent/'research-rotation-clean-2026-09-09/full-pool-preparation/prices.csv'

def main():
    trades=pd.read_csv(P/'trades.csv',dtype={'symbol':str})
    signals=pd.read_csv(P/'signals.csv',dtype={'selected':str})
    prices=pd.read_csv(DATA,dtype={'symbol':str}); prices.symbol=prices.symbol.str.split('.').str[0]
    out=[]
    for aid in sorted(x for x in trades.account_id.unique() if x.startswith('fast_reentry_exit')):
        tt=trades[trades.account_id==aid].reset_index(drop=True)
        monthly=sorted(signals[(signals.account_id==aid)&signals.opening_equity.notna()].eligible_date.unique())
        for i,t in tt.iterrows():
            if t.side!='buy' or t.reason!='fast_reentry': continue
            boundary=next((d for d in monthly if d>t.date),None)
            candidates=tt[(tt.index>i)&(tt.symbol==t.symbol)&(tt.side=='sell')]
            if boundary is not None: candidates=candidates[candidates.date<boundary]
            stop=candidates[candidates.reason=='stop'].iloc[0] if not candidates[candidates.reason=='stop'].empty else None
            q=sorted(prices[(prices.symbol==t.symbol)&(prices.date>t.date)].date.unique())
            cutoff=stop.date if stop is not None else (boundary or '9999-12-31')
            observed=sum(d<cutoff for d in q)
            sessions=(q.index(stop.date)+1) if stop is not None and stop.date in q else None
            end_reason='stop' if stop is not None else ('monthly_reset' if boundary else 'period_end')
            out.append({'account_id':aid,'symbol':t.symbol,'reentry_date':t.date,
              'boundary_date':stop.date if stop is not None else (boundary or ''),'end_reason':end_reason,
              'actual_sessions_to_stop':sessions,'observable_sessions_before_boundary':observed,
              'mature5':observed>=5 or sessions is not None,'mature20':observed>=20 or sessions is not None,
              'stop_again_within5':bool(sessions is not None and sessions<=5),
              'stop_again_within20':bool(sessions is not None and sessions<=20)})
    pd.DataFrame(out).to_csv(P/'reentry_diagnostics.csv',index=False)

if __name__=='__main__': main()
