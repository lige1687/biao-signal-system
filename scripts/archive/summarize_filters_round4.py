"""第四轮过滤器实验汇总：从 raw/filters_round4/*.json 生成报告表格数据。

输出（stdout，markdown 表格）：
  1. 增量总表（每池：baseline vs 各过滤器）
  2. E1 分年份归因
  3. E2 被过滤交易的画像（胜率/盈亏/年份/均线组/stage）
  4. E3 stage 期望曲线 + 周线引力折扣
  5. E4b RR 通过率漏斗 + 缺口救回交易质量
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "filters_round4"

POOLS = ("A股ETF", "全池")
TAGS = [
    "baseline", "vol1", "vol5",
    "prof_poc_support", "prof_vacuum", "prof_both",
    "gapmom", "rr3", "rr3_gap",
]
TAG_CN = {
    "baseline": "对照（全关）",
    "vol1": "量能·窗口1",
    "vol5": "量能·窗口5",
    "prof_poc_support": "筹码·踩峰",
    "prof_vacuum": "筹码·真空",
    "prof_both": "筹码·双条件",
    "gapmom": "缺口动能",
    "rr3": "RR3（缺口档关）",
    "rr3_gap": "RR3（缺口档开）",
}


def _load(tag: str, pool: str) -> dict | None:
    fp = RAW / f"{tag}__{pool}.json"
    if not fp.exists():
        return None
    return json.loads(fp.read_text(encoding="utf-8"))


def _f(v: float | None, digits: int = 3, sign: bool = True) -> str:
    if v is None:
        return "-"
    return f"{v:+.{digits}f}" if sign else f"{v:.{digits}f}"


def _row(tag: str, s: dict, base: dict | None) -> str:
    ov = s["overview"]
    is_n = s["is_trade_count"] or 0
    oos_n = s["oos_trade_count"] or 0
    d = ""
    if base is not None:
        b = base["overview"]
        dn = (ov["trade_count"] or 0) - (b["trade_count"] or 0)
        de = (ov["expectancy_r"] or 0) - (b["expectancy_r"] or 0)
        dt = (ov["total_r"] or 0) - (b["total_r"] or 0)
        d = f"| {dn:+d} 笔 | {_f(de)} | {dt:+.1f}R |"
    else:
        d = "| - | - | - |"
    return (
        f"| {TAG_CN[tag]} | {ov['trade_count'] or 0} | {_f(ov['expectancy_r'])} "
        f"| {_f(ov['total_r'], 1)} | {ov['profit_factor'] or 0:.2f} "
        f"| {_f(s['is_expectancy'])} ({is_n}) | {_f(s['oos_expectancy'])} ({oos_n}) "
        f"| {s['top1_symbol'] or '-'} {d}"
    )


def overview_tables() -> None:
    for pool in POOLS:
        runs = {t: _load(t, pool) for t in TAGS}
        base = runs["baseline"]
        if base is None:
            print(f"\n### {pool}：baseline 缺失，跳过\n")
            continue
        print(f"\n### {pool}\n")
        print("| 配置 | N | expR | totalR | PF | IS (n) | OOS (n) | top1 | ΔN | ΔexpR | ΔtotalR |")
        print("|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|")
        for tag in TAGS:
            s = runs[tag]
            if s is None:
                print(f"| {TAG_CN[tag]} | （未跑） |" + " - |" * 10)
                continue
            print(_row(tag, s, base if tag != "baseline" else None))


def e1_by_year() -> None:
    print("\n## E1 量能：分年份归因（expR / N）\n")
    for pool in POOLS:
        runs = {t: _load(t, pool) for t in ("baseline", "vol1", "vol5")}
        if runs["baseline"] is None:
            continue
        years = sorted(runs["baseline"]["by_year"])
        print(f"\n**{pool}**\n")
        print("| 年份 | " + " | ".join(TAG_CN[t] for t in ("baseline", "vol1", "vol5")) + " |")
        print("|---|" + "---:|" * 3)
        for y in years:
            cells = []
            for t in ("baseline", "vol1", "vol5"):
                s = runs[t]
                c = s["by_year"].get(y) if s else None
                cells.append("-" if not c else f"{_f(c['expectancy_r'])} ({c['trade_count']})")
            print(f"| {y} | " + " | ".join(cells) + " |")


def _key(t: dict) -> tuple[str, str]:
    return (t["symbol"], t["signal_date"])


def e2_dropped_profile() -> None:
    print("\n## E2 筹码：被过滤交易的画像\n")
    for pool in POOLS:
        base = _load("baseline", pool)
        if base is None:
            continue
        for mode in ("poc_support", "vacuum", "both"):
            s = _load(f"prof_{mode}", pool)
            if s is None:
                continue
            kept = {_key(t) for t in s["trades_detail"]}
            # 按原始明细迭代（同 symbol+signal_date 可有多均线信号，去重会漏计）
            dropped = [t for t in base["trades_detail"] if _key(t) not in kept]
            if not dropped:
                print(f"\n**{pool} / {mode}**：无被过滤交易")
                continue
            n = len(dropped)
            rs = [t["r_net"] for t in dropped if t["r_net"] is not None]
            wins = sum(1 for r in rs if r > 0)
            sum_r = sum(rs)
            by_ma: dict[int, list[float]] = {}
            by_stage: dict[int, list[float]] = {}
            by_year: dict[str, list[float]] = {}
            for t in dropped:
                r = t["r_net"]
                if r is None:
                    continue
                by_ma.setdefault(t["ma_period"], []).append(r)
                by_stage.setdefault(t["trend_stage"], []).append(r)
                by_year.setdefault(t["signal_date"][:4], []).append(r)
            ma_s = "、".join(
                f"SMA{k} {len(v)}笔{sum(v):+.1f}R"
                for k, v in sorted(by_ma.items())
            )
            st_s = "、".join(
                f"stage{k} {len(v)}笔{sum(v):+.1f}R"
                for k, v in sorted(by_stage.items())
            )
            yr_s = "、".join(
                f"{y} {len(v)}笔{sum(v):+.1f}R" for y, v in sorted(by_year.items())
            )
            print(
                f"\n**{pool} / {mode}**：过滤 {n} 笔"
                f"（胜率 {wins}/{n}={wins / n:.0%}，合计 {sum_r:+.1f}R，"
                f"均值 {sum_r / n:+.3f}R）\n- 按均线组：{ma_s}\n"
                f"- 按 stage：{st_s}\n- 按年份：{yr_s}"
            )


def e3_stage_curve() -> None:
    print("\n## E3 五步状态机：stage 期望曲线 + 周线引力（baseline）\n")
    for pool in POOLS:
        base = _load("baseline", pool)
        if base is None:
            continue
        st = base["trend_stage_groups"]
        print(f"\n**{pool}**\n")
        print("| stage | N | expR | totalR | PF |")
        print("|---|---:|---:|---:|---:|")
        for k in sorted(st):
            v = st[k]
            print(
                f"| {k} | {v['trade_count']} | {_f(v['expectancy_r'])} "
                f"| {_f(v['total_r'], 1)} | {v['profit_factor'] or 0:.2f} |"
            )
        wk = base["weekly_env_groups"]
        print("\n| 周线环境 | N | expR | totalR | PF |")
        print("|---|---:|---:|---:|---:|")
        for k in sorted(wk):
            v = wk[k]
            print(
                f"| {k} | {v['trade_count']} | {_f(v['expectancy_r'])} "
                f"| {_f(v['total_r'], 1)} | {v['profit_factor'] or 0:.2f} |"
            )


def e4b_funnel() -> None:
    print("\n## E4b 缺口目标档：RR 通过率漏斗 + 救回质量\n")
    for pool in POOLS:
        a = _load("rr3", pool)
        b = _load("rr3_gap", pool)
        if not a or not b:
            continue
        print(f"\n**{pool}**\n")
        print("| 配置 | touched | confirmed | no_target | filtered_by_rr | 入场 N |")
        print("|---|---:|---:|---:|---:|---:|")
        for name, s in (("RR3 缺口档关", a), ("RR3 缺口档开", b)):
            f_ = s["funnel"]
            print(
                f"| {name} | {f_['touched']} | {f_['confirmed']} "
                f"| {f_['no_target']} | {f_['filtered_by_rr']} "
                f"| {s['overview']['trade_count'] or 0} |"
            )
        for name, s in (("RR3 缺口档关", a), ("RR3 缺口档开", b)):
            ov = s["overview"]
            print(
                f"- {name}：expR {_f(ov['expectancy_r'])}、totalR {_f(ov['total_r'], 1)}、"
                f"PF {ov['profit_factor'] or 0:.2f}、"
                f"IS {_f(s['is_expectancy'])}、OOS {_f(s['oos_expectancy'])}"
            )
        a_map = {_key(t): t for t in a["trades_detail"]}
        rescued = [t for t in b["trades_detail"] if _key(t) not in a_map]
        if rescued:
            rs = [t["r_net"] for t in rescued if t["r_net"] is not None]
            wins = sum(1 for r in rs if r > 0)
            print(
                f"- 救回 {len(rescued)} 笔：胜率 {wins}/{len(rescued)}、"
                f"合计 {sum(rs):+.1f}R、均值 {sum(rs) / len(rescued):+.3f}R"
            )
            by_sym: dict[str, list[float]] = {}
            for t in rescued:
                by_sym.setdefault(t["symbol"], []).append(t["r_net"] or 0)
            top = sorted(by_sym.items(), key=lambda kv: -sum(kv[1]))[:5]
            top5 = "、".join(f"{k} {len(v)}笔{sum(v):+.1f}R" for k, v in top)
            print(f"  - 按标的（前5）：{top5}")


def main() -> None:
    overview_tables()
    e1_by_year()
    e2_dropped_profile()
    e3_stage_curve()
    e4b_funnel()


if __name__ == "__main__":
    main()
