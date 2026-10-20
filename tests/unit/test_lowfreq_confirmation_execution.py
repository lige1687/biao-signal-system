from copy import deepcopy
from datetime import date, timedelta
import importlib.util
from pathlib import Path

import pytest

from lei_signal.research.lowfreq_confirmation_execution import evaluate_asset


PERIODS = [("all", "2026-01-01", "2026-12-31")]


def sample(states=(False, True, False, False, False, False, False), closes=None):
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(7)]
    closes = closes or [100, 101, 102, 103, 104, 105, 106]
    daily = [{"date": d, "qualified": True, "adjusted_open": c,
              "adjusted_low": c - 1, "adjusted_close": c} for d, c in zip(dates, closes)]
    hours = [{"date": d, "time": "15:00", "hour_qualified": True, "bull": state}
             for d, state in zip(dates, states)]
    return {"asset": {"code": "sh.510500", "group": "etf"}, "daily": daily, "hours": hours,
            "events": [{"asset": "sh.510500", "identity_key": "one", "first_seen": dates[0],
                        "anchor_adjusted_low": 90}]}


def result(data, horizon=6):
    return evaluate_asset(data, [horizon], PERIODS)[0]


def test_intraday_true_close_false_is_not_a_daily_confirmation():
    data = sample(states=[False] * 7)
    data["hours"].append({"date": data["daily"][1]["date"], "time": "10:30",
                          "hour_qualified": True, "bull": True})
    assert result(data)["policies"]["hourly_eod"]["status"] == "nonparticipation"


def test_open_then_break_does_not_retroactively_cancel_entry():
    data = sample(states=[True] + [False] * 6)
    data["daily"][1]["adjusted_open"] = 95
    data["daily"][1]["adjusted_low"] = 85
    out = result(data)
    assert out["policies"]["direct"]["status"] == "participated"
    assert out["policies"]["hourly_eod"]["status"] == "participated"
    assert out["policies"]["direct"]["decline_pct"] == 0


def test_entry_day_close_is_in_decline():
    data = sample(states=[True] + [False] * 6)
    data["daily"][1]["adjusted_open"] = 110
    out = result(data)
    assert out["policies"]["direct"]["decline_pct"] == pytest.approx(100 * (1 - 101 / 110))


def test_h_minus_one_confirm_enters_at_h_open():
    data = sample(states=[False] * 5 + [True, False])
    out = result(data)
    assert out["policies"]["hourly_eod"]["entry_date"] == data["daily"][6]["date"]


def test_h_confirmation_cannot_enter_and_prior_known_path_is_enough():
    data = sample(states=[False] * 6 + [True])
    assert result(data)["policies"]["hourly_eod"]["status"] == "nonparticipation"
    data["hours"].pop()
    assert result(data)["policies"]["hourly_eod"]["status"] == "nonparticipation"


def test_opening_gap_below_anchor_cancels_without_reissue():
    data = sample(states=[True] + [False] * 6)
    data["daily"][1]["adjusted_open"] = 89
    data["daily"][1]["adjusted_low"] = 88
    out = result(data)
    assert out["policies"]["hourly_eod"]["reason"] == "opening_gap_below_anchor"
    assert out["policies"]["hourly_eod"]["score_pct"] == 0


def test_missing_initial_hour_marks_common_unknown_and_preserves_event():
    data = sample()
    data["hours"][0]["bull"] = None
    out = result(data)
    assert out["common_reason"] == "missing_initial15_state"
    assert not out["paired"]
    assert out["identity_key"] == "one"
    assert out["paired"] is False
    assert out["common_status"] == "unknown"


def test_immature_event_keeps_all_schema_fields():
    out = result(sample(), 10)
    assert out["initial15bull"] is None
    assert out["paired"] is False
    assert out["common_status"] == "unknown"
    assert set(out["policies"]) == {"direct", "hourly_eod", "fixed5"}


def test_unknown_hour_while_waiting_is_not_zero():
    data = sample(states=[False] * 7)
    data["hours"][2]["bull"] = None
    out = result(data)
    assert out["common_status"] == "unknown"
    assert out["policies"]["hourly_eod"]["score_pct"] is None


def test_nonfinite_price_does_not_qualify():
    data = sample(states=[True] + [False] * 6)
    data["daily"][1]["adjusted_open"] = float("nan")
    out = result(data)
    assert out["policies"]["direct"]["reason"] == "missing_open"
    assert not out["paired"]


