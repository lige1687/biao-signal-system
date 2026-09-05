"""newsfeed 存储（迁移 016）单元测试。"""
from __future__ import annotations

import json

from lei_signal.newsfeed.store import NewsStore


def _item(dedupe: str, title: str = "标题", published_at: str = "2026-08-27T10:00:00+08:00",
          source: str = "eastmoney", category: str | None = "macro") -> dict:
    return {
        "source": source,
        "source_name": "东财快讯",
        "url": None,
        "category": category,
        "title": title,
        "summary": "摘要",
        "content": None,
        "published_at": published_at,
        "dedupe_key": dedupe,
    }


def test_insert_dedupe_and_counts(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    assert store.insert_items([_item("k1"), _item("k2")]) == 2
    # 重复 dedupe_key 幂等忽略
    assert store.insert_items([_item("k1")]) == 0
    assert store.counts() == {"total": 2, "scored": 0}
    store.close()


def test_scores_and_default_ordering(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([_item("k1", "高", "2026-08-27T10:00:00+08:00"),
                        _item("k2", "低", "2026-08-27T11:00:00+08:00"),
                        _item("k3", "未评分", "2026-08-27T12:00:00+08:00")])
    ids = [r["id"] for r in store.fetch_unscored()]
    assert len(ids) == 3
    # 给 k1 打 9 分，k2 打 3 分
    rows = {r["title"]: r["id"] for r in store.fetch_unscored()}
    assert store.apply_scores([
        {"id": rows["高"], "category": "macro", "importance": 9,
         "direction": "bullish", "symbols": ["NVDA"], "note": "重要"},
        {"id": rows["低"], "category": "macro", "importance": 3,
         "direction": "neutral", "symbols": [], "note": "常规"},
    ]) == 2
    # 已评分按 importance DESC 在前，未评分垫底
    ordered = store.query_items()
    assert [r["title"] for r in ordered[0]] == ["高", "低", "未评分"]
    assert ordered[1] == 3
    # scored 过滤
    only_scored, total = store.query_items(scored="scored")
    assert total == 2 and {r["title"] for r in only_scored} == {"高", "低"}
    only_un, total_u = store.query_items(scored="unscored")
    assert total_u == 1 and only_un[0]["title"] == "未评分"
    # symbols 序列化往返
    row = store.query_items(q="高")[0][0]
    assert json.loads(row["symbols"]) == ["NVDA"]
    store.close()


def test_query_filters_and_chinese_like(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([
        _item("k1", "央行开展逆回购", "2026-08-26T09:00:00+08:00", category="macro"),
        _item("k2", "英伟达发布财报", "2026-08-27T09:00:00+08:00", category="industry"),
        _item("k3", "旧闻", "2026-08-20T09:00:00+08:00", category="macro"),
    ])
    rows, total = store.query_items(q="英伟达")
    assert total == 1 and rows[0]["title"] == "英伟达发布财报"
    rows, total = store.query_items(category="macro", date_from="2026-08-26",
                                    date_to="2026-08-26")
    assert total == 1 and rows[0]["title"] == "央行开展逆回购"
    # min_importance 过滤（未评分=NULL 不命中）
    rows, total = store.query_items(min_importance=1)
    assert total == 0
    store.close()


def test_query_symbol_direction_and_symbols_like(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([
        _item("k1", "英伟达财报大超预期", "2026-08-27T09:00:00+08:00"),
        _item("k2", "降准落地", "2026-08-27T10:00:00+08:00"),
        _item("k3", "某公司公告提到 NVDA 供应链", "2026-08-27T11:00:00+08:00"),
    ])
    ids = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": ids["英伟达财报大超预期"], "category": "industry", "importance": 8,
         "direction": "bullish", "symbols": ["NVDA", "英伟达"], "note": ""},
        {"id": ids["降准落地"], "category": "macro", "importance": 7,
         "direction": "bullish", "symbols": [], "note": ""},
        {"id": ids["某公司公告提到 NVDA 供应链"], "category": "industry", "importance": 5,
         "direction": "bearish", "symbols": [], "note": ""},
    ])
    # symbol 过滤：symbols 数组命中 + 标题命中
    rows, total = store.query_items(symbol="NVDA")
    assert total == 2
    assert {r["title"] for r in rows} == {"英伟达财报大超预期", "某公司公告提到 NVDA 供应链"}
    rows, total = store.query_items(symbol="英伟达")
    assert total == 1 and rows[0]["title"] == "英伟达财报大超预期"
    # direction 过滤
    rows, total = store.query_items(direction="bearish")
    assert total == 1 and rows[0]["title"] == "某公司公告提到 NVDA 供应链"
    # 组合：NVDA 且利多
    rows, total = store.query_items(symbol="NVDA", direction="bullish")
    assert total == 1 and rows[0]["title"] == "英伟达财报大超预期"
    # 多词（逗号分隔，任一命中）：板块代码 + 展示名双匹配
    rows, total = store.query_items(symbol="TH881272.SECTOR,降准")
    assert total == 1 and rows[0]["title"] == "降准落地"
    # q 搜索现在覆盖 symbols 列（"NVDA" 只出现在 k3 的 symbols 之外场景由 title 命中，
    # 这里验证 q 命中 symbols JSON 文本本身）
    rows, total = store.query_items(q='"NVDA"')
    assert total == 1 and rows[0]["title"] == "英伟达财报大超预期"
    store.close()


def test_scored_recent(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([
        _item("k1", "近3天", "2026-08-27T09:00:00+08:00"),
        _item("k2", "更早", "2026-08-20T09:00:00+08:00"),
    ])
    ids = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": ids["近3天"], "category": "macro", "importance": 8,
         "direction": "bullish", "symbols": [], "note": ""},
        {"id": ids["更早"], "category": "macro", "importance": 8,
         "direction": "neutral", "symbols": [], "note": ""},
    ])
    rows = store.scored_recent("2026-08-25")
    assert [r["title"] for r in rows] == ["近3天"]
    store.close()


