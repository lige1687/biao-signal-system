#!/usr/bin/env python3
"""因子证据可靠性 v1 CLI：--protocol PATH --out NEW_DIR。

先验证后计算：输出目录已存在即拒绝；协议必须为冻结正式版本
``protocol-v1.0.0.json``（文件名与内容版本一致，草案/current 拒绝）。
退出码：0=工程完成（不等于结论有效）；2=资料/数值不足；3=身份/合同错误。
导入本模块不做任何计算、不写盘。真实状态/目标重算入口不存在于本 CLI。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lei_signal.research.factor_evidence.runner import main


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="run_factor_evidence_reliability",
        description=("对 B1 已封存观察表执行固定方法的可靠性补充分析"
                     "（全期/逐年/留一年、区间重叠、成对循环区块重抽）；"
                     "不重算真实状态或未来目标。"))
    parser.add_argument("--protocol", required=True,
                        help="冻结协议路径 protocol-v1.0.0.json")
    parser.add_argument("--out", required=True,
                        help="新输出目录（必须不存在；拒绝覆盖）")
    parser.add_argument("--repo-root", default=".",
                        help="仓库根目录（默认当前目录）")
    return parser.parse_args(argv)


def cli(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    return main(args.protocol, args.out, Path(args.repo_root).resolve())


if __name__ == "__main__":
    raise SystemExit(cli())
