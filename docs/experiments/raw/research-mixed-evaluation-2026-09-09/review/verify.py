"""Independent formula and accounting review; never imports the evaluation implementation."""
from pathlib import Path
from collections import defaultdict
import hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; B=HERE.parent; ROOT=HERE.parents[4]
SRC=ROOT/'docs/experiments/raw/research-mixed-pool-audit-2026-09-09/dedup-execution'; EV=B/'evaluation'
INITIAL=1_000_000.; YEAR=365.2425

def close_enough(a,b,tol=1e-8): return abs(float(a)-float(b))<=tol
def recovery(g):
    pts=[(pd.Timestamp('2020-12-01'),INITIAL)]+list(zip(g.date,g.equity))
    peak=INITIAL;peakday=pts[0][0];open_day=None;done=[]
    for d,v in pts[1:]:
        if v>=peak-1e-9:
            if open_day is not None: done.append((open_day,d,(d-open_day).days));open_day=None
            if v>peak+1e-9:peak=v;peakday=d
        elif open_day is None:open_day=peakday
    longest=max(done,key=lambda x:x[2]);end=pts[-1][0]
    return (str(longest[0].date()),str(longest[1].date()),longest[2],open_day is not None,
            str(open_day.date()) if open_day is not None else '',(end-open_day).days if open_day is not None else 0)

