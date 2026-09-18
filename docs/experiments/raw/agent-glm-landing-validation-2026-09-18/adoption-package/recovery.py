#!/usr/bin/env python3
"""Recover an interrupted adoption operation without overwriting later edits."""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def refuse(message: str) -> int:
    print(f"RECOVERY-REFUSED: {message}", file=sys.stderr)
    print("No recovery writes were made; recovery materials were kept.", file=sys.stderr)
    return 1


def safe_relative(raw: str) -> bool:
    path = PurePosixPath(raw)
    return bool(raw) and not path.is_absolute() and ".." not in path.parts


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: recovery.py TARGET PLAN", file=sys.stderr)
        return 2
    target = Path(sys.argv[1])
    plan = Path(sys.argv[2])
    keepdir = Path(__file__).resolve().parent
    if not target.is_absolute() or not target.is_dir() or not plan.is_file():
        return refuse("target or recovery plan is invalid")

    entries: list[dict[str, str]] = []
    with plan.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            entries.append(row)
    required = {"path", "action", "expected_current", "restore_sha256", "payload"}
    if not entries or any(set(row) != required for row in entries):
        return refuse("recovery plan is empty or malformed")

    # Validate every target state and every payload before the first write.
    # Interruption-window tolerance (2026-09-18): apply/revert record the
    # recovery-plan row BEFORE the atomic rename, so a crash between the two
    # can leave a row whose target is still at its pre-step content. That
    # content is exactly the restore payload, so the row is treated as
    # already-restored (skipped). Anything else still refuses; this is a
    # per-file recovery, never a claim of whole-package atomicity.
    already: set[str] = set()
    for row in entries:
        relative = row["path"]
        if not safe_relative(relative):
            return refuse(f"unsafe target path: {relative}")
        destination = target / relative
        expected = row["expected_current"]
        restore_sha = row["restore_sha256"]
        action = row["action"]
        if action == "remove":
            if not destination.is_file() and not destination.is_symlink():
                already.add(relative)  # already removed before the interruption
            elif digest(destination) != expected:
                return refuse(f"target changed after interruption: {relative}")
        elif expected == "ABSENT":
            # copy row whose post-step state is absence (revert of an add):
            # file still present at its post-apply content = not yet removed.
            if destination.exists() or destination.is_symlink():
                if destination.is_file() and digest(destination) == restore_sha:
                    already.add(relative)
                else:
                    return refuse(
                        f"target changed after interruption: {relative} (expected absent)")
        else:
            if not destination.is_file():
                return refuse(f"target changed after interruption: {relative}")
            got = digest(destination)
            if got != expected:
                if got == restore_sha:
                    already.add(relative)  # recorded, rename never happened
                else:
                    return refuse(f"target changed after interruption: {relative}")

        if action == "copy":
            payload_name = row["payload"]
            if not safe_relative(payload_name):
                return refuse(f"unsafe recovery payload path: {payload_name}")
            payload = keepdir / payload_name
            if not payload.is_file() or digest(payload) != row["restore_sha256"]:
                return refuse(f"recovery payload missing or damaged: {relative}")
        elif action != "remove":
            return refuse(f"unknown recovery action: {action}")

    completed = 0
    for row in entries:
        relative = row["path"]
        if relative in already:
            continue  # already at its restore state; nothing to write
        destination = target / relative
        try:
            if row["action"] == "remove":
                destination.unlink()
            else:
                payload = keepdir / row["payload"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary_name = tempfile.mkstemp(
                    prefix=f".{destination.name}.recovery-", dir=destination.parent
                )
                temporary = Path(temporary_name)
                try:
                    with os.fdopen(fd, "wb") as output, payload.open("rb") as source:
                        shutil.copyfileobj(source, output)
                        output.flush()
                        os.fsync(output.fileno())
                    shutil.copystat(payload, temporary)
                    if digest(temporary) != row["restore_sha256"]:
                        raise OSError("staged recovery content hash mismatch")
                    os.replace(temporary, destination)
                finally:
                    if temporary.exists():
                        temporary.unlink()
            completed += 1
        except Exception as exc:
            print(
                f"RECOVERY-WRITE-FAIL: {relative}: {exc}; restored {completed}/{len(entries)} items.",
                file=sys.stderr,
            )
            print(
                "Recovery materials were kept for diagnosis; manually verify the reported completed items and remaining plan before any further action.",
                file=sys.stderr,
            )
            return 1

    skipped = len(already)
    print(f"RECOVERY DONE: restored {completed}/{len(entries)} items "
          f"({skipped} already at their restore state and skipped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
