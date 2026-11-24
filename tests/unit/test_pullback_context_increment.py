from datetime import date, timedelta

import pytest

from lei_signal.research.original_a_waiting import daily_bottom_events
from lei_signal.research.pullback_context_increment import daily_bottom_events_incremental, evaluate_asset


def rows(spec, start=date(2022, 1, 3)):
    out = []
    for n, item in enumerate(spec):
        if item is None:
            out.append({"date": (start + timedelta(days=n)).isoformat(), "qualified": False})
            continue
        low, high, close = item
        out.append({"date": (start + timedelta(days=n)).isoformat(), "qualified": True,
                    "adjusted_open": close, "adjusted_high": high,
                    "adjusted_low": low, "adjusted_close": close})
    return out


def event(day, close=100, anchor=95, warm=True):
    return {"asset": "X", "identity_key": "first-X", "first_seen": day,
            "warm252": warm, "anchor_adjusted_low": anchor,
            "adjusted_close_at_first": close}


def prepared(h=30, start=date(2022, 1, 3)):
    r = rows([(99, 101, 100)] * (252 + h + 2), start)
    return r, event(r[251]["date"])


@pytest.mark.parametrize("spec", [
    [(10, 12, 11), (11, 13, 12), (12, 14, 13), (12, 15, 14)],  # confirm, then contain
    [(10, 12, 11), (11, 13, 12), (12, 14, 13), (9, 11, 10), (10, 12, 11), (11, 14, 12)],
    [(10, 12, 11), (11, 13, 12), (11, 13, 12), (12, 14, 13)],  # equal containment
    [(10, 12, 11), (11, 13, 12), (12, 14, 13), None, (10, 12, 11), (11, 13, 12), (12, 14, 13)],
    [(10, 12, 11), (11, 13, 12), (12, 14, 13), (12, 15, 14), (13, 16, 15), (14, 17, 16)],
])
def test_incremental_matches_frozen_every_prefix(spec):
    daily = rows(spec)
    for n in range(1, len(daily) + 1):
        assert daily_bottom_events_incremental(daily[:n], asset="X") == daily_bottom_events(daily[:n], asset="X")


def test_incremental_warm252_identity_and_new_pending_same_group():
    spec = [(99, 101, 100)] * 249 + [(97, 100, 99), (98, 101, 100), (99, 103, 101),
                                    (100, 104, 102), (101, 105, 103)]
    daily = rows(spec)
    assert daily_bottom_events_incremental(daily, asset="X") == daily_bottom_events(daily, asset="X")
    assert daily_bottom_events_incremental(daily[:252], asset="X")[-1]["warm252"] is True


def test_bottom_strict_low_and_next_close_includes_jump():
    r, e = prepared()
    i = 251
    r[i + 1].update(adjusted_low=95, adjusted_close=100, adjusted_open=100, adjusted_high=101)
    r[i + 2].update(adjusted_low=94, adjusted_close=99, adjusted_open=99, adjusted_high=101)
    r[i + 3].update(adjusted_low=89, adjusted_close=90, adjusted_open=90, adjusted_high=101)
    got = evaluate_asset(r, [e], "X", (20,))[0]
    assert got["frozen_bottom"]["exit_date"] == r[i + 3]["date"]
    assert got["frozen_bottom"]["return_pct"] == pytest.approx(-10)
    assert got["frozen_bottom"]["loss_pct"] == pytest.approx(10)
    assert got["frozen_bottom"]["exposure_trading_days"] == 3


def test_intraday_bottom_recovery_still_signals():
    r, e = prepared()
    i = 251
    r[i + 1].update(adjusted_low=94, adjusted_close=102, adjusted_open=102, adjusted_high=103)
    r[i + 2].update(adjusted_low=99, adjusted_close=100, adjusted_open=100, adjusted_high=103)
    got = evaluate_asset(r, [e], "X", (20,))[0]
    assert got["frozen_bottom"]["exit_date"] == r[i + 2]["date"]
    assert got["frozen_bottom"]["return_pct"] == pytest.approx(0)
    assert got["frozen_bottom"]["loss_pct"] == pytest.approx(0)


