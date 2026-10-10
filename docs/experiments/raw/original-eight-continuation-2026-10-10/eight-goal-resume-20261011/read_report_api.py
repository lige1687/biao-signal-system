"""Verify the finished report's exact text and report-library registration."""
import hashlib
import json
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent
entry = json.loads((RAW.parent / "eight-goal-review-registration-entry.json").read_text())
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open("http://127.0.0.1:8000/api/experiments/" + entry["report"], timeout=30) as response:
    report = json.load(response)
actual_sha = hashlib.sha256(report["markdown"].encode()).hexdigest()
assert actual_sha == entry["entry"]["report_sha256"]
for field in ["category", "verdict", "oneLiner"]:
    assert report[field] == entry["entry"][field]
with opener.open("http://127.0.0.1:8000/api/experiments", timeout=120) as response:
    listing = json.load(response)
row = next(x for x in listing["items"] if x["name"] == entry["report"])
assert row["pending"] is False
for field in ["category", "verdict", "oneLiner"]:
    assert row[field] == report[field]
(RAW / "report-api-readback.json").write_text(json.dumps({
    "report": entry["report"], "served_markdown_sha256": actual_sha,
    "category": report["category"], "verdict": report["verdict"],
    "oneLiner": report["oneLiner"], "list_pending": False,
    "actual_single_fulltext_and_list_fields_match": True}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"actual_fulltext_sha_match": True, "classification_match": True,
                  "list_pending_false": True}))
