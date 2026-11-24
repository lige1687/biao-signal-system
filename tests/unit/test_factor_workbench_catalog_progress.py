"""The catalog extension preserves reviewed research and exposes missing sources."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from lei_signal.factor_workbench import catalog_progress
from lei_signal.factor_workbench.catalog_progress import OSAP_JSON, OSAP_MANIFEST, extend_progress


def _json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root(tmp_path: Path) -> Path:
    _json(tmp_path / "docs/research/current-standards.json",
          {"definition_registry": "docs/research/definitions.v1.json"})
    _json(tmp_path / "docs/research/definitions.v1.json", {
        "objects": [
            {"id": "same", "version": "1", "name": "同名", "type": "feature", "uses": ["排序"],
             "definition": {"formula": "a"}, "scope": {"market": "CN"}},
            {"id": "same", "version": "2", "name": "同名", "type": "policy/strategy",
             "definition": {"rule": "b"}},
            {"id": "index", "version": "1", "name": "指数", "type": "benchmark"},
        ],
        "research_references": [{"id": "same", "version": "1", "name": "同名",
                                 "kind": "feature", "construction": "方法"}],
    })
    _json(tmp_path / "web/src/pages/factor-research/catalog.generated.json", {
        "schema_version": "factor-research/1", "sources": [],
        "items": [{"reference": "same@1", "research": {"stage": "historical",
                   "summary": "旧研究只评价某一范围。", "evidence_date": "2026-09-23"}}],
    })
    return tmp_path


def _base() -> dict:
    cases = [{"id": f"review-{i}", "title": "已审阅", "definitionRefs": ["same@1"] if i == 0 else [],
              "execution": {"state": "completed", "label": "本轮结案"},
              "conclusion": {"state": "limited", "text": "具体范围"}} for i in range(20)]
    return {"checkedAt": "2026-10-24T10:00:00+08:00", "cases": cases,
            "sources": [{"id": "catalog-possible-collision", "status": "changed"}]}


def _external(root: Path, rows: list[dict] | None = None) -> None:
    rows = rows if rows is not None else [{"key": "alpha", "name": "同名", "description": "公开描述",
                                              "category": "value", "dataCategory": "price",
                                              "sourceYear": 2020, "sourceAuthors": "A", "codeUrl": "https://example.org"}]
    digest = _json(root / OSAP_JSON, {"schemaVersion": 1, "retrievedAt": "2026-10-24T10:00:00+08:00",
                                     "originalCatalogSha256": "a" * 64, "records": rows})
    _json(root / OSAP_MANIFEST, {"path": OSAP_JSON.as_posix(), "sha256": digest,
                                  "recordCount": len(rows), "originalCatalogSha256": "a" * 64,
                                  "sourceManifestPath": "external/manifest.json"})


def test_all_exact_identities_versions_and_reviewed_states(tmp_path):
    root = _root(tmp_path)
    _external(root)
    base = _base()
    saved = deepcopy(base)
    result = extend_progress(root, base)
    assert base == saved
    assert result["cases"][:20] == [{**case, "recordType": "reviewed_research"} for case in saved["cases"]]
    assert result["sources"][0] == saved["sources"][0]
    assert result["catalog"] == {"total": 5, "registeredObjects": 3,
                                  "registeredReferences": 1, "externalReferences": 1,
                                  "reviewedResearchCases": 20, "linkedObjects": 1, "issues": []}
    assert len(result["cases"]) == result["catalog"]["total"] + result["catalog"]["reviewedResearchCases"]
    cards = {case["catalogKey"]: case for case in result["cases"][20:]}
    assert set(cards) == {"object:same@1", "object:same@2", "object:index@1",
                          "reference:same@1", "alpha"}
    assert cards["object:same@1"]["relatedCaseIds"] == ["review-0"]
    assert cards["reference:same@1"]["relatedCaseIds"] == []
    assert cards["object:same@2"]["relatedCaseIds"] == []
    assert cards["object:same@2"]["researchVersion"] == "2"
    assert cards["object:same@2"]["kind"] == "strategy"
    assert cards["object:index@1"]["kind"] == "benchmark"
    assert cards["reference:same@1"]["kind"] == "reference"
    assert cards["alpha"]["recordType"] == "external_reference"
    assert cards["alpha"]["kind"] == "reference"
    assert cards["alpha"]["researchVersion"] == "原目录 " + "a" * 12
    assert cards["object:same@1"]["execution"]["label"] == "已有旧记录 · 待核对"
    assert cards["object:same@1"]["conclusion"]["state"] == "unknown"
    assert cards["object:same@1"]["legacyCatalogUrl"].endswith("same%401")
    assert all(card["execution"] == {"state": "unknown", "label": "尚未关联研究记录"}
               and card["conclusion"]["state"] == "not_evaluated"
               for key, card in cards.items() if key != "object:same@1")
    assert all(card["currentStageId"] == "definition" for card in cards.values())
    assert all([stage["status"] for stage in card["stages"]] ==
               ["unknown", "unknown", "unknown", "partial", "unknown", "unknown", "unknown", "unknown"]
               for key, card in cards.items() if key != "alpha")
    assert all(card["evidenceAsOf"] == "2026-10-24" for card in cards.values())


def test_missing_or_bad_registry_preserves_reviewed_cases(tmp_path):
    root = _root(tmp_path)
    base = _base()
    (root / "docs/research/definitions.v1.json").unlink()
    result = extend_progress(root, base)
    assert len(result["cases"]) == 20
    assert result["catalog"]["registeredObjects"] == 0
    assert len(result["catalog"]["issues"]) == 2  # Registry and external summary each fail visibly.
    assert result["cases"][0]["conclusion"]["state"] == "limited"


def test_external_hash_count_and_duplicate_fail_closed(tmp_path):
    root = _root(tmp_path)
    _external(root)
    manifest = root / OSAP_MANIFEST
    data = json.loads(manifest.read_text())
    data["sha256"] = "0" * 64
    _json(manifest, data)
    result = extend_progress(root, _base())
    assert result["catalog"]["externalReferences"] == 0
    assert any("SHA-256" in issue for issue in result["catalog"]["issues"])
    _external(root)
    data = json.loads(manifest.read_text())
    data["recordCount"] = 2
    _json(manifest, data)
    assert extend_progress(root, _base())["catalog"]["externalReferences"] == 0
    _external(root, [{"key": "duplicate"}, {"key": "duplicate"}])
    assert extend_progress(root, _base())["catalog"]["externalReferences"] == 0


def test_external_path_escape_rejected(tmp_path):
    root = _root(tmp_path)
    _external(root)
    manifest = root / OSAP_MANIFEST
    data = json.loads(manifest.read_text())
    data["path"] = "../../outside.json"
    _json(manifest, data)
    result = extend_progress(root, _base())
    assert result["catalog"]["externalReferences"] == 0
    assert any("outside project root" in issue for issue in result["catalog"]["issues"])


def test_external_source_manifest_hash_and_signal_category(tmp_path):
    root = _root(tmp_path)
    _external(root, [{"key": "osap:sample@abc", "name": "样本", "sourceSignalType": "Placebo"}])
    source = root / "docs/experiments/raw/source/manifest.json"
    digest = _json(source, {"source": "public catalog"})
    manifest = root / OSAP_MANIFEST
    data = json.loads(manifest.read_text())
    data["sourceManifestPath"] = source.relative_to(root).as_posix()
    data["sourceManifestSha256"] = digest
    _json(manifest, data)
    result = extend_progress(root, _base())
    card = next(case for case in result["cases"] if case.get("catalogKey") == "osap:sample@abc")
    assert "对照" in card["limitations"][-1]
    assert result["catalog"]["externalReferences"] == 1
    source.write_text("changed")
    result = extend_progress(root, _base())
    assert result["catalog"]["externalReferences"] == 0
    assert any("source manifest SHA-256" in issue for issue in result["catalog"]["issues"])


def test_partial_catalog_failure_keeps_reviewed_cases_and_explicit_issue(tmp_path, monkeypatch):
    root = _root(tmp_path)
    _external(root)
    original = catalog_progress._case

    def fail_second(key, *args, **kwargs):
        if key == "object:same@2":
            raise ValueError("synthetic malformed entry")
        return original(key, *args, **kwargs)

    monkeypatch.setattr(catalog_progress, "_case", fail_second)
    result = extend_progress(root, _base())
    assert result["catalog"]["registeredObjects"] == 1
    assert result["catalog"]["registeredReferences"] == 0
    assert result["catalog"]["externalReferences"] == 1
    assert result["catalog"]["total"] == 2
    assert len(result["cases"]) == 22
    assert any("synthetic malformed entry" in issue for issue in result["catalog"]["issues"])
    assert result["cases"][0]["conclusion"]["state"] == "limited"
