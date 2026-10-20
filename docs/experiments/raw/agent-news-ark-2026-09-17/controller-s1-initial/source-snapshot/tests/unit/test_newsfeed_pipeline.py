"""管线编排单元测试：mock 各源，验证粗筛/幂等/降级/LLM 步骤。"""
from __future__ import annotations

from datetime import datetime

from lei_signal.newsfeed import pipeline
from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.pipeline import run_pipeline
from lei_signal.newsfeed.sources import NewsSourceError

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
    # 简报只收"当天"条目，日期必须动态生成，否则测试第二天起必挂
    t = datetime.now().astimezone().isoformat(timespec="seconds")
    return [
        NewsItem(source="eastmoney", title="央行降准", summary="央行宣布降准",
                 published_at=t, dedupe_key="em1"),
        NewsItem(source="eastmoney", title="公司更换审计机构", summary="无关键词噪音",
                 published_at=t, dedupe_key="em2"),
    ]


def _patch_sources(monkeypatch, *, em=None, sina=None, gnews=None, bili=None):
    em_items = _em_items() if em is None else em
    monkeypatch.setattr(pipeline, "collect_eastmoney",
                        lambda since: (list(em_items), "1000"))
    monkeypatch.setattr(pipeline, "collect_sina",
                        lambda since: (list(sina or []), None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: (list(gnews or []), None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda client, mid, name, since, lookback_iso=None, **kw: (
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
        raise NewsSourceError("风控")

    monkeypatch.setattr(pipeline, "collect_eastmoney", boom)
    monkeypatch.setattr(pipeline, "collect_sina", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: ([], None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda c, mid, name, since, lookback_iso=None, **kw: ([], None))
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
    _patch_sources(monkeypatch, bili=[NewsItem(
        source="bilibili", source_name="趋势天哥", url="https://b23.tv/z",
        category="blogger", title="天哥视频",
        summary=None, content=None,
        published_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        dedupe_key="bt1")])
    monkeypatch.setattr(pipeline, "score_items",
                        lambda rows, config=None: [
                            {"id": r["id"], "category": "blogger", "importance": 6,
                             "direction": "bearish", "symbols": [], "note": "偏空观点"}
                            for r in rows])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda rows, config=None: {"sections": [], "top_events": []})
    monkeypatch.setattr(pipeline, "generate_blogger_summaries",
                        lambda rows, config=None: [
                            {"name": "趋势天哥", "stance": "bearish", "summary": "偏空观望"}])
    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["digest"] is True
    import json

    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(db)
    d = store.digests()
    assert len(d) == 1
    payload = json.loads(d[0]["payload_json"])
    assert payload["bloggers"] == [{"name": "趋势天哥", "stance": "bearish", "summary": "偏空观望"}]
    store.close()


def test_pipeline_blogger_summary_failure_does_not_block_digest(monkeypatch, tmp_path):
    """博主小结 LLM 失败：简报照常保存（不带 bloggers 字段）。"""
    _patch_sources(monkeypatch)
    monkeypatch.setattr(pipeline, "score_items",
                        lambda rows, config=None: [
                            {"id": r["id"], "category": "macro", "importance": 7,
                             "direction": "neutral", "symbols": [], "note": "n"}
                            for r in rows])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda rows, config=None: {"sections": [], "top_events": []})
    monkeypatch.setattr(pipeline, "generate_blogger_summaries",
                        lambda rows, config=None: None)
    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["digest"] is True
    import json

    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(db)
    payload = json.loads(store.digests()[0]["payload_json"])
    assert "bloggers" not in payload
    store.close()


# ---------------- 阶段留痕与水位顺序（2026-09-17 S1） ----------------


def test_pipeline_records_stage_results_and_source_attempts(monkeypatch, tmp_path):
    """正常带评分运行：stages/sources 留痕齐全，旧计数字段兼容。"""
    _patch_sources(monkeypatch)
    monkeypatch.setattr(pipeline, "score_items",
                        lambda rows, config=None: [
                            {"id": r["id"], "category": "macro", "importance": 7,
                             "direction": "bullish", "symbols": [], "note": "n"}
                            for r in rows])
    monkeypatch.setattr(pipeline, "generate_digest", lambda rows, config=None: None)
    result = run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=False)
    assert result["status"] == "ok"
    stages = result["stages"]
    assert stages["collect"]["status"] == "ok"
    assert stages["collect"]["finished_at"]
    assert stages["score"]["status"] == "ok"
    # 简报生成失败（mock 返回 None）→ 明确 failed，不再静默
    assert stages["digest"]["status"] == "failed"
    # 每源尝试时间/成败留痕
    assert result["sources"]["eastmoney"]["ok"] is True
    assert result["sources"]["eastmoney"]["attempted_at"].startswith("20")
    # 旧计数字段保持
    assert result["inserted"] == 1 and result["scored"] == 1


def test_pipeline_no_llm_marks_score_digest_push_skipped(monkeypatch, tmp_path):
    """no_llm 正常运行：评分/简报/推送明确 skipped，不误写 failed 或全 ok。"""
    _patch_sources(monkeypatch)
    result = run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=True)
    assert result["status"] == "ok"
    assert result["stages"]["score"]["status"] == "skipped"
    assert result["stages"]["score"]["reason"] == "no_llm"
    assert result["stages"]["digest"]["status"] == "skipped"
    assert result["stages"]["push"]["status"] == "skipped"
    # 未评分条目保留（采集成功与未评分是两回事）
    assert result["scored"] == 0 and result["inserted"] == 1


def test_pipeline_score_failure_visible_items_kept(monkeypatch, tmp_path):
    """原文采集成功、评分失败（模拟 429）、简报未生成：条目保留且失败可追溯。"""
    _patch_sources(monkeypatch)
    monkeypatch.setattr(pipeline, "score_items", lambda rows, config=None: None)
    monkeypatch.setattr(pipeline, "generate_digest", lambda rows, config=None: None)
    result = run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=False)
    # 采集正常 → run.status 保持 ok（采集口径）；评分失败在 stages 可见
    assert result["status"] == "ok"
    assert result["scored"] == 0
    assert result["stages"]["score"]["status"] == "failed"
    assert result["stages"]["score"]["errors"]
    # 无已评分条目 → 简报 skipped（无数据），与失败分开
    assert result["stages"]["digest"]["status"] == "skipped"
    assert result["stages"]["digest"]["reason"] == "no_items"
    # 条目保留为未评分，原文仍可查
    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(tmp_path / "p.db")
    unscored = store.fetch_unscored()
    assert len(unscored) == 1 and unscored[0]["title"] == "央行降准"
    store.close()


