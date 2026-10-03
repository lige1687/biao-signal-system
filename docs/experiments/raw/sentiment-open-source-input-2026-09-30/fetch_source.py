"""Bounded public download; every initiated request is recorded before network use."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
LEDGER = BASE / "continuation-source-ledger.json"


def fetch(url, filename, max_bytes=300_000_000):
    ledger = json.loads(LEDGER.read_text())
    if len(ledger["operations"]) >= ledger["new_source_operations_budget"]:
        raise RuntimeError("source operation budget exhausted")
    op = {"id": len(ledger["operations"]) + 1, "type": "http_download", "url": url,
          "output": filename, "initiated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "result": "started", "bytes": 0}
    ledger["operations"].append(op)
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    digest = hashlib.sha256()
    try:
        with requests.get(url, stream=True, timeout=(20, 40)) as response:
            op["status"] = response.status_code
            op["content_type"] = response.headers.get("Content-Type")
            size = int(response.headers.get("Content-Length", 0))
            if size > max_bytes:
                raise RuntimeError(f"declared response size {size} exceeds cap {max_bytes}")
            if not response.ok:
                op["result"] = "http_failure"
                op["response_excerpt"] = response.text[:200]
                return op
            destination = BASE / "inputs" / filename
            with destination.open("wb") as output:
                for chunk in response.iter_content(1 << 20):
                    op["bytes"] += len(chunk)
                    if op["bytes"] > max_bytes:
                        raise RuntimeError("stream response exceeds download cap")
                    output.write(chunk)
                    digest.update(chunk)
            op["sha256"] = digest.hexdigest()
            op["result"] = "downloaded"
            return op
    except Exception as error:
        op["result"] = "failed"
        op["error_type"] = type(error).__name__
        op["error"] = str(error).split("https://")[0][:200]
        return op
    finally:
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("filename")
    parser.add_argument("--max-bytes", type=int, default=300_000_000)
    args = parser.parse_args()
    print(json.dumps(fetch(args.url, args.filename, args.max_bytes), ensure_ascii=False))
