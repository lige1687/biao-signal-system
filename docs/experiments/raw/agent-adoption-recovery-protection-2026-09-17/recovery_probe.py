#!/usr/bin/env python3
"""Focused failure-recovery probe for the agent runtime adoption package."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[4]
SOURCE_PACKAGE = REPO / "docs/experiments/raw/agent-runtime-adoption-candidate-2026-09-17/adoption-package"
RESULTS = Path(__file__).with_name("recovery-probe-results.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(package: Path) -> list[dict[str, str]]:
    with (package / "manifest.tsv").open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def dependencies(package: Path) -> list[dict[str, str]]:
    with (package / "dependencies.tsv").open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def prepare(root: Path) -> tuple[Path, Path, list[dict[str, str]]]:
    package = root / "package"
    shutil.copytree(SOURCE_PACKAGE, package)
    target = root / "target"
    (target / "src/lei_signal").mkdir(parents=True)
    (target / "docs/experiments").mkdir(parents=True)
    manifest = rows(package)
    for row in manifest:
        path = target / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if row["op"] == "replace":
            shutil.copy2(package / "before" / row["path"], path)
    for dep in dependencies(package):
        path = target / dep["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / dep["path"], path)
        assert sha(path) == dep["required_sha256"]
    return target, package, manifest


def run(package: Path, target: Path, mode: str, temp_root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TMPDIR"] = str(temp_root)
    return subprocess.run(
        ["sh", str(package / f"{mode}.sh"), "--target", str(target)],
        cwd="/",
        env=env,
        capture_output=True,
        text=True,
    )


def snapshot(target: Path, manifest: list[dict[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in manifest:
        path = target / row["path"]
        result[row["path"]] = sha(path) if path.is_file() else "ABSENT"
    return result


def first_replace(manifest: list[dict[str, str]]) -> dict[str, str]:
    return next(row for row in manifest if row["op"] == "replace")


def find_restore(temp_root: Path, prefix: str) -> Path:
    matches = list(temp_root.glob(f"{prefix}*/restore-partial.sh"))
    assert len(matches) == 1, matches
    return matches[0]


def force_apply_failure(package: Path, target: Path, temp_root: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    blocked = target / "web/src/pages"
    blocked.chmod(0o500)
    try:
        proc = run(package, target, "apply", temp_root)
    finally:
        blocked.chmod(0o700)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    return proc, find_restore(temp_root, "adoption-keep-")


def force_revert_failure(package: Path, target: Path, manifest: list[dict[str, str]], temp_root: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    applied = run(package, target, "apply", temp_root)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    blocked = target / "web/src/pages"
    blocked.chmod(0o500)
    try:
        proc = run(package, target, "revert", temp_root)
    finally:
        blocked.chmod(0o700)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    return proc, find_restore(temp_root, "adoption-revert-keep-")


def execute_restore(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(script)], cwd="/", capture_output=True, text=True)


def main() -> None:
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)

        root = base / "apply_complete"
        target, package, manifest = prepare(root)
        initial = snapshot(target, manifest)
        _, restore = force_apply_failure(package, target, root / "tmp")
        recovered = execute_restore(restore)
        results["apply_failure_complete_restore"] = {
            "restore_rc": recovered.returncode,
            "restored": snapshot(target, manifest) == initial,
        }

        root = base / "apply_edit"
        target, package, manifest = prepare(root)
        _, restore = force_apply_failure(package, target, root / "tmp")
        victim = target / first_replace(manifest)["path"]
        victim.write_text("LATER USER EDIT\n")
        before = snapshot(target, manifest)
        recovered = execute_restore(restore)
        results["apply_later_edit_refused"] = {
            "restore_rc": recovered.returncode,
            "zero_writes": snapshot(target, manifest) == before,
            "later_edit_preserved": victim.read_text() == "LATER USER EDIT\n",
        }

        root = base / "backup_corrupt"
        target, package, manifest = prepare(root)
        _, restore = force_apply_failure(package, target, root / "tmp")
        backup = next(path for path in (restore.parent / "backup").rglob("*") if path.is_file())
        backup.write_text("CORRUPT BACKUP\n")
        before = snapshot(target, manifest)
        recovered = execute_restore(restore)
        results["corrupt_backup_refused"] = {
            "restore_rc": recovered.returncode,
            "zero_writes": snapshot(target, manifest) == before,
        }

        root = base / "apply_write_fail"
        target, package, manifest = prepare(root)
        _, restore = force_apply_failure(package, target, root / "tmp")
        blocked = (target / first_replace(manifest)["path"]).parent
        blocked.chmod(0o500)
        try:
            recovered = execute_restore(restore)
        finally:
            blocked.chmod(0o700)
        results["restore_write_failure_nonzero"] = {"restore_rc": recovered.returncode}

        root = base / "revert_edit"
        target, package, manifest = prepare(root)
        _, restore = force_revert_failure(package, target, manifest, root / "tmp")
        victim = target / first_replace(manifest)["path"]
        victim.write_text("LATER USER EDIT AFTER REVERT FAILURE\n")
        before = snapshot(target, manifest)
        recovered = execute_restore(restore)
        results["revert_later_edit_refused"] = {
            "restore_rc": recovered.returncode,
            "zero_writes": snapshot(target, manifest) == before,
            "later_edit_preserved": victim.read_text() == "LATER USER EDIT AFTER REVERT FAILURE\n",
        }

        root = base / "revert_complete"
        target, package, manifest = prepare(root)
        applied_state = None
        _, restore = force_revert_failure(package, target, manifest, root / "tmp")
        applied_state = {row["path"]: row["after_sha256"] for row in manifest}
        recovered = execute_restore(restore)
        results["revert_failure_complete_restore"] = {
            "restore_rc": recovered.returncode,
            "restored": snapshot(target, manifest) == applied_state,
        }

    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    expected = {
        "apply_failure_complete_restore": lambda x: x["restore_rc"] == 0 and x["restored"],
        "apply_later_edit_refused": lambda x: x["restore_rc"] != 0 and x["zero_writes"] and x["later_edit_preserved"],
        "corrupt_backup_refused": lambda x: x["restore_rc"] != 0 and x["zero_writes"],
        "restore_write_failure_nonzero": lambda x: x["restore_rc"] != 0,
        "revert_later_edit_refused": lambda x: x["restore_rc"] != 0 and x["zero_writes"] and x["later_edit_preserved"],
        "revert_failure_complete_restore": lambda x: x["restore_rc"] == 0 and x["restored"],
    }
    failed = [name for name, check in expected.items() if not check(results[name])]
    if failed:
        raise SystemExit("FAILED: " + ", ".join(failed))


if __name__ == "__main__":
    main()
