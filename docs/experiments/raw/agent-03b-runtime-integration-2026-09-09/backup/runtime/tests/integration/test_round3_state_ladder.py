"""Round 3 修复 1 + 修复 2：逐结构分层状态机门禁。

本文件锁定 ``ROUND3_IMPLEMENTATION_PLAN.md`` 第 3 节的状态转换真值表。

为什么断言写得这么死
--------------------
上一轮被复核批评「测试太弱」，根因是用了「存在某个阶段」「结果非空」这类
存在性断言——把整段档位判断删掉照样能过。本文件一律写死**确切日期 +
确切阶段 + 确切档位 + 确切 lifecycle_id**，任何一处语义被改坏都会红。

被锁定的两个缺陷
----------------
D1  ``live_bottoms and joint_now`` 让**未确认**结构靠全局双均线越级到
    ``JOINT_CONFIRMED``。
D2  确认档 latch 额外要求「升级当天重新出现 EMA20 交叉」，而 reclaim 是一次
    进入事件，导致结构确认后 ``early_watch`` 不熄、``early_strength`` 不亮。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.types import (
    Provenance,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state
from lei_signal.rules.ema_reclaim_tiers import (
    TIER_EARLY_WATCH,
    TIER_JOINT_CONFIRMED,
    TIER_LONG_TREND_IMPROVED,
    TIER_STRUCTURE_CONFIRMED,
    detect_structure_bound_ema_reclaim,
)
from lei_signal.state.machine import run_state_machine

# 0=01-01 1=01-02 2=01-03 3=01-04 4=01-05 5=01-08 6=01-09 7=01-10 8=01-11 9=01-12
_INDEX = pd.bdate_range("2024-01-01", periods=10)

_D = {
    "01-01": date(2024, 1, 1),
    "01-02": date(2024, 1, 2),
    "01-03": date(2024, 1, 3),
    "01-04": date(2024, 1, 4),
    "01-05": date(2024, 1, 5),
    "01-08": date(2024, 1, 8),
    "01-09": date(2024, 1, 9),
    "01-10": date(2024, 1, 10),
    "01-11": date(2024, 1, 11),
    "01-12": date(2024, 1, 12),
}


def _frame(
    *,
    close: list[float],
    ema20: list[float],
    sma20: list[float],
    color: list[str],
    long_improving: list[bool] | None = None,
    long_trend: list[str] | None = None,
) -> pd.DataFrame:
    size = len(close)
    improving = long_improving if long_improving is not None else [False] * size
    trend = long_trend if long_trend is not None else ["unknown"] * size
    return pd.DataFrame(
        {
            "open": close,
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "volume": [1_000_000.0] * size,
            "ema20": ema20,
            "sma20": sma20,
            "signal_color": color,
            "long_trend": trend,
            "long_is_improving": improving,
            "long_is_supportive": [False] * size,
        },
        index=_INDEX[:size],
    )


def _ladder_frame(color: list[str] | None = None) -> pd.DataFrame:
    """一条依次点亮全部四档的行情。

    * 01-02 收盘重新站上 EMA20（前一日在下方、EMA20 向上）→ 开启观察
    * 01-11 SMA20 首次转上行且收盘在其上方 → 共同确认
    * 01-12 长周期转为改善 → 长周期改善
    """
    return _frame(
        close=[100, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        ema20=[101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 105.5],
        sma20=[110, 109, 108, 107, 106, 105, 104, 103.5, 104, 104.5],
        color=color if color is not None else ["green"] * 10,
        long_improving=[False] * 9 + [True],
        long_trend=["unknown"] * 9 + ["long_improving"],
    )


def _structure(
    *,
    sid: str = "S-TIER",
    confirmed: date | None,
    invalidated: date | None = None,
    status: StructureStatus = StructureStatus.CANDIDATE,
    detected: date = date(2024, 1, 1),
) -> StructureInstance:
    return StructureInstance(
        structure_id=sid,
        symbol="600000",
        structure_type="bottom_C",
        side="bottom",
        detected_date=detected,
        confirmed_date=confirmed,
        invalidated_date=invalidated,
        c_price=95.0,
        neckline=105.0,
        status=status,
        provenance=Provenance.LEI_EXPLICIT,
    )


def _run(frame: pd.DataFrame, structures: list[StructureInstance]):
    bottoms = [s for s in structures if s.side == "bottom"]
    events = detect_structure_bound_ema_reclaim(frame, "600000", bottoms)
    return run_state_machine(frame, structures, ema_reclaim_events=events), events


def _by_day(history: list) -> dict[date, object]:
    return {state.day: state for state in history}


# ==========================================================================
# 真值表第 2–6 行：candidate 绝不越级（D1）
# ==========================================================================


def test_candidate_with_global_joint_stays_bottom_watch() -> None:
    """真值表 #3/#5：纯候选结构 + 全局双均线共同向上 → 必须仍是 BOTTOM_WATCH。

    这是复核指出的原始缺陷：`live_bottoms and joint_now` 不看结构是否确认。
    """
    frame = _ladder_frame()
    structure = _structure(confirmed=None, status=StructureStatus.CANDIDATE)
    history, _ = _run(frame, [structure])

    joint = dual_ma_bull_state(frame)
    # 前提校验：这条行情确实在 01-11 / 01-12 出现了全局共同确认，
    # 否则本测试会变成「因为条件没触发所以通过」的假阳性。
    assert bool(joint.loc[pd.Timestamp(_D["01-11"])]) is True
    assert bool(joint.loc[pd.Timestamp(_D["01-12"])]) is True

    for state in history:
        assert state.opportunity_stage is Stage.BOTTOM_WATCH, (
            f"{state.day} 未确认结构越级到 {state.opportunity_stage.value}"
        )


def test_candidate_with_joint_and_long_support_never_reaches_trend_reinforced() -> None:
    """真值表 #6：候选 + 共同向上 + 长周期改善，仍不得进 JOINT/TREND。"""
    frame = _ladder_frame()
    structure = _structure(confirmed=None, status=StructureStatus.CANDIDATE)
    history, _ = _run(frame, [structure])

    states = _by_day(history)
    # 01-12 同时具备：全局 joint + 长周期改善
    assert states[_D["01-12"]].long_supportive is True
    assert states[_D["01-12"]].joint_confirmed_now is True

    forbidden = {Stage.EARLY_STRENGTH, Stage.JOINT_CONFIRMED, Stage.TREND_REINFORCED}
    for state in history:
        assert state.opportunity_stage not in forbidden, (
            f"{state.day} 候选结构进入了 {state.opportunity_stage.value}"
        )


