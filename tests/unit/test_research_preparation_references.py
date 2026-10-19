import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "src/lei_signal/research/preparation.py"
SPEC = importlib.util.spec_from_file_location("worktree_preparation", MODULE_PATH)
preparation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparation)


def reference(ref_id, name, *, aliases=(), source=None, uses=None):
    return {
        "id": ref_id,
        "version": "1.0.0",
        "name": name,
        "aliases": list(aliases),
        "kind": "factor_return",
        "source": source or {"institution": "Unknown", "authors": []},
        "construction": "published definition",
        "external_id": ref_id,
        "implementation": "metadata_only",
        "market": "US",
        "asset_type": "factor_return",
        "universe": "published",
        "frequency": "monthly",
        "calendar": "published",
        "currency": "USD",
        "unit": "return",
        "inputs": [],
        "historical_availability": "unknown",
        "missing_policy": "source_defined",
        "preprocessing": [],
        "questions": [],
        "uses": list(uses or ["attribution"]),
        "not_for": ["prediction"],
        "variant": "canonical",
        "local_changes": [],
        "license_status": "metadata_only",
        "engineering_status": "not_implemented",
        "evidence_status": "registered_metadata_only",
    }


@pytest.fixture
def context(tmp_path, monkeypatch):
    registry = {
        "objects": [],
        "sources": {},
        "research_references": [
            reference("ref.french.ff5", "French Five Factor", aliases=["FF5"],
                      source={"institution": "Kenneth French", "authors": ["Eugene Fama"]}),
            reference("ref.aqr.qmj", "AQR Quality Minus Junk", aliases=["QMJ"],
                      source={"institution": "AQR", "authors": []}),
            reference("ref.jkp", "JKP Data Library", aliases=["JKP"],
                      source={"institution": "Jensen Kelly Pedersen", "authors": []}),
            reference("research.external.ff5", "ff5 Mkt-RF", source={
                "institution": "Kenneth French", "authors": ["Eugene F. Fama", "Kenneth R. French"]
            }),
        ],
    }
    (tmp_path / "docs/research/methods/research-method-cases/cases").mkdir(parents=True)
    (tmp_path / preparation.STANDARDS).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / preparation.STANDARDS).write_text(
        json.dumps({"definition_registry": "registry.json"}), encoding="utf-8"
    )
    (tmp_path / "registry.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(preparation.definitions, "load_registry", lambda path: registry)
    return tmp_path


def test_term_searches_reference_names_aliases_and_source_metadata(context):
    result = preparation.build_context(context, terms=["kenneth french"])
    assert result["definitions"] == []
    assert [item["ref"] for item in result["research_references"]] == [
        "ref.french.ff5@1.0.0", "research.external.ff5@1.0.0"
    ]
    assert result["research_references"][0]["match_reasons"] == [
        "source.institution:kenneth french"
    ]
    assert result["research_references"][0]["card"]["uses"] == ["attribution"]
    assert result["research_references"][0]["card"]["not_for"] == ["prediction"]
    assert result["research_references"][0]["registered_evidence_status"] == "registered_metadata_only"
    by_ref = {item["ref"]: item for item in result["research_references"]}
    assert by_ref["research.external.ff5@1.0.0"]["match_reasons"] == [
        "source.institution:kenneth french"
    ]
    author_result = preparation.build_context(context, terms=["Eugene F. Fama"])
    assert "research.external.ff5@1.0.0" in [
        item["ref"] for item in author_result["research_references"]
    ]


def test_explicit_reference_ref_returns_exact_card_and_rejects_unknown(context):
    result = preparation.build_context(context, reference_refs=["ref.aqr.qmj@1.0.0"])
    assert [item["ref"] for item in result["research_references"]] == ["ref.aqr.qmj@1.0.0"]
    with pytest.raises(ValueError, match="unknown exact research reference"):
        preparation.build_context(context, reference_refs=["ref.aqr.qmj@latest"])


def test_reference_results_report_truncation_and_explicit_refs_first(context):
    result = preparation.build_context(
        context, terms=["ref."], reference_refs=["ref.jkp@1.0.0"], limit=1
    )
    assert result["research_references"][0]["ref"] == "ref.jkp@1.0.0"
    assert result["reference_search"]["truncated_count"] == 2
    assert len(result["reference_search"]["undisplayed_refs"]) == 2


def test_empty_reference_registry_and_no_match_are_explicit(context, monkeypatch):
    registry = preparation.definitions.load_registry(context / "registry.json")
    registry["research_references"] = []
    monkeypatch.setattr(preparation.definitions, "load_registry", lambda path: registry)
    result = preparation.build_context(context, terms=["no such source"])
    assert result["research_references"] == []
    assert result["reference_search"]["registered_count"] == 0
    assert result["reference_search"]["no_match_note"]
