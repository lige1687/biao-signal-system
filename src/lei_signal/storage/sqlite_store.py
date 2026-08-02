"""SQLite 存储：迁移、幂等事件写入与结构生命周期。

迁移与幂等模式参考
    licai-wt-pg-integration@2ee7fdc
    src/plan_guardian/adapters/sqlite/migrations.py
改造原因：
  1. 旧实现用 `migration_steps/NNN_*.py` 模块目录 + pkgutil 发现；
     新项目规模小，改为模块内声明的 (ordinal, name, sql) 序列，
     保留「按序号顺序应用 + schema_migrations 记账 + 幂等」的核心设计。
  2. 只定义 signal_events / structure_instances / daily_assessments /
     analysis_runs / rule_registry；不移植账本、订单、通知、账户表。
  3. signal_events 只追加：以 event_id 为主键，重复写入用
     INSERT OR IGNORE 忽略，绝不 UPDATE 已有事件。
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lei_signal.domain.types import DailyAssessment, SignalEvent, StructureInstance

MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (
        1,
        "001_core_tables",
        """
        CREATE TABLE IF NOT EXISTS assets (
            symbol TEXT PRIMARY KEY,
            display_name TEXT,
            market TEXT,
            timezone TEXT
        );

        -- 只追加：event_id 为主键，重复运行以 INSERT OR IGNORE 幂等忽略
        CREATE TABLE IF NOT EXISTS signal_events (
            event_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            event_date TEXT NOT NULL,
            available_date TEXT NOT NULL,
            rule_id TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            direction TEXT NOT NULL,
            severity TEXT NOT NULL,
            strength INTEGER NOT NULL,
            reason_cn TEXT NOT NULL,
            provenance TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            invalidation_json TEXT NOT NULL,
            structure_id TEXT,
            run_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_symbol_available
            ON signal_events(symbol, available_date);
        CREATE INDEX IF NOT EXISTS idx_events_rule ON signal_events(rule_id);

        CREATE TABLE IF NOT EXISTS structure_instances (
            structure_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            structure_type TEXT NOT NULL,
            side TEXT NOT NULL,
            detected_date TEXT NOT NULL,
            confirmed_date TEXT,
            c_price REAL,
            neckline REAL,
            reference_high REAL,
            status TEXT NOT NULL,
            invalidated_date TEXT,
            invalidated_reason TEXT,
            source_event_ids TEXT NOT NULL,
            source_rule_id TEXT,
            provenance TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_assessments (
            symbol TEXT NOT NULL,
            as_of TEXT NOT NULL,
            stage TEXT NOT NULL,
            color TEXT NOT NULL,
            dimensions_json TEXT NOT NULL,
            stage_change_reason_cn TEXT,
            primary_structure_id TEXT,
            b1_price REAL,
            data_status TEXT NOT NULL,
            ruleset_version TEXT NOT NULL,
            PRIMARY KEY (symbol, as_of)
        );

        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ruleset_version TEXT NOT NULL,
            provider TEXT,
            last_data_date TEXT,
            event_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rule_registry (
            rule_id TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            provenance TEXT NOT NULL,
            note_cn TEXT,
            PRIMARY KEY (rule_id, rule_version)
        );
        """,
    ),
    (
        2,
        "002_structure_lifecycle_events",
        """
        -- 结构状态可以更新，但每次变化必须同步写一条生命周期事件
        CREATE TABLE IF NOT EXISTS structure_lifecycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            structure_id TEXT NOT NULL,
            changed_on TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reason TEXT,
            UNIQUE (structure_id, changed_on, to_status)
        );
        CREATE INDEX IF NOT EXISTS idx_lifecycle_structure
            ON structure_lifecycle(structure_id);
        """,
    ),
    (
        3,
        "003_opportunity_risk_split",
        """
        -- Round 2 修复 4：机会阶段与风险状态分离。
        -- daily_assessments 增加 opportunity_stage / risk_state 独立字段。
        -- 旧 stage 字段保留作为兼容。
        -- 使用安全的列添加：sqlite 无 IF NOT EXISTS，包装在 try/catch 中。
        """,
    ),
    (
        4,
        "004_event_lifecycle_columns",
        """
        -- Round 2 收尾修复：事件生命周期字段持久化。
        -- valid_until / lifecycle_id / ended_event_id 使数据库可还原状态的
        -- 有效/结束时间，与内存事件、解释层、研究使用同一生命周期。
        -- sqlite 无 ALTER TABLE ADD COLUMN IF NOT EXISTS，由 apply_migrations 处理。
        """,
    ),
)


@dataclass(frozen=True, slots=True)
class WriteReport:
    """写入结果，区分新增与幂等忽略。"""

    inserted: int
    ignored: int


def connect(path: str | Path) -> sqlite3.Connection:
    """打开连接并应用迁移。"""
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    apply_migrations(connection)
    return connection


def _safe_add_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    type_sql: str,
) -> None:
    """sqlite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS；用 try/except 兜底。"""
    try:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {type_sql}"
        )
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise


def apply_migrations(connection: sqlite3.Connection) -> tuple[str, ...]:
    """按序号顺序应用未执行的迁移。已应用的跳过（幂等）。"""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            ordinal INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()

    applied = {
        row["name"] for row in connection.execute("SELECT name FROM schema_migrations")
    }
    executed: list[str] = []
    for ordinal, name, sql in sorted(MIGRATIONS):
        if name in applied:
            continue
        # 003 包含 ALTER TABLE ADD COLUMN：sqlite 无 IF NOT EXISTS，
        # 用 _safe_add_column 处理
        if name == "003_opportunity_risk_split":
            _safe_add_column(connection, "daily_assessments", "opportunity_stage", "TEXT")
            _safe_add_column(connection, "daily_assessments", "risk_state", "TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_opp "
                "ON daily_assessments(symbol, as_of, opportunity_stage)"
            )
        elif name == "004_event_lifecycle_columns":
            _safe_add_column(connection, "signal_events", "valid_until", "TEXT")
            _safe_add_column(connection, "signal_events", "lifecycle_id", "TEXT")
            _safe_add_column(connection, "signal_events", "ended_event_id", "TEXT")
        else:
            # executescript 会隐式提交，因此记账单独提交
            connection.executescript(sql)
        connection.execute(
            "INSERT INTO schema_migrations (ordinal, name) VALUES (?, ?)",
            (ordinal, name),
        )
        connection.commit()
        executed.append(name)
    return tuple(executed)


def write_events(
    connection: sqlite3.Connection,
    events: Iterable[SignalEvent],
    *,
    run_id: str | None = None,
) -> WriteReport:
    """只追加写入事件。同 event_id 幂等忽略，绝不覆盖已有行。

    Round 2 收尾修复：写入 valid_until / lifecycle_id / ended_event_id，
    使数据库可还原状态的「有效/结束时间」，与内存事件、解释层、研究同一生命周期。
    """
    inserted = 0
    attempted = 0
    for event in events:
        attempted += 1
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO signal_events (
                event_id, symbol, timeframe, event_date, available_date,
                rule_id, rule_version, direction, severity, strength,
                reason_cn, provenance, evidence_json, invalidation_json,
                structure_id, run_id, valid_until, lifecycle_id, ended_event_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event.event_id,
                event.symbol,
                event.timeframe,
                event.event_date.isoformat(),
                event.available_date.isoformat(),
                event.rule_id,
                event.rule_version,
                event.direction.value,
                event.severity.value,
                event.strength,
                event.reason_cn,
                event.provenance.value,
                json.dumps(event.evidence, ensure_ascii=False, sort_keys=True, default=str),
                json.dumps(event.invalidation, ensure_ascii=False, sort_keys=True, default=str),
                event.structure_id,
                run_id or event.run_id,
                event.valid_until.isoformat() if event.valid_until is not None else None,
                event.lifecycle_id,
                event.ended_event_id,
            ),
        )
        inserted += cursor.rowcount if cursor.rowcount > 0 else 0
    connection.commit()
    return WriteReport(inserted=inserted, ignored=attempted - inserted)


def _expected_structure_transitions(
    structure: StructureInstance,
) -> list[tuple[str | None, str, date]]:
    """根据结构日期字段推断完整状态链（按时间顺序）。

    每个元素 ``(from_status, to_status, changed_on)``：
      * ``None -> candidate``                  @ detected_date
      * ``candidate -> confirmed``             @ confirmed_date     （已确认时）
      * ``confirmed/candidate -> invalidated``  @ invalidated_date  （已失效时）

    旧实现只比较「数据库已有状态」与「当前快照状态」，对一次性传入的最终结构
    只会记录一次跳变，并因 ``confirmed_date or invalidated_date`` 的 or 链把
    **确认日**误当作**失效日**，漏掉 candidate→confirmed 与 confirmed→invalidated。
    这里改为从日期字段重建完整链路，每次运行都补全缺失转换（INSERT OR IGNORE 幂等）。
    """
    transitions: list[tuple[str | None, str, date]] = [
        (None, "candidate", structure.detected_date),
    ]
    confirmed_date = structure.confirmed_date
    is_confirmed = confirmed_date is not None and structure.status.value in (
        "confirmed",
        "active",
        "invalidated",
    )
    if is_confirmed and confirmed_date is not None:
        transitions.append(("candidate", "confirmed", confirmed_date))
    if structure.invalidated_date is not None and structure.status.value == "invalidated":
        prev = "confirmed" if is_confirmed else "candidate"
        transitions.append((prev, "invalidated", structure.invalidated_date))
    return transitions


def write_structures(
    connection: sqlite3.Connection,
    structures: Iterable[StructureInstance],
) -> WriteReport:
    """写入结构。状态变化允许更新，但每次变化同步写生命周期事件。

    Round 2 收尾修复：生命周期依据 ``detected_date`` / ``confirmed_date`` /
    ``invalidated_date`` 重建完整转换链，每次运行幂等补全（不再漏记确认、不再把
    确认日误当失效日）。
    """
    inserted = 0
    updated = 0
    for structure in structures:
        existing = connection.execute(
            "SELECT status FROM structure_instances WHERE structure_id = ?",
            (structure.structure_id,),
        ).fetchone()
        payload = (
            structure.structure_id,
            structure.symbol,
            structure.structure_type,
            structure.side,
            structure.detected_date.isoformat(),
            structure.confirmed_date.isoformat() if structure.confirmed_date else None,
            structure.c_price,
            structure.neckline,
            structure.reference_high,
            structure.status.value,
            structure.invalidated_date.isoformat() if structure.invalidated_date else None,
            structure.invalidated_reason,
            json.dumps(list(structure.source_event_ids), ensure_ascii=False),
            structure.source_rule_id,
            structure.provenance.value,
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO structure_instances (
                    structure_id, symbol, structure_type, side, detected_date,
                    confirmed_date, c_price, neckline, reference_high, status,
                    invalidated_date, invalidated_reason, source_event_ids,
                    source_rule_id, provenance
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                payload,
            )
            inserted += 1
        elif existing["status"] != structure.status.value:
            connection.execute(
                """
                UPDATE structure_instances SET
                    confirmed_date = ?, status = ?, invalidated_date = ?,
                    invalidated_reason = ?
                WHERE structure_id = ?
                """,
                (
                    structure.confirmed_date.isoformat() if structure.confirmed_date else None,
                    structure.status.value,
                    structure.invalidated_date.isoformat()
                    if structure.invalidated_date
                    else None,
                    structure.invalidated_reason,
                    structure.structure_id,
                ),
            )
            updated += 1
        # 生命周期：依据日期字段重建完整转换链，幂等补全（INSERT OR IGNORE）。
        # 放在 if/elif 之外，保证无论结构是新建还是更新，缺失转换都会被补上。
        for from_status, to_status, changed_on in _expected_structure_transitions(
            structure
        ):
            _record_lifecycle(
                connection,
                structure_id=structure.structure_id,
                changed_on=changed_on,
                from_status=from_status,
                to_status=to_status,
                reason=structure.invalidated_reason or "status_change",
            )
    connection.commit()
    return WriteReport(inserted=inserted, ignored=updated)


def _record_lifecycle(
    connection: sqlite3.Connection,
    *,
    structure_id: str,
    changed_on: date,
    from_status: str | None,
    to_status: str,
    reason: str | None,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO structure_lifecycle
            (structure_id, changed_on, from_status, to_status, reason)
        VALUES (?,?,?,?,?)
        """,
        (structure_id, changed_on.isoformat(), from_status, to_status, reason),
    )


