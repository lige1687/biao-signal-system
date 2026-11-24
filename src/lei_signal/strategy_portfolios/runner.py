"""Single local daily collector; no notifications or OS startup installation."""

from __future__ import annotations

import argparse
import fcntl
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from lei_signal.research.output_storage import plan_output

from .collector import collect
from .ledger import sessions
from .service import ACTIVE, ROOT, connect, ingest, load_json, utcnow


def tick(active=ACTIVE):
    local = datetime.now(ZoneInfo("America/New_York"))
    day = local.date().isoformat()
    if (
        day not in set(sessions("US", local.year)) | set(sessions("CN", local.year))
        or local.hour < 17
    ):
        return
    attempt = 1
    recover_locator = None
    with connect(active) as conn:
        old = conn.execute("SELECT at,status,detail FROM runs WHERE date=?", (day,)).fetchone()
        if old:
            info = json.loads(old[2]) if old[2] and old[2].startswith("{") else {}
            attempt = info.get("attempt", 1)
            prior_locator = Path(active) / f"source-{day}-{attempt}.json"
            if old[1] == "completed" or info.get("stop_until_next_session"):
                return
            if old[1] == "running" and prior_locator.exists():
                recover_locator = prior_locator
            else:
                if attempt >= 2:
                    return
                if old[1] == "failed" and datetime.now(ZoneInfo("UTC")) < (
                    datetime.fromisoformat(old[0]) + timedelta(minutes=30)
                ):
                    return
                attempt += 1
        conn.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?)",
            (day, utcnow(), "running", json.dumps({"attempt": attempt})),
        )
    try:
        if recover_locator:
            locator_path = recover_locator
        else:
            plan = plan_output(
                ROOT,
                "factor-strategy-portfolios-daily",
                400 * 1024 * 1024,
                internal_bytes=2 * 1024 * 1024,
            )
            plan_path = Path(active) / f"storage-plan-{day}-{attempt}.json"
            with plan_path.open("x") as file:
                json.dump(plan, file, ensure_ascii=False, indent=2)
            locator_path = Path(active) / f"source-{day}-{attempt}.json"
            collect(plan_path=plan_path, locator_path=locator_path, compress=True)
        locator = load_json(locator_path)
        if locator.get("stopped"):
            raise ValueError("采集主动停止：" + locator["stopped"])
        state = ingest(locator_path, active)
        missing = [m for m, value in state["markets"].items() if value["status"] == "等待最新资料"]
        if missing:
            raise ValueError("本批最新收盘覆盖不足：" + ", ".join(missing))
        status, detail = "completed", {"attempt": attempt, "message": "已采集并按冻结规则记账"}
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        status, detail = (
            "failed",
            {
                "attempt": attempt,
                "message": message,
                "stop_until_next_session": any(
                    token in message for token in ("http_429", "three_consecutive", "覆盖不足")
                ),
            },
        )
    with connect(active) as conn:
        conn.execute(
            "UPDATE runs SET at=?,status=?,detail=? WHERE date=?",
            (utcnow(), status, json.dumps(detail, ensure_ascii=False), day),
        )


def watch(active=ACTIVE):
    Path(active).mkdir(parents=True, exist_ok=True)
    with (Path(active) / "worker.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = {"pid": __import__("os").getpid()}

        def pulse():
            while True:
                payload = dict(status, heartbeat_at=utcnow())
                temporary = Path(active) / "worker-status.tmp"
                temporary.write_text(json.dumps(payload))
                temporary.replace(Path(active) / "worker-status.json")
                time.sleep(30)

        threading.Thread(target=pulse, daemon=True).start()
        while True:
            try:
                tick(active)
                status.pop("error", None)
            except Exception as exc:
                status["error"] = str(exc)
            time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest", type=Path)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    if args.ingest:
        result = ingest(args.ingest)
        print(
            json.dumps(
                {
                    "started_at": result["started_at"],
                    "markets": {
                        m: {"status": v["status"], "qualified": v["qualified_count"]}
                        for m, v in result["markets"].items()
                    },
                },
                ensure_ascii=False,
            )
        )
    elif args.watch:
        watch()
