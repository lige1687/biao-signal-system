"""预热调度规则单元测试：due_actions 的时段/间隔判定。

规则对应需求（2026-08 用户确认）：
- 固定看盘时间 ~12:00（中午收盘后）与 14:45，打开页面必须命中缓存；
- 其余时间 15–30 分钟后台拉一次数据无异议；
- 基本面页面每天更新一次即可。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from lei_signal.api.preheat import (
    INDEX_INTERVAL,
    INTRADAY_INTERVAL,
    OVERSEAS_INTERVAL,
    PreheatState,
    _overseas_watchlist_symbols,
    due_actions,
    preheat_allowed,
)
from lei_signal.data.calendar import WeekdayCalendar

SH = ZoneInfo("Asia/Shanghai")
CALENDAR = WeekdayCalendar()


def sh_dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """北京时间构造，转成 UTC（due_actions 内部口径）。"""
    return datetime(year, month, day, hour, minute, tzinfo=SH).astimezone(UTC)


# 2026-08-25 是周二，2026-08-22 是周六。
TUE = (2026, 8, 25)
SAT = (2026, 8, 22)


def test_cold_start_refreshes_full_regardless_of_time() -> None:
    """冷启动（本进程从未刷过）任何时刻都立即全量刷新，覆盖 launchd 重启。"""
    state = PreheatState()  # 全 None
    now = sh_dt(*SAT, 20, 0)  # 周六晚上，非交易时段
    due = due_actions(state, now=now, calendar=CALENDAR)
    assert "full" in due
    assert "fundamentals" in due
    # full 已 due 时 index 跳过（full 覆盖指数组）
    assert "index" not in due


def test_intraday_due_after_interval() -> None:
    """交易日盘中（含午休）距上次全量 ≥ 间隔则再刷。"""
    now = sh_dt(*TUE, 10, 0)
    stale = PreheatState(full=now - INTRADAY_INTERVAL - timedelta(minutes=1))
    fresh = PreheatState(full=now - timedelta(minutes=5))
    assert "full" in due_actions(stale, now=now, calendar=CALENDAR)
    assert "full" not in due_actions(fresh, now=now, calendar=CALENDAR)


def test_lunch_counts_as_trading_window() -> None:
    """午休 12:30 属于「开盘中」区间，照常按间隔刷新。"""
    now = sh_dt(*TUE, 12, 30)
    state = PreheatState(full=now - INTRADAY_INTERVAL - timedelta(seconds=1))
    assert "full" in due_actions(state, now=now, calendar=CALENDAR)


def test_closing_window_captures_final_bar() -> None:
    """交易日 15:00–15:20 内距上次全量 ≥5 分钟则补刷收盘最终 bar。"""
    now = sh_dt(*TUE, 15, 10)
    due = PreheatState(full=now - timedelta(minutes=10))
    fresh = PreheatState(full=now - timedelta(minutes=3))
    assert "full" in due_actions(due, now=now, calendar=CALENDAR)
    assert "full" not in due_actions(fresh, now=now, calendar=CALENDAR)


def test_no_full_refresh_after_closing_window() -> None:
    """15:20 之后不再全量（A 股收盘数据由时段感知新鲜度持有到次日开盘）。"""
    now = sh_dt(*TUE, 20, 0)
    state = PreheatState(full=now - timedelta(hours=3))
    assert "full" not in due_actions(state, now=now, calendar=CALENDAR)


def test_index_only_refresh_when_full_not_due() -> None:
    """非盘中时段指数组按自身间隔刷新（海外指数夜里仍在交易）。"""
    now = sh_dt(*TUE, 20, 0)
    stale = PreheatState(
        full=now - timedelta(hours=3), index=now - INDEX_INTERVAL - timedelta(minutes=1)
    )
    fresh = PreheatState(full=now - timedelta(hours=3), index=now - timedelta(minutes=5))
    assert "index" in due_actions(stale, now=now, calendar=CALENDAR)
    assert "index" not in due_actions(fresh, now=now, calendar=CALENDAR)


def test_index_skipped_when_full_due() -> None:
    """全量刷新覆盖指数组，同 tick 不重复刷指数。"""
    now = sh_dt(*TUE, 10, 0)
    state = PreheatState(
        full=now - INTRADAY_INTERVAL - timedelta(minutes=1),
        index=now - INDEX_INTERVAL - timedelta(minutes=1),
    )
    due = due_actions(state, now=now, calendar=CALENDAR)
    assert "full" in due
    assert "index" not in due


def test_weekend_no_full_but_index_and_fundamentals_run() -> None:
    """周末不全量，指数/基本面照常按间隔。"""
    now = sh_dt(*SAT, 10, 0)
    state = PreheatState(
        full=now - timedelta(days=1),
        index=now - INDEX_INTERVAL - timedelta(minutes=1),
        fundamentals=now - timedelta(hours=21),
    )
    due = due_actions(state, now=now, calendar=CALENDAR)
    assert "full" not in due
    assert "index" in due
    assert "fundamentals" in due


def test_fundamentals_daily_pin_after_close() -> None:
    """基本面：15:35 后且距上次 ≥11h 触发；或距上次 ≥20h 任何时刻触发。"""
    # 周二 15:40，上次是昨天 15:35 之后刷的（≈24h）→ due
    now = sh_dt(*TUE, 15, 40)
    due = PreheatState(fundamentals=now - timedelta(hours=23))
    assert "fundamentals" in due_actions(due, now=now, calendar=CALENDAR)
    # 周二 15:40，上次今天上午刷的（3h）→ 不 due（不满 11h）
    fresh = PreheatState(fundamentals=now - timedelta(hours=3))
    assert "fundamentals" not in due_actions(fresh, now=now, calendar=CALENDAR)
    # 周三 11:00，距上次 19.5h 且未到 15:35 → 不 due
    now2 = sh_dt(2026, 8, 26, 11, 0)
    almost = PreheatState(fundamentals=now2 - timedelta(hours=19, minutes=30))
    assert "fundamentals" not in due_actions(almost, now=now2, calendar=CALENDAR)
    # 周三 11:00，距上次 21h → due（20h 兜底，防止固定时刻永远不触发）
    overdue = PreheatState(fundamentals=now2 - timedelta(hours=21))
    assert "fundamentals" in due_actions(overdue, now=now2, calendar=CALENDAR)


def test_preheat_allowed_env_switch() -> None:
    """LEI_PREHEAT_DISABLED=1 时允许外部整体关闭预热线程。"""
    assert preheat_allowed({})
    assert not preheat_allowed({"LEI_PREHEAT_DISABLED": "1"})
    assert not preheat_allowed({"LEI_PREHEAT_DISABLED": "true"})


def test_overseas_refreshed_off_hours_when_stale() -> None:
    """非盘中时段非 A 股自选按自身间隔保温（夜间美股盘中也要命中缓存）。"""
    now = sh_dt(*TUE, 20, 0)
    stale = PreheatState(
        full=now - timedelta(hours=3),
        index=now - timedelta(minutes=5),
        overseas=now - OVERSEAS_INTERVAL - timedelta(minutes=1),
    )
    fresh = PreheatState(
        full=now - timedelta(hours=3),
        index=now - timedelta(minutes=5),
        overseas=now - timedelta(minutes=5),
    )
    assert "overseas" in due_actions(stale, now=now, calendar=CALENDAR)
    assert "overseas" not in due_actions(fresh, now=now, calendar=CALENDAR)


def test_overseas_cold_state_refreshes_off_hours() -> None:
    """overseas 时钟从未设置时，非盘中首个 tick 即保温（含 launchd 重启后）。"""
    now = sh_dt(*TUE, 22, 0)
    state = PreheatState(full=now - timedelta(minutes=30), index=now - timedelta(minutes=5))
    assert "overseas" in due_actions(state, now=now, calendar=CALENDAR)


def test_overseas_skipped_when_full_due() -> None:
    """全量刷新覆盖非 A 股自选，同 tick 不重复刷。"""
    now = sh_dt(*TUE, 10, 0)
    state = PreheatState(
        full=now - INTRADAY_INTERVAL - timedelta(minutes=1),
        index=now - INDEX_INTERVAL - timedelta(minutes=1),
        overseas=now - OVERSEAS_INTERVAL - timedelta(minutes=1),
    )
    due = due_actions(state, now=now, calendar=CALENDAR)
    assert "full" in due
    assert "overseas" not in due


def test_overseas_symbol_selection_filters_a_share_and_indices() -> None:
    """保温清单只留非 A 股自选：剔除 A 股 ETF 与默认大盘指数组。"""

    def symbols_fn() -> list[str]:
        return ["000001.SS", "^GSPC", "SOXX", "159652.SZ", "TH881272.SECTOR"]

    selected = _overseas_watchlist_symbols(symbols_fn)
    assert selected == ["SOXX", "TH881272.SECTOR"]
