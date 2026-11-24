"""Synthetic boundaries for the read-only factor-combination helper."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.research.factor_combinations import (
    assess_candidate, build_catalog, holdings_relationship, main, query_catalog,
    return_relationship, score_relationship,
)
from lei_signal.research import osap_reference


def _file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root(tmp_path):
    _file(tmp_path / "docs/research/current-standards.json",
          {"definition_registry": "docs/research/definitions.v1.json"})
    _file(tmp_path / "docs/research/definitions.v1.json", {
        "objects": [{"id": "same", "version": "1", "name": "same", "type": "feature",
                     "uses": ["ranking"], "sources": ["old-schema"]}],
        "research_references": [{"id": "same", "version": "1", "name": "same",
                                 "kind": "feature", "market": "CN", "asset_type": "ETF"}],
    })
    return tmp_path


def _scope(kind="return"):
    return {"market": "CN", "universe_id": "u1", "frequency": "monthly",
            "currency": "CNY", "return_basis": "gross", "series_kind": kind}


def test_catalog_exact_identity_unknown_and_drift(tmp_path):
    root = _root(tmp_path)
    catalog = build_catalog(root)
    assert set(catalog["cards"]) == {"object:same@1", "reference:same@1"}
    obj = catalog["cards"]["object:same@1"]
    assert "market" in obj["unknown_fields"]
    assert obj["validation_status"] == "registered_native_only_not_globally_validated"
    assert query_catalog(catalog, term="same", limit=1)["truncated"]
    evidence = root / "proof.json"
    sha = _file(evidence, {"ok": True})
    profiles = root / "profiles.json"
    _file(profiles, {"schema": "factor-combination-profiles/1", "annotations": [
        {"key": "object:same@1", "family": "price", "financial_meaning": "hypothesis",
         "markets": ["CN"], "assets": ["ETF"], "purposes": ["ranking"],
         "horizon": "monthly", "evidence": [{"path": "proof.json", "sha256": sha}]}]})
    assert build_catalog(root, "profiles.json")["cards"]["object:same@1"]["family"] == "price"
    assert "market" in build_catalog(root, "profiles.json")["cards"]["object:same@1"]["annotation_only_fields"]
    conflict = json.loads(profiles.read_text())
    conflict["annotations"][0]["purposes"] = ["diagnostic"]
    _file(profiles, conflict)
    with pytest.raises(ValueError, match="conflicts with native uses"):
        build_catalog(root, "profiles.json")
    conflict["annotations"][0]["purposes"] = ["ranking"]
    _file(profiles, conflict)
    evidence.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="drift"):
        build_catalog(root, profiles)


def test_return_scope_missing_duplicate_constant():
    scope = _scope()
    a = [{"date": "2024-01", "value": 0.0}, {"date": "2024-02", "value": None},
         {"date": "2024-03", "value": -0.1}, {"date": "2024-04", "value": -0.2}]
    b = [{"date": "2024-01", "value": 0.0}, {"date": "2024-02", "value": -0.5},
         {"date": "2024-03", "value": -0.1}, {"date": "2024-04", "value": -0.2}]
    result = return_relationship(a, b, scope, scope)
    assert result["left_missing"] == 1 and result["common_periods"] == 3
    assert result["common_loss_count"] == 2
    assert result["left_only_loss_count"] == result["right_only_loss_count"] == 0
    assert result["joint_loss_mean_left"] == pytest.approx(-.15)
    assert result["min_joint_month_sum"] == pytest.approx(-.4)
    assert result["correlation"] == pytest.approx(1)
    changed = {**scope, "universe_id": "u2"}
    with pytest.raises(ValueError, match="incompatible"):
        return_relationship(a, b, scope, changed)
    with pytest.raises(ValueError, match="duplicate"):
        return_relationship(a + [a[0]], b, scope, scope)
    const = [{"date": row["date"], "value": 0.0} for row in a]
    assert return_relationship(const, b, scope, scope)["correlation"] is None


def test_score_same_day_ties_and_holdings_cash():
    score_scope = _scope("score")
    a = [{"date": "2024-01", "symbol": s, "value": v}
         for s, v in (("A", 1), ("B", 1), ("C", 3), ("D", 4))]
    b = [{"date": "2024-01", "symbol": s, "value": v}
         for s, v in (("A", 1), ("B", 1), ("C", 3), ("D", 4))]
    assert score_relationship(a, b, score_scope, score_scope)["per_date"][0]["spearman"] == pytest.approx(1)
    reversed_scores = [{"date": "2024-01", "symbol": s, "value": v}
                       for s, v in (("A", 4), ("B", 4), ("C", 2), ("D", 1))]
    assert score_relationship(a, reversed_scores, score_scope, score_scope)["per_date"][0]["spearman"] == pytest.approx(-1)
    missing = a[:3] + [{"date": "2024-01", "symbol": "D", "value": None}]
    assert score_relationship(missing, b, score_scope, score_scope)["per_date"][0]["missing_or_null_common"] == 1
    with pytest.raises(ValueError, match="duplicate"):
        score_relationship(a + [a[0]], b, score_scope, score_scope)
    holding_scope = _scope("holding")
    left = [{"date": "2024-01", "symbol": "A", "weight": .2},
            {"date": "2024-01", "symbol": "B", "weight": .3}]
    right = [{"date": "2024-01", "symbol": "A", "weight": .1},
             {"date": "2024-01", "symbol": "C", "weight": .4}]
    result = holdings_relationship(left, right, holding_scope, holding_scope)
    assert result["per_date"][0]["capital_overlap"] == pytest.approx(.1)
    assert result["per_date"][0]["left_invested"] == pytest.approx(.5)
    three_months = {**holding_scope, "expected_dates": ["2024-01", "2024-02", "2024-03"]}
    assert holdings_relationship(left, right, three_months, three_months)["usable_missing_dates"] == ["2024-02", "2024-03"]
    score_expected = {**score_scope, "expected_dates": ["2024-01", "2024-02"]}
    assert score_relationship(a, b, score_expected, score_expected)["coverage_status"] == "incomplete"


def test_candidate_never_forward_and_missing_gates(tmp_path, capsys):
    catalog = build_catalog(_root(tmp_path))
    candidate = {"id": "c", "name": "c", "component_keys": ["object:same@1"],
                 "mode": "joint_selection", "financial_hypothesis": "economic rationale",
                 "competing_explanation": "sector composition", "scope": {
                     "market": "CN", "asset_type": "stock", "purpose": "comparison",
                     "universe_id": "u1", "frequency": "monthly", "currency": "CNY"},
                 "rules": {}}
    checks = {field: None for field in ("historical_membership", "point_in_time",
        "prices_and_exits", "holdings", "transaction_costs", "parent_benchmark", "unseen_validation")}
    evidence = {"checks": checks, "relationships": {"return": {"correlation": 0.0}}}
    result = assess_candidate(catalog, candidate, evidence)
    assert result["state"] == "blocked_inputs" and not result["forward_eligible"]
    assert "signal" in result["missing_rules"] and "point_in_time" in result["unqualified_checks"]
    assert any("market:unknown" in issue for issue in result["metadata_issues"])
    registry_path = tmp_path / "docs/research/definitions.v1.json"
    registry = json.loads(registry_path.read_text())
    registry["objects"][0]["uses"] = ["comparison"]
    _file(registry_path, registry)
    bound = tmp_path / "checked.json"
    checked_sha = _file(bound, {"qualification": "synthetic"})
    profiles = tmp_path / "profiles.json"
    _file(profiles, {"schema": "factor-combination-profiles/1", "annotations": [
        {"key": "object:same@1", "markets": ["CN"], "assets": ["stock"],
         "purposes": ["comparison"], "family": "profitability",
         "financial_meaning": "predeclared mechanism", "horizon": "monthly",
         "evidence": [{"path": "checked.json", "sha256": checked_sha}]}]})
    catalog = build_catalog(tmp_path, "profiles.json")
    candidate["rules"] = {field: "specified" for field in ("universe", "signal",
        "decision_time", "execution_time", "allocation", "rebalance", "exit",
        "missing_data", "costs", "benchmark")}
    evidence["checks"] = {field: True for field in checks}
    result = assess_candidate(catalog, candidate, evidence)
    assert result["state"] == "blocked_inputs" and len(result["unqualified_checks"]) == len(checks)
    evidence["check_bindings"] = {field: [{"path": "checked.json", "sha256": checked_sha}]
                                  for field in checks}
    result = assess_candidate(catalog, candidate, evidence)
    assert result["state"] == "qualified_for_research_design"
    assert result["mechanism_review"]["status"] == "not_checked"
    assert result["new_research_status"] != "ready_for_manual_review"
    assert not result["metadata_issues"] and not result["unqualified_checks"]
    assert not result["forward_eligible"]
    request = tmp_path / "request.json"
    _file(request, {"candidate": candidate, "evidence": evidence})
    main(["review", "--root", str(tmp_path), "--profiles", "profiles.json",
          "--request", str(request)])
    assert json.loads(capsys.readouterr().out)["mechanism_review"]["status"] == "not_checked"
    with pytest.raises(SystemExit) as exit_info:
        main(["review", "--root", str(tmp_path), "--profiles", "profiles.json",
              "--request", str(request), "--require-mechanism"])
    assert exit_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["new_research_status"] != "ready_for_manual_review"
    evidence["check_bindings"]["point_in_time"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="drift"):
        assess_candidate(catalog, candidate, evidence)
    evidence["check_bindings"]["point_in_time"][0]["sha256"] = checked_sha
    evidence["checks"]["point_in_time"] = 1
    with pytest.raises(ValueError, match="invalid or absent check"):
        assess_candidate(catalog, candidate, evidence)
    evidence["checks"]["point_in_time"] = "false"
    with pytest.raises(ValueError, match="invalid or absent check"):
        assess_candidate(catalog, candidate, evidence)
    evidence["checks"]["point_in_time"] = True
    candidate["rules"]["signal"] = 1
    assert "signal" in assess_candidate(catalog, candidate, evidence)["missing_rules"]
    candidate["rules"]["signal"] = "specified"
    catalog["cards"]["object:same@1"]["market"] = "US"
    candidate["component_keys"].append("reference:same@1")
    with pytest.raises(ValueError, match="cross-market"):
        assess_candidate(catalog, candidate, evidence)
    candidate["component_keys"].pop()
    catalog["cards"]["object:same@1"]["market"] = ["CN"]
    prior = tmp_path / "prior.json"
    sha = _file(prior, {"negative_result": True})
    evidence["prior_results"] = [{"path": "prior.json", "sha256": sha}]
    assert assess_candidate(catalog, candidate, evidence)["reuse_existing_results"]
    prior.write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="drift"):
        assess_candidate(catalog, candidate, evidence)


def test_monthly_precision_and_interior_coverage():
    scope = _scope()
    left = [{"date": month, "value": value} for month, value in
            (("2024-01", 1.0), ("2024-03", 2.0), ("2024-05", 3.0))]
    right = [{"date": row["date"], "value": row["value"]} for row in left]
    result = return_relationship(left, right, scope, scope)
    assert result["correlation"] == pytest.approx(1)
    assert result["coverage_status"] == "incomplete"
    assert result["usable_missing_dates"] == ["2024-02", "2024-04"]
    declared = {**scope, "expected_dates": [f"2024-{i:02d}" for i in range(1, 6)]}
    assert return_relationship(left, right, declared, declared)["expected_dates_count"] == 5
    with pytest.raises(ValueError, match="monthly dates require"):
        return_relationship(left + [{"date": "2024-06-30", "value": 4.0}], right, scope, scope)
    with pytest.raises(ValueError, match="expected_dates must match"):
        return_relationship(left, right, declared, scope)
    skipped = {**scope, "expected_dates": ["2024-01", "2024-03", "2024-05"]}
    with pytest.raises(ValueError, match="must be continuous"):
        return_relationship(left, right, skipped, skipped)
    daily = {**scope, "frequency": "daily"}
    with pytest.raises(ValueError, match="daily dates require"):
        return_relationship(left, right, daily, daily)


def test_reject_nonfinite_and_overinvested_holdings():
    scope = _scope()
    with pytest.raises(ValueError, match="finite numeric"):
        return_relationship([{"date": "2024-01", "value": float("nan")}],
                            [{"date": "2024-01", "value": 0.0}], scope, scope)
    holding_scope = _scope("holding")
    excessive = [{"date": "2024-01", "symbol": "A", "weight": .8},
                 {"date": "2024-01", "symbol": "B", "weight": .3}]
    with pytest.raises(ValueError, match="exceed one"):
        holdings_relationship(excessive, [], holding_scope, holding_scope)


def test_osap_native_sign_and_months_are_descriptive(tmp_path):
    root = _root(tmp_path)
    folder = root / "osap"
    folder.mkdir()
    with (folder / "catalog.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=osap_reference.CATALOG_FIELDS)
        writer.writeheader()
        writer.writerow({"Acronym": "ABC", "Sign": "-1", "Portfolio Period": "6",
                         "LongDescription": "source wording", "Cat.Economic": "investment"})
    with (folder / "returns.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "ABC"])
        writer.writerow(["2020-01-31", "2.5"])
    manifest = {"schema": "osap-reference/1", "vintage": "synthetic", "market": "US",
                "retrieved_at": "2026-10-24T01:00:00+08:00", "published_at": None,
                "catalog": {"path": "catalog.csv", "sha256": hashlib.sha256((folder / "catalog.csv").read_bytes()).hexdigest()},
                "returns": {"path": "returns.csv", "sha256": hashlib.sha256((folder / "returns.csv").read_bytes()).hexdigest()},
                "return_unit": "percent", "return_direction": "published_long_short"}
    _file(folder / "manifest.json", manifest)
    cards = build_catalog(root, osap_manifest="osap/manifest.json")["cards"]
    osap_card = next(value for key, value in cards.items() if key.startswith("osap:ABC@"))
    assert osap_card["portfolio_period_months"] == 6
    assert osap_card["horizon"] is None
    assert osap_card["meaning_status"] == "source_description_not_reviewed_mechanism"
    assert osap_card["native_categories"]["Sign"] == "-1"
    assert osap_card["return_direction"] == "published_long_short_do_not_apply_sign_again"
