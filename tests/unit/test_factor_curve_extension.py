"""Synthetic, source-only checks for the factor curve extension adapter."""

from __future__ import annotations

import copy
import importlib.util
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

from lei_signal.research.factor_curve_extension import (
    FACTORS, build_targets, daily_extension_features,
    describe_monthly_difference, summarize_account,
)
from lei_signal.research.factor_group_curves import simulate
from lei_signal.research.output_storage import OutputStorageError


def _calendar(n=350):
    start = date(2020, 1, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(n)]


def _adapted(calendar, changes=None, gaps=(), breaks=()):
    changes = changes or {}
    return {"research_price_basis": "raw_ohlc_times_effective_foreAdjustFactor",
            "rows": [{"date": day, "close": changes.get(i, 100.0)}
                     for i, day in enumerate(calendar) if i not in gaps],
            "break_dates": [calendar[i] for i in breaks]}


def test_six_scores_hand_calculated_at_decision_close_and_future_prefix():
    calendar = _calendar()
    decision = calendar.index("2020-06-30")
    adapted = _adapted(calendar, {decision: 110.0})
    first = daily_extension_features(adapted, calendar, "x", "2020-06", "2020-06")[0]
    assert first["qualified"] is True
    assert [first[f"momentum{n}"] for n in (20, 60, 120)] == pytest.approx([0.1] * 3)
    ema20 = 100 + 10 * 2 / 21
    ema12 = 100 + 10 * 2 / 13
    ema26 = 100 + 10 * 2 / 27
    assert first["ma_distance"] == pytest.approx((110 - ema20) / ema20)
    assert first["ppo"] == pytest.approx(100 * (ema12 - ema26) / ema26)
    assert first["downside"] == 0
    changed_future = _adapted(calendar, {decision: 110.0, decision + 1: 0.01,
                                          decision + 10: 99999.0})
    second = daily_extension_features(changed_future, calendar, "x", "2020-06", "2020-06")[0]
    assert first == second


def test_break_or_missing_scheduled_row_restarts_all_seeded_means():
    calendar = _calendar()
    decision = calendar.index("2020-06-30")
    for adapted in (_adapted(calendar, gaps=(decision - 50,)),
                    _adapted(calendar, breaks=(decision - 50,))):
        row = daily_extension_features(adapted, calendar, "x", "2020-06", "2020-06")[0]
        assert row["qualified"] is False
        assert "last_121_scheduled_closes_incomplete" in row["reasons"]
        assert all(row[k] is None for k in ("momentum20", "ma_distance", "ppo", "downside"))
    adapted = _adapted(calendar, breaks=(10,))
    row = daily_extension_features(adapted, calendar, "x", "2020-06", "2020-06")[0]
    assert row["qualified"] is True


def test_downside_is_negative_rms_of_only_negative_log_returns():
    calendar = _calendar()
    decision = calendar.index("2020-06-30")
    up = daily_extension_features(_adapted(calendar, {decision: 110}), calendar,
                                  "x", "2020-06", "2020-06")[0]
    down = daily_extension_features(_adapted(calendar, {decision: 90}), calendar,
                                    "x", "2020-06", "2020-06")[0]
    assert up["downside"] == 0
    assert down["downside"] == pytest.approx(-abs(math.log(0.9)) / math.sqrt(60))
    assert down["downside"] < up["downside"]


