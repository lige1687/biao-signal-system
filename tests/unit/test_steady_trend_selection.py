"""Synthetic checks for the frozen monthly policy; never loads market data."""

import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest


SOURCE = Path(__file__).resolve().parents[2] / "src/lei_signal/research/steady_trend_selection.py"
DESIGN = Path(__file__).resolve().parents[2] / "docs/experiments/raw/gemini-steady-trend-etf-2026-10-20/design.json"
spec = importlib.util.spec_from_file_location("steady_trend_selection", SOURCE)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def fixture_data(*, missing=None, tiny_roundoff=False):
    start, stop = date(2021, 6, 1), date(2022, 9, 5)
    calendar = []
    d = start
    while d <= stop:
        if d.weekday() < 5:
            calendar.append(d.isoformat())
        d += timedelta(days=1)
    assets = ("A", "B", "C", "D")
    bars = []
    for ai, asset in enumerate(assets):
        for i, day in enumerate(calendar):
            close = 100 * np.exp((0.0003 + ai * 0.00015) * i
                                  + 0.015 * np.sin(i / (20 + ai)))
            lo, hi = close * 0.99, close * 1.01
            if tiny_roundoff and asset == "A" and day == "2022-01-03":
                hi = close - 1e-14
            bars.append({"asset": asset, "date": day, "open": close * 0.999,
                         "high": hi, "low": lo, "close": close,
                         "status": "vendor_missing" if (asset, day) == missing else "quoted",
                         "action_known": True})
    design = json.loads(DESIGN.read_text())
    design["groups"] = {"broad": list(assets)}
    design["signal_start"] = "2022-01-01"
    design["signal_end"] = "2022-07-31"
    design["evaluation_end"] = "2022-08-31"
    design["uncertainty"]["replicates"] = 50
    return {"calendar": calendar, "bars": bars}, design


def test_regression_and_score_formulas():
    prices = np.exp(np.arange(120) * 0.002)
    slope, r2 = study._regression(prices)
    assert slope == pytest.approx(0.504)
    assert r2 == pytest.approx(1)
    assert study._regression(np.ones(120)) == (0, 0)
    data, design = fixture_data()
    a = next(f for f in study.build_features(data, design)
             if f["asset"] == "A" and f["signal"].startswith("2022-01"))
    assert a["scores"]["slope_r2_120"] == pytest.approx(
        a["scores"]["slope120"] * a["scores"]["r_squared"])
    idx = data["calendar"].index(a["signal"])
    closes = [r["close"] for r in data["bars"] if r["asset"] == "A"]
    assert a["scores"]["momentum120"] == pytest.approx(np.log(closes[idx] / closes[idx-119]))
    returns = np.diff(np.log(closes[idx-119:idx+1]))
    assert a["scores"]["vol_adjusted120"] == pytest.approx(
        returns.sum() / np.sqrt(returns @ returns))


def test_feature_prefix_and_completed_month_clock():
    data, design = fixture_data()
    original = {(f["asset"], f["signal"]): f for f in study.build_features(data, design)}
    changed = {"calendar": data["calendar"], "bars": [dict(r) for r in data["bars"]]}
    for row in changed["bars"]:
        if row["date"] >= "2022-04-01":
            row["close"] *= 1.1
            row["open"] *= 1.1
            row["low"] *= 1.1
            row["high"] *= 1.1
    new = {(f["asset"], f["signal"]): f for f in study.build_features(changed, design)}
    for key in original:
        if key[1] < "2022-04-01":
            assert new[key] == original[key]
    cut = {"calendar": [d for d in data["calendar"] if d <= "2022-01-28"],
           "bars": [r for r in data["bars"] if r["date"] <= "2022-01-28"]}
    assert not study.build_features(cut, design)  # Jan completion not yet known


def test_fee_solution_initial_and_drifted_rebalance():
    after, turn, fee, holdings = study._rebalance(1.0, {"A": 0, "B": 0},
                                                  {"A": 0.5, "B": 0.5}, 0.001)
    assert after == pytest.approx(1 / 1.001)
    assert turn == pytest.approx(after)
    assert fee == pytest.approx(0.001 * turn)
    assert sum(holdings.values()) == pytest.approx(after)
    after2, turn2, fee2, h2 = study._rebalance(1.1, {"A": 0.6, "B": 0.5},
                                               {"A": 0.5, "B": 0.5}, 0.001)
    assert after2 + fee2 == pytest.approx(1.1)
    assert turn2 == pytest.approx(sum(abs(h2[a] - x) for a, x in {"A": 0.6, "B": 0.5}.items()))
    assert turn2 > 0


