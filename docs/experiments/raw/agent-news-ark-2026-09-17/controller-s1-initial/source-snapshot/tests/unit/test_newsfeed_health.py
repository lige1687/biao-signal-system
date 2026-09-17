"""资料健康状态纯函数测试（2026-09-17 S1，反例先行）。

期望值全部来自独立常识推演（手算时间差/状态语义），不用待测函数生成。
覆盖计划 §4 Task 1 固定反例：旧ok过期、正常零消息、部分源失败、评分失败、
no_llm、旧记录缺字段、中断运行、时间缺失/未来/无时区。
"""
from __future__ import annotations

from lei_signal.newsfeed.health import build_news_health


def _kw(**over):
    base = {
        "latest_run": None,
        "latest_success_at": None,
        "latest_item_at": None,
        "unscored_count": 0,
        "now": "2026-09-17T09:00:00+08:00",
        "max_age_hours": 26,
    }
    base.update(over)
    return base


# ---------------- 固定反例 1：旧 ok 而过期（计划原文钉住的用例） ----------------


def test_old_success_is_stale():
    health = build_news_health(
        latest_run={"finished_at": "2026-09-05T22:08:32+08:00", "status": "ok"},
        latest_success_at="2026-09-05T22:08:32+08:00",
        latest_item_at="2026-09-04T20:41:25+08:00", unscored_count=0,
        now="2026-09-17T09:00:00+08:00", max_age_hours=26)
    assert health["availability"] == "stale"
    assert health["latest_item_at"] == "2026-09-04T20:41:25+08:00"
    # 手算：9-05 22:08:32 → 9-17 09:00:00 = 11天10小时51分28秒 ≈ 274.9 小时
    assert health["age_hours"] == 274.9
    # 过期时不得让用户误以为「今日无重大消息」
    assert "今日无重大消息" not in health["note_cn"] or "不能" in health["note_cn"]
    assert health["last_checked_at"] == "2026-09-05T22:08:32+08:00"
    assert health["last_success_at"] == "2026-09-05T22:08:32+08:00"


# ---------------- 固定反例 2：今天所有源成功返回 0 条 → 正常无消息，不是停更 ----------------


def test_fresh_check_with_zero_items_is_fresh_not_stale():
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "ok",
            "stats": {
                "inserted": 0,
                "stages": {
                    "collect": {"status": "ok", "finished_at": "2026-09-17T08:29:50+08:00",
                                "errors": []},
                    "score": {"status": "ok", "finished_at": "2026-09-17T08:29:55+08:00",
                              "errors": []},
                    "digest": {"status": "skipped", "finished_at": None,
                               "errors": [], "reason": "no_items"},
                },
            },
            "errors": [],
        },
        latest_success_at="2026-09-17T08:29:50+08:00",
        latest_item_at=None,
    ))
    assert health["availability"] == "fresh"
    assert health["stages"]["collect"]["status"] == "ok"
    # 明确表达「本次检查无相关消息」，与「停更/过期」措辞分开
    assert "无相关消息" in health["note_cn"]
    assert "过期" not in health["note_cn"]


# --------- 固定反例 3：部分源正常、官方源失败 → 部分失败且保留该来源失败 ---------


def test_partial_run_keeps_failed_source_visible():
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "partial",
            "stats": {
                "stages": {
                    "collect": {"status": "partial", "finished_at": "2026-09-17T08:29:50+08:00",
                                "errors": [{"source": "fed", "error": "timeout"}]},
                },
            },
            "errors": [{"source": "fed", "error": "timeout"}],
        },
        latest_success_at="2026-09-16T20:30:00+08:00",
        latest_item_at="2026-09-16T21:00:00+08:00",
    ))
    assert health["availability"] == "partial"
    assert "fed" in health["note_cn"]
    assert health["stages"]["collect"]["errors"][0]["source"] == "fed"


# --------- 固定反例 4：采集成功、评分失败、简报未生成 → 条目保留且失败可见 ---------


def test_score_failure_visible_alongside_fresh_collect():
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "ok",
            "stats": {
                "inserted": 3,
                "stages": {
                    "collect": {"status": "ok", "finished_at": "2026-09-17T08:29:50+08:00",
                                "errors": []},
                    "score": {"status": "failed", "finished_at": "2026-09-17T08:29:59+08:00",
                              "errors": [{"stage": "score", "error": "批 1-3 两次失败"}]},
                    "digest": {"status": "skipped", "finished_at": None, "errors": [],
                               "reason": "no_items"},
                },
            },
            "errors": [],
        },
        latest_success_at="2026-09-17T08:29:50+08:00",
        latest_item_at="2026-09-17T08:20:00+08:00",
        unscored_count=3,
    ))
    # 采集新鲜与评分失败同时表达：单一字段不能承担所有状态
    assert health["availability"] == "fresh"
    assert health["stages"]["score"]["status"] == "failed"
    assert "评分" in health["note_cn"]
    assert health["unscored_count"] == 3


# --------- 固定反例 5：正常 no_llm → 评分/简报 skipped，不是 failed 也不是全 ok ---------


