"""factor_lab 统一入口：python scripts/run_factor_lab.py --protocol <file> --out <new dir>

退出码：0=合成检查完成；2=合法资料不足；3=身份/格式失败；1=期望核对失败。
输出目录已存在、协议含 current 指针、输入哈希不符均拒绝（3）。
"""

from __future__ import annotations

import argparse
import sys

from lei_signal.research.factor_lab.runner import run_protocol


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
    parser.add_argument(
        "--register-report", action="store_true", help="登记本次基准报告至现有实验库"
    )
    parser.add_argument("--out", required=True, help="输出目录（必须不存在）")
    parser.add_argument("--reuse-predictions", help="同预测依赖的已验收输出；只重汇总，不拟合")
    args = parser.parse_args()
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
        from lei_signal.research.workflow import freeze_workflow

        if args.register_report or args.reuse_predictions:
            parser.error("draft mode does not publish or reuse final predictions")
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
    return run_protocol(args.protocol, args.out)


if __name__ == "__main__":
    sys.exit(main())
