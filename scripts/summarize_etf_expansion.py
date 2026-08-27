"""汇总 etf_expansion 所有结果。"""
from __future__ import annotations

import json
from pathlib import Path

RAW = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/etf_expansion")


def _load(d):
    out = {}
    for fp in sorted(d.glob("*.json")):
        try:
            out[fp.stem] = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
    return out


def _cell(c, want_oos=False):
    if "error" in c or not c.get("overview"):
        return "-"
    ov = c["overview"]
    t = ov["trade_count"] or 0
    if t == 0:
        return f"0"
    if want_oos:
        e = c.get("oos_expectancy")
        n = c.get("oos_trade_count") or 0
    else:
        e = ov["expectancy_r"]
        n = t
    if e is None:
        return f"?({n})"
    return f"{e:+.2f}({n})"


def section_pool():
    d = RAW / "A_pool"
    cells = _load(d)
    print("=" * 100)
    print("任务二·Level 1：4 大子池（A_cm05_ta10_rrNone）")
    print("=" * 100)
    for k in ["行业ETF", "宽基ETF", "海外ETF", "指数本体", "no_top1", "no_top3"]:
        if k not in cells:
            continue
        c = cells[k]
        ov = c["overview"]
        print(f"  {k:<14s}  N={ov['trade_count'] or 0:>4}  expR={ov['expectancy_r']:+.3f}  "
              f"PF={ov['profit_factor']}  IS={c['is_expectancy']:+.3f}({c['is_trade_count'] or 0})  "
              f"OOS={c['oos_expectancy']:+.3f}({c['oos_trade_count'] or 0})  top1={c['top1_symbol']}")


def section_industry():
    d = RAW / "A_each_industry"
    cells = _load(d)
    print()
    print("=" * 100)
    print("任务二·Level 2：行业分化表（每行业 ETF 单标的，A 稳健档）")
    print("=" * 100)
    rows = []
    for tag, c in cells.items():
        if "error" in c or not c.get("overview"):
            continue
        ov = c["overview"]
        rows.append({
            "tag": tag,
            "n": ov["trade_count"] or 0,
            "expR": ov["expectancy_r"] or 0.0,
            "oos": c.get("oos_expectancy") or 0.0,
            "is_": c.get("is_expectancy") or 0.0,
            "total_r": ov.get("total_r") or 0.0,
        })
    rows.sort(key=lambda r: -r["total_r"])
    print(f"  {'tag':<40s} {'N':>4} {'expR':>7} {'IS':>7} {'OOS':>7} {'totalR':>9}")
    for r in rows:
        print(f"  {r['tag']:<40s} {r['n']:>4} {r['expR']:+.2f} {r['is_']:+.2f} {r['oos']:+.2f} {r['total_r']:+.1f}")


def section_index_vs_etf():
    d = RAW / "index_vs_etf"
    cells = _load(d)
    print()
    print("=" * 100)
    print("任务三：指数本体 vs 对应 ETF（A 稳健档）")
    print("=" * 100)
    for k in ["创业板_ETF_159915.SZ", "创业板_指数_399006.SZ", "创业板_both",
              "沪深300_ETF_510300.SS", "沪深300_指数_000300.SS", "沪深300_both",
              "标普500_ETF_513500.SS", "标普500_指数_GSPC", "标普500_both"]:
        if k not in cells:
            continue
        c = cells[k]
        ov = c["overview"]
        print(f"  {k:<28s}  N={ov['trade_count'] or 0:>3}  expR={ov['expectancy_r']:+.3f}  "
              f"PF={ov['profit_factor']}  IS={c['is_expectancy']:+.3f}({c['is_trade_count'] or 0})  "
              f"OOS={c['oos_expectancy']:+.3f}({c['oos_trade_count'] or 0})  top1={c['top1_symbol']}")


def section_b_industry():
    d = RAW / "B_industry"
    cells = _load(d)
    print()
    print("=" * 100)
    print("任务四：B cb=40/cl=5% 在国内半导体/通信/AI 行业 ETF 集群")
    print("=" * 100)
    for k in sorted(cells.keys()):
        c = cells[k]
        ov = c["overview"]
        t = ov["trade_count"] or 0
        exp = ov["expectancy_r"]
        exp_s = f"{exp:+.3f}" if isinstance(exp, (int, float)) and exp is not None else "  nan"
        pf = ov["profit_factor"]
        pf_s = f"{pf:.3f}" if isinstance(pf, (int, float)) and pf is not None else "-"
        if t == 0:
            print(f"  {k:<32s}  N=0（无信号）")
            continue
        is_e = c.get("is_expectancy")
        oos_e = c.get("oos_expectancy")
        is_s = f"{is_e:+.3f}({c.get('is_trade_count') or 0})" if isinstance(is_e, (int, float)) else f" ?({c.get('is_trade_count') or 0})"
        oos_s = f"{oos_e:+.3f}({c.get('oos_trade_count') or 0})" if isinstance(oos_e, (int, float)) else f" ?({c.get('oos_trade_count') or 0})"
        print(f"  {k:<32s}  N={t:>3}  expR={exp_s}  PF={pf_s}  IS={is_s}  OOS={oos_s}  top1={c['top1_symbol'] or '-'}")


if __name__ == "__main__":
    section_pool()
    section_industry()
    section_index_vs_etf()
    section_b_industry()