def test_future_extension_does_not_change_past_action():
    data = sample(states=[True] + [False] * 6)
    before = result(data, 3)["policies"]["hourly_eod"]
    extended = deepcopy(data)
    extended["daily"][5]["adjusted_close"] *= 2
    extended["hours"][5]["bull"] = True
    after = result(extended, 3)["policies"]["hourly_eod"]
    assert before == after


def test_future_daily_quality_changes_coverage_not_past_action():
    data = sample(states=[True] + [False] * 6)
    before = result(data)
    revised = deepcopy(data)
    revised["daily"][3]["qualified"] = False
    after = result(revised)
    for policy in ("direct", "hourly_eod"):
        assert before["policies"][policy]["status"] == after["policies"][policy]["status"] == "participated"
        assert before["policies"][policy]["entry_date"] == after["policies"][policy]["entry_date"]
    assert before["paired"] and not after["paired"]


def test_uniform_price_scaling_preserves_results():
    data = sample()
    before = result(data)
    scaled = deepcopy(data)
    scaled["events"][0]["anchor_adjusted_low"] *= 3
    for row in scaled["daily"]:
        for field in ("adjusted_open", "adjusted_low", "adjusted_close"):
            row[field] *= 3
    after = result(scaled)
    for policy in ("direct", "hourly_eod", "fixed5"):
        assert before["policies"][policy]["score_pct"] == pytest.approx(after["policies"][policy]["score_pct"])
        assert before["policies"][policy]["decline_pct"] == pytest.approx(after["policies"][policy]["decline_pct"])


def test_decomposition_equals_policy_difference_for_missed_up_and_avoided_down():
    for final in (120, 80):
        data = sample(states=[False] * 7, closes=[100, 100, 100, 100, 100, 100, final])
        out = result(data)
        parts = out["decomposition_pp"]
        assert sum(parts.values()) == pytest.approx(out["delta_pp"])
        assert (parts["missed_up_direct_only"] < 0) == (final > 100)
        assert (parts["avoided_down_direct_only"] > 0) == (final < 100)


def test_stocks_are_rejected():
    data = sample()
    data["asset"]["group"] = "stock"
    with pytest.raises(ValueError):
        result(data)


def test_group_average_does_not_switch_to_smaller_product_pool():
    runner = Path(__file__).parents[2] / "docs/experiments/raw/lowfreq-confirmation-execution-2026-10-20/run_comparison.py"
    spec = importlib.util.spec_from_file_location("lowfreq_runner", runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = result(sample())
    group = module._equal_asset([row], ["sh.510500", "sh.510050"])
    assert group["missing_products"] == ["sh.510050"]
    assert group["equal_asset"]["hourly_minus_direct_pp"] is None


def test_intraday_confirmation_lost_by_close_is_recorded_before_endpoint():
    runner = Path(__file__).parents[2] / "docs/experiments/raw/lowfreq-confirmation-execution-2026-10-20/run_comparison.py"
    spec = importlib.util.spec_from_file_location("lowfreq_runner", runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = sample(states=[False] * 7)
    for day in (1, 6):
        data["hours"].append({"date": data["daily"][day]["date"], "time": "10:30",
                              "hour_qualified": True, "bull": True})
    row = result(data)
    assert module.intraday_lost_before_decision(row, data) == [data["daily"][1]["date"]]


def test_conditional_wait_mean_discloses_product_without_participation():
    runner = Path(__file__).parents[2] / "docs/experiments/raw/lowfreq-confirmation-execution-2026-10-20/run_comparison.py"
    spec = importlib.util.spec_from_file_location("lowfreq_runner", runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = result(sample(states=[False] * 7))
    group = module._equal_asset([row], ["sh.510500"])
    assert group["equal_asset"]["policies"]["hourly_eod"]["score_pct"] == 0
    assert group["equal_asset"]["policies"]["hourly_eod"]["wait_trading_days_if_participated"] is None
    assert group["metric_missing_products"]["hourly_eod"]["wait_trading_days_if_participated"] == ["sh.510500"]
    unknown = result(sample(), 10)
    assert module._asset_metric([unknown])["unpaired_reasons"] == {"outside_period_or_immature": 1}
