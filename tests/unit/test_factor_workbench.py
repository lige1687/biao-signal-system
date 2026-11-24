"""The review endpoint cannot silently become a research or trading executor."""
import json
import copy
import hashlib
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from lei_signal.factor_workbench import app as module


@pytest.fixture
def client(monkeypatch):
    module._answers.clear()
    module._busy = False
    module._requests = 0
    monkeypatch.setattr(module.llm, "load_ark_config", lambda: SimpleNamespace())
    return TestClient(module.app)


BODY = {"datasetId": "fixed2014_300_legacy", "factorId": "cool", "poolId": "all_qualified", "periodId": "all", "feeBps": 25}


def test_get_never_calls_model_and_post_is_cached(client, monkeypatch):
    calls = []
    def model(*args):
        calls.append(args)
        return {"text": json.dumps({"selected_ids": ["quality", "scope", "ranking", "excess", "next"]}), "usage": None}
    monkeypatch.setattr(module, "invoke_selection", model)
    assert client.get("/api/factor-workbench/health").json()["modelRequests"] == 0
    assert client.get("/api/factor-workbench/interpret").status_code == 405
    assert not calls
    a = client.post("/api/factor-workbench/interpret", json=BODY)
    assert a.status_code == 200
    assert a.json()["mode"] == "agent"
    assert a.json()["cards"][0]["id"] == "quality"
    assert client.post("/api/factor-workbench/interpret", json=BODY).json()["cached"]
    assert len(calls) == 1
    assert next(c for c in a.json()["cards"] if c["id"] == "ranking")["source"].startswith("/research/")


def test_invalid_selection_and_cross_origin_do_not_invoke(client, monkeypatch):
    monkeypatch.setattr(module, "invoke_selection", lambda *args: pytest.fail("unexpected invocation"))
    assert client.post("/api/factor-workbench/interpret", json={**BODY, "datasetId": "unavailable"}).status_code == 422
    assert client.post("/api/factor-workbench/interpret", json=BODY, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/api/factor-workbench/interpret", json={**BODY, "extra": "execute"}).status_code == 422


def test_provider_failure_is_explicit_template_not_fabricated_agent(client, monkeypatch):
    monkeypatch.setattr(module, "invoke_selection", lambda *args: {"text": '{"selected_ids":["invented"]}'})
    response = client.post("/api/factor-workbench/interpret", json=BODY).json()
    assert response["mode"] == "rules"
    assert len(response["cards"]) == 5
    assert "固定研究检查卡" in response["limitations"][0]
    assert not module._answers


def test_derived_file_drift_rejected(monkeypatch):
    original = module.build_metrics
    def altered(*args):
        data = original(*args)
        data["irRecords"][0]["ir"] += 1
        return data
    monkeypatch.setattr(module, "build_metrics", altered)
    with pytest.raises(ValueError, match="derived_metrics_changed"):
        module.read_evidence()


def test_pinned_evidence_accepts_only_correlation_roundoff():
    frozen, _ = module.read_evidence()
    rebuilt = copy.deepcopy(frozen)
    rebuilt["correlations"][0]["matrix"][0][3] -= 1.1102230246251565e-16
    assert module._same_derived_metrics(frozen, rebuilt)


def test_actual_derived_change_and_other_fields_rejected():
    frozen, _ = module.read_evidence()
    changed = copy.deepcopy(frozen)
    changed["correlations"][0]["matrix"][0][3] += 1e-8
    assert not module._same_derived_metrics(frozen, changed)
    changed = copy.deepcopy(frozen)
    changed["correlations"][0]["counts"][0][3] += 1
    assert not module._same_derived_metrics(frozen, changed)
    changed = copy.deepcopy(frozen)
    changed["irRecords"][0]["ir"] += 1e-16
    assert not module._same_derived_metrics(frozen, changed)


def test_material_correlation_change_rejected_by_reader(monkeypatch):
    original = module.build_metrics
    def altered(*args):
        data = original(*args)
        data["correlations"][0]["matrix"][0][3] += 1e-8
        return data
    monkeypatch.setattr(module, "build_metrics", altered)
    with pytest.raises(ValueError, match="derived_metrics_changed"):
        module.read_evidence()


def test_changed_frozen_metrics_rejected_even_with_updated_manifest(monkeypatch, tmp_path):
    raw = module.METRICS.read_bytes().replace(b'"schemaVersion":1', b'"schemaVersion":2', 1)
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_bytes(raw)
    manifest = json.loads(module.METRICS_MANIFEST.read_text())
    manifest["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "METRICS", metrics_path)
    monkeypatch.setattr(module, "METRICS_MANIFEST", manifest_path)
    with pytest.raises(ValueError, match="metrics_file_changed"):
        module.read_evidence()


def test_model_cannot_drop_duplicate_or_add_cards():
    cards = [{"id": x} for x in ("a", "b")]
    assert module.validate_order('{"selected_ids":["b","a"]}', cards) == ["b", "a"]
    assert module.validate_order('{"selected_ids":["a","a"]}', cards) is None
    assert module.validate_order('{"selected_ids":["a","b"],"text":"invented"}', cards) is None
