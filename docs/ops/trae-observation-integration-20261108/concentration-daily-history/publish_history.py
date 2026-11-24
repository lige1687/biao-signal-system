"""Adopt exactly two independently verified daily cards; preserve all other data."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
contract = json.loads((HERE / 'run-contract.json').read_text())
out = Path(contract['out'])
packet_path = REPO / 'web/public/research/microstructure-observations-20261108/equity.json'
receipt = REPO / 'docs/ops/microstructure-observations-20261108/concentration-daily-history/accepted.json'
prior_receipt = REPO / 'docs/ops/microstructure-observations-20261108/concentration-refresh/accepted.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_json(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def atomic(path, payload):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.concentration-', delete=False) as f:
        f.write(payload)
        temp = Path(f.name)
    os.chmod(temp, path.stat().st_mode & 0o777 if path.exists() else 0o644)
    os.replace(temp, path)
    assert path.read_bytes() == payload


assert not receipt.exists() and not (out / 'accepted-cards.json').exists()
old_sha = '4ac6df72bc3c9c8e9390d1e932b9f4689e5513c55599d7aaf496a75586137e0a'
assert digest(packet_path) == digest(out.parent / 'equity-before.json') == old_sha
assert digest(out / 'cards.json') == 'cbab30156c16ec2be572d20de4b2518006142b020e5185e4791f9f55ec4788dc'
assert digest(out / 'result.json') == '2c759fa67c30c089c27617ecbe77702ced6e61e436ae565be05cf0bbc33a7ab2'
assert digest(out / 'audit.json') == 'cec49bbf9b772061055279a8fde3b0349df948ea9fc9bd4e7719a99083328956'
old = json.loads(packet_path.read_bytes())
original = {c['id']: c for c in old['cards']}
assert len(original) == len(old['cards']) == 67
candidate = {c['id']: c for c in json.loads((out / 'cards.json').read_bytes())}
daily_ids = ('cn-daily-amount-top5', 'cn-daily-amount-top10')
for id in daily_ids:
    card = candidate[id]
    points = card['points']
    assert len(points) == 2633 and points[-43:] == original[id]['points']
    assert points[0]['date'] == '2016-01-04' and points[-1]['date'] == '2026-11-06'
    assert [p['date'] for p in points if p['value'] is None] == ['2016-05-12', '2020-06-17']
    card['scope'] = 'BaoStock沪深A股供应商上市期覆盖股，逐日原始成交额；2016-01-04至2026-11-06。'
    card['limitations'] = [
        '2631/2633个交易日有效；2016-05-12、2020-06-17的个股成交资料未核实，留空。',
        *card['limitations'],
        '早期日历沿归档指数交易日，其中2019-09至2026-06与深交所归档日历一致；其他早期月份未独立全段认证。',
    ]
monthly_id = 'cn-monthly-amount-top5'
assert candidate[monthly_id]['points'] == original[monthly_id]['points']
accepted_cards = [*(candidate[id] for id in daily_ids), original[monthly_id]]
accepted_file = out / 'accepted-cards.json'
with accepted_file.open('xb') as f:
    f.write(raw_json(accepted_cards))
assert json.loads(accepted_file.read_bytes()) == accepted_cards
updated = {**old, 'cards': [candidate[c['id']] if c['id'] in daily_ids else c for c in old['cards']]}
assert [c['id'] for c in updated['cards']] == [c['id'] for c in old['cards']]
assert [c for c in updated['cards'] if c['id'] not in daily_ids] == [c for c in old['cards'] if c['id'] not in daily_ids]
assert updated['unavailable'] == old['unavailable']
assert digest(packet_path) == old_sha
receipt.parent.mkdir(parents=True, exist_ok=True)
binding = {'status': 'accepted', 'acceptedAt': datetime.now(timezone.utc).isoformat(),
           'cardsPath': str(accepted_file), 'cardsSha256': digest(accepted_file),
           'resultSha256': digest(out / 'result.json'), 'auditSha256': digest(out / 'audit.json'),
           'priorReceiptSha256': digest(prior_receipt), 'dailyCoverage': [2631, 2633],
           'missingDays': ['2016-05-12', '2020-06-17']}
atomic(receipt, raw_json(binding))
atomic(packet_path, raw_json(updated))
record = {'beforeSha256': old_sha, 'afterSha256': digest(packet_path),
          'acceptedCardsSha256': digest(accepted_file), 'preservedCards': 65, 'preservedUnavailable': len(old['unavailable']),
          'changedCards': list(daily_ids), 'receiptSha256': digest(receipt), 'readback': True}
(HERE / 'publication.json').write_text(json.dumps(record, indent=2) + '\n')
print(record)
