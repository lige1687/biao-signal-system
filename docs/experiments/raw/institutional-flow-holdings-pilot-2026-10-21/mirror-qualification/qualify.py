"""Schema/coverage qualification only; no flow, selling, or return relationships."""
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / "delegate-contract.json").read_text())
FILES = json.loads((HERE / "request-manifest.json").read_text())
BY_REL = {x["relative_path"]: Path(x["path"]) for x in FILES["files"]}


def path(table, quarter):
    return BY_REL[f"{table}/year=2025/quarter={quarter}/data.parquet"]


def metadata(table, quarter):
    parquet = pq.ParquetFile(path(table, quarter))
    return {"rows": parquet.metadata.num_rows,
            "columns": parquet.schema_arrow.names,
            "schema": {field.name: str(field.type) for field in parquet.schema_arrow}}


report = {"status": "structural_only", "dataset": "trader298/sec-nport",
          "revision": CONTRACT["data_revision"], "source_filing_year": 2025,
          "source_quarters": [1, 2, 3, 4],
          "files_completed": len(FILES["files"]), "requests_started": len(FILES["requests"]),
          "failures": len(FILES["failures"]), "bytes_completed": FILES["bytes_completed"],
          "tables": {}, "identity": {}, "fields": {}, "periods": {},
          "warnings": ["source filing quarter is not economic report quarter",
                       "series LEI is not unique to a fund/series; N/A is a literal string",
                       "no proven active/passive or ETF classification in these four tables",
                       "amendments and repeated filings need accession-level vintage resolution",
                       "null flow/cash is missing, not zero; CASH_NOT_RPTD_IN_C_OR_D is partial cash",
                       "holding balance is not corporate-action-adjusted trading quantity",
                       "structural availability does not qualify public release time or test a mechanism"]}

frames = []
for q in range(1, 5):
    sm = metadata("SUBMISSION", q)
    fm = metadata("FUND_REPORTED_INFO", q)
    report["tables"][f"SUBMISSION_Q{q}"] = sm
    report["tables"][f"FUND_REPORTED_INFO_Q{q}"] = fm
    a = pq.read_table(path("SUBMISSION", q)).to_pandas()
    b = pq.read_table(path("FUND_REPORTED_INFO", q)).to_pandas()
    joined = a.merge(b, on="ACCESSION_NUMBER", how="outer", validate="one_to_one", indicator=True)
    report["periods"][f"filing_Q{q}"] = {
        "submission_rows": len(a), "fund_info_rows": len(b),
        "accession_join": {str(k): int(v) for k, v in joined["_merge"].value_counts().items()},
        "filing_date_first": str(a["FILING_DATE"].min()), "filing_date_last": str(a["FILING_DATE"].max()),
        "report_date_first": str(a["REPORT_DATE"].min()), "report_date_last": str(a["REPORT_DATE"].max()),
        "report_month_counts": {str(k): int(v) for k, v in a["REPORT_DATE"].astype(str).str[:7].value_counts().sort_index().items()},
        "subtype_counts": {str(k): int(v) for k, v in a["SUB_TYPE"].value_counts(dropna=False).items()},
        "net_assets_nonpositive_rows": int((b["NET_ASSETS"] <= 0).sum()),
        "partial_cash_negative_rows": int((b["CASH_NOT_RPTD_IN_C_OR_D"] < 0).sum()),
        "partial_cash_zero_rows": int((b["CASH_NOT_RPTD_IN_C_OR_D"] == 0).sum()),
    }
    for field in ("SERIES_ID", "SERIES_LEI", "NET_ASSETS", "TOTAL_ASSETS",
                  "CASH_NOT_RPTD_IN_C_OR_D") + tuple(
        f"{prefix}_FLOW_MON{i}" for prefix in ("SALES", "REINVESTMENT", "REDEMPTION") for i in (1, 2, 3)
    ):
        report["fields"].setdefault(field, {})[f"Q{q}"] = {
            "non_null": int(b[field].notna().sum()), "null": int(b[field].isna().sum())}
    joined["source_quarter"] = q
    frames.append(joined.drop(columns=["_merge"]))

