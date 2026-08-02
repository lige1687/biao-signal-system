"""Round 2 修复 4：机会阶段与风险状态端到端分离。

UI 与 SQLite 必须分别显示/保存 opportunity_stage 与 risk_state。
旧 stage 字段保留兼容，但不得用于新 UI / 新持久化逻辑。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.storage.sqlite_store import connect, count_events


def test_opportunity_stage_independent_from_risk_state() -> None:
    """风险变化不应遮盖机会阶段。"""
    rows: list[dict[str, float]] = []
    for i in range(60):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 阴线 + 阳线反包
    rows.append({"open": 71.0, "high": 71.3, "low": 69.0, "close": 69.5, "volume": 1_100_000})
    rows.append({"open": 68.5, "high": 73.0, "low": 68.3, "close": 72.8, "volume": 1_900_000})
    for i in range(20):
        close = 72.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("T", bars, build_history=True)
    # 在最后一天：机会阶段是「结构确认」级别
    a = result.assessment
    # opportunity_stage 不应是 legacy Stage.INVALIDATED（核心断言：分离）
    assert a.opportunity_stage.value != "invalidated", (
        f"机会阶段必须独立：不应被 key_risk 覆盖为 invalidated，实际 {a.opportunity_stage.value}"
    )
    # 风险状态字段存在（不一定是 normal）
    assert a.risk_state is not None


def test_sqlite_stores_opportunity_and_risk_separately(tmp_path) -> None:  # noqa: ANN001
    """SQLite daily_assessments 必须同时保存 opportunity_stage 与 risk_state。"""
    rows: list[dict[str, float]] = []
    for i in range(60):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    rows.append({"open": 71.0, "high": 71.3, "low": 69.0, "close": 69.5, "volume": 1_100_000})
    rows.append({"open": 68.5, "high": 73.0, "low": 68.3, "close": 72.8, "volume": 1_900_000})
    for i in range(20):
        close = 72.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    db_path = tmp_path / "opp_risk.db"
    from lei_signal.compose.pipeline import analyze
    from lei_signal.data.providers import ChainedPriceProvider, EastmoneyPriceProvider
    from unittest.mock import patch
    # 直接分析 bars 并写入 SQLite
    from lei_signal.compose.pipeline import analyze_bars
    from lei_signal.storage.sqlite_store import (
        connect, write_assessment, write_events, write_structures, record_run,
    )
    from datetime import datetime, UTC
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import ValidationReport
    info = resolve_symbol("T")
    price = PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=bars,
        report=ValidationReport(
            rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
            adjusted=True, provider="fixture", duplicates_removed=0, warnings=(),
        ),
        info=info,
    )
    result = analyze_bars("T", bars, price_data=price, build_history=False)
    conn = connect(db_path)
    with conn:
        write_events(conn, result.events, run_id="opp-1")
        write_structures(conn, result.structures)
        write_assessment(conn, result.assessment)
        record_run(
            conn, run_id="opp-1", symbol="T",
            started_at=datetime.now(UTC).isoformat(),
            ruleset_version=result.assessment.rule_ruleset_version,
            provider="fixture", last_data_date=bars.index[-1].date(),
            event_count=len(result.events),
        )
    conn = connect(db_path)
    row = conn.execute(
        "SELECT opportunity_stage, risk_state, stage FROM daily_assessments "
        "WHERE symbol='T' ORDER BY as_of DESC LIMIT 1"
    ).fetchone()
    # 两个独立字段都有值
    assert row["opportunity_stage"] is not None
    assert row["risk_state"] is not None
    # opportunity_stage 不应是 legacy "invalidated"
    assert row["opportunity_stage"] != "invalidated"
    # 旧 stage 字段保留兼容
    assert row["stage"] is not None
    conn.close()


def test_migration_compatible_with_existing_database(tmp_path) -> None:  # noqa: ANN001
    """旧数据库（只有 001 + 002）升级时，003 必须兼容。"""
    import sqlite3
    from lei_signal.storage.sqlite_store import write_assessment
    from lei_signal.domain.types import (
        DailyAssessment, SignalColor, Stage, RiskState,
    )
    db_path = tmp_path / "upgrade.db"
    # 手动构造一个只有 001 + 002 的旧数据库
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "ordinal INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
        "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    # 001
    for stmt in [
        "CREATE TABLE IF NOT EXISTS assets (symbol TEXT PRIMARY KEY, display_name TEXT, market TEXT, timezone TEXT)",
        "CREATE TABLE IF NOT EXISTS signal_events ("
        "event_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, timeframe TEXT NOT NULL, "
        "event_date TEXT NOT NULL, available_date TEXT NOT NULL, "
        "rule_id TEXT NOT NULL, rule_version TEXT NOT NULL, direction TEXT NOT NULL, "
        "severity TEXT NOT NULL, strength INTEGER NOT NULL, reason_cn TEXT NOT NULL, "
        "provenance TEXT NOT NULL, evidence_json TEXT NOT NULL, "
        "invalidation_json TEXT NOT NULL, structure_id TEXT, run_id TEXT)",
        "CREATE TABLE IF NOT EXISTS structure_instances ("
        "structure_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, structure_type TEXT NOT NULL, "
        "side TEXT NOT NULL, detected_date TEXT NOT NULL, confirmed_date TEXT, "
        "c_price REAL, neckline REAL, reference_high REAL, status TEXT NOT NULL, "
        "invalidated_date TEXT, invalidated_reason TEXT, "
        "source_event_ids TEXT NOT NULL, source_rule_id TEXT, provenance TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS daily_assessments ("
        "symbol TEXT NOT NULL, as_of TEXT NOT NULL, stage TEXT NOT NULL, "
        "color TEXT NOT NULL, dimensions_json TEXT NOT NULL, "
        "stage_change_reason_cn TEXT, primary_structure_id TEXT, b1_price REAL, "
        "data_status TEXT NOT NULL, ruleset_version TEXT NOT NULL, "
        "PRIMARY KEY (symbol, as_of))",
        "CREATE TABLE IF NOT EXISTS analysis_runs ("
        "run_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, started_at TEXT NOT NULL, "
        "ruleset_version TEXT NOT NULL, provider TEXT, last_data_date TEXT, "
        "event_count INTEGER NOT NULL)",
        "CREATE TABLE IF NOT EXISTS rule_registry ("
        "rule_id TEXT NOT NULL, rule_version TEXT NOT NULL, provenance TEXT NOT NULL, "
        "note_cn TEXT, PRIMARY KEY (rule_id, rule_version))",
        "CREATE INDEX IF NOT EXISTS idx_events_symbol_available "
        "ON signal_events(symbol, available_date)",
        "CREATE INDEX IF NOT EXISTS idx_events_rule ON signal_events(rule_id)",
    ]:
        conn.executescript(stmt)
    conn.execute(
        "INSERT INTO schema_migrations (ordinal, name) VALUES (?, ?)",
        (1, "001_core_tables"),
    )
    # 002
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS structure_lifecycle ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "structure_id TEXT NOT NULL, changed_on TEXT NOT NULL, "
        "from_status TEXT, to_status TEXT NOT NULL, reason TEXT, "
        "UNIQUE (structure_id, changed_on, to_status))"
    )
    conn.execute(
        "INSERT INTO schema_migrations (ordinal, name) VALUES (?, ?)",
        (2, "002_structure_lifecycle_events"),
    )
    conn.commit()
    cols_before = [r["name"] for r in conn.execute("PRAGMA table_info(daily_assessments)")]
    assert "opportunity_stage" not in cols_before
    conn.close()
    # 现在用 connect() 触发迁移
    conn = connect(db_path)
    cols_after = [r["name"] for r in conn.execute("PRAGMA table_info(daily_assessments)")]
    assert "opportunity_stage" in cols_after
    assert "risk_state" in cols_after
    # 写一个 assessment
    from datetime import date
    assessment = DailyAssessment(
        symbol="UPG", as_of=date(2024, 1, 15),
        opportunity_stage=Stage.STRUCTURE_CONFIRMED, risk_state=RiskState.NORMAL,
        stage=Stage.STRUCTURE_CONFIRMED, color=SignalColor.GREEN,
    )
    write_assessment(conn, assessment)
    row = conn.execute(
        "SELECT opportunity_stage, risk_state FROM daily_assessments WHERE symbol='UPG'"
    ).fetchone()
    assert row["opportunity_stage"] == "structure_confirmed"
    assert row["risk_state"] == "normal"
    conn.close()
