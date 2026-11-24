"""Check the separate 47-day preview against already registered status data."""
from pathlib import Path
import importlib.util
import json
import hashlib

OUT = Path(__file__).resolve().parent
script = OUT / 'qualify-cn-westock-v4.py'
spec = importlib.util.spec_from_file_location('qualify', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source = OUT / 'cn-reconstructed-window-v4.json'
data = json.loads(source.read_text())
days = [d for d in data['target_dates'] if d <= '2026-10-23']
by_day = {}
chunks = []
for start in range(0, len(days), 9):
    module.DATES = tuple(days[start:start+9])
    result = module.baostock_crosscheck(data['unresolved_symbols_by_day'])
    by_day.update(result['by_day'])
    chunks.append({k:v for k,v in result.items() if k != 'by_day'})
counts = {}
for entries in by_day.values():
    for entry in entries.values():
        k = entry['status']
        counts[k] = counts.get(k, 0) + 1
output = {
    'scope': '47-day reconstruction preview, saved registered BaoStock sources only through 2026-10-23',
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
    'counts': counts, 'by_day': by_day, 'source_chunk_receipts': chunks,
    'later_dates': {d: data['unresolved_symbols_by_day'][d].get('no_provider_row', []) for d in data['target_dates'] if d > '2026-10-23'},
    'limits': 'Vendor tradestatus=0 corroborates a nontrading bar; not an exchange notice or PIT historical membership.',
}
(OUT / 'cn-reconstruction-status-v4.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'days':len(by_day), 'counts':counts, 'last_5_sessions_missing':sum(map(len,output['later_dates'].values()))}))
