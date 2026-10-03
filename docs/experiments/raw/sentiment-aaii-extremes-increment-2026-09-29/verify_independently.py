"""Controller: independent stdlib check, no execution-script imports."""
import bisect
import csv
import datetime as dt
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / 'executor/run-01'
prices = list(csv.DictReader((HERE / 'inputs/px_SPY.csv').open()))
dates = [dt.date.fromisoformat(r['Date']) for r in prices]
close = [float(r['Close']) for r in prices]
surveys = {r['date']: r for r in csv.DictReader((HERE / 'inputs/aaii-candidate-values.csv').open())}
end = dt.date(2026, 6, 30)
baseline = {}
max_value_error = 0.0
max_beta_error = 0.0
max_prediction_error = 0.0
all_scores = {}
fit_count = 0
draw_checks = {}

def quantile(values, q):
    v=sorted(values); z=(len(v)-1)*q; k=math.floor(z)
    return v[k]+(v[min(k+1,len(v)-1)]-v[k])*(z-k)

def approx(a, b, tol=2e-8):
    global max_value_error
    err = abs(float(a) - float(b))
    max_value_error = max(max_value_error, err)
    assert err <= tol * max(1, abs(float(b))), (a, b, err)

def base(i):
    if i not in baseline:
        rr = [close[k]/close[k-1]-1 for k in range(i-19, i+1)]
        avg = sum(rr)/20
        baseline[i] = dict(r20=100*(close[i]/close[i-20]-1),
            r63=100*(close[i]/close[i-63]-1),
            dma200=100*(close[i]/(sum(close[i-199:i+1])/200)-1),
            dd252=100*(close[i]/max(close[i-251:i+1])-1),
            rv20=100*math.sqrt(sum((v-avg)**2 for v in rr)/19)*math.sqrt(20))
    return baseline[i]

def solve(A, b):
    mat = [list(row)+[v] for row,v in zip(A,b)]
    n = len(b)
    for k in range(n):
        pivot=max(range(k,n),key=lambda j:abs(mat[j][k]))
        mat[k],mat[pivot]=mat[pivot],mat[k]
        assert abs(mat[k][k])>1e-10
        fac=mat[k][k]
        mat[k]=[v/fac for v in mat[k]]
        for j in range(n):
            if j != k:
                fac=mat[j][k]
                mat[j]=[v-fac*w for v,w in zip(mat[j],mat[k])]
    return [row[-1] for row in mat]

