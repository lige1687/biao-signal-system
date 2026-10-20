"""Clarify frozen result metadata without rerunning accounts or returns."""
import json
from pathlib import Path
import pandas as pd

P=Path(__file__).resolve().parent

def scaled(raw,factor):
    try: return json.dumps({k:v*factor for k,v in json.loads(raw).items()})
    except Exception: return raw

def main():
    s=pd.read_csv(P/'signals.csv')
    s['selection_weights']=s['weights']
    monthly=s.opening_equity.notna()
    s['allocation_fraction']=1.0
    is75=s.account_id.str.startswith('no_exit_75') & monthly
    s.loc[is75,'allocation_fraction']=.75
    s['allocation_weights']=s['weights']
    s.loc[is75,'allocation_weights']=s.loc[is75,'weights'].map(lambda x:scaled(x,.75))
    s.to_csv(P/'signals.csv',index=False)

    e=pd.read_csv(P/'reentry_events.csv')
    e['actual_stop_fill_date']=''
    latest={}
    for i,row in e.iterrows():
        key=(row.account_id,str(row.symbol))
        if row.event=='stop_budget_created': latest[key]=row.date; e.at[i,'actual_stop_fill_date']=row.date
        elif key in latest: e.at[i,'actual_stop_fill_date']=latest[key]
        if row.event=='monthly_cancel': latest.pop(key,None)
    e.to_csv(P/'reentry_events.csv',index=False)

if __name__=='__main__': main()
