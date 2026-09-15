"""写事务登记与锁等待诊断（2026-09-15 agent-ask-stability）。

背景：聊天首问曾在 ``BEGIN IMMEDIATE`` 等待数据库写锁 30 秒后失败
（「database is locked」）。既有日志只定位了**等待方**，无法回答
「当时是谁在持锁、持了多久、事务里是不是在做网络/耗时计算」。

本模块在 ``sqlite_store.connect`` 层统一接入（factory=TrackedConnection），
对**所有**写事务做进程内登记：

- 记录每个写事务的开启位置（模块:行号 函数）、线程、开启时刻——
  显式 ``BEGIN IMMEDIATE`` 与隐式事务（首个 DML 到 commit/rollback 之间）
  都覆盖；事务开着又去做网络请求/耗时计算的形态会表现为「持有时间」异常长；
- ``BEGIN IMMEDIATE`` 等待超时失败时，日志带出**当时进程内活跃写事务
  快照**（位置/线程/已持续毫秒），直接指认持锁方；
- 等待或持有超过阈值即记日志（不等到失败也有慢事务证据）。

红线：不记录 SQL 参数、密钥、用户隐私内容——日志只有位置与耗时。
跨进程写者（如 launchd 独立脚本）不在本进程注册表内；快照如实标注
「仅进程内视图」。
"""
from __future__ import annotations

import inspect
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass

__all__ = [
    "TrackedConnection",
    "active_writers_snapshot",
    "set_thresholds_for_tests",
    "SLOW_WAIT_MS",
    "SLOW_HOLD_MS",
]

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


#: 慢等待阈值（BEGIN IMMEDIATE 拿到锁之前的排队耗时）
SLOW_WAIT_MS = _env_int("LEI_DB_SLOW_WAIT_MS", 1500)
#: 慢持有阈值（首个写语句到 commit/rollback 的时长）
SLOW_HOLD_MS = _env_int("LEI_DB_SLOW_HOLD_MS", 3000)


def set_thresholds_for_tests(*, wait_ms: int | None = None,
                             hold_ms: int | None = None) -> None:
    """测试用：调整阈值后立即生效（不改环境变量）。"""
    global SLOW_WAIT_MS, SLOW_HOLD_MS
    if wait_ms is not None:
        SLOW_WAIT_MS = wait_ms
    if hold_ms is not None:
        SLOW_HOLD_MS = hold_ms


@dataclass
class _ActiveWrite:
    site: str
    thread: str
    since: float  # perf_counter
    explicit: bool  # True=显式 BEGIN，False=隐式事务（首个 DML 起算）


_registry: dict[int, _ActiveWrite] = {}
_registry_guard = threading.Lock()
_REGISTRY_CAP = 8  # 快照最多列出的活跃写者条数（防日志爆炸）


def _register(conn: sqlite3.Connection, site: str, explicit: bool) -> None:
    with _registry_guard:
        _registry[id(conn)] = _ActiveWrite(
            site=site,
            thread=threading.current_thread().name,
            since=time.perf_counter(),
            explicit=explicit,
        )


def _unregister(conn: sqlite3.Connection) -> _ActiveWrite | None:
    with _registry_guard:
        return _registry.pop(id(conn), None)


def active_writers_snapshot() -> list[dict]:
    """当前进程内活跃写事务快照（位置/线程/已持续毫秒）。

    仅进程内视图：launchd 等独立进程里的写者不在其中。"""
    now = time.perf_counter()
    with _registry_guard:
        rows = [
            {
                "site": a.site,
                "thread": a.thread,
                "held_ms": int((now - a.since) * 1000),
                "explicit": a.explicit,
            }
            for a in _registry.values()
        ]
    rows.sort(key=lambda r: -r["held_ms"])
    return rows[:_REGISTRY_CAP]


def _caller_site() -> str:
    """调用位置（跳过本模块自身的帧）：'模块:行号 函数'。不含 SQL 与参数。"""
    frame = inspect.currentframe()
    try:
        if frame is not None:
            frame = frame.f_back
        while frame is not None:
            mod = frame.f_globals.get("__name__", "")
            if mod != __name__:
                func = frame.f_code.co_name
                short = mod.rsplit(".", 1)[-1]
                return f"{short}:{frame.f_lineno} {func}"
            frame = frame.f_back
    finally:
        del frame
    return "unknown"


