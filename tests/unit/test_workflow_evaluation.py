"""Hand-calculated good/bad pairs for the shared research-only evaluator."""
from copy import deepcopy
import ast
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.workflow_evaluation import (
    EvaluationError, evaluate_observations, summarize_predictions,
)


def contract(binary=False, policy="equal_asset", kind="prediction_ridge"):
    return {
        "target": {"kind": "up" if binary else "forward_return", "unit": "probability" if binary else "percentage_point"},
        "evaluator": {"kind": kind, "version": "1.0.0", "baseline_features": ["lag_return"], "added_features": ["added"], "lambda": 1.0},
        "split": {"folds": [{"train_end": "2022-01-03", "eval_start": "2022-01-04", "eval_end": "2022-01-06"}], "label_policy": "purge"},
        "weights": {"policy": policy, "comparison": "fixed_common"},
        "dependence": {"block_length": 2, "draws": 40, "seed": 7},
        "calendar": [f"2022-01-{i:02}" for i in range(1, 8)],
    }


def obs(asset, day, y, lag=0., added=0., condition=False, eligible=True, end=None):
    d = f"2022-01-{day:02}"
    return {"id": f"{asset}:{d}", "asset": asset, "date": d, "stratum": f"{asset}|2022", "features": {"lag_return": lag, "added": added, "existing_state": float(lag > 0)}, "eligible": eligible, "y": y, "label_end": end or d, "label_reason": None if eligible else "vendor_missing", "tested_condition": condition}


def prediction(asset, day, y, b0=0., b1=0., b2=0., binary=False):
    r = {key: value for key, value in obs(asset, day, y).items() if key in {"id", "asset", "date", "y", "label_end"}}
    r.update(fold="0", B0=b0, B1=b1, B2=b2)
    if binary:
        r["B50"] = .5
    return r


def value(result, model, metric="MSE"):
    return next(r["value"] for r in result["performance"] if r["model"] == model and r["metric"] == metric)


def test_year_direction_reversal_and_few_dates_warn_not_fail():
    c=contract();c["split"]["folds"].append({"train_end":"2023-01-03","eval_start":"2023-01-04","eval_end":"2023-01-06"})
    rows=[prediction("a",4,1,0,0,1),prediction("a",4,0,0,0,1)]
    rows[1].update(id="a:2023-01-04",date="2023-01-04",label_end="2023-01-04",fold="1")
    c["calendar"]+=['2023-01-04','2023-01-05','2023-01-06']
    result=summarize_predictions(rows,c)
    assert len(result["period_comparisons"])==2
    assert any("year sign reversal" in s for s in result["warnings"])
    assert any("few date blocks" in s for s in result["warnings"])


def test_weighting_good_bad_pair_and_units():
    rows = [prediction("a", 4, 2), prediction("a", 5, 2), prediction("b", 4, 4)]
    good = summarize_predictions(rows, contract())
    # a MSE4, b MSE16: assets get 1/2 each, not pooled 8.
    assert value(good, "B0") == pytest.approx(10)
    assert value(good, "B0", "RMSE") == pytest.approx(np.sqrt(10))
    assert good["performance"][0]["unit"] == "percentage_point_squared"
    assert summarize_predictions(rows, contract(policy="equal_date"))["performance"][0]["value"] == pytest.approx(7)
    bad = contract(); bad["weights"]["comparison"] = "own_group"
    with pytest.raises(EvaluationError, match="fixed_common"):
        summarize_predictions(rows, bad)
    bad = contract(); bad["target"]["unit"] = "probability"
    with pytest.raises(EvaluationError, match="unit"):
        summarize_predictions(rows, bad)


def test_b50_exact_and_bad_probability_labels_baselines():
    rows = [prediction("a", 4, 1, .3, .7, .4, True), prediction("b", 4, 0, .3, .7, .4, True), prediction("b", 5, 0, .3, .7, .4, True)]
    result = summarize_predictions(rows, contract(True))
    assert value(result, "B50", "Brier") == .25
    assert result["execution"]["fits"] == 0
    for column, replacement in [("B50", .6), ("B2", 1.2), ("y", .2), ("B1", float("nan"))]:
        bad = deepcopy(rows); bad[0][column] = replacement
        with pytest.raises(EvaluationError):
            summarize_predictions(bad, contract(True))
    bad = deepcopy(rows); del bad[0]["B0"]
    with pytest.raises(EvaluationError, match="baseline"):
        summarize_predictions(bad, contract(True))


