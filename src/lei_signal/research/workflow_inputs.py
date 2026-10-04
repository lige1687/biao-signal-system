"""Causal research demonstration inputs; historical identity is checked by the root.

Prices must already share a certified economic price basis. This builder does
not adjust actions, fill quotes, or certify source/snapshot identity. Offsets
are declared calendar sessions; real_quote changes only the feature clock.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time
import math
from numbers import Real

STATUSES = {'quoted', 'halt', 'vendor_missing', 'not_listed', 'terminated', 'action_unknown'}
TARGETS = {'forward_return', 'mae', 'mfe', 'max_drawdown', 'up', 'downside_event'}


def _date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('date must be YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('date must be YYYY-MM-DD')
    return parsed


def _available(value):
    if not isinstance(value, str):
        raise ValueError('availability time must be an ISO date/time')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid availability time') from exc


def _number(value):
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _after(left, right):
    if (left.tzinfo is None) != (right.tzinfo is None):
        raise ValueError('availability and decision timezone must be consistent')
    return left > right


def _integer(value, name, minimum):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _selected(calendar, available_end, question, payload):
    sampling = question.get('sampling', 'daily')
    if sampling in {'daily', 'event'}:
        return {d for d in calendar if d <= available_end}
    if sampling != 'periodic':
        raise ValueError('builder supports daily, event or periodic sampling')
    frequency = question.get('frequency')
    if frequency not in {'weekly', 'monthly'}:
        raise ValueError('periodic sampling requires weekly or monthly frequency')
    explicit = set(payload.get('completed_period_ends', []))
    for d in explicit:
        _date(d)
        if d not in calendar:
            raise ValueError('completed period end is outside calendar')
    keys = [(_date(d).isocalendar()[:2] if frequency == 'weekly' else d[:7]) for d in calendar]
    selected = set()
    for i, d in enumerate(calendar):
        # A following period in the frozen calendar proves the preceding end.
        complete = i + 1 < len(calendar) and keys[i] != keys[i + 1]
        if d in explicit:
            if i + 1 < len(calendar) and keys[i] == keys[i + 1]:
                raise ValueError('declared period end contradicts calendar')
            complete = True
        if complete and d <= available_end:
            selected.add(d)
    return selected


def _label(rows, i, target):
    a, b = i + target['start_offset'], i + target['end_offset']
    if b >= len(rows):
        return None, None, 'immature_label'
    end = rows[b]['date']
    entry = rows[a]
    field = target['entry_field']
    if entry['status'] != 'quoted':
        return None, end, 'entry_' + entry['status']
    if not _number(entry.get(field)):
        return None, end, 'entry_' + field + '_missing'
    if field == 'open' and entry.get('open_actionable') is not True:
        return None, end, 'entry_open_not_actionable'
    path = rows[a:b + 1]
    provider_price = target.get('price_measure') == 'provider_index_price'
    if any(r['status'] == 'action_unknown' or not (
            r.get('action_known') is True or
            (provider_price and r.get('provider_price_known') is True
             and r.get('price_series') == 'provider_index_price')) for r in path):
        return None, end, 'action_unknown'
    kind = target['kind']
    price = float(entry[field])
    if kind in {'forward_return', 'up', 'downside_event'}:
        endpoint = rows[b]
        if endpoint['status'] != 'quoted':
            return None, end, 'endpoint_' + endpoint['status']
        if not _number(endpoint.get('close')):
            return None, end, 'endpoint_close_missing'
        if any(r['status'] in {'not_listed', 'terminated'} for r in path):
            return None, end, 'path_identity_gap'
        value = 100 * (endpoint['close'] / price - 1)
        if kind == 'up':
            value = float(value > target.get('threshold', 0))
        elif kind == 'downside_event':
            value = float(value <= -abs(target['threshold']))
        return value, end, None
    path_field = target.get('path_field', 'close')
    price_path = path[1:] if kind == 'mae' and path_field == 'low' and field == 'close' else path
    for r in path:
        if r['status'] not in {'quoted', 'halt'}:
            return None, end, 'path_' + r['status']
        if r['status'] == 'quoted' and path_field == 'close' and not _number(r.get('close')):
            return None, end, 'path_close_missing'
    if path_field == 'low':
        for r in price_path:
            if r['status'] == 'quoted':
                for required in ('low', 'high'):
                    if not _number(r.get(required)):
                        return None, end, 'path_' + required + '_missing'
    prices = [price] + [float(r[path_field]) for r in price_path if r['status'] == 'quoted']
    if kind == 'mae':
        value = max(0., 100 * (1 - min(prices) / price))
    elif kind == 'mfe':
        value = max(0., 100 * (max(prices) / price - 1))
    else:
        peak, value = prices[0], 0.
        for p in prices:
            peak = max(peak, p)
            value = max(value, 100 * (1 - p / peak))
    return value, end, None


def prepare_observations(payload, contract):
    """Build all declared opportunities, including legal excluded observations.

    SMA distance and lag return use percentages; binary decline is 0/1. Unknown
    gaps reset feature state. Confirmed halts keep state only under real_quote.
    Segmented warmup counts consecutive real quotes and is always explicit.
    MAE/MDD are positive losses. Default paths use actual closing trades (known
    halts have no trade). MAE may explicitly use daily lows; close entry excludes
    entry-day lows because they occurred before entry. MDD only supports closes,
    as daily high/low order is unknown. Fixed endpoint returns require a quote.
    """
    if contract['feature']['kind'] == 'color_continuous_workflow':
        from .color_continuous_workflow import prepare_observations as prepare_continuous
        return prepare_continuous(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'bull_gray_origin_information':
        from lei_signal.research.bull_gray_origin_information import prepare_observations as prepare_gray
        return prepare_gray(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'color_event_information':
        from lei_signal.research.color_event_information import prepare_observations as prepare_color_event
        return prepare_color_event(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'weekly_color_information':
        from lei_signal.research.weekly_color_information import prepare_observations as prepare_weekly
        return prepare_weekly(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] in {'ema_direction_persistence_information',
                                       'bull_green_transition_information'}:
        from lei_signal.research.technical_persistence_information import prepare_observations as prepare_technical
        return prepare_technical(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] in {'slope_change_risk_information', 'ema_only_wait_age_risk_information'}:
        from lei_signal.research.technical_daily_risk_information import prepare_risk_observations
        return prepare_risk_observations(payload, contract)
    if contract['feature']['kind'] == 'ema_only_wait_age_information':
        from lei_signal.research.ema_only_wait_age_information import prepare_sequence_observations
        return prepare_sequence_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'ema_sma_waiting_path':
        from lei_signal.research.ema_sma_waiting_path import prepare_waiting_observations
        return prepare_waiting_observations(payload, contract)
    if contract['feature']['kind'] == 'prior_top_dual_break_information':
        from lei_signal.research.prior_top_dual_break_information import prepare_combination_observations
        return prepare_combination_observations(payload, contract, compute_labels=(payload.get('data_mode') == 'synthetic' or contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'pullback_layer_change_information':
        from lei_signal.research.pullback_layer_change_information import prepare_pullback_observations
        return prepare_pullback_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'slope_change_information':
        from lei_signal.research.trend_slope_change_information import prepare_slope_observations
        return prepare_slope_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'green_black_state60_information':
        from lei_signal.research.green_black_state_information import prepare_state_observations
        return prepare_state_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'tsfresh_price_information':
        from lei_signal.research.tsfresh_price_information import prepare_tsfresh_observations
        return prepare_tsfresh_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'simple_top_invalidation_information':
        from lei_signal.research.top_invalidation_information import prepare_invalidation_observations
        return prepare_invalidation_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'double_ma_order_information':
        from lei_signal.research.double_ma_order_information import prepare_double_order_observations
        return prepare_double_order_observations(payload, contract, compute_labels=contract.get('permissions', {}).get('real_labels') is True)
    if contract['feature']['kind'] == 'volume_anomaly_information':
        from lei_signal.research.volume_information import prepare_volume_observations
        return prepare_volume_observations(payload, contract)
    if contract['feature']['kind'] == 'key_fluctuation_information':
        from lei_signal.research.key_fluctuation_information import prepare_key_observations
        return prepare_key_observations(payload, contract, compute_labels=contract.get('permissions', {}).get('real_labels') is True or payload.get('data_mode') == 'synthetic')
    if contract['feature']['kind'] == 'profile_overhead_information':
        from lei_signal.research.profile_information import prepare_profile_observations
        return prepare_profile_observations(payload, contract, compute_labels=(
            payload.get('data_mode') == 'synthetic' or
            contract.get('permissions', {}).get('real_labels') is True))
    if contract['feature']['kind'] == 'simple_top3_information':
        from lei_signal.research.top_structure_information import prepare_top_observations
        return prepare_top_observations(payload, contract)
    if contract['feature']['kind'] == 'future_deduction_box_information':
        from lei_signal.research.deduction_box_information import prepare_deduction_observations
        return prepare_deduction_observations(payload, contract)
    if contract['feature']['kind'] == 'ma_cluster_information':
        from lei_signal.research.ma_cluster_information import prepare_ma_cluster_observations
        return prepare_ma_cluster_observations(payload, contract)
    if contract['feature']['kind'] == 'a01_signed_band':
        from lei_signal.research.a01_index_features import prepare_a01_observations
        return prepare_a01_observations(payload, contract)
    if contract['feature']['kind'] == 'space_prior_target':
        from lei_signal.research.space_prior_target import prepare_space_observations
        return prepare_space_observations(payload, contract)
    if contract['feature']['kind'] == 'a03_pullback_order':
        from lei_signal.research.a03_pullback_order import prepare_a03_observations
        return prepare_a03_observations(payload, contract)
    calendar = payload['calendar']
    if not isinstance(calendar, list) or not calendar:
        raise ValueError('calendar must be a nonempty list')
    for d in calendar:
        _date(d)
    if calendar != sorted(set(calendar)):
        raise ValueError('calendar must be ordered and unique')
    assets = contract['universe']['assets']
    if not assets or len(set(assets)) != len(assets):
        raise ValueError('assets must be nonempty and unique')
    feature, target = contract['feature'], contract['target']
    n = _integer(feature['lookback'], 'lookback', 1)
    warmup = _integer(feature['warmup'], 'warmup', 1)
    if feature['kind'] not in {'sma_distance', 'decline_event'}:
        raise ValueError('unsupported feature kind')
    if feature['missing_policy'] not in {'real_quote', 'segmented'}:
        raise ValueError('explicit missing policy required')
    _integer(target['start_offset'], 'start_offset', 1)
    _integer(target['end_offset'], 'end_offset', 2)
    if target['end_offset'] <= target['start_offset']:
        raise ValueError('end_offset must be after start_offset')
    if target['kind'] not in TARGETS or target['entry_field'] not in {'close', 'open'}:
        raise ValueError('unsupported target')
    if target.get('path_field', 'close') not in {'close', 'low'}:
        raise ValueError('path_field must be close or low')
    if target.get('path_field', 'close') == 'low' and target['kind'] != 'mae':
        raise ValueError('only MAE supports low paths; max_drawdown uses close')
    expected_unit = 'probability' if target['kind'] in {'up', 'downside_event'} else 'percentage_point'
    if target['unit'] != expected_unit:
        raise ValueError('target unit disagrees with target kind')
    if target['kind'] == 'downside_event' and not _number(target.get('threshold')):
        raise ValueError('downside threshold must be positive')
    by_key = {}
    for record in payload['bars']:
        d = record['date']; _date(d)
        if d not in calendar:
            raise ValueError('bar date outside declared calendar')
        if record['status'] not in STATUSES:
            raise ValueError('unknown quote status')
        if record['asset'] not in assets:
            raise ValueError('bar asset outside declared universe')
        key = record['asset'], d
        if key in by_key:
            raise ValueError('duplicate asset/date')
        if 'decision_at' in record:
            decision = _available(record['decision_at'])
            if record['status'] == 'quoted' and record.get('close') is not None:
                if decision.date() < _date(d) or (decision.date() == _date(d) and decision.time() < time(15)):
                    raise ValueError('daily close feature is unavailable before the session close')
        for name in ('feature_available_at', 'period_end'):
            if name in record:
                available = _available(record[name])
                if available.date() > _date(d):
                    raise ValueError(f'{name} is after observation date')
                decision = record.get('decision_at', payload.get('decision_at'))
                if decision and _after(available, _available(decision)):
                    raise ValueError(f'{name} is after decision_at')
        if record['status'] == 'quoted':
            for field in ('open', 'high', 'low', 'close'):
                if record.get(field) is not None and not _number(record[field]):
                    raise ValueError(f'quoted {field} must be a positive finite price or null')
            low, high = record.get('low'), record.get('high')
            if low is not None and high is not None and low > high:
                raise ValueError('OHLC low exceeds high')
            for field in ('open', 'close'):
                value = record.get(field)
                if value is not None and ((low is not None and value < low) or (high is not None and value > high)):
                    raise ValueError('OHLC open/close is outside low/high')
        if record['status'] != 'quoted' and any(record.get(f) is not None for f in ('open', 'high', 'low', 'close')):
            raise ValueError('nonquoted rows must preserve null prices')
        by_key[key] = record
    available_end = max((d for _,d in by_key), default=calendar[0])
    if 'decision_at' in payload:
        available_end = min(available_end, _available(payload['decision_at']).date().isoformat())
    selected = _selected(calendar, available_end, contract.get('question', {}), payload)
    observations, per_asset, warnings = [], {}, []
    for asset in assets:
        rows = [dict(by_key.get((asset,d), {'asset': asset, 'date': d,
                    'status': 'vendor_missing', 'action_known': False})) for d in calendar]
        # Future rows do not mature labels merely because the calendar is complete.
        label_rows = [r for r in rows if r['date'] <= available_end]
        counts = {'raw': sum((asset,d) in by_key for d in calendar),
                  'calendar_slots': len(calendar), 'indicators': 0, 'observations': 0,
                  'feature_qualified': 0, 'labels_evaluable': 0, 'eligible': 0}
        history = []
        reasons = Counter()
        for i, r in enumerate(rows):
            if r['date'] > available_end:
                break
            feats = {'lag_return': None, 'added': None, 'existing_state': None}
            status = r['status']
            ready = status == 'quoted' and r.get('action_known') is True and _number(r.get('close'))
            if ready:
                history.append(float(r['close']))
                if len(history) >= max(warmup, n+1):
                    lag = 100 * (history[-1] / history[-n-1] - 1)
                    added = (100 * (history[-1] / (sum(history[-n:])/n) - 1)
                             if feature['kind']=='sma_distance' else float(history[-1]<history[-2]))
                    feats = {'lag_return': lag, 'added': added,
                             'existing_state': int(lag>0)-int(lag<0)}
                    counts['indicators'] += 1
            elif not (status == 'halt' and r.get('action_known') is True and feature['missing_policy']=='real_quote'):
                history.clear()
            if r['date'] not in selected:
                continue
            y, label_end, reason = _label(label_rows, i, target)
            counts['observations'] += 1
            feature_ready = feats['added'] is not None
            counts['feature_qualified'] += int(feature_ready)
            counts['labels_evaluable'] += int(y is not None)
            eligible = feature_ready and y is not None
            counts['eligible'] += int(eligible)
            if reason is None and not feature_ready:
                reason = 'feature_not_ready:' + status
            reasons[reason or 'eligible'] += 1
            observations.append({'id': asset+'|'+r['date'], 'asset': asset, 'date': r['date'],
                'stratum': asset+'|'+r['date'][:4], 'features': feats, 'eligible': eligible,
                'y': y, 'label_end': label_end, 'label_reason': reason,
                'tested_condition': (bool(feats['added']) if feature['kind']=='decline_event' and feature_ready else None)})
        counts['reasons'] = dict(reasons)
        per_asset[asset] = counts
        if not counts['raw']:
            warnings.append(f'{asset}: no quoted input records; declared pool retained')
    if any(r['status']=='halt' for r in by_key.values()):
        warnings.append('Known halts have no filled price; real_quote features use quote count, labels use calendar offsets; path losses use actual closing trades.')
    warnings.append('Demonstration proxy only; historical identity, calendar authority and economic action scale require root qualification.')
    coverage = {key: sum(v[key] for v in per_asset.values()) for key in
                ('raw','calendar_slots','indicators','observations','feature_qualified','labels_evaluable','eligible')}
    coverage.update(per_asset=per_asset, common_comparison=None,
                    common_comparison_reason='not evaluated by input builder')
    return {'observations': observations, 'coverage': coverage, 'warnings': warnings}


def inspect_prefix_invariance(payload, contract):
    """Compare actual full and truncated builder features, keeping frozen calendar.

    Label maturity is intentionally excluded: it depends on future evidence.
    Sampling remains fixed by the original calendar, never by future quotes.
    """
    full = {r['id']: r for r in prepare_observations(payload, contract)['observations']}
    checked, mismatches = 0, []
    decision_end = (_available(payload['decision_at']).date().isoformat()
                    if 'decision_at' in payload else '9999-12-31')
    for cutoff in sorted({r['date'] for r in payload['bars'] if r['date'] <= decision_end}):
        prefix = dict(payload, bars=[r for r in payload['bars'] if r['date'] <= cutoff])
        for r in prepare_observations(prefix, contract)['observations']:
            checked += 1
            original = full.get(r['id'])
            if original is None or any(original[k] != r[k] for k in ('features','tested_condition')):
                mismatches.append({'id': r['id'], 'prefix_end': cutoff})
    return {'passed': not mismatches, 'comparisons': checked, 'mismatches': mismatches}
