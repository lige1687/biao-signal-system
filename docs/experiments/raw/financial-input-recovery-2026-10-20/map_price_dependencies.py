"""Map a known source fault to decision dependencies before any new effects."""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True
from lei_signal.research.lowfreq_input_guard import inspect_contract


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bound(item):
    assert digest(item["path"]) == item["sha256"], item["path"]
    return json.loads(Path(item["path"]).read_text())


def table(doc):
    return [dict(zip(doc["fields"], row)) for row in doc["data"]]


def main():
    output = HERE / "price-dependency-audit.json"
    assert not output.exists(), "Do not overwrite a completed pre-effect audit"
    contract_path = HERE.parent / "lowfreq-expanded-discovery-2026-10-19/evaluation-input-contract-v2.json"
    contract = json.loads(contract_path.read_text())
    guard = inspect_contract(contract_path)
    assert set(guard["blockers"]) == {"returned_adjustflag"}, guard["blockers"]
    assert guard["blockers"]["returned_adjustflag"]["by_code"] == {"sz.001914": 1560}
    source = next(s for s in contract["sources"] if s["code"] == "sz.001914")
    raw = table(bound(source))
    quotes = {r["date"]: r for r in raw}
    valid = [r for r in raw if r["tradestatus"] == "1" and
             math.isfinite(float(r["close"])) and float(r["close"]) > 0 and r["isST"] in ("0", "1")]
    pos = {r["date"]: i for i, r in enumerate(valid)}
    calendar = [r["calendar_date"] for r in table(bound(contract["calendar"])) if str(r["is_trading_day"]) == "1"]
    cpos = {day: i for i, day in enumerate(calendar)}
    design = json.loads((HERE / "defensive-design-v2.json").read_text())
    panel_spec = design["source"]
    assert digest(panel_spec["path"]) == panel_spec["sha256"]
    rows, original_weights = [], {}
    # Never retain or use future-return/status fields; only decision-time fields.
    with Path(panel_spec["path"]).open() as handle:
        for r in csv.DictReader(handle):
            original_weights.setdefault(r["month"], []).append(float(r["weight_momentum_top20"]))
            if r["code"] == "sz.001914":
                rows.append({k: r[k] for k in ("month", "decision_date", "entry_date", "exit_date", "code", "eligibility_reason",
                                              "momentum_252_start_date", "momentum_21_calendar_days", "valid_count")})
    records = []
    for r in rows:
        detail = dict(r)
        detail["blocked_by_returned_price_basis"] = False
        if r["eligibility_reason"] == "eligible":
            day = r["decision_date"]
            i, j = pos[day], cpos[day]
            assert i >= 252 and j >= 60
            start, end = valid[i-252]["date"], valid[i-21]["date"]
            assert start == r["momentum_252_start_date"] and i + 1 == int(r["valid_count"])
            assert (dt.date.fromisoformat(day)-dt.date.fromisoformat(end)).days == int(r["momentum_21_calendar_days"])
            # Include all 61 volatility levels and the decision price/amount/ST
            # dependency, plus the two actual-quote momentum endpoints.
            dependency = set(calendar[j-60:j+1]) | {start, end, day}
            bad = sorted(d for d in dependency if d not in quotes or str(quotes[d]["adjustflag"]) != "2")
            detail.update(momentum_start=start, momentum_end=end,
                          volatility_start=calendar[j-60], volatility_end=day,
                          dependency_count=len(dependency), bad_dependency_dates=bad,
                          blocked_by_returned_price_basis=bool(bad))
            detail["evaluation_endpoint_price_basis"] = {
                key: quotes.get(r[key], {}).get("adjustflag") for key in ("entry_date", "exit_date")}
        else:
            detail["exclusion_reason"] = "Original decision eligibility excludes this code; do not alter membership."
        records.append(detail)
    original_blocked = sorted(m for m, weights in original_weights.items() if all(w == 0 for w in weights))
    integrity_blocked = sorted(r["month"] for r in records if r["blocked_by_returned_price_basis"])
    union = sorted(set(original_blocked) | set(integrity_blocked))
    kept = sorted(set(original_weights) - set(union))
    for r in records:
        if r["month"] in kept and r["eligibility_reason"] == "eligible":
            assert all(flag in ("2", None) for flag in r["evaluation_endpoint_price_basis"].values())
    result = {
        "schema": "decision-source-dependency-audit/1",
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "no_new_effects_computed": True,
        "future_fields_used": [],
        "source_contract": {"path": str(contract_path), "sha256": digest(contract_path)},
        "source": source,
        "panel": panel_spec,
        "guard_code": {"path": str(ROOT / "src/lei_signal/research/lowfreq_input_guard.py"),
                       "sha256": digest(ROOT / "src/lei_signal/research/lowfreq_input_guard.py")},
        "runner_sha256": digest(__file__),
        "fresh_all_600_guard": guard,
        "rule": "All methods share missing outcomes for an entire month if any eligible candidate needs a wrong/missing price-basis row. Do not drop the code, rerank it away, or fill the blocked month with cash.",
        "original_blocked_months": original_blocked,
        "integrity_blocked_months": integrity_blocked,
        "combined_blocked_months": union,
        "retained_evaluable_months": kept,
        "retained_counts": {"calendar": 132, "original_blocked": len(original_blocked),
                            "price_integrity_blocked": len(integrity_blocked), "combined_blocked": len(union),
                            "evaluable": len(kept)},
        "period_support": {label: sum(lo <= m <= hi for m in kept) for label, lo, hi in
                           (("2015-2020", "2015-01", "2020-12"), ("2021-2025", "2021-01", "2025-12"))},
        "records": records,
        "limitations": ["Known price-basis fault isolated, not repaired.",
                       "Remaining dates do not establish full 11-year, all-market, point-in-time or executable evidence.",
                       "Audit source marking and eligibility are decision dependencies; no return-driven omission.",
                       "Old saved panel and whole-package guard remain unchanged and blocked."],
    }
    with output.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"path": str(output), "sha256": digest(output), "counts": result["retained_counts"],
                      "period_support": result["period_support"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
