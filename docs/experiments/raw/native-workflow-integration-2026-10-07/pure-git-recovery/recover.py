"""Reassemble only accepted bytes from explicitly recorded remote Git sources."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
AUTHOR = "b2f45151128baa1fe387cda85862d71cb01e1206"
TIP = "ba106251577952bc35f5f865a76cd49d1c274773"
SNAPSHOT = "ec565b87f794541bfa6518a8675dce941390e3e8"
RAW = "docs/experiments/raw/native-workflow-integration-2026-10-07/"
commands = []

def run(args, check=True, env=None):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, env=env)
    commands.append({"argv": args, "exit_code": p.returncode,
                     "stdout": p.stdout.decode(errors="replace"),
                     "stderr": p.stderr.decode(errors="replace")})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2)+"\n")
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {args}")
    return p

def blob(commit, path):
    oid = subprocess.check_output(["git", "rev-parse", f"{commit}:{path}"], cwd=ROOT).decode().strip()
    data = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=ROOT)
    return oid, data

def load(commit, path):
    return json.loads(blob(commit, path)[1])

def sha(data):
    return hashlib.sha256(data).hexdigest()

manifest = {"created_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            "checked_coordination_sha": "59457a8785f150a47edc1e3cab869a51ec2ecfef",
            "read_task_ids": ["classic-factor-research", "research-dispatch-controller"],
            "conflict_decision": "Only new isolated worktree and own raw evidence; parent maintains coordination. No shared root or author worktree changes.",
            "worktree": str(ROOT), "author_commit": AUTHOR, "author_tip": TIP,
            "snapshot_commit": SNAPSHOT, "entries": [], "implementation": [],
            "boundary": "Existing Python environment, remote Git byte recovery and artificial engineering workflow only; no installation or real research."}
try:
    inventory = load(TIP, RAW+"remote-baseline-inventory.json")
    (OUT / "inventory-source.json").write_bytes(blob(TIP, RAW+"remote-baseline-inventory.json")[1])
    sources = []
    for item in inventory["entries"]:
        matches = [m for m in item["matches"] if m["ref"].startswith("origin/")]
        source = matches[0] if matches else {"ref": "origin/codex/native-workflow-baseline-20261008", "commit": SNAPSHOT, "path": item["path"]}
        sources.append((item, source))
    refs = {s["ref"].removeprefix("origin/"):s["commit"] for _,s in sources}
    refs["codex/native-workflow-integration-20261007"] = TIP
    manifest["remote_refs"] = []
    for ref, commit in refs.items():
        p = run(["git", "ls-remote", "origin", "refs/heads/"+ref])
        current = p.stdout.decode().split()[0]
        run(["git", "fetch", "origin", "refs/heads/"+ref])
        tip = run(["git", "rev-parse", "FETCH_HEAD"]).stdout.decode().strip()
        assert current == tip, (ref, current, tip)
        run(["git", "merge-base", "--is-ancestor", commit, tip])
        manifest["remote_refs"].append({"ref": ref, "recorded_commit": commit, "current_remote_tip": tip, "reachable": True})
    run(["git", "merge-base", "--is-ancestor", AUTHOR, TIP])
    for item, source in sources:
        oid, data = blob(source["commit"], item["path"])
        assert len(data) == item["bytes"] and sha(data) == item["baseline_sha256"], item["path"]
        target = ROOT / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        assert sha(target.read_bytes()) == item["baseline_sha256"]
        manifest["entries"].append({"path": item["path"], "bytes": len(data), "sha256": sha(data), "source": source, "git_blob": oid, "verified": True})
    assert len(manifest["entries"]) == 49
    patch_info = load(AUTHOR, RAW+"shared-entry-patch-manifest.json")
    patch = blob(AUTHOR, patch_info["patch_path"])[1]
    assert sha(patch) == patch_info["patch_sha256"]
    patch_path = OUT / "shared-entry-changes.patch"
    patch_path.write_bytes(patch)
    run(["git", "apply", "--check", "--unidiff-zero", str(patch_path)])
    run(["git", "apply", "--unidiff-zero", str(patch_path)])
    impl = patch_info["files"] + load(AUTHOR, RAW+"repair-r1-r2.json")["changed_files"]
    for item in impl:
        expected = item.get("after_sha256", item.get("sha256"))
        data = (ROOT/item["path"]).read_bytes()
        assert sha(data) == expected, item["path"]
        manifest["implementation"].append({"path":item["path"], "sha256":sha(data), "bytes":len(data), "verified":True})
    assert len(manifest["implementation"]) == 6
    manifest["assembly_passed"] = True
    run(["python3", "--version"])
    run(["python3", "-m", "pytest", "--version"])
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="src")
    args = ["python3", "-m", "pytest", "-q", "tests/integration/test_native_risk_d_mae_workflow.py::test_cli_x_then_one_y_restart_verify_and_repeat_rejection", "--tb=short"]
    p = run(args, check=False, env=env)
    (OUT/"pytest-output.txt").write_bytes(p.stdout+p.stderr)
    manifest["pytest"] = {"command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "+" ".join(args), "exit_code":p.returncode, "cwd":str(ROOT), "output_sha256":sha(p.stdout+p.stderr)}
    manifest["real_X"] = manifest["real_V"] = manifest["real_Y"] = manifest["market_requests"] = manifest["paid_requests"] = 0
    manifest["status"] = "passed" if p.returncode == 0 else "failed"
except Exception as exc:
    manifest["status"] = "blocked"
    manifest["error"] = repr(exc)
finally:
    (OUT/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(json.dumps({"status":manifest["status"], "assembled":len(manifest["entries"]), "implementation":len(manifest["implementation"]), "pytest":manifest.get("pytest"), "error":manifest.get("error")}))
sys.exit(0 if manifest["status"] == "passed" else 1)
