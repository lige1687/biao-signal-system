"""Synthetic hand examples only; no historical A01 labels/effects are computed."""
from copy import deepcopy
import math
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.a01_index_features import (
    DEFINITION_REF, _distance, _Segment, prepare_a01_observations,
)


def fixture(size=270, descending=False, sampling='daily'):
    calendar = pd.bdate_range('2020-01-01', periods=size).strftime('%Y-%m-%d').tolist()
    bars = []
    for i, day in enumerate(calendar):
        close = 100 + i if not descending else 1000 - i
        bars.append({'asset': 'synthetic-A', 'date': day, 'status': 'quoted', 'close': close,
                     'open': close, 'high': close + 1, 'low': close - 1,
                     'action_known': True, 'open_actionable': True})
    payload = {'calendar': calendar, 'bars': bars, 'data_mode': 'synthetic'}
    contract = {'universe': {'assets': ['synthetic-A']},
                'feature': {'kind': 'a01_signed_band', 'lookback': 60, 'warmup': 252,
                            'missing_policy': 'segmented', 'definition_ref': DEFINITION_REF},
                'question': {'sampling': sampling, 'period': [calendar[0], calendar[-1]]},
                'target': {'kind': 'forward_return', 'unit': 'percentage_point',
                           'start_offset': 1, 'end_offset': 2, 'entry_field': 'close'}}
    if sampling == 'periodic':
        contract['question']['frequency'] = 'weekly'
    return payload, contract


def by_day(result):
    return {r['date']: r for r in result['observations']}


def test_exact_ema_seeds_first_tr_unknown_and_atr20_not_atr14():
    state = _Segment()
    state.push(100., 101., 99.)
    assert state.last_tr is None
    assert state.tr_seed == [] and state.atr is None
    for close in range(101, 120):
        state.push(float(close), close + 1., close - 1.)
    assert state.emas[20] == 109.5  # first20 close arithmetic mean
    assert state.atr is None  # only19 known true ranges, even after14
    state.push(120., 121., 119.)
    assert state.emas[20] == pytest.approx(110.5)
    assert state.atr == 2  # exactly first20 valid TRs at raw row21
    state.push(140., 141., 139.)
    assert state.last_tr == 21
    assert state.atr == pytest.approx((19*2 + 2*21)/21)
    state = _Segment()
    for close in range(100, 220):
        state.push(float(close), close + 1., close - 1.)
    assert state.emas[60] == pytest.approx(189.5)
    assert state.emas[120] == 159.5


@pytest.mark.parametrize('close,expected,group', [(7, -1.5, 'deep_below'), (8, -1, 'slightly_below'), (9, -.5, 'slightly_below'), (10, 0, 'inside'), (11, 0, 'inside'), (12, 0, 'inside'), (13, .5, 'slightly_above'), (14, 1, 'slightly_above'), (15, 1.5, 'far_above')])
def test_signed_band_geometry_boundaries_and_line_order(close, expected, group):
    # lower10/upper12, ATR2, independent of which algorithm is upper.
    assert _distance(close, 10, 12, 2) == (expected, group, float(10 <= close <= 12))
    assert _distance(close, 12, 10, 2) == _distance(close, 10, 12, 2)


def test_hand_features_returns_logvol_direction_and_252_qualification():
    payload, contract = fixture()
    result = prepare_a01_observations(payload, contract)
    day = payload['calendar'][251]
    r = by_day(result)[day]
    f = r['features']
    close = np.arange(100., 370.)
    for n in [20, 60, 120]:
        assert f[f'ret{n}'] == pytest.approx(100*(close[251]/close[251-n]-1))
        assert f[f'sma_direction{n}'] == 1
        assert f[f'ema_direction{n}'] == 1
    logs = np.log(close[232:252] / close[231:251])
    assert len(logs) == 20
    assert f['vol20'] == pytest.approx(np.std(logs, ddof=1)*math.sqrt(252)*100)
    assert f['slope60_pct'] == pytest.approx(100*(np.mean(close[192:252])/np.mean(close[187:247])-1))
    assert f['drawdown60'] == 0
    assert f['sma_order'] == f['ema_order'] == 1
    assert f['added'] == pytest.approx(29.5/2)  # SMA=EMA on linear prices
    assert f['added_squared'] == pytest.approx(f['added']**2)
    assert f['inside'] == 0 and r['distance_group'] == 'far_above'
    assert f['asset_indicator'] == 0
    assert r['continuous_real_ohlc'] == 252 and r['eligible']
    assert r['y'] == pytest.approx(100*(353/352-1))
    assert r['tested_condition'] is None
    before = by_day(result)[payload['calendar'][250]]
    assert not before['eligible'] and before['continuous_real_ohlc'] == 251
    assert 'continuous252' in before['feature_reason']


