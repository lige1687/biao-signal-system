"""T10 机器可读示例：为 GitHub 已有的冻结实验 research-broad-etf-technical-2026-09-08 生成
“旧报告数字核对 + 冻结旧代码复现”两种用途的移交清单（只读，不改原锁）。

输出 example-manifest-broad-etf-technical.json，并立即用 handoff_check.check 自检。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
from handoff_check import check, eol, git_blob, sha256  # noqa: E402

EXP = "docs/experiments/raw/research-broad-etf-technical-2026-09-08"
ROLES = {
    "protocol.md": "frozen_protocol", "protocol-lock.json": "original_lock",
    "execution/source-lock.json": "original_lock", "execution/engine.py": "frozen_code",
    "execution/metrics.py": "frozen_code", "execution/run_accounts.py": "frozen_code",
    "execution/inputs/execution-config.json": "input", "execution/inputs/actions.json": "input",
    "execution/inputs/action-coverage.json": "input_coverage", "execution/inputs/dated-restrictions.json": "input",
    "execution/inputs/bars/sh510300-nominal.csv": "input_market_data",
    "execution/inputs/bars/sz159915-nominal.csv": "input_market_data",
    "execution/account-results/summary.json": "expected_output",
}


def main() -> int:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    files, code = [], []
    for rel, role in ROLES.items():
        b = (REPO / EXP / rel).read_bytes()
        entry = {"path": rel, "role": role, "sha256": sha256(b), "git_blob": git_blob(b), "eol": eol(b),
                 "public": role != "input_market_data",
                 "license": ("exchange/vendor terms not recorded in lock; keep extracted facts public, "
                             "originals by authorization") if role == "input_market_data" else "repository"}
        files.append(entry)
        if role == "frozen_code":
            code.append({"path": rel, "git_blob": entry["git_blob"]})
    manifest = {
        "schema_version": "handoff-manifest/0",
        "experiment_id": "research-broad-etf-technical-2026-09-08",
        "review_mode": "frozen_code_replay",
        "also_supports": ["report_numbers"],
        "base_commit_of_this_copy": commit,
        "originals": [{"path": "protocol-lock.json", "note": "kept byte-identical"},
                      {"path": "execution/source-lock.json",
                       "note": "absolute paths of the original machine kept; map below is handoff-only"}],
        "path_map": [{"from_prefix": "/Users/yongbiaoli/Desktop/lei-signal-lab/" + EXP + "/", "to_prefix": ""}],
        "files": files,
        "code": {"commit": commit, "files": code},
        "environment": {"python": "unknown in original lock (record when replaying)",
                        "packages": "unknown in original lock"},
        "objects": ["sh510300", "sz159915"], "dates": ["2015-01-01", "2026-06-30"],
        "units": {"price": "CNY nominal traded price", "account": "CNY, 100000 initial per account"},
        "expected_outputs": [{"path": "execution/account-results/summary.json", "tolerance_abs": 0.01,
                              "note": "48 accounts; compare per account final equity and max drawdown"}],
        "known_differences": [
            {"path": "execution/inputs/bars/*.csv",
             "fact": "GitHub copy is LF; execution/source-lock.json recorded the CRLF bytes of the original machine",
             "effect": "byte check reports eol_only; content identical after newline normalization"}],
        "missing": [{"item": "historical arrival time of quotes", "reason": "not recorded upstream"},
                    {"item": "exact Python/pandas versions used on 2026-09-08", "reason": "not in lock"}],
    }
    out = HERE / "example-manifest-broad-etf-technical.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    res = check(REPO / EXP, manifest, code_root=REPO / EXP)
    print("self-check:", res["status"], res["action"], len(res["findings"]))
    return 0 if res["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
