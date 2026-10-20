import datetime as dt
import csv
import hashlib
import json
import tempfile
from pathlib import Path

from annual_formation_coverage import (
    cutoff_for,
    field_candidates,
    rounded_date_candidates,
    select_filing,
    summarize_member_month,
)


def test_cutoff_convention():
    assert cutoff_for("2020-01") == dt.date(2019, 6, 30)
    assert cutoff_for("2020-06") == dt.date(2019, 6, 30)
    assert cutoff_for("2020-07") == dt.date(2020, 6, 30)


def test_rounded_date_candidate_and_two_day_period_gap():
    sub = {"period": "2020-06-30"}
    facts = [
        {"stmt": "IS", "qtrs": "4", "uom": "USD", "segments": "", "coreg": "", "ddate": "20200702"},
    ]
    result = rounded_date_candidates(sub, facts)
    assert result["rounded_date_candidate"] == ["2020-07-02"]
    assert result["offset_days"] == 2
    assert result["exact_period_unverified"] is True
    assert result["retrieval_scope"] == "registered_metadata_only"


def test_latest_accessible_filing_only_and_no_amendment_lookahead():
    original = {"adsh": "orig", "cik": "1", "form": "10-K", "period": "2019-12-31", "accepted": "2020-06-28 12:00:00.0"}
    late_amendment = {"adsh": "amend", "cik": "1", "form": "10-K/A", "period": "2019-12-31", "accepted": "2020-07-01 12:00:00.0"}
    dates = {
        "orig": {"rounded_date_candidate": ["2019-12-31"], "status": "within_7_days_rounded_date_candidate"},
        "amend": {"rounded_date_candidate": ["2019-12-31"], "status": "within_7_days_rounded_date_candidate"},
    }
    chosen, status = select_filing([original, late_amendment], dates, dt.date(2020, 6, 30), 2019)
    assert status == "candidate_filing_asof_cutoff"
    assert chosen["adsh"] == "orig"

    pres = {("amend", "Revenues", "us-gaap"): "IS"}
    facts = {"amend": [{"tag": "Revenues", "version": "us-gaap", "ddate": "20191231", "qtrs": "4", "uom": "USD", "segments": "", "coreg": "", "value": ""}]}
    values = field_candidates("amend", ["2019-12-31"], pres, facts)
    assert values["equity"]["status"] == "missing"
    assert values["revenue"]["status"] == "only_nonfinite_or_blank"
    assert values["revenue"]["distinct_finite_values"] == []
    later, status = select_filing([original, late_amendment], dates, dt.date(2020, 7, 3), 2019)
    assert status == "candidate_filing_asof_cutoff" and later["adsh"] == "amend"
    # The incomplete amendment stays incomplete; the original's fields are not imported.
    original_facts = {"orig": [{"tag": "StockholdersEquity", "version": "us-gaap", "ddate": "20191231", "qtrs": "0", "uom": "USD", "segments": "", "coreg": "", "value": "99"}]}
    old_equity = field_candidates("orig", ["2019-12-31"], {("orig", "StockholdersEquity", "us-gaap"): "BS"}, original_facts)
    assert old_equity["equity"]["finite_count"] == 1
    assert values["equity"]["finite_count"] == 0


def test_non_december_year_end_is_candidate_year_not_fiscal_identity():
    sub = {"adsh": "fy", "cik": "9", "form": "10-K", "period": "2021-06-30", "accepted": "2021-08-01 12:00:00.0"}
    dates = {"fy": {"rounded_date_candidate": ["2021-06-30"], "status": "within_7_days_rounded_date_candidate"}}
    selected, status = select_filing([sub], dates, dt.date(2022, 6, 30), 2021)
    assert status == "candidate_filing_asof_cutoff"
    assert selected["adsh"] == "fy"


def test_same_cik_share_class_rows_not_collapsed():
    sub = {"adsh": "filing", "cik": "7", "form": "10-K", "accepted": "2020-06-28 12:00:00.0"}
    dates = {"filing": {"rounded_date_candidate": ["2019-12-31"]}}
    result_a = summarize_member_month("2020-07", "AAA", ["7"], {"7": [sub]}, dates, {"filing": []}, {})
    result_b = summarize_member_month("2020-07", "AAA.A", ["7"], {"7": [sub]}, dates, {"filing": []}, {})
    assert result_a["ticker"] == "AAA"
    assert result_b["ticker"] == "AAA.A"
    assert len(result_a["candidate_cik_evaluations"]) == len(result_b["candidate_cik_evaluations"]) == 1
    assert result_a["evidence_scope"] == "upper_bound_unvalidated_identity"