def test_mood_by_day(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([
        _item("k1", "多", "2026-08-27T09:00:00+08:00"),
        _item("k2", "空", "2026-08-27T10:00:00+08:00"),
        _item("k3", "早于窗口", "2026-08-10T10:00:00+08:00"),
    ])
    ids = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": ids["多"], "category": "macro", "importance": 8,
         "direction": "bullish", "symbols": [], "note": ""},
        {"id": ids["空"], "category": "macro", "importance": 7,
         "direction": "bearish", "symbols": [], "note": ""},
        {"id": ids["早于窗口"], "category": "macro", "importance": 7,
         "direction": "bullish", "symbols": [], "note": ""},
    ])
    rows = store.mood_by_day("2026-08-20")
    assert len(rows) == 1
    assert rows[0] == {"day": "2026-08-27", "bullish": 1, "bearish": 1, "neutral": 0}
    store.close()


def test_watermark_runs_digest_roundtrip(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    assert store.get_watermark("eastmoney") is None
    store.set_watermark("eastmoney", "1787829890000")
    assert store.get_watermark("eastmoney") == "1787829890000"
    store.set_watermark("eastmoney", "1787830000000")  # upsert
    assert store.get_watermark("eastmoney") == "1787830000000"

    run_id = store.start_run()
    assert store.latest_run()["status"] == "running"
    store.finish_run(run_id, "partial", {"inserted": 3}, [{"source": "sina", "error": "x"}])
    run = store.latest_run()
    assert run["status"] == "partial"
    assert json.loads(run["stats_json"]) == {"inserted": 3}
    assert json.loads(run["errors_json"]) == [{"source": "sina", "error": "x"}]

    store.save_digest("2026-08-27", {"sections": [], "top_events": []})
    store.save_digest("2026-08-27", {"sections": [{"category": "macro"}]})  # upsert
    ds = store.digests()
    assert len(ds) == 1 and json.loads(ds[0]["payload_json"])["sections"][0]["category"] == "macro"
    store.close()


def test_scored_rows_for_digest(tmp_path) -> None:
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([
        _item("k1", "a", "2026-08-27T10:00:00+08:00"),
        _item("k2", "b", "2026-08-26T10:00:00+08:00"),
    ])
    ids = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": ids["a"], "category": "macro", "importance": 5, "direction": "neutral",
         "symbols": [], "note": ""},
        {"id": ids["b"], "category": "macro", "importance": 8, "direction": "neutral",
         "symbols": [], "note": ""},
    ])
    rows = store.scored_rows_for_digest("2026-08-27")
    assert [r["title"] for r in rows] == ["a"]
    store.close()


def test_query_items_content_trim_and_include(tmp_path) -> None:
    """with_content=False（默认）裁掉 content 大字段；True 时带出。"""
    store = NewsStore(tmp_path / "n.db")
    store.insert_items([_item("k1", "带正文", "2026-08-27T09:00:00+08:00")])
    rows = store.query_items()[0]
    assert rows[0]["content"] is None  # 默认裁掉
    rows2 = store.query_items(include_content=True)[0]
    # _item 不写 content → NULL；换一条带 content 验证带出
    store.insert_items([{**_item("k2", "字幕条", "2026-08-27T10:00:00+08:00"),
                         "content": "字幕正文" * 100}])
    rows3 = store.query_items(include_content=True)[0]
    by_title = {r["title"]: r for r in rows3}
    assert len(by_title["字幕条"]["content"] or "") == 400
    assert all(r["content"] is None for r in store.query_items()[0])
    store.close()


def test_clear_old_content_keeps_recent(tmp_path) -> None:
    """content 保留队列：7 天前置 NULL，元数据保留；近期不动。"""
    from datetime import datetime, timedelta

    def _ts(days_ago: int) -> str:
        return (datetime.now().astimezone() - timedelta(days=days_ago)).isoformat(timespec="seconds")

    store = NewsStore(tmp_path / "n.db")
    store.insert_items([
        {**_item("old", "旧字幕", _ts(10)), "content": "x" * 100},
        {**_item("new", "新字幕", _ts(1)), "content": "y" * 100},
    ])
    assert store.clear_old_content(days=7) == 1
    rows = {r["title"]: r for r in store.query_items(include_content=True)[0]}
    assert rows["旧字幕"]["content"] is None and rows["旧字幕"]["title"] == "旧字幕"
    assert rows["新字幕"]["content"] == "y" * 100
    assert store.clear_old_content(days=7) == 0  # 幂等
    store.close()
