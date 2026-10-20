"""B 全谱参数 × 标的组适配：汇总（handoff-b-adaptation 任务一）。

输入：docs/experiments/raw/b_adaptation/*.json（run_b_spectrum.py 产出）
产出：
  1. 每组 × (variant/exit/vc) 的 cb×cl 热力表（expR/OOS/N），落 raw/；
  2. 组内排名：合格档（N>=30 & OOS>0 & 排 top1 后不塌）按 expR 排序，
     取各组最优档（breakout×b3×vc0 为主轴，其余组合附列）；
  3. 「组×最优档」适配表 + 与「全池一套参数」（native 126/2、全池最优单档）
     的增量 R 对比；
  4. 适配判定：各组最优 cb/cl 是否分散在谱上（挤在同一档=适配不成立）；
  5. b_adaptation_summary.json 落盘。

防过拟合红线：排名按组、绝不按单标的；N<30 标「样本不足」不参与排名；
ex_top1 不塌定义为 ex_top1_expR >= expR - 0.3R（与 bcd-retrial 稀疏判据同口径）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "b_adaptation"

CB_LEVELS = (20, 30, 40, 63, 90, 126, 180)
CL_LEVELS = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10)
GROUPS = ("宽基ETF", "行业ETF", "A股指数", "个股", "美股ETF", "全池")
# tag 形如 B_bre_cb40_cl05_b3_vc0 / B_amb_cb40_cl05_b3_vc0 / ALL_bre_...
_COMBO_LABEL = {
    ("bre", "b3", "vc0"): "突破·b3双退·无量确",
    ("bre", "b3", "vc1"): "突破·b3双退·放量确",
    ("bre", "ss", "vc0"): "突破·a6③结构止损·无量确",
    ("bre", "ss", "vc1"): "突破·a6③结构止损·放量确",
    ("amb", "b3", "vc0"): "埋伏·b3双退·无量确",
}


def _parse_tag(tag: str) -> tuple[str, int, float, str, str, str]:
    """B_bre_cb40_cl05_b3_vc0 -> (bre,40,0.05,b3,vc0)."""
    parts = tag.split("_")
    # B_bre_cb40_cl05_b3_vc0 与 ALL_bre_cb40_cl05_b3_vc0 均带一个前缀 token
    p = parts[1:]
    variant = p[0]
    cb = int(p[1][2:])
    cl = int(p[2][2:]) / 100.0
    exit_v = p[3]
    vc = p[4]
    return variant, cb, cl, exit_v, vc, tag


def _load() -> dict[str, dict]:
    """{(group, combo_key, cb, cl): run_dict}."""
    out: dict[tuple, dict] = {}
    for fp in sorted(RAW.glob("*.json")):
        stem = fp.stem
        if "__" not in stem:
            continue
        tag, group = stem.rsplit("__", 1)
        d = json.loads(fp.read_text(encoding="utf-8"))
        variant, cb, cl, exit_v, vc, _ = _parse_tag(tag)
        out[(group, variant, exit_v, vc, cb, cl)] = d
    return out


def _ex_top1(run: dict) -> float | None:
    """排除 top1 标的全部交易后期望 R。"""
    trades = run.get("trades_detail", [])
    closed = [t for t in trades if t.get("r_net") is not None]
    if not closed:
        return None
    by_sym: dict[str, float] = {}
    for t in closed:
        by_sym[t["symbol"]] = by_sym.get(t["symbol"], 0.0) + t["r_net"]
    if not by_sym:
        return None
    top1 = max(by_sym.items(), key=lambda kv: kv[1])[0]
    rest = [t["r_net"] for t in closed if t["symbol"] != top1]
    return sum(rest) / len(rest) if rest else None


def _f(x: float | None, width: int = 6) -> str:
    if x is None:
        return "  -  ".rjust(width)
    return f"{x:+.2f}".rjust(width)


def _heatmap(
    runs: dict, group: str, variant: str, exit_v: str, vc: str, metric: str
) -> list[str]:
    """单张 cb(行)×cl(列) 热力表。metric: expR/oos/N。"""
    lines = [f"### {group} · {_COMBO_LABEL.get((variant, exit_v, vc), (variant, exit_v, vc))} · {metric}"]
    header = "| cb\\cl | " + " | ".join(f"{c*100:.0f}%" for c in CL_LEVELS) + " |"
    lines.append(header)
    lines.append("|---" * (len(CL_LEVELS) + 1) + "|")
    for cb in CB_LEVELS:
        cells = []
        for cl in CL_LEVELS:
            d = runs.get((group, variant, exit_v, vc, cb, cl))
            if d is None:
                cells.append("-")
                continue
            ov = d["overview"]
            n = ov["trade_count"] or 0
            if metric == "N":
                cells.append(str(n))
            elif metric == "expR":
                cells.append(_f(ov["expectancy_r"]))
            else:
                cells.append(_f(d.get("oos_expectancy")))
        lines.append(f"| {cb} | " + " | ".join(cells) + " |")
    return lines


def _eligible(runs: dict, group: str, combo: tuple[str, str, str]) -> list[dict]:
    """组内合格档：N>=30 & OOS>0 & 排top1后不塌（>=expR-0.3）。"""
    variant, exit_v, vc = combo
    rows = []
    for cb in CB_LEVELS:
        for cl in CL_LEVELS:
            d = runs.get((group, variant, exit_v, vc, cb, cl))
            if d is None:
                continue
            ov = d["overview"]
            n = ov["trade_count"] or 0
            exp = ov["expectancy_r"]
            oos = d.get("oos_expectancy")
            ex1 = _ex_top1(d)
            if n < 30:
                continue
            if oos is None or oos <= 0:
                continue
            if ex1 is None or ex1 < (exp or 0) - 0.3:
                continue
            rows.append({
                "cb": cb, "cl": cl, "N": n, "expR": exp, "IS": d.get("is_expectancy"),
                "OOS": oos, "ex_top1": ex1, "top1": d.get("top1_symbol"),
            })
    rows.sort(key=lambda r: -(r["expR"] or -99))
    return rows


def main() -> None:
    runs = _load()
    groups_present = sorted({k[0] for k in runs})
    print(f"loaded {len(runs)} runs across groups: {groups_present}")

    heat_lines: list[str] = ["# B 全谱参数热力表（cb 行 × cl 列）", ""]
    summary: dict[str, dict] = {}

    # ---- 主轴 breakout × b3 × vc0：每组出热力表 + 排名 ----
    primary = ("bre", "b3", "vc0")
    print("\n## 组内合格档排名（主轴：突破·b3双退·无量确；N≥30 & OOS>0 & 排top1不塌）")
    print("| 组 | 最优 cb | cl | N | expR | IS | OOS | 排top1 | top1 | 合格档数 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|")
    for group in GROUPS:
        if group not in groups_present:
            continue
        for metric in ("expR", "OOS", "N"):
            heat_lines.extend(_heatmap(runs, group, *primary, metric=metric))
            heat_lines.append("")
        elig = _eligible(runs, group, primary)
        summary[group] = {
            "primary_eligible": elig,
            "primary_best": elig[0] if elig else None,
        }
        if elig:
            b = elig[0]
            print(
                f"| {group} | {b['cb']} | {b['cl']*100:.0f}% | {b['N']} "
                f"| {b['expR']:+.3f} | {_f(b['IS'])} | {b['OOS']:+.3f} "
                f"| {b['ex_top1']:+.3f} | {b['top1']} | {len(elig)} |"
            )
        else:
            print(f"| {group} | - | - | - | 无合格档 | - | - | - | - | 0 |")

    # ---- 其他组合：每组只报最优（是否有比主轴更好的退出/量能）----
    print("\n## 其他组合的组内最优（对照主轴；仅列合格档最优）")
    print("| 组 | 组合 | cb | cl | N | expR | OOS | 排top1 |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for group in GROUPS:
        if group not in groups_present:
            continue
        summary[group]["other_combos"] = {}
        for combo in (("bre", "b3", "vc1"), ("bre", "ss", "vc0"),
                      ("bre", "ss", "vc1"), ("amb", "b3", "vc0")):
            if not any(k[:3] == (group, combo[0], combo[1]) and k[3] == combo[2]
                       for k in runs):
                continue
            elig = _eligible(runs, group, combo)
            best = elig[0] if elig else None
            summary[group]["other_combos"]["_".join(combo)] = best
            label = _COMBO_LABEL.get(combo, "/".join(combo))
            if best:
                print(
                    f"| {group} | {label} | {best['cb']} | {best['cl']*100:.0f}% "
                    f"| {best['N']} | {best['expR']:+.3f} | {best['OOS']:+.3f} "
                    f"| {best['ex_top1']:+.3f} |"
                )
            else:
                print(f"| {group} | {label} | - | - | - | 无合格档 | - | - |")
        # 热力表（主轴之外的 expR 也落 raw，便于复核；其余组合 N/OOS 从略以控篇幅）
        for combo in (("bre", "b3", "vc1"), ("bre", "ss", "vc0"), ("amb", "b3", "vc0")):
            if any(k[:3] == (group, combo[0], combo[1]) and k[3] == combo[2]
                   for k in runs):
                heat_lines.extend(_heatmap(runs, group, *combo, metric="expR"))
                heat_lines.append("")

    # ---- 适配增量：组最优 vs「全池一套参数」----
    print("\n## 适配增量（组最优档 vs 全池同档 vs native 126/2）")
    print("| 组 | 组最优 cb/cl | 组内 expR | 同档在全池 expR | native 126/2 组内 expR | 适配增量 |")
    print("|---|---|---:|---:|---:|---:|")
    for group in GROUPS:
        if group == "全池" or group not in summary:
            continue
        b = summary[group].get("primary_best")
        if not b:
            print(f"| {group} | 无合格档 | - | - | - | - |")
            continue
        same = runs.get(("全池", "bre", "b3", "vc0", b["cb"], b["cl"]))
        native = runs.get((group, "bre", "b3", "vc0", 126, 0.02))
        same_exp = same["overview"]["expectancy_r"] if same else None
        nat_exp = native["overview"]["expectancy_r"] if native else None
        delta = (
            b["expR"] - nat_exp if nat_exp is not None else None
        )
        summary[group]["adaptation_delta_vs_native"] = delta
        print(
            f"| {group} | {b['cb']}/{b['cl']*100:.0f}% | {b['expR']:+.3f} "
            f"| {_f(same_exp)} | {_f(nat_exp)} | {_f(delta)} |"
        )

    # ---- 适配判定：各组最优 cb/cl 分布 ----
    print("\n## 适配判定（主轴最优档在 cb×cl 谱上的分布）")
    optima = {
        g: (s["primary_best"]["cb"], s["primary_best"]["cl"])
        for g, s in summary.items()
        if g != "全池" and s.get("primary_best")
    }
    print("| 组 | 最优 cb | 最优 cl |")
    print("|---|---:|---:|")
    for g, (cb, cl) in optima.items():
        print(f"| {g} | {cb} | {cl*100:.0f}% |")
    cbs = {cb for cb, _ in optima.values()}
    cls = {cl for _, cl in optima.values()}
    verdict = (
        f"最优 cb 横跨 {sorted(cbs)}（{len(cbs)} 档）、cl 横跨 "
        f"{sorted(f'{c*100:.0f}%' for c in cls)}（{len(cls)} 档）。"
    )
    if len(cbs) >= 3 or len(cls) >= 3:
        verdict += " 各组最优分散在谱上不同位置 -> **适配成立**（不同标的类型需要不同密集区口径）。"
    elif len(cbs) == 1 and len(cls) == 1:
        verdict += " 各组最优挤在同一档 -> **适配不成立**（全池一套参数即可）。"
    else:
        verdict += " 各组最优部分聚集 -> 适配证据弱，需结合增量 R 判定。"
    print("\n" + verdict)
    summary["_verdict"] = verdict
    summary["_optima"] = {g: {"cb": cb, "cl": cl} for g, (cb, cl) in optima.items()}

    # ---- 落盘 ----
    (RAW / "b_adaptation_heatmaps.md").write_text(
        "\n".join(heat_lines), encoding="utf-8"
    )
    (RAW / "b_adaptation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[-> {RAW.name}/b_adaptation_heatmaps.md, b_adaptation_summary.json]")


if __name__ == "__main__":
    main()