def test_reverse20_true_at_start_exits_next_day():
    r, e = prepared()
    i = 251
    r[i].update(adjusted_low=89, adjusted_close=90, adjusted_open=90, adjusted_high=101)
    e["adjusted_close_at_first"] = 90
    e["anchor_adjusted_low"] = 85
    r[i + 1].update(adjusted_low=79, adjusted_close=80, adjusted_open=80, adjusted_high=101)
    got = evaluate_asset(r, [e], "X", (20,))[0]
    assert got["reverse20"]["exit_date"] == r[i + 1]["date"]
    assert got["reverse20"]["return_pct"] == pytest.approx(100 * (80 / 90 - 1))
    assert got["reverse20"]["end_adjusted_close"] == 80
    assert got["combined"]["exit_reason"] == "reverse20"


def test_signal_last_day_before_h_and_future_append_invariance():
    r, e = prepared()
    i = 251
    h = 20
    r[i + h - 1].update(adjusted_low=94, adjusted_close=100, adjusted_open=100, adjusted_high=101)
    r[i + h].update(adjusted_low=89, adjusted_close=90, adjusted_open=90, adjusted_high=101)
    first = evaluate_asset(r[:i + h + 1], [e], "X", (h,))[0]
    later = evaluate_asset(r, [e], "X", (h,))[0]
    assert first == later
    assert first["frozen_bottom"]["exit_date"] == r[i + h]["date"]
    assert first["frozen_bottom"]["return_pct"] == pytest.approx(-10)
    assert first["frozen_bottom"]["minus_hold_pp"] == pytest.approx(0)


def test_unknowns_and_period_boundary():
    r, e = prepared()
    assert evaluate_asset(r, [{**e, "warm252": False}], "X", (20,))[0]["unknown_reason"] == "not_warm252"
    assert evaluate_asset(r[:260], [e], "X", (20,))[0]["unknown_reason"] == "immature_horizon"
    r[255]["qualified"] = False
    assert evaluate_asset(r, [e], "X", (20,))[0]["unknown_reason"] == "unqualified_or_missing_price"
    r2, e2 = prepared(start=date(2023, 4, 24))
    assert evaluate_asset(r2, [e2], "X", (30,))[0]["unknown_reason"] == "cross_period"
    assert evaluate_asset(r2, [{**e2, "first_seen": "2020-01-01"}], "X", (20,))[0]["unknown_reason"] == "missing_start"


def test_policy_contribution_identity_and_h_after_signal_ignored():
    r, e = prepared()
    i = 251
    r[i + 1].update(adjusted_low=94, adjusted_close=98, adjusted_open=98, adjusted_high=101)
    r[i + 2].update(adjusted_low=89, adjusted_close=90, adjusted_open=90, adjusted_high=101)
    r[i + 20].update(adjusted_low=109, adjusted_close=110, adjusted_open=110, adjusted_high=111)
    got = evaluate_asset(r, [e], "X", (20,))[0]
    for key in ("hold", "frozen_bottom", "reverse20", "combined"):
        p = got[key]
        assert p["minus_hold_pp"] == pytest.approx(p["avoided_downside_pp"] - p["missed_upside_pp"])
    assert got["hold"]["return_pct"] == pytest.approx(10)
    assert got["frozen_bottom"]["return_pct"] == pytest.approx(-10)
    assert got["frozen_bottom"]["missed_upside_pp"] == pytest.approx(20)


def test_missing_price_is_unknown_not_zero():
    r, e = prepared()
    del r[260]["adjusted_close"]
    got = evaluate_asset(r, [e], "X", (20,))[0]
    assert got["status"] == "unknown"
    assert got["unknown_reason"] == "unqualified_or_missing_price"
    assert all(got[k] is None for k in ("hold", "frozen_bottom", "reverse20", "combined"))


def test_signal_only_after_h_does_not_change_h_result():
    r, e = prepared()
    i = 251
    before = evaluate_asset(r, [e], "X", (20,))[0]
    r[i + 21].update(adjusted_low=90, adjusted_close=100, adjusted_open=100, adjusted_high=101)
    after = evaluate_asset(r, [e], "X", (20,))[0]
    assert before == after
    assert after["frozen_bottom"]["exit_date"] is None


def test_generated_containment_sequences_match_frozen_oracle():
    import random
    for seed in (1, 7, 19):
        rng = random.Random(seed)
        spec = []
        center = 100
        for n in range(100):
            if n in (30, 65):
                spec.append(None)
                continue
            center = max(20, center + rng.choice((-2, -1, 0, 1, 2)))
            spread = rng.choice((1, 2, 3, 4))
            spec.append((center - spread, center + spread, center))
        daily = rows(spec)
        for n in range(1, len(daily) + 1):
            assert daily_bottom_events_incremental(daily[:n], asset="X") == daily_bottom_events(daily[:n], asset="X")
