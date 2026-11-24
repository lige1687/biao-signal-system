"""Source-bound daily/monthly reconstruction; writes a new external result only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import plistlib
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from monthly_diagnosis import load_core
from lei_signal.market_context.microstructure_equity import aggregate_amount_concentration, card, qualified_amount

HERE = Path(__file__).resolve().parent
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-refresh-20261108')
PREFIXES = ('sh.60', 'sh.68', 'sz.00', 'sz.30')


def read_bound(path, digest):
    payload = Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise RuntimeError('source SHA mismatch: ' + str(path))
    return json.loads(payload)


def table(body):
    if body.get('errorCode', body.get('error_code')) != '0':
        raise RuntimeError('source error status')
    return [dict(zip(body['fields'], row)) for row in body.get('data', body.get('rows', []))]


def verified_positive_witnesses(path):
    """Accept only six bound rows, retaining Bao amounts and its status conflict."""
    if path is None:
        return {}
    expected = {('sh.600647', '2024-06-13'), ('sh.600766', '2024-06-13'),
                ('sh.603133', '2024-06-13'), ('sz.002087', '2024-06-13'),
                ('sh.688065', '2023-06-15'), ('sz.300356', '2023-06-20')}
    witnesses = json.loads(path.read_text())['witnesses']
    if len(witnesses) != 6 or {(x['code'], x['date']) for x in witnesses} != expected:
        raise RuntimeError('witness scope differs from the six reviewed rows')
    result = {}
    for w in witnesses:
        bao = table(read_bound(w['baoPath'], w['baoSha256']))
        rows = [r for r in bao if r['code'] == w['code'] and r['date'] == w['date']]
        em = read_bound(w['emPath'], w['emSha256'])
        assert w['accepted'] is True and len(rows) == 1 and rows[0] == w['baoRow']
        rec = rows[0]
        assert rec['tradestatus'] == '0' and rec['adjustflag'] == '3'
        assert em['rc'] == 0 and em['data']['code'] == w['code'][3:]
        assert em['data']['market'] == (1 if w['code'].startswith('sh.') else 0)
        klines = [r for r in em['data']['klines'] if r.split(',')[0] == w['date']]
        assert klines == [w['emKline']]
        k = klines[0].split(',')
        amount, volume = Decimal(rec['amount']), Decimal(rec['volume'])
        assert amount.is_finite() and volume.is_finite() and amount > 0 and volume > 0
        assert abs(amount - Decimal(k[6])) <= 1 and abs(volume - Decimal(k[5])*100) <= 100
        assert all(Decimal(rec[name]) == Decimal(k[pos]) for name, pos in [('open', 1), ('close', 2), ('high', 3), ('low', 4)])
        assert Decimal(rec['low']) <= amount / volume <= Decimal(rec['high'])
        assert Decimal(rec['low']) <= min(Decimal(rec['open']), Decimal(rec['close'])) <= max(Decimal(rec['open']), Decimal(rec['close'])) <= Decimal(rec['high'])
        result[(w['code'], w['date'], w['baoSha256'])] = w
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--calendar', type=Path, required=True)
    parser.add_argument('--calendar-sha', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--positive-witnesses', type=Path)
    args = parser.parse_args()
    witnesses = verified_positive_witnesses(args.positive_witnesses)
    disk = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/win+mac通用']))
    if disk.get('VolumeUUID') != 'DEBA1C85-6059-3865-B50A-A8EE1F80E4D9':
        raise RuntimeError('external disk identity mismatch')
    if not args.out.resolve().is_relative_to(RAW.parent) or args.out.exists():
        raise RuntimeError('use a new task-owned external result directory')
    core = load_core()
    diagnostic = json.loads((HERE / 'monthly-gap-detail.json').read_text())
    meta = read_bound(core.META, diagnostic['sourceFingerprints']['meta'])
    index = Path(meta['index_path'])
    if core.digest(index) != diagnostic['sourceFingerprints']['index'] or core.digest(core.OLD) != diagnostic['sourceFingerprints']['oldUnion']:
        raise RuntimeError('old input index changed')
    probe = json.loads((HERE / 'probe-ledger.json').read_text())
    master_ref = next(e for e in probe['entries'] if e['name'] == 'baostock-stock-basic')
    master = {r['code']: r for r in table(read_bound(master_ref['path'], master_ref['sha256']))
              if r['type'] == '1' and r['code'].startswith(PREFIXES)}
    coverage = json.loads((core.REPO / 'docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json').read_text())
    calendar_ref = coverage['baseline']['calendar']
    if core.digest(Path(calendar_ref['path'])) != calendar_ref['sha256']:
        raise RuntimeError('old calendar changed')
    with Path(calendar_ref['path']).open() as stream:
        old_calendar = [r['trade_date'] for r in csv.DictReader(stream) if '2016-01-01' <= r['trade_date'] <= '2026-10-23']
    new_calendar = [r['calendar_date'] for r in table(read_bound(args.calendar, args.calendar_sha))
                    if r['is_trading_day'] == '1']
    if set(d for d in old_calendar if d >= '2026-09-01') != set(d for d in new_calendar if d <= '2026-10-23'):
        raise RuntimeError('calendar overlap disagrees')
    calendar = sorted(set(old_calendar) | set(new_calendar))
    if calendar[-1] != '2026-11-06':
        raise RuntimeError('latest calendar unavailable')
    entries = [json.loads(line) for line in (RAW / 'collection-requests.jsonl').read_text().splitlines()]
    new_refs = defaultdict(list)
    for ref in entries:
        if ref.get('event') == 'query' and ref.get('kind') in ('recent', 'history') and ref.get('status') == '0':
            new_refs[ref['code']].append(ref)
    old_items = {x['code']: x for x in core.iter_jsonl(index) if x['code'].startswith(PREFIXES)}
    old_union = {x['code']: x for x in core.iter_jsonl(core.OLD) if x['code'].startswith(PREFIXES)}
    codes = sorted(set(old_items) | {c for c, r in master.items() if r['ipoDate'] <= '2026-11-06' and (not r['outDate'] or r['outDate'] > '2026-09-01')})
    audit = {'oldRawFilesVerified': 0, 'newRawFilesVerified': 0, 'oldInvalidRows': [], 'newInvalidRows': [],
             'sameSourceRevisions': [], 'lifecycleUpdates': [], 'newOnlyCodes': [], 'validOldMonthlyDifferences': [],
             'qualifiedStatusConflicts': []}

    def stock_records():
        for code in codes:
            old = old_items.get(code)
            fresh = master.get(code)
            if old:
                ipo, out = old['supplier_ipo'], old.get('supplier_out')
            elif fresh:
                ipo, out = fresh['ipoDate'], fresh['outDate'] or None
                audit['newOnlyCodes'].append(code)
            if fresh and (fresh['ipoDate'] != ipo or (fresh['outDate'] or None) != out):
                audit['lifecycleUpdates'].append({'code': code, 'oldIpo': ipo, 'oldOut': out,
                                                  'newIpo': fresh['ipoDate'], 'newOut': fresh['outDate'] or None})
                ipo, out = fresh['ipoDate'], fresh['outDate'] or None
            amounts = {}
            old_refs = [(r, False) for r in old_union.get(code, {}).get('source_refs', [])]
            if old:
                old_refs += [(r, False) for r in old['reused_raw_sources']]
                old_refs += [(r, True) for r in old['new_price_sources']]
            seen = set()
            for ref, compressed in old_refs:
                path = ref.get('source_path') or ref['path']
                if path in seen:
                    continue
                seen.add(path)
                rows = core.source_rows(ref, compressed)
                audit['oldRawFilesVerified'] += 1
                for row in rows:
                    day = row[0]
                    if not '2016-01-01' <= day <= '2026-11-06' or not ref.get('valid_slice_start', day) <= day <= ref.get('valid_slice_end', day):
                        continue
                    if row[1] != code or row[9] != '3':
                        raise RuntimeError('raw code/adjustment conflict')
                    value = qualified_amount(row[10], row[8], row[7])
                    if value is None:
                        audit['oldInvalidRows'].append({'code': code, 'date': day, 'path': path})
                    if day in amounts and (value is None or amounts[day] is None or not math.isclose(value, amounts[day], rel_tol=0, abs_tol=.01)):
                        amounts[day] = None
                    else:
                        amounts[day] = value
            for ref in sorted(new_refs.get(code, []), key=lambda x: (x['kind'] == 'recent', x['utc'])):
                body = read_bound(ref['path'], ref['sha256'])
                if body.get('fields') != core.FIELDS or len(body.get('data', [])) != ref['rows']:
                    raise RuntimeError('new raw schema/count mismatch')
                audit['newRawFilesVerified'] += 1
                seen_days = set()
                for rec in table(body):
                    day = rec['date']
                    if rec['code'] != code or rec['adjustflag'] != '3' or day in seen_days or not ref['start'] <= day <= ref['end']:
                        raise RuntimeError('new raw identity/date conflict')
                    seen_days.add(day)
                    value = qualified_amount(rec['tradestatus'], rec['amount'], rec['volume'])
                    if value is None:
                        audit['newInvalidRows'].append({'code': code, 'date': day, 'path': ref['path']})
                        witness = witnesses.get((code, day, ref['sha256']))
                        if witness is not None:
                            assert rec == witness['baoRow'] and Path(ref['path']).resolve() == Path(witness['baoPath']).resolve()
                            value = float(rec['amount'])
                            audit['qualifiedStatusConflicts'].append(witness)
                    if day in amounts and value != amounts[day]:
                        audit['sameSourceRevisions'].append({'code': code, 'date': day, 'old': amounts[day], 'new': value})
                    amounts[day] = value
            yield code, ipo, out, amounts

    result = aggregate_amount_concentration(stock_records(), calendar, daily_start='2026-09-01', monthly_end='2026-10')
    assert len(audit['qualifiedStatusConflicts']) == len(witnesses)
    old_monthly = json.loads((core.HERE / 'monthly.json').read_text())
    monthly_lookup = {x['date']: x for x in result['monthly']}
    for old in old_monthly['points']:
        new = monthly_lookup[old['date']]
        if old['value'] is not None and (new['top5'] is None or abs(old['value'] - new['top5']) > 1e-10):
            audit['validOldMonthlyDifferences'].append({'date': old['date'], 'old': old['value'], 'new': new['top5']})
    audit.update({'generatedAt': datetime.now(timezone.utc).isoformat(),
                  'sourceFingerprints': diagnostic['sourceFingerprints'], 'masterSha256': master_ref['sha256'],
                  'calendarSha256': args.calendar_sha, 'collectionLedgerSha256': core.digest(RAW / 'collection-requests.jsonl'),
                  'sourcePolicy': 'Archived BaoStock + newly acquired BaoStock rows; new valid-version responses supersede old rows with revisions recorded. Six exact SHA-bound positive-amount rows qualify only with independent Eastmoney numerical witnesses; original status conflict retained. No cross-provider amount splice.',
                  'positiveWitnessesSha256': core.digest(args.positive_witnesses) if args.positive_witnesses else None,
                  'oldValidMonths': old_monthly['valid_months'],
                  'newValidMonths': sum(r['top5'] is not None for r in result['monthly']),
                  'newValidDays': sum(r['top5'] is not None for r in result['daily'])})
    cards = []
    limits = ['股票范围依供应商历史名录及更新后的上市/退出日期核对；上市日计入、摘牌生效日不再计入。不是交易所认证的完整历史主表。',
              '明确停牌且量额为空或零时才计零；缺源和未核实异常保留空值。6条历史成交状态冲突已用另一来源核对量额，保留原成交额。',
              '历史来源会修订，补采按当前取得的供应商版本重建；不能作为当时已知的逐时交易证据。',
              '仅描述成交分布，集中度不区分买入与卖出，也不自动判断顶底。当前是历史快照，尚未按新交易日自动采集。']
    for fraction in ('top5', 'top10'):
        rows = result['daily']
        valid_rows = [r for r in rows if r[fraction] is not None]
        last = valid_rows[-1] if valid_rows else None
        details = [{'label': '完整交易日', 'value': f"{len(valid_rows)}/{len(rows)}"},
                   {'label': '最新日期股票数', 'value': str(rows[-1]['n'])},
                   {'label': '最新缺源股票数', 'value': str(len(rows[-1]['missingCodes']))}]
        if last:
            details += [{'label': '最近合格日', 'value': last['date']}, {'label': '最近合格值', 'value': f"{last[fraction]*100:.2f}%"}]
        cards.append(card(f'cn-daily-amount-{fraction}', f'沪深A股每日成交额前{fraction[3:]}%占比', 'cn', '%',
                          'BaoStock沪深A股供应商上市期覆盖股，逐日原始成交额；已核2026-09-01至2026-11-06',
                          '按当天逐股成交额排序，观察交易集中程度。', 'BaoStock不复权日线及更新证券主表',
                          'https://github.com/zxygithub/baostock/blob/master/docs/pythonAPI.md',
                          [{'date': r['date'], 'value': None if r[fraction] is None else r[fraction]*100} for r in rows], limits, details))
    monthly = card('cn-monthly-amount-top5', '沪深A股每月成交额前5%占比', 'cn', '%',
                   'BaoStock沪深A股供应商覆盖股；先逐股累计整月成交额，再取前5%股票；2016-01至2026-10',
                   '观察整月交易集中程度；不是每日集中度的平均值。', 'BaoStock日线；6条历史异常由东方财富交叉核对',
                   'https://github.com/zxygithub/baostock/blob/master/docs/pythonAPI.md',
                   [{'date': r['date'], 'value': None if r['top5'] is None else r['top5']*100} for r in result['monthly']],
                   [f"已补齐{audit['newValidMonths']}/{len(result['monthly'])}个月；2016年5月、2020年6月仍有异常行情未核实，月值留空。"] + limits + [
                       '早期交易日历沿已绑定H00300指数日历，其中2019-09至2026-06与归档深交所官方日历一致；其他早期月份未独立全段认证。'],
                   [{'label': '完整月份', 'value': f"{audit['newValidMonths']}/{len(result['monthly'])}"},
                    {'label': '整月算法', 'value': '先每股加总整月，再按股排序；不是日值平均'}])
    monthly['frequency'] = 'monthly'
    cards.append(monthly)
    args.out.mkdir(parents=True)
    for name, payload in [('result.json', result), ('audit.json', audit), ('cards.json', cards)]:
        (args.out / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(json.dumps({'output': str(args.out), 'validDays': audit['newValidDays'], 'days': len(result['daily']),
                      'validMonths': audit['newValidMonths'], 'months': len(result['monthly']),
                      'latestDay': result['daily'][-1], 'latestMonth': result['monthly'][-1],
                      'validOldMonthlyDifferences': len(audit['validOldMonthlyDifferences']),
                      'sourceRevisions': len(audit['sameSourceRevisions']), 'newInvalidRows': len(audit['newInvalidRows'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
