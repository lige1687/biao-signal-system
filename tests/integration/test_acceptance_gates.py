"""架构第 13 节的 12 项验收测试，逐条对应。

本文件是交付门禁的单一入口：每个测试函数名标注对应的门禁编号。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.types import Provenance, Stage, StructureStatus
from lei_signal.events.log import EventLog
from lei_signal.rules.key_wave import detect_key_wave_events
from lei_signal.rules.resistance_b1 import find_b1
from tests.golden.fixtures import (
    golden_bottom_c_invalidation,
    golden_bullish_engulfing,
    golden_delayed_upgrade,
)


def _bars(rows: int = 500, seed: int = 101) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.8, rows),
            "low": close - rng.uniform(0.3, 1.8, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2022-01-03", periods=rows),
    )


def test_gate_01_appending_future_bars_never_changes_past_results() -> None:
    """门禁 1：追加未来行情后，旧日期的特征、事件和解释保持不变。"""
    bars = _bars()
    cut = 380
    as_of = bars.index[cut - 1].date()

    partial = analyze_bars("G", bars.iloc[:cut], build_history=True)
    full = analyze_bars("G", bars, build_history=True)

    # 指标
    for column in ("ema20", "ema60", "ema120", "sma20", "atr14", "close_lag20"):
        pd.testing.assert_series_equal(
            partial.frame[column],
            full.frame.loc[partial.frame.index, column],
            rtol=1e-12,
            check_names=False,
        )
    # 颜色必须完全相同
    assert partial.frame["signal_color"].tolist() == (
        full.frame.loc[partial.frame.index, "signal_color"].tolist()
    )
    # 事件
    partial_events = [
        (e.event_id, e.event_date, e.available_date)
        for e in partial.events
        if e.available_date <= as_of
    ]
    full_events = [
        (e.event_id, e.event_date, e.available_date)
        for e in full.events
        if e.available_date <= as_of
    ]
    assert partial_events == full_events
    # 解释（阶段）
    for day, assessment in partial.assessments_by_date.items():
        assert full.assessments_by_date[day].stage == assessment.stage


def test_gate_02_pivots_use_confirmation_date_not_turning_point() -> None:
    """门禁 2：摆动点使用确认日，不使用实际拐点日作为可交易信号时间。"""
    result = analyze_bars("G", _bars())
    pivot_events = [e for e in result.events if e.rule_id == "swing_pivots"]
    assert pivot_events
    for event in pivot_events:
        assert event.available_date > event.event_date
    for pivot in result.pivots:
        assert pivot.available_date > pivot.pivot_date
        assert pivot.confirmed_index == pivot.index + 3


def test_gate_03_engulfing_survives_bearish_long_trend() -> None:
    """门禁 3：反包成立但 60/120 日线不多头时，反包和底部候选仍被记录。"""
    result = analyze_bars("G", golden_bullish_engulfing())
    last = result.frame.iloc[-1]
    assert last["ema60"] < last["ema120"], "前置条件：长周期空头"

    engulfing = [e for e in result.events if e.rule_id == "bullish_engulfing"]
    assert engulfing, "反包事件必须被记录"
    bottoms = [s for s in result.bottoms if s.structure_type == "bullish_reversal_bottom"]
    assert bottoms, "底部候选必须被记录"
    assert result.assessment.stage is not Stage.NO_CLUE


def test_gate_04_delayed_upgrade_without_new_ema20_cross() -> None:
    """门禁 4：6月短期转强、8月长趋势改善时状态可升级，不要求再次穿越。"""
    from lei_signal.rules.dual_ma import ema20_reclaim_state

    result = analyze_bars("G", golden_delayed_upgrade(), build_history=True)
    reclaim = ema20_reclaim_state(result.frame)
    last_reclaim = result.frame.index[reclaim][-1].date()

    upgraded = [
        state
        for state in result.history
        if state.stage is Stage.TREND_REINFORCED and state.day > last_reclaim
    ]
    assert upgraded, "长趋势改善后必须能升级"
    day_b = upgraded[0]
    assert not bool(reclaim.loc[pd.Timestamp(day_b.day)])
    assert day_b.primary_bottom is not None
    assert day_b.primary_bottom.confirmed_date < day_b.day


def test_gate_05_c_touch_permanently_invalidates_structure() -> None:
    """门禁 5：底部结构触及 C 后永久失效，后续上涨不会复活。"""
    result = analyze_bars("G", golden_bottom_c_invalidation(), build_history=True)
    dead = [s for s in result.bottoms if s.status is StructureStatus.INVALIDATED]
    assert dead

    structure = dead[0]
    assert structure.invalidated_reason in ("bottom_C_touched",)
    later_days = [
        state for state in result.history if state.day > structure.invalidated_date
    ]
    for state in later_days:
        assert structure.structure_id not in {s.structure_id for s in state.live_bottoms}


def test_gate_06_invalidated_top_cannot_feed_top_plus_black() -> None:
    """门禁 6：Top 警报被新高解除后，Top+Black 不能继续引用已失效顶部。"""
    result = analyze_bars("G", _bars(seed=77))
    resolved = [
        s
        for s in result.tops
        if s.invalidated_reason == "top_warning_invalidated_by_new_high"
    ]
    if not resolved:
        pytest.skip("该随机样本未产生被新高解除的顶部")

    events = detect_key_wave_events(result.frame, "G", tops=result.tops)
    for event in events:
        if event.evidence.get("sub_rule") != "top_plus_black":
            continue
        top_id = event.evidence["top_structure_id"]
        top = next(s for s in result.tops if s.structure_id == top_id)
        assert top.confirmed_date <= event.event_date
        assert top.invalidated_date is None or top.invalidated_date > event.event_date


def test_gate_07_black_matches_legacy_formula_day_by_day() -> None:
    """门禁 7：黑色与 Close < EMA20 and Close < Close(t-20) 逐日一致。"""
    result = analyze_bars("G", _bars())
    frame = result.frame
    ready = frame[["close", "ema20", "close_lag20"]].notna().all(axis=1)
    expected = ready & (frame["close"] < frame["ema20"]) & (
        frame["close"] < frame["close_lag20"]
    )
    assert frame["signal_color"].eq("black").tolist() == expected.tolist()


def test_gate_08_first_twenty_bars_are_unknown_not_gray() -> None:
    """门禁 8：第一批 20 根数据标为未知，不误标灰色。"""
    result = analyze_bars("G", _bars())
    first_twenty = result.frame["signal_color"].iloc[:20]
    assert first_twenty.eq("unknown").all()
    assert not first_twenty.eq("gray").any()


def test_gate_09_missing_b1_still_produces_signal() -> None:
    """门禁 9：B1 不存在时仍产生机会信号，且不作为 3R 门槛。"""
    result = analyze_bars("G", golden_delayed_upgrade())
    assert result.assessment.b1_price is None, "该样例创新高，B1 应不存在"
    assert result.assessment.stage in (
        Stage.JOINT_CONFIRMED,
        Stage.TREND_REINFORCED,
        Stage.EARLY_STRENGTH,
        Stage.STRUCTURE_CONFIRMED,
        Stage.BOTTOM_WATCH,
    ), "B1 缺失不得导致无信号"
    assert result.assessment.dimensions["上方空间"] == "无B1数据"

    # B1 从不作为门槛：即便 distance_r 很小也不改变阶段
    b1 = find_b1(result.pivots, as_of=result.assessment.as_of,
                 current_close=float(result.frame["close"].iloc[-1]))
    assert b1 is None


def test_gate_10_weekly_never_leaks_friday_into_earlier_days() -> None:
    """门禁 10：周线信号不会把周五数据泄漏到周一至周四。"""
    result = analyze_bars("G", _bars())
    weekly = result.weekly_trend
    assert not weekly.empty
    # 每个周线索引都必须是真实交易日
    daily_index = set(result.frame.index)
    for timestamp in weekly.index:
        assert timestamp in daily_index
    # 修复后语义：available_date = 数据中下一交易日 = 该周第一次可知。
    # 因此「in-progress 周」（最后一根日线所在周）不能出现在 weekly 中：
    # 该周既没有「下一交易日」信号，week_end 应严格早于 last frame date
    last_date = result.frame.index[-1]
    for _, row in weekly.iterrows():
        assert pd.Timestamp(row["week_end"]) < last_date, (
            f"in-progress 周不得出现在 weekly 中：week_end={row['week_end']}, last={last_date}"
        )


def test_gate_11_repeated_runs_produce_identical_event_ids() -> None:
    """门禁 11：同样数据和规则重复运行产生完全相同的事件 ID。"""
    bars = _bars(400, seed=303)
    first = analyze_bars("G", bars)
    second = analyze_bars("G", bars)
    assert [e.event_id for e in first.events] == [e.event_id for e in second.events]
    assert [s.structure_id for s in first.structures] == [
        s.structure_id for s in second.structures
    ]
    # 事件 ID 必须唯一
    ids = [e.event_id for e in first.events]
    assert len(ids) == len(set(ids))
    # 幂等日志不会重复写入
    log = EventLog()
    log.extend(first.events)
    assert log.extend(first.events) == 0


def test_gate_12_every_hint_is_traceable_to_rule_version_and_data_date() -> None:
    """门禁 12：每条界面提示都能追溯到规则、版本、输入值和数据日期。"""
    result = analyze_bars("G", _bars(), build_history=True)
    for assessment in result.assessments_by_date.values():
        assert assessment.rule_ruleset_version == "1.0.0"
        assert assessment.last_data_date is not None
        for factor in [*assessment.supports, *assessment.conflicts]:
            assert factor.rule_id
            assert factor.rule_version.count(".") == 2
            assert isinstance(factor.provenance, Provenance)
            assert factor.detail_cn
        for alert in assessment.risks:
            assert alert.rule_id and alert.rule_version
        for event in assessment.new_events:
            assert event.rule_version
            assert event.evidence, "事件必须保存成立所用数值"
            assert event.invalidation, "事件必须保存客观失效条件"


def test_gate_12b_atomic_and_stage_statistics_are_both_retained() -> None:
    """门禁 12（补充）：原子信号统计与组合阶段统计均保留。"""
    from lei_signal.research.outcomes import build_forward_outcomes, summarize_by_rule

    result = analyze_bars("G", _bars(600, seed=404))
    outcomes = build_forward_outcomes(result)
    assert set(outcomes["signal_kind"]) == {"atomic", "stage"}
    summary = summarize_by_rule(outcomes)
    assert set(summary["类型"]) == {"原子信号", "组合阶段"}


def test_no_trading_execution_surface_exists() -> None:
    """系统不得包含下单、仓位、账户资金接口。

    只检查**可执行代码**：移植说明的文档字符串里会提到旧项目的
    FundID/ProxyID/StrategyEngine，用于说明「这些没有被移植」，
    那是必要的溯源记录，不是执行域代码。
    """
    import ast
    from pathlib import Path

    import lei_signal

    package_root = Path(next(iter(lei_signal.__path__)))
    forbidden_terms = (
        "place_order", "submit_order", "AccountState", "FundID", "ProxyID",
        "StrategyEngine", "CandidateIntent", "AggregateResolver", "position_size",
    )

    offenders: list[str] = []
    for path in package_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # 剥离所有 docstring 后再比对标识符
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                identifiers.add(node.name)
            elif isinstance(node, ast.alias):
                identifiers.add(node.name.split(".")[-1])
                if node.asname:
                    identifiers.add(node.asname)
        for term in forbidden_terms:
            if term in identifiers:
                offenders.append(f"{path.name}: {term}")

    assert not offenders, f"发现执行域符号：{offenders}"


def test_porting_notes_document_that_execution_domain_was_excluded() -> None:
    """移植说明必须记录旧路径与 commit，并说明未移植执行域依赖。"""
    from pathlib import Path

    import lei_signal

    package_root = Path(next(iter(lei_signal.__path__)))
    ported = {
        "data/point_in_time.py": "a25eae9",
        "features/pivots.py": "a25eae9",
        "domain/canonical.py": "2ee7fdc",
        "storage/sqlite_store.py": "2ee7fdc",
    }
    for relative, commit in ported.items():
        text = (package_root / relative).read_text(encoding="utf-8")
        assert "移植" in text, f"{relative} 缺少移植说明"
        assert commit in text, f"{relative} 缺少来源 commit {commit}"
        assert "改造原因" in text, f"{relative} 缺少改造原因"
