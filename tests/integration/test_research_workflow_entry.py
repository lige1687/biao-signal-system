"""Actual controlled-entry good/bad pairs, no market fitting or network access."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import shutil
from unittest.mock import Mock

import pytest

from lei_signal.research import workflow as w
from lei_signal.research.workflow_evaluation import evaluate_observations

REAL_ROOT = Path(__file__).resolve().parents[2]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def setup_case(tmp_path, *, event=False, assets=2, family="shared-demo"):
    root = tmp_path / "repo"
    catalog = w.read_json(REAL_ROOT / w.CATALOG)
    paths = list(w.CODE_PATHS) + [w.CATALOG, catalog["strategy_sources"], catalog["definition_registry"], catalog["report_registry"]]
    paths += [v["path"] for v in catalog["standards"].values()]
    for name in paths:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_ROOT / name, target)
    # Do not touch the user's actual experiment library in tests.
    dump(root / catalog["report_registry"], {"version": 1, "categories": ["方法论与验证"], "entries": {}})
    dates, day = [], date(2022, 1, 3)
    while len(dates) < 105:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day += timedelta(days=1)
    names = [f"SIM-{i}" for i in range(assets)]
    bars = []
    for j, asset in enumerate(names):
        price = 100.0 + j
        for i, day in enumerate(dates):
            # Fixed deterministic reversal, not a search for a profitable factor.
            movement = (0.014 if i % 6 < 3 else -0.021) if i < 55 else (-0.025 if i % 6 < 3 else (0.07 if event else 0.013))
            price *= 1 + movement + j * 0.0002
            bars.append({"asset": asset, "date": day, "status": "quoted", "close": price,
                         "open": price, "high": price * 1.01, "low": price * .99,
                         "action_known": True, "open_actionable": True})
    payload = {"data_mode": "synthetic", "calendar": dates, "bars": bars}
    data_path = dump(root / "docs/experiments/raw/input-2026-09-29/panel.json", payload)
    kind = "downside_event" if event else "forward_return"
    question = {
        "question_id": "synthetic-event-risk" if event else "synthetic-continuous",
        "hypothesis_family": family, "factor_refs": ["research.a01.signed_band@1.0.1"],
        "layer": "factor_information", "comparison": "joint", "joint_structure": "同日对象和连续日期一起保留",
        "sampling": "daily", "target": {"kind": kind, "horizon": 3, "start_offset": 1,
            "end_offset": 4, "price_basis": "close_to_close"},
        "baseline": "训练期简单均值/频率与已有滞后价变状态", "added_information": "人工示例候选；不声称复现注册A01公式",
        "method": {"name": "event_risk" if event else "prediction_ridge", "reason": "两种共享管线验收形态"},
        "primary_metric": {"name": "Brier" if event else "MSE", "direction": "lower",
            "attention_threshold": None, "threshold_reason": "工程演示不设市场效果门槛"},
        "auxiliary_metrics": ["coverage", "risk"], "universe": names, "period": [dates[0], dates[-1]],
        "validation": {"stage": "exploration", "split_policy": "训练在前、评价在后",
            "label_boundary_policy": "训练标签严格成熟，不成熟者排除并计数"},
        "dependence": "同日一起，日期连续抽取", "sources": {"panel": w.file_hash(data_path)},
        "trial_history": "人工生成；无市场发现；本轮只有限工程例"}
    review = {key: {"reason": "人工样例验证机械行为，不能推断真实市场。登记A01仅用于来源解析演示，公式不等价。",
        "source_refs": ["docs/research/lei-factor-research-mission.md"]} for key in
        ("universe_fit", "proxy_fidelity", "method_fit", "conclusion_scope")}
    c = {"schema_version": "research-workflow/1.0", "question": question,
         "data": {"path": str(data_path.relative_to(root)), "sha256": w.file_hash(data_path), "mode": "synthetic"},
         "universe": {"assets": names, "allow_partial": False, "rationale": "人工对象", "identity_basis": "合成"},
         "feature": {"kind": "decline_event" if event else "sma_distance", "lookback": 3 if event else 1, "bar_frequency": "daily_quote", "warmup": 4 if event else 2, "missing_policy": "real_quote"},
         "target": {"kind": kind, "start_offset": 1, "end_offset": 4, "entry_field": "close",
                    "unit": "probability" if event else "percentage_point", **({"threshold": 2.0,"threshold_unit":"percentage_point"} if event else {})},
         "split": {"label_policy": "purge", "folds": [{"train_end": dates[54], "eval_start": dates[55], "eval_end": dates[95]}]},
         "evaluator": {"kind": "event_risk" if event else "prediction_ridge", "version": "1.0.0",
             "baseline_features": ["existing_state"] if event else ["lag_return"], "added_features": ["added"], "lambda": 1.0},
         "training_weights": "equal_asset", "weights": {"policy": "equal_asset", "comparison": "fixed_common"},
         "dependence": {"block_length": 5, "draws": 32, "seed": 17},
         "budget": {"scientific_variants": 3, "execution_seconds": 30, "max_rows": 2000},
         "history": {"family": family, "ledger_path": str(w.family_ledger(root, family).relative_to(root))},
         "controller_review": review, "publication": {"report_path": f"docs/experiments/{question['question_id']}-2026-09-29.md",
             "category": "方法论与验证", "claimed_scope": "full", "conclusion": "not_supported"}, "sources": []}
    return root, c, payload, data_path


def frozen_path(root, c, name="frozen.json"):
    return dump(root / "docs/experiments/raw/contract-2026-09-29" / name, w.freeze_contract(c, root))


def test_bad_data_actual_entry_does_not_execute_then_good_completes(tmp_path):
    root,c,p,d = setup_case(tmp_path)
    path = frozen_path(root,c)
    original = d.read_bytes()
    p["bars"][0]["close"] = -10
    dump(d,p)
    spy = Mock(wraps=evaluate_observations)
    with pytest.raises(ValueError, match="stale_data"):
        w.execute_workflow(path,root/"bad",root=root,executor=spy)
    spy.assert_not_called()
    d.write_bytes(original)
    state = w.execute_workflow(path,root/"good",root=root,executor=spy)
    assert state["execution"] == "completed" and state["evidence"] == "not_supported"
    assert spy.call_count == 1
    result=w.read_json(root/"good/result.json")
    assert abs(result["increments"][0]["absolute_error_improvement"]) < 1e-12


def test_bad_time_before_callback_good_purge(tmp_path):
    root,c,_,_ = setup_case(tmp_path)
    path=frozen_path(root,c)
    bad=w.read_json(path); bad["split"]["label_policy"]="require_mature"
    dump(path,bad)
    spy=Mock(wraps=evaluate_observations)
    with pytest.raises(ValueError,match="training_label_leakage"):
        w.execute_workflow(path,root/"bad",root=root,executor=spy)
    spy.assert_not_called()
    assert w.execute_workflow(frozen_path(root,c,"correct.json"),root/"good",root=root)["execution"]=="completed"


def test_universe_6_to_4_undisclosed_blocks_declared_partial_completes(tmp_path):
    root,c,p,d=setup_case(tmp_path,assets=6)
    p["bars"]=[b for b in p["bars"] if b["asset"] in c["universe"]["assets"][:4]]
    dump(d,p); c["data"]["sha256"]=w.file_hash(d)
    with pytest.raises(ValueError,match="universe_missing"):
        w.freeze_contract(c,root)
    c["universe"]["allow_partial"]=True
    with pytest.raises(ValueError,match="partial coverage"):
        w.freeze_contract(c,root)
    c["publication"]["claimed_scope"]="partial"
    out=root/"partial"
    assert w.execute_workflow(frozen_path(root,c),out,root=root)["coverage"]=="partial"
    proof=w.read_json(out/"preflight.json")
    assert len(proof["coverage"]["actual_assets"])==4
    assert any(x["code"]=="partial_universe" for x in proof["warnings"])


def test_early_quotes_do_not_count_as_final_evaluation_coverage(tmp_path):
    root,c,p,d=setup_case(tmp_path,assets=3)
    p["bars"]=[b for b in p["bars"] if b["asset"]!="SIM-2" or b["date"]<c["split"]["folds"][0]["eval_start"]]
    dump(d,p); c["data"]["sha256"]=w.file_hash(d)
    with pytest.raises(ValueError,match="universe_missing"):
        w.freeze_contract(c,root)
    c["universe"]["allow_partial"]=True;c["publication"]["claimed_scope"]="partial"
    check=w.preflight(w.freeze_contract(c,root),root)
    assert len(check["coverage"]["input_assets"])==3 and len(check["coverage"]["actual_assets"])==2


def test_event_counterexamples_and_two_evaluator_end_to_end(tmp_path):
    root,c,p,d=setup_case(tmp_path,event=True)
    path=frozen_path(root,c)
    result=w.execute_workflow(path,root/"event",root=root)
    assert result["execution"]=="completed" and result["evidence"]=="not_supported"
    assert next(x for x in w.read_json(root/"event/result.json")["performance"] if x["model"]=="B50")["value"]==.25
    assert any("underperforms B0" in warning for warning in w.read_json(root/"event/result.json")["warnings"])
    # Make every candidate opportunity true; no event/complement comparison.
    for j,asset in enumerate(c["universe"]["assets"]):
        for i,b in enumerate([b for b in p["bars"] if b["asset"]==asset]):
            price=100*(.98**i)
            b.update(close=price,open=price,high=price*1.01,low=price*.99)
    dump(d,p);c["data"]["sha256"]=w.file_hash(d)
    with pytest.raises(ValueError,match="condition_prefiltered"):
        w.freeze_contract(c,root)


@pytest.mark.parametrize("change", ["weights","code","data"])
def test_stale_check_blocks_actual_entry(tmp_path,change):
    root,c,p,d=setup_case(tmp_path)
    path=frozen_path(root,c)
    if change=="weights":
        old=w.read_json(path);old["weights"]["policy"]="equal_date";dump(path,old)
    elif change=="code":
        file=root/w.CODE_PATHS[1];file.write_text(file.read_text()+"\n# changed\n")
    else:
        p["bars"][0]["open_actionable"]=False;dump(d,p)
    spy=Mock(wraps=evaluate_observations)
    with pytest.raises(ValueError,match="stale"):
        w.execute_workflow(path,root/"bad",root=root,executor=spy)
    spy.assert_not_called()


def test_unrelated_definition_card_does_not_invalidate_selected_closure(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c)
    regpath=root/"docs/research/definitions.v1.json";reg=w.read_json(regpath)
    card=deepcopy(reg["objects"][0]);card["id"]="engineering.unrelated";reg["objects"].append(card)
    dump(regpath,reg)
    assert w.preflight(w.read_json(path),root)["bindings"]==w.read_json(path)["bindings"]


def test_baseline_or_unit_omission_blocks_publication_not_bad_effect(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    out=root/"run";w.execute_workflow(frozen_path(root,c),out,root=root)
    assert w.check_publication(out,root)["execution"]=="completed"
    old=(out/"report.md").read_text();(out/"report.md").write_text(old.replace("| B0 |","| hidden |"))
    with pytest.raises(ValueError,match="artifact changed"):
        w.publish(out,root)
    (out/"report.md").write_text(old)
    result=w.read_json(out/"result.json");result["performance"][0]["unit"]="investment_return"
    dump(out/"result.json",result)
    with pytest.raises(ValueError,match="artifact changed"):
        w.check_publication(out,root)


def test_bypassed_outputs_cannot_register_and_existing_outputs_preserved(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    empty=root/"bypass";empty.mkdir();dump(empty/"contract.json",w.freeze_contract(c,root))
    dump(empty/"result.json",{"performance":[]})
    before=(root/"docs/experiments/registry.json").read_bytes()
    with pytest.raises((ValueError,OSError)):
        w.publish(empty,root)
    assert before==(root/"docs/experiments/registry.json").read_bytes()
    path=frozen_path(root,c);out=root/"proper"
    w.execute_workflow(path,out,root=root,register_report=True)
    original=(out/"result.json").read_bytes()
    with pytest.raises(ValueError,match="overwrite"):
        w.execute_workflow(path,out,root=root)
    assert (out/"result.json").read_bytes()==original


def test_words_and_weight_only_reuse_predictions_no_fit_feature_change_invalidates(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    old=root/"old";w.execute_workflow(frozen_path(root,c),old,root=root)
    c["question"]["decision_use"]="仅改解释文字"
    path=frozen_path(root,c,"words.json")
    spy=Mock(side_effect=AssertionError("must not refit"))
    assert w.execute_workflow(path,root/"words",root=root,executor=spy,reuse_predictions=old)["execution"]=="completed"
    c["weights"]["policy"]="equal_date";c["history"]["changed_after_results_reason"]="预先工程用例：只重汇总比重，承认已见。"
    assert w.execute_workflow(frozen_path(root,c,"weights.json"),root/"weights",root=root,executor=spy,reuse_predictions=old)["execution"]=="completed"
    assert w.read_json(root/"weights/result.json")["execution"]["fits"]==0
    c["feature"]["lookback"]=4
    with pytest.raises(ValueError,match="cache_invalid"):
        w.execute_workflow(frozen_path(root,c,"feature.json"),root/"feature",root=root,reuse_predictions=old)
    spy.assert_not_called()


def test_seen_results_and_budget_follow_family_not_task_name(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    c["budget"]["scientific_variants"]=1
    w.execute_workflow(frozen_path(root,c),root/"run",root=root)
    c["question"]["question_id"]="renamed-ai-task"
    c["question"]["validation"]["stage"]="unseen"
    with pytest.raises(ValueError,match="seen_evidence"):
        w.execute_workflow(frozen_path(root,c,"renamed.json"),root/"renamed",root=root)
    c["question"]["validation"]["stage"]="exploration";c["feature"]["lookback"]=4
    c["history"]["changed_after_results_reason"]="已见结果后改动，应另记录探索。"
    with pytest.raises(ValueError,match="variant budget"):
        w.execute_workflow(frozen_path(root,c,"next.json"),root/"next",root=root)


@pytest.mark.parametrize("change", ["universe","unit","review","paid","method","primary","bar_frequency"])
def test_missing_core_definition_or_scope_before_callback(tmp_path,change):
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c);bad=w.read_json(path)
    if change=="universe": del bad["universe"]
    elif change=="unit": bad["target"]["unit"]="account_return"
    elif change=="review": bad["controller_review"]["method_fit"]={"verified":True}
    elif change=="method": bad["question"]["method"]["name"]="unimplemented_method"
    elif change=="primary": bad["question"]["primary_metric"]["name"]="account_return"
    elif change=="bar_frequency": bad["feature"]["bar_frequency"]="weekly"
    else: bad["permissions"]={"paid_requests":1}
    dump(path,bad);spy=Mock(wraps=evaluate_observations)
    with pytest.raises(ValueError): w.execute_workflow(path,root/"bad",root=root,executor=spy)
    spy.assert_not_called()


def test_sentiment_definition_is_outside_the_technical_entry(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    registry=w.read_json(root/"docs/research/definitions.v1.json")
    card=next(card for card in registry["objects"] if card.get("research_owner")=="sentiment_agent")
    c["question"]["factor_refs"]=[card["id"]+"@"+card["version"]]
    with pytest.raises(ValueError,match="out_of_scope"):
        w.freeze_contract(c,root)


def test_missing_evaluation_predictions_and_wrong_baseline_block_real_publication(tmp_path):
    from lei_signal.research.workflow_evaluation import summarize_predictions
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c)
    def partial(rows,contract):
        result=evaluate_observations(rows,contract)
        return summarize_predictions(result["predictions"][:-1],contract,rows)
    with pytest.raises(ValueError,match="prediction coverage"):
        w.execute_workflow(path,root/"partial",root=root,executor=partial)
    def wrong_baseline(rows,contract):
        result=evaluate_observations(rows,contract)
        for p in result["predictions"]:
            p["B0"]+=10;p["train_mean"]+=10
        return summarize_predictions(result["predictions"],contract,rows)
    with pytest.raises(ValueError,match="B0 was not computed"):
        w.execute_workflow(path,root/"wrong-b0",root=root,executor=wrong_baseline)
    def wrong_units(rows,contract):
        result=evaluate_observations(rows,contract)
        result["performance"][0]["unit"]="investment_return"
        return result
    with pytest.raises(ValueError,match="numeric/unit/comparison"):
        w.execute_workflow(path,root/"wrong-unit",root=root,executor=wrong_units)
    # Failed acceptance adds no duplicate callback cost.
    records=[json.loads(line) for line in w.family_ledger(root,c["history"]["family"]).read_text().splitlines()]
    assert all(r["seconds"]==0 for r in records if r["event"]=="finish" and r["status"]=="publication_failed")


def test_renaming_family_does_not_make_evaluated_material_unseen(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    w.execute_workflow(frozen_path(root,c),root/"first",root=root)
    c["history"]["family"]=c["question"]["hypothesis_family"]="different-ai-name"
    c["question"]["validation"]["stage"]="unseen"
    with pytest.raises(ValueError,match="seen_evidence"):
        w.execute_workflow(frozen_path(root,c,"renamed-family.json"),root/"renamed-family",root=root)


def test_reformatted_prices_and_changed_target_do_not_become_unseen(tmp_path):
    root,c,p,d=setup_case(tmp_path,event=True)
    w.execute_workflow(frozen_path(root,c),root/"first",root=root)
    old_hash=w.file_hash(d)
    d.write_text(json.dumps(p,sort_keys=True,separators=(",",":")))
    assert w.file_hash(d)!=old_hash
    c["data"]["sha256"]=w.file_hash(d)
    c["target"]["threshold"]=3.0
    c["history"]["family"]=c["question"]["hypothesis_family"]="target-changed-family"
    c["question"]["validation"]["stage"]="unseen"
    spy=Mock(wraps=evaluate_observations)
    with pytest.raises(ValueError,match="seen_evidence"):
        w.execute_workflow(frozen_path(root,c,"target-changed.json"),root/"changed",root=root,executor=spy)
    spy.assert_not_called()
    # Declaring the actual contact and exploratory change allows a bounded run.
    c["question"]["validation"]["stage"]="exploration"
    c["history"]["changed_after_results_reason"]="已看人工旧结果，改阈值仅核工程接触史，不是未见验证"
    assert w.execute_workflow(frozen_path(root,c,"honest-change.json"),root/"honest",root=root)["execution"]=="completed"


def test_rejected_gates_charge_time_not_a_scientific_variant(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c)
    bad=w.read_json(path);bad["weights"]["policy"]="equal_date"
    bad_path=dump(root/"bad.json",bad);spy=Mock(wraps=evaluate_observations)
    with pytest.raises(ValueError,match="stale_proof"):
        w.execute_workflow(bad_path,root/"bad",root=root,executor=spy)
    spy.assert_not_called()
    journal=w.family_ledger(root,c["history"]["family"])
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    rejected=[r for r in records if r["event"]=="gate_attempt"]
    assert len(rejected)==1 and rejected[0]["seconds"]>0
    assert rejected[0]["classification"]=="mechanical_rejection"
    assert not any(r["event"]=="start" for r in records)
    # Rejections exhaust the inherited wall-time allowance, never an effect verdict.
    c["budget"]["execution_seconds"]=sum(r.get("seconds",0) for r in records if r["event"] in w.COST_EVENTS)/2
    with pytest.raises(w.WorkflowPaused,match="budget exhausted"):
        w.freeze_contract(c,root)
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    assert len([r for r in records if r["event"]=="gate_attempt"])==2


@pytest.mark.parametrize("change", ["missing", "not_object", "schema_version", "data_mode", "purpose"])
def test_execution_rejects_missing_or_invalid_rehearsal_before_callback(tmp_path, change):
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c)
    frozen=w.read_json(path)
    if change=="missing":
        del frozen["rehearsal"]
    elif change=="not_object":
        frozen["rehearsal"]=[]
    else:
        frozen["rehearsal"][change]="invalid"
    bad_path=dump(root/"bad-rehearsal.json",frozen)
    spy=Mock()
    with pytest.raises(w.WorkflowBlocked,match="missing actual frozen rehearsal"):
        w.execute_workflow(bad_path,root/"bad",root=root,executor=spy)
    spy.assert_not_called()
    records=[json.loads(line) for line in w.family_ledger(root,c["history"]["family"]).read_text().splitlines()]
    rejected=[r for r in records if r["event"]=="gate_attempt"]
    assert len(rejected)==1 and rejected[0]["seconds"]>0
    assert not any(r["event"]=="start" for r in records)


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit])
def test_execution_interruption_settles_cost_and_preserves_original_exception(tmp_path, interruption):
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c)
    stopped=interruption("artificial interruption before fitting")
    spy=Mock(side_effect=stopped)
    with pytest.raises(interruption) as caught:
        w.execute_workflow(path,root/"interrupted",root=root,executor=spy)
    assert caught.value is stopped
    spy.assert_called_once()
    journal=w.family_ledger(root,c["history"]["family"])
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    starts=[r for r in records if r["event"]=="start"]
    finishes=[r for r in records if r["event"]=="finish"]
    assert len(starts)==len(finishes)==1
    assert starts[0]["run_id"]==finishes[0]["run_id"]
    assert finishes[0]["seconds"]>0
    assert not any(r["event"]=="gate_attempt" for r in records)
    failure=w.read_json(root/"interrupted/failure.json")
    assert failure["execution"]=="paused"
    assert failure["run_id"]==starts[0]["run_id"]
    assert failure["callback_executed"] is True
    assert interruption.__name__ in failure["error"]
    # A settled interruption may retry within the same original family budget.
    retry=Mock(side_effect=RuntimeError("artificial settled retry before fitting"))
    with pytest.raises(RuntimeError,match="settled retry"):
        w.execute_workflow(path,root/"retry",root=root,executor=retry)
    retry.assert_called_once()
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    starts=[r for r in records if r["event"]=="start"]
    assert starts[-1]["classification"]=="mechanical_retry"
    assert len([r for r in records if r["event"]=="finish"])==2


def test_unsettled_start_blocks_new_reservation_without_reset(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    path=frozen_path(root,c)
    frozen=w.read_json(path)
    proof=w.preflight(frozen,root)
    run_id=w._reserve(frozen,proof,root/"hard-interrupted",root)
    journal=w.family_ledger(root,c["history"]["family"])
    original=journal.read_text()
    spy=Mock()
    with pytest.raises(w.WorkflowPaused,match="unsettled execution starts"):
        w.execute_workflow(path,root/"retry",root=root,executor=spy)
    spy.assert_not_called()
    assert journal.read_text().startswith(original)
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    assert [r["run_id"] for r in records if r["event"]=="start"]==[run_id]
    assert not any(r["event"]=="finish" for r in records)
    assert not (root/"retry").exists()


def test_sampling_cache_identity_and_concurrent_family_budget(tmp_path):
    root,c,_,_=setup_case(tmp_path)
    frozen=w.freeze_contract(c,root);old=w.preflight(frozen,root)["cache_keys"]
    periodic=deepcopy(c);periodic["question"].update(sampling="periodic",frequency="weekly")
    new=w.preflight(w.freeze_contract(periodic,root),root)["cache_keys"]
    assert new["prediction"]!=old["prediction"]
    path=dump(root/"frozen.json",frozen)
    with w.family_execution_lock(root,c):
        spy=Mock(wraps=evaluate_observations)
        with pytest.raises(ValueError,match="already running"):
            w.execute_workflow(path,root/"second",root=root,executor=spy)
        spy.assert_not_called()


def test_future_and_unfinished_week_rejected_by_actual_entry(tmp_path):
    root,c,p,d=setup_case(tmp_path)
    p["bars"][0]["period_end"]=p["calendar"][1];dump(d,p);c["data"]["sha256"]=w.file_hash(d)
    spy=Mock(wraps=evaluate_observations)
    draft=dump(root/"draft.json",c)
    with pytest.raises(ValueError,match="stale_proof"):
        w.execute_workflow(draft,root/"future",root=root,executor=spy)
    spy.assert_not_called()
    # The actual draft/freezing entry discovers the precise future-time error
    # before invoking even the synthetic numerical rehearsal.
    from unittest.mock import patch
    with patch("lei_signal.research.workflow.run_rehearsal") as rehearsal:
        with pytest.raises(ValueError,match="after observation"):
            w.freeze_workflow(draft,root/"future-freeze",root)
        rehearsal.assert_not_called()
    del p["bars"][0]["period_end"];dump(d,p);c["data"]["sha256"]=w.file_hash(d)
    c["question"].update(sampling="periodic",frequency="weekly")
    frozen=w.freeze_contract(c,root)
    proof=w.preflight(frozen,root)
    assert all(date.fromisoformat(r["date"]).weekday()==4 for r in proof["observations"])


def test_real_panel_binds_calendar_prices_actions_and_open_separately(tmp_path):
    from types import SimpleNamespace
    import pandas as pd
    root,c,p,_=setup_case(tmp_path,assets=1)
    asset="510300.SS"
    for b in p["bars"]:b["asset"]=asset
    c["universe"]["assets"]=[asset]
    snapshot_dir=tmp_path/"qualified";snapshot_dir.mkdir()
    nominal=pd.DataFrame(p["bars"]).set_index("date")[["open","high","low","close"]]
    nominal.to_csv(snapshot_dir/"nominal.csv")
    actions=dump(snapshot_dir/"actions.json",{"events":[]})
    days={}
    d=date.fromisoformat(p["calendar"][0]);end=date.fromisoformat(p["calendar"][-1])
    while d<=end:
        days[d.isoformat()]={"is_trading_day":d.weekday()<5,"source_flag":"1" if d.weekday()<5 else "0","source_month":d.isoformat()[:7]}
        d+=timedelta(days=1)
    cal=dump(snapshot_dir/"calendar.json",{"authority":"synthetic_test_only","publisher":"合成日历",
        "months_requested":sorted({d[:7] for d in days}),"months_failed":[],"days":days})
    pub=dump(snapshot_dir/"publication.json",{"annual_notices":[]})
    frame=nominal.copy();frame.index=pd.to_datetime(frame.index)
    scale=frame.close/frame.close.iloc[0]/frame.close
    economic=frame.mul(scale,axis=0)
    for b in p["bars"]:
        for field in ("open","high","low","close"):b[field]=float(economic.loc[b["date"],field])
    transform={"operator":"definitions.economic_index/1.0",
        "nominal":{"path":"nominal.csv","sha256":w.file_hash(snapshot_dir/"nominal.csv")},
        "actions":{"path":"actions.json","sha256":w.file_hash(actions)}}
    snap=SimpleNamespace(frames={asset:economic},snapshot={"semantics":{"economic_transforms":{asset:transform}}})
    q={"calendar_path":cal,"publication_path":pub,"actions_path":actions,"snapshot_dir":snapshot_dir,
       "evaluation_start":p["calendar"][0],"evaluation_end":p["calendar"][-1],"use":"diagnostic"}
    assert w.qualify_panel(p,c,q,snap)["prices_bound"]
    hidden=deepcopy(p);hidden["bars"][8]["low"]=None
    with pytest.raises(ValueError,match="hides an actual snapshot price"):
        w.qualify_panel(hidden,c,q,snap)
    periodic=deepcopy(c);periodic["question"].update(sampling="periodic",frequency="weekly")
    unfinished=deepcopy(p);unfinished["calendar"]=p["calendar"][:4]
    unfinished["completed_period_ends"]=[unfinished["calendar"][-1]]
    with pytest.raises(ValueError,match="unfinished period"):
        w.qualify_panel(unfinished,periodic,{**q,"evaluation_end":unfinished["calendar"][-1]},snap)
    finished=deepcopy(p);finished["calendar"]=p["calendar"][:5]
    finished["completed_period_ends"]=[finished["calendar"][-1]]
    assert w.qualify_panel(finished,periodic,{**q,"evaluation_end":finished["calendar"][-1]},snap)["calendar_bound"]
    bad=deepcopy(p);bad["bars"][8].update(status="halt",open=None,high=None,low=None,close=None)
    with pytest.raises(ValueError,match="hides a real"):
        w.qualify_panel(bad,c,q,snap)
    bad=deepcopy(p);del bad["calendar"][7]
    with pytest.raises(ValueError,match="calendar differs"):
        w.qualify_panel(bad,c,q,snap)
    badq={**q,"evaluation_start":p["calendar"][1]}
    with pytest.raises(ValueError,match="qualification period"):
        w.qualify_panel(p,c,badq,snap)
    missing=SimpleNamespace(frames={asset:economic},snapshot={"semantics":{}})
    with pytest.raises(ValueError,match="action_known=true"):
        w.qualify_panel(p,c,q,missing)
    opened=deepcopy(c);opened["target"]["entry_field"]="open"
    with pytest.raises(ValueError,match="opening-session"):
        w.qualify_panel(p,opened,q,snap)
