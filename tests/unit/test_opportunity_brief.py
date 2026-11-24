from copy import deepcopy

import pytest

from lei_signal.api.opportunity_brief import build_product_brief


def _evidence(identity="e1", **overrides):
    value = {
        "id": identity,
        "role": "context",
        "text": "公开披露的行业事实",
        "category": "industry",
        "source_ref": "https://example.org/report",
        "date": "2026-10-14",
        "public": True,
        "provenance": "verified_public_source",
        "narrative_kind": "industry",
        "scope": "industry_reference",
        "relevance": "direct",
    }
    value.update(overrides)
    return value


def _item(side="buy", *, subject=None, evidence=None, context=None, counter=None):
    return {
        "card": {
            "subject": subject
            or {"key": "symbol:510300", "kind": "symbol", "id": "510300", "name": "沪深300ETF"},
            "intent": side,
            "evidence": evidence if evidence is not None else [_evidence()],
            "limitations": [f"{side}资料限制"],
            "narrative_focus": {"kind": "sector"},
        },
        "audit": {
            "status": "complete",
            "generated_at": "2026-10-15T08:00:00+08:00",
            "agents": {
                "context": context or {"status": "unavailable", "points": []},
                "counter": counter or {"status": "unavailable", "points": []},
            },
        },
    }


def _board(items=None):
    return {
        "run_id": "run-1",
        "status": "partial",
        "checked_at": "2026-10-15T09:00:00+08:00",
        "limitations": ["全局资料限制"],
        "items": items if items is not None else [_item("buy"), _item("sell")],
    }


def _signal(side="buy", status="new", **overrides):
    value = {
        "id": f"{side}-1",
        "side": side,
        "status": status,
        "is_recent": True,
        "event_date": "2026-10-15",
        "title": "原规则事件",
        "summary": "原规则说明",
        "invalidation_cn": "原结构失效",
        "next_step_cn": "核对原条件",
        "missing_conditions": [],
    }
    value.update(overrides)
    return value


def _technical(signals=None, **overrides):
    value = {
        "symbol": "510300",
        "as_of": "2026-10-15",
        "meta": {
            "freshness": "current",
            "last_bar_date": "2026-10-15",
            "is_intraday_forming": False,
            "bar_status": "closed",
        },
        "chart": {"dates": ["2026-10-14", "2026-10-15"], "ohlc": [[1, 1, 1, 1], [1, 1, 1, 1]]},
        "signals": signals if signals is not None else [_signal()],
        "limitations": ["技术资料限制"],
    }
    value.update(overrides)
    return value


def test_current_event_keeps_original_signal_and_dates():
    technical = _technical([_signal(), _signal("sell", "waiting", missing_conditions=["待收盘"])])
    brief = build_product_brief(
        _board(), "symbol:510300", technical=technical, errors={"market": "超时"}
    )
    assert brief["schema_version"] == "opportunity-brief/1"
    assert brief["directions"]["buy"]["status"] == "attention"
    assert brief["directions"]["sell"]["status"] == "waiting"
    assert brief["directions"]["buy"]["signals"][0] is technical["signals"][0]
    assert "2026-10-15" in brief["summary"]["text"]
    assert brief["directions"]["buy"]["signals"][0]["invalidation_cn"] == "原结构失效"
    assert len(brief["summary"]["text"]) < 150
    assert brief["review_status"] == "partial"
    assert brief["dates"]["technical"] == "2026-10-15"
    assert brief["errors"] == {"market": "超时"}
    assert brief["limitations"] == ["全局资料限制", "buy资料限制", "sell资料限制", "技术资料限制"]