def _qualification_input(n=31):
    month = "2020-06"
    decision = "2020-06-30"
    old, residual, extra = [], [], []
    for i in range(n):
        code = f"c{i:02d}"
        old.append({"month": month, "code": code, "decision_date": decision,
                    "green": i != 0, "momentum": float(i // 2), "vol60": 0.1 + i / 100,
                    "return": 999, "adverse": -999})
        residual.append({"month": month, "code": code, "decision_date": decision,
                         "reasons": '["not_green"]' if i == 0 else "[]",
                         "ordinary": i / 30, "residual": i / 10,
                         "scaled_control": i / 20})
        extra.append({"month": month, "code": code, "decision_date": decision,
                      "qualified": True, "momentum20": float(i // 2),
                      "momentum60": float(i), "momentum120": float(i),
                      "ma_distance": i / 100, "ppo": i / 10,
                      "downside": -i / 100})
    return old, residual, extra


def test_common_pool_partition_ties_weights_and_no_future_label_use():
    old, residual, extra = _qualification_input()
    calendar = ["2020-06-30", "2020-07-01"]
    result = build_targets(old, residual, extra, ["2020-06"], calendar)
    assert len(result["targets"]) == 102
    assert result["monthly"] == [
        {"month": "2020-06", "universe": "all_qualified", "n": 31,
         "qualified": True, "decision_date": "2020-06-30"},
        {"month": "2020-06", "universe": "green_only", "n": 30,
         "qualified": True, "decision_date": "2020-06-30"},
    ]
    groups = [g for g in result["groups"] if g["universe"] == "all_qualified"
              and g["factor"] == "momentum20"]
    assert [g["n"] for g in groups] == [7, 6, 6, 6, 6]
    assert groups[0]["codes"] == [f"c{i:02d}" for i in range(7)]
    target = result["targets"]["all_qualified__momentum20__G1"]["2020-06-30"]
    assert sum(target["weights"].values()) == pytest.approx(1)
    assert set(target["weights"]) == set(groups[0]["codes"])
    assert "c00" not in result["targets"]["green_only__pool"]["2020-06-30"]["weights"]
    other_old = copy.deepcopy(old)
    for row in other_old:
        row["return"] = -99999
        row["adverse"] = 88888
        row["opportunity"] = 12345
    assert build_targets(other_old, residual, extra, ["2020-06"], calendar) == result


def test_one_missing_shared_score_changes_all_ten_factors_and_cash_threshold():
    old, residual, extra = _qualification_input(30)
    extra[-1]["ppo"] = None
    result = build_targets(old, residual, extra, ["2020-06"], ["2020-06-30", "2020-07-01"])
    assert all(not row["qualified"] for row in result["monthly"])
    assert all(item["qualified"] is False and item["weights"] == {}
               for schedule in result["targets"].values() for item in schedule.values())
    assert {row["factor"] for row in result["groups"]} == set(FACTORS)
    assert next(row for row in result["qualification"] if row["code"] == "c29")["reason"] == "common_score_missing"


def test_conflicting_frozen_decision_date_is_an_error():
    old, residual, extra = _qualification_input(30)
    extra[0]["decision_date"] = "2020-06-29"
    with pytest.raises(ValueError, match="decision date conflicts"):
        build_targets(old, residual, extra, ["2020-06"], ["2020-06-30", "2020-07-01"])


def test_summary_keeps_cash_unknown_and_period_month_axis():
    daily = [
        {"date": "2020-01-31", "nav_quote_proxy": 100.0, "cash": 100.0,
         "market_value": 0.0, "unknown_fraction": 0.0, "cash_fraction": 1.0,
         "fees_cumulative": 0.0, "gross_traded_today": 0.0, "nav_before_trade": 100.0},
        {"date": "2020-02-03", "nav_quote_proxy": 90.0, "cash": 20.0,
         "market_value": 70.0, "unknown_fraction": 0.2, "cash_fraction": 2 / 9,
         "fees_cumulative": 1.0, "gross_traded_today": 80.0, "nav_before_trade": 100.0},
        {"date": "2020-02-28", "nav_quote_proxy": 110.0, "cash": 20.0,
         "market_value": 90.0, "unknown_fraction": 0.0, "cash_fraction": 2 / 11,
         "fees_cumulative": 1.0, "gross_traded_today": 0.0, "nav_before_trade": 110.0},
    ]
    summary = summarize_account(daily, {"all": ("2020-02", "2020-02")}, initial_cash=100)
    assert summary["points"][-1][:2] == ["2020-02-28", 1.1]
    assert summary["points"][-1][4] == pytest.approx(-0.1)
    assert summary["points"][-1][5] == pytest.approx(0.2)
    assert summary["period"]["all"]["monthly"] == {"2020-02": pytest.approx(0.1)}
    assert summary["period"]["all"]["unknown_days"] == 1
    same = summary["period"]["all"]
    assert describe_monthly_difference(same, same)["mean"] == 0


def test_frozen_group_target_reaches_account_only_after_decision_close():
    old, residual, extra = _qualification_input(30)
    calendar = ["2020-06-30", "2020-07-01", "2020-07-31"]
    targets = build_targets(old, residual, extra, ["2020-06"], calendar)["targets"]
    schedule = targets["all_qualified__pool"]
    quote = {"open": 100.0, "close": 100.0, "high": 101.0, "low": 99.0,
             "preclose": 100.0, "volume": 100.0, "tradestatus": "1", "isST": "0",
             "source_valid": True}
    market = {row["code"]: {day: dict(quote) for day in calendar} for row in old}
    account = simulate(calendar, market, schedule, cost_bps=25,
                       start_date=calendar[0], end_date=calendar[-1])
    assert account["daily"][0]["held_count"] == 0
    assert account["daily"][0]["nav_quote_proxy"] == 100000
    assert account["daily"][1]["held_count"] == 30
    assert account["daily"][1]["nav_quote_proxy"] < 100000
    assert all(trade["date"] == "2020-07-01" for trade in account["trades"])
    assert len(account["trades"]) == 30


def test_execution_rechecks_capacity_before_any_account_call(monkeypatch):
    path = (Path(__file__).resolve().parents[2]
            / "docs/experiments/raw/factor-curve-library-2026-10-22/run.py")
    spec = importlib.util.spec_from_file_location("curve_extension_guard_test", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    calls = []

    def insufficient(*args, **kwargs):
        calls.append("live_capacity_probe")
        raise OutputStorageError("insufficient internal capacity")

    monkeypatch.setattr(runner, "plan_output", insufficient)
    monkeypatch.setattr(runner, "simulate", lambda *args, **kwargs: calls.append("simulate"))
    with pytest.raises(OutputStorageError, match="insufficient internal capacity"):
        runner._recheck_existing_output({"task_id": "factor-curve-library-20261022",
                                         "estimated_bytes": 123, "internal_metadata_bytes": 10})
    assert calls == ["live_capacity_probe"]