def test_complete_period_account_no_terminal_liquidation_and_serializable():
    data, design = fixture_data(tiny_roundoff=True)
    out = study.run_study(data, design)
    broad = out["groups"]["broad"]
    assert broad["periods"]
    assert [p["signal"] for p in broad["periods"]] == sorted(p["signal"] for p in broad["periods"])
    assert any(x["signal"].startswith("2022-07") for x in out["unmatured"])
    account = broad["accounts"]["0.0010"]["equal_weight"]
    assert account["months"][0]["fee_paid"] > 0
    assert account["months"][0]["before_rebalance"] == pytest.approx(1)
    assert account["daily_nav"][0]["nav"] == 1
    assert account["performance"]["last_exit"] == broad["periods"][-1]["exit"]
    assert account["daily_nav"][-1]["kind"] == "exit_open"
    assert account["daily_nav"][-1]["nav"] == pytest.approx(account["performance"]["terminal_wealth"])
    assert len(broad["paired"]["candidate_minus_momentum"]["monthly_pairs"]) == len(broad["periods"])
    winners = broad["paired"]["candidate_minus_momentum"]["top_quartile_positive_winner_capture"]
    assert winners["extreme_months"] <= winners["positive_maximum_months"] <= len(broad["periods"])
    json.dumps(out, allow_nan=False)


def test_missing_future_bar_stops_contiguous_account():
    data, design = fixture_data(missing=("A", "2022-04-15"))
    out = study.run_study(data, design)
    periods = out["groups"]["broad"]["periods"]
    assert periods
    assert all(p["exit"] <= "2022-04-15" for p in periods)
    assert any(x["reason"] == "future_trade_or_valuation_unknown" for x in out["invalid"])
    assert any(x["reason"] == "after_continuity_break" for x in out["invalid"])


def test_missing_first_action_month_does_not_shift_account_start():
    data, design = fixture_data(missing=("A", "2022-02-15"))
    out = study.run_study(data, design)
    assert out["groups"]["broad"]["periods"] == []
    assert out["groups"]["broad"]["accounts"] == {}
    assert any(x["signal"] == "2022-01-31" and
               x["reason"] == "future_trade_or_valuation_unknown" for x in out["invalid"])
    assert any(x["reason"] == "after_continuity_break" for x in out["invalid"])


def test_materially_invalid_ohlc_resets_warmup():
    data, design = fixture_data()
    row = next(r for r in data["bars"] if r["asset"] == "A" and r["date"] == "2022-01-03")
    row["high"] = row["close"] - 0.01
    features = study.build_features(data, design)
    jan = next(f for f in features if f["asset"] == "A" and f["signal"].startswith("2022-01"))
    assert not jan["eligible"]


def test_terminal_two_months_are_unmatured_without_july():
    data, design = fixture_data()
    data = {"calendar": [d for d in data["calendar"] if d <= "2022-06-30"],
            "bars": [r for r in data["bars"] if r["date"] <= "2022-06-30"]}
    design["signal_end"] = design["evaluation_end"] = "2022-06-30"
    out = study.run_study(data, design)
    unmatured = {x["signal"] for x in out["unmatured"]}
    assert "2022-05-31" in unmatured  # July open missing as exit
    assert "2022-06-30" in unmatured  # July open missing as entry
    periods = out["groups"]["broad"]["periods"]
    assert periods[-1]["signal"] == "2022-04-29"
    assert periods[-1]["exit"] == "2022-06-01"


def test_flat_one_period_charges_entry_only():
    data, design = fixture_data()
    for row in data["bars"]:
        row.update(open=100.0, high=100.0, low=100.0, close=100.0)
    calendar = data["calendar"]
    bars = {(r["asset"], r["date"]): r for r in data["bars"]}
    periods = [{"signal": "2022-01-31", "entry": "2022-02-01", "exit": "2022-03-01"}]
    weights = {"2022-01-31": {a: 0.25 for a in "ABCD"}}
    account = study._account(periods, weights, 0.001, tuple("ABCD"), bars, calendar, 1.0)
    assert account["months"][0]["net_return"] == pytest.approx(1 / 1.001 - 1)
    assert account["performance"]["terminal_wealth"] == pytest.approx(1 / 1.001)
    assert account["performance"]["total_fees"] == pytest.approx(1 - 1 / 1.001)


def test_ic_ties_and_circular_interval_deterministic():
    assert study._spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1)
    assert study._spearman([1, 1, 1, 1], [4, 3, 2, 1]) is None
    _, design = fixture_data()
    assert study._bootstrap([0, 1, 2, -1, 0.5], design) == study._bootstrap([0, 1, 2, -1, 0.5], design)


def test_winner_ties_fractional_and_positive_extreme_quartile():
    _, design = fixture_data()
    returns = [
        {"A": .1, "B": 0, "C": .1, "D": -.1},
        {"A": 0, "B": .2, "C": -.1, "D": -.1},
        {"A": .05, "B": 0, "C": .3, "D": -.1},
        {"A": .01, "B": .02, "C": .4, "D": -.1},
    ]
    periods = [{"signal": f"2022-0{i}-28", "asset_returns": r} for i, r in enumerate(returns, 1)]
    chosen = {"A": .5, "B": .5, "C": 0, "D": 0}
    months = [{"net_return": 0, "weights": chosen} for _ in periods]
    paired = study._paired({"months": months}, {"months": months}, periods, {},
                           tuple("ABCD"), design)
    assert paired["best_etf_selected_numerator"] == pytest.approx(1.5)
    assert paired["best_etf_selected_denominator"] == 4
    extreme = paired["top_quartile_positive_winner_capture"]
    assert extreme["positive_maximum_75th_percentile"] == pytest.approx(.325)
    assert extreme["extreme_months"] == 1
    assert extreme["rate"] == 0
