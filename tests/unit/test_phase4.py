"""Phase 4 门禁：组合解释器、支持/冲突矩阵、风险排序与可追溯性。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.interpreter import assessment_to_rows
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.rules_config import risk_priority
from lei_signal.domain.types import Provenance, Stage
from tests.golden.fixtures import (
    golden_bottom_c_invalidation,
    golden_bullish_engulfing,
    golden_delayed_upgrade,
    golden_top_then_black,
)


def _analyze(bars: pd.DataFrame, **kwargs):  # noqa: ANN202
    return analyze_bars("TEST", bars, **kwargs)


# ---------------- 解释快照结构 ----------------


def test_assessment_contains_every_required_section() -> None:
    """架构第 7 节要求的每日解释字段必须齐备。"""
    result = _analyze(golden_delayed_upgrade())
    a = result.assessment
    assert a.stage in set(Stage)
    assert a.dimensions.keys() == {"结构", "短周期", "长周期", "量价", "上方空间"}
    assert a.stage_change_reason_cn
    assert a.rule_ruleset_version == "1.3.0"
    assert a.last_data_date == result.frame.index[-1].date()
    assert a.data_status == "OK"
    # 新增/有效/失效三栏必须存在（可以为空列表，但字段必须有）
    assert isinstance(a.new_events, list)
    assert isinstance(a.active_events, list)
    assert isinstance(a.invalidated_events, list)


def test_no_single_opaque_score_is_produced() -> None:
    """不得输出不透明总分。"""
    a = _analyze(golden_delayed_upgrade()).assessment
    for forbidden in ("score", "total_score", "rating"):
        assert not hasattr(a, forbidden)


def test_dimensions_use_only_declared_labels() -> None:
    result = _analyze(golden_bottom_c_invalidation(), build_history=True)
    allowed = {
        "结构": {"支持", "中性", "冲突"},
        "短周期": {"支持", "中性", "冲突"},
        "长周期": {"支持", "改善中", "冲突"},
        "量价": {"支持", "中性", "冲突"},
        "上方空间": {"通畅", "存在B1阻力", "无B1数据"},
    }
    for assessment in result.assessments_by_date.values():
        for dimension, value in assessment.dimensions.items():
            assert value in allowed[dimension], f"{dimension}={value} 不在允许集合"


# ---------------- 支持与冲突并排 ----------------


def test_conflicts_are_never_hidden_when_long_trend_disagrees() -> None:
    """长周期冲突必须显示为冲突因素，但不得阻止底部线索。"""
    result = _analyze(golden_bullish_engulfing())
    a = result.assessment
    long_conflicts = [f for f in a.conflicts if f.dimension == "长周期"]
    assert long_conflicts, "长周期空头必须列为冲突"
    assert "不会阻止" in long_conflicts[0].detail_cn
    # 同时底部结构必须仍然存在
    assert a.all_live_structures, "长周期冲突下底部结构仍必须保留"
    assert a.stage is not Stage.NO_CLUE


def test_every_factor_is_traceable_to_rule_and_version() -> None:
    """门禁 12：每条提示都能追溯到规则、版本、输入值和数据日期。"""
    result = _analyze(golden_delayed_upgrade(), build_history=True)
    for assessment in result.assessments_by_date.values():
        for factor in [*assessment.supports, *assessment.conflicts]:
            assert factor.rule_id, "因素必须带 rule_id"
            assert factor.rule_version.count(".") == 2, "因素必须带 x.y.z 版本"
            assert isinstance(factor.provenance, Provenance)
            assert factor.detail_cn, "因素必须带中文说明"
        for alert in assessment.risks:
            assert alert.rule_id and alert.rule_version
        assert assessment.last_data_date is not None


def test_research_proxy_factors_are_labelled_in_text() -> None:
    """research_proxy 必须在界面文本中标注「研究代理」。"""
    result = _analyze(golden_bottom_c_invalidation(), build_history=True)
    for assessment in result.assessments_by_date.values():
        for factor in [*assessment.supports, *assessment.conflicts]:
            if factor.provenance is Provenance.RESEARCH_PROXY:
                combined = factor.label_cn + factor.detail_cn
                assert "研究代理" in combined or "代理" in combined, (
                    f"{factor.rule_id} 未标注研究代理"
                )


def test_assessment_rows_export_provenance_flags() -> None:
    rows = assessment_to_rows(_analyze(golden_bullish_engulfing()).assessment)
    assert rows
    kinds = {row["kind"] for row in rows}
    assert kinds <= {"support", "conflict", "risk"}
    for row in rows:
        assert "rule_id" in row and "rule_version" in row
        assert isinstance(row["is_research_proxy"], bool)


# ---------------- 风险优先级 ----------------


def test_risks_are_sorted_by_configured_priority() -> None:
    """多风险并存时必须按配置优先级排序。

    注意：Top+Black 与 Black 是互斥表述（有有效顶部时只报 Top+Black），
    因此多风险日主要来自「触及C + 黑色」这类组合，
    这里跨两个黄金样例收集以确保覆盖。
    """
    order = risk_priority()
    assessments = []
    for bars in (golden_top_then_black(), golden_bottom_c_invalidation()):
        assessments.extend(_analyze(bars, build_history=True).assessments_by_date.values())

    multi_risk_days = 0
    for assessment in assessments:
        codes = [alert.code for alert in assessment.risks]
        for code in codes:
            assert code in order, f"未登记的风险码 {code}"
        priorities = [alert.priority for alert in assessment.risks]
        assert priorities == sorted(priorities), "风险必须按优先级排序"
        if len(assessment.risks) >= 2:
            multi_risk_days += 1

    assert multi_risk_days > 0, "应至少有一天出现多个风险并存"


def test_c_touched_outranks_all_other_risks() -> None:
    """触及C/跌破C 必须排在最前。"""
    result = _analyze(golden_bottom_c_invalidation(), build_history=True)
    found = False
    for assessment in result.assessments_by_date.values():
        codes = [alert.code for alert in assessment.risks]
        if "c_touched_or_broken" in codes:
            found = True
            assert codes[0] == "c_touched_or_broken", "触及C必须排最前"
    assert found, "样例必须出现触及C的交易日"


def test_top_plus_black_outranks_plain_black() -> None:
    order = risk_priority()
    assert order.index("top_plus_black") < order.index("black")
    assert order.index("black") < order.index("active_top_structure")
    assert order.index("active_top_structure") < order.index("turned_gray")


def test_risk_alerts_never_instruct_selling() -> None:
    """风险优先级只决定排序，不自动执行卖出。"""
    result = _analyze(golden_top_then_black(), build_history=True)
    for assessment in result.assessments_by_date.values():
        for alert in assessment.risks:
            text = alert.label_cn + alert.detail_cn
            for forbidden in ("立即卖出", "必须卖出", "建议卖出", "自动下单", "清仓"):
                assert forbidden not in text


# ---------------- 事件三栏 ----------------


def test_invalidated_events_are_listed_separately_after_c_touch() -> None:
    """已失效事件必须单独列出，不是静默消失。"""
    result = _analyze(golden_bottom_c_invalidation(), build_history=True)
    dead_structures = [
        s for s in result.bottoms if s.invalidated_date is not None
    ]
    assert dead_structures

    after = [
        assessment
        for day, assessment in result.assessments_by_date.items()
        if day > dead_structures[0].invalidated_date
    ]
    assert after
    assert any(a.invalidated_events for a in after), "触及C后必须有事件进入已失效栏"


def test_new_events_only_contain_today() -> None:
    result = _analyze(golden_delayed_upgrade(), build_history=True)
    for day, assessment in result.assessments_by_date.items():
        for event in assessment.new_events:
            assert event.available_date == day


def test_active_events_exclude_dead_structures() -> None:
    result = _analyze(golden_bottom_c_invalidation(), build_history=True)
    for day, assessment in result.assessments_by_date.items():
        dead_ids = {
            s.structure_id
            for s in result.structures
            if s.invalidated_date is not None and s.invalidated_date <= day
        }
        for event in assessment.active_events:
            assert event.structure_id not in dead_ids


# ---------------- 阶段升级解释 ----------------


def test_stage_change_reason_explains_upgrade() -> None:
    result = _analyze(golden_delayed_upgrade(), build_history=True)
    upgrades = [
        a
        for a in result.assessments_by_date.values()
        if a.previous_stage is not None and "升级" in a.stage_change_reason_cn
    ]
    assert upgrades, "必须出现可解释的升级"
    sample = upgrades[0]
    assert "→" in sample.stage_change_reason_cn
    assert "原因" in sample.stage_change_reason_cn


def test_pipeline_is_deterministic() -> None:
    bars = golden_delayed_upgrade()
    first = _analyze(bars)
    second = _analyze(bars)
    assert [e.event_id for e in first.events] == [e.event_id for e in second.events]
    assert first.assessment.stage == second.assessment.stage
    assert [s.structure_id for s in first.structures] == [
        s.structure_id for s in second.structures
    ]


def test_pipeline_rejects_short_history_explicitly() -> None:
    from lei_signal.data.validation import DataUnavailableError

    short = golden_delayed_upgrade().head(10)
    with pytest.raises(DataUnavailableError, match="至少需要"):
        _analyze(short)


def test_swing_pivot_events_use_confirmation_date_as_available() -> None:
    """摆动点事件的 available_date 必须是确认日，event_date 是拐点日。"""
    rng = np.random.default_rng(3)
    close = 100 + np.cumsum(rng.normal(0, 2.0, 200))
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.5, 2.0, 200),
            "low": close - rng.uniform(0.5, 2.0, 200),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, 200).astype(float),
        },
        index=pd.bdate_range("2024-01-02", periods=200),
    )
    result = _analyze(bars)
    pivot_events = [e for e in result.events if e.rule_id == "swing_pivots"]
    assert pivot_events
    for event in pivot_events:
        assert event.available_date > event.event_date, "确认日必须晚于拐点日"
