#!/usr/bin/env python3
"""Build a source-qualified annual-account / price common panel; never compute OP or returns."""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import os
import plistlib
import re
import shutil
import subprocess
from collections import defaultdict, deque
from pathlib import Path

import pyarrow.dataset as ds
import pyarrow.parquet as pq


BASE = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/us-op-common-history-20261020/us-op-common-history-20261020-20261020T191922-92db83e55b32/result')
R = Path(__file__).resolve().parent
FIRST_TARGET = (2015, 1)
LAST_TARGET = (2024, 12)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def date_value(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def finite_positive(value):
    try:
        x = float(value)
        return math.isfinite(x) and x > 0
    except (TypeError, ValueError):
        return False


def norm(symbol: str) -> str:
    return re.sub(r'[.-]', '', (symbol or '').strip().upper())


def candidate_aliases(symbol):
    s = (symbol or '').strip().upper()
    out = {(s, 'exact')}
    canonical = norm(s)
    if canonical != s:
        out.add((canonical, 'normalized_dot_hyphen'))
    m = re.fullmatch(r'(.+)-(\d{6})', s)
    if m:
        stem = m.group(1)
        out.add((stem, 'legacy_month_suffix_candidate'))
        if norm(stem) != stem:
            out.add((norm(stem), 'legacy_month_suffix_candidate_normalized'))
    return out


def rename_reachable(start, edges):
    graph = defaultdict(set)
    for old, new in edges:
        graph[old.upper()].add(new.upper())
        graph[new.upper()].add(old.upper())
    seen = {start.upper()}
    q = deque([start.upper()])
    while q:
        for node in graph[q.popleft()]:
            if node not in seen:
                seen.add(node)
                q.append(node)
    return seen - {start.upper()}


def parse_bound(value):
    value = (value or '').strip()
    if value.endswith('*'):
        value = value[:-1]
    return dt.date.fromisoformat(value) if value else None


def temporal_eligible(rec, day):
    added = parse_bound(rec.get('date_added'))
    removed = parse_bound(rec.get('date_removed'))
    created = parse_bound(rec.get('created_at'))
    return (added is None or added <= day) and (removed is None or day < removed) and (created is None or created <= day)


def match_identity(ticker, day, law_by_symbol, edges, window_rules):
    found = {}

    def add(record, mode):
        key = (record.get('symbol', ''), record.get('cik', ''), record.get('name', ''),
               record.get('date_added', ''), record.get('date_removed', ''), record.get('created_at', ''))
        if key not in found:
            found[key] = {'record': record, 'modes': set()}
        found[key]['modes'].add(mode)

    aliases = candidate_aliases(ticker)
    for alias, mode in aliases:
        for record in law_by_symbol.get(norm(alias), []):
            if temporal_eligible(record, day):
                add(record, mode)
    for alias in sorted(rename_reachable(ticker, edges)):
        for record in law_by_symbol.get(norm(alias), []):
            if temporal_eligible(record, day):
                add(record, 'rename')

    active_rules = []
    ym = f'{day.year:04d}-{day.month:02d}'
    for rule in window_rules:
        rule_tickers = rule.get('tickers', [rule.get('ticker', '')])
        if ticker.upper() not in {x.upper() for x in rule_tickers}:
            continue
        if rule['start_month'] <= ym < rule['end_month']:
            active_rules.append(rule)
            # This is a verified-window annotation only; it remains an identity candidate.
            add({'symbol': ticker, 'cik': str(rule['cik']).zfill(10), 'name': rule['issuer'],
                 'sector': '', 'date_added': rule['start_month'] + '-01',
                 'date_removed': rule['end_month'] + '-01', 'created_at': ''},
                'verified_window_annotation')

    evidence = []
    for value in found.values():
        rec = value['record']
        evidence.append({**{k: rec.get(k, '') for k in ('symbol', 'cik', 'name', 'sector', 'date_added', 'date_removed', 'created_at')},
                         'match_modes': sorted(value['modes'])})
    ciks = sorted({str(x['record'].get('cik', '')).lstrip('0') or '0' for x in found.values()
                   if x['record'].get('cik')})
    ciks = [x.zfill(10) for x in ciks]
    modes = sorted(set().union(*(x['modes'] for x in found.values()))) if found else []
    status = 'no_candidate' if not ciks else ('ambiguous' if len(ciks) > 1 else ('exact_candidate' if 'exact' in modes else 'nonexact_candidate'))
    return {'ciks': ciks, 'modes': modes, 'status': status, 'evidence': evidence, 'window_rules': active_rules}


def month_start(y, m):
    return dt.date(y, m, 1)


def shift_month(y, m, delta):
    n = y * 12 + m - 1 + delta
    return n // 12, n % 12 + 1


def months_between(start=(2013, 12), end=(2024, 12)):
    y, m = start
    out = []
    while (y, m) <= end:
        out.append((y, m))
        y, m = shift_month(y, m, 1)
    return out


def anchor_for_target(year, month):
    # A June 30 annual anchor is usable for July through the following June.
    return year if month >= 7 else year - 1


def observed_anchor_cutoff(year, spy_sessions):
    anchor = dt.date(year, 6, 30)
    eligible = [date_value(x) for x in spy_sessions if date_value(x) <= anchor]
    if not eligible:
        raise ValueError(f'no SPY session on/before annual anchor {anchor}')
    observed = max(eligible)
    return {'anchor_calendar_date': anchor, 'observed_anchor_date': observed,
            'accepted_cutoff': observed - dt.timedelta(days=2)}


def choose_latest_filing(records, target_period_year, cutoff):
    eligible = []
    for rec in records:
        if rec.get('form') not in ('10-K', '10-K/A'):
            continue
        period = str(rec.get('period', ''))
        if len(period) < 4 or not period[:4].isdigit() or int(period[:4]) != target_period_year:
            continue
        try:
            accepted_day = dt.date.fromisoformat(str(rec.get('accepted', ''))[:10])
        except ValueError:
            continue
        if accepted_day <= cutoff:
            eligible.append(rec)
    if not eligible:
        return None
    return max(eligible, key=lambda r: (str(r.get('period', '')), str(r.get('accepted', '')), r.get('adsh', '')))


def price_qualification(rows, ticker, day, no_trade, gaps):
    found = rows.get((day, ticker), [])
    reasons = []
    if not found:
        reasons.append('missing_exact_ticker_price')
    if len(found) > 1:
        reasons.append('duplicate_exact_ticker_prices')
    if (ticker, day) in no_trade:
        reasons.append('source_no_trade_day:' + '|'.join(no_trade[(ticker, day)]))
    for last_trade, next_trade in gaps.get(ticker, []):
        if last_trade and next_trade and last_trade < day < next_trade:
            reasons.append(f'source_reported_gap:{last_trade}..{next_trade}')
            break
    if len(found) == 1:
        rec = found[0]
        if not finite_positive(rec.get('close')):
            reasons.append('invalid_close')
        if not finite_positive(rec.get('adj_close')):
            reasons.append('invalid_adj_close')
        if not finite_positive(rec.get('volume')):
            reasons.append('invalid_volume')
        if not str(rec.get('source') or '').strip():
            reasons.append('missing_source_label')
    good = len(found) == 1 and not reasons
    row = found[0] if len(found) == 1 else {}
    return {'qualified': good, 'reason': '|'.join(reasons), 'price': row, 'row_count': len(found)}


def price_status_detail(day, result):
    row = result.get('price') or {}
    return {'date': day.isoformat(), 'qualified': result['qualified'], 'reason': result['reason'],
            'exact_price_row_count': result.get('row_count', 0),
            'close': row.get('close'), 'adj_close': row.get('adj_close'), 'volume': row.get('volume'),
            'source': row.get('source')}


def momentum_window(rows, ticker, endpoint_dates, no_trade, gaps):
    checks = [price_qualification(rows, ticker, day, no_trade, gaps) for day in endpoint_dates]
    qualified = len(endpoint_dates) == 12 and all(x['qualified'] for x in checks)
    value = None
    if qualified:
        value = float(checks[-1]['price']['adj_close']) / float(checks[0]['price']['adj_close']) - 1.0
    return qualified, value, checks


def source_difference_links(differences, ticker, formation_day, target_day, momentum_dates):
    links = []
    for difference in differences:
        if difference.get('ticker') != ticker:
            continue
        try:
            day = dt.date.fromisoformat(difference.get('date', ''))
        except ValueError:
            continue
        roles = []
        if day == formation_day:
            roles.append('formation_quote_date')
        if formation_day < day <= target_day:
            roles.append('formation_to_target_quote_window')
        if momentum_dates and momentum_dates[0] < day <= momentum_dates[-1]:
            roles.append('momentum_adjusted_price_window')
        if roles:
            links.append({**difference, 'roles': '|'.join(roles),
                          'status': 'source_difference_flag_for_review_only'})
    return links


def bound_paths():
    sources = BASE / 'sources'
    return {
        'filings_jsonl': BASE / 'reported-op-qualification-v2' / 'filings.jsonl',
        'membership_intervals': sources / 'membership_intervals.parquet',
        'prices': sources / 'prices.parquet',
        'lawcal_history': sources / 'lawcal-data-components_history.csv',
        'renames': sources / 'renames.csv',
        'no_trade_days': sources / 'no_trade_days.csv',
        'exit_gaps': sources / 'exit_gaps.csv',
        'verified_issuer_rules': R / 'verified-issuer-window-rules.json',
        'price_source_differences': BASE / 'price-source-comparison' / 'differences-over-1pp.csv',
        'identity_runner': R / 'qualify_identity_daily_v2.py',
        'identity_daily_receipt': R / 'identity-daily-receipt-v2.json',
        'reported_op_receipt': R / 'reported-op-qualification-v2-receipt.json',
        'accounting_acceptance': R / 'controller-accounting-acceptance.json',
    }


def check_storage(output_path):
    mount = Path('/Volumes/win+mac通用')
    allowed = {BASE / f'reported-op-common-panel-v{i}' for i in (1, 2, 3, 4, 5)}
    allowed.add(BASE / 'reported-op-common-panel')
    if output_path.resolve() not in {x.resolve() for x in allowed}:
        raise ValueError(f'output must be a new bound sibling of {BASE / "reported-op-common-panel"}')
    if not mount.exists():
        raise RuntimeError(f'external result volume unavailable: {mount}')
    device = os.stat(mount).st_dev
    if device != 16777238:
        raise RuntimeError(f'external device mismatch: expected 16777238, got {device}')
    info = subprocess.run(['diskutil', 'info', '-plist', str(mount)], check=True, capture_output=True).stdout
    volume_uuid = plistlib.loads(info).get('VolumeUUID')
    if volume_uuid != 'DEBA1C85-6059-3865-B50A-A8EE1F80E4D9':
        raise RuntimeError(f'external UUID mismatch: {volume_uuid}')
    free = shutil.disk_usage(mount).free
    if free < 10 * 1024 ** 3:
        raise RuntimeError(f'external free space below 10 GiB reserve: {free}')


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_inputs():
    paths = bound_paths()
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f'{name}: {path}')
    receipt = json.loads(paths['identity_daily_receipt'].read_text())
    assert receipt['status'] == 'data_outputs_validated_manifest_finalized'
    # The core price, membership and lawcal bytes must still match the earlier source qualification job.
    identity_job_path = R / 'identity-daily-job-v2.json'
    identity_job = json.loads(identity_job_path.read_text())
    prior = {str(Path(x['path']).resolve()): x['sha256'] for x in identity_job['input_files']}
    for name in ('membership_intervals', 'prices', 'lawcal_history', 'renames', 'no_trade_days'):
        path = paths[name]
        expected = prior.get(str(path.resolve()))
        if expected is not None:
            actual = sha256(path)
            if actual != expected:
                raise ValueError(f'{name} sha mismatch: expected {expected}, got {actual}')
    inputs = {name: {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size}
              for name, path in paths.items()}
    inputs['identity_daily_job'] = {'path': str(identity_job_path), 'sha256': sha256(identity_job_path), 'bytes': identity_job_path.stat().st_size}
    filings = []
    with paths['filings_jsonl'].open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                filings.append(json.loads(line))
    intervals = pq.read_table(paths['membership_intervals']).to_pylist()
    law = read_csv(paths['lawcal_history'])
    edges = [(r['old'], r['new']) for r in read_csv(paths['renames'])]
    no_trade = defaultdict(list)
    for r in read_csv(paths['no_trade_days']):
        no_trade[(r['ticker'], dt.date.fromisoformat(r['date']))].append(r.get('kind', ''))
    gaps = defaultdict(list)
    for r in read_csv(paths['exit_gaps']):
        try:
            last = dt.date.fromisoformat(r['last_trade']) if r.get('last_trade') else None
            nxt = dt.date.fromisoformat(r['next_trade']) if r.get('next_trade') else None
        except ValueError:
            continue
        gaps[r['ticker']].append((last, nxt))
    rules = json.loads(paths['verified_issuer_rules'].read_text())['rules']
    price_diffs = read_csv(paths['price_source_differences'])
    return paths, inputs, filings, intervals, law, edges, no_trade, gaps, rules, price_diffs


