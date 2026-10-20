"""Independent read-only comparison; no package assembly or factor calculation."""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.trading_calendar import TradingCalendar

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

raw = ROOT / 'docs/experiments/raw/510300-offline-reuse-2026-09-15'
pack = raw / 'run-02'
m = json.loads((pack/'manifest.json').read_text())
files = {str(p.relative_to(pack)) for p in pack.rglob('*') if p.is_file() and p.name != 'manifest.json'}
assert files == set(m['file_hashes'])
assert all(sha(pack/p) == h for p,h in m['file_hashes'].items())
trusted = json.loads((ROOT/'docs/experiments/raw/factor-unit-four-fixes-controller-2026-09-15/verification.json').read_text())['reuse']
assert sha(pack/'fetch-manifest.json') == trusted['source_manifest_sha256']
assert sha(pack/'calendar.json') == trusted['calendar_sha256']
expected = {}
duplicate_count = 0
for entry in trusted['source_files']:
    p = pack/'originals'/entry['file']
    assert sha(p) == entry['sha256']
    for row in json.loads(p.read_text())['data']['sh510300']['qfqday']:
        if row[0] in expected:
            assert row == expected[row[0]]
            duplicate_count += 1
        expected[row[0]] = row
with (pack/'prices.csv').open(newline='') as f:
    reader = csv.reader(f)
    assert next(reader) == ['date','open','close','high','low','volume']
    actual = list(reader)
calendar = TradingCalendar.from_file(pack/'calendar.json')
sessions = list(calendar.trading_days('2019-09-02','2026-02-03'))
assert [r[0] for r in actual] == sessions
differences = [r[0] for r in actual if r != expected[r[0]]]
assert not differences
changed = []
baseline = (raw/'baseline/frozen-inputs-sha256.txt').read_text().splitlines()
for line in baseline:
    h, name = line.split(maxsplit=1)
    p = ROOT/name
    if not p.exists() or sha(p) != h:
        changed.append(name)
draft = json.loads((raw/'b1-contract-draft.json').read_text())
assert draft['data']['prices_csv_sha256'] == sha(pack/'prices.csv')
assert sha(ROOT/draft['candidate_card']['path']) == draft['candidate_card']['sha256']
assert sha(ROOT/draft['formula_binding']['module']) == draft['formula_binding']['sha256']
out = {'package_files':len(files),'rows_checked_all_fields':len(actual),
       'raw_overlap_rows':duplicate_count,'row_differences':differences,
       'prices_sha256':sha(pack/'prices.csv'), 'manifest_sha256':sha(pack/'manifest.json'),
       'baseline_count':len(baseline),'baseline_changed':changed,
       'draft_binding_matches':True,'first_evaluation':sessions[20],
       'formal_reassembly':False,'real_factor_or_target_calculation':False}
text = json.dumps(out,ensure_ascii=False,indent=2)
print(text)
if len(sys.argv)>1:
    with Path(sys.argv[1]).open('x') as f:
        f.write(text+'\n')
