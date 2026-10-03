#!/usr/bin/env python3
"""Reproduce the bounded, source-only CBOE put/call qualification audit."""
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
INPUTS = BASE / "inputs"
MANIFEST = json.loads((BASE / "source-manifest.json").read_text())
EXPECTED = {Path(x["frozen_path"]).name: x["sha256"] for x in MANIFEST["files"] if x.get("frozen_path")}
FIELDS = ["date", "CALL", "PUT", "TOTAL", "reported_ratio", "ratio_exact"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_file(filename, calls_col, puts_col, outname):
    path = INPUTS / filename
    actual_sha = sha(path)
    if actual_sha != EXPECTED[filename]:
        raise SystemExit(f"source hash drift: {filename}: {actual_sha}")
    raw = path.read_bytes().decode("latin1").splitlines()
    header_line = next(i for i, line in enumerate(raw) if line.startswith("DATE,"))
    rows = list(csv.DictReader(raw[header_line:]))
    date_counts, dates, normalized, problems = Counter(), [], [], []
    reported_diff = []; ratio_deltas=[]
    for line_no, row in enumerate(rows, header_line + 2):
        try:
            date = dt.datetime.strptime(row["DATE"].strip(), "%m/%d/%Y").date()
        except Exception:
            problems.append({"line": line_no, "type": "invalid_date", "row": row})
            continue
        iso = date.isoformat()
        date_counts[iso] += 1
        dates.append(date)
        try:
            call, put, total = (int(row[k].strip()) for k in (calls_col, puts_col, "TOTAL"))
            reported = Decimal(row["P/C Ratio"].strip())
            exact = Decimal(put) / Decimal(call) if call else None
        except (ValueError, KeyError, InvalidOperation) as e:
            problems.append({"line": line_no, "date": iso, "type": "invalid_numeric", "error": str(e), "row": row})
            continue
        if call <= 0 or put < 0 or total < 0:
            problems.append({"line": line_no, "date": iso, "type": "invalid_sign_or_zero_call", "CALL": call, "PUT": put, "TOTAL": total})
        if call + put != total:
            problems.append({"line": line_no, "date": iso, "type": "call_plus_put_mismatch", "CALL": call, "PUT": put, "TOTAL": total, "sum": call + put})
        # Cboe reports two decimals; allow nearest-hundredth rounding (half-up),
        # expressed as an absolute tolerance around the published value.
        delta = abs(reported - exact) if exact is not None else None
        if delta is not None: ratio_deltas.append((delta, iso, reported, exact))
        if delta is not None and delta > Decimal("0.0050000001"):
            reported_diff.append({"date": iso, "reported_ratio": str(reported), "ratio_exact": str(exact), "absolute_delta": str(delta)})
        normalized.append({"date": iso, "CALL": call, "PUT": put, "TOTAL": total,
                           "reported_ratio": str(reported),
                           "ratio_exact": format(exact, ".10f") if exact is not None else ""})
    # Keep every parsable source row, including any duplicates; no dates are synthesized.
    with (HERE / outname).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(normalized)
    counts = Counter(dates)
    duplicates = {d.isoformat(): n for d, n in counts.items() if n > 1}
    ordered = sorted(set(dates))
    gaps = [(a + dt.timedelta(days=1), b - dt.timedelta(days=1)) for a, b in zip(ordered, ordered[1:]) if (b-a).days > 3]
    return {"file": filename, "sha256": actual_sha, "bytes": path.stat().st_size,
            "raw_header": raw[:header_line + 1], "csv_header": raw[header_line],
            "source_rows": len(rows), "normalized_rows": len(normalized),
            "date_min": min(dates).isoformat() if dates else None, "date_max": max(dates).isoformat() if dates else None,
            "unique_dates": len(counts), "duplicate_dates": duplicates,
            "invalid_date_or_numeric_rows": problems, "sum_mismatch_rows": [p for p in problems if p["type"] == "call_plus_put_mismatch"],
            "reported_ratio_outside_rounding_tolerance": reported_diff,
            "max_ratio_abs_difference": str(max((x[0] for x in ratio_deltas), default=Decimal(0))),
            "max_ratio_abs_difference_example": ({"date":max(ratio_deltas)[1],"reported_ratio":str(max(ratio_deltas)[2]),"ratio_exact":str(max(ratio_deltas)[3])} if ratio_deltas else None),
            "calendar_gaps_over_3_days": [{"from": a.isoformat(), "through": b.isoformat(), "calendar_days": (b-a).days+1} for a,b in gaps],
            "dates": [d.isoformat() for d in dates], "normalized_file": outname}


def runs(day_strings, source_order):
    selected=set(day_strings); result=[]; start=prev=None; length=0
    for value in source_order:
        d=dt.date.fromisoformat(value)
        if value in selected:
            if start is None: start=d
            prev=d; length+=1
        elif start is not None:
            result.append({"start": start.isoformat(), "end": prev.isoformat(), "source_observation_count": length})
            start=prev=None; length=0
    if start is not None: result.append({"start": start.isoformat(), "end": prev.isoformat(), "source_observation_count": length})
    return result


def main():
    eq = parse_file("equitypc.csv", "CALL", "PUT", "normalized-equity.csv")
    total = parse_file("totalpc.csv", "CALLS", "PUTS", "normalized-total.csv")
    spy_path=INPUTS/"px_SPY.csv"
    if sha(spy_path) != EXPECTED["px_SPY.csv"]: raise SystemExit("SPY source hash drift")
    spy=[]
    with spy_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            for k in ("date", "Date", "DATE"):
                if row.get(k):
                    try: spy.append(dt.date.fromisoformat(row[k][:10]))
                    except ValueError: pass
                    break
    spyset=set(spy)
    product_results={}
    for name, item in (("equity",eq),("total",total)):
        ds=set(item["dates"])
        periods={}
        source_min=dt.date.fromisoformat(item["date_min"]); source_max=dt.date.fromisoformat(item["date_max"])
        for label,lo,hi in (("pre_2012_06_11",source_min,dt.date(2012,6,10)),("post_2012_06_11_through_2019_10_04",dt.date(2012,6,11),dt.date(2019,10,4))):
            lo=max(lo,source_min); hi=min(hi,source_max)
            selected=sorted(dt.date.fromisoformat(x) for x in ds if (lo is None or dt.date.fromisoformat(x)>=lo) and (hi is None or dt.date.fromisoformat(x)<=hi))
            benchmark_dates=sorted(d for d in spyset if lo<=d<=hi)
            missing=[d.isoformat() for d in benchmark_dates if d.isoformat() not in ds]
            periods[label]={"unique_source_dates":len(selected),"first":selected[0].isoformat() if selected else None,"last":selected[-1].isoformat() if selected else None,
                            "spy_weekday_dates_in_period":len(benchmark_dates),"spy_weekday_dates_missing_from_source_count":len(missing),"spy_weekday_dates_missing_examples":missing[:20],
                            "source_dates_absent_from_spy":sorted(d.isoformat() for d in selected if d not in spyset)}
        over_reported=[]; over_exact=[]; normalized_rows=[]
        normpath=HERE/item["normalized_file"]
        with normpath.open(newline="",encoding="utf-8") as f:
            normalized_rows=list(csv.DictReader(f))
        for row in normalized_rows:
            if Decimal(row["reported_ratio"])>1: over_reported.append(row["date"])
            if Decimal(row["ratio_exact"])>1: over_exact.append(row["date"])
        for label,lo,hi in (("pre_2012_06_11",source_min,dt.date(2012,6,10)),("post_2012_06_11_through_2019_10_04",dt.date(2012,6,11),dt.date(2019,10,4))):
            lo=max(lo,source_min); hi=min(hi,source_max)
            rows=[r for r in normalized_rows if lo<=dt.date.fromisoformat(r["date"])<=hi]
            period_reported=[r["date"] for r in rows if Decimal(r["reported_ratio"])>1]
            period_exact=[r["date"] for r in rows if Decimal(r["ratio_exact"])>1]
            periods[label]["reported_ratio_gt_1_date_count"]=len(period_reported)
            periods[label]["reported_ratio_gt_1_run_count_gap_under_4_days"]=len(runs(period_reported,[r["date"] for r in rows]))
            periods[label]["ratio_exact_gt_1_date_count"]=len(period_exact)
            periods[label]["ratio_exact_gt_1_run_count_gap_under_4_days"]=len(runs(period_exact,[r["date"] for r in rows]))
        product_results[name]={"periods":periods,
            "reported_ratio_gt_1_date_count":len(over_reported),"reported_ratio_gt_1_runs_gap_under_4_days":runs(over_reported,item["dates"]),
            "ratio_exact_gt_1_date_count":len(over_exact),"ratio_exact_gt_1_runs_gap_under_4_days":runs(over_exact,item["dates"])}
    def above_dates(path):
        with (HERE/path).open(newline="",encoding="utf-8") as f:
            return {row["date"] for row in csv.DictReader(f) if Decimal(row["ratio_exact"])>1}
    eq_over=set()
    total_over=set()
    for path, target in ((eq["normalized_file"],eq_over),(total["normalized_file"],total_over)):
        with (HERE/path).open(newline="",encoding="utf-8") as f:
            target.update(row["date"] for row in csv.DictReader(f) if Decimal(row["reported_ratio"])>1)
    out={"scope":"source qualification only; no forward labels or performance results",
         "revision_notes":["audit-v1.json preserves the initial report; it compared date objects to date strings when checking coverage and incorrectly reported missing dates. Corrected in this report.","Original Equity > 1 counts use reported_ratio, matching the source threshold; exact PUT/CALL > 1 is shown separately.","Continuous runs break when adjacent source observations are at least four calendar days apart."],
         "source_policy":{"equity_note":"As of 2012-06-11 Equity includes equity-option products only and excludes exchange-traded products; after 2012-05-31 volume is preliminary reported volume rather than cleared volume.","total_note":"Total is a distinct product aggregate; after 2012-05-31 volume is preliminary reported volume rather than cleared volume.","ratio_tolerance":"reported to two decimals; flag only if absolute error from PUT/CALL exceeds 0.0050000001"},
         "spy_source":{"file":"px_SPY.csv","sha256":sha(spy_path),"rows_with_parseable_date":len(spy),"unique_dates":len(spyset),"date_min":min(spy).isoformat() if spy else None,"date_max":max(spy).isoformat() if spy else None},
         "products":{"equity":eq,"total":total},"coverage_and_extremes":product_results,
         "product_mix_check":{"same_date_ratio_exact_gt_1_count":len(eq_over & total_over),"same_date_examples":sorted(eq_over & total_over)[:20],"basis":"reported_ratio > 1", "interpretation":"descriptive source-mixing check only; Total > 1 is not an authorized threshold"}}
    (HERE/"audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
