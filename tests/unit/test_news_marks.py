"""K 线消息标记（news_marks）单元测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

from lei_signal.api.news_marks import build_news_marks
from lei_signal.newsfeed.store import NewsStore


def _today(offset_days: int = 0) -> str:
    d = datetime.now().astimezone() - timedelta(days=offset_days)
    return d.isoformat(timespec="seconds")


def test_build_news_marks_aggregation(tmp_path) -> None:
    db = tmp_path / "m.db"
    day0 = _today(0)[:10]
    store = NewsStore(db)
    store.insert_items([
        {"source": "eastmoney", "source_name": "东财", "url": None,
         "category": "industry", "title": "利空大事件", "summary": None,
         "content": None, "published_at": _today(0), "dedupe_key": "n1"},
        {"source": "eastmoney", "source_name": "东财", "url": None,
         "category": "industry", "title": "小消息", "summary": None,
         "content": None, "published_at": _today(0), "dedupe_key": "n2"},
        {"source": "eastmoney", "source_name": "东财", "url": None,
         "category": "industry", "title": "同日另一条", "summary": None,
         "content": None, "published_at": _today(0), "dedupe_key": "n3"},
    ])
    rows = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": rows["利空大事件"], "category": "industry", "importance": 8,
         "direction": "bearish", "symbols": ["NVDA"], "note": ""},
        {"id": rows["小消息"], "category": "industry", "importance": 5,
         "direction": "bullish", "symbols": ["NVDA"], "note": ""},
        {"id": rows["同日另一条"], "category": "industry", "importance": 7,
         "direction": "bullish", "symbols": ["NVDA"], "note": ""},
    ])
    store.close()

    dates = [day0]
    marks = build_news_marks(db, symbol="NVDA", display_name=None, dates=dates)
    assert len(marks) == 1
    m = marks[0]
    assert m["date"] == day0
    assert m["count"] == 2  # 5 分条被门槛挡掉
    assert m["importance"] == 8 and m["direction"] == "bearish"  # 最高分定调
    assert m["titles"] == ["利空大事件", "同日另一条"]

    # dates 不含该日（非交易日/范围外）→ 不出标记
    assert build_news_marks(db, symbol="NVDA", display_name=None, dates=["2020-01-02"]) == []
    # 无关标的 → 空
    assert build_news_marks(db, symbol="AAPL", display_name=None, dates=dates) == []


def test_build_news_marks_board_double_match(tmp_path) -> None:
    db = tmp_path / "m2.db"
    day0 = _today(0)[:10]
    store = NewsStore(db)
    store.insert_items([
        {"source": "sina", "source_name": "新浪", "url": None,
         "category": "industry", "title": "通信设备板块大涨", "summary": None,
         "content": None, "published_at": _today(0), "dedupe_key": "b1"},
    ])
    rows = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": rows["通信设备板块大涨"], "category": "industry", "importance": 6,
         "direction": "bullish", "symbols": [], "note": ""},
    ])
    store.close()
    marks = build_news_marks(
        db, symbol="TH881272.SECTOR", display_name="通信设备", dates=[day0]
    )
    assert len(marks) == 1 and marks[0]["count"] == 1
