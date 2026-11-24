"""Isolated evidence board checks; no live account, market or model access."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

from lei_signal.api import opportunity_evidence as evidence
from lei_signal.api.schemas import (
    BuyPointCandidateDTO,
    BuyPointReviewDTO,
    FactorDTO,
    RiskAlertDTO,
    TradabilityDTO,
)


def _request(tmp_path, *, entries=None, news=False):
    watch = tmp_path / "watch.db"
    with sqlite3.connect(watch) as conn:
        conn.execute(
            "CREATE TABLE watchlist_items (symbol TEXT,display_name TEXT,market TEXT,"
            "note TEXT,sort_order INTEGER,added_at TEXT,group_id INTEGER)"
        )
        conn.executemany(
            "INSERT INTO watchlist_items VALUES (?,?,?,?,?,?,?)",
            [
                ("512890.SS", "红利低波ETF", "cn_sh", None, 1, "2026-10-01", None),
                ("600519.SS", "贵州茅台", "cn_sh", None, 2, "2026-10-01", None),
                ("BK0457.SECTOR", "板块", "sector", None, 3, "2026-10-01", None),
            ],
        )
    news_path = tmp_path / "news.db"
    if news:
        with sqlite3.connect(news_path) as conn:
            conn.execute(
                "CREATE TABLE news_items (id INTEGER,title TEXT,source TEXT,source_name TEXT,"
                "url TEXT,published_at TEXT,symbols TEXT,direction TEXT)"
            )
    service = SimpleNamespace(_entries=entries or {})
    state = SimpleNamespace(
        watchlist_db_path=str(watch),
        analysis_service=service,
        newsfeed_service=SimpleNamespace(_db_path=str(news_path)) if news else None,
    )
    return SimpleNamespace(app=SimpleNamespace(state=state)), news_path


def _holding(**overrides):
    row = {
        "holding_id": "fund-A",
        "name": "真实基金A",
        "code": "001513",
        "symbol": None,
        "holding_as_of": "2026-10-14",
        "original_note": "",
        "nav": None,
        "disclosure": {},
        "industry_reference": {},
        "gaps": [],
        "plan": None,
        "alerts": [],
    }
    row.update(overrides)
    return row


def test_watchlist_filter_and_unmatched_fund_stays_unknown(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    monkeypatch.setattr(evidence, "build_workspace", lambda _request: {"items": [_holding()]})
    out = evidence.build_snapshot(request)
    assert [card["candidate_key"] for card in out["items"]] == [
        "holding:fund-A:buy",
        "holding:fund-A:sell",
        "symbol:512890.SS:buy",
        "symbol:512890.SS:sell",
    ]
    fund = out["items"][1]
    assert fund["status"] == "unknown" and not fund["agent_eligible"]
    assert any("原持仓计划" in text for text in fund["limitations"])
    assert fund["searches"][-1]["status"] == "unavailable"
    assert out["coverage"] == {
        "watchlist": 1,
        "holdings": 1,
        "review_candidates": 2,
        "unavailable": 4,
    }


def test_fund_disclosure_is_detailed_public_context_while_private_note_stays_private(
    tmp_path, monkeypatch
):
    request, _ = _request(tmp_path)
    disclosure = {
        "status": "available",
        "report_period": "2026Q2",
        "report_date": "2026-06-30",
        "published_at": "2026-08-31",
        "checked_at": "2026-10-12T12:00:00+08:00",
        "source_name": "基金公司",
        "official_report_url": "https://example.test/report",
        "coverage_pct": 12.5,
        "unknown_pct": 87.5,
        "industry_coverage_pct": 12.5,
        "industry_unknown_pct": 87.5,
        "source_recheck_required": True,
        "limitations": ["仅直接持股前十"],
        "holdings": [
            {
                "stock_code": "600000",
                "stock_name": "示例公司",
                "weight_pct": 12.5,
                "industry_label": "银行",
            }
        ],
    }
    holding = _holding(
        disclosure=disclosure,
        original_note="我的私人买入理由",
        industry_reference={
            "references": [
                {
                    "symbol": "515880.SS",
                    "name": "行业ETF",
                    "source_url": "https://example.test/sector",
                }
            ],
            "fundamentals": [
                {
                    "kind": "经理观点",
                    "summary": "行业仍需观察",
                    "published_at": "2026-08-31",
                    "source_url": "https://example.test/manager",
                }
            ],
        },
    )
    monkeypatch.setattr(evidence, "build_workspace", lambda _request: {"items": [holding]})
    cards = evidence.build_snapshot(request)["items"]
    for intent in ("buy", "sell"):
        card = next(c for c in cards if c["candidate_key"] == f"holding:fund-A:{intent}")
        public = [e for e in card["evidence"] if e["public"]]
        assert any("示例公司" in e["text"] and "12.5%" in e["text"] for e in public)
        assert any("未覆盖87.5%" in e["text"] for e in public)
        assert any(
            e["report_date"] == "2026-06-30" and e["published_at"] == "2026-08-31" for e in public
        )
        assert any("不能认定为最新披露" in text for text in card["limitations"])
    sell = next(c for c in cards if c["candidate_key"] == "holding:fund-A:sell")
    buy = next(c for c in cards if c["candidate_key"] == "holding:fund-A:buy")
    assert buy["subject"]["id"] == sell["subject"]["id"] == "fund-A"
    assert {
        e["id"]
        for e in buy["evidence"]
        if e["public"] and e["category"] in {"fundamentals", "industry", "news"}
    } == {
        e["id"]
        for e in sell["evidence"]
        if e["public"] and e["category"] in {"fundamentals", "industry", "news"}
    }
    assert not any("私人买入理由" in e["text"] for e in buy["evidence"])
    assert any("私人买入理由" in e["text"] and e["public"] is False for e in sell["evidence"])


def test_public_context_keeps_both_watchlist_directions_reviewable(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    monkeypatch.setattr(evidence, "build_workspace", lambda _request: {"items": []})
    monkeypatch.setattr(
        evidence.opportunity_context,
        "public_sources",
        lambda *_args, **_kwargs: [
            {
                "text": "产品投资范围",
                "source": "基金公司",
                "source_ref": "https://example.test/profile",
                "date": None,
                "published_at": None,
                "checked_at": "2026-10-15",
                "report_date": None,
                "category": "industry",
                "scope": "same_product",
                "public": True,
                "provenance": "product_profile",
                "limitations": ["最新成分未知"],
            }
        ],
    )
    cards = evidence.build_snapshot(request)["items"]
    assert len(cards) == 2
    assert all(c["agent_eligible"] for c in cards)
    assert all(any(e["provenance"] == "product_profile" for e in c["evidence"]) for c in cards)


def test_risk_search_receipt_and_unverified_lead_reach_both_directions(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    monkeypatch.setattr(evidence, "build_workspace", lambda _request: {"items": []})
    monkeypatch.setattr(
        evidence.opportunity_context,
        "cached_risk_news",
        lambda *_args: {
            "status": "checked",
            "detail": "风险方向标题检索完成",
            "query": '("红利低波ETF" OR "512890") (风险 OR risk) when:7d',
            "checked_at": "2026-10-15T12:00:00+08:00",
            "count": 1,
            "error": "",
            "leads": [
                {
                    "title": "红利低波ETF 风险标题",
                    "source_name": "Google News",
                    "source_url": "https://example.test/risk",
                    "published_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                }
            ],
        },
    )
    cards = evidence.build_snapshot(request)["items"]
    assert len(cards) == 2
    for card in cards:
        receipt = next(s for s in card["searches"] if s["name"] == "同产品风险方向标题检索")
        assert receipt["status"] == "checked" and receipt["count"] == 1
        assert receipt["checked_at"] and receipt["query"] and receipt["error"] == ""
        leads = [e for e in card["evidence"] if e["source_ref"] == "https://example.test/risk"]
        assert len(leads) == 1 and leads[0]["role"] == "lead"
        assert leads[0]["provenance"] == "unverified_news"
        assert "不代表已证实利空" in leads[0]["text"]


def test_same_title_and_url_from_two_lookups_is_one_news_lead(monkeypatch):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    lead = {
        "title": "红利低波ETF 风险标题",
        "source_name": "Google News",
        "source_url": "https://example.test/one-article",
        "published_at": now.isoformat(),
    }
    monkeypatch.setattr(evidence.opportunity_context, "public_sources", lambda *_args, **_kw: [])
    monkeypatch.setattr(
        evidence.opportunity_context,
        "cached_news",
        lambda *_args: {
            "status": "checked",
            "detail": "已查",
            "checked_on": now.date().isoformat(),
            "leads": [lead],
        },
    )
    monkeypatch.setattr(
        evidence.opportunity_context,
        "cached_risk_news",
        lambda *_args: {
            "status": "checked",
            "detail": "风险方向已查",
            "query": "同产品风险方向查询",
            "checked_at": now.isoformat(),
            "count": 1,
            "error": "",
            "leads": [lead],
        },
    )
    card = evidence._card(
        {"key": "symbol:512890.SS", "kind": "symbol", "id": "512890.SS", "name": "红利低波ETF"},
        "buy",
    )
    evidence._public_context(None, card, "512890.SS", "红利低波ETF", now)
    leads = [row for row in card["evidence"] if row["source_ref"] == lead["source_url"]]
    assert len(leads) == 1 and leads[0]["role"] == "lead"
    searches = [
        row
        for row in card["searches"]
        if "消息标题" in row["name"] or "风险方向" in row["name"]
    ]
    assert len(searches) == 2
    assert next(row for row in searches if "风险方向" in row["name"])["count"] == 1


def test_short_mirror_is_not_a_buy_or_a_time_failure():
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    short = SimpleNamespace(
        direction="short",
        state="confirmed",
        last_state_change_date=today.isoformat(),
        opened_date=today.isoformat(),
        module="D",
    )
    review = SimpleNamespace(candidates=[short], resonance_groups=[], degraded_cn=None)
    assert evidence._qualified_candidates(review, today.isoformat(), today) == ([], 0)


def test_only_short_mirror_does_not_create_buy_card(monkeypatch):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    subject = {
        "key": "symbol:512890.SS",
        "kind": "symbol",
        "id": "512890.SS",
        "name": "红利低波ETF",
    }
    assessment = SimpleNamespace(
        as_of=now.date().isoformat(),
        supports=[],
        conflicts=[],
        risks=[],
        stage_cn="上升",
        color_cn="绿",
        risk_state_cn="正常",
        dimensions={},
    )
    short = SimpleNamespace(
        direction="short",
        state="confirmed",
        last_state_change_date=now.date().isoformat(),
        opened_date=now.date().isoformat(),
        module="D",
        scenario_cn="做空镜像",
        satisfied_conditions=["做空镜像条件"],
        missing_conditions=[],
        caveat_cn="",
    )
    monkeypatch.setattr(evidence, "_technical", lambda *_: (object(), assessment, []))
    monkeypatch.setattr(evidence, "extract_sell_signals", lambda *_: [])
    monkeypatch.setattr(
        evidence,
        "build_review",
        lambda *_a, **_k: SimpleNamespace(
            candidates=[short],
            resonance_groups=[],
            degraded_cn=None,
            tradability=SimpleNamespace(tradable=True, blocking_reasons=[]),
            verdict="actionable",
        ),
    )
    card = evidence._buy_card(request, subject, now)
    assert card["status"] == "no_opportunity"
    assert not any("候选日期无效" in text for text in card["limitations"])
    assert not any("做空镜像条件" in e["text"] for e in card["evidence"])


def test_buy_candidate_method_caveat_is_unknown_and_source_is_chinese(monkeypatch):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    subject = {
        "key": "symbol:512890.SS",
        "kind": "symbol",
        "id": "512890.SS",
        "name": "红利低波ETF",
    }
    assessment = SimpleNamespace(
        as_of=now.date().isoformat(),
        supports=[],
        conflicts=[],
        risks=[],
        stage_cn="上升",
        color_cn="绿",
        risk_state_cn="正常",
        dimensions={},
    )
    monkeypatch.setattr(evidence, "_technical", lambda *_: (object(), assessment, []))
    monkeypatch.setattr(evidence, "extract_sell_signals", lambda *_: [])
    candidate = SimpleNamespace(
        direction="long",
        state="confirmed",
        last_state_change_date=now.date().isoformat(),
        opened_date=now.date().isoformat(),
        module="D",
        scenario_cn="回撤后的条件化做多",
        rule_id="internal_rule",
        scenario_id="internal_scenario",
        satisfied_conditions=["已有收盘条件"],
        missing_conditions=["仍待成交条件"],
        caveat_cn="这套判断方法尚有局限",
    )
    monkeypatch.setattr(
        evidence,
        "build_review",
        lambda *_a, **_k: SimpleNamespace(
            candidates=[candidate],
            resonance_groups=[],
            degraded_cn="部分候选方法已降级",
            tradability=SimpleNamespace(tradable=True, blocking_reasons=[]),
            verdict="actionable",
        ),
    )
    card = evidence._buy_card(request, subject, now)
    by_text = {row["text"]: row for row in card["evidence"]}
    assert by_text["已有收盘条件"]["source"] == "买点条件 回撤后的条件化做多"
    assert by_text["这套判断方法尚有局限"]["role"] == "unknown"
    assert by_text["部分候选方法已降级"]["role"] == "unknown"
    assert not any(row["role"] == "opposition" for row in card["evidence"])


def test_industry_risk_uses_known_states_and_displays_actual_background():
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    technical = {
        "as_of": now.date().isoformat(),
        "stale": False,
        "is_intraday_forming": False,
        "cache_fallback_used": False,
        "stage_cn": "上升",
        "color_cn": "绿",
        "risk_state_cn": "无新增风险",
    }
    holding = _holding(
        industry_reference={
            "references": [{"symbol": "515880.SS", "name": "行业ETF", "technical": technical}]
        }
    )
    card = evidence._sell_card(request, holding, now)
    assert card["status"] == "unknown" and not card["agent_eligible"]
    context = [e for e in card["evidence"] if e["scope"] == "industry_reference"]
    assert len(context) == 1 and context[0]["role"] == "context"
    assert context[0]["date"] == now.date().isoformat()
    assert context[0]["published_at"] is None
    assert "颜色 绿" in context[0]["text"] and "风险状态 无新增风险" in context[0]["text"]
    technical["risk_state_cn"] = "转灰观察"
    assert evidence._sell_card(request, holding, now)["status"] == "unknown"


def test_stale_and_future_dates_cannot_mark_buy_candidate(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    result = SimpleNamespace(symbol="512890.SS", cache_fallback_used=False)
    request.app.state.analysis_service._entries["512890.SS"] = SimpleNamespace(
        result=result, error=None, fetched_at=now
    )
    monkeypatch.setattr(evidence, "build_workspace", lambda _request: {"items": []})
    monkeypatch.setattr(evidence, "_expected_bar_date", lambda *_: now.date().isoformat())
    monkeypatch.setattr(evidence, "_forming", lambda *_: False)
    monkeypatch.setattr(
        evidence,
        "build_review",
        lambda *_args, **_kw: SimpleNamespace(
            verdict="actionable",
            candidates=[],
            resonance_groups=[],
            tradability=None,
            degraded_cn=None,
        ),
    )
    for as_of in ("2020-01-01", "2999-01-01"):
        monkeypatch.setattr(
            evidence,
            "_assessment_dto",
            lambda _, d=as_of: SimpleNamespace(
                as_of=d,
                supports=[],
                conflicts=[],
                risks=[],
                stage_cn="上行",
                color_cn="绿",
                risk_state_cn="低",
            ),
        )
        card = evidence.build_snapshot(request)["items"][0]
        assert card["status"] == "unknown"
        assert any("日期" in problem for problem in card["limitations"])


def test_industry_reference_without_technical_stays_background(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    reference = {
        "references": [
            {
                "symbol": "515880.SS",
                "name": "行业ETF",
                "technical": None,
                "source_url": "https://example.test/etf",
            }
        ]
    }
    monkeypatch.setattr(
        evidence,
        "build_workspace",
        lambda _request: {"items": [_holding(industry_reference=reference)]},
    )
    card = next(c for c in evidence.build_snapshot(request)["items"] if c["intent"] == "sell")
    assert card["status"] == "unknown"
    assert not any(
        e["role"] == "support" and e["scope"] == "same_product" for e in card["evidence"]
    )
    assert any(
        e["scope"] == "industry_reference" and e["role"] == "context" for e in card["evidence"]
    )
    assert any(e["source_ref"] == "https://example.test/etf" for e in card["evidence"])


def test_same_product_sell_signal_without_plan_keeps_opposing_evidence(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    monkeypatch.setattr(
        evidence, "build_workspace", lambda _request: {"items": [_holding(symbol="512890.SS")]}
    )
    result = SimpleNamespace(symbol="512890.SS")
    assessment = SimpleNamespace(
        as_of="2026-10-14",
        supports=[{"text_cn": "趋势仍向上"}],
        conflicts=[{"text_cn": "转弱迹象"}],
        risks=[],
        stage_cn="上涨",
        color_cn="灰",
        risk_state_cn="关注",
    )
    monkeypatch.setattr(evidence, "_technical", lambda *_: (result, assessment, []))
    monkeypatch.setattr(
        evidence,
        "extract_sell_signals",
        lambda _: [
            SimpleNamespace(
                title="颜色转黑",
                reason_cn="趋势转弱提醒",
                available_date="2026-10-14",
                provenance="system",
            )
        ],
    )
    monkeypatch.setattr(
        evidence,
        "build_review",
        lambda *_a, **_kw: SimpleNamespace(
            candidates=[
                BuyPointCandidateDTO(
                    scenario_id="x",
                    scenario_cn="测试",
                    state="watch",
                    last_state_change_date="2026-10-14",
                )
            ],
            resonance_groups=[],
            degraded_cn=None,
            summary_cn="仍有观察中的买入条件",
        ),
    )
    card = next(c for c in evidence.build_snapshot(request)["items"] if c["intent"] == "sell")
    assert card["status"] == "review" and card["agent_eligible"]
    assert any(e["role"] == "support" and "颜色转黑" in e["text"] for e in card["evidence"])
    assert any(e["role"] == "opposition" and "趋势仍向上" in e["text"] for e in card["evidence"])
    assert any(e["role"] == "opposition" and "买入条件" in e["text"] for e in card["evidence"])
    assert any(e["role"] == "unknown" and "原持仓计划" in e["text"] for e in card["evidence"])


def test_new_top_uses_own_dates_and_price_while_old_assessment_price_is_background():
    days = pd.to_datetime(["2026-10-13", "2026-10-14", "2026-10-15"])
    result = SimpleNamespace(
        frame=pd.DataFrame({"close": [0.60, 0.57, 0.53]}, index=days),
        structures=[
            SimpleNamespace(
                side="top",
                status="confirmed",
                structure_id="new-top",
                detected_date="2026-10-14",
                confirmed_date="2026-10-15",
                invalidated_date=None,
                neckline=0.542,
                reference_high=0.61,
                provenance="lei_explicit",
            )
        ],
        events=[
            SimpleNamespace(
                rule_id="top_structure",
                structure_id="new-top",
                evidence={"sub_rule": "top_structure_confirmed"},
                reason_cn="顶部构造确认：第二高点低于前高，收盘跌破此前回落低点",
            )
        ],
    )
    card = evidence._card(
        {"key": "symbol:512890.SS", "kind": "symbol", "id": "512890.SS", "name": "红利低波ETF"},
        "sell",
    )
    assessment = SimpleNamespace(
        supports=[],
        conflicts=[],
        risks=[
            RiskAlertDTO(
                priority=1,
                code="top_plus_black",
                label_cn="顶部风险",
                detail_cn="旧顶部回落低点 0.7420",
            )
        ],
        stage_cn=None,
        color_cn=None,
        risk_state_cn=None,
        dimensions={},
    )
    evidence._add_technical_evidence(card, assessment, "sell", "2026-10-15", True)
    rules = evidence._add_dated_signal_evidence(
        card,
        result,
        SimpleNamespace(candidates=[], resonance_groups=[], historical_structures=[]),
        "sell",
        current=True,
        provisional=False,
    )
    assert rules == {"top_structure"}
    support = [row for row in card["evidence"] if row["role"] == "support"]
    assert len(support) == 1
    assert support[0]["date"] == "2026-10-15"
    assert all(
        text in support[0]["text"]
        for text in ("顶部候选开始观察：2026-10-14", "0.5420", "0.6100", "距触发已过 0 根日 K")
    )
    assert "解除或失效条件" in support[0]["text"]
    assert "0.7420" not in json.dumps(card["evidence"], ensure_ascii=False)
    assert any(
        row["role"] == "context" and "现有风险状态" in row["text"]
        for row in card["evidence"]
    )


def test_cleared_top_retains_trigger_and_clear_dates_only_as_history():
    days = pd.to_datetime(["2026-10-13", "2026-10-14", "2026-10-15"])
    result = SimpleNamespace(
        frame=pd.DataFrame({"close": [0.53, 0.60, 0.62]}, index=days),
        structures=[
            SimpleNamespace(
                side="top",
                structure_id="cleared-top",
                detected_date="2026-10-13",
                confirmed_date="2026-10-14",
                invalidated_date="2026-10-15",
                neckline=0.542,
                reference_high=0.61,
                provenance="lei_explicit",
            )
        ],
        events=[],
    )
    card = evidence._card(
        {"key": "symbol:512890.SS", "kind": "symbol", "id": "512890.SS", "name": "红利低波ETF"},
        "sell",
    )
    current_rules = evidence._add_dated_signal_evidence(
        card,
        result,
        SimpleNamespace(candidates=[], resonance_groups=[], historical_structures=[]),
        "sell",
        current=True,
        provisional=False,
    )
    assert current_rules == set()
    assert len(card["evidence"]) == 1
    row = card["evidence"][0]
    assert row["role"] == "context" and row["date"] == "2026-10-14"
    assert "状态变化日期 2026-10-15" in row["text"]
    assert "0.5420" in row["text"] and "已被新高解除" in row["text"]


def test_many_old_signals_cannot_crowd_out_recent_model_evidence(monkeypatch):
    card = evidence._card(
        {"key": "symbol:512890.SS", "kind": "symbol", "id": "512890.SS", "name": "红利低波ETF"},
        "sell",
    )

    def row(side, title, event_date, *, recent=False, changed=None):
        return {
            "id": title,
            "side": side,
            "title": title,
            "event_date": event_date,
            "state_changed_date": changed or event_date,
            "age_bars": 0 if recent else 20,
            "is_recent": recent,
            "status": "new" if recent else "cleared",
            "rule_id": "top_structure" if title == "最新顶部" else None,
            "conditions": [],
            "missing_conditions": [],
            "key_prices": [],
        }

    old = [
        row(side, f"旧{side}{index}", f"2026-01-{index + 1:02d}")
        for side in ("buy", "sell")
        for index in range(26)
    ]
    old.append(row("sell", "最近解除的旧顶部", "2026-01-01", changed="2026-10-14"))
    recent = [
        row("sell", "最新顶部", "2026-10-15", recent=True),
        row("buy", "最新买点", "2026-10-15", recent=True),
    ]
    monkeypatch.setattr(evidence, "build_signal_rows", lambda *_: old + recent)
    result = SimpleNamespace(frame=pd.DataFrame(index=pd.to_datetime(["2026-10-15"])))
    current_rules = evidence._add_dated_signal_evidence(
        card, result, None, "sell", current=True, provisional=False
    )
    rows = [e for e in card["evidence"] if e["source"].startswith("同产品")]
    assert current_rules == {"top_structure"}
    assert len(rows) == 8
    assert [e["role"] for e in rows[:2]] == ["support", "opposition"]
    assert all(e["role"] == "context" for e in rows[2:])
    assert sum("旧buy" in e["text"] for e in rows) == 3
    assert sum("旧sell" in e["text"] for e in rows) == 2
    assert any("最近解除的旧顶部" in e["text"] for e in rows)
    assert not any("旧buy0" in e["text"] for e in rows)
    assert any("完整历史见 K 线信号清单" in text for text in card["limitations"])


def test_old_buy_candidate_is_history_not_waiting(monkeypatch):
    now = datetime(2026, 10, 15, 17, tzinfo=ZoneInfo("Asia/Shanghai"))
    days = pd.to_datetime(["2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"])
    result = SimpleNamespace(frame=pd.DataFrame({"close": [1, 1, 1, 1, 1]}, index=days))
    assessment = SimpleNamespace(
        as_of="2026-10-15",
        supports=[],
        conflicts=[],
        risks=[],
        stage_cn="上升",
        color_cn="绿",
        risk_state_cn="正常",
        dimensions={},
    )
    review = BuyPointReviewDTO(
        symbol="512890.SS",
        as_of="2026-10-15",
        verdict="watch",
        verdict_cn="观察",
        summary_cn="旧候选",
        candidates=[
            BuyPointCandidateDTO(
                scenario_id="old-bottom",
                scenario_cn="旧底部候选",
                direction="long",
                state="watch",
                opened_date="2026-10-09",
                last_state_change_date="2026-10-09",
                satisfied_conditions=["旧底部条件"],
            )
        ],
    )
    monkeypatch.setattr(evidence, "_technical", lambda *_: (result, assessment, []))
    monkeypatch.setattr(evidence, "build_review", lambda *_a, **_kw: review)
    monkeypatch.setattr(evidence, "extract_sell_signals", lambda _: [])
    monkeypatch.setattr(
        evidence, "_news", lambda *_a, **_kw: ([], {"name": "消息", "status": "checked"})
    )
    monkeypatch.setattr(evidence, "_public_context", lambda *_a: None)
    card = evidence._buy_card(
        SimpleNamespace(),
        {"key": "symbol:512890.SS", "kind": "symbol", "id": "512890.SS", "name": "红利低波ETF"},
        now,
    )
    assert card["status"] == "no_opportunity"
    assert "旧候选仅作历史" in card["headline"]
    assert not any(
        row["role"] == "support" and "旧底部条件" in row["text"]
        for row in card["evidence"]
    )
    assert any(
        row["role"] == "context"
        and row["date"] == "2026-10-09"
        and "距触发已过 4 根日 K" in row["text"]
        for row in card["evidence"]
    )


def test_generic_macd_gray_and_b1_risks_are_not_sell_triggers(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    assessment = SimpleNamespace(
        as_of=now.date().isoformat(),
        supports=[{"text_cn": "持有方向仍有支撑"}],
        conflicts=[
            FactorDTO(
                dimension="强度",
                label_cn="MACD强度弱化",
                detail_cn="均线强度观察",
                rule_id="macd_strength",
            ),
            {"text_cn": "B1上方阻力"},
        ],
        risks=[{"text_cn": "灰色状态需观察"}],
        dimensions={"强度(MACD)": "弱化"},
        stage_cn="观察",
        color_cn="灰",
        risk_state_cn="关注",
    )
    monkeypatch.setattr(
        evidence,
        "_technical",
        lambda *_: (SimpleNamespace(symbol="512890.SS"), assessment, []),
    )
    monkeypatch.setattr(evidence, "extract_sell_signals", lambda _: [])
    symbol = {
        "key": "symbol:512890.SS",
        "kind": "symbol",
        "id": "512890.SS",
        "name": "红利低波ETF",
    }
    cards = [
        evidence._sell_symbol_card(request, symbol, now),
        evidence._sell_card(request, _holding(symbol="512890.SS"), now),
    ]
    for card in cards:
        assert not any(e["role"] == "support" for e in card["evidence"])
        for phrase in ("MACD强度弱化", "B1上方阻力", "灰色状态需观察"):
            assert any(phrase in e["text"] and e["role"] == "context" for e in card["evidence"])
        assert any(
            e["role"] == "opposition" and "持有方向仍有支撑" in e["text"] for e in card["evidence"]
        )
    assert cards[0]["status"] == "no_opportunity"


def test_local_news_requires_exact_symbol_url_and_date(tmp_path):
    request, path = _request(tmp_path, news=True)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    published = (now - timedelta(minutes=1)).isoformat()
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO news_items VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    1,
                    "同产品风险",
                    "source",
                    "来源",
                    "https://example.test/1",
                    published,
                    json.dumps(["512890.SS"]),
                    "bearish",
                ),
                (
                    2,
                    "相似代码",
                    "source",
                    "来源",
                    "https://example.test/2",
                    published,
                    json.dumps(["512890.SSX"]),
                    "bearish",
                ),
                (
                    3,
                    "未来消息",
                    "source",
                    "来源",
                    "https://example.test/3",
                    (now + timedelta(hours=1)).isoformat(),
                    json.dumps(["512890.SS"]),
                    "bearish",
                ),
                (
                    4,
                    "无原文",
                    "source",
                    "来源",
                    "",
                    published,
                    json.dumps(["512890.SS"]),
                    "bearish",
                ),
            ],
        )
    rows, search = evidence._news(request, "512890.SS", "红利低波ETF", "buy", now)
    assert search["status"] == "checked" and len(rows) == 1
    assert rows[0]["role"] == "lead" and rows[0]["provenance"] == "news_lead"
    assert rows[0]["source_ref"] == "https://example.test/1"
    assert rows[0]["checked_at"] == now.date().isoformat()
    later = now + timedelta(minutes=2)
    subject = {
        "key": "symbol:512890.SS",
        "kind": "symbol",
        "id": "512890.SS",
        "name": "红利低波ETF",
    }
    first = evidence._buy_card(request, subject, now)
    second = evidence._buy_card(request, subject, later)
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )


def test_real_dto_future_and_degraded_candidates_never_become_current(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    bar = now.date().isoformat()
    future = (now.date() + timedelta(days=1)).isoformat()
    result = SimpleNamespace(symbol="512890.SS")
    assessment = SimpleNamespace(
        as_of=bar,
        supports=[
            FactorDTO(
                dimension="强度",
                label_cn="MACD多头扩散（研究代理）",
                detail_cn="破线须看颜色，拐头须看长周期",
                rule_id="macd_strength",
            )
        ],
        conflicts=[],
        risks=[
            RiskAlertDTO(priority=1, code="RISK", label_cn="风险关注", detail_cn="风险尚未解除")
        ],
        dimensions={"强度(MACD)": "支持", "长周期": "斜率待核"},
        stage_cn="上涨",
        color_cn="灰",
        risk_state_cn="关注",
    )
    monkeypatch.setattr(evidence, "_technical", lambda *_: (result, assessment, []))
    monkeypatch.setattr(evidence, "build_workspace", lambda _request: {"items": []})
    future_candidate = BuyPointCandidateDTO(
        scenario_id="a",
        scenario_cn="未来",
        module="A",
        state="confirmed",
        last_state_change_date=future,
        satisfied_conditions=["条件成立"],
    )
    future_opened = BuyPointCandidateDTO(
        scenario_id="b",
        scenario_cn="未来起点",
        module="B",
        state="confirmed",
        last_state_change_date=bar,
        opened_date=future,
        satisfied_conditions=["未来起点条件"],
    )
    degraded_candidate = BuyPointCandidateDTO(
        scenario_id="c",
        scenario_cn="降级",
        module="C",
        state="confirmed",
        last_state_change_date=bar,
        satisfied_conditions=["条件成立"],
    )
    review = BuyPointReviewDTO(
        symbol="512890.SS",
        as_of=bar,
        verdict="actionable",
        verdict_cn="成立",
        summary_cn="旧摘要",
        candidates=[future_candidate, future_opened, degraded_candidate],
        degraded_cn="C已降级",
        tradability=TradabilityDTO(trend_type="up", trend_type_cn="上涨", tradable=True),
    )
    monkeypatch.setattr(evidence, "build_review", lambda *_a, **_kw: review)
    card = evidence.build_snapshot(request)["items"][0]
    assert card["status"] == "unknown"
    assert all("条件成立" not in e["text"] for e in card["evidence"])
    assert all("未来起点条件" not in e["text"] for e in card["evidence"])
    macd = next(e for e in card["evidence"] if "MACD多头扩散" in e["text"])
    assert macd["provenance"] == "research_proxy" and "破线须看颜色" in macd["text"]
    assert any("MACD只表示均线强度" in e["text"] for e in card["evidence"])
    assert all(
        e["source_ref"].startswith("/symbol/")
        for e in card["evidence"]
        if e["category"] == "technical"
    )


def test_intraday_only_is_waiting_but_intraday_plus_stale_is_unknown(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    bar = now.date().isoformat()
    result = SimpleNamespace(symbol="512890.SS")
    assessment = SimpleNamespace(
        as_of=bar,
        supports=[
            FactorDTO(dimension="趋势", label_cn="仍有强度", detail_cn="盘中所见", rule_id="trend")
        ],
        conflicts=[
            FactorDTO(dimension="风险", label_cn="开始转弱", detail_cn="盘中所见", rule_id="weak")
        ],
        risks=[],
        dimensions={},
        stage_cn="观察",
        color_cn="灰",
        risk_state_cn="关注",
    )
    review = BuyPointReviewDTO(
        symbol="512890.SS",
        as_of=bar,
        verdict="actionable",
        verdict_cn="成立",
        summary_cn="盘中候选",
        tradability=TradabilityDTO(trend_type="up", trend_type_cn="上行", tradable=True),
        candidates=[
            BuyPointCandidateDTO(
                scenario_id="x",
                scenario_cn="盘中候选",
                state="confirmed",
                last_state_change_date=bar,
                satisfied_conditions=["条件盘中出现"],
            )
        ],
    )
    monkeypatch.setattr(evidence, "build_review", lambda *_a, **_kw: review)
    monkeypatch.setattr(evidence, "extract_sell_signals", lambda _: [])
    subject = {
        "key": "symbol:512890.SS",
        "kind": "symbol",
        "id": "512890.SS",
        "name": "红利低波ETF",
    }
    for problems, expected_status in [
        ([evidence._INTRADAY_GAP], "waiting"),
        ([evidence._INTRADAY_GAP, "技术资料使用旧缓存"], "unknown"),
    ]:
        monkeypatch.setattr(evidence, "_technical", lambda *_a, p=problems: (result, assessment, p))
        card = evidence._buy_card(request, subject, now)
        assert card["status"] == expected_status
        assert card["status"] != "candidate"
        if expected_status == "waiting":
            assert any(
                e["role"] == "support" and e["text"].startswith("盘中观察（尚未收盘）")
                for e in card["evidence"]
            )
            assert any(
                e["role"] == "opposition" and e["text"].startswith("盘中观察（尚未收盘）")
                for e in card["evidence"]
            )
            assert any(e["role"] == "unknown" and "收盘确认" in e["text"] for e in card["evidence"])
        else:
            assert all(e["role"] not in ("support", "opposition") for e in card["evidence"])


def test_sell_intraday_observation_never_personal_exit(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    assessment = SimpleNamespace(
        as_of=now.date().isoformat(),
        supports=[],
        conflicts=[
            FactorDTO(dimension="趋势", label_cn="转弱", detail_cn="盘中数据", rule_id="weak")
        ],
        risks=[],
        dimensions={},
        stage_cn="观察",
        color_cn="灰",
        risk_state_cn="关注",
    )
    result = SimpleNamespace(symbol="512890.SS")
    monkeypatch.setattr(
        evidence, "_technical", lambda *_: (result, assessment, [evidence._INTRADAY_GAP])
    )
    monkeypatch.setattr(
        evidence,
        "extract_sell_signals",
        lambda _: [
            SimpleNamespace(
                title="转黑",
                reason_cn="盘中变化",
                available_date=now.date().isoformat(),
                provenance="system",
            )
        ],
    )
    monkeypatch.setattr(
        evidence,
        "build_review",
        lambda *_a, **_kw: SimpleNamespace(
            candidates=[], resonance_groups=[], degraded_cn=None, summary_cn=""
        ),
    )
    card = evidence._sell_card(request, _holding(symbol="512890.SS"), now)
    assert card["status"] == "waiting" and card["headline"] == "盘中观察，待收盘确认"
    assert not any("退出" in e["text"] and e["role"] == "support" for e in card["evidence"])
    assert any(
        e["role"] == "support" and e["text"].startswith("盘中观察（尚未收盘）")
        for e in card["evidence"]
    )
    assert any(e["role"] == "unknown" and "个人退出条件" in e["text"] for e in card["evidence"])


def test_cn_1430_current_bar_is_only_intraday_gap(tmp_path, monkeypatch):
    request, _ = _request(tmp_path)
    now = datetime(2026, 10, 15, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = SimpleNamespace(symbol="512890.SS", cache_fallback_used=False)
    request.app.state.analysis_service._entries["512890.SS"] = SimpleNamespace(
        result=result, error=None, fetched_at=now
    )
    monkeypatch.setattr(evidence, "_assessment_dto", lambda _: SimpleNamespace(as_of="2026-10-15"))
    monkeypatch.setattr(evidence, "_forming", lambda *_: True)
    assert evidence._expected_bar_date("512890.SS", now) == "2026-10-14"
    _result, _assessment, problems = evidence._technical(request, "512890.SS", now)
    assert problems == [evidence._INTRADAY_GAP]


def test_historical_structure_totals_are_not_current_opposition():
    card = evidence._card(
        {"id": "515880.SS", "key": "symbol:515880.SS", "name": "通信ETF", "kind": "symbol"}, "sell"
    )
    assessment = SimpleNamespace(
        supports=[
            SimpleNamespace(
                rule_id="bottom_c_lifecycle", label_cn="存在32个有效底部结构", detail_cn="旧结构"
            )
        ],
        conflicts=[],
        risks=[],
        dimensions={},
    )
    evidence._add_technical_evidence(card, assessment, "sell", "2026-10-15", True)
    row = card["evidence"][0]
    assert row["role"] == "context"
    assert "未绑定近期入场依据" in row["text"]


def test_industry_macro_material_is_public_context_not_fund_trigger(monkeypatch):
    card = evidence._card(
        {"id": "fund1", "key": "holding:fund1", "kind": "holding", "name": "基金甲"}, "buy"
    )
    row = {
        "text": "行业经营：已有统计",
        "source": "主管部门",
        "date": "2026-09-28",
        "scope": "industry_reference",
        "provenance": "verified_public_source",
        "source_ref": "https://example.test/industry",
        "category": "industry",
        "published_at": "2026-09-28",
        "checked_at": "2026-10-15",
        "report_date": "2026-08-31",
        "limitations": [],
    }
    monkeypatch.setattr(
        evidence.opportunity_context, "public_sources", lambda *args, **kwargs: [row]
    )
    item = {
        "disclosure": {"status": "available", "holdings": []},
        "industry_reference": {"references": [{"symbol": "515880.SS", "name": "通信ETF"}]},
    }
    evidence._fund_disclosure(card, item, datetime(2026, 10, 15, tzinfo=ZoneInfo("Asia/Shanghai")))
    found = [x for x in card["evidence"] if x["text"].startswith("行业经营")]
    assert (
        len(found) == 1
        and found[0]["role"] == "context"
        and found[0]["scope"] == "industry_reference"
    )
    assert card["status"] == "unknown"




def test_same_market_macro_is_narrative_and_does_not_change_technical_status(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_macro
    request, _ = _request(tmp_path)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    calls = []
    def read(_request, market, _now):
        calls.append(market)
        return {"status": "ready", "rows": [{"text": "过去一个月融资余额变化，仅为资金背景",
            "source": "已有宏观观察", "source_ref": "https://example.test/macro",
            "date": "2026-10-14",
            "provenance": "local_macro_observation", "limitations": []}]}
    monkeypatch.setattr(opportunity_macro, "read_macro", read)
    card = evidence._card({"key": "symbol:000300.SS", "kind": "symbol",
                           "id": "000300.SS", "name": "沪深300"}, "buy")
    evidence._public_context(request, card, "000300.SS", "沪深300", now)
    assert calls == ["cn"]
    assert card["status"] == "unknown" and not card["agent_eligible"]
    row = next(e for e in card["evidence"] if e["provenance"] == "local_macro_observation")
    assert row["role"] == "context" and row["scope"] == "narrative"
    assert row["narrative_kind"] == "macro" and row["relevance"] == "market_context"
    assert card["narrative_focus"]["kind"] == "broad"
