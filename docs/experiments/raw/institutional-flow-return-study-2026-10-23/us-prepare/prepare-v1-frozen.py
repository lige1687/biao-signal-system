"""Prepare dated N-PORT fund pressure, lagged holdings, and identity evidence.

This module never reads prices, outcomes, or computes effect statistics.
"""

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import plistlib
import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
OUT = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/us-prepared')
NEW_MANIFEST = ROOT / 'nport-acquisition.json'
OLD_MANIFEST = ROOT.parent / 'institutional-flow-holdings-pilot-2026-10-21/mirror-qualification/request-manifest.json'
FILINGS = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/prepared/four-fund-all-filings.parquet')
STORAGE_PLAN = ROOT / 'storage-plan.json'
FUNDS = ('S000000856', 'S000006037', 'S000007112', 'S000011202')
HOLD_COLS = ['ACCESSION_NUMBER', 'HOLDING_ID', 'ISSUER_CUSIP', 'ISSUER_NAME', 'ISSUER_TITLE',
             'BALANCE', 'UNIT', 'CURRENCY_CODE', 'CURRENCY_VALUE', 'PAYOFF_PROFILE',
             'ASSET_CAT', 'ISSUER_TYPE', 'INVESTMENT_COUNTRY', 'IS_RESTRICTED_SECURITY',
             'FAIR_VALUE_LEVEL', 'DERIVATIVE_CAT']
ID_COLS = ['HOLDING_ID', 'IDENTIFIER_ISIN', 'IDENTIFIER_TICKER']


def quarter_ends():
    return [dt.date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m])
            for y in range(2020, 2027) for m in (3, 6, 9, 12)
            if dt.date(y, m, 1) <= dt.date(2026, 6, 1)]


def previous_quarter(date):
    m = date.month - 3
    return dt.date(date.year if m else date.year - 1, m if m else 12,
                   {3: 31, 6: 30, 9: 30, 12: 31}[m if m else 12])


def cusip_valid(c):
    if not isinstance(c, str) or not re.fullmatch(r'[0-9A-Z*@#]{9}', c):
        return False
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ*@#'
    values = [chars.index(x) for x in c]
    digits = []
    for i, value in enumerate(values[:8]):
        n = value * (2 if i % 2 else 1)
        digits.extend(divmod(n, 10) if n >= 10 else (n,))
    return (10 - sum(digits) % 10) % 10 == values[8]


def isin_valid(s):
    if not isinstance(s, str) or not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', s):
        return False
    chars = ''.join(str(int(c, 36)) if c.isalpha() else c for c in s)
    digits = [int(x) for x in chars]
    total = 0
    for i, digit in enumerate(reversed(digits)):
        n = digit * (2 if i % 2 else 1)
        total += n // 10 + n % 10
    return total % 10 == 0


def ticker(s):
    if not isinstance(s, str):
        return None
    s = s.strip().upper()
    return s if re.fullmatch(r'[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z0-9]{1,2})?', s) else None


def eligible(row):
    tests = [
        ('asset_cat', row['ASSET_CAT'] == 'EC'), ('unit', row['UNIT'] == 'NS'),
        ('currency', row['CURRENCY_CODE'] == 'USD'), ('issuer_type', row['ISSUER_TYPE'] == 'CORP'),
        ('country', row['INVESTMENT_COUNTRY'] == 'US'),
        ('long', row['PAYOFF_PROFILE'] == 'Long'),
        ('restricted', row['IS_RESTRICTED_SECURITY'] == 'N'),
        ('level1', str(row['FAIR_VALUE_LEVEL']) == '1'),
        ('nonderivative', not row['DERIVATIVE_CAT']),
        ('positive_value', row['CURRENCY_VALUE'] is not None and row['CURRENCY_VALUE'] > 0),
        ('positive_shares', row['BALANCE'] is not None and row['BALANCE'] > 0),
        ('cusip9', cusip_valid(row['ISSUER_CUSIP'])),
    ]
    return [name for name, passed in tests if not passed]


