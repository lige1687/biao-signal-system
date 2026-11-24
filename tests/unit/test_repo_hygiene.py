from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts" / "check_repo_hygiene.py"
SPEC = importlib.util.spec_from_file_location("check_repo_hygiene", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HYGIENE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HYGIENE)


def test_project_level_codex_skills_are_allowed_at_repo_root(tmp_path: Path) -> None:
    (tmp_path / ".agents").mkdir()
    problems: list[str] = []

    HYGIENE.check_layer(
        tmp_path,
        HYGIENE.ROOT_KEEP_FILES,
        HYGIENE.ROOT_KEEP_DIRS,
        "仓库根层",
        problems,
    )

    assert problems == []


def test_unknown_repo_root_directory_is_still_rejected(tmp_path: Path) -> None:
    (tmp_path / ".unknown-tool").mkdir()
    problems: list[str] = []

    HYGIENE.check_layer(
        tmp_path,
        HYGIENE.ROOT_KEEP_FILES,
        HYGIENE.ROOT_KEEP_DIRS,
        "仓库根层",
        problems,
    )

    assert problems == [
        "[仓库根层] 多出目录: .unknown-tool/（白名单外，归档或删除）"
    ]


def test_workspace_governance_passes_for_clean_single_main_repo(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("/.codex/\n", encoding="utf-8")
    problems: list[str] = []

    HYGIENE.check_workspace_governance(
        tmp_path,
        problems,
        worktrees=[str(tmp_path)],
        local_branches=["main"],
    )

    assert problems == []


def test_workspace_governance_rejects_nested_codex_extra_worktrees_and_branch_sprawl(
    tmp_path: Path,
) -> None:
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".gitignore").write_text(".workbuddy/\n", encoding="utf-8")
    problems: list[str] = []

    HYGIENE.check_workspace_governance(
        tmp_path,
        problems,
        worktrees=[str(tmp_path), "/tmp/extra-worktree"],
        local_branches=["main", "b1", "b2", "b3", "b4", "b5"],
    )

    assert len(problems) == 4
    assert any(".codex/" in p for p in problems)
    assert any("忽略项 /.codex/" in p for p in problems)
    assert any("多余的分身工作区" in p for p in problems)
    assert any("本地分支过多" in p for p in problems)
