"""timing_backtest.sweep 网格构建/批量执行/稳健筛选测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.sweep import (
    build_grid,
    robust_mask,
    robust_top,
    run_sweep,
)


def test_build_grid_dimensions_and_uniqueness():
    grid = build_grid(["000300"], ["b200"])
    # ladder 3×2×2×2=24 + reversal 3×1×2×3×2=36 = 60
    assert len(grid) == 60
    keys = [str(sorted(g.items())) for g in grid]
    assert len(set(keys)) == 60
    strategies = {g["strategy"] for g in grid}
    assert strategies == {"ladder", "reversal"}
    with pytest.raises(ValueError):
        build_grid(["NOPE"], ["b200"])


def test_run_sweep_produces_window_columns(tmp_path):
    idx = pd.bdate_range("2022-01-03", periods=600)
    rng = np.random.default_rng(21)
    close = pd.Series(3000 * np.exp(rng.normal(0.0002, 0.012, 600).cumsum()), index=idx)
    pd.DataFrame({"open": close * 0.999, "close": close}).to_parquet(tmp_path / "000300.parquet")
    b = pd.Series(np.clip(50 + rng.normal(0, 8, 600).cumsum(), 1, 99), index=idx)
    pd.DataFrame({"b20": b, "b50": b, "b200": b}).to_parquet(tmp_path / "breadth_cn_all.parquet")

    grid = [
        {"symbol": "000300", "strategy": "ladder", "indicator": "b200", "n_bands": 3},
        {"symbol": "000300", "strategy": "reversal", "indicator": "b200", "batches": 3},
    ]
    df = run_sweep(grid, cache_dir=tmp_path)
    assert len(df) == 2
    for col in ("full_excess", "h1_excess", "h2_excess", "full_mdd", "full_calmar", "score"):
        assert col in df.columns
    # 半窗长度和应接近全窗（年数字段单调性不检验，只查存在性）
    assert df["full_n_trades"].notna().all()


def test_robust_top_filters_and_per_symbol_cap():
    rows = []
    # A: 全部条件满足；B: 后半超额为负；C: 回撤劣于基准；D: 满足
    base = dict(
        strategy="ladder", indicator="b200", gate="off", params="{}",
        full_cagr=0.10, full_bh_cagr=0.05, full_excess=0.05, full_mdd=-0.10,
        full_bh_mdd=-0.20, full_calmar=1.0, full_sharpe=1.0, full_n_trades=10,
        full_avg_weight=0.5, h1_excess=0.03, h1_cagr=0.1, h1_bh_cagr=0.07, h1_mdd=-0.1,
        h1_bh_mdd=-0.2, h1_calmar=1.0, h1_sharpe=1.0, h1_n_trades=5, h1_avg_weight=0.5,
        h2_excess=0.04, h2_cagr=0.1, h2_bh_cagr=0.06, h2_mdd=-0.1, h2_bh_mdd=-0.2,
        h2_calmar=1.0, h2_sharpe=1.0, h2_n_trades=5, h2_avg_weight=0.5,
    )
    rows.append({**base, "symbol": "000300", "score": 1.0})
    rows.append({**base, "symbol": "000300", "h2_excess": -0.01, "score": 0.9})
    rows.append({**base, "symbol": "000300", "full_mdd": -0.50, "score": 0.8})
    rows.append({**base, "symbol": "^GSPC", "score": 0.7})
    df = pd.DataFrame(rows)
    top = robust_top(df)
    assert set(top["symbol"]) == {"000300", "^GSPC"}
    assert len(top[top["symbol"] == "000300"]) == 1  # B、C 被稳健条件剔除
    assert robust_mask(df).tolist() == [True, False, False, True]