def write_assessment(
    connection: sqlite3.Connection,
    assessment: DailyAssessment,
) -> None:
    """写入每日解释快照（同一天重复运行覆盖为同值）。

    Round 2 修复 4：同时写入 opportunity_stage 与 risk_state 独立字段。
    旧 stage 字段保留作为兼容。
    """
    connection.execute(
        """
        INSERT OR REPLACE INTO daily_assessments (
            symbol, as_of, stage, color, dimensions_json,
            stage_change_reason_cn, primary_structure_id, b1_price,
            data_status, ruleset_version,
            opportunity_stage, risk_state
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            assessment.symbol,
            assessment.as_of.isoformat(),
            assessment.stage.value,
            assessment.color.value,
            json.dumps(assessment.dimensions, ensure_ascii=False, sort_keys=True),
            assessment.stage_change_reason_cn,
            assessment.primary_structure.structure_id
            if assessment.primary_structure
            else None,
            assessment.b1_price,
            assessment.data_status,
            assessment.rule_ruleset_version,
            assessment.opportunity_stage.value,
            assessment.risk_state.value,
        ),
    )
    connection.commit()


def record_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    symbol: str,
    started_at: str,
    ruleset_version: str,
    provider: str | None,
    last_data_date: date | None,
    event_count: int,
) -> None:
    """记录运行元数据，使结果可复现追溯。"""
    connection.execute(
        """
        INSERT OR REPLACE INTO analysis_runs (
            run_id, symbol, started_at, ruleset_version,
            provider, last_data_date, event_count
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            run_id,
            symbol,
            started_at,
            ruleset_version,
            provider,
            last_data_date.isoformat() if last_data_date else None,
            event_count,
        ),
    )
    connection.commit()


def count_events(connection: sqlite3.Connection, symbol: str | None = None) -> int:
    if symbol is None:
        row = connection.execute("SELECT COUNT(*) AS n FROM signal_events").fetchone()
    else:
        row = connection.execute(
            "SELECT COUNT(*) AS n FROM signal_events WHERE symbol = ?", (symbol,)
        ).fetchone()
    return int(row["n"])


__all__ = [
    "MIGRATIONS",
    "WriteReport",
    "apply_migrations",
    "connect",
    "count_events",
    "record_run",
    "write_assessment",
    "write_events",
    "write_structures",
]