def test_negative_complex_prediction_warns_and_does_not_fail():
    rows = [prediction("a", 4, 0, 0, 0, 3), prediction("b", 5, 0, 0, 0, 3)]
    result = summarize_predictions(rows, contract())
    assert value(result, "B2") == 9
    assert result["increments"][1]["relative_percent"] is None  # zero base loss
    assert any("underperforms B0" in warning for warning in result["warnings"])
    json.dumps(result, allow_nan=False)


def test_paired_identity_missing_model_duplicate_and_correct_observation():
    rows = [prediction("a", 4, 1), prediction("b", 5, 0)]
    observations = [obs("a", 4, 1), obs("b", 5, 0)]
    assert summarize_predictions(rows, contract(), observations)["descriptions"]["common_prediction_rows"] == 2
    with pytest.raises(EvaluationError, match="duplicate"):
        summarize_predictions(rows + [rows[0]], contract())
    wrong = deepcopy(rows); wrong[0]["y"] = 2
    with pytest.raises(EvaluationError, match="identity/target"):
        summarize_predictions(wrong, contract(), observations)
    wrong = deepcopy(rows); wrong[0]["fold"] = "another"
    with pytest.raises(EvaluationError, match="fold/date"):
        summarize_predictions(wrong, contract())


def test_training_only_standardization_and_fixed_lambda_hand_example():
    rows = [obs("a", 1, 1, lag=0), obs("a", 2, 3, lag=2), obs("a", 4, 5, lag=4, added=999)]
    result = evaluate_observations(rows, contract())
    # Training x mean1/std1, ymean2; normalized lambda1 gives slope .5.
    assert result["predictions"][0]["B0"] == 2
    assert result["predictions"][0]["B1"] == pytest.approx(3.5)
    fit = result["execution"]["fit_details"][0]
    assert fit["mean"] == [1]
    assert fit["std"] == [1]
    assert fit["coef"] == pytest.approx([.5])
    # Changing eval-only features cannot alter training preprocessing.
    changed = deepcopy(rows); changed[-1]["features"]["lag_return"] = 400
    changed_fit = evaluate_observations(changed, contract())["execution"]["fit_details"][0]
    assert changed_fit["mean"] == fit["mean"]
    assert changed_fit["coef"] == fit["coef"]
    bad = contract(); bad["evaluator"]["lambda"] = .1
    with pytest.raises(EvaluationError, match="lambda"):
        evaluate_observations(rows, bad)


def test_maturity_boundary_good_purge_bad_require_mature_pre_fit():
    rows = [obs("a", 1, 1), obs("a", 2, 3, end="2022-01-04"), obs("a", 4, 2)]
    result = evaluate_observations(rows, contract())
    assert result["execution"]["purged_rows"] == 1
    assert result["predictions"][0]["B0"] == 1
    bad = contract(); bad["split"]["label_policy"] = "require_mature"
    with patch("lei_signal.research.workflow_evaluation._ridge") as numerical_fit:
        with pytest.raises(EvaluationError, match="strictly mature"):
            evaluate_observations(rows, bad)
        numerical_fit.assert_not_called()
    bad = contract(); bad["split"]["folds"][0]["train_end"] = "2022-01-04"
    with pytest.raises(EvaluationError, match="precede"):
        evaluate_observations(rows, bad)


def test_validation_of_all_folds_occurs_before_any_fit():
    rows = [obs("a", 1, 1), obs("a", 4, 2), obs("a", 5, 3, end="2022-01-07"), obs("a", 6, 4)]
    c = contract(); c["split"] = {"label_policy": "require_mature", "folds": [{"train_end": "2022-01-01", "eval_start": "2022-01-04", "eval_end": "2022-01-04"}, {"train_end": "2022-01-05", "eval_start": "2022-01-06", "eval_end": "2022-01-07"}]}
    with patch("lei_signal.research.workflow_evaluation._ridge") as numerical_fit:
        with pytest.raises(EvaluationError, match="strictly mature"):
            evaluate_observations(rows, c)
        numerical_fit.assert_not_called()


