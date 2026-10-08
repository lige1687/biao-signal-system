"""Read-only catalog coverage check; no requests or membership writes."""
import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = read(HERE / "source-manifest.json")
facts = read(HERE / "qualified-facts.json")
checks = []


def check(name, passed, evidence):
    checks.append({"name": name, "passed": bool(passed), "evidence": evidence})


for source in manifest["new_sources"]:
    path = ROOT / source["raw_path"]
    check(source["id"] + ":source_bytes", sha(path) == source["raw_sha256"]
          and path.stat().st_size == source["raw_bytes"], source["raw_path"])
for source in manifest["reused_inputs"]:
    check(source["path"] + ":unchanged", sha(ROOT / source["path"]) == source["sha256"], source["path"])

groups = {}
for prefix, key in [("indexed", "indexed_query"), ("title", "keyword_query")]:
    pages = [s for s in manifest["new_sources"] if s["id"].startswith(prefix)]
    rows = [v for s in pages for v in read(ROOT / s["raw_path"])["data"]]
    ids = [r["id"] for r in rows]
    groups[prefix] = {r["id"]: r for r in rows}
    check(prefix + ":page_coverage", sorted(s["body"]["page"]["page"] for s in pages)
          == list(range(1, facts[key]["pages"] + 1))
          and all(read(ROOT / s["raw_path"])["total"] == facts[key]["total"] for s in pages)
          and len(ids) == len(set(ids)) == facts[key]["total"]
          and sorted(ids) == facts[key]["unique_ids"], "all reported pages, stable total, no duplicate id")
    check(prefix + ":date_window", all("2022-01-04" <= r["publishDate"] <= "2026-06-30" for r in rows),
          "publication-date coverage only, not effective-date completeness")
    field, value = facts[key]["field"], facts[key]["value"]
    check(prefix + ":query_binding", all(s["body"].get(field) == value for s in pages), field)

regular = read(ROOT / "docs/experiments/raw/csi300-regular-transitions-2026-10-08/qualified-facts.json")
known = {e["notice_id"] for e in regular["events"]} | {15546, 1006022}
union = groups["indexed"] | groups["title"]
check("known_notice_controls", sorted(known) == facts["known_formal_event_ids_in_publication_window"]
      and sorted(known - groups["indexed"].keys()) == facts["known_missing_from_indexed"] == [14796, 3006000]
      and not known - groups["title"].keys(), "9 regular +2 conditional formal notices; 2021 notice excluded by publication window")
for notice_id in [14796, 3006000]:
    doc = read(ROOT / f"docs/experiments/raw/csi300-regular-transitions-2026-10-08/originals/notice-{notice_id}.json")["data"]
    text = re.sub(r"\s+", "", BeautifulSoup(doc["content"], "html.parser").get_text())
    check(str(notice_id) + ":positive_control", doc["id"] == notice_id
          and doc["publishDate"][:10] == union[notice_id]["publishDate"]
          and "沪深300指数更换" in text and "收市后生效" in text, "saved formal source, not search-snippet assumption")
formal = [r for r in union.values() if r["theme"] == "指数调样" and r["noticeType"] == "announcement"]
check("formal_union", {r["id"] for r in formal} == known
      and facts["additional_formal_adjustments_identified"] == [], "no extra formal adjustment in these queries; not absence proof")
check("set_comparison", len(union) == facts["union_count"] == 83
      and sorted(groups["title"].keys() - groups["indexed"].keys()) == facts["keyword_only_ids"]
      and not groups["indexed"].keys() - groups["title"].keys(), "six keyword-only metadata records")
ledger = read(HERE / "request-ledger.json")
check("budget", sum(s["raw_bytes"] for s in manifest["new_sources"]) == ledger["new_http_bytes"] == 32128
      and len(manifest["new_sources"]) == ledger["new_http_requests"] == 5
      and ledger["cumulative_family_bytes"] == ledger["prior_family_bytes"] + ledger["new_http_bytes"]
      and ledger["cumulative_family_bytes"] <= ledger["family_limit_bytes"], "same10MiB family")
check("conclusion_boundary", not facts["full_historical_chain_qualified"]
      and not facts["full_start_anchor_qualified"] and not facts["full_catalog_archive_certified"]
      and all(facts[k] == 0 for k in ["membership_repairs", "fits", "labels"]), "keep negative coverage finding; no source promotion")
passed = sum(x["passed"] for x in checks)
print(json.dumps({"status": "passed" if passed == len(checks) else "failed", "passed": passed,
                  "total": len(checks), "checks": checks}, ensure_ascii=False, indent=2))
raise SystemExit(0 if passed == len(checks) else 1)
