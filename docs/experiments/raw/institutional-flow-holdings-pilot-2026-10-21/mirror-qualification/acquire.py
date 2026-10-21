"""Bounded public N-PORT mirror acquisition; raw tables only, no economic analysis."""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / "delegate-contract.json").read_text())
MOUNT = Path(CONTRACT["storage_guard"]["mount"])
EXTERNAL = Path(CONTRACT["write_paths"][1])
MANIFEST = HERE / "request-manifest.json"
REV = CONTRACT["data_revision"]
HOSTS = {"huggingface.co", "cdn-lfs.hf.co", "cas-bridge.xethub.hf.co", "cas-server.xethub.hf.co"}


def guard():
    device = CONTRACT["storage_guard"]["device"]
    if not MOUNT.is_dir() or MOUNT.stat().st_dev != device:
        raise RuntimeError("fixed external mount unavailable or device changed")
    if not EXTERNAL.parent.is_dir() or EXTERNAL.parent.stat().st_dev != device:
        raise RuntimeError("fixed external parent unavailable or device changed")
    if EXTERNAL.exists() and EXTERNAL.stat().st_dev != device:
        raise RuntimeError("result directory device changed")
    if shutil.disk_usage(MOUNT).free < 10 * 1024 ** 3:
        raise RuntimeError("external 10GiB reserve not met")


def save(manifest):
    temp = MANIFEST.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, MANIFEST)


def load():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        "dataset": "trader298/sec-nport", "revision": REV, "year": 2025,
        "files": [], "requests": [], "failures": [], "bytes_completed": 0,
    }


def acquire(table, quarter, manifest):
    relative = f"{table}/year=2025/quarter={quarter}/data.parquet"
    url = f"https://huggingface.co/datasets/trader298/sec-nport/resolve/{REV}/{relative}"
    target = EXTERNAL / relative
    guard()
    if target.exists():
        if target.stat().st_dev != CONTRACT["storage_guard"]["device"]:
            raise RuntimeError("saved file on wrong device")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        known = next((f for f in manifest["files"] if f["relative_path"] == relative), None)
        if known and known["sha256"] == digest and known["bytes"] == target.stat().st_size:
            print("reuse", relative, target.stat().st_size)
            return
        raise RuntimeError(f"existing file lacks matching manifest: {relative}")
    partial = Path(str(target) + ".part")
    if partial.exists():
        raise RuntimeError(f"preserved incomplete file requires manual review: {partial}")
    target.parent.mkdir(parents=True, exist_ok=True)
    guard()
    item = {"url": url, "relative_path": relative, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "started", "http_status": None, "redirect_url": None, "bytes": 0}
    manifest["requests"].append(item)
    save(manifest)
    digest = hashlib.sha256()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LeiSignal-public-research/1.0"})
        with urllib.request.urlopen(req, timeout=90) as response:
            item["http_status"] = response.status
            redirected = urllib.parse.urlsplit(response.url)
            item["redirect_url"] = urllib.parse.urlunsplit((redirected.scheme, redirected.netloc,
                                                               redirected.path, "", ""))
            item["redirect_query_redacted"] = bool(redirected.query)
            final_host = redirected.hostname
            if final_host not in HOSTS and not (final_host and final_host.endswith(".hf.co")):
                raise RuntimeError(f"unexpected redirect host {final_host}")
            length = response.headers.get("Content-Length")
            if length and (manifest["bytes_completed"] + int(length) > CONTRACT["storage_guard"]["max_planned_external_bytes"]):
                raise RuntimeError("planned byte cap would be exceeded")
            with partial.open("wb") as output:
                while True:
                    guard()
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    item["bytes"] += len(chunk)
                    if manifest["bytes_completed"] + item["bytes"] > CONTRACT["storage_guard"]["max_planned_external_bytes"]:
                        raise RuntimeError("planned byte cap exceeded")
                    output.write(chunk)
                    digest.update(chunk)
        if length and item["bytes"] != int(length):
            raise RuntimeError("incomplete HTTP body")
        guard()
        os.replace(partial, target)
        item["status"] = "completed"
        item["sha256"] = digest.hexdigest()
        item["ended_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        manifest["files"].append({"relative_path": relative, "source_url": url,
                                  "final_url_host": urllib.parse.urlsplit(item["redirect_url"]).hostname,
                                  "path": str(target), "bytes": item["bytes"], "sha256": digest.hexdigest(),
                                  "retrieved_at": item["ended_at"]})
        manifest["bytes_completed"] += item["bytes"]
        save(manifest)
        print("completed", relative, item["bytes"], digest.hexdigest())
    except Exception as error:
        item["status"] = "failed"
        item["error"] = f"{type(error).__name__}: {error}"
        item["ended_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        item["partial_path"] = str(partial) if partial.exists() else None
        manifest["failures"].append(dict(item))
        save(manifest)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["metadata", "large"])
    args = parser.parse_args()
    guard()
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    manifest = load()
    tables = ("SUBMISSION", "FUND_REPORTED_INFO") if args.stage == "metadata" else (
        "FUND_REPORTED_HOLDING", "MONTHLY_TOTAL_RETURN")
    for table in tables:
        for quarter in CONTRACT["quarters"]:
            acquire(table, quarter, manifest)
