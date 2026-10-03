"""Root independent outcome/population review; saved arithmetic, no fitting."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1]
RUN = RAW / 'executor/run-01'
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    return json.loads(Path(path).read_text())
def near(a, b, tolerance=1e-9):
    assert abs(float(a)-float(b)) <= tolerance, (a, b)
manifest = load(RUN/'manifest.json')
assert manifest['status'] == 'completed'
assert manifest['started_fits'] == manifest['completed_fits'] == 68
assert manifest['failed_fits'] == 0
assert sha(RAW/'executor/analyze.py') == manifest['code_sha256'] == load(RAW/'controller/code-review.json')['code_sha256']
for name, record in manifest['outputs'].items():
    assert sha(RUN/name) == record['sha256'], name
obs = pd.read_csv(RUN/'observations.csv', parse_dates=['t','source_date','target_start','target_end'])
pred = pd.read_csv(RUN/'predictions.csv', parse_dates=['t','source_date','target_start','target_end'])
price = pd.read_csv(RAW/'inputs/px_SPY.csv', parse_dates=['Date'])
survey = pd.read_csv(RAW/'inputs/aaii-candidate-values.csv', parse_dates=['date'])
result = load(RUN/'results.json')
expected = load(RAW/'validation/expectation.json')
assert len(obs) == len(survey) == 2038 and len(price) == 8456
assert obs.eligible.sum() == 1615 and len(pred) == 835
ev = obs.loc[obs.eligible & obs.t.ge('2010-01-01')]
assert ev.source_row.tolist() == pred.source_row.tolist()
assert pred.t.is_unique and not pred[['pred_I','pred_V','pred_B','pred_BX']].isna().any().any()
assert np.isfinite(pred[['y','pred_I','pred_V','pred_B','pred_BX']]).all().all()
assert obs.loc[obs.eligible,'y'].ge(0).all() and obs.loc[obs.eligible,'y'].lt(100).all()
assert (obs.loc[obs.eligible,'target_end_index']-obs.loc[obs.eligible,'target_start_index']).eq(120).all()
assert obs.loc[obs.eligible,'target_end'].le('2026-06-30').all()
dates = price.Date.to_numpy(dtype='datetime64[ns]')
for row in obs.loc[obs.eligible].itertuples():
    original = survey.iloc[row.source_row]
    k = np.searchsorted(dates, (original.date+pd.Timedelta(days=7)).to_datetime64(), side='right')
    assert int(k) == row.t_index and price.iloc[k].Date == row.t
    assert row.target_start_index == k+1 and row.target_end_index == k+121
    near(row.x,100*(original.bullish-original.bearish),1e-11)

old = RAW.parent/'sentiment-aaii-extremes-increment-2026-09-29/executor/run-01/observations-h120.csv'
prior = pd.read_csv(old)
joined = obs.loc[obs.eligible].merge(prior.loc[prior.eligible],on='source_row',suffixes=('_new','_old'),validate='one_to_one')
assert len(joined)==1615
background_diff = {c:float(np.max(np.abs(joined[c+'_new']-joined[c+'_old']))) for c in ['x','r20','r63','dma200','dd252','rv20']}
assert max(background_diff.values()) < 2e-10

cases=[]
for case in expected['prespecified_examples']:
    p=pred.loc[pred.t.eq(case['t_date'])]
    assert len(p)==1
    row=p.iloc[0]
    # Independent checker names the physical CSV line (header is line1),
    # whereas the executor names the zero-based data-row index.
    assert row.source_row+2==case['physical_source_row']
    assert str(row.source_date.date())==case['source_date']
    assert str(row.target_start.date())==case['target_start'] and str(row.target_end.date())==case['target_end']
    hand=100*(case['peak_close']-case['trough_close'])/case['peak_close']
    near(row.y,hand,1e-10)
    cases.append({'t':case['t_date'],'actual_target':float(row.y),'independent_target':hand,'abs_difference':abs(row.y-hand)})

MODELS=['I','V','B','BX']
PAIRS=[('BX','B'),('BX','I'),('BX','V'),('B','I'),('V','I'),('B','V')]
def metrics(df):
    return {m:{'mse':float(np.mean((df['pred_'+m]-df.y)**2)),
               'rmse':float(np.sqrt(np.mean((df['pred_'+m]-df.y)**2))),
               'mae':float(np.mean(np.abs(df['pred_'+m]-df.y)))} for m in MODELS}
def inc(df):
    met=metrics(df)
    return {m+'_vs_'+b:100*(1-met[m]['mse']/met[b]['mse']) for m,b in PAIRS}
overall=metrics(pred)
for m, met in overall.items():
    for name, val in met.items():near(val,result['overall']['metrics'][m][name])
for name,val in inc(pred).items():near(val,result['overall']['improvement_pct'][name])
annual={}
for year in range(2010,2027):
    df=pred.loc[pred.t.dt.year.eq(year)]
    assert len(df)==expected['coverage']['evaluation_by_t_year'][str(year)]==result['annual'][str(year)]['n']
    annual[year]=inc(df)
    for name,val in annual[year].items():near(val,result['annual'][str(year)]['improvement_pct'][name])
    for name,val in inc(pred.loc[~pred.t.dt.year.eq(year)]).items():near(val,result['delete_one_year_no_refit'][str(year)]['improvement_pct'][name])
for name,a,b in [('2010-2014','2010-01-01','2014-12-31'),('2015-2019','2015-01-01','2019-12-31'),('2020-2026H1','2020-01-01','2026-06-30')]:
    for key,val in inc(pred.loc[pred.t.between(a,b)]).items():near(val,result['bands'][name]['improvement_pct'][key])
loss=(pred.pred_B-pred.y)**2-(pred.pred_BX-pred.y)**2
contributions=loss.groupby(pred.t.dt.year).sum()
for year,val in contributions.items():near(val,result['contributions']['BX_vs_B']['annual'][str(year)],1e-8)
best=int(contributions.idxmax());worst=int(contributions.idxmin())
assert best==result['contributions']['BX_vs_B']['largest_reduction_year']==2016
assert worst==result['contributions']['BX_vs_B']['largest_loss_increase_year']==2019
remove_best=inc(pred.loc[~pred.t.dt.year.eq(best)])['BX_vs_B']
assert remove_best<0
intervals={}
for block in [52,104]:
    d=pd.read_csv(RUN/f'draws-block{block}.csv')
    assert len(d)==2000
    v=d.improvement_BX_vs_B.to_numpy()
    lo,hi=np.quantile(v,[.025,.975])
    near(lo,result['uncertainty'][str(block)]['BX_vs_B']['p2_5'])
    near(hi,result['uncertainty'][str(block)]['BX_vs_B']['p97_5'])
    intervals[block]=[float(lo),float(hi)]
shared=np.maximum(0,np.minimum(pred.target_end_index.to_numpy()[:-1],pred.target_end_index.to_numpy()[1:])-np.maximum(pred.target_start_index.to_numpy()[:-1],pred.target_start_index.to_numpy()[1:]))
assert len(shared)==834 and (shared>0).sum()==834
assert np.min(shared)==111 and np.median(shared)==115 and np.max(shared)==117
audit={'status':'passed','review_attempts':2,'prior_review_failure':'physical CSV line versus zero-based row convention; retained outcome-review-attempt-01.json, no changed market result','review_type':'root independent identities, population, six prespecified targets, saved loss/stability arithmetic; no optimizing or fitting',
       'real_fits_added':0,'model_metrics':overall,'increments_pct':inc(pred),'target_cases':cases,
       'background_compatibility_maxabs':background_diff,'common_rows':1615,'evaluation_rows':835,
       'annual_primary_positive_complete_years':sum(annual[y]['BX_vs_B']>0 for y in range(2010,2026)),
       'annual_primary_negative_complete_years':sum(annual[y]['BX_vs_B']<0 for y in range(2010,2026)),
       '2026_partial_rows':1,'best_year':best,'worst_year':worst,'primary_without_best_year':remove_best,
       'intervals_primary_pct':intervals,'raw_shared_date_pairs':834,'code_sha256':manifest['code_sha256'],
       'result_sha256':sha(RUN/'results.json'),'review_code_sha256':sha(__file__),
       'unverified_by_this_checker':['saved parameter objective/gradient and blockdraw replay delegated to independent Sol review','source actual first releases/price vintage unknown; no account/production research']}
(RAW/'controller/outcome-review.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':'passed','evaluation_rows':835,'root_fits_added':0,'primary':inc(pred)['BX_vs_B'],'remove2016':remove_best}))
