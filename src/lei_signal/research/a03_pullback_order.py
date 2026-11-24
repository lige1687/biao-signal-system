"""Research proxy for Module A N60 first/later touch, not an A3/A4 entry.

Only same-day completed OHLC and previously seeded moving averages determine
the lifecycle. The pending V2.1 SMA+1 ATR threshold is deliberately unused.
Every declared daily opportunity is retained, including non-touches and gaps.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from . import workflow_inputs as shared
from .a01_index_features import _mean, _Segment, _source_known
from .a01_index_features import _validate as _validate_a01

FEATURE_KIND = 'a03_pullback_order'
WARMUP = 252


@dataclass
class _Trend:
    sequence: int = 0
    active: bool = False
    age: int = 0  # opening day is0; advances once per complete following day
    armed: bool = False
    touches: int = 0

    def clear(self) -> None:
        self.active = False
        self.age = 0
        self.armed = False
        self.touches = 0

    def advance(self, *, close: float, low: float, upper60: float,
                sma120: float, sma_order: bool, ema_order: bool,
                direction60: bool) -> dict:
        """One completed day. Exit precedes entry and touch; no lookahead."""
        outside = low > upper60 and close > upper60
        contact = low <= upper60
        ended = self.active and (not sma_order or close < sma120)
        if ended:
            self.clear()
            return self._view('trend_ended', outside, contact, False, False)
        if not self.active:
            if sma_order and ema_order and direction60:
                self.sequence += 1
                self.active = True
                self.age = 0
                # "after trend opens": the opening day itself cannot arm.
                return self._view('trend_opened', outside, contact, False, False)
            return self._view('no_active_trend', outside, contact, False, False)
        self.age += 1
        if outside:
            self.armed = True
            return self._view('outside_armed', outside, contact, False, False)
        if not contact:
            return self._view('inside_not_contact', outside, contact, False, False)
        if not self.armed:
            return self._view('touch_unarmed_or_consecutive', outside, contact, False, False)
        if not ema_order:
            return self._view('touch_blocked_ema_order', outside, contact, False, False)
        if not direction60:
            return self._view('touch_blocked_60_direction', outside, contact, False, False)
        first = self.touches == 0
        self.touches += 1
        self.armed = False
        return self._view('first_touch' if first else 'later_touch', outside, contact, True, first)

    def _view(self, reason, outside, contact, touch, first):
        return {'reason': reason, 'outside': outside, 'contact_candidate': contact,
                'is_touch': touch, 'is_first_touch': first if touch else None,
                'trend_id': self.sequence if self.active else None,
                'trend_age': self.age if self.active else None,
                'armed_after': self.armed if self.active else False,
                'touch_count_after': self.touches if self.active else 0}


def _contract_inputs(payload, contract):
    """Reuse the A01 raw-OHLC validator with only its feature identity changed."""
    feature = contract.get('feature', {})
    if (feature.get('kind') != FEATURE_KIND or feature.get('lookback') != 60 or
            feature.get('warmup') != WARMUP or feature.get('missing_policy') != 'segmented'):
        raise ValueError('A03 freezes kind=a03_pullback_order, N60 and segmented252 complete OHLC')
    if any(name in feature for name in ('touch_distance_atr', 'ma_touch_distance',
                                        'touch_atr_threshold')):
        raise ValueError('A03 does not use a pending ATR touch threshold')
    if contract.get('question', {}).get('sampling') not in {'daily', 'event'}:
        raise ValueError('A03 full touch opportunities require daily/event sampling')
    delegated = dict(contract)
    delegated['feature'] = {'kind': 'a01_signed_band', 'lookback': 60,
                            'warmup': WARMUP, 'missing_policy': 'segmented'}
    return _validate_a01(payload, delegated)


def _empty(asset_indicator):
    return dict.fromkeys(('ret20', 'vol20', 'slope60_pct', 'drawdown60',
                          'distance60_atr', 'trend_age', 'added', 'lag_return',
                          'existing_state')) | {'asset_indicator': asset_indicator}


def prepare_a03_observations(payload, contract):
    """Retain one row per calendar day and asset in the declared observation period.

    Eligibility means a real, labeled first/later touch. An occurrence is decided
    after its day's close; it does not assert execution, confirmation or profit.
    """
    calendar, assets, by_key = _contract_inputs(payload, contract)
    available_end = max((day for _, day in by_key), default=calendar[0])
    if 'decision_at' in payload:
        decision_day = shared._available(payload['decision_at']).date().isoformat()
        available_end = min(available_end, decision_day)
    selected = shared._selected(calendar, available_end, contract['question'], payload)
    period_start, period_end = contract['question']['period']
    observations, per_asset = [], {}
    for asset_number, asset in enumerate(assets):
        rows = [dict(by_key.get((asset, d), {'asset': asset, 'date': d,
                    'status': 'vendor_missing', 'action_known': False})) for d in calendar]
        label_rows = [r for r in rows if r['date'] <= available_end]
        segment, trend, reasons, target_reasons = _Segment(), _Trend(), Counter(), Counter()
        counts = {'raw': sum((asset, d) in by_key for d in calendar),
                  'calendar_slots': len(calendar), 'indicators': 0,
                  'observations': 0, 'feature_qualified': 0,
                  'labels_evaluable': 0, 'eligible': 0, 'trends_started': 0,
                  'touches': 0, 'first_touches': 0, 'later_touches': 0,
                  'non_touch_opportunities': 0, 'reset_rows': 0}
        for index, row in enumerate(rows):
            day = row['date']
            if day > available_end:
                break
            ready = (row['status'] == 'quoted' and _source_known(row) and
                     all(shared._number(row.get(k)) for k in ('open', 'high', 'low', 'close')))
            if not ready:
                segment = _Segment()
                trend.clear()
                counts['reset_rows'] += 1
                features = _empty(asset_number)
                state = trend._view('missing_real_ohlc_reset', False, False, False, False)
            else:
                segment.push(float(row['close']), float(row['high']), float(row['low']))
                base, _, _ = segment.features(asset_number)
                baseline_keys = ('ret20', 'vol20', 'slope60_pct', 'drawdown60')
                features = {key: base[key] for key in baseline_keys}
                features.update(asset_indicator=asset_number,
                                distance60_atr=base['added'], trend_age=None,
                                added=None, lag_return=base['ret20'],
                                existing_state=base['existing_state'])
                indicator_ready = (len(segment.closes) >= WARMUP and
                                   segment.atr is not None and segment.atr > 0 and
                                   base['added'] is not None)
                if indicator_ready:
                    closes = segment.closes
                    sma60, sma120 = _mean(closes[-60:]), _mean(closes[-120:])
                    state = trend.advance(
                        close=closes[-1], low=float(row['low']),
                        upper60=max(sma60, segment.emas[60]),
                        sma120=sma120, sma_order=bool(base['sma_order']),
                        ema_order=bool(base['ema_order']),
                        direction60=closes[-1] > closes[-61])
                    features['trend_age'] = state['trend_age']
                    counts['trends_started'] += int(state['reason'] == 'trend_opened')
                else:
                    trend.clear()
                    state = trend._view('indicator_not_ready', False, False, False, False)
            indicator_ready = (ready and len(segment.closes) >= WARMUP and
                               features['distance60_atr'] is not None)
            counts['indicators'] += int(indicator_ready)
            if day not in selected or not period_start <= day <= period_end:
                continue
            counts['observations'] += 1
            if state['is_touch']:
                counts['touches'] += 1
                counts['first_touches'] += int(state['is_first_touch'])
                counts['later_touches'] += int(not state['is_first_touch'])
                features['added'] = int(state['is_first_touch'])
            else:
                counts['non_touch_opportunities'] += 1
            # The same shared target semantics and actual available end apply
            # to touched and untouched opportunities. No survivor-only mother.
            y, label_end, target_reason = shared._label(label_rows, index, contract['target'])
            target_reasons[target_reason or 'evaluable'] += 1
            counts['labels_evaluable'] += int(y is not None)
            feature_qualified = bool(state['is_touch'])
            counts['feature_qualified'] += int(feature_qualified)
            eligible = feature_qualified and y is not None
            counts['eligible'] += int(eligible)
            reason = (None if eligible else target_reason if state['is_touch']
                      else 'not_touch:' + state['reason'])
            reasons[reason or 'eligible'] += 1
            observations.append({
                'id': asset + '|' + day, 'asset': asset, 'date': day,
                'stratum': asset + '|' + day[:4], 'features': features,
                'eligible': eligible, 'y': y, 'label_end': label_end,
                'label_reason': reason, 'target_label_reason': target_reason,
                'tested_condition': bool(state['is_first_touch']) if state['is_touch'] else None,
                'event_stage': 'touched' if state['is_touch'] else None,
                'touch_order': ('first' if state['is_first_touch'] else
                                'later' if state['is_touch'] else None),
                'touch_reason': state['reason'], 'outside': state['outside'],
                'contact_candidate': state['contact_candidate'],
                'armed_after': state['armed_after'], 'trend_id': state['trend_id'],
                'trend_age': state['trend_age'],
                'touch_count_after': state['touch_count_after'],
                'continuous_real_ohlc': len(segment.closes),
                'price_proxy_note': 'historical supplier index price; not executable fill'})
        counts['reasons'] = dict(reasons)
        counts['target_reasons'] = dict(target_reasons)
        per_asset[asset] = counts
    keys = ('raw', 'calendar_slots', 'indicators', 'observations',
            'feature_qualified', 'labels_evaluable', 'eligible',
            'trends_started', 'touches', 'first_touches', 'later_touches',
            'non_touch_opportunities', 'reset_rows')
    coverage = {key: sum(value[key] for value in per_asset.values()) for key in keys}
    coverage.update(per_asset=per_asset, common_comparison=None,
                    common_comparison_reason='not evaluated by event input builder')
    warnings = [
        'A03仅为Module A首次/后续触碰的日线研究代理；不含A3/A4入场确认。',
        '触碰使用60日双均线组上沿和当日低价，不使用仍待确认的V2.1一倍ATR触碰阈值。',
        '所有预定每日机会、未触碰和未成熟标签均保留；缺价会重置连续252日报价与触碰状态。',
    ]
    return {'observations': observations, 'coverage': coverage,
            'warnings': warnings}
