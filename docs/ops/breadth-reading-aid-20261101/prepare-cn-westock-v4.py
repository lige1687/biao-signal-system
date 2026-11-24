"""Collect a bounded, review-only WeStock A-share qfq candidate.

This does not calculate breadth, qualify historical membership, or alter live caches.
Each completed batch is immutable; rerunning resumes from its verified receipt.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CODES = Path("/Users/yongbiaoli/.lei_signal_lab/cache/a_share_codes.json")
CLI = ROOT / ".codex/breadth-reading-coordination-20261101/cn-provider-probe-v4/npm-cache/_npx/f124025a92f4edba/node_modules/westock-data-skillhub/scripts/index.js"
OUT = ROOT / ".codex/breadth-reading-coordination-20261101/cn-westock-candidate-v4"
LIMIT = 300
BATCH_SIZE = 20
CUTOFF = "2026-10-30"
TIMEOUT = 45
MIN_FREE = 5 * 1024**3
MAX_OUTPUT = 100 * 1024**2
HEADER = ("symbol", "date", "open", "last", "high", "low", "volume", "amount", "exchange")
TABLE = re.compile(r"^\|\s*((?:sh|sz|bj)\d{6})\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", re.I)
BATCH = re.compile(r"\[Batch\]\s*状态:\s*(\S+)\s*\|\s*总数:\s*(\d+)\s*\|\s*成功:\s*(\d+)\s*\|\s*失败:\s*(\d+)")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, obj: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def disk_guard() -> None:
    stat = os.statvfs(OUT)
    free = stat.f_bavail * stat.f_frsize
    if free < MIN_FREE:
        raise RuntimeError(f"available disk {free} bytes is below 5 GiB reserve")
    used = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    if used >= MAX_OUTPUT:
        raise RuntimeError(f"candidate output {used} bytes reached 100 MiB cap")


def load_codes() -> tuple[list[str], str]:
    raw = CODES.read_bytes()
    obj = json.loads(raw)
    codes = obj["codes"]
    if len(codes) != 5577 or len(set(codes)) != len(codes):
        raise ValueError("expected 5,577 unique current symbols")
    if any(not re.fullmatch(r"(?:sh|sz|bj)\d{6}", c) for c in codes):
        raise ValueError("unexpected symbol format")
    return codes, sha(raw)


def run_cli(symbols: list[str]) -> tuple[bytes, str, float, int | None]:
    cmd = ["node", str(CLI), "kline", ",".join(symbols), "--period", "day", "--limit", str(LIMIT), "--fq", "qfq"]
    start = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=TIMEOUT)
        status = "returned"
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        status = "timeout"
    elapsed = time.monotonic() - start
    # Keep the full provider response while bounding unexpected output.
    if len(stdout) + len(stderr) > 3 * 1024**2:
        raise RuntimeError("batch output exceeded 3 MiB")
    return stdout + (b"\n[stderr]\n" + stderr if stderr else b""), status, elapsed, proc.returncode


def parse(markdown: bytes, requested: list[str]) -> tuple[list[dict], dict]:
    text = markdown.decode("utf-8", errors="replace")
    match = BATCH.search(text)
    advertised = {"status": match.group(1), "total": int(match.group(2)), "success": int(match.group(3)), "failed": int(match.group(4))} if match else None
    rows: list[dict] = []
    counts = Counter()
    reject = Counter()
    seen: set[tuple[str, str]] = set()
    in_table = False
    requested_set = set(requested)
    for line in text.splitlines():
        if line.strip().startswith("| symbol | date | open |"):
            in_table = True
            continue
        if not in_table or not TABLE.match(line):
            continue
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) != len(HEADER):
            reject["bad_columns"] += 1
            continue
        raw = dict(zip(HEADER, cells))
        sym, date = raw["symbol"], raw["date"]
        if sym not in requested_set:
            reject["unexpected_symbol"] += 1
            continue
        if (sym, date) in seen:
            reject["duplicate_symbol_date"] += 1
            continue
        seen.add((sym, date))
        try:
            nums = {k: float(raw[k].replace(",", "")) for k in HEADER[2:]}
        except ValueError:
            reject["bad_number"] += 1
            continue
        if any(not math.isfinite(v) for v in nums.values()):
            reason = "nonfinite_number"
        elif date > CUTOFF:
            reason = "after_cutoff"
        elif any(nums[k] <= 0 for k in ("open", "last", "high", "low")):
            reason = "nonpositive_ohlc_placeholder"
        elif nums["volume"] <= 0 or nums["amount"] <= 0:
            reason = "zero_volume_or_amount"
        elif not nums["low"] <= min(nums["open"], nums["last"]) or not nums["high"] >= max(nums["open"], nums["last"]):
            reason = "invalid_ohlc_order"
        else:
            reason = "candidate"
        counts[reason] += 1
        rows.append({**raw, "numeric": nums, "candidate_valid": reason == "candidate", "exclusion_reason": None if reason == "candidate" else reason})
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append(row)
    for series in by_symbol.values():
        count = 0
        for row in sorted(series, key=lambda x: x["date"]):
            if row["candidate_valid"]:
                count += 1
            row["valid_history_through_date"] = count
            row["sma200_input_ready"] = row["candidate_valid"] and count >= 200
    covered = sorted(by_symbol)
    return rows, {"advertised": advertised, "parsed_rows": len(rows), "covered_symbols": covered, "missing_symbols": sorted(requested_set - set(covered)), "row_reasons": dict(counts), "parse_rejections": dict(reject)}


def write_batch(index: int, symbols: list[str], raw: bytes, rows: list[dict], receipt: dict) -> None:
    stem = f"batch-{index:03d}"
    raw_path = OUT / f"{stem}.md.gz"
    with gzip.open(raw_path, "wb", compresslevel=6) as f:
        f.write(raw)
    receipt.update({"symbols": symbols, "raw_file": raw_path.name, "raw_sha256": sha(raw), "raw_gzip_bytes": raw_path.stat().st_size})
    write_json(OUT / f"{stem}.receipt.json", receipt)


def collect() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    disk_guard()
    if not CLI.is_file():
        raise FileNotFoundError(CLI)
    codes, source_sha = load_codes()
    batches = [codes[i : i + BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)]
    consecutive_failed = 0
    for i, symbols in enumerate(batches):
        receipt_path = OUT / f"batch-{i:03d}.receipt.json"
        if receipt_path.exists():
            old = json.loads(receipt_path.read_text())
            if old.get("symbols") != symbols or old.get("codes_sha256") != source_sha:
                raise RuntimeError(f"batch {i} source identity changed")
            raw = gzip.open(OUT / old["raw_file"], "rb").read()
            if sha(raw) != old["raw_sha256"]:
                raise RuntimeError(f"batch {i} raw fingerprint mismatch")
            continue
        disk_guard()
        attempts = []
        for trial in (1, 2):
            requested_at = now()
            raw, status, seconds, rc = run_cli(symbols)
            rows, parsed = parse(raw, symbols)
            retry_reason = None
            if status == "timeout":
                retry_reason = "process_timeout"
            elif rc != 0:
                retry_reason = "process_error"
            elif parsed["advertised"] is not None and parsed["advertised"]["status"] == "success" and parsed["missing_symbols"]:
                retry_reason = "partial_response_missing_symbols"
            elif parsed["advertised"] is not None and parsed["advertised"]["failed"] > 0:
                retry_reason = "provider_partial_failure"
            temporary = retry_reason is not None
            attempts.append({"trial": trial, "retrieved_at": requested_at, "elapsed_seconds": round(seconds, 3), "process_status": status, "returncode": rc, "provider": parsed["advertised"], "parsed_rows": parsed["parsed_rows"], "missing_symbols": parsed["missing_symbols"], "retry_reason": retry_reason, "raw_sha256": sha(raw)})
            good = status == "returned" and rc == 0 and parsed["advertised"] is not None and parsed["advertised"]["failed"] == 0 and not parsed["missing_symbols"]
            if good or not temporary or trial == 2:
                break
            # A retry retains the unsuccessful original response separately.
            with gzip.open(OUT / f"batch-{i:03d}-attempt-{trial}.md.gz", "wb", compresslevel=6) as f:
                f.write(raw)
            time.sleep(0.25)
        result = "success" if good else "failed"
        receipt = {"batch": i, "codes_sha256": source_sha, "result": result, "attempts": attempts, **parsed}
        write_batch(i, symbols, raw, rows, receipt)
        consecutive_failed = 0 if good else consecutive_failed + 1
        if (i + 1) % 20 == 0 or not good:
            print(json.dumps({"completed_batches": i + 1, "total_batches": len(batches), "batch_result": result, "rows": parsed["parsed_rows"], "consecutive_failed": consecutive_failed}), flush=True)
        if consecutive_failed >= 2:
            print("stop: two consecutive failed batches", flush=True)
            break
        time.sleep(0.25)
    summarize(batches, source_sha)


def summarize(batches: list[list[str]], source_sha: str) -> None:
    receipts = [json.loads(p.read_text()) for p in sorted(OUT.glob("batch-???.receipt.json"))]
    total = Counter()
    symbols_seen: set[str] = set()
    by_symbol: dict[str, dict] = defaultdict(lambda: {"candidate_dates": set(), "all_dates": set(), "reasons": Counter()})
    combined = OUT / "candidate-rows.jsonl.gz"
    with gzip.open(combined, "wt", encoding="utf-8", compresslevel=6) as combined_file:
        for rec in receipts:
            for k, v in rec["row_reasons"].items():
                total[k] += v
            raw = gzip.open(OUT / rec["raw_file"], "rb").read()
            if sha(raw) != rec["raw_sha256"]:
                raise RuntimeError(f"batch {rec['batch']} raw fingerprint mismatch")
            rows, parsed = parse(raw, rec["symbols"])
            if parsed["parsed_rows"] != rec["parsed_rows"]:
                raise RuntimeError(f"batch {rec['batch']} parsed count changed")
            for row in rows:
                line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                combined_file.write(line)
                sym, date = row["symbol"], row["date"]
                symbols_seen.add(sym)
                by_symbol[sym]["all_dates"].add(date)
                by_symbol[sym]["reasons"][row["exclusion_reason"] or "candidate"] += 1
                if row["candidate_valid"]:
                    by_symbol[sym]["candidate_dates"].add(date)
    # Only a descriptive calendar: no fabricated non-trading rows or historical universe.
    calendar = sorted({d for x in by_symbol.values() for d in x["candidate_dates"]})
    recent_calendar = set(calendar[-LIMIT:])
    summary = []
    for sym, x in sorted(by_symbol.items()):
        valid = sorted(x["candidate_dates"])
        summary.append({"symbol": sym, "candidate_valid_count": len(valid), "first_candidate_date": valid[0] if valid else None, "last_candidate_date": valid[-1] if valid else None, "has_200_valid_by_cutoff": len(valid) >= 200, "excluded_rows": {str(k): v for k, v in x["reasons"].items() if k != "candidate"}, "missing_recent_union_dates": sorted(recent_calendar - x["all_dates"])})
    write_json(OUT / "symbol-coverage.json", summary)
    manifest = {"schema": "cn-westock-candidate-v4/1", "created_at": now(), "source_codes": str(CODES), "source_codes_sha256": source_sha, "source_code_count": sum(len(x) for x in batches), "cli": str(CLI), "request": {"batch_size": BATCH_SIZE, "period": "day", "limit": LIMIT, "fq": "qfq", "cutoff": CUTOFF, "timeout_seconds": TIMEOUT}, "completed_batches": len(receipts), "planned_batches": len(batches), "successful_batches": sum(x["result"] == "success" for x in receipts), "failed_batches": [x["batch"] for x in receipts if x["result"] != "success"], "parsed_rows": sum(total.values()), "row_reasons": dict(total), "combined_jsonl_gzip": combined.name, "combined_gzip_bytes": combined.stat().st_size, "combined_gzip_sha256": sha(combined.read_bytes()), "symbols_with_rows": len(symbols_seen), "observed_union_dates": len(calendar), "symbols_with_200_valid_by_cutoff": sum(x["has_200_valid_by_cutoff"] for x in summary), "limits": ["Current 2026-11-02 code list is not historical PIT membership", "300 returned observations include excluded 2026-11-02 rows", "Missing per-symbol dates are not filled", "No live cache or breadth calculation was changed"]}
    write_json(OUT / "manifest.json", manifest)
    print(json.dumps({"manifest": str(OUT / "manifest.json"), "completed_batches": len(receipts), "successful_batches": manifest["successful_batches"], "failed_batches": manifest["failed_batches"], "parsed_rows": manifest["parsed_rows"]}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", action="store_true", help="perform bounded provider calls")
    args = parser.parse_args()
    if not args.collect:
        parser.error("pass --collect after coordination registration")
    collect()


if __name__ == "__main__":
    main()
