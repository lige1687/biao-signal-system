"""Guarded command builders and structured-output parsers for providers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import TaskPaths, TaskRequest, ValidationError, read_json

DEFAULT_CC = "/opt/homebrew/bin/claude"
DEFAULT_NODE = "/opt/homebrew/Cellar/node@22/22.22.1_1/bin/node"
DEFAULT_ZCODE = "/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    cc: str
    node: str
    zcode_script: str
    fake: str | None = None

    @classmethod
    def from_environment(cls) -> ProviderConfig:
        return cls(
            cc=os.environ.get("AGENT_DELEGATE_CC_BIN", DEFAULT_CC),
            node=os.environ.get("AGENT_DELEGATE_NODE_BIN", DEFAULT_NODE),
            zcode_script=os.environ.get("AGENT_DELEGATE_ZCODE_SCRIPT", DEFAULT_ZCODE),
            fake=os.environ.get("AGENT_DELEGATE_FAKE_BIN"),
        )


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    provider: str
    ok: bool
    version: str | None
    detail: str
    command: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ok": self.ok,
            "version": self.version,
            "detail": self.detail,
            "command": list(self.command),
        }


def _run_doctor_command(command: list[str], *, provider: str) -> DoctorCheck:
    executable = Path(command[0])
    if not executable.is_file() or not os.access(executable, os.X_OK):
        return DoctorCheck(
            provider=provider,
            ok=False,
            version=None,
            detail=f"executable not found: {executable}",
            command=tuple(command),
        )
    if provider == "zcode" and not Path(command[1]).is_file():
        return DoctorCheck(
            provider=provider,
            ok=False,
            version=None,
            detail=f"script not found: {command[1]}",
            command=tuple(command),
        )
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            env=_doctor_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return DoctorCheck(
            provider=provider,
            ok=False,
            version=None,
            detail=f"doctor command failed: {type(exc).__name__}",
            command=tuple(command),
        )

    output = (completed.stdout or completed.stderr).strip()
    version = _extract_version(provider, output)
    return DoctorCheck(
        provider=provider,
        ok=completed.returncode == 0,
        version=version,
        detail=(output[:500] if output else f"exit code {completed.returncode}"),
        command=tuple(command),
    )


def _doctor_environment() -> dict[str, str]:
    keep = ("HOME", "PATH", "LANG", "LC_ALL", "TMPDIR")
    return {name: os.environ[name] for name in keep if name in os.environ}


def _extract_version(provider: str, output: str) -> str | None:
    if not output:
        return None
    if provider == "zcode":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            value = None
        if isinstance(value, dict):
            for key in ("version", "cliVersion", "packageVersion"):
                found = value.get(key)
                if isinstance(found, str) and found:
                    return found
            cli = value.get("cli")
            if isinstance(cli, dict):
                found = cli.get("version")
                if isinstance(found, str) and found:
                    return found
    return output.splitlines()[0][:120]


def doctor_checks(config: ProviderConfig | None = None) -> list[DoctorCheck]:
    """Check local binaries without prompting or invoking a model."""

    selected = config or ProviderConfig.from_environment()
    cc_check = _run_doctor_command([selected.cc, "--version"], provider="cc")
    zcode_check = _run_doctor_command(
        [selected.node, selected.zcode_script, "doctor", "--json"],
        provider="zcode",
    )
    configured_path = os.environ.get("AGENT_DELEGATE_ZCODE_CONFIG")
    home = os.environ.get("HOME")
    zcode_config = (
        Path(configured_path).expanduser()
        if configured_path
        else Path(home) / ".zcode" / "cli" / "config.json"
        if home
        else None
    )
    has_zcode_model = False
    if zcode_config is not None:
        try:
            value = read_json(zcode_config)
        except (OSError, ValueError, json.JSONDecodeError):
            value = None
        model = value.get("model") if isinstance(value, dict) else None
        main_model = model.get("main") if isinstance(model, dict) else None
        has_zcode_model = (
            isinstance(main_model, dict)
            and isinstance(main_model.get("provider"), str)
            and bool(main_model["provider"].strip())
            and isinstance(main_model.get("model"), str)
            and bool(main_model["model"].strip())
        )
    if zcode_check.ok and not has_zcode_model:
        location = str(zcode_config) if zcode_config is not None else "~/.zcode/cli/config.json"
        zcode_check = DoctorCheck(
            provider="zcode",
            ok=False,
            version=zcode_check.version,
            detail=f"CLI model config missing: {location}",
            command=zcode_check.command,
        )
    return [cc_check, zcode_check]


def build_provider_argv(
    request: TaskRequest,
    paths: TaskPaths,
    config: ProviderConfig | None = None,
) -> list[str]:
    """Build a shell-free provider command with v1 safety restrictions."""

    selected = config or ProviderConfig.from_environment()
    if request.provider in {"cc", "zcode"} and request.mode == "edit":
        raise ValidationError("edit mode is not enabled for real providers in v1")

    if request.provider == "cc":
        return [
            selected.cc,
            "--restricted",
            "--safe-mode",
            "--permission-mode",
            "plan",
            "--tools",
            "Read,Glob,Grep",
            "--disallowedTools",
            "Agent,Task,Bash,Edit,Write,NotebookEdit,mcp__*",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--disable-slash-commands",
            "--max-turns",
            str(request.max_turns),
            "--output-format",
            "stream-json",
            "--verbose",
            "-p",
        ]
    if request.provider == "zcode":
        return [
            selected.node,
            selected.zcode_script,
            "--prompt",
            request.task_text,
            "--cwd",
            str(paths.workspace),
            "--mode",
            "plan",
            "--json",
            "--no-color",
            "--disallowed-tools",
            "Bash,Edit,Write,Agent,Task,mcp__*",
        ]
    if request.provider == "fake":
        if not selected.fake:
            raise ValidationError("fake provider path is not configured")
        match = re.search(r"scenario:\s*([a-z-]+)", request.task_text)
        scenario = match.group(1) if match else "normal"
        return [sys.executable, selected.fake, "--scenario", scenario]
    raise ValidationError(f"unsupported provider: {request.provider}")


def provider_stdin(request: TaskRequest) -> str | None:
    """Return prompt input for providers that keep task text out of argv."""

    if request.provider in {"cc", "fake"}:
        return request.task_text
    return None


def _content_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, list):
        pieces = [piece for item in value if (piece := _content_text(item))]
        return "\n".join(pieces) or None
    if isinstance(value, dict):
        for key in ("content", "text", "result", "output", "message"):
            if key in value and (text := _content_text(value[key])):
                return text
    return None


def _find_key(value: Any, key: str) -> str | None:
    if isinstance(value, dict):
        if key in value and (text := _content_text(value[key])):
            return text
        for nested in value.values():
            if (text := _find_key(nested, key)) is not None:
                return text
    elif isinstance(value, list):
        for nested in value:
            if (text := _find_key(nested, key)) is not None:
                return text
    return None


def parse_provider_line(provider: str, line: str) -> dict[str, Any]:
    """Normalize one output line without claiming fractional progress."""

    stripped = line.strip()
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        return {
            "activity": "provider output",
            "text": stripped,
            "structured": False,
        }

    if not isinstance(event, dict):
        return {
            "activity": "provider event",
            "text": _content_text(event) or "",
            "structured": True,
            "event": event,
        }

    event_type = event.get("type")
    activity = "provider event"
    if provider == "cc" and event_type == "assistant":
        activity = "assistant response"
    elif (provider == "cc" and event_type == "result") or (
        provider == "zcode" and event_type in {"result", "completed", "complete"}
    ):
        activity = "result received"
    return {
        "activity": activity,
        "text": _content_text(event) or "",
        "structured": True,
        "event": event,
    }


def _json_objects(lines: list[str]) -> list[Any]:
    joined = "\n".join(lines).strip()
    if joined:
        try:
            return [json.loads(joined)]
        except json.JSONDecodeError:
            pass
    objects: list[Any] = []
    for line in lines:
        try:
            objects.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return objects


def _single_json_object(lines: list[str]) -> dict[str, Any] | None:
    joined = "\n".join(lines).strip()
    if not joined:
        return None
    try:
        value = json.loads(joined)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def extract_final_result(provider: str, lines: list[str]) -> str | None:
    """Extract only a structured final result from captured provider output."""

    objects = _json_objects(lines)
    if provider == "cc":
        for event in reversed(objects):
            if isinstance(event, dict) and event.get("type") == "result":
                return _content_text(event.get("result"))
        return None
    if provider == "zcode":
        single_object = _single_json_object(lines)
        if single_object is not None and "type" not in single_object:
            for key in ("result", "output", "text", "message"):
                if (text := _find_key(single_object, key)) is not None:
                    return text
        for event in reversed(objects):
            if not isinstance(event, dict) or event.get("type") not in {
                "result",
                "completed",
                "complete",
                "final",
            }:
                continue
            for key in ("result", "output", "text", "message"):
                if (text := _find_key(event, key)) is not None:
                    return text
        return None
    if provider == "fake":
        for event in reversed(objects):
            if isinstance(event, dict) and event.get("type") == "result":
                return _content_text(event.get("result"))
        return None
    return None
