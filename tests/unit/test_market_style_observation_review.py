"""The five-question review cannot omit a question or manufacture missing history."""
from datetime import date, timedelta
import json
import math
import statistics

from fastapi.testclient import TestClient
import pytest

from lei_signal.market_style_observation import app as module
from lei_signal.market_style_observation.conditions import market_volatility
from lei_signal.market_style_observation.review import build_review
from lei_signal.market_style_observation.review import question_cards
from lei_signal.market_style_observation.portfolio_review import summarize_portfolio


def _prices(count=65):
    prices = [100.0]
    returns = [0.01 if i % 2 else -0.005 for i in range(count - 1)]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    return {"series": {"sse": {"dates": dates, "values": prices}}}, returns


def test_realized_volatility_units_and_required_prices():
    data, returns = _prices()
    result = market_volatility(data, "cn")
    assert result["latest20"] == pytest.approx(statistics.stdev(returns[-20:]) * math.sqrt(252) * 100)
    assert result["latest60"] == pytest.approx(statistics.stdev(returns[-60:]) * math.sqrt(252) * 100)
    assert result["rv20"][:20] == [None] * 20
    assert result["rv60"][:60] == [None] * 60
    short, _ = _prices(21)
    assert market_volatility(short, "cn")["latest60"] is None
    short, _ = _prices(20)
    assert market_volatility(short, "cn")["available"] is False


def test_missing_prices_are_not_zero_filled_and_duplicate_dates_fail():
    data, _ = _prices()
    data["series"]["sse"]["values"][-2] = None
    result = market_volatility(data, "cn")
    assert result["available"] is False
    assert result["latest20"] is None and result["latest60"] is None
    json.dumps(result, allow_nan=False)
    data, _ = _prices()
    data["series"]["sse"]["dates"][-1] = data["series"]["sse"]["dates"][-2]
    assert market_volatility(data, "cn")["available"] is False


def test_five_answers_retain_unknowns_and_unique_sources():
    result = build_review("cn", get_json=lambda url: None)
    cards = result["questions"]
    assert [card["id"] for card in cards] == [f"q{i}" for i in range(1, 6)]
    assert result["completion"] == "partial"
    assert "当前离高点" in cards[0]["watch"]
    assert "收益贡献仍未回答" in cards[2]["watch"]
    assert "历史估值分位" in cards[3]["watch"]
    assert not cards[4]["available"]
    assert "不能回答" in cards[4]["fact"]
    assert "暂不能判断" in cards[4]["reading"]
    ids = [source["id"] for source in result["sources"]]
    assert len(ids) == len(set(ids))
    assert len(result["nfci"]["dates"]) == 5
    json.dumps(result, allow_nan=False)


def test_empty_account_structures_do_not_assert_common_risk():
    portfolio = summarize_portfolio({"markets": [{"id": "US", "accounts": [
        {"scheme": "mv", "history": {"series": []}},
        {"scheme": "rv", "history": {"series": []}},
    ]}]}, "us")
    assert portfolio["history"]["status"] == "no_common_valid_returns"
    q5 = question_cards(portfolio, "us")[4]
    assert not q5["available"]
    assert "不能回答" in q5["fact"]
    assert "暂不能判断" in q5["reading"]


def test_read_and_monthly_mode_are_passive_and_monthly_cannot_omit(monkeypatch):
    with module._LOCK:
        for store in (module._SNAPSHOTS, module._GENERATED, module._SNAPSHOT_TIMES,
                      module._QUERY_CACHE, module._REVIEW_CACHE):
            store.clear()
        module._MODEL_REQUESTS = 0
    monkeypatch.setattr(module, "get_history", lambda: {"available": False})
    monkeypatch.setattr(module, "build_review", lambda market, **kwargs: build_review(market, get_json=lambda url: None, **kwargs))
    calls = []
    def fake_selection(*args):
        calls.append(args)
        return {"text": '{"selected_ids":["q5","q1","q2","q3","q4"]}',
                "usage": None, "elapsed_ms": 1}
    monkeypatch.setattr(module, "invoke_selection", fake_selection)
    monkeypatch.setattr(module.llm, "load_ark_config", lambda: module.llm.ArkConfig(api_key="test-only", model="fake"))
    client = TestClient(module.app)
    assert client.get("/api/market-style/review?market=us").status_code == 200
    monthly = client.get("/api/market-style/snapshot?market=us&mode=monthly").json()
    assert monthly["review_mode"] == "monthly"
    assert len(monthly["cards"]) == 5
    assert not calls
    assert module._select_ids('{"selected_ids":["q1","q2","q3","q4"]}', monthly["cards"], require_all=True) is None
    assert module._select_ids('{"selected_ids":["q1","q2","q3","q4","q4"]}', monthly["cards"], require_all=True) is None
    body = {"snapshot_id": monthly["snapshot_id"]}
    answer = client.post("/api/market-style/interpret", json=body)
    assert answer.status_code == 200
    assert {card["id"] for card in answer.json()["cards"]} == {f"q{i}" for i in range(1, 6)}
    assert client.post("/api/market-style/interpret", json=body).json() == answer.json()
    assert len(calls) == 1
