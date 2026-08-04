"""P0 持续买点 DTO 门禁。

测试重点不是“有字段”，而是锁定三条产品语义：
1. early_watch 只观察，不是买点；
2. 历史最高档与今天原子条件分开；
3. 非升级当天仍能通过状态机 observations 看见本轮生命周期。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.api.routes.symbols import _build_trade_opportunities
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.domain.types import (
    DailyAssessment,
    LongTrendState,
    Provenance,
    RiskState,
    SignalColor,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.rules.ema_reclaim_tiers import (
    TIER_EARLY_WATCH,
    TIER_JOINT_CONFIRMED,
)
from lei_signal.state.machine import DayState, StructureObservation


def _structure(*, confirmed: date | None) -> StructureInstance:
    return StructureInstance(
        structure_id="S-P0",
        symbol="600000.SS",
        structure_type="higher_low_bottom",
        side="bottom",
        detected_date=date(2024, 1, 2),
        confirmed_date=confirmed,
        status=StructureStatus.CONFIRMED if confirmed else StructureStatus.CANDIDATE,
        c_price=95.0,
        neckline=105.0,
        provenance=Provenance.LEI_EXPLICIT,
    )


def _result(
    *,
    tier: str,
    confirmed: date | None,
    joint_now: bool,
    color: SignalColor = SignalColor.GREEN,
) -> AnalysisResult:
    day = date(2024, 1, 10)
    structure = _structure(confirmed=confirmed)
    observation = StructureObservation(
        structure_id=structure.structure_id,
        lifecycle_id="ema20_reclaim_rising:S-P0:2024-01-03",
        tier=tier,
        opened_on=date(2024, 1, 3),
        # 特意早于 as_of：证明非升级当天仍持续展示。
        last_upgraded_on=date(2024, 1, 5),
    )
    state = DayState(
        day=day,
        opportunity_stage=Stage.BOTTOM_WATCH if tier == TIER_EARLY_WATCH else Stage.JOINT_CONFIRMED,
        risk_state=RiskState.NORMAL,
        color=color,
        live_bottoms=[structure],
        primary_bottom=structure,
        observations={structure.structure_id: observation},
        joint_confirmed_now=joint_now,
        daily_long=LongTrendState.UNKNOWN,
        weekly_long=LongTrendState.UNKNOWN,
        long_supportive=False,
    )
    assessment = DailyAssessment(
        symbol="600000.SS",
        as_of=day,
        opportunity_stage=state.opportunity_stage,
        risk_state=state.risk_state,
        stage=state.stage,
        color=color,
        primary_structure=structure,
        all_live_structures=[structure],
        joint_confirmed_now=joint_now,
    )
    frame = pd.DataFrame(
        {"close": [106.0]}, index=[pd.Timestamp(day)]
    )
    # DTO 构造只读取这些字段；其余内部对象在本纯函数测试中不参与。
    return AnalysisResult(
        symbol="600000.SS",
        display_name="测试标的",
        frame=frame,
        weekly_trend=pd.DataFrame(),
        events=[],
        structures=[structure],
        pivots=(),
        history=[state],
        assessment=assessment,
        b1=None,
        profile=None,
        price_data=None,  # type: ignore[arg-type]
    )


def test_early_watch_is_visible_but_never_a_buy_reference() -> None:
    item = _build_trade_opportunities(
        _result(tier=TIER_EARLY_WATCH, confirmed=None, joint_now=False)
    )[0]

    assert item.state == "watch"
    assert item.is_buy_reference is False
    assert item.current_conditions_confirmed is True
    assert "尚未确认" in "；".join(item.missing_conditions)
    assert "等待同一底部结构确认" in item.next_step_cn


def test_reached_joint_tier_does_not_pretend_joint_is_true_today() -> None:
    item = _build_trade_opportunities(
        _result(
            tier=TIER_JOINT_CONFIRMED,
            confirmed=date(2024, 1, 4),
            joint_now=False,
        )
    )[0]

    assert item.reached_tier == TIER_JOINT_CONFIRMED
    assert item.reached_tier_cn == "共同确认"
    assert item.is_buy_reference is True
    assert item.state == "weakened"
    assert item.current_conditions_confirmed is False
    assert any("曾达共同确认" in text for text in item.missing_conditions)


def test_non_upgrade_day_still_exposes_structure_and_lifecycle() -> None:
    item = _build_trade_opportunities(
        _result(
            tier=TIER_JOINT_CONFIRMED,
            confirmed=date(2024, 1, 4),
            joint_now=True,
        )
    )[0]

    assert item.opened_on == "2024-01-03"
    assert item.last_upgraded_on == "2024-01-05"
    assert item.last_upgraded_on != "2024-01-10"
    assert item.lifecycle_id == "ema20_reclaim_rising:S-P0:2024-01-03"
    assert item.structure.structure_id == "S-P0"
    assert item.state == "confirmed"
    assert item.current_conditions_confirmed is True
    assert "颜色转黑关闭本轮" in item.invalidation_cn
    assert "C 点永久失效" in item.invalidation_cn
