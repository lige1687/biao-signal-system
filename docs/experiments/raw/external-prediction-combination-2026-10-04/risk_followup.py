"""Fixed mean of two different owners' archived downside predictions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    assert not a.output.exists(), 'do not overwrite'
    protocol_path = Path(__file__).with_name('risk-followup-protocol.json')
    protocol = json.loads(protocol_path.read_text())
    sys.path.insert(0, str(a.root / '.agents/skills/lei-quant-tools/scripts'))
    from workflow_bridge import read_archived_run
    loaded = [read_archived_run(a.root / r) for r in protocol['sources']]
    for key in ['target', 'split', 'weights']:
        assert loaded[0][0][key] == loaded[1][0][key], key
    assert loaded[0][0]['weights']['policy'] == 'equal_asset'
    rows = [x[1]['predictions'] for x in loaded]
    indices = [{r['id']: r for r in rs} for rs in rows]
    assert len(indices[0]) == len(rows[0]) == len(indices[1]) == len(rows[1])
    assert set(indices[0]) == set(indices[1])
    keys = sorted(indices[0])
    observation_maps = [{r['id']: r for r in x[2]['observations']} for x in loaded]
    for j, index in enumerate(indices):
        for k in keys:
            r = index[k]
            assert all(r[f] == indices[0][k][f] for f in ['asset', 'date', 'fold', 'label_end', 'y'])
            assert observation_maps[j][k]['eligible']
            assert all(r[f] == observation_maps[j][k][f] for f in ['asset', 'date', 'label_end', 'y'])
    ordered = [[i[k] for k in keys] for i in indices]
    dates = sorted({r['date'] for r in ordered[0]})
    assets = sorted({r['asset'] for r in ordered[0]})
    assert len(assets) == 3 and len(keys) == 951 and len(dates) == 317
    assert all({r['asset'] for r in ordered[0] if r['date'] == d} == set(assets) for d in dates)
    y = np.asarray([r['y'] for r in ordered[0]])
    pred = {f'{n}.{b}': np.asarray([r[b] for r in rs])
            for n, rs in zip(['volume', 'session'], ordered) for b in ['B0', 'B1', 'B2']}
    pred['equal2'] = np.average(np.column_stack([pred['volume.B2'], pred['session.B2']]), axis=1)
    assert all(np.isfinite(x).all() for x in [y, *pred.values()])
    masks = {'all': np.ones(len(y), bool)}
    masks.update({f'fold_{f}': np.array([r['fold'] == f for r in ordered[0]])
                  for f in sorted({r['fold'] for r in ordered[0]})})
    masks.update({f'asset_{x}': np.array([r['asset'] == x for r in ordered[0]]) for x in assets})
    masks.update({f'without_{x}': np.array([r['asset'] != x for r in ordered[0]]) for x in assets})
    scores = {}
    max_delta = 0.0
    count = 0
    for group, mask in masks.items():
        mse = {n: float(np.mean((v[mask] - y[mask]) ** 2)) for n, v in pred.items()}
        selected = [k for k, flag in zip(keys, mask) if flag]
        scalar = {n: [] for n in pred}
        for k in selected:
            left, right = indices[0][k], indices[1][k]
            values = {f'{n}.{b}': r[b] for n, r in [('volume', left), ('session', right)]
                      for b in ['B0', 'B1', 'B2']}
            values['equal2'] = math.fsum([left['B2'], right['B2']]) / 2
            for n, v in values.items():
                scalar[n].append((v - left['y']) ** 2)
        for n, losses in scalar.items():
            delta = abs(math.fsum(losses) / len(losses) - mse[n])
            assert delta < 1e-10
            max_delta = max(max_delta, delta)
            count += 1
        scores[group] = {'rows': len(selected), 'mse': mse,
                         'rmse': {n: math.sqrt(v) for n, v in mse.items()},
                         'improvement_equal2_vs_each': {n: v - mse['equal2'] for n, v in mse.items()}}
    err = np.column_stack([pred['volume.B2'] - y, pred['session.B2'] - y])
    second = err.T @ err / len(y)
    assert abs(second.sum() / 4 - scores['all']['mse']['equal2']) < 1e-10
    assert all(hashlib.sha256((a.root / integrity['run_dir'] / n).read_bytes()).hexdigest() == h
               for *_, integrity in loaded for n, h in integrity['files'].items())
    result = {'status': 'computed_archived_diagnostic', 'new_fits': 0, 'rows': len(y), 'dates': len(dates),
              'assets': assets, 'target': loaded[0][0]['target'], 'scores': scores,
              'different_baselines_retained': True, 'same_id_target_rows': True,
              'source_integrity': [x[3] for x in loaded],
              'residual_correlation': float(np.corrcoef(err.T)[0, 1]),
              'error_second_moment': second.tolist(),
              'independent_scalar_checks': count, 'max_abs_difference': max_delta,
              'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              'scope': 'all already-seen original rows; equal original asset weights; no new unseen evidence'}
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'all': scores['all'], 'folds': {k: v for k, v in scores.items() if k.startswith('fold_')},
                      'correlation': result['residual_correlation'], 'checks': count}))


if __name__ == '__main__':
    main()
