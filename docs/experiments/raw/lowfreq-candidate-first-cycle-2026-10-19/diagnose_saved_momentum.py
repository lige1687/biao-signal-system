"""One supplementary diagnostic of unchanged saved results; never reruns B1."""
import ast
import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
from lei_signal.research.output_storage import _probe

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
OLD = ROOT / 'docs/experiments/raw/factor-etf-momentum-effect-b1-2026-09-23'
COLS = ['rank_ic', 'high_minus_low', 'high_minus_six']


def verified_existing_output():
    """Resume our own existing run, preserving exact binding and exclusive writes."""
    plan = json.loads((HERE / 'storage-plan.json').read_text())
    mount = Path(plan['external_mount'])
    check = _probe(ROOT, mount)
    info = check['info']
    assert check['mounted'] and info['VolumeUUID'] == plan['external_uuid']
    assert info['Internal'] is False and info['Writable'] is True
    assert info['FilesystemType'] == 'exfat'
    assert check['external_device'] == plan['external_device']
    assert check['external_free'] >= plan['external_reserve_bytes'] + plan['estimated_bytes']
    assert check['internal_free'] >= plan['internal_reserve_bytes'] + plan['internal_metadata_bytes']
    out = Path(plan['output'])
    assert out == Path(plan['run_directory']) / 'result'
    assert out.resolve() == out and out.is_dir() and out.stat().st_dev == plan['external_device']
    assert json.loads((out.parent / 'storage-plan.json').read_text()) == plan
    return out


def read_csv(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def mean(rows, key):
    values = [float(r[key]) for r in rows if r[key] != '']
    return math.fsum(values) / len(values)


def run():
    out = verified_existing_output()
    destination = out / 'momentum-diagnostic.json'
    assert not destination.exists(), 'Never overwrite an executed diagnostic'
    plan = json.loads((HERE / 'diagnostic-plan.json').read_text())
    for name, expected in plan['input_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
    rows = read_csv(OLD / 'formal/daily.csv')
    pairs = read_csv(OLD / 'formal/pairs.csv')
    valid = [r for r in rows if r['group_valid'] == 'True']
    assert len(rows) == 1085 and len(valid) == 1062
    assert [r['factor_date'] for r in rows] == sorted({r['factor_date'] for r in rows})
    last = max(i for i, r in enumerate(rows) if r['group_valid'] == 'True')
    timeline = rows[:last + 1]
    matrix = np.array([[float(r[k]) if r[k] else np.nan for k in COLS] for r in timeline])
    assert len(timeline) == 1064 and np.isfinite(matrix).sum(axis=0).tolist() == [1062]*3
    assert all(r['reason'] == 'target_horizon_outside_frozen_end' for r in rows[last+1:])
    summary = json.loads((OLD / 'formal/summary.json').read_text())
    for key in COLS:
        saved_key = key + '_mean'
        assert abs(mean(valid, key) - summary['overall'][saved_key]) < 1e-12
    outcomes = {(r['factor_date'], r['symbol']): float(r['target_return'])
                for r in pairs if r['valid'] == 'True'}
    symbols = sorted({r['symbol'] for r in pairs})
    contributions = {s: [] for s in symbols}
    high_counts = {s: 0 for s in symbols}
    for r in valid:
        high = set(ast.literal_eval(r['high_members']))
        assert len(high) == 2
        values = {s: outcomes[(r['factor_date'], s)] for s in symbols}
        assert abs(math.fsum(values.values()) / 6 - float(r['six_mean'])) < 1e-12
        assert abs(math.fsum(values[s] for s in high) / 2 - float(r['high_mean'])) < 1e-12
        terms = {s: ((.5 if s in high else 0) - 1/6) * values[s] for s in symbols}
        assert abs(math.fsum(terms.values()) - float(r['high_minus_six'])) < 1e-12
        for s in symbols:
            contributions[s].append(terms[s])
            high_counts[s] += int(s in high)
    # A hand-computable contrast: one selected asset gains 6%, all others zero.
    assert abs((.5-1/6)*.06 - (.06/2-.06/6)) < 1e-15
    intervals = {}
    n = len(timeline)
    for length in plan['block_lengths']:
        rng = np.random.default_rng(plan['seed'])
        samples = np.empty((plan['resamples'], 3))
        counts = np.empty((plan['resamples'], 3), dtype=int)
        offsets = np.arange(length)
        for b in range(plan['resamples']):
            starts = rng.integers(0, n, size=math.ceil(n/length))
            ix = ((starts[:, None] + offsets) % n).ravel()[:n]
            selected = matrix[ix]
            counts[b] = np.isfinite(selected).sum(axis=0)
            samples[b] = np.nanmean(selected, axis=0)
        assert counts.min() > 0
        intervals[str(length)] = {
            k: {'point_mean': mean(valid, k),
                'percentile_95': np.quantile(samples[:, j], [.025, .975]).tolist(),
                'finite_dates_range': [int(counts[:, j].min()), int(counts[:, j].max())]}
            for j, k in enumerate(COLS)
        }
    periods = plan['original_periods']
    year = lambda r: '2026H1' if r['factor_date'].startswith('2026') else r['factor_date'][:4]
    period_rows, omitted_rows = {}, {}
    for period in periods:
        selected = [r for r in valid if year(r) == period]
        omitted = [r for r in valid if year(r) != period]
        period_rows[period] = {'dates': len(selected), **{k: mean(selected, k) for k in COLS}}
        omitted_rows[period] = {'dates': len(omitted), **{k: mean(omitted, k) for k in COLS}}
    data = {'status': 'completed', 'evidence': 'not_supported_within_fixed_historical_scope',
            'completed_at': datetime.now().astimezone().isoformat(),
            'scope': 'retrospective saved-output diagnostic, no signal generation or account backtest',
            'attempt_dates': len(rows), 'eligible_dates': len(valid), 'calendar_rows': len(timeline),
            'first_factor_date': valid[0]['factor_date'], 'last_factor_date': valid[-1]['factor_date'],
            'last_target_date': valid[-1]['target_end'], 'maturity_exclusions': len(rows)-len(timeline),
            'missing_in_range': [{k:r[k] for k in ['factor_date','target_end','reason']}
                                 for r in timeline if r['group_valid'] != 'True'],
            'means': {k: mean(valid,k) for k in COLS+['high_mean','low_mean','six_mean']},
            'uncertainty': intervals, 'periods': period_rows, 'leave_one_period_out': omitted_rows,
            'per_asset': {s:{'high_dates':high_counts[s],
                            'mean_contribution_high_minus_six': math.fsum(contributions[s])/len(valid)}
                          for s in symbols},
            'limitations': plan['limitations'], 'input_sha256':plan['input_sha256']}
    assert abs(sum(x['mean_contribution_high_minus_six'] for x in data['per_asset'].values())
               - data['means']['high_minus_six']) < 1e-12
    verified_existing_output()
    with destination.open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps({'path':str(destination), 'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
                      'means':data['means'], 'uncertainty': intervals}, ensure_ascii=False))


if __name__ == '__main__':
    run()
