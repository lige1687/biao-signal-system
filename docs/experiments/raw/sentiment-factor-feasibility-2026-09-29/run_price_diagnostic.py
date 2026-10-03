"""Single frozen, price-only historical diagnostic. No downloader/production imports."""
from pathlib import Path
import datetime as dt
import hashlib, json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = Path('/Users/yongbiaoli/.lei_signal_lab/cache/sentiment_research_2026-09')
protocol_path = HERE/'price-diagnostic-protocol.json'
protocol = json.loads(protocol_path.read_text())
for mname in ['accepted-source-manifest.json','authority-manifest.json','calculation-manifest.json']:
    for f in json.loads((HERE/mname).read_text())['files']:
        assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()==f['sha256'], f['path']
out = HERE/'run-01'
assert not out.exists(), 'Never overwrite a previous run.'
out.mkdir()
start,end = map(pd.Timestamp,protocol['observation_range'])
results={}
for asset in ['SPY','510300']:
    fn,col = ('px_SPY.csv','Date') if asset=='SPY' else ('apx_510300_SS.csv','date')
    px = pd.read_csv(SRC/fn,parse_dates=[col]).rename(columns={col:'date'}).sort_values('date').set_index('date')
    assert not px.index.duplicated().any() and px.Close.gt(0).all()
    c = px.Close
    px['r20'] = 100*(c/c.shift(20)-1)
    px['dma200'] = 100*(c/c.rolling(200,min_periods=200).mean()-1)
    px['rv20'] = 100*c.pct_change(fill_method=None).rolling(20,min_periods=20).std(ddof=1)*np.sqrt(20)
    if asset=='SPY':
        src = pd.read_csv(HERE/'aaii-candidate-values.csv',parse_dates=['date'])[['date','spread_pp']].rename(columns={'date':'source_date','spread_pp':'x'})
    else:
        src = pd.read_csv(HERE/'margin-candidate-values.csv',parse_dates=['date'])[['date','change20_pct']].rename(columns={'date':'source_date','change20_pct':'x'})
    rows=[]
    for r in src.itertuples(index=False):
        assumed = r.source_date + pd.Timedelta(days=7)
        i = int(px.index.searchsorted(assumed,side='right'))
        row={'asset':asset,'source_date':r.source_date,'assumed_available_date':assumed,'actual_available_at':None,'x':r.x,'eligible':False,'exclusion':None}
        if i>=len(px): row['exclusion']='no_quote_after_assumed_availability';rows.append(row);continue
        t=px.index[i];row['t']=t;row['price_index']=i
        if not start<=t<=end: row['exclusion']='t_outside_range';rows.append(row);continue
        row.update({k:px.iloc[i][k] for k in ['r20','dma200','rv20']})
        if pd.isna(r.x): row['exclusion']='factor_window_missing';rows.append(row);continue
        if any(pd.isna(row[k]) for k in ['r20','dma200','rv20']): row['exclusion']='baseline_warmup';rows.append(row);continue
        if i+21>=len(px) or px.index[i+21]>end: row['exclusion']='target_end_outside_range';rows.append(row);continue
        first,last=px.index[i+1],px.index[i+21]
        row.update({'target_start':first,'target_end':last,'target_first_close':float(c.iloc[i+1]),'target_last_close':float(c.iloc[i+21]),'y':100*(c.iloc[i+21]/c.iloc[i+1]-1),'downside':100*(c.iloc[i+1:i+22].min()/c.iloc[i+1]-1),'eligible':True})
        rows.append(row)
    obs=pd.DataFrame(rows)
    superseded=obs.t.notna() & obs.duplicated('t',keep='last')
    obs.loc[superseded,'eligible']=False
    obs.loc[superseded,'exclusion']='superseded_at_t'
    obs.to_csv(out/f'{asset}-observations.csv',index=False)
    valid=obs[obs.eligible].copy().sort_values('t')
    assert not valid.source_date.duplicated().any()
    assert not valid.t.duplicated().any()
    predictions=[];fits=[]
    for year in range(2020,2027):
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        train=valid[(valid.t<cutoff)&(valid.target_end<cutoff)]
        test=valid[valid.t.dt.year.eq(year)]
        assert len(train)>50 and len(test)>0
        p=test.copy()
        for name,features in [('I',[]),('X',['x']),('B',['r20','dma200','rv20']),('BX',['r20','dma200','rv20','x'])]:
            tr=np.ones((len(train),len(features)+1));te=np.ones((len(test),len(features)+1))
            mean=train[features].mean();scale=train[features].std(ddof=0)
            if features:
                assert scale.gt(0).all()
                tr[:,1:]=(train[features]-mean)/scale;te[:,1:]=(test[features]-mean)/scale
            assert np.linalg.matrix_rank(tr)==tr.shape[1]
            beta=np.linalg.lstsq(tr,train.y.to_numpy(),rcond=None)[0]
            p['pred_'+name]=te@beta
            fits.append({'year':year,'model':name,'train_rows':len(train),'train_label_end_max':str(train.target_end.max().date()),'features':features,'mean':mean.to_dict(),'scale':scale.to_dict(),'beta':beta.tolist()})
        predictions.append(p)
    pred=pd.concat(predictions).reset_index(drop=True)
    assert len(fits)==28
    pred.to_csv(out/f'{asset}-predictions.csv',index=False)
    def score(d):
        mse={name:float(np.mean((d.y-d['pred_'+name])**2)) for name in ['I','X','B','BX']}
        return {'rows':len(d),'up_fraction':float(d.y.gt(0).mean()),'mean_y_pp':float(d.y.mean()),'median_y_pp':float(d.y.median()),'mean_downside_pp':float(d.downside.mean()),'mse_pp_squared':mse,'rmse_pp':{k:float(np.sqrt(v)) for k,v in mse.items()},'increment_mse_pp_squared':mse['B']-mse['BX'],'improvement_pct':100*(1-mse['BX']/mse['B'])}
    overall=score(pred);byyear={str(y):score(g) for y,g in pred.groupby(pred.t.dt.year)}
    leave={str(y):score(pred[~pred.t.dt.year.eq(y)])['improvement_pct'] for y in range(2020,2027)}
    err=np.column_stack([(pred.y-pred['pred_'+k]).to_numpy()**2 for k in ['I','X','B','BX']])
    n=len(err);block=26 if asset=='SPY' else 130
    rng=np.random.default_rng(20260929);draws=[]
    for _ in range(2000):
        starts=rng.integers(0,n-block+1,size=int(np.ceil(n/block)))
        indices=np.concatenate([np.arange(k,k+block) for k in starts])[:n]
        es=err[indices].mean(axis=0);draws.append(100*(1-es[3]/es[2]))
    interval=np.quantile(draws,[.025,.975]).tolist()
    # Targets overlap when adjacent start/end date intervals intersect.
    overlap=(pred.target_start<=pred.target_end.shift(1)).iloc[1:]
    results[asset]={'overall':overall,'by_year':byyear,'leave_one_evaluation_year_out_improvement_pct':leave,'uncertainty_improvement_pct_95range':interval,'block_rows':block,'fit_count':len(fits),'source_rows':len(src),'valid_all_rows':len(valid),'excluded_counts':obs.exclusion.value_counts().to_dict(),'evaluation_unique_dates':int(pred.t.nunique()),'adjacent_target_overlap_rows':int(overlap.sum()),'adjacent_target_pairs':len(overlap),'assumed_delay_days':7,'width_increment':'not_evaluated','strategy_E':'not_evaluated'}
    (out/f'{asset}-fits.json').write_text(json.dumps(fits,ensure_ascii=False,indent=2))
    pd.DataFrame({'improvement_pct':draws}).to_csv(out/f'{asset}-uncertainty-draws.csv',index=False)

(out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
bindings=[]
for f in [protocol_path,Path(__file__),HERE/'aaii-candidate-values.csv',HERE/'margin-candidate-values.csv']:
    b=f.read_bytes();bindings.append({'path':str(f.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(out/'manifest.json').write_text(json.dumps({'run_id':'20260929-r1-price01','created_at':dt.datetime.now(dt.timezone.utc).isoformat(),'files':bindings,'input_manifests':['../accepted-source-manifest.json','../authority-manifest.json','../calculation-manifest.json'],'actual_model_fits':56,'no_production_imports':True},ensure_ascii=False,indent=2))
print(json.dumps({a:{'overall':r['overall'],'range':r['uncertainty_improvement_pct_95range'],'leave_year_out':r['leave_one_evaluation_year_out_improvement_pct']} for a,r in results.items()},ensure_ascii=False,indent=2))
