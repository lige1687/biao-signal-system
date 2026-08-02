"""Round 3 修复 D6：UI 按结构展示观察链 —— 端到端状态对象 → 渲染结果。

为什么不写源码字符串检查
------------------------
任务书第八节明确要求「不要只写源码字符串检查，至少增加一个端到端状态对象到
UI 渲染结果的测试」。源码里出现某个字符串，不等于它会在这条状态下被渲染出来
——``if`` 分支写错、早退条件写错，源码检查一样是绿的。

本文件的做法：用一个假的 streamlit 模块**记录所有渲染调用**（方法名 + 参数），
喂进真实的 ``DayState`` + ``StructureInstance``，然后对**捕获到的渲染结果**
做断言：哪些结构出现了、用的是 info 还是 success、文案含不含「尚未确认」。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd
import pytest

from lei_signal.domain.types import (
    LongTrendState,
    Provenance,
    RiskState,
    SignalColor,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.state.machine import DayState, StructureObservation


# ==========================================================================
# 渲染记录器：捕获 streamlit 调用，而不是读源码
# ==========================================================================


@dataclass
class RenderCall:
    """一次渲染调用。"""

    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    @property
    def text(self) -> str:
        """把位置参数里的字符串拼起来，便于文案断言。"""
        parts = [str(a) for a in self.args if isinstance(a, str)]
        return " ".join(parts)


@dataclass
class RecordingStreamlit:
    """最小可用的 streamlit 替身，记录所有调用。

    只实现被 ``_render_per_structure_observations`` 用到的方法。
    任何未实现的方法访问都会抛 AttributeError —— 这是刻意的：
    如果实现改成调用别的渲染方法而测试没跟上，会立刻暴露，
    而不是静默漏掉断言。
    """

    calls: list[RenderCall] = field(default_factory=list)

    def _record(self, method: str):  # noqa: ANN202
        def _inner(*args: Any, **kwargs: Any) -> None:
            self.calls.append(RenderCall(method, args, kwargs))
        return _inner

    def __getattr__(self, name: str):  # noqa: ANN204
        if name in {"markdown", "caption", "info", "success", "warning",
                    "error", "write", "dataframe"}:
            return self._record(name)
        raise AttributeError(
            f"RecordingStreamlit 未实现 st.{name}()；"
            "若实现新增了渲染调用，请同步更新本替身与断言"
        )

    # -------- 查询辅助 --------

    def methods(self) -> list[str]:
        return [call.method for call in self.calls]

    def of(self, method: str) -> list[RenderCall]:
        return [call for call in self.calls if call.method == method]

    def all_text(self) -> str:
        return "\n".join(call.text for call in self.calls)

    def frames(self) -> list[pd.DataFrame]:
        """所有 st.dataframe() 渲染出的表格。"""
        found: list[pd.DataFrame] = []
        for call in self.of("dataframe"):
            for arg in call.args:
                if isinstance(arg, pd.DataFrame):
                    found.append(arg)
        return found


@pytest.fixture()
def recorder(monkeypatch):  # noqa: ANN001, ANN201
    """把 ui.app 里的 st 换成记录器。"""
    from lei_signal.ui import app

    fake = RecordingStreamlit()
    monkeypatch.setattr(app, "st", fake)
    return fake


# ==========================================================================
# 测试用状态对象
# ==========================================================================


def _structure(
    *,
    sid: str,
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


def _day_state(
    *,
    day: date = date(2024, 1, 12),
    stage: Stage = Stage.BOTTOM_WATCH,
    color: SignalColor = SignalColor.GREEN,
    live: list[StructureInstance],
    observations: dict[str, StructureObservation],
    risk: RiskState = RiskState.NORMAL,
) -> DayState:
    early_watch = {
        sid: True for sid, obs in observations.items()
        if obs.tier == "early_watch"
    }
    early_strength = {
        sid: True for sid, obs in observations.items()
        if obs.tier is not None and obs.tier != "early_watch"
    }
    return DayState(
        day=day,
        opportunity_stage=stage,
        risk_state=risk,
        color=color,
        live_bottoms=live,
        primary_bottom=live[0] if live else None,
        observations=observations,
        early_watch_by_structure=early_watch,
        early_strength_by_structure=early_strength,
        daily_long=LongTrendState.UNKNOWN,
        weekly_long=LongTrendState.UNKNOWN,
    )


def _observation(
    *,
    sid: str,
    tier: str | None,
    lifecycle: str = "ema20_reclaim_rising:S:2024-01-02",
    opened: date = date(2024, 1, 2),
    upgraded: date = date(2024, 1, 2),
) -> StructureObservation:
    return StructureObservation(
        structure_id=sid,
        lifecycle_id=lifecycle,
        tier=tier,
        opened_on=opened,
        last_upgraded_on=upgraded,
    )


# ==========================================================================
# 1. 必须显示全部七个字段
# ==========================================================================


def test_render_shows_all_seven_required_columns(recorder) -> None:  # noqa: ANN001
    """任务书第八节：至少显示结构ID/档位/开启日/升级日/是否有效/失效原因/等待条件。"""
    from lei_signal.ui.app import _render_per_structure_observations

    structure = _structure(
        sid="S-CONFIRMED", confirmed=date(2024, 1, 5),
        status=StructureStatus.CONFIRMED,
    )
    state = _day_state(
        stage=Stage.JOINT_CONFIRMED,
        live=[structure],
        observations={
            "S-CONFIRMED": _observation(
                sid="S-CONFIRMED", tier="joint_confirmed",
                opened=date(2024, 1, 2), upgraded=date(2024, 1, 11),
            )
        },
    )
    _render_per_structure_observations(state, [structure])

    frames = recorder.frames()
    assert frames, "必须渲染出逐结构表格（而不是只有全局布尔）"
    columns = set(frames[0].columns)
    for required in (
        "结构ID", "档位", "生命周期ID", "开启日", "最近升级日",
        "当前是否有效", "失效原因", "下一步等待条件",
    ):
        assert required in columns, f"逐结构表缺少必需列「{required}」，实际列 {sorted(columns)}"


def test_render_shows_exact_lifecycle_dates(recorder) -> None:  # noqa: ANN001
    """开启日与最近升级日必须是**该实例的真实日期**，不能写死或取当天。"""
    from lei_signal.ui.app import _render_per_structure_observations

    structure = _structure(
        sid="S-A", confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED
    )
    state = _day_state(
        day=date(2024, 1, 12),
        stage=Stage.TREND_REINFORCED,
        live=[structure],
        observations={
            "S-A": _observation(
                sid="S-A", tier="long_trend_improved",
                opened=date(2024, 1, 2), upgraded=date(2024, 1, 12),
            )
        },
    )
    _render_per_structure_observations(state, [structure])

    row = recorder.frames()[0].iloc[0]
    assert row["开启日"] == "2024-01-02"
    assert row["最近升级日"] == "2024-01-12"
    assert row["档位"] == "长周期改善档"
    assert row["当前是否有效"] is True or row["当前是否有效"] == True  # noqa: E712


# ==========================================================================
# 2. 「尚未确认」文案只能出现在 candidate 结构上
# ==========================================================================


def test_only_candidate_structures_are_described_as_unconfirmed(recorder) -> None:  # noqa: ANN001
    """已确认结构的渲染结果里不得出现「尚未确认」。"""
    from lei_signal.ui.app import _render_per_structure_observations

    confirmed = _structure(
        sid="S-CONFIRMED", confirmed=date(2024, 1, 5),
        status=StructureStatus.CONFIRMED,
    )
    state = _day_state(
        stage=Stage.EARLY_STRENGTH,
        live=[confirmed],
        observations={
            "S-CONFIRMED": _observation(
                sid="S-CONFIRMED", tier="structure_confirmed",
                upgraded=date(2024, 1, 5),
            )
        },
    )
    _render_per_structure_observations(state, [confirmed])

    text = recorder.all_text()
    assert "尚未确认" not in text, (
        "已确认结构的渲染结果不得出现「尚未确认」文案"
    )
    # 表格里也不能出现
    frame_text = recorder.frames()[0].to_string()
    assert "尚未确认" not in frame_text


def test_candidate_structure_is_described_as_unconfirmed(recorder) -> None:  # noqa: ANN001
    """对照组：candidate + early_watch 必须明确写「尚未确认」+「不构成买入信号」。"""
    from lei_signal.ui.app import _render_per_structure_observations

    candidate = _structure(sid="S-CAND", confirmed=None)
    state = _day_state(
        stage=Stage.BOTTOM_WATCH,
        live=[candidate],
        observations={
            "S-CAND": _observation(sid="S-CAND", tier="early_watch")
        },
    )
    _render_per_structure_observations(state, [candidate])

    text = recorder.all_text()
    assert "尚未确认" in text, "候选结构必须明确标注尚未确认"
    assert "不构成买入信号" in text, "观察档必须明确写不构成买入信号"


# ==========================================================================
# 3. early_watch 必须用中性 info，不得用绿色 success
# ==========================================================================


def test_early_watch_uses_neutral_info_not_success(recorder) -> None:  # noqa: ANN001
    """观察档用 st.info（中性）；绝不能用 st.success（绿色成功态）。

    这条是 Round 2 变异 M8 的自动化版本：把 info 改成 success 必须变红。
    """
    from lei_signal.ui.app import _render_per_structure_observations

    candidate = _structure(sid="S-CAND", confirmed=None)
    state = _day_state(
        stage=Stage.BOTTOM_WATCH,
        live=[candidate],
        observations={
            "S-CAND": _observation(sid="S-CAND", tier="early_watch")
        },
    )
    _render_per_structure_observations(state, [candidate])

    methods = recorder.methods()
    assert "info" in methods, "候选观察档必须用 st.info 呈现"
    assert "success" not in methods, (
        "观察档不得使用 st.success（绿色成功样式会被读成「条件达成」）"
    )
    # 进一步锁定：含「不构成买入信号」的那条必须是 info
    buy_signal_calls = [
        call for call in recorder.calls if "不构成买入信号" in call.text
    ]
    assert buy_signal_calls, "必须有一条渲染明确写「不构成买入信号」"
    for call in buy_signal_calls:
        assert call.method == "info", (
            f"「不构成买入信号」提示必须用 info，实际用了 {call.method}"
        )


# ==========================================================================
# 4. 已确认结构不得出现在 early_watch 块
# ==========================================================================


def test_confirmed_structure_absent_from_early_watch_block(recorder) -> None:  # noqa: ANN001
    """A 已确认（结构确认档）、B 候选（观察档）→ early_watch 块只能提到 B。"""
    from lei_signal.ui.app import _render_per_structure_observations

    a = _structure(
        sid="S-AAA", confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED
    )
    b = _structure(sid="S-BBB", confirmed=None)
    state = _day_state(
        stage=Stage.EARLY_STRENGTH,
        live=[a, b],
        observations={
            "S-AAA": _observation(
                sid="S-AAA", tier="structure_confirmed",
                lifecycle="ema20_reclaim_rising:S-AAA:2024-01-02",
                upgraded=date(2024, 1, 5),
            ),
            "S-BBB": _observation(
                sid="S-BBB", tier="early_watch",
                lifecycle="ema20_reclaim_rising:S-BBB:2024-01-02",
            ),
        },
    )
    _render_per_structure_observations(state, [a, b])

    # early_watch 提示块 = 含「不构成买入信号」的那条 info
    watch_blocks = [
        call for call in recorder.calls
        if call.method == "info" and "不构成买入信号" in call.text
    ]
    assert watch_blocks, "应存在 early_watch 提示块"
    block_text = "\n".join(call.text for call in watch_blocks)
    assert "S-BBB" in block_text, "候选结构 B 必须出现在观察档块"
    assert "S-AAA" not in block_text, (
        "已确认结构 A 不得出现在 early_watch 块（它已经是结构确认档）"
    )


# ==========================================================================
# 5. 多结构并存时不得只显示主结构
# ==========================================================================


def test_multiple_structures_are_all_rendered(recorder) -> None:  # noqa: ANN001
    """三个结构（确认+转强 / 候选+观察 / 确认无转强）必须全部出现。"""
    from lei_signal.ui.app import _render_per_structure_observations

    a = _structure(
        sid="S-AAA", confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED
    )
    b = _structure(sid="S-BBB", confirmed=None)
    c = _structure(
        sid="S-CCC", confirmed=date(2024, 1, 8), status=StructureStatus.CONFIRMED
    )
    state = _day_state(
        stage=Stage.JOINT_CONFIRMED,
        live=[a, b, c],
        observations={
            "S-AAA": _observation(
                sid="S-AAA", tier="joint_confirmed",
                lifecycle="ema20_reclaim_rising:S-AAA:2024-01-02",
                upgraded=date(2024, 1, 11),
            ),
            "S-BBB": _observation(
                sid="S-BBB", tier="early_watch",
                lifecycle="ema20_reclaim_rising:S-BBB:2024-01-02",
            ),
            # C 没有观察档（确认但无转强）
        },
    )
    _render_per_structure_observations(state, [a, b, c])

    frame = recorder.frames()[0]
    rendered_ids = set(frame["结构ID"])
    for sid in ("S-AAA", "S-BBB", "S-CCC"):
        assert sid in rendered_ids, (
            f"{sid} 未出现在逐结构表中——多结构并存时不得只显示主结构。"
            f"实际渲染 {sorted(rendered_ids)}"
        )
    # C 必须被标为「无观察档」而不是被隐藏
    c_row = frame[frame["结构ID"] == "S-CCC"].iloc[0]
    assert c_row["档位"] == "无观察档"
    assert c_row["当前是否有效"] is True or c_row["当前是否有效"] == True  # noqa: E712


# ==========================================================================
# 6. 高档必须说明绑定的是哪个结构
# ==========================================================================


def test_higher_tiers_state_which_structure_they_bind(recorder) -> None:  # noqa: ANN001
    """共同确认 / 趋势增强必须写清绑定结构，不能只说「双均线向上」。"""
    from lei_signal.ui.app import _render_per_structure_observations

    a = _structure(
        sid="S-JOINT", confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED
    )
    state = _day_state(
        stage=Stage.JOINT_CONFIRMED,
        live=[a],
        observations={
            "S-JOINT": _observation(
                sid="S-JOINT", tier="joint_confirmed",
                upgraded=date(2024, 1, 11),
            )
        },
    )
    _render_per_structure_observations(state, [a])

    text = recorder.all_text()
    assert "S-JOINT" in text, "高档观察必须点名绑定的结构ID"
    # 必须说明是沿用同一结构升级，而非全局条件单独触发
    assert "同一结构" in text or "绑定结构" in text, (
        "必须说明高档是绑定到具体结构的升级"
    )


# ==========================================================================
# 7. 转黑 / 触及 C 的失效原因必须可见
# ==========================================================================


def test_black_close_reason_is_rendered(recorder) -> None:  # noqa: ANN001
    """转黑关闭观察实例时，失效原因必须写明「结构本身仍存活」。"""
    from lei_signal.ui.app import _render_per_structure_observations

    structure = _structure(
        sid="S-BLK", confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED
    )
    state = _day_state(
        stage=Stage.STRUCTURE_CONFIRMED,
        color=SignalColor.BLACK,
        risk=RiskState.BLACK,
        live=[structure],
        observations={
            # 转黑后状态机会删除 tier；这里模拟「实例已关闭」的展示
            "S-BLK": _observation(sid="S-BLK", tier=None),
        },
    )
    _render_per_structure_observations(state, [structure])

    frame = recorder.frames()[0]
    row = frame[frame["结构ID"] == "S-BLK"].iloc[0]
    assert row["当前是否有效"] is False or row["当前是否有效"] == False  # noqa: E712
    assert "转黑" in str(row["失效原因"])
    assert "仍存活" in str(row["失效原因"]), (
        "转黑只关闭转强生命周期，必须说明底部结构本身没有失效"
    )


def test_empty_state_renders_explicit_message(recorder) -> None:  # noqa: ANN001
    """没有结构时必须明确说明，不得渲染空表让用户以为出错。"""
    from lei_signal.ui.app import _render_per_structure_observations

    state = _day_state(stage=Stage.NO_CLUE, live=[], observations={})
    _render_per_structure_observations(state, [])

    assert not recorder.frames(), "无结构时不应渲染空表格"
    text = recorder.all_text()
    assert "没有有效底部结构" in text
