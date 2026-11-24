"""A historical factor row and its bound evidence can answer one use question."""
from __future__ import annotations

import copy
import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

from lei_signal.research.factor_access import AccessError


MODULE = Path(__file__).resolve().parents[2] / "src/lei_signal/copilot/factor_readonly.py"
SPEC = importlib.util.spec_from_file_location("factor_observation_delivery", MODULE)
assert SPEC and SPEC.loader
fr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fr)

REF = "research.test.range@1.0.0"
NOW = datetime.fromisoformat("2026-10-12T16:00:00+08:00")


@pytest.fixture()
def research(monkeypatch):
    card = {"name": "测试波动观察", "input": {"price_basis": "economic_price"},
            "definition": {"unit": "ratio"},
            "status": {"production": "not_authorized"},
            "lifecycle": {"state": "verified"}}
    row = {"observation_date": "2026-06-30", "entity_id": "510300.SS",
           "value": 0.01809099161819631, "missing_reason": None}
    packet = {"values": [row], "calculated_at": "2026-10-12T15:00:00+08:00",
              "definition_contract_sha256": "a" * 64,
              "metadata": {"reference": REF, "card": card, "unit": "ratio",
                           "purpose": "calculation_only", "synthetic": True}}
    material = {"label": "测试波动观察", "batches": [packet],
                "evidence": [{"kind": "predictive_study",
                              "summary": "历史误差改善很小，且没有胜过简单历史平均。",
                              "scope": "人工隔离资料，仅测试回答结构。",
                              "limitations": ["人工资料，不能证明真实效果。"]}],
                "sources_verified": [{"path": "tests/fixtures/factor-observation.json",
                                      "sha256": "b" * 64}]}
    catalog = {"definitions": {REF: card},
               "bindings": {REF: {"reference": REF, "aliases": ["测试波动观察"]}},
               "catalog_source": {"path": "configs/factor-access.v1.json", "sha256": "c" * 64},
               "registry_source": {"path": "docs/research/definitions.v1.json", "sha256": "d" * 64}}
    monkeypatch.setattr(fr, "load_access_catalog", lambda **kwargs: catalog)
    monkeypatch.setattr(fr, "read_materials", lambda *args, **kwargs: material)

    def ask(message, symbol="510300.SS"):
        def forbidden():
            raise AssertionError("legacy panel or calculation was called")
        return fr.build_factor_reply(message, symbol, panel_loader=forbidden,
                                     now=NOW, root=Path("/unused"))

    return material, ask


def test_explicit_usefulness_combines_validated_row_and_bound_evidence(research):
    material, ask = research
    result = ask(f"{REF} 510300.SS 2026-06-30 已有读数和研究证据对判断有什么帮助？")
    assert result["status"] == "historical_only"
    assert result["intent"] == "usefulness_assessment"
    assert result["metadata"]["decision_change"] == "not_authorized"
    assert result["metadata"]["observation_as_of"] == "2026-06-30"
    assert result["metadata"]["calculated_at"] == "2026-10-12T15:00:00+08:00"
    assert result["metadata"]["synthetic"] is True
    assert "人工数据测试" in result["reply"]
    assert "0.01809099162" in result["reply"] and "1.8091%" in result["reply"]
    assert material["evidence"][0]["summary"] in result["reply"]
    assert "观测日期：2026-06-30" in result["reply"]
    assert "计算时间：2026-10-12T15:00:00+08:00" in result["reply"]
    assert "接入只证明资料可读" in result["reply"]
    assert any(s["path"] == "tests/fixtures/factor-observation.json" for s in result["sources"])
    assert "\n\n已有研究：" in result["reply"]
    assert ask(f"{REF} 510300.SS 2026-06-30 已有读数和研究证据")["status"] == "needs_clarification"


@pytest.mark.parametrize("message,symbol,expected", [
    (f"{REF} 510500.SS 2026-06-30 对判断有什么帮助", "510500.SS", "unavailable"),
    (f"{REF} 510300.SS 2026-06-29 对判断有什么帮助", "510300.SS", "unavailable"),
    (f"{REF} 510300.SS 当前读数对判断有什么帮助", "510300.SS", "unqualified_current"),
])
def test_usefulness_keeps_existing_observation_failures(research, message, symbol, expected):
    _, ask = research
    result = ask(message, symbol)
    assert result["status"] == expected
    assert result["intent"] != "usefulness_assessment"
    assert "已有研究：" not in result["reply"]


def test_missing_packet_future_row_and_missing_value_do_not_become_success(research):
    material, ask = research
    original = copy.deepcopy(material["batches"])
    material["batches"] = []
    assert ask(f"{REF} 510300.SS 2026-06-30 怎样用于判断")["status"] == "unavailable"
    material["batches"] = copy.deepcopy(original)
    material["batches"][0]["values"][0]["observation_date"] = "2030-06-30"
    assert ask(f"{REF} 510300.SS 2030-06-30 怎样用于判断")["status"] == "unavailable"
    material["batches"] = copy.deepcopy(original)
    material["batches"][0]["values"][0].update(value=None, missing_reason="no_quote")
    assert ask(f"{REF} 510300.SS 2026-06-30 怎样用于判断")["status"] == "unavailable"


def test_source_or_definition_error_and_unsafe_requests_stay_blocked(research, monkeypatch):
    _, ask = research
    message = f"{REF} 510300.SS 2026-06-30 怎样用于判断"
    monkeypatch.setattr(fr, "read_materials", lambda *args, **kwargs: (_ for _ in ()).throw(
        AccessError("bad source or definition identity")))
    assert ask(message)["status"] == "source_drift"
    assert ask(f"{REF} 510300.SS 2026-06-30 能直接买吗，怎样用于判断")["status"] == "unsupported_use"
    assert ask(f"{REF} 510300.SS 2026-06-30 帮我回测，怎样用于判断")["status"] == "proposal_only"