def test_outside_or_multiple_rounded_dates_do_not_supply_fields():
    from annual_formation_coverage import summarize_member_month
    sub = {"adsh": "old", "cik": "1", "form": "10-K", "period": "2019-12-31", "accepted": "2020-02-01 12:00:00.0"}
    dates = {"old": {"rounded_date_candidate": ["2018-12-31"], "status": "outside_7_days"}}
    facts = {"old": [{"tag": "Revenues", "version": "us-gaap", "ddate": "20181231", "qtrs": "4", "uom": "USD", "segments": "", "coreg": "", "value": "100"}]}
    presentation = {("old", "Revenues", "us-gaap"): "IS"}
    result = summarize_member_month("2020-07", "T", ["1"], {"1": [sub]}, dates, facts, presentation)
    row = result["candidate_cik_evaluations"][0]
    assert row["raw_rounded_date_candidates"] == ["2018-12-31"]
    assert row["rounded_date_candidate"] == []
    assert row["fields"]["revenue"]["status"] == "missing"
    dates["old"] = {"rounded_date_candidate": ["2019-12-31", "2020-01-01"], "status": "within_7_days_rounded_date_candidate"}
    result = summarize_member_month("2020-07", "T", ["1"], {"1": [sub]}, dates, facts, presentation)
    row = result["candidate_cik_evaluations"][0]
    assert row["raw_rounded_date_candidates"] == ["2019-12-31", "2020-01-01"]
    assert row["rounded_date_candidate"] == []
    assert row["fields"]["revenue"]["status"] == "missing"


