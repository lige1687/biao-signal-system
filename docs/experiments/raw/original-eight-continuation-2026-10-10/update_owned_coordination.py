"""Update only the current owner's coordination task using an isolated index."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).parent
TASK = "docs/coordination/tasks/original-eight-continuation-20261010.md"
OWNER = "01a123fc-553b-7b81-9952-36e1acb11dcc"


def git(*args, **kw):
    return subprocess.check_output(["git", *args], cwd=ROOT, **kw)


def main():
    phase = sys.argv[1]
    change = json.loads((RAW / (phase + "-coordination-update.json")).read_text())
    main_head = git("rev-parse", "HEAD", text=True).strip()
    main_index = hashlib.sha256((ROOT / ".git/index").read_bytes()).hexdigest()
    git("fetch", "origin", "coordination/lei")
    base = git("rev-parse", "origin/coordination/lei", text=True).strip()
    body = git("show", base + ":" + TASK, text=True)
    start = "<!-- lei-coordination-json:start -->"
    end = "<!-- lei-coordination-json:end -->"
    first, rest = body.split(start, 1)
    block, tail = rest.split(end, 1)
    record = json.loads(block)
    assert record["owner"] == OWNER
    baseline = change["reviewed_baseline"]
    changed = git("diff", "--name-only", baseline, base, text=True).splitlines()
    assert set(changed) <= {"docs/coordination/tasks/cash-position-video-20261009.md"}, changed
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    paths = ["COORDINATION.md"] + ["docs/coordination/tasks/" + t + ".md" for t in record["read_task_ids"]]
    reads = []
    for path in paths:
        data = git("show", base + ":" + path)
        reads.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    record["checked_coordination_sha"] = base
    record["checked_at"] = now
    record["latest_result_commit"] = change["result_commit"]
    record["status"] = change.get("status", "active")
    record["updated_at"] = now
    record["conflict_decision"] = change["conflict_decision"]
    for key in ["write_paths", "external_write_paths", "question_ids"]:
        for value in change.get(key, []):
            if value not in record[key]:
                record[key].append(value)
    for key in ["scope_amendment", "current_work", "paused_questions"]:
        if key in change:
            record[key] = change[key]
    body = first + start + "\n" + json.dumps(record, ensure_ascii=False, indent=2) + "\n" + end + tail
    body += "\n## " + now + " " + change["title"] + "\n\n" + change["note"] + "\n"
    data = body.encode()
    fd, index = tempfile.mkstemp(prefix="lei-own-coordination-", dir=ROOT / ".git")
    os.close(fd)
    Path(index).unlink()
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index
    try:
        git("read-tree", base, env=env)
        blob = git("hash-object", "-w", "--stdin", input=data).decode().strip()
        git("update-index", "--add", "--cacheinfo", "100644", blob, TASK, env=env)
        tree = git("write-tree", env=env, text=True).strip()
        assert git("diff", "--name-only", base, tree, text=True).splitlines() == [TASK]
        git("diff", "--check", base, tree)
        commit = git("commit-tree", tree, "-p", base, "-m", "Update original eight continuation: " + phase, text=True).strip()
        git("push", "origin", commit + ":refs/heads/coordination/lei")
        git("fetch", "origin", "coordination/lei")
        tip = git("rev-parse", "origin/coordination/lei", text=True).strip()
        assert git("merge-base", "--is-ancestor", commit, tip) == b""
        assert git("show", tip + ":" + TASK) == data
        assert git("rev-parse", "HEAD", text=True).strip() == main_head
        assert hashlib.sha256((ROOT / ".git/index").read_bytes()).hexdigest() == main_index
        receipt = {"at": now, "commit": commit, "remote_tip": tip, "checked_coordination_sha": base,
                   "read_files": reads, "only_own_task_changed": True, "remote_task_bytes_equal": True,
                   "main_head_and_index_unchanged": True, "result_commit": change["result_commit"],
                   "status": record["status"], "conflict_decision": change["conflict_decision"]}
        (RAW / (phase + "-coordination-readback.json")).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: v for k, v in receipt.items() if k != "read_files"}))
    finally:
        if Path(index).exists():
            Path(index).unlink()


if __name__ == "__main__":
    main()
