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
    parser.add_argument("--protocol", required=True, help="不可变协议 JSON 路径")
    parser.add_argument("--out", required=True, help="输出目录（必须不存在）")
    args = parser.parse_args()
    return run_protocol(args.protocol, args.out)


if __name__ == "__main__":
    sys.exit(main())