def test_intraday_waits_and_cleared_or_old_events_do_not_alert():
    technical = _technical(
        [_signal(), _signal("sell", "cleared"), _signal("buy", "active", is_recent=False)]
    )
    technical["meta"]["is_intraday_forming"] = True
    technical["meta"]["bar_status"] = "intraday"
    brief = build_product_brief(_board(), "symbol:510300", technical=technical)
    assert brief["directions"]["buy"]["status"] == "waiting"
    assert "盘中待收盘" in brief["directions"]["buy"]["text"]
    assert brief["directions"]["sell"]["status"] == "none"
    assert len(brief["directions"]["buy"]["signals"]) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"symbol": "159915"},
        {"meta": {"freshness": "stale", "last_bar_date": "2026-10-15"}},
        {"meta": {"freshness": "current", "last_bar_date": "2026-10-14"}},
        {"chart": {"dates": ["2026-10-14"]}},
        {"meta": {"freshness": "current", "last_bar_date": "2026-10-15", "bar_status": "unknown"}},
        {"chart": {"dates": ["2026-10-14", "2026-10-15"], "ohlc": [[1, 1, 1, 1]]}},
    ],
)
def test_wrong_product_stale_or_date_mismatch_is_unavailable(change):
    technical = _technical(**change)
    brief = build_product_brief(_board(), "symbol:510300", technical=technical)
    assert brief["directions"]["buy"]["status"] == "unavailable"
    assert brief["directions"]["buy"]["signals"] == []
    assert "无法确认" in brief["summary"]["text"]
    assert brief["technical"] is technical


def test_fund_market_and_sector_reference_do_not_create_signal():
    subject = {
        "key": "holding:123",
        "kind": "holding",
        "id": "123",
        "code": "012345",
        "name": "某行业基金",
    }
    evidence = _evidence(text="披露行业事实", category="industry")
    market = {
        "subject_key": "holding:123",
        "nav": {"latest": {"date": "2026-10-14", "value": 1.2}},
        "references": [{"symbol": "510300", "relation": "行业参考"}],
        "disclosure": {"report_date": "2026-09-30"},
    }
    board = _board([_item(subject=subject, evidence=[evidence])])
    brief = build_product_brief(board, "holding:123", technical=_technical(), market=market)
    assert brief["directions"]["buy"]["status"] == "unavailable"
    assert brief["background"][0] == {
        "text": "披露行业事实",
        "tone": "unclear",
        "kind": "source",
        "evidence": [evidence],
    }
    assert brief["dates"]["nav"] == "2026-10-14"
    assert brief["dates"]["disclosure"] == "2026-09-30"
    assert "已取得截至2026-10-14的净值走势" in brief["summary"]["text"]


def test_holding_technical_uses_verified_symbol_and_never_bare_fund_code():
    subject = {
        "key": "holding:123",
        "kind": "holding",
        "id": "123",
        "code": "012345",
        "symbol": "510300",
    }
    board = _board([_item(subject=subject)])
    assert (
        build_product_brief(board, "holding:123", technical=_technical())["directions"]["buy"][
            "status"
        ]
        == "attention"
    )
    assert (
        build_product_brief(board, "holding:123", technical=_technical(symbol="012345"))[
            "directions"
        ]["buy"]["status"]
        == "unavailable"
    )


def test_wrong_fund_market_cannot_appear_in_summary_or_chart():
    subject = {"key": "holding:123", "kind": "holding", "id": "123"}
    value = build_product_brief(
        _board([_item(subject=subject)]),
        "holding:123",
        market={"subject_key": "holding:other", "nav": {"latest": {"date": "2026-10-15"}}},
    )
    assert value["market"] is None
    assert value["dates"]["nav"] is None
    assert value["errors"]["market"]


def test_counter_accepts_dated_same_product_rule_but_not_personal_note():
    evidence = _evidence(
        public=False,
        category="technical",
        scope="same_product",
        provenance="existing_rule",
        source_ref="/symbol/510300",
        role="opposition",
    )
    stage = {
        "status": "complete",
        "points": [{"text": "规则反例", "stance": "risk", "evidence_ids": ["e1"]}],
    }
    board = _board([_item(evidence=[evidence], counter=stage)])
    assert build_product_brief(board, "symbol:510300")["opposition"]["buy"]["status"] == "complete"
    evidence["provenance"] = "personal_note"
    assert (
        build_product_brief(board, "symbol:510300")["opposition"]["buy"]["status"] == "unavailable"
    )


