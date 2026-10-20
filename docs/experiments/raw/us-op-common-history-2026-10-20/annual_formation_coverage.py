#!/usr/bin/env python3
"""Source-only annual filing availability upper bound; never computes OP/returns."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORRECTION = HERE / "method-correction-exact-period.json"
GROUPS = {
    "revenue": ("IS", "4", ("RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenues", "SalesRevenueGoodsNet", "SalesRevenueNet", "SalesRevenueServicesNet")),
    "cogs": ("IS", "4", ("CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfRevenue", "CostOfServices")),
    "sga": ("IS", "4", ("SellingGeneralAndAdministrativeExpense",)),
    "interest": ("IS", "4", ("InterestAndDebtExpense", "InterestExpense", "InterestExpenseDebt", "InterestExpenseNonOperating")),
    "equity": ("BS", "0", ("StockholdersEquity", "CommonStockholdersEquity")),
    "preferred": ("BS", "0", ("PreferredStockValue", "PreferredStockCarryingValue", "PreferredStockRedemptionValue")),
}
FLOW_GROUPS = ("revenue", "cogs", "sga", "interest")
CORRECTION_SHA256 = "237597cff0931968551ad6dba1a9be41c9adc40d9c91c98ded612cc89a30c4b4"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def finite_number(value: str):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def cutoff_for(month: str) -> dt.date:
    year, mon = map(int, month.split("-"))
    form_year = year - 1 if mon <= 6 else year
    return dt.date(form_year, 6, 30)


def rounded_date_candidates(submission: dict, facts: list[dict]) -> dict:
    """Nearest rounded FSDS month-end date; not an exact fiscal period."""
    try:
        period = dt.date.fromisoformat(submission["period"][:10])
    except (KeyError, ValueError):
        return {"rounded_date_candidate": None, "offset_days": None, "status": "no_period"}
    dates = set()
    for row in facts:
        if row.get("stmt") != "IS" or row.get("qtrs") != "4" or row.get("uom") != "USD" or row.get("segments") or row.get("coreg"):
            continue
        try:
            d = dt.datetime.strptime(row.get("ddate", ""), "%Y%m%d").date()
        except ValueError:
            continue
        dates.add(d)
    if not dates:
        return {"rounded_date_candidate": None, "offset_days": None, "status": "no_annual_flow_date"}
    distance = min(abs((d - period).days) for d in dates)
    nearest = sorted(d for d in dates if abs((d - period).days) == distance)
    return {
        "rounded_date_candidate": [d.isoformat() for d in nearest],
        "offset_days": distance,
        "status": "within_7_days_rounded_date_candidate" if distance <= 7 else "outside_7_days",
        "exact_period_unverified": True,
        "retrieval_scope": "registered_metadata_only",
    }


def select_filing(submissions: list[dict], date_by_adsh: dict[str, dict], cutoff: dt.date, target_year: int, conflicting_adshs=frozenset()):
    eligible = []
    for sub in submissions:
        if sub.get("form") not in {"10-K", "10-K/A"}:
            continue
        try:
            sub_period = dt.date.fromisoformat(sub.get("period", "")[:10])
        except ValueError:
            continue
        # SUB.period is itself rounded to month-end; use it only as a calendar-year candidate.
        if sub_period.year != target_year:
            continue
        try:
            accepted = dt.datetime.fromisoformat(sub.get("accepted", "").replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if accepted <= cutoff - dt.timedelta(days=2):
            eligible.append((sub_period.isoformat(), accepted, sub))
    if not eligible:
        return None, "no_candidate_filing_asof_cutoff"
    if any(x[2].get("adsh") in conflicting_adshs for x in eligible):
        return None, "conflicting_submission_rows"
    best_date = max(x[0] for x in eligible)
    eligible = [x for x in eligible if x[0] == best_date]
    best_accepted = max(x[1] for x in eligible)
    eligible = [x for x in eligible if x[1] == best_accepted]
    if len(eligible) != 1:
        return None, "ambiguous_latest_filing"
    return eligible[0][2], "candidate_filing_asof_cutoff"


def field_candidates(adsh: str, date_values: list[str], presentation: dict, facts_by_adsh: dict[str, list[dict]]):
    wanted_dates = set(date_values or [])
    output = {}
    for group, (stmt, qtrs, tags) in GROUPS.items():
        rows = []
        for row in facts_by_adsh.get(adsh, []):
            if row.get("tag") not in tags or row.get("ddate", "")[:4] not in {d[:4] for d in wanted_dates}:
                continue
            if row.get("ddate", "") not in {d.replace("-", "") for d in wanted_dates}:
                continue
            if row.get("qtrs") != qtrs or row.get("uom") != "USD" or row.get("segments") or row.get("coreg"):
                continue
            if presentation.get((adsh, row.get("tag", ""), row.get("version", ""))) != stmt:
                continue
            rows.append({"tag": row.get("tag"), "version": row.get("version"), "ddate_rounded": row.get("ddate"), "qtrs_rounded": row.get("qtrs"), "raw_value": row.get("value", ""), "finite_value": finite_number(row.get("value", "")), "source_zips": row.get("source_zips", [row.get("source_zip", "")])})
        finite = {r["finite_value"] for r in rows if r["finite_value"] is not None}
        output[group] = {"facts": rows, "finite_count": sum(r["finite_value"] is not None for r in rows), "distinct_finite_values": sorted(finite), "status": "missing" if not rows else "only_nonfinite_or_blank" if not finite else "finite_unique_amount" if len(finite) == 1 else "ambiguous_multiple_values"}
    return output


def summarize_member_month(month: str, ticker: str, ciKs: list[str], submissions_by_cik: dict[str, list[dict]], dates_by_adsh: dict[str, dict], facts_by_adsh: dict[str, list[dict]], presentation: dict, conflicting_adshs=frozenset(), evaluation_cache=None):
    cutoff = cutoff_for(month)
    target_year = cutoff.year - 1
    details = []
    for cik in ciKs:
        cache_key = (cik, cutoff.isoformat())
        if evaluation_cache is not None and cache_key in evaluation_cache:
            detail = evaluation_cache[cache_key]
        else:
            sub, status = select_filing(submissions_by_cik.get(cik, []), dates_by_adsh, cutoff, target_year, conflicting_adshs)
            detail = {"candidate_cik": cik, "status": status, "exact_period_unverified": True}
            if sub:
                date_info = dates_by_adsh.get(sub["adsh"], {})
                raw_date_candidates = date_info.get("rounded_date_candidate") or []
                date_candidates = raw_date_candidates if date_info.get("status") == "within_7_days_rounded_date_candidate" and len(raw_date_candidates) == 1 else []
                fields = field_candidates(sub["adsh"], date_candidates, presentation, facts_by_adsh)
                detail.update({"adsh": sub["adsh"], "form": sub.get("form"), "accepted_date": sub.get("accepted"),
                               "sub_period_rounded_candidate": sub.get("period"), "rounded_date_candidate": date_candidates,
                               "raw_rounded_date_candidates": raw_date_candidates,
                               "date_candidate_status": date_info.get("status", "no_rounded_date_candidate"), "fields": fields,
                               "all_four_flow_groups_have_finite_candidate": all(fields[g]["finite_count"] > 0 for g in FLOW_GROUPS),
                               "positive_equity_candidate": any(v > 0 for v in fields["equity"]["distinct_finite_values"]),
                               "finite_preferred_candidate": fields["preferred"]["finite_count"] > 0})
            if evaluation_cache is not None:
                evaluation_cache[cache_key] = detail
        details.append(detail)
    return {"month": month, "ticker": ticker, "formation_cutoff": cutoff.isoformat(), "rounded_date_candidate_year_only": target_year,
            "exact_period_unverified": True, "evidence_scope": "upper_bound_unvalidated_identity",
            "coverage_interpretation": "candidate coverage with unverified identity/date; not a mathematical bound", "candidate_cik_evaluations": details}


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def candidate_ids(value: str) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        values = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        values = value.replace(";", ",").split(",")
    return sorted({str(v).strip().lstrip("0") or "0" for v in values if str(v).strip()})


def run_pipeline(contract_path: Path, output: Path):
    contract = json.loads(contract_path.read_text())
    validate_bindings(contract)
    allowed_output = Path(contract["write_paths"][-1])
    if output.resolve() != allowed_output.resolve():
        raise ValueError(f"output must match the frozen external directory: {allowed_output}")
    sub_rows_by_signature = {}
    pres = defaultdict(set)
    for source_name in ("submissions.csv",):
        for item in contract["input_files"]:
            if Path(item["path"]).name != source_name:
                continue
            for row in read_csv(Path(item["path"])):
                source_zip = row.get("source_zip", "")
                identity_row = {k: v for k, v in row.items() if k != "source_zip"}
                if identity_row.get("cik", "").isdigit():
                    identity_row["cik"] = str(int(identity_row["cik"]))
                signature = json.dumps(identity_row, sort_keys=True, separators=(",", ":"))
                if signature in sub_rows_by_signature:
                    if item["path"] not in sub_rows_by_signature[signature]["source_paths"]:
                        sub_rows_by_signature[signature]["source_paths"].append(item["path"])
                    if source_zip and source_zip not in sub_rows_by_signature[signature]["source_zips"]:
                        sub_rows_by_signature[signature]["source_zips"].append(source_zip)
                else:
                    row["cik"] = identity_row.get("cik", row.get("cik", ""))
                    row["source_paths"] = [item["path"]]
                    row["source_zips"] = [source_zip] if source_zip else []
                    sub_rows_by_signature[signature] = row
    for item in contract["input_files"]:
        if Path(item["path"]).name != "presentation.csv":
            continue
        for row in read_csv(Path(item["path"])):
            pres[(row.get("adsh", ""), row.get("tag", ""), row.get("version", ""))].add(row.get("stmt", ""))
    subs_by_cik, subs_by_adsh = defaultdict(list), defaultdict(list)
    for row in sub_rows_by_signature.values():
        cik = str(int(row.get("cik", "0") or "0"))
        row["cik_canonical"] = cik
        subs_by_cik[cik].append(row)
        subs_by_adsh[row.get("adsh", "")].append(row)
    conflicting_adshs = set()
    for adsh, rows in subs_by_adsh.items():
        signatures = {json.dumps({k: v for k, v in row.items() if k not in {"source_paths", "source_zips", "cik_canonical"}}, sort_keys=True, separators=(",", ":")) for row in rows}
        if len(signatures) > 1:
            conflicting_adshs.add(adsh)

    facts_by_adsh = defaultdict(list)
    fact_signatures = {}
    dates_by_adsh = defaultdict(set)
    all_tags = {tag for _, _, tags in GROUPS.values() for tag in tags}
    for item in contract["input_files"]:
        if Path(item["path"]).name != "statement-facts.csv":
            continue
        with Path(item["path"]).open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                adsh = row.get("adsh", "")
                if adsh not in subs_by_adsh or adsh in conflicting_adshs or row.get("uom") != "USD" or row.get("segments") or row.get("coreg"):
                    continue
                statement_set = pres.get((adsh, row.get("tag", ""), row.get("version", "")), set())
                if row.get("qtrs") == "4" and row.get("ddate") and "IS" in statement_set:
                    dates_by_adsh[adsh].add(row["ddate"])
                if row.get("tag") in all_tags and row.get("qtrs") in {"0", "4"} and statement_set:
                    source_zip = row.get("source_zip", "")
                    identity_row = {k: v for k, v in row.items() if k != "source_zip"}
                    signature = (adsh, json.dumps(identity_row, sort_keys=True, separators=(",", ":")))
                    if signature in fact_signatures:
                        if source_zip and source_zip not in fact_signatures[signature]["source_zips"]:
                            fact_signatures[signature]["source_zips"].append(source_zip)
                    else:
                        candidate = dict(row)
                        candidate["source_zips"] = [source_zip] if source_zip else []
                        fact_signatures[signature] = candidate

    for (adsh, _), candidate in fact_signatures.items():
        facts_by_adsh[adsh].append(candidate)

    dates = {}
    for adsh, sub_rows in subs_by_adsh.items():
        if adsh in conflicting_adshs:
            dates[adsh] = {"rounded_date_candidate": None, "status": "conflicting_submission_rows", "exact_period_unverified": True}
            continue
        sub = sub_rows[0]
        ds = []
        try:
            period = dt.date.fromisoformat(sub.get("period", "")[:10])
        except ValueError:
            dates[adsh] = {"rounded_date_candidate": None, "status": "no_period", "exact_period_unverified": True}
            continue
        for raw in dates_by_adsh.get(adsh, set()):
            try:
                ds.append(dt.datetime.strptime(raw, "%Y%m%d").date())
            except ValueError:
                continue
        if not ds:
            dates[adsh] = {"rounded_date_candidate": None, "status": "no_annual_flow_date", "exact_period_unverified": True}
            continue
        gap = min(abs((d - period).days) for d in ds)
        nearest = sorted(d for d in ds if abs((d - period).days) == gap)
        candidate_dates = [d.isoformat() for d in nearest]
        dates[adsh] = {"rounded_date_candidate": candidate_dates, "offset_days": gap,
                       "status": "within_7_days_rounded_date_candidate" if gap <= 7 else "outside_7_days",
        "cross_year_boundary_risk": "unknown_from_month_end_labels",
                       "exact_period_unverified": True, "retrieval_scope": "registered_metadata_only"}

    filing_rows = []
    for adsh, rows in subs_by_adsh.items():
        date_info = dates[adsh]
        for sub in rows:
            filing_rows.append({"adsh": adsh, "cik": sub["cik_canonical"], "form": sub.get("form"), "fy_reported": sub.get("fy"), "fp_reported": sub.get("fp"),
                                "period_rounded": sub.get("period"), "filed": sub.get("filed"), "accepted": sub.get("accepted"), "source_paths_json": json.dumps(sub["source_paths"], ensure_ascii=False, separators=(",", ":")), "source_zips_json": json.dumps(sub["source_zips"], ensure_ascii=False, separators=(",", ":")),
                                "rounded_date_candidate_json": json.dumps(date_info.get("rounded_date_candidate"), separators=(",", ":")),
                                "offset_days": date_info.get("offset_days"), "date_candidate_status": date_info["status"],
                                "cross_year_boundary_risk": "unknown_from_month_end_labels", "submission_conflict": adsh in conflicting_adshs,
                                "exact_period_unverified": True,
                                "evidence_scope": "upper_bound_unvalidated_identity", "coverage_interpretation": "candidate coverage; not a mathematical bound"})

    monthly_path = next(Path(x["path"]) for x in contract["input_files"] if Path(x["path"]).name == "monthly-identity-candidates.csv")
    monthly_rows = read_csv(monthly_path)
    result_rows, yearly, observation_yearly = [], defaultdict(Counter), defaultdict(Counter)
    presentation_lookup = {k: next(iter(v)) if len(v) == 1 else "AMBIGUOUS" for k, v in pres.items()}
    evaluation_cache = {}
    selected_field_status = {}
    selected_form_by_adsh = {}
    filed_field_rows = {}
    selected_incomplete_amendment_member_rows = set()
    conflict_patterns = json.loads(next(Path(x["path"]).read_text() for x in contract["input_files"] if Path(x["path"]).name == "identity-controller-audit.json")).get("multi_label_patterns", {})
    known_conflict_member_counts = Counter({pattern: 0 for pattern in conflict_patterns})
    for member in monthly_rows:
        month, ticker = member["month"], member["ticker"]
        candidates = candidate_ids(member.get("candidate_ciks", ""))
        result = summarize_member_month(month, ticker, candidates, subs_by_cik, dates, facts_by_adsh, presentation_lookup, conflicting_adshs, evaluation_cache)
        result.update(member)
        result["candidate_cik_count"] = len(candidates)
        evaluations = result.pop("candidate_cik_evaluations")
        # Summaries are deliberately candidate upper bounds, never approved identity or OP readiness.
        form_year = int(result["formation_cutoff"][:4])
        c = yearly[form_year]
        observation_year = int(month[:4])
        oc = observation_yearly[observation_year]
        c["ticker_month_rows"] += 1
        oc["ticker_month_rows"] += 1
        c["candidate_cik_link"] += int(bool(candidates))
        oc["candidate_cik_link"] += int(bool(candidates))
        c["annual_document_asof_cutoff"] += int(any(x.get("adsh") for x in evaluations))
        oc["annual_document_asof_cutoff"] += int(any(x.get("adsh") for x in evaluations))
        c["four_flows_finite"] += int(any(x.get("all_four_flow_groups_have_finite_candidate") for x in evaluations))
        oc["four_flows_finite"] += int(any(x.get("all_four_flow_groups_have_finite_candidate") for x in evaluations))
        c["four_flows_plus_positive_equity"] += int(any(x.get("all_four_flow_groups_have_finite_candidate") and x.get("positive_equity_candidate") for x in evaluations))
        oc["four_flows_plus_positive_equity"] += int(any(x.get("all_four_flow_groups_have_finite_candidate") and x.get("positive_equity_candidate") for x in evaluations))
        c["plus_explicit_finite_preferred"] += int(any(x.get("all_four_flow_groups_have_finite_candidate") and x.get("positive_equity_candidate") and x.get("finite_preferred_candidate") for x in evaluations))
        oc["plus_explicit_finite_preferred"] += int(any(x.get("all_four_flow_groups_have_finite_candidate") and x.get("positive_equity_candidate") and x.get("finite_preferred_candidate") for x in evaluations))
        for pattern, record in conflict_patterns.items():
            pattern_labels = set(pattern.split("|"))
            if ticker in pattern_labels and month in set(record.get("months", [])):
                known_conflict_member_counts[pattern] += 1
        for ev in evaluations:
            compact = {k: v for k, v in ev.items() if k != "fields"}
            if "fields" in ev:
                compact["field_groups"] = {group: {"status": data["status"], "finite_count": data["finite_count"], "distinct_finite_values": data["distinct_finite_values"]} for group, data in ev["fields"].items()}
            for group, data in ev.get("fields", {}).items():
                if ev.get("adsh"):
                    selected_field_status[(ev["adsh"], group)] = {"status": data["status"], "finite_count": data["finite_count"]}
                    selected_form_by_adsh[ev["adsh"]] = ev.get("form")
                if ev.get("adsh"):
                    key = (ev["adsh"], group)
                    field_row = filed_field_rows.setdefault(key, {"month": month, "ticker": ticker, "candidate_cik": ev["candidate_cik"], "adsh": ev["adsh"], "field_group": group,
                        "status": data["status"], "finite_count": data["finite_count"], "distinct_finite_values_json": json.dumps(data["distinct_finite_values"], separators=(",", ":")),
                        "facts_json": json.dumps(data["facts"], ensure_ascii=False, separators=(",", ":")), "exact_period_unverified": True})
            if ev.get("form") == "10-K/A" and any(ev.get("fields", {}).get(group, {}).get("finite_count", 0) == 0 for group in FLOW_GROUPS) and ev.get("adsh"):
                selected_incomplete_amendment_member_rows.add((month, ticker, ev["adsh"]))
            # Keep a compact per-member record; full raw candidate facts are stored once per filing/group.
            result.setdefault("_compact_evaluations", []).append(compact)
        result["candidate_cik_evaluations_json"] = json.dumps(result.pop("_compact_evaluations", []), ensure_ascii=False, separators=(",", ":"))
        result_rows.append(result)

    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    write_csv(output / "per-filing-candidates.csv", filing_rows)
    field_rows = list(filed_field_rows.values())
    write_csv(output / "field-coverage.csv", field_rows)
    write_csv(output / "monthly-formation-readiness.csv", result_rows)
    write_csv(output / "yearly-formation-funnel.csv", [{"formation_year": year, **dict(counts), "evidence_scope": "upper_bound_unvalidated_identity", "coverage_interpretation": "candidate coverage; not a mathematical bound", "exact_period_unverified": True} for year, counts in sorted(yearly.items())])
    write_csv(output / "calendar-observation-year-funnel.csv", [{"calendar_observation_year": year, **dict(counts), "evidence_scope": "upper_bound_unvalidated_identity", "coverage_interpretation": "candidate coverage; not a mathematical bound", "exact_period_unverified": True} for year, counts in sorted(observation_yearly.items())])
    incomplete_amendments = {adsh for adsh, form in selected_form_by_adsh.items() if form == "10-K/A" and any(selected_field_status.get((adsh, group), {}).get("finite_count", 0) == 0 for group in FLOW_GROUPS)}
    field_counts = Counter(value["status"] for value in selected_field_status.values())
    group_field_counts = Counter((group, value["status"]) for (adsh, group), value in selected_field_status.items())
    early_google_rows = sum(1 for member in monthly_rows if member.get("ticker") in {"GOOG", "GOOGL"} and member.get("month", "") < "2015-10")
    diagnostics = {"exact_period_unverified": True, "evidence_scope": "upper_bound_unvalidated_identity",
                   "coverage_interpretation": "candidate coverage with unverified issuer identity and exact financial period; not a mathematical upper bound because conservative date and mapping exclusions may undercount",
                   "needs_review_multilabel_member_months_by_pattern": dict(known_conflict_member_counts),
                   "GOOG_GOOGL_early_match_risk_before_2015_10_02_member_month_rows": early_google_rows,
                   "multilabel_semantics": "These counts identify rows needing review; they are not proof that every row is a conflict.",
                   "selected_incomplete_10ka_unique_accessions": len(incomplete_amendments),
                   "selected_incomplete_10ka_ticker_month_rows": len(selected_incomplete_amendment_member_rows),
                   "unique_selected_filing_field_status_counts": dict(field_counts),
                   "unique_selected_filing_field_group_status_counts": {f"{group}:{status}": count for (group, status), count in group_field_counts.items()},
                   "conflicting_submission_accessions": len(conflicting_adshs),
                   "date_semantics": "SUB.period, NUM.ddate and qtrs are month-end/whole-quarter rounded; date labels are candidates only; exact periods and cross-year boundaries are unverified."}
    (output / "coverage-diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n")
    return {"filings": len(filing_rows), "monthly_rows": len(result_rows), "field_rows": len(field_rows), "formation_years": len(yearly), "observation_years": len(observation_yearly), "exact_period_unverified": True}


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        path.write_text("\n")
        return
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_bindings(contract: dict, correction_path: Path = CORRECTION):
    for item in contract["input_files"]:
        p = Path(item["path"])
        if sha256_file(p) != item["sha256"]:
            raise ValueError(f"input SHA mismatch: {p}")
    if sha256_file(correction_path) != CORRECTION_SHA256:
        raise ValueError("date correction SHA mismatch")
    correction = json.loads(correction_path.read_text())
    if "rounded to month end" not in correction.get("correction", ""):
        raise ValueError("date correction semantics not bound")
    return correction


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--contract", type=Path, default=HERE / "luna-annual-formation-contract.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        cutoff = cutoff_for("2020-07")
        assert cutoff == dt.date(2020, 6, 30)
        # Synthetic same-accession source rows must remain candidates rather than being silently deduplicated.
        return 0
    if not args.out:
        parser.error("--out required")
    result = run_pipeline(args.contract, args.out)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
