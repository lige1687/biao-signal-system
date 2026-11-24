import pytest

from lei_signal.research.focus_zero_evaluation import build_rows, standardized, upcross


def test_crossings_require_observed_predecessor():
    assert upcross(-.1, .1)
    assert upcross(0, .1)
    assert not upcross(None, .1)
    assert not upcross(-.1, 0)


def test_future_label_starts_next_session_and_missing_predecessor_breaks_event():
    from datetime import date, timedelta
    cal = [(date(2014, 1, 1) + timedelta(days=i)).isoformat() for i in range(400)]
    prices = {d: 100 + i for i, d in enumerate(cal)}
    features = {d: {"focus": -.1 if i < 250 else .1, "pool_momentum": 0, "breadth": .5} for i, d in enumerate(cal)}
    rows = build_rows(cal, prices, features, 20, cal[249], cal[250])
    event = rows[-1]
    assert event["focus_up"]
    assert event["label_start"] == cal[251]
    assert event["label_end"] == cal[271]
    assert event["forward_return"] == pytest.approx(371 / 351 - 1)
    del features[cal[249]]
    assert build_rows(cal, prices, features, 20, cal[250], cal[250]) == []


def test_state_matching_does_not_confuse_composition_with_increment():
    # Signal picks strong-market states more often; within each state it adds zero.
    rows = [{"baseline_cell": c, "focus_up": event, "forward_return": value}
            for c, event, value in [(0, True, .1), (0, True, .1), (0, False, .1),
                                    (1, True, -.1), (1, False, -.1), (1, False, -.1)]]
    result = standardized(rows, "focus_up")
    assert result["difference"] == 0
    assert result["supported_event_weight"] == 3
    rows.append({"baseline_cell": 2, "focus_up": True, "forward_return": .5})
    assert standardized(rows, "focus_up")["supported_event_weight"] == 3
