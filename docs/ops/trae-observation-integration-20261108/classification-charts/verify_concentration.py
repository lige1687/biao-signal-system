"""Independent source arithmetic for the concentration UI handoff; no network."""
from pathlib import Path
from hashlib import sha256
import json
import math

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = REPO / 'docs/ops/microstructure-observations-20261108/concentration-refresh'


def bound(path, digest):
    raw = Path(path).read_bytes()
    assert sha256(raw).hexdigest() == digest, str(path)
    return json.loads(raw)


def records(body):
    assert body.get('errorCode', body.get('error_code')) == '0'
    return [dict(zip(body['fields'], row)) for row in body.get('data', body.get('rows', []))]


probe = json.loads((SOURCE / 'probe-ledger.json').read_text())
master_ref = next(row for row in probe['entries'] if row['name'] == 'baostock-stock-basic')
master = records(bound(master_ref['path'], master_ref['sha256']))
ledger = json.loads((SOURCE / 'collection-ledger.json').read_text())
raw_log = Path(ledger['requestLog']).read_bytes()
assert sha256(raw_log).hexdigest() == ledger['requestLogSha256']
refs = [json.loads(line) for line in raw_log.splitlines()]
recent = {r['code']: r for r in refs if r.get('event') == 'query' and r.get('kind') == 'recent' and r.get('status') == '0'}
packet_path = REPO / 'web/public/research/microstructure-observations-20261108/equity.json'
packet = json.loads(packet_path.read_text())
cards = {card['id']: card for card in packet['cards']}
assert 'cn-monthly-amount-top5' in cards, 'New packet has not been handed off yet'
days = ['2026-10-19', '2026-10-22', '2026-10-23', '2026-11-06']
summary = json.loads((SOURCE / 'collection-summary.json').read_text())
calendar_ref = summary['calendar']
october = [r['calendar_date'] for r in records(bound(calendar_ref['sourcePath'], calendar_ref['sha256']))
           if r['calendar_date'].startswith('2026-10') and r['is_trading_day'] == '1']
amounts = {day: {} for day in sorted(set(days + october))}
suspended = {day: [] for day in amounts}
for code, ref in recent.items():
    for row in records(bound(ref['path'], ref['sha256'])):
        day = row['date']
        if day not in amounts:
            continue
        assert row['code'] == code and row['adjustflag'] == '3'
        assert code not in amounts[day]
        if row['tradestatus'] == '0':
            assert row['amount'] in ('', '0', '0.0000') or float(row['amount']) == 0
            assert row['volume'] in ('', '0', '0.0000') or float(row['volume']) == 0
            amount = 0.0
            suspended[day].append(code)
        else:
            assert row['tradestatus'] == '1'
            amount = float(row['amount'])
            volume = float(row['volume'])
            assert math.isfinite(amount) and math.isfinite(volume) and amount >= 0 and volume >= 0
            assert (amount == 0) == (volume == 0)
        amounts[day][code] = amount

checks = []
for day in days:
    expected = {r['code'] for r in master if r['type'] == '1' and r['code'].startswith(('sh.60', 'sh.68', 'sz.00', 'sz.30'))
                and r['ipoDate'] <= day and (not r['outDate'] or day < r['outDate'])}
    assert expected == set(amounts[day]), (day, sorted(expected - set(amounts[day])), sorted(set(amounts[day]) - expected))
    ranked = sorted(amounts[day].items(), key=lambda x: x[1], reverse=True)
    total = math.fsum(value for _, value in ranked)
    values = {}
    for fraction in (5, 10):
        count = math.ceil(len(expected) * fraction / 100)
        numerator = math.fsum(value for _, value in ranked[:count])
        value = 100 * numerator / total
        shown = next(point['value'] for point in cards[f'cn-daily-amount-top{fraction}']['points'] if point['date'] == day)
        assert shown is not None and abs(value - shown) < 1e-8, (day, fraction, value, shown)
        values[str(fraction)] = {'topCount': count, 'topAmount': numerator, 'percent': value, 'packetPercent': shown}
    checks.append({'date': day, 'expectedStocks': len(expected), 'actualStocks': len(amounts[day]), 'totalAmount': total,
                   'explicitSuspensions': len(suspended[day]), 'concentration': values,
                   'largestThree': ranked[:3], 'absentRowsFilled': 0})

