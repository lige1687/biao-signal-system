"""Acquire 070002 semiannual/annual original reports from the official JSFund list.

Reuses three previously retained PDFs by hash and records source metadata. No returns.
"""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).parent
PLAN = json.loads((ROOT.parent / "storage-plan.json").read_text())
OUT = Path(PLAN["output"]) / "jiashi-history"
BASE = "https://www.jsfund.cn"
LIST_URL = BASE + "/servlet/json"
OLD = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china")
OLD_FY = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/china")
REUSE = {
    "2021FY": OLD / "070002-2021FY-jsfund.pdf",
    "2024H1": OLD / "070002-2024H1-jsfund.pdf",
    "2024FY": OLD_FY / "070002-2024FY-jsfund.pdf",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def key(title):
    y = re.search(r"(2019|202[0-5])年", title)
    if not y or not ("年度报告" in title or "中期报告" in title or "半年度报告" in title):
        return None
    return y.group(1) + ("H1" if "半年度报告" in title or "中期报告" in title else "FY")


def main():
    assert Path(PLAN["external_mount"]).stat().st_dev == PLAN["external_device"]
    assert OUT.parent.is_dir()
    OUT.mkdir(exist_ok=True)
    session = requests.Session()
    params = {"funcNo": "741015", "product_id": "18", "curtpage": "1", "numperpage": "200", "keyword": "报告", "start_date": "", "end_date": "", "select_time": "", "type": "156"}
    response = session.get(LIST_URL, params=params, timeout=30)
    response.raise_for_status()
    result = response.json()["results"][0]
    assert result["totalPages"] == 1
    items = {}
    for item in result["data"]:
        k = key(item["title"])
        if k:
            assert k not in items, k
            items[k] = item
    assert len(items) == 14 and set(items) == {f"{y}{s}" for y in range(2019, 2026) for s in ("H1", "FY")}
    records = []
    for k in sorted(items):
        item = items[k]
        source_url = urljoin(BASE, item["attachment_url"]) if item["attachment_url"] else None
        detail_url = None
        if not source_url:
            detail_url = BASE + f"/Services/cn/jsp/product/gg_detail_iframe.jsp?ArticleID={item['ad_id']}&FundCode=070002&type=1"
            detail = session.get(detail_url, timeout=30)
            detail.raise_for_status()
            match = re.search(r'zcmsattachrela="(\d+)"', detail.text)
            if match:
                source_url = BASE + f"/cms/Services/AttachDownLoad.jsp?id={match.group(1)}"
        reused = k in REUSE
        path = REUSE[k] if reused else OUT / f"070002-{k}-jsfund.pdf"
        status = "missing_source_url" if not source_url else "found"
        error = None
        if source_url and not reused and not (path.exists() and path.read_bytes()[:5] == b"%PDF-"):
            try:
                resp = session.get(source_url, timeout=90)
                resp.raise_for_status()
                if not resp.content.startswith(b"%PDF-"):
                    status = "non_pdf_response"
                else:
                    path.write_bytes(resp.content)
            except requests.RequestException as exc:
                status = "download_error"
                error = type(exc).__name__ + ": " + str(exc)[:160]
        if status == "found":
            assert path.exists() and path.read_bytes()[:5] == b"%PDF-", path
        records.append({"period": k, "period_end": f"{k[:4]}-{'06-30' if k.endswith('H1') else '12-31'}", "official_title": item["title"], "official_pub_date": item["pub_date"], "official_ad_id": item["ad_id"], "official_list_url": BASE + "/main/fund/070002/fundAnn.shtml", "detail_url": detail_url, "pdf_url": source_url, "pdf_path": str(path) if status == "found" else None, "pdf_sha256": sha(path) if status == "found" else None, "pdf_bytes": path.stat().st_size if status == "found" else None, "reused": reused, "status": status, "error": error})
        print(k, status, "reused" if reused else "new", records[-1]["pdf_bytes"])
        (ROOT / "source-manifest.json").write_text(json.dumps({"fund_code": "070002", "official_list_query_url": response.url, "reports": records}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
