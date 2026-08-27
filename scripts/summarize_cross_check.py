"""读 cross_check 全部结果，输出全池 vs 排除 top1 对比表 + 分年份 + 牛熊横盘。"""
from __future__ import annotations

import json
from pathlib import Path

D = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/cross_check")


def load():
    out = {}
    for fp in sorted(D.glob("*.json")):
        out[fp.stem] = json.loads(fp.read_text(encoding="utf-8"))
    return out


def main():
    cells = load()

    # 分组：候选 -> {full, no_top1}
    groups: dict[str, dict[str, dict]] = {}
    for tag, c in cells.items():
        cand = c["candidate"]
        v = c["variant"]
        groups.setdefault(cand, {})[v] = c

    print("=" * 100)
    print("全池 vs 排除 top1 对比（按期望 R、IS、OOS、PF）")
    print("=" * 100)
    print(f"{'candidate':<22} {'variant':<14} {'N':>5} {'expR':>7} {'PF':>5} {'IS_R':>7} {'IS_N':>5} {'OOS_R':>7} {'OOS_N':>5}  top1")
    for cand, vs in groups.items():
        for vname in sorted(vs.keys()):
            c = vs[vname]
            ov = c["overview"]
            is_e = c["is_expectancy"] if c["is_expectancy"] is not None else float("nan")
            oos_e = c["oos_expectancy"] if c["oos_expectancy"] is not None else float("nan")
            is_n = c["is_trade_count"] or 0
            oos_n = c["oos_trade_count"] or 0
            print(
                f"{cand:<22} {vname:<14} {ov['trade_count'] or 0:>5} "
                f"{ov['expectancy_r']:+.3f}  {ov['profit_factor']:.2f}  "
                f"{is_e:+.3f}  {is_n:>5}  {oos_e:+.3f}  {oos_n:>5}  {c['top1_symbol'] or '-'}"
            )

    print()
    print("=" * 100)
    print("分年份贡献（仅全池）")
    print("=" * 100)
    for cand, vs in groups.items():
        c = vs.get("full")
        if not c:
            continue
        years = sorted(c["by_year"].items())
        line = f"{cand:<22} "
        for y, m in years:
            line += f"{y}={m['expectancy_r']:+.2f}({m['trade_count']})  "
        print(line)

    print()
    print("=" * 100)
    print("牛/熊/横盘（基准时钟）—— 仅全池")
    print("=" * 100)
    for cand, vs in groups.items():
        c = vs.get("full")
        if not c:
            continue
        regs = c["by_regime"]
        line = f"{cand:<22} "
        for r, m in regs.items():
            line += f"{r}={m['expectancy_r']:+.2f}({m['trade_count']})  "
        print(line)


if __name__ == "__main__":
    main()
