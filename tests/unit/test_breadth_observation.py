"""Descriptive breadth observations: no real quotes, network, or strategy simulation."""
from __future__ import annotations

import copy
import importlib
import importlib.util
import math
from datetime import date, timedelta

import pandas as pd
import pytest

from lei_signal.market_context.breadth import rolling_percentile_at


def _build(history, market_id="CN_ALL_A", **kwargs):
    name = "lei_signal.market_context.breadth_observation"
    assert importlib.util.find_spec(name) is not None, "breadth observation reader is missing"
    return importlib.import_module(name).build_breadth_observation(history, market_id, **kwargs)


def _rows(values, *, b50=None, b200=None):
    return [
        {"date": (date(2010, 1, 1) + timedelta(days=i)).isoformat(),
         "breadth_20": value,
         "breadth_50": value if b50 is None else b50[i],
         "breadth_200": value if b200 is None else b200[i]}
        for i, value in enumerate(values)
    ]


def test_warmup_quantiles_and_percentile_use_actual_valid_count():
    rows = _rows([float(i % 101) for i in range(252)])
    result = _build(rows)
    assert result["lookback_observations"] == 1260
    assert result["min_observations"] == 252
    assert result["lower_quantile"] == 0.1
    assert result["upper_quantile"] == 0.9
    assert result["includes_current"] is True
    prior = result["history"][250]["horizons"]["20"]
    assert prior["status"] == "insufficient"
    assert prior["sample_count"] == 251
    assert prior["lower"] is None
    last = result["latest"]["horizons"]["20"]
    values = pd.Series([row["breadth_20"] for row in rows])
    assert last["status"] == "ready"
    assert last["sample_count"] == 252
    assert last["lower"] == pytest.approx(values.quantile(.1))
    assert last["median"] == pytest.approx(values.quantile(.5))
    assert last["upper"] == pytest.approx(values.quantile(.9))


def test_prefix_is_unchanged_and_matches_existing_less_equal_rank():
    rows = _rows([float(i % 101) for i in range(1310)])
    before = _build(rows[:1301])
    after = _build(rows)
    assert before["history"] == after["history"][:1301]
    series = pd.Series([r["breadth_20"] for r in rows],
                       index=pd.to_datetime([r["date"] for r in rows]))
    for i in (251, 900, 1300):
        expected = rolling_percentile_at(
            series, as_of=date.fromisoformat(rows[i]["date"]),
            lookback=1260, min_periods=252,
        )
        horizon = after["history"][i]["horizons"]["20"]
        assert horizon["percentile"] == pytest.approx(expected)
        assert horizon["sample_count"] == min(i + 1, 1260)


def test_missing_invalid_values_and_horizons_do_not_share_warmup():
    rows = _rows([40.0] * 252)
    rows[100]["breadth_50"] = None
    rows[-1]["breadth_200"] = math.inf
    original = copy.deepcopy(rows)
    result = _build(rows)
    assert rows == original
    last = result["latest"]["horizons"]
    assert last["20"]["status"] == "ready"
    assert last["50"]["status"] == "insufficient"
    assert last["50"]["sample_count"] == 251
    assert last["200"]["status"] == "missing"
    assert last["200"]["sample_count"] == 251
    for field in ("lower", "median", "upper", "percentile", "delta_5"):
        assert last["200"][field] is None


@pytest.mark.parametrize("bad", [-.01, 100.01, math.nan, math.inf, True, "50"])
def test_non_percentage_values_are_missing(bad):
    result = _build(_rows([50.0] * 252 + [bad]))
    horizon = result["latest"]["horizons"]["20"]
    assert horizon["status"] == "missing"
    assert horizon["position"] == "unknown"
    assert horizon["event"] == "unknown"
    assert result["latest"]["state"]["code"] == "unknown"


def test_constant_history_is_flat_not_both_extremes():
    result = _build(_rows([50.0] * 253))
    horizon = result["latest"]["horizons"]["20"]
    assert horizon["lower"] == horizon["median"] == horizon["upper"] == 50
    assert horizon["percentile"] == 100
    assert horizon["position"] == "flat"
    assert horizon["event"] == "none"
    assert result["latest"]["state"]["code"] == "flat"


@pytest.mark.parametrize(("value", "position", "event"), [
    (0.0, "low", "enter_low"), (100.0, "high", "enter_high"),
])
def test_collapsed_band_keeps_current_outside_visible(value, position, event):
    result = _build(_rows([50.0] * 252 + [value]))
    horizon = result["latest"]["horizons"]["20"]
    assert horizon["lower"] == horizon["median"] == horizon["upper"] == 50
    assert horizon["position"] == position
    assert horizon["event"] == event


