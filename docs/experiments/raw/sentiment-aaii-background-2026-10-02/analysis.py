"""Thin, frozen sentiment adapter. Reuses the project OLS numerical kernel.

This is not an adapter accepted by the technical-factor workflow. Historical
release/adjustment vintages remain unknown; outputs are retrospective estimates.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import traceback

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.workflow_evaluation import _ols_design, _ols_fit

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / 'protocol.json').read_text())
MODELS = PROTOCOL['models']
PRICE = PROTOCOL['definitions']['baseline_price']
PAIRS = [('BX', 'B'), ('X', 'I'), ('B', 'I'), ('BX', 'I')]
OUT = HERE / 'run-01'
EVIDENCE = HERE


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def mean20(source):
    dates = pd.to_datetime(source.date)
    weeks = dates.dt.to_period('W-SUN').astype('int64')
    if dates.duplicated().any() or (weeks.diff().dropna() <= 0).any():
        raise ValueError('duplicate/unordered survey calendar week')
    x = 100 * source.bull_bear
    result = x.rolling(20, min_periods=20).mean()
    return result.where(weeks.diff(19).eq(19)), weeks


def numerical_examples():
    f = pd.DataFrame({'date': pd.date_range('2020-01-02', periods=41, freq='7D'),
                      'bull_bear': np.arange(41) / 100})
    m, _ = mean20(f)
    assert m.iloc[:19].isna().all() and abs(m.iloc[19] - 9.5) < 1e-12
    gap = f.drop(index=5).reset_index(drop=True)
    gm, _ = mean20(gap)
    assert gm.iloc[19:24].isna().all() and abs(gm.iloc[24] - 15.5) < 1e-12
    f2 = f.copy(); f2.loc[25:, 'bull_bear'] = 1000
    m2, _ = mean20(f2)
    np.testing.assert_allclose(m[:25], m2[:25], equal_nan=True)
    return {'first20_mean': 9.5, 'first19_missing': True,
            'missing_calendar_week_not_compressed': True,
            'restored20_complete_weeks_mean': 15.5,
            'future_append_or_change_leaves_past_features_unchanged': True}


def prepare():
    for binding in PROTOCOL['sources']:
        assert hashlib.sha256((ROOT / binding['path']).read_bytes()).hexdigest() == binding['sha256']
    for binding in json.loads((HERE / 'standards-manifest.json').read_text()):
        if binding['path'].endswith('workflow_evaluation.py') or binding['path'].startswith('/Users/'):
            p = Path(binding['path']) if Path(binding['path']).is_absolute() else ROOT / binding['path']
            assert hashlib.sha256(p.read_bytes()).hexdigest() == binding['sha256']
    source = pd.read_csv(ROOT / PROTOCOL['sources'][0]['path'])
    prices = pd.read_csv(ROOT / PROTOCOL['sources'][1]['path'])
    previous = pd.read_csv(ROOT / PROTOCOL['sources'][2]['path']).sort_values('source_row').reset_index(drop=True)
    assert len(source) == len(previous)
    dates = pd.to_datetime(prices.Date).to_numpy('datetime64[ns]')
    assert pd.Series(dates).is_monotonic_increasing and pd.Series(dates).is_unique
    c = pd.to_numeric(prices.Close, errors='coerce').to_numpy(float)
    c[~np.isfinite(c) | (c <= 0)] = np.nan
    close = pd.Series(c)
    b = pd.DataFrame({'r20': 100*(close/close.shift(20)-1),
                      'r63': 100*(close/close.shift(63)-1),
                      'dma200': 100*(close/close.rolling(200, min_periods=200).mean()-1),
                      'dd252': 100*(close/close.rolling(252, min_periods=252).max()-1),
                      'rv20': 100*close.pct_change(fill_method=None).rolling(20, min_periods=20).std(ddof=1)*math.sqrt(20)})
    m, weeks = mean20(source)
    np.testing.assert_allclose(source.ma20_pp, (100*source.bull_bear).rolling(20).mean(), atol=1e-12, equal_nan=True)
    rows = []
    for i, record in source.iterrows():
        reported = pd.Timestamp(record.date)
        assumed = reported + pd.Timedelta(days=7)
        k = int(np.searchsorted(dates, assumed.to_datetime64(), side='right'))
        row = {'source_row': i, 'source_date': record.date, 'survey_week': int(weeks.iloc[i]),
               'assumed_available': str(assumed.date())+' 23:59:00', 't_index': k,
               't': None, 'target_start': None, 'target_end': None,
               'target_start_index': k+1, 'target_end_index': k+121,
               'x': 100*float(record.bull_bear), 'm20': float(m.iloc[i]),
               'y': np.nan, 'max_stage_fall_pp': np.nan}
        row.update({name: np.nan for name in PRICE})
        reasons = []
        if k >= len(c):
            reasons.append('no_observation_quote')
        else:
            row['t'] = prices.Date.iloc[k]
            row.update(b.iloc[k].to_dict())
            if not ('1995-01-01' <= row['t'] <= '2026-06-30'):
                reasons.append('observation_outside_range')
            if not np.isfinite([row['x']]+[row[name] for name in PRICE]).all():
                reasons.append('nonfinite_x_or_baseline')
            a, end = k+1, k+121
            if a < len(c): row['target_start'] = prices.Date.iloc[a]
            if end < len(c): row['target_end'] = prices.Date.iloc[end]
            if end >= len(c):
                reasons.append('incomplete_target_quotes')
            elif row['target_start'] > '2026-06-30' or row['target_end'] > '2026-06-30':
                reasons.append('target_beyond_cutoff')
            elif not np.isfinite(c[a:end+1]).all():
                reasons.append('nonfinite_target_path')
            else:
                row['y'] = 100*(c[end]/c[a]-1)
                row['max_stage_fall_pp'] = 100*float(np.max(1-c[a:end+1]/np.maximum.accumulate(c[a:end+1])))
        row['base_exclusion'] = '|'.join(reasons)
        rows.append(row)
    obs = pd.DataFrame(rows)
    duplicate = obs.t.notna() & obs.duplicated('t', keep='last')
    obs.loc[duplicate, 'base_exclusion'] += '|duplicate_t_keep_latest_source'
    obs['base_eligible'] = obs.base_exclusion.eq('') & np.isfinite(obs.y)
    obs['eligible'] = obs.base_eligible & np.isfinite(obs.m20)
    obs['exclusion'] = obs.base_exclusion
    obs.loc[obs.m20.isna(), 'exclusion'] += '|incomplete_20_calendar_survey_weeks'
    np.testing.assert_array_equal(obs.base_eligible, previous.eligible)
    for name in PRICE+['x', 'y']:
        np.testing.assert_allclose(obs[name], previous[name], atol=1e-10, rtol=1e-10, equal_nan=True)
    for name in ['t', 'target_start', 'target_end']:
        assert obs[name].fillna('').tolist() == previous[name].fillna('').tolist(), name
    obs['asset'] = 'SPY'; obs['date'] = obs.t
    obs['features'] = obs.apply(lambda z: {k: float(z[k]) for k in PRICE+['x','m20']}, axis=1)
    return source, prices, obs


def score(frame):
    errors = {m: frame['pred_'+m].to_numpy()-frame.y.to_numpy() for m in MODELS}
    mse = {m: float(np.mean(e**2)) for m, e in errors.items()}
    return {'n': len(frame), 'mse': mse,
            'rmse': {m: float(math.sqrt(v)) for m, v in mse.items()},
            'mean_absolute_error': {m: float(np.mean(abs(v))) for m, v in errors.items()},
            'improvement_pct': {m+'_vs_'+b: 100*(1-mse[m]/mse[b]) for m,b in PAIRS},
            'squared_error_reduction_sum': {m+'_vs_'+b: len(frame)*(mse[b]-mse[m]) for m,b in PAIRS}}


def block_intervals(pred, block):
    # Calendar weeks with unavailable observations remain positions on the axis.
    first, last = int(pred.survey_week.min()), int(pred.survey_week.max())
    axis = np.arange(first,last+1); n = len(axis)
    loss = np.full((n,len(MODELS)), np.nan)
    for j,m in enumerate(MODELS):
        loss[pred.survey_week.to_numpy(int)-first,j] = (pred['pred_'+m]-pred.y)**2
    rng = np.random.default_rng(20261002)
    output = []
    names = list(MODELS)
    for draw in range(2000):
        starts = rng.integers(0,n-block+1,math.ceil(n/block))
        ix = np.concatenate([np.arange(k,k+block) for k in starts])[:n]
        values = np.nanmean(loss[ix],axis=0)
        item = {'draw': draw, 'calendar_weeks': n, 'valid_rows': int(np.isfinite(loss[ix,0]).sum()),
                'block_starts': json.dumps(starts.tolist()), 'block_weeks': block}
        item.update({m+'_vs_'+b: 100*(1-values[names.index(m)]/values[names.index(b)]) for m,b in PAIRS})
        output.append(item)
    f = pd.DataFrame(output); f.to_csv(OUT/f'paired-blocks-{block}.csv',index=False)
    return {m+'_vs_'+b: {'p2_5': float(f[m+'_vs_'+b].quantile(.025)),
                         'p97_5': float(f[m+'_vs_'+b].quantile(.975)), 'valid_draws': 2000,
                         'calendar_weeks': n, 'missing_calendar_weeks': int(np.isnan(loss[:,0]).sum())} for m,b in PAIRS}


def main(do_fit):
    if OUT.exists(): raise RuntimeError('run-01 exists: never overwrite an executed attempt')
    OUT.mkdir()
    examples = numerical_examples()
    source, prices, obs = prepare()
    display = obs.drop(columns='features'); display.to_csv(OUT/'observations.csv', index=False)
    counts = {'source_rows': len(source), 'price_rows': len(prices),
              'complete_20week_inputs': int(obs.m20.notna().sum()),
              'prefix19_unavailable': 19, 'gap_20week_windows_unavailable': int(obs.m20.isna().sum())-19,
              'base_eligible_all_years': int(obs.base_eligible.sum()), 'common_eligible_all_years': int(obs.eligible.sum()),
              'old_evaluation_rows': int((obs.base_eligible & obs.t.ge('2010-01-01')).sum()),
              'common_evaluation_rows': int((obs.eligible & obs.t.ge('2010-01-01')).sum()),
              'exclusion_counts_nonexclusive': obs.exclusion.str.split('|').explode().value_counts().drop('',errors='ignore').to_dict()}
    save(EVIDENCE/'qualification.json', {'counts':counts, 'numerical_examples':examples,
         'original_observation_reconstruction': 'all2038source rows,5pricefeatures,currentAAII,target dates and y agree',
         'calendar': 'AAII source gaps3 calendar weeks. No empty survey week compressed into20week mean.',
         'available_at': 'unknown;source+7days assumption only',
         'permitted_scope':'saved-series retrospective120quote-interval comparison only',
         'production':'not_authorized'})
    if not do_fit: return
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save(EVIDENCE/'execution-freeze.json', {'protocol_sha256':hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
         'analysis_sha256':code_hash,'reused_kernel_sha256':hashlib.sha256((ROOT/'src/lei_signal/research/workflow_evaluation.py').read_bytes()).hexdigest()})
    fits, predictions, attempts, boundaries = [], [], [], []
    for year in range(2010,2027):
        boundary = f'{year}-01-01'
        train = obs[obs.eligible & obs.t.lt(boundary) & obs.target_end.lt(boundary)].copy()
        ev = obs[obs.eligible & obs.t.str.startswith(str(year),na=False)].copy()
        if ev.empty: continue
        assert len(train)>=100 and train.t.max()<boundary and train.target_end.max()<boundary
        boundaries.append({'year':year,'training':len(train),'evaluation':len(ev),
            'train_observation_max':train.t.max(),'train_target_end_max':train.target_end.max(),
            'unmatured_training_excluded':int((obs.eligible & obs.t.lt(boundary) & obs.target_end.ge(boundary)).sum()),
            'first_evaluation':ev.t.min(),'last_evaluation':ev.t.max()})
        designs = {m: _ols_design(train,ev,cols,'equal_asset') for m,cols in MODELS.items()}
        for m, design in designs.items():
            assert not design['zero'].any() and design['rank']==len(MODELS[m])
            attempt = {'trial':f'core-{year}-{m}','year':year,'model':m,'status':'running','features':MODELS[m],'input_rows':len(train)}
            attempts.append(attempt); save(EVIDENCE/'trial-ledger.json', {'fits':len(attempts),'records':attempts,'family_previous_fits_at_least':744})
            try:
                prediction, detail = _ols_fit(train, design)
                ev['pred_'+m] = prediction
                detail.update(year=year,model=m,train_target_end_max=train.target_end.max(),train_t_max=train.t.max())
                fits.append(detail); attempt['status']='completed'
            except Exception as exc:
                attempt.update(status='failed',error=str(exc)); save(EVIDENCE/'trial-ledger.json', {'fits':len(attempts),'records':attempts}); raise
        predictions.append(ev)
    pred = pd.concat(predictions).sort_values('t').reset_index(drop=True)
    pred.drop(columns='features').to_csv(OUT/'predictions.csv',index=False)
    save(OUT/'fits.json',fits); save(OUT/'boundaries.json',boundaries)
    save(EVIDENCE/'trial-ledger.json', {'fits':len(attempts),'records':attempts,'family_previous_fits_at_least':744})
    overlap = np.maximum(0,np.minimum(pred.target_end_index.to_numpy()[:-1],pred.target_end_index.to_numpy()[1:])-np.maximum(pred.target_start_index.to_numpy()[:-1],pred.target_start_index.to_numpy()[1:]))
    intervals = {str(b):block_intervals(pred,b) for b in [52,104]}
    annual = {str(y):score(f) for y,f in pred.groupby(pred.t.str[:4])}
    periods = {name:score(pred[pred.t.between(start,end)]) for name,start,end in [('2010-2014','2010-01-01','2014-12-31'),('2015-2019','2015-01-01','2019-12-31'),('2020-2026','2020-01-01','2026-06-30')]}
    deleted = {str(y):score(pred[~pred.t.str.startswith(str(y))]) for y in range(2010,2027)}
    groups = {}
    for name, mask in [('m20_nonpositive',pred.m20.le(0)),('m20_positive',pred.m20.gt(0))]:
        f = pred[mask]
        groups[name]={'n':len(f),'mean_return_pp':float(f.y.mean()),'median_return_pp':float(f.y.median()),
                     'up_share':float(f.y.gt(0).mean()),'mean_max_stage_fall_pp':float(f.max_stage_fall_pp.mean()),'errors':score(f)}
    counts.update(eval_first=pred.t.min(),eval_last=pred.t.max(),target_first=pred.target_start.min(),target_last=pred.target_end.max(),
                  adjacent_pairs=len(overlap),overlapping_adjacent_pairs=int((overlap>0).sum()),overlap_mean_segments=float(overlap.mean()),overlap_max_segments=int(overlap.max()))
    save(OUT/'results.json', {'overall':score(pred),'coverage':counts,'intervals':intervals,'annual':annual,'periods':periods,'remove_eval_year':deleted,'raw_groups':groups,'fits':len(fits),
         'uncertainty':'fixed prediction reaggregation; no refit uncertainty; alreadyseenhistoricaldata not independent confirmation'})
    print(json.dumps({'completed_fits':len(fits),'evaluation_rows':len(pred)},ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fit',action='store_true')
    parser.add_argument('--output', help='A new empty directory for a separately registered reproduction; never replaces run-01')
    args=parser.parse_args()
    if args.output:
        OUT = Path(args.output).resolve()
        if not OUT.is_relative_to(ROOT): raise RuntimeError('reproduction outside repository is not authorized')
        EVIDENCE = OUT / 'audit'
    try: main(args.fit)
    except Exception:
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        (EVIDENCE/'execution-failure.txt').write_text(traceback.format_exc()); raise
