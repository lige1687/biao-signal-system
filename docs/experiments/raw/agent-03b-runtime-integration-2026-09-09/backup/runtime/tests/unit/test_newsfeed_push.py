"""消息面重大事件推送（宏观线）单元测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

from lei_signal.newsfeed import push as push_mod
from lei_signal.newsfeed.store import NewsStore


def _day(offset: int) -> str:
    return (datetime.now().astimezone() - timedelta(days=offset)).strftime("%Y-%m-%d")


def _seed(db, rows: list[tuple[str, str, int, str]]) -> None:
    """(dedupe, category, importance, direction) → 当日发布（published_at 可覆盖默认）。"""
    store = NewsStore(db)
    items = []
    for dedupe, cat, imp, dr in rows:
        items.append({
            "source": "eastmoney", "source_name": "东财", "url": None,
            "category": cat, "title": f"事件{dedupe}", "summary": None,
            "content": None, "published_at": f"{_day(0)}T10:00:00+08:00",
            "dedupe_key": dedupe,
        })
    store.insert_items(items)
    unscored = store.fetch_unscored()
    store.apply_scores([
        {"id": r["id"], "category": cat, "importance": imp, "direction": dr,
         "symbols": [], "note": f"note-{r['title']}"}
        for r, (_d, cat, imp, _dr) in zip(unscored, rows)
    ])
    store.close()


def _no_crisis(monkeypatch):
    monkeypatch.setattr(
        "lei_signal.market_context.crisis_events.get_crisis_states", lambda: None
    )


def test_push_only_macro_risk_and_importance(tmp_path, monkeypatch):
    _no_crisis(monkeypatch)
    db = tmp_path / "n.db"
    _seed(db, [
        ("m9", "macro", 9, "bearish"),     # 当日 ≥8 宏观 → 推
        ("r8", "risk", 8, "bullish"),      # 当日 ≥8 风险 → 推
        ("m7", "macro", 7, "neutral"),     # <8 → 不推
        ("i9", "industry", 9, "bullish"),  # 非宏观/风险 → 不推
    ])
    payloads = push_mod.build_push_payloads(db)
    assert len(payloads) == 1
    body = payloads[0].body_md
    assert "事件m9" in body and "事件r8" in body
    assert "事件m7" not in body and "事件i9" not in body
    assert payloads[0].title.startswith("📰 消息面")


def test_push_impact_window_three_days(tmp_path, monkeypatch):
    """≥9 分事件 3 日内持续出现（窗口），>3 日消失；<9 分不进窗口。"""
    _no_crisis(monkeypatch)
    db = tmp_path / "n.db"
    store = NewsStore(db)
    # 手工构造不同发布日
    for dedupe, days_ago, imp in (("w1", 1, 9), ("w2", 2, 9), ("w3", 3, 9), ("w4", 4, 9), ("w5", 1, 8)):
        store.insert_items([{
            "source": "eastmoney", "source_name": "东财", "url": None,
            "category": "macro", "title": f"窗口{dedupe}", "summary": None,
            "content": None,
            "published_at": f"{_day(days_ago)}T10:00:00+08:00",
            "dedupe_key": dedupe,
        }])
    ids = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": i, "category": "macro", "importance": 9 if k != "窗口w5" else 8,
         "direction": "neutral", "symbols": [], "note": ""}
        for k, i in ids.items()
    ])
    store.close()
    payloads = push_mod.build_push_payloads(db)
    assert len(payloads) == 1
    body = payloads[0].body_md
    assert "窗口w1" in body and "窗口w2" in body   # 1-2 日前在窗口
    assert "窗口w3" not in body                    # 3 日前 = 超出（< n 严格）
    assert "窗口w4" not in body                    # 4 日前超出
    assert "窗口w5" not in body                    # 8 分不进窗口
    assert "影响窗口" in body


def test_push_crisis_alert_first(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lei_signal.market_context.crisis_events.get_crisis_states",
        lambda: {"readings": [], "alerts": [{
            "level": "danger", "type": "crash_warning", "title": "V4 刚崩警示 · 上证指数",
            "symbol": "000001.SS", "desc": "回避窗口20日",
        }]},
    )
    db = tmp_path / "n.db"
    _seed(db, [("m9", "macro", 9, "bearish")])
    payloads = push_mod.build_push_payloads(db)
    assert len(payloads) == 2
    assert payloads[0].title.startswith("⚠ V4")
    assert "不构成买卖建议" in payloads[0].body_md


def test_push_empty_when_nothing_major(tmp_path, monkeypatch):
    _no_crisis(monkeypatch)
    db = tmp_path / "n.db"
    _seed(db, [("m5", "macro", 5, "neutral")])
    assert push_mod.build_push_payloads(db) == []


def test_push_daily_brief_pytest_skip(tmp_path, monkeypatch):
    """pytest 环境默认不投递（dry_run 可用）——防止单测发网络。"""
    _no_crisis(monkeypatch)
    db = tmp_path / "n.db"
    _seed(db, [("m9", "macro", 9, "bearish")])
    assert push_mod.push_daily_brief(db) == 0
    sent = push_mod.push_daily_brief(db, dry_run=True)
    assert sent >= 1  # dry_run 走 MacNotifier dry-run
