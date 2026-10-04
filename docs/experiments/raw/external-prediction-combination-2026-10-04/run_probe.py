"""One fixed read-only diagnostic of archived predictions; no training."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def align(rows):
    indices = [{r['id']: r for r in rs} for rs in rows]
    if any(len(i) != len(rs) for i, rs in zip(indices, rows)):
        raise ValueError('duplicate identity')
    ids = sorted(indices[0])
    if any(set(i) != set(ids) for i in indices):
        raise ValueError('different identities; no intersection allowed')
    for key in ids:
        for index in indices[1:]:
            if any(index[key][f] != indices[0][key][f]
                   for f in ['asset', 'date', 'fold', 'label_end', 'y', 'B0', 'B1']):
                raise ValueError('different target, date or baseline')
    return [[i[k] for k in ids] for i in indices]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve()
    if out.exists():
        raise ValueError('output already exists')
    out.mkdir(parents=True)
    start = time.monotonic()
    protocol_path = Path(__file__).with_name('protocol.json')
    protocol = json.loads(protocol_path.read_text())
    sys.path.insert(0, str(root / '.agents/skills/lei-quant-tools/scripts'))
    from workflow_bridge import read_archived_run, prepare_workflow_input

    hashes = {}
    runs = [root / p for p in protocol['read_only_runs']]
    for run in runs:
        for f in ['contract.json', 'result.json', 'receipt.json', 'preflight.json', 'report.md']:
            hashes[str((run / f).relative_to(root))] = digest(run / f)
    archives = [read_archived_run(p) for p in runs]
    checks = []
    for c, result, proof, integrity in archives:
        if any(c[k] != archives[0][0][k] for k in ['target', 'weights', 'split', 'calendar']):
            raise ValueError('incompatible contracts')
        for begin, end in protocol['windows']:
            readiness, _ = prepare_workflow_input(c, result, proof, start=begin, end=end)
            checks.append(readiness)
            if readiness['status'] != 'ready':
                (out / 'rejected.json').write_text(json.dumps(checks, indent=2))
                raise ValueError('archive window not ready')
    rows = align([r[1]['predictions'] for r in archives])
    if any(not any(a <= r['date'] <= b for a, b in protocol['windows']) for r in rows[0]):
        raise ValueError('declared windows omit saved predictions')
    y = np.asarray([r['y'] for r in rows[0]], float)
    pred = {name: np.asarray([r['B2'] for r in rs], float)
            for name, rs in zip(['joint', 'amplitude', 'serial'], rows)}
    pred.update({name: np.asarray([r[name] for r in rows[0]], float) for name in ['B0', 'B1']})
    matrix = np.column_stack([pred[n] for n in ['joint', 'amplitude', 'serial']])
    pred['equal3'] = np.average(matrix, axis=1)
    pred['half_simple'] = np.average(np.column_stack([pred['B0'], pred['equal3']]), axis=1)
    assert all(np.isfinite(v).all() for v in [y, *pred.values()])
    dates = np.asarray([r['date'] for r in rows[0]])
    assets = np.asarray([r['asset'] for r in rows[0]])
    folds = np.asarray([r['fold'] for r in rows[0]])
    masks = {'all': np.ones(len(y), bool)}
    masks.update({f'fold_{f}': folds == f for f in sorted(set(folds))})
    masks.update({f'asset_{a}': assets == a for a in sorted(set(assets))})
    masks.update({f'without_{a}': assets != a for a in sorted(set(assets))})
    scores = {}
    for name, mask in masks.items():
        mse = {k: float(np.mean((v[mask] - y[mask]) ** 2)) for k, v in pred.items()}
        scores[name] = {'rows': int(mask.sum()), 'dates': len(set(dates[mask])),
                        'rmse': {k: float(np.sqrt(v)) for k, v in mse.items()}, 'mse': mse,
                        'mse_improvement_vs_B0': {k: mse['B0'] - v for k, v in mse.items()}}
    err = matrix - y[:, None]
    second_moment = err.T @ err / len(y)
    w = np.ones(3) / 3
    identity = float(w @ second_moment @ w)
    assert abs(identity - scores['all']['mse']['equal3']) < 1e-10
    rejection = {}
    for kind in ['missing_id', 'wrong_target', 'wrong_baseline']:
        copy = json.loads(json.dumps(rows))
        if kind == 'missing_id':
            copy[1].pop()
        elif kind == 'wrong_target':
            copy[1][0]['y'] += 1
        else:
            copy[1][0]['B0'] += 1
        try:
            align(copy)
        except ValueError as exc:
            rejection[kind] = str(exc)
        else:
            raise AssertionError('bad inputs accepted')
    assert all(digest(root / p) == h for p, h in hashes.items())
    result = {'status': 'computed_archived_diagnostic', 'new_fits': 0,
              'scope': 'two price expressions, three old models; all historical data already seen',
              'scores': scores, 'residual_correlation': np.corrcoef(err.T).tolist(),
              'error_second_moment': second_moment.tolist(),
              'equal3_mse_from_error_cross_products': identity,
              'same_rows_all_methods': True, 'rejection_checks': rejection,
              'original_files_unchanged': hashes, 'qualifications': checks,
              'source_integrity': [x[3] for x in archives],
              'protocol_sha256': digest(protocol_path),
              'versions': {'numpy': np.__version__, 'python': sys.version},
              'wall_seconds': time.monotonic() - start}
    (out / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'all': scores['all'],
                      'residual_correlation': result['residual_correlation'], 'new_fits': 0}))


if __name__ == '__main__':
    main()
