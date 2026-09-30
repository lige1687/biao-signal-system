"""Bar 完成度三态契约测试（W2-S1，2026-09-20）。

契约文档：docs/ops/bar-completeness-contract.md。
覆盖：
- G4 A股 final 判定纯函数（收盘时间/日历注入、三态各分支）；
- G3 生产信号路径契约：partial/unknown 最后一根 bar 必须被拒绝
  （PartialBarError，含明细），不得静默当 final；
- G3 研究路径契约：partial 显式放行且带完成度标注；
- 处置语义经生产 signal_scan 调用契约验证：守卫在进入 run_signal_scan
  之前拦截 partial 数据（本阶段不改 run_signal_scan 本体，接线属后续
  阶段——契约以「必须先过守卫」的形式钉死）。
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from lei_signal.data.bar_completeness import (
    FINAL,
    PARTIAL,
    UNKNOWN,
    PartialBarError,
    annotate_bars,
    classify_a_share_bar,
    require_final_for_production,
    research_view,
)
from lei_signal.data.calendar import WeekdayCalendar

CN = ZoneInfo("Asia/Shanghai")
HOLIDAY = dt.date(2024, 10, 7)  # 国庆假期内非交易日
CAL = WeekdayCalendar(holidays=frozenset({HOLIDAY}))


def _frame(dates: list[str]) -> pd.DataFrame:
    idx = pd.DatetimeIndex(pd.Timestamp(d) for d in dates)
    return pd.DataFrame(
        {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100},
        index=idx,
    )


# ---------- G4：A股 final 判定纯函数 ----------


def test_final_after_close_same_day() -> None:
    """交易日当天 15:00 及以后观测 -> final。"""
    assert classify_a_share_bar(
        dt.date(2024, 10, 8), dt.datetime(2024, 10, 8, 15, 0, tzinfo=CN), calendar=CAL,
    ) == FINAL
    assert classify_a_share_bar(
        dt.date(2024, 10, 8), dt.datetime(2024, 10, 8, 16, 30, tzinfo=CN), calendar=CAL,
    ) == FINAL


def test_partial_intraday_same_day() -> None:
    """交易日当天盘中观测 -> partial。"""
    assert classify_a_share_bar(
        dt.date(2024, 10, 8), dt.datetime(2024, 10, 8, 14, 59, tzinfo=CN), calendar=CAL,
    ) == PARTIAL


def test_final_next_day_even_if_holiday_follows() -> None:
    """节前最后一个交易日的 bar，次交易日（含跨节假日）观测 -> final。"""
    assert classify_a_share_bar(
        dt.date(2024, 9, 30), dt.datetime(2024, 10, 8, 9, 30, tzinfo=CN), calendar=CAL,
    ) == FINAL


def test_unknown_when_not_trading_day() -> None:
    """日历不认的日期（周末/注入节假日）-> unknown（保守不判定）。"""
    assert classify_a_share_bar(
        dt.date(2024, 10, 7), dt.datetime(2024, 10, 8, 16, 0, tzinfo=CN), calendar=CAL,
    ) == UNKNOWN
    assert classify_a_share_bar(
        dt.date(2024, 10, 5), dt.datetime(2024, 10, 8, 16, 0, tzinfo=CN), calendar=CAL,
    ) == UNKNOWN


def test_unknown_when_observed_before_bar_date() -> None:
    """观测时刻早于 bar 日期（数据异常）-> unknown。"""
    assert classify_a_share_bar(
        dt.date(2024, 10, 8), dt.datetime(2024, 10, 7, 16, 0, tzinfo=CN), calendar=CAL,
    ) == UNKNOWN


def test_close_time_injectable_not_hardcoded() -> None:
    """收盘时刻可注入：同一观测时刻，注入更晚收盘 -> partial。"""
    at = dt.datetime(2024, 10, 8, 15, 30, tzinfo=CN)
    assert classify_a_share_bar(
        dt.date(2024, 10, 8), at, calendar=CAL,
        close_time=dt.time(16, 0),
    ) == PARTIAL


def test_naive_observed_at_treated_as_shanghai() -> None:
    """不带时区的观测时刻按上海时间解释（收盘后 -> final）。"""
    assert classify_a_share_bar(
        dt.date(2024, 10, 8), dt.datetime(2024, 10, 8, 15, 1), calendar=CAL,
    ) == FINAL


# ---------- G3：调用契约（生产拒绝 / 研究放行且标注） ----------


def _partial_fixture() -> dict[str, pd.DataFrame]:
    """最后一根 bar 是交易日当天（2024-10-08）盘中仍未走完的日线。"""
    return {"510300": _frame(["2024-09-30", "2024-10-08"])}


OBSERVED_INTRADAY = dt.datetime(2024, 10, 8, 10, 0, tzinfo=CN)
OBSERVED_AFTER_CLOSE = dt.datetime(2024, 10, 8, 16, 0, tzinfo=CN)


def test_production_contract_rejects_partial_bar() -> None:
    """production_signal_requires_final：partial 最后一根 bar 被拒绝。"""
    report = annotate_bars(_partial_fixture(), OBSERVED_INTRADAY, calendar=CAL)
    assert report.last_bar["510300"][0] == PARTIAL
    with pytest.raises(PartialBarError) as excinfo:
        require_final_for_production(report)
    assert "510300" in excinfo.value.problems
    assert excinfo.value.problems["510300"][0] == PARTIAL


def test_production_contract_rejects_unknown_as_partial() -> None:
    """保守缺省：unknown（非交易日数据）在生产路径同样被拒绝。"""
    bars = {"510300": _frame(["2024-10-07"])}  # 注入日历中的节假日
    report = annotate_bars(bars, OBSERVED_AFTER_CLOSE, calendar=CAL)
    assert report.last_bar["510300"][0] == UNKNOWN
    with pytest.raises(PartialBarError):
        require_final_for_production(report)


def test_production_contract_rejects_empty_frame_as_unknown() -> None:
    report = annotate_bars({"510300": _frame([])}, OBSERVED_AFTER_CLOSE, calendar=CAL)
    assert report.last_bar["510300"][0] == UNKNOWN
    with pytest.raises(PartialBarError):
        require_final_for_production(report)


def test_production_contract_allows_final() -> None:
    """全部 final（收盘后观测）-> 守卫放行，语义与 close 信号一致。"""
    report = annotate_bars(_partial_fixture(), OBSERVED_AFTER_CLOSE, calendar=CAL)
    assert report.last_bar["510300"][0] == FINAL
    require_final_for_production(report)  # 不抛即通过


def test_annotate_does_not_mutate_frame() -> None:
    """旁侧标注不改 DataFrame 结构：列与索引原样。"""
    fixture = _partial_fixture()
    frame = fixture["510300"]
    columns_before = list(frame.columns)
    annotate_bars(fixture, OBSERVED_INTRADAY, calendar=CAL)
    assert list(frame.columns) == columns_before
    assert len(frame) == 2


def test_research_contract_allows_partial_with_annotation() -> None:
    """research_allow_partial：partial 显式放行，且标注里可见 partial。"""
    report = annotate_bars(_partial_fixture(), OBSERVED_INTRADAY, calendar=CAL)
    labels = research_view(report)
    assert labels == {"510300": PARTIAL}
    # 研究路径不抛、不静默：标注值必须显式等于 partial，而非 final。
    assert labels["510300"] != FINAL


def test_signal_scan_calling_contract_gates_before_scan() -> None:
    """生产 signal_scan 路径处置语义：数据未过守卫前不得进入扫描。

    run_signal_scan 的调用契约（production_signal_requires_final）要求：
    送入其服务层数据的最后一根 bar 必须先通过 require_final_for_production。
    本测试钉死该前置步骤：partial 数据在调用 run_signal_scan 之前即被
    拦截（拒绝处置），close 信号永远不会吃到形成中的 bar。
    """
    from lei_signal.api.signal_scan import AS_OF_CLOSE  # noqa: PLC0415

    report = annotate_bars(_partial_fixture(), OBSERVED_INTRADAY, calendar=CAL)
    with pytest.raises(PartialBarError):
        require_final_for_production(report)
    # 只有守卫通过（final）后，as_of=close 的生产扫描调用才是合法的。
    final_report = annotate_bars(_partial_fixture(), OBSERVED_AFTER_CLOSE, calendar=CAL)
    require_final_for_production(final_report)
    assert AS_OF_CLOSE == "close"
