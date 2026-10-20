#!/usr/bin/env python3
"""因子证据可靠性 v1：冻结协议生成器（Task 4，一次性执行）。

从 ``contract`` 模块常量生成正式协议 ``protocol-v1.0.0.json``（排他创建，
已存在即拒绝），并把 8 个必需代码键的**原字节**快照到 ``freeze/v1.0.0/``
（版本目录排他，不共用覆盖）。修改代码/目标/方法必须新版本，旧件保留。
草案 ``protocol-v1.0.0.draft.json`` 保留为历史（其 input_identity 为嵌套
布局、code_identity 为占位），最终以本脚本生成的扁平布局为准。
"""
from __future__ import annotations

import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.research.factor_evidence.contract import (  # noqa: E402
    CARD,
    FIXED_INPUT_IDENTITY,
    FIXED_NO_CLAIMS,
    FIXED_PARAMS,
    FIXED_TOLERANCE,
    IDENTITY,
    REQUIRED_CODE_KEYS,
    REQUIRED_OUTPUT_FIELDS,
    REQUIRED_STANDARDS,
    SPEC_VERSION,
    TASK_BOOK,
    sha256_file,
)

RAW = REPO / "docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16"
PROTOCOL = RAW / f"protocol-v{SPEC_VERSION}.json"
FREEZE_DIR = RAW / "freeze" / SPEC_VERSION


def main() -> None:
    if PROTOCOL.exists():
        raise SystemExit(f"排他创建失败：{PROTOCOL} 已存在（修改须新版本）")
    if FREEZE_DIR.exists():
        raise SystemExit(f"排他创建失败：{FREEZE_DIR} 已存在（修改须新版本）")

    protocol = {
        "identity": IDENTITY,
        "spec_status": "frozen",
        "spec_version": SPEC_VERSION,
        "use": "post_hoc_historical_sensitivity_diagnostic",
        "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
        "analysis_basis": ("只消费 B1 已封存观察表（日期、二元状态、未来结果、"
                           "合法性）；不重算真实状态、标签或未来目标，"
                           "不读价格序列另造标签"),
        "fixed_params": FIXED_PARAMS,
        "standards": [{"path": a, "version": b, "sha256": c}
                      for a, b, c in REQUIRED_STANDARDS],
        "task_book": dict(TASK_BOOK),
        "candidate_card": dict(CARD),
        "input_identity": dict(FIXED_INPUT_IDENTITY),
        "code_identity": {rel: sha256_file(REPO / rel)
                          for rel in REQUIRED_CODE_KEYS},
        "tolerance": dict(FIXED_TOLERANCE),
        "output_fields": list(REQUIRED_OUTPUT_FIELDS),
        "no_claims": list(FIXED_NO_CLAIMS),
        "exit_codes": {"0": "工程完成（不等于结论有效）",
                       "2": "资料/数值不足", "3": "身份/合同错误"},
        "approval": None,
        "approval_note": ("授权只来自任务书及派发文件的用户授权记录；"
                          "协议不得自填 approval=true"),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
    PROTOCOL.write_text(json.dumps(protocol, ensure_ascii=False, indent=1,
                                   allow_nan=False) + "\n", encoding="utf-8")

    FREEZE_DIR.mkdir(parents=True)
    snap = FREEZE_DIR / "code-snapshot"
    snap.mkdir()
    copied = {}
    for rel in REQUIRED_CODE_KEYS:
        dst = snap / rel.replace("/", "__")
        shutil.copyfile(REPO / rel, dst)
        copied[rel] = sha256_file(dst)
    # 快照字节必须与协议声明逐值一致
    assert copied == protocol["code_identity"], "快照字节与协议声明不一致"
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": __import__("numpy").__version__,
        "pandas": __import__("pandas").__version__,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "恢复运行环境参考；起点矩阵与逐次结果已另存，"
                "不依赖随机库版本即可复算汇总",
    }
    (FREEZE_DIR / "environment.json").write_text(
        json.dumps(env, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copyfile(PROTOCOL, FREEZE_DIR / f"protocol-v{SPEC_VERSION}.json")

    print("frozen protocol:", PROTOCOL.relative_to(REPO))
    print("protocol sha256:", sha256_file(PROTOCOL))
    print("freeze dir:", FREEZE_DIR.relative_to(REPO),
          "files:", len(copied) + 2)


if __name__ == "__main__":
    main()