for h in [5,20,60,120,252]:
    obs=list(csv.DictReader((RUN/f'observations-h{h}.csv').open()))
    assert len(obs)==len(surveys)
    expected_sources=set()
    for source_date in surveys:
        a=dt.date.fromisoformat(source_date)+dt.timedelta(days=7)
        i=bisect.bisect_right(dates,a)
        if i<len(dates) and i>=251 and dt.date(1995,1,1)<=dates[i]<=end:
            if i+1+h<len(dates) and dates[i+1+h]<=end:
                expected_sources.add(source_date)
    eligible=[]
    for r in obs:
        if str(r['eligible']).lower() not in ('true','1'): continue
        sr=surveys[r['source_date']]
        a=dt.date.fromisoformat(r['source_date'])+dt.timedelta(days=7)
        i=bisect.bisect_right(dates,a)
        assert dates[i].isoformat()==r['t']
        assert dates[i+1].isoformat()==r['target_start']
        assert dates[i+1+h].isoformat()==r['target_end']
        assert dates[i+1+h] <= end
        assert dates[i]>=dt.date(1995,1,1)
        x=100*(float(sr['bullish'])-float(sr['bearish']))
        approx(r['x'],x); approx(r['lo'],max(-25-x,0)); approx(r['hi'],max(x-25,0))
        for k,v in base(i).items(): approx(r[k],v)
        y=100*(close[i+1+h]/close[i+1]-1); approx(r['y'],y)
        independent={**base(i),'x':x,'lo':max(-25-x,0),'hi':max(x-25,0),'y':y,
                     't':dates[i],'target_end':dates[i+1+h],'source_date':r['source_date']}
        eligible.append(independent)
    assert len({r['t'] for r in eligible})==len(eligible)
    assert {r['source_date'] for r in eligible}==expected_sources
    pred=list(csv.DictReader((RUN/f'predictions-h{h}.csv').open()))
    assert {r['source_date'] for r in pred}=={r['source_date'] for r in eligible if r['t']>=dt.date(2010,1,1)}
    fits=json.loads((RUN/f'fits-h{h}.json').read_text())
    if isinstance(fits,dict): fits=fits['fits']
    for f in fits:
        year=int(f['year']); cutoff=dt.date(year,1,1)
        train=[r for r in eligible if r['t']<cutoff and r['target_end']<cutoff]
        assert len(train)==int(f['train_rows'])
        assert max(r['target_end'] for r in train).isoformat()==f['train_label_end_max'][:10]
        keys=f['features']; means={k:sum(r[k] for r in train)/len(train) for k in keys}
        scales={k:math.sqrt(sum((r[k]-means[k])**2 for r in train)/len(train)) for k in keys}
        fit_means=f['mean'] if isinstance(f['mean'],dict) else dict(zip(keys,f['mean']))
        fit_scales=f['scale'] if isinstance(f['scale'],dict) else dict(zip(keys,f['scale']))
        for k in keys: approx(fit_means[k],means[k]); approx(fit_scales[k],scales[k])
        m=len(keys)+1; A=[[0.0]*m for _ in range(m)]; b=[0.0]*m
        for r in train:
            x=[1.0]+[(r[k]-means[k])/scales[k] for k in keys]
            for j in range(m):
                b[j]+=x[j]*r['y']
                for k in range(m): A[j][k]+=x[j]*x[k]
        beta=solve(A,b)
        err=max(abs(a-b) for a,b in zip(beta,f['beta']));max_beta_error=max(max_beta_error,err)
        assert err<1e-7,(h,f['model'],year,err)
        rows=[r for r in pred if dt.date.fromisoformat(r['t']).year==year]
        assert rows
        for r in rows:
            vals=next(v for v in eligible if v['source_date']==r['source_date'])
            expected=beta[0]+sum(beta[j+1]*(vals[k]-means[k])/scales[k] for j,k in enumerate(keys))
            err=abs(expected-float(r['pred_'+f['model']]));max_prediction_error=max(max_prediction_error,err)
            assert err<1e-6,(h,year,f['model'],err)
        fit_count+=1
    mse={k:sum((float(r['y'])-float(r['pred_'+k]))**2 for r in pred)/len(pred)
         for k in ['I','X','XE','B','BX','BXE']}
    all_scores[str(h)]={'rows':len(pred),'rmse_pp':{k:math.sqrt(v) for k,v in mse.items()},
        'improvement_pct':100*(1-mse['BXE']/mse['B']),
        'linear_improvement_pct':100*(1-mse['BX']/mse['B']),
        'extreme_over_linear_improvement_pct':100*(1-mse['BXE']/mse['BX'])}
    rr=json.loads((RUN/'results.json').read_text())['horizons'][str(h)]
    assert len(pred)==rr['overall']['n']
    for k,v in mse.items(): approx(v,rr['overall']['mse'][k])
    draws=list(csv.DictReader((RUN/f'draws-h{h}.csv').open())); assert len(draws)==2000
    for draw_index in [0,999,1999]:
        draw=draws[draw_index]; starts=json.loads(draw['block_starts'])
        assert all(0<=k<=len(pred)-52 for k in starts)
        ix=[k+j for k in starts for j in range(52)][:len(pred)]; assert len(ix)==len(pred)
        re={k:sum((float(pred[j]['y'])-float(pred[j]['pred_'+k]))**2 for j in ix)/len(ix) for k in mse}
        for k,v in re.items(): approx(v,draw['mse_'+k])
    intervals={}
    for a,b in [('BXE','B'),('BX','B'),('BXE','BX')]:
        pair=a+'_vs_'+b; values=[float(d['improvement_'+pair]) for d in draws]
        low,high=quantile(values,.025),quantile(values,.975)
        approx(low,rr['paired_block_intervals'][pair]['p2_5']); approx(high,rr['paired_block_intervals'][pair]['p97_5'])
        intervals[pair]=[low,high]
    draw_checks[str(h)]={'draw_count':len(draws),'recomputed_draws':[0,999,1999],'all_saved_draw_interval_endpoints':intervals}

out={'passed':True,'no_executor_imports':True,'all_eligible_values_max_error':max_value_error,
     'normal_equation_beta_max_error':max_beta_error,'predictions_max_error':max_prediction_error,
     'independently_verified_fit_count':fit_count,'headline_recalculation':all_scores,
     'block_draw_checks':draw_checks,
     'scope':'All eligible values/time/labels, complete eligibility population, all fits/headline metrics recomputed; three draws per horizon reconstructed and all interval endpoints checked. Not new independent market evidence.'}
(HERE/'independent-review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
