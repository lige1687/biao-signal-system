"""LLM 打分/简报单元测试：解析容错与降级。"""
from __future__ import annotations

from lei_signal.newsfeed import llm_score
from lei_signal.plans.llm import ArkConfig

_CFG = ArkConfig(api_key="test", base_url="http://localhost:1", model="m")


def test_parse_scores_plain() -> None:
    out = llm_score.parse_scores(
        '[{"id": 1, "category": "macro", "importance": 8, "direction": "bullish",'
        ' "symbols": ["NVDA"], "note": "美联储放鸽"}]'
    )
    assert out == [
        {"id": 1, "category": "macro", "importance": 8, "direction": "bullish",
         "symbols": ["NVDA"], "note": "美联储放鸽"}
    ]


def test_parse_scores_fenced_and_dirty() -> None:
    text = (
        "好的，以下是评分：\n```json\n"
        '[{"id": 2, "category": "risk", "importance": 99, "direction": "unknown",'
        ' "symbols": "bad", "note": "x"}]\n```\n以上。'
    )
    out = llm_score.parse_scores(text)
    assert len(out) == 1
    assert out[0]["importance"] == 10  # clamp
    assert out[0]["direction"] == "neutral"  # 白名单外降级
    assert out[0]["symbols"] == []  # 非数组 → 空
    assert out[0]["category"] == "risk"


def test_parse_scores_garbage_returns_empty() -> None:
    assert llm_score.parse_scores("模型胡言乱语没有数组") == []
    assert llm_score.parse_scores('{"id": 1}') == []


def test_parse_digest_structure() -> None:
    text = (
        '{"sections":[{"category":"macro","headline":"美联储放鸽","bullets":["降息25bp"]}],'
        '"top_events":[{"title":"英伟达财报","importance":9,"why":"指引超预期"}]}'
    )
    d = llm_score.parse_digest(text)
    assert d["sections"][0]["category"] == "macro"
    assert d["top_events"][0]["importance"] == 9


def test_parse_digest_bad_category_dropped() -> None:
    d = llm_score.parse_digest(
        '{"sections":[{"category":"foo","bullets":["x"]},{"category":"risk","bullets":["y"]}]}'
    )
    assert [s["category"] for s in d["sections"]] == ["risk"]


def test_score_items_filters_unknown_ids(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_score, "post_user_content",
        lambda *a, **k: '[{"id": 1, "category": "macro", "importance": 5,'
                        ' "direction": "neutral", "symbols": [], "note": "n"},'
                        '{"id": 99, "category": "macro", "importance": 5,'
                        ' "direction": "neutral", "symbols": [], "note": "n"}]',
    )
    rows = [{"id": 1, "title": "t", "summary": "s", "content": None}]
    out = llm_score.score_items(rows, _CFG)
    assert out is not None and [s["id"] for s in out] == [1]


def test_score_items_none_when_llm_fails(monkeypatch) -> None:
    monkeypatch.setattr(llm_score, "post_user_content", lambda *a, **k: None)
    assert llm_score.score_items([{"id": 1, "title": "t"}], _CFG) is None


def test_score_items_empty_rows_and_no_config(monkeypatch) -> None:
    assert llm_score.score_items([], _CFG) == []
    monkeypatch.setattr(llm_score, "load_ark_config", lambda: None)
    assert llm_score.score_items([{"id": 1, "title": "t"}]) is None


def test_generate_digest(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_score, "post_user_content",
        lambda *a, **k: '{"sections":[{"category":"macro","headline":"h","bullets":["b"]}],'
                        '"top_events":[]}',
    )
    d = llm_score.generate_digest([{"title": "t"}], _CFG)
    assert d is not None and d["sections"][0]["headline"] == "h"
    # 空输入 / LLM 失败 → None
    assert llm_score.generate_digest([], _CFG) is None
    monkeypatch.setattr(llm_score, "post_user_content", lambda *a, **k: None)
    assert llm_score.generate_digest([{"title": "t"}], _CFG) is None
