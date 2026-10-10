"""Publish this task's exact files using a separate index; preserve main WIP."""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTROL = Path(__file__).parent
BRANCH = "codex/original-eight-continuation-20261010"
MAIN_HEAD = "18e64fa632dba5dbad0e5fcae09b4ccc75f119a9"
MAIN_INDEX = "e93cdb1d84cd2a8a793acb5f35b36521003dd72efa23333102a0fc9d64343970"


def git(*args, **kwargs):
    return subprocess.check_output(["git", *args], cwd=ROOT, **kwargs)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    phase = sys.argv[1]
    final_source = "--source-final" in sys.argv[2:]
    assert git("rev-parse", "HEAD", text=True).strip() == MAIN_HEAD
    assert digest((ROOT / ".git/index").read_bytes()) == MAIN_INDEX
    base = git("rev-parse", BRANCH, text=True).strip()
    registrations = ["D", "cross-week", "etf-h1"]
    if final_source:
        registrations.append("etf-full-actions")
    entries = [json.loads((CONTROL / f"{name}-registration-entry.json").read_text())
               for name in registrations]
    paths = {"src/lei_signal/research/native_d_conditional_risk.py",
             "tests/unit/test_native_d_conditional_risk.py",
             "docs/ops/work-progress/original-eight-continuation-20261010.md",
             "docs/experiments/raw/stock-data-qualification-2026-10-07/march-event-binding-20261010/reuse-review.json"}
    paths.update(entry["report"] for entry in entries)
    directories = ["native-d-conditional-risk-2026-10-10",
                   "weekly-portfolio-cross-week-fixed-orders-2026-10-10",
                   "etf-pair-h1-action-qualification-2026-10-10",
                   "original-eight-continuation-2026-10-10"]
    if final_source:
        directories.append("etf-pair-action-coverage-completion-2026-10-10")
    for directory in directories:
        for p in (ROOT / "docs/experiments/raw" / directory).rglob("*"):
            if p.is_file() and not any(s in {"__pycache__", ".pytest_cache"}
                                     or s.startswith("._") or s == ".DS_Store"
                                     for s in p.relative_to(ROOT).parts):
                paths.add(p.relative_to(ROOT).as_posix())
    if not final_source:
        for name in ["executor-contract.json", "controller-reuse-acceptance.json",
                     "independent-reuse-review.json"]:
            paths.add("docs/experiments/raw/etf-pair-action-coverage-completion-2026-10-10/" + name)
    content = {p: (ROOT / p).read_bytes() for p in sorted(paths)}
    assert all(len(b) < 1024**2 and b"\x00" not in b for b in content.values())
    registry_path = "docs/experiments/registry.json"
    registry = git("show", base + ":" + registry_path, text=True)
    original = json.loads(registry)
    for entry in entries:
        name = entry["report"]
        assert digest(content[name]) == entry["entry"]["report_sha256"]
        if name in original["entries"]:
            match = re.search(r"(?m)^[ \t]*" + re.escape(json.dumps(name)) + r"[ \t]*:[ \t]*", registry)
            assert match is not None
            _, end = json.JSONDecoder().raw_decode(registry[match.end():])
            replacement = json.dumps(entry["entry"], ensure_ascii=False, indent=2)
            registry = registry[:match.end()] + replacement + registry[match.end() + end:]
        else:
            match = re.search(r'(?m)^[ \t]*"entries"[ \t]*:[ \t]*\{\n', registry)
            assert match is not None
            registry = registry[:match.end()] + entry["insert"] + registry[match.end():]
    parsed = json.loads(registry)
    own_names = {e["report"] for e in entries}
    for k, v in original["entries"].items():
        if k not in own_names:
            assert parsed["entries"][k] == v
    assert set(parsed["entries"]) == set(original["entries"]) | own_names
    content[registry_path] = registry.encode()
    inserts = json.loads((CONTROL / "shared-document-insertions.json").read_text())
    index_path = "docs/experiments/INDEX.md"
    index = git("show", base + ":" + index_path, text=True)
    line_keys = ["D_index_line", "cross_week_index_line", "etf_h1_index_line"]
    if final_source:
        line_keys.append("etf_full_actions_index_line")
    lines = "".join(inserts[k] for k in line_keys if inserts[k] not in index)
    anchor = "## 1. 任务编号总账（任务书 → 执行归档）"
    pos = index.index("\n", index.index(anchor)) + 1
    content[index_path] = (index[:pos] + "\n" + lines + index[pos:]).encode()
    catalog_path = "docs/experiments/research-evidence-catalog-2026-10-07.md"
    catalog = git("show", base + ":" + catalog_path, text=True)
    header = "## 2026-10-10 当前接续：D条件描述已结案，历史成员单事件复用已有原件\n"
    if catalog.startswith(header):
        marker = "\n---\n\n"
        catalog = catalog[catalog.index(marker) + len(marker):]
    content[catalog_path] = (inserts["catalog_prefix"] + catalog).encode()
    manifest = {"schema": "original-eight-exact-publication/1", "phase": phase,
                "at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
                "branch": BRANCH, "base_commit": base, "main_head": MAIN_HEAD,
                "main_index_sha256": MAIN_INDEX, "published_catalog_prefix": inserts["catalog_prefix"],
                "shared_base_plus_only_own_changes": True, "active_source_files_excluded": not final_source,
                "files": [{"path": p, "bytes": len(b), "sha256": digest(b)} for p, b in sorted(content.items())],
                "manifest_self_excluded": True}
    name = f"docs/experiments/raw/original-eight-continuation-2026-10-10/{phase}-publication-manifest.json"
    (ROOT / name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    content[name] = (ROOT / name).read_bytes()
    fd, index_file = tempfile.mkstemp(prefix="lei-eight-results-", dir=ROOT / ".git")
    os.close(fd)
    Path(index_file).unlink()
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index_file
    try:
        git("read-tree", base, env=env)
        for p, b in sorted(content.items()):
            blob = git("hash-object", "-w", "--stdin", input=b).decode().strip()
            git("update-index", "--add", "--cacheinfo", "100644", blob, p, env=env)
        tree = git("write-tree", env=env, text=True).strip()
        changed = set(git("diff", "--name-only", base, tree, text=True).splitlines())
        assert changed <= set(content) and changed
        git("diff", "--check", base, tree)
        commit = git("commit-tree", tree, "-p", base, "-m", "Archive original eight goals bounded evidence: " + phase, text=True).strip()
        git("update-ref", "refs/heads/" + BRANCH, commit, base)
        git("push", "origin", "refs/heads/" + BRANCH + ":refs/heads/" + BRANCH)
        git("fetch", "origin", BRANCH)
        assert git("rev-parse", "origin/" + BRANCH, text=True).strip() == commit
        for p, b in content.items():
            assert git("show", commit + ":" + p) == b
        assert git("rev-parse", "HEAD", text=True).strip() == MAIN_HEAD
        assert digest((ROOT / ".git/index").read_bytes()) == MAIN_INDEX
        receipt = {"commit": commit, "branch": BRANCH, "base": base,
                   "files_read_back": len(content), "changed_paths": len(changed),
                   "all_remote_bytes_equal": True, "main_head_and_index_unchanged": True,
                   "ordinary_bytes": sum(len(b) for b in content.values()), "at": manifest["at"]}
        (CONTROL / f"{phase}-publication-readback.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(receipt))
    finally:
        if Path(index_file).exists():
            Path(index_file).unlink()


if __name__ == "__main__":
    main()
