"""Small, opt-in research storage supervisor. Never deletes or copies research data.

Run with ``python -m lei_signal.research.storage_guard --help``. The default
is a read-only plan; --execute starts only the explicitly supplied command.
Polling is a stop mechanism, not an operating-system filesystem quota.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from typing import Callable, Iterable


class StorageStop(RuntimeError):
    """The run must pause; its existing evidence remains in place."""


@dataclass(frozen=True)
class StoragePolicy:
    max_output_bytes: int
    reserve_bytes: int = 512 * 1024 * 1024
    max_entries: int = 100_000

    def __post_init__(self) -> None:
        if self.max_output_bytes <= 0 or self.reserve_bytes < 0 or self.max_entries <= 0:
            raise ValueError("storage limits must be positive; reserve may be zero")


def _plain_path(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    # macOS system aliases are not caller-controlled research links. Canonicalize
    # only these exact mappings; still reject arbitrary symlink descendants.
    for alias, target in ((Path("/tmp"), Path("/private/tmp")),
                          (Path("/var"), Path("/private/var"))):
        if path.is_relative_to(alias) and alias.is_symlink() and alias.resolve() == target:
            path = target / path.relative_to(alias)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise StorageStop(f"symlink path is not a managed output: {path}")
    return path


def _existing_parent(path: Path) -> Path:
    while not path.exists():
        path = path.parent
    return path


def output_usage(path: Path, max_entries: int = 100_000) -> int:
    """Bounded, conservative byte count; do not follow symlinks or other volumes."""
    path = _plain_path(path)
    if not path.exists():
        return 0
    device = path.stat().st_dev
    pending = [path]
    total = count = 0
    while pending:
        current = pending.pop()
        count += 1
        if count > max_entries:
            raise StorageStop(f"output inspection exceeds {max_entries} entries")
        if current.is_symlink():
            raise StorageStop(f"output contains a symlink: {current}")
        info = current.stat()
        if info.st_dev != device:
            raise StorageStop(f"output crosses a volume: {current}")
        if current.is_dir():
            # Limit the frontier as well as visited entries.
            with os.scandir(current) as entries:
                for entry in entries:
                    if len(pending) + count >= max_entries:
                        raise StorageStop(f"output inspection exceeds {max_entries} entries")
                    pending.append(Path(entry.path))
        elif current.is_file():
            total += max(info.st_size, getattr(info, "st_blocks", 0) * 512)
        else:
            raise StorageStop(f"output contains a special file: {current}")
    return total


def check_space(output: Path, policy: StoragePolicy, *, planned_bytes: int = 0,
                free_bytes: Callable[[Path], int] | None = None) -> dict:
    """Check before launch and at checkpoints. Raises before any write on failure."""
    if planned_bytes < 0:
        raise ValueError("planned_bytes must not be negative")
    output = _plain_path(output)
    used = output_usage(output, policy.max_entries)
    free = (free_bytes or (lambda p: shutil.disk_usage(p).free))(_existing_parent(output))
    if used + planned_bytes > policy.max_output_bytes:
        raise StorageStop(f"output quota: {used}+{planned_bytes}>{policy.max_output_bytes} bytes")
    if free < policy.reserve_bytes + planned_bytes:
        raise StorageStop(f"low space: {free} available; need {policy.reserve_bytes}+{planned_bytes} bytes")
    return {"output": str(output), "output_bytes": used, "free_bytes": free,
            "planned_bytes": planned_bytes, "reserve_bytes": policy.reserve_bytes,
            "max_output_bytes": policy.max_output_bytes}


def write_chunks(destination: Path, chunks: Iterable[bytes], *, output: Path,
                 policy: StoragePolicy,
                 free_bytes: Callable[[Path], int] | None = None) -> dict:
    """Cooperative writer checks allocation before every chunk; never overwrites.

    Partial files are retained on failure. Other writers still need supervision;
    this is not a global reservation across concurrent processes.
    """
    output, destination = _plain_path(output), _plain_path(destination)
    if destination == output or not destination.is_relative_to(output):
        raise StorageStop("destination must be inside the managed output")
    check_space(output, policy, free_bytes=free_bytes)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb", buffering=0) as handle:
        for chunk in chunks:
            if not isinstance(chunk, bytes):
                raise ValueError("writer chunks must be bytes")
            info = os.fstat(handle.fileno())
            allocation_unit = max(4096, os.statvfs(destination.parent).f_frsize)
            new_size = info.st_size + len(chunk)
            projected = ((new_size + allocation_unit - 1) // allocation_unit) * allocation_unit
            current = max(info.st_size, getattr(info, "st_blocks", 0) * 512)
            check_space(output, policy, planned_bytes=max(0, projected - current),
                        free_bytes=free_bytes)
            view = memoryview(chunk)
            while view:
                written = handle.write(view)
                if not written:
                    raise OSError("zero-byte write")
                view = view[written:]
    return check_space(output, policy, free_bytes=free_bytes)


def _stop_group(child: subprocess.Popen) -> list[str]:
    # The supervisor created this session; unrelated running research is untouched.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        return [f"process group termination denied: {exc}"]
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # Also terminate a descendant that outlived the group leader.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        return [f"process group kill denied: {exc}"]
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        return ["child did not exit after termination"]
    return []


def supervise(command: list[str], output: Path, policy: StoragePolicy, *,
              execute: bool = False, interval: float = 0.25,
              free_bytes: Callable[[Path], int] | None = None) -> dict:
    """Run a new output directory under a monitored process group, or only plan.

    Output outside the configured directory is not included in the per-run quota.
    Global free-space checks still observe concurrent disk consumption.
    """
    if not command or not (0.01 <= interval <= 5):
        raise ValueError("command required; polling interval must be 0.01..5 seconds")
    output = _plain_path(output)
    # Prevent an accidental mismatch at the project's unified research launcher.
    # Other commands must confine their outputs themselves (see module docs).
    runner = Path(__file__).resolve().parents[3] / "scripts/run_factor_lab.py"
    for index, part in enumerate(command):
        if Path(part).name == "run_factor_lab.py" and Path(part).resolve() == runner:
            arguments = command[index + 1:]
            output_values = [arg.partition("=")[2] for arg in arguments if arg.startswith("--out=")]
            output_values += [arguments[i + 1] for i, arg in enumerate(arguments[:-1]) if arg == "--out"]
            if len(output_values) != 1 or _plain_path(Path(output_values[0])) != output:
                raise StorageStop("run_factor_lab --out must match the supervised output")
    if output.exists():
        raise StorageStop(f"new run output must not already exist: {output}")
    initial = check_space(output, policy, planned_bytes=policy.max_output_bytes,
                          free_bytes=free_bytes)
    if not execute:
        return {"status": "dry_run", "check": initial, "command": command}
    child = subprocess.Popen(command, start_new_session=True)
    try:
        while True:
            check_space(output, policy, free_bytes=free_bytes)
            code = child.poll()
            if code is not None:
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    errors = _stop_group(child)
                    return {"status": "paused_stop_unconfirmed" if errors else "failed_descendants", "returncode": code,
                            "reason": "child group outlived its leader; " + ("stop unconfirmed" if errors else "stopped"),
                            "stop_errors": errors, "stop_confirmed": not errors,
                            "evidence_preserved": True}
                # A successful exit must pass the last on-disk check too.
                final = check_space(output, policy, free_bytes=free_bytes)
                return {"status": "completed" if code == 0 else "failed",
                        "returncode": code, "check": final}
            time.sleep(interval)
    except (StorageStop, OSError) as exc:
        errors = _stop_group(child)
        return {"status": "paused_stop_unconfirmed" if errors else "paused_storage", "reason": str(exc),
                "stop_errors": errors, "stop_confirmed": not errors,
                "returncode": child.returncode, "output": str(output),
                "evidence_preserved": True}
    except BaseException:
        errors = _stop_group(child)
        if errors:
            raise StorageStop("interrupted; process stop unconfirmed: " + "; ".join(errors))
        raise


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with _plain_path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_cache(manifest: dict, expected_dependencies: dict) -> dict:
    """Return read-only references only when exact dependencies and bytes match.

    Caller binds definition/version, adapter SHA, inputs, parameters and date
    range in expected_dependencies. A cache hit is not research acceptance.
    """
    required = {"definition_ref", "adapter_sha256", "inputs", "parameters", "date_range"}
    if not required <= expected_dependencies.keys() or not expected_dependencies["inputs"]:
        raise StorageStop("cache dependency identity is incomplete")
    if manifest.get("dependencies") != expected_dependencies:
        raise StorageStop("cache dependencies differ; recomputation needs a new budget")
    for name, sha in expected_dependencies["inputs"].items():
        if not Path(name).is_absolute() or fingerprint(Path(name)) != sha:
            raise StorageStop(f"cache input fingerprint differs: {name}")
    artifacts = manifest.get("artifacts", [])
    if not artifacts:
        raise StorageStop("cache has no artifacts")
    references = []
    for artifact in artifacts:
        path = Path(artifact["path"])
        if not path.is_absolute() or fingerprint(path) != artifact["sha256"]:
            raise StorageStop(f"cache artifact fingerprint differs: {path}")
        references.append(str(path))
    return {"status": "reuse_by_reference", "references": references,
            "copied_bytes": 0}


def cleanup_plan(candidates: list[dict], *, references: list[Path],
                 protected_roots: list[Path], quarantine: Path,
                 reference_inventory_complete: bool = False) -> list[dict]:
    """Plan reversible moves only; no execution, deletion, or duplicate guessing.

    A reviewed, complete reference inventory and explicit retirement are needed.
    Archive/raw/input roots belong in protected_roots. Same-volume moves free 0.
    """
    quarantine = _plain_path(quarantine)
    protected = [_plain_path(p) for p in [*references, *protected_roots]]
    names = [Path(candidate["path"]).name for candidate in candidates]
    results = []
    for candidate in candidates:
        path = _plain_path(Path(candidate["path"]))
        blocked = []
        if not reference_inventory_complete:
            blocked.append("reference_inventory_incomplete")
        if candidate.get("kind") != "temporary" or candidate.get("retired") is not True:
            blocked.append("not_explicitly_retired_temporary")
        if not path.exists():
            blocked.append("missing")
        if any(path == p or path in p.parents or p in path.parents for p in protected):
            blocked.append("protected_or_referenced")
        if path == quarantine or path in quarantine.parents or quarantine in path.parents:
            blocked.append("quarantine_overlaps_source")
        target = quarantine / path.name
        if names.count(path.name) > 1:
            blocked.append("duplicate_destination_name")
        if target.exists() or target.is_symlink():
            blocked.append("destination_exists")
        if path.exists() and path.stat().st_dev != _existing_parent(quarantine).stat().st_dev:
            blocked.append("cross_volume_move_not_planned")
        results.append({"path": str(path), "target": str(target), "dry_run": True,
                        "status": "blocked" if blocked else "reversible_move_candidate",
                        "reasons": blocked, "expected_freed_bytes": 0})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-output-bytes", type=int, required=True)
    parser.add_argument("--reserve-bytes", type=int, default=512 * 1024 * 1024)
    parser.add_argument("--execute", action="store_true", help="explicitly execute supplied command")
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        result = supervise(command, args.output,
                           StoragePolicy(args.max_output_bytes, args.reserve_bytes),
                           execute=args.execute, interval=args.interval)
    except (StorageStop, OSError, ValueError) as exc:
        result = {"status": "blocked_before_launch", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] in {"dry_run", "completed"}:
        return 0
    return 4 if result["status"] in {"blocked_before_launch", "paused_storage", "paused_stop_unconfirmed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
