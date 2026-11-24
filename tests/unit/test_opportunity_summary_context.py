"""Narrative context stays dated, identity-bound, and observational."""

import json
from datetime import date

from lei_signal.api.opportunity_summary_context import (
    curated_sources,
    recent_news_watch,
    select_slots,
    valid_day,
)


def test_optional_sources_require_exact_identity_and_real_publication_dates(tmp_path):
    path = tmp_path / "sources.json"
    base = {
        "symbol": "SOXX",
        "name": "半导体 SOXX",
        "kind": "news",
        "published_at": "2026-10-15",
        "report_date": "2026-09-30",
        "checked_at": "2026-10-18",
        "text": "季度营收上升，利润率下降。",
        "source": "公司公告",
        "source_ref": "https://example.com/source",
    }
    method = {
        **base,
        "kind": "sentiment",
        "evidence_type": "method",
        "published_at": None,
        "report_date": None,
        "text": "VIX只衡量预期波动，不预测涨跌。",
    }
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "products": [
                    base,
                    {**base, "published_at": "2026-10-19"},
                    {**base, "name": "另一只基金"},
                    method,
                ],
            }
        ),
        encoding="utf-8",
    )
    rows = curated_sources("SOXX", "半导体 SOXX", date(2026, 10, 18), path=path)
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-10-15"
    assert rows[0]["report_date"] == "2026-09-30"
    assert rows[0]["published_at"] == "2026-10-15"
    assert rows[1]["date"] is None and rows[1]["checked_at"] == "2026-10-18"
    assert curated_sources("XLK", "半导体 SOXX", date(2026, 10, 18), path=path) == []


def test_method_alone_cannot_make_a_context_available():
    method = {
        "id": "m",
        "kind": "macro",
        "evidence_type": "method",
        "date": None,
        "limitations": ["方法发布日期未知"],
    }
    slots = select_slots([method])
    assert slots["macro"]["sources"] == []
    observation = {
        "id": "o",
        "kind": "macro",
        "evidence_type": "observation",
        "date": "2026-10-16",
        "limitations": [],
    }
    assert [x["id"] for x in select_slots([method, observation])["macro"]["sources"]] == ["o", "m"]


def test_future_and_undated_values_are_not_current_facts():
    today = date(2026, 10, 18)
    assert valid_day("2026-10-19", today) is None
    assert valid_day("2026-10-17T10:00:00", today) is None
    assert valid_day("2026-10-17T10:00:00+08:00", today) == "2026-10-17"


def test_five_calendar_days_use_publication_not_check_or_report_date(tmp_path):
    event = {
        "scope": "macro",
        "provenance": "verified_public_source",
        "event_type": "macro_release",
        "published_at": "2026-10-15",
        "checked_at": "2026-10-19",
        "report_date": "2026-09-30",
        "source_ref": "https://example.com/release",
        "text": "正式经济发布。",
        "source": "官方",
    }
    rows = [
        event,
        {**event, "source_ref": "https://example.com/old", "published_at": "2026-10-14"},
        {**event, "source_ref": "https://example.com/future", "published_at": "2026-10-20"},
        {**event, "source_ref": "https://example.com/undated", "published_at": None},
    ]
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"schema_version": 1, "events": rows}))
    result = recent_news_watch({}, date(2026, 10, 19), path=path)
    assert [x["source_ref"] for x in result["macro_news"]] == [event["source_ref"]]
    assert result["older_macro_news"][0]["published_at"] == "2026-10-14"
    assert not recent_news_watch({}, date(2026, 10, 20), path=path)["macro_news"]


def test_shared_news_deduplicates_products_and_keeps_only_verified_recent(tmp_path):
    source = {
        "provenance": "verified_public_source",
        "category": "industry",
        "public": True,
        "published_at": "2026-10-16",
        "date": "2026-10-16",
        "source_ref": "https://example.com/earnings",
        "text": "行业企业季度经营披露。",
        "source": "原始公告",
    }
    board = {
        "items": [
            {
                "card": {
                    "subject": {"kind": "symbol", "id": symbol, "name": symbol},
                    "evidence": [
                        source,
                        {**source, "provenance": "unverified_news"},
                        {
                            **source,
                            "source_ref": "https://example.com/old",
                            "published_at": "2026-08-31",
                        },
                    ],
                }
            }
            for symbol in ["SOXX", "XLK"]
        ]
    }
    result = recent_news_watch(board, date(2026, 10, 19), path=tmp_path / "missing.json")
    assert len(result["industry_news"]) == 1
    assert {p["symbol"] for p in result["industry_news"][0]["products"]} == {"SOXX", "XLK"}
    assert result["news_coverage"]["older_industry_excluded"] == 1


