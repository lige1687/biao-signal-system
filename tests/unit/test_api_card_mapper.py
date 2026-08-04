"""card_mapper 纯函数测试：颜色天数、关键变化回退链、C 点距离、事件标签。"""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from lei_signal.api import labels
from lei_signal.api.card_mapper import (
    build_card,
    color_duration,
    event_dto,
    key_change,
    structure_brief,
)
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.domain.types import (
    Direction,
    Severity,
    SignalEvent,
    StructureInstance,
    StructureStatus,
)


def _bars(rows: list[dict[str, float]], start: str = "2024-01-02") -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=len(rows))
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _uptrend_bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    return _bars(rows)


def _analyzed(symbol: str = "TEST", bars: pd.DataFrame | None = None):
    bars = bars if bars is not None else _uptrend_bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol("QQQ")  # 任意合法 SymbolInfo，提供 timezone
    price_data = PriceData(
        symbol=symbol, display_name=symbol, bars=frame, report=report, info=info
    )
    return analyze_bars(symbol, frame, price_data=price_data)


def _frame_with_colors(colors: list[str]) -> SimpleNamespace:
    index = pd.bdate_range(start="2024-01-02", periods=len(colors))
    frame = pd.DataFrame({"signal_color": colors}, index=index)
    return SimpleNamespace(frame=frame)


def test_color_duration_counts_trailing_run() -> None:
    result = _frame_with_colors(["black", "gray", "gray", "green", "green", "green"])
    since, days = color_duration(result)
    assert days == 3
    assert since == "2024-01-05"  # bdate 序列：01-02,03,04,05(五),08(一),09(二)


def test_color_duration_single_bar() -> None:
    since, days = color_duration(_frame_with_colors(["unknown"]))
    assert days == 1
    assert since == "2024-01-02"


def _make_event(
    rule_id: str,
    severity: Severity,
    available: date,
    reason: str,
    sub_rule: str | None = None,
) -> SignalEvent:
    return SignalEvent(
        event_id=f"{rule_id}-{available.isoformat()}",
        symbol="TEST",
        timeframe="1d",
        event_date=available,
        available_date=available,
        rule_id=rule_id,
        rule_version="v1",
        direction=Direction.BULLISH,
        severity=severity,
        strength=1,
        reason_cn=reason,
        provenance="lei_explicit",  # type: ignore[arg-type]
        evidence={"sub_rule": sub_rule} if sub_rule else {},
    )


def _key_change_result(
    *,
    stage_change: str = "",
    new_events: list[SignalEvent] | None = None,
    events: list[SignalEvent] | None = None,
) -> SimpleNamespace:
    last = pd.Timestamp("2024-06-28")
    return SimpleNamespace(
        assessment=SimpleNamespace(
            stage_change_reason_cn=stage_change,
            as_of=date(2024, 6, 28),
            new_events=new_events or [],
        ),
        events=events or [],
        price_data=SimpleNamespace(report=SimpleNamespace(last_date=last)),
    )


def test_key_change_prefers_stage_change_reason() -> None:
    result = _key_change_result(
        stage_change="阶段由「底部观察」升级为「结构确认」",
        new_events=[_make_event("lei_color", Severity.CRITICAL, date(2024, 6, 28), "转绿")],
    )
    text, day = key_change(result)
    assert text == "阶段由「底部观察」升级为「结构确认」"
    assert day == "2024-06-28"


def test_key_change_falls_back_to_highest_severity_new_event() -> None:
    low = _make_event("volume_proxies", Severity.WATCH, date(2024, 6, 28), "量能一般")
    high = _make_event("lei_color", Severity.IMPORTANT, date(2024, 6, 28), "转灰")
    text, _ = key_change(_key_change_result(new_events=[low, high]))
    assert text == "转灰"


def test_key_change_falls_back_to_recent_important_event() -> None:
    old = _make_event("lei_color", Severity.IMPORTANT, date(2024, 6, 20), "8天前转灰")
    older = _make_event("double_bottom", Severity.CRITICAL, date(2024, 6, 10), "双底确认")
    text, day = key_change(_key_change_result(events=[older, old]))
    assert text == "8天前转灰"
    assert day == "2024-06-20"


def test_key_change_ignores_low_severity_and_returns_none() -> None:
    info_only = [_make_event("swing_pivots", Severity.INFO, date(2024, 6, 20), "摆动点")]
    text, day = key_change(_key_change_result(events=info_only))
    assert text is None
    assert day is None


