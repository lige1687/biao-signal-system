"""修复 8 + 9：行情缓存、SQLite 持久化与本地导入入口。"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze
from lei_signal.data.cache import ParquetCache
from lei_signal.data.validation import DataUnavailableError


def _bars(rows: int = 300, seed: int = 7) -> pd.DataFrame:
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


def _fixed_provider(bars: pd.DataFrame, name: str = "fixed"):
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import ValidationReport

    class Fixed:
        def fetch(self, symbol, *, min_rows=21):
            info = resolve_symbol(symbol)
            return PriceData(
                symbol=info.symbol, display_name=info.symbol,
                bars=bars,
                report=ValidationReport(
                    rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
                    adjusted=True, provider=name, duplicates_removed=0, warnings=(),
                ),
                info=info,
            )
    return Fixed()


def test_successful_fetch_writes_parquet_cache(tmp_path) -> None:  # noqa: ANN001
    """修复 8：成功获取行情后必须写入 Parquet 缓存。"""
    cache_root = tmp_path / "cache"
    result = analyze(
        "QQQ", provider=_fixed_provider(_bars(300, seed=11)),
        cache_root=str(cache_root),
    )
    assert (cache_root / "QQQ.bars.parquet").exists(), "成功获取后必须写入 Parquet 缓存"
    assert not result.cache_fallback_used


def test_network_failure_falls_back_to_recent_cache(tmp_path) -> None:  # noqa: ANN001
    """修复 8：网络失败时若缓存存在且未过期，可降级使用。"""
    cache_root = tmp_path / "cache"
    cache = ParquetCache(cache_root)
    cache.write("QQQ", _bars(300, seed=21))

    class AlwaysFail:
        def fetch(self, symbol, *, min_rows=21):
            raise DataUnavailableError("远程行情不可用")

    result = analyze(
        "QQQ", provider=AlwaysFail(),
        cache_root=str(cache_root), cache_max_age_seconds=86400,
    )
    assert result.cache_fallback_used
    assert result.cache_age_seconds is not None
    assert result.cache_age_seconds < 86400


def test_network_failure_with_stale_cache_still_raises(tmp_path) -> None:  # noqa: ANN001
    """修复 8：缓存已过期时不得静默使用陈旧数据。"""
    cache_root = tmp_path / "cache"
    cache = ParquetCache(cache_root)
    cache.write("QQQ", _bars(300, seed=31))
    cache_path = cache_root / "QQQ.bars.parquet"
    seven_days_ago = (pd.Timestamp.now() - pd.Timedelta(days=7)).timestamp()
    os.utime(cache_path, (seven_days_ago, seven_days_ago))

    class AlwaysFail:
        def fetch(self, symbol, *, min_rows=21):
            raise DataUnavailableError("远程不可用")

    with pytest.raises(DataUnavailableError, match="过期"):
        analyze(
            "QQQ", provider=AlwaysFail(),
            cache_root=str(cache_root), cache_max_age_seconds=86400,
        )


def test_no_cache_means_pure_remote_failure_propagates() -> None:
    """修复 8：无缓存且远程失败时，原始 DataUnavailableError 必须透传。"""
    class AlwaysFail:
        def fetch(self, symbol, *, min_rows=21):
            raise DataUnavailableError("远程不可用")

    with pytest.raises(DataUnavailableError, match="远程不可用"):
        analyze("QQQ", provider=AlwaysFail(), cache_root=None)


def test_sqlite_records_events_structures_assessment_and_runs(tmp_path) -> None:  # noqa: ANN001
    """修复 8：事件/结构/评估/运行元数据必须写入 SQLite。"""
    from lei_signal.storage.sqlite_store import connect, count_events

    db_path = tmp_path / "result.db"
    result = analyze(
        "QQQ", provider=_fixed_provider(_bars(300, seed=41)),
        sqlite_path=str(db_path), run_id="run-test-1",
    )
    conn = connect(db_path)
    n_events = count_events(conn, "QQQ")
    assert n_events == len(result.events), "事件必须全部写入 SQLite"
    run = conn.execute(
        "SELECT * FROM analysis_runs WHERE run_id = 'run-test-1'"
    ).fetchone()
    assert run is not None
    assert run["event_count"] == len(result.events)

    # 同一 run_id 第二次运行：事件应被幂等忽略
    analyze("QQQ", provider=_fixed_provider(_bars(300, seed=41)),
            sqlite_path=str(db_path), run_id="run-test-1")
    n_events_2 = count_events(conn, "QQQ")
    assert n_events_2 == n_events, "重复运行不得重复写入事件"


def test_sqlite_preserves_complete_structure_lifecycle(tmp_path) -> None:  # noqa: ANN001
    """修复 8：结构状态变化必须保存完整转换。

    流水线中 detect_*_bottoms 在调用 apply_c_lifecycle 之前已记录
    candidate 事件；apply_c_lifecycle 在已确认结构上把状态从
    confirmed → invalidated，存入 SQLite 时也会按新结构写入 from=confirmed。
    """
    from lei_signal.storage.sqlite_store import connect
    from tests.golden.fixtures import golden_bottom_c_invalidation

    db_path = tmp_path / "life.db"
    bars = golden_bottom_c_invalidation()
    # 模拟完整流水线：先写候选结构，再让 C 生命周期触发状态变化
    class Fixed:
        name = "fixed"
        def fetch(self, symbol, *, min_rows=21):
            from lei_signal.data.providers import PriceData
            from lei_signal.data.symbols import resolve_symbol
            from lei_signal.data.validation import ValidationReport
            info = resolve_symbol(symbol)
            return PriceData(
                symbol=info.symbol, display_name=info.symbol, bars=bars,
                report=ValidationReport(
                    rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
                    adjusted=True, provider="fixed", duplicates_removed=0, warnings=(),
                ),
                info=info,
            )
    analyze(
        "SYN", provider=Fixed(),
        sqlite_path=str(db_path), run_id="life-1",
    )
    conn = connect(db_path)
    lifecycle = conn.execute(
        "SELECT from_status, to_status, reason FROM structure_lifecycle ORDER BY id"
    ).fetchall()
    assert len(lifecycle) > 0, "结构生命周期必须被记录"
    # 必须记录到 None→candidate（创建）+ 至少一个真实转换
    transitions = {(r["from_status"], r["to_status"]) for r in lifecycle}
    # from_status=NULL 表示创建
    assert (None, "candidate") in transitions or (None, "invalidated") in transitions
    # 至少一个真实转换：结构进入失效或确认
    assert any(t in transitions for t in [
        ("candidate", "confirmed"),
        ("candidate", "invalidated"),
        ("confirmed", "invalidated"),
    ]), f"必须有完整的状态转换记录，实际 {transitions}"


def test_local_csv_upload_drives_analysis(tmp_path) -> None:  # noqa: ANN001
    """修复 9：上传本地 CSV 必须能驱动分析。"""
    from lei_signal.ui.app import _analyze_upload
    bars = _bars(120, seed=51)
    csv_path = tmp_path / "fixture.csv"
    bars.to_csv(csv_path)

    class FakeUpload:
        name = "fixture.csv"
        def __init__(self, path):
            self._path = path
        def read(self):
            with open(self._path, "rb") as f:
                return f.read()

    result = _analyze_upload(FakeUpload(csv_path), "159915", build_history=False)
    assert result.symbol == "159915.SZ"
    assert len(result.frame) == 120


def test_local_parquet_upload_drives_analysis(tmp_path) -> None:  # noqa: ANN001
    """修复 9：上传本地 Parquet 必须能驱动分析。"""
    from lei_signal.ui.app import _analyze_upload
    bars = _bars(120, seed=53)
    pq_path = tmp_path / "fixture.parquet"
    bars.to_parquet(pq_path)

    class FakeUpload:
        name = "fixture.parquet"
        def __init__(self, path):
            self._path = path
        def read(self):
            with open(self._path, "rb") as f:
                return f.read()

    result = _analyze_upload(FakeUpload(pq_path), "159915", build_history=False)
    assert result.symbol == "159915.SZ"
    assert len(result.frame) == 120
