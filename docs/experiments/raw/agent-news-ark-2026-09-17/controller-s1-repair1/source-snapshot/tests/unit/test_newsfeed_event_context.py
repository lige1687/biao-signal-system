"""事件来源与阶段归一化测试（2026-09-17 S1，反例先行）。

固定已核事实：2026-09-16 14:00 EDT（美联储官方声明发布时间）对应北京时间
2026-09-17 02:00（+08:00）。9月4日的概率报道是「预期」，9月17日凌晨落库的
官方声明是「正式结果」，两者不混同、不凭日期相近伪造关联。
期望值全部来自独立常识推演，不用待测函数生成。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lei_signal.newsfeed.event_context import build_event_reference, dedupe_events

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "newsfeed" / "agent-news"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text("utf-8"))


# ---------------- 9月4日概率报道：预期阶段，时间与会议时间分开 ----------------


def test_expectation_item_stage_and_fields():
    item = _load("item-expectation-20260904.json")
    ref = build_event_reference(item)
    assert ref["event_stage"] == "expectation"
    assert ref["source"] == "sina"
    assert ref["source_name"] == "新浪7x24"
    assert ref["source_url"] is None  # 原条目 URL 为空，不伪造
    assert ref["published_at"] == "2026-09-04T20:41:25+08:00"
    assert ref["ingested_at"] == "2026-09-04T20:55:30+08:00"
    # 文章只提「9月」无确定会议日期：事件时间宁缺毋滥
    assert ref["event_at"] is None
    # 非官方来源：不给确定事件身份，不与后来正式结果合并
    assert ref["event_key"] is None
    assert ref["related_to"] is None
    # 模型标签（利空/8分）与事实分开放置
    assert ref["model_annotation"]["scored"] is True
    assert ref["model_annotation"]["direction"] == "bearish"
    assert ref["model_annotation"]["importance"] == 8


# ---------------- 9月16日官方声明：正式结果，无 AI 评分仍成立 ----------------


def test_official_statement_stage_unscored():
    item = _load("item-fed-statement-20260916.json")
    ref = build_event_reference(item)
    assert ref["event_stage"] == "official_result"
    assert ref["source"] == "fed"
    assert ref["source_url"] == (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm"
    )
    # 官方声明的发布时间即事件时间
    assert ref["event_at"] == "2026-09-17T02:00:00+08:00"
    # 确定事件身份（官方公告 URL）：可用于同一公告去重
    assert ref["event_key"] is not None
    assert "monetary20260916a" in ref["event_key"]
    # 无评分：不凭空赋重要度/利空，也不写成「中性事实」
    assert ref["model_annotation"]["scored"] is False
    assert ref["model_annotation"]["direction"] is None
    assert ref["model_annotation"]["importance"] is None


def test_beijing_cross_day_fact():
    """已核事实：2026-09-16 14:00 EDT = 2026-09-17 02:00 (+08:00)，跨北京时间日界。"""
    item = _load("item-fed-statement-20260916.json")
    ref = build_event_reference(item)
    dt = datetime.fromisoformat(ref["published_at"])
    assert dt == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    assert dt.astimezone(ZoneInfo("Asia/Shanghai")).isoformat() == "2026-09-17T02:00:00+08:00"
    assert dt.astimezone(ZoneInfo("America/New_York")).isoformat() == "2026-09-16T14:00:00-04:00"


# ---------------- 官方域名的讲话/纪要/日历不自动算新利率决议 ----------------


def test_official_domain_speech_is_commentary_not_decision():
    item = {
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/speech/powell20260910a.htm",
        "title": "Speech by Chair Powell on the economic outlook",
        "summary": "Chair Jerome H. Powell delivered remarks.",
        "published_at": "2026-09-10T13:30:00-04:00",
        "ingested_at": "2026-09-11T08:30:00+08:00",
        "importance": None, "direction": None,
    }
    ref = build_event_reference(item)
    assert ref["event_stage"] == "commentary"
    assert ref["event_at"] is None  # 讲话不是新决议，不给决议时间


def test_official_domain_minutes_is_commentary_not_decision():
    item = {
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260826a.htm",
        "title": "Minutes of the Federal Open Market Committee, July 28-29, 2026",
        "summary": None,
        "published_at": "2026-08-26T14:00:00-04:00",
        "ingested_at": "2026-08-27T08:30:00+08:00",
        "importance": None, "direction": None,
    }
    ref = build_event_reference(item)
    assert ref["event_stage"] == "commentary"


# ---------------- 非官方来源的「宣布加息」快讯：不能冒充正式结果 ----------------


def test_non_official_decision_flash_is_unknown_not_official_result():
    item = {
        "source": "sina", "source_name": "新浪7x24",
        "url": None,
        "title": "美联储宣布加息25个基点",
        "summary": "据快讯，美联储宣布加息25个基点。",
        "published_at": "2026-09-17T02:05:00+08:00",
        "ingested_at": "2026-09-17T02:06:00+08:00",
        "importance": 9, "direction": "bearish",
    }
    ref = build_event_reference(item)
    # 正式结果必须由可信官方来源支持；非官方快讯不给 official_result
    assert ref["event_stage"] == "unknown"
    assert ref["event_key"] is None
    assert ref["model_annotation"]["importance"] == 9  # 模型标签仍在，但与事实分开


# ---------------- 评论类与完全未知 ----------------


def test_blogger_item_is_commentary():
    item = {
        "source": "bilibili", "source_name": "趋势天哥",
        "url": "https://b23.tv/x",
        "category": "blogger",
        "title": "例行复盘：加息落地怎么看",
        "summary": "个人观点", "published_at": "2026-09-17T12:00:00+08:00",
        "ingested_at": "2026-09-17T12:05:00+08:00",
        "importance": 5, "direction": "neutral",
    }
    ref = build_event_reference(item)
    assert ref["event_stage"] == "commentary"


def test_plain_headline_is_unknown():
    item = {
        "source": "eastmoney", "source_name": "东财快讯",
        "url": "https://example.com/n/1",
        "title": "某公司发布三季度业绩预告",
        "summary": None, "published_at": "2026-09-17T10:00:00+08:00",
        "ingested_at": "2026-09-17T10:01:00+08:00",
        "importance": None, "direction": None,
    }
    ref = build_event_reference(item)
    assert ref["event_stage"] == "unknown"
    assert ref["event_at"] is None
    assert ref["relevance_cn"] is None


# ---------------- 时间缺失不冒充 ----------------


def test_missing_published_at_not_replaced_by_ingested():
    item = {
        "source": "sina", "source_name": "新浪7x24", "url": None,
        "title": "美联储9月加息25个基点的概率为50.6%",
        "summary": None,
        "published_at": None,
        "ingested_at": "2026-09-04T20:55:30+08:00",
        "importance": None, "direction": None,
    }
    ref = build_event_reference(item)
    assert ref["published_at"] is None  # 缺发布时间，不能用抓取时间冒充
    assert ref["ingested_at"] == "2026-09-04T20:55:30+08:00"
    assert ref["event_stage"] == "expectation"  # 阶段仍可由文本判定


# ---------------- 去重：同一官方公告合并；不跨会议、不与预期混同 ----------------


def test_dedupe_same_official_url_keeps_official_result():
    official = build_event_reference(_load("item-fed-statement-20260916.json"))
    rescraped = dict(official)
    rescraped["ingested_at"] = "2026-09-17T20:30:00+08:00"  # 同一公告再次采集
    out = dedupe_events([official, rescraped])
    assert len(out) == 1
    assert out[0]["event_stage"] == "official_result"


def test_no_merge_across_meetings_or_expectation():
    sept = build_event_reference(_load("item-fed-statement-20260916.json"))
    july = build_event_reference({
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm",
        "title": "Federal Reserve issues FOMC statement",
        "summary": None, "published_at": "2026-07-29T14:00:00-04:00",
        "ingested_at": "2026-07-30T08:30:00+08:00",
        "importance": None, "direction": None,
    })
    expectation = build_event_reference(_load("item-expectation-20260904.json"))
    out = dedupe_events([expectation, sept, july])
    # 三条都保留：两次会议是两个身份；预期无确定身份，不与任何正式结果合并
    assert len(out) == 3
    keys = [o["event_key"] for o in out]
    assert len({k for k in keys if k}) == 2


# ---------------- 主控复核 R2 返修反例（独立预期，与主控探针口径一致） ----------------


def test_speech_mentioning_fomc_statement_is_commentary():
    """标题含 "FOMC statement" 的讲话：先识别非决议内容，不得判成正式结果。"""
    item = {
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/speech/powell20260910a.htm",
        "title": "Speech by Powell on the FOMC statement",
        "summary": None,
        "published_at": "2026-09-10T13:30:00-04:00",
        "ingested_at": "2026-09-11T08:30:00+08:00",
        "importance": None, "direction": None,
    }
    ref = build_event_reference(item)
    assert ref["event_stage"] == "commentary"
    assert ref["event_at"] is None


def test_minutes_mentioning_fomc_statement_is_commentary():
    """标题含 "FOMC statement" 的纪要：不得判成正式结果。"""
    item = {
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260826a.htm",
        "title": "Minutes of the FOMC statement discussion",
        "summary": None,
        "published_at": "2026-08-26T14:00:00-04:00",
        "ingested_at": "2026-08-27T08:30:00+08:00",
        "importance": None, "direction": None,
    }
    ref = build_event_reference(item)
    assert ref["event_stage"] == "commentary"
    assert ref["event_at"] is None


def test_event_key_uses_full_path_not_filename():
    """同一文件名在不同路径：不是同一公告，不得合并（主控复核 R2）。"""
    a = build_event_reference({
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        "title": "Federal Reserve issues FOMC statement",
        "summary": None, "published_at": "2026-09-17T02:00:00+08:00",
        "ingested_at": "2026-09-17T08:30:00+08:00",
        "importance": None, "direction": None,
    })
    b = build_event_reference({
        "source": "fed", "source_name": "美联储官网",
        "url": "https://www.federalreserve.gov/archive/2025/monetary20260916a.htm",
        "title": "Federal Reserve issues FOMC statement",
        "summary": None, "published_at": "2025-09-18T02:00:00+08:00",
        "ingested_at": "2025-09-18T08:30:00+08:00",
        "importance": None, "direction": None,
    })
    assert a["event_key"] != b["event_key"]
    assert "federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm" in a["event_key"]
    out = dedupe_events([a, b])
    assert len(out) == 2  # 不同路径不合并
