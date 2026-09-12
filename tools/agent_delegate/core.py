"""Core data, filesystem isolation, and persistence helpers.

This module deliberately has no provider-specific behavior.  Its job is to
turn a bounded request into a task-owned copy and to make unsafe requests fail
before any external agent starts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VALID_PROVIDERS = frozenset({"cc", "zcode", "fake"})
VALID_MODES = frozenset({"review", "edit"})
TASK_ID_RE = re.compile(r"^task_[a-f0-9]{12}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

_EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".agent-delegate",
        ".local-state",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
        "venv",
    }
)
_SECRET_ENV_RE = re.compile(r"^\.env(?:\..*)?$")

_REDACTION_PATTERNS = (
    re.compile(
        r"(?i)(\b(?:[A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|PASSWORD))\b\s*=\s*)"
        r"([^\s\"']+)"
    ),
    re.compile(r"(?i)(\bAuthorization\s*:\s*Bearer\s+)([^\s\"']+)"),
    re.compile(
        r'(?i)(["\'](?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)'
        r'["\']\s*:\s*["\'])([^"\']+)(["\'])'
    ),
)


class ValidationError(ValueError):
    """Raised when a delegation request crosses a safety boundary."""


@dataclass(frozen=True, slots=True)
class TaskRequest:
    task_id: str
    request_id: str
    provider: str
    mode: str
    source_cwd: str
    task_text: str
    read_paths: tuple[str, ...]
    write_paths: tuple[str, ...]
    verify_commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int
    max_turns: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TaskRequest:
        """Restore tuple fields after reading a JSON request."""

        data = dict(value)
        data["read_paths"] = tuple(data.get("read_paths", ()))
        data["write_paths"] = tuple(data.get("write_paths", ()))
        data["verify_commands"] = tuple(
            tuple(command) for command in data.get("verify_commands", ())
        )
        return cls(**data)


@dataclass(frozen=True, slots=True)
class TaskPaths:
    root: Path
    workspace: Path
    request: Path
    task_md: Path
    state: Path
    events: Path
    stdout: Path
    stderr: Path
    baseline: Path
    patch: Path
    verification: Path
    result: Path
    handoff: Path
    stop_request: Path


def default_state_root() -> Path:
    """Return the per-user state directory without creating it."""

    configured = os.environ.get("AGENT_DELEGATE_STATE_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "state" / "agent-delegate"


def task_paths(state_root: Path, task_id: str) -> TaskPaths:
    """Build all stable paths for one task."""

    root = Path(state_root) / "tasks" / task_id
    return TaskPaths(
        root=root,
        workspace=root / "workspace",
        request=root / "request.json",
        task_md=root / "task.md",
        state=root / "state.json",
        events=root / "events.jsonl",
        stdout=root / "stdout.log",
        stderr=root / "stderr.log",
        baseline=root / "baseline.json",
        patch=root / "changes.patch",
        verification=root / "verification.json",
        result=root / "result.json",
        handoff=root / "handoff.md",
        stop_request=root / "stop.requested",
    )


def _relative_path(value: str, *, kind: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{kind} path must not be empty")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValidationError(f"{kind} path must stay within the source workspace: {value}")
    normalized = Path(os.path.normpath(value))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValidationError(f"{kind} path must stay within the source workspace: {value}")
    return normalized


def _is_excluded(relative: Path) -> bool:
    return any(part in _EXCLUDED_DIRECTORY_NAMES for part in relative.parts) or any(
        _SECRET_ENV_RE.match(part) for part in relative.parts
    )


def _reject_symlinks(source: Path, selected: Path) -> None:
    current = source
    for part in selected.parts:
        if part == ".":
            continue
        current = current / part
        if current.is_symlink():
            raise ValidationError(f"selected path contains a symlink: {selected}")

    target = source / selected
    if target.is_dir():
        for root, directory_names, file_names in os.walk(target, followlinks=False):
            root_path = Path(root)
            relative_root = root_path.relative_to(source)
            directory_names[:] = [
                name
                for name in directory_names
                if not _is_excluded(relative_root / name)
            ]
            for name in (*directory_names, *file_names):
                child = root_path / name
                if child.is_symlink() and not _is_excluded(child.relative_to(source)):
                    raise ValidationError(
                        f"selected path contains a nested symlink: {child.relative_to(source)}"
                    )


def _contains(parent: Path, child: Path) -> bool:
    return parent == Path(".") or child == parent or parent in child.parents


def validate_request(request: TaskRequest) -> None:
    """Validate every request boundary before making a task workspace."""

    if not TASK_ID_RE.fullmatch(request.task_id):
        raise ValidationError("task id must match task_[a-f0-9]{12}")
    if not REQUEST_ID_RE.fullmatch(request.request_id):
        raise ValidationError("request id must be 1-128 safe characters")
    if request.provider not in VALID_PROVIDERS:
        raise ValidationError(f"provider must be one of {sorted(VALID_PROVIDERS)}")
    if request.mode not in VALID_MODES:
        raise ValidationError(f"mode must be one of {sorted(VALID_MODES)}")
    if not request.task_text.strip():
        raise ValidationError("task text must not be empty")
    if request.timeout_seconds <= 0:
        raise ValidationError("timeout must be positive")
    if request.max_turns <= 0:
        raise ValidationError("max turns must be positive")

    source = Path(request.source_cwd).expanduser()
    if not source.exists() or not source.is_dir():
        raise ValidationError("source workspace must be an existing directory")
    if not request.read_paths:
        raise ValidationError("at least one read path is required")

    reads = tuple(_relative_path(value, kind="read") for value in request.read_paths)
    writes = tuple(_relative_path(value, kind="write") for value in request.write_paths)
    if len(set(reads)) != len(reads):
        raise ValidationError("read paths must not contain duplicates")
    if len(set(writes)) != len(writes):
        raise ValidationError("write paths must not contain duplicates")

    for selected in reads:
        target = source / selected
        if not target.exists():
            raise ValidationError(f"read path does not exist: {selected}")
        _reject_symlinks(source, selected)

    if request.mode == "edit" and not writes:
        raise ValidationError("edit mode requires at least one write path")
    for selected in writes:
        if not any(_contains(read, selected) for read in reads):
            raise ValidationError(f"write path is outside the authorized read paths: {selected}")
        _reject_symlinks(source, selected)

    for command in request.verify_commands:
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValidationError("verification commands require a non-empty argv")


def _copy_directory(source: Path, destination: Path, source_root: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copystat(source, destination, follow_symlinks=False)
    for child in source.iterdir():
        relative = child.relative_to(source_root)
        if _is_excluded(relative):
            continue
        target = destination / child.name
        if child.is_dir():
            _copy_directory(child, target, source_root)
        elif child.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, target, follow_symlinks=False)


def create_workspace_snapshot(request: TaskRequest, paths: TaskPaths) -> dict[str, Any]:
    """Create the isolated workspace and persist its initial file fingerprint."""

    validate_request(request)
    source = Path(request.source_cwd).expanduser()
    if paths.workspace.exists():
        raise ValidationError(f"task workspace already exists: {paths.workspace}")
    paths.workspace.mkdir(parents=True)

    copied: set[Path] = set()
    for value in request.read_paths:
        relative = _relative_path(value, kind="read")
        if any(_contains(existing, relative) for existing in copied):
            continue
        source_path = source / relative
        destination = paths.workspace if relative == Path(".") else paths.workspace / relative
        if source_path.is_dir():
            _copy_directory(source_path, destination, source)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination, follow_symlinks=False)
        copied.add(relative)

    baseline = snapshot_tree(paths.workspace)
    atomic_write_json(paths.baseline, baseline)
    return baseline


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, dict[str, Any]]:
    """Hash all regular files below root using stable relative names."""

    snapshot: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return snapshot
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValidationError(f"workspace contains a symlink: {path.relative_to(root)}")
        if not path.is_file():
            continue
        file_stat = path.stat()
        snapshot[path.relative_to(root).as_posix()] = {
            "sha256": _sha256(path),
            "size": file_stat.st_size,
            "mode": stat.S_IMODE(file_stat.st_mode),
        }
    return snapshot


def diff_snapshots(
    before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    """Return stable added, modified, and deleted file lists."""

    before_paths = set(before)
    after_paths = set(after)
    return {
        "added": sorted(after_paths - before_paths),
        "modified": sorted(
            path for path in before_paths & after_paths if before[path] != after[path]
        ),
        "deleted": sorted(before_paths - after_paths),
    }


def redact_text(text: str) -> str:
    """Mask common credential shapes before text reaches persistent logs."""

    redacted = text
    for pattern in _REDACTION_PATTERNS:
        if pattern.groups == 3:
            redacted = pattern.sub(r"\1[REDACTED]\3", redacted)
        else:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def atomic_write_json(target: Path, value: Any) -> None:
    """Durably replace one JSON document without exposing a partial file."""

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, target)
        temporary_name = None
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def read_json(path: Path) -> Any:
    """Read one UTF-8 JSON document."""

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
