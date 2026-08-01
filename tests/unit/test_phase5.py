"""Phase 5 门禁：历史有效性研究与统计约束。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.research.outcomes import (
    HORIZONS,
    build_forward_outcomes,
    gray_transition_stats,
    summarize_by_rule,
    top_transition_stats,
)
from lei_signal.research.stability import (
    MIN_SAMPLES_FOR_CI,
    baseline_comparison,
    block_bootstrap_ci,
    cluster_by_structure,
    drop_top_k_analysis,
    split_by_group,
)


def _synthetic(rows: int = 900, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.6, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 2.0, rows),
            "low": close - rng.uniform(0.3, 2.0, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2021-01-04", periods=rows),
    )


@pytest.fixture(scope="module")
def analysis():  # noqa: ANN201
    return analyze_bars("SYN", _synthetic())


@pytest.fixture(scope="module")
def outcomes(analysis) -> pd.DataFrame:  # noqa: ANN001
    return build_forward_outcomes(analysis)


# ---------------- 后续收益 ----------------


def test_all_required_horizons_are_computed(outcomes: pd.DataFrame) -> None:
    """必须计算 1/5/10/20/60/120 日收益。"""
    assert not outcomes.empty
    for horizon in HORIZONS:
        assert f"fwd_return_{horizon}" in outcomes.columns
        assert f"mfe_{horizon}" in outcomes.columns
        assert f"mae_{horizon}" in outcomes.columns
    assert HORIZONS == (1, 5, 10, 20, 60, 120)


def test_forward_returns_use_only_future_data(analysis, outcomes: pd.DataFrame) -> None:  # noqa: ANN001
    """收益必须严格向前：逐样本重算核对。"""
    frame = analysis.frame
    close = frame["close"].astype(float)
    sample = outcomes.dropna(subset=["fwd_return_20"]).head(30)
    for _, row in sample.iterrows():
        position = frame.index.get_loc(pd.Timestamp(row["available_date"]))
        expected = (float(close.iloc[position + 20]) / float(close.iloc[position]) - 1.0) * 100.0
        assert row["fwd_return_20"] == pytest.approx(expected, rel=1e-9)
        assert row["entry_close"] == pytest.approx(float(close.iloc[position]))


def test_mfe_is_never_below_mae(outcomes: pd.DataFrame) -> None:
    valid = outcomes.dropna(subset=["mfe_20", "mae_20"])
    assert not valid.empty
    assert (valid["mfe_20"] >= valid["mae_20"]).all()


def test_mfe_mae_windows_exclude_the_signal_day_itself(analysis, outcomes) -> None:  # noqa: ANN001
    """MFE/MAE 从信号日之后开始，不含信号日本身。"""
    frame = analysis.frame
    sample = outcomes.dropna(subset=["mfe_5"]).head(20)
    for _, row in sample.iterrows():
        position = frame.index.get_loc(pd.Timestamp(row["available_date"]))
        entry = row["entry_close"]
        window = frame.iloc[position + 1 : position + 6]
        expected_mfe = (float(window["high"].max()) / entry - 1.0) * 100.0
        assert row["mfe_5"] == pytest.approx(expected_mfe, rel=1e-9)


def test_atr_targets_report_reach_ratio_and_days(outcomes: pd.DataFrame) -> None:
    for label in ("plus_1atr", "plus_2atr", "minus_1atr"):
        assert f"days_to_{label}" in outcomes.columns
        assert f"reached_{label}" in outcomes.columns
    reached = outcomes[outcomes["reached_plus_1atr"]]
    assert not reached.empty
    assert (reached["days_to_plus_1atr"] > 0).all(), "达成天数必须为正"
    # +2ATR 必然不早于 +1ATR
    both = outcomes[outcomes["reached_plus_1atr"] & outcomes["reached_plus_2atr"]]
    assert (both["days_to_plus_2atr"] >= both["days_to_plus_1atr"]).all()


def test_c_and_b1_paths_are_tracked(outcomes: pd.DataFrame) -> None:
    for column in (
        "touched_c", "days_to_touch_c", "c_price",
        "reached_b1", "broke_b1", "extension_after_b1_pct", "b1_price",
    ):
        assert column in outcomes.columns
    touched = outcomes[outcomes["touched_c"]]
    if not touched.empty:
        assert (touched["days_to_touch_c"] > 0).all()
    broke = outcomes[outcomes["broke_b1"]]
    if not broke.empty:
        assert broke["reached_b1"].all(), "突破B1必然先到达B1"


# ---------------- 事件去重与聚类 ----------------


def test_consecutive_same_stage_counts_once(analysis, outcomes: pd.DataFrame) -> None:  # noqa: ANN001
    """同一阶段连续多日只算一次信号，不是每天一个独立样本。"""
    stage_rows = outcomes[outcomes["signal_kind"] == "stage"]
    assert not stage_rows.empty

    from lei_signal.domain.types import Stage

    joint_days = sum(1 for s in analysis.history if s.stage is Stage.JOINT_CONFIRMED)
    joint_signals = len(stage_rows[stage_rows["signal_key"] == "stage:joint_confirmed"])
    if joint_days > 0:
        assert joint_signals < joint_days, "连续同阶段不得每天算一个信号"


def test_atomic_and_stage_signals_are_both_retained(outcomes: pd.DataFrame) -> None:
    """不能只统计最强信号，原子与组合都要保留。"""
    kinds = set(outcomes["signal_kind"])
    assert kinds == {"atomic", "stage"}


def test_summary_reports_both_types_with_sample_counts(outcomes: pd.DataFrame) -> None:
    summary = summarize_by_rule(outcomes, horizon=20)
    assert not summary.empty
    assert set(summary["类型"]) == {"原子信号", "组合阶段"}
    for column in ("样本数", "有效样本", "胜率", "来源"):
        assert column in summary.columns
    assert (summary["样本数"] > 0).all()


def test_structure_clustering_links_multiple_signals(outcomes: pd.DataFrame) -> None:
    """同一结构的多次升级保留关联 ID，可按结构聚类。"""
    clusters = cluster_by_structure(outcomes)
    if not clusters.empty:
        assert "关联信号数" in clusters.columns
        assert (clusters["关联信号数"] >= 1).all()


# ---------------- Bootstrap 与稳定性 ----------------


def test_block_bootstrap_returns_ordered_interval(outcomes: pd.DataFrame) -> None:
    key = outcomes["signal_key"].value_counts().index[0]
    subset = outcomes[outcomes["signal_key"] == key]
    low, high = block_bootstrap_ci(subset)
    assert low is not None and high is not None
    assert low < high


def test_block_bootstrap_is_reproducible(outcomes: pd.DataFrame) -> None:
    """固定种子使区间可复现。"""
    key = outcomes["signal_key"].value_counts().index[0]
    subset = outcomes[outcomes["signal_key"] == key]
    assert block_bootstrap_ci(subset) == block_bootstrap_ci(subset)


def test_block_bootstrap_refuses_to_fabricate_interval_for_tiny_samples() -> None:
    """样本不足时返回 None，不伪造区间。"""
    tiny = pd.DataFrame(
        {
            "available_date": pd.bdate_range("2024-01-02", periods=3).date,
            "fwd_return_20": [1.0, 2.0, 3.0],
        }
    )
    assert block_bootstrap_ci(tiny) == (None, None)
    assert MIN_SAMPLES_FOR_CI >= 8


def test_quarter_and_year_blocks_are_supported(outcomes: pd.DataFrame) -> None:
    key = outcomes["signal_key"].value_counts().index[0]
    subset = outcomes[outcomes["signal_key"] == key]
    quarterly = block_bootstrap_ci(subset, block="quarter")
    yearly = block_bootstrap_ci(subset, block="year")
    assert quarterly[0] is not None
    assert yearly[0] is not None


def test_drop_top_k_shows_right_tail_dependence(outcomes: pd.DataFrame) -> None:
    """删除最大 1/3/5 个事件必须都被报告。"""
    key = outcomes["signal_key"].value_counts().index[0]
    table = drop_top_k_analysis(outcomes[outcomes["signal_key"] == key])
    assert table["删除最大N个"].tolist() == [0, 1, 3, 5]
    # 删除最大值后均值必然不升高
    means = table["均值%"].tolist()
    assert means[0] >= means[1] >= means[2] >= means[3]
    assert "相对基准变化" in table.columns


def test_split_by_year_and_market_state(outcomes: pd.DataFrame) -> None:
    key = outcomes["signal_key"].value_counts().index[0]
    subset = outcomes[outcomes["signal_key"] == key]
    by_year = split_by_group(subset, group="year")
    by_state = split_by_group(subset, group="market_state")
    assert not by_year.empty and "样本数" in by_year.columns
    assert not by_state.empty
    assert by_year["样本数"].sum() == len(subset)


def test_baseline_comparison_reports_incremental_information(
    analysis, outcomes: pd.DataFrame  # noqa: ANN001
) -> None:
    """必须与同标的相似市场阶段的普通日期比较。"""
    key = outcomes["signal_key"].value_counts().index[0]
    table = baseline_comparison(outcomes, analysis.frame, key)
    assert len(table) == 3
    assert "信号日" in table["组别"].iloc[0]
    assert "匹配基准" in table["组别"].iloc[1]
    assert "差值" in table["组别"].iloc[2]
    # 基准样本必须排除信号日本身
    assert table["样本数"].iloc[1] > 0


# ---------------- 转灰与顶部概率 ----------------


def test_gray_transition_probabilities_sum_to_one(analysis) -> None:  # noqa: ANN001
    table = gray_transition_stats(analysis.frame)
    assert not table.empty
    assert set(table["转灰后结果"]) == {"恢复绿色", "转为黑色", "仍为灰色"}
    assert table["占比"].sum() == pytest.approx(1.0, abs=0.01)


def test_top_transition_probabilities_are_reported(analysis) -> None:  # noqa: ANN001
    table = top_transition_stats(analysis)
    if not table.empty:
        assert set(table["顶部后结果"]) == {"转为黑色", "新高解除", "既未转黑也未解除"}
        assert table["占比"].sum() == pytest.approx(1.0, abs=0.01)


# ---------------- 研究结果确定性 ----------------


def test_research_output_is_reproducible() -> None:
    bars = _synthetic(600, seed=13)
    first = build_forward_outcomes(analyze_bars("SYN", bars))
    second = build_forward_outcomes(analyze_bars("SYN", bars))
    pd.testing.assert_frame_equal(first, second)


def test_research_never_simulates_positions(outcomes: pd.DataFrame) -> None:
    """研究层不得出现仓位、资金、账户相关字段。"""
    forbidden = {"position", "shares", "capital", "equity", "cash", "pnl", "account"}
    for column in outcomes.columns:
        assert not any(word in column.lower() for word in forbidden), (
            f"研究输出不得包含仓位/资金字段: {column}"
        )
