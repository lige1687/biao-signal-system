"""Read the actual bound observation and reject tampered isolated packets."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest

from lei_signal.research import definitions
from lei_signal.research.description_registry import load_description_registry


MAIN = definitions.ROOT.resolve()
WORKTREE = Path(__file__).resolve().parents[2]
REF = "research.price_volume.range_mean20@1.0.0"
DATE = "2026-06-30"
SYMBOL = "510300.SS"
PACKET = MAIN / "docs/research/factor-observations/510300-range-mean20-20261012/packet.json"
BASELINE_DIR = WORKTREE / "docs/experiments/raw/factor-observation-agent-2026-10-12"
BASELINE_SNAPSHOT = BASELINE_DIR / "factor-access.before.json"
BASELINE_FINGERPRINTS = BASELINE_DIR / "baseline-source-fingerprints.json"


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


access = _module("factor_access_delivery", WORKTREE / "src/lei_signal/research/factor_access.py")
consumer = _module("factor_readonly_delivery", WORKTREE / "src/lei_signal/copilot/factor_readonly.py")
consumer.load_access_catalog = access.load_access_catalog
consumer.read_materials = access.read_materials


def _ask(catalog_path: Path):
    def forbidden_panel():
        raise AssertionError("legacy panel or computation must not run")
    return consumer.build_factor_reply(
        f"{REF} {SYMBOL} {DATE} 已有读数和研究证据对判断有什么帮助？",
        SYMBOL, panel_loader=forbidden_panel,
        now=datetime.fromisoformat("2026-10-12T16:00:00+08:00"),
        root=MAIN, catalog_path=catalog_path,
    )


def test_real_bound_packet_is_read_and_changes_answer_fields():
    recorded = json.loads(BASELINE_FINGERPRINTS.read_text(encoding="utf-8"))
    assert hashlib.sha256(BASELINE_SNAPSHOT.read_bytes()).hexdigest() == recorded[
        "configs/factor-access.v1.json"
    ]
    baseline = json.loads(BASELINE_SNAPSHOT.read_text(encoding="utf-8"))
    baseline_binding = next(item for item in baseline["bindings"] if item["reference"] == REF)
    assert baseline_binding["batches"] == []
    before = _ask(BASELINE_SNAPSHOT)
    after = _ask(WORKTREE / "configs/factor-access.v1.json")
    assert before["status"] == "unavailable"
    assert before["intent"] != "usefulness_assessment"
    assert after["status"] == "historical_only"
    assert after["intent"] == "usefulness_assessment"
    assert after["metadata"]["synthetic"] is False
    assert after["metadata"]["observation_as_of"] == DATE
    assert after["metadata"]["calculated_at"]
    assert after["metadata"]["decision_change"] == "not_authorized"
    assert "1.8091%" in after["reply"]
    assert "对判断的帮助" in after["reply"]
    assert "已有研究" in after["reply"]
    assert str(PACKET.relative_to(MAIN)) in {s["path"] for s in after["sources"]}

    catalog = access.load_access_catalog(root=MAIN,
        catalog_path=WORKTREE / "configs/factor-access.v1.json")
    materials = access.read_materials(catalog, REF, root=MAIN)
    assert len(materials["batches"]) == 1
    packet = materials["batches"][0]
    assert packet["values"] == [{"observation_date": DATE, "entity_id": SYMBOL,
                                   "value": pytest.approx(0.01809099161819631),
                                   "missing_reason": None}]
    assert packet["metadata"]["synthetic"] is False
    assert packet["metadata"]["production_authorization"] == "not_authorized"

    current = consumer.build_factor_reply(
        f"{REF} {SYMBOL} 当前读数对判断有什么帮助", SYMBOL,
        panel_loader=lambda: (_ for _ in ()).throw(AssertionError("panel called")),
        now=datetime.fromisoformat("2026-10-12T16:00:00+08:00"),
        root=MAIN, catalog_path=WORKTREE / "configs/factor-access.v1.json")
    assert current["status"] == "unqualified_current"
    assert current["intent"] != "usefulness_assessment"


@pytest.fixture()
def isolated_packet(tmp_path):
    view, errors = load_description_registry(MAIN / "docs/research/definitions.v1.json")
    assert len(errors) == 3
    obj = next(item for item in view["objects"] if
               f"{item['id']}@{item['version']}" == REF)
    registry = copy.deepcopy(view)
    registry["objects"] = [copy.deepcopy(obj)]
    registry["models"] = []
    registry.pop("research_references", None)
    registry_path = tmp_path / "docs/research/definitions.v1.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    assert REF in definitions.validate_registry(registry)

    # This is a synthetic validation fixture; it makes no claim about the real input.
    source_path = tmp_path / "tests/fixtures/artificial-input.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text('{"artificial":true}', encoding="utf-8")
    source = {"path": "tests/fixtures/artificial-input.json",
              "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()}
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    packet["sources"] = [source]
    metadata = packet["metadata"]
    metadata["synthetic"] = True
    metadata["data_status"] = "synthetic_input"
    metadata["data_identity"] = {"synthetic": True, "fixture": source}
    metadata["protocol"]["data_mode"] = "synthetic"
    metadata["time_evidence"] = {"observation_time": "artificial fixture"}
    assert access.validate_research_packet(packet, root=tmp_path,
                                           registry_path=registry_path)["metadata"]["synthetic"] is True
    return tmp_path, registry_path, source_path, packet


def test_isolated_source_hash_drift_is_rejected(isolated_packet):
    root, registry_path, source_path, packet = isolated_packet
    source_path.write_text('{"artificial":false}', encoding="utf-8")
    with pytest.raises(access.AccessError, match="hash mismatch"):
        access.validate_research_packet(packet, root=root, registry_path=registry_path)


@pytest.mark.parametrize("change", ["definition_contract", "production_authorization", "bad_dependency"])
def test_isolated_identity_or_authorization_tampering_is_rejected(isolated_packet, change):
    root, registry_path, _, packet = isolated_packet
    if change == "definition_contract":
        packet["definition_contract_sha256"] = "0" * 64
    elif change == "production_authorization":
        packet["metadata"]["production_authorization"] = "production_approved"
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["objects"][0]["dependencies"] = ["research.missing@1.0.0"]
        registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(access.AccessError):
        access.validate_research_packet(packet, root=root, registry_path=registry_path)


def test_strict_research_loader_still_rejects_the_three_global_bad_definitions():
    _, errors = load_description_registry(MAIN / "docs/research/definitions.v1.json")
    assert len(errors) == 3
    with pytest.raises(ValueError):
        definitions.load_registry(MAIN / "docs/research/definitions.v1.json")
