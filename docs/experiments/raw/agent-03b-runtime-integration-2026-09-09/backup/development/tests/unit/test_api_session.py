"""收盘后/非开盘时段的缓存 TTL 行为：A 股收盘后数据不变，缓存到下一开盘。

时段换算：Asia/Shanghai = UTC+8（中国无夏令时）。
  09:30 SH = 01:30 UTC（开盘）   15:00 SH = 07:00 UTC（收盘）
默认日历认定周一至周五为交易日（无节假日表）。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lei_signal.api import session
from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR

CAL = DEFAULT_TRADING_CALENDAR
OPEN_TTL = 900.0

# 2026-08-07 周五（交易日）/ 08-08 周六 / 08-10 周一
FRI_OPEN_UTC = datetime(2026, 8, 7, 1, 30, tzinfo=UTC)      # 09:30 SH
FRI_MORNING_UTC = datetime(2026, 8, 7, 3, 0, tzinfo=UTC)     # 11:00 SH 盘中
FRI_CLOSE_UTC = datetime(2026, 8, 7, 7, 0, tzinfo=UTC)       # 15:00 SH
FRI_EVENING_UTC = datetime(2026, 8, 7, 10, 0, tzinfo=UTC)    # 18:00 SH 收盘后
SAT_UTC = datetime(2026, 8, 8, 10, 0, tzinfo=UTC)            # 周六
MON_PREOPEN_UTC = datetime(2026, 8, 10, 0, 30, tzinfo=UTC)   # 08:30 SH 开盘前
MON_OPEN_UTC = datetime(2026, 8, 10, 1, 30, tzinfo=UTC)      # 09:30 SH 开盘


def test_is_open_trading_morning():
    assert session.is_open(CAL, now=FRI_MORNING_UTC) is True


def test_is_open_closed_after_close():
    assert session.is_open(CAL, now=FRI_EVENING_UTC) is False


def test_is_open_weekend():
    assert session.is_open(CAL, now=SAT_UTC) is False


def test_is_open_before_open_same_day():
    # 开盘前（08:30 SH）仍属收盘区间
    assert session.is_open(CAL, now=MON_PREOPEN_UTC) is False


def test_last_close_after_close_is_today():
    # 18:00 SH（已过 15:00）-> 当日收盘
    assert session.last_close(CAL, now=FRI_EVENING_UTC) == FRI_CLOSE_UTC


def test_last_close_intraday_is_previous_day():
    # 11:00 SH（未到 15:00）-> 上一交易日收盘（周四 15:00 = 周四 07:00 UTC）
    prev_close = session.last_close(CAL, now=FRI_MORNING_UTC)
    assert prev_close == datetime(2026, 8, 6, 7, 0, tzinfo=UTC)


def test_last_close_weekend_is_friday():
    assert session.last_close(CAL, now=SAT_UTC) == FRI_CLOSE_UTC


def test_next_open_weekend_is_monday():
    assert session.next_open(CAL, now=SAT_UTC) == MON_OPEN_UTC


def test_next_open_before_open_is_today():
    # 08:30 SH -> 今日 09:30 开盘
    assert session.next_open(CAL, now=MON_PREOPEN_UTC) == MON_OPEN_UTC


def test_next_open_after_close_is_next_trading_day():
    # 周五 18:00 -> 下周一 09:30
    assert session.next_open(CAL, now=FRI_EVENING_UTC) == MON_OPEN_UTC


def test_cache_fresh_open_recent():
    # 盘中、刚取 -> 新鲜
    fetched = FRI_MORNING_UTC - timedelta(seconds=60)
    assert session.is_cache_fresh(CAL, fetched, now=FRI_MORNING_UTC, open_ttl=OPEN_TTL) is True


def test_cache_stale_open_expired():
    # 盘中、超过 TTL -> 过期重算
    fetched = FRI_MORNING_UTC - timedelta(seconds=1000)
    assert session.is_cache_fresh(CAL, fetched, now=FRI_MORNING_UTC, open_ttl=OPEN_TTL) is False


def test_cache_fresh_after_close_recent_entry():
    # 18:00 收盘后、收盘后刚取（17:59 SH）-> 新鲜，缓存到下周一
    fetched = FRI_EVENING_UTC - timedelta(seconds=60)
    assert session.is_cache_fresh(CAL, fetched, now=FRI_EVENING_UTC, open_ttl=OPEN_TTL) is True


def test_cache_stale_after_close_intraday_entry():
    # 18:00 收盘后，但缓存是盘中（11:30 SH）取的 -> 缺最终收盘，过期重算
    fetched = FRI_MORNING_UTC + timedelta(minutes=30)  # 11:30 SH 盘中
    assert session.is_cache_fresh(CAL, fetched, now=FRI_EVENING_UTC, open_ttl=OPEN_TTL) is False


def test_cache_fresh_weekend_post_close_entry():
    # 周六、条目是周五收盘后取的 -> 新鲜，缓存到下周一
    fetched = FRI_EVENING_UTC
    assert session.is_cache_fresh(CAL, fetched, now=SAT_UTC, open_ttl=OPEN_TTL) is True


def test_cache_stale_weekend_intraday_entry():
    # 周六、条目是周五盘中取的 -> 缺最终收盘，过期重算
    fetched = FRI_MORNING_UTC
    assert session.is_cache_fresh(CAL, fetched, now=SAT_UTC, open_ttl=OPEN_TTL) is False


def test_cache_fresh_before_open_holds_previous_close():
    # 周一 08:30（开盘前），条目是周五收盘后取的 -> 仍新鲜（上周五最终数据）
    fetched = FRI_EVENING_UTC
    assert session.is_cache_fresh(CAL, fetched, now=MON_PREOPEN_UTC, open_ttl=OPEN_TTL) is True


def test_cache_stale_at_open_boundary():
    # 周一 09:30 开盘 -> 切回短 TTL；上周五的条目已过期，重算拿盘中数据
    fetched = FRI_EVENING_UTC
    assert session.is_cache_fresh(CAL, fetched, now=MON_OPEN_UTC, open_ttl=OPEN_TTL) is False
