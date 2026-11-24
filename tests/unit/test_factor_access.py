"""通用因子研究材料接入：仅人工 ResearchBatch 与临时文件。"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research import definitions
from lei_signal.research.factor_access import (
    AccessError,
    load_access_catalog,
    pack_research_batch,
    read_comparison,
    read_materials,
    validate_research_packet,
)
from lei_signal.research.factor_lab.contracts import METADATA_REQUIRED, ResearchBatch
from lei_signal.research.factor_runtime import contract_digest

REF = "mixed.momentum.raw@1.0.0"
OTHER_REF = "mixed.rv20@1.0.0"
CAND_REF = "candidate:mixed.example@draft-1"
BOOLEAN_REF = "mixed.volatility_allowed@1.0.0"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _card(reference: str = REF) -> dict:
    registry = definitions.load_registry()
    return definitions.resolve(registry, reference, purpose="description")


def _metadata(reference: str = REF) -> dict:
    card = _card(reference)
    meta = {
        "reference": reference,
        "card": card,
        "card_kind": "registered",
        "type": card["type"],
        "unit": card["definition"]["unit"],
        "purpose": "calculation_only",
        "entity_axis": "instrument",
        "value_type": "continuous",
        "protocol": {
            "protocol_id": "artificial-only",
            "version": "1.0.0",
            "kind": "calculation_only",
            "data_mode": "synthetic",
            "sha256": "a" * 64,
        },
        "data_identity": {"synthetic": True, "input_fingerprint": "b" * 64},
        "code_identity": {"modules": []},
        "calendar": {"timezone": "Asia/Shanghai", "kind": "artificial_days"},
        "time_evidence": {"historical_availability": "unknown"},
        "synthetic": True,
        "definition_status": card["status"]["definition_clarity"],
        "data_status": "synthetic_input",
        "implementation_status": card["status"]["implementation"],
        "effectiveness_status": card["status"]["effectiveness"],
        "production_authorization": "not_authorized",
    }
    assert meta.keys() >= METADATA_REQUIRED
    return meta


def _batch(reference: str = REF) -> ResearchBatch:
    values = pd.DataFrame(
        {
            "observation_date": [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-05")],
            "entity_id": ["510300.SS", "510300.SS"],
            "value": [0.12, float("nan")],
            "missing_reason": [None, "warmup_history_insufficient"],
        }
    )
    return ResearchBatch(
        values=values,
        metadata=_metadata(reference),
        findings=[{"code": "artificial_check", "detail": "人工结果，不是行情计算"}],
    )


def _historical_batch() -> ResearchBatch:
    batch = _batch()
    metadata = deepcopy(batch.metadata)
    metadata["synthetic"] = False
    metadata["protocol"]["data_mode"] = "historical_reconstruction"
    metadata["data_identity"]["synthetic"] = False
    metadata["data_status"] = "historical_reconstruction"
    return ResearchBatch(batch.values, metadata, batch.findings)


def _boolean_batch() -> ResearchBatch:
    metadata = _metadata(BOOLEAN_REF)
    metadata["value_type"] = "boolean"
    values = pd.DataFrame(
        {
            "observation_date": [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-05")],
            "entity_id": ["510300.SS", "510300.SS"],
            "value": [True, 0.0],
            "missing_reason": [None, None],
        }
    )
    return ResearchBatch(values, metadata, [])


def _source(root: Path, name: str = "evidence.md", text: str = "人工研究材料") -> dict:
    registry = root / "docs/research/definitions.v1.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(Path(definitions.REGISTRY).read_bytes())
    path = root / "docs/experiments" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha(path)}


def _catalog_file(root: Path, *, source: dict, packet: dict | None = None) -> Path:
    batches = []
    if packet is not None:
        packet_path = root / "docs/experiments/raw/artificial/packet.json"
        _write_json(packet_path, packet)
        batches.append(
            {"path": packet_path.relative_to(root).as_posix(), "sha256": _sha(packet_path)}
        )
    catalog = {
        "schema_version": 1,
        "bindings": [
            {
                "reference": REF,
                "aliases": ["普通动量", "12-1动量"],
                "kind": "registered",
                "label": "普通动量",
                "definition_notes": ["按有效报价行解释"],
                "sources": [source],
                "evidence": [
                    {
                        "kind": "calculation_check",
                        "summary": "仅检查人工值与定义身份",
                        "scope": "人工小例",
                        "limitations": ["不能证明投资有效"],
                        "sources": [source],
                    }
                ],
                "batches": batches,
                "legacy_panel": {"field": "mom_121"},
            },
            {
                "reference": CAND_REF,
                "aliases": ["示例候选"],
                "kind": "candidate",
                "label": "示例候选",
                "definition_notes": ["只作结构测试"],
                "sources": [source],
                "evidence": [],
                "batches": [],
                "draft_definition": source["path"],
            },
        ],
        "comparisons": [
            {
                "references": [REF, CAND_REF],
                "summary": "只比较概念，不生成新实验",
                "limitations": ["没有效果结论"],
                "sources": [source],
            }
        ],
    }
    path = root / "configs/factor-access.v1.json"
    _write_json(path, catalog)
    return path


def test_pack_research_batch_serializes_existing_rows_without_calculation(tmp_path, monkeypatch):
    from lei_signal.research.factor_lab import adapters

    monkeypatch.setattr(
        adapters,
        "calculate_batch",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("不得调用计算入口")),
    )
    source = _source(tmp_path)
    packet = pack_research_batch(
        _batch(),
        sources=[source],
        calculated_at="2026-09-22T15:30:00+08:00",
        root=tmp_path,
    )

    assert packet["schema_version"] == 1
    assert packet["kind"] == "research_batch"
    assert packet["values"][0]["value"] == 0.12
    assert packet["values"][1]["value"] is None
    assert packet["values"][1]["missing_reason"] == "warmup_history_insufficient"
    assert packet["metadata"]["synthetic"] is True
    assert packet["metadata"]["production_authorization"] == "not_authorized"
    assert packet["definition_contract_sha256"] == contract_digest(_card())


def test_validate_packet_round_trip_preserves_synthetic_qualification(tmp_path):
    source = _source(tmp_path)
    packet = pack_research_batch(
        _batch(), sources=[source], calculated_at="2026-09-22T15:30:00+08:00", root=tmp_path
    )
    checked = validate_research_packet(packet, root=tmp_path)
    assert checked == packet
    assert checked["metadata"]["data_status"] == "synthetic_input"
    assert checked["metadata"]["effectiveness_status"] == _card()["status"]["effectiveness"]


def test_pack_preserves_historical_identity_without_granting_qualification(tmp_path):
    source = _source(tmp_path)
    packet = pack_research_batch(
        _historical_batch(),
        sources=[source],
        calculated_at="2026-09-22T15:30:00+08:00",
        root=tmp_path,
    )
    assert packet["metadata"]["synthetic"] is False
    assert packet["metadata"]["protocol"]["data_mode"] == "historical_reconstruction"
    assert packet["metadata"]["data_status"] == "historical_reconstruction"
    assert packet["metadata"]["production_authorization"] == "not_authorized"


def test_boolean_values_accept_bool_and_existing_zero_one_representation(tmp_path):
    source = _source(tmp_path)
    packet = pack_research_batch(
        _boolean_batch(),
        sources=[source],
        calculated_at="2026-09-22T15:30:00+08:00",
        root=tmp_path,
    )
    assert packet["values"][0]["value"] is True
    assert packet["values"][1]["value"] == 0.0

    batch = _boolean_batch()
    batch.values.loc[0, "value"] = 2
    with pytest.raises(AccessError, match="bool or numeric 0/1"):
        pack_research_batch(
            batch,
            sources=[source],
            calculated_at="2026-09-22T15:30:00+08:00",
            root=tmp_path,
        )


@pytest.mark.parametrize(
    "mutator, match",
    [
        (lambda p: p.update(schema_version=2), "schema"),
        (lambda p: p.update(kind="script"), "kind"),
        (lambda p: p.update(calculated_at="2026-09-22 15:30:00"), "timezone"),
        (lambda p: p["metadata"].update(production_authorization="approved"), "production"),
        (lambda p: p["metadata"].update(unit="percent"), "unit"),
        (lambda p: p.update(definition_contract_sha256="0" * 64), "contract"),
        (lambda p: p["metadata"].update(purpose="unknown"), "purpose"),
        (lambda p: p["metadata"].update(entity_axis="unknown"), "entity_axis"),
        (lambda p: p["metadata"]["protocol"].update(protocol_id=""), "protocol_id"),
        (lambda p: p["metadata"]["protocol"].update(version="latest"), "version"),
        (lambda p: p["metadata"]["protocol"].update(sha256="short"), "sha256"),
        (lambda p: p["metadata"].update(calendar=[]), "calendar"),
        (lambda p: p["metadata"].update(time_evidence=[]), "time_evidence"),
        (lambda p: p["metadata"].update(code_identity=[]), "code_identity"),
    ],
)
def test_validate_packet_rejects_identity_or_authorization_drift(tmp_path, mutator, match):
    source = _source(tmp_path)
    packet = pack_research_batch(
        _batch(), sources=[source], calculated_at="2026-09-22T15:30:00+08:00", root=tmp_path
    )
    mutator(packet)
    with pytest.raises(AccessError, match=match):
        validate_research_packet(packet, root=tmp_path)


def test_packet_rejects_duplicate_rows_infinite_and_unexplained_missing(tmp_path):
    source = _source(tmp_path)
    batch = _batch()
    duplicate = pd.concat([batch.values, batch.values.iloc[[0]]], ignore_index=True)
    with pytest.raises(AccessError, match="duplicate"):
        pack_research_batch(
            ResearchBatch(duplicate, batch.metadata, []),
            sources=[source],
            calculated_at="2026-09-22T15:30:00+08:00",
            root=tmp_path,
        )

    bad_values = [(float("inf"), None, "finite"), (float("nan"), None, "missing_reason")]
    for bad, reason, match in bad_values:
        values = batch.values.iloc[[0]].copy()
        values.loc[:, "value"] = bad
        values.loc[:, "missing_reason"] = reason
        with pytest.raises(AccessError, match=match):
            pack_research_batch(
                ResearchBatch(values, batch.metadata, []),
                sources=[source],
                calculated_at="2026-09-22T15:30:00+08:00",
                root=tmp_path,
            )

    normalized_duplicate = batch.values.iloc[[0, 0]].copy()
    normalized_duplicate.index = [0, 1]
    normalized_duplicate.loc[0, "observation_date"] = "2026-01-02"
    normalized_duplicate.loc[1, "entity_id"] = " 510300.SS "
    with pytest.raises(AccessError, match="duplicate normalized"):
        pack_research_batch(
            ResearchBatch(normalized_duplicate, batch.metadata, []),
            sources=[source],
            calculated_at="2026-09-22T15:30:00+08:00",
            root=tmp_path,
        )


def test_sources_reject_absolute_parent_escape_wrong_hash_and_symlink_escape(tmp_path):
    source = _source(tmp_path)
    for bad in [
        {"path": str((tmp_path / source["path"]).resolve()), "sha256": source["sha256"]},
        {"path": "../secret", "sha256": source["sha256"]},
        {"path": source["path"], "sha256": "0" * 64},
    ]:
        with pytest.raises(AccessError):
            pack_research_batch(
                _batch(),
                sources=[bad],
                calculated_at="2026-09-22T15:30:00+08:00",
                root=tmp_path,
            )
    outside = tmp_path.parent / "outside-factor-access.md"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "docs/research/escape.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    with pytest.raises(AccessError, match="outside"):
        pack_research_batch(
            _batch(),
            sources=[{"path": "docs/research/escape.md", "sha256": _sha(outside)}],
            calculated_at="2026-09-22T15:30:00+08:00",
            root=tmp_path,
        )


def test_load_catalog_resolves_registered_and_keeps_candidate_separate(tmp_path):
    source = _source(tmp_path)
    path = _catalog_file(tmp_path, source=source)
    catalog = load_access_catalog(root=tmp_path, catalog_path=path)

    assert catalog["registry"]["version"] == "1.4.4"
    assert catalog["definitions"][REF]["id"] == "mixed.momentum.raw"
    assert catalog["definitions"][OTHER_REF]["id"] == "mixed.rv20"
    assert CAND_REF not in catalog["definitions"]
    assert catalog["bindings"][REF]["legacy_panel"] == {"field": "mom_121"}
    assert catalog["catalog_source"]["sha256"] == _sha(path)
    assert len(catalog["registry_source"]["sha256"]) == 64


def test_catalog_rejects_unknown_ref_and_code_but_keeps_ambiguous_aliases(tmp_path):
    source = _source(tmp_path)
    path = _catalog_file(tmp_path, source=source)
    data = json.loads(path.read_text(encoding="utf-8"))

    unknown = deepcopy(data)
    unknown["bindings"][0]["reference"] = "mixed.unknown@1.0.0"
    _write_json(path, unknown)
    with pytest.raises(AccessError, match="resolvable"):
        load_access_catalog(root=tmp_path, catalog_path=path)

    conflict = deepcopy(data)
    conflict["bindings"][1]["aliases"] = ["普通动量"]
    _write_json(path, conflict)
    catalog = load_access_catalog(root=tmp_path, catalog_path=path)
    assert "普通动量" in catalog["bindings"][REF]["aliases"]
    assert catalog["bindings"][CAND_REF]["aliases"] == ["普通动量"]

    code = deepcopy(data)
    code["bindings"][0]["module"] = "evil.module"
    _write_json(path, code)
    with pytest.raises(AccessError, match="code entry"):
        load_access_catalog(root=tmp_path, catalog_path=path)


def test_catalog_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "configs/factor-access.v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schema_version":1,"schema_version":1,"bindings":[],"comparisons":[]}',
        encoding="utf-8",
    )
    with pytest.raises(AccessError, match="duplicate JSON key"):
        load_access_catalog(root=tmp_path, catalog_path=path)


def test_catalog_rejects_bool_schema_candidate_panel_and_empty_evidence_sources(tmp_path):
    source = _source(tmp_path)
    path = _catalog_file(tmp_path, source=source)
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    bad_schema = deepcopy(data)
    bad_schema["schema_version"] = True
    cases.append((bad_schema, "schema"))
    candidate_panel = deepcopy(data)
    candidate_panel["bindings"][1]["legacy_panel"] = {"field": "draft"}
    cases.append((candidate_panel, "registered-only"))
    empty_evidence = deepcopy(data)
    empty_evidence["bindings"][0]["evidence"][0]["sources"] = []
    cases.append((empty_evidence, "must not be empty"))
    empty_comparison = deepcopy(data)
    empty_comparison["comparisons"][0]["sources"] = []
    cases.append((empty_comparison, "must not be empty"))
    for payload, match in cases:
        _write_json(path, payload)
        with pytest.raises(AccessError, match=match):
            load_access_catalog(root=tmp_path, catalog_path=path)


def test_read_materials_verifies_sources_and_packet_and_isolates_bad_binding(tmp_path):
    source = _source(tmp_path)
    packet = pack_research_batch(
        _batch(), sources=[source], calculated_at="2026-09-22T15:30:00+08:00", root=tmp_path
    )
    path = _catalog_file(tmp_path, source=source, packet=packet)
    catalog = load_access_catalog(root=tmp_path, catalog_path=path)

    materials = read_materials(catalog, REF, root=tmp_path)
    assert materials["reference"] == REF
    assert materials["batches"][0] == packet
    verified_paths = {item["path"] for item in materials["sources_verified"]}
    assert verified_paths == {source["path"], "docs/experiments/raw/artificial/packet.json"}

    # 破坏候选来源不会污染未绑定来源的其他正式定义读取。
    (tmp_path / source["path"]).write_text("drift", encoding="utf-8")
    empty = read_materials(catalog, OTHER_REF, root=tmp_path)
    assert empty["reference"] == OTHER_REF
    assert empty["binding"] is None and empty["batches"] == []
    assert empty["label"] == catalog["definitions"][OTHER_REF]["name"]
    assert empty["sources"] == [] and empty["batch_files_verified"] == []
    with pytest.raises(AccessError, match="hash"):
        read_materials(catalog, REF, root=tmp_path)


def test_read_comparison_matches_same_set_and_verifies_source(tmp_path):
    source = _source(tmp_path)
    path = _catalog_file(tmp_path, source=source)
    catalog = load_access_catalog(root=tmp_path, catalog_path=path)
    comparison = read_comparison(catalog, [CAND_REF, REF], root=tmp_path)
    assert comparison is not None
    assert comparison["summary"] == "只比较概念，不生成新实验"
    assert comparison["sources_verified"] == [source]
    assert read_comparison(catalog, [REF], root=tmp_path) is None

    data = json.loads(path.read_text(encoding="utf-8"))
    data["comparisons"][0]["references"] = [REF, OTHER_REF]
    _write_json(path, data)
    catalog = load_access_catalog(root=tmp_path, catalog_path=path)
    assert read_comparison(catalog, [OTHER_REF, REF], root=tmp_path) is not None


def test_catalog_path_must_stay_inside_root(tmp_path):
    outside = tmp_path.parent / "outside-catalog.json"
    _write_json(outside, {"schema_version": 1, "bindings": [], "comparisons": []})
    with pytest.raises(AccessError, match="outside"):
        load_access_catalog(root=tmp_path, catalog_path=outside)
