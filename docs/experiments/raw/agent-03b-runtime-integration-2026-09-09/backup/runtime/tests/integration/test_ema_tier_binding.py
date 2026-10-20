"""EMA20 早期转强「分档绑定」口径门禁。

复核结论要求：candidate 底部允许绑定 EMA20 早期转强，但只进入
``early_watch``，**不视为结构确认或买入信号**；后续结构确认、共同确认和
长周期改善沿用同一 ``structure_id`` 逐级升级；触及 C 永久失效；转黑只关闭
转强生命周期。

本文件的断言刻意写死**确切日期 + 确切档位链 + 确切事件条数**。只写
「有事件产生」这种存在性断言毫无意义——把档位判断整段删掉照样能过。
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.types import (
    Provenance,
    Severity,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.research.outcomes import build_forward_outcomes
from lei_signal.rules.ema_reclaim_tiers import (
    EARLY_WATCH_SUB_RULES,
    SUB_RULE_BY_TIER,
    TIER_EARLY_WATCH,
    TIER_JOINT_CONFIRMED,
    TIER_LADDER,
    TIER_LONG_TREND_IMPROVED,
    TIER_RANK,
    TIER_SEVERITY,
    TIER_STRENGTH,
    TIER_STRUCTURE_CONFIRMED,
    detect_structure_bound_ema_reclaim,
)
from lei_signal.state.machine import run_state_machine

# 索引固定为 2024-01-01 起的工作日：
# 0=01-01 1=01-02 2=01-03 3=01-04 4=01-05 5=01-08 6=01-09 7=01-10 8=01-11 9=01-12
_INDEX = pd.bdate_range("2024-01-01", periods=10)


def _frame(
    *,
    close: list[float],
    ema20: list[float],
    sma20: list[float],
    color: list[str],
    long_improving: list[bool] | None = None,
) -> pd.DataFrame:
    size = len(close)
    improving = long_improving if long_improving is not None else [False] * size
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
            "long_trend": ["unknown"] * size,
            "long_is_improving": improving,
            "long_is_supportive": [False] * size,
        },
        index=_INDEX[:size],
    )


def _ladder_frame() -> pd.DataFrame:
    """一条能依次点亮全部四档的行情。

    * 01-02 收盘重新站上 EMA20（前一日在下方，EMA20 向上）→ 开启观察
    * 01-11 SMA20 首次转为上行且收盘在其上方 → 共同确认
    * 01-12 长周期转为改善 → 长周期改善
    """
    return _frame(
        close=[100, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        ema20=[101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 105.5],
        # 前八日 SMA20 单调下行 → 共同确认不成立；第九日起转上行
        sma20=[110, 109, 108, 107, 106, 105, 104, 103.5, 104, 104.5],
        color=["green"] * 10,
        long_improving=[False] * 9 + [True],
    )


def _structure(
    *,
    confirmed: date | None,
    invalidated: date | None = None,
    status: StructureStatus = StructureStatus.CANDIDATE,
) -> StructureInstance:
    return StructureInstance(
        structure_id="S-TIER",
        symbol="600000",
        structure_type="bottom_C",
        side="bottom",
        detected_date=date(2024, 1, 1),
        confirmed_date=confirmed,
        invalidated_date=invalidated,
        c_price=95.0,
        neckline=105.0,
        status=status,
        provenance=Provenance.LEI_EXPLICIT,
    )


def _tiers(events: list) -> list[tuple[date, str]]:
    return [(event.available_date, event.evidence["tier"]) for event in events]


# --------------------------------------------------------------------------
# 1. 档位阶梯本身
# --------------------------------------------------------------------------


def test_tier_ladder_is_strictly_ordered_and_fully_specified() -> None:
    """阶梯顺序、强度、严重度必须整体单调，且每档都有独立 sub_rule。"""
    assert TIER_LADDER == (
        TIER_EARLY_WATCH,
        TIER_STRUCTURE_CONFIRMED,
        TIER_JOINT_CONFIRMED,
        TIER_LONG_TREND_IMPROVED,
    )
    ranks = [TIER_RANK[tier] for tier in TIER_LADDER]
    assert ranks == [1, 2, 3, 4]

    strengths = [TIER_STRENGTH[tier] for tier in TIER_LADDER]
    assert strengths == sorted(strengths), "强度必须随档位单调不降"
    assert strengths[0] < strengths[-1], "观察档强度必须明显低于最高档"

    sub_rules = [SUB_RULE_BY_TIER[tier] for tier in TIER_LADDER]
    assert len(set(sub_rules)) == 4, "每档必须有独立 sub_rule，否则研究层无法分档"

    # early_watch 必须而且只能是观察档
    assert set(EARLY_WATCH_SUB_RULES) == {SUB_RULE_BY_TIER[TIER_EARLY_WATCH]}
    assert TIER_SEVERITY[TIER_EARLY_WATCH] is Severity.WATCH
    assert TIER_SEVERITY[TIER_STRUCTURE_CONFIRMED] is Severity.IMPORTANT


# --------------------------------------------------------------------------
# 2. 候选绑定与逐级升级
# --------------------------------------------------------------------------


def test_candidate_structure_opens_at_early_watch_and_is_not_a_buy_signal() -> None:
    """候选期绑定必须落在 early_watch，且显式标记为非买入。"""
    frame = _ladder_frame()
    structure = _structure(confirmed=None)

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    assert _tiers(events) == [(date(2024, 1, 2), TIER_EARLY_WATCH)], (
        "候选结构只应在转强日开启一条观察，且档位必须是 early_watch"
    )
    only = events[0]
    assert only.evidence["sub_rule"] == SUB_RULE_BY_TIER[TIER_EARLY_WATCH]
    assert only.evidence["is_buy_signal"] is False
    assert only.evidence["is_upgrade"] is False
    assert only.evidence["structure_status_at_event"] == "candidate"
    assert only.severity is Severity.WATCH
    assert only.strength == TIER_STRENGTH[TIER_EARLY_WATCH]
    assert "不构成结构确认或买入" in only.reason_cn


def test_full_ladder_upgrades_in_place_on_one_lifecycle() -> None:
    """四档必须按确切日期依次升级，且**全部共享同一条观察实例**。"""
    frame = _ladder_frame()
    structure = _structure(
        confirmed=date(2024, 1, 5), status=StructureStatus.CONFIRMED
    )

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    assert _tiers(events) == [
        (date(2024, 1, 2), TIER_EARLY_WATCH),
        (date(2024, 1, 5), TIER_STRUCTURE_CONFIRMED),
        (date(2024, 1, 11), TIER_JOINT_CONFIRMED),
        (date(2024, 1, 12), TIER_LONG_TREND_IMPROVED),
    ]

    lifecycle_ids = {event.lifecycle_id for event in events}
    assert lifecycle_ids == {"ema20_reclaim_rising:S-TIER:2024-01-02"}, (
        "升级不得重开观察实例：四条事件必须共享开启日的 lifecycle_id"
    )
    assert [event.evidence["is_upgrade"] for event in events] == [
        False,
        True,
        True,
        True,
    ]
    assert {event.evidence["opened_on"] for event in events} == {"2024-01-02"}
    # 买入标记：只有 early_watch 是 False
    assert [event.evidence["is_buy_signal"] for event in events] == [
        False,
        True,
        True,
        True,
    ]


def test_confirmed_before_reclaim_opens_directly_at_confirmed_tier() -> None:
    """转强发生时结构已确认 → 直接从结构确认档开启，不应先补一条观察档。"""
    frame = _ladder_frame()
    structure = _structure(
        confirmed=date(2024, 1, 1), status=StructureStatus.CONFIRMED
    )

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    assert _tiers(events)[0] == (date(2024, 1, 2), TIER_STRUCTURE_CONFIRMED)
    assert TIER_EARLY_WATCH not in [event.evidence["tier"] for event in events]


def test_tier_never_downgrades_and_never_repeats() -> None:
    """升到共同确认后，共同确认条件消失不得回落，也不得重复发同档事件。"""
    frame = _frame(
        close=[100, 103, 104, 105, 106, 107],
        ema20=[101, 101.5, 102, 102.5, 103, 103.5],
        # 收盘全程在 SMA20 之上；SMA20 仅 01-03 一天上行 → 共同确认只成立一天
        sma20=[102, 101, 101.5, 101.0, 100.5, 100.0],
        color=["green"] * 6,
    )
    structure = _structure(
        confirmed=date(2024, 1, 1), status=StructureStatus.CONFIRMED
    )

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])
    tiers = _tiers(events)

    assert tiers == [
        (date(2024, 1, 2), TIER_STRUCTURE_CONFIRMED),
        (date(2024, 1, 3), TIER_JOINT_CONFIRMED),
    ], "共同确认条件消失后不得回落，也不得再发同档事件"


# --------------------------------------------------------------------------
# 3. 终止语义：触及 C 永久失效 / 转黑只关转强
# --------------------------------------------------------------------------


def test_c_touch_permanently_ends_the_observation() -> None:
    """结构在 01-05 触及 C 失效 → 当天起不得再有任何事件，含升级。"""
    frame = _ladder_frame()
    structure = _structure(
        confirmed=date(2024, 1, 3),
        invalidated=date(2024, 1, 5),
        status=StructureStatus.INVALIDATED,
    )

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    assert _tiers(events) == [
        (date(2024, 1, 2), TIER_EARLY_WATCH),
        (date(2024, 1, 3), TIER_STRUCTURE_CONFIRMED),
    ]
    assert all(event.available_date < date(2024, 1, 5) for event in events), (
        "C 触及日当天及之后必须彻底静默——结构已永久失效"
    )


def test_black_closes_only_the_strength_lifecycle_and_allows_a_new_one() -> None:
    """转黑关闭转强生命周期，但结构存活；之后再次转强开的是**新**实例。"""
    frame = _frame(
        close=[100, 103, 104, 103, 100, 105],
        ema20=[101, 101.5, 102, 102.5, 103, 103.5],
        sma20=[110, 110, 110, 110, 110, 110],
        # 01-04 转黑
        color=["green", "green", "green", "black", "green", "green"],
    )
    structure = _structure(confirmed=None)

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    assert _tiers(events) == [
        (date(2024, 1, 2), TIER_EARLY_WATCH),
        (date(2024, 1, 8), TIER_EARLY_WATCH),
    ]
    lifecycle_ids = [event.lifecycle_id for event in events]
    assert lifecycle_ids[0] != lifecycle_ids[1], (
        "转黑后重新转强必须开启新观察实例，不能续用旧 lifecycle_id"
    )
    assert lifecycle_ids == [
        "ema20_reclaim_rising:S-TIER:2024-01-02",
        "ema20_reclaim_rising:S-TIER:2024-01-08",
    ]
    # 结构本身没有被转黑弄失效
    assert structure.invalidated_date is None
    assert structure.status is StructureStatus.CANDIDATE


# --------------------------------------------------------------------------
# 4. 状态机：观察档不得抬升机会阶段
# --------------------------------------------------------------------------


def test_early_watch_alone_never_lifts_stage_to_early_strength() -> None:
    """纯候选观察档只能停在底部观察，绝不能越过「结构确认」升到「早期转强」。"""
    frame = _ladder_frame()
    structure = _structure(confirmed=None)
    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    history = run_state_machine(frame, [structure], ema_reclaim_events=events)
    state = next(item for item in history if item.day == date(2024, 1, 2))

    assert state.early_watch_by_structure.get("S-TIER") is True
    assert state.early_strength_by_structure.get("S-TIER", False) is False
    assert state.opportunity_stage is Stage.BOTTOM_WATCH, (
        "候选底部的 EMA20 转强只是观察，不构成结构确认或买入"
    )
    assert any("观察档" in reason for reason in state.reasons), (
        "观察档必须在理由里可见，否则界面上会凭空消失"
    )
    # 全程都不得出现 EARLY_STRENGTH
    assert all(item.opportunity_stage is not Stage.EARLY_STRENGTH for item in history)


def test_confirmed_tier_does_lift_stage_to_early_strength() -> None:
    """对照组：结构确认档必须照常点亮早期转强，否则上面那条就是假通过。"""
    frame = _ladder_frame()
    structure = _structure(
        confirmed=date(2024, 1, 1), status=StructureStatus.CONFIRMED
    )
    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])

    history = run_state_machine(frame, [structure], ema_reclaim_events=events)
    state = next(item for item in history if item.day == date(2024, 1, 2))

    assert state.early_strength_by_structure.get("S-TIER") is True
    assert state.opportunity_stage is Stage.EARLY_STRENGTH


# --------------------------------------------------------------------------
# 5. 研究层分档
# --------------------------------------------------------------------------


def _random_bars(rows: int = 700, seed: int = 303) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.6, rows))
    return pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.3, rows),
            "high": close + rng.uniform(0.2, 1.8, rows),
            "low": close - rng.uniform(0.2, 1.8, rows),
            "close": close,
            "volume": rng.integers(500_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2022-01-03", periods=rows),
    )


def test_forward_outcomes_keep_every_tier_in_its_own_bucket() -> None:
    """前向收益必须按档分开：候选样本不得并入已确认档的胜率基线。"""
    result = analyze_bars("600000", _random_bars(), build_history=True)
    outcomes = build_forward_outcomes(result)

    assert "signal_tier" in outcomes.columns
    assert "is_buy_signal" in outcomes.columns

    ema = outcomes[outcomes["signal_key"].str.startswith("ema20_reclaim_rising")]
    assert not ema.empty, "样例必须产出 EMA20 转强信号，否则本测试形同虚设"

    # 每一档独占一个 signal_key，档位与 key 一一对应
    pairs = set(map(tuple, ema[["signal_tier", "signal_key"]].dropna().to_numpy()))
    for tier, key in pairs:
        assert key == f"ema20_reclaim_rising:{SUB_RULE_BY_TIER[tier]}"
    assert len({key for _, key in pairs}) == len({tier for tier, _ in pairs})

    # 观察档必须存在，且是唯一被标记为非买入的档
    non_buy = set(ema.loc[ema["is_buy_signal"] == False, "signal_tier"])  # noqa: E712
    assert non_buy == {TIER_EARLY_WATCH}

    early = ema[ema["signal_tier"] == TIER_EARLY_WATCH]
    confirmed = ema[ema["signal_tier"] == TIER_STRUCTURE_CONFIRMED]
    assert not early.empty and not confirmed.empty
    assert set(early["signal_key"]).isdisjoint(set(confirmed["signal_key"]))


def test_pipeline_binds_candidate_stage_reclaims_end_to_end() -> None:
    """端到端：完整管线必须真的产出候选档事件，且都绑定在未确认结构上。"""
    result = analyze_bars("600000", _random_bars(), build_history=True)
    by_id = {s.structure_id: s for s in result.structures}

    early = [
        event
        for event in result.events
        if event.evidence.get("sub_rule") in EARLY_WATCH_SUB_RULES
    ]
    assert early, "放开候选绑定后，端到端必须能看到 early_watch 事件"

    for event in early:
        structure = by_id[event.structure_id]
        confirmed = structure.confirmed_date
        assert confirmed is None or event.available_date < confirmed, (
            f"early_watch 绑定到了已确认结构 {event.structure_id}"
        )


def test_upgrade_events_share_valid_until_with_their_opening_event() -> None:
    """同一观察实例内所有事件共享 valid_until，升级不得截断开启事件。"""
    result = analyze_bars("600000", _random_bars(), build_history=True)
    buckets: dict[str, list] = {}
    for event in result.events:
        if event.rule_id != "ema20_reclaim_rising":
            continue
        buckets.setdefault(event.lifecycle_id or "", []).append(event)

    multi = {key: value for key, value in buckets.items() if len(value) > 1}
    assert multi, "样例必须包含发生过升级的观察实例"

    for lifecycle_id, group in multi.items():
        ends = {event.valid_until for event in group}
        assert len(ends) == 1, f"{lifecycle_id} 同实例 valid_until 不一致：{ends}"
        assert None not in ends


class _StreamlitRecorder:
    """记录 UI 渲染调用，用于在无浏览器环境下断言展示口径。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def info(self, body: str) -> None:
        self.calls.append(("info", body))

    def success(self, body: str) -> None:
        self.calls.append(("success", body))

    def warning(self, body: str) -> None:
        self.calls.append(("warning", body))

    def caption(self, body: str) -> None:
        self.calls.append(("caption", body))