def test_candidate_early_watch_does_not_lift_stage() -> None:
    """真值表 #4：候选结构的 early_watch 档只写理由，不抬阶段。"""
    frame = _ladder_frame()
    structure = _structure(confirmed=None, status=StructureStatus.CANDIDATE)
    history, events = _run(frame, [structure])

    # 前提：事件层确实产出了 early_watch，且只有这一档
    tiers = [event.evidence["tier"] for event in events]
    assert tiers == [TIER_EARLY_WATCH]

    states = _by_day(history)
    assert states[_D["01-02"]].early_watch_by_structure["S-TIER"] is True
    assert states[_D["01-02"]].opportunity_stage is Stage.BOTTOM_WATCH
    # 观察档必须在理由里可见，否则界面无从展示
    assert any("观察档" in reason for reason in states[_D["01-02"]].reasons)


def test_global_joint_without_any_structure_produces_no_opportunity() -> None:
    """没有任何结构关联生命周期时，全局双均线向上不得产生共同确认阶段。"""
    frame = _ladder_frame()
    history = run_state_machine(frame, [], ema_reclaim_events=[])

    joint = dual_ma_bull_state(frame)
    assert bool(joint.loc[pd.Timestamp(_D["01-11"])]) is True

    for state in history:
        assert state.opportunity_stage is Stage.NO_CLUE, (
            f"{state.day} 无结构却给出 {state.opportunity_stage.value}"
        )


# ==========================================================================
# 真值表第 7–10 行：确认后的逐日交接（D2）
# ==========================================================================


