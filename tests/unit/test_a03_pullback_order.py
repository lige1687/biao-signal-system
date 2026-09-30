"""Hand-built price paths only; no historical A03 outcomes are read."""
from copy import deepcopy
from unittest.mock import patch

import pandas as pd
import pytest

from lei_signal.research import workflow_inputs
from lei_signal.research.a03_pullback_order import _Trend, prepare_a03_observations


def fixture(size=285):
    calendar = pd.bdate_range('2020-01-01', periods=size).strftime('%Y-%m-%d').tolist()
    bars = []
    for i, day in enumerate(calendar):
        close = float(100 + i)
        bars.append({'asset': 'synthetic-A', 'date': day, 'status': 'quoted',
                     'open': close, 'high': close + 1, 'low': close - 1,
                     'close': close, 'action_known': True, 'open_actionable': True})
    payload = {'calendar': calendar, 'bars': bars, 'data_mode': 'synthetic'}
    contract = {
        'universe': {'assets': ['synthetic-A']},
        'question': {'sampling': 'daily', 'period': [calendar[0], calendar[-1]]},
        'feature': {'kind': 'a03_pullback_order', 'lookback': 60, 'warmup': 252,
                    'missing_policy': 'segmented'},
        'target': {'kind': 'forward_return', 'unit': 'percentage_point',
                   'start_offset': 1, 'end_offset': 2, 'entry_field': 'close'},
    }
    return payload, contract


def rows_by_date(result):
    return {r['date']: r for r in result['observations']}


def touch_path(size=285):
    payload, contract = fixture(size)
    # The linear price path has SMA60=EMA60=close-29.5 and ATR20=2.
    # A low of300 therefore crosses the group; the close stays above lag60.
    for i in (253, 254, 256):
        payload['bars'][i]['low'] = 300.
    return payload, contract


def test_first_later_touch_and_consecutive_day_deduplication():
    payload, contract = touch_path()
    result = prepare_a03_observations(payload, contract)
    d = payload['calendar']
    rows = rows_by_date(result)
    assert rows[d[250]]['touch_reason'] == 'indicator_not_ready'
    assert rows[d[250]]['continuous_real_ohlc'] == 251
    assert rows[d[251]]['touch_reason'] == 'trend_opened'
    assert rows[d[251]]['trend_age'] == 0
    assert rows[d[252]]['touch_reason'] == 'outside_armed'
    first = rows[d[253]]
    assert first['touch_reason'] == 'first_touch'
    assert first['touch_order'] == 'first'
    assert first['tested_condition'] is True
    assert first['features']['added'] == 1
    assert first['features']['trend_age'] == 2
    # Crossing far through the band raises same-day TR and thus ATR20.
    assert first['features']['distance60_atr'] == pytest.approx(29.5 / ((19 * 2 + 2 * 54) / 21))
    assert first['eligible']
    assert rows[d[254]]['touch_reason'] == 'touch_unarmed_or_consecutive'
    assert not rows[d[254]]['eligible']
    assert rows[d[255]]['touch_reason'] == 'outside_armed'
    later = rows[d[256]]
    assert later['touch_reason'] == 'later_touch'
    assert later['touch_order'] == 'later'
    assert later['tested_condition'] is False
    assert later['features']['added'] == 0
    assert later['trend_id'] == first['trend_id'] == 1
    assert result['coverage']['touches'] == 2
    assert result['coverage']['first_touches'] == 1
    assert result['coverage']['later_touches'] == 1
    assert result['coverage']['observations'] == size_of(payload)
    assert (result['coverage']['touches'] +
            result['coverage']['non_touch_opportunities']) == size_of(payload)
    reasons = result['coverage']['per_asset']['synthetic-A']['reasons']
    assert sum(reasons.values()) == size_of(payload)


def size_of(payload):
    return len(payload['calendar'])


def test_touch_depth_is_not_the_unconfirmed_one_atr_band():
    payload, contract = fixture()
    # Day252 opens trend, day253 at low=upper+0.5 (within +1 ATR) is
    # outside, not touch. A later deep cross of the line counts.
    payload['bars'][252]['low'] = payload['bars'][252]['close'] - 29.
    payload['bars'][253]['low'] = 250.
    rows = rows_by_date(prepare_a03_observations(payload, contract))
    d = payload['calendar']
    assert rows[d[252]]['touch_reason'] == 'outside_armed'
    assert rows[d[253]]['touch_reason'] == 'first_touch'
    assert rows[d[253]]['features']['added'] == 1


def test_trend_ending_and_reopening_restart_first_touch_order():
    trend = _Trend()
    same = dict(close=200., low=180., upper60=190., sma120=170.,
                sma_order=True, ema_order=True, direction60=True)
    assert trend.advance(**same)['reason'] == 'trend_opened'
    assert trend.advance(**dict(same, low=195.))['reason'] == 'outside_armed'
    assert trend.advance(**same)['reason'] == 'first_touch'
    assert trend.advance(**dict(same, sma_order=False))['reason'] == 'trend_ended'
    assert trend.advance(**same)['trend_id'] == 2
    assert trend.advance(**dict(same, low=195.))['reason'] == 'outside_armed'
    assert trend.advance(**same)['reason'] == 'first_touch'
    assert trend.touches == 1
    assert trend.advance(**dict(same, close=160.))['reason'] == 'trend_ended'


