"""Round 3 修复 D3：SQLite 增量回放生命周期一致性。

复现的真实场景（来自任务书）：

    先分析同一序列前 300 根并写库
    → 再用同一行情 600 根分析并写入同一个数据库
    → 查询每个共同 event_id 的最新生命周期
    → 必须与第二次 AnalysisResult 完全一致

之所以需要这条测试：旧实现 ``INSERT OR IGNORE + event_id`` 主键
会让 ``valid_until`` 第一次写入后被锁死，二次重跑（更长行情下同一事件
的 valid_until 延长）会丢失真正的有效窗口。
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.storage.sqlite_store import (
    connect,
    read_latest_lifecycle,
    write_assessment,
    write_event_lifecycles,
    write_events,
    write_structures,
)


def _bars(rows: int, seed: int = 5) -> pd.DataFrame:
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


def _write_full(conn, result, run_id: str, as_of: date) -> None:
    """完整持久化（与 ``analyze`` 内部使用同一组函数）。"""
    write_events(conn, result.events, run_id=run_id)
    write_structures(conn, result.structures)
    write_assessment(conn, result.assessment)
    write_event_lifecycles(conn, result.events, run_id=run_id, as_of=as_of)


def test_incremental_replay_keeps_lifecycle_consistent(tmp_path) -> None:  # noqa: ANN001
    """300 根 → 600 根增量重跑：每个共同 event_id 的最新快照必须与
    第二次 AnalysisResult 的内存值完全一致。"""
    db_path = tmp_path / "incr.db"
    full = _bars(600, seed=11)
    prefix = full.iloc[:300]

    # 第一次：300 根
    r1 = analyze_bars("SYN", prefix)
    conn = connect(db_path)
    _write_full(conn, r1, run_id="run-300", as_of=prefix.index[-1].date())
    # 第二次：600 根
    r2 = analyze_bars("SYN", full)
    _write_full(conn, r2, run_id="run-600", as_of=full.index[-1].date())

    r1_ids = {event.event_id for event in r1.events}
    r2_ids = {event.event_id for event in r2.events}
    common = r1_ids & r2_ids
    assert common, "两次分析必须存在共同事件才能验证增量一致性"

    by_id_r2 = {event.event_id: event for event in r2.events}

    drift: list[tuple[str, str, object, object]] = []
    for eid in common:
        snap = read_latest_lifecycle(conn, eid)
        latest = by_id_r2[eid]
        # 共同事件中以 as_of 较大的那次为准：``read_latest_lifecycle`` 按 as_of
        # 降序取最新，run-600 的 as_of 必然更大，所以返回的应该是 run-600 的快照
        assert snap is not None, f"{eid} 缺少生命周期快照"
        if snap.run_id != "run-600":
            drift.append((eid, "run_id", snap.run_id, "run-600"))
        expected_valid = latest.valid_until.isoformat() if latest.valid_until else None
        if snap.valid_until != expected_valid:
            drift.append((eid, "valid_until", snap.valid_until, expected_valid))
        if snap.lifecycle_id != latest.lifecycle_id:
            drift.append((eid, "lifecycle_id", snap.lifecycle_id, latest.lifecycle_id))
        if snap.ended_event_id != latest.ended_event_id:
            drift.append((eid, "ended_event_id", snap.ended_event_id, latest.ended_event_id))

    assert not drift, (
        f"增量回放后 {len(drift)} 条共同事件的生命周期与最新内存结果不一致：\n"
        + "\n".join(f"  {eid} {field}: db={db!r} mem={mem!r}"
                    for eid, field, db, mem in drift[:5])
    )


def test_repeated_write_is_idempotent(tmp_path) -> None:  # noqa: ANN001
    """同一 event_id / run_id / as_of 三元组重复写入不得产生新行。"""
    db_path = tmp_path / "idem.db"
    bars = _bars(300, seed=23)
    result = analyze_bars("SYN", bars)
    conn = connect(db_path)
    as_of = bars.index[-1].date()

    first, _ = write_event_lifecycles(
        conn, result.events, run_id="run-1", as_of=as_of
    )
    second, _ = write_event_lifecycles(
        conn, result.events, run_id="run-1", as_of=as_of
    )
    assert first == second, "同 (event_id, run_id, as_of) 重复写入应保持幂等"
    rows = conn.execute(
        "SELECT COUNT(*) AS n FROM event_lifecycle_snapshots"
    ).fetchone()["n"]
    assert rows == len(result.events)


def test_lifecycle_extends_when_more_data(tmp_path) -> None:  # noqa: ANN001
    """更长行情下 valid_until 延长必须被记录（旧 valid_until 不被覆盖）。"""
    db_path = tmp_path / "ext.db"
    full = _bars(600, seed=29)
    prefix = full.iloc[:300]
    conn = connect(db_path)
    r1 = analyze_bars("SYN", prefix)
    write_event_lifecycles(
        conn, r1.events, run_id="run-300", as_of=prefix.index[-1].date()
    )
    r2 = analyze_bars("SYN", full)
    write_event_lifecycles(
        conn, r2.events, run_id="run-600", as_of=full.index[-1].date()
    )

    # 找一个两次都出现且内存里 valid_until 不同的 event
    by_id_r1 = {e.event_id: e for e in r1.events}
    by_id_r2 = {e.event_id: e for e in r2.events}
    diffs = [
        eid for eid in by_id_r1.keys() & by_id_r2.keys()
        if by_id_r1[eid].valid_until != by_id_r2[eid].valid_until
    ]
    if not diffs:
        pytest.skip("本样例两次分析 valid_until 没有差异（结构性可能如此）")
    for eid in diffs[:5]:
        snap = read_latest_lifecycle(conn, eid)
        assert snap is not None
        expected = by_id_r2[eid].valid_until.isoformat() if by_id_r2[eid].valid_until else None
        assert snap.valid_until == expected, (
            f"{eid}: 增量后应取较长 valid_until={expected}，实际 {snap.valid_until}"
        )

    # 旧快照仍然存在（历史演变过程不抹除）
    old_rows = conn.execute(
        "SELECT COUNT(*) AS n FROM event_lifecycle_snapshots WHERE run_id = 'run-300'"
    ).fetchone()["n"]
    assert old_rows > 0, "旧 run_id 的快照应保留以便审计"


def test_identical_run_produces_identical_snapshot(tmp_path) -> None:  # noqa: ANN001
    """同一完整行情同一 run_id 跑两次：所有字段必须一致。"""
    db_path = tmp_path / "same.db"
    bars = _bars(400, seed=37)
    conn = connect(db_path)
    r = analyze_bars("SYN", bars)
    as_of = bars.index[-1].date()
    write_event_lifecycles(conn, r.events, run_id="r-1", as_of=as_of)
    write_event_lifecycles(conn, r.events, run_id="r-1", as_of=as_of)
    # 每条 event 仍然只有一条快照
    rows = conn.execute(
        "SELECT event_id, COUNT(*) AS n FROM event_lifecycle_snapshots "
        "WHERE run_id = 'r-1' GROUP BY event_id"
    ).fetchall()
    duplicates = [row for row in rows if row["n"] > 1]
    assert not duplicates, f"同主键不应有重复行: {duplicates[:3]}"


def test_read_latest_picks_higher_as_of(tmp_path) -> None:  # noqa: ANN001
    """``read_latest_lifecycle`` 在两次不同 as_of 的快照中必须返回较大者。"""
    db_path = tmp_path / "asof.db"
    bars = _bars(400, seed=41)
    conn = connect(db_path)
    result = analyze_bars("SYN", bars)
    # 同一 run 不同 as_of 模拟「同一事件在两个时间点看到不同 valid_until」
    write_event_lifecycles(
        conn, result.events, run_id="r-1", as_of=date(2023, 1, 1)
    )
    write_event_lifecycles(
        conn, result.events, run_id="r-1", as_of=date(2024, 6, 1)
    )

    sample = result.events[0]
    snap = read_latest_lifecycle(conn, sample.event_id)
    assert snap is not None
    assert snap.as_of == "2024-06-01", "应按 as_of 降序取最新"