monthly_amounts = {}
for security in master:
    code = security['code']
    if security['type'] != '1' or not code.startswith(('sh.60', 'sh.68', 'sz.00', 'sz.30')):
        continue
    expected_days = [d for d in october if security['ipoDate'] <= d and (not security['outDate'] or d < security['outDate'])]
    if expected_days:
        monthly_amounts[code] = math.fsum(amounts[day][code] for day in expected_days)
ranked_month = sorted(monthly_amounts.values(), reverse=True)
monthly_top_count = math.ceil(len(ranked_month) * .05)
monthly_value = 100 * math.fsum(ranked_month[:monthly_top_count]) / math.fsum(ranked_month)
shown_monthly = next(p['value'] for p in cards['cn-monthly-amount-top5']['points'] if p['date'] == october[-1])
assert shown_monthly is not None and abs(monthly_value - shown_monthly) < 1e-8
monthly_check = {'date': october[-1], 'tradingDays': len(october), 'stocks': len(ranked_month),
                 'topCount': monthly_top_count, 'percent': monthly_value, 'packetPercent': shown_monthly,
                 'method': 'sum each listed stock over its eligible October dates, then rank stock totals'}

diagnostic = json.loads((SOURCE / 'monthly-gap-detail.json').read_text())
frozen = REPO / 'docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/implementation-v2/concentration/monthly.json'
old_monthly = bound(frozen, diagnostic['sourceFingerprints']['monthly'])
new_monthly = {p['date']: p['value'] for p in cards['cn-monthly-amount-top5']['points']}
for old_point in old_monthly['points']:
    if old_point['value'] is not None:
        assert new_monthly[old_point['date']] is not None
        assert abs(100 * old_point['value'] - new_monthly[old_point['date']]) < 1e-8
history_check = {'oldValidMonths': sum(p['value'] is not None for p in old_monthly['points']),
                 'newValidMonths': sum(v is not None for v in new_monthly.values()),
                 'totalMonths': len(new_monthly), 'oldQualifiedValuesUnchanged': True,
                 'remainingMissingMonths': [d for d, v in new_monthly.items() if v is None]}

witnesses = json.loads((SOURCE / 'positive-amount-witnesses.json').read_text())['witnesses']
verified_witnesses = []
for witness in witnesses:
    bao = records(bound(witness['bao']['path'], witness['bao']['sha256']))
    row = next(r for r in bao if r['date'] == witness['date'])
    em = bound(witness['eastmoney']['path'], witness['eastmoney']['sha256'])['data']
    assert row['code'] == witness['code'] and row['tradestatus'] == '0'
    assert em['code'] == witness['code'].split('.')[1]
    other = next(r.split(',') for r in em['klines'] if r.startswith(witness['date'] + ','))
    amount, volume = float(row['amount']), float(row['volume'])
    assert amount > 0 and volume > 0
    assert abs(float(other[6]) - amount) <= 1
    assert abs(100 * float(other[5]) - volume) <= 100
    assert float(row['low']) <= amount / volume <= float(row['high'])
    assert [float(row[k]) for k in ('open', 'close', 'high', 'low')] == [float(x) for x in other[1:5]]
    verified_witnesses.append({'code': witness['code'], 'date': witness['date'], 'originalStatusConflictPreserved': True})
assert len(verified_witnesses) == 6

before = json.loads((SOURCE / 'before/web/public/research/microstructure-observations-20261108/equity.json').read_text())
changed_other = [c['id'] for c in before['cards'] if 'daily-amount-top' not in c['id'] and c != cards.get(c['id'])]
assert not changed_other, changed_other
result = {'status': 'passed', 'publicPacketSha256': sha256(packet_path.read_bytes()).hexdigest(),
          'rawLedgerSha256': ledger['requestLogSha256'], 'masterSha256': master_ref['sha256'],
          'independentChecks': checks, 'monthlyCheck': monthly_check, 'unrelatedCardsUnchanged': True,
          'frozenMonthlyUnchanged': True, 'monthlyHistoryCheck': history_check,
          'independentPositiveAmountWitnessChecks': verified_witnesses,
          'scope': 'Provider lifecycle pool, latest acquired source version; not historical tradability or timing evidence.'}
(HERE / 'data-arithmetic-acceptance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
