"""A new research producer plugs in using only data; no factor engine is run."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.copilot import factor_readonly as fr
from lei_signal.research.definitions import load_registry, resolve
from lei_signal.research.factor_access import pack_research_batch
from lei_signal.research.factor_lab.contracts import ResearchBatch, build_metadata
from tests.integration import test_agent_factor_readonly as offline_fixtures

client = offline_fixtures.client

NOW = datetime.fromisoformat("2026-09-22T16:00:00+08:00")
REF = "unseen.frost_strength@1.0.0"


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def source(root, rel):
    return {"path": rel, "sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest()}


@pytest.fixture()
def research(tmp_path):
    registry = copy.deepcopy(load_registry())
    card = resolve(registry, "mixed.rv20@1.0.0", purpose="description")
    card.update(id="unseen.frost_strength", version="1.0.0", name="霜叶强度测试因子")
    card["definition"]["formula"] = "fixture value; never evaluate this text"
    registry["objects"].append(card)
    regpath = tmp_path / "docs/research/definitions.v1.json"
    save_json(regpath, registry)
    report = "docs/experiments/frost-fixture-2026-09-22.md"
    (tmp_path / report).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / report).write_text("# 人工夹具\n\n## 一句话结论（大白话）\n仅说明接口。")
    src = source(tmp_path, report)
    metadata = build_metadata(
        reference=REF, card=resolve(registry, REF, purpose="description"),
        card_kind="registered",
        protocol={"protocol_id": "fixture-only", "version": "1.0.0",
                  "kind": "calculation_only", "data_mode": "synthetic", "synthetic": True,
                  "timezone": "Asia/Shanghai"},
        entity_axis="instrument", value_type="continuous",
        data_identity={"synthetic": True, "inputs": {"fixture": src}},
        code_identity={"kind": "handwritten fixture; no calculation"},
        calendar={"timezone": "Asia/Shanghai", "note": "artificial"},
        time_evidence={"observation_time": "synthetic close"},
    )
    # This is an existing result fixture, not a call to a factor calculation.
    batch = ResearchBatch(pd.DataFrame([{
        "observation_date": "2026-09-21", "entity_id": "510300.SS",
        "value": 0.125, "missing_reason": None,
    }]), metadata, [])
    packet = pack_research_batch(batch, sources=[src], calculated_at=NOW.isoformat(),
                                 root=tmp_path, registry_path=regpath)
    batchrel = "docs/experiments/raw/frost-fixture-2026-09-22/result.json"
    save_json(tmp_path / batchrel, packet)
    binding = {
        "reference": REF, "kind": "registered", "label": "霜叶强度",
        "aliases": ["霜叶强度"], "definition_notes": [], "sources": [src],
        "evidence": [{"kind": "calculation_check", "summary": "只核对接口，不证明市场效果。",
                      "scope": "人工行，510300.SS，2026-09-21",
                      "limitations": ["没有真实研究结果。"], "sources": [src]}],
        "batches": [source(tmp_path, batchrel)],
    }
    index = {"schema_version": 1, "bindings": [binding], "comparisons": []}
    indexpath = tmp_path / "configs/factor-access.v1.json"
    save_json(indexpath, index)
    return {"root": tmp_path, "registry_path": regpath, "index_path": indexpath,
            "index": index, "report": report, "packet": packet, "batchrel": batchrel}


def ask(research, question):
    def forbidden():
        raise AssertionError("generic research material must not read the legacy panel")
    return fr.build_factor_reply(question, "510300.SS", root=research["root"],
                                 registry_path=research["registry_path"], panel_loader=forbidden,
                                 now=NOW)


def test_unseen_factor_end_to_end_through_one_contract(research):
    engine_sha = hashlib.sha256(Path(fr.__file__).read_bytes()).hexdigest()
    assert fr.is_factor_question("霜叶强度是什么", root=research["root"])
    definition = ask(research, "霜叶强度怎么定义")
    assert definition["definition_refs"] == [REF]
    assert "fixture value" in definition["reply"]
    evidence = ask(research, "霜叶强度过去有用吗")
    assert evidence["intent"] == "evidence"
    assert "人工行" in evidence["reply"] and "不证明市场效果" in evidence["reply"]
    reading = ask(research, "霜叶强度2026-09-21已有读数是多少")
    assert reading["status"] == "historical_only"
    assert reading["metadata"]["synthetic"] is True
    assert reading["metadata"]["calculated_at"] == NOW.isoformat()
    assert "12.50%" in reading["reply"] and "人工数据" in reading["reply"]
    assert "数据截止：未知" in reading["reply"]
    assert "定义要求的价格口径" in reading["reply"]
    assert research["batchrel"] in {src["path"] for src in reading["sources"]}
    assert ask(research, "霜叶强度当前读数是多少")["status"] == "unqualified_current"
    assert ask(research, "帮我回测霜叶强度")["metadata"]["executed"] is False
    assert hashlib.sha256(Path(fr.__file__).read_bytes()).hexdigest() == engine_sha


def test_new_binding_is_discovered_without_restart_or_code_edit(research):
    original = copy.deepcopy(research["index"])
    research["index"]["bindings"] = []
    save_json(research["index_path"], research["index"])
    assert ask(research, REF + "过去有用吗")["status"] == "evidence_not_bound"
    assert not fr.is_factor_question("霜叶强度过去有用吗", root=research["root"])
    save_json(research["index_path"], original)
    assert fr.is_factor_question("霜叶强度过去有用吗", root=research["root"])
    assert ask(research, "霜叶强度因子过去有用吗")["intent"] == "evidence"
    assert ask(research, "霜叶强度因子过去有用吗")["status"] == "limited"


def test_source_drift_stops_only_that_material(research):
    (research["root"] / research["report"]).write_text("changed")
    assert ask(research, "霜叶强度过去有用吗")["status"] == "source_drift"
    separate = ask(research, "trend.sma50@1.0.0怎么定义")
    assert separate["intent"] == "definition" and separate["status"] != "source_drift"


def test_new_version_does_not_inherit_old_version_evidence(research):
    registry = json.loads(research["registry_path"].read_text())
    newer = copy.deepcopy(registry["objects"][-1])
    newer["version"] = "2.0.0"
    registry["objects"].append(newer)
    save_json(research["registry_path"], registry)
    result = ask(research, "unseen.frost_strength@2.0.0过去有用吗")
    assert result["status"] == "evidence_not_bound"
    result = ask(research, "霜叶强度测试因子过去有用吗")
    assert result["status"] == "needs_clarification"


def test_multiple_observation_dates_require_selection(research):
    packet = research["packet"]
    row = copy.deepcopy(packet["values"][0])
    row["observation_date"] = "2026-09-20"
    packet["values"].append(row)
    save_json(research["root"] / research["batchrel"], packet)
    research["index"]["bindings"][0]["batches"] = [
        source(research["root"], research["batchrel"])]
    save_json(research["index_path"], research["index"])
    assert ask(research, "霜叶强度已有读数是多少")["status"] == "needs_clarification"
    assert ask(research, "霜叶强度2026-09-20读数是多少")["status"] == "historical_only"


def test_actual_agent_route_discovers_new_alias(client, research, monkeypatch):
    loader = fr.load_access_catalog
    monkeypatch.setattr(fr, "_ROOT", research["root"])
    monkeypatch.setattr(fr, "load_access_catalog", lambda **kw: loader(
        **{**kw, "root": research["root"], "registry_path": research["registry_path"]}))
    response = client.post("/api/agent/chat", json={
        "message": "霜叶强度过去有用吗", "symbol": "510300.SS",
    })
    assert response.status_code == 200
    pack = response.json()["evidence_card"]["factor_readonly"]
    assert pack["definition_refs"] == [REF]
    assert "人工行" in pack["reply"]
    resolved = client.post("/api/copilot/resolve", json={
        "message": "霜叶强度是什么", "selected_symbol": "510300.SS",
    }).json()
    assert resolved["discussion_context"]["factor_readonly"] is True


@pytest.mark.parametrize("entities", [
    "entity_id=510300.SS entity_id=510500.SS",
    "entity_id=universe.fixture 510300 510500",
    "entity_id=510500.SS 510300",
])
def test_conflicting_research_entities_are_not_silently_selected(research, entities):
    result = ask(research, f"霜叶强度2026-09-21已有读数 {entities}")
    assert result["status"] == "needs_clarification"


def test_generic_universe_entity_reaches_agent_route(client, research, monkeypatch):
    packet = research["packet"]
    packet["values"][0]["entity_id"] = "universe.fixture"
    packet["metadata"]["entity_axis"] = "universe"
    packet["metadata"]["universe_identity"] = {"kind": "artificial_fixture"}
    save_json(research["root"] / research["batchrel"], packet)
    research["index"]["bindings"][0]["batches"] = [source(research["root"], research["batchrel"])]
    save_json(research["index_path"], research["index"])
    loader = fr.load_access_catalog
    monkeypatch.setattr(fr, "_ROOT", research["root"])
    monkeypatch.setattr(fr, "load_access_catalog", lambda **kw: loader(
        **{**kw, "root": research["root"], "registry_path": research["registry_path"]}))
    response = client.post("/api/agent/chat", json={
        "message": "霜叶强度2026-09-21已有读数 entity_id=universe.fixture",
    })
    assert response.status_code == 200
    pack = response.json()["evidence_card"]["factor_readonly"]
    assert pack["status"] == "historical_only"
    assert pack["symbol"] == "universe.fixture"


def test_unregistered_comparison_only_explains_definitions(research):
    result = ask(research, f"比较{REF}与trend.sma50@1.0.0")
    assert result["status"] == "comparison_not_bound"
    assert result["metadata"]["executed"] is False
    assert "不能判断谁更有效" in result["reply"]