def test_real_pipeline_entry_synthetic_files():
    from annual_formation_coverage import run_pipeline

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        entries = []

        def write_table(folder, name, fields, rows):
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / name
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            entries.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return path

        sub_fields = ["adsh", "cik", "form", "period", "fy", "fp", "filed", "accepted", "source_zip"]
        pre_fields = ["adsh", "stmt", "tag", "version", "source_zip"]
        num_fields = ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value", "source_zip"]
        monthly_fields = ["month", "quote_date", "ticker", "interval_id", "interval_start", "interval_end_exclusive", "status", "candidate_record_count", "candidate_ciks", "candidate_symbols", "candidate_evidence_json"]
        main = root / "main"
        write_table(main, "submissions.csv", sub_fields, [
            {"adsh": "orig", "cik": "1", "form": "10-K", "period": "2019-12-31", "fy": "2019", "fp": "FY", "filed": "2020-02-01", "accepted": "2020-02-01 12:00:00.0", "source_zip": "s1"},
            {"adsh": "amend", "cik": "1", "form": "10-K/A", "period": "2019-12-31", "fy": "2019", "fp": "FY", "filed": "2020-06-28", "accepted": "2020-06-28 12:00:00.0", "source_zip": "s1"},
            {"adsh": "late", "cik": "1", "form": "10-K/A", "period": "2019-12-31", "fy": "2019", "fp": "FY", "filed": "2020-07-01", "accepted": "2020-07-01 12:00:00.0", "source_zip": "s1"},
            {"adsh": "conflict", "cik": "2", "form": "10-K", "period": "2019-12-31", "fy": "2019", "fp": "FY", "filed": "2020-02-01", "accepted": "2020-02-01 12:00:00.0", "source_zip": "s1"},
            {"adsh": "blank", "cik": "3", "form": "10-K", "period": "2019-12-31", "fy": "2019", "fp": "FY", "filed": "2020-02-01", "accepted": "2020-02-01 12:00:00.0", "source_zip": "s1"},
        ])
        pred = root / "pred"
        write_table(pred, "submissions.csv", sub_fields, [
            {"adsh": "conflict", "cik": "22", "form": "10-K", "period": "2019-12-31", "fy": "2019", "fp": "FY", "filed": "2020-02-01", "accepted": "2020-02-01 12:00:00.0", "source_zip": "s2"},
        ])
        warm = root / "warm"
        write_table(warm, "submissions.csv", sub_fields, [])
        for folder in (pred, warm):
            write_table(folder, "presentation.csv", pre_fields, [])
        write_table(main, "presentation.csv", pre_fields, [
            {"adsh": "orig", "stmt": "IS", "tag": "Revenues", "version": "us-gaap", "source_zip": "s1"},
            {"adsh": "blank", "stmt": "IS", "tag": "Revenues", "version": "us-gaap", "source_zip": "s1"},
        ])
        for folder in (pred, warm):
            write_table(folder, "statement-facts.csv", num_fields, [])
        write_table(main, "statement-facts.csv", num_fields, [
            {"adsh": "orig", "tag": "Revenues", "version": "us-gaap", "ddate": "20191231", "qtrs": "4", "uom": "USD", "segments": "", "coreg": "", "value": "123", "source_zip": "s1"},
            {"adsh": "blank", "tag": "Revenues", "version": "us-gaap", "ddate": "20191231", "qtrs": "4", "uom": "USD", "segments": "", "coreg": "", "value": "", "source_zip": "s1"},
        ])
        monthly = root / "monthly"
        write_table(monthly, "monthly-identity-candidates.csv", monthly_fields, [
            {"month": "2020-07", "quote_date": "2020-07-31", "ticker": "T1", "interval_id": "1", "interval_start": "", "interval_end_exclusive": "", "status": "exact", "candidate_record_count": "1", "candidate_ciks": "1", "candidate_symbols": "T1", "candidate_evidence_json": "[]"},
            {"month": "2020-07", "quote_date": "2020-07-31", "ticker": "T1.A", "interval_id": "2", "interval_start": "", "interval_end_exclusive": "", "status": "exact", "candidate_record_count": "1", "candidate_ciks": "1", "candidate_symbols": "T1.A", "candidate_evidence_json": "[]"},
            {"month": "2020-07", "quote_date": "2020-07-31", "ticker": "T2", "interval_id": "3", "interval_start": "", "interval_end_exclusive": "", "status": "exact", "candidate_record_count": "1", "candidate_ciks": "2", "candidate_symbols": "T2", "candidate_evidence_json": "[]"},
            {"month": "2020-07", "quote_date": "2020-07-31", "ticker": "T3", "interval_id": "4", "interval_start": "", "interval_end_exclusive": "", "status": "exact", "candidate_record_count": "1", "candidate_ciks": "3", "candidate_symbols": "T3", "candidate_evidence_json": "[]"},
        ])
        tags = root / "tags.json"
        tags.write_text("{}")
        entries.append({"path": str(tags), "sha256": hashlib.sha256(tags.read_bytes()).hexdigest()})
        audit = root / "identity-controller-audit.json"
        audit.write_text(json.dumps({"multi_label_patterns": {}}))
        entries.append({"path": str(audit), "sha256": hashlib.sha256(audit.read_bytes()).hexdigest()})
        output = root / "result"
        contract = {"input_files": entries, "write_paths": [str(output)]}
        contract_path = root / "contract.json"
        contract_path.write_text(json.dumps(contract))
        result = run_pipeline(contract_path, output)
        assert result["monthly_rows"] == 4
        with (output / "monthly-formation-readiness.csv").open(encoding="utf-8", newline="") as stream:
            rows = {row["ticker"]: row for row in csv.DictReader(stream)}
        t1 = json.loads(rows["T1"]["candidate_cik_evaluations_json"])[0]
        assert t1["adsh"] == "amend"  # Latest as-of amendment selected despite absent flow facts.
        assert t1["field_groups"]["revenue"]["status"] == "missing"  # No borrowing original's 123.
        assert rows["T1"]["ticker"] != rows["T1.A"]["ticker"]
        t2 = json.loads(rows["T2"]["candidate_cik_evaluations_json"])[0]
        assert t2["status"] == "conflicting_submission_rows"
        t3 = json.loads(rows["T3"]["candidate_cik_evaluations_json"])[0]
        assert t3["field_groups"]["revenue"]["status"] == "only_nonfinite_or_blank"
