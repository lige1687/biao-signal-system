"""Controller's independent arithmetic and 27-fit review; never rerun silently."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import math
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    out = HERE / 'independent-review'
    out.mkdir(exist_ok=False)
    p = json.loads((HERE / 'protocol.json').read_text())
    obs = pd.read_csv(HERE / 'run-01/observations.csv')
    pred = pd.read_csv(HERE / 'run-01/predictions.csv')
    source = pd.read_csv(ROOT / p['sources'][0]['path'])
    px = pd.read_csv(ROOT / p['sources'][1]['path'])
    models = p['models']
    checks = []
    for b in p['sources']:
        assert hashlib.sha256((ROOT / b['path']).read_bytes()).hexdigest() == b['sha256']
    checks.append('all_bound_source_bytes_match')
    week = [pd.Timestamp(d).to_period('W-SUN').ordinal for d in source.date]
    x = [100 * v for v in source.bull_bear]
    expected = []
    count = None
    for i, value in enumerate(x):
        adjacent = i > 0 and week[i] == week[i-1] + 1
        if value >= 0:
            count = 0
        elif adjacent and count is not None:
            count += 1
        else:
            count = None
        d4 = value-x[i-4] if i >= 4 and week[i]-week[i-4] == 4 else np.nan
        mean20 = sum(x[i-19:i+1])/20 if i >= 19 and week[i]-week[i-19] == 19 else np.nan
        recovered = float(x[i-1] <= -25 < value) if adjacent else np.nan
        expected.append([value, mean20, d4, count if count is not None else np.nan, recovered])
    expected = np.asarray(expected)
    for j, name in enumerate(['x', 'm20', 'd4', 'neg_run', 'exit_pessimism']):
        np.testing.assert_allclose(obs.sort_values('source_row')[name], expected[:, j], atol=1e-10, rtol=1e-10, equal_nan=True)
    checks.append('all_2038_source_rows_five_survey_features_independently_reconstructed')
    # Date alignment and prices independently from source, not the runner's index arithmetic.
    quotes = [dt.date.fromisoformat(d) for d in px.Date]
    close = px.Close.to_numpy(float)
    max_label_error = 0.0
    for row in obs.itertuples():
        i = int(row.source_row)
        assumed = dt.date.fromisoformat(source.date.iloc[i]) + dt.timedelta(days=7)
        k = int(np.searchsorted(quotes, assumed, side='right'))
        assert int(row.t_index) == k
        if k < len(quotes):
            assert row.t == str(quotes[k])
        if not row.eligible:
            continue
        assert row.target_start == str(quotes[k+1]) and row.target_end == str(quotes[k+121])
        assert row.target_end <= '2026-06-30'
        y = 100 * (close[k+121]/close[k+1]-1)
        max_label_error = max(max_label_error, abs(y-row.y))
        assert abs(y-row.y) < 1e-10
        r20 = 100*(close[k]/close[k-20]-1)
        r63 = 100*(close[k]/close[k-63]-1)
        dma200 = 100*(close[k]/np.mean(close[k-199:k+1])-1)
        dd252 = 100*(close[k]/max(close[k-251:k+1])-1)
        returns = close[k-19:k+1]/close[k-20:k]-1
        rv20 = 100*np.std(returns, ddof=1)*math.sqrt(20)
        np.testing.assert_allclose([row.r20,row.r63,row.dma200,row.dd252,row.rv20], [r20,r63,dma200,dd252,rv20], atol=1e-10, rtol=1e-10)
    checks.append('eligible_labels_dates_and_five_price_features_independently_reconstructed')
    # No candidate-dependent date selection across nine estimates.
    eligible = obs[obs.eligible & obs.t.ge('2010-01-01')].sort_values('t')
    assert eligible.source_row.tolist() == pred.source_row.tolist()
    assert not pred.t.duplicated().any()
    assert np.isfinite(pred[['pred_'+m for m in models]].to_numpy()).all()
    checks.append('same_evaluation_dates_for_all_nine_models')
    trials = []
    max_prediction_error = 0.0
    for year in [2010, 2020, 2026]:
        train = obs[obs.eligible & obs.t.lt(f'{year}-01-01') & obs.target_end.lt(f'{year}-01-01')]
        ev = pred[pred.t.str.startswith(str(year))]
        assert len(train) >= 100 and len(ev) > 0
        for name, cols in models.items():
            item = {'year': year, 'model': name, 'status': 'running', 'fit_number': len(trials)+1}
            trials.append(item)
            save(out/'trials.json', {'fits':len(trials), 'limit':27, 'records':trials})
            a = train[cols].to_numpy(float)
            b = ev[cols].to_numpy(float)
            # Use direct, unscaled explicit-intercept least squares, independent of project kernel.
            a = np.column_stack([np.ones(len(a)), a])
            b = np.column_stack([np.ones(len(b)), b])
            coef, _, rank, _ = np.linalg.lstsq(a, train.y.to_numpy(float), rcond=None)
            assert rank == len(cols)+1
            error = float(np.max(np.abs(b@coef-ev['pred_'+name].to_numpy(float))))
            assert error < 1e-8
            max_prediction_error = max(max_prediction_error, error)
            item.update(status='completed', train_n=len(train), evaluation_n=len(ev), max_abs_prediction_difference_pp=error)
            save(out/'trials.json', {'fits':len(trials), 'limit':27, 'records':trials})
    checks.append('27_direct_unscaled_explicit_intercept_fits_agree')
    all_pairs = p['primary_comparisons'] + p['secondary_comparisons']
    mse = {m:float(np.mean(np.square(pred['pred_'+m]-pred.y))) for m in models}
    increments = {m+'_vs_'+b:100*(1-mse[m]/mse[b]) for m,b in all_pairs}
    results = json.loads((HERE/'run-01/results.json').read_text())
    for m,v in mse.items():
        assert math.isclose(v,results['overall']['mse'][m],rel_tol=1e-10,abs_tol=1e-10)
    for k,v in increments.items():
        assert math.isclose(v,results['overall']['improvement_pct'][k],rel_tol=1e-10,abs_tol=1e-10)
    checks.append('all_headline_loss_and_increment_arithmetic_agrees')
    # Independently recreate fixed-prediction block draws; no extra model fitting.
    interval_review = {}
    first,last = int(pred.survey_week.min()),int(pred.survey_week.max())
    names = list(models)
    loss = np.full((last-first+1,len(names)),np.nan)
    for j,m in enumerate(names):
        loss[pred.survey_week.to_numpy(int)-first,j] = np.square(pred['pred_'+m]-pred.y)
    for block in [52,104]:
        rng=np.random.default_rng(20261003)
        samples={m+'_vs_'+b:[] for m,b in all_pairs}
        for _ in range(2000):
            starts=rng.integers(0,len(loss)-block+1,math.ceil(len(loss)/block))
            indices=np.concatenate([np.arange(k,k+block) for k in starts])[:len(loss)]
            means=np.nanmean(loss[indices],axis=0)
            for m,b in all_pairs:
                samples[m+'_vs_'+b].append(100*(1-means[names.index(m)]/means[names.index(b)]))
        intervals={k:{'p2_5':float(np.quantile(v,.025)),'p97_5':float(np.quantile(v,.975)),
                      'p0_625':float(np.quantile(v,.00625)),'p99_375':float(np.quantile(v,.99375))} for k,v in samples.items()}
        for k,v in intervals.items():
            reported=results['intervals'][str(block)][k]
            for q in ['p2_5','p97_5']:
                assert math.isclose(v[q],reported[q],abs_tol=1e-8,rel_tol=1e-8)
        interval_review[str(block)]=intervals
    checks.append('52_and104_week_dependence_intervals_independently_recomputed')
    review={'status':'passed','completed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'checks':checks,
            'source_rows':len(source),'evaluation_rows':len(pred),'independent_fits':len(trials),
            'core_fits':results['fits'],'total_new_fits':results['fits']+len(trials),'maximum_label_error_pp':max_label_error,
            'maximum_prediction_error_pp':max_prediction_error,'mse':mse,'increments':increments,
            'independent_intervals':interval_review,'not_validated':['historical first releases or adjusted-price vintages','independent unseen history','account or production returns','other OS']}
    save(out/'review.json',review)
    print(json.dumps({k:v for k,v in review.items() if k not in ['independent_intervals','mse','increments']},ensure_ascii=False))


if __name__ == '__main__':
    main()