def test_down_direction_not_up_excluded_but_observation_and_label_preserved():
    payload, contract = fixture(descending=True)
    result = prepare_a01_observations(payload, contract)
    row = result['observations'][251]
    assert row['features']['sma_direction60'] == row['features']['ema_direction60'] == -1
    assert row['features']['sma_order'] == row['features']['ema_order'] == 0
    assert row['features']['added'] < -1 and row['distance_group'] == 'deep_below'
    assert row['label_reason'] == 'sma60_not_up' and not row['eligible']
    assert row['y'] is not None
    assert row['target_label_reason'] is None


@pytest.mark.parametrize('status', ['halt', 'vendor_missing', 'not_listed', 'terminated', 'action_unknown'])
def test_all_nonquoted_statuses_reset_full_252_segment(status):
    payload, contract = fixture(530)
    gap = payload['bars'][252]
    gap.update(status=status, open=None, high=None, low=None, close=None)
    result = by_day(prepare_a01_observations(payload, contract))
    before = result[payload['calendar'][251]]
    assert before['continuous_real_ohlc'] == 252 and before['feature_reason'] is None
    assert not before['eligible']  # next-day label entry is the nonquoted gap
    assert before['target_label_reason'] == 'entry_' + status
    assert result[payload['calendar'][252]]['continuous_real_ohlc'] == 0
    assert result[payload['calendar'][253]]['continuous_real_ohlc'] == 1
    assert not result[payload['calendar'][503]]['eligible']
    assert result[payload['calendar'][504]]['eligible']


def test_missing_calendar_row_and_partial_ohlc_reset_no_forward_fill():
    payload, contract = fixture(530)
    del payload['bars'][252]
    result = by_day(prepare_a01_observations(payload, contract))
    assert result[payload['calendar'][252]]['continuous_real_ohlc'] == 0
    assert 'vendor_missing' in result[payload['calendar'][252]]['feature_reason']
    assert result[payload['calendar'][504]]['eligible']
    payload, contract = fixture(530)
    payload['bars'][252]['low'] = None
    result = by_day(prepare_a01_observations(payload, contract))
    assert result[payload['calendar'][252]]['continuous_real_ohlc'] == 0
    assert result[payload['calendar'][504]]['eligible']


def test_synthetic_second_asset_indicator_and_scale_invariance():
    payload, contract = fixture()
    contract['universe']['assets'].append('synthetic-B')
    second = deepcopy(payload['bars'])
    for row in second:
        row['asset'] = 'synthetic-B'
        for field in ['open', 'high', 'low', 'close']:
            row[field] *= 7
    payload['bars'].extend(second)
    rows = prepare_a01_observations(payload, contract)['observations']
    a = [r for r in rows if r['asset'] == 'synthetic-A'][251]
    b = [r for r in rows if r['asset'] == 'synthetic-B'][251]
    assert a['features']['asset_indicator'] == 0 and b['features']['asset_indicator'] == 1
    for name, value in a['features'].items():
        if name != 'asset_indicator' and value is not None:
            assert b['features'][name] == pytest.approx(value, abs=1e-10)
    assert a['y'] == pytest.approx(b['y'])


