#!/usr/bin/env python3
"""factor_unit 离线资格检查与冻结候选包 CLI（B0）。

用法：
    python3 scripts/check_factor_unit_readiness.py --contract PATH --out NEW_DIRECTORY

只做合同校验、输入哈希先验、结构资格检查与冻结候选包打包；**不计算任何真实
因子表现**（不运行 compute_close_state 于真实全史，不生成真实状态/未来目标值）。

退出码：0=本轮声明用途资料齐备；2=资料不足（原因写全）；3=合同/身份错误。
资格齐备也不自动启动 B1 真实统计。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.research.factor_unit.study_contract import (  # noqa: E402
    CARD_PATH,
    validate_study_contract,
)

CODE_FILES = [
    "src/lei_signal/research/factor_unit/__init__.py",
    "src/lei_signal/research/factor_unit/close_state.py",
    "src/lei_signal/research/factor_unit/study_contract.py",
    "src/lei_signal/research/factor_unit/state_description.py",
    "scripts/check_factor_unit_readiness.py",
]
SPEC_FILES = [
    "docs/research/experiment-backtest-principles.md",
    "docs/research/definition-standard.md",
    "docs/research/ai-execution-contract.md",
    "docs/research/experiment-report-template.md",
    "docs/research/definitions.v1.json",
]
A_STAGE_SHAS = {
    "510300": "a6d518e02313f03cb98ebd69a3e459c9382bd85864f5b1d86771c3c04665fcb4",
    "159915": "f6d5010501fd14cf10941407ca9e6954c6d0fbcc48d631027839f45ac0d8af37",
    "SPY": "584ea5441e19065ac557df14235aa621a5c74f39659e4a8b8926435a33ca4713",
    "QQQ": "3706b3d182fb986aec13ffabe4020638ae7a0fa101043b226bd26e04c9f48548",
}


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def structure_read(p: Path) -> dict:
    """只读结构资格：行数/首末日期/列/重复——不计算状态或目标。"""
    import pandas as pd

    df = pd.read_parquet(p)
    if isinstance(df.index, pd.DatetimeIndex):
        idx = df.index
    else:
        date_col = "date" if "date" in df.columns else df.columns[0]
        idx = pd.to_datetime(df[date_col])
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "first_date": str(idx.min().date()),
        "last_date": str(idx.max().date()),
        "duplicate_dates": int(idx.duplicated().sum()),
        "note": "结构检查only：未计算状态/目标/收益",
    }


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out", required=True, help="新目录；已存在则拒绝")
    args = ap.parse_args()
    now = datetime.now(timezone(timedelta(hours=8)))
    out = Path(args.out)
    if out.exists():
        print(f"REFUSE: 输出目录已存在 {out}", file=sys.stderr)
        return 3

    contract_path = Path(args.contract)
    if not contract_path.is_file():
        print(f"REFUSE: 合同文件不存在 {contract_path}", file=sys.stderr)
        return 3
    try:
        contract = json.loads(contract_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"合同JSON解析失败: {exc}", file=sys.stderr)
        return 3

    data_mode = contract.get("data_mode")
    if data_mode not in {"synthetic", "real"}:
        print("data_mode 必须是 synthetic 或 real", file=sys.stderr)
        return 3
    contract["_repo_root"] = str(REPO)

    # ── 合同校验（ValueError → 3） ──
    try:
        verdict = validate_study_contract(contract)
    except ValueError as exc:
        print(f"合同/身份错误: {exc}", file=sys.stderr)
        return 3

    reasons = list(verdict["reasons"])  # 仅阻断性原因决定退出码；notes 不阻断
    notes = list(verdict.get("notes", []))
    structure: dict = {}
    source_decision_ok = False
    sd = contract.get("source_decision") or {}
    sd_path = REPO / str(sd.get("path", ""))
    if sd.get("path") and sd_path.is_file():
        if sd.get("sha256") and sd["sha256"] != sha256_of(sd_path):
            reasons.append("source-decision.csv 哈希与合同不符")
        else:
            source_decision_ok = True
    else:
        reasons.append("合同未引用有效 source_decision（来源裁定表）")

    if data_mode == "real":
        if not source_decision_ok:
            print("真实模式必须先绑定来源裁定表", file=sys.stderr)
            return 3
        for symbol, entry in (contract.get("data_identity") or {}).items():
            p = Path(entry["path"])
            expected = entry["sha256"]
            actual = sha256_of(p)
            if actual != expected:
                reasons.append(f"{symbol}: 文件哈希与合同不符（先验哈希后消费）")
                continue
            if symbol in A_STAGE_SHAS and actual != A_STAGE_SHAS[symbol]:
                reasons.append(f"{symbol}: 与A阶段清单身份不一致 → 标为新快照，不得静默替换")
            structure[symbol] = structure_read(p)

    # code_identity 哈希核验（读取未提交工作区源码，不只记 git HEAD）
    for rel, expected in (contract.get("code_identity") or {}).items():
        p = REPO / rel
        if not p.is_file():
            reasons.append(f"code_identity 文件缺失: {rel}")
        elif sha256_of(p) != expected:
            reasons.append(f"code_identity 哈希不符: {rel}")

    insufficient = bool(reasons)

    # ── 冻结候选包（先写文件，manifest 最后；失败不写 completed） ──
    try:
        out.mkdir(parents=True)
        (out / "verdict.json").write_text(json.dumps(
            {
                "status": verdict["status"], "reasons": reasons, "notes": notes,
                "allowed_uses": verdict["allowed_uses"], "markets": verdict["markets"],
                "data_mode": data_mode, "generated_at": now.isoformat(),
            },
            ensure_ascii=False, indent=1,
        ) + "\n")
        code_dir = out / "code-freeze"
        code_dir.mkdir()
        copied: dict[str, str] = {}
        for rel in CODE_FILES + SPEC_FILES + [CARD_PATH]:
            src = REPO / rel
            dest = code_dir / rel.replace("/", "__")
            dest.write_bytes(src.read_bytes())
            copied[rel] = sha256_of(src)
        if source_decision_ok:
            dest = code_dir / sd["path"].replace("/", "__")
            dest.write_bytes(sd_path.read_bytes())
            copied[sd["path"]] = sha256_of(sd_path)
        cal = (contract.get("calendar_identity") or {}).get("CN") or {}
        if cal.get("source"):
            cal_src = REPO / str(cal["source"])
            if cal_src.is_file():
                dest = code_dir / str(cal["source"]).replace("/", "__")
                dest.write_bytes(cal_src.read_bytes())
                copied[str(cal["source"])] = sha256_of(cal_src)
        (out / "environment.json").write_text(json.dumps({
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependencies": {m: __import__(m).__version__ for m in ("pandas", "numpy")},
            "git_head": git_head(),
            "note": "读取的是未提交工作区源码原字节（code-freeze/），git HEAD仅参考",
        }, ensure_ascii=False, indent=1) + "\n")
        manifest = {
            "schema_version": "1.0.0",
            "protocol_candidate": {
                "id": "b0-dual-ma-close-state-readiness",
                "version": "1.0.0",
                "status": "candidate_not_approved",
            },
            "data_mode": data_mode,
            "contract_sha256": sha256_of(contract_path),
            "files": copied,
            "structure": structure,
            "written_at": now.isoformat(),
            "completed": False,
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n"
        )
        # 全部成功才置 completed
        manifest["completed"] = True
        manifest["file_hashes"] = {
            f.name: sha256_of(f)
            for f in sorted(out.rglob("*")) if f.is_file() and f.name != "manifest.json"
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n"
        )
    except OSError as exc:
        print(f"写盘失败（不写 completed）: {exc}", file=sys.stderr)
        return 3

    for r in reasons:
        print(f"BLOCKING: {r}")
    for n in notes:
        print(f"NOTE: {n}")
    if insufficient:
        print("EXIT 2: 资料不足（资格诊断已冻结，见 verdict.json）")
        return 2
    print("EXIT 0: 本轮声明用途资料齐备（不自动启动B1）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