all_funds = pd.concat(frames, ignore_index=True)
sid = all_funds["SERIES_ID"].astype(str).str.fullmatch(r"S\d{9}")
lei = all_funds["SERIES_LEI"].astype(str).str.fullmatch(r"[A-Z0-9]{20}")
report["identity"].update({
    "accession_rows": len(all_funds), "accession_unique": int(all_funds["ACCESSION_NUMBER"].nunique()),
    "series_id_valid_rows": int(sid.sum()), "series_id_invalid_or_null_rows": int((~sid).sum()),
    "series_lei_format_valid_rows": int(lei.sum()), "series_lei_invalid_rows": int((~lei).sum()),
    "series_lei_na_literal_rows": int((all_funds["SERIES_LEI"] == "N/A").sum()),
    "valid_series_id_unique": int(all_funds.loc[sid, "SERIES_ID"].nunique()),
    "series_lei_with_multiple_valid_series_ids": int(
        (all_funds.loc[sid & lei].groupby("SERIES_LEI")["SERIES_ID"].nunique() > 1).sum()),
})
valid = all_funds.loc[sid].copy()
duplicate = valid.groupby(["SERIES_ID", "REPORT_DATE"]).agg(
    rows=("ACCESSION_NUMBER", "size"), series_names=("SERIES_NAME", "nunique"))
report["identity"]["valid_id_report_date_duplicate_groups"] = int((duplicate.rows > 1).sum())
report["identity"]["valid_id_report_date_extra_rows"] = int((duplicate.rows - 1).sum())
report["identity"]["duplicate_groups_with_multiple_series_names"] = int(
    ((duplicate.rows > 1) & (duplicate.series_names > 1)).sum())
deduped = valid.sort_values(["SERIES_ID", "REPORT_DATE", "FILING_DATE", "ACCESSION_NUMBER"]).drop_duplicates(
    ["SERIES_ID", "REPORT_DATE"], keep="last").copy()
deduped["previous_report_date"] = deduped.groupby("SERIES_ID")["REPORT_DATE"].shift()
deduped["gap_days"] = (pd.to_datetime(deduped.REPORT_DATE) -
                       pd.to_datetime(deduped.previous_report_date)).dt.days
quarter_pairs = deduped[deduped.gap_days.between(89, 92)]
report["identity"].update({"unique_valid_series_id_report_date": len(deduped),
                            "consecutive_89_92day_pairs_structural_only": len(quarter_pairs),
                            "series_ids_in_those_pairs": int(quarter_pairs.SERIES_ID.nunique()),
                            "qualification_note": "latest filing date is a count-only tie rule, not confirmed final amendment"})

for table in ("FUND_REPORTED_HOLDING", "MONTHLY_TOTAL_RETURN"):
    if any(f"{table}/year=2025/quarter={q}/data.parquet" not in BY_REL for q in range(1, 5)):
        continue
    for q in range(1, 5):
        report["tables"][f"{table}_Q{q}"] = metadata(table, q)

if all(f"FUND_REPORTED_HOLDING/year=2025/quarter={q}/data.parquet" in BY_REL for q in range(1, 5)):
    report["holdings_structure"] = {}
    all_holding_accessions = set()
    all_ec_accessions = set()
    for q in range(1, 5):
        parquet = pq.ParquetFile(path("FUND_REPORTED_HOLDING", q))
        asset_cats = collections.Counter()
        units = collections.Counter()
        currencies = collections.Counter()
        accession_ids = set()
        ec_accession_ids = set()
        valid_cusip = 0
        ec_valid_cusip = 0
        ec_balance_nonnull = 0
        ec_unit_shares = 0
        ec_rows = 0
        for group in range(parquet.num_row_groups):
            frame = parquet.read_row_group(group, columns=["ACCESSION_NUMBER", "ASSET_CAT",
                "ISSUER_CUSIP", "BALANCE", "UNIT", "CURRENCY_CODE"]).to_pandas()
            asset_cats.update({str(k): int(v) for k, v in frame.ASSET_CAT.value_counts(dropna=False).items()})
            units.update({str(k): int(v) for k, v in frame.UNIT.value_counts(dropna=False).items()})
            currencies.update({str(k): int(v) for k, v in frame.CURRENCY_CODE.value_counts(dropna=False).items()})
            accession_ids.update(frame.ACCESSION_NUMBER.dropna().unique())
            ec = frame[frame.ASSET_CAT == "EC"]
            ec_rows += len(ec)
            ec_accession_ids.update(ec.ACCESSION_NUMBER.dropna().unique())
            ec_balance_nonnull += int(ec.BALANCE.notna().sum())
            ec_unit_shares += int((ec.UNIT == "NS").sum())
            valid_cusip += int(frame.ISSUER_CUSIP.astype(str).str.fullmatch(r"[A-Z0-9]{9}").sum())
            ec_valid_cusip += int(ec.ISSUER_CUSIP.astype(str).str.fullmatch(r"[A-Z0-9]{9}").sum())
        fund_accessions = set(frames[q - 1].ACCESSION_NUMBER)
        all_holding_accessions.update(accession_ids)
        all_ec_accessions.update(ec_accession_ids)
        report["holdings_structure"][f"Q{q}"] = {
            "rows": parquet.metadata.num_rows, "accessions_with_any_holding": len(accession_ids),
            "accessions_missing_from_fund_info": len(accession_ids - fund_accessions),
            "fund_info_accessions_without_holding": len(fund_accessions - accession_ids),
            "asset_category_counts": dict(asset_cats), "unit_counts": dict(units),
            "currency_counts": dict(currencies),
            "ec_equity_common_rows": ec_rows, "ec_accessions": len(ec_accession_ids),
            "ec_balance_nonnull": ec_balance_nonnull, "ec_unit_ns_rows": ec_unit_shares,
            "nine_alphanumeric_cusip_rows_all_categories": valid_cusip,
            "nine_alphanumeric_cusip_rows_ec": ec_valid_cusip,
            "cusip_warning": "pattern only; not full issuer identity or corporate-action-adjusted security key",
        }

