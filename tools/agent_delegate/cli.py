"""Command-line lifecycle for local cross-agent delegation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .core import (
    TASK_ID_RE,
    TaskRequest,
    ValidationError,
    atomic_write_json,
    default_state_root,
    read_json,
    redact_text,
    task_document,
    task_paths,
    validate_request,
)
from .providers import ProviderConfig, build_provider_argv, doctor_checks
from .runner import (
    guard_process_group,
    launch_provider,
    recover_interrupted_tasks,
    request_stop,
    run_task,
)

TERMINAL_STATES = frozenset(
    {"completed", "failed", "stopped", "timed_out", "interrupted"}
)


class CliError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _atomic_write_text(target: Path, text: str) -> None:
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
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, target)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _parse_verification(values: list[str] | None) -> tuple[tuple[str, ...], ...]:
    commands: list[tuple[str, ...]] = []
    for raw in values or []:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError("--verify must be a JSON string array") from exc
        if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
            raise ValidationError("--verify must be a JSON string array")
        commands.append(tuple(value))
    return tuple(commands)


def _request_payload(request: TaskRequest) -> dict[str, Any]:
    value = request.to_dict()
    value.pop("task_id")
    value.pop("created_at")
    return value


def _fingerprint(request: TaskRequest) -> str:
    encoded = json.dumps(
        _request_payload(request), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _new_task_id(state_root: Path) -> str:
    while True:
        task_id = f"task_{secrets.token_hex(6)}"
        if not task_paths(state_root, task_id).root.exists():
            return task_id


def _make_request(args: argparse.Namespace, state_root: Path, *, dry_run: bool) -> TaskRequest:
    task_id = "task_000000000000" if dry_run else _new_task_id(state_root)
    request_id = args.request_id or ("dry-run" if dry_run else f"req-{secrets.token_hex(8)}")
    source_path = Path(args.cwd).expanduser().resolve()
    canonical_state_root = state_root.resolve(strict=False)
    if canonical_state_root == source_path or source_path in canonical_state_root.parents:
        raise ValidationError("state root must be outside the source workspace")
    source = str(source_path)
    request = TaskRequest(
        task_id=task_id,
        request_id=request_id,
        provider=args.provider,
        mode=args.mode,
        source_cwd=source,
        task_text=redact_text(args.task.strip()),
        read_paths=tuple(args.read_path or ()),
        write_paths=tuple(args.write_path or ()),
        verify_commands=_parse_verification(args.verify),
        timeout_seconds=args.timeout,
        max_turns=args.max_turns,
        created_at=_now(),
    )
    validate_request(request)
    build_provider_argv(
        request,
        task_paths(state_root, request.task_id),
        ProviderConfig.from_environment(),
    )
    return request


@contextmanager
def _index_lock(state_root: Path) -> Iterator[None]:
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "request-index.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _find_request_id(state_root: Path, request_id: str) -> tuple[str, str] | None:
    tasks_root = state_root / "tasks"
    if not tasks_root.exists():
        return None
    for request_path in tasks_root.glob("task_*/request.json"):
        existing = TaskRequest.from_dict(read_json(request_path))
        if existing.request_id != request_id:
            continue
        state_path = request_path.parent / "state.json"
        state = read_json(state_path)
        return existing.task_id, state.get("request_fingerprint", _fingerprint(existing))
    return None


def _dashboard_command(script: Path, state_root: Path) -> str:
    return shlex.join(
        [sys.executable, str(script), "dashboard", "--state-root", str(state_root)]
    )


def _start(args: argparse.Namespace) -> int:
    state_root = Path(args.state_root).expanduser()
    request = _make_request(args, state_root, dry_run=args.dry_run)
    provisional_paths = task_paths(state_root, request.task_id)
    provider_request = replace(request, task_text=task_document(request))
    argv = build_provider_argv(
        provider_request, provisional_paths, ProviderConfig.from_environment()
    )
    if args.dry_run:
        _json_print(
            {
                "would_start": False,
                "provider": request.provider,
                "mode": request.mode,
                "source_cwd": request.source_cwd,
                "read_paths": list(request.read_paths),
                "write_paths": list(request.write_paths),
                "verify_commands": [list(command) for command in request.verify_commands],
                "argv": argv,
            }
        )
        return 0

    fingerprint = _fingerprint(request)
    script = Path(__file__).resolve().parents[2] / "scripts" / "agent_delegate.py"
    with _index_lock(state_root):
        existing = _find_request_id(state_root, request.request_id)
        if existing:
            existing_task_id, existing_fingerprint = existing
            if existing_fingerprint != fingerprint:
                raise CliError(
                    "request_id_conflict",
                    "the request id already belongs to a different task body",
                )
            _json_print(
                {
                    "task_id": existing_task_id,
                    "reused": True,
                    "dashboard": _dashboard_command(script, state_root),
                }
            )
            return 0

        paths = task_paths(state_root, request.task_id)
        paths.root.mkdir(parents=True)
        atomic_write_json(paths.request, request.to_dict())
        _atomic_write_text(paths.task_md, task_document(request))
        atomic_write_json(
            paths.state,
            {
                "task_id": request.task_id,
                "request_id": request.request_id,
                "request_fingerprint": fingerprint,
                "provider": request.provider,
                "mode": request.mode,
                "source_cwd": request.source_cwd,
                "state": "queued",
                "created_at": request.created_at,
                "latest_activity": "waiting for runner",
                "verification_state": "pending",
            },
        )
        runner_log = (paths.root / "runner.log").open("ab")
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    str(script),
                    "_run",
                    "--task-id",
                    request.task_id,
                    "--state-root",
                    str(state_root),
                ],
                cwd=script.parents[1],
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                stdout=runner_log,
                stderr=runner_log,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as exc:
            state = read_json(paths.state)
            state.update(
                {
                    "state": "failed",
                    "reason": "runner_start_failed",
                    "error_type": type(exc).__name__,
                    "finished_at": _now(),
                }
            )
            atomic_write_json(paths.state, state)
            raise CliError("runner_start_failed", "could not start the detached runner") from exc
        finally:
            runner_log.close()

    _json_print(
        {
            "task_id": request.task_id,
            "reused": False,
            "state": "queued",
            "dashboard": _dashboard_command(script, state_root),
        }
    )
    return 0


def _checked_paths(state_root: Path, task_id: str):
    if not TASK_ID_RE.fullmatch(task_id):
        raise CliError("invalid_task_id", "task id has an invalid format")
    paths = task_paths(state_root, task_id)
    if not paths.root.is_dir():
        raise CliError("task_not_found", f"task does not exist: {task_id}")
    return paths


def _list_tasks(state_root: Path) -> list[dict[str, Any]]:
    recover_interrupted_tasks(state_root)
    tasks_root = state_root / "tasks"
    if not tasks_root.exists():
        return []
    tasks = [
        read_json(path)
        for path in tasks_root.glob("task_*/state.json")
        if path.is_file()
    ]
    return sorted(tasks, key=lambda item: item.get("created_at", ""), reverse=True)


def _tail(path: Path, line_count: int) -> str:
    if not path.exists():
        return ""
    with path.open(encoding="utf-8", errors="replace") as handle:
        return "".join(handle.readlines()[-line_count:])


def _age(timestamp: str | None) -> str:
    if not timestamp:
        return "-"
    try:
        then = datetime.fromisoformat(timestamp)
    except ValueError:
        return "?"
    seconds = max(0, int((datetime.now(UTC) - then).total_seconds()))
    return f"{seconds}s"


def _dashboard_text(state_root: Path) -> str:
    tasks = _list_tasks(state_root)
    if not tasks:
        return "No delegation tasks.\n"
    headers = (
        "TASK",
        "PROVIDER",
        "MODE",
        "STATE",
        "ELAPSED",
        "HEARTBEAT",
        "OUTPUT",
        "VERIFY",
        "ACTIVITY",
    )
    rows = [
        (
            str(item.get("task_id", "?")),
            str(item.get("provider", "?")),
            str(item.get("mode", "?")),
            str(item.get("state", "?")),
            f"{item.get('elapsed_seconds', 0)}s",
            _age(item.get("runner_heartbeat_at")),
            _age(item.get("provider_output_at")),
            str(item.get("verification_state", "pending")),
            str(item.get("latest_activity", "-")),
        )
        for item in tasks
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = ["  ".join(value.ljust(widths[index]) for index, value in enumerate(headers))]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-delegate",
        description="Dispatch one bounded task to CC or ZCode in an isolated copy.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="check provider CLIs without a model call")
    doctor.add_argument("--state-root", default=str(default_state_root()))

    start = subparsers.add_parser("start", help="validate and start one detached task")
    start.add_argument("--provider", choices=("cc", "zcode", "fake"), required=True)
    start.add_argument("--mode", choices=("review", "edit"), default="review")
    start.add_argument("--cwd", required=True)
    start.add_argument("--task", required=True)
    start.add_argument("--read-path", action="append", required=True)
    start.add_argument("--write-path", action="append")
    start.add_argument(
        "--verify",
        action="append",
        help='preapproved argv encoded as JSON, for example \'["pytest","-q"]\'',
    )
    start.add_argument("--timeout", type=int, default=900)
    start.add_argument("--max-turns", type=int, default=10)
    start.add_argument("--request-id")
    start.add_argument("--state-root", default=str(default_state_root()))
    start.add_argument("--dry-run", action="store_true")

    listing = subparsers.add_parser("list", help="list local tasks")
    listing.add_argument("--state-root", default=str(default_state_root()))

    status = subparsers.add_parser("status", help="print one task state")
    status.add_argument("task_id")
    status.add_argument("--state-root", default=str(default_state_root()))

    logs = subparsers.add_parser("logs", help="tail redacted provider output")
    logs.add_argument("task_id")
    logs.add_argument(
        "--stream",
        choices=("stdout", "stderr", "events", "runner"),
        default="stdout",
    )
    logs.add_argument("--lines", type=int, default=50)
    logs.add_argument("--state-root", default=str(default_state_root()))

    result = subparsers.add_parser("result", help="show the handoff or result JSON")
    result.add_argument("task_id")
    result.add_argument("--json", action="store_true")
    result.add_argument("--state-root", default=str(default_state_root()))

    stop = subparsers.add_parser("stop", help="request an idempotent task stop")
    stop.add_argument("task_id")
    stop.add_argument("--reason", default="requested by user")
    stop.add_argument("--state-root", default=str(default_state_root()))

    dashboard = subparsers.add_parser("dashboard", help="show a token-free local dashboard")
    dashboard.add_argument("--once", action="store_true")
    dashboard.add_argument("--interval", type=float, default=1.0)
    dashboard.add_argument("--state-root", default=str(default_state_root()))
    return parser


def _run_public_command(args: argparse.Namespace) -> int:
    state_root = Path(args.state_root).expanduser()
    if args.command == "doctor":
        _json_print({"checks": [check.to_dict() for check in doctor_checks()]})
        return 0
    if args.command == "start":
        return _start(args)
    if args.command == "list":
        _json_print({"tasks": _list_tasks(state_root)})
        return 0
    if args.command == "status":
        paths = _checked_paths(state_root, args.task_id)
        _json_print(read_json(paths.state))
        return 0
    if args.command == "logs":
        if args.lines <= 0:
            raise CliError("invalid_line_count", "--lines must be positive")
        paths = _checked_paths(state_root, args.task_id)
        selected = {
            "stdout": paths.stdout,
            "stderr": paths.stderr,
            "events": paths.events,
            "runner": paths.root / "runner.log",
        }[args.stream]
        sys.stdout.write(_tail(selected, args.lines))
        return 0
    if args.command == "result":
        paths = _checked_paths(state_root, args.task_id)
        selected = paths.result if args.json else paths.handoff
        if not selected.exists():
            raise CliError("result_not_ready", "the task result is not ready")
        if args.json:
            _json_print(read_json(selected))
        else:
            sys.stdout.write(selected.read_text(encoding="utf-8"))
        return 0
    if args.command == "stop":
        paths = _checked_paths(state_root, args.task_id)
        state = read_json(paths.state)
        if state.get("state") not in TERMINAL_STATES:
            request_stop(paths, args.reason)
        _json_print(
            {
                "task_id": args.task_id,
                "stop_requested": state.get("state") not in TERMINAL_STATES,
                "state": state.get("state"),
            }
        )
        return 0
    if args.command == "dashboard":
        if args.interval <= 0:
            raise CliError("invalid_interval", "--interval must be positive")
        while True:
            if not args.once:
                sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.write(_dashboard_text(state_root))
            sys.stdout.flush()
            if args.once:
                return 0
            time.sleep(args.interval)
    raise CliError("unknown_command", f"unsupported command: {args.command}")


def _run_internal(arguments: Sequence[str]) -> int | None:
    if not arguments or arguments[0] not in {"_run", "_guard", "_launch"}:
        return None
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("internal_command", choices=("_run", "_guard", "_launch"))
    parser.add_argument("--task-id")
    parser.add_argument("--state-root")
    parser.add_argument("--runner-pid", type=int)
    parser.add_argument("--provider-pgid", type=int)
    parser.add_argument("--ready-fd", type=int)
    parser.add_argument("--release-fd", type=int)
    parser.add_argument("--command-file")
    parser.add_argument("--cwd")
    args = parser.parse_args(arguments)
    if args.internal_command == "_guard":
        if args.runner_pid is None or args.provider_pgid is None:
            parser.error("_guard requires --runner-pid and --provider-pgid")
        return guard_process_group(args.runner_pid, args.provider_pgid, ready_fd=args.ready_fd)
    if args.internal_command == "_launch":
        if (
            args.runner_pid is None
            or args.release_fd is None
            or not args.command_file
            or not args.cwd
        ):
            parser.error(
                "_launch requires --runner-pid, --release-fd, --command-file, and --cwd"
            )
        return launch_provider(
            args.runner_pid,
            args.release_fd,
            Path(args.command_file),
            Path(args.cwd),
        )
    if not args.task_id or not args.state_root:
        parser.error("_run requires --task-id and --state-root")
    return run_task(Path(args.state_root).expanduser(), args.task_id)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    internal = _run_internal(arguments)
    if internal is not None:
        return internal
    parser = _build_parser()
    args = parser.parse_args(arguments)
    try:
        return _run_public_command(args)
    except (CliError, ValidationError) as exc:
        code = exc.code if isinstance(exc, CliError) else "validation_error"
        print(f"{code}: {exc}", file=sys.stderr)
        return 2
