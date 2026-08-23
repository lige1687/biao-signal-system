"""Phase 0 门禁：规则账本完整性与确定性事件 ID。"""
from __future__ import annotations

from datetime import date

import pytest

from lei_signal.domain.canonical import (
    CanonicalizationError,
    canonical_float,
    canonical_json,
    canonical_sha256,
    make_event_id,
)
from lei_signal.domain.rules_config import (
    get_rule,
    indicator_config,
    load_ruleset,
    risk_priority,
    ruleset_version,
    state_machine_config,
)
from lei_signal.domain.types import Provenance, Stage

# 架构第 5 节要求首批登记的全部原子规则
REQUIRED_RULES = [
    "lei_color",
    "ema20_reclaim_rising",
    "dual_ma_bull_confirmed",
    "dual_ma_spread",
    "long_trend",
    "swing_pivots",
    "bullish_engulfing",
    "bullish_outside_reversal",
    "bearish_engulfing",
    "bearish_outside_reversal",
    "higher_low_bottom",
    "double_bottom",
    "bullish_reversal_bottom",
    "bottom_c_lifecycle",
    "top_structure",
    "key_wave_black",
    "volume_proxies",
    "volume_profile_proxy",
    "first_ma_pullback",
    "resistance_b1",
]


@pytest.mark.parametrize("rule_id", REQUIRED_RULES)
def test_every_required_rule_is_registered_with_provenance(rule_id: str) -> None:
    """每条规则必须登记来源、版本和公式，缺失即报错。"""
    spec = get_rule(rule_id)
    assert spec.rule_id == rule_id
    assert isinstance(spec.provenance, Provenance)
    assert spec.version.count(".") == 2, f"{rule_id} 版本号必须是 x.y.z"
    assert spec.formula, f"{rule_id} 缺少公式"
    assert spec.note_cn, f"{rule_id} 缺少中文说明"


def test_unregistered_rule_raises_instead_of_defaulting() -> None:
    """规则缺失必须报错，不得静默使用默认值。"""
    with pytest.raises(KeyError, match="没有登记"):
        get_rule("not_a_real_rule")


def test_reversal_rules_are_labelled_research_proxy() -> None:
    """视频未明确的反包/外包规则必须标注 research_proxy，不得冒充 LEI 原规则。"""
    for rule_id in (
        "bullish_engulfing",
        "bullish_outside_reversal",
        "bearish_engulfing",
        "bearish_outside_reversal",
        "volume_proxies",
        "volume_profile_proxy",
        "first_ma_pullback",
        "exit_ema20_costbasis",
    ):
        assert get_rule(rule_id).is_research_proxy, f"{rule_id} 必须标注 research_proxy"


def test_core_lei_rules_are_marked_explicit() -> None:
    """三色与关键性波动来自视频明确规则。"""
    for rule_id in ("lei_color", "ema20_reclaim_rising", "dual_ma_bull_confirmed",
                    "key_wave_black", "bottom_c_lifecycle"):
        assert get_rule(rule_id).provenance is Provenance.LEI_EXPLICIT


def test_thresholds_live_in_config_not_code() -> None:
    """所有阈值必须来自配置。"""
    assert get_rule("swing_pivots").param("left") == 3
    assert get_rule("swing_pivots").param("right") == 3
    assert get_rule("volume_proxies").param("up_surge_ratio") == 1.5
    assert get_rule("volume_proxies").param("breakout_ratio") == 1.5
    assert get_rule("volume_profile_proxy").param("window") == 120
    assert get_rule("volume_profile_proxy").param("value_area") == 0.70
    assert get_rule("resistance_b1").param("lookback_years") == 2
    assert get_rule("double_bottom").param("max_diff_atr") == 1.0
    pullback = get_rule("first_ma_pullback")
    assert pullback.param("ma_periods") == [20, 60, 120]
    assert pullback.param("confirmation_window") == 3
    assert pullback.param("min_separation_atr") == 1.0