def test_five_record_delta_uses_original_dates_not_nonmissing_rows():
    rows = _rows([10, 20, 30, 40, 50, 60, 70])
    rows[1]["breadth_50"] = None
    result = _build(rows)
    assert result["history"][4]["horizons"]["20"]["delta_5"] is None
    assert result["latest"]["horizons"]["20"]["delta_5"] == 50
    assert result["latest"]["horizons"]["50"]["delta_5"] is None
    assert result["latest"]["state"]["code"] == "unknown"


def test_valid_observation_window_does_not_count_missing_rows():
    values = [float(i % 101) for i in range(1261)]
    values.insert(1255, None)
    result = _build(_rows(values))
    last = result["latest"]["horizons"]["20"]
    expected = pd.Series([v for v in values if v is not None][-1260:])
    assert last["sample_count"] == 1260
    assert last["lower"] == pytest.approx(expected.quantile(.1))
    assert last["upper"] == pytest.approx(expected.quantile(.9))


def test_events_enter_stay_exit_and_do_not_cross_missing_or_warmup():
    base = [float(i % 101) for i in range(252)]
    values = base + [100, 100, 50, 0, 0, 50, None, 100, 100]
    result = _build(_rows(values))
    events = [r["horizons"]["20"]["event"] for r in result["history"]]
    assert events[251] == "unknown"
    assert events[252:] == ["enter_high", "stay_high", "exit_high", "enter_low",
                            "stay_low", "exit_low", "unknown", "unknown", "stay_high"]


@pytest.mark.parametrize(
    ("values", "b200", "market_id", "code"),
    [([10, 20, 35, 45, 55, 60], [70] * 6, "CN_ALL_A", "recovering"),
     ([18, 25, 35, 45, 55, 60], [70] * 6, "SP500", "expanding"),
     ([30, 35, 40, 50, 55, 60], [70] * 6, "CN_ALL_A", "expanding"),
     ([25, 27, 30, 35, 40, 45], [70] * 6, "CN_ALL_A", "improving"),
     ([90, 85, 70, 60, 50, 40], [30] * 6, "CN_ALL_A", "retreating"),
     ([70, 65, 60, 55, 50, 40], [30] * 6, "CN_ALL_A", "weakening"),
     ([70, 65, 60, 55, 50, 40], [70] * 6, "CN_ALL_A", "contracting"),
     ([60] * 6, [70] * 6, "CN_ALL_A", "flat"),
     ([30, 35, 40, 50, 55, 60], [None] * 6, "CN_ALL_A", "improving")],
)
def test_state_is_breadth_only_and_recent_extreme_has_priority(values, b200, market_id, code):
    state = _build(_rows(values, b200=b200), market_id)["latest"]["state"]
    assert state["code"] == code
    assert state["tone"] in {"supportive", "caution", "neutral", "unknown"}
    assert not any(word in state["summary"] for word in ["买入", "卖出", "确认顶", "确认底"])
    if b200[-1] is None:
        assert "200日" in state["summary"] and "不足" in state["summary"]


def test_mixed_direction_is_not_confirmation():
    state = _build(_rows([30, 35, 40, 50, 55, 60], b50=[70, 65, 60, 55, 50, 40]))
    assert state["latest"]["state"]["code"] == "mixed"


@pytest.mark.parametrize("dates", [
    ["2024-01-02", "2024-01-02"], ["2024-01-03", "2024-01-02"],
    ["2024-01-02", "2024-02-30"], ["2024-01-02", "20240103"],
    ["2024-01-02", None],
])
def test_invalid_date_axis_is_explicit_without_mutating_original(dates):
    rows = _rows([30, 40])
    for row, day in zip(rows, dates, strict=True):
        row["date"] = day
    original = copy.deepcopy(rows)
    result = _build(rows)
    assert rows == original
    assert result["error"] == "invalid_date_axis"
    assert result["history"] == []
    assert result["latest"] is None


def test_empty_history_is_honest():
    result = _build([])
    assert result["history"] == []
    assert result["latest"] is None


def test_tail_limits_transport_only_and_keeps_full_history_warmup():
    rows = _rows([float(i % 101) for i in range(1400)])
    full = _build(rows)
    tail = _build(rows, tail_observations=30)
    assert tail["history"] == full["history"][-30:]
    assert tail["latest"] == full["latest"]
    assert tail["history"][0]["horizons"]["20"]["status"] == "ready"
    assert tail["history"][0]["horizons"]["20"]["sample_count"] == 1260
    assert tail["total_observations"] == full["total_observations"] == 1400
    assert full["returned_observations"] == 1400
    assert tail["returned_observations"] == 30
    assert _build(rows, tail_observations=2000)["history"] == full["history"]
