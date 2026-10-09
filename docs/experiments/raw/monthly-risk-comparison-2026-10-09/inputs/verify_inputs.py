"""Read-only qualification of saved inputs; no returns, ratios or accounts run.

The optional receipt is restricted to this inputs directory. Historical runner
modules are never imported. Original input bytes and paths are never changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def dates(first, last):
    start, end = date.fromisoformat(first), date.fromisoformat(last)
    return [(start + timedelta(days=i)).isoformat()
            for i in range((end - start).days + 1)]


def previous(day):
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def by_date(values):
    days = [v['date'] for v in values]
    if days != sorted(set(days)):
        raise ValueError('duplicate or unordered dates')
    return {v['date']: v for v in values}


def qualify(manifest):
    checks, problems = [], []

    def check(name, passed, detail=None):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})
        if not passed:
            problems.append(name)

    # This entry is read-only; no output plan, new result directory or download.
    process = subprocess.run(
        ['python3', '-m', 'lei_signal.integrations.gpt_context', '--view', 'storage'],
        cwd=SOURCE_ROOT, env=__import__('os').environ | {'PYTHONPATH': 'src'},
        capture_output=True, text=True, check=True)
    storage = json.loads(process.stdout)
    ext = storage['data']['external']
    check('fixed_external_identity', ext.get('available') and ext.get('identity_ok')
          and ext.get('expected_uuid') == manifest['storage']['required_external_uuid'],
          {'checked_at': storage['data']['checked_at'], 'external': ext})

    bound = {}
    identities = []
    for item in manifest['artifacts']:
        path = Path(item['read_path'])
        # Migrated registered resources must be accessed via the returned read_path.
        resource = item.get('storage_resource_id')
        if resource:
            current = next((r for r in storage['data']['resources'] if r['id'] == resource), None)
            if not current or not current.get('available') or not current.get('read_path'):
                check('resource_available:' + item['id'], False)
                continue
            if not path.is_relative_to(Path(current['read_path'])):
                check('registered_read_path:' + item['id'], False)
                continue
        info = {'id': item['id'], 'read_path': str(path), 'exists': path.is_file(),
                'resolved_path': str(path.resolve()), 'expected_sha256': item['sha256']}
        if item['category'] == 'accepted_external_original_result':
            mount = Path(ext['mount_point'])
            location_ok = path.is_file() and path.resolve().is_relative_to(mount.resolve())
            location_ok = location_ok and path.stat().st_dev == mount.stat().st_dev
            check('external_original_file_device:' + item['id'], location_ok)
            if not location_ok:
                continue
        if path.is_file():
            info.update(bytes=path.stat().st_size, sha256=sha(path))
            good = info['bytes'] == item['bytes'] and info['sha256'] == item['sha256']
        else:
            good = False
        info['matches'] = good
        identities.append(info)
        check('identity:' + item['id'], good, info)
        if good:
            bound[item['id']] = path
    if problems:
        return {'status': 'input_identity_blocked', 'checks': checks,
                'problems': problems, 'identities': identities, 'storage': storage}

    calendar = json.loads(bound['original_calendar'].read_text())['days']
    trading = {d for d, value in calendar.items() if value['is_trading_day']}
    quote_rows = rows(bound['original_nominal_quotes'])
    quotes = by_date(quote_rows)
    reference = by_date(json.loads(bound['original_510300_execution_reference'].read_text()))
    daily = {}
    coverage = {}
    required_start, required_end = '2025-09-25', '2026-06-30'
    required_days = dates(required_start, required_end)
    expected_trading = {d for d in required_days if d in trading}
    check('calendar_natural_day_coverage', all(d in calendar for d in required_days))
    check('nominal_quote_and_reference_dates',
          {d for d in quotes if required_start <= d <= required_end} == expected_trading
          == {d for d in reference if required_start <= d <= required_end})

    for policy in ['all', 'sma', 'b0']:
        for fee in ['base', 'stress']:
            key = f'original_b0_{fee}_daily' if policy == 'b0' else f'original_a_{policy}_{fee}_daily'
            values = rows(bound[key])
            account = by_date(values)
            daily[key] = account
            missing = [d for d in required_days if d not in account]
            check('natural_day_coverage:' + key, not missing, missing)
            failures = []
            for day in required_days:
                if day not in account:
                    continue
                row = account[day]
                try:
                    nums = {k: Decimal(row[k]) for k in ['cash', 'receivable', 'units', 'mark', 'wealth']}
                    bridge = json.loads(row['reconciliation'])
                    valid = all(n.is_finite() for n in nums.values()) and nums['wealth'] > 0
                    valid = valid and min(nums['cash'], nums['receivable'], nums['units']) >= 0
                    valid = valid and nums['wealth'] == nums['cash'] + nums['receivable'] + nums['units'] * nums['mark']
                    valid = valid and all(Decimal(bridge[k]) == 0 for k in
                        ['cash_residual_cny', 'receivable_residual_cny', 'unit_residual', 'wealth_residual_cny'])
                    valid = valid and (row['is_trading_day'] == 'True') == (day in trading)
                    if day in trading:
                        valid = valid and row['raw_close'] != '' and row['mark_basis'] == 'nominal_close'
                        valid = valid and nums['mark'] == Decimal(quotes[day]['close']) == Decimal(row['raw_close'])
                    if not valid:
                        failures.append(day)
                except (KeyError, ValueError, ArithmeticError):
                    failures.append(day)
            check('saved_fields_and_wealth_identity:' + key, not failures, failures)
            coverage[key] = {'file_rows': len(values), 'first_date': values[0]['date'],
                            'last_date': values[-1]['date'], 'required_natural_rows': len(required_days),
                            'required_trading_rows': len(expected_trading), 'columns': list(values[0])}

    months = []
    for cutoff, apply_month in manifest['monthly_cutoffs']:
        selected = sorted(d for d in trading if d <= cutoff)[-63:]
        basic = ['original_a_all_base_daily', 'original_a_sma_base_daily', 'original_b0_base_daily']
        # Missing a latest official day blocks; never reach farther back to hide it.
        missing = {key: [d for d in selected if d not in daily[key] or previous(d) not in daily[key]]
                   for key in basic}
        valid = len(selected) == 63 and not any(missing.values())
        check('63_common_days_and_prior_natural_assets:' + cutoff, valid, missing)
        month_rows = sorted(d for d in expected_trading if d.startswith(apply_month))
        blocked = [{'date': d, 'reason': reference[d]['reason'],
                    'restriction': reference[d]['restriction']}
                   for d in month_rows if reference[d]['restriction'] is not None]
        months.append({'cutoff': cutoff, 'apply_month': apply_month,
                       'available_common_count': len(selected), 'first_return_day': selected[0],
                       'last_return_day': selected[-1], 'first_denominator_natural_day': previous(selected[0]),
                       'selected_trading_dates': selected, 'missing_dates': missing,
                       'all_dates_at_or_before_cutoff': all(d <= cutoff for d in selected),
                       'month_first_trading_day': month_rows[0],
                       'month_first_trading_day_original_restriction': reference[month_rows[0]]['restriction'],
                       'month_restrictions': blocked, 'ratio_or_return_computed': False})

    yearend = {}
    for key, account in daily.items():
        row = account['2025-12-31']
        yearend[key] = {k: row[k] for k in ['cash', 'receivable', 'units', 'mark', 'wealth']}
        yearend[key]['source_row_number_including_header'] = list(account).index('2025-12-31') + 2
        yearend[key]['cumulative_fees_cny'] = json.loads(row['reconciliation'])['fees_cny']
    for fee in ['base', 'stress']:
        all_key, sma_key = f'original_a_all_{fee}_daily', f'original_a_sma_{fee}_daily'
        expected_cash = Decimal(manifest['initial_new_comparison_cash'][fee])
        check('yearend_new_comparison_cash:' + fee,
              all(Decimal(yearend[k]['cash']) == Decimal(yearend[k]['wealth']) == expected_cash
                  and Decimal(yearend[k]['units']) == Decimal(yearend[k]['receivable']) == 0
                  for k in [all_key, sma_key]))
        check('saved_A_2025_identity:' + fee,
              [v for d, v in daily[all_key].items() if d.startswith('2025-')]
              == [v for d, v in daily[sma_key].items() if d.startswith('2025-')])

    mapped = json.loads(bound['original_510300_mapped_actions'].read_text())
    facts = [e for e in json.loads(bound['original_input_actions'].read_text())['events']
             if e['symbol'] == '510300.SS']
    check('510300_action_mapping_identity', len(mapped) == len(facts) and all(
        any(m['event_id'] == f['event_id'] and m['record_date'] == f['record_date']
            and m['ex_date'] == f['ex_date'] and m['pay_date'] == f['payment_date']
            and Decimal(m['cash_per_unit']) == Decimal(f['cash_cny_per_unit']) for f in facts)
        for m in mapped))
    in_period = [e for e in mapped if any('2026-01-01' <= e[k] <= '2026-06-30'
                 for k in ['record_date', 'ex_date', 'pay_date'])]
    check('known_actions_no_cross_boundary', all('2026-01-01' <= e['record_date'] < e['ex_date']
          <= e['pay_date'] <= '2026-06-30' for e in in_period))
    check('saved_2026_ex_day_blocked', all(reference[e['ex_date']]['restriction'] == 'blocked'
          and reference[e['ex_date']]['reason'] == 'reference_unknown' for e in in_period))
    saved_settlements = {}
    for fee in ['base', 'stress']:
        ledger = json.loads(bound[f'original_b0_{fee}_ledger'].read_text())['action_ledger']
        saved_settlements[fee] = [e for e in ledger if '2026-01-01' <= e['date'] <= '2026-06-30']
        check('B0_saved_dividend_phases:' + fee, all(
            [(v['date'], v['type']) for v in saved_settlements[fee] if v['event_id'] == e['event_id']]
            == [(e['record_date'], 'record_right'), (e['ex_date'], 'ex_receivable'),
                (e['pay_date'], 'payment_day_end')] for e in in_period))

    saved_A_ledgers = {}
    for policy in ['all', 'sma']:
        for fee in ['base', 'stress']:
            key = f'original_a_{policy}_{fee}_ledger'
            ledger = json.loads(bound[key].read_text())
            corrected = json.loads(bound[f'accepted_correction_a_{policy}_{fee}_ledger'].read_text())
            check('original_A_ledger_equals_accepted_correction:' + key, ledger == corrected)
            last = daily[f'original_a_{policy}_{fee}_daily']['2026-06-30']
            check('original_A_saved_ledger_terminal_identity:' + key,
                  Decimal(ledger['full']['ending_assets_100k_cny']) == Decimal(last['wealth'])
                  and Decimal(ledger['full']['total_fees_cny'])
                  == Decimal(json.loads(last['reconciliation'])['fees_cny']))
            saved_A_ledgers[key] = {
                'fills_in_H1': [v for v in ledger['fills'] if '2026-01-01' <= v['date'] <= '2026-06-30'],
                'action_ledger_in_H1': [v for v in ledger['action_ledger']
                                       if '2026-01-01' <= v['date'] <= '2026-06-30'],
                'same_JSON_content_as_accepted_correction': ledger == corrected,
                'note': 'Saved observations only; no orders or accounts recomputed.'}

    return {'schema': 'monthly-risk-input-qualification/1',
            'status': 'inputs_ready_with_retrospective_limits' if not problems else 'inputs_blocked',
            'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
            'checks': checks, 'problems': problems, 'identities': identities,
            'storage': storage, 'daily_coverage': coverage,
            'monthly_windows': months, 'yearend_states': yearend,
            'known_2026_actions': in_period, 'saved_B0_settlements': saved_settlements,
            'saved_A_ledgers': saved_A_ledgers,
            'counts': {'new_ratio_calculations': 0, 'account_runs': 0, 'old_experiment_replays': 0,
                       'downloads': 0, 'runner_imports': 0},
            'scope': 'Saved input field/date/amount qualification; no performance or new risk calculation.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=HERE / 'manifest.json')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    result = qualify(manifest)
    if args.receipt:
        receipt = args.receipt.resolve()
        if receipt.parent != HERE or receipt.exists():
            raise ValueError('receipt must be a new file inside this inputs directory')
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'problems': result['problems'],
                      'checks': len(result['checks']), 'receipt': str(args.receipt or '')}, ensure_ascii=False))
    raise SystemExit(0 if not result['problems'] else 1)


if __name__ == '__main__':
    main()
