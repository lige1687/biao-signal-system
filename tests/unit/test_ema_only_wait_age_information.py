from __future__ import annotations

from datetime import date, timedelta
from copy import deepcopy
import math

import pytest

from lei_signal.research.ema_only_wait_age_information import (
    BASELINE_FEATURES, DEFINITION_REF, prepare_sequence_observations,
)


def panel(prices, missing=()):
    days = [(date(2022, 1, 3) + timedelta(days=i)).isoformat() for i in range(len(prices))]
    bars = []
    for i, (day, price) in enumerate(zip(days, prices)):
        if i in missing:
            bars.append({'asset': 'synthetic-A', 'date': day, 'status': 'vendor_missing'})
        else:
            bars.append({'asset': 'synthetic-A', 'date': day, 'status': 'quoted',
                         'action_known': True, 'open': price, 'high': price,
                         'low': price, 'close': price})
    payload = {'data_mode': 'synthetic', 'calendar': days, 'bars': bars}
    contract = {'feature': {'kind': 'ema_only_wait_age_information',
                'definition_ref': DEFINITION_REF, 'warmup': 252,
                'missing_policy': 'segmented'},
        'target': {'kind': 'forward_return', 'start_offset': 1, 'end_offset': 21,
                   'entry_field': 'close', 'price_measure': 'economic_price'},
        'question': {'sampling': 'daily', 'period': [days[0], days[-1]]},
        'universe': {'assets': ['synthetic-A']}}
    return payload, contract


def test_default_no_labels_prefix_and_decision_cutoff():
    prices = [100 + .1*i for i in range(280)]
    payload, contract = panel(prices)
    full = prepare_sequence_observations(payload, contract)
    assert all(r['y'] is None and r['label_end'] is None for r in full['observations'])
    assert all(r['target_label_reason'] == 'not_computed' for r in full['observations'])
    altered = deepcopy(payload)
    for row in altered['bars'][271:]:
        row.update(open=500., high=500., low=500., close=500.)
    other = prepare_sequence_observations(altered, contract)
    assert full['observations'][:271] == other['observations'][:271]
    cutoff = deepcopy(payload)
    cutoff['decision_at'] = payload['calendar'][260] + 'T16:00:00'
    observed = prepare_sequence_observations(cutoff, contract)['observations']
    assert len(observed) == 261
    assert observed == full['observations'][:261]
    cutoff['decision_at'] = payload['calendar'][260] + 'T14:59:00'
    assert prepare_sequence_observations(cutoff, contract)['observations'] == full['observations'][:260]


def test_fixed_definition_fields_reject_conflicts():
    payload, contract = panel([100.] * 260)
    for field, wrong in [('lookback', 19), ('ema_seed', 'sma20'),
                         ('sma_lag', 19), ('age_transform', 'linear'),
                         ('censor_policy', 'assume_zero')]:
        altered = deepcopy(contract)
        altered['feature'][field] = wrong
        with pytest.raises(ValueError, match='fixed EMA-only age'):
            prepare_sequence_observations(payload, altered)


def test_exact_equality_and_first_close_seed():
    prices = [100.] * 21 + [99.] * 240
    payload, contract = panel(prices)
    rows = prepare_sequence_observations(payload, contract)['observations']
    assert rows[0]['E'] is False
    assert rows[20]['S'] is False
    assert rows[21]['E'] is False
    assert rows[251]['ready_252'] is True
    assert rows[251]['features']['ema20_distance'] < 0
    assert len(BASELINE_FEATURES) == 10


def test_wait_age_reentry_and_missing_reset():
    # The first known E-only day at quote 21 is left-censored. A later
    # E-only entry after an observed non-E-only close starts at age one.
    prices = [200.] * 10 + [100.] * 10 + [150., 151., 152., 100., 151.] + [151.] * 230
    payload, contract = panel(prices)
    rows = prepare_sequence_observations(payload, contract)['observations']
    assert [(r['E_only'], r['wait_age'], r['left_censored']) for r in rows[20:25]] == [
        (True, 1, True), (True, 2, True), (True, 3, True),
        (False, None, None), (True, 1, False)]
    assert rows[24]['features']['added'] is None  # Still before 252 warmup.
    payload2, contract2 = panel([100.] * 260 + [99., 100., 101., 100., 99., 101.], missing={262})
    rows2 = prepare_sequence_observations(payload2, contract2)['observations']
    assert rows2[262]['E'] is None and rows2[262]['S'] is None
    assert rows2[262]['wait_age'] is None and not rows2[262]['eligible']
    assert rows2[263]['continuous_real_ohlc'] == 1
    assert not rows2[263]['ready_252']


def test_age_one_two_and_exact_box_after_warmup():
    payload, contract = panel([100.] * 250 + [99., 100., 100.])
    rows = prepare_sequence_observations(payload, contract)['observations']
    assert rows[251]['E_only'] is True and rows[251]['wait_age'] == 1
    assert rows[252]['E_only'] is True and rows[252]['wait_age'] == 2
    assert rows[251]['features']['added'] == pytest.approx(math.log1p(1))
    assert rows[252]['features']['added'] == pytest.approx(math.log1p(2))
    assert rows[251]['features']['deduction_box_distance'] == 0


def test_real_label_dual_permission():
    payload, contract = panel([100 + i for i in range(275)])
    payload['data_mode'] = 'historical_reconstruction'
    payload['price_series'] = 'economic_price'
    contract['permissions'] = {'real_labels': True}
    with pytest.raises(ValueError, match='real_labels and effect_authorized'):
        prepare_sequence_observations(payload, contract, compute_labels=True)
    contract['permissions'] = {'effect_authorized': True}
    with pytest.raises(ValueError, match='real_labels and effect_authorized'):
        prepare_sequence_observations(payload, contract, compute_labels=True)