def test_event_frequency_fallback_not_ridge_and_binary_only():
    rows = [obs("a", 1, 0, lag=-1, added=0), obs("a", 2, 1, lag=-1, added=1), obs("a", 3, 1, lag=1, added=0), obs("a", 4, 0, lag=1, added=1)]
    c = contract(True, kind="event_risk")
    with patch("lei_signal.research.workflow_evaluation._ridge") as ridge:
        result = evaluate_observations(rows, c)
        ridge.assert_not_called()
    r = result["predictions"][0]
    assert r["B0"] == pytest.approx(2/3)
    assert r["B1"] == 1
    assert r["B2"] == pytest.approx(2/3)  # absent (existing_state=1,event=1)
    assert result["execution"]["fit_details"][1]["fallback_rows"] == 1
    bad = contract(kind="event_risk")
    with pytest.raises(EvaluationError, match="binary"):
        evaluate_observations(rows, bad)
    badrows = deepcopy(rows); badrows[0]["features"]["added"] = .2
    with pytest.raises(EvaluationError, match="binary event"):
        evaluate_observations(badrows, c)


def test_full_axis_sync_blocks_not_compressed_and_fixed_assets_missing_draws():
    rows = [prediction("a", 4, 1, 0, 0, 1), prediction("b", 6, 0, 0, 0, 1)]
    result = summarize_predictions(rows, contract())
    assert result["increments"][0]["calendar_dates"] == 7
    assert result["increments"][0]["unestimable_draws"] > 0
    assert result == summarize_predictions(rows, contract())
    # Both assets on identical dates, opposite improvements cancel in every draw.
    paired = [prediction("a", 4, 1, 0, 0, 1), prediction("b", 4, 0, 0, 0, 1)]
    synced = summarize_predictions(paired, contract())
    assert synced["increments"][0]["lo"] == 0
    assert synced["increments"][0]["hi"] == 0
    bad = contract(); del bad["calendar"]
    with pytest.raises(EvaluationError, match="full calendar"):
        summarize_predictions(rows, bad)
    # Full observation dates are accepted with matching eligible prediction rows.
    full = [obs("a", day, None, eligible=False) for day in range(1, 8) if day != 4] + [obs("a", 4, 1)]
    assert summarize_predictions([paired[0]], bad, full)["increments"][0]["calendar_dates"] == 7


def test_natural_description_and_fixed_common_years_are_distinct():
    rows = [obs("a", 4, 0, condition=False), obs("a", 5, 10, condition=True), obs("b", 4, 100, condition=True)]
    predictions = [prediction(r["asset"], int(r["date"][-2:]), r["y"]) for r in rows]
    result = summarize_predictions(predictions, contract(), rows)
    d = result["descriptions"]
    assert d["own_group"][1]["mean"] == 55  # different products => not net increment
    assert d["fixed_common_means"]["difference"] == 10  # only a has both states
    assert d["fixed_common_means"]["baseline"] == 5
    assert d["fixed_common_means"]["identity_error"] == 0
    assert d["unsupported_strata"][0]["asset"] == "b"
    bad = deepcopy(rows); bad[0]["tested_condition"] = True
    no_support = summarize_predictions(predictions, contract(), bad)
    assert no_support["descriptions"]["comparison_available"] is False
    assert any("common support absent" in warning for warning in no_support["warnings"])


