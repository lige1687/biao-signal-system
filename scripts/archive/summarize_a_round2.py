"""读 A round2 结果，输出矩阵与候选最优点。"""
from __future__ import annotations

import json
from pathlib import Path

D = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/A_round2")


def load():
    out = {}
    for fp in sorted(D.glob("cm*_ta*_rr*.json")):
        out[fp.stem] = json.loads(fp.read_text(encoding="utf-8"))
    return out


def main():
    cells = load()
    cms = [0.5, 1.0]
    tas = [0.5, 1.0, 1.5]
    rrs = [None, 3.0, 4.0]
    rr_labels = ["None", "3", "4"]

    def lookup(cm, ta, rr):
        rr_tag = "None" if rr is None else f"{rr:.1f}"
        tag = f"cm{int(cm*10):02d}_ta{int(ta*10)}_rr{rr_tag.replace('.', '_')}"
        return cells.get(tag)

    def cell(e, t):
        if e is None:
            return f"  ?  ({t})"
        return f"{e:+.2f}({t})"

    for label, key in [("期望 R（笔数）", "expectancy_r"), ("样本外期望 R", "oos_expectancy"), ("样本内期望 R", "is_expectancy")]:
        print(f"\n== {label} ==")
        for rridx, rr in enumerate(rrs):
            print(f"  rr={rr_labels[rridx]}")
            hd = "cm\\ta"
            print(f"    {hd:>7}", end="")
            for ta in tas:
                print(f"{ta}".rjust(10), end="")
            print()
            for cm in cms:
                print(f"    {cm:>7}", end="")
                for ta in tas:
                    c = lookup(cm, ta, rr)
                    if c is None:
                        print(" " * 10, end="")
                        continue
                    if key == "expectancy_r":
                        e = c["overview"][key]
                        t = c["overview"]["trade_count"]
                    elif key == "oos_expectancy":
                        e = c["oos_expectancy"]
                        t = c["oos_trade_count"]
                    else:
                        e = c["is_expectancy"]
                        t = c["is_trade_count"]
                    print(cell(e, t).rjust(10), end="")
                print()

    print("\n== 候选最优点（IS>0 且 OOS>0 且 N>=50） ==")
    cands = []
    for tag, c in cells.items():
        t = c["overview"]["trade_count"] or 0
        if t < 50:
            continue
        is_e = c["is_expectancy"] or 0
        oos_e = c["oos_expectancy"] or 0
        if is_e <= 0 or oos_e <= 0:
            continue
        cands.append((tag, c))
    cands.sort(key=lambda x: -(x[1]["overview"]["expectancy_r"] or 0))
    for tag, c in cands:
        ov = c["overview"]
        print(
            f"  {tag}  N={ov['trade_count']:>3}  expR={ov['expectancy_r']:+.3f}  "
            f"PF={ov['profit_factor']}  IS={c['is_expectancy']:+.3f}({c['is_trade_count']})  "
            f"OOS={c['oos_expectancy']:+.3f}({c['oos_trade_count']})  "
            f"top1={c['top1_symbol']}({c['top1_total_r']:+.1f}R)"
        )


if __name__ == "__main__":
    main()
