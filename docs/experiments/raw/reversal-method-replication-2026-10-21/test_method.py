"""Synthetic-only checks for the frozen reversal runner; no market inputs."""
from __future__ import annotations

import importlib.util
import inspect
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("reversal_run", HERE / "run.py")
RUN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUN)


def _features(n=31):
    return [
        {"code": f"sh.{i:06d}", "eligible": True, "hot": 0.0,
         "momentum": float(i), "vol60": float(i), "reasons": []}
        for i in range(n)
    ]


def test_tied_ranks_use_average_rank():
    assert RUN.average_ranks([1, 1, 3, 4]).tolist() == [1.5, 1.5, 3.0, 4.0]


def test_top_and_bottom_count_uses_ceiling_and_stable_tie_order():
    selected = RUN.select_exchange_month(_features(31))
    assert selected["k"] == 4
    assert selected["weights"]["loser"] == {
        f"sh.{i:06d}": .25 for i in range(4)
    }
    # With exact score ties, both tails use the frozen code tie-break.
    assert selected["weights"]["winner"] == {
        f"sh.{i:06d}": .25 for i in range(4)
    }
    assert math.isclose(sum(selected["weights"]["all"].values()), 1.0)


def test_selection_contract_has_no_future_outcome_argument():
    assert list(inspect.signature(RUN.prepare_selection).parameters) == ["features", "min_n"]
    before = RUN.prepare_selection(_features(30))
    # A radically changed label set cannot be passed into the selection API.
    after = RUN.prepare_selection(_features(30))
    assert before["weights"] == after["weights"]


def test_only_green_reasons_are_removed():
    row = {"eligible": False,
           "reasons": ["not_green", "green_unknown", "adjusted_price_break_in_window",
                       "decision_not_traded_or_st"]}
    result = RUN.remove_only_green_qualifiers(row)
    assert result["eligible"] is False
    assert result["original_reasons"] == sorted(row["reasons"])
    assert result["eligibility_reasons"] == ["adjusted_price_break_in_window",
                                              "decision_not_traded_or_st"]


def test_lag_endpoints_use_the_frozen_first_sessions():
    firsts = {f"2025-{m:02d}": f"2025-{m:02d}-02" for m in range(1, 13)}
    assert RUN.lag_endpoints("2025-09", 0, firsts) == ("2025-10-02", "2025-11-02")
    assert RUN.lag_endpoints("2025-09", 1, firsts) == ("2025-11-02", "2025-12-02")


def test_missing_returns_keep_original_weight_and_do_not_renormalize():
    result = RUN.weighted_month({"a": .5, "b": .5}, {
        "a": {"return": .10, "adverse": -.02, "opportunity": .12},
        "b": {"return": None, "adverse": None, "opportunity": None},
    })
    assert math.isclose(result["known_weighted_contribution"], .05)
    assert math.isclose(result["unknown_weight"], .5)
    assert result["complete_return"] is None


def test_portfolio_and_paired_difference_match_hand_calculation():
    returns = {"a": {"return": .10}, "b": {"return": -.02}}
    left = RUN.weighted_month({"a": .5, "b": .5}, returns)
    right = RUN.weighted_month({"a": 1.0}, returns)
    assert math.isclose(left["complete_return"], .04)
    assert math.isclose(right["complete_return"], .10)
    assert math.isclose(RUN._paired_difference(left, right, "complete_return"), -.06)


def test_cost_is_one_side_rate_times_gross_trading_and_unknown_stays_unknown():
    assert math.isclose(RUN.cost_at_25bps_per_side(.4, 1.0), .0035)
    assert RUN.cost_at_25bps_per_side(None, 1.0) is None


def test_turnover_never_relabels_unknown_previous_outcome_as_initial_buy():
    result = RUN.weighted_turnover({"a": .5, "b": .5}, {"a": {"return": .1}}, {"a": .5, "b": .5})
    assert result["traded_gross"] is None
    assert result["reason"] == "unknown_previous_outcome"


def test_rank_association_uses_intercept_and_two_controls_without_group_dummies():
    features = [
        {"code": f"c{i}", "eligible": True, "hot": float(i),
         "momentum": float(i), "vol60": float((i * 7) % 9)}
        for i in range(12)
    ]
    outcomes = {row["code"]: {"return": float(i % 4)} for i, row in enumerate(features)}
    result = RUN.ranked_association(features, outcomes)
    assert result["n"] == 12
    assert "partial_momentum_vol60" in result
    assert "full" not in result


def test_hac_summary_preserves_empty_calendar_slot():
    result = RUN.summarize_axis(["2024-01", "2024-02", "2024-03"], [1.0, None, 3.0], [])
    assert result["calendar_axis_length"] == 3
    assert result["missing_months"] == 1
    assert result["all"]["n"] == 2
    assert math.isclose(result["all"]["mean"], 2.0)


def test_comparison_only_returns_paired_complete_values():
    assert RUN._paired_difference({"complete_return": .04}, {"complete_return": .01},
                                  "complete_return") == .03
    assert RUN._paired_difference({"complete_return": None}, {"complete_return": .01},
                                  "complete_return") is None


def test_gross_and_net_comparisons_share_the_same_complete_cost_sample():
    gross, gross_on_net_sample, net = RUN.common_gross_net_difference(
        {"complete_return": .04, "after_cost_25bps": .02},
        {"complete_return": .01, "after_cost_25bps": -.01},
    )
    assert math.isclose(gross, .03)
    assert math.isclose(gross_on_net_sample, .03)
    assert math.isclose(net, .03)
    assert RUN.common_gross_net_difference(
        {"complete_return": .04, "after_cost_25bps": None},
        {"complete_return": .01, "after_cost_25bps": -.01},
    ) == (.03, None, None)


def test_first_qualified_month_is_initial_purchase_but_later_gap_is_unknown():
    first = RUN.rebalance_turnover(0, None, None, {"a": 1.0})
    assert first["traded_gross"] == 1.0
    assert first["reason"] == "initial_purchase"
    later_gap = RUN.rebalance_turnover(1, None, None, {"a": 1.0})
    assert later_gap["traded_gross"] is None
    assert later_gap["reason"] == "no_qualified_prior_month"


def test_runner_resolves_and_imports_helpers_from_design_bound_main_source():
    expected = (RUN.ROOT / "src").resolve()
    assert expected.is_dir()
    for module in (RUN.fip_module, RUN.high52_module,
                   RUN.output_storage_module, RUN.reversal_module):
        assert Path(module.__file__).resolve().is_relative_to(expected)


def run_all():
    checks = [value for name, value in sorted(globals().items())
              if name.startswith("test_") and callable(value)]
    for check in checks:
        check()
    print(f"synthetic checks passed: {len(checks)}")


if __name__ == "__main__":
    run_all()
