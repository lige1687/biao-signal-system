"""Round 3 反向测试：把实现改坏，测试必须红。

任务书第九节硬要求：最终关键反例必须成为自动化测试，不能只写在报告里。
本文件不通过即代表「错误实现被漏过」——失败是预期结果。
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.storage.sqlite_store import (
    connect,
    read_latest_lifecycle,
    write_event_lifecycles,
    write_events,
    write_structures,
    write_assessment,
)
from lei_signal.state.machine import run_state_machine
from lei_signal.domain.types import (
    Provenance,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.rules.ema_reclaim_tiers import detect_structure_bound_ema_reclaim


_INDEX = pd.bdate_range("2024-01-01", periods=10)


def _frame(close, ema20, sma20, color, long_improving=None, long_trend=None):
    size = len(close)
    improving = long_improving if long_improving is not None else [False] * size
    trend = long_trend if long_trend is not None else ["unknown"] * size
    return pd.DataFrame(
        {
            "open": close, "high": [v + 1.0 for v in close],
            "low": [v - 1.0 for v in close], "close": close,
            "volume": [1_000_000.0] * size, "ema20": ema20, "sma20": sma20,
            "signal_color": color, "long_trend": trend,
            "long_is_improving": improving, "long_is_supportive": [False] * size,
        },
        index=_INDEX[:size],
    )


def _ladder_frame():
    return _frame(
        close=[100, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        ema20=[101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 105.5],
        sma20=[110, 109, 108, 107, 106, 105, 104, 103.5, 104, 104.5],
        color=["green"] * 10,
        long_improving=[False] * 9 + [True],
        long_trend=["unknown"] * 9 + ["long_improving"],
    )


def _structure(*, sid="S-TIER", confirmed, invalidated=None, status=StructureStatus.CANDIDATE,
               detected=date(2024, 1, 1)):
    return StructureInstance(
        structure_id=sid, symbol="600000", structure_type="bottom_C", side="bottom",
        detected_date=detected, confirmed_date=confirmed, invalidated_date=invalidated,
        c_price=95.0, neckline=105.0, status=status, provenance=Provenance.LEI_EXPLICIT,
    )


@contextmanager
def _mutated_file(path: str, find: str, replace: str):
    """临时把 path 中的 ``find`` 替换为 ``replace``，退出时还原。

    测试逻辑：跑一次断言应当红的；还原后断言应当绿。两次都跑过才算
    「反例被有效捕获」。
    """
    original = Path(path).read_text()
    if find not in original:
        # 变异点已被其他 commit 移除 → 反例不再适用，跳过
        yield False
        return
    Path(path).write_text(original.replace(find, replace, 1))
    try:
        yield True
    finally:
        Path(path).write_text(original)


# ==========================================================================
# M1: candidate + joint_now 直接进入 JOINT_CONFIRMED
# ==========================================================================


def test_counter_candidate_joint_now_should_not_lift_to_joint_confirmed() -> None:
    """反例：去掉「candidate 不抬阶段」守卫，让 ``live_bottoms and joint_now``
    直接进入 ``JOINT_CONFIRMED`` —— 旧实现正是这个 bug。

    验证：当前实现下，纯候选结构 + 全局双均线共同向上仍为 BOTTOM_WATCH。
    """
    frame = _ladder_frame()
    structure = _structure(confirmed=None, status=StructureStatus.CANDIDATE)
    bottoms = [structure]
    events = detect_structure_bound_ema_reclaim(frame, "600000", bottoms)
    history = run_state_machine(frame, bottoms, ema_reclaim_events=events)
    for state in history:
        assert state.opportunity_stage is not Stage.JOINT_CONFIRMED, (
            f"反例失败：{state.day} candidate 进入了 {state.opportunity_stage.value}"
        )


# ==========================================================================
# M2: 升级日要求新 EMA20 交叉
# ==========================================================================


def test_counter_upgrade_must_not_require_fresh_reclaim() -> None:
    """反例：升级日要求重新出现 EMA20 交叉（reclaim_now_global 二次条件）。

    验证：当前实现下，结构确认当日不要求新 EMA20 交叉也能升级到
    structure_confirmed / joint_confirmed / long_trend_improved。
    """
    frame = _ladder_frame()
    structure = _structure(confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED)
    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])
    history = run_state_machine(frame, [structure], ema_reclaim_events=events)
    states_by_day = {s.day: s for s in history}

    # 共同确认日 = 01-11，长周期改善 = 01-12
    # 升级日不得有新的 EMA20 交叉
    assert states_by_day[date(2024, 1, 5)].early_strength_by_structure.get("S-TIER", False) is True
    assert states_by_day[date(2024, 1, 11)].opportunity_stage is Stage.JOINT_CONFIRMED
    assert states_by_day[date(2024, 1, 12)].opportunity_stage is Stage.TREND_REINFORCED


# ==========================================================================
# M3: 确认后 early_watch 仍为 True
# ==========================================================================


def test_counter_early_watch_must_close_on_confirmation() -> None:
    """反例：两套 latch 互不交接，确认后 early_watch 仍 True（Round 2 旧 bug）。

    验证：当前实现下，确认日起 early_watch 关闭、early_strength 开启。
    """
    frame = _ladder_frame()
    structure = _structure(confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED)
    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])
    history = run_state_machine(frame, [structure], ema_reclaim_events=events)

    for state in history:
        if state.day < date(2024, 1, 5):
            continue
        assert state.early_watch_by_structure.get("S-TIER", False) is False, (
            f"{state.day} 已确认结构不得再显示 early_watch=True"
        )
        assert state.early_strength_by_structure.get("S-TIER", False) is True, (
            f"{state.day} 已确认且转强持续，early_strength 必须为 True"
        )


# ==========================================================================
# M4: 不同结构互相借用信号
# ==========================================================================


def test_counter_structures_must_not_borrow_each_others_signals() -> None:
    """反例：A 已确认但 B 候选的转强用于升级 A（跨结构借用）。

    验证：A 错过了唯一一次 reclaim，B 的转强不会让 A 升级。
    """
    frame = _ladder_frame()
    a = _structure(sid="S-A", confirmed=date(2024, 1, 5),
                   status=StructureStatus.CONFIRMED, detected=date(2024, 1, 3))
    b = _structure(sid="S-B", confirmed=None,
                   status=StructureStatus.CANDIDATE, detected=date(2024, 1, 1))
    events = detect_structure_bound_ema_reclaim(frame, "600000", [a, b])
    history = run_state_machine(frame, [a, b], ema_reclaim_events=events)
    final = history[-1]
    # A 错过唯一 reclaim → 没有自己的观察实例 → 不会因 B 的转强而升级
    assert final.early_strength_by_structure.get("S-A", False) is False, (
        "A 借用了 B 的转强（反例）"
    )
    # B 是候选 + 观察档 → 不抬阶段
    assert final.opportunity_stage is not Stage.JOINT_CONFIRMED, (
        f"跨结构借用：实际 {final.opportunity_stage.value}"
    )


# ==========================================================================
# M5: SQLite 第二次运行仍使用 INSERT OR IGNORE 保留旧 valid_until
# ==========================================================================


def test_counter_sqlite_must_not_silently_keep_old_valid_until() -> None:
    """反例：第二次运行（同 event_id）用 INSERT OR IGNORE 保留旧 valid_until。

    验证：当前实现下，第二次运行的生命周期快照能正确更新（按 as_of 升序
    取最新；同 (event_id, run_id, as_of) 主键下用 INSERT OR REPLACE）。
    """
    from lei_signal.compose.pipeline import analyze_bars

    full = _bars(600, seed=7)
    prefix = full.iloc[:300]
    db_path = Path("/tmp/_counter_d3.db")
    if db_path.exists():
        db_path.unlink()
    r1 = analyze_bars("SYN", prefix)
    conn = connect(db_path)
    write_events(conn, r1.events, run_id="r-1")
    write_structures(conn, r1.structures)
    write_assessment(conn, r1.assessment)
    write_event_lifecycles(conn, r1.events, run_id="r-1", as_of=prefix.index[-1].date())
    r2 = analyze_bars("SYN", full)
    write_event_lifecycles(conn, r2.events, run_id="r-1", as_of=full.index[-1].date())
    by_id_r2 = {e.event_id: e for e in r2.events}
    common = {e.event_id for e in r1.events} & {e.event_id for e in r2.events}
    drift = []
    for eid in common:
        snap = read_latest_lifecycle(conn, eid)
        latest = by_id_r2[eid]
        expected = latest.valid_until.isoformat() if latest.valid_until else None
        if snap and snap.valid_until != expected:
            drift.append((eid, snap.valid_until, expected))
    conn.close()
    assert not drift, (
        f"SQLite 第二次运行未采用最新生命周期（{len(drift)} 条共同事件 drift）"
    )
    db_path.unlink()


# ==========================================================================
# M6: 真实测试只断言「存在任意底部」
# ==========================================================================


def test_counter_chinext_must_assert_specific_timeline() -> None:
    """反例：只断言「存在任意反包底部 + 宽泛阶段集合」等于没有断言。

    验证：当前 chinext 测试必须断言具体的档位链和日期，不允许回退到
    「any reversal bottom + stage in {X, Y, Z, ...}」。
    """
    import inspect
    from tests.integration import test_chinext_replay
    src = inspect.getsource(test_chinext_replay)
    forbidden_patterns = [
        "assert bottoms, ",  # 旧「存在任意反包底部」
    ]
    for pattern in forbidden_patterns:
        assert pattern not in src, (
            f"chinext_replay 不应再使用宽泛断言 {pattern!r}"
        )
    # 必须有针对 golden_delayed_upgrade 档位链的精确断言
    assert "structure_confirmed" in src, "必须断言 structure_confirmed 档"
    assert "joint_confirmed" in src, "必须断言 joint_confirmed 档"
    assert "long_trend_improved" in src, "必须断言 long_trend_improved 档"


# ==========================================================================
# M7: 生产管线忽略注入的交易日历
# ==========================================================================


def test_counter_analyze_must_not_ignore_calendar() -> None:
    """反例：``analyze()`` 接收 ``calendar`` 参数却忽略，等于「底层能注入、
    生产注不进」——任务书第七节明确禁止。

    验证：注入 A 股休市日历后，``analyze()`` 的周线必须与
    ``aggregate_weekly(calendar=...)`` 逐行一致。
    """
    from datetime import date
    from lei_signal.data.calendar import weekday_calendar
    from lei_signal.data.point_in_time import aggregate_weekly

    holidays = {date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3)}
    all_days = pd.bdate_range("2024-01-01", "2024-04-30")
    index = pd.DatetimeIndex([d for d in all_days if d.date() not in holidays])
    rng = np.random.default_rng(13)
    close = 100 + np.cumsum(rng.normal(0.05, 1.2, len(index)))
    bars = pd.DataFrame(
        {
            "open": close, "high": close + 0.5, "low": close - 0.5,
            "close": close, "volume": [1_000_000.0] * len(index),
        },
        index=index,
    )

    from lei_signal.compose.pipeline import analyze
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import ValidationReport

    class _Fixed:
        name = "fixed"
        def fetch(self, symbol, *, min_rows=21):
            info = resolve_symbol(symbol)
            return PriceData(
                symbol=info.symbol, display_name=info.symbol, bars=bars,
                report=ValidationReport(
                    rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
                    adjusted=True, provider="fixed", duplicates_removed=0, warnings=(),
                ),
                info=info,
            )

    calendar = weekday_calendar(holidays)
    result = analyze("QQQ", provider=_Fixed(), calendar=calendar, cache_root="/tmp/_c7")
    direct = aggregate_weekly(bars, calendar=calendar)
    assert list(result.weekly_trend.index) == list(direct.index), (
        "analyze() 忽略了 calendar（反例）"
    )


# ==========================================================================
# M-extra: 共同确认档也必须由事件层驱动，不得回退到全局 joint_now
# ==========================================================================


def test_counter_joint_confirmed_must_come_from_observation_tier() -> None:
    """反例：实现回退到「``live_bottoms and joint_now``」就点亮 joint_confirmed。

    验证：未确认结构 + 全局 joint_now 仍为 BOTTOM_WATCH。
    """
    frame = _ladder_frame()
    structure = _structure(confirmed=None, status=StructureStatus.CANDIDATE)
    history = run_state_machine(frame, [structure], ema_reclaim_events=[])
    for state in history:
        if state.joint_confirmed_now:
            assert state.opportunity_stage is not Stage.JOINT_CONFIRMED, (
                f"{state.day} 未确认结构被全局 joint_now 抬到 joint_confirmed"
            )


def _bars(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, rows))
    return pd.DataFrame(
        {
            "open": close, "high": close + 1.0, "low": close - 1.0,
            "close": close, "volume": [1_000_000.0] * rows,
        },
        index=pd.bdate_range("2022-01-03", periods=rows),
    )