def test_context_requires_all_real_citations_and_prioritizes_direct_sector_fact():
    context = {
        "status": "complete",
        "points": [
            {"text": "无引用观点", "evidence_ids": [], "stance": "support"},
            {"text": "缺失引用观点", "evidence_ids": ["missing"], "stance": "support"},
            {"text": "行业直接业务", "evidence_ids": ["industry"], "stance": "neutral"},
            {"text": "公司披露", "evidence_ids": ["profile"], "stance": "support"},
        ],
    }
    evidence = [
        _evidence("profile", narrative_kind="profile", scope="same_product", text="公司披露原文"),
        _evidence("industry", text="行业原文"),
    ]
    brief = build_product_brief(
        _board([_item(evidence=evidence, context=context)]), "symbol:510300"
    )
    assert [entry["text"] for entry in brief["background"]] == ["行业直接业务", "公司披露"]
    assert all(entry["kind"] == "agent" for entry in brief["background"])
    bad = deepcopy(context)
    bad["points"] = [{"text": "标题线索", "evidence_ids": ["lead"], "stance": "support"}]
    fallback = build_product_brief(
        _board([_item(evidence=[_evidence("lead", role="lead"), evidence[1]], context=bad)]),
        "symbol:510300",
    )
    assert fallback["background"][0]["kind"] == "source"


def test_counter_is_separate_dated_and_all_references_must_resolve():
    buy = {
        "status": "complete",
        "generated_at": "2026-10-14T16:00:00+08:00",
        "points": [{"text": "买入侧风险", "evidence_ids": ["buy-e"], "stance": "risk"}],
    }
    sell = {
        "status": "complete",
        "generated_at": "2026-10-13T16:00:00+08:00",
        "points": [{"text": "卖出侧疑点", "evidence_ids": ["sell-e"], "stance": "unknown"}],
    }
    board = _board(
        [
            _item("buy", evidence=[_evidence("buy-e")], counter=buy),
            _item("sell", evidence=[_evidence("sell-e")], counter=sell),
        ]
    )
    brief = build_product_brief(board, "symbol:510300")
    assert brief["opposition"]["buy"]["status"] == "complete"
    assert "2026-10-14" in brief["opposition"]["buy"]["text"]
    assert "2026-10-13" in brief["opposition"]["sell"]["text"]
    assert brief["opposition"]["buy"]["evidence"][0]["id"] == "buy-e"
    board["items"][1]["audit"]["agents"]["counter"]["points"].append(
        {"text": "无依据", "evidence_ids": [], "stance": "risk"}
    )
    assert (
        build_product_brief(board, "symbol:510300")["opposition"]["sell"]["status"] == "unavailable"
    )


def test_subject_must_exist():
    with pytest.raises(ValueError):
        build_product_brief(_board(), "symbol:missing")


def test_sell_supporting_rule_is_a_check_not_opposition():
    evidence = _evidence(
        category="technical", scope="same_product", provenance="existing_rule",
        source_ref="/symbol/510300", role="support", text="底部结构失效，核对原计划",
    )
    counter = {"status": "complete", "points": [
        {"text": "底部结构失效，需核对是否适用于原计划", "stance": "risk", "evidence_ids": ["e1"]},
    ]}
    entry = build_product_brief(
        _board([_item("sell", evidence=[evidence], counter=counter)]), "symbol:510300",
    )["opposition"]["sell"]
    assert entry["kind"] == "check"
    assert entry["evidence"][0]["role"] == "support"


def test_technical_opposition_keeps_original_rule_direction():
    evidence = _evidence(
        category="technical", scope="same_product", provenance="existing_rule",
        source_ref="/symbol/510300", role="opposition", text="长周期背景支持或改善中",
    )
    counter = {"status": "complete", "points": [
        {"text": "该技术支持项实为退出方向证据", "stance": "risk", "evidence_ids": ["e1"]},
    ]}
    entry = build_product_brief(
        _board([_item("sell", evidence=[evidence], counter=counter)]), "symbol:510300",
    )["opposition"]["sell"]
    assert entry["kind"] == "opposition"
    assert entry["text"] == "原规则的反向条件：长周期背景支持或改善中"


def test_fund_background_leads_with_allocation_and_coverage_not_arbitrary_stocks():
    manager = _evidence(
        "manager",
        provenance="disclosed",
        category="fundamentals",
        text="基金经理观点：提高了AI算力、半导体配置；后续调仓未知。",
    )
    coverage = _evidence(
        "coverage",
        provenance="disclosed",
        category="fundamentals",
        text="已披露股票覆盖基金净值43.49%；其余持仓未知。",
    )
    stock = _evidence(
        "stock",
        provenance="disclosed",
        category="fundamentals",
        text="披露股票：某公司，占基金净值4.5%。",
    )
    item = _item(evidence=[stock, _evidence(), coverage, manager])
    item["card"]["narrative_focus"] = {"kind": "mixed"}
    brief = build_product_brief(_board([item]), "symbol:510300")
    assert [e["text"] for e in brief["background"]] == [manager["text"], coverage["text"]]
    assert all(e["kind"] == "source" and e["tone"] == "unclear" for e in brief["background"])


