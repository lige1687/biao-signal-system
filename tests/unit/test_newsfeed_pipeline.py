"""管线编排单元测试：mock 各源，验证粗筛/幂等/降级/LLM 步骤。"""
from __future__ import annotations

from lei_signal.newsfeed import pipeline
from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.pipeline import run_pipeline

_CFG = {
    "bili_ups": [{"mid": 1, "name": "测试UP"}],
    "rss_feeds": [],
    "gnews_queries": ["q1"],
    "symbols": ["NVDA"],
    "flash_keywords": {
        "macro": ["央行"],
        "risk": ["危机"],
        "policy": ["国务院"],
        "industry": ["财报"],
    },
    "lookback_days": 30,
}


def _em_items() -> list[NewsItem]:
    return [
        NewsItem(source="eastmoney", title="央行降准", summary="央行宣布降准",
                 published_at="2026-08-27T10:00:00+08:00",
                 dedupe_key="em1"),
        NewsItem(source="eastmoney", title="公司更换审计机构", summary="无关键词噪音",
                 published_at="2026-08-27T11:00:00+08:00",
                 dedupe_key="em2"),
    ]


def _patch_sources(monkeypatch, *, em=_em_items(), sina=None, gnews=None, bili=None):
    monkeypatch.setattr(pipeline, "collect_eastmoney",
                        lambda since: (list(em), "1000"))
    monkeypatch.setattr(pipeline, "collect_sina",
                        lambda since: (list(sina or []), None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: (list(gnews or []), None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda client, mid, name, since, lookback_iso=None: (
                            list(bili or []), None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())


def test_pipeline_filters_flash_noise_and_scores(monkeypatch, tmp_path):
    _patch_sources(monkeypatch)
    scored_calls = []

    def fake_score(rows, config=None):
        scored_calls.append(rows)
        return [
            {"id": r["id"], "category": "macro", "importance": 7,
             "direction": "bullish", "symbols": [], "note": "n"}
            for r in rows
        ]

    monkeypatch.setattr(pipeline, "score_items", fake_score)
    monkeypatch.setattr(pipeline, "generate_digest", lambda rows, config=None: None)

    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["status"] == "ok"
    # 噪音被粗筛丢弃
    assert result["per_source"]["eastmoney"] == 1
    assert result["scored"] == 1
    assert scored_calls and scored_calls[0][0]["title"] == "央行降准"

    # 二跑幂等：水位推进 + dedupe，不再入库
    result2 = run_pipeline(db, config=_CFG, no_llm=True)
    assert result2["inserted"] == 0


def test_pipeline_partial_when_one_source_fails(monkeypatch, tmp_path):
    def boom(since):
        raise pipeline.NewsSourceError("风控")

    monkeypatch.setattr(pipeline, "collect_eastmoney", boom)
    monkeypatch.setattr(pipeline, "collect_sina", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: ([], None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda c, mid, name, since, lookback_iso=None: ([], None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())

    result = run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=True)
    assert result["status"] == "partial"
    assert result["errors"] == [{"source": "eastmoney", "error": "风控"}]


def test_pipeline_no_llm_skips_scoring(monkeypatch, tmp_path):
    _patch_sources(monkeypatch)
    called = {"score": False, "digest": False}
    monkeypatch.setattr(pipeline, "score_items",
                        lambda *a, **k: called.__setitem__("score", True) or [])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda *a, **k: called.__setitem__("digest", True) or None)
    run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=True)
    assert not called["score"] and not called["digest"]


def test_pipeline_saves_digest(monkeypatch, tmp_path):
    _patch_sources(monkeypatch)
    monkeypatch.setattr(pipeline, "score_items",
                        lambda rows, config=None: [
                            {"id": r["id"], "category": "macro", "importance": 7,
                             "direction": "neutral", "symbols": [], "note": "n"}
                            for r in rows])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda rows, config=None: {"sections": [], "top_events": []})
    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["digest"] is True
    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(db)
    assert len(store.digests()) == 1
    store.close()