def main():
    files=[B/'protocol.json',B/'protocol.sha256',SRC/'equity.csv',SRC/'trades.csv',SRC/'actions.csv',EV/'phase-metrics.csv',EV/'annual-metrics.csv',EV/'recovery.csv',EV/'profit-attribution.csv',B/'charts/drawdown-data.csv']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert before[str(B/'protocol.json')]==(B/'protocol.sha256').read_text().split()[0]
    eq=pd.read_csv(SRC/'equity.csv',parse_dates=['date']);tr=pd.read_csv(SRC/'trades.csv',parse_dates=['date'],dtype={'symbol':str});ac=pd.read_csv(SRC/'actions.csv',parse_dates=['date'])
    phases=pd.read_csv(EV/'phase-metrics.csv'); annual=pd.read_csv(EV/'annual-metrics.csv'); rec=pd.read_csv(EV/'recovery.csv').fillna(''); attrib=pd.read_csv(EV/'profit-attribution.csv'); chart=pd.read_csv(B/'charts/drawdown-data.csv')
    failures=[];checks=defaultdict(int);calc_phase=[];calc_annual=[];calc_rec=[];calc_attr=[]
    windows={'early':('2020-12-01','2024-12-31'),'late':('2025-01-01','2026-06-30'),'full':('2020-12-01','2026-06-30')}
    for aid,g in eq.groupby('account_id'):
        g=g.sort_values('date');tt=tr[tr.account_id==aid]
        for name,(lo,hi) in windows.items():
            q=g[(g.date>=lo)&(g.date<=hi)];prior=g[g.date<lo];base=INITIAL if name!='late' else float(prior.iloc[-1].equity);baseday=pd.Timestamp(lo) if name!='late' else prior.iloc[-1].date
            vals=np.r_[base,q.equity];dd=float(np.min(vals/np.maximum.accumulate(vals)-1));days=(pd.Timestamp(hi)-baseday).days;end=float(q.iloc[-1].equity);qt=tt[(tt.date>=lo)&(tt.date<=hi)]
            calc_phase.append([aid,name,base,end,end/base-1,(end/base)**(YEAR/days)-1,dd,q.exposure.mean(),q.iloc[-1].exposure,q.equity.mean(),qt.notional.sum(),qt.notional.sum()/q.equity.mean(),qt.fee.sum(),len(qt)])
        for yr,q in g.groupby(g.date.dt.year):
            prior=g[g.date<q.iloc[0].date];base=INITIAL if prior.empty else float(prior.iloc[-1].equity);qt=tt[tt.date.dt.year==yr]
            calc_annual.append([aid,yr,base,float(q.iloc[-1].equity),float(q.iloc[-1].equity)/base-1,q.exposure.mean(),q.iloc[-1].exposure,q.equity.mean(),qt.notional.sum(),qt.notional.sum()/q.equity.mean(),qt.fee.sum(),len(qt)])
        rr=recovery(g);calc_rec.append([aid,*rr])
        # Moving-average cost bookkeeping; fees remain a separate account expense.
        units=defaultdict(float);basis=defaultdict(float);realized=0.;aa=ac[ac.account_id==aid]
        for day in sorted(set(tt.date)|set(aa.date)):
            for r in aa[aa.date==day].itertuples():
                if r.event=='split':units[r.event_id.split('-')[0]]*=float(r.amount)
            for r in tt[tt.date==day].itertuples():
                s=str(r.symbol)
                if r.side=='buy':units[s]+=r.qty;basis[s]+=r.notional
                else:
                    avg=basis[s]/units[s];removed=avg*r.qty;realized+=r.notional-removed;units[s]-=r.qty;basis[s]-=removed
                    if abs(units[s])<1e-8:units[s]=basis[s]=0.
        unit_cols={c[6:]:float(g.iloc[-1][c]) for c in g if c.startswith('units_')};unreal=float(g.iloc[-1].market_value)-sum(basis.values());div=float(aa[aa.event=='receivable'].amount.sum());fees=float(tt.fee.sum());net=realized+unreal+div-fees
        if max(abs(units[s]-unit_cols.get(s,0)) for s in units)>1e-7:failures.append({'type':'ending_units','account':aid})
        calc_attr.append([aid,realized,unreal,div,fees,net,float(g.iloc[-1].equity)-INITIAL,sum(basis.values()),sum(v>0 for v in units.values())])
    cp=pd.DataFrame(calc_phase,columns=['account_id','window','starting_equity','ending_equity','cumulative_return','annualized_return','local_max_drawdown','average_exposure','ending_exposure','average_equity','two_sided_traded_notional','turnover_over_average_equity','fees','trade_rows'])
    ca=pd.DataFrame(calc_annual,columns=['account_id','year','starting_equity','ending_equity','return','average_exposure','year_end_exposure','average_equity','two_sided_traded_notional','turnover_over_average_equity','fees','trade_rows'])
    cr=pd.DataFrame(calc_rec,columns=['account_id','longest_peak_date','longest_recovery_date','longest_recovery_days','unrecovered_at_end','end_unrecovered_peak_date','end_unrecovered_days'])
    ct=pd.DataFrame(calc_attr,columns=['account_id','realized_price_pnl','ending_unrealized_price_pnl','earned_dividends','fees','attributed_net_profit','account_net_profit','ending_cost_basis','ending_units_symbols'])
    def compare(left,right,keys,cols,label,tol=1e-8):
        z=left.merge(right,on=keys,suffixes=('_calc','_reported'));checks[label]=len(z)
        if len(z)!=len(left) or len(z)!=len(right):failures.append({'type':label+'_rows'})
        for c in cols:
            bad=(z[c+'_calc'].astype(float)-z[c+'_reported'].astype(float)).abs()>tol
            if bad.any():failures.append({'type':label,'column':c,'max_diff':float((z[c+'_calc']-z[c+'_reported']).abs().max())})
    compare(cp,phases,['account_id','window'],[c for c in cp if c not in ('account_id','window')],'phase')
    compare(ca,annual,['account_id','year'],[c for c in ca if c not in ('account_id','year')],'annual')
    compare(ct,attrib,['account_id'],[c for c in ct if c!='account_id'],'attribution',1e-6)
    mr=cr.merge(rec,on='account_id',suffixes=('_calc','_reported'));checks['recovery']=len(mr)
    for _,r in mr.iterrows():
        for c in cr.columns[1:]:
            a=r[c+'_calc'];b=r[c+'_reported']
            if str(a).lower()!=str(b).lower() and not (c=='end_unrecovered_peak_date' and str(a)=='' and str(b)==''):
                failures.append({'type':'recovery','account':r.account_id,'column':c,'calc':str(a),'reported':str(b)})
    # Chart must equal independently computed running drawdown and have identical minima.
    for aid,g in eq.groupby('account_id'):
        vals=g.sort_values('date').equity.to_numpy();calc=vals/np.maximum.accumulate(np.r_[INITIAL,vals])[1:]-1;q=chart[chart.account_id==aid].sort_values('date');checks['chart_rows']+=len(q)
        if len(q)!=len(calc) or np.max(np.abs(q.drawdown.to_numpy()-calc))>1e-12:failures.append({'type':'chart','account':aid})
        reported=float(phases[(phases.account_id==aid)&(phases.window=='full')].local_max_drawdown.iloc[0])
        if not close_enough(calc.min(),reported):failures.append({'type':'chart_min','account':aid})
    expected_end={'equal-fee0.001':0,'equal-fee0.002':0,'no_exit_100-fee0.001':36,'no_exit_100-fee0.002':36,'no_exit_75-fee0.001':36,'no_exit_75-fee0.002':36,'fast_reentry_exit-fee0.001':5,'fast_reentry_exit-fee0.002':5}
    if dict(zip(cr.account_id,cr.end_unrecovered_days))!=expected_end:failures.append({'type':'specified_end_recovery'})
    cp.to_csv(HERE/'independent-phase.csv',index=False);ca.to_csv(HERE/'independent-annual.csv',index=False);cr.to_csv(HERE/'independent-recovery.csv',index=False);ct.to_csv(HERE/'independent-attribution.csv',index=False)
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};assert before==after
    result={'passed':not failures,'principles_version':'v1.0','checks':dict(checks),'failures':failures,'source_hashes':before};(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['passed'],dict(checks),len(failures))

if __name__=='__main__':main()
