from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.agent_delegate.core import (
    TaskRequest,
    ValidationError,
    atomic_write_json,
    create_workspace_snapshot,
    diff_snapshots,
    redact_text,
    snapshot_tree,
    task_paths,
    validate_request,
)


def make_request(
    source: Path,
    *,
    mode: str = "review",
    read_paths: tuple[str, ...] = ("allowed.txt",),
    write_paths: tuple[str, ...] = (),
) -> TaskRequest:
    return TaskRequest(
        task_id="task_0123456789ab",
        request_id="req-core",
        provider="fake",
        mode=mode,
        source_cwd=str(source),
        task_text="Review the authorized material.",
        read_paths=read_paths,
        write_paths=write_paths,
        verify_commands=(),
        timeout_seconds=30,
        max_turns=3,
        created_at="2026-09-13T00:00:00+00:00",
    )


def test_review_snapshot_copies_only_authorized_files_and_protects_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "allowed.txt").write_text("before", encoding="utf-8")
    (source / "secret.txt").write_text("outside", encoding="utf-8")
    request = make_request(source)
    paths = task_paths(tmp_path / "state", request.task_id)

    create_workspace_snapshot(request, paths)
    (paths.workspace / "allowed.txt").write_text("changed", encoding="utf-8")

    assert (source / "allowed.txt").read_text(encoding="utf-8") == "before"
    assert not (paths.workspace / "secret.txt").exists()


@pytest.mark.parametrize("bad", ["/etc/passwd", "../outside", "link"])
def test_validation_rejects_absolute_parent_and_symlink_paths(
    tmp_path: Path, bad: str
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "target").write_text("x", encoding="utf-8")
    (source / "link").symlink_to(source / "target")

    with pytest.raises(ValidationError):
        validate_request(make_request(source, read_paths=(bad,)))


def test_validation_rejects_symlink_nested_below_selected_directory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    selected = source / "selected"
    selected.mkdir(parents=True)
    (source / "outside.txt").write_text("secret", encoding="utf-8")
    (selected / "nested-link").symlink_to(source / "outside.txt")

    with pytest.raises(ValidationError, match="symlink"):
        validate_request(make_request(source, read_paths=("selected",)))


def test_write_paths_must_be_within_read_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "docs").mkdir(parents=True)
    (source / "src").mkdir()

    with pytest.raises(ValidationError, match="write path"):
        validate_request(
            make_request(
                source,
                mode="edit",
                read_paths=("docs",),
                write_paths=("src",),
            )
        )


def test_edit_mode_requires_write_path(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "allowed.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ValidationError, match="write path"):
        validate_request(make_request(source, mode="edit"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("task_id", "task_not-hex", "task id"),
        ("request_id", "", "request id"),
        ("provider", "unknown", "provider"),
        ("mode", "write-everything", "mode"),
        ("task_text", "   ", "task text"),
        ("timeout_seconds", 0, "timeout"),
        ("max_turns", 0, "max turns"),
    ],
)
def test_validation_rejects_invalid_request_fields(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "allowed.txt").write_text("x", encoding="utf-8")
    request = make_request(source)
    values = {
        name: getattr(request, name)
        for name in request.__dataclass_fields__
    }
    values[field] = value

    with pytest.raises(ValidationError, match=message):
        validate_request(TaskRequest(**values))


def test_validation_rejects_missing_read_path_and_empty_verification_argv(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValidationError, match="read path"):
        validate_request(make_request(source, read_paths=("missing",)))

    (source / "allowed.txt").write_text("x", encoding="utf-8")
    request = make_request(source)
    values = {
        name: getattr(request, name)
        for name in request.__dataclass_fields__
    }
    values["verify_commands"] = ((),)
    with pytest.raises(ValidationError, match="verification"):
        validate_request(TaskRequest(**values))


def test_dot_snapshot_excludes_repository_and_secret_state(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "visible.txt").write_text("yes", encoding="utf-8")
    (source / ".env").write_text("SECRET=no", encoding="utf-8")
    (source / ".env.local").write_text("SECRET=no", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".git" / "config").write_text("hidden", encoding="utf-8")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "dep.js").write_text("hidden", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "cached.pyc").write_bytes(b"hidden")
    paths = task_paths(tmp_path / "state", "task_0123456789ab")

    create_workspace_snapshot(make_request(source, read_paths=(".",)), paths)

    assert (paths.workspace / "visible.txt").is_file()
    assert not (paths.workspace / ".env").exists()
    assert not (paths.workspace / ".env.local").exists()
    assert not (paths.workspace / ".git").exists()
    assert not (paths.workspace / "node_modules").exists()
    assert not (paths.workspace / "__pycache__").exists()


def test_snapshot_diff_reports_added_modified_and_deleted(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "same.txt").write_text("same", encoding="utf-8")
    (root / "changed.txt").write_text("before", encoding="utf-8")
    (root / "deleted.txt").write_text("gone", encoding="utf-8")
    before = snapshot_tree(root)

    (root / "changed.txt").write_text("after", encoding="utf-8")
    (root / "deleted.txt").unlink()
    (root / "added.txt").write_text("new", encoding="utf-8")
    changes = diff_snapshots(before, snapshot_tree(root))

    assert changes == {
        "added": ["added.txt"],
        "modified": ["changed.txt"],
        "deleted": ["deleted.txt"],
    }


def test_redaction_removes_common_secret_forms() -> None:
    raw = (
        "OPENAI_API_KEY=sk-test-secret\n"
        "Authorization: Bearer abc.def.ghi\n"
        '"api_key":"private-value"'
    )
    redacted = redact_text(raw)

    assert "sk-test-secret" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "private-value" not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_atomic_write_json_replaces_complete_document(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_json(target, {"state": "queued"})
    atomic_write_json(target, {"state": "running", "count": 2})

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "state": "running",
        "count": 2,
    }
    assert list(tmp_path.glob("*.tmp")) == []
