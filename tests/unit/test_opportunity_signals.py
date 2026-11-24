"""Technical signal rows keep event age and lifecycle separate from current risk."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace as NS

import pandas as pd
import pytest

from lei_signal.api.opportunity_signals import build_signal_rows


def _result():
    frame = pd.DataFrame(
        {"close": [10.0] * 8, "ema20": [10.5] * 7 + [9.5], "close_lag20": [10.8] * 7 + [9.8]},
        index=pd.bdate_range("2026-08-12", periods=8),
    )
    return NS(frame=frame, events=[], structures=[])


def _review():
    return NS(candidates=[], resonance_groups=[], historical_structures=[])


def test_buy_signal_has_exact_event_date_and_bar_age() -> None:
    result = _result()
    day = result.frame.index[-2].date().isoformat()
    review = _review()
    review.candidates = [
        NS(
            lifecycle_id="life-1",
            rule_id="dense_breakout",
            scenario_id="dense",
            scenario_cn="均线密集区突破",
            state_cn="条件成立",
            state="confirmed",
            last_state_change_date=day,
            opened_date=result.frame.index[0].date().isoformat(),
            satisfied_conditions=["突破参考位"],
            missing_conditions=[],
            key_price=10.2,
            invalidation_price=9.1,
            invalidation_cn="跌回密集区",
            next_step_cn="观察下一根日 K",
            research_proxy=True,
        )
    ]
    signal = build_signal_rows(result, review)[0]
    assert signal["event_date"] == day
    assert signal["state_changed_date"] == day
    assert signal["age_bars"] == 1 and signal["is_recent"] is True
    assert signal["status"] == "active"
    assert signal["key_prices"] == [
        {"label": "关键价", "value": 10.2},
        {"label": "失效价", "value": 9.1},
    ]


def test_old_buy_structure_is_history_not_current_opportunity() -> None:
    result = _result()
    review = _review()
    old = result.frame.index[0].date().isoformat()
    review.historical_structures = [
        NS(
            lifecycle_id="old",
            rule_id="bottom_structure",
            state="confirmed",
            state_cn="已确认",
            scenario_cn="底部结构",
            opened_date=old,
            last_state_change_date=old,
            key_price=9.2,
            note="历史结构",
        )
    ]
    signal = build_signal_rows(result, review)[0]
    assert signal["age_bars"] == 7 and signal["is_recent"] is False
    assert signal["event_date"] == old


def test_cleared_top_preserves_confirmation_and_clearing_dates() -> None:
    result = _result()
    confirmed = result.frame.index[-3].date()
    cleared = result.frame.index[-1].date()
    result.structures = [
        NS(
            side="top",
            status="invalidated",
            detected_date=result.frame.index[-4].date(),
            confirmed_date=confirmed,
            invalidated_date=cleared,
            structure_id="top-1",
            neckline=10.5,
            reference_high=12.0,
            provenance="lei_explicit",
        )
    ]
    signal = build_signal_rows(result, _review())[0]
    assert signal["event_date"] == confirmed.isoformat()
    assert signal["state_changed_date"] == cleared.isoformat()
    assert signal["age_bars"] == 2 and signal["state_age_bars"] == 0
    assert signal["status"] == "cleared" and signal["is_recent"] is False
    assert signal["conditions"][0] == "顶部候选开始观察：2026-08-18"
    assert signal["key_prices"] == [
        {"label": "此前回落低点", "value": 10.5},
        {"label": "前高（解除预警参考）", "value": 12.0},
    ]


def test_current_top_uses_exact_confirmation_reason_and_concrete_next_step() -> None:
    result = _result()
    confirmed = result.frame.index[-1].date()
    detected = result.frame.index[-2].date()
    result.structures = [
        NS(
            side="top",
            status="confirmed",
            structure_id="top-1",
            detected_date=detected,
            confirmed_date=confirmed,
            invalidated_date=None,
            neckline=10.5,
            reference_high=12.0,
            provenance="lei_explicit",
        )
    ]
    result.events = [
        NS(
            rule_id="top_structure",
            structure_id="top-1",
            evidence={"sub_rule": "top_structure_confirmed"},
            reason_cn="顶部警报确认：收盘跌破此前回落低点10.5000。仅为风险提示。",
        )
    ]
    signal = build_signal_rows(result, _review())[0]
    assert signal["event_date"] == confirmed.isoformat()
    assert signal["conditions"][0] == f"顶部候选开始观察：{detected.isoformat()}"
    assert "第二高点低于前高" in signal["conditions"]
    assert "确认日收盘跌破此前回落低点 10.5000" in signal["conditions"]
    assert "顶部警报确认" in signal["summary"]
    assert signal["invalidation_cn"] == "最高价突破前高 12.0000 时解除预警"
    assert "单独顶部预警不构成卖出结论" in signal["next_step_cn"]


def test_ended_and_reopened_wave_have_distinct_lifecycles() -> None:
    result = _result()
    days = [ts.date() for ts in result.frame.index[-3:]]

    def event(identity, day, sub):
        return NS(
            event_id=identity,
            rule_id="key_wave_black",
            available_date=day,
            reason_cn=sub,
            evidence={"sub_rule": sub},
            provenance="lei_inferred",
            lifecycle_id=identity,
        )

    result.events = [
        event("first", days[0], "key_wave_black_started"),
        event("end", days[1], "key_wave_black_ended"),
        event("again", days[2], "key_wave_black_started"),
    ]
    signals = [
        row for row in build_signal_rows(result, _review()) if row["rule_id"] == "key_wave_black"
    ]
    assert len(signals) == 2
    assert {row["status"] for row in signals} == {"cleared", "new"}


def test_recovered_exit_event_keeps_original_date_only_as_history() -> None:
    result = _result()
    day = result.frame.index[-2].date()
    result.events = [
        NS(
            event_id="exit",
            rule_id="exit_ema20_costbasis",
            available_date=day,
            reason_cn="退出条件触发",
            evidence={"ema20": 10.5},
        )
    ]
    signal = build_signal_rows(result, _review())[0]
    assert signal["event_date"] == day.isoformat()
    assert signal["status"] == "cleared" and signal["is_recent"] is False


def test_today_watch_candidate_stays_waiting() -> None:
    result = _result()
    review = _review()
    today = result.frame.index[-1].date().isoformat()
    review.candidates = [
        NS(
            lifecycle_id="watch",
            rule_id="dense_breakout",
            scenario_id="dense",
            scenario_cn="均线密集区观察",
            state_cn="观察中",
            state="watch",
            last_state_change_date=today,
            opened_date=today,
            satisfied_conditions=[],
            missing_conditions=["等待突破"],
            key_price=None,
            invalidation_price=None,
            invalidation_cn="",
            next_step_cn="观察",
            research_proxy=True,
        )
    ]
    signal = build_signal_rows(result, review)[0]
    assert signal["age_bars"] == 0 and signal["status"] == "waiting"
    review.resonance_groups = [NS(candidates=review.candidates)]
    assert len(build_signal_rows(result, review)) == 1


def test_freshness_marks_old_bar_stale_even_if_fetched_today() -> None:
    from zoneinfo import ZoneInfo

    from lei_signal.api.routes.opportunity_reviews import _technical_freshness

    now = datetime(2026, 8, 24, 16, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    state, reason = _technical_freshness(
        symbol="510300.SS",
        last_bar=pd.Timestamp("2026-08-21").date(),
        timezone="Asia/Shanghai",
        bar_status="closed",
        now=now,
    )
    assert state == "stale" and "2026-08-24" in reason


def test_freshness_distinguishes_intraday_and_unknown_provenance() -> None:
    from zoneinfo import ZoneInfo

    from lei_signal.api.routes.opportunity_reviews import _technical_freshness

    now = datetime(2026, 8, 24, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    current, _ = _technical_freshness(
        symbol="510300.SS",
        last_bar=now.date(),
        timezone="Asia/Shanghai",
        bar_status="intraday",
        now=now,
    )
    unknown, _ = _technical_freshness(
        symbol="510300.SS",
        last_bar=now.date(),
        timezone="Asia/Shanghai",
        bar_status="unknown",
        now=now,
    )
    assert current == "current" and unknown == "unknown"


def test_endpoint_uses_one_exact_analysis_result_for_chart_and_signals(monkeypatch) -> None:
    from starlette.requests import Request

    from lei_signal.api.routes import opportunities, symbols
    from lei_signal.api.routes import opportunity_reviews as route
    from lei_signal.ui import echarts_kline

    result = _result()
    result.symbol = "510300.SS"
    result.display_name = "沪深300ETF"
    result.weekly_trend = pd.DataFrame()
    result.cache_fallback_used = False
    result.price_data = NS(
        report=NS(last_date=result.frame.index[-1], provider="test", adjusted=True),
        info=NS(timezone="Asia/Shanghai"),
    )
    seen = []

    def assessment(value):
        seen.append(value)
        return NS(
            as_of=result.frame.index[-1].date().isoformat(),
            color="green",
            color_cn="绿色",
            stage_cn="趋势增强",
        )

    def review(value, *, symbol, display_name):
        seen.append(value)
        return _review()

    def chart(value, **kwargs):
        seen.append(value)
        return {"dates": [ts.date().isoformat() for ts in value.frame.index]}

    monkeypatch.setattr(symbols, "_assessment_dto", assessment)
    monkeypatch.setattr(opportunities, "build_review", review)
    monkeypatch.setattr(echarts_kline, "serialize_result", chart)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 21, 6, 30, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(route, "datetime", FixedDatetime)
    fetched = datetime(2026, 8, 21, 6, 0, tzinfo=UTC)
    service = NS(get=lambda symbol: NS(result=result, error=None, fetched_at=fetched))
    app = NS(state=NS(analysis_service=service))
    request = Request({"type": "http", "app": app})
    response = route.technical_signals(request, result.symbol)
    assert seen == [result, result, result]
    assert response["chart"]["dates"][-1] == response["as_of"]
    assert response["meta"]["bar_status"] == "intraday"
    assert response["meta"]["is_intraday_forming"] is True
    assert response["meta"]["freshness"] == "current"
    assert response["signals"] == []
    result.cache_fallback_used = True
    unknown = route.technical_signals(request, result.symbol)
    assert unknown["meta"]["bar_status"] == "unknown"
    assert unknown["meta"]["freshness"] == "unknown"
    result.cache_fallback_used = False
    result.price_data.report.last_date = result.frame.index[-2]
    mismatch = route.technical_signals(request, result.symbol)
    assert mismatch["meta"]["freshness"] == "unknown"
    assert "图表" in mismatch["meta"]["freshness_reason"]


def test_endpoint_rejects_a_different_product_snapshot() -> None:
    from fastapi import HTTPException
    from starlette.requests import Request

    from lei_signal.api.routes.opportunity_reviews import technical_signals

    entry = NS(result=NS(symbol="510500.SS"), error=None)
    request = Request(
        {"type": "http", "app": NS(state=NS(analysis_service=NS(get=lambda symbol: entry)))}
    )
    with pytest.raises(HTTPException) as error:
        technical_signals(request, "510300.SS")
    assert error.value.status_code == 502
