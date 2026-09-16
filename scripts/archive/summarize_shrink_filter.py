"""缩量回调验证汇总：从 raw/shrink_filter/*.json 生成报告表格。

输出（stdout，markdown）：
  1. 联合矩阵总表（两池 × 4 配置）
  2. 缩量组 vs 非缩量组的 IS/OOS 分解
  3. 排除 top1 / top3 复核
  4. 分年份归因（缩量组 vs 非缩量组）
  5. 敏感性（窗口变体 + 严格档）
  6. 分标的类型（宽基 / 行业 / 指数）
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "shrink_filter"

SPLIT = "2024-08-25"  # OOS 切分日（与第四轮一致）


def _load(tag: str, pool: str) -> dict | None:
    fp = RAW / f"{tag}__{pool}.json"
    if not fp.exists():
        return None
    return json.loads(fp.read_text(encoding="utf-8"))


def _f(v: float | None, sign: bool = True) -> str:
    if v is None:
        return "-"
    return f"{v:+.3f}" if sign else f"{v:.3f}"


def _key(t: dict) -> tuple[str, str]:
    return (t["symbol"], t["signal_date"])


def _grp(trades: list[dict]) -> dict:
    rs = [t["r_net"] for t in trades if t["r_net"] is not None]
    if not rs:
        return {"n": 0}
    wins = sum(1 for r in rs if r > 0)
    is_ = [t["r_net"] for t in trades
           if t["r_net"] is not None and t["signal_date"] < SPLIT]
    oos = [t["r_net"] for t in trades
           if t["r_net"] is not None and t["signal_date"] >= SPLIT]
    return {
        "n": len(rs),
        "win": wins / len(rs),
        "exp": sum(rs) / len(rs),
        "total": sum(rs),
        "is": (sum(is_) / len(is_)) if is_ else None,
        "is_n": len(is_),
        "oos": (sum(oos) / len(oos)) if oos else None,
        "oos_n": len(oos),
    }


def _grp_str(g: dict) -> str:
    if g.get("n", 0) == 0:
        return "N=0"
    return (
        f"N={g['n']} 胜率{g['win']:.0%} expR={g['exp']:+.3f} totalR={g['total']:+.1f}"
        f"｜IS={_f(g['is'])}({g['is_n']}) OOS={_f(g['oos'])}({g['oos_n']})"
    )


def overview_tables() -> None:
    print("## 1. 联合矩阵（none / shrink / vacuum / shrink+vacuum）\n")
    for pool in ("A股ETF", "全池"):
        print(f"### {pool}\n")
        print("| 配置 | N | expR | totalR | PF | IS (n) | OOS (n) | ΔexpR | ΔtotalR |")
        print("|---|---:|---:|---:|---:|---|---|---:|---:|")
        base = _load("baseline", pool)
        for tag, cn in (("baseline", "none（对照）"), ("shrink", "shrink"),
                        ("vacuum", "vacuum"), ("shrink_vacuum", "shrink+vacuum")):
            s = _load(tag, pool)
            if s is None:
                print(f"| {cn} | （未跑）" + " - |" * 8)
                continue
            ov = s["overview"]
            de = (ov["expectancy_r"] or 0) - (base["overview"]["expectancy_r"] or 0)
            dt = (ov["total_r"] or 0) - (base["overview"]["total_r"] or 0)
            print(
                f"| {cn} | {ov['trade_count'] or 0} | {_f(ov['expectancy_r'])} "
                f"| {_f(ov['total_r'])} | {ov['profit_factor'] or 0:.2f} "
                f"| {_f(s['is_expectancy'])} ({s['is_trade_count'] or 0}) "
                f"| {_f(s['oos_expectancy'])} ({s['oos_trade_count'] or 0}) "
                f"| {de:+.3f} | {dt:+.1f} |"
            )
        print()


def group_is_oos() -> None:
    print("## 2. 缩量组 vs 非缩量组（IS/OOS 分解，任务一.1）\n")
    for pool in ("A股ETF", "全池"):
        base = _load("baseline", pool)
        shr = _load("shrink", pool)
        if not base or not shr:
            continue
        kept = {_key(t) for t in shr["trades_detail"]}
        shrink_grp = [t for t in base["trades_detail"] if _key(t) in kept]
        non_shrink = [t for t in base["trades_detail"] if _key(t) not in kept]
        print(f"- **{pool}**")
        print(f"  - 缩量组：{_grp_str(_grp(shrink_grp))}")
        print(f"  - 非缩量组：{_grp_str(_grp(non_shrink))}")
        print()


def top_exclude() -> None:
    print("## 3. 排除 top1 / top3 复核（任务一.2）\n")
    for pool in ("A股ETF", "全池"):
        base = _load("baseline", pool)
        if not base:
            continue
        by_sym: dict[str, list[float]] = {}
        for t in base["trades_detail"]:
            by_sym.setdefault(t["symbol"], []).append(t["r_net"] or 0)
        ranked = sorted(by_sym, key=lambda k: -sum(by_sym[k]))
        top1 = "518850.SS"  # 主理人指定（黄金）
        top3 = ranked[:3]
        print(f"- **{pool}**：top1(指定)={top1}，top3(按基线totalR)={top3}")
        for tag in ("baseline", "shrink", "shrink_vacuum"):
            s = _load(tag, pool)
            if not s:
                continue
            for label, excl in (("全样本", []), ("排top1", [top1]),
                                ("排top3", top3)):
                g = _grp([t for t in s["trades_detail"] if t["symbol"] not in excl])
                sub = _grp_str(g)
                print(f"  - {tag} {label}：{sub}")
        print()


def by_year() -> None:
    print("## 4. 分年份归因（任务一.3，缩量组 vs 非缩量组 expR / N）\n")
    for pool in ("A股ETF", "全池"):
        base = _load("baseline", pool)
        shr = _load("shrink", pool)
        if not base or not shr:
            continue
        kept = {_key(t) for t in shr["trades_detail"]}
        years = sorted({t["signal_date"][:4] for t in base["trades_detail"]})
        print(f"### {pool}\n")
        print("| 年份 | 缩量组 | 非缩量组 |")
        print("|---|---|---|")
        for y in years:
            cells = []
            for want_kept in (True, False):
                grp = [t for t in base["trades_detail"]
                       if (_key(t) in kept) == want_kept
                       and t["signal_date"][:4] == y and t["r_net"] is not None]
                if not grp:
                    cells.append("-")
                    continue
                rs = [t["r_net"] for t in grp]
                cells.append(f"{sum(rs)/len(rs):+.3f} ({len(rs)})")
            print(f"| {y} | {cells[0]} | {cells[1]} |")
        print()


def sensitivity() -> None:
    print("## 5. 敏感性（全池：窗口变体 + 严格档，任务一.5）\n")
    rows = (
        ("baseline", "对照（无过滤）"),
        ("shrink", "shrink 3/3（默认）"),
        ("shrink_5_3", "shrink 5/3"),
        ("shrink_2_5", "shrink 2/5"),
        ("shrink_vr70", "shrink + 量比<0.7"),
        ("shrink_vr60", "shrink + 量比<0.6"),
    )
    print("| 配置 | N | expR | totalR | PF | IS (n) | OOS (n) | 保留率 |")
    print("|---|---:|---:|---:|---:|---|---|---:|")
    base = _load("baseline", "全池")
    base_n = base["overview"]["trade_count"] or 1 if base else 1
    for tag, cn in rows:
        s = _load(tag, "全池")
        if s is None:
            print(f"| {cn} | （未跑）" + " - |" * 7)
            continue
        ov = s["overview"]
        n = ov["trade_count"] or 0
        print(
            f"| {cn} | {n} | {_f(ov['expectancy_r'])} | {_f(ov['total_r'])} "
            f"| {ov['profit_factor'] or 0:.2f} "
            f"| {_f(s['is_expectancy'])} ({s['is_trade_count'] or 0}) "
            f"| {_f(s['oos_expectancy'])} ({s['oos_trade_count'] or 0}) "
            f"| {n / base_n:.0%} |"
        )
    print()


def symtype() -> None:
    print("## 6. 分标的类型（任务一.6）\n")
    print("| 池 | 配置 | N | expR | totalR | PF | IS (n) | OOS (n) |")
    print("|---|---|---:|---:|---:|---:|---|---|")
    for pool in ("宽基ETF", "行业ETF", "指数本体"):
        for tag in ("baseline", "shrink"):
            s = _load(tag, pool)
            if s is None:
                print(f"| {pool} | {tag} | （未跑）" + " - |" * 6)
                continue
            ov = s["overview"]
            print(
                f"| {pool} | {tag} | {ov['trade_count'] or 0} "
                f"| {_f(ov['expectancy_r'])} | {_f(ov['total_r'])} "
                f"| {ov['profit_factor'] or 0:.2f} "
                f"| {_f(s['is_expectancy'])} ({s['is_trade_count'] or 0}) "
                f"| {_f(s['oos_expectancy'])} ({s['oos_trade_count'] or 0}) |"
            )
    print()


def main() -> None:
    overview_tables()
    group_is_oos()
    top_exclude()
    by_year()
    sensitivity()
    symtype()


if __name__ == "__main__":
    main()