def test_full_ladder_daily_timeline_after_confirmation() -> None:
    """逐日锁定完整升级链：01-02 观察 → 01-05 确认 → 01-11 共同 → 01-12 长周期。

    每日断言：日期 / 机会阶段 / early_watch / early_strength /
    structure_id / lifecycle_id / 当天是否有新 EMA20 交叉。
    """
    frame = _ladder_frame()
    structure = _structure(
        confirmed=_D["01-05"], status=StructureStatus.CONFIRMED
    )
    history, events = _run(frame, [structure])

    # ---- 事件层前提：四档共享同一 lifecycle_id ----
    timeline = [(e.available_date, e.evidence["tier"], e.lifecycle_id) for e in events]
    assert timeline == [
        (_D["01-02"], TIER_EARLY_WATCH, "ema20_reclaim_rising:S-TIER:2024-01-02"),
        (_D["01-05"], TIER_STRUCTURE_CONFIRMED, "ema20_reclaim_rising:S-TIER:2024-01-02"),
        (_D["01-11"], TIER_JOINT_CONFIRMED, "ema20_reclaim_rising:S-TIER:2024-01-02"),
        (_D["01-12"], TIER_LONG_TREND_IMPROVED, "ema20_reclaim_rising:S-TIER:2024-01-02"),
    ]

    reclaim = ema20_reclaim_state(frame)
    lifecycle = "ema20_reclaim_rising:S-TIER:2024-01-02"

    # (日期, 阶段, early_watch, early_strength, 期望档位, 当天是否新EMA交叉)
    expected = [
        (_D["01-01"], Stage.BOTTOM_WATCH, False, False, None, False),
        (_D["01-02"], Stage.BOTTOM_WATCH, True, False, TIER_EARLY_WATCH, True),
        (_D["01-03"], Stage.BOTTOM_WATCH, True, False, TIER_EARLY_WATCH, False),
        (_D["01-04"], Stage.BOTTOM_WATCH, True, False, TIER_EARLY_WATCH, False),
        # 确认日：watch 熄灭、strength 点亮，且当天没有新的 EMA20 交叉
        (_D["01-05"], Stage.EARLY_STRENGTH, False, True, TIER_STRUCTURE_CONFIRMED, False),
        (_D["01-08"], Stage.EARLY_STRENGTH, False, True, TIER_STRUCTURE_CONFIRMED, False),
        (_D["01-09"], Stage.EARLY_STRENGTH, False, True, TIER_STRUCTURE_CONFIRMED, False),
        (_D["01-10"], Stage.EARLY_STRENGTH, False, True, TIER_STRUCTURE_CONFIRMED, False),
        (_D["01-11"], Stage.JOINT_CONFIRMED, False, True, TIER_JOINT_CONFIRMED, False),
        (_D["01-12"], Stage.TREND_REINFORCED, False, True, TIER_LONG_TREND_IMPROVED, False),
    ]

    states = _by_day(history)
    assert len(history) == len(expected)

    for day, stage, watch, strength, tier, cross in expected:
        state = states[day]
        assert state.day == day
        assert state.opportunity_stage is stage, (
            f"{day} 阶段应为 {stage.value}，实际 {state.opportunity_stage.value}"
        )
        assert state.early_watch_by_structure.get("S-TIER", False) is watch, (
            f"{day} early_watch 应为 {watch}"
        )
        assert state.early_strength_by_structure.get("S-TIER", False) is strength, (
            f"{day} early_strength 应为 {strength}"
        )
        observation = state.observations.get("S-TIER")
        actual_tier = observation.tier if observation is not None else None
        assert actual_tier == tier, f"{day} 档位应为 {tier}，实际 {actual_tier}"
        if tier is not None:
            assert observation is not None
            assert observation.structure_id == "S-TIER"
            assert observation.lifecycle_id == lifecycle, (
                f"{day} 必须沿用同一 lifecycle_id，不得重开"
            )
            assert observation.opened_on == _D["01-02"]
        assert bool(reclaim.loc[pd.Timestamp(day)]) is cross, (
            f"{day} 新 EMA20 交叉前提不符"
        )


