"""最后一轮收尾 Task 0：源码原字节快照 + 基线冻结（排他创建）。

- 保存允许修改面的当前源码**原字节副本**（不仅哈希）到 source-snapshot/；
- 冻结现有协议/正式运行/保护清单哈希到 protection-baseline.json；
- 只读操作，不改任何受保护文件。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "source-snapshot"
OUT = HERE / "protection-baseline.json"

SNAPSHOT_FILES = [
    "src/lei_signal/research/factor_lab/__init__.py",
    "src/lei_signal/research/factor_lab/contracts.py",
    "src/lei_signal/research/factor_lab/adapters.py",
    "src/lei_signal/research/factor_lab/diagnostics.py",
    "src/lei_signal/research/factor_lab/validation.py",
    "src/lei_signal/research/factor_lab/attribution.py",
    "src/lei_signal/research/factor_lab/runner.py",
    "scripts/run_factor_lab.py",
    "tests/unit/test_factor_lab_contracts.py",
    "tests/unit/test_factor_lab_adapters.py",
    "tests/unit/test_factor_lab_diagnostics.py",
    "tests/unit/test_factor_lab_validation.py",
    "tests/unit/test_factor_lab_attribution.py",
    "tests/integration/test_factor_lab_cli.py",
    "docs/research/factor-lab-usage.md",
    "docs/experiments/factor-research-workbench-v1-2026-09-14.md",
    "docs/experiments/factor-lab-concentrated-repair-2026-09-14.md",
    "docs/experiments/registry.json",
    "docs/experiments/INDEX.md",
]

REPAIR_RAW = ROOT / "docs/experiments/raw/factor-lab-concentrated-repair-2026-09-14"
ORIG_RAW = ROOT / "docs/experiments/raw/factor-research-workbench-v1-2026-09-14"
CONTROLLER_RAW = ROOT / "docs/experiments/raw/factor-lab-controller-review-2026-09-15"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def main() -> int:
    if OUT.exists() or SNAP.exists():
        print("refusing to overwrite existing baseline or snapshot")
        return 3
    SNAP.mkdir()
    snapshot = {}
    for rel in SNAPSHOT_FILES:
        source = ROOT / rel
        target = SNAP / rel.replace("/", "__")
        shutil.copy2(source, target)
        snapshot[rel] = {"sha256": sha(source), "snapshot_file": target.name}
    protocol_hashes = {p.name: sha(p)
                       for p in sorted(REPAIR_RAW.glob("protocol-*.json"))}
    run_manifests = {}
    for m in sorted((REPAIR_RAW / "runs").glob("*/manifest.json")):
        run_manifests[m.parent.name] = sha(m)
    prev_baseline = json.loads((REPAIR_RAW / "protection-baseline.json").read_text())
    status = git("status", "--porcelain")
    record = {
        "task": "factor-lab-final-closeout",
        "created": "2026-09-15",
        "source_plan": (
            "docs/experiments/factor-lab-controller-review-2026-09-15.md（第二轮复核，"
            "最后一轮限定收尾S1–S4）"),
        "git_head": git("rev-parse", "HEAD").strip(),
        "dirty_workspace_fingerprint": {
            "porcelain_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "porcelain_lines": len(status.splitlines()),
        },
        "source_snapshot": snapshot,
        "frozen_protocols_v1_1_1": protocol_hashes,
        "frozen_formal_runs_v1_1_0": run_manifests,
        "independent_expectations_v1": {
            "path": "docs/experiments/raw/factor-research-workbench-v1-2026-09-14/"
                    "independent-expectations.json",
            "sha256": sha(ORIG_RAW / "independent-expectations.json"),
        },
        "controller_review_script": {
            "path": "docs/experiments/raw/factor-lab-controller-review-2026-09-15/"
                    "reproduce.py",
            "sha256": sha(CONTROLLER_RAW / "reproduce.py"),
        },
        "carried_protection": {
            "protected_files_from_prev": prev_baseline["protected_files_from_prev_baseline"],
            "protected_raw_from_prev": prev_baseline["protected_raw_from_prev_baseline"],
        },
        "note": "v1.1.0交付时runner.py原字节未单独存档且文件未被git跟踪："
                "旧运行保留为历史证据，源码不可从哈希恢复（详见收尾报告）。",
    }
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"written {OUT}")
    print(f"snapshot={len(snapshot)} protocols={len(protocol_hashes)} "
          f"runs={len(run_manifests)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