def test_opening_uses_only_three_frozen_conditions_not_an_added_price_gate():
    trend = _Trend()
    row = trend.advance(close=169., low=160., upper60=190., sma120=170.,
                        sma_order=True, ema_order=True, direction60=True)
    assert row['reason'] == 'trend_opened'
    # The separately frozen end rule is checked on the next completed day.
    ended = trend.advance(close=169., low=160., upper60=190., sma120=170.,
                          sma_order=True, ema_order=True, direction60=True)
    assert ended['reason'] == 'trend_ended'


def test_ema_or_60_direction_departure_blocks_touch_without_resetting_trend():
    trend = _Trend(sequence=1, active=True, age=5, armed=True, touches=1)
    base = dict(close=200., low=180., upper60=190., sma120=170.,
                sma_order=True, ema_order=True, direction60=True)
    row = trend.advance(**dict(base, ema_order=False))
    assert row['reason'] == 'touch_blocked_ema_order' and row['armed_after']
    row = trend.advance(**dict(base, direction60=False))
    assert row['reason'] == 'touch_blocked_60_direction' and row['armed_after']
    row = trend.advance(**base)
    assert row['reason'] == 'later_touch' and row['trend_id'] == 1
    assert row['touch_count_after'] == 2


@pytest.mark.parametrize('gap', ['missing_row', 'nonquoted', 'partial_ohlc'])
def test_real_ohlc_gap_resets_252_warmup_and_touch_lifecycle(gap):
    payload, contract = touch_path(515)
    payload['bars'][511]['low'] = 500.
    if gap == 'missing_row':
        del payload['bars'][257]
    elif gap == 'nonquoted':
        payload['bars'][257].update(status='vendor_missing', open=None,
                                    high=None, low=None, close=None)
    else:
        payload['bars'][257]['low'] = None
    d = payload['calendar']
    rows = rows_by_date(prepare_a03_observations(payload, contract))
    assert rows[d[256]]['touch_order'] == 'later'
    assert rows[d[257]]['touch_reason'] == 'missing_real_ohlc_reset'
    assert rows[d[257]]['continuous_real_ohlc'] == 0
    assert rows[d[258]]['continuous_real_ohlc'] == 1
    assert rows[d[508]]['continuous_real_ohlc'] == 251
    assert rows[d[508]]['touch_reason'] == 'indicator_not_ready'
    assert rows[d[509]]['continuous_real_ohlc'] == 252
    assert rows[d[509]]['touch_reason'] == 'trend_opened'
    assert rows[d[510]]['touch_reason'] == 'outside_armed'
    assert rows[d[511]]['touch_reason'] == 'first_touch'
    assert rows[d[511]]['trend_id'] == 2


def test_prefix_state_is_unchanged_by_future_quotes_or_label_maturity():
    payload, contract = touch_path()
    full = rows_by_date(prepare_a03_observations(payload, contract))
    d = payload['calendar']
    for cutoff_index in (250, 251, 252, 253, 254, 255, 256, 270):
        cutoff = d[cutoff_index]
        short_payload = dict(payload, bars=[r for r in payload['bars'] if r['date'] <= cutoff])
        partial = rows_by_date(prepare_a03_observations(short_payload, contract))
        for day, row in partial.items():
            reference = full[day]
            for field in ('features', 'touch_reason', 'tested_condition', 'touch_order',
                          'trend_id', 'trend_age', 'armed_after', 'continuous_real_ohlc'):
                assert row[field] == reference[field]
    assert partial[cutoff]['target_label_reason'] == 'immature_label'
    assert full[cutoff]['target_label_reason'] is None


def test_full_non_touch_and_immature_ledger_including_period_filter():
    payload, contract = touch_path()
    contract['question']['period'] = [payload['calendar'][250], payload['calendar'][-1]]
    with patch.object(workflow_inputs, '_label', wraps=workflow_inputs._label) as label:
        result = prepare_a03_observations(payload, contract)
    rows = result['observations']
    assert len(rows) == len(payload['calendar']) - 250
    assert label.call_count == len(rows)
    assert result['coverage']['raw'] == len(payload['calendar'])
    assert result['coverage']['touches'] == 2
    assert result['coverage']['non_touch_opportunities'] == len(rows) - 2
    assert rows[-1]['target_label_reason'] == 'immature_label'
    assert rows[-2]['target_label_reason'] == 'immature_label'
    assert result['coverage']['per_asset']['synthetic-A']['target_reasons']['immature_label'] == 2
    assert all(r['label_reason'] or r['eligible'] for r in rows)
    assert all(r['target_label_reason'] is not None or r['y'] is not None for r in rows)


def test_bad_contract_is_rejected_without_downgrading_to_periodic_or_short_warmup():
    payload, contract = fixture()
    bad = deepcopy(contract)
    bad['feature']['warmup'] = 120
    with pytest.raises(ValueError, match='252'):
        prepare_a03_observations(payload, bad)
    bad = deepcopy(contract)
    bad['question']['sampling'] = 'periodic'
    bad['question']['frequency'] = 'weekly'
    with pytest.raises(ValueError, match='daily/event'):
        prepare_a03_observations(payload, bad)
    bad = deepcopy(contract)
    bad['feature']['touch_distance_atr'] = 1
    with pytest.raises(ValueError, match='pending ATR'):
        prepare_a03_observations(payload, bad)
