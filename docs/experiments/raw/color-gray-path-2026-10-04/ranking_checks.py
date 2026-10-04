"""Independent rank arithmetic and common-date references; no fits."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
d=pd.read_csv(HERE/'same-day-ranking-daily.csv');r=pd.read_csv(HERE/'same-day-ranking-rows.csv');out={'matched_dates':{},'independent_checks':{},'model_ranking':{},'rank_difference_vs_simple':{},'early_period':{}}
checks=0;maxerr=0.
for f in ['green_share20','switch_frequency20','distance_to_ema20','ret20','ema20_up_share20']:
 for day,g in r.groupby('date'):
  xs=g[f].tolist();n=len(xs);expected=[(sum(z<x for z in xs)+(sum(z==x for z in xs)-1)/2)/(n-1) for x in xs]
  err=max(abs(a-b) for a,b in zip(expected,g[f+'_rank']));maxerr=max(maxerr,err);checks+=len(g)
 sub=d[d.factor==f];valid=sub[sub.high_minus_low.notna()]
 out['matched_dates'][f]={'valid_dates':len(valid),'pool_return_on_valid_dates':float(valid.pool_return.mean()),'high_minus_pool':float(valid.high_minus_pool.mean()),'low_return':float(valid.low_return.mean()),'high_return':float(valid.high_return.mean()),'high_minus_low':float(valid.high_minus_low.mean()),'mean_high_count':float(valid.n_high.mean()),'mean_low_count':float(valid.n_low.mean()),'excluded_constant_dates':len(sub)-len(valid)}
 for baseline in ['ret20','ema20_up_share20']:
  both=sub.merge(d[d.factor==baseline],on='date',suffixes=('_x','_b')).dropna(subset=['high_minus_low_x','high_minus_low_b'])
  out['rank_difference_vs_simple'][f+'/'+baseline]={'common_dates':len(both),'gap_candidate_minus_simple_pp':float((both.high_minus_low_x-both.high_minus_low_b).mean()),'high_candidate_minus_simple_pp':float((both.high_return_x-both.high_return_b).mean())}
 # Earlier mature dates, same fixed groups; no direction selection.
 p=HERE/'continuous/ridge-forward_return/core-01/preflight.json';obs=json.loads(p.read_text())['observations'];earlier=[{**x,**x['features']} for x in obs if x['eligible'] and x['label_end']<'2025-01-01']
 e=pd.DataFrame(earlier);gaps=[]
 for day,g in e.groupby('date'):
  rank=(g[f].rank(method='average')-1)/(len(g)-1);lo=g[rank<.5];hi=g[rank>.5]
  if len(lo) and len(hi):gaps.append(hi.y.mean()-lo.y.mean())
 out['early_period'][f]={'rows':len(e),'dates':e.date.nunique(),'nonconstant_dates':len(gaps),'high_minus_low_pp':float(np.mean(gaps))}
assert maxerr<1e-12
out['independent_checks']={'rank_values_checked':checks,'max_rank_error':maxerr,'future_labels_used_to_rank':False,'new_fits':0}
for target in ['forward_return','mae']:
 for method in ['ridge','lightgbm']:
  f=pd.read_csv(HERE/('continuous-'+method+'-'+target+'-saved.csv'))
  for model in ['B1','B2']:
   vals=[]
   for day,g in f.groupby('date'):
    rank=(g[model].rank(method='average')-1)/(len(g)-1);lo=g[rank<.5];hi=g[rank>.5];ic=g[model].rank().corr(g.y.rank()) if g[model].nunique()>1 and g.y.nunique()>1 else np.nan
    vals.append({'date':day,'n':len(g),'high_n':len(hi),'low_n':len(lo),'rank_correlation':ic,'pool_target':g.y.mean(),'high_target':hi.y.mean(),'low_target':lo.y.mean(),'high_minus_low':hi.y.mean()-lo.y.mean()})
   z=pd.DataFrame(vals);key=method+'-'+target+'-'+model;z.to_csv(HERE/('model-ranking-'+key+'.csv'),index=False)
   out['model_ranking'][key]={'dates':len(z),'usable_dates':int(z.high_minus_low.notna().sum()),'mean_rank_correlation':float(z.rank_correlation.mean()),'high_minus_low_target_pp':float(z.high_minus_low.mean()),'by_period':{yr:{'dates':int(z.date.str.startswith(yr).sum()),'high_minus_low':float(z[z.date.str.startswith(yr)].high_minus_low.mean())} for yr in ['2025','2026']},'interpretation':'return prediction: high expected better return; risk prediction: high expected larger loss, not a buy rank'}
(HERE/'ranking-independent-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps(out['matched_dates'],ensure_ascii=False))
