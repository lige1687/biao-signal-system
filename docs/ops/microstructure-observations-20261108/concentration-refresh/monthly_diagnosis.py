"""Read-only diagnosis of frozen BaoStock monthly concentration gaps.

Run from any directory with python3 this_file.py. Only writes its two sibling
diagnostic artifacts; every source object is verified before it contributes.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import plistlib
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE.parents[2] / "experiments/raw/douyin-observation-models-overlap-2026-10-31/implementation-v2/concentration/compute-v2.py"
DETAIL = HERE / "monthly-gap-detail.json"
REPORT = HERE / "monthly-diagnosis.md"


def load_core():
    spec = importlib.util.spec_from_file_location("frozen_concentration_compute", CORE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def period_rows(core):
    coverage_path = core.REPO / "docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json"
    coverage = json.loads(coverage_path.read_text())
    calendar_ref = coverage["baseline"]["calendar"]
    calendar_path = Path(calendar_ref["path"])
    if core.digest(calendar_path) != calendar_ref["sha256"] or calendar_ref["sha256"] != core.SPEC["inputs"]["h00300_calendar_sha256"]:
        raise RuntimeError("calendar source SHA conflict")
    with calendar_path.open() as stream:
        dates = [row["trade_date"] for row in csv.DictReader(stream) if core.FIRST <= row["trade_date"][:7] <= core.LAST]
    return dates


def main():
    core = load_core()
    info = subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(core.MOUNT)], capture_output=True, check=True).stdout
    if plistlib.loads(info).get("VolumeUUID") != core.SPEC["inputs"]["external_volume_uuid"]:
        raise RuntimeError("external volume UUID conflict")
    meta = json.loads(core.META.read_text())
    index = Path(meta["index_path"])
    if core.digest(core.META) != core.SPEC["inputs"]["v8_meta_sha256"] or core.digest(index) != core.SPEC["inputs"]["v8_index_sha256"] or core.digest(core.OLD) != core.SPEC["inputs"]["old_union_sha256"]:
        raise RuntimeError("frozen index or old union SHA conflict")
    if core.digest(Path(meta["missing_dates_path"])) != meta["missing_dates_sha256"]:
        raise RuntimeError("missing-date ledger SHA conflict")
    dates = period_rows(core)
    calendar = set(dates)
    month_days = defaultdict(list)
    for day in dates:
        month_days[day[:7]].append(day)
    frozen = json.loads((core.HERE / "monthly.json").read_text())
    old_iter = core.iter_jsonl(core.OLD)
    old_row = next(old_iter, None)
    files_verified = 0
    compressed_verified = 0
    selected = 0
    gap_records = []
    invalid_rows = []
    conflicts = []
    by_month = Counter()
    raw_bytes = 0
    for item in core.iter_jsonl(index):
        code = item["code"]
        while old_row is not None and old_row["code"] < code:
            old_row = next(old_iter, None)
        previous = old_row if old_row is not None and old_row["code"] == code else None
        if not code.startswith(tuple(core.SPEC["codes"])):
            continue
        selected += 1
        ipo, out = item["supplier_ipo"], item["supplier_out"]
        if not ipo:
            continue
        refs = ([(ref, False) for ref in previous["source_refs"]] if previous else [])
        refs += [(ref, False) for ref in item["reused_raw_sources"]]
        refs += [(ref, True) for ref in item["new_price_sources"]]
        observed = {}
        source_spans = []
        seen = set()
        for ref, compressed in refs:
            path = str(ref.get("source_path") or ref["path"])
            if path in seen:
                continue
            seen.add(path)
            source_path = Path(path)
            rows = core.source_rows(ref, compressed)
            files_verified += 1
            compressed_verified += int(compressed)
            raw_bytes += source_path.stat().st_size
            first = ref.get("valid_slice_start") or ref.get("first")
            last = ref.get("valid_slice_end") or ref.get("last")
            if first and last:
                source_spans.append((first, last))
            for offset, row in enumerate(rows):
                day = row[0]
                month = day[:7]
                if month < core.FIRST or month > core.LAST or not ref.get("valid_slice_start", day) <= day <= ref.get("valid_slice_end", day):
                    continue
                reason = None
                if row[1] != code or row[9] != "3" or not ipo <= day or (out and day > out):
                    reason = "code/adjustflag/lifecycle mismatch"
                else:
                    amount, volume = core.number(row[8]), core.number(row[7])
                    status = row[10]
                    if status == "0":
                        if (row[8] not in ("", "0", "0.0", "0.0000") and amount != 0) or (row[7] not in ("", "0", "0.0", "0.0000") and volume != 0):
                            reason = "status0 with nonzero amount/volume"
                        amount, volume = Decimal(0), Decimal(0)
                    elif status == "1":
                        if amount is None or volume is None or amount < 0 or volume < 0 or ((amount == 0) != (volume == 0)):
                            reason = "invalid trading amount/volume"
                    else:
                        reason = "invalid trade status"
                if reason:
                    counted = month in month_days and any(ipo <= candidate and (not out or candidate <= out) for candidate in month_days[month])
                    invalid_rows.append({"code": code, "date": day, "source": path, "rowIndex": offset, "reason": reason,
                                         "countedInFrozenMonth": counted, "row": row})
                    continue
                payload = (amount, volume, status)
                if day in observed:
                    if observed[day] != payload:
                        conflicts.append({"code": code, "date": day, "source": path, "rowIndex": offset})
                    continue
                observed[day] = payload
        expected = [day for day in dates if ipo <= day and (not out or day <= out)]
        missing = [day for day in expected if day not in observed]
        if missing:
            outside = [day for day in missing if not any(first <= day <= last for first, last in source_spans)]
            inside = [day for day in missing if day not in set(outside)]
            exit_days = [day for day in missing if out and day == out]
            for day in missing:
                by_month[day[:7]] += 1
            gap_records.append({"code": code, "supplierIpo": ipo, "supplierOut": out,
                                "missingCount": len(missing), "firstMissing": missing[0], "lastMissing": missing[-1],
                                "missingDates": missing, "outsideSavedSourceSpan": len(outside),
                                "insideSavedSourceSpan": len(inside), "missingExitDate": exit_days,
                                "affectedMonths": sorted({day[:7] for day in missing}),
                                "minimumSingleRange": {"start": missing[0], "end": missing[-1]}})
    frozen_month_missing = {row["month"]: row["missing_days"] for row in frozen["points"]}
    if any(by_month[month] != amount for month, amount in frozen_month_missing.items()):
        raise RuntimeError("reconstructed per-month gaps differ from frozen monthly.json")
    frozen_invalid = sum(row["countedInFrozenMonth"] for row in invalid_rows)
    frozen_invalid_expected = sum(row["invalid_rows"] for row in frozen["points"])
    if sum(by_month.values()) != 4906 or frozen_invalid != frozen_invalid_expected or files_verified != 12587:
        raise RuntimeError(f"expected scan profile changed: files={files_verified}, missing={sum(by_month.values())}, frozen-invalid={frozen_invalid}, raw-invalid={len(invalid_rows)}")
    output = {"qualification": "read-only full raw SHA/schema scan; original frozen result unchanged",
              "sourceFingerprints": {"meta": core.digest(core.META), "index": core.digest(index),
                                     "oldUnion": core.digest(core.OLD), "missingLedger": core.digest(Path(meta["missing_dates_path"])),
                                     "monthly": core.digest(core.HERE / "monthly.json")},
              "selectedCodes": selected, "verifiedRawFiles": files_verified, "verifiedCompressedFiles": compressed_verified,
              "rawBytesRead": raw_bytes, "missingStockDays": sum(by_month.values()), "affectedCodes": len(gap_records),
              "minimumSingleRangeRequests": len(gap_records), "frozenInvalidRows": frozen_invalid,
              "invalidRows": invalid_rows, "contentConflicts": conflicts,
              "missingByMonth": dict(sorted(by_month.items())), "requests": gap_records}
    encoded = json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(encoded.encode()) >= 1024 * 1024:
        raise RuntimeError("diagnostic JSON exceeds 1 MiB local cap")
    DETAIL.write_text(encoded)
    span_days = sum((len(row["missingDates"]) for row in gap_records))
    estimate = math.ceil(span_days * 170)
    REPORT.write_text(
        f"# 月频成交额集中度缺口诊断\n\n原件完整扫描 {files_verified} 件，其中压缩件 {compressed_verified} 件，读取 {raw_bytes:,} 字节；全部逐件核 SHA、响应结构和字段。"
        f"与封存 `monthly.json` 逐月缺行一致：{sum(by_month.values())} 个上市期股票日、{len(gap_records)} 只股票、{frozen_invalid} 条计入封存月份的异常行（raw另有{len(invalid_rows)-frozen_invalid}条不计入）、{len(conflicts)} 条冲突。\n\n"
        f"若每股一个起止日期查询，**理论最少 {len(gap_records)} 请求**；精确清单和缺日见 `monthly-gap-detail.json`。仅缺日返回的粗体积按170字节/行约 {estimate:,} 字节，单区间回收既有行会更大，且仍需核供应商端上市/退出日期。"
        f"日期在已保存源有效区间外与区间内分别为 {sum(x['outsideSavedSourceSpan'] for x in gap_records)}、{sum(x['insideSavedSourceSpan'] for x in gap_records)}；缺退出当天 {sum(len(x['missingExitDate']) for x in gap_records)} 行。"
        "这里的区间仅按保存ref的有效切片或首末返回日判断，不能证明旧请求参数是否覆盖该日。\n\n"
        "本次没有联网、补源、重算收益或修改封存产物；缺日期不自动填零，单次补采未必可恢复所有异常行。"
        f"诊断JSON大小 {len(encoded.encode()):,} 字节。\n"
    )
    print(json.dumps({k: output[k] for k in ("selectedCodes", "verifiedRawFiles", "rawBytesRead", "missingStockDays", "affectedCodes", "minimumSingleRangeRequests")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