def test_structure_brief_distance_only_for_live_bottom() -> None:
    bottom = StructureInstance(
        structure_id="s1",
        symbol="TEST",
        structure_type="higher_low_bottom",
        side="bottom",
        detected_date=date(2024, 5, 1),
        c_price=90.0,
        status=StructureStatus.CONFIRMED,
        confirmed_date=date(2024, 5, 10),
    )
    dto = structure_brief(bottom, close=100.0)
    assert dto.distance_to_c_pct == pytest.approx(10.0)
    assert dto.structure_type_cn == "更高低点底部"
    assert dto.status_cn == "已确认"

    invalidated = StructureInstance(
        structure_id="s2",
        symbol="TEST",
        structure_type="double_bottom",
        side="bottom",
        detected_date=date(2024, 5, 1),
        c_price=90.0,
        status=StructureStatus.INVALIDATED,
        invalidated_date=date(2024, 6, 1),
    )
    assert structure_brief(invalidated, close=100.0).distance_to_c_pct is None

    top = StructureInstance(
        structure_id="s3",
        symbol="TEST",
        structure_type="top_structure",
        side="top",
        detected_date=date(2024, 5, 1),
        neckline=110.0,
        status=StructureStatus.ACTIVE,
    )
    assert structure_brief(top, close=100.0).distance_to_c_pct is None


def test_event_dto_labels_early_watch_neutral() -> None:
    event = _make_event(
        "ema20_reclaim_rising",
        Severity.WATCH,
        date(2024, 6, 28),
        "EMA20 早期转强",
        sub_rule="ema20_reclaim_rising_early_watch",
    )
    dto = event_dto(event, as_of=date(2024, 6, 28))
    # early_watch 必须是中性的「候选观察」，不得出现任何买入措辞
    assert dto.sub_rule_cn == "候选观察"
    assert "买" not in dto.sub_rule_cn
    assert dto.is_new_today is True
    assert dto.rule_cn == "EMA20 早期转强"


def test_build_card_full_success() -> None:
    result = _analyzed()
    card = build_card(
        symbol="TEST",
        display_name="测试标的",
        market_cn="美股",
        group="watchlist",
        result=result,
        error=None,
        data_time=datetime(2024, 6, 28, 14, 30),
    )
    assert card.error is None
    assert card.price == pytest.approx(float(result.frame["close"].iloc[-1]))
    assert card.change_pct is not None and card.change_pct > 0
    assert card.color in ("green", "gray", "black", "unknown")
    assert card.color_cn == {"green": "绿色", "gray": "灰色",
                             "black": "黑色", "unknown": "数据不足"}[card.color]
    assert card.color_days is not None and card.color_days >= 1
    assert card.stage_cn is not None
    assert card.risk_state_cn in labels.RISK_STATE_CN.values()
    assert len(card.sparkline) == 60
    assert card.sparkline[-1].close == pytest.approx(card.price, abs=1e-4)


def test_build_card_error_degrades() -> None:
    card = build_card(
        symbol="BROKEN",
        display_name="BROKEN",
        market_cn="",
        group="index",
        result=None,
        error="网络不通：连接中断",
        data_time=datetime(2024, 6, 28, 14, 30),
    )
    assert card.error == "网络不通：连接中断"
    assert card.price is None
    assert card.color is None
    assert card.sparkline == []


def test_explanations_cover_all_rule_ids_and_structures() -> None:
    """标签表里的每个 rule_id / 结构类型都必须有解释条目。

    否则用户点开图上标记会看到空面板——这是「解释系统」的核心承诺。
    """
    from lei_signal.api import explanations, labels

    # 结构类型：STRUCTURE_TYPE_CN 是展示用标签表，二者必须同步
    missing_structs = set(labels.STRUCTURE_TYPE_CN) - set(explanations.STRUCTURES)
    assert not missing_structs, f"结构类型缺解释：{missing_structs}"

    # 规则：RULE_CN 中每条都必须能通过 lookup 查到解释（lei_color 走 sub_rule）。
    # 用 lookup 而非直查 RULES，因为结构类事件落 STRUCTURES、
    # ema20_reclaim_rising 无档位时回退到概念——这些都是合法路径。
    exempt = {"lei_color"}
    unresolvable = {
        rule for rule in set(labels.RULE_CN) - exempt
        if explanations.lookup(rule_id=rule) is None
    }
    assert not unresolvable, f"规则无法解析出解释：{unresolvable}"

    # sub_rule 标签表同样要全覆盖
    missing_subs = set(labels.SUB_RULE_CN) - set(explanations.RULES)
    assert not missing_subs, f"子规则缺解释：{missing_subs}"

    # 每条解释必须至少有 definition + usage（「是什么 + 怎么用」）
    for name, table in (
        ("CONCEPTS", explanations.CONCEPTS),
        ("STRUCTURES", explanations.STRUCTURES),
        ("RULES", explanations.RULES),
    ):
        for key, exp in table.items():
            assert exp.get("title"), f"{name}[{key}] 缺 title"
            assert exp.get("definition"), f"{name}[{key}] 缺 definition"
            assert exp.get("usage"), f"{name}[{key}] 缺 usage"


