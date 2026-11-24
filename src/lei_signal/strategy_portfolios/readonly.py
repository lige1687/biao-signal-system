"""Read-only adapter for the frozen strategy portfolio dashboard.

The existing dashboard owns all presentation formulas and copy. This module
reuses that exact function body with local, read-only database bindings; it
never patches service globals or enters the standalone server lifespan.
If the original function gains another global dependency, fail closed until
that dependency's read/write behavior has been reviewed here.
"""

from __future__ import annotations

import dis
import hashlib
import json
import re
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from types import CodeType, FunctionType

from . import service

_EXPECTED_GLOBALS = frozenset({
    "KeyError", "NAMES", "OSError", "Path", "RAW", "RULES", "TypeError",
    "ValueError", "_empty_history", "binding", "combined_forward", "connect",
    "datetime", "dict", "digest", "freeze", "int", "isinstance", "json", "len",
    "list", "load_json", "next", "next_collection", "read_state", "summary",
    "utcnow",
})


@contextmanager
def _connect(active: Path):
    db = Path(active) / "ledger.sqlite"
    if not db.is_file():
        raise FileNotFoundError(db)
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=20)) as conn:
        conn.execute("PRAGMA query_only=ON")
        yield conn


def _frozen(active: Path) -> dict | None:
    with _connect(active) as conn:
        row = conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()
    return json.loads(row[0]) if row else None


def _read_state(active: Path):
    frozen = _frozen(active)
    if frozen is None:
        return None
    with _connect(active) as conn:
        latest = conn.execute("SELECT payload FROM events ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(latest[0]) if latest else frozen["state"]


def _freeze_read(active: Path):
    """Return the existing binding receipt; never initialize a missing one."""
    frozen = _frozen(active)
    if frozen is None:
        raise ValueError("本地冻结记录缺失")
    return frozen


def _global_dependencies(code: CodeType) -> frozenset[str]:
    """Include nested comprehensions whether Python inlines them or not."""
    names = {instruction.argval for instruction in dis.get_instructions(code)
             if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}}
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            names.update(_global_dependencies(constant))
    return frozenset(names)


def _presentation(*, history_root: Path, cache_root: Path | None = None):
    names = _global_dependencies(service.dashboard.__code__)
    if names != _EXPECTED_GLOBALS:
        raise RuntimeError("组合看板依赖已变化，需重新核查只读适配")
    bindings = {
        name: service.dashboard.__globals__[name]
        for name in names if name in service.dashboard.__globals__
    }
    history_root = Path(history_root)
    cache_root = Path(cache_root) if cache_root is not None else (
        service.ROOT / ".codex/strategy-portfolios-display"
    )
    history_path = None
    history_hash = None

    def cached_history_bytes(path):
        if history_path is None or Path(path) != history_path:
            raise OSError("历史展示文件未在定位记录中声明")
        if not isinstance(history_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", history_hash):
            raise ValueError("历史展示文件指纹无效")
        mirror = cache_root / f"{history_hash}.json"
        try:
            content = mirror.read_bytes()
        except OSError as exc:
            raise OSError("仓内历史展示副本缺失或不可读") from exc
        if hashlib.sha256(content).hexdigest() != history_hash:
            raise ValueError("仓内历史展示副本指纹不一致")
        return content

    def load_json(path):
        nonlocal history_path, history_hash
        if Path(path) == history_root / "history-result.json":
            locator = service.load_json(path)
            history_path = Path(locator.get("dashboard") or locator.get("dashboard_path") or "")
            history_hash = locator.get("dashboard_sha256")
            return locator
        if history_path is not None and Path(path) == history_path:
            return json.loads(cached_history_bytes(path))
        return service.load_json(path)

    def digest(path):
        return hashlib.sha256(cached_history_bytes(path)).hexdigest()

    bindings.update(
        connect=_connect, read_state=_read_state, freeze=_freeze_read,
        RAW=history_root, load_json=load_json, digest=digest,
    )
    # FunctionType creates per-call globals. Concurrent requests cannot modify
    # the original service or each other's database bindings.
    return FunctionType(service.dashboard.__code__, bindings,
                        name="readonly_dashboard", argdefs=service.dashboard.__defaults__)


def dashboard(active: Path = service.ACTIVE, *, history_root: Path = service.RAW,
              cache_root: Path | None = None) -> dict:
    """Render the original dashboard without creating or modifying its ledger."""
    active = Path(active)
    present = _presentation(history_root=history_root, cache_root=cache_root)
    if not (active / "ledger.sqlite").is_file():
        # Use an empty in-memory read-only state for the original presentation.
        # There is no on-disk connection and no frozen receipt to inspect.
        bindings = dict(present.__globals__)
        bindings["read_state"] = lambda _active: None
        empty = FunctionType(present.__code__, bindings,
                             name="unstarted_dashboard", argdefs=present.__defaults__)
        result = empty(active)
        result["run"]["status"] = "尚未启动：本地账本不存在"
        return result
    return present(active)


__all__ = ["dashboard"]
