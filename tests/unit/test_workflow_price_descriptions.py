from copy import deepcopy

import pytest

from lei_signal.research.workflow_inputs import _label
from lei_signal.research.workflow_descriptions import summarize_price_groups


def test_next_close_price_anchor_and_distinct_path_losses():
    prices = [100, 110, 100, 121]
    rows = [{"date": f"2022-01-0{i+3}", "status": "quoted", "close": p, "action_known": True} for i, p in enumerate(prices)]
    target = {"kind": "forward_return", "start_offset": 1, "end_offset": 3, "entry_field": "close"}
    assert _label(rows, 0, target)[0] == pytest.approx(10)
    assert _label(rows, 0, {**target, "kind": "mae"})[0] == pytest.approx(100 / 11)
    assert _label(rows, 0, {**target, "kind": "mfe"})[0] == pytest.approx(10)
    assert _label(rows, 0, {**target, "kind": "max_drawdown"})[0] == pytest.approx(100 / 11)
    assert _label(rows[:3], 0, target)[2] == "immature_label"


def test_provider_price_flag_is_not_corporate_action_certification():
    rows = [{"date": f"2022-01-0{i+3}", "status": "quoted", "close": 100 + i,
             "action_known": False, "provider_price_known": True, "price_series": "provider_index_price"} for i in range(4)]
    target = {"kind": "forward_return", "start_offset": 1, "end_offset": 3, "entry_field": "close"}
    assert _label(rows, 0, target)[2] == "action_unknown"
    assert _label(rows, 0, {**target, "price_measure": "provider_index_price"})[0] == pytest.approx(200 / 101)


def test_absent_common_background_is_not_a_zero_increment():
    dates = [f"2022-01-{d:02d}" for d in range(3, 11)]
    bars = [{"asset": a, "date": d, "status": "quoted", "close": 100 * growth**i, "action_known": True}
            for a, growth in [("A", 1.01), ("B", 1.03)] for i, d in enumerate(dates)]
    obs = [{"id": f"{a}|{d}", "asset": a, "date": d, "stratum": f"{a}|2022", "feature_reason": None,
            "distance_group": group} for a, group in [("A", "inside"), ("B", "far_above")] for d in dates[:6]]
    contract = {"universe": {"assets": ["A", "B"]}, "target": {"kind": "forward_return", "start_offset": 1,
                "end_offset": 2, "entry_field": "close"}, "descriptive": {"horizons": [1],
                "groups": ["inside", "far_above"], "minimum_each_background": 3},
                "split": {"folds": [{"eval_start": "2024-01-01", "eval_end": "2024-12-31"}]}}
    result = summarize_price_groups(obs, {"calendar": dates, "bars": bars}, contract)
    overall = next(r for r in result["tables"] if r["phase"] == "all" and r["group"] == "all")
    assert overall["rows"] == 12
    assert overall["values"]["return"] == pytest.approx(2)
    assert overall["values"]["up"] == 1
    comparison = next(r for r in result["common_background_comparisons"] if r["phase"] == "all" and r["group"] == "inside")
    assert comparison["difference"] is None
    assert comparison["left"] is None
    assert comparison["lost_rows"] == 12
    assert comparison["retained_rows"] == 0