def _render_watch(state, monkeypatch) -> _StreamlitRecorder:  # type: ignore[no-untyped-def]
    from lei_signal.ui import app as ui_app

    recorder = _StreamlitRecorder()
    monkeypatch.setattr(ui_app, "st", recorder)
    ui_app._render_early_watch(state)
    return recorder


def test_ui_stays_silent_when_no_candidate_early_watch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """没有观察档时不得渲染任何内容——避免制造「有信号」的错觉。"""
    result = analyze_bars("600000", _random_bars(), build_history=True)
    state = result.history[-1]
    object.__setattr__(state, "early_watch_by_structure", {"S-1": False, "S-2": False})

    assert _render_watch(state, monkeypatch).calls == []


def test_ui_shows_early_watch_as_observation_not_buy(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """观察档必须可见，且措辞必须否定「结构确认 / 买入 / 抬阶段」。"""
    result = analyze_bars("600000", _random_bars(), build_history=True)
    state = result.history[-1]
    object.__setattr__(
        state,
        "early_watch_by_structure",
        {"S-BOTTOM-2": True, "S-BOTTOM-9": True, "S-BOTTOM-4": False},
    )

    calls = _render_watch(state, monkeypatch).calls
    assert len(calls) == 1
    kind, body = calls[0]

    # 必须是中性提示，不能用 success（绿色成功态会被读成「达标」）
    assert kind == "info"
    assert "2 个" in body
    assert "`S-BOTTOM-2`" in body and "`S-BOTTOM-9`" in body
    assert "S-BOTTOM-4" not in body, "未激活的结构不得出现在观察档列表里"
    for phrase in ("尚未确认", "不计入结构确认", "不构成买入信号", "不会抬升"):
        assert phrase in body, f"观察档文案缺少必要否定语：{phrase}"


def test_ui_early_watch_ids_are_sorted_and_deduped(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """展示顺序必须稳定，否则同一状态每次刷新排列不同，无法复核。"""
    result = analyze_bars("600000", _random_bars(), build_history=True)
    state = result.history[-1]
    object.__setattr__(
        state,
        "early_watch_by_structure",
        {"S-9": True, "S-1": True, "S-5": True},
    )

    _, body = _render_watch(state, monkeypatch).calls[0]
    assert body.index("`S-1`") < body.index("`S-5`") < body.index("`S-9`")
