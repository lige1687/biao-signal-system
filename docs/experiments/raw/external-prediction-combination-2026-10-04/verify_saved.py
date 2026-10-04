"""Stdlib arithmetic verification; --root additionally checks original forecasts."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--summary', required=True, type=Path)
    p.add_argument('--root', type=Path)
    args = p.parse_args()
    s = json.loads(args.summary.read_text())
    checks = 0
    largest = 0.0

    def close(a, b):
        nonlocal checks, largest
        delta = abs(a - b)
        assert delta < 1e-10, (a, b, delta)
        checks += 1
        largest = max(largest, delta)

    for record in s['scores'].values():
        for model, mse in record['mse'].items():
            close(math.sqrt(mse), record['rmse'][model])
            close(record['mse']['B0'] - mse, record['mse_improvement_vs_B0'][model])
    all_scores = s['scores']['all']
    folds = [v for k, v in s['scores'].items() if k.startswith('fold_')]
    assert sum(v['rows'] for v in folds) == all_scores['rows'] == 1268
    assert sum(v['dates'] for v in folds) == all_scores['dates'] == 317
    for model, mse in all_scores['mse'].items():
        close(sum(v['rows'] * v['mse'][model] for v in folds) / 1268, mse)
    close(sum(sum(row) for row in s['error_second_moment']) / 9,
          all_scores['mse']['equal3'])
    verified_inputs = False
    if args.root:
        root = args.root.resolve()
        for name, sha in s['original_files_unchanged'].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, name
        base = root / 'docs/experiments/raw/tsfresh-factor-validation-2026-10-02'
        runs = [json.loads((base / ('run-' + name) / 'result.json').read_text())['predictions']
                for name in ['joint', 'amplitude', 'serial']]
        indices = [{r['id']: r for r in rs} for rs in runs]
        for group, score in s['scores'].items():
            selected = []
            for row in runs[0]:
                if group.startswith('fold_') and str(row['fold']) != group[5:]:
                    continue
                if group.startswith('asset_') and row['asset'] != group[6:]:
                    continue
                if group.startswith('without_') and row['asset'] == group[8:]:
                    continue
                selected.append(row)
            assert len(selected) == score['rows']
            losses = {k: [] for k in score['mse']}
            for row in selected:
                values = [i[row['id']]['B2'] for i in indices]
                preds = dict(zip(['joint', 'amplitude', 'serial'], values))
                preds.update(B0=row['B0'], B1=row['B1'])
                preds['equal3'] = math.fsum(values) / 3
                preds['half_simple'] = (row['B0'] + math.fsum(values) / 3) / 2
                for name, value in preds.items():
                    losses[name].append((value - row['y']) ** 2)
            for name, values in losses.items():
                close(math.fsum(values) / len(values), score['mse'][name])
        verified_inputs = True
    print(json.dumps({'status': 'passed', 'numeric_checks': checks,
                      'max_abs_difference': largest, 'original_predictions_checked': verified_inputs,
                      'scope': 'arithmetic and saved identities, not market source requalification'}))


if __name__ == '__main__':
    main()
