"""Validate the prepared correction. Installation requires explicit user approval.

Default is read-only. The approved operation changes only the named history cache,
keeps its exact original bytes in a new backup, and records a local receipt.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import os

BASE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-approved', action='store_true')
    args = parser.parse_args()
    plan_path = BASE / 'cn-history-change-plan-v4.json'
    plan = json.loads(plan_path.read_text())
    target = Path(plan['target'])
    assert target == Path('/Users/yongbiaoli/.lei_signal_lab/cache/a_share_ma_breadth_history.json')
    original = target.read_bytes()
    assert sha(original) == plan['before_sha256'], 'Live history changed; stop for reconciliation'
    candidate_path = BASE / plan['candidate_file']
    candidate_bytes = candidate_path.read_bytes()
    assert sha(candidate_bytes) == plan['candidate_sha256']
    source_path = BASE / plan['source_file']
    source_bytes = source_path.read_bytes()
    assert sha(source_bytes) == plan['source_sha256']
    source = json.loads(source_bytes)
    before_rows, rows = json.loads(original), json.loads(candidate_bytes)
    before = {r['date']:r for r in before_rows}
    candidate = {r['date']:r for r in rows}
    assert len(before_rows) == len(before) == 1288
    assert len(rows) == len(candidate) == 1302
    assert [r['date'] for r in rows] == sorted(candidate)
    dates = set(source['target_dates'])
    assert len(dates) == 47
    assert len(set(candidate) - set(before)) == 14
    assert len(dates & set(before)) == 33
    assert len(set(before) - dates) == 1255
    for day, row in before.items():
        if day not in dates:
            assert candidate[day] == row
    for day in dates:
        counts = source['days'][day]['all']
        assert counts.get('same_day_valid_quote', 0) + counts.get('no_provider_row', 0) == counts['listed_current_code']
        for n in (20, 50, 200):
            assert counts.get(f'history_short_or_nontrade_under_{n}', 0) == 0
            assert counts[f'E{n}'] + counts.get(f'ipo_warmup_under_{n}', 0) == counts['same_day_valid_quote']
            value = candidate[day][f'ma{n}_pct']
            assert math.isfinite(value) and 0 <= value <= 100
            assert value == round(100 * counts[f'above{n}'] / counts[f'E{n}'], 6)
    known = json.loads((BASE / 'cn-reconstruction-status-v4.json').read_text())
    assert known['source_sha256'] == plan['source_sha256']
    checked_pairs = set()
    for day, entries in known['by_day'].items():
        for symbol, status in entries.items():
            assert status['status'] == 'observed_tradestatus_0'
            checked_pairs.add((day, symbol))
    recent = json.loads((BASE / 'cn-last-baostock-status-v4.json').read_text())
    assert recent['worker_exit_code'] == 0 and recent['timeout'] is None
    for event in recent['sdk_events']:
        if event['kind'] == 'end' and event['operation'] == 'query':
            assert event['error_code'] == '0'
            for raw in event['rows']:
                r = dict(zip(event['fields'], raw))
                if r['tradestatus'] == '0':
                    checked_pairs.add((r['date'], r['code'].replace('.', '')))
    required = {(d,s) for d in dates for s in source['unresolved_symbols_by_day'][d].get('no_provider_row', [])}
    assert len(required) == 338 and required <= checked_pairs
    receipt = {
        'status':'validated_not_installed', 'checked_at':datetime.now(timezone.utc).isoformat(),
        'target':str(target), 'before_sha256':sha(original), 'candidate_sha256':sha(candidate_bytes),
        'source_sha256':sha(source_bytes), 'plan_sha256':sha(plan_path.read_bytes()),
        'old_rows':1288, 'new_rows':1302, 'additions':14, 'corrections':33,
        'other_original_rows_preserved':1255, 'confirmed_nontrading_stock_days':338,
        'qualification':'current_list_observation_reconstruction; not PIT or strict_all_verified',
    }
    if not args.install_approved:
        print(json.dumps(receipt,ensure_ascii=False))
        return
    stamp = datetime.now().strftime('%Y%m%dT%H%M%S%f')
    backup = target.with_name(target.name + '.before-reconstruction-' + stamp + '.bak')
    with backup.open('xb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    assert backup.read_bytes() == original
    temporary = target.with_name(target.name + '.reconstruction-' + stamp + '.tmp')
    with temporary.open('xb') as f:
        f.write(candidate_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(temporary, target.stat().st_mode & 0o777)
    assert target.read_bytes() == original, 'Concurrent live change; preserved backup and temp, did not replace'
    temporary.replace(target)
    assert target.read_bytes() == candidate_bytes
    receipt.update(status='installed', backup=str(backup), backup_sha256=sha(backup.read_bytes()), after_sha256=sha(target.read_bytes()))
    (BASE / 'installation-v4.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__ == '__main__':
    main()
