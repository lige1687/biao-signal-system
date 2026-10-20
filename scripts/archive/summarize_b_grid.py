"""读 B 细网格结果，输出按合并性可读的矩阵 + 横向对比表。"""
from __future__ import annotations

import json
from pathlib import Path

D = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/B_breakout_matrix")


def load():
    cells = {}
    for fp in sorted(D.glob("cb*_cl*.json")):
        tag = fp.stem
        cb = int(tag.split("_")[0][2:])
        cl = int(tag.split("_")[1][2:]) / 100
        cells[(cb, cl)] = json.loads(fp.read_text(encoding="utf-8"))
    return cells


def main():
    cells = load()
    cbs = sorted({k[0] for k in cells})
    cls = sorted({k[1] for k in cells})

    def cell(e, t):
        if e is None:
            return f"  ?  ({t})"
        return f"{e:+.2f}({t})"

    h = "cb\\cl"
    print("== 期望 R（笔数） ==")
    print(f"{h:>7}", end="")
    for cl in cls:
        print(f"{int(cl*100):>4}%".rjust(10), end="")
    print()
    for cb in cbs:
        print(f"{cb:>7}", end="")
        for cl in cls:
            c = cells.get((cb, cl))
            if c is None:
                print(" " * 10, end="")
                continue
            t = c["overview"]["trade_count"] or 0
            e = c["overview"]["expectancy_r"]
            print(cell(e, t).rjust(10), end="")
        print()

    print("\n== 样本外期望 R（笔数） ==")
    print(f"{h:>7}", end="")
    for cl in cls:
        print(f"{int(cl*100):>4}%".rjust(10), end="")
    print()
    for cb in cbs:
        print(f"{cb:>7}", end="")
        for cl in cls:
            c = cells.get((cb, cl))
            if c is None:
                print(" " * 10, end="")
                continue
            t = c["oos_trade_count"] or 0
            e = c["oos_expectancy"]
            print(cell(e, t).rjust(10), end="")
        print()

    print("\n== 样本内期望 R（笔数） ==")
    print(f"{h:>7}", end="")
    for cl in cls:
        print(f"{int(cl*100):>4}%".rjust(10), end="")
    print()
    for cb in cbs:
        print(f"{cb:>7}", end="")
        for cl in cls:
            c = cells.get((cb, cl))
            if c is None:
                print(" " * 10, end="")
                continue
            t = c["is_trade_count"] or 0
            e = c["is_expectancy"]
            print(cell(e, t).rjust(10), end="")
        print()

    print("\n== 头部 1 标的 total_r / 总 R 占比 ==")
    print(f"{h:>7}", end="")
    for cl in cls:
        print(f"{int(cl*100):>4}%".rjust(10), end="")
    print()
    for cb in cbs:
        print(f"{cb:>7}", end="")
        for cl in cls:
            c = cells.get((cb, cl))
            if c is None or not c["overview"]["trade_count"]:
                print(" " * 10, end="")
                continue
            total = c["overview"]["total_r"] or 0.0
            top1 = c["top1_total_r"] or 0.0
            share = top1 / total if total else 0.0
            print(f"{share*100:+.0f}%".rjust(10), end="")
        print()

    print("\n== 候选最优点（OOS>0 且总 R>0 且 trade>=30） ==")
    cands = []
    for k, c in cells.items():
        t = c["overview"]["trade_count"] or 0
        if t < 30:
            continue
        if (c["oos_expectancy"] or 0) <= 0:
            continue
        if (c["overview"]["total_r"] or 0) <= 0:
            continue
        cands.append((k, c))
    cands.sort(key=lambda x: -(x[1]["overview"]["expectancy_r"] or 0))
    for k, c in cands:
        ov = c["overview"]
        print(
            f"  cb={k[0]:>3}  cl={k[1]:.2%}  N={ov['trade_count']:>3}  "
            f"expR={ov['expectancy_r']:+.3f}  PF={ov['profit_factor']:.2f}  "
            f"IS={c['is_expectancy']:+.3f}  OOS={c['oos_expectancy']:+.3f}  "
            f"top1={c['top1_symbol']}({c['top1_total_r']:+.1f}R)"
        )


if __name__ == "__main__":
    main()
