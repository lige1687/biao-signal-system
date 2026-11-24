"""Independent Decimal arithmetic on new original rows, without the builder."""
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-refresh-20261108')
RESULT = RAW.parent / 'concentration-derived-20261108-run2/result.json'


def load(path, digest):
    data = Path(path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest
    return json.loads(data)


def main():
    probe = json.loads((HERE / 'probe-ledger.json').read_text())
    master_ref = next(x for x in probe['entries'] if x['name'] == 'baostock-stock-basic')
    body = load(master_ref['path'], master_ref['sha256'])
    basic = {r['code']: r for row in body['rows'] if (r := dict(zip(body['fields'], row)))['type'] == '1'
             and r['code'].startswith(('sh.60', 'sh.68', 'sz.00', 'sz.30'))}
    log = json.loads((HERE / 'collection-ledger.json').read_text())
    raw_log = Path(log['requestLog']).read_bytes()
    assert hashlib.sha256(raw_log).hexdigest() == log['requestLogSha256']
    entries = [json.loads(line) for line in raw_log.splitlines()]
    panel = defaultdict(dict)
    read_count = 0
    for ref in entries:
        if ref.get('kind') != 'recent' or ref.get('event') != 'query' or ref.get('status') != '0':
            continue
        source = load(ref['path'], ref['sha256'])
        read_count += 1
        for row in source['data']:
            rec = dict(zip(source['fields'], row))
            status = rec['tradestatus']
            volume = Decimal(rec['volume'] or '0')
            amount = Decimal(rec['amount'] or '0')
            assert volume.is_finite() and amount.is_finite() and amount >= 0 and volume >= 0
            if status == '0':
                assert volume == 0 and amount == 0
            else:
                assert status == '1' and rec['volume'] and rec['amount'] and ((volume == 0) == (amount == 0))
            assert rec['code'] == ref['code'] and rec['adjustflag'] == '3'
            assert rec['code'] not in panel[rec['date']]
            panel[rec['date']][rec['code']] = amount
    built = json.loads(RESULT.read_text())
    output = []
    for item in built['daily']:
        day = item['date']
        if day < '2026-10-08':
            continue
        expected = {c for c, r in basic.items() if r['ipoDate'] <= day and (not r['outDate'] or day < r['outDate'])}
        assert set(panel[day]) == expected
        values = sorted(panel[day].values(), reverse=True)
        denominator = sum(values)
        a = sum(values[:math.ceil(len(values)*.05)]) / denominator
        b = sum(values[:math.ceil(len(values)*.10)]) / denominator
        assert abs(float(a)-item['top5']) < 1e-12 and abs(float(b)-item['top10']) < 1e-12
        output.append({'date': day, 'n': len(values), 'denominator': str(denominator), 'top5': str(a), 'top10': str(b)})
    months = defaultdict(Decimal)
    october_days = [x['date'] for x in output if x['date'].startswith('2026-10')]
    for day in october_days:
        for code, amount in panel[day].items():
            months[code] += amount
    values = sorted(months.values(), reverse=True)
    monthly = sum(values[:math.ceil(len(values)*.05)]) / sum(values)
    actual_month = built['monthly'][-1]
    assert actual_month['date'] == '2026-10-30' and actual_month['n'] == len(values)
    assert abs(float(monthly)-actual_month['top5']) < 1e-12
    previous = json.loads((HERE / 'before/web/public/research/microstructure-observations-20261108/equity.json').read_text())
    unchanged = 0
    revisions = []
    review = json.loads((HERE / 'daily-revision-review.json').read_text())
    assert review['newOnly'] == ['sz.301718'] and not review['oldOnly']
    assert review['finding']['oldIndexMissingCode'] is True
    new_days = {x['date']: x for x in built['daily']}
    for card in previous['cards']:
        if card['id'] not in ('cn-daily-amount-top5', 'cn-daily-amount-top10'):
            continue
        key = card['id'].rsplit('-', 1)[-1]
        for point in card['points']:
            if point['value'] is not None:
                new_value = new_days[point['date']][key]*100
                if abs(new_value-point['value']) < 1e-9:
                    unchanged += 1
                else:
                    assert point['date'] == review['date'] == '2026-10-22'
                    assert abs(review['old'][key]-point['value']) < 1e-9
                    assert abs(review['new'][key]-new_value) < 1e-9
                    revisions.append({'id': card['id'], 'date': point['date'], 'old': point['value'], 'new': new_value,
                                      'reason': 'Old supplier index omitted sz.301718 on its listing day; new raw and master restore it.'})
    assert len(revisions) == 2 and unchanged == 60
    added = review['changed'][0]['new']
    raw = load(added['path'], added['sha256'])
    added_row = next(dict(zip(raw['fields'], r)) for r in raw['data'] if r[0] == review['date'])
    assert added_row['code'] == 'sz.301718' and Decimal(added_row['amount']) == Decimal('2187703775.4200')
    assert basic['sz.301718']['ipoDate'] == '2026-10-22'
    old_monthly = json.loads((ROOT / 'docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/implementation-v2/concentration/monthly.json').read_text())
    month_map = {r['date']: r for r in built['monthly']}
    original_valid = [p for p in old_monthly['points'] if p['value'] is not None]
    assert len(original_valid) == 84
    assert all(abs(month_map[p['date']]['top5']-p['value']) < 1e-10 for p in original_valid)
    result = {'recentRawObjectsVerified': read_count, 'daysIndependentlyVerified': len(output), 'daily': output,
              'october': {'stockCount': len(values), 'denominator': str(sum(values)), 'top5': str(monthly)},
              'oldValidDailyReadingsUnchanged': unchanged, 'explainedDailyRevisions': revisions,
              'oldValidMonthsUnchanged': 84,
              'method': 'Decimal raw sums/ranks; no production calculation imports'}
    (HERE / 'independent-arithmetic.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'recentRawObjectsVerified': read_count, 'days': len(output), 'oldValidDailyReadingsUnchanged': unchanged,
                      'latest': output[-1], 'october': result['october']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
