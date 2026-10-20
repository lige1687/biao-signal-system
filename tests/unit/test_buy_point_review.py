"""买点审阅门禁：verdict 四态派生、止损不编造、watch 条件价位/状态区分。

核心红线：本模块不做买点判断。verdict 由既有 DTO 字段组合派生；
止损只引场景/结构已给出的失效位；盈亏比只照抄。无法取到的数值一律 None。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.routes.opportunities import (
    VERDICT_ACTIONABLE,
    VERDICT_BLOCKED,
    VERDICT_NONE,
    VERDICT_WAITING,
    _review_from_assessment,
)
from lei_signal.api.schemas import (
    ConditionalScenarioDTO,
    EventDTO,
    StructureBriefDTO,
    TradabilityDTO,
    TradeOpportunityDTO,
)
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.storage.sqlite_store import connect

# ---- 构造测试用 AssessmentDTO 的轻量替身 ----

@dataclass
class _Assessment:
    conditional_scenarios: list[Any] = field(default_factory=list)
    trade_opportunities: list[Any] = field(default_factory=list)
    pullback_opportunities: list[Any] = field(default_factory=list)
    tradability: Any = None
    as_of: str = "2026-08-05"


def _tradability(tradable: bool, reasons: list[str] | None = None) -> TradabilityDTO:
    return TradabilityDTO(
        trend_type="trending", trend_type_cn="趋势", tradable=tradable,
        blocking_reasons=reasons or [], condition_checks=[], research_proxy=True,
        caveat_cn="",
    )


def _scenario(
    *, state: str = "confirmed", rule_id: str = "dense_breakout",
    key_price: float = 3820.0, missing: list[str] | None = None,
    satisfied: list[str] | None = None, rr: float | None = 3.5,
    computable: bool = True, invalidation_cn: str = "跌回密集区且 SMA20 下弯",
) -> ConditionalScenarioDTO:
    return ConditionalScenarioDTO(
        scenario_id=rule_id, scenario_cn="均线密集区突破", direction="long",
        direction_cn="潜在做多", state=state,
        state_cn={"confirmed": "确认", "watch": "观察"}.get(state, state),
        anchor_date="2026-08-01", trigger_date="2026-08-05" if state == "confirmed" else None,
        latest_date="2026-08-05", key_price=key_price, reference_price=key_price,
        distance_pct=1.2, current_conditions_confirmed=(state == "confirmed"),
        satisfied_conditions=satisfied or ["收盘突破密集区上沿", "完整多头排列成立"],
        missing_conditions=missing or [],
        next_step_cn="下一根开盘可执行", invalidation_cn=invalidation_cn,
        caveat_cn="研究代理", research_proxy=True,
        explanation=None,
        supporting_event=EventDTO(
            event_id="e1", rule_id=rule_id, rule_cn="密集区突破", sub_rule=None,
            sub_rule_cn=None, direction="bullish", direction_cn="看多", severity="important",
            severity_cn="重要", reason_cn="", event_date="2026-08-05",
            available_date="2026-08-05", lifecycle_id="lc1", evidence={},
            research_proxy=True, explanation=None,
        ) if state == "confirmed" else None,
        reward_risk_ratio=rr, reward_risk_target=4200.0,
        reward_risk_target_source_cn="摆动高点", reward_risk_computable=computable,
    )


def _review(assessment: _Assessment, **kw: Any):
    return _review_from_assessment(
        assessment, last_close=3850.0, symbol="000001.SS", display_name="上证",
        active_plan_ids=(), **kw,
    )


# ---- verdict 四态 ----

def test_verdict_actionable_when_confirmed_and_tradable() -> None:
    a = _Assessment(
        conditional_scenarios=[_scenario(state="confirmed")],
        tradability=_tradability(True),
    )
    r = _review(a)
    assert r.verdict == VERDICT_ACTIONABLE
    assert r.suggested_plan is not None
    assert r.suggested_plan.entry_rule_id == "dense_breakout"
    assert r.suggested_plan.invalidation_price is None  # 场景卡只给文案不给价
    assert r.suggested_plan.reward_risk_at_plan == 3.5
    assert r.watch_conditions == []


def test_verdict_blocked_when_candidates_but_not_tradable() -> None:
    a = _Assessment(
        conditional_scenarios=[_scenario(state="confirmed")],
        tradability=_tradability(False, reasons=["横盘不频繁交易"]),
    )
    r = _review(a)
    assert r.verdict == VERDICT_BLOCKED
    assert r.suggested_plan is None  # 阻断时不给建计划预填
    assert "横盘不频繁交易" in r.summary_cn


def test_verdict_waiting_when_only_watch_candidates() -> None:
    a = _Assessment(
        conditional_scenarios=[_scenario(
            state="watch", missing=["收盘突破密集区上沿 3820"],
            satisfied=[],
        )],
        tradability=_tradability(True),
    )
    r = _review(a)
    assert r.verdict == VERDICT_WAITING
    assert r.suggested_plan is None
    assert len(r.watch_conditions) == 1
    wc = r.watch_conditions[0]
    assert wc.kind == "price"
    assert wc.price == 3820.0


def test_verdict_none_when_no_candidates() -> None:
    a = _Assessment(tradability=_tradability(True))
    r = _review(a)
    assert r.verdict == VERDICT_NONE
    assert r.candidates == []
    assert r.suggested_plan is None


def test_invalidated_candidates_excluded() -> None:
    a = _Assessment(
        conditional_scenarios=[_scenario(state="invalidated")],
        tradability=_tradability(True),
    )
    r = _review(a)
    assert r.verdict == VERDICT_NONE  # 已失效的不算候选


# ---- watch_conditions 价位型 vs 状态型 ----

def test_state_condition_has_no_price() -> None:
    """缺「完整多头排列未成立」这类条件没有单一价位，不贴数字。"""
    a = _Assessment(
        conditional_scenarios=[_scenario(
            state="watch", missing=["完整多头排列未成立"], satisfied=[],
        )],
        tradability=_tradability(True),
    )
    r = _review(a)
    assert r.verdict == VERDICT_WAITING
    wc = r.watch_conditions[0]
    assert wc.kind == "state"
    assert wc.price is None
    assert wc.as_signal_rule_ids == ["ma_full_alignment"]  # 可跟踪化建议


def test_price_condition_carries_key_price() -> None:
    a = _Assessment(
        conditional_scenarios=[_scenario(
            state="watch", missing=["收盘站上 EMA20"], satisfied=[],
            key_price=3810.0,
        )],
        tradability=_tradability(True),
    )
    r = _review(a)
    wc = r.watch_conditions[0]
    assert wc.kind == "price"
    assert wc.price == 3810.0
    assert wc.as_signal_rule_ids == ["ema20_reclaim_rising"]


# ---- 盈亏比不可计算时不编数值 ----

def test_rr_not_computable_kept_honest() -> None:
    a = _Assessment(
        conditional_scenarios=[_scenario(rr=None, computable=False)],
        tradability=_tradability(True),
    )
    r = _review(a)
    assert r.verdict == VERDICT_ACTIONABLE
    assert r.candidates[0].reward_risk_computable is False
    assert r.candidates[0].reward_risk_ratio is None
    assert r.suggested_plan.reward_risk_at_plan is None  # 照抄 None，不编


# ---- 结构机会的失效价取 C 点 ----

def test_opportunity_invalidation_from_structure_c() -> None:
    structure = StructureBriefDTO(
        structure_id="s1", structure_type="higher_low_bottom",
        structure_type_cn="更高低点底部", side="bottom", status="confirmed",
        status_cn="确认", c_price=3650.0, neckline=3900.0,
        detected_date="2026-07-01", confirmed_date="2026-07-10",
        invalidated_date=None, invalidated_reason=None,
        distance_to_c_pct=-5.0, explanation=None,
    )
    opp = TradeOpportunityDTO(
        direction="long", direction_cn="潜在做多", state="confirmed", state_cn="确认",
        structure=structure, lifecycle_id="lc2", reached_tier="tier2",
        reached_tier_cn="第二档", reached_tier_rank=2, opened_on="2026-07-10",
        last_upgraded_on="2026-08-01", is_buy_reference=True, is_active=True,
        current_conditions_confirmed=True, satisfied_conditions=["结构确认"],
        missing_conditions=[], next_step_cn="可参考", invalidation_cn="跌破 C 点",
        b1_price=4200.0, distance_to_b1_pct=8.0, explanation=None,
        supporting_event=None, reward_risk_ratio=4.0, reward_risk_target=4200.0,
        reward_risk_target_source_cn="B1", reward_risk_computable=True,
    )
    a = _Assessment(trade_opportunities=[opp], tradability=_tradability(True))
    r = _review(a)
    assert r.verdict == VERDICT_ACTIONABLE
    cand = r.candidates[0]
    assert cand.invalidation_price == 3650.0  # 结构 C 点，系统已确认


# ---- has_active_plan ----

def test_has_active_plan_flagged(tmp_path) -> None:  # noqa: ANN001
    from lei_signal.plans.store import confirm_plan, create_plan

    db = str(tmp_path / "bp.db")
    conn = connect(db)
    p = create_plan(
        conn, symbol="000001.SS", module="A", direction="long",
        ruleset_version="1.3.0", reason="测试", valid_until="2026-12-31",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="回撤", entry_price_ref=3800.0, invalidation_price=3650.0,
        target_b_price=4200.0, target_b_source="swing_high", reward_risk_at_plan=3.0,
        thesis_cn="假设", invalidation_criteria_cn="跌破", drawdown_playbook_cn="回踩",
        take_profit_plan_cn="分批", stop_plan_cn="结构止损",
    )
    confirm_plan(conn, p.plan_id)
    conn.close()

    a = _Assessment(
        conditional_scenarios=[_scenario(state="confirmed")],
        tradability=_tradability(True),
    )
    from lei_signal.api.routes.opportunities import _active_plan_ids
    r = _review_from_assessment(
        a, last_close=3850.0, symbol="000001.SS", display_name="上证",
        active_plan_ids=_active_plan_ids(db, "000001.SS"),
    )
    assert r.has_active_plan is True
    assert len(r.active_plan_ids) == 1


# ---- HTTP 端点：无分析结果时 502 ----

def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
                     "close": close, "volume": 1_000_000})
    df = pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=n))
    return df[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info))


def _client(tmp_path, monkeypatch):
    db = str(tmp_path / "bp_http.db")
    svc = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=svc)
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    return TestClient(app), db


def test_review_endpoint_returns_none_for_steady_trend(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """单边上涨无结构 -> verdict=none（Python 已判，端点只汇总）。"""
    client, _ = _client(tmp_path, monkeypatch)
    r = client.get("/api/symbols/000001.SS/buy-point-review")
    assert r.status_code == 200
    b = r.json()
    assert b["verdict"] == VERDICT_NONE
    assert b["candidates"] == []
    assert "研究代理" in b["disclaimer_cn"] or "判定" in b["disclaimer_cn"]


def test_scan_endpoint_isolates_per_symbol_errors(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """单标的失败不影响整体：BROKEN.SS 报错，正常标的仍返回。"""
    def analyze(symbol: str, **kwargs):
        if symbol == "BROKEN.SS":
            from lei_signal.data.validation import DataUnavailableError
            raise DataUnavailableError("网络中断")
        return _fake_analyze(symbol, **kwargs)
    db = str(tmp_path / "bp_scan.db")
    svc = AnalysisService(analyze_fn=analyze, sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=svc)
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    client = TestClient(app)
    r = client.get("/api/opportunities/scan?symbols=000001.SS,BROKEN.SS&only_with_candidates=false")
    assert r.status_code == 200
    body = r.json()
    assert body["scanned"] == 2
    by_sym = {i["symbol"]: i for i in body["items"]}
    assert by_sym["000001.SS"]["error"] is None
    assert by_sym["BROKEN.SS"]["error"] is not None


def test_scan_only_with_candidates_filters_none(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client, _ = _client(tmp_path, monkeypatch)
    r = client.get("/api/opportunities/scan?symbols=000001.SS&only_with_candidates=true")
    assert r.status_code == 200
    # 单边上涨无机会 -> 被 only_with_candidates 过滤掉
    assert r.json()["items"] == []
    # 关闭过滤则返回 none 项
    r2 = client.get("/api/opportunities/scan?symbols=000001.SS&only_with_candidates=false")
    assert len(r2.json()["items"]) == 1
