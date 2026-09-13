from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools.agent_delegate.core import read_json, task_paths

SCRIPT = Path(__file__).parents[2] / "scripts" / "agent_delegate.py"
FAKE_PROVIDER = Path(__file__).parents[1] / "fixtures" / "fake_agent_provider.py"


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "README.md").write_text("source stays unchanged", encoding="utf-8")
    return root


@pytest.fixture
def cli(tmp_path: Path):
    state_root = tmp_path / "state"
    environment = os.environ.copy()
    environment["AGENT_DELEGATE_STATE_ROOT"] = str(state_root)
    environment["AGENT_DELEGATE_FAKE_BIN"] = str(FAKE_PROVIDER)

    def run(*arguments: str, timeout: float = 10) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=SCRIPT.parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    run.state_root = state_root
    return run


def start_args(source: Path, *, task: str = "scenario: normal") -> tuple[str, ...]:
    return (
        "start",
        "--provider",
        "fake",
        "--cwd",
        str(source),
        "--task",
        task,
        "--read-path",
        "README.md",
    )


def wait_for_terminal(state_root: Path, task_id: str, timeout: float = 5) -> dict:
    paths = task_paths(state_root, task_id)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if paths.state.exists():
            state = read_json(paths.state)
            if state.get("state") in {
                "completed",
                "failed",
                "stopped",
                "timed_out",
                "interrupted",
            }:
                return state
        time.sleep(0.05)
    raise AssertionError("task did not reach a terminal state")


def test_dry_run_never_spawns_provider(cli, source: Path) -> None:
    result = cli(
        "start",
        "--dry-run",
        "--provider",
        "cc",
        "--cwd",
        str(source),
        "--task",
        "Review README",
        "--read-path",
        "README.md",
    )

    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["would_start"] is False
    assert "--restricted" in body["argv"]
    assert not cli.state_root.exists()


def test_request_id_is_idempotent(cli, source: Path) -> None:
    first = cli(*start_args(source), "--request-id", "req-123")
    second = cli(*start_args(source), "--request-id", "req-123")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert json.loads(first.stdout)["task_id"] == json.loads(second.stdout)["task_id"]
    assert json.loads(second.stdout)["reused"] is True


def test_same_request_id_with_different_body_is_rejected(cli, source: Path) -> None:
    first = cli(*start_args(source), "--request-id", "req-123")
    result = cli(
        *start_args(source, task="scenario: empty"),
        "--request-id",
        "req-123",
    )

    assert first.returncode == 0, first.stderr
    assert result.returncode == 2
    assert "request_id_conflict" in result.stderr


def test_detached_fake_task_completes_after_start_returns(cli, source: Path) -> None:
    started = time.monotonic()
    result = cli(*start_args(source), "--request-id", "req-detached")
    duration = time.monotonic() - started

    assert result.returncode == 0, result.stderr
    assert duration < 5
    task_id = json.loads(result.stdout)["task_id"]
    state = wait_for_terminal(cli.state_root, task_id)
    assert state["state"] == "completed"
    assert (source / "README.md").read_text(encoding="utf-8") == "source stays unchanged"


def test_dashboard_once_contains_no_percentage(cli, source: Path) -> None:
    started = cli(*start_args(source), "--request-id", "req-dashboard")
    task_id = json.loads(started.stdout)["task_id"]
    wait_for_terminal(cli.state_root, task_id)

    result = cli("dashboard", "--once")

    assert result.returncode == 0, result.stderr
    assert task_id in result.stdout
    assert "%" not in result.stdout
    assert "completed" in result.stdout


def test_status_logs_and_result_are_read_only(cli, source: Path) -> None:
    started = cli(*start_args(source), "--request-id", "req-read")
    task_id = json.loads(started.stdout)["task_id"]
    wait_for_terminal(cli.state_root, task_id)

    status = cli("status", task_id)
    logs = cli("logs", task_id, "--lines", "5")
    result = cli("result", task_id)
    listing = cli("list")

    assert json.loads(status.stdout)["state"] == "completed"
    assert "fixture completed" in logs.stdout
    assert "## Conclusion" in result.stdout
    assert task_id in listing.stdout


def test_stop_is_idempotent(cli, source: Path) -> None:
    started = cli(
        *start_args(source, task="scenario: ignore-term"),
        "--request-id",
        "req-stop",
        "--timeout",
        "30",
    )
    task_id = json.loads(started.stdout)["task_id"]
    first = cli("stop", task_id)
    second = cli("stop", task_id)
    state = wait_for_terminal(cli.state_root, task_id, timeout=8)

    assert first.returncode == 0
    assert second.returncode == 0
    assert state["state"] == "stopped"


def test_real_provider_edit_mode_is_rejected_before_task_creation(cli, source: Path) -> None:
    result = cli(
        "start",
        "--provider",
        "cc",
        "--mode",
        "edit",
        "--cwd",
        str(source),
        "--task",
        "Change README",
        "--read-path",
        "README.md",
        "--write-path",
        "README.md",
    )

    assert result.returncode == 2
    assert "not enabled" in result.stderr
    assert not cli.state_root.exists()


def test_state_root_inside_source_is_rejected_before_copy(cli, source: Path) -> None:
    nested_state = source / ".delegate-state"

    result = cli(
        "start",
        "--dry-run",
        "--provider",
        "cc",
        "--cwd",
        str(source),
        "--task",
        "Review everything",
        "--read-path",
        ".",
        "--state-root",
        str(nested_state),
    )

    assert result.returncode == 2
    assert "state root" in result.stderr
    assert not nested_state.exists()


def test_provider_receives_the_full_task_contract(cli, source: Path) -> None:
    started = cli(
        *start_args(source, task="scenario: require-contract"),
        "--request-id",
        "req-contract",
    )
    task_id = json.loads(started.stdout)["task_id"]

    state = wait_for_terminal(cli.state_root, task_id)

    assert state["state"] == "completed"


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_guardian_kills_provider_if_runner_is_killed(cli, source: Path) -> None:
    started = cli(
        *start_args(source, task="scenario: ignore-term"),
        "--request-id",
        "req-guardian",
        "--timeout",
        "30",
    )
    task_id = json.loads(started.stdout)["task_id"]
    paths = task_paths(cli.state_root, task_id)
    deadline = time.monotonic() + 5
    state: dict = {}
    while time.monotonic() < deadline:
        state = read_json(paths.state)
        if state.get("runner_pid") and state.get("provider_pid"):
            break
        time.sleep(0.05)
    runner_pid = int(state["runner_pid"])
    provider_pid = int(state["provider_pid"])
    assert int(state["guardian_pid"]) > 0

    try:
        os.kill(runner_pid, signal.SIGKILL)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _process_is_alive(provider_pid):
            time.sleep(0.05)
        assert not _process_is_alive(provider_pid)
    finally:
        if _process_is_alive(provider_pid):
            os.killpg(provider_pid, signal.SIGKILL)
