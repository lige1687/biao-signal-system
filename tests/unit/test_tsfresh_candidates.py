"""Formula and temporal-boundary checks for the optional two-calculator preview."""

import importlib.util
import math
import sys
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / ".agents/skills/lei-quant-tools/scripts"
for module in ("tsfresh_calculators", "tsfresh_candidates"):
    spec = importlib.util.spec_from_file_location(module, SCRIPTS / f"{module}.py")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[module] = loaded
    spec.loader.exec_module(loaded)
core = sys.modules["tsfresh_calculators"]
preview = sys.modules["tsfresh_candidates"].candidate_preview


def packet(n=50):
    days = [(date(2025, 1, 1) + timedelta(days=2 * i)).isoformat() for i in range(n)]
    return {
        "schema": "tsfresh-candidate-input/1.0",
        "data_mode": "synthetic",
        "price_series": "economic_price",
        "source_note": "artificial declared two-day calendar",
        "calendar": days,
        "assets": ["A", "B"],
        "bars": [
            {
                "date": d,
                "asset": a,
                "status": "quoted",
                "action_known": True,
                "close": 100 * math.exp((i % 2) * 0.01),
            }
            for a in ["A", "B"]
            for i, d in enumerate(days)
        ],
    }


def first(data, when=None):
    return preview(data, when or data["calendar"][-1])["rows"][0]


def test_independent_four_point_arithmetic():
    a = np.array([1.0, -1.0, 1.0, -1.0])
    b = np.array([1.0, 1.0, -1.0, -1.0])
    c = np.array([math.sqrt(2), -math.sqrt(2), 0.0, 0.0])
    for x in [a, b, c]:
        assert sum(x) == pytest.approx(0)
        assert sum(x * x) == pytest.approx(4)
    assert [core.autocorrelation(x, 1) for x in [a, b, c]] == pytest.approx([-1, 1 / 3, -2 / 3])
    assert [core.mean_abs_change(np.r_[0, x.cumsum()]) for x in [a, b, c]] == pytest.approx(
        [1, 1, math.sqrt(2) / 2]
    )


def test_twenty_return_arithmetic_and_baselines():
    row = first(packet(21))
    assert row["values"] == pytest.approx(
        {"mean_abs_log_change20": 1, "return_autocorrelation20_lag1": -1}
    )
    assert row["baseline"]["ret20_pct"] == pytest.approx(0, abs=1e-10)
    assert row["baseline"]["vol20_annualized_pct"] == pytest.approx(math.sqrt(20 / 19 * 252))


def test_future_changes_and_future_append_do_not_change_past():
    data = packet(40)
    cutoff = data["calendar"][25]
    expected = first(data, cutoff)
    truncated = deepcopy(data)
    truncated["calendar"] = truncated["calendar"][:26]
    truncated["bars"] = [r for r in truncated["bars"] if r["date"] <= cutoff]
    assert first(truncated, cutoff) == expected
    for r in data["bars"]:
        if r["date"] > cutoff:
            r["close"] = 10000000
            r["action_known"] = False
    assert first(data, cutoff) == expected


def test_rescale_and_asset_isolation():
    data = packet()
    base = first(data)
    for r in data["bars"]:
        r["close"] *= 8192 if r["asset"] == "A" else 0.001
    changed = first(data)
    assert changed["values"] == pytest.approx(base["values"], abs=1e-10)
    assert changed["baseline"] == pytest.approx(base["baseline"], abs=1e-10)
    data["bars"] = [r for r in data["bars"] if r["asset"] == "B"]
    rows = preview(data, data["calendar"][-1])["rows"]
    assert rows[0]["status"] == "unknown"
    assert rows[1]["values"]["mean_abs_log_change20"] == pytest.approx(1)


@pytest.mark.parametrize(
    "break_kind", ["missing", "halt", "vendor_missing", "action", "zero", "nan", "bool", "huge"]
)
def test_break_requires_twenty_one_new_prices(break_kind):
    data = packet(50)
    bar = data["bars"][25]
    if break_kind == "missing":
        data["bars"].remove(bar)
    elif break_kind in {"halt", "vendor_missing"}:
        bar["status"] = break_kind
    elif break_kind == "action":
        bar["action_known"] = False
    else:
        bar["close"] = {"zero": 0, "nan": float("nan"), "bool": True, "huge": 10**1000}[break_kind]
    assert first(data, data["calendar"][45])["status"] == "unknown"
    assert first(data, data["calendar"][46])["status"] == "available"


@pytest.mark.parametrize("size", [1, 20])
def test_insufficient_history_is_unknown(size):
    assert first(packet(size))["values"] is None


@pytest.mark.parametrize("step", [0, 1e-6])
def test_constant_or_near_zero_variance_is_partial(step):
    data = packet(21)
    for i, r in enumerate(data["bars"][:21]):
        r["close"] = 100 * math.exp((i % 2) * step / 100)
    row = first(data)
    assert row["status"] == "partial"
    assert row["values"]["return_autocorrelation20_lag1"] is None
    assert row["values"]["mean_abs_log_change20"] == pytest.approx(step, abs=1e-10)


@pytest.mark.parametrize(
    "problem",
    [
        "date_duplicate",
        "date_unsorted",
        "bar_duplicate",
        "outside_date",
        "asset_duplicate",
        "outside_asset",
        "mode",
        "price_series",
        "note",
    ],
)
def test_ambiguous_input_is_rejected(problem):
    data = packet()
    if problem == "date_duplicate":
        data["calendar"].append(data["calendar"][-1])
    elif problem == "date_unsorted":
        data["calendar"].reverse()
    elif problem == "bar_duplicate":
        data["bars"].append(data["bars"][0])
    elif problem == "outside_date":
        data["bars"][0]["date"] = "2024-01-01"
    elif problem == "asset_duplicate":
        data["assets"].append("A")
    elif problem == "outside_asset":
        data["bars"][0]["asset"] = "C"
    elif problem == "mode":
        data["data_mode"] = "live"
    elif problem == "price_series":
        data["price_series"] = "raw"
    elif problem == "note":
        data["source_note"] = ""
    with pytest.raises(ValueError):
        first(data)


def test_does_not_fallback_to_an_earlier_date():
    with pytest.raises(ValueError, match="as_of"):
        first(packet(), "2025-01-02")
