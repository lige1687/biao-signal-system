"""Frozen four-fund N-PORT behavior pilot. Only `prepare`/`synthetic` are authorized initially.

`run` requires a separate controller freeze, source-bound fund-type qualification,
and this exact script hash. Never imports an old factor or uses future returns.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = HERE.parents[4]
CONTRACT_PATH = HERE / "measurement-contract.json"
PLAN_PATH = ROOT / "storage-plan.json"
MANIFEST_PATH = ROOT / "mirror-qualification/request-manifest.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text())
PLAN = json.loads(PLAN_PATH.read_text())
MANIFEST = json.loads(MANIFEST_PATH.read_text())
SERIES = tuple(CONTRACT["series_ids"])
REPORT_DATES = tuple(CONTRACT["report_dates"])
FLOW_FIELDS = tuple(f"{kind}_FLOW_MON{month}" for kind in ("SALES", "REDEMPTION", "REINVESTMENT")
                    for month in (1, 2, 3))
OUT = Path(PLAN["output"]) / "behavior-pilot"
FILES = {item["relative_path"]: item for item in MANIFEST["files"]}
HOLD_COLUMNS = ["ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_CUSIP", "ISSUER_LEI",
                "ISSUER_TITLE", "BALANCE", "UNIT", "CURRENCY_CODE", "CURRENCY_VALUE",
                "ASSET_CAT", "INVESTMENT_COUNTRY", "PAYOFF_PROFILE", "IS_RESTRICTED_SECURITY",
                "FAIR_VALUE_LEVEL", "DERIVATIVE_CAT"]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    os.replace(temporary, path)


def data_path(table, quarter):
    relative = f"{table}/year=2025/quarter={quarter}/data.parquet"
    return Path(FILES[relative]["path"])


def storage_guard():
    mount = Path(PLAN["external_mount"])
    expected = int(PLAN["external_device"])
    if not mount.is_dir() or mount.stat().st_dev != expected:
        raise RuntimeError("fixed external mount unavailable or changed")
    if not Path(PLAN["output"]).is_dir() or Path(PLAN["output"]).stat().st_dev != expected:
        raise RuntimeError("fixed output unavailable or changed")
    if OUT.exists() and OUT.stat().st_dev != expected:
        raise RuntimeError("behavior result path on wrong device")


def source_guard():
    storage_guard()
    expected_tables = {"SUBMISSION", "FUND_REPORTED_INFO", "FUND_REPORTED_HOLDING", "MONTHLY_TOTAL_RETURN"}
    expected = {f"{table}/year=2025/quarter={q}/data.parquet" for table in expected_tables for q in range(1, 5)}
    if MANIFEST["revision"] != CONTRACT["source_revision"] or set(FILES) != expected:
        raise RuntimeError("source revision or 16 fixed file list differs")
    if len(MANIFEST["requests"]) != 16 or MANIFEST["failures"]:
        raise RuntimeError("source request ledger not 16 successful files")
    for relative, item in FILES.items():
        path = Path(item["path"])
        if not path.is_file() or path.stat().st_dev != int(PLAN["external_device"]):
            raise RuntimeError(f"missing or wrong-device source: {relative}")
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"source bytes or SHA changed: {relative}")


def clean_identity(value):
    if value is None:
        return None
    normalized = " ".join(str(value).upper().split())
    return None if normalized in ("", "N/A", "NA", "NONE") else normalized


def identity_conflict(first, second):
    """Conservative within-fund, across-date or within-filing comparison."""
    for field in ("lei", "title"):
        a, b = first.get(field), second.get(field)
        if a is not None and b is not None and a != b:
            return True
    return False


def cross_fund_same_issuer(first, second):
    """Frozen clarification: valid matching LEI overrides vendor title wording."""
    a, b = first.get("lei"), second.get("lei")
    return (isinstance(a, str) and isinstance(b, str) and
            re.fullmatch(r"[A-Z0-9]{20}", a) is not None and a == b)


def finite_positive(value):
    if value is None:
        return False
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError, OverflowError):
        return False


def derivative_missing(value):
    return value is None or str(value).strip().upper() == "N/A"


def check_holding(row):
    rules = {
        "ASSET_CAT": row["ASSET_CAT"] == CONTRACT["eligible_holdings"]["ASSET_CAT"],
        "UNIT": row["UNIT"] == CONTRACT["eligible_holdings"]["UNIT"],
        "CURRENCY_CODE": row["CURRENCY_CODE"] == CONTRACT["eligible_holdings"]["CURRENCY_CODE"],
        "INVESTMENT_COUNTRY": row["INVESTMENT_COUNTRY"] == CONTRACT["eligible_holdings"]["INVESTMENT_COUNTRY"],
        "PAYOFF_PROFILE": row["PAYOFF_PROFILE"] == CONTRACT["eligible_holdings"]["PAYOFF_PROFILE"],
        "IS_RESTRICTED_SECURITY": row["IS_RESTRICTED_SECURITY"] == CONTRACT["eligible_holdings"]["IS_RESTRICTED_SECURITY"],
        "FAIR_VALUE_LEVEL": str(row["FAIR_VALUE_LEVEL"]) == CONTRACT["eligible_holdings"]["FAIR_VALUE_LEVEL"],
        "DERIVATIVE_CAT": derivative_missing(row["DERIVATIVE_CAT"]),
        "BALANCE": finite_positive(row["BALANCE"]),
        "ISSUER_CUSIP": isinstance(row["ISSUER_CUSIP"], str) and
                        re.fullmatch(r"[A-Z0-9]{9}", row["ISSUER_CUSIP"]) is not None,
    }
    return rules


def select_filings():
    selected = collections.defaultdict(list)
    all_accessions = set()
    monthly = collections.Counter()
    for quarter in range(1, 5):
        storage_guard()
        submissions = pq.ParquetFile(data_path("SUBMISSION", quarter)).read().to_pylist()
        info = pq.ParquetFile(data_path("FUND_REPORTED_INFO", quarter)).read().to_pylist()
        by_accession = {}
        for row in submissions:
            accession = row["ACCESSION_NUMBER"]
            if accession in all_accessions:
                raise RuntimeError(f"duplicate accession across source files: {accession}")
            all_accessions.add(accession)
            by_accession[accession] = row
        if len(by_accession) != len(submissions):
            raise RuntimeError(f"duplicate accession in SUBMISSION Q{quarter}")
        seen_info = set()
        for row in info:
            accession = row["ACCESSION_NUMBER"]
            if accession in seen_info or accession not in by_accession:
                raise RuntimeError(f"unmatched or duplicate FUND_REPORTED_INFO accession: {accession}")
            seen_info.add(accession)
            sid = row["SERIES_ID"]
            date = by_accession[accession]["REPORT_DATE"]
            date_string = date.isoformat() if date else None
            if sid in SERIES and date_string in REPORT_DATES:
                selected[(sid, date_string)].append({"series_id": sid, "report_date": date_string,
                    "accession": accession, "source_quarter": quarter,
                    "filing_date": by_accession[accession]["FILING_DATE"].isoformat(),
                    "sub_type": by_accession[accession]["SUB_TYPE"],
                    "series_name": row["SERIES_NAME"], "net_assets": row["NET_ASSETS"],
                    "cash_not_reported": row["CASH_NOT_RPTD_IN_C_OR_D"],
                    "flows": {field: row[field] for field in FLOW_FIELDS}})
        if seen_info != set(by_accession):
            raise RuntimeError(f"SUBMISSION/FUND_REPORTED_INFO mismatch Q{quarter}")
        returns = pq.ParquetFile(data_path("MONTHLY_TOTAL_RETURN", quarter)).read(
            columns=["ACCESSION_NUMBER", "CLASS_ID"]).to_pylist()
        monthly.update(r["ACCESSION_NUMBER"] for r in returns)
    expected_keys = {(sid, date) for sid in SERIES for date in REPORT_DATES}
    if set(selected) != expected_keys or any(len(selected[key]) != 1 for key in expected_keys):
        raise RuntimeError("not exactly one accession for each of the 16 series/report dates")
    chosen = {key: selected[key][0] for key in sorted(expected_keys)}
    if len({v["accession"] for v in chosen.values()}) != 16:
        raise RuntimeError("selected accession not unique")
    if any(v["sub_type"] != "NPORT-P" for v in chosen.values()):
        raise RuntimeError("selected filing is amended or unexpected type")
    if any(not finite_positive(v["net_assets"]) for v in chosen.values()):
        raise RuntimeError("selected net assets unavailable or nonpositive")
    if any(monthly[v["accession"]] == 0 for v in chosen.values()):
        raise RuntimeError("selected accession missing monthly return table row")
    for sid in SERIES:
        for date in REPORT_DATES[1:]:
            current = chosen[(sid, date)]
            if any(current["flows"][field] is None for field in FLOW_FIELDS):
                raise RuntimeError(f"missing flow field: {sid} {date}")
    return chosen, {v["accession"]: monthly[v["accession"]] for v in chosen.values()}


def reduce_holdings(raw):
    """Keep only contract holdings; aggregate compatible duplicate CUSIPs."""
    waterfall = collections.Counter()
    marginal = collections.Counter()
    buckets = collections.defaultdict(list)
    raw_cusips = set()
    for row in raw:
        cusip = row["ISSUER_CUSIP"]
        if isinstance(cusip, str) and re.fullmatch(r"[A-Z0-9]{9}", cusip):
            raw_cusips.add(cusip)
        rules = check_holding(row)
        for field, passed in rules.items():
            if not passed:
                marginal[field] += 1
        first_failed = next((field for field, passed in rules.items() if not passed), None)
        if first_failed is not None:
            waterfall[first_failed] += 1
            continue
        buckets[cusip].append(row)
    valid = {}
    ambiguous = set()
    duplicate_compatible = 0
    for cusip, lines in buckets.items():
        first = {"lei": clean_identity(lines[0]["ISSUER_LEI"]),
                 "title": clean_identity(lines[0]["ISSUER_TITLE"])}
        if any(identity_conflict(first, {"lei": clean_identity(line["ISSUER_LEI"]),
                                         "title": clean_identity(line["ISSUER_TITLE"])}) for line in lines[1:]):
            ambiguous.add(cusip)
            continue
        # Check pairwise as an unknown first LEI/title could hide a conflict.
        known_leis = {clean_identity(line["ISSUER_LEI"]) for line in lines} - {None}
        known_titles = {clean_identity(line["ISSUER_TITLE"]) for line in lines} - {None}
        if len(known_leis) > 1 or len(known_titles) > 1:
            ambiguous.add(cusip)
            continue
        if len(lines) > 1:
            duplicate_compatible += len(lines) - 1
        values = [float(line["CURRENCY_VALUE"]) for line in lines if finite_positive(line["CURRENCY_VALUE"])]
        valid[cusip] = {"quantity": sum(float(line["BALANCE"]) for line in lines),
                        "value": sum(values) if len(values) == len(lines) else None,
                        "lei": next(iter(known_leis), None), "title": next(iter(known_titles), None)}
    return valid, {"raw_rows": len(raw), "raw_identified_cusips": len(raw_cusips),
                   "raw_cusip_set": raw_cusips, "marginal_failures": dict(marginal),
                   "first_failure_waterfall": dict(waterfall),
                   "duplicate_compatible_extra_rows": duplicate_compatible,
                   "ambiguous_duplicate_cusips": sorted(ambiguous),
                   "eligible_cusips": len(valid)}


def scan_selected_holdings(chosen):
    holdings, diagnostics = {}, {}
    for quarter in range(1, 5):
        storage_guard()
        accession_set = {v["accession"] for v in chosen.values() if v["source_quarter"] == quarter}
        selected_raw = collections.defaultdict(list)
        parquet = pq.ParquetFile(data_path("FUND_REPORTED_HOLDING", quarter))
        seek = pa.array(sorted(accession_set))
        for group in range(parquet.num_row_groups):
            storage_guard()
            block = parquet.read_row_group(group, columns=HOLD_COLUMNS)
            filtered = block.filter(pc.is_in(block["ACCESSION_NUMBER"], value_set=seek))
            for row in filtered.to_pylist():
                selected_raw[row["ACCESSION_NUMBER"]].append(row)
        for accession in accession_set:
            if not selected_raw[accession]:
                raise RuntimeError(f"selected accession has no holding rows: {accession}")
            holdings[accession], diagnostics[accession] = reduce_holdings(selected_raw[accession])
    return holdings, diagnostics


def structural_pairs(chosen, holdings, diagnostic):
    output = []
    for sid in SERIES:
        for before, after in zip(REPORT_DATES, REPORT_DATES[1:]):
            a, b = chosen[(sid, before)], chosen[(sid, after)]
            old, new = holdings[a["accession"]], holdings[b["accession"]]
            old_raw = diagnostic[a["accession"]]["raw_cusip_set"]
            new_raw = diagnostic[b["accession"]]["raw_cusip_set"]
            retained = set(old) & set(new)
            compatible = {c for c in retained if not identity_conflict(old[c], new[c])}
            conflicting = retained - compatible
            new_to_observed_list = {c for c in new if c not in old_raw}
            disappeared_from_observed_list = {c for c in old if c not in new_raw}
            changed_eligibility = (set(old) ^ set(new)) - new_to_observed_list - disappeared_from_observed_list
            peer_map = {}
            peer_title_difference_links = 0
            peer_invalid_or_conflicting_lei_links = 0
            for c in compatible:
                peers = []
                for other_sid in SERIES:
                    if other_sid == sid:
                        continue
                    other_a, other_b = chosen[(other_sid, before)], chosen[(other_sid, after)]
                    p0, p1 = holdings[other_a["accession"]].get(c), holdings[other_b["accession"]].get(c)
                    if p0 and p1 and not identity_conflict(p0, p1):
                        if cross_fund_same_issuer(old[c], p0) and cross_fund_same_issuer(new[c], p1):
                            peers.append(other_sid)
                            if old[c]["title"] != p0["title"] or new[c]["title"] != p1["title"]:
                                peer_title_difference_links += 1
                        else:
                            peer_invalid_or_conflicting_lei_links += 1
                if peers:
                    peer_map[c] = peers
            output.append({"series_id": sid, "start_report_date": before, "end_report_date": after,
                           "start_accession": a["accession"], "end_accession": b["accession"],
                           "opening_eligible_cusips": len(old), "ending_eligible_cusips": len(new),
                           "retained_cusips": len(retained), "identity_conflict_cusips": len(conflicting),
                           "retained_identity_compatible_cusips": len(compatible),
                           "new_to_observed_list_cusips_absent_in_prior_raw_filing": len(new_to_observed_list),
                           "disappeared_from_observed_list_cusips_absent_in_current_raw_filing": len(disappeared_from_observed_list),
                           "eligibility_changes_not_raw_entries_or_exits": len(changed_eligibility),
                           "retained_without_peer": len(compatible - set(peer_map)),
                           "matched_same_security_peer_cusips": len(peer_map),
                           "allowed_peer_links_with_title_text_difference": peer_title_difference_links,
                           "rejected_peer_links_invalid_or_conflicting_lei": peer_invalid_or_conflicting_lei_links,
                           "peer_map": peer_map})
    return output


def flow_values(current, previous):
    flows = current["flows"]
    if any(flows[field] is None for field in FLOW_FIELDS):
        raise RuntimeError("flow null is not zero")
    prior_nav = float(previous["net_assets"])
    if not finite_positive(prior_nav):
        raise RuntimeError("prior NAV unavailable")
    sales = sum(float(flows[f"SALES_FLOW_MON{i}"]) for i in (1, 2, 3))
    redemption = sum(float(flows[f"REDEMPTION_FLOW_MON{i}"]) for i in (1, 2, 3))
    reinvestment = sum(float(flows[f"REINVESTMENT_FLOW_MON{i}"]) for i in (1, 2, 3))
    return {"sales_3m": sales, "redemptions_3m": redemption,
            "reinvestment_3m_separate": reinvestment,
            "net_flow_pct_prior_nav": 100 * (sales - redemption) / prior_nav,
            "prior_net_assets": prior_nav}


def relative_change(target, peers):
    own = math.log(target[1] / target[0])
    others = [math.log(new / old) for old, new in peers]
    if not others:
        raise RuntimeError("target lacks other-fund peer")
    peer_mean = sum(others) / len(others)
    return own, peer_mean, own - peer_mean


def qualification_gate(path):
    if path is None:
        raise RuntimeError("fund-type qualification JSON is required")
    doc = json.loads(Path(path).read_text())
    if doc.get("qualified") is not True or doc.get("status") != "passed_for_bounded_descriptive_pilot_only":
        raise RuntimeError("fund-type qualification has no bounded pass")
    if doc.get("series_ids") != list(SERIES) or doc.get("report_dates") != list(REPORT_DATES):
        raise RuntimeError("fund-type qualification does not cover exact series and dates")
    sources = doc.get("sources", [])
    if not sources:
        raise RuntimeError("fund-type source fingerprints absent")
    for item in sources:
        source = Path(item["path"])
        if not source.is_absolute():
            source = REPO / source
        if not source.is_file() or digest(source) != item["sha256"]:
            raise RuntimeError("fund-type source fingerprint mismatch")
    return doc


def freeze_gate(freeze_path, qualification_path):
    if freeze_path is None:
        raise RuntimeError("separate controller freeze JSON is required")
    freeze = json.loads(Path(freeze_path).read_text())
    required = {"run_authorized": True, "script_sha256": digest(__file__),
                "measurement_contract_sha256": digest(CONTRACT_PATH),
                "source_manifest_sha256": digest(MANIFEST_PATH),
                "fund_type_qualification_sha256": digest(qualification_path),
                "source_revision": CONTRACT["source_revision"],
                "output": str(OUT)}
    for key, expected in required.items():
        if freeze.get(key) != expected:
            raise RuntimeError(f"controller freeze missing or mismatched {key}")
    return freeze


def prepare():
    source_guard()
    chosen, monthly = select_filings()
    holdings, diagnostic = scan_selected_holdings(chosen)
    structural = structural_pairs(chosen, holdings, diagnostic)
    if len(structural) != 12:
        raise RuntimeError("not twelve fund-interval rows")
    readable = {}
    for (sid, date), row in chosen.items():
        accession = row["accession"]
        item = diagnostic[accession]
        readable[f"{sid}@{date}"] = {"accession": accession, "source_quarter": row["source_quarter"],
            "filing_date": row["filing_date"], "sub_type": row["sub_type"],
            "series_name_unqualified_type": row["series_name"],
            "net_assets_present_positive": finite_positive(row["net_assets"]),
            "monthly_return_class_rows": monthly[accession],
            "raw_holding_rows": item["raw_rows"], "eligible_cusips": item["eligible_cusips"],
            "marginal_failures": item["marginal_failures"],
            "first_failure_waterfall": item["first_failure_waterfall"],
            "duplicate_compatible_extra_rows": item["duplicate_compatible_extra_rows"],
            "ambiguous_duplicate_cusips": item["ambiguous_duplicate_cusips"]}
    pairs = [{key: value for key, value in row.items() if key != "peer_map"} for row in structural]
    report = {"status": "prepared_no_effects", "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script_sha256": digest(__file__), "measurement_contract_sha256": digest(CONTRACT_PATH),
        "source_manifest_sha256": digest(MANIFEST_PATH), "source_revision": CONTRACT["source_revision"],
        "selected": readable, "fund_intervals": pairs,
        "fund_type_qualification": "not checked; controller review required before run",
        "effect_calculations": 0, "flow_amounts_computed": 0,
        "boundary": "counts only; not a behavior, return or causal result"}
    write_json(HERE / "prepare-status.json", report)
    print(json.dumps({"status": report["status"], "selected_filings": len(readable),
                      "fund_intervals": len(pairs), "matched_peer_counts": [x["matched_same_security_peer_cusips"] for x in pairs],
                      "script_sha256": report["script_sha256"]}))


def synthetic():
    checks = {}
    own, peer, relative = relative_change((10, 20), [(30, 60), (7, 14)])
    checks["common_split_multiplier_cancels"] = math.isclose(relative, 0, abs_tol=1e-12)
    own, peer, relative = relative_change((10, 11), [(10, 12), (10, 9)])
    checks["leave_own_out_peer_mean"] = math.isclose(peer,
        (math.log(1.2) + math.log(0.9)) / 2, abs_tol=1e-12) and not math.isclose(peer,
        (math.log(1.1) + math.log(1.2) + math.log(0.9)) / 3, abs_tol=1e-12)
    mock_filings = {(sid, date): {"accession": f"{sid}-{date}"} for sid in SERIES for date in REPORT_DATES}
    stock = {"quantity": 10.0, "value": 100.0, "lei": "TESTLEI", "title": "TEST CORP"}
    mock_holdings = {item["accession"]: {"123456789": stock.copy()} for item in mock_filings.values()}
    mock_diagnostics = {item["accession"]: {"raw_cusip_set": {"123456789"}} for item in mock_filings.values()}
    missing_accession = mock_filings[(SERIES[0], REPORT_DATES[1])]["accession"]
    mock_holdings[missing_accession] = {}
    mock_diagnostics[missing_accession]["raw_cusip_set"] = set()
    synthetic_pairs = structural_pairs(mock_filings, mock_holdings, mock_diagnostics)
    first_pair = next(x for x in synthetic_pairs if x["series_id"] == SERIES[0] and
                      x["end_report_date"] == REPORT_DATES[1])
    checks["disappearance_not_zero_imputation"] = (first_pair[
        "disappeared_from_observed_list_cusips_absent_in_current_raw_filing"] == 1 and
        first_pair["retained_cusips"] == 0 and not first_pair["peer_map"])
    before = {"net_assets": 100.0}
    current = {"flows": {f"{kind}_FLOW_MON{i}": 0.0 for kind in ("SALES", "REDEMPTION", "REINVESTMENT") for i in (1, 2, 3)}}
    current["flows"].update({"SALES_FLOW_MON1": 4.0, "REDEMPTION_FLOW_MON1": 10.0,
                             "REINVESTMENT_FLOW_MON1": 2.0})
    flow = flow_values(current, before)
    checks["flow_sign_and_separate_reinvestment"] = close(flow["net_flow_pct_prior_nav"], -6) and close(
        flow["reinvestment_3m_separate"], 2)
    current["flows"]["SALES_FLOW_MON2"] = None
    try:
        flow_values(current, before)
        checks["missing_flow_not_zero"] = False
    except RuntimeError:
        checks["missing_flow_not_zero"] = True
    template = {name: None for name in HOLD_COLUMNS}
    template.update({"ACCESSION_NUMBER": "test", "HOLDING_ID": 1, "ISSUER_CUSIP": "123456789",
                     "ISSUER_LEI": "549300TESTTESTTEST12", "ISSUER_TITLE": "ACME INC", "BALANCE": 10,
                     "UNIT": "NS", "CURRENCY_CODE": "USD", "CURRENCY_VALUE": 100,
                     "ASSET_CAT": "EC", "INVESTMENT_COUNTRY": "US", "PAYOFF_PROFILE": "Long",
                     "IS_RESTRICTED_SECURITY": "N", "FAIR_VALUE_LEVEL": "1"})
    second = template | {"HOLDING_ID": 2, "BALANCE": 5, "CURRENCY_VALUE": 50}
    good, info = reduce_holdings([template, second])
    checks["compatible_duplicate_sums"] = close(good["123456789"]["quantity"], 15) and info[
        "duplicate_compatible_extra_rows"] == 1
    conflict, info = reduce_holdings([template, second | {"ISSUER_TITLE": "OTHER COMPANY"}])
    checks["issuer_title_conflict_excluded"] = "123456789" not in conflict
    checks["cross_period_issuer_conflict"] = identity_conflict(
        {"lei": "A", "title": "SAME CORP"}, {"lei": "B", "title": "SAME CORP"})
    lei_a = {"lei": "5493006MHB84DD0ZWV18", "title": "ALPHABET INC-CL A 0.00000000"}
    lei_b = {"lei": "5493006MHB84DD0ZWV18", "title": "ALPHABET INC CL A"}
    checks["same_valid_lei_allows_cross_fund_free_text_title_difference"] = (
        cross_fund_same_issuer(lei_a, lei_b) and identity_conflict(lei_a, lei_b))
    checks["conflicting_valid_lei_rejects_cross_fund_peer"] = not cross_fund_same_issuer(
        lei_a, {"lei": "5493006MHB84DD0ZWV19", "title": lei_a["title"]})
    checks["missing_or_invalid_lei_rejects_cross_fund_peer"] = (
        not cross_fund_same_issuer(lei_a, {"lei": None, "title": lei_a["title"]}) and
        not cross_fund_same_issuer(lei_a, {"lei": "N/A", "title": lei_a["title"]}))
    restricted, info = reduce_holdings([template | {"IS_RESTRICTED_SECURITY": "Y"}])
    checks["new_restriction_filter"] = not restricted and info["marginal_failures"]["IS_RESTRICTED_SECURITY"] == 1
    checks["new_fair_value_derivative_filters"] = (
        not check_holding(template | {"FAIR_VALUE_LEVEL": "2"})["FAIR_VALUE_LEVEL"] and
        not check_holding(template | {"DERIVATIVE_CAT": "OPT"})["DERIVATIVE_CAT"])
    checks["long_literal_from_raw_contract"] = check_holding(template)["PAYOFF_PROFILE"] and not check_holding(
        template | {"PAYOFF_PROFILE": "L"})["PAYOFF_PROFILE"]
    report = {"status": "pass" if all(checks.values()) else "fail",
              "script_sha256": digest(__file__), "measurement_contract_sha256": digest(CONTRACT_PATH),
              "checks": checks, "effects_on_real_data": 0}
    write_json(HERE / "synthetic-check.json", report)
    print(json.dumps(report))
    if report["status"] != "pass":
        raise RuntimeError("synthetic checks failed")


def close(a, b):
    return math.isclose(float(a), float(b), abs_tol=1e-12, rel_tol=1e-12)


def run(qualification_path, freeze_path, expected_script_sha):
    if expected_script_sha is None or expected_script_sha != digest(__file__):
        raise RuntimeError("explicit exact script SHA required")
    qualification_gate(qualification_path)
    freeze_gate(freeze_path, qualification_path)
    source_guard()
    chosen, _ = select_filings()
    holdings, diagnostic = scan_selected_holdings(chosen)
    structural = structural_pairs(chosen, holdings, diagnostic)
    if len(structural) != 12 or any(not row["peer_map"] for row in structural):
        raise RuntimeError("twelve intervals with same-security peers required")
    security_rows = []
    summaries = []
    for row in structural:
        sid, before, after = row["series_id"], row["start_report_date"], row["end_report_date"]
        old = holdings[chosen[(sid, before)]["accession"]]
        new = holdings[chosen[(sid, after)]["accession"]]
        flow = flow_values(chosen[(sid, after)], chosen[(sid, before)])
        for cusip, other_ids in sorted(row["peer_map"].items()):
            peer_pairs = []
            for other in other_ids:
                peer_old = holdings[chosen[(other, before)]["accession"]][cusip]
                peer_new = holdings[chosen[(other, after)]["accession"]][cusip]
                peer_pairs.append((peer_old["quantity"], peer_new["quantity"]))
            own, peer, difference = relative_change((old[cusip]["quantity"], new[cusip]["quantity"]), peer_pairs)
            security_rows.append({"series_id": sid, "start_report_date": before, "end_report_date": after,
                "cusip": cusip, "opening_quantity": old[cusip]["quantity"],
                "ending_quantity": new[cusip]["quantity"], "opening_value": old[cusip]["value"],
                "own_log_quantity_change": own, "peer_count": len(other_ids),
                "peer_series_ids": "|".join(other_ids), "leave_own_out_peer_mean_log_change": peer,
                "relative_log_change": difference})
        local = [x for x in security_rows if x["series_id"] == sid and x["end_report_date"] == after]
        if not local:
            raise RuntimeError("empty matched securities interval")
        mean_own = sum(x["own_log_quantity_change"] for x in local) / len(local)
        mean_peer = sum(x["leave_own_out_peer_mean_log_change"] for x in local) / len(local)
        mean_difference = mean_own - mean_peer
        denominator_values = [h["value"] for h in old.values() if h["value"] is not None]
        matched_values = [old[x["cusip"]]["value"] for x in local if old[x["cusip"]]["value"] is not None]
        denominator = sum(denominator_values)
        prior_nav = float(chosen[(sid, before)]["net_assets"])
        summaries.append({key: value for key, value in row.items() if key != "peer_map"} | flow | {
            "matched_securities": len(local), "raw_own_mean_log_quantity_change": mean_own,
            "leave_own_out_peer_mean_log_quantity_change": mean_peer,
            "mean_relative_log_quantity_change": mean_difference,
            "relative_multiplicative_adjustment": math.expm1(mean_difference),
            "opening_eligible_value_share_matched_with_nonnull_values":
                sum(matched_values) / denominator if denominator > 0 else None,
            "opening_eligible_equity_value_with_nonnull_values": denominator,
            "opening_eligible_equity_value_pct_prior_fund_nav":
                100 * denominator / prior_nav if prior_nav > 0 else None,
            "opening_eligible_value_rows_missing": sum(h["value"] is None for h in old.values()),
            "matched_value_rows_missing": len(local) - len(matched_values)})
    if len(summaries) != 12:
        raise RuntimeError("result not twelve equal-status fund/interval rows")
    storage_guard()
    OUT.mkdir(parents=True, exist_ok=False)
    with (OUT / "security-rows.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(security_rows[0]))
        writer.writeheader()
        writer.writerows(security_rows)
    write_json(OUT / "summary.json", {"status": "bounded_descriptive_behavior_only",
        "source_revision": CONTRACT["source_revision"], "source_manifest_sha256": digest(MANIFEST_PATH),
        "measurement_contract_sha256": digest(CONTRACT_PATH), "script_sha256": digest(__file__),
        "fund_type_qualification_sha256": digest(qualification_path),
        "controller_freeze_sha256": digest(freeze_path), "fund_interval_rows": summaries,
        "security_rows": len(security_rows),
        "scope_note": "INVESTMENT_COUNTRY=US means issuer organization country, not a full US-listed pool; position disappearance from named filing rows is not confirmed sale because miscellaneous disclosure is possible.",
        "not_assessed": ["returns", "reversal", "costs", "causality", "historical public time"]})
    print(json.dumps({"summary": str(OUT / "summary.json"), "security_rows": len(security_rows),
                      "fund_intervals": len(summaries)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "synthetic", "run"])
    parser.add_argument("--fund-type-qualification", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--expected-script-sha")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "synthetic":
        synthetic()
    else:
        run(args.fund_type_qualification, args.freeze, args.expected_script_sha)