def test_summary_news_expires_even_if_old_review_run_is_reused():
    news = {
        "id": "n",
        "kind": "news",
        "date": "2026-10-15",
        "published_at": "2026-10-15",
        "evidence_type": "observation",
    }
    assert select_slots([news], as_of=date(2026, 10, 19))["news"]["sources"]
    assert not select_slots([news], as_of=date(2026, 10, 20))["news"]["sources"]


def test_automatic_originals_use_publication_window_and_exact_product_mapping(tmp_path):
    from lei_signal.api.opportunity_summary_context import news_profiles, recent_news_watch

    empty = tmp_path / "sources.json"
    empty.write_text('{"schema_version":1}')
    board = {
        "items": [
            {
                "card": {
                    "subject": {"kind": "symbol", "id": "515880.SS", "name": "通信ETF"},
                    "narrative_focus": {"market": "cn", "topics": ["光模块"]},
                }
            }
        ]
    }
    assert news_profiles(board)[0]["topics"] == ["光模块"]
    event = {
        "scope": "industry",
        "source_ref": "https://example.org/release",
        "published_at": "2026-10-16",
        "checked_at": "2026-10-19T01:00:00+08:00",
        "text": "原件中的具体产业信息。",
        "provenance": "verified_public_source",
        "products": [{"symbol": "515880.SS", "name": "通信ETF"}],
    }
    auto = {
        "events": [
            event,
            {**event, "source_ref": "https://example.org/old", "published_at": "2026-10-12"},
        ],
        "coverage": {"checked_sources": 1, "expected_sources": 2, "status": "partial"},
    }
    result = recent_news_watch(board, date(2026, 10, 19), path=empty, automated=auto)
    assert len(result["industry_news"]) == 1
    assert result["industry_news"][0]["published_at"] == "2026-10-16"
    assert result["news_update"]["status"] == "partial"
    assert result["news_coverage"]["older_industry_excluded"] == 1


def test_curated_and_automatic_directory_article_are_one_event(tmp_path):
    from lei_signal.api.opportunity_summary_context import recent_news_watch

    event = {
        "scope": "macro",
        "source_ref": "https://www.federalreserve.gov/releases/g17/20261016/",
        "published_at": "2026-10-16",
        "text": "美国工业产出增长，制造业与需求仍需分开看。",
        "provenance": "verified_public_source",
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"schema_version": 1, "events": [event]}))
    automatic = {"events": [{**event, "source_ref": event["source_ref"] + "default.htm"}]}
    result = recent_news_watch({}, date(2026, 10, 19), path=path, automated=automatic)
    assert len(result["macro_news"]) == 1
    assert result["macro_news"][0]["text"] == event["text"]
    assert result["news_coverage"]["verified_recent"] == 1


def test_news_product_merge_uses_symbol_not_optional_relation_metadata(tmp_path):
    from lei_signal.api.opportunity_summary_context import recent_news_watch

    event = {
        "scope": "industry", "source_ref": "https://example.org/earnings",
        "published_at": "2026-10-16", "text": "公司经营披露。",
        "provenance": "verified_public_source",
        "products": [{"symbol": "SOXX", "name": "半导体ETF"}],
    }
    board = {"items": [{"card": {"subject": {"kind": "symbol", "id": "SOXX"}}}]}
    automatic = {"events": [event, {**event, "products": [
        {"symbol": "SOXX", "name": "半导体ETF", "relation": "industry_reference"}
    ]}]}
    result = recent_news_watch(
        board, date(2026, 10, 19), path=tmp_path / "none", automated=automatic
    )
    assert len(result["industry_news"][0]["products"]) == 1



def test_automatic_nbs_display_omits_page_header_but_retains_report_year(tmp_path):
    from lei_signal.api.opportunity_summary_context import recent_news_watch

    text = ("2026/10/16 09:30 Aa 分享到： 2025年统计公报 国家统计局 "
            "2026年10月16日 2025年，全国研究经费保持增长。")
    event = {
        "scope": "macro", "source_id": "cn-nbs",
        "source_ref": "https://www.stats.gov.cn/sj/zxfb/example.html",
        "published_at": "2026-10-16", "text": text,
        "provenance": "verified_public_source",
    }
    result = recent_news_watch(
        {}, date(2026, 10, 19), path=tmp_path / "missing.json",
        automated={"events": [event]},
    )
    assert result["macro_news"][0]["text"] == "2025年，全国研究经费保持增长。"
    assert event["text"] == text
