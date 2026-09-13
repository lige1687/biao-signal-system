from __future__ import annotations

import json
import os
import select
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.agent_delegate.core import (
    TaskPaths,
    TaskRequest,
    atomic_write_json,
    read_json,
    task_paths,
)
from tools.agent_delegate.runner import (
    _filtered_environment,
    _start_blocked_provider,
    recover_interrupted_tasks,
    request_stop,
    run_task,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "fake_agent_provider.py"


@dataclass(frozen=True)
class PreparedTask:
    state_root: Path
    task_id: str
    paths: TaskPaths
    source: Path


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_DELEGATE_FAKE_BIN", str(FIXTURE))


@pytest.fixture
def task_factory(tmp_path: Path):
    counter = 0

    def prepare(
        *,
        scenario: str = "normal",
        mode: str = "review",
        write_paths: tuple[str, ...] = (),
        timeout_seconds: int = 10,
        verify_commands: tuple[tuple[str, ...], ...] = (),
        task_text: str | None = None,
    ) -> PreparedTask:
        nonlocal counter
        counter += 1
        task_id = f"task_{counter:012x}"
        source = tmp_path / f"source-{counter}"
        (source / "allowed").mkdir(parents=True)
        (source / "outside").mkdir()
        (source / "allowed" / "keep.txt").write_text("original", encoding="utf-8")
        (source / "outside" / "forbidden.txt").write_text("original", encoding="utf-8")
        state_root = tmp_path / "state"
        paths = task_paths(state_root, task_id)
        paths.root.mkdir(parents=True)
        request = TaskRequest(
            task_id=task_id,
            request_id=f"req-{counter}",
            provider="fake",
            mode=mode,
            source_cwd=str(source),
            task_text=task_text or f"scenario: {scenario}",
            read_paths=("allowed", "outside"),
            write_paths=write_paths,
            verify_commands=verify_commands,
            timeout_seconds=timeout_seconds,
            max_turns=3,
            created_at="2026-09-13T00:00:00+00:00",
        )
        atomic_write_json(paths.request, request.to_dict())
        atomic_write_json(
            paths.state,
            {
                "task_id": task_id,
                "provider": "fake",
                "mode": mode,
                "state": "queued",
                "created_at": request.created_at,
            },
        )
        return PreparedTask(state_root, task_id, paths, source)

    return prepare


def test_exit_zero_without_result_is_failed(task_factory) -> None:
    task = task_factory(scenario="empty")

    assert run_task(task.state_root, task.task_id) == 1

    state = read_json(task.paths.state)
    assert state["state"] == "failed"
    assert state["reason"] == "result_missing"
    assert task.paths.result.is_file()
    assert task.paths.handoff.is_file()


def test_scope_violation_cannot_complete(task_factory) -> None:
    task = task_factory(
        mode="edit",
        write_paths=("allowed",),
        scenario="write-outside",
    )

    assert run_task(task.state_root, task.task_id) == 1

    state = read_json(task.paths.state)
    assert state["state"] == "failed"
    assert state["reason"] == "scope_violation"
    assert state["scope_violations"] == ["outside/forbidden.txt"]
    assert (
        task.source / "outside" / "forbidden.txt"
    ).read_text(encoding="utf-8") == "original"


def test_scope_violation_skips_verification_commands(task_factory) -> None:
    task = task_factory(
        mode="edit",
        write_paths=("allowed",),
        scenario="write-outside",
        verify_commands=(("touch", "verification-ran"),),
    )

    assert run_task(task.state_root, task.task_id) == 1

    assert not (task.paths.workspace / "verification-ran").exists()
    assert read_json(task.paths.verification)["state"] == "skipped"


def test_timeout_escalates_and_records_cleanup(
    task_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tools.agent_delegate.runner.STOP_GRACE_SECONDS", 0.1)
    task = task_factory(scenario="ignore-term", timeout_seconds=1)

    assert run_task(task.state_root, task.task_id) == 1

    state = read_json(task.paths.state)
    assert state["state"] == "timed_out"
    assert state["cleanup_status"] == "confirmed"


def test_large_stdin_cannot_block_timeout(
    task_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tools.agent_delegate.runner.STOP_GRACE_SECONDS", 0.1)
    task = task_factory(
        scenario="block-stdin",
        task_text="scenario: block-stdin\n" + ("x" * (1024 * 1024)),
        timeout_seconds=1,
    )

    started = time.monotonic()
    assert run_task(task.state_root, task.task_id) == 1

    assert time.monotonic() - started < 5
    assert read_json(task.paths.state)["state"] == "timed_out"


def test_blocked_launcher_cannot_invoke_provider_before_release(task_factory) -> None:
    task = task_factory()
    task.paths.workspace.mkdir(parents=True)
    process, release_fd = _start_blocked_provider(
        [sys.executable, str(FIXTURE), "--scenario", "normal"],
        task.paths,
        _filtered_environment(),
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.close()

    try:
        readable, _, _ = select.select([process.stdout], [], [], 0.25)
        assert readable == []
        assert process.poll() is None

        os.write(release_fd, b"1")
        os.close(release_fd)
        release_fd = -1
        stdout = process.stdout.read().decode()
        assert process.wait(timeout=3) == 0
        assert '"type": "result"' in stdout
    finally:
        if release_fd >= 0:
            os.close(release_fd)
        if process.poll() is None:
            os.killpg(process.pid, 9)
            process.wait(timeout=3)


def test_large_stderr_does_not_deadlock_and_is_bounded(task_factory) -> None:
    task = task_factory(scenario="stderr-flood")

    assert run_task(task.state_root, task.task_id) == 0

    assert read_json(task.paths.state)["state"] == "completed"
    assert task.paths.stderr.stat().st_size <= 1024 * 1024 + 4096


def test_partial_json_line_is_reassembled(task_factory) -> None:
    task = task_factory(scenario="partial-json")

    assert run_task(task.state_root, task.task_id) == 0

    assert read_json(task.paths.result)["final_answer"] == "partial line assembled"


def test_success_requires_verification_and_preserves_source(task_factory) -> None:
    task = task_factory(
        scenario="write-inside",
        mode="edit",
        write_paths=("allowed",),
        verify_commands=(("test", "-f", "allowed/generated.txt"),),
    )

    assert run_task(task.state_root, task.task_id) == 0

    state = read_json(task.paths.state)
    assert state["state"] == "completed"
    assert state["verification_state"] == "passed"
    assert state["review_status"] == "pending"
    assert not (task.source / "allowed" / "generated.txt").exists()
    assert read_json(task.paths.verification)["commands"][0]["exit_code"] == 0


def test_failed_verification_cannot_complete(task_factory) -> None:
    task = task_factory(verify_commands=(("false",),))

    assert run_task(task.state_root, task.task_id) == 1

    state = read_json(task.paths.state)
    assert state["reason"] == "verification_failed"
    assert state["verification_state"] == "failed"


def test_logs_are_redacted_before_write(task_factory) -> None:
    task = task_factory(scenario="secret")

    assert run_task(task.state_root, task.task_id) == 0

    log = task.paths.stderr.read_text(encoding="utf-8")
    assert "sk-fixture-secret" not in log
    assert "[REDACTED]" in log


def test_stop_request_ends_running_process_group(
    task_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tools.agent_delegate.runner.STOP_GRACE_SECONDS", 0.1)
    task = task_factory(scenario="ignore-term", timeout_seconds=30)
    result: list[int] = []
    worker = threading.Thread(
        target=lambda: result.append(run_task(task.state_root, task.task_id))
    )
    worker.start()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = read_json(task.paths.state)
        if state.get("provider_pid"):
            break
        time.sleep(0.02)

    request_stop(task.paths, "test stop")
    worker.join(timeout=5)

    assert result == [1]
    state = read_json(task.paths.state)
    assert state["state"] == "stopped"
    assert state["cleanup_status"] == "confirmed"


def test_queued_stop_never_starts_provider(task_factory) -> None:
    task = task_factory(scenario="normal")
    request_stop(task.paths, "cancel before start")

    assert run_task(task.state_root, task.task_id) == 1

    state = read_json(task.paths.state)
    assert state["state"] == "stopped"
    assert "provider_pid" not in state
    assert not task.paths.workspace.exists()
    assert task.paths.result.is_file()


def test_recovery_marks_only_orphaned_active_tasks(task_factory) -> None:
    queued = task_factory()
    orphaned = task_factory()
    orphaned_state = read_json(orphaned.paths.state)
    orphaned_state.update({"state": "running", "runner_pid": 999_999_999})
    atomic_write_json(orphaned.paths.state, orphaned_state)

    recovered = recover_interrupted_tasks(orphaned.state_root)

    assert recovered == [orphaned.task_id]
    assert read_json(orphaned.paths.state)["state"] == "interrupted"
    assert read_json(orphaned.paths.state)["cleanup_status"] == "confirmed"
    assert read_json(queued.paths.state)["state"] == "queued"


def test_cc_provider_loads_only_required_runtime_env_from_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "private-token",
                    "ANTHROPIC_BASE_URL": "https://provider.invalid",
                    "IWENCAI_API_KEY": "must-not-leak",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in tuple(os.environ):
        if name.startswith(("ANTHROPIC_", "CLAUDE_CODE_")):
            monkeypatch.delenv(name)

    cc_environment = _filtered_environment(provider_name="cc")
    zcode_environment = _filtered_environment(provider_name="zcode")

    assert cc_environment["ANTHROPIC_AUTH_TOKEN"] == "private-token"
    assert cc_environment["ANTHROPIC_BASE_URL"] == "https://provider.invalid"
    assert "IWENCAI_API_KEY" not in cc_environment
    assert "ANTHROPIC_AUTH_TOKEN" not in zcode_environment
