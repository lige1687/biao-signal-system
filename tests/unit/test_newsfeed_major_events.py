"""重大事件简报（Agent 参考层）单元测试。

口径（2026-09-05 用户拍板）：
- 类别 = macro/risk/industry/policy（含英伟达/谷歌资本开支类产业大事）；
- 客观字段 only：标题/类别/方向/分数/时间——llm_note 主观小结不进 Agent；
- 博主观点（blogger 类）不进；
- importance ≥ 7 门槛。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from lei_signal.copilot.ops import _build_major_events_block
from lei_signal.newsfeed.service import NewsfeedService
from lei_signal.newsfeed.store import NewsStore
from lei_signal.plans.llm_context import _major_events_block


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _seed(db) -> None:
    store = NewsStore(db)
    today = datetime.now().astimezone()
    rows = [
        # 产业大事（用户点名级别）：今日 8 分，应进且标「今日」
        {"source": "gnews", "source_name": "gnews", "url": None,
         "category": "industry", "title": "Nvidia forecasts 70% revenue jump",
         "summary": "", "content": None,
         "published_at": today.isoformat(timespec="seconds"), "dedupe_key": "m1"},
        # 宏观 7 分、2 天前：进，标「2天前」
        {"source": "gnews", "source_name": "gnews", "url": None,
         "category": "macro", "title": "美联储议息落地",
         "summary": "", "content": None,
         "published_at": (today - timedelta(days=2)).isoformat(timespec="seconds"),
         "dedupe_key": "m2"},
        # 博主观点 9 分：blogger 类不进（主观信息红线）
        {"source": "bilibili", "source_name": "趋势天哥", "url": None,
         "category": "blogger", "title": "博主喊单英伟达",
         "summary": "", "content": None,
         "published_at": today.isoformat(timespec="seconds"), "dedupe_key": "m3"},
        # 产业 6 分：低于门槛不进
        {"source": "gnews", "source_name": "gnews", "url": None,
         "category": "industry", "title": "某小厂订单新闻",
         "summary": "", "content": None,
         "published_at": today.isoformat(timespec="seconds"), "dedupe_key": "m4"},
    ]
    store.insert_items(rows)
    store.apply_scores([
        {"id": 1, "category": "industry", "importance": 8,
         "direction": "bullish", "symbols": [], "note": "AI主观小结不该外泄"},
        {"id": 2, "category": "macro", "importance": 7,
         "direction": "neutral", "symbols": [], "note": "宏观备注"},
        {"id": 3, "category": "blogger", "importance": 9,
         "direction": "bullish", "symbols": [], "note": "博主立场"},
        {"id": 4, "category": "industry", "importance": 6,
         "direction": "neutral", "symbols": [], "note": "小事件"},
    ])
    store.close()


def test_major_events_brief_filters_and_fields(tmp_path):
    db = tmp_path / "nf.db"
    _seed(db)
    brief = NewsfeedService(db_path=str(db)).major_events_brief(days=3)

    assert brief["available"] is True
    titles = [i["title"] for i in brief["items"]]
    assert "Nvidia forecasts 70% revenue jump" in titles
    assert "美联储议息落地" in titles
    # blogger 类（主观）与低分产业不进
    assert "博主喊单英伟达" not in titles
    assert "某小厂订单新闻" not in titles
    # 客观字段 only：llm_note / summary / note 不外泄
    for it in brief["items"]:
        assert "note" not in it and "summary" not in it and "llm_note" not in it
    # 中文映射与时间标注
    by_title = {i["title"]: i for i in brief["items"]}
    assert by_title["Nvidia forecasts 70% revenue jump"]["when_cn"] == "今日"
    assert by_title["Nvidia forecasts 70% revenue jump"]["category_cn"] == "产业"
    assert by_title["美联储议息落地"]["when_cn"] == "2天前"
    assert "不参与技术判定" in brief["note_cn"]


def test_major_events_brief_empty(tmp_path):
    brief = NewsfeedService(db_path=str(tmp_path / "empty.db")).major_events_brief()
    assert brief["available"] is False
    assert brief["items"] == []


def test_ops_major_events_block_passthrough():
    # None（服务缺席）→ 区块整体缺省，页面不显示该段
    assert _build_major_events_block(None) is None
    block = _build_major_events_block({
        "available": True,
        "items": [{
            "title": "谷歌削减Gemini资本开支", "category_cn": "产业",
            "direction_cn": "利空", "importance": 8, "when_cn": "今日",
            "published_at": _now_iso(),
        }],
    })
    assert block is not None and block.available
    assert block.items[0].importance == 8
    assert block.items[0].direction_cn == "利空"


def test_discussion_context_major_events_block():
    # 服务缺席/无数据 → None 不硬凑；有数据 → 客观字段
    assert _major_events_block(None) is None
    assert _major_events_block({"available": False, "items": []}) is None
    out = _major_events_block({
        "available": True,
        "items": [{"title": "英伟达资本开支上修", "category_cn": "产业",
                   "direction_cn": "利多", "importance": 8, "when_cn": "今日"}],
    })
    assert out is not None
    assert out["items"][0]["title"] == "英伟达资本开支上修"
    assert "不参与技术判定" in out["note_cn"]