def test_no_llm_run_marks_scoring_skipped():
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "ok",
            "stats": {
                "inserted": 2,
                "stages": {
                    "collect": {"status": "ok", "finished_at": "2026-09-17T08:29:50+08:00",
                                "errors": []},
                    "score": {"status": "skipped", "finished_at": None, "errors": [],
                              "reason": "no_llm"},
                    "digest": {"status": "skipped", "finished_at": None, "errors": [],
                               "reason": "no_llm"},
                },
            },
            "errors": [],
        },
        latest_success_at="2026-09-17T08:29:50+08:00",
        latest_item_at="2026-09-17T08:10:00+08:00",
        unscored_count=2,
    ))
    assert health["availability"] == "fresh"
    assert health["stages"]["score"]["status"] == "skipped"
    assert health["stages"]["digest"]["status"] == "skipped"


# --------- 固定反例 6：旧 news_runs 没有阶段字段 → unknown，不追溯伪造成功 ---------


def test_legacy_run_without_stage_fields_is_unknown_not_fabricated():
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "ok",
            "stats": {"inserted": 7, "per_source": {"sina": 2}, "scored": 9,
                      "digest": True, "pushed": 0},
            "errors": [],
        },
        latest_success_at=None,  # 旧记录无明确采集成功字段，不回填
        latest_item_at="2026-09-17T08:00:00+08:00",
    ))
    assert health["availability"] == "fresh"  # 检查时间新鲜这一事实可用
    for stage in ("collect", "score", "digest"):
        assert health["stages"][stage]["status"] == "unknown"
    assert health["last_success_at"] is None


# --------- 固定反例 8：运行中断（running 遗留）→ 中断可见，不是永久健康 ---------


def test_stuck_running_is_not_healthy():
    health = build_news_health(**_kw(
        latest_run={
            "started_at": "2026-09-05T20:30:00+08:00", "finished_at": None,
            "status": "running", "stats": {}, "errors": [],
        },
        latest_success_at="2026-09-04T20:30:00+08:00",
        latest_item_at="2026-09-04T20:41:25+08:00",
    ))
    assert health["availability"] != "fresh"
    assert "中断" in health["note_cn"] or "未完成" in health["note_cn"]


def test_recent_running_is_unknown_not_failed_or_fresh():
    health = build_news_health(**_kw(
        latest_run={
            "started_at": "2026-09-17T08:55:00+08:00", "finished_at": None,
            "status": "running", "stats": {}, "errors": [],
        },
        latest_item_at="2026-09-16T21:00:00+08:00",
    ))
    assert health["availability"] == "unknown"
    assert health["last_checked_at"] == "2026-09-17T08:55:00+08:00"


# ---------------- 时间合法性：缺失 / 未来 / 无时区 / 坏串 分别 unknown ----------------


def test_naive_timestamp_is_unknown():
    health = build_news_health(**_kw(
        latest_run={"finished_at": "2026-09-17 08:30:00", "status": "ok"},
    ))
    assert health["availability"] == "unknown"
    assert health["age_hours"] is None


def test_future_timestamp_is_unknown():
    health = build_news_health(**_kw(
        latest_run={"finished_at": "2026-09-18T10:00:00+08:00", "status": "ok"},
    ))
    assert health["availability"] == "unknown"
    assert health["age_hours"] is None


def test_garbage_timestamp_is_unknown():
    health = build_news_health(**_kw(
        latest_run={"finished_at": "not-a-time", "status": "ok"},
    ))
    assert health["availability"] == "unknown"


def test_missing_run_time_is_unknown():
    health = build_news_health(**_kw(
        latest_run={"status": "ok"},
        latest_item_at="2026-09-16T21:00:00+08:00",
    ))
    assert health["availability"] == "unknown"
    assert health["last_checked_at"] is None


# ---------------- 其余边界：从未运行 / 全部源失败 ----------------


def test_never_ran():
    health = build_news_health(**_kw())
    assert health["availability"] == "never"
    assert health["last_checked_at"] is None


def test_recent_failed_run():
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "failed",
            "stats": {"stages": {"collect": {
                "status": "failed", "finished_at": "2026-09-17T08:29:50+08:00",
                "errors": [{"source": "sina", "error": "HTTP 503"}]}}},
            "errors": [{"source": "sina", "error": "HTTP 503"}],
        },
        latest_success_at="2026-09-16T20:30:00+08:00",
        latest_item_at="2026-09-16T21:00:00+08:00",
    ))
    assert health["availability"] == "failed"
    assert "sina" in health["note_cn"]
    # 失败时仍保留最后一次成功与最新条目时间，不抹掉历史
    assert health["last_success_at"] == "2026-09-16T20:30:00+08:00"
    assert health["latest_item_at"] == "2026-09-16T21:00:00+08:00"


def test_unscored_count_does_not_override_recorded_stages():
    """不从条目数推断成功：未评分数为 0 也不能把已记录的评分失败改写成 ok。"""
    health = build_news_health(**_kw(
        latest_run={
            "finished_at": "2026-09-17T08:30:00+08:00", "status": "ok",
            "stats": {"stages": {
                "score": {"status": "failed", "finished_at": "2026-09-17T08:29:59+08:00",
                          "errors": [{"stage": "score", "error": "HTTP 429"}]}}},
            "errors": [],
        },
        latest_item_at="2026-09-17T08:00:00+08:00",
        unscored_count=0,
    ))
    assert health["stages"]["score"]["status"] == "failed"