def test_upgrade_days_require_no_fresh_ema_reclaim() -> None:
    """升级三日（确认 / 共同 / 长周期）当天都不得存在新的 EMA20 交叉。

    如果实现回退成「升级需要当天重新交叉」，这三天根本不会升级，
    上面的时间线测试会红——本测试则锁死「前提确实是没有交叉」，
    防止有人靠改 fixture（制造额外交叉）来让时间线测试变绿。
    """
    frame = _ladder_frame()
    reclaim = ema20_reclaim_state(frame)
    for day in (_D["01-05"], _D["01-11"], _D["01-12"]):
        assert bool(reclaim.loc[pd.Timestamp(day)]) is False, (
            f"{day} 不应有新的 EMA20 交叉，否则本组测试失去意义"
        )
    # 唯一的交叉发生在开启日
    crossings = [ts.date() for ts in frame.index if bool(reclaim.loc[ts])]
    assert crossings == [_D["01-02"]]


def test_confirmed_structure_handover_is_exact() -> None:
    """确认日起的硬约束（任务书特别要求）。"""
    frame = _ladder_frame()
    structure = _structure(
        confirmed=_D["01-05"], status=StructureStatus.CONFIRMED
    )
    history, _ = _run(frame, [structure])

    for state in history:
        if state.day < _D["01-05"]:
            continue
        assert state.early_watch_by_structure.get("S-TIER", False) is False, (
            f"{state.day} 结构已确认，early_watch 必须为 False"
        )
        assert state.early_strength_by_structure.get("S-TIER", False) is True, (
            f"{state.day} 结构已确认且转强持续，early_strength 必须为 True"
        )


def test_structure_confirmed_without_reclaim_stays_structure_confirmed() -> None:
    """真值表 #7：结构确认但从未出现 EMA20 转强 → 停在 STRUCTURE_CONFIRMED。"""
    # 收盘一路在 EMA20 下方：不会有任何 reclaim
    frame = _frame(
        close=[100, 99, 98, 97, 96, 95, 94, 93, 92, 91],
        ema20=[110, 110, 110, 110, 110, 110, 110, 110, 110, 110],
        sma20=[120, 119, 118, 117, 116, 115, 114, 113, 112, 111],
        color=["green"] * 10,
    )
    structure = _structure(
        confirmed=_D["01-05"], status=StructureStatus.CONFIRMED
    )
    history, events = _run(frame, [structure])
    assert events == []

    states = _by_day(history)
    assert states[_D["01-04"]].opportunity_stage is Stage.BOTTOM_WATCH
    assert states[_D["01-05"]].opportunity_stage is Stage.STRUCTURE_CONFIRMED
    assert states[_D["01-12"]].opportunity_stage is Stage.STRUCTURE_CONFIRMED
    assert states[_D["01-12"]].observations.get("S-TIER") is None


def test_immediate_confirmation_opens_at_confirmed_tier_without_fake_watch() -> None:
    """真值表补充：反包类结构确认当日即转强 → 直接从确认档开启。

    不得为了「凑齐阶梯」伪造一条 candidate early_watch。
    """
    frame = _ladder_frame()
    # 结构在 01-01 就已确认；01-02 出现 reclaim
    structure = _structure(
        confirmed=_D["01-01"], status=StructureStatus.CONFIRMED
    )
    history, events = _run(frame, [structure])

    tiers = [(e.available_date, e.evidence["tier"]) for e in events]
    assert tiers[0] == (_D["01-02"], TIER_STRUCTURE_CONFIRMED), (
        "已确认结构的首个事件必须直接是确认档，不得伪造 early_watch"
    )
    assert TIER_EARLY_WATCH not in [tier for _, tier in tiers]

    states = _by_day(history)
    assert states[_D["01-02"]].opportunity_stage is Stage.EARLY_STRENGTH
    assert states[_D["01-02"]].early_watch_by_structure.get("S-TIER", False) is False


# ==========================================================================
# 真值表第 11–13 行：转黑 / 触及 C / 多结构隔离
# ==========================================================================


