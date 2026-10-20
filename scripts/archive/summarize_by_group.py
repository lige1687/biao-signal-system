"""读 by_symbol_group 结果，输出按候选 × 标的类型的矩阵。"""
from __future__ import annotations

import json
from pathlib import Path

D = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/by_symbol_group")


def load():
    out = {}
    for fp in sorted(D.glob("*.json")):
        out[fp.stem] = json.loads(fp.read_text(encoding="utf-8"))
    return out


def main():
    cells = load()
    # 行：candidate，列：group
    cands = [
        "A_cm05_ta10_rrNone",
        "A_cm10_ta10_rr4",
        "A_cm10_ta15_rr4",
        "B_cb40_cl05",
        "B_cb40_cl03",
    ]
    groups = ["A股指数", "美股_港股_韩国指数", "A股ETF", "申万行业板块", "美股行业ETF", "A股个股"]

    def cell_str(c, want_n=False):
        if "error" in c:
            return "ERR"
        ov = c["overview"]
        t = ov["trade_count"] or 0
        if t == 0:
            return f"  0"
        e = ov["expectancy_r"]
        if e is None:
            return f"  ?  ({t})"
        if want_n:
            return f"{e:+.2f}({t})"
        return f"{e:+.2f}"

    # 期望 R 矩阵
    print("== 期望 R（笔数）==")
    print(f"{'cand':<22}", end="")
    for g in groups:
        print(f"  {g:>10}", end="")
    print()
    for cand in cands:
        print(f"{cand:<22}", end="")
        for g in groups:
            tag = f"{cand}__{g}"
            c = cells.get(tag, {})
            print(f"  {cell_str(c, want_n=True):>10}", end="")
        print()

    # OOS 期望
    print("\n== 样本外期望 R（笔数）==")
    print(f"{'cand':<22}", end="")
    for g in groups:
        print(f"  {g:>10}", end="")
    print()
    for cand in cands:
        print(f"{cand:<22}", end="")
        for g in groups:
            tag = f"{cand}__{g}"
            c = cells.get(tag, {})
            if "error" in c or not c.get("overview") or not c["overview"].get("trade_count"):
                print(f"  {'-':>10}", end="")
                continue
            t = c["oos_trade_count"] or 0
            e = c["oos_expectancy"]
            if e is None:
                print(f"  {'?':>10}", end="")
            else:
                print(f"  {e:+.2f}({t})".rjust(11), end="")
        print()

    # IS 期望
    print("\n== 样本内期望 R（笔数）==")
    print(f"{'cand':<22}", end="")
    for g in groups:
        print(f"  {g:>10}", end="")
    print()
    for cand in cands:
        print(f"{cand:<22}", end="")
        for g in groups:
            tag = f"{cand}__{g}"
            c = cells.get(tag, {})
            if "error" in c or not c.get("overview") or not c["overview"].get("trade_count"):
                print(f"  {'-':>10}", end="")
                continue
            t = c["is_trade_count"] or 0
            e = c["is_expectancy"]
            if e is None:
                print(f"  {'?':>10}", end="")
            else:
                print(f"  {e:+.2f}({t})".rjust(11), end="")
        print()


if __name__ == "__main__":
    main()
