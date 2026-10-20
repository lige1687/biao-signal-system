#!/usr/bin/env python3
"""Extract a narrow SEC FSDS annual filing/presentation/fact qualification set."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import plistlib
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Callable, TextIO


SUBMISSION_FIELDS = ["adsh", "cik", "name", "sic", "period", "fy", "fp", "filed", "accepted"]
FORM_SET = {"10-K", "10-K/A"}
STATEMENT_SET = {"IS", "BS"}
OUTPUTS = ("annual-submissions.csv", "presentation.csv", "statement-facts.csv", "qualification.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv_member(zf: zipfile.ZipFile, member: str):
    stream = zf.open(member, "r")
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text, delimiter="\t")
    if not reader.fieldnames:
        text.close()
        raise ValueError(f"empty CSV/TSV member: {member}")
    return text, reader


def csv_writer(stream: TextIO, fields: list[str]) -> csv.DictWriter:
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    return writer


class MemoryDuplicateTracker:
    """Small synthetic-test tracker; real extraction uses a disk-backed index."""
    def __init__(self):
        self.rows: dict[tuple[str, ...], list[str]] = {}

    def add(self, row: dict[str, str]) -> None:
        key = tuple(row.get(k, "") for k in ("adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg"))
        self.rows.setdefault(key, []).append(row.get("value", ""))

    def summary(self) -> dict[str, int]:
        groups = [values for values in self.rows.values() if len(values) > 1]
        return {
            "duplicate_groups": len(groups),
            "duplicate_extra_rows": sum(len(values) - 1 for values in groups),
            "conflicting_value_groups": sum(len(set(values)) > 1 for values in groups),
        }


class SQLiteDuplicateTracker:
    """Disk-backed aggregate index; keeps the 443 MB NUM source out of memory."""
    def __init__(self, path: Path):
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=OFF")
        self.db.execute("PRAGMA synchronous=OFF")
        self.db.execute("PRAGMA cache_size=-32768")
        self.db.execute("CREATE TABLE groups (k TEXT PRIMARY KEY, n INTEGER NOT NULL, first_value TEXT NOT NULL, conflict INTEGER NOT NULL)")
        self.pending = 0

    def add(self, row: dict[str, str]) -> None:
        fields = ("adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg")
        key = json.dumps([row.get(k, "") for k in fields], ensure_ascii=False, separators=(",", ":"))
        value = row.get("value", "")
        self.db.execute(
            "INSERT INTO groups(k,n,first_value,conflict) VALUES(?,1,?,0) "
            "ON CONFLICT(k) DO UPDATE SET n=n+1, conflict=MAX(conflict, CASE WHEN first_value != excluded.first_value THEN 1 ELSE 0 END)",
            (key, value),
        )
        self.pending += 1
        if self.pending >= 10000:
            self.db.commit()
            self.pending = 0

    def summary(self) -> dict[str, int]:
        self.db.commit()
        groups, extras, conflicts = self.db.execute(
            "SELECT SUM(CASE WHEN n>1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN n>1 THEN n-1 ELSE 0 END), SUM(conflict) FROM groups"
        ).fetchone()
        return {
            "duplicate_groups": int(groups or 0),
            "duplicate_extra_rows": int(extras or 0),
            "conflicting_value_groups": int(conflicts or 0),
        }

    def close(self) -> None:
        self.db.close()


def extract_archive(zf: zipfile.ZipFile, output_open: Callable[[str], TextIO], duplicate_tracker) -> dict:
    infos = {info.filename: info for info in zf.infolist()}
    for required in ("sub.txt", "pre.txt", "num.txt"):
        if required not in infos:
            raise ValueError(f"missing FSDS member: {required}")
    structure = {name: {"uncompressed_bytes": infos[name].file_size, "compressed_bytes": infos[name].compress_size} for name in ("sub.txt", "pre.txt", "num.txt")}
    counts: Counter[str] = Counter()
    forms: Counter[str] = Counter()
    adshs: set[str] = set()

    with ExitStack() as stack:
        out_sub = stack.enter_context(output_open("annual-submissions.csv"))
        sub_src, sub_reader = read_csv_member(zf, "sub.txt")
        stack.callback(sub_src.close)
        sub_header = list(sub_reader.fieldnames or [])
        missing = set(SUBMISSION_FIELDS + ["form"]) - set(sub_header)
        if missing:
            raise ValueError(f"sub.txt missing fields: {sorted(missing)}")
        sub_writer = csv_writer(out_sub, SUBMISSION_FIELDS)
        for row in sub_reader:
            counts["sub_rows_scanned"] += 1
            form = row.get("form", "")
            if form not in FORM_SET:
                continue
            adsh = row.get("adsh", "")
            if not adsh:
                counts["selected_submissions_missing_adsh"] += 1
                continue
            adshs.add(adsh)
            forms[form] += 1
            counts["selected_submissions"] += 1
            sub_writer.writerow({field: row.get(field, "") for field in SUBMISSION_FIELDS})
        structure["sub.txt"] = {"uncompressed_bytes": infos["sub.txt"].file_size, "compressed_bytes": infos["sub.txt"].compress_size, "header": sub_header}

        out_pre = stack.enter_context(output_open("presentation.csv"))
        pre_src, pre_reader = read_csv_member(zf, "pre.txt")
        stack.callback(pre_src.close)
        pre_header = list(pre_reader.fieldnames or [])
        required_pre = {"adsh", "stmt", "tag", "version"}
        if not required_pre.issubset(pre_header):
            raise ValueError(f"pre.txt missing fields: {sorted(required_pre - set(pre_header))}")
        pre_writer = csv_writer(out_pre, pre_header)
        tag_versions: set[tuple[str, str, str]] = set()
        for row in pre_reader:
            counts["pre_rows_scanned"] += 1
            if row.get("adsh", "") not in adshs or row.get("stmt", "") not in STATEMENT_SET:
                continue
            counts["pre_main_is_bs_rows"] += 1
            pre_writer.writerow(row)
            tag_versions.add((row.get("adsh", ""), row.get("tag", ""), row.get("version", "")))
        structure["pre.txt"] = {"uncompressed_bytes": infos["pre.txt"].file_size, "compressed_bytes": infos["pre.txt"].compress_size, "header": pre_header}

        out_num = stack.enter_context(output_open("statement-facts.csv"))
        num_src, num_reader = read_csv_member(zf, "num.txt")
        stack.callback(num_src.close)
        num_header = list(num_reader.fieldnames or [])
        required_num = {"adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value"}
        if not required_num.issubset(num_header):
            raise ValueError(f"num.txt missing fields: {sorted(required_num - set(num_header))}")
        num_writer = csv_writer(out_num, num_header)
        for row in num_reader:
            counts["num_rows_scanned"] += 1
            key = (row.get("adsh", ""), row.get("tag", ""), row.get("version", ""))
            if key not in tag_versions:
                counts["num_rows_without_selected_is_bs_presentation_match"] += 1
                continue
            counts["num_rows_matched_selected_presentation"] += 1
            fails = []
            if row.get("uom", "") != "USD":
                counts["excluded_non_usd"] += 1
                fails.append("uom")
            if row.get("qtrs", "") not in {"0", "4"}:
                counts["excluded_qtrs_not_0_or_4"] += 1
                fails.append("qtrs")
            if row.get("segments", "") != "":
                counts["excluded_nonempty_segments"] += 1
                fails.append("segments")
            if row.get("coreg", "") != "":
                counts["excluded_nonempty_coreg"] += 1
                fails.append("coreg")
            if fails:
                counts["excluded_union"] += 1
                continue
            num_writer.writerow(row)
            duplicate_tracker.add(row)
            counts["retained_statement_fact_rows"] += 1
        structure["num.txt"] = {"uncompressed_bytes": infos["num.txt"].file_size, "compressed_bytes": infos["num.txt"].compress_size, "header": num_header}

    return {
        "counts": dict(counts),
        "selected_form_counts": dict(forms),
        "selected_accession_count": len(adshs),
        "presentation_tag_version_key_count": len(tag_versions),
        "duplicate_audit": duplicate_tracker.summary(),
        "source_table_structure": structure,
        "policies": {
            "forms": sorted(FORM_SET),
            "presentation_statements": sorted(STATEMENT_SET),
            "join_key": ["adsh", "tag", "version"],
            "fact_filter": {"uom": "USD", "qtrs": ["0", "4"], "segments": "empty", "coreg": "empty"},
            "dates": "all ddate values preserved as source strings; no fiscal-period backfill or date inference",
            "duplicates": "original rows are retained; no values are summed or collapsed",
        },
    }


def verify_external_storage(mount: Path, expected_device: int, expected_uuid: str, required_free: int) -> dict:
    if not mount.is_dir():
        raise RuntimeError(f"external mount unavailable: {mount}")
    st = mount.stat()
    if st.st_dev != expected_device:
        raise RuntimeError(f"unexpected external device: {st.st_dev} != {expected_device}")
    proc = subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)], capture_output=True, check=True, timeout=15)
    info = plistlib.loads(proc.stdout)
    actual_uuid = info.get("VolumeUUID")
    if actual_uuid != expected_uuid:
        raise RuntimeError(f"external UUID mismatch: {actual_uuid} != {expected_uuid}")
    free = shutil.disk_usage(mount).free
    if free < required_free:
        raise RuntimeError(f"insufficient external capacity: {free} < {required_free}")
    return {"mount": str(mount), "device": st.st_dev, "uuid": actual_uuid, "free_bytes": free}


def run_job(job_path: Path, script_path: Path) -> dict:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    source = Path(job["inputs"][0]["path"])
    output = Path(job["output"])
    plan_path = job_path.with_name("storage-plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if len(job.get("inputs", [])) != 1:
        raise ValueError("this extractor accepts exactly the frozen ZIP input")
    if source.exists() is False:
        raise FileNotFoundError(source)
    actual_source_sha = sha256_file(source)
    if actual_source_sha != job["inputs"][0]["sha256"]:
        raise RuntimeError("SEC FSDS ZIP fingerprint mismatch")
    storage_before = verify_external_storage(Path(plan["external_mount"]), plan["external_device"], plan["external_uuid"], plan["external_reserve_bytes"] + plan["estimated_bytes"])
    if output.exists():
        raise FileExistsError(f"create-only output already exists: {output}")
    if output.parent.stat().st_dev != plan["external_device"]:
        raise RuntimeError("output parent is not on the planned external device")
    output.mkdir()

    names = {"annual-submissions.csv", "presentation.csv", "statement-facts.csv"}
    def output_open(name: str):
        if name not in names:
            raise ValueError(f"unexpected output: {name}")
        return (output / name).open("x", encoding="utf-8", newline="")

    index_path = output / ".duplicate-index.sqlite3"
    tracker = SQLiteDuplicateTracker(index_path)
    try:
        with zipfile.ZipFile(source) as zf:
            facts = extract_archive(zf, output_open, tracker)
    finally:
        tracker.close()
        if index_path.exists():
            index_path.unlink()

    table_hashes = {}
    for name in ("annual-submissions.csv", "presentation.csv", "statement-facts.csv"):
        p = output / name
        table_hashes[name] = {"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size}
    with zipfile.ZipFile(source) as zf:
        archive_member_count = len(zf.infolist())
        archive_uncompressed_bytes = sum(info.file_size for info in zf.infolist())
    facts["schema"] = "sec-fsds-annual-qualification/1"
    facts["source"] = {
        "path": str(source), "sha256": actual_source_sha, "bytes": source.stat().st_size,
        "archive_member_count": archive_member_count,
        "archive_uncompressed_bytes": archive_uncompressed_bytes,
        "retrieval_and_data_vintage": "fixed supplied 2014 Q1 SEC Financial Statement Data Set; no later data fetched",
    }
    facts["output_tables"] = table_hashes
    facts["limitations"] = [
        "This is a source qualification extract, not an operating-profitability calculation or factor result.",
        "XBRL tags are preserved verbatim; no cross-tag equivalence, missing-value substitution, or duplicate summation is performed.",
        "Filing filed/accepted strings are retained without timezone inference; filing date alone is not a point-in-time availability decision.",
    ]
    qualification = output / "qualification.json"
    with qualification.open("x", encoding="utf-8") as stream:
        json.dump(facts, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    storage_after = verify_external_storage(Path(plan["external_mount"]), plan["external_device"], plan["external_uuid"], plan["external_reserve_bytes"])
    result = {
        "status": "completed_source_qualification_only",
        "job_path": str(job_path), "job_sha256": sha256_file(job_path),
        "script_path": str(script_path), "script_sha256": sha256_file(script_path),
        "storage_plan_path": str(plan_path), "storage_plan_sha256": sha256_file(plan_path),
        "source_sha256_verified": actual_source_sha,
        "storage_before": storage_before, "storage_after": storage_after,
        "output_directory": str(output),
        "outputs": {name: {"sha256": sha256_file(output / name), "bytes": (output / name).stat().st_size} for name in OUTPUTS},
        "retained_rows": facts["counts"].get("retained_statement_fact_rows", 0),
        "submission_rows": facts["counts"].get("selected_submissions", 0),
        "presentation_rows": facts["counts"].get("pre_main_is_bs_rows", 0),
        "duplicate_audit": facts["duplicate_audit"],
        "scratch_index_removed": True,
        "calculated_factor_or_return_statistics": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", default=str(Path(__file__).with_name("fsds-qualification-job.json")))
    args = parser.parse_args()
    receipt_path = Path(__file__).with_name("fsds-development-receipt.json")
    if receipt_path.exists():
        print(f"receipt already exists: {receipt_path}", file=sys.stderr)
        return 2
    try:
        result = run_job(Path(args.job), Path(__file__))
        receipt = {"schema": "fsds-extraction-development-receipt/1", **result}
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps(receipt, ensure_ascii=False))
        return 0
    except Exception as exc:
        failure = {
            "schema": "fsds-extraction-development-receipt/1", "status": "failed",
            "error_type": type(exc).__name__, "error": str(exc),
            "job_path": str(Path(args.job)), "job_sha256": sha256_file(Path(args.job)),
            "script_path": str(Path(__file__)), "script_sha256": sha256_file(Path(__file__)),
        }
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(failure, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