def test_pipeline_partial_preserves_failed_source_attempt(monkeypatch, tmp_path):
    """部分源正常、官方源失败：总体 partial 且该来源失败留痕，不被其他源掩盖。"""
    _patch_sources(monkeypatch)

    def boom(*a, **k):
        raise NewsSourceError("fed timeout")

    monkeypatch.setattr(pipeline, "collect_fed_press", boom)
    cfg = dict(_CFG, fed_press={"enabled": True, "url": "https://example.test/fed.xml"})
    result = run_pipeline(tmp_path / "p.db", config=cfg, no_llm=True)
    assert result["status"] == "partial"
    assert result["stages"]["collect"]["status"] == "partial"
    assert result["sources"]["fed"]["ok"] is False
    assert "timeout" in result["sources"]["fed"]["error"]
    assert {"source": "fed", "error": "fed timeout"} in result["errors"]
    # 其他源成功不受牵连
    assert result["sources"]["eastmoney"]["ok"] is True


def test_pipeline_fed_items_are_macro_not_blogger(monkeypatch, tmp_path):
    """官方公告归 macro：不将官方声明分进博主。"""
    _patch_sources(monkeypatch)
    monkeypatch.setattr(
        pipeline, "collect_fed_press",
        lambda *, url, since_iso: ([NewsItem(
            source="fed", source_name="美联储官网",
            url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
            category="macro", title="Federal Reserve issues FOMC statement",
            summary="stmt", content=None,
            published_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            dedupe_key="fed1")], None),
    )
    cfg = dict(_CFG, fed_press={"enabled": True, "url": "https://example.test/fed.xml"})
    result = run_pipeline(tmp_path / "p.db", config=cfg, no_llm=True)
    assert result["per_source"]["fed"] == 1
    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(tmp_path / "p.db")
    rows = store.query_items(source="fed")[0]
    assert rows[0]["category"] == "macro"
    store.close()