def test_waiting_condition_survives_summary_and_direction_text():
    signal = _signal("buy", "waiting", missing_conditions=["站回原规则参考线"])
    brief = build_product_brief(_board(), "symbol:510300", technical=_technical([signal]))
    for text in (brief["summary"]["text"], brief["directions"]["buy"]["text"]):
        assert "等待条件" in text
        assert "站回原规则参考线" in text
    assert brief["directions"]["buy"]["status"] == "waiting"


def test_mixed_confirmed_and_waiting_events_remain_distinct_in_compact_text():
    signals = [
        _signal(title="事件甲"),
        _signal("buy", "active", id="buy-2", title="事件乙"),
        _signal("buy", "waiting", id="buy-3", title="事件丙", missing_conditions=["确认原结构"]),
    ]
    brief = build_product_brief(_board(), "symbol:510300", technical=_technical(signals))
    assert brief["directions"]["buy"]["status"] == "attention"
    for text in (brief["summary"]["text"], brief["directions"]["buy"]["text"]):
        assert "已触发" in text
        assert "等待条件" in text
        assert "确认原结构" in text
    assert brief["directions"]["buy"]["signals"] == signals


def test_intraday_text_never_presents_event_as_confirmed():
    technical = _technical()
    technical["meta"]["bar_status"] = "intraday"
    brief = build_product_brief(_board(), "symbol:510300", technical=technical)
    for text in (brief["summary"]["text"], brief["directions"]["buy"]["text"]):
        assert "盘中待收盘" in text
        assert "已触发" not in text


def test_key_gaps_preserve_specific_agent_gap_and_deduplicate_between_sides():
    gap = "缺该基金最近披露持仓的覆盖比例"
    stage = {"status": "complete", "points": [], "gaps": [gap, gap]}
    board = _board([_item("buy", context=stage), _item("sell", context=stage)])
    board["status"] = "complete"
    brief = build_product_brief(board, "symbol:510300", technical=_technical())
    assert brief["key_gaps"] == [{"kind": "agent", "text": gap, "side": "buy", "agent": "context"}]
    assert brief["limitations"] == ["全局资料限制", "buy资料限制", "sell资料限制", "技术资料限制"]


def test_key_gaps_separate_technical_failure_from_partial_review():
    board = _board()
    brief = build_product_brief(board, "symbol:510300", errors={"technical": "技术读取超时"})
    assert [gap["kind"] for gap in brief["key_gaps"]] == ["technical", "review"]
    assert brief["errors"] == {"technical": "技术读取超时"}
    assert brief["review_status"] == "partial"
    assert "技术" in brief["key_gaps"][0]["text"]
    assert "本批" in brief["key_gaps"][1]["text"]


def test_selected_product_gaps_take_priority_over_batch_partial_and_cap_at_two():
    context = {
        "status": "complete",
        "points": [],
        "gaps": ["缺持仓覆盖比例", "缺最近发布原件", "缺第三项"],
    }
    board = _board([_item(context=context)])
    brief = build_product_brief(board, "symbol:510300", technical=_technical())
    assert [gap["text"] for gap in brief["key_gaps"]] == ["缺持仓覆盖比例", "缺最近发布原件"]


def test_selected_failed_agent_is_a_review_gap_not_a_technical_failure():
    context = {"status": "failed", "points": [], "gaps": []}
    board = _board([_item(context=context)])
    brief = build_product_brief(board, "symbol:510300", technical=_technical())
    assert brief["key_gaps"][0]["kind"] == "review"
    assert brief["key_gaps"][0]["agent"] == "context"
    assert "基本面与新闻" in brief["key_gaps"][0]["text"]
    assert brief["directions"]["buy"]["status"] == "attention"


def test_complete_review_without_gaps_has_no_key_gaps():
    board = _board()
    board["status"] = "complete"
    assert build_product_brief(board, "symbol:510300", technical=_technical())["key_gaps"] == []


