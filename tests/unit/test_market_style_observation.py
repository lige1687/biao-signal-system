"""Preview API boundaries: read-only facts, explicit model click and strict selection."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from lei_signal.market_style_observation import app as module
from lei_signal.market_style_observation.evidence import build_evidence
from lei_signal.market_style_observation import transport


def _upstream(url: str):
    if "breadth-history" in url:
        return {"history": [
            {"date": "2026-10-15", "breadth_20": 41, "breadth_50": 35, "breadth_200": 29},
            {"date": "2026-10-16", "breadth_20": 40, "breadth_50": 34, "breadth_200": 28},
        ]}
    if "observations" in url:
        return {"items": [
            {"metric_id": "vix", "value": 18.5, "unit": "指数点", "observation_date": "2026-10-16", "quality_status": "time_unverified"},
            {"metric_id": "hy_oas", "value": 4.2, "unit": "%", "observation_date": "2026-10-15", "quality_status": "stale"},
        ]}
    if "strategy-portfolios" in url:
        return {"markets": [{"id": "US", "comparison": {
            "return_correlation": 0.8, "holding_overlap": 0.3,
        }}]}
    return None


def _reset():
    with module._LOCK:
        module._SNAPSHOTS.clear()
        module._GENERATED.clear()
        module._IN_FLIGHT.clear()
        module._SNAPSHOT_TIMES.clear()
        module._QUERY_CACHE.clear()
        module._MODEL_REQUESTS = 0


def test_get_snapshot_never_calls_model(monkeypatch):
    _reset()
    monkeypatch.setattr(module, "build_evidence", lambda market, window_days: build_evidence(market, window_days, get_json=_upstream))
    monkeypatch.setattr(module, "invoke_selection", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("GET called model")))
    client = TestClient(module.app)
    response = client.get("/api/market-style/snapshot", params={"market": "us", "window_days": 365})
    assert response.status_code == 200
    data = response.json()
    assert len(data["snapshot_id"]) == 64
    assert data["asof"] and data["market"] == "us" and data["window_days"] == 365
    assert len(data["cards"]) == 4
    assert "−4.55%" in data["cards"][0]["fact"]
    assert "收缩" in data["cards"][1]["fact"]
    assert "VIX" in data["cards"][2]["fact"]
    assert "可用时点待核" in data["cards"][2]["fact"]
    assert "旧数据" in data["cards"][2]["fact"]
    assert data["cards"][2]["data_date"] is None
    assert data["cards"][3]["data_date"] is None
    assert "持仓" not in data["cards"][3]["fact"]
    assert client.get("/health").json()["model_requests"] == 0
    assert client.get("/api/market-style/snapshot", params={"market": "us", "window_days": 2}).status_code == 422


def test_post_selects_server_cards_once(monkeypatch):
    _reset()
    monkeypatch.setattr(module, "build_evidence", lambda market, window_days: build_evidence(market, window_days, get_json=_upstream))
    calls = []
    monkeypatch.setattr(module.llm, "load_ark_config", lambda: module.llm.ArkConfig(api_key="test-only", model="fake-test-model"))
    def choose(*args, **kwargs):
        calls.append(1)
        return {"text": '{"selected_ids":["risk","world_style","breadth"]}',
                "usage": {"input_tokens": 100, "output_tokens": 20},
                "elapsed_ms": 1200, "error_code": ""}
    monkeypatch.setattr(module, "invoke_selection", choose)
    client = TestClient(module.app)
    sid = client.get("/api/market-style/snapshot", params={"market": "us"}).json()["snapshot_id"]
    first = client.post("/api/market-style/interpret", json={"snapshot_id": sid})
    second = client.post("/api/market-style/interpret", json={"snapshot_id": sid})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["mode"] == "evidence_selection"
    assert first.json()["usage"] == {"input_tokens": 100, "output_tokens": 20}
    assert first.json()["elapsed_ms"] == 1200 and first.json()["cost"] is None
    assert [card["id"] for card in first.json()["cards"]] == ["risk", "world_style", "breadth"]
    assert calls == [1]
    assert client.get("/health").json()["model_requests"] == 1


def test_unknown_snapshot_and_invalid_model_output(monkeypatch):
    _reset()
    monkeypatch.setattr(module, "build_evidence", lambda market, window_days: build_evidence(market, window_days, get_json=_upstream))
    monkeypatch.setattr(module.llm, "load_ark_config", lambda: module.llm.ArkConfig(api_key="test-only", model="fake-test-model"))
    client = TestClient(module.app)
    assert client.post("/api/market-style/interpret", json={"snapshot_id": "0" * 64}).status_code == 404
    sid = client.get("/api/market-style/snapshot", params={"market": "cn"}).json()["snapshot_id"]
    for raw in ('{"selected_ids":["world_style","world_style","breadth"]}',
                '{"selected_ids":["world_style","breadth","invented"]}',
                '{"selected_ids":["world_style","breadth","risk"],"fact":"buy"}'):
        monkeypatch.setattr(module, "invoke_selection", lambda *args, value=raw, **kwargs: {"text": value, "usage": None, "elapsed_ms": 5, "error_code": ""})
        response = client.post("/api/market-style/interpret", json={"snapshot_id": sid})
        assert response.status_code == 422
        assert response.json()["generated"] is False
    monkeypatch.setattr(module, "invoke_selection", lambda *args, **kwargs: {"text": None, "usage": None, "elapsed_ms": 5, "error_code": "timeout"})
    response = client.post("/api/market-style/interpret", json={"snapshot_id": sid})
    assert response.status_code == 503 and response.json()["generated"] is False
    assert response.json()["error"] == "timeout"
    assert client.get("/health").json()["completed"] == 0
    with module._LOCK:
        module._IN_FLIGHT.add(sid)
    assert client.post("/api/market-style/interpret", json={"snapshot_id": sid}).status_code == 409
    with module._LOCK:
        module._IN_FLIGHT.clear()
    monkeypatch.setattr(module.llm, "load_ark_config", lambda: None)
    assert client.post("/api/market-style/interpret", json={"snapshot_id": sid}).status_code == 503


def test_missing_and_nonfinite_values_remain_missing():
    def bad_upstream(url: str):
        if "breadth-history" in url:
            return {"history": [{"date": "2026-10-16", "breadth_20": float("nan"), "breadth_50": 30, "breadth_200": None}]}
        if "observations" in url:
            return {"items": [{"metric_id": "vix", "value": float("inf"), "observation_date": "2026-10-16"}]}
        return None
    data = build_evidence("us", 365, get_json=bad_upstream)
    assert data["cards"][1]["available"] is False
    assert data["cards"][2]["available"] is False
    assert data["cards"][3]["available"] is False
    assert "nan" not in str(data["cards"]).lower()
    assert "inf" not in str(data["cards"]).lower()


def test_risk_rejects_invalid_date_missing_quality_and_wrong_unit():
    for reading in (
        {"value": 18.5, "unit": "指数点", "observation_date": "not-a-date", "quality_status": "current"},
        {"value": 18.5, "unit": "指数点", "observation_date": "2026-10-16", "quality_status": "missing"},
        {"value": 18.5, "unit": "%", "observation_date": "2026-10-16", "quality_status": "current"},
    ):
        def upstream(url):
            if "observations" in url:
                return {"items": [{"metric_id": "vix", **reading}]}
            return None
        risk = build_evidence("us", 365, get_json=upstream)["cards"][2]
        assert risk["available"] is False
        assert "18.50" not in risk["fact"]


def test_deepseek_anthropic_transport_one_bounded_call(monkeypatch):
    sent = []
    class Response:
        status_code = 200
        def iter_content(self, chunk_size):
            yield json.dumps({"content": [{"type": "text", "text": '{"selected_ids":["breadth","risk","world_style"]}'}],
                              "stop_reason": "end_turn", "usage": {"input_tokens": 71, "output_tokens": 19}}).encode()
        def close(self):
            pass
    def post(url, **kwargs):
        sent.append((url, kwargs))
        return Response()
    monkeypatch.setattr(transport.requests, "post", post)
    config = module.llm.ArkConfig(api_key="test-only", base_url="https://api.deepseek.com", model="deepseek-v4-pro[1m]", style=module.llm.STYLE_ANTHROPIC, timeout=180, max_tokens=16000)
    result = transport.invoke_selection("facts", "select ids", config)
    assert result["text"] and result["usage"] == {"input_tokens": 71, "output_tokens": 19}
    assert len(sent) == 1
    url, kwargs = sent[0]
    assert url == "https://api.deepseek.com/v1/messages"
    assert kwargs["json"]["thinking"] == {"type": "disabled"}
    assert kwargs["json"]["max_tokens"] == 1024
    assert kwargs["json"]["model"] == "deepseek-v4-pro[1m]"
    assert kwargs["timeout"] == (5, 40) and kwargs["stream"] is True


def test_deepseek_openai_transport_and_http_failure(monkeypatch):
    calls = []
    class Response:
        def __init__(self, status):
            self.status_code = status
        def iter_content(self, chunk_size):
            yield json.dumps({"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                              "usage": {"prompt_tokens": 15, "completion_tokens": 2}}).encode()
        def close(self):
            pass
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response(200 if len(calls) == 1 else 429)
    monkeypatch.setattr(transport.requests, "post", post)
    config = module.llm.ArkConfig(api_key="test-only", base_url="https://api.deepseek.com", style=module.llm.STYLE_OPENAI)
    success = transport.invoke_selection("facts", "select ids", config)
    failure = transport.invoke_selection("facts", "select ids", config)
    assert success["usage"] == {"prompt_tokens": 15, "completion_tokens": 2}
    assert failure["error_code"] == "provider_http_429" and failure["text"] is None
    assert len(calls) == 2  # One request per explicit invocation, no hidden retry.
    assert calls[0][0] == "https://api.deepseek.com/chat/completions"
    assert calls[0][1]["json"]["thinking"] == {"type": "disabled"}