def test_watermark_not_advanced_when_insert_fails(monkeypatch, tmp_path):
    """写库失败不提前推进水位；修复后重跑不重复插入（2026-09-17 S1 顺序修复）。"""
    monkeypatch.setattr(pipeline, "collect_sina",
                        lambda since: ([NewsItem(
                            source="sina", title="央行降准", summary="s",
                            published_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                            dedupe_key="s1")], "5062609"))
    # 东财同步失败：全部源失败 → failed（部分成功场景见 partial 用例）
    monkeypatch.setattr(pipeline, "collect_eastmoney",
                        lambda since: (_ for _ in ()).throw(NewsSourceError("em down")))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: ([], None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda c, mid, name, since, lookback_iso=None, **kw: ([], None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())

    from lei_signal.newsfeed.store import NewsStore

    original_insert = NewsStore.insert_items

    def boom_insert(self, items):
        raise RuntimeError("disk full")

    monkeypatch.setattr(NewsStore, "insert_items", boom_insert)
    db = tmp_path / "p.db"
    # 最小配置：只留快讯两源（gnews/bili/rss 不启用），全部失败才是 failed
    cfg = {**_CFG, "gnews_queries": [], "bili_ups": [], "rss_feeds": []}
    result1 = run_pipeline(db, config=cfg, no_llm=True)
    assert result1["status"] == "failed"  # 写库失败 + 东财失败 → 全部源失败
    store = NewsStore(db)
    assert store.get_watermark("sina") is None  # 水位未推进
    store.close()

    monkeypatch.setattr(NewsStore, "insert_items", original_insert)
    monkeypatch.setattr(pipeline, "collect_eastmoney", lambda since: ([], None))
    result2 = run_pipeline(db, config=cfg, no_llm=True)
    assert result2["status"] == "ok"
    assert result2["per_source"]["sina"] == 1
    store = NewsStore(db)
    assert store.get_watermark("sina") == "5062609"
    # 第三次重跑：水位 + dedupe，不重复插入
    store.close()
    result3 = run_pipeline(db, config=cfg, no_llm=True)
    assert result3["inserted"] == 0


def test_blogger_category_restricted_to_blogger_sources(monkeypatch, tmp_path):
    """gnews 的英文股评被 LLM 判成 blogger 时，回落预分类 industry。"""
    monkeypatch.setattr(
        pipeline, "collect_eastmoney", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_sina", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: ([], None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda c, mid, name, since, lookback_iso=None, **kw: ([], None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())
    monkeypatch.setattr(pipeline, "generate_digest", lambda rows, config=None: None)

    def fake_score(rows, config=None):
        out = []
        for r in rows:
            # 模拟 LLM：所有条目都判成 blogger
            out.append({"id": r["id"], "category": "blogger", "importance": 5,
                        "direction": "neutral", "symbols": [], "note": "n"})
        return out

    monkeypatch.setattr(pipeline, "score_items", fake_score)

    from lei_signal.newsfeed.store import NewsStore

    db = tmp_path / "cat.db"
    store = NewsStore(db)
    store.insert_items([
        {"source": "gnews", "source_name": "Reuters", "url": "http://x/1",
         "category": "industry", "title": "NVIDIA remains a buy", "summary": "opinion",
         "content": None, "published_at": "2026-08-27T10:00:00+08:00",
         "dedupe_key": "g1"},
        {"source": "bilibili", "source_name": "UP", "url": "http://x/2",
         "category": "blogger", "title": "例行更新", "summary": "s",
         "content": None, "published_at": "2026-08-27T11:00:00+08:00",
         "dedupe_key": "g2"},
    ])
    store.close()

    run_pipeline(db, config=_CFG, no_llm=False)
    store = NewsStore(db)
    cats = {r["title"]: r["category"] for r in store.query_items(limit=10)[0]}
    store.close()
    assert cats["NVIDIA remains a buy"] == "industry"  # 回落
    assert cats["例行更新"] == "blogger"  # 博主源保留