if all(f"MONTHLY_TOTAL_RETURN/year=2025/quarter={q}/data.parquet" in BY_REL for q in range(1, 5)):
    report["monthly_return_structure"] = {}
    all_return_accessions = set()
    for q in range(1, 5):
        table = pq.ParquetFile(path("MONTHLY_TOTAL_RETURN", q)).read()
        frame = table.to_pandas()
        accession_ids = set(frame.ACCESSION_NUMBER.dropna().unique())
        all_return_accessions.update(accession_ids)
        fund_accessions = set(frames[q - 1].ACCESSION_NUMBER)
        report["monthly_return_structure"][f"Q{q}"] = {
            "rows": len(frame), "accessions": len(accession_ids),
            "accessions_missing_from_fund_info": len(accession_ids - fund_accessions),
            "fund_info_accessions_without_return_row": len(fund_accessions - accession_ids),
            "field_non_null": {name: int(frame[name].notna().sum()) for name in frame.columns},
        }

if "holdings_structure" in report and "monthly_return_structure" in report:
    deduped["previous_accession"] = deduped.groupby("SERIES_ID")["ACCESSION_NUMBER"].shift()
    deduped["previous_cash"] = deduped.groupby("SERIES_ID")["CASH_NOT_RPTD_IN_C_OR_D"].shift()
    pair = deduped[deduped.gap_days.between(89, 92)].copy()
    flow_fields = [f"{prefix}_FLOW_MON{i}" for prefix in ("SALES", "REINVESTMENT", "REDEMPTION")
                   for i in (1, 2, 3)]
    both_holding = pair.ACCESSION_NUMBER.isin(all_holding_accessions) & pair.previous_accession.isin(all_holding_accessions)
    both_ec = pair.ACCESSION_NUMBER.isin(all_ec_accessions) & pair.previous_accession.isin(all_ec_accessions)
    has_return = pair.ACCESSION_NUMBER.isin(all_return_accessions) & pair.previous_accession.isin(all_return_accessions)
    complete_current_flows = pair[flow_fields].notna().all(axis=1)
    prior_cash_present = pair.previous_cash.notna()
    report["paired_period_structure"] = {
        "base_valid_id_89_92day_pairs": len(pair),
        "both_filings_any_holdings": int(both_holding.sum()),
        "both_filings_any_ec_equity_common": int(both_ec.sum()),
        "both_filings_monthly_return_rows": int(has_return.sum()),
        "current_filing_all_nine_flow_fields_non_null": int(complete_current_flows.sum()),
        "previous_filing_partial_cash_field_non_null": int(prior_cash_present.sum()),
        "all_conditions_before_identity_vintage_security_checks": int((both_ec & has_return & complete_current_flows & prior_cash_present).sum()),
        "warning": "duplicate amendments are only count-deduped; no active/passive classification, security identity, corporate actions or historical release qualification",
    }

(HERE / "schema-coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"files": report["files_completed"], "requests": report["requests_started"],
                  "identity": report["identity"],
                  "tables": {k: v["rows"] for k, v in report["tables"].items()}}, ensure_ascii=False))
