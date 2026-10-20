"""Freeze source-only review priorities from saved blocker counts, never returns."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "lowfreq-profitability-increment-2026-10-19"
PRIOR = HERE.parent / "osap-history-revisions-2026-10-20"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(binding):
    assert sha(binding["path"]) == binding["sha256"], binding["path"]
    return json.loads(Path(binding["path"]).read_text())


contract = json.loads((OLD / "source-panel-final-01-contract.json").read_text())
preparation = load(contract["inputs"]["preparation"][0])
base = Path(contract["output"]["path"])
queue_path = base / "notice-review-queue.json"
audit_path = base / "audit.json"
assert sha(queue_path) == "9c519865b6de7cd16ecb968e9d45fbe62719b4bcd654790b351417ef7d450282"
assert sha(audit_path) == "5765e8f64f0e201a5713e8c988bd336c0cbf29715f9014c079fa207fed5105a5"
queue = json.loads(queue_path.read_text())
audit = json.loads(audit_path.read_text())
meta = {(d["cohort_code"], str(d["announcement_id"])): d for d in preparation["documents"]}
index = {(r["code"], str(r["announcement_id"])): r for r in queue}
excluded = set()
for review in (load(contract["inputs"]["notice_review"]),
               json.loads((PRIOR / "notice-review-one.json").read_text())):
    excluded.update((d["cohort_code"], str(d["announcement_id"])) for d in review["decisions"])
controller = load(contract["inputs"]["controller_review"])
excluded.update((d["cohort_code"], str(d["announcement_id"])) for d in controller["decisions"]
                if d.get("controller_decision") == "accept_explicit_business_scope_for_this_document_only")
single = defaultdict(set)
all_affected = defaultdict(set)
for row in audit:
    for feature in ("gp", "cfo"):
        blockers = row[feature].get("blockers", [])
        for blocker in blockers:
            key = (row["code"], str(blocker["announcement_id"]))
            all_affected[key].add(row["month"])
            if len(blockers) == 1:
                single[key].add(row["month"])
candidates = []
for key, months in single.items():
    item = meta.get(key, {})
    notice = item.get("notice_text")
    if key in excluded or not notice or notice.get("pages", 999) > 3:
        continue
    if index[key]["source_status"] != "obtained":
        continue
    candidates.append({"code": key[0], "announcement_id": key[1],
                       "single_blocker_company_months": len(months),
                       "all_affected_company_months": len(all_affected[key]),
                       "queue": index[key], "prepared": item})
candidates.sort(key=lambda r: (-r["single_blocker_company_months"], r["code"], r["announcement_id"]))
selected = candidates[:20]
for row in selected:
    prepared = load(row["prepared"])
    row["source"] = prepared["source"]
    identity = prepared["source"]["source_identity"]
    assert sha(identity["path"]) == identity["sha256"]
    text = load(row["prepared"]["notice_text"])
    assert len(text) == row["prepared"]["notice_text"]["pages"]
    row["all_pages_read_required"] = list(range(1, len(text) + 1))
packet = {
    "schema": "notice-controller-packet/1", "created_at": datetime.now().astimezone().isoformat(),
    "selection": "Obtained saved notice text <=3 pages, excludes prior accepted/reviewed notices; rank by unique company-months where this is the sole blocker, then code and ID; first20. No title-based clearance and no returns read.",
    "why_refined_from_luna": "A queue entry's total blocked count can overlap many other blockers. Sole-blocker count prioritizes potential usable-row recovery; all unresolved co-blockers remain.",
    "eligible_short_single_blocker_notices": len(candidates), "selected_count": len(selected),
    "source_bindings": {
        "queue": {"path": str(queue_path), "sha256": sha(queue_path)},
        "audit": {"path": str(audit_path), "sha256": sha(audit_path)},
        "preparation": contract["inputs"]["preparation"][0],
        "luna": {"path": str(HERE / "luna-triage.json"), "sha256": sha(HERE / "luna-triage.json")},
    },
    "selected": selected, "market_outcomes_read": False,
}
with (HERE / "review-packet.json").open("x") as stream:
    json.dump(packet, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
agent = json.loads((HERE / "sol-contract-v2.json").read_text())
agent["mission"] = "Independently read all pages of the20 frozen notices; judge financial scope, never change source qualification or market tests"
agent["read_only_paths"].append(str(HERE / "review-packet.json").lstrip("/"))
agent["write_paths"] = [str(HERE / "astra-notice-proposals.json").lstrip("/")]
agent["expected_outputs"] = ["astra-notice-proposals.json with each full-text scope, exact quotes/pages, reject/clear/field-specific proposal"]
agent["executor"] = {"model": "gpt-6-astra", "reasoning_effort": "high"}
with (HERE / "astra-notice-contract.json").open("x") as stream:
    json.dump(agent, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"selected": len(selected), "eligible": len(candidates),
                  "source_only": True, "packet_sha256": sha(HERE / "review-packet.json")}))
