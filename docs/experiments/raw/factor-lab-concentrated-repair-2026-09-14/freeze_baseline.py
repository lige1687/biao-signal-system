"""集中返修 Task 0 基线：保存 git 状态、逐项哈希上轮 29 项保护与 408 项 raw 清单。

只读；输出 protection-baseline.json（排他创建）。原清单缺项如实注明，不制造可比数字。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "protection-baseline.json"
PREV = ROOT / "docs/experiments/raw/factor-research-workbench-v1-2026-09-14/protection-baseline.json"

ALLOWED_TO_MODIFY = [
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
    "docs/experiments/registry.json",
    "docs/experiments/INDEX.md",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def main() -> int:
    if OUT.exists():
        print(f"refusing to overwrite {OUT}")
        return 3
    prev = json.loads(PREV.read_text())
    protected = {}
    missing = []
    for rel, meta in prev["protected_files"].items():
        p = ROOT / rel
        if p.is_file():
            protected[rel] = sha(p)
        else:
            missing.append(rel)
    raw_items = []
    for item in prev["protected_raw"]:
        base = ROOT / item["path"]
        if base.is_file():
            raw_items.append({"path": item["path"], "file_count": 1,
                              "files": {item["path"]: sha(base)}})
            continue
        files = {}
        for rel, expected in item["files"].items():
            f = ROOT / rel
            files[rel] = sha(f) if f.is_file() else "MISSING"
        raw_items.append({"path": item["path"], "file_count": len(files),
                          "files": files})
    status = git("status", "--porcelain")
    record = {
        "task": "factor-lab-concentrated-repair",
        "created": "2026-09-15",
        "source_plan": "docs/superpowers/plans/2026-09-14-factor-lab-concentrated-repair.md@1.0.0",
        "git_head": git("rev-parse", "HEAD").strip(),
        "dirty_workspace_fingerprint": {
            "porcelain_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "porcelain_lines": len(status.splitlines()),
        },
        "allowed_to_modify_pre_state": {
            rel: ({"sha256": sha(ROOT / rel)} if (ROOT / rel).is_file()
                  else {"sha256": "MISSING"})
            for rel in ALLOWED_TO_MODIFY
        },
        "protected_files_from_prev_baseline": protected,
        "protected_raw_from_prev_baseline": raw_items,
        "missing_from_prev_baseline": missing,
    }
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"written {OUT}")
    print(f"protected={len(protected)} raw_items={len(raw_items)} missing={missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
