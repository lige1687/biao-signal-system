"""Read-only verification of nine saved CSI300 notices and candidate date errors.

No network, labels, model runs, repairs, or writes. Prints a JSON result.
PDF code columns are independently extracted with pypdf, not saved text.
"""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
read = lambda p: json.loads(p.read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []


def check(name, passed, evidence):
    checks.append({"name": name, "passed": bool(passed), "evidence": evidence})


sources = read(HERE / "source-manifest.json")["sources"]
by_id = {s["id"]: s for s in sources}
for source in sources:
    path = ROOT / source["raw_path"]
    check(source["id"] + ":bytes", path.stat().st_size == source["raw_bytes"]
          and digest(path) == source["raw_sha256"], source["raw_path"])
    if "text_path" in source:
        check(source["id"] + ":saved_text_hash",
              digest(ROOT / source["text_path"]) == source["text_sha256"], source["text_path"])

bindings = read(HERE / "input-bindings.json")
for item in bindings["inputs"]:
    check(item["path"] + ":immutable", digest(ROOT / item["path"]) == item["sha256"], item["path"])
check("contract_immutable", digest(HERE / "contract.json") == bindings["contract_sha256"], "contract.json")
frame = pd.read_parquet(ROOT / bindings["inputs"][0]["path"])
manifest = read(ROOT / bindings["inputs"][1]["path"])
originals = {x["candidate_difference_detected_date"]: x
             for x in manifest["candidate_change_objects_not_complete_chain"]}
facts = read(HERE / "qualified-facts.json")["events"]
comparison = read(HERE / "candidate-comparison.json")
events = {x["notice_id"]: x for x in comparison["events"]}
axis = frame.date.drop_duplicates().sort_values()
total_errors = total_bad_dates = checked_blocks = 0
for fact in facts:
    key = "notice-" + str(fact["notice_id"])
    document = read(ROOT / by_id[key]["raw_path"])["data"]
    soup = BeautifulSoup(document["content"], "html.parser")
    plain = re.sub(r"\s+", "", soup.get_text())
    close = pd.Timestamp(fact["effective_after_close"])
    effective_text = f"{close.year}年{close.month}月{close.day}日收市后生效"
    check(key + ":date_metadata", document["publishDate"][:10] == fact["published"]
          and effective_text in plain and document["id"] == fact["notice_id"], effective_text)
    check(key + ":published_count", f"沪深300指数更换{fact['declared_replacements']}只样本" in plain,
          fact["declared_replacements"])
    if key + "-attachment" in by_id:
        pdf = by_id[key + "-attachment"]
        text = PdfReader(ROOT / pdf["raw_path"]).pages[0].extract_text()
        section = re.split(r"中证\s*500", text)[0]
        codes = re.findall(r"\b\d{6}\b", section)
        source_old, source_new = codes[::2], codes[1::2]
        check(key + ":pdf_scope", "沪深300指数样本调整名单" in re.sub(r"\s+", "", section)
              and "调出名单调入名单" in re.sub(r"\s+", "", section), "pypdf first-page columns")
    else:
        tables = pd.read_html(__import__('io').StringIO(str(soup.find_all("table")[0])), dtype_backend="numpy_nullable")
        table = tables[0]
        source_old = [str(v).strip() for v in table.iloc[2:, 0]]
        source_new = [str(v).strip() for v in table.iloc[2:, 2]]
        check(key + ":html_scope", str(table.iloc[0, 0]) == "调出名单"
              and str(table.iloc[0, 2]) == "调入名单" and "沪深300指数样本调整名单" in plain,
              "pandas independently parsed first notice table")
    saved_old = [r["removed_code"] for r in fact["rows"]]
    saved_new = [r["added_code"] for r in fact["rows"]]
    check(key + ":source_lists", source_old == saved_old and source_new == saved_new
          and len(source_old) == fact["declared_replacements"], "independent source extraction")
    target = pd.Timestamp(fact["candidate_date"])
    old, new = set(saved_old), set(saved_new)
    original = originals[fact["candidate_date"]]
    check(key + ":original_object", old == set(original["removed_codes_from_candidate"])
          and new == set(original["added_codes_from_candidate"]), "unmodified original12-object queue")
    first = axis[axis > close].iloc[0].date().isoformat()
    check(key + ":effective_axis", first == fact["first_saved_axis_date_after_effective_close"],
          "first saved date strictly after official after-close effect; not independent exchange calendar")
    slice_ = frame[(frame.date > close) & (frame.date <= target)]
    # A presence matrix is deliberately separate from the producer's set-subtraction loop.
    matrix = pd.crosstab(slice_.date, slice_.symbol).reindex(columns=sorted(old | new), fill_value=0)
    stale = matrix[sorted(old)].sum(axis=1)
    missing = (matrix[sorted(new)] == 0).sum(axis=1)
    computed = stale + missing
    recorded = events[fact["notice_id"]]
    observations = recorded["observations"]
    check(key + ":dated_error_counts", list(computed.astype(int)) == [x["status_errors"] for x in observations]
          and [d.date().isoformat() for d in computed.index] == [x["date"] for x in observations]
          and int(stale.sum()) == recorded["obsolete_present_count"]
          and int(missing.sum()) == recorded["required_absent_count"], "independent presence matrix")
    check(key + ":preserved_300", bool((slice_.groupby("date").symbol.nunique() == 300).all())
          and not slice_.duplicated(["date", "symbol"]).any(), "count alone does not establish right identities")
    before = set(frame.loc[frame.date == close, "symbol"])
    after = set(frame.loc[frame.date == target, "symbol"])
    previous_day = axis[axis < target].iloc[-1]
    previous = set(frame.loc[frame.date == previous_day, "symbol"])
    check(key + ":endpoints", old <= before and not new & before and new <= after and not old & after
          and after - previous == new and previous - after == old, "actual original daily records")
    total_errors += int(computed.sum())
    total_bad_dates += int((computed > 0).sum())
    checked_blocks += len(computed)

summary = comparison["summary"]
check("aggregate", total_errors == summary["status_errors"] == 1920
      and total_bad_dates == summary["mismatch_dates"] == 64
      and checked_blocks == summary["checked_date_blocks"] == 73
      and sum(f["declared_replacements"] for f in facts) == summary["replacements"] == 131,
      "nine events, eight timely; one15-pair event delayed across64 saved dates")
ledger = read(HERE / "request-ledger.json")
check("source_budget", len(sources) == ledger["requests"] == 25
      and sum(s["raw_bytes"] for s in sources) == ledger["raw_response_bytes"] == 1889600
      and ledger["source_family_bytes"] == ledger["source_family_prior_bytes"] + ledger["raw_response_bytes"]
      and ledger["source_family_bytes"] <= ledger["source_family_limit_bytes"], "same cumulative family, no reset")
check("boundary", not summary["full_anchor_qualified"] and not summary["all_historical_events_qualified"]
      and all(summary[k] == 0 for k in ["membership_repairs", "prices", "fits", "labels"]),
      "research inputs not released; retrospective factual qualification only")
passed = sum(c["passed"] for c in checks)
print(json.dumps({"status": "passed" if passed == len(checks) else "failed", "passed": passed,
                  "total": len(checks), "checks": checks}, ensure_ascii=False, indent=2))
raise SystemExit(0 if passed == len(checks) else 1)
