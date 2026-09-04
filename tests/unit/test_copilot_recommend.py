"""今日推荐：资格门 + 透明计分 + 板块排序 + 消息面容错适配。"""
from __future__ import annotations

from lei_signal.api.schemas import ScanItemDTO
from lei_signal.copilot.recommend import (
    build_recommendation,
    extract_news_heat,
    pick_sectors,
)


def _scan(symbol: str, verdict: str, rr: float | None = None, name: str = "") -> ScanItemDTO:
    return ScanItemDTO(
        symbol=symbol,
        display_name=name or symbol,
        verdict=verdict,
        verdict_cn=verdict,
        reward_risk_ratio=rr,
        reward_risk_computable=rr is not None,
    )


def test_gate_excludes_blocked_and_none():
    card = build_recommendation(
        [_scan("000001", "blocked"), _scan("600000", "none"), _scan("515880", "waiting", 2.0)],
        run_date="2026-09-05",
    )
    assert [i.symbol for i in card.items] == ["515880"]


def test_actionable_ranks_above_waiting_rr_breaks_ties():
    card = build_recommendation(
        [
            _scan("A", "waiting", rr=4.0),
            _scan("B", "actionable", rr=2.0),
            _scan("C", "actionable", rr=3.5),
        ],
        run_date="2026-09-05",
    )
    assert [i.symbol for i in card.items] == ["C", "B", "A"]


def test_reasons_are_transparent_and_carry_numbers():
    card = build_recommendation(
        [_scan("515880", "actionable", rr=3.4, name="通信ETF")],
        run_date="2026-09-05",
    )
    item = card.items[0]
    assert any("actionable" in r or "条件" in r for r in item.reasons)
    assert any("3.4" in r for r in item.reasons)


def test_top_symbols_limit():
    items = [_scan(f"s{i}", "waiting") for i in range(8)]
    card = build_recommendation(items, run_date="2026-09-05", top_symbols=5)
    assert len(card.items) == 5


def test_news_heat_two_shapes():
    brief_a = {"items": [{"symbol": "515880", "bull_count": 2, "bear_count": 0}]}
    brief_b = {"symbols": {"515880": {"bull": 3, "bear": 1}}}
    assert extract_news_heat(brief_a, "515880") == (2, ["近3天消息偏多（多2/空0）"])
    heat, _ = extract_news_heat(brief_b, "515880")
    assert heat == 2
    assert extract_news_heat(None, "515880") == (0, [])
    assert extract_news_heat({}, "515880") == (0, [])


def test_news_bonus_affects_order_not_gate():
    brief = {"items": [
        {"symbol": "LOW", "bull_count": 0, "bear_count": 0},
        {"symbol": "HIGH", "bull_count": 3, "bear_count": 0},
    ]}
    card = build_recommendation(
        [_scan("LOW", "waiting", 2.0), _scan("HIGH", "waiting", 2.0)],
        run_date="2026-09-05", news_brief=brief,
    )
    assert card.items[0].symbol == "HIGH"


def test_pick_sectors_orders_by_stage_rank():
    rows = [
        {"code": "BK1", "name": "半导体", "stage": "markup"},
        {"code": "BK2", "name": "电力", "stage": "decline"},
        {"code": "BK3", "name": "有色", "stage": "accumulation"},
    ]
    picks = pick_sectors(rows, top_n=2)
    assert [p.code for p in picks] == ["BK1", "BK3"]
    assert picks[0].stage_cn == "上升"


def test_pick_sectors_tolerates_none_and_unknown_keys():
    assert pick_sectors(None, 3) == []
    assert pick_sectors([{"code": "BK1"}], 3)[0].code == "BK1"