def test_early_watch_explanation_is_neutral() -> None:
    """early_watch 的解释必须明确「不构成买入」，不得出现诱导性表述。"""
    from lei_signal.api.explanations import lookup

    exp = lookup(sub_rule="ema20_reclaim_rising_early_watch")
    assert exp is not None
    assert "不构成买入" in exp["usage"]


def test_structure_and_event_dto_carry_explanation() -> None:
    """结构与事件 DTO 必须自带解释，前端点击即可展示，无需二次请求。"""
    bottom = StructureInstance(
        structure_id="s1",
        symbol="TEST",
        structure_type="higher_low_bottom",
        side="bottom",
        detected_date=date(2024, 5, 1),
        c_price=90.0,
        status=StructureStatus.CONFIRMED,
    )
    dto = structure_brief(bottom, close=100.0)
    assert dto.explanation is not None
    assert dto.explanation.title == "更高低点底部"
    assert "C 点" in dto.explanation.invalidation

    event = _make_event(
        "lei_color",
        Severity.IMPORTANT,
        date(2024, 6, 28),
        "颜色转黑",
        sub_rule="lei_color_black_started",
    )
    edto = event_dto(event, as_of=date(2024, 6, 28))
    assert edto.explanation is not None
    assert edto.explanation.title == "转黑（关键性波动）"
    # 转黑不销毁结构，这个口径必须在解释里说清
    assert "不会" in edto.explanation.usage


def test_quote_provider_parses_and_degrades() -> None:
    """盘口解析：字段映射正确；非 A 股与异常一律 None（不编数据）。"""
    from lei_signal.api.quotes import TencentQuoteProvider

    # 真实响应形状（88 字段，~ 分隔），此处截取到量比后即可
    fields = ["v_sh000300=\"1", "沪深300", "000300", "4543.18", "4588.20", "4561.82"]
    fields += ["0"] * (31 - len(fields))
    fields.append("-45.02")  # 31 涨跌额
    fields.append("-0.98")  # 32 涨跌幅
    fields += ["0"] * (37 - len(fields))
    fields.append("61575095")  # 37 成交额（万）
    fields.append("0.69")  # 38 换手率
    fields += ["0"] * (44 - len(fields))
    fields.append("516568.72")  # 44 流通市值
    fields.append("544760.92")  # 45 总市值
    fields += ["0"] * (49 - len(fields))
    fields.append("0.95")  # 49 量比
    payload = "~".join(fields)

    provider = TencentQuoteProvider(opener=lambda _url: payload)
    quote = provider.fetch("000300.SS")
    assert quote is not None
    assert quote.display_name == "沪深300"
    assert quote.price == pytest.approx(4543.18)
    assert quote.change_pct == pytest.approx(-0.98)
    assert quote.turnover_rate == pytest.approx(0.69)
    assert quote.volume_ratio == pytest.approx(0.95)
    assert quote.float_cap_yi == pytest.approx(516568.72)

    # 非 A 股：源不覆盖，返回 None 而不是猜
    assert provider.fetch("^IXIC") is None
    assert provider.fetch("QQQ") is None

    # 响应过短 / 网络异常 → None，不抛
    assert TencentQuoteProvider(opener=lambda _u: "short~payload").fetch("000300.SS") is None

    def boom(_url: str) -> str:
        raise OSError("connection reset")

    assert TencentQuoteProvider(opener=boom).fetch("000300.SS") is None

    # 腾讯用 '-1' 表示不适用，必须转成 None 而非 -1
    idx38 = fields.copy()
    idx38[38] = "-1"
    q2 = TencentQuoteProvider(opener=lambda _u: "~".join(idx38)).fetch("000300.SS")
    assert q2 is not None and q2.turnover_rate is None


def test_today_overview_volume_tiers() -> None:
    """量能分级阈值：≥2×放量，1.2-2×温和，0.8-1.2×正常，<0.8×缩量。"""
    from lei_signal.api.overview import _classify_volume

    assert _classify_volume(2.5)[0] == "放量"
    assert _classify_volume(2.0)[0] == "放量"
    assert _classify_volume(1.5)[0] == "温和放量"
    assert _classify_volume(1.0)[0] == "正常"
    assert _classify_volume(0.5)[0] == "缩量"


def test_today_overview_without_quote_marks_unavailable() -> None:
    """无盘口数据时：quote_available=False，换手率/量比为 None 且有说明。"""
    from lei_signal.api.overview import build_today_overview

    result = _analyzed()
    ov = build_today_overview(result, quote=None)
    assert ov.quote_available is False
    assert ov.quote_note_cn
    vol = {m.key: m for m in ov.volume}
    assert vol["turnover_rate"].value is None
    assert vol["volume_ratio"].value is None
    assert ov.capital == [], "无盘口时不应编造市值指标"
    # 但量能倍数来自日线，应该有值
    assert vol["vol_ratio20"].value is not None
