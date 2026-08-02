"""存储层门禁：迁移幂等、事件只追加、结构生命周期。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.types import StructureStatus
from lei_signal.storage.sqlite_store import (
    apply_migrations,
    connect,
    count_events,
    record_run,
    write_assessment,
    write_events,
    write_structures,
)


def _bars(rows: int = 400, seed: int = 3) -> pd.DataFrame:
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
        index=pd.bdate_range("2023-01-02", periods=rows),
    )


@pytest.fixture()
def db(tmp_path):  # noqa: ANN001, ANN201
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_migrations_apply_once_and_are_idempotent(tmp_path) -> None:  # noqa: ANN001
    connection = connect(tmp_path / "m.db")
    # 首次连接已应用全部迁移
    first_rerun = apply_migrations(connection)
    assert first_rerun == (), "重复应用迁移必须是空操作"

    names = {
        row["name"]
        for row in connection.execute("SELECT name FROM schema_migrations")
    }
    assert names == {
        "001_core_tables",
        "002_structure_lifecycle_events",
        "003_opportunity_risk_split",
    }
    connection.close()

    # 重新打开同一文件不得重复应用
    reopened = connect(tmp_path / "m.db")
    assert apply_migrations(reopened) == ()
    reopened.close()


def test_all_required_tables_exist(db) -> None:  # noqa: ANN001
    tables = {
        row["name"]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    for required in (
        "assets", "signal_events", "structure_instances", "daily_assessments",
        "analysis_runs", "rule_registry", "structure_lifecycle", "schema_migrations",
    ):
        assert required in tables, f"缺少表 {required}"


def test_events_are_append_only_and_idempotent(db) -> None:  # noqa: ANN001
    """同样数据重复写入不得重复插入，也不得覆盖已有事件。"""
    result = analyze_bars("SYN", _bars())
    first = write_events(db, result.events, run_id="run-1")
    assert first.inserted == len(result.events)
    assert first.ignored == 0

    second = write_events(db, result.events, run_id="run-2")
    assert second.inserted == 0, "重复运行不得重复写入"
    assert second.ignored == len(result.events)
    assert count_events(db, "SYN") == len(result.events)

    # run_id 不得被第二次运行覆盖
    row = db.execute(
        "SELECT run_id FROM signal_events WHERE event_id = ?",
        (result.events[0].event_id,),
    ).fetchone()
    assert row["run_id"] == "run-1", "已有事件不得被回写"


def test_event_evidence_roundtrips_as_json(db) -> None:  # noqa: ANN001
    result = analyze_bars("SYN", _bars())
    write_events(db, result.events)
    row = db.execute(
        "SELECT evidence_json, invalidation_json, rule_version, provenance "
        "FROM signal_events WHERE rule_id = 'lei_color' LIMIT 1"
    ).fetchone()
    assert row is not None
    import json

    evidence = json.loads(row["evidence_json"])
    assert "close" in evidence and "ema20" in evidence
    assert json.loads(row["invalidation_json"])
    assert row["rule_version"].count(".") == 2


def test_structure_status_change_writes_lifecycle_event(db) -> None:  # noqa: ANN001
    """结构状态可更新，但每次变化必须同步写生命周期事件。"""
    result = analyze_bars("SYN", _bars())
    bottoms = result.bottoms
    assert bottoms

    first = write_structures(db, bottoms)
    assert first.inserted == len(bottoms)

    lifecycle_count = db.execute(
        "SELECT COUNT(*) AS n FROM structure_lifecycle"
    ).fetchone()["n"]
    # 每个结构至少记录 1 条「None→candidate」创建记录
    assert lifecycle_count >= len(bottoms)

    # 手动推进一个**仍然存活**的结构的状态，必须产生新的生命周期记录。
    # （已失效结构再写入同一状态不构成变化，因此不能用它做本断言。）
    live = [s for s in bottoms if s.status is not StructureStatus.INVALIDATED]
    assert live, "样例必须包含至少一个未失效结构"
    target = live[0]
    original_status = target.status
    target.status = StructureStatus.INVALIDATED
    target.invalidated_date = result.frame.index[-1].date()
    target.invalidated_reason = "bottom_C_touched"

    write_structures(db, [target])
    rows = db.execute(
        "SELECT from_status, to_status, reason FROM structure_lifecycle "
        "WHERE structure_id = ? ORDER BY id",
        (target.structure_id,),
    ).fetchall()
    # 创建 (None→candidate) + 原始状态 (None→confirmed) + UPDATE 转换 (confirmed→invalidated)
    assert len(rows) >= 2
    # 必须有原始状态 → invalid 的转换
    assert any(r["to_status"] == "invalidated" and r["from_status"] == original_status.value
               for r in rows)


def test_assessment_and_run_metadata_are_recorded(db) -> None:  # noqa: ANN001
    result = analyze_bars("SYN", _bars())
    write_assessment(db, result.assessment)
    row = db.execute("SELECT * FROM daily_assessments").fetchone()
    assert row["symbol"] == "SYN"
    assert row["stage"] == result.assessment.stage.value
    assert row["ruleset_version"] == "1.0.0"
    assert row["data_status"] == "OK"

    record_run(
        db,
        run_id="run-1",
        symbol="SYN",
        started_at="2026-08-01T10:00:00",
        ruleset_version="1.0.0",
        provider="fixture",
        last_data_date=result.frame.index[-1].date(),
        event_count=len(result.events),
    )
    run_row = db.execute("SELECT * FROM analysis_runs").fetchone()
    assert run_row["event_count"] == len(result.events)
    assert run_row["ruleset_version"] == "1.0.0"


def test_two_identical_runs_produce_identical_stored_event_set(tmp_path) -> None:  # noqa: ANN001
    """门禁 11：同样数据和规则重复运行，存储结果完全一致。"""
    bars = _bars(300, seed=17)

    def stored_ids(db_name: str) -> list[str]:
        connection = connect(tmp_path / db_name)
        result = analyze_bars("SYN", bars)
        write_events(connection, result.events)
        rows = connection.execute(
            "SELECT event_id FROM signal_events ORDER BY event_id"
        ).fetchall()
        connection.close()
        return [row["event_id"] for row in rows]

    assert stored_ids("a.db") == stored_ids("b.db")
