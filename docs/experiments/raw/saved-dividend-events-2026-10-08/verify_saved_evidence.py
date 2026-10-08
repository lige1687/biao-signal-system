"""Verify six fixed observations against saved issuer disclosures; makes no requests."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
import re
import unicodedata

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
def read(name):
    return json.loads((BASE / name).read_text())
def digest(path):
    return sha256(path.read_bytes()).hexdigest()
def normalized(text):
    return re.sub(r"[\s\x00]+", "", unicodedata.normalize("NFKC", text))
checks = []
def check(name, ok, evidence):
    checks.append({"name": name, "passed": bool(ok), "evidence": evidence})
facts = read("qualified-facts.json")
manifest = read("source-manifest.json")
sources = {s["id"]: s for s in manifest["sources"]}
texts = {}
for sid, s in sources.items():
    check(sid + ":raw_hash", digest(ROOT / s["raw_path"]) == s["raw_sha256"], s["raw_path"])
    check(sid + ":text_hash", digest(ROOT / s["selected_text_path"]) == s["selected_text_sha256"], s["selected_text_path"])
    texts[sid] = normalized((ROOT / s["selected_text_path"]).read_text())
observations = []
for b in read("saved-factor-bindings.json"):
    path = ROOT / b["path"]
    check(path.name + ":unchanged", digest(path) == b["expected_sha256"], b["path"])
    actual = json.loads(path.read_text())["records"]
    check(path.name + ":exact_records", actual == b["records"], "provider strings unchanged")
    observations.extend((r["code"], r["dividOperateDate"]) for r in actual)
check("exact_six_keys", len(observations) == 6 and set(observations) == {(e["security"], e["ex_date"]) for e in facts["events"]}, sorted(observations))
visual = read("visual-verification.json")
check("visual_source_and_render_hash", digest(ROOT / sources[visual["source"]]["raw_path"]) == visual["source_sha256"] and digest(ROOT / visual["render_path"]) == visual["render_sha256"], "Hash binds root visual inspection; machine does not read date pixels")
for e in facts["events"]:
    sid, t = e["id"], texts[e["amount_source"]]
    check(sid + ":issuer_and_notice", e["security"].split(".")[1] in t and e["announcement_id"] in t, e["amount_source"])
    cash = re.escape(e["cash_per_eligible_share_cny_gross"])
    check(sid + ":gross_per_share", bool(re.search(r"每股(?:派发)?现金红利(?:人民币)?" + cash + r"元", t)) and "含税" in t, e["amount_source"])
    if sid == "zg2024":
        matches = all(visual["observed_" + k] == e[k] for k in ["record_date", "ex_date"]) and visual["observed_payment_date"] == e["announced_payment_date"]
        check(sid + ":visual_dates_binding", matches and visual["observed_code"] == e["security"].split(".")[1], "root visual check only; no independent reviewer and no OCR assertion")
    else:
        def slash(d):
            y, m, day = d.split("-")
            return f"{y}/{int(m)}/{int(day)}"
        row = "A股" + slash(e["record_date"]) + "-" + slash(e["ex_date"]) + slash(e["announced_payment_date"])
        check(sid + ":source_date_row", row in texts[e["dates_source"]], e["dates_source"])
    check(sid + ":time_and_credit_boundary", e["signature_date"] <= e["public_document_date"] <= e["record_date"] < e["ex_date"] and e["actual_account_credit_verified"] is False and e["historical_vendor_arrival"] is None, "document day is not exact availability timestamp; scheduled pay is not actual credit")
a = {k: Decimal(v) for k, v in facts["differential_dividend_A_shares"].items()}
check("eligible_plus_excluded_equals_total", a["eligible"] + a["excluded_buyback"] == a["total"], {k: str(v) for k, v in a.items()})
for sid, dp in [("ht2024a", 4), ("ht2024h", 5)]:
    e = next(e for e in facts["events"] if e["id"] == sid)
    computed = (a["eligible"] * Decimal(e["cash_per_eligible_share_cny_gross"]) / a["total"]).quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)
    check(sid + ":reference_cash_recomputed", computed == Decimal(e["price_reference_cash_per_total_A_share"]) and str(computed) in texts[sid] and all(f"{int(v):,}" in texts[sid] for k, v in a.items() if k != "excluded_buyback"), str(computed))
for sid, rate, total in [("zg2024", "0.01", "228020353.24"), ("zg2025", "0.018", "410436635.83")]:
    e = next(e for e in facts["events"] if e["id"] == sid)
    value = (Decimal("22802035324") * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    check(sid + ":gross_total_recomputed", value == Decimal(total) and f"{value:,.2f}" in texts[e["amount_source"]], str(value))
check("no_completeness_or_price_claim", all(facts[k] is False for k in ["entire_history_complete", "sina_qfq_reconstructed", "factor_numeric_values_validated"]), "six positive observations only")
result = {"status": "passed" if all(c["passed"] for c in checks) else "failed", "checks": checks, "passed": sum(c["passed"] for c in checks), "total": len(checks), "local_only_source_files_required": True, "independent_agent_review": False, "price_repairs": 0, "labels": 0, "fits": 0}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["status"] == "passed" else 1)
