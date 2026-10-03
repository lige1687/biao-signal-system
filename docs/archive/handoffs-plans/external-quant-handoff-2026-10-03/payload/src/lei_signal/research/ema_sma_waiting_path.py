"""Fixed EMA-leading waiting paths: retrospective price description, never a policy.

Preparation is strictly prefix-only. Future path computation has a separate
explicit permission gate. Exact fractions preserve equality without tolerance.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path

KIND = 'ema_sma_waiting_path'
DEFINITION_REF = 'research.trend.ema20_sma20_waiting_path@1.0.0'
EVALUATOR = 'waiting_path_description@1.0.0'
ROOT = Path(__file__).resolve().parents[3]


def _number(value):
    if isinstance(value, bool):
        raise ValueError('boolean price')
    return Fraction(Decimal(str(value)))


def _bound_json(root, binding):
    raw = (root / binding['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('source hash changed: ' + binding['path'])
    return json.loads(raw, parse_float=Decimal)


def _inputs(payload, contract, root):
    synthetic = payload.get('data_mode') == 'synthetic'
    if payload.get('data_mode') != contract['data']['mode']:
        raise ValueError('payload and contract modes differ')
    if contract['feature']['kind'] != KIND or contract['feature']['definition_ref'] != DEFINITION_REF:
        raise ValueError('fixed waiting-path definition required')
    if contract['feature'].get('warmup', 252) != 252:
        raise ValueError('fixed 252 consecutive qualified quotes required')
    if not synthetic and 'path' in contract['data']:
        raw = (root / contract['data']['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != contract['data']['sha256'] or json.loads(raw) != payload:
            raise ValueError('caller payload differs from bound panel')
    calendar = payload['calendar']
    if not calendar or calendar != sorted(set(calendar)):
        raise ValueError('ordered unique calendar required')
    assets = contract['universe']['assets']
    if len(set(assets)) != len(assets):
        raise ValueError('duplicate asset')
    keyed = {}
    for row in payload['bars']:
        key = (row['asset'], row['date'])
        if key in keyed or row['asset'] not in assets or row['date'] not in calendar:
            raise ValueError('duplicate/out-of-scope bar')
        keyed[key] = row
    nominal = {}
    if synthetic:
        actions = payload.get('economic_actions', [])
        for key, row in keyed.items():
            if row.get('close') is not None:
                nominal[key] = _number(row.get('exact_nominal_close', row['close']))
    else:
        q = contract['data']['qualification']
        manifest = _bound_json(root, {'path': q['manifest_path'], 'sha256': q['manifest_sha256']})
        source = _bound_json(root, manifest['source_qualification'])
        actions = _bound_json(root, manifest['economic_actions'])['included']
        cache = {}
        for asset in assets:
            info = source['products'][asset]
            index = _bound_json(root, {'path': info['row_source_index_path'], 'sha256': info['row_source_index_sha256']})
            bindings = {x['path']: x for x in info['sources']}
            for date in calendar:
                row = keyed.get((asset, date), {})
                if row.get('status') != 'quoted':
                    continue
                values = []
                for ref in index['rows'][date]:
                    path = ref['source_path']
                    if path not in cache:
                        cache[path] = _bound_json(root, bindings[path])
                    data = cache[path].get('data', cache[path])
                    raw = data['sh' + asset[:6]]['day'][ref['source_row_index']]
                    if raw[0] != date:
                        raise ValueError('raw source date mismatch')
                    values.append(_number(raw[2]))
                if not values or len(set(values)) != 1:
                    raise ValueError('raw close overlap mismatch')
                nominal[asset, date] = values[0]
    out = {}
    for asset in assets:
        closes, states = [], []
        previous_nominal = previous_economic = ema = None
        continuous = 0
        for i, date in enumerate(calendar):
            row = keyed.get((asset, date), {})
            price = nominal.get((asset, date))
            known = row.get('status') == 'quoted' and row.get('action_known') is True and price is not None and price > 0
            try:
                oh = [_number(row[x]) for x in ('open', 'high', 'low', 'close')]
                known = known and min(oh) > 0 and oh[2] <= min(oh[0], oh[3]) and oh[1] >= max(oh[0], oh[3])
            except (KeyError, ValueError, TypeError, ArithmeticError):
                known = False
            if not known:
                closes.append(None)
                states.append({'E': None, 'S': None, 'ready_252': False, 'continuous_close': 0})
                continuous = 0
                previous_nominal = previous_economic = ema = None
                continue
            if previous_nominal is None:
                economic = price
            else:
                events = sorted((a for a in actions if a['symbol'] == asset and calendar[i-1] < a['close_effective_date'] <= date), key=lambda a: (a['close_effective_date'], a['event_id']))
                mult, cash = Fraction(1), Fraction(0)
                for action in reversed(events):
                    if action['type'] == 'split':
                        mult *= _number(action['ratio'])
                        cash *= _number(action['ratio'])
                    elif action['type'] == 'cash_dividend':
                        cash += _number(action['cash'])
                    else:
                        raise ValueError('unknown economic action')
                economic = previous_economic * (price * mult + cash) / previous_nominal
            previous_nominal, previous_economic = price, economic
            ema = economic if ema is None else (2 * economic + 19 * ema) / 21
            continuous += 1
            ready = continuous >= 252
            closes.append(economic)
            states.append({'E': economic > ema if ready else None, 'S': economic > closes[i-20] if ready else None,
                           'ready_252': ready, 'continuous_close': continuous})
        out[asset] = (closes, states)
    return out


def prepare_waiting_observations(payload, contract, *, root=None):
    """Return current/past fields only; no future prices, dates or statuses."""
    inputs = _inputs(payload, contract, Path(root) if root else ROOT)
    rows = []
    start, end = contract['question']['period']
    for asset, (_, states) in inputs.items():
        for i, date in enumerate(payload['calendar']):
            if not start <= date <= end:
                continue
            state = states[i]
            prev = states[i-1]['E'] if i else None
            t0 = prev is False and state['E'] is True and state['S'] is False
            rows.append({'id': f'{asset}|{date}', 'asset': asset, 'date': date, 'stratum': f'{asset}|{date[:4]}',
                         **state, 'prev_E': prev, 'is_t0': t0,
                         'features': {'E': state['E'], 'S': state['S'], 'added': int(t0) if state['ready_252'] else None},
                         'feature_reason': None if state['ready_252'] else 'close_unqualified_or_segment_warmup252',
                         'eligible': state['ready_252'], 'episode_id': f'{asset}|{date}' if t0 else None,
                         'label': None, 'y': None, 'label_end': None, 'label_reason': 'not_computed',
                         'tested_condition': t0 if state['ready_252'] else None})
    return {'observations': rows, 'coverage': {'observations': len(rows), 'ready_252': sum(r['ready_252'] for r in rows), 'starts': sum(r['is_t0'] for r in rows)},
            'warnings': ['Historical arrival unknown; price-math description only.']}


def _path(prices):
    if not prices or any(p is None for p in prices):
        return None
    entry = prices[0]
    peak = entry
    drawdown = Fraction(0)
    for price in prices:
        peak = max(peak, price)
        drawdown = max(drawdown, 1 - price / peak)
    return {'intervals': len(prices)-1, 'terminal_return': float(100*(prices[-1]/entry-1)),
            'lowest_close_decline': float(100*max(Fraction(0), 1-min(prices)/entry)),
            'highest_close_rise': float(100*max(Fraction(0), max(prices)/entry-1)),
            'peak_to_trough_decline': float(100*drawdown)}


def _group(rows, expected_assets=None, numeric_rows=None):
    counts = Counter(r['status'] for r in rows)
    assets = sorted(set(expected_assets) if expected_assets is not None else {r['asset'] for r in rows})
    numeric_rows = rows if numeric_rows is None else numeric_rows
    paired_assets = sorted({r['asset'] for r in numeric_rows if r['paired']})
    fields = ('waiting_cost', 'terminal_difference')
    means = {}
    raw_means = {}
    for field in fields:
        raw_values = [r[field] for r in numeric_rows if r[field] is not None]
        raw_means[field] = sum(raw_values)/len(raw_values) if raw_values else None
        asset_means = []
        for asset in assets:
            values = [r[field] for r in numeric_rows if r['asset'] == asset and r[field] is not None]
            if values:
                asset_means.append(sum(values)/len(values))
        means[field] = sum(asset_means)/len(asset_means) if asset_means else None
    return {'starts': len(rows), 'status_counts': dict(counts), 'confirmed': sum(r['confirmation_date'] is not None for r in rows),
            'paired_rows': sum(r['paired'] for r in numeric_rows), 'expected_assets': assets, 'raw_event_means': raw_means,
            'supported_assets': paired_assets, 'missing_assets': sorted(set(assets)-set(paired_assets)),
            'numeric_rows': len(numeric_rows),
            'confirmed_mature_price_rows': sum(r['confirmation_date'] is not None and r['early_path'] is not None for r in numeric_rows),
            'immature_outcomes': sum(r['outcome_reason'] == 'immature' for r in rows), 'asset_count': len(assets), 'equal_asset_means': means,
            'confirmation_rate': sum(r['confirmation_date'] is not None for r in rows)/len(rows) if rows else None,
            'paired_share': sum(r['paired'] for r in numeric_rows)/len(rows) if rows else None,
            'count_scope': 'all starts in group; price numeric scope separately declared',
            'price_path_means': _path_means(numeric_rows, assets),
            'weighting': 'mean within each supported asset, then equal asset mean; no independence assertion'}


def _path_means(rows, expected_assets=None):
    expected_assets = sorted(set(expected_assets) if expected_assets is not None else {r['asset'] for r in rows})
    result = {}
    for name in ('early_path', 'before_waiting_path', 'waiting_path'):
        fields = ('terminal_return', 'lowest_close_decline', 'highest_close_rise', 'peak_to_trough_decline', 'intervals')
        values = {}
        raw_values = {}
        supported = {r['asset'] for r in rows if r[name] is not None}
        for field in fields:
            raw = [r[name][field] for r in rows if r[name] is not None]
            raw_values[field] = sum(raw)/len(raw) if raw else None
            asset_means = []
            for asset in sorted(supported):
                data = [r[name][field] for r in rows if r['asset'] == asset and r[name] is not None]
                asset_means.append(sum(data)/len(data))
            values[field] = sum(asset_means)/len(asset_means) if asset_means else None
        result[name] = {'rows': sum(r[name] is not None for r in rows), 'supported_assets': sorted(supported), 'supported_asset_count': len(supported),
                        'expected_assets': expected_assets, 'missing_assets': sorted(set(expected_assets)-supported),
                        'values': values, 'raw_event_means': raw_values}
    paired = [r for r in rows if r['paired']]
    if paired != rows:
        result['early_paired_path'] = _path_means(paired, expected_assets)['early_path']
    else:
        result['early_paired_path'] = result['early_path']
    return result


def evaluate_waiting_paths(payload, contract, observations=None, *, root=None):
    """Future outcomes allowed only for synthetic or explicitly authorized real data."""
    synthetic = payload.get('data_mode') == 'synthetic' and contract['data']['mode'] == 'synthetic'
    if not synthetic and (contract.get('permissions', {}).get('real_labels') is not True or
                          contract.get('permissions', {}).get('effect_authorized') is not True):
        raise ValueError('real waiting paths require explicit real_labels and effect_authorized authorization')
    prepared = prepare_waiting_observations(payload, contract, root=root)['observations']
    if observations is not None and observations != prepared:
        raise ValueError('supplied observations differ from prefix preparation')
    inputs = _inputs(payload, contract, Path(root) if root else ROOT)
    calendar = payload['calendar']
    positions = {d: i for i, d in enumerate(calendar)}
    ledger = []
    for row in prepared:
        if not row['is_t0']:
            continue
        i = positions[row['date']]
        h = i+21
        closes, states = inputs[row['asset']]
        confirmation = stop = None
        status = 'no_confirmation'
        for j in range(i+1, min(h+1, len(calendar))):
            if states[j]['E'] is None:
                status, stop = 'missing', j
                break
            if states[j]['E'] is False:
                status, stop = 'ema_failed', j
                break
            if states[j]['S'] is True:
                confirmation = j
                status = 'too_late' if j == h else 'confirmed'
                break
        if confirmation is None and stop is None and h >= len(calendar):
            status = 'immature'
        early = _path(closes[i+1:h+1]) if h < len(calendar) else None
        w = confirmation+1 if confirmation is not None else None
        waiting = _path(closes[w:h+1]) if w is not None and w <= h and h < len(calendar) else None
        prewait = _path(closes[i+1:w+1]) if w is not None and w <= h and h < len(calendar) else None
        paired = early is not None and waiting is not None
        ledger.append({'id': row['id'], 'asset': row['asset'], 'date': row['date'], 'stratum': row['stratum'],
                       'status': status, 'status_scope': 'first confirmation or interruption in (t0,H]; no_confirmation means only not confirmed by H',
                       'window_mature': h < len(calendar), 'price_outcome_mature': early is not None,
                       'confirmation_date': calendar[confirmation] if confirmation is not None else None,
                       'waiting_sessions': confirmation-i if confirmation is not None else None,
                       'stop_date': calendar[stop] if stop is not None else None,
                       'terminal_date': calendar[h] if h < len(calendar) else None,
                       'early_entry_date': calendar[i+1] if i+1 < len(calendar) else None,
                       'waiting_entry_date': calendar[w] if w is not None and w < len(calendar) else None,
                       'early_path': early, 'before_waiting_path': prewait, 'waiting_path': waiting,
                       'outcome_reason': 'immature' if h >= len(calendar) else ('missing_price_path' if early is None else None),
                       'paired': paired, 'waiting_cost': float(100*(closes[w]/closes[i+1]-1)) if paired else None,
                       'terminal_difference': waiting['terminal_return']-early['terminal_return'] if paired else None})
    descriptions = []
    assets = contract['universe']['assets']
    groups = [('all', ledger, None, None, assets)]
    groups += [(asset, [r for r in ledger if r['asset'] == asset], None, None, [asset]) for asset in assets]
    phases = [('2022-2024', '2022-01-01', '2024-12-31'), ('2025', '2025-01-01', '2025-12-31'), ('2026H1', '2026-01-01', '2026-06-30')]
    groups += [(phase, [r for r in ledger if lo <= r['date'] <= hi], lo, hi, assets) for phase, lo, hi in phases]
    groups += [(f'{asset}|{phase}', [r for r in ledger if r['asset'] == asset and lo <= r['date'] <= hi], lo, hi, [asset])
               for asset in assets for phase, lo, hi in phases]
    groups += [(f'{asset}|{year}', [r for r in ledger if r['asset'] == asset and r['date'][:4] == year],
                f'{year}-01-01', f'{year}-12-31', [asset])
               for asset in assets for year in sorted({r['date'][:4] for r in ledger})]
    for group, rows, lo, hi, expected in groups:
        contained = rows if lo is None else [r for r in rows if r['terminal_date'] is not None and lo <= r['terminal_date'] <= hi]
        descriptions.append({'group': group, **_group(rows, expected, contained),
                             'numeric_scope': 'all period' if lo is None else 'start and terminal both within group period',
                             'cross_boundary_outcomes': 0 if lo is None else sum(r['terminal_date'] is not None and not lo <= r['terminal_date'] <= hi for r in rows),
                             'not_yet_terminal_outcomes': sum(r['terminal_date'] is None for r in rows)})
    return {'evaluator': EVALUATOR, 'definition_ref': DEFINITION_REF, 'event_ledger': ledger,
            'performance': descriptions, 'descriptions': descriptions,
            'increments': {'status': 'descriptive_only', 'paired_price_difference': _group(ledger, assets),
                           'prediction_increment': 'not_evaluated', 'account_policy': 'not_evaluated'},
            'coverage': _group(ledger, assets), 'fits': 0, 'execution': {'fits': 0}, 'warnings': [], 'predictions': [],
            'period_comparisons': [d for d in descriptions if d['group'] in {'2022-2024', '2025', '2026H1'}],
            'uncertainty': 'Overlapping windows, correlated assets and previously seen history; no independent significance claim.',
            'limitations': ['Historical arrival unknown; action completeness not proved.', 'Exposure differences are price facts, not demonstrated risk avoidance.', 'No costs, cash policy, account return or trade permission.']}


def inspect_waiting_prefix_invariance(payload, contract, *, root=None):
    """Check every prefix with an independent unnormalised EMA numerator.

    This is an algebraic all-prefix check, not N repetitions of source I/O or
    prepare(). Truncation equivalence is additionally covered by synthetic tests.
    The reference uses C[n]*21**n > 19*N[n-1]+2*C[n]*21**(n-1), so no prepared
    EMA state or floating-point output is reused.
    """
    prepared = prepare_waiting_observations(payload, contract, root=root)['observations']
    lookup = {(r['asset'], r['date']): r for r in prepared}
    inputs = _inputs(payload, contract, Path(root) if root else ROOT)
    comparisons = 0
    mismatches = []
    for asset, (closes, _) in inputs.items():
        numerator = None
        denominator = 1
        run = 0
        prev = None
        for i, close in enumerate(closes):
            if close is None:
                numerator = None
                denominator = 1
                run = 0
                e = s = None
            else:
                if numerator is None:
                    numerator = close
                else:
                    numerator = 19*numerator + 2*close*denominator
                    denominator *= 21
                run += 1
                e = close*denominator > numerator if run >= 252 else None
                s = close > closes[i-20] if run >= 252 else None
            row = lookup.get((asset, payload['calendar'][i]))
            if row is not None:
                comparisons += 1
                is_t0 = prev is False and e is True and s is False
                if (row['E'], row['S'], row['prev_E'], row['is_t0']) != (e, s, prev, is_t0):
                    mismatches.append(row['id'])
            prev = e
    return {'ok': not mismatches, 'prefixes_checked': len(payload['calendar']),
            'asset_prefixes_checked': len(payload['calendar'])*len(inputs), 'compared_period_rows': comparisons,
            'mismatches': mismatches, 'method': 'independent unnormalised EMA numerator for every prefix; separate synthetic actual truncation checks',
            'future_outcomes': 0, 'fits': 0}
