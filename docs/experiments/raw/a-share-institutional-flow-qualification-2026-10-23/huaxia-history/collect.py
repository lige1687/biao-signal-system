"""Collect the twelve still-missing official ChinaAMC 000001 reports.

The 2024 originals in ../huaxia/ are reused and never fetched again.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
RAW = HERE.parent
PLAN = json.loads((RAW / "storage-plan.json").read_text())
HISTORY = json.loads((RAW / "huaxia" / "historical-list.json").read_text())
OUT = Path(PLAN["output"]) / "huaxia-history"
LEDGER = HERE / "source-request-ledger.json"


def record(ledger, entry):
    ledger.append(entry)
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def main():
    mount = Path(PLAN["external_mount"])
    if not mount.is_dir() or mount.stat().st_dev != PLAN["external_device"]:
        raise RuntimeError("planned external device unavailable")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free < PLAN["external_reserve_bytes"] + 60 * 1024 * 1024:
        raise RuntimeError("external reserve or 60 MiB estimate unavailable")
    OUT.mkdir(exist_ok=False)
    if OUT.stat().st_dev != PLAN["external_device"]:
        raise RuntimeError("wrong output device")
    ledger = []
    for item in HISTORY["reports"]:
        year, kind = item["year"], item["type"]
        if year == 2024:
            continue
        key = f"{year}{kind}"
        page_entry = {"key": key, "kind": "announcement_page", "url": item["page"],
                      "requested_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        try:
            response = requests.get(item["page"], timeout=25)
            page_entry.update(status=response.status_code, bytes=len(response.content),
                              final_url=response.url)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            if "华夏成长证券投资基金" not in title:
                raise ValueError(f"unexpected announcement title: {title}")
            wanted = "半年度报告" if year == 2019 and kind == "H1" else ("中期报告" if kind == "H1" else "年度报告")
            links = [(a.get_text(" ", strip=True), urljoin(item["page"], a.get("href") or ""))
                     for a in soup.find_all("a")]
            links = [(name, url) for name, url in links
                     if "华夏成长证券投资基金" in name and wanted in name
                     and "摘要" not in name and url.startswith("https://www.chinaamc.com/")]
            if len(links) != 1:
                raise ValueError(f"expected one full-report PDF link, found {links}")
            page_entry.update(title=title, pdf_label=links[0][0], pdf_url=links[0][1])
        except Exception as exc:
            page_entry["error"] = f"{type(exc).__name__}: {exc}"
            record(ledger, page_entry)
            continue
        record(ledger, page_entry)

        pdf_url = links[0][1]
        pdf_entry = {"key": key, "kind": "official_pdf", "url": pdf_url,
                     "requested_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        target = OUT / f"000001-{key}-chinaamc.pdf"
        try:
            digest = hashlib.sha256()
            size = 0
            with requests.get(pdf_url, timeout=40, stream=True) as source:
                pdf_entry.update(status=source.status_code, final_url=source.url,
                                 content_type=source.headers.get("content-type"))
                source.raise_for_status()
                with target.open("xb") as destination:
                    for chunk in source.iter_content(65536):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > 10 * 1024 * 1024:
                            raise ValueError("PDF exceeds 10 MiB cap")
                        digest.update(chunk)
                        destination.write(chunk)
            if target.open("rb").read(5) != b"%PDF-":
                raise ValueError("not a PDF")
            pdf_entry.update(bytes=size, sha256=digest.hexdigest(),
                             pages=len(PdfReader(str(target)).pages), saved_path=str(target))
        except Exception as exc:
            pdf_entry["error"] = f"{type(exc).__name__}: {exc}"
        record(ledger, pdf_entry)
    print(json.dumps({"pdf_success": sum(x["kind"] == "official_pdf" and "error" not in x for x in ledger),
                      "failures": [x for x in ledger if "error" in x],
                      "requests": len(ledger)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
