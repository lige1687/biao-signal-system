"""Exact A01 N60 price-state adapter, research.a01.signed_band@2.0.0.

Provider index prices are not economic wealth prices or executable fills. Every
gap restarts a continuous real-OHLC segment. Labels and sampling remain owned by
the shared input builder; this module performs no evaluation or fitting.
"""
from __future__ import annotations

from collections import Counter
import math
import statistics

from . import workflow_inputs as shared

DEFINITION_REF = "research.a01.signed_band@2.0.0"
PERIODS = (20, 60, 120)
WARMUP = 252


def _mean(values):
    return math.fsum(values) / len(values)


def _sign(value):
    return int(value > 0) - int(value < 0)


def _distance(close, sma, ema, atr):
    lower, upper = min(sma, ema), max(sma, ema)
    distance = ((close - upper) / atr if close > upper else
                (close - lower) / atr if close < lower else 0.)
    group = ('deep_below' if distance < -1 else 'slightly_below' if distance < 0
             else 'inside' if distance == 0 else 'slightly_above' if distance <= 1
             else 'far_above')
    return distance, group, float(lower <= close <= upper)


class _Segment:
    """Seed each EMA on its first N closes; seed ATR on first 20 known TRs."""
    def __init__(self):
        self.closes = []
        self.emas = {n: None for n in PERIODS}
        self.tr_seed = []
        self.atr = None
        self.last_tr = None

    def push(self, close, high, low):
        previous = self.closes[-1] if self.closes else None
        self.closes.append(close)
        size = len(self.closes)
        for n in PERIODS:
            if size == n:
                self.emas[n] = _mean(self.closes[:n])
            elif size > n:
                alpha = 2 / (n + 1)
                self.emas[n] = alpha * close + (1 - alpha) * self.emas[n]
        self.last_tr = None if previous is None else max(high - low, abs(high - previous), abs(low - previous))
        if self.last_tr is not None:
            if self.atr is None:
                self.tr_seed.append(self.last_tr)
                if len(self.tr_seed) == 20:
                    self.atr = _mean(self.tr_seed)
            else:
                self.atr = (2 / 21) * self.last_tr + (19 / 21) * self.atr

    def features(self, asset_indicator):
        c = self.closes
        result = {f'ret{n}': (100 * (c[-1] / c[-n-1] - 1) if len(c) > n else None) for n in PERIODS}
        result['vol20'] = (statistics.stdev([math.log(c[i] / c[i-1]) for i in range(len(c)-20, len(c))]) * math.sqrt(252) * 100 if len(c) >= 21 else None)
        result['slope60_pct'] = (100 * (_mean(c[-60:]) / _mean(c[-65:-5]) - 1) if len(c) >= 65 else None)
        result['drawdown60'] = 100 * (c[-1] / max(c[-60:]) - 1) if len(c) >= 60 else None
        for n in PERIODS:
            result[f'sma_direction{n}'] = _sign(c[-1] - c[-n-1]) if len(c) > n else None
            result[f'ema_direction{n}'] = _sign(c[-1] - self.emas[n]) if self.emas[n] is not None else None
        result['sma_order'] = float(_mean(c[-20:]) > _mean(c[-60:]) > _mean(c[-120:])) if len(c) >= 120 else None
        result['ema_order'] = float(self.emas[20] > self.emas[60] > self.emas[120]) if self.emas[120] is not None else None
        result['asset_indicator'] = asset_indicator
        result.update(added=None, added_squared=None, inside=None)
        group = None
        if len(c) >= 60 and self.emas[60] is not None and self.atr is not None and self.atr > 0:
            distance, group, inside = _distance(c[-1], _mean(c[-60:]), self.emas[60], self.atr)
            result.update(added=distance, added_squared=distance * distance, inside=inside)
        # Explicit compatibility aliases; they add no independent information.
        result['lag_return'] = result['ret20']
        result['existing_state'] = _sign(result['ret20']) if result['ret20'] is not None else None
        trend = len(c) >= 65 and _mean(c[-60:]) > _mean(c[-65:-5])
        return result, group, trend


def _empty_features(asset_indicator):
    keys = [f'ret{n}' for n in PERIODS] + ['vol20', 'slope60_pct', 'drawdown60']
    keys += [f'{name}_direction{n}' for name in ('sma', 'ema') for n in PERIODS]
    keys += ['sma_order', 'ema_order', 'added', 'added_squared', 'inside', 'lag_return', 'existing_state']
    return {**dict.fromkeys(keys), 'asset_indicator': asset_indicator}


