#!/usr/bin/env python3
"""Frozen AAII120risk: default synthetic only; real execution needs reviewed flag.
No network, fitting search, global runtime consumers or production writes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import minimize
from scipy.special import expit, logit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = next(p for p in HERE.parents if (p / 'AGENTS.md').exists())
PROTOCOL_HASH = '10610236e4da9e497ee43086d3f5b9845d0c7bc9c9f16018dc15d254d66f8230'
MANIFEST_HASH = 'f304a3ef739657680d40154be187568fca76a801d60314900ce4e316ab86dee8'
INPUT_HASHES = {'aaii-candidate-values.csv': '12f30895c7ea2c68663a60f2d60a85384dfd0d9d324474e0501298e460cf9c05',
                'px_SPY.csv': '952f397be0ccc5745185b91cce6acc781737c0f30a7a34aa8a230ae892ed5e45'}
BASE = ['r20', 'r63', 'dma200', 'dd252', 'rv20']
MODELS = {'I': [], 'V': ['rv20'], 'B': BASE, 'BX': BASE + ['x']}
PAIRS = [('BX', 'B'), ('BX', 'I'), ('BX', 'V'), ('B', 'I'), ('V', 'I'), ('B', 'V')]
START, EVAL, CUTOFF = map(pd.Timestamp, ['1995-01-01', '2010-01-01', '2026-06-30'])
H = 120
PENALTY = .001
OPTIONS = {'maxiter': 1000, 'ftol': 1e-12, 'gtol': 1e-8}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(obj):
    if isinstance(obj, dict): return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, pd.Series): return clean(obj.tolist())
    if isinstance(obj, (list, tuple, np.ndarray)): return [clean(v) for v in obj]
    if obj is pd.NaT: return None
    if isinstance(obj, (datetime, pd.Timestamp)): return obj.isoformat()
    if isinstance(obj, (float, np.floating)): return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.bool_): return bool(obj)
    return obj


def write_json(path, value):
    Path(path).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def bindings():
    if sha(ROOT / 'protocol.json') != PROTOCOL_HASH: raise RuntimeError('STOP: protocol drift')
    if sha(ROOT / 'source-manifest.json') != MANIFEST_HASH: raise RuntimeError('STOP: source manifest drift')
    inputs = {}
    for name, expected in INPUT_HASHES.items():
        p = ROOT / 'inputs' / name
        if sha(p) != expected: raise RuntimeError('STOP: input drift: ' + name)
        inputs[name] = {'sha256': expected, 'bytes': p.stat().st_size}
    norm_binding = json.loads((ROOT / 'controller/norm-binding.json').read_text())
    snapshots = {r['source_path']: ROOT / r['snapshot_path'] for r in norm_binding['standards']}
    authority = []
    for rec in json.loads((ROOT / 'source-manifest.json').read_text())['files']:
        path = rec['path']
        # Approved desktop originals are checked via authorized byte-identical snapshots.
        if rec.get('role') == 'readonly approved desktop authority':
            p = REPO / 'docs/experiments/raw/sentiment-library-s01-readiness-2026-09-29/strategy-source' / Path(path).name
        else:
            p = snapshots.get(path, REPO / path)
        actual = sha(p)
        authority.append({'bound_path': path, 'checked_path': str(p), 'bound_sha256': rec['sha256'],
                          'actual_sha256': actual, 'changed': actual != rec['sha256']})
    # Frozen protocol is the arithmetic authority; shared standard drift is exposed,
    # but cannot silently alter this method or permit real execution without review.
    return {'protocol_sha256': PROTOCOL_HASH, 'source_manifest_sha256': MANIFEST_HASH,
            'inputs': inputs, 'authority_audit': authority,
            'norm_binding_sha256': sha(ROOT / 'controller/norm-binding.json'),
            'implementation_clarification_sha256': sha(ROOT / 'controller/implementation-clarification.json')}


def prepare_prices(frame):
    p = frame.copy()
    p['Date'] = pd.to_datetime(p['Date'], errors='raise').dt.normalize()
    if p['Date'].isna().any() or p['Date'].duplicated().any(): raise RuntimeError('STOP: quote dates invalid')
    p = p.sort_values('Date', kind='stable').reset_index(drop=True)
    p['Close'] = pd.to_numeric(p['Close'], errors='coerce')
    p.loc[~np.isfinite(p['Close']) | (p['Close'] <= 0), 'Close'] = np.nan
    c = p['Close']  # Keep invalid quotation positions; do not dropna or fill.
    p['r20'] = 100 * (c / c.shift(20) - 1)
    p['r63'] = 100 * (c / c.shift(63) - 1)
    p['dma200'] = 100 * (c / c.rolling(200, min_periods=200).mean() - 1)
    p['dd252'] = 100 * (c / c.rolling(252, min_periods=252).max() - 1)
    ret = c.pct_change(fill_method=None)
    p['rv20'] = 100 * ret.rolling(20, min_periods=20).std(ddof=1) * np.sqrt(20)
    return p


def window_risk(closes):
    c = np.asarray(closes, dtype=float)
    if len(c) != H + 1 or not np.isfinite(c).all() or np.any(c <= 0):
        raise ValueError('requires exactly121 finite positive closes')
    return float(100 * np.max(1 - c / np.maximum.accumulate(c)))


def observations(survey, prices):
    s = survey.copy()
    s['source_date'] = pd.to_datetime(s['date'], errors='raise').dt.normalize()
    if s['source_date'].isna().any(): raise RuntimeError('STOP: missing source date')
    s['source_row'] = np.arange(len(s))
    s = s.sort_values(['source_date', 'source_row'], kind='stable')
    dates, c = prices['Date'].to_numpy(dtype='datetime64[ns]'), prices['Close'].to_numpy()
    rows = []
    for source in s.to_dict('records'):
        assumed = source['source_date'] + pd.Timedelta(days=7)
        k = int(np.searchsorted(dates, assumed.to_datetime64(), side='right'))
        b = k + 121
        bullish = pd.to_numeric(source['bullish'], errors='coerce')
        bearish = pd.to_numeric(source['bearish'], errors='coerce')
        r = {'source_row': source['source_row'], 'source_date': source['source_date'],
             'assumed_available': (assumed + pd.Timedelta(hours=23, minutes=59)).tz_localize('Asia/Shanghai'),
             't': pd.NaT, 't_index': k, 'target_start': pd.NaT, 'target_end': pd.NaT,
             'target_start_index': k + 1, 'target_end_index': b, 'h': H,
             'x': 100 * (bullish - bearish), 'y': np.nan, **{col: np.nan for col in BASE}}
        reasons = []
        if k >= len(prices): reasons.append('no_quote_after_assumed_date')
        else:
            r['t'] = prices.at[k, 'Date']
            for col in BASE: r[col] = prices.at[k, col]
            if not START <= r['t'] <= CUTOFF: reasons.append('observation_outside_range')
            if not np.isfinite([r[col] for col in ['x'] + BASE]).all(): reasons.append('nonfinite_x_or_baseline')
            if k + 1 < len(prices): r['target_start'] = prices.at[k + 1, 'Date']
            if b < len(prices): r['target_end'] = prices.at[b, 'Date']
            if b >= len(prices): reasons.append('incomplete_target_quotes')
            elif prices.at[b, 'Date'] > CUTOFF: reasons.append('target_beyond_cutoff')
            elif not np.isfinite(c[k + 1:b + 1]).all(): reasons.append('nonfinite_target_path')
            else: r['y'] = window_risk(c[k + 1:b + 1])
        r['exclusion'] = '|'.join(reasons)
        rows.append(r)
    out = pd.DataFrame(rows)
    if out.empty: raise RuntimeError('STOP: no surveys')
    dup = out['t'].notna() & out.duplicated('t', keep='last')
    for i in out.index[dup]:
        out.at[i, 'exclusion'] += ('|' if out.at[i, 'exclusion'] else '') + 'duplicate_t_keep_latest_source'
    out['eligible'] = out['exclusion'].eq('') & np.isfinite(out['y'])
    return out.sort_values(['t', 'source_date', 'source_row'], kind='stable').reset_index(drop=True)


def train_mask(obs, year):
    boundary = pd.Timestamp(f'{year}-01-01')
    return obs['eligible'] & (obs['t'] >= START) & (obs['t'] < boundary) & (obs['target_end'] < boundary)


def objective(theta, z, y_fraction):
    p = expit(theta[0] + z @ theta[1:])
    err = p - y_fraction
    value = np.mean(err ** 2) + PENALTY * np.sum(theta[1:] ** 2)
    core = 2 * err * p * (1 - p) / len(y_fraction)
    gradient = np.r_[np.sum(core), z.T @ core + 2 * PENALTY * theta[1:]]
    if not np.isfinite(value) or not np.isfinite(gradient).all(): raise RuntimeError('STOP: nonfinite objective')
    return float(value), gradient


def fit_model(train, features, log=None):
    if len(train) < 100: raise RuntimeError('STOP: insufficient mature training')
    y = train['y'].to_numpy(float) / 100
    if not np.isfinite(y).all() or np.any(y < 0) or np.any(y >= 1): raise RuntimeError('STOP: invalid risk target')
    mean_y = float(y.mean())
    fit = {'features': list(features), 'train_rows': len(train), 'target_mean_fraction': mean_y,
           'train_t_max': train['t'].max(), 'train_label_end_max': train['target_end'].max()}
    if not features:
        fit.update({'branch': 'arithmetic_mean', 'constant_pp': 100 * mean_y, 'optimizer_started': False})
        return fit
    a = train[features].to_numpy(float)
    mean, scale = a.mean(axis=0), a.std(axis=0, ddof=0)
    if not np.isfinite(a).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise RuntimeError('STOP: invalid training-only scaling')
    z = (a - mean) / scale
    fit.update({'mean': mean, 'scale': scale})
    if mean_y == 0:
        fit.update({'branch': 'constant_zero', 'constant_pp': 0., 'intercept': None,
                    'beta': None, 'optimizer_started': False, 'final_gradient': None})
        return fit
    theta0 = np.r_[logit(mean_y), np.zeros(len(features))]
    history = []
    def record(theta, stage):
        value, grad = objective(theta, z, y)
        entry = {'iteration': len(history), 'stage': stage, 'beta': theta.copy(),
                 'objective': value, 'gradient': grad.copy(), 'max_abs_gradient': float(np.max(np.abs(grad)))}
        history.append(entry)
        if log: log(entry)
    record(theta0, 'single_start')
    result = minimize(objective, theta0, args=(z, y), method='L-BFGS-B', jac=True,
                      callback=lambda theta: record(theta, 'iteration'), options=OPTIONS)
    record(result.x, 'final')
    value, grad = objective(result.x, z, y)
    fit.update({'branch': 'bounded_sigmoid', 'optimizer_started': True, 'beta': result.x,
                'intercept': float(result.x[0]), 'success': bool(result.success), 'status': int(result.status),
                'message': str(result.message), 'nit': int(result.nit), 'nfev': int(result.nfev),
                'njev': int(result.njev), 'objective': value, 'final_gradient': grad,
                'max_abs_gradient': float(np.max(np.abs(grad))), 'optimizer_history': history,
                'initial_objective': history[0]['objective'], 'final_objective': value,
                'objective_change_final_minus_initial': value-history[0]['objective']})
    if (not result.success or not np.isfinite(result.x).all() or fit['max_abs_gradient'] > 1e-6
            or value > fit['initial_objective'] + 1e-12):
        error = RuntimeError('STOP: optimizer invalid: convergence/gradient/objective-nonincreasing requirement')
        error.fit_record = fit
        raise error
    return fit


def predict(frame, fit):
    if fit['branch'] in ['arithmetic_mean', 'constant_zero']:
        p = np.full(len(frame), fit['constant_pp'])
    else:
        a = frame[fit['features']].to_numpy(float)
        p = 100 * expit(fit['beta'][0] + ((a - fit['mean']) / fit['scale']) @ fit['beta'][1:])
    if not np.isfinite(p).all() or np.any(p < 0) or np.any(p > 100): raise RuntimeError('STOP: prediction outside physical risk bounds')
    return p


def annual_predictions(obs, ledger, persist=lambda: None):
    rows, fits = [], []
    for year in range(2010, 2027):
        ev = obs.loc[obs['eligible'] & (obs['t'].dt.year == year)].copy()
        if ev.empty: continue
        tr = obs.loc[train_mask(obs, year)].copy()
        boundary = pd.Timestamp(f'{year}-01-01')
        if not (tr['t'].lt(boundary).all() and tr['target_end'].lt(boundary).all()): raise RuntimeError('STOP: immature train label')
        common_ids = ev['source_row'].tolist()
        for model, features in MODELS.items():
            if ledger['started_fits'] >= 68: raise RuntimeError('STOP: core fit budget exhausted')
            attempt = {'year': year, 'model': model, 'train_rows': len(tr), 'eval_rows': len(ev),
                       'started_at': datetime.now(timezone.utc), 'status': 'started', 'optimizer_log': []}
            ledger['attempts'].append(attempt); ledger['started_fits'] += 1; persist()
            try:
                def optimizer_log(row):
                    attempt['optimizer_log'].append(row)
                    persist()
                fit = fit_model(tr, features, log=optimizer_log)
                fit.update({'year': year, 'model': model, 'train_t_min': tr['t'].min(),
                            'eval_t_min': ev['t'].min(), 'eval_t_max': ev['t'].max()})
                if ev['source_row'].tolist() != common_ids: raise RuntimeError('STOP: model population mismatch')
                ev['pred_' + model] = predict(ev, fit)
                fits.append(fit); attempt['status'] = 'completed'; ledger['completed_fits'] += 1
                attempt['result'] = fit
            except Exception as exc:
                attempt['status'] = 'failed'; attempt['error'] = str(exc); ledger['failed_fits'] += 1
                if hasattr(exc, 'fit_record'): attempt['result'] = exc.fit_record
                persist(); raise
            persist()
        rows.append(ev)
    if not rows: raise RuntimeError('STOP: no eligible evaluation rows')
    return pd.concat(rows).sort_values(['t', 'source_row'], kind='stable').reset_index(drop=True), fits


def scores(frame):
    if not len(frame): return {'n': 0, 'status': 'not_evaluated', 'metrics': None, 'improvement_pct': None}
    metrics = {}
    y = frame['y'].to_numpy(float)
    for model in MODELS:
        p = frame['pred_' + model].to_numpy(float); err = p - y
        metrics[model] = {'mse': float(np.mean(err ** 2)), 'rmse': float(np.sqrt(np.mean(err ** 2))),
                          'mae': float(np.mean(np.abs(err))), 'mean_prediction': float(p.mean()),
                          'mean_actual': float(y.mean()), 'signed_mean_error': float(err.mean()),
                          'prediction_min': float(p.min()), 'prediction_max': float(p.max()),
                          'negative_count': int((p < 0).sum()), 'over100_count': int((p > 100).sum())}
    mse = {m: metrics[m]['mse'] for m in MODELS}
    return {'n': len(frame), 'status': 'evaluated', 't_start': frame['t'].min() if 't' in frame else None,
            't_end': frame['t'].max() if 't' in frame else None,
            'target_end_max': frame['target_end'].max() if 'target_end' in frame else None,
            'metrics': metrics, 'improvement_pct': {f'{m}_vs_{b}': 100 * (1 - mse[m] / mse[b]) if mse[b] > 0 else None for m, b in PAIRS},
            'squared_error_reduction_sum': {f'{m}_vs_{b}': len(frame) * (mse[b] - mse[m]) for m, b in PAIRS}}


def overlap_table(pred):
    out = pred[['source_row', 'target_start_index', 'target_end_index']].copy()
    a, b = out['target_start_index'].to_numpy(), out['target_end_index'].to_numpy()
    spans = np.maximum(0, np.minimum(b[:-1], b[1:]) - np.maximum(a[:-1], a[1:]))
    out['shared_return_segments_with_next'] = np.r_[spans, np.nan]
    return out, {'adjacent_pairs': len(spans), 'shared_positive_pairs': int((spans > 0).sum()),
                 'shared_positive_percent': 100 * float((spans > 0).mean()) if len(spans) else None,
                 'segments_min': int(spans.min()) if len(spans) else None,
                 'segments_median': float(np.median(spans)) if len(spans) else None,
                 'segments_max': int(spans.max()) if len(spans) else None}


def blocks(pred, block):
    n = len(pred)
    if n < block: raise RuntimeError('STOP: not enough rows for frozen block size')
    loss = np.column_stack([(pred['pred_' + m] - pred['y']) ** 2 for m in MODELS])
    ids = {m: i for i, m in enumerate(MODELS)}; rng = np.random.default_rng(20260929 + block)
    rows = []
    for draw in range(2000):
        starts = rng.integers(0, n - block + 1, size=math.ceil(n / block))
        idx = np.concatenate([np.arange(k, k + block) for k in starts])[:n]
        mse = loss[idx].mean(axis=0)
        r = {'draw': draw, 'seed': 20260929 + block, 'block_rows': block, 'n': n,
             'block_starts': json.dumps(starts.tolist(), separators=(',', ':'))}
        r.update({'mse_' + m: float(mse[i]) for m, i in ids.items()})
        r.update({f'improvement_{m}_vs_{b}': 100 * (1 - mse[ids[m]] / mse[ids[b]]) if mse[ids[b]] > 0 else np.nan for m, b in PAIRS})
        rows.append(r)
    table = pd.DataFrame(rows)
    intervals = {}
    for m, b in PAIRS:
        values = table[f'improvement_{m}_vs_{b}'].dropna()
        intervals[f'{m}_vs_{b}'] = {'valid_draws': len(values), 'p2_5': values.quantile(.025), 'p97_5': values.quantile(.975), 'refit': False}
    return table, intervals


def summarize(obs, pred, prices):
    overall = scores(pred)
    annual = {year: scores(pred.loc[pred['t'].dt.year == year]) for year in range(2010, 2027)}
    bands = {name: scores(pred.loc[pred['t'].between(a, b)]) for name, a, b in [
        ('2010-2014', '2010-01-01', '2014-12-31'), ('2015-2019', '2015-01-01', '2019-12-31'), ('2020-2026H1', '2020-01-01', '2026-06-30')]}
    contributions = {}
    for m, b in PAIRS:
        key = f'{m}_vs_{b}'
        vals = {year: result['squared_error_reduction_sum'][key] for year, result in annual.items() if result['n']}
        best, worst = max(vals, key=vals.get), min(vals, key=vals.get)
        contributions[key] = {'annual': vals, 'sum_positive': sum(v for v in vals.values() if v > 0),
                              'sum_negative': sum(v for v in vals.values() if v < 0),
                              'total': sum(vals.values()), 'largest_reduction_year': best,
                              'largest_loss_increase_year': worst, 'remove_largest_year': scores(pred.loc[pred['t'].dt.year != best])}
    reasons = obs['exclusion'].str.split('|').explode(); reasons = reasons.loc[reasons != ''].value_counts().to_dict()
    overlap, overlap_summary = overlap_table(pred)
    coverage = {'raw_survey_rows': len(obs), 'raw_quote_rows': len(prices),
                'valid_quote_rows': int(prices['Close'].notna().sum()),
                'finite_x_and_background_rows': int(np.isfinite(obs[['x'] + BASE]).all(axis=1).sum()),
                'finite_target_rows': int(obs['y'].notna().sum()), 'common_eligible_rows': int(obs['eligible'].sum()),
                'evaluation_rows': len(pred), 'exclusion_counts_nonexclusive': reasons,
                'quote_start': prices['Date'].min(), 'quote_end': prices['Date'].max(),
                'eval_t_first': pred['t'].min(), 'eval_t_last': pred['t'].max(),
                'target_end_last': pred['target_end'].max(), 'overlap': overlap_summary}
    return {'overall': overall, 'annual': annual, 'bands': bands, 'contributions': contributions,
            'delete_one_year_no_refit': {year: scores(pred.loc[pred['t'].dt.year != year]) for year in range(2010, 2027)},
            'coverage': coverage, 'uncertainty': {}, 'units': {'y': 'percentage points of within-window peak-to-trough decline',
              'mse': 'squared percentage points', 'primary': 'relative squared estimation error reduction percent, NOT investment return'},
            'limitations': ['survey date+7 scenario, true historical first release and revisions unknown',
              'price adjustment vintage unknown; historical cache already seen', 'exploratory question/method after earlier results, no independent new validation',
              'single-start nonlinear local optimum not global-optimum proof', 'fixed-prediction block draws do not refit or cover whole-family selection/model uncertainty',
              'not probability, account loss, original E confirmation or production']}, overlap


def real_run():
    output = HERE / 'run-01'
    if output.exists(): raise RuntimeError('STOP: run-01 exists; never overwrite or silently rerun')
    bound = bindings()
    if any(r['changed'] for r in bound['authority_audit']): raise RuntimeError('STOP: shared authority drift requires controller reconciliation')
    output.mkdir()
    ledger = {'started_fits': 0, 'completed_fits': 0, 'failed_fits': 0, 'attempts': [],
              'core_batches_started': 1, 'correction_batches_started': 0, 'core_fit_limit': 68}
    begin = time.monotonic(); started = datetime.now(timezone.utc)
    def persist():
        write_json(output / 'fit-ledger.json', ledger)
        if time.monotonic() - begin > 900: raise RuntimeError('STOP: wall budget exceeded')
        if sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()) > 20971520: raise RuntimeError('STOP: output size budget exceeded')
    try:
        obs = observations(pd.read_csv(ROOT / 'inputs/aaii-candidate-values.csv'),
                           prices := prepare_prices(pd.read_csv(ROOT / 'inputs/px_SPY.csv')))
        obs.to_csv(output / 'observations.csv', index=False, float_format='%.17g'); persist()
        pred, fits = annual_predictions(obs, ledger, persist)
        pred.to_csv(output / 'predictions.csv', index=False, float_format='%.17g')
        write_json(output / 'fits.json', fits)
        losses = pred[['source_row', 't', 'target_start', 'target_end', 'y']].copy()
        for m in MODELS: losses['loss_' + m] = (pred['pred_' + m] - pred['y']) ** 2
        losses.to_csv(output / 'losses.csv', index=False, float_format='%.17g')
        result, overlap = summarize(obs, pred, prices)
        overlap.to_csv(output / 'overlap.csv', index=False)
        for block in [52, 104]:
            draw, interval = blocks(pred, block)
            draw.to_csv(output / f'draws-block{block}.csv', index=False, float_format='%.17g')
            result['uncertainty'][str(block)] = interval; persist()
        write_json(output / 'results.json', result)
        final = bindings()
        if final != bound: raise RuntimeError('STOP: source/authority drift during run')
        persist()
        write_json(output / 'manifest.json', {'status': 'completed', 'protocol_id': 'sentiment.aaii-risk120-increment@1.0.0',
          'started_at': started, 'completed_at': datetime.now(timezone.utc), 'binding': bound,
          'code_sha256': sha(__file__), 'started_fits': ledger['started_fits'], 'completed_fits': ledger['completed_fits'],
          'failed_fits': ledger['failed_fits'], 'python': platform.python_version(), 'numpy': np.__version__,
          'pandas': pd.__version__, 'scipy': scipy.__version__, 'argv': sys.argv, 'network_requests': 0,
          'outputs': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(output.iterdir())}})
        persist()
    except Exception as exc:
        write_json(output / 'fit-ledger.json', ledger)
        write_json(output / 'failure.json', {'status': 'paused', 'started_at': started, 'error': str(exc),
          'binding': bound, 'actual_started_fits': ledger['started_fits'], 'remaining_core_fits': 68-ledger['started_fits'],
          'automatic_correction_not_authorized': True})
        raise


def synthetic_checks():
    checks = []
    def test(name, actual, expected, tolerance=1e-11):
        ok = bool(np.allclose(actual, expected, atol=tolerance, rtol=tolerance))
        checks.append({'name': name, 'actual': actual, 'independent_expected': expected, 'passed': ok})
        if not ok: raise AssertionError(name)
    increasing = np.arange(100, 221, dtype=float)
    test('increasing_zero_risk', window_risk(increasing), 0.)
    path = np.r_[100., 120., 60., np.full(118, 90.)]
    # Independent all-pairs peak/trough oracle, no cumulative-max implementation.
    brute = max(100*(1-path[j]/path[i]) for i in range(121) for j in range(i,121))
    test('peak_later_trough_exact50', window_risk(path), brute)
    test('window_peak_not_preceding_window', window_risk(increasing), 0.)
    for bad in [path[:-1], np.r_[path[:-1], np.nan], np.r_[path[:-1], 0.]]:
        try: window_risk(bad)
        except ValueError: checks.append({'name': 'bad_target_rejected', 'passed': True})
        else: raise AssertionError('invalid path accepted')
    dates = pd.bdate_range('2007-01-01', periods=900)
    rng = np.random.default_rng(11)
    c = 100*np.exp(np.cumsum(rng.normal(.0003,.012,900)))
    p = prepare_prices(pd.DataFrame({'Date': dates, 'Close': c}))
    survey = pd.DataFrame({'date': [dates[400]-pd.Timedelta(days=7)], 'bullish': [.4], 'bearish': [.3]})
    r = observations(survey, p).iloc[0]
    test('strict_date_after_assumption', r.t_index, 401)
    test('121_closes120_segments', r.target_end_index-r.target_start_index, 120)
    test('end_t_plus121', r.target_end_index, 522)
    target = c[402:523]
    expected = max(100*(1-target[j]/target[i]) for i in range(121) for j in range(i,121))
    test('observation_independent_target', r.y, expected)
    altered = p.copy();altered.at[401,'Close'] = 1000000
    test('observation_excludes_pre_window_peak', observations(survey,altered).iloc[0].y, expected)
    pm = p.copy();pm.at[410,'Close'] = np.nan
    missing = observations(survey, pm).iloc[0]
    test('internal_nan_whole_window_excluded', missing.eligible, False)
    test('internal_nan_no_quote_compression', missing.target_end_index, 522)
    checks.append({'name':'internal_nan_reason','passed':'nonfinite_target_path' in missing.exclusion})
    short = observations(survey,p.iloc[:500]).iloc[0]
    test('incomplete_target_not_shortened', short.eligible, False)
    pc = prepare_prices(pd.DataFrame({'Date':pd.bdate_range('2024-01-01','2026-07-31'),'Close':100+np.arange(len(pd.bdate_range('2024-01-01','2026-07-31')))}))
    end_idx=int(pc.index[pc.Date.eq(CUTOFF)][0]);k=end_idx-121
    sc=pd.DataFrame({'date':[pc.at[k-1,'Date']-pd.Timedelta(days=7)],'bullish':[.4],'bearish':[.3]})
    exact=observations(sc,pc).iloc[0]
    test('cutoff_exact_endpoint_allowed',exact.eligible,True)
    checks.append({'name':'cutoff_exact_date','passed':exact.target_end==CUTOFF})
    sc.at[0,'date']=pc.at[k,'Date']-pd.Timedelta(days=7)
    test('cutoff_one_quote_later_rejected',observations(sc,pc).iloc[0].eligible,False)
    dup=pd.concat([survey,survey],ignore_index=True);dup.at[1,'bullish']=.7
    du=observations(dup,p)
    test('same_source_date_latest_physical_row',du.loc[du.eligible,'x'].to_numpy(),[40.])
    test('r20',p.at[401,'r20'],100*(c[401]/c[381]-1))
    test('r63',p.at[401,'r63'],100*(c[401]/c[338]-1))
    test('dma200_includes_t',p.at[401,'dma200'],100*(c[401]/(sum(c[202:402])/200)-1))
    test('dd252',p.at[401,'dd252'],100*(c[401]/max(c[150:402])-1))
    returns=[c[i]/c[i-1]-1 for i in range(382,402)]
    avg=sum(returns)/20;test('rv20_ddof1',p.at[401,'rv20'],100*math.sqrt(sum((x-avg)**2 for x in returns)/19)*math.sqrt(20))
    mature = pd.DataFrame({'eligible':[True]*4,'t':pd.to_datetime(['2009-12-01','2009-12-01','2010-01-01','1994-12-30']),
      'target_end':pd.to_datetime(['2009-12-31','2010-01-01','2009-12-31','1994-12-31'])})
    test('strict_training_maturity',train_mask(mature,2010),[True,False,False,False])
    z=rng.normal(size=(130,3));yy=rng.uniform(0,.5,130);theta=np.array([-.6,.2,-.3,.1])
    value,gradient=objective(theta,z,yy);eps=1e-6
    fd=np.array([(objective(theta+np.eye(4)[i]*eps,z,yy)[0]-objective(theta-np.eye(4)[i]*eps,z,yy)[0])/(2*eps) for i in range(4)])
    test('analytic_gradient_finite_difference',gradient,fd,tolerance=1e-7)
    independent=sum((1/(1+math.exp(-(theta[0]+sum(z[i,j]*theta[j+1] for j in range(3)))))-yy[i])**2 for i in range(130))/130+.001*sum(theta[1:]**2)
    test('objective_mean_unpenalized_intercept',value,independent)
    tr=pd.DataFrame({f'f{i}':z[:,i] for i in range(3)});tr['y']=100*yy;tr['t']=pd.Timestamp('2009-01-01');tr['target_end']=pd.Timestamp('2009-07-01')
    fit=fit_model(tr,['f0','f1','f2'])
    checks.append({'name':'single_start_final_objective_nonincrease','passed':fit['final_objective']<=fit['initial_objective']+1e-12})
    test('training_population_std',fit['scale'],np.sqrt(np.sum((z-z.mean(axis=0))**2,axis=0)/130))
    test('training_mean',fit['mean'],np.sum(z,axis=0)/130)
    evalf=tr.copy();evalf['f0']=10000.
    pred=predict(evalf,fit)
    checks.append({'name':'prediction_bounds_extreme_eval','passed':bool(np.isfinite(pred).all() and ((pred>=0)&(pred<=100)).all())})
    test('prediction_no_eval_scaling',pred,100*expit(fit['beta'][0]+((evalf[fit['features']].to_numpy()-fit['mean'])/fit['scale'])@fit['beta'][1:]))
    zero=tr.copy();zero['y']=0
    fzero=fit_model(zero,['f0']);test('zero_risk_no_floor',predict(zero,fzero),np.zeros(130))
    checks.append({'name':'zero_branch_no_optimizer_or_intercept','passed':fzero['intercept'] is None and not fzero['optimizer_started']})
    constant=tr.copy();constant['f0']=1
    try:fit_model(constant,['f0'])
    except RuntimeError:checks.append({'name':'zero_scale_stops','passed':True})
    else:raise AssertionError('zero scale allowed')
    fixture=pd.DataFrame({col:rng.normal(size=132) for col in BASE+['x']});fixture['y']=rng.uniform(0,40,132);fixture['eligible']=True;fixture['source_row']=np.arange(132)
    fixture['t']=list(pd.date_range('1995-01-01',periods=130,freq='30D'))+[pd.Timestamp('2009-12-01'),pd.Timestamp('2010-01-04')]
    fixture['target_end']=fixture['t']+pd.Timedelta(days=180)
    ledger={'started_fits':0,'completed_fits':0,'failed_fits':0,'attempts':[]}
    pp,ff=annual_predictions(fixture,ledger)
    test('four_models_one_eval_year',ledger['started_fits'],4);test('no_cross_year_training', [f['train_rows'] for f in ff],[130]*4)
    test('common_eval_one_row',len(pp),1)
    for f in ff:checks.append({'name':'fit_mature_'+f['model'],'passed':f['train_label_end_max']<pd.Timestamp('2010-01-01')})
    fake=pd.DataFrame({'y':np.zeros(208)})
    for i,m in enumerate(MODELS):fake['pred_'+m]=i+1.
    for size in [52,104]:
        draw,_=blocks(fake,size);test(f'blocks{size}_draws',len(draw),2000)
        test(f'blocks{size}_paired_loss',draw['improvement_BX_vs_B'],np.full(2000,100*(1-16/9)))
        starts=json.loads(draw.iloc[0].block_starts);idx=np.concatenate([np.arange(k,k+size) for k in starts])[:208]
        test(f'blocks{size}_exact_n',len(idx),208)
        checks.append({'name':f'blocks{size}_noncircular','passed':max(starts)+size<=208 and draw.iloc[0].seed==20260929+size})
    checks.append({'name':'empty_score_explicit','passed':scores(pp.iloc[:0])['metrics'] is None})
    if not all(c['passed'] for c in checks):raise AssertionError('boolean check failed')
    write_json(HERE/'synthetic-check.json',{'status':'passed','checks_count':len(checks),'checks':checks,
      'market_inputs_loaded':False,'real_label_batches':0,'real_model_fits':0,'synthetic_model_fit_attempts':7,
      'synthetic_execution_attempts':3,'prior_synthetic_failures':[{'error':'KeyError source_row','cause':'annual synthetic fixture omitted identity column','fix':'fixture source_row added; method unchanged','real_model_fits':0},{'error':'TypeError Series not JSON serializable','cause':'check report serialization lacked pandas Series handling','fix':'JSON normalizer handles Series; all numeric checks had passed','real_model_fits':0}],
      'code_sha256':sha(__file__),'libraries':{'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__}})
    print(json.dumps({'synthetic':'passed','checks':len(checks),'market_labels':0,'market_fits':0}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-reviewed',action='store_true',help='controller authorization required after code review')
    args=parser.parse_args()
    if args.run_reviewed:real_run()
    else:synthetic_checks()
