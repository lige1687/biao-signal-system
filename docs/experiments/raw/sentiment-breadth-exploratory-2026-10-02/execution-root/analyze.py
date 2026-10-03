"""Frozen, retrospective provider-series experiment. No production imports."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = {'I': [], 'B': ['r20'], 'X': ['b20'], 'BX': ['r20', 'b20'],
          'BXD': ['r20', 'b20', 'delta20']}
PAIRS = {'B_to_BX': ('B', 'BX'), 'BX_to_BXD': ('BX', 'BXD'),
         'I_to_B': ('I', 'B'), 'I_to_BX': ('I', 'BX'), 'I_to_BXD': ('I', 'BXD')}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csvout(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def valid(values):
    return all(math.isfinite(float(x)) and float(x) > 0 for x in values)


def target(closes, i):
    window = closes[i + 1:i + 22]
    if len(window) != 21 or not valid(window):
        return None
    peaks = np.maximum.accumulate(window)
    return float(100 * (window[-1] / window[0] - 1)), float(100 * np.max(1 - window / peaks))


def prefix(dates, bmap, i):
    return i >= 20 and all(d in bmap and math.isfinite(float(bmap[d]['ma_20']['percentage_above']))
                           for d in dates[i - 20:i + 1])


def fit(rows, features, scaler, penalty=.001):
    y = np.array([r['y'] for r in rows])
    z = np.column_stack([np.ones(len(rows))] +
                        [(np.array([r[k] for r in rows]) - scaler[k][0]) / scaler[k][1]
                         for k in features])
    reg = np.diag([0] + [len(rows) * penalty] * len(features))
    beta = np.linalg.solve(z.T @ z + reg, z.T @ y)
    return {'features': features, 'beta': beta.tolist(), 'n': len(rows),
            'scaler': {k: scaler[k] for k in features},
            'max_training_target_end': max(r['target_end'] for r in rows)}


def predict(model, rows):
    features = model['features']
    z = np.column_stack([np.ones(len(rows))] +
                        [(np.array([r[k] for r in rows]) - model['scaler'][k][0]) / model['scaler'][k][1]
                         for k in features])
    return z @ np.array(model['beta'])


def metrics(y, predictions):
    return {k: {'n': len(y), 'mse_pp2': float(np.mean((y - a)**2)),
                'rmse_pp': float(np.sqrt(np.mean((y - a)**2))),
                'mae_pp': float(np.mean(np.abs(y - a)))} for k, a in predictions.items()}


def increments(perf):
    return {name: {'before_mse_pp2': perf[a]['mse_pp2'], 'after_mse_pp2': perf[b]['mse_pp2'],
                   'absolute_gain_pp2': perf[a]['mse_pp2'] - perf[b]['mse_pp2'],
                   'relative_gain_percent': 100 * (1 - perf[b]['mse_pp2'] / perf[a]['mse_pp2'])}
            for name, (a, b) in PAIRS.items()}


def summary(rows):
    if not rows:
        return {'n': 0, 'mean_return_pp': None, 'median_return_pp': None,
                'positive_percent': None, 'mean_future_decline_pp': None,
                'median_future_decline_pp': None}
    return {'n': len(rows), 'mean_return_pp': float(np.mean([r['y'] for r in rows])),
            'median_return_pp': float(np.median([r['y'] for r in rows])),
            'positive_percent': 100 * sum(r['y'] > 0 for r in rows) / len(rows),
            'mean_future_decline_pp': float(np.mean([r['risk'] for r in rows])),
            'median_future_decline_pp': float(np.median([r['risk'] for r in rows]))}


def synthetic():
    a = np.arange(1., 51.)
    y, risk = target(a, 20)
    assert math.isclose(y, 100 * (42 / 22 - 1)) and risk == 0
    b = a.copy(); b[30] = np.nan
    assert target(b, 20) is None
    assert target(a[:41], 20) is None
    w = np.ones(42) * 100; w[21:42] = [100, 120, 90] + [100] * 18
    assert math.isclose(target(w, 20)[1], 25.)
    dates = [str(i) for i in range(21)]
    bm = {d: {'ma_20': {'percentage_above': 50}} for d in dates}
    assert prefix(dates, bm, 20)
    del bm['10']; assert not prefix(dates, bm, 20)
    rows = [{'y': 2., 'r20': 5., 'target_end': '2025-01-01'}] * 5
    m = fit(rows, ['r20'], {'r20': [5., 1.]})
    assert np.allclose(predict(m, rows), 2.)
    perf = metrics(np.array([1., 3.]), {k: np.array([2., 2.]) for k in MODELS})
    assert perf['I']['mse_pp2'] == 1 and perf['I']['rmse_pp'] == 1
    assert increments(perf)['B_to_BX']['relative_gain_percent'] == 0
    return {'passed': True, 'checks': ['target_next_close_plus20intervals', 'invalid_price_no_compression',
            'unmatured_target', 'future_peak_to_trough', 'complete_quote_calendar_breadth_prefix',
            'constant_feature_ridge', 'manual_loss_arithmetic'], 'real_fits': 0}


def run(freeze_path, out):
    freeze = json.loads(freeze_path.read_text())
    for p, expected in freeze['files'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == expected, 'hash drift: ' + p
    assert not out.exists(), 'Output already exists; preserve prior run'
    out.mkdir()
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    assert protocol['models'] == MODELS
    spy = next(p for p in protocol['inputs'] if p.endswith('px_SPY.csv'))
    breadth = next(p for p in protocol['inputs'] if p.endswith('ma_percentage_historical.json'))
    quotes = list(csv.DictReader(Path(spy).open()))
    dates = [r['Date'] for r in quotes]
    assert len(set(dates)) == len(dates) and dates == sorted(dates)
    closes = np.array([float(r['Close']) for r in quotes])
    source = json.loads(Path(breadth).read_text())['data']
    assert len({r['date'] for r in source}) == len(source)
    bm = {r['date']: r for r in source}; idx = {d: i for i, d in enumerate(dates)}
    rows, excluded = [], {}
    for r in source:
        d = r['date']; i = idx.get(d)
        reason = None
        if i is None: reason = 'unmatched_quote'
        elif not prefix(dates, bm, i): reason = 'insufficient_source_prefix'
        elif not valid(closes[i-20:i+1]): reason = 'invalid_price'
        elif i + 21 >= len(dates): reason = 'unmatured'
        elif target(closes, i) is None: reason = 'invalid_price'
        if reason:
            excluded.setdefault(reason, []).append(d); continue
        y, risk = target(closes, i)
        end = dates[i+21]
        part = 'train' if end < '2026-01-01' else ('eval' if d >= '2026-01-01' else 'boundary_purge')
        b20 = float(r['ma_20']['percentage_above'])
        rows.append({'date': d, 'target_start': dates[i+1], 'target_end': end,
                     'r20': float(100*(closes[i]/closes[i-20]-1)), 'b20': b20,
                     'b50': float(r['ma_50']['percentage_above']), 'b200': float(r['ma_200']['percentage_above']),
                     'delta20': b20 - float(bm[dates[i-20]]['ma_20']['percentage_above']),
                     'y': y, 'risk': risk, 'partition': part})
    train = [r for r in rows if r['partition'] == 'train']
    evaluation = [r for r in rows if r['partition'] == 'eval']
    kept = [r for r in train if not (r['target_start'] <= '2025-04-30' and r['target_end'] >= '2025-04-01')]
    assert (len(rows), len(train), len(evaluation), len(kept)) == (343, 175, 147, 149)
    assert evaluation[0]['date'] == '2026-01-02' and evaluation[-1]['date'] == '2026-08-04'
    assert all(r['date'] < '2026-01-01' and r['target_end'] < '2026-01-01' for r in train)
    scaler = {k: [float(np.mean([r[k] for r in train])), float(np.std([r[k] for r in train])) or 1.]
              for k in ['r20', 'b20', 'delta20']}
    fits, preds, trial = {}, {}, []
    for variant, training in [('core', train), ('without_April', kept)]:
        fits[variant], preds[variant] = {}, {}
        for name, features in MODELS.items():
            trial.append({'attempt': len(trial)+1, 'variant': variant, 'model': name,
                          'status': 'started', 'training_n': len(training)})
            dump(out / 'trial-ledger.json', trial)
            model = fit(training, features, scaler)
            fits[variant][name] = model
            preds[variant][name] = predict(model, evaluation)
            assert np.all(np.isfinite(preds[variant][name]))
            trial[-1]['status'] = 'completed'; dump(out / 'trial-ledger.json', trial)
    y = np.array([r['y'] for r in evaluation])
    perf = {v: metrics(y, p) for v, p in preds.items()}
    inc = {v: increments(p) for v, p in perf.items()}
    predrows = [{**r, **{v+'_'+k: float(a[i]) for v, pp in preds.items() for k, a in pp.items()}}
                for i, r in enumerate(evaluation)]
    csvout(out / 'all-observations.csv', rows); csvout(out / 'predictions.csv', predrows)
    dump(out / 'fits.json', fits); dump(out / 'exclusions.json', excluded)
    states = {k: [] for k in ['low', 'high', 'neither']}
    for r in rows:
        key = 'low' if r['b20'] <= 15 and r['b50'] <= 15 else ('high' if r['b20'] >= 85 and r['b50'] >= 85 else 'neither')
        states[key].append(r)
    csvout(out / 'original-low-cases.csv', states['low'])
    bins = [{**{'lower': n, 'upper': n+10}, **summary([r for r in rows if n <= r['b20'] < n+10 or n == 90 and r['b20'] == 100])}
            for n in range(0, 100, 10)]
    csvout(out / 'b20-bins.csv', bins)
    strata = {}
    for name, mask in [('2026Q1', np.array([r['date'][5:7] <= '03' for r in evaluation])),
                       ('2026Q2', np.array(['04' <= r['date'][5:7] <= '06' for r in evaluation])),
                       ('2026Q3_partial', np.array([r['date'][5:7] >= '07' for r in evaluation])),
                       ('r20_negative', np.array([r['r20'] < 0 for r in evaluation])),
                       ('r20_nonnegative', np.array([r['r20'] >= 0 for r in evaluation]))]:
        pp = metrics(y[mask], {k: a[mask] for k, a in preds['core'].items()})
        strata[name] = {'performance': pp, 'increment': increments(pp)}
        if name.startswith('2026'):
            remaining = metrics(y[~mask], {k: a[~mask] for k, a in preds['core'].items()})
            strata[name]['delete_quarter_increment'] = increments(remaining)
    gains = (y - preds['core']['B'])**2 - (y - preds['core']['BX'])**2
    order = np.argsort(-gains)[:5]
    mask = np.ones(len(y), dtype=bool); mask[order] = False
    largest = [{**{'date': evaluation[i]['date'], 'gain_pp2': float(gains[i])},
                **{k: float((y[i]-preds['core'][k][i])**2) for k in ['B', 'BX']}} for i in order]
    csvout(out / 'largest-five-contributions.csv', largest)
    trimmed = increments(metrics(y[mask], {k: a[mask] for k, a in preds['core'].items()}))
    uncertainties = {}
    for length in [40, 80]:
        rng = np.random.default_rng(20261002 + length); samples = {k: [] for k in PAIRS}
        for _ in range(2000):
            starts = rng.integers(0, len(y)-length+1, size=math.ceil(len(y)/length))
            take = np.concatenate([np.arange(s, s+length) for s in starts])[:len(y)]
            p = metrics(y[take], {k: a[take] for k, a in preds['core'].items()})
            for name, val in increments(p).items(): samples[name].append(val)
        uncertainties[str(length)] = {name: {key: np.quantile([a[key] for a in vals], [.025, .975]).tolist()
                                            for key in ['absolute_gain_pp2', 'relative_gain_percent']}
                                     for name, vals in samples.items()}
        csvout(out / ('uncertainty-'+str(length)+'.csv'),
               [{name: a[i]['relative_gain_percent'] for name, a in samples.items()} for i in range(2000)])
    overlap = [len(set(dates[idx[a['date']]+2:idx[a['date']]+22]) &
                   set(dates[idx[b['date']]+2:idx[b['date']]+22])) for a, b in zip(evaluation, evaluation[1:])]
    result = {'scope': protocol['id'], 'performance': perf, 'increment': inc, 'uncertainty': uncertainties,
              'strata': strata, 'original_states': {k: summary(a) for k, a in states.items()},
              'counts': {'source': len(source), 'common_mature': len(rows), 'train': len(train),
                         'eval': len(evaluation), 'purged': 21, 'April_removed': len(train)-len(kept),
                         'April_retained': len(kept)},
              'largest_five': {'rows': largest, 'gain_total_pp2': float(gains.sum()),
                               'share_percent': float(100*gains[order].sum()/gains.sum()),
                               'after_delete_increment': trimmed},
              'dependence': {'adjacent_pairs': len(overlap), 'overlapping_pairs': sum(x>0 for x in overlap),
                             'shared_intervals_min': min(overlap), 'shared_intervals_max': max(overlap)},
              'feature_ranges': {part: {k: [min(r[k] for r in a), max(r[k] for r in a)] for k in scaler}
                                 for part, a in [('train', train), ('eval', evaluation)]},
              'actual_core_fits': 5, 'actual_sensitivity_fits': 5,
              'original_E': 'not_evaluated; unqualified historical membership/method/availability',
              'historically_available_prediction': 'not_evaluated; current revised provider vintage'}
    dump(out / 'results.json', result)
    print(json.dumps({'status': 'completed', 'fits': len(trial), 'out': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.synthetic:
        check = synthetic(); dump(ROOT / 'execution-root' / 'synthetic-check.json', check); print(check)
    elif args.run and args.freeze and args.out:
        run(args.freeze, args.out)
    else:
        parser.error('choose synthetic or run with freeze and out')
