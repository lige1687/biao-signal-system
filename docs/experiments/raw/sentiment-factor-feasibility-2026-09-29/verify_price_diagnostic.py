"""Independent standard-library checks from original CSV and saved observations.

Does not import the calculator, pandas or numpy; does not fit new hypotheses.
"""
from pathlib import Path
import bisect, csv, datetime as dt, hashlib, json, math, statistics

HERE=Path(__file__).resolve().parent
SRC=Path('/Users/yongbiaoli/.lei_signal_lab/cache/sentiment_research_2026-09')
OUT=HERE/'run-01'
read=lambda p:list(csv.DictReader(Path(p).open()))
date=lambda s:dt.date.fromisoformat(s[:10])
results=json.loads((OUT/'results.json').read_text())
report={}

def solve(a,b):
    n=len(b);m=[row[:]+[v] for row,v in zip(a,b)]
    for i in range(n):
        k=max(range(i,n),key=lambda k:abs(m[k][i]))
        m[i],m[k]=m[k],m[i]
        assert abs(m[i][i])>1e-10
        pivot=m[i][i];m[i]=[v/pivot for v in m[i]]
        for j in range(n):
            if j!=i:
                factor=m[j][i];m[j]=[v-factor*w for v,w in zip(m[j],m[i])]
    return [row[-1] for row in m]

for asset in ['SPY','510300']:
    path,col=('px_SPY.csv','Date') if asset=='SPY' else ('apx_510300_SS.csv','date')
    prices=read(SRC/path);ds=[date(r[col]) for r in prices];cs=[float(r['Close']) for r in prices]
    source=read(SRC/('aaii_clean.csv' if asset=='SPY' else 'margin_history.csv'))
    source={date(r['reported' if asset=='SPY' else 'date']):r for r in source}
    predictions=read(OUT/f'{asset}-predictions.csv')
    errors={k:[] for k in ['I','X','B','BX']};max_target=0.;max_x=0.;max_background=0.
    for r in predictions:
        s=date(r['source_date']);t=date(r['t']);i=bisect.bisect_right(ds,s+dt.timedelta(days=7))
        assert ds[i]==t and date(r['target_start'])==ds[i+1] and date(r['target_end'])==ds[i+21]
        assert ds[i+21]<=dt.date(2026,6,30)
        y=100*(cs[i+21]/cs[i+1]-1)
        downside=100*(min(cs[i+1:i+22])/cs[i+1]-1)
        max_target=max(max_target,abs(y-float(r['y'])),abs(downside-float(r['downside'])))
        if asset=='SPY':
            x=100*(float(source[s]['bullish'])-float(source[s]['bearish']))
        else:
            j=bisect.bisect_left(ds,s);assert ds[j]==s and j>=20
            assert all(d in source and float(source[d]['RZYE'])>0 for d in ds[j-20:j+1])
            x=100*(float(source[s]['RZYE'])/float(source[ds[j-20]]['RZYE'])-1)
        max_x=max(max_x,abs(x-float(r['x'])))
        b=[100*(cs[i]/cs[i-20]-1),100*(cs[i]/statistics.mean(cs[i-199:i+1])-1),100*statistics.stdev([cs[k]/cs[k-1]-1 for k in range(i-19,i+1)])*math.sqrt(20)]
        max_background=max(max_background,max(abs(v-float(r[k])) for v,k in zip(b,['r20','dma200','rv20'])))
        for k in errors: errors[k].append((y-float(r['pred_'+k]))**2)
    assert max(max_target,max_x,max_background)<1e-9
    mse={k:statistics.mean(v) for k,v in errors.items()}
    improvement=100*(1-mse['BX']/mse['B'])
    assert max(abs(mse[k]-results[asset]['overall']['mse_pp_squared'][k]) for k in mse)<1e-9
    assert abs(improvement-results[asset]['overall']['improvement_pct'])<1e-9
    assert len(predictions)==results[asset]['overall']['rows']
    assert len(set(r['t'] for r in predictions))==len(predictions)
    obs=[r for r in read(OUT/f'{asset}-observations.csv') if r['eligible']=='True']
    fits=json.loads((OUT/f'{asset}-fits.json').read_text())
    max_beta=0.;fold_checks=[]
    for f in fits:
        cutoff=dt.date(f['year'],1,1)
        train=[r for r in obs if date(r['t'])<cutoff and date(r['target_end'])<cutoff]
        assert len(train)==f['train_rows'] and max(date(r['target_end']) for r in train)<cutoff
        features=f['features'];mean={k:statistics.mean(float(r[k]) for r in train) for k in features}
        scale={k:statistics.pstdev(float(r[k]) for r in train) for k in features}
        design=[[1.]+[(float(r[k])-mean[k])/scale[k] for k in features] for r in train]
        n=len(features)+1
        a=[[math.fsum(row[i]*row[j] for row in design) for j in range(n)] for i in range(n)]
        b=[math.fsum(row[i]*float(r['y']) for row,r in zip(design,train)) for i in range(n)]
        beta=solve(a,b)
        diff=max(abs(x-y) for x,y in zip(beta,f['beta']));max_beta=max(max_beta,diff)
        assert diff<1e-8
        fold_checks.append({'year':f['year'],'model':f['model'],'train_rows':len(train),'max_beta_difference':diff})
    draws=sorted(float(r['improvement_pct']) for r in read(OUT/f'{asset}-uncertainty-draws.csv'))
    def quantile(p):
        v=(len(draws)-1)*p;i=int(v);w=v-i
        return draws[i]*(1-w)+draws[min(i+1,len(draws)-1)]*w
    bounds=[quantile(.025),quantile(.975)]
    assert max(abs(a-b) for a,b in zip(bounds,results[asset]['uncertainty_improvement_pct_95range']))<1e-9
    by_year=[]
    for y in range(2020,2027):
        inds=[i for i,r in enumerate(predictions) if date(r['t']).year==y]
        imp=100*(1-statistics.mean(errors['BX'][i] for i in inds)/statistics.mean(errors['B'][i] for i in inds))
        assert abs(imp-results[asset]['by_year'][str(y)]['improvement_pct'])<1e-9
        by_year.append({'year':y,'rows':len(inds),'improvement_pct':imp})
    report[asset]={'rows':len(predictions),'independent_mse_pp_squared':mse,'improvement_pct':improvement,'max_raw_x_difference':max_x,'max_raw_target_difference':max_target,'max_raw_baseline_difference':max_background,'independent_linear_system_max_beta_difference':max_beta,'all_28_fold_fits_verified':True,'uncertainty_endpoints_verified_not_new_draws':bounds,'by_year':by_year}

hashes=[]
for name in ['accepted-source-manifest.json','authority-manifest.json','calculation-manifest.json']:
    for f in json.loads((HERE/name).read_text())['files']:
        actual=hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()
        hashes.append({'path':f['path'],'match':actual==f['sha256']})
assert all(f['match'] for f in hashes)
report['source_hashes_all_match']=True
report['limits']=['Recalculation checks arithmetic, calendar mapping and fits; it cannot prove historical publication, revision vintages, prices, or causality.','Uncertainty endpoints are independently checked from saved draws; draws use the declared calculation code, not an independent new method.']
(HERE/'independent-price-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
