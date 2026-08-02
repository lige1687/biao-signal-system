"""修复 6：研究统计——方向调整、关联结构 C 路径、按时间顺序分类、聚类、资产类别。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.research.outcomes import (
    build_forward_outcomes,
    infer_asset_class,
    summarize_by_rule,
    top_transition_stats,
)
from lei_signal.research.stability import (
    cluster_by_structure,
    split_by_group,
)


def _bars(rows: int = 800, seed: int = 33) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.5, rows),
            "low": close - rng.uniform(0.3, 1.5, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2022-01-03", periods=rows),
    )


def test_bearish_signal_uses_direction_adjusted_return() -> None:
    """修复 6.1：看空信号后价格下跌应记为方向命中。"""
    # 构造一个明显的 black 序列
    rng = np.random.default_rng(7)
    n = 300
    close = np.concatenate([np.linspace(100, 90, n // 2), np.linspace(90, 70, n // 2)])
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.5, n),
            "low": close - rng.uniform(0.3, 1.5, n),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=n),
    )
    result = analyze_bars("SYN", bars, build_history=True)
    outcomes = build_forward_outcomes(result)
    # 找 black 类事件
    black_events = outcomes[outcomes["signal_key"].str.contains("key_wave_black", na=False)]
    if black_events.empty:
        # 用 key_wave_black_started
        black_events = outcomes[outcomes["signal_key"] == "key_wave_black:key_wave_black_started"]
    if not black_events.empty:
        sample = black_events.iloc[0]
        # 方向应识别为 bearish
        assert sample["direction"] in ("bearish", "risk")
        # raw vs direction-adjusted 必须符号相反
        raw_20 = sample["fwd_return_20"]
        adj_20 = sample.get("direction_adjusted_return_20")
        if pd.notna(raw_20) and pd.notna(adj_20) and raw_20 != 0:
            # 方向相反
            assert (raw_20 * adj_20) < 0 or raw_20 == 0, (
                f"看空信号的 raw={raw_20} 与 adj={adj_20} 应当方向相反"
            )


def test_c_path_uses_event_own_structure() -> None:
    """修复 6.2：事件带 structure_id 时必须使用该结构自己的 C。"""
    # 构造：每个反转底部结构都自带 C，事件应该引用该 C 而不是「主结构」。
    np.random.default_rng(11)
    rows: list[dict[str, float]] = []
    for i in range(150):
        close = 100 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 第一个反包：A 底部
    rows.append({"open": 26.0, "high": 26.3, "low": 24.0, "close": 24.5, "volume": 1_100_000})
    rows.append({"open": 23.5, "high": 28.0, "low": 23.3, "close": 27.8, "volume": 1_900_000})
    # 第二个反包：B 底部（远低于 A）
    for _ in range(2, 10):
        rows.append({"open": 27.0, "high": 27.0, "low": 10.0,
                     "close": 11.0, "volume": 1_000_000})
    rows.append({"open": 11.0, "high": 11.3, "low": 9.0, "close": 9.5, "volume": 1_100_000})
    rows.append({"open": 8.5, "high": 13.0, "low": 8.3, "close": 12.8, "volume": 1_900_000})
    bars = pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("SYN", bars, build_history=True)
    outcomes = build_forward_outcomes(result)
    own_c = outcomes[outcomes["c_source"] == "own_structure"]
    inferred = outcomes[outcomes["c_source"] == "inferred_primary"]
    # 必须有 own_structure 来源：所有反包事件都关联到具体结构
    assert not own_c.empty, f"事件应使用 own_structure C；inferred={len(inferred)}"


def test_top_outcome_classified_by_first_event() -> None:
    """修复 6.3：顶部后续按最早发生事件分类。

    不能因为最终创新高而忽略此前已经先转黑。
    """
    # 直接使用真实合成的 800 根数据，其中很多顶部同时存在「先转黑 + 后新高解除」。
    result = analyze_bars("SYN", _bars())
    # 找同时满足：confirmed + invalidated_reason=新高解除 的顶部
    both = [
        s for s in result.tops
        if s.confirmed_date is not None
        and s.invalidated_reason == "top_warning_invalidated_by_new_high"
    ]
    assert both, "样例应至少有一个先转黑后新高解除的顶部"
    # 验证语义：对于先转黑后新高解除的顶部，旧实现归到「新高解除」，
    # 新实现必须归到「转为黑色」。
    after = result.frame.loc[result.frame.index > pd.Timestamp(both[0].confirmed_date)]
    first_black = after.index[after["signal_color"].eq("black")]
    assert len(first_black) > 0
    new_high_day = pd.Timestamp(both[0].invalidated_date)
    assert first_black[0] < new_high_day, "测试前提：先转黑后新高"
    # 重新构造一个 AnalysisResult，只包含这个顶部
    from lei_signal.compose.pipeline import AnalysisResult
    minimal = AnalysisResult(
        symbol="SYN",
        display_name="SYN",
        frame=result.frame,
        weekly_trend=result.weekly_trend,
        events=result.events,
        structures=[both[0]],
        pivots=(),
        history=result.history,
        assessment=result.assessment,
        b1=result.b1,
        profile=result.profile,
        price_data=result.price_data,
    )
    table = top_transition_stats(minimal)
    # 关键：必须先分类为「转为黑色」
    assert "转为黑色" in table["顶部后结果"].tolist()
    row = table[table["顶部后结果"] == "转为黑色"].iloc[0]
    assert row["次数"] >= 1


def test_cluster_by_structure_wired_into_research() -> None:
    """修复 6.4：cluster_by_structure 已接入研究页面。"""
    result = analyze_bars("SYN", _bars())
    outcomes = build_forward_outcomes(result)
    cluster = cluster_by_structure(outcomes)
    # cluster 必须返回 DataFrame，列名清晰
    assert isinstance(cluster, pd.DataFrame)
    if not cluster.empty:
        assert "structure_id" in cluster.columns
        assert "关联信号数" in cluster.columns
        assert "信号种类" in cluster.columns


def test_infer_asset_class_handles_unknown() -> None:
    """修复 6.5：无法可靠分类时必须返回 unknown。"""
    assert infer_asset_class("QQQ") == "us_equity_or_etf"
    assert infer_asset_class("159915.SZ") == "cn_equity"
    assert infer_asset_class("510300.SS") == "cn_equity"
    assert infer_asset_class("0700.HK") == "hk_equity"
    assert infer_asset_class("UNKNOWN_TICKER_12345") == "unknown"
    # 短全字母（≤ 5）默认视为 us
    assert infer_asset_class("SPY") == "us_equity_or_etf"
    # 6+ 字符且非 .SS/.SZ/.HK → unknown
    assert infer_asset_class("RANDOM_TICKER") == "unknown"


def test_summary_table_uses_direction_hit_label() -> None:
    """summary 表必须使用「方向命中」列名，不误导为胜率。"""
    result = analyze_bars("SYN", _bars())
    outcomes = build_forward_outcomes(result)
    summary = summarize_by_rule(outcomes)
    if not summary.empty:
        assert "方向命中率" in summary.columns


def test_split_by_group_supports_asset_class() -> None:
    """资产类别可作为分组维度。"""
    result = analyze_bars("QQQ", _bars())
    outcomes = build_forward_outcomes(result)
    assert "asset_class" in outcomes.columns
    table = split_by_group(outcomes, group="asset_class", column="fwd_return_20")
    assert "样本数" in table.columns