def test_common_asset_year_weights_and_valid_mixture_outside_group_range():
    c = contract(); c["calendar"] = ["2022-01-04", "2022-01-05", "2023-01-04", "2023-01-05", "2023-01-06"]
    c["split"]["folds"][0]["eval_end"] = "2023-01-06"
    rows = [obs("a", 4, 0, condition=False), obs("a", 5, 10, condition=True)]
    for day, y, condition in [(4, 10, False), (5, 0, True), (6, 10, False)]:
        r = obs("a", day, y, condition=condition)
        r.update(date=f"2023-01-{day:02}", id=f"a:2023-01-{day:02}", label_end=f"2023-01-{day:02}", stratum="a|2023")
        rows.append(r)
    predictions = []
    for r in rows:
        p = {k: r[k] for k in ("id", "asset", "date", "label_end", "y")}; p.update(fold="0", B0=0, B1=0, B2=0); predictions.append(p)
    d = summarize_predictions(predictions, c, rows)["descriptions"]
    assert d["fixed_common_means"]["condition0"] == 5
    assert d["fixed_common_means"]["condition1"] == 5
    assert d["fixed_common_means"]["baseline"] == pytest.approx(35/6)
    assert d["fixed_common_means"]["identity_error"] == pytest.approx(0)


def test_pure_reaggregation_changes_weights_without_fitting():
    rows = [prediction("a", 4, 2), prediction("a", 5, 2), prediction("b", 4, 4)]
    with patch("lei_signal.research.workflow_evaluation._ridge") as ridge:
        a = summarize_predictions(rows, contract())
        b = summarize_predictions(rows, contract(policy="equal_date"))
        ridge.assert_not_called()
    assert a["execution"]["fits"] == b["execution"]["fits"] == 0
    assert a["predictions"] == b["predictions"]
    assert value(a, "B0") != value(b, "B0")


def test_training_weights_are_separate_from_aggregation_and_bad_policy_rejected():
    rows = [obs("a", 1, 1, lag=0), obs("a", 2, 3, lag=2), obs("b", 1, 6, lag=4), obs("a", 4, 2, lag=3), obs("a", 5, 2, lag=4), obs("b", 4, 5, lag=6)]
    a = evaluate_observations(rows, contract())
    b = evaluate_observations(rows, contract(policy="equal_date"))
    assert a["predictions"] == b["predictions"]
    assert a["predictions"][0]["B0"] == 4  # train equal_asset by default
    changed_training = contract(); changed_training["training_weights"] = "equal_date"
    c = evaluate_observations(rows, changed_training)
    assert c["predictions"][0]["B0"] == 3.25
    assert c["predictions"] != a["predictions"]
    assert a["execution"]["fit_details"][0]["training_weights"] == "equal_asset"
    bad = contract(); bad["training_weights"] = "pooled"
    with pytest.raises(EvaluationError, match="training_weights"):
        evaluate_observations(rows, bad)


def test_old_ridge_expression_common_domain_from_archived_source_only_in_test():
    # Read the actual old functions without importing/executing its runner.
    archive = Path(__file__).resolve().parents[2] / "docs/experiments/raw/a01-guide-study-2026-09-29/execution/run.py"
    tree = ast.parse(archive.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"weights", "fit_predict"}]
    assert len(nodes) == 2
    namespace = {"np": np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(archive), "exec"), namespace)
    rows = [obs("a", 1, 1, lag=0, added=10), obs("a", 2, 3, lag=2, added=0), obs("b", 1, 6, lag=4, added=1), obs("a", 4, 4, lag=3, added=2), obs("b", 4, 5, lag=6, added=3)]
    result = evaluate_observations(rows, contract())
    flat = pd.DataFrame([{**r, **r["features"]} for r in rows])
    train, ev = flat[flat.date < "2022-01-04"], flat[flat.date >= "2022-01-04"]
    for model, cols in [("B1", ["lag_return"]), ("B2", ["lag_return", "added"])]:
        old_prediction, old_fit = namespace["fit_predict"](train, ev, cols, "y")
        assert [r[model] for r in result["predictions"]] == pytest.approx(old_prediction, abs=1e-12)
        fit = next(r for r in result["execution"]["fit_details"] if r["model"] == model)
        assert fit["mean"] == pytest.approx(old_fit["mean"])
        assert fit["std"] == pytest.approx(old_fit["std"])
        assert fit["coef"] == pytest.approx(old_fit["coef"])