def _source_known(row):
    return (row.get('action_known') is True or
            (row.get('provider_price_known') is True and row.get('price_series') == 'provider_index_price'))


def _validate(payload, contract):
    calendar = payload['calendar']
    if not isinstance(calendar, list) or not calendar:
        raise ValueError('calendar must be a nonempty ordered list')
    for d in calendar:
        shared._date(d)
    if calendar != sorted(set(calendar)):
        raise ValueError('calendar must be ordered and unique')
    assets = contract['universe']['assets']
    if not isinstance(assets, list) or not assets or len(set(assets)) != len(assets):
        raise ValueError('universe assets must be nonempty and unique')
    feature = contract['feature']
    if feature.get('kind') != 'a01_signed_band' or feature.get('lookback') != 60 or feature.get('warmup') != WARMUP or feature.get('missing_policy') != 'segmented':
        raise ValueError('A01 adapter freezes kind=a01_signed_band, N60, continuous real OHLC252 segmented policy')
    if feature.get('definition_ref', DEFINITION_REF) != DEFINITION_REF:
        raise ValueError('A01 adapter definition version differs')
    period = contract.get('question', {}).get('period')
    if not isinstance(period, list) or len(period) != 2:
        raise ValueError('A01 question.period must declare observation start/end')
    for d in period:
        shared._date(d)
    if period[0] > period[1]:
        raise ValueError('A01 observation period ends before it starts')
    target = contract['target']
    for name, minimum in [('start_offset', 1), ('end_offset', 2)]:
        value = target[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(name + ' must be a positive calendar offset')
    if target['end_offset'] <= target['start_offset']:
        raise ValueError('end_offset must be after start_offset')
    if target['kind'] not in shared.TARGETS or target['entry_field'] not in ('close', 'open'):
        raise ValueError('unsupported label target')
    expected_unit = 'probability' if target['kind'] in ('up', 'downside_event') else 'percentage_point'
    if target['unit'] != expected_unit:
        raise ValueError('target unit disagrees with target kind')
    if target.get('path_field', 'close') not in ('close', 'low') or (target.get('path_field') == 'low' and target['kind'] != 'mae'):
        raise ValueError('only MAE supports low paths')
    if target['kind'] == 'downside_event' and not shared._number(target.get('threshold')):
        raise ValueError('downside threshold must be positive')
    by_key = {}
    dates = set(calendar)
    for row in payload['bars']:
        shared._date(row['date'])
        if row['date'] not in dates or row['asset'] not in assets:
            raise ValueError('bar is outside declared calendar/universe')
        if row['status'] not in shared.STATUSES:
            raise ValueError('unknown quote status')
        key = row['asset'], row['date']
        if key in by_key:
            raise ValueError('duplicate asset/date')
        for name in ('decision_at', 'feature_available_at', 'period_end'):
            if name in row:
                parsed = shared._available(row[name])
                if name in ('feature_available_at', 'period_end') and parsed.date() > shared._date(row['date']):
                    raise ValueError('feature is available after observation date')
                if name == 'decision_at' and row['status'] == 'quoted' and row.get('close') is not None:
                    if parsed.date() < shared._date(row['date']) or (parsed.date() == shared._date(row['date']) and parsed.hour < 15):
                        raise ValueError('daily close unavailable before session close')
        for name in ('feature_available_at', 'period_end'):
            if name not in row or not row.get('decision_at', payload.get('decision_at')):
                continue
            available = shared._available(row[name])
            decision = shared._available(row.get('decision_at', payload.get('decision_at')))
            if (available.tzinfo is None) != (decision.tzinfo is None):
                raise ValueError('availability timezone differs from decision')
            if available > decision:
                raise ValueError('feature is available after decision_at')
        if row['status'] == 'quoted':
            for field in ('open', 'high', 'low', 'close'):
                if row.get(field) is not None and not shared._number(row[field]):
                    raise ValueError('quoted OHLC must be positive finite values or null')
            low, high = row.get('low'), row.get('high')
            if low is not None and high is not None and low > high:
                raise ValueError('low exceeds high')
            for field in ('open', 'close'):
                v = row.get(field)
                if v is not None and ((low is not None and v < low) or (high is not None and v > high)):
                    raise ValueError('open/close outside high-low')
        elif any(row.get(field) is not None for field in ('open', 'high', 'low', 'close')):
            raise ValueError('nonquoted rows must have null OHLC')
        by_key[key] = row
    return calendar, assets, by_key


def prepare_a01_observations(payload, contract):
    """Build exact price-state observations; every scheduled opportunity stays.

    Mathematical features may exist before252 quotes, but eligibility requires
    the frozen252 quote policy, positive ATR20, SMA60(t)>SMA60(t-5) and a legal
    shared label. None of the five distances is an eligibility filter.
    """
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if 'decision_at' in payload:
        available_end = min(available_end, shared._available(payload['decision_at']).date().isoformat())
    selected = shared._selected(calendar, available_end, contract.get('question', {}), payload)
    observation_start, observation_end = contract['question']['period']
    observations, per_asset = [], {}
    for number, asset in enumerate(assets):
        rows = [dict(by_key.get((asset, d), {'asset': asset, 'date': d, 'status': 'vendor_missing', 'action_known': False})) for d in calendar]
        label_rows = [r for r in rows if r['date'] <= available_end]
        counts = {'raw': sum((asset, d) in by_key for d in calendar), 'calendar_slots': len(calendar), 'indicators': 0, 'observations': 0, 'feature_qualified': 0, 'labels_evaluable': 0, 'eligible': 0, 'trend_up': 0, 'reset_rows': 0}
        segment, reasons = _Segment(), Counter()
        for i, row in enumerate(rows):
            if row['date'] > available_end:
                break
            ready = row['status'] == 'quoted' and _source_known(row) and all(shared._number(row.get(field)) for field in ('open', 'high', 'low', 'close'))
            if ready:
                segment.push(float(row['close']), float(row['high']), float(row['low']))
                features, group, trend = segment.features(number)
            else:
                segment = _Segment()
                features, group, trend = _empty_features(number), None, False
                counts['reset_rows'] += 1
            indicator_ready = len(segment.closes) >= WARMUP and features['added'] is not None
            counts['indicators'] += int(indicator_ready)
            counts['trend_up'] += int(indicator_ready and trend)
            if row['date'] not in selected or not observation_start <= row['date'] <= observation_end:
                continue
            # Index-offset labels must use only actual available rows, not a
            # future end carried in the frozen full calendar.
            y, label_end, label_reason = shared._label(label_rows, i, contract['target'])
            counts['observations'] += 1
            counts['labels_evaluable'] += int(y is not None)
            feature_qualified = indicator_ready and trend
            counts['feature_qualified'] += int(feature_qualified)
            eligible = feature_qualified and y is not None
            counts['eligible'] += int(eligible)
            if not indicator_ready:
                exclusion = 'feature_not_ready:' + (row['status'] if row['status'] != 'quoted' else 'incomplete_ohlc_or_price_basis' if not ready else 'continuous252_or_positive_atr20')
            elif not trend:
                exclusion = 'sma60_not_up'
            else:
                exclusion = label_reason
            reasons[exclusion or 'eligible'] += 1
            observations.append({'id': asset + '|' + row['date'], 'asset': asset, 'date': row['date'], 'stratum': asset + '|' + row['date'][:4], 'features': features, 'eligible': eligible, 'y': y, 'label_end': label_end, 'label_reason': exclusion, 'target_label_reason': label_reason, 'feature_reason': None if feature_qualified else exclusion, 'tested_condition': None, 'distance_group': group, 'continuous_real_ohlc': len(segment.closes), 'definition_ref': DEFINITION_REF})
        counts['reasons'] = dict(reasons)
        per_asset[asset] = counts
    coverage = {key: sum(value[key] for value in per_asset.values()) for key in ('raw', 'calendar_slots', 'indicators', 'observations', 'feature_qualified', 'labels_evaluable', 'eligible', 'trend_up', 'reset_rows')}
    coverage.update(per_asset=per_asset, common_comparison=None, common_comparison_reason='not evaluated by input builder', definition_ref=DEFINITION_REF)
    warnings = ['采用A01的60日双均线距离、先以20个有效真实波幅均值为种子再递推的ATR20，以及连续252日真实开高低收才合格的规则；不按距离预先筛选。', '供应商指数价格仅用于回溯价格变化，不能当ETF分红财富、官方全收益或可成交价格；收盘后观察时间约定不证明历史到达时间。', '不足连续252个真实报价日时，部分数学特征可能已可计算，但观察仍被排除。标签复用共享输入工具，只使用实际已到达的报价末日。']
    return {'observations': observations, 'coverage': coverage, 'warnings': warnings}
