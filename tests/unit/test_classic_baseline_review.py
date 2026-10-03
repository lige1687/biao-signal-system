"""Fixed arithmetic and boundary checks; no market data or fitting."""
from copy import deepcopy
import pytest
from lei_signal.research.factor_lab.baseline_review import build_baseline_review


def case():
    c = {"target": {"kind": "forward_return", "unit": "percentage_point"},
         "split": {"label_policy": "purge", "folds": [{"train_end": "2022-01-03", "eval_start": "2022-01-05", "eval_end": "2022-01-07"}]},
         "weights": {"policy": "equal_asset", "comparison": "fixed_common"},
         "dependence": {"block_length": 1, "draws": 1, "seed": 0},
         "calendar": ["2022-01-03", "2022-01-04", "2022-01-05", "2022-01-06", "2022-01-07"]}
    rows = []
    for a, y in [("A", 0), ("B", 10)]:
        for d, end in [("2022-01-03", "2022-01-04"), ("2022-01-05", "2022-01-06")]:
            rows.append({"id": a+d, "asset": a, "date": d, "label_end": end,
                         "eligible": True, "y": y, "features": {}, "stratum": a+"|2022", "tested_condition": None, "label_reason": None})
    p = [{**{k: r[k] for k in ("id", "asset", "date", "label_end", "y")}, "fold": "0", "B0": 5, "B1": 4 if r["asset"] == "A" else 6, "B2": 2 if r["asset"] == "A" else 8} for r in rows if r["date"] == "2022-01-05"]
    return c, rows, p


def test_fixed_counterexample_and_no_fit(monkeypatch):
    from lei_signal.research import workflow_evaluation as e
    monkeypatch.setattr(e, "_ridge", lambda *a, **kw: pytest.fail("fitting forbidden"))
    monkeypatch.setattr(e, "_event", lambda *a, **kw: pytest.fail("fitting forbidden"))
    review = build_baseline_review(*case())
    assert {r["model"]: r["mse"] for r in review["performance"]} == {"B0":25, "B1":16, "B2":4, "asset_training_mean":0}
    assert review["increments"][-1]["absolute_error_improvement"] == -4
    assert review["increments"][-1]["relative_percent"] is None
    assert review["execution"]["fits"] == 0
    assert review["source_verification"] == "numeric_inputs_only"


def test_evaluation_y_never_changes_training_mean():
    c,r,p=case()
    original=build_baseline_review(c,r,p)["training_means"]
    for row in r:
        if row["date"] == "2022-01-05": row["y"] += 20
    for row in p: row["y"] += 20
    assert build_baseline_review(c,r,p)["training_means"] == original


@pytest.mark.parametrize("change", ["maturity", "missing", "duplicate", "identity", "nonfinite", "fold", "contained", "target", "weight"])
def test_invalid_pairs_rejected(change):
    c,r,p=case()
    if change == "maturity": r[0]["label_end"]="2022-01-05"
    elif change == "missing": p.pop()
    elif change == "duplicate": r.append(deepcopy(r[0]))
    elif change == "identity": p[0]["y"]=1
    elif change == "nonfinite": p[0]["B2"]=float("nan")
    elif change == "fold": p[0]["fold"]="1"
    elif change == "contained": c["split"]["evaluation_label_policy"]="contained"; c["split"]["folds"][0]["eval_end"]="2022-01-05"
    elif change == "target": c["target"]["kind"]="downside_event"
    else: c["weights"]["policy"]="custom"
    with pytest.raises(ValueError): build_baseline_review(c,r,p)


def test_maturity_require_policy_rejects_even_when_asset_has_other_training():
    c,r,p=case(); bad=deepcopy(r[0]); bad.update(id="later",date="2022-01-04",label_end="2022-01-05")
    r.append(bad); c["split"]["folds"][0]["train_end"]="2022-01-04"; c["split"]["label_policy"]="require_mature"
    with pytest.raises(ValueError,match="mature"): build_baseline_review(c,r,p)


def test_equal_asset_and_equal_date_are_actual_same_pair_weights():
    c,r,p=case(); row=deepcopy(r[1]);row.update(id="A-second",date="2022-01-06",label_end="2022-01-07")
    r.append(row); pred=deepcopy(p[0]);pred.update(id=row["id"],date=row["date"],label_end=row["label_end"],B2=4);p.append(pred)
    asset=build_baseline_review(c,r,p)
    c["weights"]["policy"]="equal_date"; day=build_baseline_review(c,r,p)
    assert next(x["mse"] for x in asset["performance"] if x["model"]=="B2") == 7
    assert next(x["mse"] for x in day["performance"] if x["model"]=="B2") == 10


def test_no_predictions_insufficient_only_when_no_evaluable_rows():
    c,r,p=case()
    with pytest.raises(ValueError,match="coverage"): build_baseline_review(c,r,[])
    result=build_baseline_review(c,r[:1],[])
    assert result["status"]=="insufficient_data" and result["performance"]==[]
