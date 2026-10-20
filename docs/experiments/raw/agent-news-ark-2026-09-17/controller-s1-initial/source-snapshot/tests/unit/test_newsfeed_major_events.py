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


def test_major_events_brief_per_category_cap(tmp_path):
    """同类刷屏限额：宏观塞满 9 条时，每类最多 4 条，产业大事不被挤出。"""
    store = NewsStore(tmp_path / "cap.db")
    today = datetime.now().astimezone()
    rows, scores = [], []
    for i in range(9):  # 9 条 8 分宏观（模拟非农刷屏）
        rows.append({"source": "gnews", "source_name": "g", "url": None,
                     "category": "macro", "title": f"宏观刷屏{i}",
                     "summary": "", "content": None,
                     "published_at": today.isoformat(timespec="seconds"),
                     "dedupe_key": f"macro-{i}"})
        scores.append({"id": i + 1, "category": "macro", "importance": 8,
                       "direction": "neutral", "symbols": [], "note": "n"})
    rows.append({"source": "gnews", "source_name": "g", "url": None,
                 "category": "industry", "title": "英伟达资本开支上修",
                 "summary": "", "content": None,
                 "published_at": today.isoformat(timespec="seconds"),
                 "dedupe_key": "ind-1"})
    scores.append({"id": 10, "category": "industry", "importance": 7,
                   "direction": "bullish", "symbols": [], "note": "n"})
    store.insert_items(rows)
    store.apply_scores(scores)
    store.close()
    brief = NewsfeedService(db_path=str(tmp_path / "cap.db")).major_events_brief()
    cats = [i["category"] for i in brief["items"]]
    assert cats.count("macro") == 4  # 9 条压到 4 条
    assert "industry" in cats        # 产业大事保住位置
    assert "英伟达资本开支上修" in [i["title"] for i in brief["items"]]


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


# ---------------- 资料状态与官方事件材料（2026-09-17 S1） ----------------


def _seed_fed_statement(db, *, scored: bool) -> None:
    """模拟 sources/fed.py 采集的官方声明行（9-16 14:00 EDT = 9-17 02:00+08）。"""
    store = NewsStore(db)
    store.insert_items([{
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        "category": "macro", "title": "Federal Reserve issues FOMC statement",
        "summary": "The Committee decided to raise the target range.",
        "content": None,
        "published_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ingested_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dedupe_key": f"fed-stmt-{scored}",
    }])
    if scored:
        ids = [r["id"] for r in store.fetch_unscored()]
        store.apply_scores([
            {"id": i, "category": "macro", "importance": 9,
             "direction": "bearish", "symbols": [], "note": "模型点评"} for i in ids
        ])
    store.close()


def test_major_events_brief_carries_health(tmp_path):
    """空条目与「资料过期/失败」不再混为一句没有消息：health 始终随简报返回。"""
    db = tmp_path / "nf.db"
    _seed(db)
    brief = NewsfeedService(db_path=str(db)).major_events_brief(days=3)
    assert "health" in brief
    # 种子只有条目、无任务记录 → 状态未知而非假装正常
    assert brief["health"]["availability"] == "unknown"
    assert brief["health"]["latest_item_at"] is not None


def test_major_events_empty_db_health_unknown(tmp_path):
    brief = NewsfeedService(db_path=str(tmp_path / "empty.db")).major_events_brief()
    assert brief["available"] is False
    assert brief["health"]["availability"] == "never"


def test_unscored_official_statement_displayable(tmp_path):
    """正式声明无 AI 评分仍可展示：原文链接/阶段/带时区时间保留，不凭空赋分。"""
    db = tmp_path / "fed.db"
    _seed_fed_statement(db, scored=False)
    brief = NewsfeedService(db_path=str(db)).major_events_brief(days=3)
    assert brief["available"] is True
    fed = [i for i in brief["items"] if i["title"] == "Federal Reserve issues FOMC statement"]
    assert len(fed) == 1
    item = fed[0]
    assert item["importance"] is None
    assert item["direction_cn"] is None  # 未知不填为「中性事实」
    assert item["score_state_cn"] == "尚未评分"
    assert item["event"]["event_stage"] == "official_result"
    assert item["event"]["source_url"].endswith("monetary20260916a.htm")
    assert item["event"]["event_at"] == item["published_at"]
    assert "note" not in item and "llm_note" not in item and "summary" not in item


def test_scored_items_carry_event_reference(tmp_path):
    """已评分条目带事件参考：模型标签与事实分开（model_annotation）。"""
    db = tmp_path / "nf.db"
    _seed(db)
    brief = NewsfeedService(db_path=str(db)).major_events_brief(days=3)
    by_title = {i["title"]: i for i in brief["items"]}
    ev = by_title["美联储议息落地"]["event"]
    assert ev["event_stage"] in ("expectation", "commentary", "unknown")
    assert ev["model_annotation"]["scored"] is True
    assert ev["model_annotation"]["importance"] == 7


def test_same_official_url_deduped_scored_preferred(tmp_path):
    """同一官方公告 URL 的已评分+未评分两行：只显示一条，优先已评分。"""
    db = tmp_path / "dup.db"
    store = NewsStore(db)
    row = {
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        "category": "macro", "title": "Federal Reserve issues FOMC statement",
        "summary": "stmt", "content": None,
        "published_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dedupe_key": "dup-scored",
    }
    store.insert_items([row, {**row, "dedupe_key": "dup-unscored"}])
    ids = sorted(r["id"] for r in store.fetch_unscored())
    store.apply_scores([
        {"id": ids[0], "category": "macro", "importance": 9,
         "direction": "bearish", "symbols": [], "note": "n"},
    ])
    store.close()
    brief = NewsfeedService(db_path=str(db)).major_events_brief(days=3)
    fed = [i for i in brief["items"] if "FOMC statement" in i["title"]]
    assert len(fed) == 1
    assert fed[0]["importance"] == 9  # 已评分优先


def test_ops_block_passthrough_health_and_event():
    """ops DTO 透传 health 与事件阶段（旧输入无这些键仍兼容）。"""
    block = _build_major_events_block({
        "available": True,
        "items": [{
            "title": "Federal Reserve issues FOMC statement", "category_cn": "宏观",
            "direction_cn": "", "importance": 0, "when_cn": "今日",
            "published_at": _now_iso(), "score_state_cn": "尚未评分",
            "event": {"event_stage": "official_result",
                      "source_url": "https://www.federalreserve.gov/x.htm",
                      "event_at": _now_iso()},
        }],
        "health": {"availability": "fresh"},
    })
    assert block is not None
    assert block.health["availability"] == "fresh"
    assert block.items[0].event_stage == "official_result"
    assert block.items[0].score_state_cn == "尚未评分"
    old = _build_major_events_block({"available": True, "items": [{
        "title": "t", "category_cn": "宏观", "direction_cn": "利空",
        "importance": 8, "when_cn": "今日", "published_at": _now_iso(),
    }]})
    assert old is not None and old.health is None and old.items[0].event_stage is None
