"""Detached runner for one isolated delegation task."""

from __future__ import annotations

import difflib
import errno
import fcntl
import hashlib
import json
import os
import queue
import re
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from .core import (
    TaskPaths,
    TaskRequest,
    atomic_write_json,
    create_workspace_snapshot,
    diff_snapshots,
    read_json,
    redact_text,
    snapshot_tree,
    task_document,
    task_paths,
    validate_request,
)
from .providers import (
    ProviderConfig,
    build_provider_argv,
    extract_final_result,
    parse_provider_line,
    provider_stdin,
)

MAX_EVENT_BYTES = 256 * 1024
MAX_CAPTURED_LINES = 10_000
STOP_GRACE_SECONDS = 3.0
HEARTBEAT_SECONDS = 1.0
VERIFICATION_TIMEOUT_SECONDS = 120
_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _clean_output(text: str) -> str:
    return redact_text(_ANSI_RE.sub("", text))


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


def _append_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()


def _append_event(target: Path, value: dict[str, Any]) -> None:
    safe = json.loads(redact_text(json.dumps(value, ensure_ascii=False)))
    _append_text(target, json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")


def _workspace_lock(state_root: Path, source_cwd: str) -> tuple[int, Path]:
    canonical = str(Path(source_cwd).expanduser().resolve())
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    lock_path = state_root / "locks" / f"{digest}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(descriptor)
        raise
    return descriptor, lock_path


def _release_lock(descriptor: int) -> None:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _cc_settings_environment(home: str | None) -> dict[str, str]:
    if not home:
        return {}
    configured = os.environ.get("AGENT_DELEGATE_CC_SETTINGS")
    settings_path = (
        Path(configured).expanduser()
        if configured
        else Path(home) / ".claude/settings.json"
    )
    try:
        if settings_path.stat().st_size > 1024 * 1024:
            return {}
        value = read_json(settings_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    configured_environment = value.get("env") if isinstance(value, dict) else None
    if not isinstance(configured_environment, dict):
        return {}
    return {
        key: item
        for key, item in configured_environment.items()
        if isinstance(key, str)
        and isinstance(item, str)
        and key.startswith(("ANTHROPIC_", "CLAUDE_CODE_"))
    }


def _filtered_environment(*, provider_name: str | None = None) -> dict[str, str]:
    names = {
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "SHELL",
        "TERM",
    }
    environment = {name: os.environ[name] for name in names if name in os.environ}
    if provider_name == "cc":
        environment.update(_cc_settings_environment(environment.get("HOME")))
        environment.update(
            {
                name: value
                for name, value in os.environ.items()
                if name.startswith(("ANTHROPIC_", "CLAUDE_CODE_"))
            }
        )
    elif provider_name == "zcode":
        environment.update(
            {
                name: value
                for name, value in os.environ.items()
                if name.startswith(("ZAI_", "ZHIPUAI_"))
            }
        )
    if provider_name:
        environment.update(
            {
                name: os.environ[name]
                for name in (
                    "HTTP_PROXY",
                    "HTTPS_PROXY",
                    "NO_PROXY",
                    "http_proxy",
                    "https_proxy",
                    "no_proxy",
                )
                if name in os.environ
            }
        )
    return environment


def _stream_reader(
    stream: BinaryIO,
    channel: str,
    events: queue.Queue[tuple[str, bytes | None]],
) -> None:
    buffer = bytearray()
    read_chunk = getattr(stream, "read1", stream.read)
    try:
        while chunk := read_chunk(64 * 1024):
            buffer.extend(chunk)
            while True:
                newline = buffer.find(b"\n")
                if newline >= 0 and newline + 1 <= MAX_EVENT_BYTES:
                    size = newline + 1
                elif len(buffer) >= MAX_EVENT_BYTES:
                    size = MAX_EVENT_BYTES
                else:
                    break
                events.put((channel, bytes(buffer[:size])))
                del buffer[:size]
        if buffer:
            events.put((channel, bytes(buffer)))
    finally:
        events.put((channel, None))
        stream.close()


def _provider_input_writer(stream: BinaryIO, prompt: str | None) -> None:
    try:
        if prompt is not None:
            stream.write(prompt.encode("utf-8"))
            stream.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        stream.close()


def _group_exists(process_group_id: int) -> bool | None:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    return True


def _signal_group(process_group_id: int, selected_signal: signal.Signals) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process_group_id, selected_signal)


def _cleanup_group(process_group_id: int, grace_seconds: float) -> str:
    exists = _group_exists(process_group_id)
    if exists is False:
        return "confirmed"
    if exists is None:
        return "unknown"
    _signal_group(process_group_id, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if _group_exists(process_group_id) is False:
            return "confirmed"
        time.sleep(0.02)
    _signal_group(process_group_id, signal.SIGKILL)
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        exists = _group_exists(process_group_id)
        if exists is False:
            return "confirmed"
        if exists is None:
            return "unknown"
        time.sleep(0.02)
    return "incomplete"


def guard_process_group(
    runner_pid: int,
    provider_process_group_id: int,
    grace_seconds: float = STOP_GRACE_SECONDS,
    ready_fd: int | None = None,
) -> int:
    """Independently stop the provider if this guardian loses its runner parent."""

    if ready_fd is not None:
        try:
            os.write(ready_fd, b"1")
        except OSError:
            return 1
        finally:
            with suppress(OSError):
                os.close(ready_fd)
    while True:
        exists = _group_exists(provider_process_group_id)
        if exists is False:
            return 0
        if exists is None:
            return 1
        if os.getppid() != runner_pid:
            return (
                0
                if _cleanup_group(provider_process_group_id, grace_seconds) == "confirmed"
                else 1
            )
        time.sleep(0.1)


def _start_guardian(provider_process_group_id: int) -> subprocess.Popen[bytes]:
    script = Path(__file__).resolve().parents[2] / "scripts" / "agent_delegate.py"
    ready_read_fd, ready_write_fd = os.pipe()
    try:
        guardian = subprocess.Popen(
            [
                sys.executable,
                str(script),
                "_guard",
                "--runner-pid",
                str(os.getpid()),
                "--provider-pgid",
                str(provider_process_group_id),
                "--ready-fd",
                str(ready_write_fd),
            ],
            cwd=script.parents[1],
            env=_filtered_environment(),
            pass_fds=(ready_write_fd,),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError:
        os.close(ready_read_fd)
        raise
    finally:
        os.close(ready_write_fd)
    readable, _, _ = select.select([ready_read_fd], [], [], 2.0)
    ready = os.read(ready_read_fd, 1) if readable else b""
    os.close(ready_read_fd)
    if not ready or guardian.poll() is not None:
        with suppress(ProcessLookupError):
            guardian.terminate()
        with suppress(subprocess.TimeoutExpired):
            guardian.wait(timeout=1)
        raise OSError("guardian failed to become ready")
    return guardian


def launch_provider(
    runner_pid: int,
    release_fd: int,
    command_file: Path,
    cwd: Path,
) -> int:
    """Wait inertly for the runner to establish a guardian, then exec the provider."""

    try:
        while True:
            if os.getppid() != runner_pid:
                return 1
            readable, _, _ = select.select([release_fd], [], [], 0.1)
            if not readable:
                continue
            released = os.read(release_fd, 1)
            if not released or os.getppid() != runner_pid:
                return 1
            command_document = read_json(command_file)
            if not isinstance(command_document, dict):
                raise ValueError("invalid provider command document")
            command = command_document.get("argv")
            if not isinstance(command, list) or not command or not all(
                isinstance(part, str) and part for part in command
            ):
                raise ValueError("invalid provider command")
            os.chdir(cwd)
            os.execvpe(command[0], command, os.environ)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        message = f"provider launcher failed: {type(exc).__name__}\n".encode()
        with suppress(OSError):
            os.write(2, message)
        return 127
    finally:
        with suppress(OSError):
            os.close(release_fd)


def _start_blocked_provider(
    argv: list[str],
    paths: TaskPaths,
    provider_environment: dict[str, str],
) -> tuple[subprocess.Popen[bytes], int]:
    """Start an inert launcher that cannot invoke the provider until released."""

    command_file = paths.root / "provider-command.json"
    atomic_write_json(command_file, {"argv": argv})
    release_read_fd, release_write_fd = os.pipe()
    script = Path(__file__).resolve().parents[2] / "scripts" / "agent_delegate.py"
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                str(script),
                "_launch",
                "--runner-pid",
                str(os.getpid()),
                "--release-fd",
                str(release_read_fd),
                "--command-file",
                str(command_file.resolve()),
                "--cwd",
                str(paths.workspace.resolve()),
            ],
            cwd=script.parents[1],
            env=provider_environment,
            pass_fds=(release_read_fd,),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            start_new_session=True,
            close_fds=True,
            shell=False,
        )
    except OSError:
        os.close(release_write_fd)
        raise
    finally:
        os.close(release_read_fd)
    return process, release_write_fd


def _relative_contains(parent_value: str, child_value: str) -> bool:
    parent = Path(parent_value)
    child = Path(child_value)
    return parent == Path(".") or child == parent or parent in child.parents


def _scope_violations(
    request: TaskRequest, changes: dict[str, list[str]]
) -> list[str]:
    changed = sorted(set().union(*changes.values()))
    if request.mode == "review":
        return changed
    return [
        path
        for path in changed
        if not any(_relative_contains(write_path, path) for write_path in request.write_paths)
    ]


def _file_text(path: Path) -> list[str] | None:
    if not path.is_file():
        return []
    data = path.read_bytes()
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace").splitlines(keepends=True)


def _build_patch(request: TaskRequest, paths: TaskPaths, changes: dict[str, list[str]]) -> str:
    source = Path(request.source_cwd).expanduser()
    sections: list[str] = []
    for relative in sorted(set().union(*changes.values())):
        original = _file_text(source / relative)
        updated = _file_text(paths.workspace / relative)
        if original is None or updated is None:
            sections.append(f"Binary file changed: {relative}\n")
            continue
        sections.extend(
            difflib.unified_diff(
                original,
                updated,
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
    return _clean_output("".join(sections))


def _run_verification(request: TaskRequest, paths: TaskPaths) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for command in request.verify_commands:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                list(command),
                cwd=paths.workspace,
                env=_filtered_environment(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=VERIFICATION_TIMEOUT_SECONDS,
                shell=False,
                check=False,
            )
            exit_code: int | None = completed.returncode
            stdout = _clean_output(completed.stdout)[:MAX_EVENT_BYTES]
            stderr = _clean_output(completed.stderr)[:MAX_EVENT_BYTES]
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            exit_code = None
            stdout = _clean_output(exc.stdout or "")[:MAX_EVENT_BYTES]
            stderr = _clean_output(exc.stderr or "")[:MAX_EVENT_BYTES]
            timed_out = True
        except OSError as exc:
            exit_code = None
            stdout = ""
            stderr = f"{type(exc).__name__}: verification executable unavailable"
            timed_out = False
        results.append(
            {
                "argv": list(command),
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": timed_out,
                "duration_seconds": round(time.monotonic() - started, 3),
            }
        )
    state = (
        "not_requested"
        if not results
        else "passed"
        if all(item["exit_code"] == 0 and not item["timed_out"] for item in results)
        else "failed"
    )
    evidence = {"state": state, "commands": results}
    atomic_write_json(paths.verification, evidence)
    return evidence


def _format_changes(changes: dict[str, list[str]]) -> str:
    entries = [
        f"- {kind}: {path}"
        for kind in ("added", "modified", "deleted")
        for path in changes[kind]
    ]
    return "\n".join(entries) if entries else "- No file changes observed."


def _write_handoff(
    paths: TaskPaths,
    *,
    final_answer: str | None,
    changes: dict[str, list[str]],
    verification: dict[str, Any],
    reason: str | None,
) -> None:
    conclusion = final_answer or "The provider did not return a structured final answer."
    unresolved = f"- {reason}" if reason else "- None reported by the runner."
    handoff = (
        "# Agent task handoff\n\n"
        "## Conclusion\n\n"
        f"{conclusion}\n\n"
        "## Provider-reported changes\n\n"
        "- See the provider conclusion above; claims are not treated as filesystem evidence.\n\n"
        "## Runner-observed changes\n\n"
        f"{_format_changes(changes)}\n\n"
        "## Verification evidence\n\n"
        f"- State: {verification['state']}\n\n"
        "## Unresolved items\n\n"
        f"{unresolved}\n\n"
        "## Next step\n\n"
        "- Codex should review this handoff and only the relevant evidence "
        "before any source change.\n"
    )
    _atomic_write_text(paths.handoff, _clean_output(handoff))


def _update_state(paths: TaskPaths, document: dict[str, Any], **changes: Any) -> None:
    document.update(changes)
    atomic_write_json(paths.state, document)


def _finish_before_provider(
    request: TaskRequest,
    paths: TaskPaths,
    state: dict[str, Any],
    *,
    started_monotonic: float,
) -> int:
    changes = {"added": [], "modified": [], "deleted": []}
    verification = {"state": "skipped", "commands": []}
    atomic_write_json(paths.verification, verification)
    _atomic_write_text(paths.patch, "")
    result = {
        "task_id": request.task_id,
        "provider": request.provider,
        "mode": request.mode,
        "state": "stopped",
        "reason": "stop_requested",
        "provider_exit_code": None,
        "final_answer": None,
        "changes": changes,
        "scope_violations": [],
        "verification": verification,
        "cleanup_status": "confirmed",
        "review_status": "not_ready",
    }
    atomic_write_json(paths.result, result)
    _write_handoff(
        paths,
        final_answer=None,
        changes=changes,
        verification=verification,
        reason="stop_requested",
    )
    finished_at = _now()
    _update_state(
        paths,
        state,
        state="stopped",
        reason="stop_requested",
        started_at=state.get("started_at", finished_at),
        finished_at=finished_at,
        runner_pid=os.getpid(),
        runner_heartbeat_at=finished_at,
        latest_activity="task stopped before provider start",
        elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
        cleanup_status="confirmed",
        changes=changes,
        scope_violations=[],
        verification_state="skipped",
        review_status="not_ready",
    )
    return 1


def _execute_locked(
    state_root: Path,
    request: TaskRequest,
    paths: TaskPaths,
) -> int:
    state = read_json(paths.state) if paths.state.exists() else {"task_id": request.task_id}
    started_at = _now()
    started_monotonic = time.monotonic()
    if paths.stop_request.exists():
        return _finish_before_provider(
            request,
            paths,
            state,
            started_monotonic=started_monotonic,
        )
    _update_state(
        paths,
        state,
        state="running",
        reason=None,
        started_at=started_at,
        finished_at=None,
        runner_pid=os.getpid(),
        runner_heartbeat_at=started_at,
        provider_output_at=None,
        latest_activity="creating isolated workspace",
        verification_state="pending",
        cleanup_status="pending",
    )

    if not paths.workspace.exists():
        create_workspace_snapshot(request, paths)
    baseline = read_json(paths.baseline)
    canonical_task = task_document(request)
    _atomic_write_text(paths.task_md, canonical_task)
    if paths.stop_request.exists():
        return _finish_before_provider(
            request,
            paths,
            state,
            started_monotonic=started_monotonic,
        )
    paths.events.touch(exist_ok=True)
    paths.stdout.touch(exist_ok=True)
    paths.stderr.touch(exist_ok=True)

    provider_request = replace(request, task_text=canonical_task)
    argv = build_provider_argv(
        provider_request, paths, ProviderConfig.from_environment()
    )
    process, release_fd = _start_blocked_provider(
        argv,
        paths,
        _filtered_environment(provider_name=request.provider),
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    process_group_id = process.pid
    try:
        guardian = _start_guardian(process_group_id)
    except OSError:
        os.close(release_fd)
        _cleanup_group(process_group_id, 0.1)
        process.wait(timeout=2)
        raise
    try:
        output_events: queue.Queue[tuple[str, bytes | None]] = queue.Queue(maxsize=512)
        threads = [
            threading.Thread(
                target=_stream_reader,
                args=(process.stdout, "stdout", output_events),
                daemon=True,
            ),
            threading.Thread(
                target=_stream_reader,
                args=(process.stderr, "stderr", output_events),
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()

        prompt = provider_stdin(provider_request)
        input_thread = threading.Thread(
            target=_provider_input_writer,
            args=(process.stdin, prompt),
            daemon=True,
        )
        input_thread.start()
        _update_state(
            paths,
            state,
            provider_pid=process.pid,
            guardian_pid=guardian.pid,
            latest_activity="provider starting under guardian",
        )
        os.write(release_fd, b"1")
        os.close(release_fd)
        release_fd = -1
        _update_state(paths, state, latest_activity="provider started")
    except Exception:
        if release_fd >= 0:
            with suppress(OSError):
                os.close(release_fd)
        _cleanup_group(process_group_id, 0.1)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=2)
        with suppress(ProcessLookupError):
            guardian.terminate()
        with suppress(subprocess.TimeoutExpired):
            guardian.wait(timeout=1)
        raise

    stdout_lines: deque[str] = deque(maxlen=MAX_CAPTURED_LINES)
    finished_streams: set[str] = set()
    deadline = started_monotonic + request.timeout_seconds
    next_heartbeat = time.monotonic() + HEARTBEAT_SECONDS
    terminal_intent: str | None = None
    termination_started: float | None = None
    killed = False

    while len(finished_streams) < 2 or process.poll() is None or not output_events.empty():
        now = time.monotonic()
        if terminal_intent is None and paths.stop_request.exists():
            terminal_intent = "stopped"
        if terminal_intent is None and now >= deadline:
            terminal_intent = "timed_out"
        if terminal_intent is not None and process.poll() is None and termination_started is None:
            _update_state(
                paths,
                state,
                state="stopping",
                latest_activity=f"stopping provider: {terminal_intent}",
            )
            _signal_group(process_group_id, signal.SIGTERM)
            termination_started = now
        if (
            termination_started is not None
            and not killed
            and process.poll() is None
            and now - termination_started >= STOP_GRACE_SECONDS
        ):
            _signal_group(process_group_id, signal.SIGKILL)
            killed = True

        try:
            channel, chunk = output_events.get(timeout=0.05)
        except queue.Empty:
            channel = ""
            chunk = b""
        if chunk is None:
            finished_streams.add(channel)
        elif chunk:
            text = _clean_output(chunk.decode("utf-8", errors="replace"))
            target = paths.stdout if channel == "stdout" else paths.stderr
            _append_text(target, text)
            if channel == "stdout":
                stdout_lines.append(text.rstrip("\r\n"))
                parsed = parse_provider_line(request.provider, text)
                activity = parsed["activity"]
            else:
                activity = "provider stderr"
            timestamp = _now()
            _append_event(
                paths.events,
                {"at": timestamp, "stream": channel, "text": text.rstrip("\r\n")},
            )
            _update_state(
                paths,
                state,
                provider_output_at=timestamp,
                latest_activity=activity,
                runner_heartbeat_at=timestamp,
                elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
            )
            next_heartbeat = time.monotonic() + HEARTBEAT_SECONDS
        if time.monotonic() >= next_heartbeat:
            _update_state(
                paths,
                state,
                runner_heartbeat_at=_now(),
                elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
            )
            next_heartbeat = time.monotonic() + HEARTBEAT_SECONDS

    exit_code = process.wait()
    input_thread.join(timeout=0.2)
    for thread in threads:
        thread.join(timeout=0.2)
    cleanup_status = _cleanup_group(process_group_id, STOP_GRACE_SECONDS)
    try:
        guardian.wait(timeout=1)
    except subprocess.TimeoutExpired:
        guardian.terminate()
        guardian.wait(timeout=1)

    after = snapshot_tree(paths.workspace)
    changes = diff_snapshots(baseline, after)
    scope_violations = _scope_violations(request, changes)
    _atomic_write_text(paths.patch, _build_patch(request, paths, changes))
    final_answer = extract_final_result(request.provider, list(stdout_lines))

    safe_to_verify = (
        terminal_intent is None
        and cleanup_status == "confirmed"
        and exit_code == 0
        and final_answer is not None
        and not scope_violations
    )
    if not safe_to_verify:
        verification = {"state": "skipped", "commands": []}
        atomic_write_json(paths.verification, verification)
    else:
        verification = _run_verification(request, paths)

    terminal_state = "completed"
    reason: str | None = None
    if terminal_intent is not None:
        terminal_state = terminal_intent
        reason = "stop_requested" if terminal_intent == "stopped" else "timeout"
    elif cleanup_status != "confirmed":
        terminal_state = "failed"
        reason = "cleanup_incomplete"
    elif exit_code != 0:
        terminal_state = "failed"
        reason = "provider_exit_nonzero"
    elif final_answer is None:
        terminal_state = "failed"
        reason = "result_missing"
    elif scope_violations:
        terminal_state = "failed"
        reason = "scope_violation"
    elif verification["state"] == "failed":
        terminal_state = "failed"
        reason = "verification_failed"

    result = {
        "task_id": request.task_id,
        "provider": request.provider,
        "mode": request.mode,
        "state": terminal_state,
        "reason": reason,
        "provider_exit_code": exit_code,
        "final_answer": final_answer,
        "changes": changes,
        "scope_violations": scope_violations,
        "verification": verification,
        "cleanup_status": cleanup_status,
        "review_status": "pending" if terminal_state == "completed" else "not_ready",
    }
    atomic_write_json(paths.result, result)
    _write_handoff(
        paths,
        final_answer=final_answer,
        changes=changes,
        verification=verification,
        reason=reason,
    )
    finished_at = _now()
    _update_state(
        paths,
        state,
        state=terminal_state,
        reason=reason,
        provider_exit_code=exit_code,
        finished_at=finished_at,
        runner_heartbeat_at=finished_at,
        elapsed_seconds=round(time.monotonic() - started_monotonic, 1),
        cleanup_status=cleanup_status,
        changes=changes,
        scope_violations=scope_violations,
        verification_state=verification["state"],
        review_status="pending" if terminal_state == "completed" else "not_ready",
        latest_activity=f"task {terminal_state}",
    )
    return 0 if terminal_state == "completed" else 1


def run_task(state_root: Path, task_id: str) -> int:
    """Run one queued task and return zero only for a verified completion."""

    paths = task_paths(Path(state_root), task_id)
    request = TaskRequest.from_dict(read_json(paths.request))
    validate_request(request)
    lock_descriptor: int | None = None
    try:
        try:
            lock_descriptor, _ = _workspace_lock(Path(state_root), request.source_cwd)
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                raise
            state = read_json(paths.state)
            _update_state(
                paths,
                state,
                state="failed",
                reason="workspace_busy",
                finished_at=_now(),
                latest_activity="workspace is already running another task",
            )
            return 1
        return _execute_locked(Path(state_root), request, paths)
    except Exception as exc:
        state = read_json(paths.state) if paths.state.exists() else {"task_id": task_id}
        _update_state(
            paths,
            state,
            state="failed",
            reason="runner_error",
            error_type=type(exc).__name__,
            finished_at=_now(),
            latest_activity="runner failed",
        )
        return 1
    finally:
        if lock_descriptor is not None:
            _release_lock(lock_descriptor)


def request_stop(paths: TaskPaths, reason: str = "requested by user") -> None:
    """Idempotently ask the owning runner to stop its provider process group."""

    if paths.stop_request.exists():
        return
    atomic_write_json(paths.stop_request, {"requested_at": _now(), "reason": redact_text(reason)})


def _pid_is_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def recover_interrupted_tasks(state_root: Path) -> list[str]:
    """Mark orphaned tasks and record whether their guardian finished cleanup."""

    recovered: list[str] = []
    tasks_root = Path(state_root) / "tasks"
    if not tasks_root.exists():
        return recovered
    for state_path in tasks_root.glob("task_*/state.json"):
        state = read_json(state_path)
        if state.get("state") not in {"running", "stopping"} or _pid_is_alive(
            state.get("runner_pid")
        ):
            continue
        paths = task_paths(Path(state_root), state_path.parent.name)
        provider_pid = state.get("provider_pid")
        cleanup_status = "confirmed"
        if isinstance(provider_pid, int):
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline and _group_exists(provider_pid) is True:
                time.sleep(0.05)
            cleanup_status = (
                "confirmed" if _group_exists(provider_pid) is False else "unknown"
            )
        _update_state(
            paths,
            state,
            state="interrupted",
            reason="runner_missing",
            cleanup_status=cleanup_status,
            finished_at=_now(),
            latest_activity="runner is no longer alive",
        )
        recovered.append(state_path.parent.name)
    return sorted(recovered)
