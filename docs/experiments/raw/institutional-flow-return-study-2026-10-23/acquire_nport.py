"""Acquire explicitly selected immutable public N-PORT partitions; no effects."""
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "storage-plan.json").read_text())
OUT = Path(PLAN["output"]) / "nport"
REV = "d8db5addd8261a422aa2df269b764d746b7ceb54"
MANIFEST = HERE / "nport-acquisition.json"


def guard():
    mount = Path(PLAN["external_mount"])
    if not mount.is_dir() or mount.stat().st_dev != PLAN["external_device"]:
        raise RuntimeError("registered external device unavailable")
    if shutil.disk_usage(mount).free < PLAN["external_reserve_bytes"]:
        raise RuntimeError("external reserve unavailable")


def fetch(key):
    table, year, quarter = key.split(":")
    rel = f"{table}/year={year}/quarter={quarter}/data.parquet"
    target = OUT / rel
    url = f"https://huggingface.co/datasets/trader298/sec-nport/resolve/{REV}/{rel}"
    row = {"relative_path": rel, "path": str(target), "url": url,
           "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    guard()
    if target.exists() or target.with_suffix(".partial").exists():
        raise RuntimeError("preserve existing or partial response: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")
    h = hashlib.sha256()
    n = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LeiSignal-public-research/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response, partial.open("wb") as f:
            row["status"] = response.status
            length = response.headers.get("Content-Length")
            while chunk := response.read(1024 * 1024):
                guard()
                n += len(chunk)
                if n > PLAN["estimated_bytes"]:
                    raise RuntimeError("partition exceeds entire planned storage")
                f.write(chunk)
                h.update(chunk)
        if length and n != int(length):
            raise RuntimeError("truncated response")
        with partial.open("rb") as check:
            magic = check.read(4)
        if magic != b"PAR1":
            raise RuntimeError("response is not parquet")
        os.replace(partial, target)
        row.update(bytes=n, sha256=h.hexdigest(), state="completed")
    except Exception as exc:
        row.update(state="failed", bytes=n, error=str(exc), partial_path=str(partial))
    return row


if __name__ == "__main__":
    guard()
    rows = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    known = {r["relative_path"] for r in rows}
    keys = sys.argv[1:]
    if any(f"{k.split(':')[0]}/year={k.split(':')[1]}/quarter={k.split(':')[2]}/data.parquet" in known for k in keys):
        raise RuntimeError("request already recorded; review rather than retry")
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for row in pool.map(fetch, keys):
            rows.append(row)
            MANIFEST.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({k: row.get(k) for k in ["relative_path", "state", "bytes", "error"]}), flush=True)
    if any(r["state"] != "completed" for r in rows):
        sys.exit(1)
