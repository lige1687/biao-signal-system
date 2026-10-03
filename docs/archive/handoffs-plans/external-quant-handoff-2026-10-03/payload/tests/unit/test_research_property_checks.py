"""Bounded generated inputs for the existing demonstration adapter, not factors.

Requires the optional property-tests extra. Real calendars, prices, registered
factor adapters and account results are deliberately outside this test domain.
"""
import math
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta

import pytest

pytest.importorskip("hypothesis")
from hypothesis import Phase, find, given, settings
from hypothesis import strategies as st

from lei_signal.research.workflow_inputs import prepare_observations

RUN_COUNTS = Counter()
CONTROL = {}
BOUNDED = settings(max_examples=64, derandomize=True, database=None,
                   deadline=None, phases=[Phase.generate, Phase.shrink])


@st.composite
def synthetic_inputs(draw):
    n = draw(st.integers(16, 28))
    lookback = draw(st.integers(2, 6))
    start = draw(st.dates(date(2024, 1, 1), date(2026, 8, 1)))
    gaps = draw(st.lists(st.integers(1, 4), min_size=n-1, max_size=n-1))
    days = [start]
    for gap in gaps:
        days.append(days[-1] + timedelta(days=gap))
    days = [d.isoformat() for d in days]
    prices = draw(st.lists(st.integers(100, 100000), min_size=2*n, max_size=2*n))
    bars = [dict(asset=asset, date=d, status="quoted", close=float(prices[k*n+i]),
                 open=float(prices[k*n+i]), high=float(prices[k*n+i]+10),
                 low=float(prices[k*n+i]-10), action_known=True, open_actionable=True)
            for k, asset in enumerate(("A", "B")) for i, d in enumerate(days)]
    missing = draw(st.sampled_from([None, "halt", "vendor_missing"]))
    if missing:
        i = draw(st.integers(lookback+2, n-2))
        bars[i].update(status=missing, close=None, open=None, high=None, low=None,
                       open_actionable=False)
    payload = {"calendar": days, "data_mode": "synthetic", "bars": bars}
    contract = {
        "universe": {"assets": ["A", "B"], "allow_partial": False},
        "feature": {"kind": "sma_distance", "lookback": lookback, "warmup": lookback+1,
                    "missing_policy": draw(st.sampled_from(["real_quote", "segmented"]))},
        "question": {"sampling": "daily"},
        "target": {"kind": "forward_return", "start_offset": 1, "end_offset": 3,
                   "entry_field": "close", "unit": "percentage_point"},
    }
    cutoff = draw(st.integers(lookback+1, n-4))
    exponent = draw(st.integers(-4, 4))
    return payload, contract, days[cutoff], 2.0**exponent


@BOUNDED
@given(synthetic_inputs())
def test_future_quotes_do_not_rewrite_past_features(case):
    RUN_COUNTS["future_change"] += 1
    payload, contract, cutoff, _ = case
    altered = deepcopy(payload)
    for row in altered["bars"]:
        if row["date"] > cutoff and row["status"] == "quoted":
            for key in ("open", "high", "low", "close"):
                row[key] *= 3
    before = prepare_observations(payload, contract)["observations"]
    after = prepare_observations(altered, contract)["observations"]
    past_before = {r["id"]: (r["features"], r["tested_condition"])
                   for r in before if r["date"] <= cutoff}
    past_after = {r["id"]: (r["features"], r["tested_condition"])
                  for r in after if r["date"] <= cutoff}
    assert any(r[0]["added"] is not None for r in past_before.values())
    assert past_before == past_after


@BOUNDED
@given(synthetic_inputs())
def test_price_scale_preserves_percentage_quantities(case):
    RUN_COUNTS["scale_invariance"] += 1
    payload, contract, _, scale = case
    scaled = deepcopy(payload)
    for row in scaled["bars"]:
        if row["status"] == "quoted":
            for key in ("open", "high", "low", "close"):
                row[key] *= scale
    before = prepare_observations(payload, contract)["observations"]
    after = prepare_observations(scaled, contract)["observations"]
    assert len(before) == len(after)
    for left, right in zip(before, after, strict=True):
        for key in ("id", "eligible", "label_end", "label_reason", "tested_condition"):
            assert left[key] == right[key]
        pairs = [(left["y"], right["y"])] + [
            (left["features"][key], right["features"][key]) for key in left["features"]]
        for old, new in pairs:
            if old is None:
                assert new is None
            else:
                assert math.isclose(old, new, rel_tol=1e-10, abs_tol=1e-10)


def test_generator_finds_an_intentional_future_leak():
    """Control for the test tool, deliberately not a project implementation."""
    def violates_past_invariance(prices):
        RUN_COUNTS["negative_control_predicate_calls"] += 1
        past_value = prices[-2]
        # Deliberate error: today's normalizer includes the next quote.
        return past_value / max(prices) != past_value / max(prices[:-1])

    example = find(st.lists(st.integers(1, 100), min_size=3, max_size=12),
                   violates_past_invariance,
                   settings=settings(max_examples=128, derandomize=True,
                                     database=None, deadline=None))
    CONTROL.update(prices=example, past_only=example[-2]/max(example[:-1]),
                   wrongly_using_future=example[-2]/max(example))
    assert CONTROL["past_only"] != CONTROL["wrongly_using_future"]
