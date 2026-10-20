#!/usr/bin/env python3
"""Stream SEC FSDS ZIPs into a candidate-CIK, filing-version-preserving panel.

This is a source extractor only. It does not choose annual values, resolve XBRL
tag equivalence, calculate operating profitability, or calculate returns.
"""
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
from typing import TextIO


FORM_SET = {"10-K", "10-K/A"}
STATEMENT_SET = {"IS", "BS"}
TABLES = {"sub": "submissions.csv", "pre": "presentation.csv", "num": "statement-facts.csv"}
SUB_REQUIRED = {"adsh", "cik", "form", "period", "fy", "fp", "filed", "accepted"}
PRE_REQUIRED = {"adsh", "stmt", "tag", "version"}
NUM_REQUIRED = {"adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value"}
DUP_KEY = ("adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(zf: zipfile.ZipFile, member: str):
    text = io.TextIOWrapper(zf.open(member, "r"), encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text, delimiter="\t")
    if not reader.fieldnames:
        text.close()
        raise ValueError(f"empty FSDS member: {member}")
    return text, reader


def canonical_cik(value: str | int) -> str:
    text = str(value).strip()
    if not text.isdigit():
        raise ValueError(f"invalid CIK: {value!r}")
    return str(int(text))


class PanelWriters:
    """Create-only table writers; source schemas must stay stable across ZIPs."""
    def __init__(self, output: Path):
        self.output = output
        self.headers: dict[str, list[str]] = {}
        self.files: dict[str, TextIO] = {}
        self.writers: dict[str, csv.DictWriter] = {}

    def write(self, table: str, source_header: list[str], row: dict[str, str], source_zip: str) -> None:
        if table not in TABLES:
            raise ValueError(f"unknown table: {table}")
        header = list(source_header)
        if "source_zip" in header:
            raise ValueError(f"source table unexpectedly contains reserved field source_zip: {table}")
        if table not in self.headers:
            self.headers[table] = header
            path = self.output / TABLES[table]
            stream = path.open("x", encoding="utf-8", newline="")
            self.files[table] = stream
            self.writers[table] = csv.DictWriter(
                stream, fieldnames=header + ["source_zip"], extrasaction="raise", lineterminator="\n"
            )
            self.writers[table].writeheader()
        elif self.headers[table] != header:
            raise ValueError(f"source schema changed across ZIPs for {table}")
        output_row = {field: row.get(field, "") for field in header}
        output_row["source_zip"] = source_zip
        self.writers[table].writerow(output_row)

    def close(self) -> None:
        for stream in self.files.values():
            stream.close()


class DuplicateTracker:
    """Disk-backed duplicate summaries; all original rows remain in CSV output."""
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=OFF")
        self.db.execute("PRAGMA synchronous=OFF")
        self.db.execute("PRAGMA cache_size=-8192")
        self.db.execute("CREATE TABLE local_rows (source TEXT NOT NULL, k TEXT NOT NULL, n INTEGER NOT NULL, first_value TEXT NOT NULL, conflict INTEGER NOT NULL, PRIMARY KEY(source,k))")
        self.db.execute("CREATE TABLE global_rows (k TEXT PRIMARY KEY, n INTEGER NOT NULL, first_value TEXT NOT NULL, conflict INTEGER NOT NULL, sources TEXT NOT NULL)")
        self.pending = 0

    @staticmethod
    def _key(row: dict[str, str]) -> str:
        return json.dumps([row.get(field, "") for field in DUP_KEY], ensure_ascii=False, separators=(",", ":"))

    def add(self, source: str, row: dict[str, str]) -> None:
        key, value = self._key(row), row.get("value", "")
        self.db.execute(
            "INSERT INTO local_rows VALUES(?,?,1,?,0) ON CONFLICT(source,k) DO UPDATE SET n=n+1, conflict=MAX(conflict, CASE WHEN first_value != excluded.first_value THEN 1 ELSE 0 END)",
            (source, key, value),
        )
        self.db.execute(
            "INSERT INTO global_rows VALUES(?,1,?,0,?) ON CONFLICT(k) DO UPDATE SET n=n+1, conflict=MAX(conflict, CASE WHEN first_value != excluded.first_value THEN 1 ELSE 0 END), sources=CASE WHEN instr('|'||sources||'|','|'||excluded.sources||'|')=0 THEN sources||'|'||excluded.sources ELSE sources END",
            (key, value, source),
        )
        self.pending += 1
        if self.pending >= 5000:
            self.db.commit()
            self.pending = 0

    def _counts(self, table: str) -> dict[str, int]:
        groups, extras, conflicts = self.db.execute(
            f"SELECT SUM(CASE WHEN n>1 THEN 1 ELSE 0 END), SUM(CASE WHEN n>1 THEN n-1 ELSE 0 END), SUM(conflict) FROM {table}"
        ).fetchone()
        return {"duplicate_groups": int(groups or 0), "duplicate_extra_rows": int(extras or 0), "conflicting_value_groups": int(conflicts or 0)}

    def summary(self) -> dict:
        self.db.commit()
        local = {source: self._counts_for_source(source) for (source,) in self.db.execute("SELECT DISTINCT source FROM local_rows")}
        cross = self.db.execute("SELECT COUNT(*) FROM global_rows WHERE instr(sources,'|')>0").fetchone()[0]
        return {"within_source": local, "across_all_sources": self._counts("global_rows"), "keys_seen_in_multiple_sources": int(cross)}

    def _counts_for_source(self, source: str) -> dict[str, int]:
        groups, extras, conflicts = self.db.execute(
            "SELECT SUM(CASE WHEN n>1 THEN 1 ELSE 0 END), SUM(CASE WHEN n>1 THEN n-1 ELSE 0 END), SUM(conflict) FROM local_rows WHERE source=?", (source,)
        ).fetchone()
        return {"duplicate_groups": int(groups or 0), "duplicate_extra_rows": int(extras or 0), "conflicting_value_groups": int(conflicts or 0)}

    def close(self) -> None:
        self.db.close()


def extract_archive(zf: zipfile.ZipFile, source_zip: str, candidate_ciks: set[str], writers: PanelWriters, tracker: DuplicateTracker) -> dict:
    infos = {info.filename: info for info in zf.infolist()}
    for member in ("sub.txt", "pre.txt", "num.txt"):
        if member not in infos:
            raise ValueError(f"missing FSDS member: {member}")
    counts: Counter[str] = Counter()
    forms: Counter[str] = Counter()
    accessions: set[str] = set()

    with ExitStack() as stack:
        sub_text, sub_reader = read_tsv(zf, "sub.txt")
        stack.callback(sub_text.close)
        sub_header = list(sub_reader.fieldnames or [])
        missing = SUB_REQUIRED - set(sub_header)
        if missing:
            raise ValueError(f"sub.txt missing fields: {sorted(missing)}")
        for row in sub_reader:
            counts["sub_rows_scanned"] += 1
            if row.get("form", "") not in FORM_SET:
                continue
            try:
                cik = canonical_cik(row.get("cik", ""))
            except ValueError:
                counts["selected_form_rows_invalid_cik"] += 1
                continue
            if cik not in candidate_ciks:
                counts["selected_form_rows_noncandidate_cik"] += 1
                continue
            adsh = row.get("adsh", "")
            if not adsh:
                counts["selected_submissions_missing_adsh"] += 1
                continue
            accessions.add(adsh)
            forms[row["form"]] += 1
            counts["selected_submissions"] += 1
            writers.write("sub", sub_header, row, source_zip)

        pre_text, pre_reader = read_tsv(zf, "pre.txt")
        stack.callback(pre_text.close)
        pre_header = list(pre_reader.fieldnames or [])
        missing = PRE_REQUIRED - set(pre_header)
        if missing:
            raise ValueError(f"pre.txt missing fields: {sorted(missing)}")
        selected_keys: set[tuple[str, str, str]] = set()
        for row in pre_reader:
            counts["pre_rows_scanned"] += 1
            if row.get("adsh", "") not in accessions or row.get("stmt", "") not in STATEMENT_SET:
                continue
            writers.write("pre", pre_header, row, source_zip)
            selected_keys.add((row.get("adsh", ""), row.get("tag", ""), row.get("version", "")))
            counts["pre_main_is_bs_rows"] += 1

        num_text, num_reader = read_tsv(zf, "num.txt")
        stack.callback(num_text.close)
        num_header = list(num_reader.fieldnames or [])
        missing = NUM_REQUIRED - set(num_header)
        if missing:
            raise ValueError(f"num.txt missing fields: {sorted(missing)}")
        for row in num_reader:
            counts["num_rows_scanned"] += 1
            join_key = (row.get("adsh", ""), row.get("tag", ""), row.get("version", ""))
            if join_key not in selected_keys:
                counts["num_rows_without_selected_main_statement_match"] += 1
                continue
            counts["num_rows_matched_selected_main_statement"] += 1
            failed = []
            if row.get("uom", "") != "USD":
                counts["excluded_non_usd"] += 1
                failed.append("uom")
            if row.get("qtrs", "") not in {"0", "4"}:
                counts["excluded_qtrs_not_0_or_4"] += 1
                failed.append("qtrs")
            if row.get("segments", "") != "":
                counts["excluded_nonempty_segments"] += 1
                failed.append("segments")
            if row.get("coreg", "") != "":
                counts["excluded_nonempty_coreg"] += 1
                failed.append("coreg")
            if failed:
                counts["excluded_union"] += 1
                continue
            writers.write("num", num_header, row, source_zip)
            tracker.add(source_zip, row)
            counts["retained_statement_fact_rows"] += 1

    return {
        "source_zip": source_zip,
        "counts": dict(counts),
        "selected_form_counts": dict(forms),
        "selected_accession_count": len(accessions),
        "presentation_tag_version_key_count": len(selected_keys),
        "table_structure": {
            member: {"uncompressed_bytes": infos[member].file_size, "compressed_bytes": infos[member].compress_size,
                    "header": sub_header if member == "sub.txt" else pre_header if member == "pre.txt" else num_header}
            for member in ("sub.txt", "pre.txt", "num.txt")
        },
        "period_policy": "SEC submission period is reported at month-end; all NUM ddate values are preserved independently, without equality filtering or annual value selection.",
    }


def verify_external_storage(mount: Path, expected_device: int, expected_uuid: str, required_free: int) -> dict:
    if not mount.is_dir():
        raise RuntimeError(f"external mount unavailable: {mount}")
    device = mount.stat().st_dev
    if device != expected_device:
        raise RuntimeError(f"external device mismatch: {device} != {expected_device}")
    result = subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)], capture_output=True, check=True, timeout=15)
    info = plistlib.loads(result.stdout)
    actual_uuid = info.get("VolumeUUID")
    if actual_uuid != expected_uuid:
        raise RuntimeError(f"external UUID mismatch: {actual_uuid} != {expected_uuid}")
    free = shutil.disk_usage(mount).free
    if free < required_free:
        raise RuntimeError(f"external capacity insufficient: {free} < {required_free}")
    return {"mount": str(mount), "device": device, "uuid": actual_uuid, "free_bytes": free}


