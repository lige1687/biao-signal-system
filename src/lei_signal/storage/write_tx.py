"""写事务登记与锁等待诊断（2026-09-15 agent-ask-stability；S2/S3 补修版）。

背景：聊天首问曾在 ``BEGIN IMMEDIATE`` 等待数据库写锁 30 秒后失败
（「database is locked」）。既有日志只定位了**等待方**，无法回答
「当时是谁在持锁、持了多久、事务里是不是在做网络/耗时计算」。

设计原则（主控复验 S2/S3 后重写）：

- **事务语义完全交给原生连接**：提交/回滚/异常传播/上下文管理器一律走
  ``sqlite3`` 原生实现，本层只在每个语句/边界之后按**真实事务状态**
  （``Connection.in_transaction``）同步登记，不自行重新定义提交失败时
  该怎么办（S2：自行改写 ``__exit__`` 曾在延迟外键提交失败时漏掉原生
  回滚，导致事务残留占锁）。
- **区分「等待 / 事务开启 / 已取得写锁」三种状态**（S3）：
    * ``BEGIN IMMEDIATE`` 成功返回才算取得写锁，持锁时间从返回时起算；
    * 隐式事务以**首个成功的写语句**为取得写锁的近似时点；
    * 仅 ``BEGIN``（deferred）未写入 = 事务开着但**不是持锁者**；
    * 执行失败的写语句（如等锁超时的 INSERT）**不登记**——等待方不是
      持锁者；等待时长只在日志里记为等待，绝不计入持锁时长；
    * 无法证明的状态标 ``unknown_open``（事务/锁状态未知），不写死成
      持锁者。
- **覆盖全部写入口**：``Connection.execute/executemany/executescript``
  与 ``cursor().execute/...``（S3 反例：cursor 写入此前完全不可见）。
- **快照区分数据库**：每条登记带库文件路径，锁失败日志只列同库持锁者，
  其他库的事务不被当成本次锁冲突的原因。
- **诚实边界**：快照只是本进程、已覆盖入口的视图——空列表**不能**证明
  持锁者在其他进程（也可能来自本层未知的路径），日志如实这样写。

红线：不记录 SQL 参数、密钥、用户隐私内容——日志只有位置与耗时。
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
    "TrackedCursor",
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


#: 慢等待阈值（BEGIN IMMEDIATE 拿到锁之前的排队耗时；这是可证明的等待）
SLOW_WAIT_MS = _env_int("LEI_DB_SLOW_WAIT_MS", 1500)
#: 慢持有阈值（取得写锁到事务结束的时长）
SLOW_HOLD_MS = _env_int("LEI_DB_SLOW_HOLD_MS", 3000)


def set_thresholds_for_tests(*, wait_ms: int | None = None,
                             hold_ms: int | None = None) -> None:
    """测试用：调整阈值后立即生效（不改环境变量）。"""
    global SLOW_WAIT_MS, SLOW_HOLD_MS
    if wait_ms is not None:
        SLOW_WAIT_MS = wait_ms
    if hold_ms is not None:
        SLOW_HOLD_MS = hold_ms


#: 登记状态：write_lock=已取得写锁（BEGIN IMMEDIATE 成功或已有成功写入）；
#: tx_open_no_write=事务开着但尚未写入（deferred BEGIN，不是持锁者）；
#: unknown_open=事务开着但本层无法证明其写锁状态（如脚本/未分类语句开启）。
STATE_WRITE_LOCK = "write_lock"
STATE_TX_OPEN_NO_WRITE = "tx_open_no_write"
STATE_UNKNOWN_OPEN = "unknown_open"


@dataclass
class _ActiveWrite:
    site: str
    thread: str
    since: float          # 取得写锁（或事务开启）的近似时点
    state: str            # STATE_*
    db: str | None        # 库文件路径（快照按库区分）


_registry: dict[int, _ActiveWrite] = {}
_registry_guard = threading.Lock()
_REGISTRY_CAP = 8  # 每类最多列出的条数（防日志爆炸）


def _register(conn: sqlite3.Connection, site: str, state: str,
              since: float) -> None:
    db = getattr(conn, "_lei_tracked_db", None)
    with _registry_guard:
        _registry[id(conn)] = _ActiveWrite(
            site=site, thread=threading.current_thread().name,
            since=since, state=state, db=db,
        )


def _unregister(conn: sqlite3.Connection, how: str) -> None:
    with _registry_guard:
        active = _registry.pop(id(conn), None)
    if active is None:
        return
    held_ms = int((time.perf_counter() - active.since) * 1000)
    if held_ms >= SLOW_HOLD_MS:
        # 只有 write_lock 的持有才是可证明的持锁时长；其余如实标注状态
        logger.info(
            "db_write_tx slow_hold site=%s thread=%s state=%s db=%s "
            "held_ms=%d end=%s",
            active.site, active.thread, active.state, active.db or "-",
            held_ms, how,
        )


def active_writers_snapshot(db: str | None = None) -> list[dict]:
    """当前进程内活跃写事务/开启事务快照。

    每条含 ``state``（write_lock / tx_open_no_write / unknown_open）与
    ``db``（库路径）。``db`` 给出时只返回该库的条目（路径未知的条目
    除外标注保留——它们可能属于本库也可能不属于，如实呈现）。

    诚实边界：仅本进程、已覆盖入口的视图；空列表不能证明持锁者在
    其他进程（也可能来自本层未知的路径）。"""
    now = time.perf_counter()
    with _registry_guard:
        rows = []
        for a in _registry.values():
            if db is not None and a.db is not None and a.db != db:
                continue
            rows.append({
                "site": a.site,
                "thread": a.thread,
                "state": a.state,
                "db": a.db,
                "held_ms": int((now - a.since) * 1000),
            })
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
    """粗分类：begin_immediate / begin / write / commit / rollback / read。"""
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
    if kw in ("COMMIT", "END"):
        return "commit"
    if kw == "ROLLBACK":
        return "rollback"
    return "read"


class TrackedCursor(sqlite3.Cursor):
    """把 cursor 写入口接回所属连接的跟踪（S3：cursor 写入此前不可见）。"""

    def execute(self, sql, parameters=(), /):  # noqa: ANN001, ANN202
        conn = self.connection
        if isinstance(conn, TrackedConnection):
            return conn._tracked_exec(super().execute, sql, (parameters,))
        return super().execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters, /):  # noqa: ANN001, ANN202
        conn = self.connection
        if isinstance(conn, TrackedConnection):
            return conn._tracked_exec(super().executemany, sql, (seq_of_parameters,))
        return super().executemany(sql, seq_of_parameters)

    def executescript(self, sql_script, /):  # noqa: ANN001, ANN202
        conn = self.connection
        if isinstance(conn, TrackedConnection):
            return conn._tracked_script(super().executescript, sql_script)
        return super().executescript(sql_script)


class TrackedConnection(sqlite3.Connection):
    """按真实事务状态同步登记的连接子类。

    事务语义（提交/回滚/异常/with 块）完全交给原生实现；本层只做：
    语句级测量（BEGIN IMMEDIATE 等待）+ 边界后按 ``in_transaction``
    同步登记 + 三处日志（锁失败指认同库持锁者、慢等待、慢持有）。"""

    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        # sqlite3.connect 的第一个位置参数即库路径（uri 字符串原样保留）
        if not getattr(self, "_lei_tracked_db", None):
            self._lei_tracked_db = str(args[0]) if args else None

    # -- 登记同步（唯一事实来源是 in_transaction） -------------------
    def _sync_tx(self, site: str, *, wrote: bool = False,
                 since: float | None = None, how: str = "sync") -> None:
        """按真实事务状态同步登记。

        ``wrote=True`` 表示刚有写语句成功：事务从「开着未写」升级为
        「已取得写锁」，持锁计时从语句成功返回开始（``since``）；
        语句执行期间无法拆分等待与计算，不计入已确认的持锁时长。"""
        if self.in_transaction:
            with _registry_guard:
                cur = _registry.get(id(self))
            if cur is None:
                _register(
                    self, site,
                    STATE_WRITE_LOCK if wrote else STATE_UNKNOWN_OPEN,
                    since if since is not None else time.perf_counter())
            elif wrote and cur.state != STATE_WRITE_LOCK:
                _register(self, cur.site, STATE_WRITE_LOCK,
                          since if since is not None else time.perf_counter())
        else:
            _unregister(self, how)

    def _db_of(self) -> str | None:
        return getattr(self, "_lei_tracked_db", None)

    # -- 语句执行跟踪 ------------------------------------------------
    def _tracked_exec(self, call, sql: str, args=()):  # noqa: ANN001, ANN202
        kind = _classify(sql if isinstance(sql, str) else "")
        site = _caller_site()
        if kind == "begin_immediate":
            started = time.perf_counter()
            try:
                cur = call(sql, *args)
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower():
                    wait_ms = int((time.perf_counter() - started) * 1000)
                    db = self._db_of()
                    snap = active_writers_snapshot(db=db)
                    logger.warning(
                        "db_write_tx lock_failed site=%s thread=%s db=%s "
                        "wait_ms=%d holders_same_db=%s note=%s",
                        site, threading.current_thread().name, db or "-",
                        wait_ms,
                        [w for w in snap if w["state"] == STATE_WRITE_LOCK],
                        "仅进程内已覆盖入口视图；空列表不证明持锁者在其他进程",
                    )
                raise
            wait_ms = int((time.perf_counter() - started) * 1000)
            # 成功返回=已取得写锁，持锁从此时起算（S3：等待不计入持有）
            self._sync_tx(site, wrote=True, since=time.perf_counter(),
                          how="begin_immediate")
            if wait_ms >= SLOW_WAIT_MS:
                logger.info(
                    "db_write_tx slow_wait site=%s thread=%s db=%s wait_ms=%d "
                    "holders_same_db=%s",
                    site, threading.current_thread().name, self._db_of() or "-",
                    wait_ms,
                    [w for w in active_writers_snapshot(db=self._db_of())
                     if w["state"] == STATE_WRITE_LOCK],
                )
            return cur
        if kind == "begin":
            cur = call(sql, *args)
            # deferred BEGIN：事务开着但尚未写入——不是持锁者（S3）
            if self.in_transaction:
                with _registry_guard:
                    existing = _registry.get(id(self))
                if existing is None:
                    _register(self, site, STATE_TX_OPEN_NO_WRITE,
                              time.perf_counter())
            else:
                _unregister(self, "begin")
            return cur
        if kind == "write":
            started = time.perf_counter()
            cur = call(sql, *args)  # 失败（如等锁超时）不登记——等待方不是持锁者
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self._sync_tx(site, wrote=True, since=time.perf_counter(), how="write")
            if elapsed_ms >= SLOW_WAIT_MS:
                # 单条写语句慢：可能是等锁也可能是语句本身耗时，无法区分，如实写
                logger.info(
                    "db_write_tx slow_write_stmt site=%s thread=%s db=%s "
                    "elapsed_ms=%d note=%s",
                    site, threading.current_thread().name, self._db_of() or "-",
                    elapsed_ms, "可能是锁等待或语句本身耗时，无法区分",
                )
            return cur
        if kind in ("commit", "rollback"):
            # SQL 级 COMMIT/ROLLBACK：提交失败时事务可能仍开着（原生语义），
            # 按真实状态同步，不假设已结束
            try:
                return call(sql, *args)
            finally:
                self._sync_tx(site, how=f"sql_{kind}")
        return call(sql, *args)

    def _tracked_script(self, call, script):  # noqa: ANN001, ANN202
        site = _caller_site()
        try:
            return call(script)
        finally:
            # executescript 可能隐式提交、也可能留下未结束事务——按真实状态
            self._sync_tx(site, how="script")

    # -- 覆写（全部委托原生，事后同步） ------------------------------
    def cursor(self, cursorClass=None, /):  # noqa: ANN001, ANN202
        return super().cursor(cursorClass or TrackedCursor)

    def execute(self, sql, parameters=(), /):  # noqa: ANN001, ANN202
        return self._tracked_exec(super().execute, sql, (parameters,))

    def executemany(self, sql, seq_of_parameters, /):  # noqa: ANN001, ANN202
        return self._tracked_exec(super().executemany, sql, (seq_of_parameters,))

    def executescript(self, sql_script, /):  # noqa: ANN001, ANN202
        return self._tracked_script(super().executescript, sql_script)

    def commit(self) -> None:
        try:
            super().commit()
        finally:
            self._sync_tx(_caller_site(), how="commit")

    def rollback(self) -> None:
        try:
            super().rollback()
        finally:
            self._sync_tx(_caller_site(), how="rollback")

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: ANN001, ANN202
        # 事务语义完全交给原生 __exit__（含提交失败时的原生回滚处理，S2）；
        # 本层只按结果同步登记。
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            try:
                self._sync_tx(
                    _caller_site(),
                    how="with_exit" if exc_type is None else "with_exit_exc")
            except sqlite3.Error:
                pass  # 同步失败不掩盖原生异常

    def close(self) -> None:
        try:
            super().close()
        finally:
            # 关闭即终结（未提交事务由 sqlite 回滚）；登记不得残留
            _unregister(self, "close")