def test_black_closes_strength_lifecycle_but_keeps_structure_alive() -> None:
    """真值表 #11：转黑关闭转强生命周期，结构本身存活；重开须换新 lifecycle_id。"""
    color = ["green", "green", "green", "black", "green", "green",
             "green", "green", "green", "green"]
    frame = _frame(
        close=[100, 103, 104, 99, 106, 107, 108, 109, 110, 111],
        ema20=[101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 105.5],
        sma20=[110, 109, 108, 107, 106, 105, 104, 103.5, 104, 104.5],
        color=color,
    )
    structure = _structure(
        confirmed=_D["01-01"], status=StructureStatus.CONFIRMED
    )
    history, events = _run(frame, [structure])
    states = _by_day(history)

    # 01-04 转黑当日：观察实例关闭，但结构仍在 live_bottoms
    assert states[_D["01-04"]].observations.get("S-TIER") is None
    assert [s.structure_id for s in states[_D["01-04"]].live_bottoms] == ["S-TIER"]

    # 01-05 重新站上 EMA20 → 新实例、新 lifecycle_id
    lifecycles = [event.lifecycle_id for event in events]
    assert len(set(lifecycles)) >= 2, "转黑后重新转强必须开启新的 lifecycle_id"
    assert lifecycles[0] != lifecycles[-1]

    reopened = states[_D["01-05"]].observations.get("S-TIER")
    assert reopened is not None
    assert reopened.opened_on == _D["01-05"]
    assert reopened.lifecycle_id != lifecycles[0]


def test_c_touch_permanently_kills_all_tiers() -> None:
    """真值表 #12：触及 C 永久失效，watch / early / joint / long 全部关闭且不复活。"""
    frame = _ladder_frame()
    structure = _structure(
        confirmed=_D["01-05"],
        invalidated=_D["01-08"],
        status=StructureStatus.INVALIDATED,
    )
    history, events = _run(frame, [structure])

    # 失效日及以后不得再有事件
    assert all(event.available_date < _D["01-08"] for event in events)

    for state in history:
        if state.day < _D["01-08"]:
            continue
        assert state.observations.get("S-TIER") is None
        assert state.early_watch_by_structure.get("S-TIER", False) is False
        assert state.early_strength_by_structure.get("S-TIER", False) is False
        assert state.opportunity_stage is Stage.NO_CLUE, (
            f"{state.day} 结构已永久失效，不应保留任何机会阶段"
        )


def test_two_structures_do_not_borrow_each_others_signals() -> None:
    """真值表 #13：A 已确认、B 候选出现转强 → 不得把 B 的转强用于升级 A。"""
    frame = _ladder_frame()
    # A：01-01 确认，但其观察实例在 01-02 开启（同一行情，两个结构都会被扫描）
    # 为了隔离，让 A 在 reclaim 之前就失效？不行——那样 A 不在 live。
    # 改用：A 已确认但 detected 较晚，错过 01-02 的唯一一次 reclaim。
    structure_a = _structure(
        sid="S-A",
        confirmed=_D["01-05"],
        status=StructureStatus.CONFIRMED,
        detected=_D["01-03"],   # 晚于 01-02 的唯一 reclaim → A 永远开不了实例
    )
    structure_b = _structure(
        sid="S-B",
        confirmed=None,
        status=StructureStatus.CANDIDATE,
        detected=_D["01-01"],   # B 能吃到 01-02 的 reclaim → early_watch
    )
    history, events = _run(frame, [structure_a, structure_b])

    by_structure: dict[str, list[str]] = {}
    for event in events:
        by_structure.setdefault(event.structure_id, []).append(event.evidence["tier"])

    # B 只有观察档；A 因错过唯一一次 reclaim 而没有任何事件
    assert by_structure.get("S-B") == [TIER_EARLY_WATCH]
    assert "S-A" not in by_structure, "A 错过了唯一一次 reclaim，不应凭空获得事件"

    states = _by_day(history)
    final = states[_D["01-12"]]
    # A 已确认但无自己的转强 → 最高只能到 STRUCTURE_CONFIRMED
    assert final.observations.get("S-A") is None
    assert final.early_strength_by_structure.get("S-A", False) is False
    # B 是候选 + 观察档 → 不抬阶段
    assert final.early_watch_by_structure.get("S-B", False) is True
    assert final.early_strength_by_structure.get("S-B", False) is False
    # 综合：不得因为 B 的转强 + 全局 joint 把整体推到 JOINT_CONFIRMED
    assert final.opportunity_stage is Stage.STRUCTURE_CONFIRMED, (
        f"跨结构借用信号：实际 {final.opportunity_stage.value}"
    )