@pytest.fixture
def cached_brief_client(monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace as NS

    import pandas as pd
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from lei_signal.api.routes import opportunities, symbols
    from lei_signal.api.routes import opportunity_reviews as route
    from lei_signal.ui import echarts_kline

    frame = pd.DataFrame({'close': [1., 1.]}, index=pd.to_datetime(['2026-10-15', '2026-10-16']))
    result = NS(symbol='510300.SS', display_name='沪深300ETF', frame=frame,
                events=[], structures=[], weekly_trend=pd.DataFrame(), cache_fallback_used=False,
                price_data=NS(report=NS(last_date=frame.index[-1], provider='test', adjusted=True),
                              info=NS(timezone='Asia/Shanghai')))
    entry = NS(result=result, error=None, fetched_at=datetime(2026, 10, 16, 8, tzinfo=UTC))
    def forbidden_get(*args, **kwargs):
        pytest.fail('brief must not call analysis service.get')
    service = NS(_entries={}, get=forbidden_get)
    app = FastAPI()
    app.state.analysis_service = service
    app.include_router(route.router)
    subject = {'key': 'symbol:510300.SS', 'kind': 'symbol',
               'id': '510300.SS', 'name': '沪深300ETF'}
    monkeypatch.setattr(route, 'run', lambda *a: _board([_item(subject=subject)]))
    monkeypatch.setattr(symbols, '_assessment_dto', lambda value: NS(
        as_of=value.frame.index[-1].date().isoformat(),
        color='green', color_cn='绿色', stage_cn='趋势增强'))
    monkeypatch.setattr(opportunities, 'build_review', lambda *a, **k: NS(
        candidates=[], resonance_groups=[], historical_structures=[]))
    monkeypatch.setattr(echarts_kline, 'serialize_result', lambda value, **k: {
        'dates': [ts.date().isoformat() for ts in value.frame.index],
        'ohlc': [[1, 1, 1, 1]] * len(value.frame)})
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 18, 5, tzinfo=UTC).astimezone(tz)
    monkeypatch.setattr(route, 'datetime', FixedDatetime)
    return TestClient(app), service, entry


def _cached_brief(client):
    response = client.get('/api/opportunity-reviews/runs/orb_' + 'a' * 64 + '/brief',
                          params={'subject_key': 'symbol:510300.SS'})
    assert response.status_code == 200
    return response.json()


def test_cold_brief_returns_saved_background_without_fetching(cached_brief_client):
    client, service, _entry = cached_brief_client
    body = _cached_brief(client)
    assert body['technical'] is None
    assert body['background'][0]['text'] == '公开披露的行业事实'
    assert body['directions']['buy']['status'] == 'unavailable'
    assert '尚未读取' in body['errors']['technical']
    del service._entries
    assert _cached_brief(client)['technical'] is None


def test_cached_brief_preserves_same_snapshot_and_dates_without_get(cached_brief_client):
    client, service, entry = cached_brief_client
    service._entries['510300.SS'] = entry
    body = _cached_brief(client)
    assert body['technical']['symbol'] == '510300.SS'
    assert body['technical']['as_of'] == '2026-10-16'
    assert body['technical']['chart']['dates'][-1] == body['technical']['meta']['last_bar_date']
    assert body['technical']['meta']['freshness'] == 'current'
    assert body['technical']['meta']['bar_status'] == 'closed'
    assert body['directions']['buy']['status'] == 'none'
    assert body['errors'] == {}


def test_cached_brief_rejects_wrong_product_and_report_chart_date_mismatch(cached_brief_client):
    client, service, entry = cached_brief_client
    service._entries['510300.SS'] = entry
    entry.result.symbol = '510500.SS'
    wrong = _cached_brief(client)
    assert wrong['technical'] is None
    assert '身份不一致' in wrong['errors']['technical']
    entry.result.symbol = '510300.SS'
    entry.result.price_data.report.last_date = entry.result.frame.index[-2]
    mismatch = _cached_brief(client)
    assert mismatch['technical']['meta']['freshness'] == 'unknown'
    assert mismatch['directions']['buy']['status'] == 'unavailable'


def test_explicit_technical_endpoint_still_reads_service(cached_brief_client):
    client, service, entry = cached_brief_client
    calls = []
    service.get = lambda symbol: calls.append(symbol) or entry
    response = client.get('/api/opportunity-reviews/technical/510300.SS')
    assert response.status_code == 200
    assert calls == ['510300.SS']
    assert response.json()['meta']['freshness'] == 'current'
