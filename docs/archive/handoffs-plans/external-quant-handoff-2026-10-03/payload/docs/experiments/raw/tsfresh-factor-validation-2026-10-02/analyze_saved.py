"""Fixed sensitivity on saved predictions only; never performs numerical fits."""
import copy
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from lei_signal.research.workflow_evaluation import _block_draws
RAW=Path(__file__).resolve().parent

def mse(rows,model):
    groups=defaultdict(list)
    for r in rows: groups[r['asset']].append((r['y']-r[model])**2)
    return sum(sum(v)/len(v) for v in groups.values())/len(groups)

def scores(rows):
    values={m:mse(rows,m) for m in ('B0','B1','B2')}
    return dict(rows=len(rows), dates=len({r['date'] for r in rows}),
        assets=len({r['asset'] for r in rows}),mse=values,
        rmse={m:math.sqrt(v) for m,v in values.items()},
        delta_mse_B1_B2=values['B1']-values['B2'],
        delta_rmse_B1_B2=math.sqrt(values['B1'])-math.sqrt(values['B2']),
        delta_rmse_B0_B2=math.sqrt(values['B0'])-math.sqrt(values['B2']))

def analyze(ident):
    out=RAW/f'run-{ident}'
    result=json.loads((out/'result.json').read_text())
    contract=json.loads((out/'contract.json').read_text())
    rows=result['predictions']
    assert len({r['id'] for r in rows})==len(rows)
    overall=scores(rows)
    for model in ('B0','B1','B2'):
        official=next(p['value'] for p in result['performance'] if p['model']==model and p['metric']=='MSE')
        assert math.isclose(overall['mse'][model],official,abs_tol=1e-10,rel_tol=1e-12)
    # All calendar dates in declared evaluation, including unlabelled tails.
    axis=[d for d in contract['calendar'] if any(f['eval_start']<=d<=f['eval_end'] for f in contract['split']['folds'])]
    frame=pd.DataFrame(rows).sort_values(['date','asset']).reset_index(drop=True)
    uncertainty={}
    for length in (20,60):
        dep=dict(contract['dependence'],block_length=length)
        draws={}
        invalid={}
        for model in ('B0','B1','B2'):
            draws[model],invalid[model]=_block_draws(frame,((frame[model]-frame.y)**2).to_numpy(),axis,'equal_asset',dep)
        assert len(set(invalid.values()))==1 and len({len(v) for v in draws.values()})==1
        comparisons={}
        for baseline in ('B1','B0'):
            rmse_delta=np.sqrt(draws[baseline])-np.sqrt(draws['B2'])
            mse_delta=draws[baseline]-draws['B2']
            comparisons[baseline]=dict(delta_rmse=float(np.sqrt(overall['mse'][baseline])-np.sqrt(overall['mse']['B2'])),
                rmse_lo=float(np.quantile(rmse_delta,.025)),rmse_hi=float(np.quantile(rmse_delta,.975)),
                delta_mse=float(overall['mse'][baseline]-overall['mse']['B2']),
                mse_lo=float(np.quantile(mse_delta,.025)),mse_hi=float(np.quantile(mse_delta,.975)))
            if length==20:
                official=next(i for i in result['increments'] if i['old_model']==baseline)
                assert math.isclose(comparisons[baseline]['mse_lo'],official['lo'],abs_tol=1e-10)
                assert math.isclose(comparisons[baseline]['mse_hi'],official['hi'],abs_tol=1e-10)
        uncertainty[str(length)]=dict(calendar_dates=len(axis),draws=dep['draws'],seed=dep['seed'],
            unestimable_draws=invalid['B2'],comparisons=comparisons,
            interpretation='conditional on fixed fitted predictions; correlated ETF/calendar blocks together; no refitting')
    byasset={a:scores([r for r in rows if r['asset']==a]) for a in sorted({r['asset'] for r in rows})}
    byyear={y:scores([r for r in rows if r['date'][:4]==y]) for y in sorted({r['date'][:4] for r in rows})}
    loo={a:scores([r for r in rows if r['asset']!=a]) for a in byasset}
    bydate=defaultdict(list)
    for r in rows: bydate[r['date']].append((r['B1']-r['y'])**2-(r['B2']-r['y'])**2)
    # Signed improvement descending, exactly the predeclared largest improvements.
    top=sorted(bydate,key=lambda d:(-sum(bydate[d])/len(bydate[d]),d))[:20]
    trimmed=scores([r for r in rows if r['date'] not in top])
    return dict(variant=ident, result_sha256=hashlib.sha256((out/'result.json').read_bytes()).hexdigest(),
        overall=overall,uncertainty=uncertainty,by_asset=byasset,by_year=byyear,
        leave_one_asset_out=loo,remove_top20=dict(dates=top,selection='signed descending equal-asset daily B1-B2 squared loss improvement',remaining=trimmed),
        new_fits=0,selection_after_results=False)

if __name__=='__main__':
    all_results={i:analyze(i) for i in ('joint','amplitude','serial','factor_only')}
    all_ids=[set(r['id'] for r in json.loads((RAW/f'run-{i}'/'result.json').read_text())['predictions']) for i in all_results]
    assert all(s==all_ids[0] for s in all_ids)
    path=RAW/'saved-prediction-analysis.json'
    with path.open('x') as f: json.dump(all_results,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({i:r['overall'] for i,r in all_results.items()},ensure_ascii=False))
