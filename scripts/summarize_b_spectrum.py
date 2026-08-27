"""B 全谱扫描汇总（handoff-b-adaptation 任务一）。

读 raw/b_adaptation/*.json，产出：
  1. 每组 × 主轴(breakout×b3×vc0) 的 cb×cl 热力表（expR / OOS / N）；
  2. 组内最优档（OOS>0、排 top1 后不塌、N>=30；不足 30 标「样本不足」不排名）；
  3. 「组×最优档」适配表 + 与全池一套参数（全池最优单档 / 默认 126/2）的增量 R；
  4. 适配是否成立的判定（各组最优档是否分散在不同 cb/cl 档）。
另外把其他轴（vc1 / a6_3 / ambush）的最优档作为附表。

落盘：raw/b_adaptation/b_spectrum_summary.json + 控制台 Markdown 表。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "b_adaptation"

CB_LEVELS = (20, 30, 40, 63, 90, 126, 180)
CL_LEVELS = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10)
GROUPS = ("宽基ETF", "行业ETF", "A股指数", "个股", "美股ETF", "全池")


def _f(x: float | None, w: int = 6) -> str:
    if x is None:
        return "  -  ".rjust(w)
    return f"{x:+.2f}".rjust(w)


def _ex_top1(trades: list[dict]) -> float | None:
    """排除 total_r 最高的单个标的后的期望 R。"""
    by_sym: dict[str, float] = {}
    for t in trades:
        if t.get("r_net") is not None:
            by_sym[t["symbol"]] = by_sym.get(t["symbol"], 0.0) + t["r_net"]
    if not by_sym:
        return None
    top = max(by_sym, key=by_sym.get)
    rest = [t["r_net"] for t in trades if t.get("r_net") is not None and t["symbol"] != top]
    return sum(rest) / len(rest) if rest else None


def load_runs() -> dict[tuple[str, str], dict]:
    """{(group, tag): summary}。"""
    out: dict[tuple[str, str], dict] = {}
    for fp in RAW.glob("*.json"):
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        name = fp.stem
        # 文件名形如 B_bre_cb40_cl03_b3_vc0__宽基ETF
        if "__" not in name:
            continue
        tag, group = name.rsplit("__", 1)
        d["_ex_top1"] = _ex_top1(d.get("trades_detail", []))
        out[(group, tag)] = d
    return out


def parse_tag(tag: str) -> tuple[str, int, float, str, bool]:
    """B_bre_cb40_cl03_b3_vc0 -> (variant, cb, cl, exit, vc)."""
    parts = tag.split("_")
    variant = {"bre": "breakout", "amb": "ambush"}.get(parts[1], parts[1])
    cb = int(parts[2][2:])
    cl = int(parts[3][2:]) / 100.0
    exit_v = {"b3": "b3_dual", "ss": "a6_3_structure_stop"}.get(parts[4], parts[4])
    vc = parts[5] == "vc1"
    return variant, cb, cl, exit_v, bool(vc)


def _group_axis(group: str, axis_tag: str) -> str:
    """全池基线文件名前缀为 ALL_，其余组为 B_。"""
    if group == "全池":
        return axis_tag.replace("B_", "ALL_", 1)
    return axis_tag


def heatmap(runs: dict, group: str, axis_tag: str) -> str:
    """axis_tag 形如 'B_bre_{cb}_cl{cl}_b3_vc0'（cb/cl 用占位符）。"""
    lines = []
    header = "cb \\ cl   " + "".join(f"{cl*100:>7.0f}%" for cl in CL_LEVELS)
    lines.append(header)
    gaxis = _group_axis(group, axis_tag)
    for cb in CB_LEVELS:
        cells = []
        for cl in CL_LEVELS:
            tag = gaxis.format(cb=cb, cl=f"{round(cl * 100):02d}")
            d = runs.get((group, tag))
            if d is None:
                cells.append("   .  ")
                continue
            ov = d["overview"]
            n = ov["trade_count"] or 0
            exp = ov["expectancy_r"]
            cells.append(f"{exp * 100 if exp is not None else 0:>6.1f}" if n else "   0  ")
        lines.append(f"{cb:>6}  " + "".join(f"{c:>7}" for c in cells))
    lines.append("（格内 = expR×100；0 = 无成交；. = 未跑）")
    return "\n".join(lines)


def best_per_group(
    runs: dict, groups: tuple[str, ...], axis_tag: str
) -> dict[str, dict]:
    """每组在该轴上的最优档（满足判据的里面 expR 最高）。"""
    result: dict[str, dict] = {}
    for group in groups:
        gaxis = _group_axis(group, axis_tag)
        candidates = []
        for cb in CB_LEVELS:
            for cl in CL_LEVELS:
                tag = gaxis.format(cb=cb, cl=f"{round(cl * 100):02d}")
                d = runs.get((group, tag))
                if d is None:
                    continue
                ov = d["overview"]
                n = ov["trade_count"] or 0
                exp = ov["expectancy_r"]
                oos = d.get("oos_expectancy")
                ex1 = d.get("_ex_top1")
                qualifies = (
                    n >= 30
                    and exp is not None and exp > 0
                    and oos is not None and oos > 0
                    and ex1 is not None and ex1 > 0
                )
                candidates.append(
                    {
                        "cb": cb, "cl": cl, "N": n, "expR": exp, "OOS": oos,
                        "ex_top1": ex1, "IS": d.get("is_expectancy"),
                        "top1": d.get("top1_symbol"), "qualifies": qualifies,
                    }
                )
        if not candidates:
            result[group] = {"cb": None, "cl": None, "N": 0, "expR": None,
                             "OOS": None, "ex_top1": None, "IS": None,
                             "top1": None, "qualifies": False, "status": "未跑"}
            continue
        qual = [c for c in candidates if c["qualifies"]]
        if qual:
            best = max(qual, key=lambda c: c["expR"])
            best["status"] = "PASS"
        else:
            has_n = [c for c in candidates if c["N"] >= 30]
            best = max(
                has_n or candidates,
                key=lambda c: c["expR"] if c["expR"] is not None else -99,
            )
            best["status"] = "样本不足" if not has_n else "无达标档"
        result[group] = best
    return result


def main() -> None:
    runs = load_runs()
    print(f"载入 {len(runs)} 个 run 文件\n")

    # ---- 主轴热力表：breakout × b3_dual × vc0 ----
    axis = "B_bre_cb{cb}_cl{cl}_b3_vc0"
    for group in GROUPS:
        print(f"\n### 热力表 · {group} · breakout/b3/vc0（expR×100）")
        print("```")
        print(heatmap(runs, group, axis))
        print("```")

    # OOS / N 热力表（主轴）
    for group in GROUPS:
        gaxis = _group_axis(group, axis)
        print(f"\n### OOS 热力 · {group}（OOS×100，样本外两年）")
        print("```")
        header = "cb \\ cl   " + "".join(f"{cl*100:>7.0f}%" for cl in CL_LEVELS)
        print(header)
        for cb in CB_LEVELS:
            cells = []
            for cl in CL_LEVELS:
                tag = gaxis.format(cb=cb, cl=f"{round(cl * 100):02d}")
                d = runs.get((group, tag))
                if d is None:
                    cells.append("   .  ")
                    continue
                oos = d.get("oos_expectancy")
                n = d["overview"]["trade_count"] or 0
                cells.append(
                    f"{oos * 100:>6.1f}" if oos is not None and n
                    else "   0  "
                )
            print(f"{cb:>6}  " + "".join(f"{c:>7}" for c in cells))
        print("```")

    # ---- 组×最优档适配表（主轴） ----
    best = best_per_group(runs, GROUPS, axis)
    print("\n## 组×最优档适配表（breakout × b3_dual × 无放量确认）")
    print("| 组 | 最优 cb | 最优 cl | N | expR | IS | OOS | 排top1后 | top1 | 状态 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for group, b in best.items():
        cl_str = f"{b['cl']:.0%}" if b["cl"] is not None else "-"
        cb_str = b["cb"] if b["cb"] is not None else "-"
        print(
            f"| {group} | {cb_str} | {cl_str} | {b['N']} | "
            f"{_f(b['expR'])} | {_f(b['IS'])} | {_f(b['OOS'])} | "
            f"{_f(b['ex_top1'])} | {b['top1'] or '-'} | {b['status']} |"
        )

    # ---- 与「全池一套参数」的增量 ----
    all_best = best.get("全池", {})
    all_cb, all_cl = all_best.get("cb"), all_best.get("cl")
    all_exp_pool = all_best.get("expR")

    def _grp_cell(group: str, cb: int, cl: float) -> tuple[int, float | None]:
        gaxis = _group_axis(group, axis)
        d = runs.get((group, gaxis.format(cb=cb, cl=f"{round(cl * 100):02d}")))
        if d is None:
            return 0, None
        return (d["overview"]["trade_count"] or 0), d["overview"]["expectancy_r"]

    if all_cb is not None and all_cl is not None:
        print(
            f"\n全池（5 组并集）单档最优 = cb{all_cb}/cl{all_cl:.0%}，"
            f"全池 expR {_f(all_exp_pool)}（N={all_best['N']}，top1={all_best['top1']}）。"
        )
        print("**注意：该档在每个组内 N 均<30，全池 N 靠单标的拼凑，是过拟合档，不可直接部署。**")
        print("| 组 | 全池最优档在该组 N | 该组 expR | 组内最优档 expR | 差值 |")
        print("|---|---:|---:|---:|---:|")
        for group in GROUPS:
            if group == "全池":
                continue
            n_all, all_exp = _grp_cell(group, all_cb, all_cl)
            grp_exp = best[group]["expR"]
            delta = (grp_exp - all_exp) if (grp_exp is not None and all_exp is not None) else None
            flag = " ⚠️N<30" if n_all < 30 else ""
            print(
                f"| {group} | {n_all}{flag} | {_f(all_exp)} | {_f(grp_exp)} | "
                f"{_f(delta) if delta is not None else '  -  '} |"
            )

    # 与账本默认档 cb126/cl2 的对比（这才是适配的真实基线）
    DEF_CB, DEF_CL = 126, 0.02
    print(
        f"\n账本默认档 cb{DEF_CB}/cl{DEF_CL:.0%} 在各组的表现（适配前基线）："
    )
    print("| 组 | 默认档 N | 默认档 expR | 组内最优档 | 最优 expR | 适配增量 |")
    print("|---|---:|---:|---|---:|---:|")
    deltas = []
    for group in GROUPS:
        if group == "全池":
            continue
        n_def, def_exp = _grp_cell(group, DEF_CB, DEF_CL)
        b = best[group]
        grp_exp = b["expR"]
        both = grp_exp is not None and def_exp is not None
        delta = grp_exp - def_exp if both else (grp_exp or 0)
        deltas.append(delta)
        def_str = _f(def_exp) if def_exp is not None else "无信号"
        tier = f"cb{b['cb']}/cl{b['cl']:.0%}" if b["cb"] is not None else "-"
        print(
            f"| {group} | {n_def} | {def_str} | {tier} | {_f(grp_exp)} | {_f(delta)} |"
        )
    if deltas:
        print(
            f"\n五组等权平均适配增量 = {sum(deltas)/len(deltas):+.2f}R"
            f"（组内稳健最优 vs 账本默认 cb126/cl2）。"
        )

    # ---- 其他轴的最优档（附表） ----
    print("\n## 其他退出/量能/变体的组内最优（附表）")
    other_axes = {
        "breakout × b3 × 放量确认": "B_bre_cb{cb}_cl{cl}_b3_vc1",
        "breakout × a6_3 × 无确认": "B_bre_cb{cb}_cl{cl}_ss_vc0",
        "breakout × a6_3 × 放量确认": "B_bre_cb{cb}_cl{cl}_ss_vc1",
        "ambush × b3 × 无确认": "B_amb_cb{cb}_cl{cl}_b3_vc0",
    }
    for label, atag in other_axes.items():
        ob = best_per_group(runs, tuple(g for g in GROUPS if g != "全池"), atag)
        print(f"\n### {label}")
        print("| 组 | cb | cl | N | expR | OOS | 排top1 | 状态 |")
        print("|---|---:|---:|---:|---:|---:|---:|---|")
        for group, b in ob.items():
            cl_str = f"{b['cl']:.0%}" if b["cl"] is not None else "-"
            cb_str = b["cb"] if b["cb"] is not None else "-"
            print(
                f"| {group} | {cb_str} | {cl_str} | {b['N']} | "
                f"{_f(b['expR'])} | {_f(b['OOS'])} | {_f(b['ex_top1'])} | {b['status']} |"
            )

    # ---- 适配是否成立：各组最优 cb/cl 的离散程度 ----
    print("\n## 适配是否成立")
    pass_groups = [g for g, b in best.items() if g != "全池" and b["status"] == "PASS"]
    opt_cb = [best[g]["cb"] for g in pass_groups]
    opt_cl = [best[g]["cl"] for g in pass_groups]
    if pass_groups:
        print(
            f"过判据的组：{', '.join(pass_groups)}；"
            f"最优 cb = {opt_cb}（极差 {max(opt_cb) - min(opt_cb)} 根），"
            f"最优 cl = {[f'{c:.0%}' for c in opt_cl]}（极差 {(max(opt_cl) - min(opt_cl)):.0%}）。"
        )
        if max(opt_cb) - min(opt_cb) >= 30 or max(opt_cl) - min(opt_cl) >= 0.02:
            print("→ 各组最优档分散：适配成立（不同标的的最优密集区口径不同）。")
        else:
            print("→ 各组最优档挤在同一档：适配不成立，全池一套参数即可。")
    else:
        print("→ 主轴无任何组过判据（OOS>0 且排top1不塌 且 N≥30）：B 在全谱上仍无系统优势，")
        print("  「参数适配标的」的前提不成立，维持 B 原判。")

    # 落盘 JSON
    summary = {
        "axis": axis,
        "best": {g: {k: (float(v) if isinstance(v, float) else v) for k, v in b.items()}
                 for g, b in best.items()},
        "all_pool_best_cb": all_cb,
        "all_pool_best_cl": all_cl,
        "pass_groups": pass_groups,
        "runs_count": len(runs),
    }
    out_fp = RAW / "b_spectrum_summary.json"
    out_fp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[-> {out_fp.relative_to(ROOT)}]")


if __name__ == "__main__":
    main()
