"""Controller-only synthetic diagnostics; never run real factor/target calculations."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from lei_signal.research.factor_unit.study_contract import validate_study_contract
from lei_signal.research.factor_unit.state_description import describe_states

RAW = ROOT / 'docs/experiments/raw/factor-unit-close-adapter-2026-09-15'
base = json.loads((RAW / 'b0-synthetic-positive-contract.json').read_text())
base['_repo_root'] = str(ROOT)
results = {}
results['contract_control'] = validate_study_contract(base)['status']
c = copy.deepcopy(base)
for e in c['data_identity'].values():
    e['price_basis_evidence'] = '/definitely/not/a/real/evidence.json'
results['nonexistent_price_evidence'] = validate_study_contract(c)['status']
c = copy.deepcopy(base)
for cal in c['calendar_identity'].values():
    cal['source'] = base['candidate_card']['path']  # Markdown is not a session schedule.
    cal.pop('sha256', None)
    cal['coverage'] = ['1990-01-01', '2099-12-31']
results['markdown_as_calendar_without_hash'] = validate_study_contract(c)['status']
c = copy.deepcopy(base)
e = c['data_identity']['SPY']
e.update(available_at='garbageT', available_at_source='dummy', point_in_time_verified=True)
results['invalid_timestamp_and_dummy_source'] = validate_study_contract(c)['status']

# Formal CLI check with only synthetic inputs. No old output is touched.
c = copy.deepcopy(base)
keep = 'src/lei_signal/research/factor_unit/__init__.py'
c['code_identity'] = {keep: hashlib.sha256((ROOT / keep).read_bytes()).hexdigest()}
with tempfile.TemporaryDirectory(prefix='lei-b0-review-') as tmp:
    p = Path(tmp)
    (p / 'contract.json').write_text(json.dumps(c))
    run = subprocess.run([sys.executable, str(ROOT / 'scripts/check_factor_unit_readiness.py'),
                          '--contract', str(p / 'contract.json'), '--out', str(p / 'out')],
                         capture_output=True, text=True, cwd=ROOT)
    results['cli_deleted_required_code_keys'] = {'exit': run.returncode, 'stdout': run.stdout}

dates = pd.date_range('2020-01-01', periods=30, freq='D')
schedule = pd.DataFrame({'session': dates, 'close_at': dates.tz_localize('Asia/Shanghai')
                        + pd.Timedelta(hours=15)})
values = pd.DataFrame({'symbol': 'SYNTHETIC', 'session': dates,
                       'state': [None]*5 + [True]*25, 'I': [100.]*30})
contract = {'data_mode': 'synthetic', 'object_ref': base['object_ref'],
            'lookback': 20, 'e_offset': 1, 'x_offset': 22,
            'research_cutoff': '2019-01-01T15:00:00+08:00'}
d = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
results['past_cutoff_and_population'] = {
    'cutoff': contract['research_cutoff'], 'unconditional_n': d['unconditional']['n'],
    'true_n': d['true_group']['n'], 'false_n': d['false_group']['n']}
bad = values.copy()
bad['state'] = 'false'
results['string_false_counted_true'] = describe_states(bad, schedule, contract)['symbols']['SYNTHETIC']['state_true']
bad = values.copy()
bad['session'] = bad['session'] + pd.DateOffset(years=5)
try:
    describe_states(bad, schedule, contract)
    results['all_dates_outside_schedule'] = 'returned'
except Exception as exc:
    results['all_dates_outside_schedule'] = type(exc).__name__ + ': ' + str(exc)

protected = json.loads((RAW / 'protection-before.json').read_text())['protected']
changes = []
for rel, expected in protected.items():
    p = (Path('/Users/yongbiaoli/.lei_signal_lab/cache/timing') / (rel.split(':')[1]+'.parquet')
         if rel.startswith('CARRIER:') else ROOT / rel)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
        changes.append(rel)
results['protection'] = {'count': len(protected), 'changed': changes}
packages = {}
for name in ('b0-synthetic-positive-01', 'b0-synthetic-negative-01', 'b0-real-readiness-check-01'):
    run = RAW / name
    manifest = json.loads((run / 'manifest.json').read_text())
    bad = []
    for key, sha in manifest['file_hashes'].items():
        matches = [p for p in run.rglob('*') if p.is_file() and p.name == key]
        if len(matches) != 1 or hashlib.sha256(matches[0].read_bytes()).hexdigest() != sha:
            bad.append(key)
    packages[name] = {'files':len(manifest['file_hashes']), 'hash_errors':bad,
                      'contains_contract_bytes': any(p.name in ('contract.json','protocol.json') for p in run.rglob('*'))}
results['packages'] = packages
text = json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False)
print(text)
if len(sys.argv) > 1:
    with Path(sys.argv[1]).open('x') as f:
        f.write(text+'\n')
