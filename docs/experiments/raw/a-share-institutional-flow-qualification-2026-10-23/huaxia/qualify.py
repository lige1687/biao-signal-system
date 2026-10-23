"""Qualify 000001 official 2024 semiannual and annual PDF originals.

This only collects and checks source data. It does not calculate returns.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import requests
from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE.parent / "storage-plan.json").read_text())
OUT = Path(PLAN["output"]) / "huaxia"
SOURCES = {
    "2024H1": {
        "page": "https://www.chinaamc.com/c/2024-08-30/682062.shtml",
        "pdf": "https://www.chinaamc.com/front/ui/contentcore/resource/download?ID=162234",
        "announcement_date": "2024-08-30",
        "period_end": "2024-06-30",
    },
    "2024FY": {
        "page": "https://www.chinaamc.com/c/2025-03-31/10000442391.shtml",
        "pdf": "https://www.chinaamc.com/front/ui/contentcore/resource/download?ID=10000440781",
        "announcement_date": "2025-03-31",
        "period_end": "2024-12-31",
    },
}


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def check_storage():
    mount = Path(PLAN["external_mount"])
    if not mount.is_dir() or mount.stat().st_dev != PLAN["external_device"]:
        raise RuntimeError("planned external device is unavailable")
    stat = os.statvfs(mount)
    free = stat.f_bavail * stat.f_frsize
    if free < PLAN["external_reserve_bytes"] + 20 * 1024 * 1024:
        raise RuntimeError("external reserve would be breached")
    OUT.mkdir(parents=True, exist_ok=False)
    if OUT.stat().st_dev != PLAN["external_device"]:
        raise RuntimeError("output is not on planned device")


def collect():
    check_storage()
    ledger = []
    for period, src in SOURCES.items():
        destination = OUT / f"000001-{period}-chinaamc.pdf"
        record = {"period": period, "url": src["pdf"], "at": now()}
        ledger.append(record)
        try:
            digest = hashlib.sha256()
            size = 0
            with requests.get(src["pdf"], timeout=30, stream=True) as response:
                record.update(status=response.status_code,
                              final_url=response.url,
                              content_type=response.headers.get("content-type"))
                response.raise_for_status()
                with destination.open("xb") as output:
                    for chunk in response.iter_content(65536):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > 10 * 1024 * 1024:
                            raise RuntimeError("PDF exceeds 10 MiB source cap")
                        digest.update(chunk)
                        output.write(chunk)
            record.update(bytes=size, sha256=digest.hexdigest(),
                          pdf_header=destination.open("rb").read(5) == b"%PDF-")
            if not record["pdf_header"]:
                raise RuntimeError("not a PDF")
            record["pages"] = len(PdfReader(str(destination)).pages)
            record["saved_path"] = str(destination)
        except Exception as exc:
            record.update(error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            (HERE / "source-request-ledger.json").write_text(
                json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    collect()
