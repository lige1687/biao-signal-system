"""Read-only input and archive review; no signals or returns computed."""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.trading_calendar import TradingCalendar

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

raw = ROOT / 'docs/experiments/raw/factor-unit-four-fixes-2026-09-15'
protected = []
for line in (raw / 'baseline/protected-raw-sha256.txt').read_text().splitlines():
    h, name = line.split(maxsplit=1)
    protected.append((name, (ROOT / name).is_file() and sha(ROOT / name) == h))
p = raw / 'final-synthetic-positive-01'
m = json.loads((p / 'manifest.json').read_text())
actual = {str(f.relative_to(p)) for f in p.rglob('*') if f.is_file() and f.name != 'manifest.json'}
package = {'count': len(actual), 'key_difference': sorted(actual ^ set(m['file_hashes'])),
           'hash_errors': [k for k,h in m['file_hashes'].items() if sha(p/k) != h],
           'contract_equal': sha(p/'contract.source.json') == m['contract_sha256'],
           'dependency_closure': m['dependency_closure'], 'exit_code': m['exit_code']}
base = ROOT / 'docs/experiments/raw/research-third-2026-09-08/06'
manifest = json.loads((base/'fetch-manifest.json').read_text())
entries = [e for e in manifest if e['symbol'] == 'sh510300']
quotes = {}
conflicts = []
duplicates = 0
for e in entries:
    assert sha(base/e['file']) == e['sha256'], e['file']
    payload = json.loads((base/e['file']).read_text())
    assert payload['code'] == 0 and e['field'] == 'qfqday'
    rows = payload['data']['sh510300']['qfqday']
    assert len(rows) == e['rows']
    for row in rows:
        if row[0] in quotes:
            duplicates += 1
            if row != quotes[row[0]]:
                conflicts.append(row[0])
        quotes[row[0]] = row
cal_path = ROOT/'docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json'
cal = TradingCalendar.from_file(cal_path)
days = cal.trading_days('2019-09-02', '2026-02-03')
selected = {d:r for d,r in quotes.items() if '2019-09-02' <= d <= '2026-02-03'}
invalid = [d for d,r in selected.items() if any(not math.isfinite(float(v)) or float(v) <= 0 for v in r[1:5])]
result = {'protected_count':len(protected), 'protected_changed':[n for n,ok in protected if not ok],
          'package':package, 'reuse':{'source_manifest_sha256':sha(base/'fetch-manifest.json'),
          'source_files':entries, 'unique_all_dates':len(quotes), 'overlap_rows':duplicates,
          'overlap_conflicts':conflicts, 'calendar_sha256':sha(cal_path),
          'required_sessions':len(days), 'selected_rows':len(selected),
          'missing':sorted(set(days)-set(selected)), 'non_sessions':sorted(set(selected)-set(days)),
          'invalid_ohlc':invalid, 'first_evaluation':days[20],
          'tail':cal.trading_days('2026-01-01','2026-03-01')[21],
          'scope':'input structure only; not point-in-time or total-return verification'}}
assert not result['protected_changed']
assert not package['key_difference'] and not package['hash_errors'] and package['contract_equal']
text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
print(text)
if len(sys.argv) > 1:
    with Path(sys.argv[1]).open('x') as f:
        f.write(text + '\n')