def load_prices(days, tickers):
    path = bound_paths()['prices']
    dataset = ds.dataset(str(path), format='parquet')
    filter_expr = ds.field('ticker').isin(sorted(tickers)) & ds.field('date').isin([dt.datetime.combine(d, dt.time()) for d in sorted(days)])
    table = dataset.to_table(columns=['date', 'ticker', 'close', 'adj_close', 'volume', 'source'], filter=filter_expr)
    result = defaultdict(list)
    for r in table.to_pylist():
        result[(date_value(r['date']), str(r['ticker']))].append(r)
    return result


def build(job_out: Path):
    paths, input_hashes, filings, intervals, law, edges, no_trade, gaps, rules, price_diffs = load_inputs()
    if job_out.exists():
        raise FileExistsError(f'refusing to overwrite output: {job_out}')
    check_storage(job_out)
    job_out.parent.mkdir(parents=True, exist_ok=True)
    law_by_symbol = defaultdict(list)
    for r in law:
        law_by_symbol[norm(r['symbol'])].append(r)

    # Resolve actual monthly price dates from SPY only; all other securities use exact ticker/date rows.
    all_dates = ds.dataset(str(paths['prices']), format='parquet').to_table(columns=['date', 'ticker'], filter=ds.field('ticker') == 'SPY').to_pylist()
    spy_by_month = defaultdict(list)
    for r in all_dates:
        day = date_value(r['date'])
        spy_by_month[(day.year, day.month)].append(day)
    month_dates = {ym: max(days) for ym, days in spy_by_month.items()}
    target_months = [(y, m) for y in range(FIRST_TARGET[0], LAST_TARGET[0] + 1)
                     for m in range(1, 13) if (y, m) >= FIRST_TARGET and (y, m) <= LAST_TARGET]
    # Formation date is the final SPY trading date of the prior calendar month.
    formation_dates = {}
    target_dates = {}
    mom_dates = {}
    for y, m in target_months:
        prior = shift_month(y, m, -1)
        if prior not in month_dates or (y, m) not in month_dates:
            raise ValueError(f'missing SPY endpoint for target {(y,m)} or formation {prior}')
        formation_dates[(y, m)] = month_dates[prior]
        target_dates[(y, m)] = month_dates[(y, m)]
        mom_dates[(y, m)] = [month_dates[shift_month(y, m, k)] for k in range(-13, -1)]

    # Annual June anchor and its information cutoff use the last SPY session <= June 30, less 2 calendar days.
    annual_cutoffs = {}
    for anchor_year in range(2014, 2025):
        annual_cutoffs[anchor_year] = observed_anchor_cutoff(anchor_year, spy_by_month.get((anchor_year, 6), []))

    # Read only prices for the required month-end endpoints and exact original ticker labels.
    tickers = {str(r['ticker']) for r in intervals}
    tickers.add('SPY')
    required_days = set(formation_dates.values()) | set(target_dates.values())
    for dates in mom_dates.values():
        required_days.update(dates)
    price_map = load_prices(required_days, tickers)
    # Ensure SPY endpoints themselves are valid and unique.
    for day in required_days:
        p = price_qualification(price_map, 'SPY', day, no_trade, gaps)
        if not p['qualified']:
            raise ValueError(f'SPY endpoint invalid {day}: {p["reason"]}')

    # Index and select annual filings by CIK/anchor-year. Latest as-of filing is selected before testing qualification.
    filing_by_cik = defaultdict(list)
    for f in filings:
        filing_by_cik[str(f.get('cik', '')).lstrip('0').zfill(10)].append(f)
    selection_cache = {}
    def annual_for(cik, anchor_year):
        key = (cik, anchor_year)
        if key not in selection_cache:
            cutoff = annual_cutoffs[anchor_year]['accepted_cutoff']
            selection_cache[key] = choose_latest_filing(filing_by_cik.get(cik, []), anchor_year - 1, cutoff)
        return selection_cache[key]

    intervals_by_ticker = defaultdict(list)
    for row in intervals:
        ticker = str(row['ticker'])
        start = date_value(row['start']) if row.get('start') else dt.date.min
        end = date_value(row['end']) if row.get('end') else dt.date.max
        intervals_by_ticker[ticker].append((start, end, row))

    all_rows = []
    acct_rows = []
    identity_review = {}
    diff_links = []
    diff_by_ticker = defaultdict(list)
    for d in price_diffs:
        diff_by_ticker[d.get('ticker', '')].append(d)
    coverage = defaultdict(lambda: defaultdict(int))
    eligible_ciks_by_month = defaultdict(set)
    monthly_rows = defaultdict(list)

    for y, m in target_months:
        target_ym = f'{y:04d}-{m:02d}'
        formation_day = formation_dates[(y, m)]
        target_day = target_dates[(y, m)]
        anchor_year = anchor_for_target(y, m)
        cutoff_info = annual_cutoffs[anchor_year]
        # Build active member rows at formation date; interval end is exclusive.
        active = []
        for ticker, values in intervals_by_ticker.items():
            for start, end, raw in values:
                if start <= formation_day < end:
                    active.append((ticker, start, end, raw))
        for ticker, start, end, interval in active:
            coverage[target_ym]['formation_rows'] += 1
            ident = match_identity(ticker, formation_day, law_by_symbol, edges, rules)
            formation_price = price_qualification(price_map, ticker, formation_day, no_trade, gaps)
            target_price = price_qualification(price_map, ticker, target_day, no_trade, gaps)
            mdates = mom_dates[(y, m)]
            mom_ok, mom_value, mom_checks = momentum_window(price_map, ticker, mdates, no_trade, gaps)
            linked_diffs = source_difference_links(diff_by_ticker.get(ticker, []), ticker, formation_day, target_day, mdates)
            for dd in linked_diffs:
                diff_links.append({**dd, 'target_month': target_ym, 'formation_ticker': ticker,
                                   })
            selected_by_cik = []
            for cik in ident['ciks']:
                selected = annual_for(cik, anchor_year)
                if selected is None:
                    selected_by_cik.append({'cik': cik, 'filing_found': False, 'reason': 'no_matching_10k_period_accepted_by_cutoff'})
                    continue
                item = {'cik': cik, 'filing_found': True, 'adsh': selected['adsh'], 'sec_name': selected.get('name', ''),
                        'form': selected.get('form', ''), 'period': selected.get('period', ''), 'fy': selected.get('fy', ''),
                        'accepted': selected.get('accepted', ''), 'sourcequalified': bool(selected.get('sourcequalified')),
                        'automatic_scoring_eligible': bool(selected.get('automatic_scoring_eligible')),
                        'manual_review_required': bool(selected.get('manual_review_required')),
                        'reasons_json': json.dumps(selected.get('reasons', []), ensure_ascii=False, separators=(',', ':')),
                        'input_panel': selected.get('input_panel', ''), 'source_zip': selected.get('source_zip', '')}
                selected_by_cik.append(item)
                law_names = sorted({e['name'] for e in ident['evidence'] if e['cik'].lstrip('0').zfill(10) == cik})
                key = (cik, ticker, str(selected.get('period', ''))[:4])
                review = identity_review.setdefault(key, {'cik': cik, 'ticker': ticker, 'period_year': str(selected.get('period', ''))[:4],
                    'lawcal_names': set(), 'sec_names': set(), 'mapping_methods': set(), 'adshs': set(), 'source_zips': set(), 'status': ident['status']})
                review['lawcal_names'].update(law_names)
                review['sec_names'].add(selected.get('name', ''))
                review['mapping_methods'].update(ident['modes'])
                review['adshs'].add(selected.get('adsh', ''))
                review['source_zips'].add(selected.get('source_zip', ''))
                if selected.get('sourcequalified') and selected.get('automatic_scoring_eligible'):
                    coverage[target_ym]['eligible_report_candidate_rows'] += 1
                    if mom_ok: coverage[target_ym]['eligible_report_and_mom_rows'] += 1
                    if target_price['qualified']: coverage[target_ym]['eligible_report_and_target_quote_rows'] += 1
                    if mom_ok and target_price['qualified']:
                        coverage[target_ym]['eligible_report_mom_and_target_quote_rows'] += 1
                        eligible_ciks_by_month[target_ym].add(cik)
                    acct_rows.append({
                        'target_month': target_ym, 'formation_date': formation_day.isoformat(), 'target_month_end_date': target_day.isoformat(),
                        'ticker': ticker, 'lawcal_symbol': interval.get('ticker', ticker), 'lawcal_names_json': json.dumps(law_names, ensure_ascii=False),
                        'candidate_cik': cik, 'mapping_status': ident['status'], 'mapping_methods': '|'.join(ident['modes']),
                        'mapping_evidence_json': json.dumps(ident['evidence'], ensure_ascii=False, separators=(',', ':')),
                        'verified_window_rule_json': json.dumps(ident['window_rules'], ensure_ascii=False, separators=(',', ':')),
                        'membership_start': interval.get('start').isoformat() if interval.get('start') else '',
                        'membership_end_exclusive': interval.get('end').isoformat() if interval.get('end') else '',
                        'selected_sec_name': selected.get('name', ''), 'adsh': selected['adsh'], 'form': selected.get('form', ''),
                        'period': selected.get('period', ''), 'accepted': selected.get('accepted', ''), 'fy': selected.get('fy', ''),
                        'source_zip': selected.get('source_zip', ''), 'sourcequalified': True, 'automatic_scoring_eligible': True,
                        'mom_endpoint_dates_json': json.dumps([x.isoformat() for x in mdates]), 'mom_all_12_endpoints_qualified': mom_ok,
                        'mom_11_month_adjusted_price_change': mom_value,
                        'mom_endpoint_status_json': json.dumps([price_status_detail(day, q) for day,q in zip(mdates,mom_checks)], ensure_ascii=False, separators=(',', ':')),
                        'formation_quote_detail_json': json.dumps(price_status_detail(formation_day, formation_price), ensure_ascii=False, separators=(',', ':')),
                        'target_month_end_quote_detail_json': json.dumps(price_status_detail(target_day, target_price), ensure_ascii=False, separators=(',', ':')),
                        'formation_quote_qualified': formation_price['qualified'], 'formation_quote_reason': formation_price['reason'],
                        'formation_quote_row_count': len(price_map.get((formation_day, ticker), [])),
                        'formation_quote_present': bool(price_map.get((formation_day, ticker))),
                        'target_month_end_quote_present_and_qualified': target_price['qualified'], 'target_quote_reason': target_price['reason'],
                        'target_month_end_quote_row_count': len(price_map.get((target_day, ticker), [])),
                        'target_month_end_quote_present': bool(price_map.get((target_day, ticker))),
                        'price_source_difference_flag': bool(linked_diffs), 'price_source_difference_json': json.dumps(linked_diffs, ensure_ascii=False, separators=(',', ':')),
                        'index_removal_before_target_month_end': end <= target_day,
                        'future_outcome_calculated': False, 'op_value_calculated': False,
                    })
            row = {
                'target_month': target_ym, 'formation_date': formation_day.isoformat(), 'target_month_end_date': target_day.isoformat(),
                'ticker': ticker, 'original_interval_ticker': interval.get('ticker', ticker),
                'lawcal_original_symbol': '|'.join(sorted({e['symbol'] for e in ident['evidence']})),
                'lawcal_original_name_json': json.dumps(sorted({e['name'] for e in ident['evidence']}), ensure_ascii=False),
                'lawcal_original_cik_json': json.dumps(sorted({e['cik'] for e in ident['evidence']})),
                'membership_start': interval.get('start').isoformat() if interval.get('start') else '',
                'membership_end_exclusive': interval.get('end').isoformat() if interval.get('end') else '',
                'membership_active_on_formation': True, 'identity_status_candidate_only': ident['status'],
                'candidate_ciks_json': json.dumps(ident['ciks']), 'mapping_methods': '|'.join(ident['modes']),
                'identity_evidence_json': json.dumps(ident['evidence'], ensure_ascii=False, separators=(',', ':')),
                'verified_window_rule_json': json.dumps(ident['window_rules'], ensure_ascii=False, separators=(',', ':')),
                'annual_anchor_calendar_date': cutoff_info['anchor_calendar_date'].isoformat(),
                'annual_anchor_observed_spy_date': cutoff_info['observed_anchor_date'].isoformat(),
                'annual_source_cutoff': cutoff_info['accepted_cutoff'].isoformat(), 'annual_period_year': anchor_year - 1,
                'latest_selected_filing_by_cik_json': json.dumps(selected_by_cik, ensure_ascii=False, separators=(',', ':')),
                'mom_endpoint_dates_json': json.dumps([d.isoformat() for d in mdates]), 'mom_all_12_endpoints_qualified': mom_ok,
                'mom_11_month_adjusted_price_change': mom_value,
                'mom_endpoint_status_json': json.dumps([price_status_detail(day, q) for day,q in zip(mdates,mom_checks)], ensure_ascii=False, separators=(',', ':')),
                'formation_quote_detail_json': json.dumps(price_status_detail(formation_day, formation_price), ensure_ascii=False, separators=(',', ':')),
                'target_month_end_quote_detail_json': json.dumps(price_status_detail(target_day, target_price), ensure_ascii=False, separators=(',', ':')),
                'formation_quote_qualified': formation_price['qualified'], 'formation_quote_reason': formation_price['reason'],
                'formation_quote_row_count': len(price_map.get((formation_day, ticker), [])),
                'formation_quote_present': bool(price_map.get((formation_day, ticker))),
                'target_month_end_quote_present_and_qualified': target_price['qualified'], 'target_quote_reason': target_price['reason'],
                'target_month_end_quote_row_count': len(price_map.get((target_day, ticker), [])),
                'target_month_end_quote_present': bool(price_map.get((target_day, ticker))),
                'price_source_difference_flag': bool(linked_diffs), 'price_source_difference_json': json.dumps(linked_diffs, ensure_ascii=False, separators=(',', ':')),
                'index_removal_before_target_month_end': end <= target_day,
                'exit_gap_records_json': json.dumps([{'last_trade': a.isoformat() if a else '', 'next_trade': b.isoformat() if b else ''} for a,b in gaps.get(ticker, [])]),
                'future_outcome_calculated': False, 'op_value_calculated': False,
            }
            all_rows.append(row)
            monthly_rows[target_ym].append(row)
            coverage[target_ym]['unique_tickers'] += 1
            if ident['status'] == 'exact_candidate': coverage[target_ym]['exact_candidate_rows'] += 1
            if ident['status'] == 'ambiguous': coverage[target_ym]['ambiguous_identity_rows'] += 1
            if ident['status'] == 'no_candidate': coverage[target_ym]['no_identity_candidate_rows'] += 1
            if mom_ok: coverage[target_ym]['mom_qualified_rows'] += 1
            if target_price['qualified']: coverage[target_ym]['target_quote_qualified_rows'] += 1
            if not target_price['qualified']: coverage[target_ym]['target_quote_missing_or_rejected_rows'] += 1

    # Verify the fixed 120 target months and expected initial December formation calendar.
    if len(monthly_rows) != 120 or not all(monthly_rows.values()):
        raise AssertionError(f'expected 120 populated target months, got {len(monthly_rows)}')
    if monthly_rows['2015-01'][0]['formation_date'][:7] != '2014-12':
        raise AssertionError('2015-01 must use 2014-12 formation date')

    job_out.mkdir(parents=True, exist_ok=False)
    def write_csv(name, rows):
        p = job_out / name
        if not rows:
            p.write_text('', encoding='utf-8')
            return
        with p.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)

    write_csv('all-formation-rows.csv', all_rows)
    write_csv('accounting-candidate-rows.csv', acct_rows)
    write_csv('identity-review.csv', [{
        'candidate_cik': v['cik'], 'ticker': v['ticker'], 'period_year': v['period_year'],
        'lawcal_names_json': json.dumps(sorted(x for x in v['lawcal_names'] if x), ensure_ascii=False),
        'selected_sec_names_json': json.dumps(sorted(x for x in v['sec_names'] if x), ensure_ascii=False),
        'mapping_methods': '|'.join(sorted(v['mapping_methods'])), 'selected_adshs_json': json.dumps(sorted(x for x in v['adshs'] if x)),
        'source_zips_json': json.dumps(sorted(x for x in v['source_zips'] if x)), 'identity_status_candidate_only': v['status']
    } for _,v in sorted(identity_review.items())])
    write_csv('coverage-by-target-year.csv', [
        {'target_year': year,
         'formation_member_rows': sum(coverage[f'{year}-{m:02d}']['formation_rows'] for m in range(1,13)),
         'unique_tickers_total': sum(coverage[f'{year}-{m:02d}']['unique_tickers'] for m in range(1,13)),
         'identity_exact_candidate_rows': sum(coverage[f'{year}-{m:02d}']['exact_candidate_rows'] for m in range(1,13)),
         'identity_ambiguous_rows': sum(coverage[f'{year}-{m:02d}']['ambiguous_identity_rows'] for m in range(1,13)),
         'identity_missing_candidate_rows': sum(coverage[f'{year}-{m:02d}']['no_identity_candidate_rows'] for m in range(1,13)),
         'eligible_annual_filing_rows': sum(coverage[f'{year}-{m:02d}']['eligible_report_candidate_rows'] for m in range(1,13)),
         'eligible_filing_and_12_mom_endpoint_rows': sum(coverage[f'{year}-{m:02d}']['eligible_report_and_mom_rows'] for m in range(1,13)),
         'eligible_filing_and_target_month_quote_rows': sum(coverage[f'{year}-{m:02d}']['eligible_report_and_target_quote_rows'] for m in range(1,13)),
         'eligible_filing_mom_and_target_quote_rows': sum(coverage[f'{year}-{m:02d}']['eligible_report_mom_and_target_quote_rows'] for m in range(1,13)),
         'unique_eligible_ciks': len(set().union(*(eligible_ciks_by_month[f'{year}-{m:02d}'] for m in range(1,13)))),
         'formation_tickers_with_qualified_12_mom_endpoints': sum(coverage[f'{year}-{m:02d}']['mom_qualified_rows'] for m in range(1,13)),
         'formation_tickers_with_qualified_target_quote': sum(coverage[f'{year}-{m:02d}']['target_quote_qualified_rows'] for m in range(1,13)),
         'formation_tickers_missing_or_rejected_target_quote': sum(coverage[f'{year}-{m:02d}']['target_quote_missing_or_rejected_rows'] for m in range(1,13)),
         'identity_historical_validity': 'pending_manual_review', 'future_returns_calculated': False, 'op_calculated': False}
        for year in range(2015, 2025)])
    linked_by_source = defaultdict(list)
    for link in diff_links:
        linked_by_source[(link.get('date', ''), link.get('ticker', ''))].append(link)
    diff_review_rows = []
    for source_diff in price_diffs:
        links = linked_by_source.get((source_diff.get('date', ''), source_diff.get('ticker', '')), [])
        diff_review_rows.append({**source_diff,
            'linked_target_months_json': json.dumps(sorted({x['target_month'] for x in links})),
            'linked_roles_json': json.dumps(sorted({role for x in links for role in x.get('roles', '').split('|') if role})),
            'link_count': len(links),
            'status': 'linked_to_relevant_price_window_review_only' if links else 'not_linked_to_this_formation_or_momentum_window_but_retained_for_review'})
    write_csv('price-source-difference-review.csv', diff_review_rows)
    summary = {
        'status': 'completed_source_qualification_only', 'target_months': 120,
        'target_period': ['2015-01', '2024-12'], 'formation_calendar_first_month': '2014-12',
        'all_formation_rows': len(all_rows), 'eligible_accounting_candidate_rows': len(acct_rows),
        'identity_review_rows': len(identity_review), 'price_source_difference_link_rows': len(diff_links),
        'price_source_difference_input_rows': len(price_diffs),
        'price_source_difference_rows_linked_to_windows': len({(x.get('date'), x.get('ticker')) for x in diff_links}),
        'candidate_identity_status': 'all exact, rename, suffix and verified-window CIKs remain candidates pending review',
        'annual_anchor_rule': 'calendar June 30, observable anchor is final SPY trading date on or before June 30; accepted cutoff is that observed date minus 2 calendar days; anchor applies July through following June',
        'annual_report_selection': 'latest 10-K/10-K/A rounded period-year anchor_year-1 accepted by cutoff is selected before source qualification; do not fall back if latest filing is unqualified',
        'momentum_window': '12 exact monthly endpoints t-13 through t-2; value is adjusted-price change from first to last only when all 12 endpoints pass',
        'price_rule': 'exact original ticker only; no alias-fill; reject missing/duplicate/nonpositive/nonfinite rows, explicit no-trade dates, and dates strictly inside source-reported last_trade<date<next_trade gaps',
        'future_quote_usage': 'presence/qualification metadata only; no target returns or strategy results',
        'network_requests': 0, 'op_values_calculated': False, 'future_returns_calculated': False,
        'source_selection_and_qualification_are_not_historical_identity_validation': True,
    }
    (job_out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    output_files = []
    expected_files = ['all-formation-rows.csv', 'accounting-candidate-rows.csv', 'identity-review.csv',
                      'coverage-by-target-year.csv', 'price-source-difference-review.csv', 'summary.json']
    for name in expected_files:
        p = job_out / name
        if not p.is_file():
            raise FileNotFoundError(f'expected output missing: {p}')
        rows = None
        if p.suffix == '.csv':
            with p.open(encoding='utf-8', newline='') as f:
                rows = max(0, sum(1 for _ in csv.reader(f)) - 1)
        output_files.append({'path': p.name, 'sha256': sha256(p), 'bytes': p.stat().st_size, 'rows': rows})
    manifest = {'inputs': input_hashes, 'identity_daily_runner_sha256': sha256(paths['identity_runner']),
                'issuer_window_rules_sha256': sha256(paths['verified_issuer_rules']), 'accounting_acceptance_sha256': sha256(paths['accounting_acceptance']),
                'outputs': output_files, 'ignored_nondata_entries': ['._* AppleDouble metadata', '.DS_Store'], 'summary': summary}
    (job_out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True)
    a = p.parse_args()
    out = Path(a.out)
    manifest = build(out)
    print(json.dumps({'output': str(out), 'formation_rows': manifest['summary']['all_formation_rows'],
                      'eligible_accounting_candidate_rows': manifest['summary']['eligible_accounting_candidate_rows'],
                      'output_count': len(manifest['outputs'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