def _classify(sql: str) -> str:
    """粗分类：begin_immediate / begin / write / read。只看首个关键字。"""
    head = sql.lstrip().split(None, 1)
    if not head:
        return "read"
    kw = head[0].upper()
    if kw == "BEGIN":
        rest = head[1].upper() if len(head) > 1 else ""
        return "begin_immediate" if "IMMEDIATE" in rest else "begin"
    if kw in ("INSERT", "UPDATE", "DELETE", "REPLACE",
              "CREATE", "ALTER", "DROP", "VACUUM", "REINDEX"):
        return "write"
    return "read"


class TrackedConnection(sqlite3.Connection):
    """在 execute/commit/rollback 上登记写事务的连接子类。

    行为与 ``sqlite3.Connection`` 完全一致（返回值、异常类型不变），
    只多做：登记/注销 + 慢等待/慢持有/锁失败三处日志。"""

    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self._tx_open = False

    # -- 写事务边界 -------------------------------------------------
    def _mark_open(self, site: str, explicit: bool) -> None:
        if not self._tx_open:
            self._tx_open = True
            _register(self, site, explicit)

    def _mark_closed(self, how: str) -> None:
        if not self._tx_open:
            return
        self._tx_open = False
        active = _unregister(self)
        if active is not None:
            held_ms = int((time.perf_counter() - active.since) * 1000)
            if held_ms >= SLOW_HOLD_MS:
                logger.info(
                    "db_write_tx slow_hold site=%s thread=%s held_ms=%d end=%s",
                    active.site, active.thread, held_ms, how,
                )

    def _execute_tracked(self, sql, parameters=()):  # noqa: ANN001, ANN202
        kind = _classify(sql if isinstance(sql, str) else "")
        if kind in ("begin_immediate", "begin"):
            site = _caller_site()
            started = time.perf_counter()
            try:
                cur = super().execute(sql, parameters)
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower():
                    wait_ms = int((time.perf_counter() - started) * 1000)
                    logger.warning(
                        "db_write_tx lock_failed site=%s thread=%s wait_ms=%d "
                        "active_writers_in_process=%s",
                        site, threading.current_thread().name, wait_ms,
                        active_writers_snapshot(),
                    )
                raise
            wait_ms = int((time.perf_counter() - started) * 1000)
            self._mark_open(site, explicit=True)
            if wait_ms >= SLOW_WAIT_MS:
                logger.info(
                    "db_write_tx slow_wait site=%s thread=%s wait_ms=%d "
                    "active_writers_in_process=%s",
                    site, threading.current_thread().name, wait_ms,
                    active_writers_snapshot(),
                )
            return cur
        if kind == "write":
            self._mark_open(_caller_site(), explicit=False)
        return super().execute(sql, parameters)

    # -- 覆写 -------------------------------------------------------
    def execute(self, sql, parameters=(), /):  # noqa: ANN001, ANN202
        return self._execute_tracked(sql, parameters)

    def executemany(self, sql, seq_of_parameters, /):  # noqa: ANN001, ANN202
        kind = _classify(sql if isinstance(sql, str) else "")
        if kind == "write":
            self._mark_open(_caller_site(), explicit=False)
        return super().executemany(sql, seq_of_parameters)

    def executescript(self, sql_script, /):  # noqa: ANN001, ANN202
        # executescript 会先隐式 COMMIT 再整段执行；按一次写事务登记。
        site = _caller_site()
        self._mark_closed("commit_before_script")
        self._mark_open(site, explicit=True)
        try:
            return super().executescript(sql_script)
        finally:
            self._mark_closed("script_end")

    def commit(self) -> None:
        super().commit()
        self._mark_closed("commit")

    def rollback(self) -> None:
        super().rollback()
        self._mark_closed("rollback")

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: ANN001, ANN202
        # C 层 ``with conn:`` 未必走 Python 覆写的 commit/rollback，显式接管。
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False

    def close(self) -> None:
        self._mark_closed("close")
        super().close()
