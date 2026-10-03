"""Frozen, retrospective AAII dynamics adapter. No production signal is emitted."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE / 'protocol.json'
DEFINITIONS_PATH = HERE / 'definitions.json'
# Byte-for-byte snapshot of the existing project math, not another implementation.
KERNEL_PATH = HERE / 'snapshots/workflow_evaluation.py'
import importlib.util
_kernel_spec = importlib.util.spec_from_file_location('frozen_lei_ols', KERNEL_PATH)
_kernel = importlib.util.module_from_spec(_kernel_spec)
_kernel_spec.loader.exec_module(_kernel)
_ols_design, _ols_fit = _kernel._ols_design, _kernel._ols_fit
OUT = HERE / 'run-01'
LEDGER = HERE / 'trial-ledger.json'
PRICE = ('r20', 'r63', 'dma200', 'dd252', 'rv20')
DYNAMIC = ('d4', 'neg_run', 'exit_pessimism')
LEGACY_NUMERIC = ('source_row', 'survey_week', 't_index', 'target_start_index',
                  'target_end_index', 'x', 'm20', 'y', 'max_stage_fall_pp') + PRICE
LEGACY_TEXT = ('source_date', 'assumed_available', 't', 'target_start',
               'target_end', 'base_exclusion', 'exclusion', 'asset', 'date')
PAIRS = [('BD', 'B'), ('BP', 'B'), ('BR', 'B'), ('BALL', 'B'),
         ('X_D', 'I'), ('X_P', 'I'), ('X_R', 'I'), ('B', 'I'),
         ('BD', 'I'), ('BP', 'I'), ('BR', 'I'), ('BALL', 'I')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def write_ledger(obj):
    # This one task-owned ledger is updated before and after each single fit.
    temp = LEDGER.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temp.replace(LEDGER)


def verify_inputs(protocol):
    for item in protocol['sources']:
        path = ROOT / item['path']
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError(f'source fingerprint changed: {item["path"]}')
    manifest = json.loads((HERE / 'authority-manifest.json').read_text())
    for item in manifest:
        if item['path'] == 'src/lei_signal/research/workflow_evaluation.py':
            if sha(KERNEL_PATH) != item['sha256']:
                raise RuntimeError('shared numerical kernel fingerprint changed')
    defs = json.loads(DEFINITIONS_PATH.read_text())
    if [x['definition']['field'] for x in defs] != list(DYNAMIC):
        raise RuntimeError('feature definitions changed')
    if list(protocol['models']) != ['I', 'B', 'X_D', 'X_P', 'X_R', 'BD', 'BP', 'BR', 'BALL']:
        raise RuntimeError('frozen model set changed')
    if protocol['models']['I'] != [] or list(protocol['definitions']['baseline_price']) != list(PRICE):
        raise RuntimeError('frozen baseline changed')


def dynamic_features(source):
    dates = pd.to_datetime(source['date'], errors='raise')
    weeks = dates.dt.to_period('W-SUN').astype('int64')
    if dates.duplicated().any() or (weeks.diff().dropna() <= 0).any():
        raise ValueError('duplicate or unordered survey calendar week')
    x = pd.to_numeric(source['bull_bear'], errors='coerce') * 100
    if not np.isfinite(x).all():
        raise ValueError('nonfinite source survey spread')
    consecutive = weeks.diff().eq(1)
    m20 = x.rolling(20, min_periods=20).mean().where(weeks.diff(19).eq(19))
    d4 = (x - x.shift(4)).where(weeks.diff(4).eq(4))
    exit_pessimism = pd.Series(np.nan, index=source.index, dtype=float)
    exit_pessimism.loc[consecutive] = ((x.shift(1) <= -25) & (x > -25)).loc[consecutive].astype(float)
    run = np.full(len(source), np.nan)
    known = False
    previous = 0
    for i, value in enumerate(x.to_numpy(float)):
        if i and not bool(consecutive.iloc[i]):
            known = False
        if value >= 0:
            run[i] = 0
            previous = 0
            known = True
        elif known:
            previous += 1
            run[i] = previous
    return pd.DataFrame({'survey_week': weeks, 'x': x, 'm20': m20,
                         'd4': d4, 'neg_run': run, 'exit_pessimism': exit_pessimism})


def old_extremes_exclusion_equal(current, archived, source_row):
    """One proven archived wording change for a missing post-survey quote."""
    if current == archived:
        return True
    return (source_row == 2037 and current == 'no_observation_quote'
            and archived == 'no_quote_after_assumed_date')


def legacy_observations(source, prices, features):
    old = pd.read_csv(ROOT / json.loads(PROTOCOL_PATH.read_text())['sources'][2]['path'])
    background = pd.read_csv(ROOT / json.loads(PROTOCOL_PATH.read_text())['sources'][4]['path'])
    if len(source) != len(old) or len(source) != len(background):
        raise RuntimeError('legacy source lengths differ')
    dates = pd.to_datetime(prices.Date).to_numpy('datetime64[ns]')
    if not pd.Series(dates).is_monotonic_increasing or not pd.Series(dates).is_unique:
        raise RuntimeError('unordered/duplicate quotes')
    c = pd.to_numeric(prices.Close, errors='coerce').to_numpy(float)
    c[~np.isfinite(c) | (c <= 0)] = np.nan
    close = pd.Series(c)
    b = pd.DataFrame({'r20': 100 * (close / close.shift(20) - 1),
                      'r63': 100 * (close / close.shift(63) - 1),
                      'dma200': 100 * (close / close.rolling(200, min_periods=200).mean() - 1),
                      'dd252': 100 * (close / close.rolling(252, min_periods=252).max() - 1),
                      'rv20': 100 * close.pct_change(fill_method=None).rolling(20, min_periods=20).std(ddof=1) * math.sqrt(20)})
    rows = []
    for i, record in source.iterrows():
        reported = pd.Timestamp(record.date)
        assumed = reported + pd.Timedelta(days=7)
        k = int(np.searchsorted(dates, assumed.to_datetime64(), side='right'))
        row = {'source_row': i, 'source_date': record.date,
               'survey_week': int(features.survey_week.iloc[i]),
               'assumed_available': str(assumed.date()) + ' 23:59:00',
               't_index': k, 't': None, 'target_start': None, 'target_end': None,
               'target_start_index': k + 1, 'target_end_index': k + 121,
               'x': float(features.x.iloc[i]), 'm20': float(features.m20.iloc[i]),
               'd4': float(features.d4.iloc[i]), 'neg_run': float(features.neg_run.iloc[i]),
               'exit_pessimism': float(features.exit_pessimism.iloc[i]),
               'y': np.nan, 'max_stage_fall_pp': np.nan}
        row.update({p: np.nan for p in PRICE})
        reasons = []
        if k >= len(c):
            reasons.append('no_observation_quote')
        else:
            row['t'] = prices.Date.iloc[k]
            row.update(b.iloc[k].to_dict())
            if not ('1995-01-01' <= row['t'] <= '2026-06-30'):
                reasons.append('observation_outside_range')
            if not np.isfinite([row['x']] + [row[p] for p in PRICE]).all():
                reasons.append('nonfinite_x_or_baseline')
            a, end = k + 1, k + 121
            if a < len(c):
                row['target_start'] = prices.Date.iloc[a]
            if end < len(c):
                row['target_end'] = prices.Date.iloc[end]
            if end >= len(c):
                reasons.append('incomplete_target_quotes')
            elif row['target_start'] > '2026-06-30' or row['target_end'] > '2026-06-30':
                reasons.append('target_beyond_cutoff')
            elif not np.isfinite(c[a:end + 1]).all():
                reasons.append('nonfinite_target_path')
            else:
                row['y'] = 100 * (c[end] / c[a] - 1)
                row['max_stage_fall_pp'] = 100 * float(np.max(1 - c[a:end + 1] / np.maximum.accumulate(c[a:end + 1])))
        row['base_exclusion'] = '|'.join(reasons)
        rows.append(row)
    obs = pd.DataFrame(rows)
    duplicate = obs.t.notna() & obs.duplicated('t', keep='last')
    obs.loc[duplicate, 'base_exclusion'] += '|duplicate_t_keep_latest_source'
    obs['base_eligible'] = obs.base_exclusion.eq('') & np.isfinite(obs.y)
    obs['eligible'] = obs.base_eligible & np.isfinite(obs[list(('m20',) + DYNAMIC)]).all(axis=1)
    obs['exclusion'] = obs.base_exclusion
    obs.loc[obs.m20.isna(), 'exclusion'] += '|incomplete_20_calendar_survey_weeks'
    legacy_exclusion = obs.exclusion.copy()
    for feature, reason in [('d4', 'incomplete_5_calendar_survey_weeks'),
                            ('neg_run', 'left_censored_negative_run'),
                            ('exit_pessimism', 'missing_adjacent_calendar_survey_week')]:
        obs.loc[obs[feature].isna(), 'exclusion'] += '|' + reason
    obs['negative_episode_id'] = obs.neg_run.eq(1).cumsum().where(obs.neg_run.gt(0))
    obs['asset'] = 'SPY'
    obs['date'] = obs.t
    # Compare every field that exists in each archive. The new exclusion column
    # adds only dynamic reasons, so its legacy prefix is compared separately.
    for archived in (old, background):
        for name in LEGACY_NUMERIC:
            if name in archived:
                np.testing.assert_allclose(pd.to_numeric(obs[name]), pd.to_numeric(archived[name]),
                                           atol=1e-10, rtol=1e-10, equal_nan=True,
                                           err_msg=f'legacy mismatch: {name}')
        for name in LEGACY_TEXT:
            if name in archived:
                current = (obs.base_exclusion if archived is old else legacy_exclusion) if name == 'exclusion' else obs[name]
                left = current.fillna('').astype(str).tolist()
                right = archived[name].fillna('').astype(str).tolist()
                if archived is old and name == 'exclusion':
                    same = all(old_extremes_exclusion_equal(a, b, int(row))
                               for a, b, row in zip(left, right, obs.source_row))
                else:
                    same = left == right
                if not same:
                    raise RuntimeError(f'legacy mismatch: {name}')
        if 'eligible' in archived:
            expected = obs.base_eligible if archived is old else (obs.base_eligible & obs.m20.notna())
            np.testing.assert_array_equal(expected.to_numpy(), archived.eligible.to_numpy())
    np.testing.assert_array_equal(obs.m20.notna().to_numpy(), background.m20.notna().to_numpy())
    obs['features'] = obs.apply(lambda r: {p: float(r[p]) for p in PRICE + ('x', 'm20') + DYNAMIC}, axis=1)
    return obs


def prepare():
    protocol = json.loads(PROTOCOL_PATH.read_text())
    verify_inputs(protocol)
    source = pd.read_csv(ROOT / protocol['sources'][0]['path'])
    prices = pd.read_csv(ROOT / protocol['sources'][1]['path'])
    features = dynamic_features(source)
    np.testing.assert_allclose(source.ma20_pp, features.x.rolling(20).mean(),
                               atol=1e-12, equal_nan=True)
    obs = legacy_observations(source, prices, features)
    designs = {}
    boundaries = []
    for year in range(2010, 2027):
        boundary = f'{year}-01-01'
        train = obs[obs.eligible & obs.t.lt(boundary) & obs.target_end.lt(boundary)].copy()
        ev = obs[obs.eligible & obs.t.str.startswith(str(year), na=False)].copy()
        if ev.empty or len(train) < 100:
            raise RuntimeError(f'year {year}: missing evaluation or fewer than 100 matured training rows')
        if train.t.max() >= boundary or train.target_end.max() >= boundary:
            raise RuntimeError(f'year {year}: immature training target')
        boundaries.append({'year': year, 'training': len(train), 'evaluation': len(ev),
                           'train_observation_max': train.t.max(),
                           'train_target_end_max': train.target_end.max(),
                           'unmatured_training_excluded': int((obs.eligible & obs.t.lt(boundary) & obs.target_end.ge(boundary)).sum()),
                           'first_evaluation': ev.t.min(), 'last_evaluation': ev.t.max()})
        designs[year] = {}
        for model, cols in protocol['models'].items():
            design = _ols_design(train, ev, cols, 'equal_asset')
            if design['zero'].any() or design['rank'] != len(cols):
                raise RuntimeError(f'year {year} model {model}: zero variance or deficient X rank')
            designs[year][model] = design
    counts = {'source_rows': len(source), 'price_rows': len(prices),
              'complete_20week_inputs': int(features.m20.notna().sum()),
              'complete_d4_inputs': int(features.d4.notna().sum()),
              'known_negative_run_inputs': int(features.neg_run.notna().sum()),
              'known_recovery_inputs': int(features.exit_pessimism.notna().sum()),
              'base_eligible_all_years': int(obs.base_eligible.sum()),
              'common_eligible_all_years': int(obs.eligible.sum()),
              'common_evaluation_rows': int(sum(b['evaluation'] for b in boundaries)),
              'exclusion_counts_nonexclusive': obs.exclusion.str.split('|').explode().value_counts().drop('', errors='ignore').to_dict()}
    return protocol, obs, designs, boundaries, counts


def score(frame):
    if frame.empty:
        raise ValueError('empty evaluation group')
    models = list(json.loads(PROTOCOL_PATH.read_text())['models'])
    error = {m: frame['pred_' + m].to_numpy(float) - frame.y.to_numpy(float) for m in models}
    mse = {m: float(np.mean(e * e)) for m, e in error.items()}
    return {'n': len(frame), 'mse': mse,
            'rmse': {m: float(math.sqrt(v)) for m, v in mse.items()},
            'mean_absolute_error': {m: float(np.mean(np.abs(e))) for m, e in error.items()},
            'improvement_pct': {a + '_vs_' + b: 100 * (1 - mse[a] / mse[b]) for a, b in PAIRS},
            'squared_error_reduction_sum': {a + '_vs_' + b: len(frame) * (mse[b] - mse[a]) for a, b in PAIRS}}


def intervals(pred, block, names):
    first, last = int(pred.survey_week.min()), int(pred.survey_week.max())
    axis_n = last - first + 1
    loss = np.full((axis_n, len(names)), np.nan)
    positions = pred.survey_week.to_numpy(int) - first
    if len(np.unique(positions)) != len(positions):
        raise RuntimeError('duplicate survey week in predictions')
    for j, model in enumerate(names):
        loss[positions, j] = (pred['pred_' + model].to_numpy(float) - pred.y.to_numpy(float)) ** 2
    rng = np.random.default_rng(20261003)
    draws = {a + '_vs_' + b: [] for a, b in PAIRS}
    for _ in range(2000):
        starts = rng.integers(0, axis_n - block + 1, math.ceil(axis_n / block))
        ix = np.concatenate([np.arange(k, k + block) for k in starts])[:axis_n]
        values = np.nanmean(loss[ix], axis=0)
        for a, b in PAIRS:
            draws[a + '_vs_' + b].append(100 * (1 - values[names.index(a)] / values[names.index(b)]))
    result = {}
    for a, b in PAIRS:
        key = a + '_vs_' + b
        v = np.asarray(draws[key])
        entry = {'p2_5': float(np.quantile(v, .025)), 'p97_5': float(np.quantile(v, .975)),
                 'valid_draws': len(v), 'calendar_weeks': axis_n,
                 'missing_calendar_weeks': int(np.isnan(loss[:, 0]).sum())}
        if b == 'B':
            entry.update({'p0_625': float(np.quantile(v, .00625)),
                          'p99_375': float(np.quantile(v, .99375))})
        result[key] = entry
    return result


def raw_group(frame):
    if frame.empty:
        return {'n': 0, 'mean_return_pp': None, 'median_return_pp': None, 'up_share': None}
    return {'n': len(frame), 'mean_return_pp': float(frame.y.mean()),
            'median_return_pp': float(frame.y.median()), 'up_share': float(frame.y.gt(0).mean())}


def require_freeze(protocol):
    freeze_path = HERE / 'execution-freeze.json'
    if not freeze_path.is_file():
        raise RuntimeError('controller execution-freeze.json missing')
    frozen = json.loads(freeze_path.read_text())
    expected = {'protocol_sha256': sha(PROTOCOL_PATH), 'analysis_sha256': sha(Path(__file__)),
                'reused_kernel_sha256': sha(KERNEL_PATH), 'definitions_sha256': sha(DEFINITIONS_PATH)}
    for field, value in expected.items():
        if frozen.get(field) != value:
            raise RuntimeError(f'execution freeze mismatch: {field}')
    if frozen.get('inputs') != protocol['sources']:
        raise RuntimeError('execution freeze inputs do not match frozen protocol sources')
    return frozen


def fit():
    protocol, obs, designs, boundaries, counts = prepare()
    require_freeze(protocol)
    if OUT.exists() or LEDGER.exists():
        raise RuntimeError('run output or trial ledger already exists: no silent rerun')
    OUT.mkdir(exist_ok=False)
    started = time.monotonic()
    ledger = {'fits_attempted': 0, 'fits_completed': 0, 'core_fits_max': 153,
              'family_previous_fits_at_least': protocol['budget']['family_prior_fits_at_least'],
              'records': []}
    write_ledger(ledger)
    obs.drop(columns='features').to_csv(OUT / 'observations.csv', index=False, mode='x')
    write_new(OUT / 'qualification.json', {'counts': counts, 'boundaries': boundaries,
              'legacy_reconstruction': 'all legacy fields matched old h120 and background observations',
              'availability': 'retrospective; source+7 day release is assumed, not historically verified'})
    fits = []
    predictions = []
    try:
        for year in range(2010, 2027):
            boundary = f'{year}-01-01'
            train = obs[obs.eligible & obs.t.lt(boundary) & obs.target_end.lt(boundary)].copy()
            ev = obs[obs.eligible & obs.t.str.startswith(str(year), na=False)].copy()
            for model in protocol['models']:
                if time.monotonic() - started >= protocol['budget']['core_wall_minutes_max'] * 60:
                    raise RuntimeError('core wall time budget exhausted before next fit')
                if ledger['fits_attempted'] >= 153:
                    raise RuntimeError('core fit budget exhausted')
                record = {'trial': f'core-{year}-{model}', 'year': year, 'model': model,
                          'status': 'running', 'training_rows': len(train), 'evaluation_rows': len(ev),
                          'features': protocol['models'][model],
                          'elapsed_before_seconds': float(time.monotonic() - started)}
                ledger['records'].append(record)
                ledger['fits_attempted'] += 1
                write_ledger(ledger)
                try:
                    prediction, detail = _ols_fit(train, designs[year][model])
                    ev['pred_' + model] = prediction
                    detail.update(year=year, model=model, train_target_end_max=train.target_end.max(),
                                  train_t_max=train.t.max())
                    fits.append(detail)
                    record['status'] = 'completed'
                    record['elapsed_after_seconds'] = float(time.monotonic() - started)
                    ledger['fits_completed'] += 1
                    write_ledger(ledger)
                except Exception as exc:
                    record.update(status='failed', error=repr(exc),
                                  elapsed_after_seconds=float(time.monotonic() - started))
                    write_ledger(ledger)
                    raise
            predictions.append(ev)
        pred = pd.concat(predictions).sort_values('t').reset_index(drop=True)
        pred.drop(columns='features').to_csv(OUT / 'predictions.csv', index=False, mode='x')
        write_new(OUT / 'fits.json', fits)
        write_new(OUT / 'boundaries.json', boundaries)
        names = list(protocol['models'])
        overlap = np.maximum(0, np.minimum(pred.target_end_index.to_numpy()[:-1], pred.target_end_index.to_numpy()[1:]) -
                             np.maximum(pred.target_start_index.to_numpy()[:-1], pred.target_start_index.to_numpy()[1:]))
        concentration = {}
        for a, b in PAIRS[:4]:
            key = a + '_vs_' + b
            contribution = (pred['pred_' + b] - pred.y) ** 2 - (pred['pred_' + a] - pred.y) ** 2
            top = contribution.abs().nlargest(5).index
            concentration[key] = {'top5_source_rows': pred.loc[top, 'source_row'].astype(int).tolist(),
                                  'top5_abs_share_of_abs_contributions': (float(contribution.loc[top].abs().sum() / contribution.abs().sum())
                                                                          if contribution.abs().sum() > 0 else None),
                                  'remove_top5': score(pred.drop(index=top))['improvement_pct'][key]}
        event_counts = {str(y): {'exit_pessimism': int(f.exit_pessimism.sum()),
                                 'negative_run_rows': int(f.neg_run.gt(0).sum()),
                                 'negative_run_episodes': int(f.negative_episode_id.nunique())}
                        for y, f in pred.groupby(pred.t.str[:4])}
        counts.update(eval_first=pred.t.min(), eval_last=pred.t.max(),
                      target_first=pred.target_start.min(), target_last=pred.target_end.max(),
                      adjacent_pairs=len(overlap), overlapping_adjacent_pairs=int((overlap > 0).sum()),
                      overlap_mean_segments=float(overlap.mean()), overlap_max_segments=int(overlap.max()))
        result = {'overall': score(pred), 'coverage': counts,
                  'intervals': {str(block): intervals(pred, block, names) for block in (52, 104)},
                  'annual': {str(y): score(f) for y, f in pred.groupby(pred.t.str[:4])},
                  'periods': {name: score(pred[pred.t.between(start, end)]) for name, start, end in
                              [('2010-2014', '2010-01-01', '2014-12-31'),
                               ('2015-2019', '2015-01-01', '2019-12-31'),
                               ('2020-2026', '2020-01-01', '2026-06-30')]},
                  'remove_eval_year': {str(y): score(pred[~pred.t.str.startswith(str(y))]) for y in range(2010, 2027)},
                  'remove_top5_absolute_contributions': concentration,
                  'event_counts_by_year': event_counts,
                  'raw_groups': {key: raw_group(pred[mask]) for key, mask in
                                 [('d4_positive', pred.d4.gt(0)), ('d4_nonpositive', pred.d4.le(0)),
                                  ('neg_run_positive', pred.neg_run.gt(0)), ('neg_run_zero', pred.neg_run.eq(0)),
                                  ('recovery_one', pred.exit_pessimism.eq(1)), ('recovery_zero', pred.exit_pessimism.eq(0))]},
                  'fits': len(fits),
                  'uncertainty': 'fixed prediction block reaggregation only; no refit uncertainty or independent history'}
        result['core_wall_seconds'] = float(time.monotonic() - started)
        write_new(OUT / 'results.json', result)
        print(json.dumps({'completed_fits': len(fits), 'evaluation_rows': len(pred)}, ensure_ascii=False))
    except Exception:
        (OUT / 'execution-failure.txt').write_text(traceback.format_exc())
        raise


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare-only', action='store_true')
    group.add_argument('--fit', action='store_true')
    parser.add_argument('--output', type=Path, help='new JSON preflight file, outside run-01; prepare-only only')
    args = parser.parse_args()
    if args.fit:
        if args.output:
            parser.error('--output only applies to --prepare-only')
        fit()
    else:
        protocol, obs, designs, boundaries, counts = prepare()
        result = {'status': 'prepared_no_fit', 'counts': counts, 'boundaries': boundaries,
                  'models': list(protocol['models']), 'preflight_matrices': 153,
                  'legacy_fields_reconstructed': list(LEGACY_NUMERIC + LEGACY_TEXT) + ['base_eligible'],
                  'code_sha256': sha(Path(__file__)), 'protocol_sha256': sha(PROTOCOL_PATH),
                  'kernel_sha256': sha(KERNEL_PATH), 'definitions_sha256': sha(DEFINITIONS_PATH)}
        if args.output:
            dest = args.output.resolve()
            if not dest.is_relative_to(HERE) or dest.is_relative_to(OUT) or dest.exists():
                raise RuntimeError('preflight output must be a new file in research directory outside run-01')
            write_new(dest, result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
