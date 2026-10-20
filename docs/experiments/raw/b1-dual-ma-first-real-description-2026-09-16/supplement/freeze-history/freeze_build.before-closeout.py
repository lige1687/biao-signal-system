"""Task5：生成 B1 冻结协议 protocol-v1.0.0.json（排他）并保存代码原字节/环境。

没有代码哈希就不得正式计算；本脚本把当前必需代码键原字节与哈希一并封存。
"""
import hashlib
import json
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent
ROOT = RAW.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lei_signal.research.factor_unit.b1_contract import (  # noqa: E402
    CARD_PATH,
    CARD_SHA256,
    FIXED_DATA_DECLARATIONS,
    FIXED_INPUT_IDENTITY,
    FIXED_PARAMS,
    REQUIRED_CODE_KEYS,
    TASK_BOOK,
)

STANDARDS = [
    ("docs/research/experiment-backtest-principles.md", "1.1"),
    ("docs/research/definition-standard.md", "1.1.0"),
    ("docs/research/ai-execution-contract.md", "1.0.1"),
    ("docs/research/experiment-report-template.md", "1.1.0"),
    ("docs/research/definitions.v1.json", "容器1.2.0（只读）"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    proto_path = RAW / f"protocol-v{version}.json"
    if proto_path.exists():
        print(f"REFUSE: {proto_path} 已存在（排他）", file=sys.stderr)
        return 3
    now = datetime.now(timezone(timedelta(hours=8)))
    code_identity = {rel: sha(ROOT / rel) for rel in REQUIRED_CODE_KEYS}

    snap = RAW / "freeze" / "code-snapshot"
    for rel in REQUIRED_CODE_KEYS:
        dest = snap / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / rel).read_bytes())

    import numpy
    import pandas
    import yaml
    env = {"python": platform.python_version(), "platform": platform.platform(),
           "dependencies": {"pandas": pandas.__version__,
                            "numpy": numpy.__version__,
                            "PyYAML": yaml.__version__},
           "frozen_at": now.isoformat(),
           "note": "pytest/ruff 版本见正式运行 environment.json；源码以原字节为准，"
                   "不用 HEAD 代表"}
    (RAW / "freeze" / "environment.json").write_text(
        json.dumps(env, ensure_ascii=False, indent=1) + "\n")

    protocol = {
        "spec_status": "frozen",
        "spec_version": version,
        "frozen_at": now.isoformat(),
        **FIXED_PARAMS,
        **FIXED_DATA_DECLARATIONS,
        "candidate_card": {"path": CARD_PATH, "sha256": CARD_SHA256},
        "task_book": dict(TASK_BOOK),
        "standards": [{"path": p, "version": v, "sha256": sha(ROOT / p)}
                      for p, v in STANDARDS],
        "input_identity": dict(FIXED_INPUT_IDENTITY),
        "code_identity": code_identity,
        "authorization": {
            "user_words": "可以的，开写计划（2026-09-16，授权编制任务书）；"
                          "用户将任务书交给执行者并要求执行后启动实现与预算内运行",
            "task_book_sha256": TASK_BOOK["sha256"],
            "boundary": "离线、单产品、固定目标的历史描述消费者开发和首次正式运行；"
                        "不含联网、参数寻优、扩池、生产、OKR",
        },
        "research_family": "B1-dual-ma-unit",
        "attempt_history": [
            "2026-09-15 四轮：B0集中修复→四项限定修复→510300离线输入包→主控S1-S4收尾；"
            "真实资格0次运行；本次为首次真实历史描述",
        ],
        "run_budget": {
            "real_formal_runs": "1次；可定位工程错误后新编号修正再1次；结果不好不得重跑",
            "old_regression": "≤2次",
            "synthetic_cli_debug": "≤3批",
            "restore_verify": "1次（只核字节与从observations重汇总，不重算状态/目标）",
            "network": 0,
        },
        "tolerance": {"float": 1e-12,
                      "counts_keys_nulls": "严格一致"},
        "output_fields": ["protocol.source.json", "input-package/", "source-snapshot/",
                          "environment.json", "states.csv", "observations.csv",
                          "summary.json", "quality.json", "report.md",
                          "manifest.json"],
        "no_claims": ["strategy_return", "annualization", "significance", "IC",
                      "alpha", "production_advice", "factor_effective",
                      "total_return_wealth", "point_in_time_verified"],
    }
    proto_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=1) + "\n")
    print(f"protocol frozen: {proto_path}")
    print(f"sha256: {sha(proto_path)}")

    # 冻结后立即自验（只校验，不计算）
    from lei_signal.research.factor_unit.b1_contract import validate_b1_protocol
    validate_b1_protocol(proto_path, ROOT)
    print("validate_b1_protocol: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
