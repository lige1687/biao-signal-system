"""Daily/calendar attribution of already fixed outcomes; no new signals or strategy."""
from pathlib import Path
import csv,gzip,hashlib,json
import numpy as np
import pandas as pd

P=Path(__file__).resolve().parent; S=P.parent/'research-sixth-2026-09-08'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    lock=json.loads((P/'calendar-lock.json').read_text())
    assert all(sha(Path(k))==v for k,v in lock['files'].items())
    d=pd.read_csv(S/'atr-opportunity-ledger.csv')
    d=d[(d.fee=='amount_5bp')&d.arm.isin(['base','buffer'])].copy()
    assert len(d)==9236 and not d.duplicated(['key','arm','sizing']).any()
    manifest=json.loads((S/'full-baseline-review/input-manifest.json').read_text())
    prices={}
    for x in manifest['files']:
        if x['source'].endswith('.bars.parquet'):
            p=S/'full-baseline-review'/x['copy'];assert sha(p)==x['sha256']
            b=pd.read_parquet(p);b.index=pd.to_datetime(b.index)
            assert b.index.is_monotonic_increasing and not b.index.duplicated().any()
            prices[p.name.removesuffix('.bars.parquet')]=b
    start=pd.Timestamp(d[d.entered].entry_date.min());end=pd.Timestamp(d[d.entered].valuation_date.max())
    dates=pd.date_range(start,end,freq='D'); n=len(dates); datepos={t:i for i,t in enumerate(dates)}
    keys=sorted(set(zip(d.module,d.sizing,d.arm)))
    arrays={key:{'delta':np.zeros(n),'exposure':np.zeros(n),'active':np.zeros(n),'entries':np.zeros(n)} for key in keys}
    checks=[]; journal_count=0
    with gzip.open(P/'calendar-daily-opportunity-ledger.csv.gz','wt',newline='') as f:
        writer=csv.writer(f);writer.writerow(['key','module','arm','sizing','date','budget_value','change','is_exit'])
        for r in d.to_dict('records'):
            if not r['entered']:
                checks.append({'key':r['key'],'arm':r['arm'],'sizing':r['sizing'],'entered':False,'sum_daily_changes':0.,'expected':r['budget_return'],'difference':-r['budget_return']});continue
            b=prices[r['symbol']]; ep=pd.Timestamp(r['entry_date']);endp=pd.Timestamp(r['valuation_date'])
            assert ep in b.index and endp in b.index
            q=float(r['quantity_proxy']);buy=q*r['entry_price']*.0005;cash=1-q*r['entry_price']-buy
            assert cash>=-1e-12
            sub=b.loc[ep:endp,'close'].copy()
            if r['closed']:sub=sub.iloc[:-1]
            assert np.isfinite(sub.to_numpy()).all()
            values=cash+q*sub
            if r['closed']:
                value=cash+q*r['terminal_price']*(1-.0005)
                values.loc[endp]=value
            assert len(values)>0 and abs(values.iloc[-1]-1-r['budget_return'])<1e-10
            changes=values.diff();changes.iloc[0]=values.iloc[0]-1
            total=float(changes.sum());err=total-r['budget_return'];assert abs(err)<1e-10
            key=(r['module'],r['sizing'],r['arm']);arr=arrays[key]
            idx=np.array([datepos[t] for t in values.index]);arr['delta'][idx]+=changes.to_numpy()
            arr['entries'][datepos[ep]]+=1
            # Exposure carries only through the actual holding period, not beyond an unknown tail.
            exposed_end=endp-pd.Timedelta(days=1) if r['closed'] else endp
            exposure_dates=pd.date_range(ep,exposed_end,freq='D')
            if len(exposure_dates):
                mark=sub.reindex(exposure_dates).ffill();assert mark.notna().all()
                xi=np.array([datepos[t] for t in exposure_dates]);arr['exposure'][xi]+=q*mark.to_numpy();arr['active'][xi]+=1
            for t,v,ch in zip(values.index,values.to_numpy(),changes.to_numpy()):
                writer.writerow([r['key'],r['module'],r['arm'],r['sizing'],str(t.date()),v,ch,bool(r['closed'] and t==endp)])
            journal_count+=len(values)
            checks.append({'key':r['key'],'arm':r['arm'],'sizing':r['sizing'],'entered':True,'sum_daily_changes':total,'expected':r['budget_return'],'difference':err})
    counts={'A':1521,'B':563,'C':225};monthly=[];yearly=[];quarterly=[]
    for (mod,sizing,arm),arr in arrays.items():
        f=pd.DataFrame(arr,index=dates);f['year']=f.index.year;f['month']=f.index.to_period('M').astype(str);f['quarter']=f.index.to_period('Q').astype(str)
        for group,target in [('month',monthly),('year',yearly),('quarter',quarterly)]:
            for label,g in f.groupby(group,sort=True):
                target.append({'module':mod,'sizing':sizing,'arm':arm,group:label,'budget_change_sum':float(g.delta.sum()),'per_opportunity_contribution':float(g.delta.sum()/counts[mod]),'average_position_fraction':float(g.exposure.mean()/counts[mod]),'average_active_opportunities':float(g.active.mean()),'entries':int(g.entries.sum()),'calendar_days':len(g)})
    pd.DataFrame(checks).to_csv(P/'calendar-opportunity-reconciliation.csv',index=False)
    for filename,rows in [('calendar-monthly.csv',monthly),('calendar-yearly.csv',yearly),('calendar-quarterly.csv',quarterly)]:pd.DataFrame(rows).to_csv(P/filename,index=False)
    allstats=json.loads((S/'atr-results.json').read_text())['stats'];summary=[]
    ys=pd.DataFrame(yearly)
    for mod in counts:
        for sizing in ['same_budget','same_planned_risk']:
            y=ys[(ys.module==mod)&(ys.sizing==sizing)].pivot(index='year',columns='arm',values='per_opportunity_contribution')
            for arm in ['base','buffer']:
                expected=next(x['mean_budget_return'] for x in allstats if x['module']==mod and x['sizing']==sizing and x['arm']==arm and x['fee']=='amount_5bp')
                assert abs(float(y[arm].sum())-expected)<1e-10
            change=y.buffer-y.base;total=float(change.sum());loo=[{'omitted_year':int(yr),'contribution_removed':float(v),'remaining_contribution':total-float(v),'sign_reversed':bool(total*(total-float(v))<0)} for yr,v in change.items()]
            summary.append({'module':mod,'sizing':sizing,'all_years_delta':total,'positive_years':int((change>1e-12).sum()),'negative_years':int((change<-1e-12).sum()),'zero_years':int((abs(change)<=1e-12).sum()),'leave_one_year_out':loo})
    result={'scope':'post hoc calendar contribution diagnosis; not a portfolio or future probability','window':[str(start.date()),str(end.date())],'opportunities':2309,'views':4,'checked_rows':len(checks),'daily_journal_rows':journal_count,'maximum_per_row_error':max(abs(x['difference']) for x in checks),'all_twelve_totals_match_sixth':True,'series':summary,'code_sha256':sha(Path(__file__)),'daily_journal_sha256':sha(P/'calendar-daily-opportunity-ledger.csv.gz'),'monthly_sha256':sha(P/'calendar-monthly.csv')}
    (P/'calendar-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='series'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