def test_prefix_preserves_features_not_future_label_maturity():
    payload, contract = fixture(285, sampling='periodic')
    full = by_day(prepare_a01_observations(payload, contract))
    for cutoff in [payload['calendar'][60], payload['calendar'][250], payload['calendar'][259], payload['calendar'][275]]:
        prefix = dict(payload, bars=[r for r in payload['bars'] if r['date'] <= cutoff])
        short = by_day(prepare_a01_observations(prefix, contract))
        for d, r in short.items():
            assert r['features'] == full[d]['features']
            assert r['tested_condition'] is None
            assert r['distance_group'] == full[d]['distance_group']
    # Label maturity depends on future actual quotes, not frozen calendar alone.
    cutoff = payload['calendar'][259]
    partial, daily = fixture(285)
    partial['bars'] = partial['bars'][:260]
    row = by_day(prepare_a01_observations(partial, daily))[cutoff]
    assert row['target_label_reason'] == 'immature_label'
    assert row['label_end'] is None and not row['eligible']


def test_observation_period_filters_opportunities_but_not_warmup_or_indicators():
    payload, contract = fixture(280, sampling='periodic')
    full = prepare_a01_observations(payload, contract)
    contract['question']['period'] = [payload['calendar'][260], payload['calendar'][-1]]
    narrow = prepare_a01_observations(payload, contract)
    assert narrow['coverage']['raw'] == full['coverage']['raw'] == 280
    assert narrow['coverage']['calendar_slots'] == full['coverage']['calendar_slots']
    assert narrow['coverage']['indicators'] == full['coverage']['indicators']
    assert narrow['coverage']['observations'] < full['coverage']['observations']
    assert all(r['date'] >= payload['calendar'][260] for r in narrow['observations'])
    lookup = by_day(full)
    assert all(r['features'] == lookup[r['date']]['features'] for r in narrow['observations'])


def test_sampling_and_labels_are_called_through_shared_helpers():
    from lei_signal.research import workflow_inputs
    payload, contract = fixture(255)
    with patch.object(workflow_inputs, '_selected', wraps=workflow_inputs._selected) as selected, patch.object(workflow_inputs, '_label', wraps=workflow_inputs._label) as label:
        result = prepare_a01_observations(payload, contract)
    selected.assert_called_once()
    assert label.call_count == result['coverage']['observations']


def test_bound_provider_index_price_qualifies_features_without_action_wealth_claim():
    # This is an artificial provider-price series, not the historical panel.
    payload, contract = fixture()
    contract['target']['price_measure'] = 'provider_index_price'
    for row in payload['bars']:
        row.update(action_known=False, provider_price_known=True, price_series='provider_index_price', open_actionable=False)
    result = prepare_a01_observations(payload, contract)
    r = result['observations'][251]
    assert r['continuous_real_ohlc'] == 252
    assert r['features']['added'] == pytest.approx(14.75)
    # Shared price-measure semantics (implemented by controller) govern labels.
    assert r['eligible']
    payload['bars'][252]['provider_price_known'] = False
    result = prepare_a01_observations(payload, contract)
    assert result['observations'][252]['continuous_real_ohlc'] == 0


def test_invalid_definition_ohlc_future_availability_and_period_are_rejected():
    payload, contract = fixture()
    wrong = deepcopy(contract); wrong['feature']['warmup'] = 14
    with pytest.raises(ValueError, match='252'):
        prepare_a01_observations(payload, wrong)
    wrong = deepcopy(contract); wrong['question']['period'].reverse()
    with pytest.raises(ValueError, match='before'):
        prepare_a01_observations(payload, wrong)
    bad = deepcopy(payload); bad['bars'][0]['high'] = 50
    with pytest.raises(ValueError, match='low|outside'):
        prepare_a01_observations(bad, contract)
    bad = deepcopy(payload)
    bad['bars'][0].update(decision_at=bad['calendar'][0]+'T16:00:00+08:00', feature_available_at=bad['calendar'][1]+'T16:00:00+08:00')
    with pytest.raises(ValueError, match='after observation'):
        prepare_a01_observations(bad, contract)
