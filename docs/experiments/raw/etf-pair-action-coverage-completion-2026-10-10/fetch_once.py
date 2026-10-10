"""One synchronous public source request under the frozen six-report contract."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "executor-contract.json").read_text())
LEDGER = ROOT / "request-ledger.json"
MANIFEST = ROOT / "source-manifest.json"
EXTERNAL = Path(CONTRACT["output_plan"]["run_directory"])
ALLOWED = {"www.huatai-pb.com", "api.efunds.com.cn", "cdn.efunds.com.cn", "static.cninfo.com.cn"}


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--operation", required=True)
    ap.add_argument("--method", choices=["GET", "POST"], required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--form", default="{}")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    assert urlparse(args.url).scheme == "https" and urlparse(args.url).hostname in ALLOWED
    assert "/" not in args.name and ".." not in args.name
    form = json.loads(args.form)
    ledger = json.loads(LEDGER.read_text())
    assert len(ledger["requests"]) < CONTRACT["budgets"]["new_public_requests_max"]
    assert sum(r["status"].startswith("failed") for r in ledger["requests"] if r["operation"] == args.operation) < CONTRACT["budgets"]["same_operation_attempts_max"]
    n = len(ledger["requests"]) + 1
    row = {"n": n, "operation": args.operation, "method": args.method, "url": args.url,
           "form": form if args.method == "POST" else None, "status": "pending",
           "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "response_bytes": 0}
    ledger["requests"].append(row)
    ledger["actual_requests"] = n
    save_json(LEDGER, ledger)
    body_path = EXTERNAL / f"{n:02d}-{args.name}"
    header_path = EXTERNAL / f"{n:02d}-{args.name}.headers.json"
    digest = hashlib.sha256()
    size = 0
    try:
        session = requests.Session()
        session.trust_env = False
        with session.request(args.method, args.url, data=form if args.method == "POST" else None,
                              timeout=(10, 30), stream=True, allow_redirects=True) as response:
            headers = {"status_code": response.status_code, "url": response.url,
                       "headers": dict(response.headers), "redirects": [x.url for x in response.history]}
            save_json(header_path, headers)
            with body_path.open("wb") as out:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if ledger["raw_bytes"] + size > CONTRACT["budgets"]["new_raw_response_bytes_max"]:
                        raise RuntimeError("raw byte limit")
                    out.write(chunk)
                    digest.update(chunk)
            row.update({"http_status": response.status_code, "final_url": response.url,
                        "response_path": str(body_path), "headers_path": str(header_path),
                        "response_bytes": size, "sha256": digest.hexdigest(),
                        "status": "success" if response.ok else "failed_http"})
    except Exception as exc:
        row.update({"status": "failed_exception", "error": type(exc).__name__ + ": " + str(exc)[:200],
                    "response_path": str(body_path) if body_path.exists() else None,
                    "headers_path": str(header_path) if header_path.exists() else None,
                    "response_bytes": size, "sha256": digest.hexdigest() if size else None})
    row["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    ledger["raw_bytes"] += size
    save_json(LEDGER, ledger)
    manifest = json.loads(MANIFEST.read_text())
    if size:
        manifest["sources"].append({"n": n, "operation": args.operation, "url": args.url,
                                    "final_url": row.get("final_url"), "status": row["status"],
                                    "path": str(body_path), "bytes": size, "sha256": row.get("sha256"),
                                    "headers_path": str(header_path) if header_path.exists() else None})
        save_json(MANIFEST, manifest)
    print(json.dumps({"n": n, "status": row["status"], "http_status": row.get("http_status"),
                      "bytes": size, "sha256": row.get("sha256"), "path": str(body_path) if size else None,
                      "error": row.get("error")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
