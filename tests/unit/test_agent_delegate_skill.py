from __future__ import annotations

from pathlib import Path

import yaml

SKILL = Path(__file__).parents[2] / ".agents" / "skills" / "agent-delegate" / "SKILL.md"


def test_skill_has_discoverable_frontmatter_and_guarded_workflow() -> None:
    text = SKILL.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)

    assert metadata["name"] == "agent-delegate"
    assert "CC" in metadata["description"]
    assert "ZCode" in metadata["description"]
    assert "scripts/agent_delegate.py" in body
    assert "--mode review" in body
    assert "--read-path" in body
    assert "real-provider edit mode" in body
    assert "dashboard" in body
    assert body.index("handoff.md") < body.index("changes.patch")


def test_skill_forbids_automatic_continuation_without_naming_bypass_flags() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "Do not poll with model turns" in text
    assert "Do not automatically retry, resume, apply, commit, or dispatch" in text
    for dangerous in ("dangerously-skip-permissions", "bypassPermissions", "--mode yolo"):
        assert dangerous not in text
