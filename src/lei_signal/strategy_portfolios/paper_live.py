"""Separately frozen US quote-paper cohort; one shared, unchanged daily collector."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import signal
import sqlite3
import tempfile
import threading
from contextlib import contextmanager, nullcontext
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import ledger, runner, service

ROOT = service.ROOT
ACTIVE = ROOT / "data/strategy-paper-live"
CONFIG = ROOT / "configs/strategy-paper-live.v1.json"
SCHEMES = ("m", "mv", "v", "equal")


def binding():
    return dict(
        service.binding(),
        **{
            str(CONFIG.relative_to(ROOT)): service.digest(CONFIG),
            str(Path(__file__).relative_to(ROOT)): service.digest(__file__),
        },
    )


def _now(at=None):
    value = at or service.utcnow()
    if datetime.fromisoformat(value).tzinfo is None:
        raise ValueError("时间必须包含时区")
    return value


@contextmanager
def _readonly(active):
    path = Path(active) / "ledger.sqlite"
    if not path.is_file():
        yield None
        return
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


def _frozen(conn):
    row = conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()
    if not row:
        raise ValueError("账户尚未冻结")
    return json.loads(row[0])


def _verified(active, legacy=False):
    with _readonly(active) as conn:
        if conn is None:
            raise ValueError("账户尚未冻结")
        frozen = _frozen(conn)
    if frozen["bindings"] != (service.binding() if legacy else binding()):
        raise ValueError("冻结代码或规则变化，暂停新增记账")
    return frozen


def freeze(active=ACTIVE, at=None):
    config = service.load_json(CONFIG)
    if set(config["schemes"]) != set(SCHEMES) or config.get("markets") != ["US"]:
        raise ValueError("新账户仅允许美股四个冻结方案")
    with service.connect(active) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()
        if row:
            frozen = json.loads(row[0])
            if frozen["bindings"] != binding():
                raise ValueError("冻结代码或规则变化，需新版本")
            return frozen
        frozen = {"bindings": binding(), "state": ledger.initialize(config, _now(at))}
        conn.execute("INSERT INTO frozen VALUES (1,?)", (json.dumps(frozen),))
    return frozen


def ingest(locator_path, active=ACTIVE, at=None):
    now = _now(at)
    frozen = _verified(active)
    if datetime.fromisoformat(now) < datetime.fromisoformat(frozen["state"]["started_at"]):
        raise ValueError("不能回溯记账")
    locator = service.load_json(locator_path)
    source = Path(locator["snapshot"])
    if service.digest(source) != locator["snapshot_sha256"]:
        raise ValueError("采集原件指纹不一致")
    snapshot = service.load_json(source)
    if datetime.fromisoformat(_now(snapshot["received_at"])) > datetime.fromisoformat(now):
        raise ValueError("未来接收时间")
    with service.connect(active) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if _frozen(conn)["bindings"] != binding():
            raise ValueError("冻结代码或规则变化")
        previous = conn.execute("SELECT payload FROM events ORDER BY id DESC LIMIT 1").fetchone()
        state = json.loads(previous[0]) if previous else frozen["state"]
        if conn.execute(
            "SELECT 1 FROM events WHERE source_hash=?", (locator["snapshot_sha256"],)
        ).fetchone():
            return state
        state = ledger.advance(state, "US", snapshot["markets"].get("US", {}), now)
        conn.execute(
            "INSERT INTO events(at,source_hash,source_path,payload) VALUES (?,?,?,?)",
            (
                now,
                locator["snapshot_sha256"],
                str(source.resolve()),
                json.dumps(state, ensure_ascii=False, allow_nan=False),
            ),
        )
    return state


def _relative(series, equal):
    left, right = (
        {
            p["date"]: p["nav"]
            for p in rows
            if isinstance(p.get("nav"), (int, float))
            and math.isfinite(p["nav"])
            and p["nav"] > 0
            and p.get("unknown_weight", 0) == 0
        }
        for rows in (series, equal)
    )
    days = sorted(left.keys() & right.keys())
    result = {
        "cumulative_difference_pp": None,
        "relative_wealth_return": None,
        "matched_dates": len(days),
    }
    if days:
        last = days[-1]
        # Frozen initial capital is identical; compare NAV on the same valuation date.
        a, b = left[last], right[last]
        result.update(cumulative_difference_pp=(a - b) * 100, relative_wealth_return=a / b - 1)
    return result


def dashboard(active=ACTIVE):
    now = service.utcnow()
    frozen = state = event = None
    error = None
    with _readonly(active) as conn:
        if conn is not None:
            frozen = _frozen(conn)
            event = conn.execute(
                "SELECT at,source_path,source_hash,payload FROM events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            state = json.loads(event[3]) if event else frozen["state"]
    config = state["config"] if state else service.load_json(CONFIG)
    try:
        expected = ledger.expected_close("US", now)
        next_run = service.next_collection(now)
        if next_run is None:
            raise ValueError("交易日历到期，需核实新年度日历")
    except ValueError as exc:
        expected, next_run, error = None, None, str(exc)
    run = {
        "status": "已冻结，采集进程尚未启动" if state else "等待冻结",
        "last_run_at": event[0] if event else None,
        "next_run_at": next_run,
        "error": error,
        "heartbeat_age_seconds": None,
        "source_path": event[1] if event else None,
        "source_hash": event[2] if event else None,
    }
    try:
        hb = service.load_json(Path(active) / "worker-status.json")
        age = (
            datetime.fromisoformat(now) - datetime.fromisoformat(hb["heartbeat_at"])
        ).total_seconds()
        run.update(
            heartbeat_age_seconds=age,
            pid=hb.get("pid"),
            status=hb.get("status", "运行中") if age < 180 else "采集进程心跳过期",
        )
        run["error"] = hb.get("error") or run["error"]
    except FileNotFoundError:
        pass
    except (ValueError, KeyError) as exc:
        run["error"] = f"进程状态无法读取：{exc}"
    if frozen and frozen["bindings"] != binding():
        run["error"] = "冻结代码或规则变化，暂停新增记账"
    ms = state["markets"].get("US", {}) if state else {}
    accounts = ms.get("accounts", {})
    market = {
        "id": "US",
        "source_date": ms.get("source_date"),
        "expected_date": expected,
        "qualified_count": ms.get("qualified_count", 0),
        "universe_count": len(ms.get("universe", [])) or 504,
        "status": ms.get("status", "等待资料"),
        "reason": ms.get("reason"),
        "last_date": ms.get("last_date"),
        "errors": ms.get("errors", {}),
    }
    recorded = {p["date"] for a in accounts.values() for p in a.get("series", [])}
    gaps = []
    if state and expected:
        start = datetime.fromisoformat(state["started_at"]).astimezone(ZoneInfo("America/New_York"))
        for year in range(start.year, int(expected[:4]) + 1):
            for day in ledger.sessions("US", year):
                hour = 13 if day in {"2026-11-27", "2026-12-24"} else 16
                close = datetime.fromisoformat(f"{day}T{hour}:00:00").replace(tzinfo=start.tzinfo)
                if close > start and day <= expected and day not in recorded:
                    gaps.append(day)
    market["missing_sessions"] = gaps
    result_accounts = []
    for scheme in SCHEMES:
        a = accounts.get(scheme, {})
        series = a.get("series", [])
        orders = a.get("orders", [])
        result_accounts.append(
            {
                "id": "US:" + scheme,
                "scheme": scheme,
                "name": config["schemes"][scheme],
                "role": "candidate"
                if scheme == "m"
                else "comparison"
                if scheme == "mv"
                else "control",
                "cash": a.get("cash", config["initial_cash"]),
                "holdings": list(a.get("holdings", {}).values()),
                "targets": a.get("targets", []),
                "orders": orders,
                "series": series,
                "summary": ledger.summary(series, config["initial_cash"], a.get("cost", 0)),
                "next_execution_dates": sorted(
                    {o["execute_date"] for o in orders if o["status"] == "等待"}
                ),
                "relative_to_equal": _relative(series, accounts.get("equal", {}).get("series", [])),
            }
        )
    return {
        "version": config["version"],
        "started_at": state["started_at"] if state else None,
        "generated_at": now,
        "run": run,
        "market": market,
        "accounts": result_accounts,
        "benchmark": {"name": "同池合格股票均分", "kind": "same_universe_control"},
        "parent_index": {
            "name": "S&P 500",
            "status": "not_evaluated",
            "reason": "未接入同口径母指数全收益",
        },
        "pending": [
            {"name": "A股动量＋经营现金流", "reason": "缺合格的当前逐股财务字段，尚未启动"},
            {"name": "美股经营盈利＋低资产扩张", "reason": "缺合格的当前逐股财务字段，尚未启动"},
            {"name": "账面市值比＋经营盈利", "reason": "证据不足，未晋升候选"},
        ],
        "limitations": [
            "报价研究单位可含小数，不是真实股数或券商成交。",
            "费用是统一假设，未证明开盘可成交。",
            "股票池固定为2026-10-13 IVV持仓，不是动态标普500。",
            "短样本尚不能证明有效；不足365日不年化。",
            "旧账户10月22日之后存在停采空档，新账户从实际冻结起记录，不补成绩。",
            "当前四方案未使用财务因子，财务组合仍待资料。",
        ],
    }


@contextmanager
def _lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"采集锁已占用：{path.name}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def tick(active=ACTIVE, legacy_active=service.ACTIVE, *, _legacy_lock_held=False):
    frozen = _verified(active)
    _verified(legacy_active, legacy=True)
    # Do not let even a read of the scheduler collect outside a qualified calendar.
    now = service.utcnow()
    ledger.expected_close("US", now)
    if service.next_collection(now) is None:
        raise ValueError("交易日历到期，暂停采集")
    lock = nullcontext() if _legacy_lock_held else _lock(Path(legacy_active) / "worker.lock")
    with lock:
        _verified(active)
        _verified(legacy_active, legacy=True)
        runner.tick(legacy_active)
        day = (
            datetime.fromisoformat(now).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        )
        with _readonly(legacy_active) as conn:
            row = conn.execute("SELECT at,status,detail FROM runs WHERE date=?", (day,)).fetchone()
        if not row:
            return {"status": "等待下一次采集"}
        detail = json.loads(row[2]) if row[2] else {}
        if datetime.fromisoformat(row[0]) < datetime.fromisoformat(frozen["state"]["started_at"]):
            return {"status": "等待冻结后的新采集"}
        path = Path(legacy_active) / f"source-{day}-{detail.get('attempt', 1)}.json"
        ingested = False
        if path.is_file():
            locator = service.load_json(path)
            snapshot = service.load_json(locator["snapshot"])
            received = datetime.fromisoformat(snapshot["received_at"])
            expected = ledger.expected_close("US", now)
            bars = snapshot.get("markets", {}).get("US", {}).get("bars", [])
            if (
                received >= datetime.fromisoformat(frozen["state"]["started_at"])
                and max((r["date"] for r in bars), default=None) == expected
            ):
                ingest(path, active)
                ingested = True
        if row[1] == "failed":
            raise RuntimeError(detail.get("message", "共享采集失败"))
        return {
            "status": "运行中，按日等待新收盘",
            "successful_collection": row[1] == "completed" and ingested,
        }


def _heartbeat(active, status):
    with tempfile.NamedTemporaryFile(
        mode="w", dir=active, prefix="worker-status-", suffix=".tmp", delete=False
    ) as handle:
        json.dump(dict(status, heartbeat_at=service.utcnow()), handle, ensure_ascii=False)
        temporary = Path(handle.name)
    temporary.replace(Path(active) / "worker-status.json")


def watch(active=ACTIVE, legacy_active=service.ACTIVE):
    _verified(active)
    _verified(legacy_active, legacy=True)
    status = {
        "pid": os.getpid(),
        "status": "启动中",
        "error": None,
        "managed_by": "strategy-paper-live",
    }

    def heartbeat():
        _heartbeat(active, status)
        _heartbeat(legacy_active, status)

    stop = threading.Event()

    def shutdown(signum, frame):
        status.update(status="已停止", error=f"进程收到退出信号 {signum}")
        heartbeat()
        stop.set()

    with _lock(Path(active) / "paper-live.lock"), _lock(Path(legacy_active) / "worker.lock"):
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)

        def pulse():
            while not stop.is_set():
                heartbeat()
                stop.wait(30)

        thread = threading.Thread(target=pulse, daemon=True)
        thread.start()
        try:
            while not stop.is_set():
                try:
                    outcome = tick(active, legacy_active, _legacy_lock_held=True)
                    status.update(outcome)
                    if outcome.get("successful_collection"):
                        status["error"] = None
                except Exception as exc:
                    status.update(status="采集异常", error=f"{type(exc).__name__}: {exc}")
                heartbeat()
                stop.wait(60)
        finally:
            stop.set()
            thread.join(timeout=2)
            status["status"] = "已停止"
            status["error"] = status["error"] or "采集进程已退出"
            heartbeat()


app = FastAPI(title="美股前向报价模拟账户")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/strategy-paper-live")
def get_dashboard():
    return dashboard()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--ingest", type=Path)
    group.add_argument("--watch", action="store_true")
    group.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(), ensure_ascii=False))
    elif args.ingest:
        print(json.dumps(ingest(args.ingest), ensure_ascii=False))
    elif args.watch:
        watch()
    else:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=8029)


if __name__ == "__main__":
    main()