def run_job(job_path: Path, script_path: Path) -> dict:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    required = {"execution_authorized", "inputs", "candidate_ciks", "candidate_ciks_sha256", "script_sha256", "storage_plan", "storage_plan_sha256", "output", "external_device", "external_uuid", "external_mount", "external_reserve_bytes", "estimated_bytes"}
    missing = required - set(job)
    if missing:
        raise ValueError(f"job missing fields: {sorted(missing)}")
    if job["execution_authorized"] is not True:
        raise PermissionError("job is not explicitly authorized for extraction")
    if not job["inputs"]:
        raise ValueError("job input list is empty")
    if sha256_file(script_path) != job["script_sha256"]:
        raise RuntimeError("extractor script SHA mismatch")
    ciks_path = Path(job["candidate_ciks"])
    if sha256_file(ciks_path) != job["candidate_ciks_sha256"]:
        raise RuntimeError("candidate CIK file SHA mismatch")
    candidates_doc = json.loads(ciks_path.read_text(encoding="utf-8"))
    candidate_ciks = {canonical_cik(cik) for cik in candidates_doc["ciks"]}
    plan_path = Path(job["storage_plan"])
    if sha256_file(plan_path) != job["storage_plan_sha256"]:
        raise RuntimeError("storage plan SHA mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for key in ("external_mount", "external_device", "external_uuid", "external_reserve_bytes"):
        if job[key] != plan[key]:
            raise RuntimeError(f"job/storage-plan binding mismatch: {key}")

    inputs = []
    source_ids = set()
    for item in job["inputs"]:
        source = Path(item["path"])
        source_id = item.get("source_id", source.name)
        if not source_id or "|" in source_id or source_id in source_ids:
            raise ValueError(f"input source_id must be nonempty, unique, and exclude '|': {source_id!r}")
        source_ids.add(source_id)
        actual = sha256_file(source)
        if actual != item["sha256"]:
            raise RuntimeError(f"input SHA mismatch: {source}")
        inputs.append({"path": str(source), "sha256": actual, "bytes": source.stat().st_size, "period": item.get("period")})
    output = Path(job["output"])
    if output.exists():
        raise FileExistsError(f"create-only output exists: {output}")
    storage_before = verify_external_storage(Path(job["external_mount"]), job["external_device"], job["external_uuid"], job["external_reserve_bytes"] + job["estimated_bytes"])
    if output.parent.stat().st_dev != job["external_device"]:
        raise RuntimeError("output parent is not on expected external device")
    output.mkdir()
    writers = PanelWriters(output)
    scratch = output / ".duplicate-index.sqlite3"
    tracker = DuplicateTracker(scratch)
    source_summaries = []
    try:
        for item in job["inputs"]:
            source = Path(item["path"])
            source_id = item.get("source_id", source.name)
            with zipfile.ZipFile(source) as zf:
                summary = extract_archive(zf, source_id, candidate_ciks, writers, tracker)
                summary["source_sha256"] = item["sha256"]
                summary["source_bytes"] = source.stat().st_size
                summary["archive_member_count"] = len(zf.infolist())
                summary["archive_uncompressed_bytes"] = sum(info.file_size for info in zf.infolist())
                source_summaries.append(summary)
    finally:
        writers.close()
        duplicate_summary = tracker.summary()
        tracker.close()
        if scratch.exists():
            scratch.unlink()

    tables = {}
    for filename in TABLES.values():
        path = output / filename
        if path.exists():
            tables[filename] = {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
    storage_after = verify_external_storage(Path(job["external_mount"]), job["external_device"], job["external_uuid"], job["external_reserve_bytes"])
    return {
        "schema": "sec-fsds-candidate-panel/1",
        "status": "source_extraction_only",
        "job_path": str(job_path), "job_sha256": sha256_file(job_path),
        "script_path": str(script_path), "script_sha256": sha256_file(script_path),
        "candidate_ciks_path": str(ciks_path), "candidate_ciks_sha256": job["candidate_ciks_sha256"],
        "candidate_cik_count": len(candidate_ciks),
        "storage_plan_path": str(plan_path), "storage_plan_sha256": job["storage_plan_sha256"],
        "storage_before": storage_before, "storage_after": storage_after,
        "input_sources": inputs, "per_source": source_summaries,
        "duplicate_audit": duplicate_summary, "output_directory": str(output), "output_tables": tables,
        "limitations": [
            "Source rows retain filing accession/version; no later amendment is selected as the preferred truth.",
            "All NUM ddate strings are retained; SEC period is a filing period reported at month-end and is not equated to each fact date.",
            "Tag equivalence, annual-value selection, missing-value filling, operating-profitability construction, and return analysis are not performed.",
            "Filed and accepted fields are source strings; accepted timezone is not inferred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, help="SHA-bound FSDS panel job JSON")
    args = parser.parse_args()
    try:
        print(json.dumps(run_job(Path(args.job), Path(__file__)), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
