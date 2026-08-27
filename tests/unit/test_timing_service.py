"""timing_backtest.service 执行/落盘/选项测试（tmp 缓存目录）。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.service import (
    TimingDataUnavailable,
    build_options,
    execute_run,
    list_runs,
)


@pytest.fixture()
def fake_cache(tmp_path):
    idx = pd.bdate_range("2022-01-03", periods=600)
    rng = np.random.default_rng(11)
    close = pd.Series(3000 * np.exp(rng.normal(0.0002, 0.012, 600).cumsum()), index=idx)
    bars = pd.DataFrame({"open": close * 0.999, "close": close})
    b = pd.Series(np.clip(50 + rng.normal(0, 8, 600).cumsum(), 1, 99), index=idx)
    breadth = pd.DataFrame({"b20": b, "b50": b, "b200": b})
    bars.to_parquet(tmp_path / "000300.parquet")
    breadth.to_parquet(tmp_path / "breadth_cn_all.parquet")
    return tmp_path


def test_execute_run_ladder_full_flow(fake_cache, tmp_path):
    runs_dir = tmp_path / "runs"
    res = execute_run(
        {"symbol": "000300", "strategy": "ladder"}, cache_dir=fake_cache, runs_dir=runs_dir
    )
    for key in ("run_id", "created_at", "params", "metrics", "yearly", "trades", "daily"):
        assert key in res
    m = res["metrics"]
    assert "strategy_cagr" in m and "benchmark_cagr" in m and "excess_cagr" in m
    assert res["daily"]["date"][0] == res["daily"]["date"][0]  # 非空
    assert len(res["daily"]["equity"]) == len(res["daily"]["date"])
    for key in ("open", "high", "low", "close", "weight", "breadth"):
        assert len(res["daily"][key]) == len(res["daily"]["date"])
    files = list(runs_dir.glob("*.json"))
    assert len(files) == 1


def test_execute_run_reversal(fake_cache, tmp_path):
    res = execute_run(
        {"symbol": "000300", "strategy": "reversal", "batch_mode": "time", "batches": 5},
        cache_dir=fake_cache,
        runs_dir=tmp_path / "runs",
    )
    assert res["params"]["strategy"] == "reversal"
    assert res["metrics"]["n_trades"] >= 0


def test_execute_run_data_unavailable(tmp_path):
    with pytest.raises(TimingDataUnavailable) as ei:
        execute_run({"symbol": "000300"}, cache_dir=tmp_path, runs_dir=tmp_path)
    assert "DATA_UNAVAILABLE" in str(ei.value)


def test_execute_run_unknown_symbol(fake_cache, tmp_path):
    with pytest.raises(ValueError, match="未知标的"):
        execute_run({"symbol": "NOPE"}, cache_dir=fake_cache, runs_dir=tmp_path)


def test_execute_run_respects_window(fake_cache, tmp_path):
    res = execute_run(
        {"symbol": "000300", "strategy": "ladder", "start": "2023-01-02"},
        cache_dir=fake_cache,
        runs_dir=tmp_path / "runs",
    )
    assert res["daily"]["date"][0] >= "2023-01-02"


def test_list_runs(fake_cache, tmp_path):
    runs_dir = tmp_path / "runs"
    execute_run({"symbol": "000300"}, cache_dir=fake_cache, runs_dir=runs_dir)
    execute_run({"symbol": "000300", "strategy": "reversal"}, cache_dir=fake_cache, runs_dir=runs_dir)
    runs = list_runs(runs_dir=runs_dir)
    assert len(runs) == 2
    assert {"run_id", "created_at", "params", "metrics"} <= set(runs[0].keys())


def test_build_options(fake_cache):
    opts = build_options(cache_dir=fake_cache)
    assert len(opts["disclaimers"]) >= 3
    inst = {i["symbol"]: i for i in opts["instruments"]}
    assert inst["000300"]["data_start"] == "2022-01-03"
    assert inst["000300"]["breadth_label"].startswith("全A")
    assert inst["^GSPC"]["data_start"] is None  # 无数据时显式 None
    assert len(opts["presets"]) >= 8
    assert opts["strategies"]["ladder"]["defaults"]["n_bands"] == 5
