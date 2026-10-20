"""Read saved public evidence; no downloads, panel rebuild or outcome calculation."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "lowfreq-profitability-increment-2026-10-19"
BULK = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/lowfreq-profitability-bulk-20261019/lowfreq-profitability-bulk-20261019-20261019T103720-b6ff13df5b8d/result")
SEC = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/personal-lowfreq-system-audit-20261018/personal-lowfreq-system-audit-20261018-20261019T005338-7bfb5ca1b315/result/sources")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bound(path):
    return {"path": str(path), "sha256": sha(path)}


def load(path, expected=None):
    if expected is not None:
        assert sha(path) == expected, str(path)
    return json.loads(Path(path).read_text())


def save(name, value):
    # Only this turn's new small audit receipts, never archived source material.
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


manifest_path = BULK / "manifest-0001.json"
manifest = load(manifest_path, "ab07d9e0c310131258faf2a5338cc394c44f1cdd385fe35695f466acec4cf553")
annual = [r for c in manifest["codes"].values() for r in c.get("pdfs", [])
          if "annual" in r["categories"] and r["status"] in {"obtained", "reused"}]
groups = Counter((r["code"], r["report_year_from_title"]) for r in annual)
assert all(Path(r["source_path"]).is_file() for r in annual)
receipt_path = OLD / "source-panel-final-01-receipt.json"
receipt = load(receipt_path, "3598a5927043270f28afb13382ff6d2f35a3a8b1c0482b861e0bfc78db777e01")
panel_dir = BULK / "source-panel-final-01"
queue_path = panel_dir / "notice-review-queue.json"
queue = load(queue_path, "9c519865b6de7cd16ecb968e9d45fbe62719b4bcd654790b351417ef7d450282")
months_path = panel_dir / "monthly-coverage.json"
months = load(months_path, "0a1c8ec483a8f31362fd2516664bf02db8f22d68ecba271e5ba881a45498f29d")
audit_path = panel_dir / "audit.json"
audit = load(audit_path, "5765e8f64f0e201a5713e8c988bd336c0cbf29715f9014c079fa207fed5105a5")

# Root has read all 11 saved pages; independently re-extract the original PDF.
aid, code = "1206159525", "sz.300048"
pdf_record = next(r for r in manifest["codes"]["300048"]["pdfs"] if r["announcement_id"] == aid)
assert sha(pdf_record["source_path"]) == pdf_record["sha256"]
pages = list(PdfReader(pdf_record["source_path"]).pages)
text_path = BULK / "source-batch-02/notice-text/300048-1206159525.json"
text = load(text_path, "446271db1e207a9f1b5f5491608cca468db1eeee05e407a924f4e3b12d9dac36")
assert len(pages) == len(text) == 11
assert all("".join(p.extract_text().split()) == "".join(t["text"].split())
           for p, t in zip(pages, text))
quotes = [
    {"page": 1, "exact_quote": "议案表格里表决意见缺失"},
    {"page": 2, "exact_quote": "除上述更正外，原公告其他内容不变。"},
]
assert all(q["exact_quote"] in text[q["page"]-1]["text"] for q in quotes)
review = {
    "schema": "financial-notice-review/1",
    "reviewer": "root; full saved text and independent PDF extraction",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "decisions": [{
        "cohort_code": code, "announcement_id": aid, "publication_date": "2019-04-30",
        "source_sha256": pdf_record["sha256"],
        "notice_text_path": str(text_path), "notice_text_sha256": sha(text_path),
        "controller_accepted": True, "disposition": "unrelated_business",
        "affected_years": None, "affected_fields": None, "continuing_scope": "cleared",
        "whole_notice_cleared": True, "evidence": quotes,
        "root_basis": "全文及附件仅修补股东大会委托书的表决选项；出现年报、减值和回购议案名称并非修改那些报告或金额。",
        "review_scope": "Only this exact announcement's relevance to assets/revenue/cost/CFO; does not clear other issuer notices.",
    }],
}
runner = OLD / "build_financial_panel.py"
assert sha(runner) == "bcb154293894dc3f2b76c9871647489bdd859ebd7220bcaf766f03363e51f9be"
spec = importlib.util.spec_from_file_location("saved_panel_review_api", runner)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
records = module.expected_index(manifest, [code])
prep_path = BULK / "source-batch-08/manifest.json"
prep = load(prep_path, "56a486d82b994659baf2e3a9fff9b715877bdddd7dde96c529b6716784594014")
item = next(d for d in prep["documents"] if d["cohort_code"] == code and d["announcement_id"] == aid)
module.merge_preparation(records, [{**prep, "documents": [item]}])
decision = module._reviewed_notice(review, records[(code, aid)])
assert decision == review["decisions"][0]
event = {"record": records[(code, aid)], "review": decision, "ambiguous_annual": False}
assert module.event_applies(event, 2018, "gp", None) == (False, "whole_notice_cleared")
assert module.event_applies(event, 2018, "cfo", None) == (False, "whole_notice_cleared")
save("notice-review-one.json", review)
exposure = []
for row in audit:
    if row["code"] != code:
        continue
    for feature in ("gp", "cfo"):
        blockers = row[feature].get("blockers", [])
        if any(str(b["announcement_id"]) == aid for b in blockers):
            exposure.append({"month": row["month"], "feature": feature,
                             "other_blockers": [b["announcement_id"] for b in blockers if str(b["announcement_id"]) != aid]})
old_case = next(r for r in audit if r["code"] == code and r["month"] == "2024-07")
assert old_case["gp"]["amounts_yuan"]["cost"] == "1237465019.86"

# SEC evidence is a saved, public CompanyFacts aggregation, not a complete archive.
facts_path, sub_path = SEC / "aapl-companyfacts.json", SEC / "aapl-submissions.json"
facts = load(facts_path, "73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43")
sub = load(sub_path, "aad00f6aa75ba1405e0a34c788bdba9042281b2724fe1db3ff26f434b9a92e44")
assets = facts["facts"]["us-gaap"]["Assets"]["units"]["USD"]
by_end = defaultdict(list)
for r in assets:
    by_end[r["end"]].append(r)
recent = sub["filings"]["recent"]
acceptance = dict(zip(recent["accessionNumber"], recent["acceptanceDateTime"]))
example = [r for r in assets if r["end"] == "2015-09-26" and r["accn"] in {
    "0001193125-15-356351", "0001628280-16-020309"}]
assert len({r["val"] for r in example}) == 2
result = {
    "schema": "public-saved-evidence-audit/1", "checked_at": datetime.now(timezone.utc).isoformat(),
    "sources": [bound(p) for p in (manifest_path, receipt_path, queue_path, months_path,
                                 audit_path, prep_path, runner, facts_path, sub_path)],
    "initial_cninfo_snapshot": {
        "annual_obtained_or_reused_records": len(annual),
        "distinct_paths": len({r["source_path"] for r in annual}),
        "all_paths_exist": True, "full_collection_content_hash_recomputed": False,
        "distinct_recorded_hashes": len({r["sha256"] for r in annual}),
        "companies": len({r["code"] for r in annual}), "company_year_groups": len(groups),
        "multiple_version_company_year_groups": sum(v > 1 for v in groups.values()),
        "report_years": dict(sorted(Counter(r["report_year_from_title"] for r in annual).items())),
        "limits": "Initial snapshot only; includes cancelled/revised reports; not all valid final versions, not final 600-company collection.",
    },
    "final_existing_panel": {
        "rows": len(audit), "companies": len({r["code"] for r in audit}), "months": len(months),
        "month_range": [months[0]["month"], months[-1]["month"]],
        "common_qualified_min_median_max": [min(r["common_pool"] for r in months),
            statistics.median(r["common_pool"] for r in months), max(r["common_pool"] for r in months)],
        "notice_feature_queue_rows": len(queue),
        "distinct_company_announcements": len({(r["code"], r["announcement_id"]) for r in queue}),
        "queue_source_status": dict(Counter(r["source_status"] for r in queue)),
        "queue_has_hash": sum(bool(r["source_sha256"]) for r in queue),
        "already_preserved_original_hekang_2023_cost": old_case["gp"]["amounts_yuan"]["cost"],
        "limits": "qualification under the archived version policy only; not issuer authenticity, trading readiness or full-market evidence",
    },
    "new_exact_notice_review": {
        "review": bound(HERE / "notice-review-one.json"), "original_pdf": bound(pdf_record["source_path"]),
        "all_11_pdf_pages_normalized_equal_saved_text": True, "existing_review_validator_passed": True,
        "event_no_longer_applies_gp_cfo": True, "old_affected_feature_months": exposure,
        "legacy_panel_or_results_changed": False, "newly_qualified_stock_months_claimed": 0,
        "limits": "Stage-1 annotation only; other issuer notices remain unreviewed. Subsequent single-company qualification is recorded separately in notice-effect-verification.json; the archived full panel is not overwritten.",
    },
    "sec_apple_assets": {
        "rows": len(assets), "end_range": [min(by_end), max(by_end)], "different_ends": len(by_end),
        "ends_multiple_accessions": sum(len({r["accn"] for r in rs}) > 1 for rs in by_end.values()),
        "ends_different_values": sum(len({r["val"] for r in rs}) > 1 for rs in by_end.values()),
        "all_instant_no_start": all("start" not in r for r in assets),
        "forms": dict(Counter(r["form"] for r in assets)),
        "example": [{**r, "acceptanceDateTime": acceptance.get(r["accn"])} for r in example],
        "rows_with_recent_acceptance": sum(r["accn"] in acceptance for r in assets),
        "accessions": len({r["accn"] for r in assets}),
        "accessions_with_recent_acceptance": len({r["accn"] for r in assets if r["accn"] in acceptance}),
        "historical_files_listed_not_read": sub["filings"]["files"],
        "limits": "Same-end value differences need original filing explanation; do not infer restatement from facts alone. Acceptance is not historical API/vendor delivery time.",
    },
    "downloads": 0, "market_effect_runs": 0, "archived_panel_reruns": 0,
}
save("public-saved-audit.json", result)
print(json.dumps({"annual_records": len(annual), "queue_rows": len(queue),
                  "queue_unique_announcements": result["final_existing_panel"]["distinct_company_announcements"],
                  "notice_validator": True, "old_notice_feature_months": len(exposure),
                  "assets_rows": len(assets), "output": str(HERE / "public-saved-audit.json")}))
