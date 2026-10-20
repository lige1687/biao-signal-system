"""Task 0 基线冻结：保存 git HEAD、脏工作区指纹与逐文件哈希。

只读操作；输出 protection-baseline.json（拒绝覆盖已存在文件）。
不 checkout、不 reset、不改动任何受保护文件。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "protection-baseline.json"

# 本轮允许修改的既有文件（修改前基线）。
ALLOWED_TO_MODIFY = [
    "docs/experiments/registry.json",
    "docs/experiments/INDEX.md",
    "docs/research/factor-research-roadmap-2026-09-10.md",
]

# 本轮必须保持不变的相关原模块/卡/规则/规范/旧测试。
PROTECTED = [
    "AGENTS.md",
    "CLAUDE.md",
    "docs/trading-spec-v1.md",
    "configs/rules.v1.yaml",
    "docs/research/definitions.v1.json",
    "docs/research/experiment-backtest-principles.md",
    "docs/research/definition-standard.md",
    "docs/research/ai-execution-contract.md",
    "docs/research/experiment-report-template.md",
    "docs/research/factor-research-roadmap-2026-09-10.md",
    "docs/experiments/factor-research-workbench-mandate-2026-09-14.md",
    "docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md",
    "src/lei_signal/research/definitions.py",
    "src/lei_signal/research/momentum_prototype.py",
    "src/lei_signal/research/factor_diagnostics.py",
    "src/lei_signal/research/factor_runtime.py",
    "src/lei_signal/research/factor_account_adapter.py",
    "src/lei_signal/research/data_snapshot.py",
    "src/lei_signal/research/data_quality.py",
    "src/lei_signal/research/input_preflight.py",
    "src/lei_signal/research/qualification_bundle.py",
    "src/lei_signal/rules/dual_ma.py",
    "src/lei_signal/rules/lei_color.py",
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/domain/rules_config.py",
    "src/lei_signal/domain/types.py",
    "tests/unit/test_research_definitions.py",
    "tests/unit/test_momentum_prototype.py",
    "tests/unit/test_factor_diagnostics.py",
]

# 上轮冻结产物（momentum prototype S1–S3 收口相关 raw，只读抽查代表）。
PROTECTED_RAW = [
    "docs/experiments/raw/momentum-prototype-controller-review-2026-09-13",
    "docs/experiments/raw/research-data-provenance-2026-09-10/reuse-decision.md",
    "docs/experiments/raw/research-data-provenance-2026-09-10/protocol.json",
    "docs/experiments/raw/research-data-provenance-2026-09-10/protected-baseline.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def dir_fingerprint(rel: str) -> dict:
    base = ROOT / rel
    if base.is_file():
        return {"path": rel, "file_count": 1, "files": {rel: sha256(base)}}
    files = {}
    if base.is_dir():
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                files[p.relative_to(ROOT).as_posix()] = sha256(p)
    return {"path": rel, "file_count": len(files), "files": files}


def main() -> int:
    if OUT.exists():
        print(f"refusing to overwrite {OUT}")
        return 3
    status = git("status", "--porcelain")
    record = {
        "task": "factor-research-workbench-v1",
        "created": "2026-09-14",
        "git_head": git("rev-parse", "HEAD").strip(),
        "git_head_subject": git("log", "-1", "--format=%s").strip(),
        "dirty_workspace_fingerprint": {
            "porcelain_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "porcelain_lines": len(status.splitlines()),
            "porcelain": status.splitlines(),
        },
        "allowed_to_modify_pre_state": {
            rel: {"sha256": sha256(ROOT / rel)} for rel in ALLOWED_TO_MODIFY
        },
        "protected_files": {
            rel: {"sha256": sha256(ROOT / rel)} for rel in PROTECTED
        },
        "protected_raw": [dir_fingerprint(rel) for rel in PROTECTED_RAW],
    }
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written {OUT}")
    print(f"git_head={record['git_head']}")
    print(f"dirty_lines={record['dirty_workspace_fingerprint']['porcelain_lines']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
