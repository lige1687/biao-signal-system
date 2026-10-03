"""One pre-recorded engineering batch on archived predictions, no new fits."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np

from independent_core_check import reference

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ENTRY = ROOT / '.agents/skills/lei-quant-tools/scripts/multiple_comparison.py'
RUNS = [ROOT / 'docs/experiments/raw/tsfresh-factor-validation-2026-10-02' / ('run-' + name)
        for name in ('joint', 'amplitude', 'serial')]


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for run in RUNS for p in [run / name for name in
            ('contract.json', 'preflight.json', 'result.json', 'receipt.json', 'report.md')]}


def invoke(start, end, baseline, filename, expected_code):
    cmd = [sys.executable, str(ENTRY), 'compare-workflows', *map(str, RUNS),
           '--start', start, '--end', end, '--baseline', baseline,
           '--block-size', '20', '--reps', '1000', '--seed', '20261002']
    process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    record = {'command': cmd, 'returncode': process.returncode,
              'stderr': process.stderr, 'stdout': process.stdout}
    (OUT / (filename + '-process.json')).write_text(json.dumps(record, indent=2) + '\n')
    assert process.returncode == expected_code, record
    data = json.loads(process.stdout)
    (OUT / (filename + '.json')).write_text(json.dumps(data, indent=2) + '\n')
    return data


def main():
    before = hashes()
    rejected = invoke('2025-01-02', '2026-06-30', 'B1', 'archive-full-period', 2)
    assert rejected['status'] == 'not_applicable'
    summaries = []
    for baseline in ('B0', 'B1'):
        data = invoke('2025-01-02', '2025-12-02', baseline, 'archive-' + baseline, 0)
        assert data['daily_rows'] == 222 and data['asset_count'] == 4 and data['fits'] == 0
        rows = [json.loads((run / 'result.json').read_text())['predictions'] for run in RUNS]
        lookup = [{r['id']: r for r in records if '2025-01-02' <= r['date'] <= '2025-12-02'}
                  for records in rows]
        assert all(set(index) == set(lookup[0]) for index in lookup)
        daily_base, daily_candidates = [], []
        for day in data['calendar']:
            ids = sorted(key for key, row in lookup[0].items() if row['date'] == day)
            assert len(ids) == 4
            daily_base.append(np.mean([(lookup[0][key][baseline] - lookup[0][key]['y']) ** 2
                                       for key in ids]))
            daily_candidates.append([np.mean([(index[key]['B2'] - index[key]['y']) ** 2
                                              for key in ids]) for index in lookup])
        observed, _, expected = reference(np.array(daily_base), np.array(daily_candidates),
                                         20, 1000, 20261002)
        assert np.isclose(observed, data['observed_max_mean_improvement'], rtol=0, atol=1e-12)
        assert expected == data['upper_pvalue']
        scores = {'baseline_rmse': float(np.sqrt(np.mean(daily_base))),
                  'candidate_rmse': {name: float(np.sqrt(np.mean(np.array(daily_candidates)[:, i])))
                                     for i, name in enumerate(('joint', 'amplitude', 'serial'))}}
        summaries.append({'baseline': baseline, 'upper_fraction': data['upper_pvalue'],
                          'independent_fraction': expected, 'max_mean_improvement': observed,
                          'daily_rows': 222, 'prediction_rows': 888, 'scores': scores})
    assert before == hashes()
    report = {'status': 'passed', 'batch': 3, 'full_period_status': rejected['status'],
              'full_period_reasons': rejected['reasons'], 'complete_periods': summaries,
              'original_files_unchanged': before, 'real_fits': 0,
              'scope': 'Already-seen fixed archive engineering demo; not a new efficacy experiment or complete family selection adjustment'}
    (OUT / 'archive-demo-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key != 'original_files_unchanged'}, indent=2))


if __name__ == '__main__':
    main()
