"""Explicit local observation runner. No broker, historical replay, or alerts."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import signal
import time as time_module
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from pathlib import Path

from .collector import SHANGHAI, clock, collect, session_time
from .models import instant
from .reconcile import reconcile
from .service import build_dashboard, initialize, process_observation

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "data/forward-observation/ledger.db"
DEFAULT_CONFIG = ROOT / "configs/forward-observation.v1.json"


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    hashes = config.get("code_hashes") or {}
    if not hashes:
        raise ValueError("code fingerprints must be frozen before starting")
    for relative, expected in hashes.items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT.resolve()):
            raise ValueError("fingerprint path outside repository")
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"已冻结代码发生变化，暂停新增记录：{relative}")
    return config


@contextmanager
def exclusive(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("另一个观察进程正在执行，本次未重复处理") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def save_status(db_path: Path, payload: dict) -> None:
    path = db_path.parent / "runner-status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".runner-status.{os.getpid()}.json")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def observe_once(db_path=DEFAULT_DB, config_path=DEFAULT_CONFIG, now=None) -> dict:
    """Fetch now. An API request timestamp never becomes a simulated clock."""
    db_path, config_path = Path(db_path), Path(config_path)
    with exclusive(db_path.parent / ".cycle.lock"):
        attempt = {
            "started_at": clock().isoformat(),
            "requested_at": now,
            "status": "started",
            "observations_recorded": 0,
        }
        try:
            config = load_config(config_path)
            initialize(db_path, config, clock().isoformat())
            frozen = db_path.parent / "frozen-config.json"
            if frozen.exists():
                if json.loads(frozen.read_text()) != config:
                    raise ValueError("saved frozen configuration differs")
            else:
                with frozen.open("x", encoding="utf-8") as out:
                    out.write(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
            observations = collect(config)
            for observation in observations:
                process_observation(db_path, observation, clock().isoformat())
                attempt["observations_recorded"] += 1
            check = reconcile(db_path)
            check["checked_at"] = clock().isoformat()
            check_path = db_path.parent / "reconciliation.json"
            temporary = check_path.with_name(f".reconciliation.{os.getpid()}.json")
            temporary.write_text(json.dumps(check, ensure_ascii=False, indent=2) + "\n")
            os.replace(temporary, check_path)
            if not check["passed"]:
                raise ValueError("账户独立核对未通过：" + "; ".join(check["reasons"][:3]))
            attempt["status"] = "recorded"
            return build_dashboard(db_path, config, clock().isoformat())
        except Exception as exc:
            attempt.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            attempt["finished_at"] = clock().isoformat()
            # Failures persist separately even if a ledger transaction rolls back.
            with (db_path.parent / "run-attempts.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(attempt, ensure_ascii=False) + "\n")


def next_run(at: datetime) -> datetime:
    """Five-minute daytime checks and one after-close check; no historical catch-up."""
    local = instant(at).astimezone(SHANGHAI)
    if session_time(local):
        candidate = local + timedelta(minutes=5)
        if session_time(candidate):
            return candidate
    if local.weekday() < 5:
        if local.time().replace(tzinfo=None) < time(9, 30):
            return datetime.combine(local.date(), time(9, 30), SHANGHAI)
        if local.time().replace(tzinfo=None) < time(13):
            return datetime.combine(local.date(), time(13), SHANGHAI)
        if local.time().replace(tzinfo=None) < time(16, 35):
            return datetime.combine(local.date(), time(16, 35), SHANGHAI)
    day = local.date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime.combine(day, time(9, 30), SHANGHAI)


def watch(db_path: Path, config_path: Path) -> None:
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with exclusive(db_path.parent / ".watch.lock"):
        started = clock().isoformat()
        due = clock()
        state = {
            "pid": os.getpid(),
            "mode": "watch",
            "started_at": started,
            "status": "starting",
            "last_success_at": None,
            "last_error": None,
            "automatic_restart": False,
            "schedule_note": "交易时段每5分钟；16:35检查收盘资料。休眠漏跑保留缺口，不追溯成交。",
        }
        while not stopping:
            at = clock()
            if at >= due:
                try:
                    observe_once(db_path, config_path)
                    state.update(
                        status="waiting", last_success_at=clock().isoformat(), last_error=None
                    )
                except (
                    Exception
                ) as exc:  # Record source/lock/code errors without inventing observations.
                    state.update(status="error", last_error=f"{type(exc).__name__}: {exc}")
                due = next_run(clock())
            state.update(heartbeat_at=clock().isoformat(), next_run_at=due.isoformat())
            save_status(db_path, state)
            time_module.sleep(min(30, max(1, (due - clock()).total_seconds())))
        state.update(status="stopped", heartbeat_at=clock().isoformat(), next_run_at=None)
        save_status(db_path, state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    if args.watch:
        watch(args.db, args.config)
    elif args.initialize:
        result = initialize(args.db, load_config(args.config), clock().isoformat())
        print(json.dumps(result["run"], ensure_ascii=False))
    else:
        result = observe_once(args.db, args.config)
        print(json.dumps({"run": result["run"], "health": result["health"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
