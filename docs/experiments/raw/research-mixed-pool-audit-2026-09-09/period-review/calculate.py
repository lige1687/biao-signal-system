from pathlib import Path
import pandas as pd,json,hashlib
SRC=Path('docs/experiments/raw/research-mixed-defense-2026-09-09/execution'); OUT=Path(__file__).resolve().parent
INITIAL=1_000_000.0; END=pd.Timestamp('2026-06-30')
def recovery_intervals(g):
    peak=INITIAL; peak_date=pd.Timestamp('2020-11-30'); start=None; start_peak=None; rows=[]
    for r in g.itertuples():
        d=r.date; e=float(r.equity)
        if start is None:
            if e>=peak: peak=e; peak_date=d
            else: start=d; start_peak=peak_date
        elif e>=peak:
            rows.append({'peak_date':str(start_peak.date()),'underwater_start':str(start.date()),'recovery_date':str(d.date()),'days':int((d-start_peak).days),'completed':True})
            peak=e; peak_date=d; start=None; start_peak=None
    if start is not None: rows.append({'peak_date':str(start_peak.date()),'underwater_start':str(start.date()),'recovery_date':None,'days':int((END-start_peak).days),'completed':False})
    return rows
def main():
    d=pd.read_csv(SRC/'equity.csv',parse_dates=['date']); out=[]; evidence={}
    for aid,g in d.groupby('account_id',sort=False):
        g=g.sort_values('date'); e24=float(g[g.date<=pd.Timestamp('2024-12-31')].iloc[-1].equity); final=float(g.iloc[-1].equity)
        ints=recovery_intervals(g); longest=max(ints,key=lambda x:x['days']) if ints else None; unfinished=[x for x in ints if not x['completed']]
        out.append({'account_id':aid,'initial_equity':INITIAL,'equity_2024_end':e24,'final_equity':final,'profit_through_2024':e24-INITIAL,'profit_2025_to_2026_06':final-e24,'total_profit':final-INITIAL,'profit_identity_diff':(e24-INITIAL)+(final-e24)-(final-INITIAL),'longest_unrecovered_days':longest['days'] if longest else 0,'longest_peak_date':longest['peak_date'] if longest else None,'longest_recovery_date':longest['recovery_date'] if longest else None,'longest_completed':longest['completed'] if longest else True,'unfinished_at_end':bool(unfinished),'current_unrecovered_days':unfinished[-1]['days'] if unfinished else 0,'current_peak_date':unfinished[-1]['peak_date'] if unfinished else None})
        evidence[aid]=ints
    pd.DataFrame(out).to_csv(OUT/'period-results.csv',index=False); (OUT/'recovery-intervals.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    lockfiles=[SRC/'equity.csv',SRC/'summary.json',Path(__file__)]; (OUT/'source-lock.json').write_text(json.dumps({'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in lockfiles]},ensure_ascii=False,indent=2)+'\n')
    assert max(abs(x['profit_identity_diff']) for x in out)<1e-7
    print(pd.DataFrame(out).to_string(index=False))
if __name__=='__main__':main()
