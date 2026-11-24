"""Small transactional SQLite event store for immutable prospective facts."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import canonical

SCHEMA = """
CREATE TABLE IF NOT EXISTS run (id INTEGER PRIMARY KEY CHECK(id=1),
 spec TEXT NOT NULL, spec_hash TEXT NOT NULL,
 last_run_at TEXT, last_source_at TEXT, actions_verified_through TEXT);
CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL,
 account_id TEXT, observation_id TEXT, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_events_at ON events(at,id);
CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY,
 payload_hash TEXT NOT NULL, payload TEXT NOT NULL,
 source_at TEXT NOT NULL, received_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, account_id TEXT NOT NULL,
 created_at TEXT NOT NULL,
 symbol TEXT NOT NULL, requested_qty INTEGER, filled_qty INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL, first_quote_id TEXT);
CREATE TABLE IF NOT EXISTS fills (id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
 observation_id TEXT NOT NULL,
 at TEXT NOT NULL, qty INTEGER NOT NULL, price TEXT NOT NULL, fee TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, economic_key TEXT NOT NULL UNIQUE,
 payload TEXT NOT NULL, ex_date TEXT NOT NULL, pay_date TEXT, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS valuations (id TEXT PRIMARY KEY,
 account_id TEXT NOT NULL, day TEXT NOT NULL,
 observation_id TEXT, payload TEXT NOT NULL, UNIQUE(account_id,day));
"""


@contextmanager
def transaction(path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA)
        db.execute("BEGIN IMMEDIATE")
        if "actions_verified_through" not in {
            row[1] for row in db.execute("PRAGMA table_info(run)")
        }:
            db.execute("ALTER TABLE run ADD COLUMN actions_verified_through TEXT")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def read_only(path: str | Path) -> sqlite3.Connection | None:
    path = Path(path)
    if not path.is_file():
        return None
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def event(
    db: sqlite3.Connection,
    *,
    id: str,
    at: str,
    kind: str,
    account_id: str | None = None,
    observation_id: str | None = None,
    payload: dict | None = None,
) -> None:
    body = canonical(payload or {})
    old = db.execute(
        "SELECT at,kind,account_id,observation_id,payload FROM events WHERE id=?", (id,)
    ).fetchone()
    value = (at, kind, account_id, observation_id, body)
    if old:
        if tuple(old) != value:
            raise ValueError(f"event identity conflict: {id}")
        return
    db.execute(
        "INSERT INTO events(id,at,kind,account_id,observation_id,payload) VALUES(?,?,?,?,?,?)",
        (id, *value),
    )
