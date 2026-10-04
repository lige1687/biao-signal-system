"""Fixed revised-history survey combination; never a live/as-of trading test."""
import argparse, hashlib, json, os, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
INPUTS={
 'prices':'docs/experiments/raw/sentiment-naaim-public-window-2026-09-30/inputs/px_SPY.csv',
 'aaii':'docs/experiments/raw/sentiment-aaii-extremes-increment-2026-09-29/inputs/aaii-candidate-values.csv',
 'naaim':'docs/experiments/raw/sentiment-naaim-public-window-2026-09-30/inputs/naaim-official-delayed.csv',
 'old_predictions':'docs/experiments/raw/sentiment-naaim-public-window-2026-09-30/run-01/predictions.csv',
 'breadth':'docs/experiments/raw/sentiment-short-history-2026-10-02/inputs/ma_percentage_historical.json',
}
MODELS={'A':['aaii'],'BA':['r20','aaii'],'BAN':['r20','aaii','naaim'],'BANI':['r20','aaii','naaim','interaction']}
ALL=['I','B','N','BN',*MODELS]
PAIRS=[('BAN','BN'),('BAN','BA'),('BANI','BAN'),('BAN','I'),('BANI','I'),('BAN','N'),('BANI','N')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
def match_aaii(a,dates):
    # Seven-calendar-day delay is inherited research assumption, not publication proof.
    available=a.date+pd.Timedelta(days=7)
    indices=available.searchsorted(pd.DatetimeIndex(dates),side='right')-1
    out=[]
    for d,i in zip(dates,indices):
        if i<0:out.append(None);continue
        row=a.iloc[int(i)];age=(pd.Timestamp(d)-row.date).days
        out.append(None if age>14 else (row.date,float(row.spread_pp),age))
    return out

def panel(with_y=False):
    px=pd.read_csv(ROOT/INPUTS['prices'],parse_dates=['Date']);a=pd.read_csv(ROOT/INPUTS['aaii'],parse_dates=['date']);n=pd.read_csv(ROOT/INPUTS['naaim'],parse_dates=['date'])
    for f,k in [(px,'Date'),(a,'date'),(n,'date')]:assert f[k].is_unique and f[k].is_monotonic_increasing
    assert np.allclose(a.spread_pp,100*(a.bullish-a.bearish),atol=1e-9,rtol=0)
    closes=px.Close.to_numpy();rows=[]
    for item in n.itertuples():
        t=int(px.Date.searchsorted(item.date,side='right'))
        assert t>=20 and t+21<len(px)
        assert np.isfinite(closes[t-20:t+22]).all() and (closes[t-20:t+22]>0).all()
        rows.append(dict(source_date=item.date,anchor_date=px.Date.iloc[t],target_start=px.Date.iloc[t+1],target_end=px.Date.iloc[t+21],anchor_index=t,r20=100*(closes[t]/closes[t-20]-1),naaim=float(item.naaim)))
        if with_y:rows[-1]['y']=100*(closes[t+21]/closes[t+1]-1)
    f=pd.DataFrame(rows);m=match_aaii(a,list(f.anchor_date));assert all(x is not None for x in m),'AAII missing: freeze revised common support before any fit'
    f['aaii_source_date']=[x[0] for x in m];f['aaii']=[x[1] for x in m];f['aaii_age_days']=[x[2] for x in m]
    return f,px,a

def matrix(train,test,cols):
    cols0=[x for x in cols if x!='interaction'];tr=train[cols0].to_numpy(float);te=test[cols0].to_numpy(float);interaction=None
    if 'interaction' in cols:
        x=train[['aaii','naaim']].to_numpy(float);mu=x.mean(0);scale=x.std(0);assert (scale>0).all()
        cross_tr=np.prod((x-mu)/scale,axis=1);cross_te=np.prod((test[['aaii','naaim']].to_numpy(float)-mu)/scale,axis=1)
        tr=np.column_stack([tr,cross_tr]);te=np.column_stack([te,cross_te]);interaction={'mu':mu.tolist(),'scale':scale.tolist()}
    return tr,te,interaction

def fit(x,y):
    # Same frozen NAAIM ridge formula, lambda .001; intercept unpenalized.
    mu=x.mean(0);scale=x.std(0);assert (scale>0).all()
    z=np.column_stack([np.ones(len(y)),(x-mu)/scale]);pen=np.diag([0]+[1]*x.shape[1])
    beta=np.linalg.solve(z.T@z+len(y)*.001*pen,z.T@y)
    return beta,mu,scale

def summary(f):
    return {m:dict(n=len(f),mse_pp2=float(np.mean((f['pred_'+m]-f.y)**2)),rmse_pp=float(np.sqrt(np.mean((f['pred_'+m]-f.y)**2))),mae_pp=float(np.mean(np.abs(f['pred_'+m]-f.y)))) for m in ALL}
def gain(f,c,b):return float(100*(1-np.mean((f['pred_'+c]-f.y)**2)/np.mean((f['pred_'+b]-f.y)**2)))

def preflight():
    f,px,a=panel(False);assert len(f)==131
    support={}
    for yr in [2025,2026]:
        cut=pd.Timestamp(f'{yr}-01-01');tr=f[f.target_end<cut];te=f[f.anchor_date.dt.year==yr]
        specs={}
        for name,cols in MODELS.items():
            x,_,_=matrix(tr,te,cols);z=np.column_stack([np.ones(len(x)),x]);specs[name]={'columns_including_intercept':z.shape[1],'rank':int(np.linalg.matrix_rank(z)),'constant_features':bool((x.std(0)==0).any())}
        support[str(yr)]={'train':len(tr),'eval':len(te),'train_latest_target_end':str(tr.target_end.max().date()),'eval_first':str(te.anchor_date.min().date()),'eval_last':str(te.anchor_date.max().date()),'designs':specs}
    assert [support[y]['train'] for y in support]==[49,101]
    assert [support[y]['eval'] for y in support]==[52,26]
    d=json.loads((ROOT/INPUTS['breadth']).read_text())['data'];b=pd.DataFrame({'date':[x['date'] for x in d],'b20':[x['ma_20']['percentage_above'] for x in d],'b50':[x['ma_50']['percentage_above'] for x in d]});b.date=pd.to_datetime(b.date);b=b[b.date.isin(px.Date)].copy();bm=match_aaii(a,list(b.date));b['aaii']=[np.nan if x is None else x[1] for x in bm];b['low']=(b.b20<=15)&(b.b50<=15);low=b[b.low];episodes=int((b.low&~b.low.shift(1,fill_value=False)).sum())
    source_manifest=[{'name':k,'path':v,'bytes':(ROOT/v).stat().st_size,'sha256':sha(ROOT/v),'git_delivery':False} for k,v in INPUTS.items()]
    dump(HERE/'source-manifest.json',{'files':source_manifest,'private_raw_not_delivered':True})
    q={'as_of_qualified':False,'scope':'current-vintage retrospective association only','rows':len(f),'aaii_age_days':{str(k):int(v) for k,v in f.aaii_age_days.value_counts().sort_index().items()},'support':support,'original_naaim_low_rows':int((f.naaim<=40).sum()),'original_aaii_low_rows':int((f.aaii<=-25).sum()),'both_survey_low_rows':int(((f.naaim<=40)&(f.aaii<=-25)).sum()),'breadth_support_only':{'eligible_dates':len(b),'both_width_low_dates':len(low),'continuous_low_episodes':episodes,'also_aaii_low_dates':int((low.aaii<=-25).sum()),'without_aaii_low_dates':int((low.aaii>-25).sum()),'historical_membership_qualified':False},'future_result_values_computed':False,'new_fits':0,'official_naaim_delay':'current free table three months; old first releases and revisions unknown','aaii_delay':'7 days inherited hypothetical, maximum source age14; not historical publication proof','other_gap':'price adjustment vintage and exact exchange calendar qualification unknown'}
    dump(HERE/'qualification.json',q);f.to_csv(HERE/'qualification-rows.csv',index=False);print(json.dumps(q,ensure_ascii=False))

def synthetic():
    a=pd.DataFrame({'date':pd.to_datetime(['2020-01-02','2020-01-09']),'spread_pp':[-25.,12.]});assert match_aaii(a,[pd.Timestamp('2020-01-08')])==[None];assert match_aaii(a,[pd.Timestamp('2020-01-09')])[0][1]==-25.
    old=match_aaii(a,[pd.Timestamp('2020-01-15')]);later=pd.concat([a,pd.DataFrame({'date':[pd.Timestamp('2020-01-16')],'spread_pp':[99.]})],ignore_index=True);assert match_aaii(later,[pd.Timestamp('2020-01-15')])==old
    assert match_aaii(a,[pd.Timestamp('2020-02-01')])==[None]
    tr=pd.DataFrame({'r20':[-4,-1,2,5],'aaii':[-40,-10,10,40],'naaim':[10,50,20,100]});te=tr.iloc[:2].copy();x,z,m=matrix(tr,te,MODELS['BANI']);te.aaii=1000;xx,zz,mm=matrix(tr,te,MODELS['BANI']);assert m==mm and np.array_equal(x,xx) and not np.array_equal(z,zz)
    assert np.allclose(x[:,-1],np.prod((tr[['aaii','naaim']].to_numpy()-np.array(m['mu']))/np.array(m['scale']),axis=1))
    dates=pd.to_datetime(['2024-12-31','2025-01-01']);assert int((dates<pd.Timestamp('2025-01-01')).sum())==1
    dump(HERE/'synthetic-check.json',{'passed':True,'cases':['strict prior availability','equal availability accepted under stated date assumption','future append invariant','stale rejected','train-only interaction scaling','manual interaction values','target maturity strict'],'market_fits':0,'synthetic_fits':0});print('7 boundary assertions passed; 0 fits')

def run():
    frozen=json.loads((HERE/'execution-freeze.json').read_text())
    for p,h in frozen['bound_files'].items():assert sha(ROOT/p)==h,p
    start=time.monotonic();out=HERE/'run-01';out.mkdir(exist_ok=False)
    state={'execution':'running','started_at':now(),'pid':os.getpid(),'core_fits':0,'independent_fits':0,'all_history_seen':True};dump(HERE/'state.json',state)
    f,px,a=panel(True);frames=[];fits=[]
    for year in [2025,2026]:
        cut=pd.Timestamp(f'{year}-01-01');tr=f[f.target_end<cut];te=f[f.anchor_date.dt.year==year].copy();assert tr.target_end.max()<te.anchor_date.min()
        for name,cols in MODELS.items():
            state['core_fits']+=1;dump(HERE/'state.json',state)
            with (HERE/'trial-ledger.jsonl').open('a') as log:log.write(json.dumps({'at':now(),'phase':'core','year':year,'model':name,'fit':state['core_fits']})+'\n')
            x,xt,meta=matrix(tr,te,cols);beta,mu,scale=fit(x,tr.y.to_numpy());te['pred_'+name]=np.column_stack([np.ones(len(xt)),(xt-mu)/scale])@beta;fits.append({'year':year,'model':name,'columns':cols,'n':len(tr),'beta':beta.tolist(),'mu':mu.tolist(),'scale':scale.tolist(),'interaction':meta})
        frames.append(te)
    v=pd.concat(frames).sort_values('anchor_date');old=pd.read_csv(ROOT/INPUTS['old_predictions'],parse_dates=['anchor_date','target_start','target_end']);assert len(v)==len(old)==78
    v=v.merge(old[['anchor_date','target_start','target_end','y','pred_I','pred_B','pred_X','pred_BX']],on='anchor_date',suffixes=('','_old'),validate='one_to_one');assert (v.target_start==v.target_start_old).all() and (v.target_end==v.target_end_old).all();assert np.allclose(v.y,v.y_old,atol=1e-9,rtol=0)
    v=v.rename(columns={'pred_X':'pred_N','pred_BX':'pred_BN'}).drop(columns=['target_start_old','target_end_old','y_old']);assert np.isfinite(v[['pred_'+m for m in ALL]].to_numpy()).all()
    v.to_csv(out/'predictions.csv',index=False);f.to_csv(out/'observations.csv',index=False);dump(out/'fits.json',fits)
    res={'overall':summary(v),'years':{str(y):summary(v[v.anchor_date.dt.year==y]) for y in [2025,2026]},'comparisons':{},'uncertainty_scope':'fixed saved predictions; no refitting/source-vintage/family-selection uncertainty'}
    for cand,base in PAIRS:
        key=cand+'_vs_'+base;eb=(v['pred_'+base]-v.y).to_numpy()**2;ec=(v['pred_'+cand]-v.y).to_numpy()**2;contrib=eb-ec;drop=np.argsort(contrib)[-5:];keep=np.ones(len(v),bool);keep[drop]=False
        row={'improvement_pct':gain(v,cand,base),'years':{str(y):gain(v[v.anchor_date.dt.year==y],cand,base) for y in [2025,2026]},'delete_most_favorable_five_pct':gain(v.loc[keep],cand,base),'total_error_reduction_pp2':float(contrib.sum()),'largest_five_error_reduction_pp2':float(contrib[drop].sum()),'blocks':{}}
        for length in [8,16]:
            rng=np.random.default_rng(20261004+length);vals=[]
            for _ in range(2000):
                starts=rng.integers(0,len(v)-length+1,int(np.ceil(len(v)/length)));idx=np.concatenate([np.arange(s,s+length) for s in starts])[:len(v)];vals.append(100*(1-ec[idx].mean()/eb[idx].mean()))
            row['blocks'][str(length)]={'draws':2000,'interval_pct':np.quantile(vals,[.025,.975]).tolist()}
        res['comparisons'][key]=row
    overlap=np.maximum(0,20-np.diff(v.anchor_index));res['support']={'eval_n':len(v),'date_first':str(v.anchor_date.min().date()),'date_last':str(v.anchor_date.max().date()),'target_last':str(v.target_end.max().date()),'overlapping_adjacent_pairs':int((overlap>0).sum()),'median_shared_future_intervals':float(np.median(overlap))};res['single_model_error_correlation_BA_BN']=float(np.corrcoef(v.pred_BA-v.y,v.pred_BN-v.y)[0,1]);dump(out/'results.json',res)
    state.update(execution='core_complete_review_pending',ended_at=now(),elapsed_seconds=time.monotonic()-start);dump(HERE/'state.json',state);print(json.dumps({'core_fits':state['core_fits'],'rmse':{k:round(z['rmse_pp'],6) for k,z in res['overall'].items()},'comparisons':{k:round(z['improvement_pct'],5) for k,z in res['comparisons'].items()}}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','synthetic','run']);args=p.parse_args();globals()[args.mode]()
