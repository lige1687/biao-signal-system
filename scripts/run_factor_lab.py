"""factor_lab 统一入口：python scripts/run_factor_lab.py --protocol <file> --out <new dir>

退出码：0=检查完成；2=合法资料不足/命令参数冲突；3=身份/格式失败；1=期望核对失败。
输出目录已存在、协议含 current 指针、输入哈希不符均拒绝（3）。
--review-workflow-contract 仅审查合同声明并输出 stdout，不授予研究执行权限。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _review_workflow_contract(path: str) -> int:
    from lei_signal.research.question_contract import validate_workflow_contract

    result = {
        "mode": "declaration_review",
        "declaration_valid": False,
        "execution_authorized": False,
        "scope": "contract_declarations_only",
    }
    try:
        contract = json.loads(Path(path).read_text(encoding="utf-8"))
        validate_workflow_contract(contract)
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        RecursionError,
        OverflowError,
    ) as exc:
        result["error"] = str(exc)
        print(json.dumps(result, ensure_ascii=False))
        return 3
    result["declaration_valid"] = True
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="factor_lab synthetic protocol runner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--protocol", help="不可变合成协议 JSON 路径")
    mode.add_argument("--benchmark-protocol", help="冻结的经典基准真实ETF研究协议")
    mode.add_argument(
        "--attribution-protocol", help="冻结的经典月频同期解释协议（非预测或账户收益）"
    )
    mode.add_argument("--workflow-contract", help="新研究六阶段受控合同（已有冻结入口不变）")
    mode.add_argument("--workflow-draft", help="先检查资料并做模拟流程演练，生成冻结合同")
    mode.add_argument(
        "--review-workflow-contract",
        help="仅用现有校验器审查合同声明并输出 stdout；不检查实际资料或执行研究",
    )
    parser.add_argument(
        "--register-report", action="store_true", help="登记本次基准报告至现有实验库"
    )
    parser.add_argument("--out", help="执行模式必填的输出目录（必须不存在）；声明审查禁止使用")
    parser.add_argument("--reuse-predictions", help="同预测依赖的已验收输出；只重汇总，不拟合")
    args = parser.parse_args()
    if args.review_workflow_contract is not None:
        if args.out is not None or args.register_report or args.reuse_predictions is not None:
            parser.error(
                "declaration review forbids --out, --register-report and --reuse-predictions"
            )
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            return _review_workflow_contract(args.review_workflow_contract)
        finally:
            sys.dont_write_bytecode = previous
    if args.out is None:
        parser.error("execution modes require --out")
    if args.attribution_protocol:
        if args.register_report or args.reuse_predictions:
            parser.error(
                "attribution mode neither publishes workflow receipts "
                "nor reuses workflow predictions"
            )
        from lei_signal.research.factor_lab.classic_attribution import run_attribution

        run_attribution(args.attribution_protocol, args.out)
        return 0
    if args.workflow_draft:
        if args.register_report or args.reuse_predictions:
            parser.error("draft mode does not publish or reuse final predictions")
        from lei_signal.research.workflow import freeze_workflow

        freeze_workflow(args.workflow_draft, args.out)
        return 0
    if args.workflow_contract:
        from lei_signal.research.workflow import run_workflow

        return run_workflow(
            args.workflow_contract,
            args.out,
            register_report=args.register_report,
            reuse_predictions=args.reuse_predictions,
        )
    if args.reuse_predictions:
        parser.error("--reuse-predictions requires --workflow-contract")
    if args.benchmark_protocol:
        from lei_signal.research.factor_lab.benchmark_pilot import run_pilot

        run_pilot(args.benchmark_protocol, args.out, register_report=args.register_report)
        return 0
    if args.register_report:
        parser.error("--register-report requires --benchmark-protocol or --workflow-contract")
    from lei_signal.research.factor_lab.runner import run_protocol

    return run_protocol(args.protocol, args.out)


if __name__ == "__main__":
    sys.exit(main())
