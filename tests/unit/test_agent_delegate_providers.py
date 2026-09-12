from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.agent_delegate.core import TaskRequest, ValidationError, task_paths
from tools.agent_delegate.providers import (
    ProviderConfig,
    _extract_version,
    build_provider_argv,
    extract_final_result,
    parse_provider_line,
    provider_stdin,
)


def request(tmp_path: Path, *, provider: str = "cc", mode: str = "review") -> TaskRequest:
    return TaskRequest(
        task_id="task_0123456789ab",
        request_id="req-provider",
        provider=provider,
        mode=mode,
        source_cwd=str(tmp_path),
        task_text="Review README without changing it.",
        read_paths=("README.md",),
        write_paths=(),
        verify_commands=(),
        timeout_seconds=30,
        max_turns=4,
        created_at="2026-09-13T00:00:00+00:00",
    )


def config() -> ProviderConfig:
    return ProviderConfig(
        cc="/opt/homebrew/bin/claude",
        node="/opt/homebrew/bin/node",
        zcode_script="/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs",
        fake="/tmp/fake_agent_provider.py",
    )


def pair(argv: list[str], option: str) -> str:
    return argv[argv.index(option) + 1]


def test_cc_review_argv_is_restricted_and_noninteractive(tmp_path: Path) -> None:
    current = request(tmp_path)
    paths = task_paths(tmp_path / "state", current.task_id)

    argv = build_provider_argv(current, paths, config())

    assert argv[0] == "/opt/homebrew/bin/claude"
    assert "--restricted" in argv
    assert "--safe-mode" in argv
    assert pair(argv, "--permission-mode") == "plan"
    assert pair(argv, "--tools") == "Read,Glob,Grep"
    assert "Bash" in pair(argv, "--disallowedTools")
    assert pair(argv, "--output-format") == "stream-json"
    assert "--strict-mcp-config" in argv
    assert pair(argv, "--mcp-config") == '{"mcpServers":{}}'
    assert "--dangerously-skip-permissions" not in argv
    assert "--background" not in argv
    assert current.task_text not in argv
    assert provider_stdin(current) == current.task_text


def test_zcode_review_argv_never_uses_yolo(tmp_path: Path) -> None:
    current = request(tmp_path, provider="zcode")
    paths = task_paths(tmp_path / "state", current.task_id)

    argv = build_provider_argv(current, paths, config())

    assert argv[:2] == [config().node, config().zcode_script]
    assert pair(argv, "--mode") == "plan"
    assert "yolo" not in argv
    assert pair(argv, "--cwd") == str(paths.workspace)
    assert pair(argv, "--prompt") == current.task_text
    assert "--print" in argv
    assert "--json" in argv
    assert "Bash" in pair(argv, "--disallowed-tools")
    assert provider_stdin(current) is None


@pytest.mark.parametrize("provider", ["cc", "zcode"])
def test_real_provider_edit_mode_is_rejected(tmp_path: Path, provider: str) -> None:
    current = replace(
        request(tmp_path, provider=provider, mode="edit"),
        write_paths=("README.md",),
    )

    with pytest.raises(ValidationError, match="not enabled"):
        build_provider_argv(
            current,
            task_paths(tmp_path / "state", current.task_id),
            config(),
        )


def test_cc_result_parser_requires_result_event() -> None:
    lines = [json.dumps({"type": "assistant", "message": {"content": []}})]

    assert extract_final_result("cc", lines) is None

    lines.append(json.dumps({"type": "result", "result": "bounded review"}))
    assert extract_final_result("cc", lines) == "bounded review"


def test_zcode_parser_accepts_nested_structured_result_but_not_plain_text() -> None:
    lines = [
        "starting up",
        json.dumps({"type": "progress", "message": {"text": "reading"}}),
        json.dumps({"data": {"output": {"content": [{"text": "review done"}]}}}),
    ]

    assert extract_final_result("zcode", lines) == "review done"
    assert extract_final_result("zcode", ["plain final answer"]) is None
    assert parse_provider_line("zcode", "not-json") == {
        "activity": "provider output",
        "text": "not-json",
        "structured": False,
    }


def test_unknown_structured_event_does_not_invent_activity() -> None:
    event = parse_provider_line("cc", json.dumps({"type": "mystery", "value": 1}))

    assert event["activity"] == "provider event"
    assert event["structured"] is True


def test_zcode_doctor_version_uses_nested_cli_value() -> None:
    output = json.dumps({"cli": {"name": "zcode", "version": "0.16.3"}})

    assert _extract_version("zcode", output) == "0.16.3"