def test_sealed_a02_217_binary_scores_reaggregation_only():
    # The frozen historical fixture is reused only for arithmetic regression.
    # Do not resample its intervals or write new research artifacts.
    root = Path(__file__).resolve().parents[2]
    sealed = root / "docs/experiments/raw/a02-sma-maintenance-2026-09-29/execution/attempt1"
    stored = pd.read_csv(sealed / "predictions.csv")
    stored = stored[(stored.scope == "main") & (stored.N == 60) & (stored.freq == "W") & (stored.h == 20) & (stored.target == "up")]
    wide = stored.pivot(index=["asset", "date", "year", "actual", "label_end"], columns="model", values="prediction").reset_index()
    assert len(wide) == 217 and wide.asset.nunique() == 4
    predictions = [{"id": f"{r.asset}|{r.date}", "asset": r.asset, "date": r.date, "fold": str(int(r.year) - 2024), "y": r.actual, "label_end": r.label_end, "B0": r.B0, "B1": r.B2, "B2": r.B2F, "B50": .5} for r in wide.itertuples()]
    calendar = json.loads((root / "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json").read_text())
    c = contract(True)
    c["calendar"] = sorted(d for d, flag in calendar["days"].items() if flag["is_trading_day"] and "2022-01-01" <= d <= "2026-06-30")
    c["split"]["folds"] = [{"train_end": f"{y-1}-12-31", "eval_start": f"{y}-01-01", "eval_end": f"{y}-12-31" if y < 2026 else "2026-06-30"} for y in [2024, 2025, 2026]]
    with patch("lei_signal.research.workflow_evaluation._ridge") as fit, patch("lei_signal.research.workflow_evaluation._block_draws", return_value=(np.array([0.]), 0)):
        result = summarize_predictions(predictions, c)
        fit.assert_not_called()
    assert value(result, "B0", "Brier") == pytest.approx(.26722664385736306, abs=1e-12)
    assert value(result, "B1", "Brier") == pytest.approx(.31855483799619455, abs=1e-12)
    assert value(result, "B2", "Brier") == pytest.approx(.31948388542914696, abs=1e-12)
    assert value(result, "B50", "Brier") == .25
    assert result["execution"]["fits"] == 0
    assert any("underperforms B50" in w for w in result["warnings"])


def test_future_label_and_nonconstant_b0_are_invalid_cached_predictions():
    rows = [prediction("a", 4, 1), prediction("b", 5, 0)]
    assert summarize_predictions(rows, contract())["execution"]["fits"] == 0
    bad = deepcopy(rows); bad[1]["B0"] = .1
    with pytest.raises(EvaluationError, match="constant training"):
        summarize_predictions(bad, contract())
    bad = deepcopy(rows); bad[0]["label_end"] = "2030-01-01"
    with pytest.raises(EvaluationError, match="dates"):
        summarize_predictions(bad, contract())


def test_policy_account_use_is_explicitly_blocked():
    c = contract(); c["question"] = {"layer": "decision_policy"}
    with pytest.raises(EvaluationError, match="not implemented"):
        summarize_predictions([prediction("a", 4, 0)], c)


def test_all_unestimated_is_finite_and_not_an_effect_failure():
    result = evaluate_observations([obs("a", 4, 1)], contract())
    assert result["performance"] == []
    assert result["execution"]["fits"] == 0
    assert any("not estimated" in warning for warning in result["warnings"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("mutation", ["duplicate_features", "missing_feature", "bad_stratum", "duplicate_observation"])
def test_malformed_inputs_block_before_fit(mutation):
    rows = [obs("a", 1, 1), obs("a", 4, 2)]
    c = contract()
    if mutation == "duplicate_features":c["evaluator"]["added_features"] = ["lag_return"]
    if mutation == "missing_feature":del rows[0]["features"]["added"]
    if mutation == "bad_stratum":rows[0]["stratum"] = "all assets pooled"
    if mutation == "duplicate_observation":rows.append(rows[0])
    with patch("lei_signal.research.workflow_evaluation._ridge") as numerical_fit:
        with pytest.raises(EvaluationError):evaluate_observations(rows, c)
        numerical_fit.assert_not_called()
