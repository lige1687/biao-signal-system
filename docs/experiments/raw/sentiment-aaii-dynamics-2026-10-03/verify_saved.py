"""Verify this archived small evidence package without running market fits."""
from pathlib import Path
import argparse
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(name):
    return json.loads((HERE / name).read_text())


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9), (a, b)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-inputs', action='store_true')
    args = parser.parse_args()
    protocol, frozen = read('protocol.json'), read('execution-freeze.json')
    bindings = {'protocol.json':'protocol_sha256', 'analysis.py':'analysis_sha256',
                'definitions.json':'definitions_sha256',
                'snapshots/workflow_evaluation.py':'reused_kernel_sha256',
                'verify_independently.py':'independent_verifier_sha256'}
    for name, key in bindings.items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == frozen[key], name
    r = read('run-01/results.json')
    n = sum(v['n'] for v in r['annual'].values())
    assert n == r['overall']['n'] == 816
    for name in protocol['models']:
        mse = sum(v['n']*v['mse'][name] for v in r['annual'].values())/n
        close(mse, r['overall']['mse'][name])
        close(math.sqrt(mse), r['overall']['rmse'][name])
        close(sum(v['n']*v['mean_absolute_error'][name] for v in r['annual'].values())/n,
              r['overall']['mean_absolute_error'][name])
        close(sum(v['n']*v['mse'][name] for v in r['periods'].values())/n, mse)
    for a, b in protocol['primary_comparisons']+protocol['secondary_comparisons']:
        close(100*(1-r['overall']['mse'][a]/r['overall']['mse'][b]),
              r['overall']['improvement_pct'][a+'_vs_'+b])
    ledger, review = read('trial-ledger.json'), read('independent-review/trials.json')
    assert ledger['fits_attempted'] == ledger['fits_completed'] == len(ledger['records']) == 153
    assert review['fits'] == len(review['records']) == 27
    assert all(x['status'] == 'completed' for x in ledger['records']+review['records'])
    missing = []
    for source in protocol['sources']:
        path = ROOT/source['path']
        if not path.is_file():
            missing.append(source['path'])
        else:
            assert path.stat().st_size == source['bytes']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
    print(json.dumps({'archive_summary_and_freeze':'passed', 'new_market_fits':0,
                      'source_inputs_missing':missing,
                      'market_reproduction':'not_run; missing inputs block full reproduction' if missing else 'inputs_match; no market rerun performed'}, ensure_ascii=False))
    if args.require_inputs and missing:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
