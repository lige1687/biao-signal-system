"""The integrated portfolio reader must leave the frozen ledger untouched."""

from __future__ import annotations

import hashlib
import gc
import json
import sqlite3
from pathlib import Path
from types import FunctionType

import pytest

from lei_signal.strategy_portfolios import readonly, service


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _original_with_history(active: Path, history_root: Path) -> dict:
    """Original presentation, with only its research fixture location redirected."""
    bindings = dict(service.dashboard.__globals__)
    bindings["RAW"] = history_root
    original = FunctionType(service.dashboard.__code__, bindings,
                            name="fixture_dashboard", argdefs=service.dashboard.__defaults__)
    return original(active)


def test_missing_ledger_is_explicit_and_creates_nothing(tmp_path):
    active = tmp_path / "absent" / "active"
    before = _sha(Path(service.__file__))
    result = readonly.dashboard(active, history_root=tmp_path / "absent-history")
    assert result["run"]["status"] == "尚未启动：本地账本不存在"
    assert result["started_at"] is None
    assert not active.exists()
    assert before == _sha(Path(service.__file__))


def test_existing_frozen_ledger_matches_original_presentation_without_writes(tmp_path):
    active = tmp_path / "active"
    history_root = tmp_path / "history"
    service.freeze(active, at="2026-10-30T00:00:00+00:00")
    original = _original_with_history(active, history_root)
    # Legacy service context managers do not close connections; let their WAL
    # checkpoint finish before measuring the read-only adapter's effects.
    gc.collect()
    ledger_sha = _sha(active / "ledger.sqlite")
    source_sha = _sha(Path(service.__file__))

    result = readonly.dashboard(active, history_root=history_root)
    original.pop("generated_at")
    result.pop("generated_at")
    assert result == original
    assert _sha(active / "ledger.sqlite") == ledger_sha
    assert {p.name for p in active.iterdir()} <= {
        "ledger.sqlite", "ledger.sqlite-wal", "ledger.sqlite-shm"
    }
    assert _sha(Path(service.__file__)) == source_sha


def test_readonly_connection_rejects_mutation(tmp_path):
    active = tmp_path / "active"
    service.freeze(active, at="2026-10-30T00:00:00+00:00")
    with readonly._connect(active) as conn:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO runs(date, at, status) VALUES ('x', 'x', 'x')")
    with sqlite3.connect(active / "ledger.sqlite") as conn:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_binding_mismatch_is_reported_without_re_freezing(tmp_path):
    active = tmp_path / "active"
    service.freeze(active, at="2026-10-30T00:00:00+00:00")
    with sqlite3.connect(active / "ledger.sqlite") as conn:
        frozen = json.loads(conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()[0])
        frozen["bindings"]["configs/strategy-portfolios.v1.json"] = "changed"
        conn.execute("UPDATE frozen SET payload=? WHERE id=1", (json.dumps(frozen),))
    result = readonly.dashboard(active, history_root=tmp_path / "history")
    assert "代码或规则已变化" in result["run"]["error"]
    with readonly._connect(active) as conn:
        saved = json.loads(conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()[0])
    assert saved == frozen


def test_reads_committed_wal_without_checkpointing_or_freezing(tmp_path):
    active = tmp_path / "active"
    writer = service.connect(active)
    try:
        service.freeze(active, at="2026-10-30T00:00:00+00:00")
        assert (active / "ledger.sqlite-wal").stat().st_size > 0
        result = readonly.dashboard(active, history_root=tmp_path / "history")
        assert result["started_at"] == "2026-10-30T00:00:00+00:00"
        assert result["run"]["status"] == "已冻结，采集进程尚未启动"
    finally:
        writer.close()


def test_presentation_global_list_fails_closed_if_service_changes(tmp_path):
    assert readonly._global_dependencies(service.dashboard.__code__) == readonly._EXPECTED_GLOBALS
    presenter = readonly._presentation(history_root=tmp_path)
    assert presenter.__globals__["connect"] is readonly._connect
    assert presenter.__globals__["read_state"] is readonly._read_state
    assert presenter.__globals__["freeze"] is readonly._freeze_read
    assert service.dashboard.__globals__["connect"] is service.connect

    def nested_global():
        return [int(value) for value in ("1",)]

    assert "int" in readonly._global_dependencies(nested_global.__code__)


def _history_mirror(tmp_path: Path):
    history_root = tmp_path / "history"
    history_root.mkdir()
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    external = tmp_path / "external" / "dashboard.json"
    content = json.dumps({"markets": {}}, ensure_ascii=False).encode()
    fingerprint = hashlib.sha256(content).hexdigest()
    (history_root / "history-result.json").write_text(json.dumps({
        "dashboard": str(external), "dashboard_sha256": fingerprint,
    }))
    mirror = cache_root / f"{fingerprint}.json"
    mirror.write_bytes(content)
    return history_root, cache_root, external, mirror


def test_history_uses_verified_mirror_without_opening_external_path(tmp_path, monkeypatch):
    history_root, cache_root, external, mirror = _history_mirror(tmp_path)
    original_read = Path.read_bytes

    def guarded_read(path):
        if path == external:
            raise AssertionError("external dashboard must not be opened")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    result = readonly.dashboard(tmp_path / "absent", history_root=history_root,
                                cache_root=cache_root)
    assert result["run"]["error"] is None
    assert len(result["markets"]) == 2
    assert mirror.is_file()
    assert not external.exists()


def test_verified_mirror_matches_original_history_presentation(tmp_path):
    history_root, cache_root, external, mirror = _history_mirror(tmp_path)
    external.parent.mkdir()
    external.write_bytes(mirror.read_bytes())
    active = tmp_path / "active"
    service.freeze(active, at="2026-10-30T00:00:00+00:00")
    original = _original_with_history(active, history_root)
    actual = readonly.dashboard(active, history_root=history_root, cache_root=cache_root)
    original.pop("generated_at")
    actual.pop("generated_at")
    assert actual == original


@pytest.mark.parametrize("damage", ["missing", "tampered"])
def test_history_mirror_unavailable_is_explicit(tmp_path, damage):
    history_root, cache_root, external, mirror = _history_mirror(tmp_path)
    if damage == "missing":
        mirror.unlink()
    else:
        mirror.write_bytes(b"tampered")
    result = readonly.dashboard(tmp_path / "absent", history_root=history_root,
                                cache_root=cache_root)
    assert "历史资料尚未就绪" in result["run"]["error"]
    assert not external.exists()