def select_latest(rows, series, period, decision):
    candidates = [r for r in rows if r['SERIES_ID'] == series and r['REPORT_DATE'] == period
                  and r['SUB_TYPE'] in ('NPORT-P', 'NPORT-P/A')
                  and r['FILING_DATE'] is not None and r['FILING_DATE'] < decision]
    if not candidates:
        return None, 'missing_asof_filing'
    last = max(r['FILING_DATE'] for r in candidates)
    finalists = {r['ACCESSION_NUMBER']: r for r in candidates if r['FILING_DATE'] == last}
    if len(finalists) != 1:
        return None, 'same_day_version_ambiguity'
    return next(iter(finalists.values())), None


def pressure(row, lag):
    fields = [row.get(f'{name}_FLOW_MON{i}') for name in ('SALES', 'REDEMPTION') for i in (1, 2, 3)]
    nav = lag.get('NET_ASSETS')
    if nav is None or nav <= 0 or any(v is None for v in fields):
        return None, 'missing_flow_or_lag_nav'
    if any(v < 0 for v in fields):
        return None, 'negative_gross_flow'
    sales = sum((row[f'SALES_FLOW_MON{i}'] for i in (1, 2, 3)), Decimal(0))
    redemption = sum((row[f'REDEMPTION_FLOW_MON{i}'] for i in (1, 2, 3)), Decimal(0))
    reinvest = [row.get(f'REINVESTMENT_FLOW_MON{i}') for i in (1, 2, 3)]
    raw = (redemption - sales) / nav
    return dict(sales=sales, redemption=redemption,
                reinvestment=sum(reinvest, Decimal(0)) if all(x is not None for x in reinvest) else None,
                lag_nav=nav, signed_redemption_ratio=raw,
                redemption_pressure=max(raw, Decimal(0))), None


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(4 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def guard_output_storage():
    plan = json.loads(STORAGE_PLAN.read_text())
    mount = Path(plan['external_mount'])
    planned_root = Path(plan['output'])
    if not OUT.resolve().is_relative_to(planned_root.resolve()):
        raise ValueError('output escaped planned external result directory')
    if not mount.is_dir() or mount.stat().st_dev != plan['external_device']:
        raise ValueError('external storage device differs from saved plan')
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', str(mount)]))
    if volume.get('VolumeUUID', '').upper() != plan['external_uuid'].upper():
        raise ValueError('external storage volume UUID differs from saved plan')
    if shutil.disk_usage(mount).free < plan['external_reserve_bytes'] + 4 * 1024 * 1024:
        raise ValueError('external storage below plan reserve')


def source_index():
    latest = json.loads(NEW_MANIFEST.read_text())
    prior = json.loads(OLD_MANIFEST.read_text())['files']
    result = {r['relative_path']: r for r in prior}
    for r in latest:
        if r.get('state') == 'completed' and r.get('sha256'):
            result[r['relative_path']] = r
    return result


def required_sources(index):
    names = []
    for y in range(2019, 2027):
        for q in range(1, 5):
            if (y, q) < (2019, 4) or (y, q) > (2026, 2):
                continue
            for kind in ('SUBMISSION', 'FUND_REPORTED_INFO', 'FUND_REPORTED_HOLDING', 'IDENTIFIERS'):
                names.append(f'{kind}/year={y}/quarter={q}/data.parquet')
    missing = [name for name in names if name not in index or not Path(index[name]['path']).is_file()]
    return names, missing


def verified(path_name, index, checked):
    entry = index[path_name]
    if path_name not in checked:
        path = Path(entry['path'])
        if path.stat().st_size != entry['bytes'] or sha256_file(path) != entry['sha256']:
            raise ValueError(f'source fingerprint mismatch: {path_name}')
        checked[path_name] = dict(path=str(path), bytes=entry['bytes'], sha256=entry['sha256'])
    return Path(entry['path'])


def filtered_batches(path, columns, allowed, field='ACCESSION_NUMBER'):
    pf = pq.ParquetFile(path)
    value_set = pa.array(sorted(allowed))
    for batch in pf.iter_batches(batch_size=131072, columns=columns):
        sub = batch.filter(pc.is_in(batch.column(batch.schema.get_field_index(field)), value_set=value_set))
        if sub.num_rows:
            yield sub.to_pylist()


def identity_resolution(target, candidates):
    own = [x for x in candidates if x['series'] == target['series'] and x['holding_id'] == target['holding_id']]
    peers = [x for x in candidates if x['series'] != target['series']]
    observed = own + peers
    invalid_isin = [x for x in observed if x.get('isin') and not isin_valid(x['isin'])]
    isins = {x['isin'] for x in observed if x.get('isin') and isin_valid(x['isin'])}
    if invalid_isin or len(isins) > 1:
        return None, 'isin_conflict_or_invalid', observed
    if any(s.startswith('US') and s[2:11] != target['cusip'] for s in isins):
        return None, 'isin_cusip_mismatch', observed
    tickers = {x['ticker'] for x in observed if x.get('ticker')}
    if len(tickers) > 1:
        return None, 'ticker_conflict', observed
    if not tickers:
        return None, 'ticker_missing', observed
    bad_ticker = any(x.get('raw_ticker') and not x.get('ticker') for x in observed)
    if bad_ticker:
        return None, 'ticker_invalid', observed
    return next(iter(tickers)), 'candidate_only', observed


def run():
    index = source_index()
    names, missing = required_sources(index)
    if missing:
        raise SystemExit('Required source partitions incomplete: ' + ', '.join(missing[:20]))
    checked = {}
    rows = pq.read_table(FILINGS).to_pylist()
    filings_hash = sha256_file(FILINGS)
    # Read and verify all filings' source partitions for peer as-of identity eligibility.
    submissions = {}
    submission_conflicts = set()
    series_memberships = collections.defaultdict(set)
    for name in names:
        if name.startswith('SUBMISSION/'):
            for r in pq.read_table(verified(name, index, checked), columns=['ACCESSION_NUMBER', 'FILING_DATE', 'SUB_TYPE', 'REPORT_DATE']).to_pylist():
                if r['ACCESSION_NUMBER'] in submissions and submissions[r['ACCESSION_NUMBER']] != r:
                    submission_conflicts.add(r['ACCESSION_NUMBER'])
                submissions[r['ACCESSION_NUMBER']] = r
        elif name.startswith('FUND_REPORTED_INFO/'):
            for r in pq.read_table(verified(name, index, checked), columns=['ACCESSION_NUMBER', 'SERIES_ID']).to_pylist():
                if r['SERIES_ID']:
                    series_memberships[r['ACCESSION_NUMBER']].add(r['SERIES_ID'])
    for accession in submission_conflicts:
        submissions.pop(accession, None)
    series_by_acc = {acc: next(iter(series)) for acc, series in series_memberships.items() if len(series) == 1}
    ambiguous_series_accessions = sum(len(series) > 1 for series in series_memberships.values())
    selected, decisions = [], quarter_ends()
    for decision in decisions:
        q = previous_quarter(decision)
        lag = previous_quarter(q)
        for series in FUNDS:
            cur, err = select_latest(rows, series, q, decision)
            old, old_err = select_latest(rows, series, lag, decision)
            rec = dict(decision_date=decision.isoformat(), flow_period=q.isoformat(), lag_period=lag.isoformat(),
                       series=series, flow_accession=cur['ACCESSION_NUMBER'] if cur else None,
                       lag_accession=old['ACCESSION_NUMBER'] if old else None,
                       flow_filed=cur['FILING_DATE'].isoformat() if cur else None,
                       lag_filed=old['FILING_DATE'].isoformat() if old else None,
                       flow_subtype=cur['SUB_TYPE'] if cur else None,
                       lag_subtype=old['SUB_TYPE'] if old else None,
                       status=err or old_err or 'selected')
            if rec['status'] == 'selected':
                v, error = pressure(cur, old)
                if error:
                    rec['status'] = error
                else:
                    rec.update({k: str(x) if x is not None else None for k, x in v.items()})
            selected.append(rec)
    active = [x for x in selected if x['status'] == 'selected']
    lag_accessions = {x['lag_accession'] for x in active}
    lag_lookup = {x['lag_accession']: x for x in active}
    target_holdings, exclusions = [], collections.Counter()
    target_holding_ids = set()
    # First bounded pass: only selected lag-report holdings, including all exclusion counts.
    for name in names:
        if not name.startswith('FUND_REPORTED_HOLDING/'):
            continue
        path = verified(name, index, checked)
        for batch in filtered_batches(path, HOLD_COLS, lag_accessions):
            for r in batch:
                why = eligible(r)
                exclusions.update(why)
                exclusions['all_lag_rows'] += 1
                if why:
                    continue
                if r['HOLDING_ID'] in target_holding_ids:
                    raise ValueError(f'duplicate selected holding ID {r["HOLDING_ID"]}')
                target_holding_ids.add(r['HOLDING_ID'])
                rec = dict(r)
                rec['source_partition'] = name
                target_holdings.append(rec)
    target_cusips = {x['ISSUER_CUSIP'] for x in target_holdings}
    # Peer as-of versions: latest unique NPORT-P or amendment for each fund/lag period.
    peer_rows = collections.defaultdict(list)
    for accession, meta in submissions.items():
        series = series_by_acc.get(accession)
        if series and meta['REPORT_DATE'] and meta['SUB_TYPE'] in ('NPORT-P', 'NPORT-P/A'):
            peer_rows[(series, meta['REPORT_DATE'])].append(dict(meta, SERIES_ID=series))
    peer_series_by_period = collections.defaultdict(set)
    for series, period in peer_rows:
        peer_series_by_period[period].add(series)
    peer_accessions = set()
    for decision in decisions:
        lag = previous_quarter(previous_quarter(decision))
        for series in peer_series_by_period[lag]:
            choice, error = select_latest(peer_rows[(series, lag)], series, lag, decision)
            if not error:
                peer_accessions.add(choice['ACCESSION_NUMBER'])
    acc_values = pa.array(sorted(peer_accessions), type=pa.string())
    cusip_values = pa.array(sorted(target_cusips), type=pa.string())
    # Second bounded pass: same lag date and CUSIP; never look at current-end holdings.
    evidence = collections.defaultdict(list)
    for name in names:
        if not name.startswith('FUND_REPORTED_HOLDING/'):
            continue
        pf = pq.ParquetFile(verified(name, index, checked))
        candidate = {}
        for batch in pf.iter_batches(batch_size=131072, columns=HOLD_COLS):
            c = batch.column(batch.schema.get_field_index('ISSUER_CUSIP'))
            sub = batch.filter(pc.is_in(c, value_set=cusip_values))
            if sub.num_rows == 0:
                continue
            a = sub.column(sub.schema.get_field_index('ACCESSION_NUMBER'))
            sub = sub.filter(pc.is_in(a, value_set=acc_values))
            for r in sub.to_pylist():
                if eligible(r):
                    continue
                m = submissions.get(r['ACCESSION_NUMBER'])
                if not m:
                    continue
                if r['HOLDING_ID'] in candidate:
                    raise ValueError(f'duplicate identity holding ID {r["HOLDING_ID"]}')
                candidate[r['HOLDING_ID']] = dict(holding_id=r['HOLDING_ID'], accession=r['ACCESSION_NUMBER'],
                     series=series_by_acc[r['ACCESSION_NUMBER']], report_date=m['REPORT_DATE'].isoformat(),
                     filed=m['FILING_DATE'].isoformat(), subtype=m['SUB_TYPE'],
                     cusip=r['ISSUER_CUSIP'], source_partition=name,
                     isin=None, raw_ticker=None, ticker=None)
        if not candidate:
            continue
        id_name = name.replace('FUND_REPORTED_HOLDING/', 'IDENTIFIERS/')
        id_path = verified(id_name, index, checked)
        for batch in filtered_batches(id_path, ID_COLS, set(candidate), 'HOLDING_ID'):
            for r in batch:
                x = candidate[r['HOLDING_ID']]
                if r['IDENTIFIER_ISIN']:
                    value = r['IDENTIFIER_ISIN'].strip().upper()
                    if x['isin'] and x['isin'] != value:
                        x['isin'] = 'CONFLICT'
                    else:
                        x['isin'] = value
                if r['IDENTIFIER_TICKER']:
                    value = r['IDENTIFIER_TICKER'].strip().upper()
                    if x['raw_ticker'] and x['raw_ticker'] != value:
                        x['raw_ticker'] = 'CONFLICT'
                        x['ticker'] = None
                    else:
                        x['raw_ticker'] = value
                        x['ticker'] = ticker(value)
        for x in candidate.values():
            evidence[(x['report_date'], x['cusip'])].append(x)
    results = []
    for h in target_holdings:
        link = lag_lookup[h['ACCESSION_NUMBER']]
        key = (link['lag_period'], h['ISSUER_CUSIP'])
        candidates = [x for x in evidence.get(key, []) if x['filed'] < link['decision_date']]
        value, status, support = identity_resolution(dict(series=link['series'], holding_id=h['HOLDING_ID'],
                                                         cusip=h['ISSUER_CUSIP']), candidates)
        results.append(dict(decision_date=link['decision_date'], flow_period=link['flow_period'],
                            lag_period=link['lag_period'], series=link['series'],
                            lag_accession=h['ACCESSION_NUMBER'], holding_id=h['HOLDING_ID'],
                            cusip=h['ISSUER_CUSIP'], issuer_name=h['ISSUER_NAME'],
                            issuer_title=h['ISSUER_TITLE'], holding_value_usd=str(h['CURRENCY_VALUE']),
                            shares=str(h['BALANCE']), ticker=value, ticker_status=status,
                            isin=next(iter({x['isin'] for x in support if x.get('isin') and isin_valid(x['isin'])}), None)
                                 if len({x['isin'] for x in support if x.get('isin') and isin_valid(x['isin'])}) == 1 else None,
                            evidence_accessions='|'.join(sorted({x['accession'] for x in support})),
                            evidence_filed_dates='|'.join(sorted({x['filed'] for x in support})),
                            evidence_holdings='|'.join(str(x['holding_id']) for x in support),
                            evidence_raw_tickers='|'.join(sorted({x['raw_ticker'] for x in support if x['raw_ticker']})),
                            source_partition=h['source_partition']))
    guard_output_storage()
    expected_outputs = ('fund-flow-selection.csv', 'lag-holdings-identities.parquet',
                        'same-date-identity-evidence.parquet', 'qualification.json')
    if any((OUT / name).exists() for name in expected_outputs):
        raise ValueError('prepared output already exists; inspect prior attempt before rerunning')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'fund-flow-selection.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in selected for k in r)))
        writer.writeheader(); writer.writerows(selected)
    pq.write_table(pa.Table.from_pylist(results), OUT / 'lag-holdings-identities.parquet', compression='zstd')
    evidence_rows = [row for rows_for_key in evidence.values() for row in rows_for_key]
    pq.write_table(pa.Table.from_pylist(evidence_rows), OUT / 'same-date-identity-evidence.parquet', compression='zstd')
    output_hashes = {path.name: sha256_file(path) for path in
                     (OUT / 'fund-flow-selection.csv', OUT / 'lag-holdings-identities.parquet',
                      OUT / 'same-date-identity-evidence.parquet')}
    candidate_values = collections.defaultdict(lambda: Decimal(0))
    for row in results:
        candidate_values[row['ticker_status']] += Decimal(row['holding_value_usd'])
    qualification = dict(decisions=len(decisions), fund_decisions=len(selected), status_counts=dict(collections.Counter(x['status'] for x in selected)),
                         qualified_lag_holdings=len(results), holding_exclusions=dict(exclusions),
                         ticker_status_counts=dict(collections.Counter(x['ticker_status'] for x in results)),
                         holding_value_by_ticker_status_usd={k: str(v) for k, v in candidate_values.items()},
                         ambiguous_series_accessions=ambiguous_series_accessions,
                         conflicting_submission_accessions=len(submission_conflicts),
                         peer_identity_evidence_rows=len(evidence_rows), output_sha256=output_hashes,
                         preparation_script_sha256=sha256_file(Path(__file__)),
                         source_files=checked, filings_path=str(FILINGS), filings_sha256=filings_hash,
                         methods='strict filing date before calendar decision; exact previous report quarters; no outcomes', effects_calculated=0)
    (OUT / 'qualification.json').write_text(json.dumps(qualification, ensure_ascii=False, indent=2))
    print(json.dumps({k: qualification[k] for k in ('decisions', 'fund_decisions', 'status_counts', 'qualified_lag_holdings', 'ticker_status_counts')}, ensure_ascii=False))


def synthetic():
    d = dt.date(2025, 3, 31)
    q = previous_quarter(d); lag = previous_quarter(q)
    assert (q, lag) == (dt.date(2024, 12, 31), dt.date(2024, 9, 30))
    rows = [dict(SERIES_ID='X', REPORT_DATE=q, FILING_DATE=dt.date(2025, 2, 1), SUB_TYPE='NPORT-P', ACCESSION_NUMBER='old'),
            dict(SERIES_ID='X', REPORT_DATE=q, FILING_DATE=dt.date(2025, 3, 30), SUB_TYPE='NPORT-P/A', ACCESSION_NUMBER='new'),
            dict(SERIES_ID='X', REPORT_DATE=q, FILING_DATE=d, SUB_TYPE='NPORT-P/A', ACCESSION_NUMBER='late')]
    assert select_latest(rows, 'X', q, d)[0]['ACCESSION_NUMBER'] == 'new'
    assert select_latest(rows + [{**rows[1], 'ACCESSION_NUMBER': 'another'}], 'X', q, d)[1] == 'same_day_version_ambiguity'
    assert select_latest(rows, 'X', dt.date(2024, 9, 30), d)[1] == 'missing_asof_filing'
    assert cusip_valid('594918104') and not cusip_valid('594918105')
    assert isin_valid('US5949181045') and not isin_valid('US5949181046')
    cur = {f'{kind}_FLOW_MON{i}': Decimal(3 if kind == 'REDEMPTION' else 1) for kind in ('SALES', 'REDEMPTION') for i in (1, 2, 3)}
    cur.update({f'REINVESTMENT_FLOW_MON{i}': Decimal(100) for i in (1, 2, 3)})
    value, error = pressure(cur, {'NET_ASSETS': Decimal(12)})
    assert not error and value['redemption_pressure'] == Decimal('0.5') and value['reinvestment'] == Decimal(300)
    assert pressure({**cur, 'SALES_FLOW_MON1': None}, {'NET_ASSETS': Decimal(12)})[1] == 'missing_flow_or_lag_nav'
    assert pressure({**cur, 'REDEMPTION_FLOW_MON1': Decimal(-1)}, {'NET_ASSETS': Decimal(12)})[1] == 'negative_gross_flow'
    target = dict(series='X', holding_id=1, cusip='594918104')
    own = dict(series='X', holding_id=1, isin='US5949181045', ticker='MSFT', raw_ticker='MSFT')
    peer = dict(series='Y', holding_id=2, isin='US5949181045', ticker='MSFT', raw_ticker='MSFT')
    assert identity_resolution(target, [own, peer])[0] == 'MSFT'
    assert identity_resolution(target, [own])[0] == 'MSFT'
    assert identity_resolution(target, [])[1] == 'ticker_missing'
    assert identity_resolution(target, [own, {**peer, 'ticker': 'WRONG'}])[1] == 'ticker_conflict'
    assert identity_resolution(target, [own, {**peer, 'isin': 'US5949181046'}])[1] == 'isin_conflict_or_invalid'
    assert identity_resolution({**target, 'cusip': '594918105'}, [own])[1] == 'isin_cusip_mismatch'
    print('synthetic preparation checks passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--synthetic', action='store_true')
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if a.synthetic:
        synthetic()
    elif a.run:
        run()
    else:
        p.error('select --synthetic or --run')
