"""One bounded anonymous public source request per invocation; never execute JS."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
URLS = {
    "qfq": "https://finance.sina.com.cn/realstock/company/sh600705/qfq.js",
    "history": "https://finance.sina.com.cn/realstock/company/sh600705/hisdata_klc2/klc_kl.js",
    "qfq-600837": "https://finance.sina.com.cn/realstock/company/sh600837/qfq.js",
    "history-600837": "https://finance.sina.com.cn/realstock/company/sh600837/hisdata_klc2/klc_kl.js",
}
CAP_REQUESTS = 6
CAP_BYTES = 20 * 1024 * 1024


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=URLS)
    kind = p.parse_args().kind
    ledger_path = OUT / "request-ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"schema": "stock-gap-pilot-source-requests/1.0", "attempts": []}
    attempts = ledger["attempts"]
    assert len(attempts) < CAP_REQUESTS
    assert kind not in [a["kind"] for a in attempts], "do not repeat an attempted URL"
    used = sum(a["received_bytes"] for a in attempts)
    assert used < CAP_BYTES
    assert shutil.disk_usage(ROOT).free > 536870912 + CAP_BYTES - used
    attempt = {"kind": kind, "url": URLS[kind], "attempt_number": len(attempts) + 1,
               "requested_at_local": datetime.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
               "anonymous": True, "login_or_cookie_sent_by_script": False,
               "redirect_followed": False, "received_bytes": 0, "body_file": None, "sha256": None}
    try:
        with requests.get(URLS[kind], headers={"User-Agent": "LeiSignal-source-qualification/1.0"},
                          timeout=(8, 20), stream=True, allow_redirects=False) as response:
            attempt["http_status"] = response.status_code
            attempt["safe_headers"] = {k: response.headers[k] for k in ("Content-Type", "Content-Length", "Date", "ETag", "Last-Modified") if k in response.headers}
            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                body.extend(chunk)
                if used + len(body) > CAP_BYTES:
                    raise RuntimeError("20MiB cumulative response cap reached")
            attempt["received_bytes"] = len(body)
            if body:
                symbol = "sh600837" if kind.endswith("-600837") else "sh600705"
                endpoint = kind.split("-")[0]
                file_name = f"sina-{endpoint}-{symbol}-response.bin"
                target = OUT / file_name
                assert not target.exists()
                target.write_bytes(body)
                attempt["body_file"] = file_name
                attempt["sha256"] = hashlib.sha256(body).hexdigest()
            attempt["result"] = "response_saved" if response.status_code == 200 else "http_non_200"
    except Exception as exc:
        attempt["result"] = "request_error"
        attempt["error_type"] = type(exc).__name__
        attempt["error_summary"] = str(exc)[:400]
    attempts.append(attempt)
    ledger["cumulative_requests_attempted"] = len(attempts)
    ledger["cumulative_response_bytes"] = sum(a["received_bytes"] for a in attempts)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"kind": kind, "result": attempt["result"], "status": attempt.get("http_status"),
                      "bytes": attempt["received_bytes"], "sha256": attempt["sha256"],
                      "attempts": ledger["cumulative_requests_attempted"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
