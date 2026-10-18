"""One predeclared use diagnostic of frozen forecasts. No fit or label generation."""
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

import numpy as np

from diagnose_saved_momentum import verified_existing_output

HERE = Path(__file__).resolve().parent
OLD = Path('/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/classic-risk-target-fit-2026-10-02')
METHODS = ['asset_mean', 'B1', 'B2']


def pick(rows, method):
    ordered = sorted(rows, key=lambda r: (r[method], r['asset']))
    if ordered[1][method] == ordered[2][method]:
        return None
    return [r['asset'] for r in ordered[:2]]


def run():
    output = verified_existing_output() / 'defensive-selection-diagnostic.json'
    assert not output.exists()
    plan = json.loads((HERE / 'defensive-selection-plan.json').read_text())
    for path, expected in plan['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    result = json.loads((OLD / 'run-01/result.json').read_text())
    contract = json.loads((OLD / 'run-01/contract.json').read_text())
    checks = json.loads((OLD / 'saved-result-checks.json').read_text())
    for relative, expected in checks['fingerprints'].items():
        path = Path('/Users/yongbiaoli/Desktop/lei-signal-lab') / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, path
    fold_means = {f['fold']: f['asset_training_means'] for f in checks['folds']}
    rows = result['predictions']
    assert len(rows) == 1268 and len({r['id'] for r in rows}) == 1268
    daily = defaultdict(list)
    for row in rows:
        row['asset_mean'] = fold_means[row['fold']][row['asset']]
        assert all(math.isfinite(row[m]) for m in METHODS + ['y'])
        fold = contract['split']['folds'][int(row['fold'])]
        assert row['date'] >= fold['eval_start'] and row['label_end'] <= fold['eval_end']
        daily[row['date']].append(row)
    assert len(daily) == 317
    # Synthetic selection obeys forecast only, including the boundary-tie rule.
    fake = [{'asset': str(i), 'B2': v, 'y': 100-i} for i, v in enumerate([4, 1, 3, 2])]
    assert pick(fake, 'B2') == ['1', '3']
    assert pick([{'asset': str(i), 'B2': v} for i, v in enumerate([1, 2, 2, 4])], 'B2') is None
    counts = {m: Counter() for m in METHODS}
    evaluated, excluded = [], []
    for date, items in sorted(daily.items()):
        assert len(items) == 4 and sorted(r['asset'] for r in items) == sorted(plan['universe'])
        assert len({r['fold'] for r in items}) == 1
        choices = {m: pick(items, m) for m in METHODS}
        if any(v is None for v in choices.values()):
            excluded.append({'date': date, 'reason': 'boundary_tie_in_at_least_one_method'})
            continue
        values = {r['asset']: r['y'] for r in items}
        observed = {m: mean(values[a] for a in choices[m]) for m in METHODS}
        for m in METHODS:
            counts[m].update(choices[m])
        evaluated.append({'date': date, 'fold': items[0]['fold'], 'choices': choices,
                          'actual_individual_volatility_mean': observed,
                          'all_four': mean(values.values()),
                          'B2_minus_asset_mean': observed['B2']-observed['asset_mean'],
                          'B2_minus_B1': observed['B2']-observed['B1']})
    def summarize(part):
        return {'dates': len(part), 'mean_individual_future_volatility': {
            **{m: mean(r['actual_individual_volatility_mean'][m] for r in part) for m in METHODS},
            'all_four': mean(r['all_four'] for r in part)},
            'B2_minus_asset_mean': mean(r['B2_minus_asset_mean'] for r in part),
            'B2_minus_B1': mean(r['B2_minus_B1'] for r in part),
            'B2_changed_vs_asset_mean_dates': sum(set(r['choices']['B2']) != set(r['choices']['asset_mean']) for r in part),
            'B2_changed_vs_B1_dates': sum(set(r['choices']['B2']) != set(r['choices']['B1']) for r in part)}
    axis = [d for d in contract['calendar'] if any(f['eval_start'] <= d <= f['eval_end'] for f in contract['split']['folds'])]
    assert len(axis) == 359 and len(axis)-len(daily) == 42
    keyed = {r['date']: r for r in evaluated}
    cols = ['B2_minus_asset_mean', 'B2_minus_B1']
    matrix = np.array([[keyed[d][c] if d in keyed else np.nan for c in cols] for d in axis])
    ranges = {}
    for length in plan['uncertainty']['paired_blocks']:
        rng = np.random.default_rng(plan['uncertainty']['seed'])
        samples, finite = [], []
        for _ in range(plan['uncertainty']['draws']):
            starts = rng.integers(0, len(axis), size=math.ceil(len(axis)/length))
            ix = ((starts[:, None] + np.arange(length)) % len(axis)).ravel()[:len(axis)]
            values = matrix[ix]
            finite.append(np.isfinite(values[:, 0]).sum())
            assert finite[-1] > 0
            samples.append(np.nanmean(values, axis=0))
        samples = np.asarray(samples)
        ranges[str(length)] = {c: np.quantile(samples[:, i], [.025, .975]).tolist() for i, c in enumerate(cols)}
        ranges[str(length)]['finite_dates_range'] = [int(min(finite)), int(max(finite))]
    data = {'status': 'completed', 'scope': plan['scope'], 'completed_at': datetime.now().astimezone().isoformat(),
            'universe': plan['universe'], 'unit': 'percentage_points_of_individual_daily_return_volatility_not_annualized',
            'first_date': min(daily), 'last_date': max(daily), 'source_dates': len(daily), 'evaluation_axis_dates': len(axis),
            'maturity_boundary_excluded_dates': 42, 'selection_exclusions': excluded,
            'overall': summarize(evaluated), 'periods': {y: summarize([r for r in evaluated if r['date'].startswith(y)]) for y in ['2025', '2026']},
            'counts': {m: dict(counts[m]) for m in METHODS}, 'intervals': ranges,
            'input_sha256': plan['inputs'], 'limitations': plan['limitations'], 'daily': evaluated}
    verified_existing_output()
    with output.open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'overall': data['overall'], 'periods': data['periods'], 'counts': data['counts'], 'intervals': ranges}, ensure_ascii=False))


if __name__ == '__main__':
    run()