def test_indicator_config_declares_required_periods() -> None:
    config = indicator_config()
    assert config["ema_periods"] == [20, 60, 120]
    assert config["sma_periods"] == [20, 60, 120]
    assert config["atr_period"] == 14
    assert config["ema_seed"] == "first_window_sma"


def test_risk_priority_order_matches_specification() -> None:
    """风险优先级顺序被冻结：仅决定提示排序，不自动执行卖出。"""
    assert risk_priority() == [
        "c_touched_or_broken",
        "top_plus_black",
        "black",
        "active_top_structure",
        "turned_gray",
        "volume_conflict",
    ]


def test_state_machine_declares_all_stages_and_invariants() -> None:
    config = state_machine_config()
    stages = config["stages"]
    for stage in Stage:
        assert stage.value in stages, f"状态机缺少 {stage.value}"
    invariants = " ".join(config["invariants"])
    assert "不要求当天重新穿越" in invariants
    assert "永久终止" in invariants


def test_ruleset_version_is_present() -> None:
    assert ruleset_version() == "1.5.0"  # 1.5.0：macd_strength 扩散/收敛改 |DIF| 口径
    assert load_ruleset()["source_video"].startswith("https://www.youtube.com/watch?v=7NkwlH6NOk8")


# ---------------- 确定性 event_id（门禁 11）----------------


def test_event_id_is_stable_across_runs() -> None:
    """同样输入必须产生完全相同的事件 ID。"""
    kwargs = {
        "rule_id": "lei_color",
        "rule_version": "1.0.0",
        "symbol": "QQQ",
        "timeframe": "1d",
        "available_date": date(2025, 3, 14),
        "source_id": "green_started",
    }
    assert make_event_id(**kwargs) == make_event_id(**kwargs)  # type: ignore[arg-type]
    assert make_event_id(**kwargs).startswith("lei_color:")  # type: ignore[arg-type]


def test_event_id_changes_when_any_key_component_changes() -> None:
    base = {
        "rule_id": "lei_color",
        "rule_version": "1.0.0",
        "symbol": "QQQ",
        "timeframe": "1d",
        "available_date": date(2025, 3, 14),
        "source_id": "",
    }
    baseline = make_event_id(**base)  # type: ignore[arg-type]
    for field, value in (
        ("rule_version", "1.0.1"),
        ("symbol", "159915.SZ"),
        ("timeframe", "1w"),
        ("available_date", date(2025, 3, 17)),
        ("source_id", "other"),
    ):
        variant = {**base, field: value}
        assert make_event_id(**variant) != baseline, f"{field} 改变后 ID 必须不同"  # type: ignore[arg-type]


def test_canonical_json_is_independent_of_insertion_order() -> None:
    """插入顺序不得泄漏进哈希。"""
    first = {"b": 1, "a": 2, "c": {"y": 1, "x": 2}}
    second = {"c": {"x": 2, "y": 1}, "a": 2, "b": 1}
    assert canonical_json(first) == canonical_json(second)
    assert canonical_sha256(first) == canonical_sha256(second)


def test_canonical_float_folds_representation_noise() -> None:
    """float repr 尾差必须折叠，否则事件 ID 会随机漂移。"""
    assert canonical_float(0.1 + 0.2) == canonical_float(0.3)
    assert canonical_float(1.10) == canonical_float(1.1)
    assert canonical_float(-0.0) == "0.0"
    assert canonical_sha256({"p": 0.1 + 0.2}) == canonical_sha256({"p": 0.3})


def test_canonical_rejects_unstable_containers_and_values() -> None:
    """set 迭代顺序依赖哈希种子，必须拒绝而不是静默排序。"""
    with pytest.raises(CanonicalizationError, match="set/frozenset"):
        canonical_json({"k": {1, 2, 3}})
    with pytest.raises(CanonicalizationError, match="非有限浮点数"):
        canonical_float(float("nan"))
    with pytest.raises(CanonicalizationError, match="非有限浮点数"):
        canonical_float(float("inf"))
