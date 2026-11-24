"""Offline continuation of the immutable fixed-300 focus observation."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from math import ceil, isfinite
from pathlib import Path

from lei_signal.research.fip import SOURCE_FIELDS
from lei_signal.research.high52_revalidation import ADJUSTMENT_FIELDS, adapt_back_adjusted

ROOT = Path(__file__).resolve().parents[3]
OLD_DIR = ROOT / "docs/experiments/raw/focus-stock-momentum-evaluation-2026-10-25"
OPS = ROOT / "docs/ops/focus-live-and-erp-thresholds-20261102/focus-continuation"
INDEX = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity/all-equity-read-index-v8.jsonl")
META = INDEX.with_name("all-equity-read-index-v8-meta.json")
OLD_UNION = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/twenty-year-universe-data-20261025/twenty-year-universe-data-20261025-20261025T154847-f27d39c4e083/result/cn/stock-source-union-v4/actual-date-unions.jsonl")
CALENDAR_PLAN = ROOT / "docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json"
START = "2025-10-01"  # warm-up covers every December 2025 21-session window
OVERLAP_START, OVERLAP_END, END = "2025-12-01", "2025-12-31", "2026-10-23"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked(path: Path, expected: str) -> bytes:
    resolved = path.resolve()
    if not path.is_file() or not (resolved.is_relative_to("/Volumes/win+mac通用") or resolved.is_relative_to(ROOT)):
        raise ValueError(f"source path outside authorized locations: {path}")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"source SHA mismatch: {path}")
    return raw


def source(ref: dict, fields: tuple[str, ...] | list[str], code: str) -> list[list[str]]:
    path = Path(ref.get("source_path") or ref["path"])
    compressed = "compressed_sha256" in ref
    raw = checked(path, ref.get("compressed_sha256") or ref["sha256"])
    body = gzip.decompress(raw) if compressed else raw
    if ref.get("payload_sha256") and hashlib.sha256(body).hexdigest() != ref["payload_sha256"]:
        raise ValueError(f"payload SHA mismatch: {path}")
    payload = json.loads(body)
    rows = payload.get("data")
    if payload.get("error_code") != "0" or payload.get("fields") != list(fields) or not isinstance(rows, list):
        raise ValueError(f"source schema/status mismatch: {path}")
    if len(rows) != ref.get("rows", len(rows)):
        raise ValueError(f"source row count mismatch: {path}")
    previous = ""
    for row in rows:
        if len(row) != len(fields):
            raise ValueError(f"source row width mismatch: {path}")
        identity = row[0] if fields[0] == "code" else row[1]
        if identity != code:
            raise ValueError(f"source identity/width mismatch: {path}")
        day = row[1] if fields[0] == "code" else row[0]
        date.fromisoformat(day)
        if day <= previous:
            raise ValueError(f"source order mismatch: {path}")
        previous = day
    return rows


def merge_rows(code: str, refs: list[dict], fields: tuple[str, ...] | list[str],
               start: str, end: str, audit: Counter, verified: list[dict]) -> list[list[str]]:
    by_day: dict[str, list[str]] = {}
    invalid: set[str] = set()
    seen_files: dict[str, str] = {}
    for ref in refs:
        path = ref.get("source_path") or ref["path"]
        expected = ref.get("compressed_sha256") or ref["sha256"]
        if path in seen_files:
            if seen_files[path] != expected:
                raise ValueError(f"same source path has competing SHA: {path}")
            continue
        seen_files[path] = expected
        rows = source(ref, fields, code)
        audit["source_files_verified"] += 1
        verified.append({"code": code, "kind": "adjustments" if fields[0] == "code" else "daily",
                         "path": path, "sha256": ref.get("compressed_sha256") or ref["sha256"]})
        for row in rows:
            day = row[1] if fields[0] == "code" else row[0]
            if not start <= day <= end or not ref.get("valid_slice_start", day) <= day <= ref.get("valid_slice_end", day):
                continue
            if day in by_day and by_day[day] != row:
                invalid.add(day)
            else:
                by_day[day] = row
    for day in invalid:
        del by_day[day]
    audit["conflict_dates"] += len(invalid)
    if invalid and fields[0] == "code":
        raise ValueError(f"conflicting factor events for {code}: {sorted(invalid)}")
    return [by_day[day] for day in sorted(by_day)]


def stock_windows(adapted: dict, calendar: list[str], code: str, audit: Counter) -> dict[str, dict]:
    """Mirror frozen 21-adjacent-session and mean-amount rules, including zero daily amount."""
    if adapted["research_price_basis"] != "raw_ohlc_times_effective_foreAdjustFactor":
        raise ValueError("wrong research price basis")
    prices = {row["date"]: row for row in adapted["rows"]}
    raw = adapted["raw_by_day"]
    breaks = set(adapted["break_dates"])
    result = {}
    for i in range(20, len(calendar)):
        days = calendar[i - 20:i + 1]
        day = days[-1]
        if any(d not in raw for d in days):
            audit["missing_source_day"] += 1; continue
        if any(d in breaks or d not in prices for d in days):
            audit["adapter_price_break"] += 1; continue
        if any(raw[d]["tradestatus"] != "1" for d in days):
            audit["nontrading_day"] += 1; continue
        if raw[day]["isST"] != "0":
            audit["current_st_or_unknown"] += 1; continue
        closes = [number(prices[d]["close"]) for d in days]
        amounts = [number(raw[d]["amount"]) for d in days[1:]]
        if any(x is None or x <= 0 for x in closes):
            audit["invalid_adjusted_price"] += 1; continue
        if any(x is None or x < 0 for x in amounts):
            audit["missing_or_invalid_amount"] += 1; continue
        mean_amount = sum(amounts) / 20
        if mean_amount <= 0:
            audit["zero_mean_amount"] += 1; continue
        result[day] = {"momentum": closes[-1] / closes[0] - 1,
                       "mean_amount": mean_amount, "current_amount": amounts[-1]}
    return result


def number(value: object) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def observation(day: str, stock: dict[str, dict]) -> dict:
    count = len(stock)
    row = {"date": day, "qualified_count": count, "signal_valid": count >= 100}
    if count < 100:
        return {**row, "focus_count": 0, "focus_members": [],
                **{key: None for key in ("focus", "pool_momentum", "breadth", "concentration", "top1_contribution", "focus_below_zero", "focus_below_zero_numeric")}}
    ranked = sorted(stock, key=lambda code: (-stock[code]["mean_amount"], code))
    selected = ranked[:ceil(0.05 * count)]
    focus_returns = [stock[code]["momentum"] for code in selected]
    all_returns = [stock[code]["momentum"] for code in stock]
    amount_total = sum(stock[code]["mean_amount"] for code in stock)
    abs_total = sum(abs(value) for value in focus_returns)
    focus = sum(focus_returns) / len(selected)
    return {**row, "focus_count": len(selected), "focus_members": selected,
            "focus": focus, "focus_below_zero": focus < 0,
            "focus_below_zero_numeric": int(focus < 0),
            "pool_momentum": sum(all_returns) / count,
            "breadth": sum(value > 0 for value in all_returns) / count,
            "concentration": sum(stock[code]["mean_amount"] for code in selected) / amount_total if amount_total > 0 else None,
            "top1_contribution": max(map(abs, focus_returns)) / abs_total if abs_total else 0.0}


def compare_overlap(rows: list[dict]) -> dict:
    frozen = {}
    with (OLD_DIR / "core-v1/daily_features.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if OVERLAP_START <= row["date"] <= OVERLAP_END:
                frozen[row["date"]] = row
    keys = ("focus", "pool_momentum", "breadth", "concentration", "top1_contribution")
    failures = []
    for row in rows:
        if row["date"] not in frozen:
            continue
        old = frozen[row["date"]]
        for key in ("qualified_count", "focus_count"):
            if row[key] != int(old[key]): failures.append([row["date"], key, old[key], row[key]])
        for key in keys:
            left = None if old[key] == "" else float(old[key])
            right = row[key]
            if left is None and right is None: continue
            if left is None or right is None or abs(left-right) > 1e-12:
                failures.append([row["date"], key, old[key], right])
        if row["focus_members"] != json.loads(old["focus_members"]):
            failures.append([row["date"], "focus_members", "different", "different"])
    days = [r for r in rows if OVERLAP_START <= r["date"] <= OVERLAP_END]
    if set(frozen) != {r["date"] for r in days}:
        failures.append(["overlap", "dates", len(frozen), len(days)])
    return {"matched": not failures, "days_compared": len(days), "failures": failures[:30], "failure_count": len(failures),
            "frozen_sha256": sha(OLD_DIR / "core-v1/daily_features.csv")}


def gap_sources(result_path: Path, codes: set[str], end: str) -> tuple[dict, dict]:
    """Admit only the separately recorded, same-supplier six-session supplement."""
    result = json.loads(result_path.read_text())
    if (result.get("status") != "qualified_raw_available" or result.get("asOfRequested") != end
            or result.get("dailyRange") != ["2026-10-26", end]
            or result.get("factorRange") != ["2026-10-24", end]):
        raise ValueError("gap source qualification/range mismatch")
    ref = result["acquisitionLedger"]
    ledger = json.loads(checked(Path(ref["path"]), ref["sha256"]))
    if ledger.get("fixedManifestSha256") != result["manifestSha256"]:
        raise ValueError("gap manifest mismatch")
    grouped = {code: {} for code in codes}
    for source_ref in ledger["responses"]:
        code, kind = source_ref["code"], source_ref["kind"]
        if code not in grouped or kind not in ("daily", "factor") or kind in grouped[code]:
            raise ValueError("gap source cohort/kind/duplicate mismatch")
        grouped[code][kind] = source_ref
    if any(set(pair) != {"daily", "factor"} for pair in grouped.values()):
        raise ValueError("gap source missing response")
    return grouped, {"resultSha256": sha(result_path), "ledgerSha256": ref["sha256"],
                     "manifestSha256": result["manifestSha256"], "end": end}


def run(output: Path = OPS, *, end: str = END, gap_result: Path | None = None,
        gap_calendar: Path | None = None) -> dict:
    inputs = json.loads((OLD_DIR / "inputs.json").read_text())
    manifest_path = Path(inputs["source_manifest"]["path"])
    manifest = json.loads(checked(manifest_path, inputs["source_manifest"]["sha256"]))
    assets = manifest["asset_sources"]
    if len(assets) != 300 or len(set(assets)) != 300:
        raise ValueError("fixed cohort not 300 unique codes")
    gap, gap_meta = gap_sources(gap_result, set(assets), end) if gap_result else ({}, None)
    if end != END and not gap_result:
        raise ValueError("extending the source date requires a qualified supplement")
    if gap_meta and gap_meta["manifestSha256"] != inputs["source_manifest"]["sha256"]:
        raise ValueError("gap and frozen manifest differ")
    meta = json.loads(META.read_text())
    if sha(INDEX) != meta["index_sha256"]:
        raise ValueError("v8 index SHA mismatch")
    plan = json.loads(CALENDAR_PLAN.read_text())
    cal_ref = plan["baseline"]["calendar"]
    calendar_bytes = checked(Path(cal_ref["path"]), cal_ref["sha256"])
    calendar = [row["trade_date"] for row in csv.DictReader(calendar_bytes.decode().splitlines())
                if START <= row["trade_date"] <= end]
    if gap:
        if not gap_calendar:
            raise ValueError("supplement requires independently qualified calendar")
        supplement = json.loads(gap_calendar.read_text())
        for ref in supplement["sources"]:
            checked(Path(ref["path"]), ref["sha256"])
        sessions = supplement["sessions"]
        if (not supplement["sources"] or sessions != sorted(set(sessions))
                or not sessions or sessions[0] <= calendar[-1] or sessions[-1] != end):
            raise ValueError("gap calendar continuity/range mismatch")
        calendar.extend(sessions)
        gap_meta["calendarSha256"] = sha(gap_calendar)
    if calendar != sorted(set(calendar)) or calendar[-1] != end:
        raise ValueError("calendar coverage/order mismatch")
    wanted = set(assets)
    index = {}
    for line in INDEX.open():
        row = json.loads(line)
        if row["code"] in wanted: index[row["code"]] = row
    if set(index) != wanted:
        raise ValueError("v8 fixed cohort mismatch")
    old = {}
    for line in OLD_UNION.open():
        row = json.loads(line)
        if row.get("code") in wanted: old[row["code"]] = row
    audit = Counter()
    verified: list[dict] = []
    by_day: dict[str, dict[str, dict]] = defaultdict(dict)
    gap_breaks = {}
    for code, pair in sorted(assets.items()):
        v8 = index[code]
        old_refs = old.get(code, {}).get("source_refs", [])
        daily_refs = [pair["daily"], *old_refs, *v8["reused_raw_sources"], *v8["new_price_sources"]]
        # The frozen fixed-300 adjustment vintage owns pre-2026 events. Other
        # old-union factor vintages may rebase historical foreAdjustFactor values.
        factor_refs = [pair["adjustments"], *v8["reused_factor_sources"], *v8["new_factor_sources"]]
        if gap:
            daily_refs.append({**gap[code]["daily"], "valid_slice_start": "2026-10-26"})
            factor_refs.append({**gap[code]["factor"], "valid_slice_start": "2026-10-24"})
        if v8.get("old_union_factor_source") and v8["old_union_factor_source"]["path"] != pair["adjustments"]["path"]:
            audit["alternate_old_factor_vintages_not_merged"] += 1
        raw_daily = merge_rows(code, daily_refs, SOURCE_FIELDS, START, end, audit, verified)
        factors = merge_rows(code, factor_refs, ADJUSTMENT_FIELDS, "1900-01-01", end, audit, verified)
        if not factors:
            audit["stocks_without_factor"] += 1
        adapted = adapt_back_adjusted({"error_code":"0", "fields":list(SOURCE_FIELDS), "data":raw_daily},
                                      {"error_code":"0", "fields":list(ADJUSTMENT_FIELDS), "data":factors},
                                      code, calendar, factor_field="foreAdjustFactor")
        audit["adapter_breaks"] += len(adapted["break_dates"])
        new_breaks = [day for day in adapted["break_dates"] if day > END]
        if new_breaks:
            gap_breaks[code] = sorted(new_breaks)
        partial = stock_windows(adapted, calendar, code, audit)
        for day, values in partial.items(): by_day[day][code] = values
    rows = [observation(day, by_day.get(day, {})) for day in calendar if day >= OVERLAP_START]
    overlap = compare_overlap(rows)
    output.mkdir(parents=True, exist_ok=True)
    review = {"status": "overlap_matched" if overlap["matched"] else "overlap_failed_no_append",
              "fixed_codes": len(assets), "calendar_start": calendar[0], "calendar_end": calendar[-1],
              "manifest_sha256": inputs["source_manifest"]["sha256"], "v8_index_sha256": meta["index_sha256"],
              "old_union_sha256": sha(OLD_UNION), "calendar_sha256": cal_ref["sha256"],
              "adapter_sha256": sha(ROOT / "src/lei_signal/research/high52_revalidation.py"),
              "verified_sources": verified,
              "source_audit": dict(audit), "overlap": overlap,
              "raw_price_basis": "BaoStock adjustflag=3 is unadjusted; apply effective foreAdjustFactor",
              "factor_vintage_rule": "Original fixed-300 manifest owns pre-2026 adjustment events; alternate old-union factor vintages are not merged",
              "source_arrival_and_revision_time": "unknown"}
    if gap_meta:
        review.update({"gap_source": gap_meta, "gap_adapter_breaks": gap_breaks})
    (output / "audit.json").write_text(json.dumps(review, ensure_ascii=False, allow_nan=False, indent=2))
    if not overlap["matched"]:
        return review
    new = [r for r in rows if r["date"] > OVERLAP_END]
    valid = [r for r in new if r["signal_valid"]]
    gaps = [{"date": r["date"], "qualifiedCount": r["qualified_count"], "reason": "fewer_than_100_qualified"}
            for r in new if not r["signal_valid"]]
    if not valid:
        review["status"] = "no_valid_continuation"
        (output / "audit.json").write_text(json.dumps(review, ensure_ascii=False, allow_nan=False, indent=2))
        return review
    point = lambda r: {"date": r["date"], "focus": r["focus"], "poolMomentum": r["pool_momentum"],
                       "breadth": r["breadth"], "concentration": r["concentration"],
                       "qualifiedCount": r["qualified_count"], "focusCount": r["focus_count"],
                       "top1Contribution": r["top1_contribution"]}
    previous = next(r for r in reversed(rows) if r["date"] <= OVERLAP_END and r["signal_valid"])
    latest = valid[-1]
    preceding = valid[-2] if len(valid) > 1 else previous
    frozen = json.loads((ROOT / "web/public/research/focus-momentum/observation.v1.json").read_text())
    payload = {"schemaVersion":1, "definitionId":frozen["definitionId"], "overlapVerified":True,
               "asOf": latest["date"], "historicalAsOf": OVERLAP_END,
               "scope": {"label":"原固定300股离线续接", "sampleSize":300,
                         "selection":"原冻结 source_manifest.asset_sources；无替换"},
               "series":[point(r) for r in valid], "gaps":gaps,
               "latest":{**point(latest), "members":latest["focus_members"],
                         "changeFocus":latest["focus"]-preceding["focus"]},
               "source":{"manifestSha256":inputs["source_manifest"]["sha256"],
                         "v8IndexSha256":meta["index_sha256"], "oldUnionSha256":review["old_union_sha256"],
                         "calendarSha256":cal_ref["sha256"], "sourceFilesVerified":audit["source_files_verified"]},
               "stale":{"latestSourceDate":end, "reason":"dated observation snapshot; not an automatic live feed"}}
    if gap_meta:
        payload["source"]["gapLedgerSha256"] = gap_meta["ledgerSha256"]
        payload["source"]["gapResultSha256"] = gap_meta["resultSha256"]
        payload["source"]["gapCalendarSha256"] = gap_meta["calendarSha256"]
    target = output / "continuation.json"
    text = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(text.encode()) > 2 * 1024 * 1024:
        raise ValueError("continuation exceeds 2 MiB")
    target.write_text(text)
    review.update({"continuation_days":len(valid), "gap_days":len(gaps), "latest":latest["date"],
                   "latest_qualified_count":latest["qualified_count"], "continuation_sha256":sha(target)})
    (output / "audit.json").write_text(json.dumps(review, ensure_ascii=False, allow_nan=False, indent=2))
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OPS)
    parser.add_argument("--end", default=END)
    parser.add_argument("--gap-result", type=Path)
    parser.add_argument("--gap-calendar", type=Path)
    args = parser.parse_args()
    result = run(args.output, end=args.end, gap_result=args.gap_result, gap_calendar=args.gap_calendar)
    print(json.dumps({key: value for key, value in result.items() if key != "verified_sources"}, ensure_ascii=False))
