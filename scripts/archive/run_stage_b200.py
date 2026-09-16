#!/usr/bin/env python3
"""stage 路由组合实验（任务一/二，docs/handoff-stage-b200-prompt.md，2026-08-27）。

任务一：A 稳健档（ETF 池，cm0.5+shrink）2026 失血逐笔归因 + 候选止血过滤器交换比。
任务二：双层路由（基准态×trend_stage）vs 对照组；附带 518880/510300 多模块买卖点 CSV。

判定标准（事前写死）：
  任务二「路由有效」= 累计R >= 1.15×最好对照 且 分年不塌（每个有信号年份，
    路由组当年累计R >= 三对照组同年最小值 - 2.0R）且 2026 段失血减半
    （路由组 2026 累计R >= 0.5 × 只做A 的 2026 累计R，两者均为负数）。
  任务一过滤器「可用」（机械标签）= 2026 止血量 >= 0.5×|2026总亏| 且
    被剔除的历史段（非2026）累计R >= 0（不误伤正贡献）且 保留段历史 N >= 100。

纪律：不改 configs/ src/ web/；基准标的 000300.SS 入池、自身交易剔除；
trend_stage 口径 = 账本 trend_stage v2.0.0（0..5，累进合取）。
产出：docs/experiments/raw/stage_b200/*.json + *.csv
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW = REPO / "docs/experiments/raw/stage_b200"
RAW.mkdir(parents=True, exist_ok=True)

BENCHMARK = "000300.SS"
BROAD_CODES = {"510300", "510500", "512100", "510050", "159915",
               "159901", "588000", "515300", "159652"}
CLOCK_CN = {1: "牛", 2: "牛", 3: "横", 4: "熊", 5: "熊"}


def build_pools():
    frames = load_pool_frames()
    available = set(frames)
    stocks = []
    pool_txt = REPO / "docs/experiments/raw/bcd_retrial/stock_pool.txt"
    for line in pool_txt.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.split()[0] in available:
            stocks.append(line.split()[0])
    etf_all = sorted(
        s for s in available
        if s.split(".")[0].startswith(("51", "56", "58", "159"))
        and not s.split(".")[0].startswith("513")
    )
    return stocks, etf_all


def run_and_save(name: str, params: BacktestParams) -> dict:
    t0 = time.time()
    r = execute_run(params)
    n_bench = sum(1 for t in r["trades"] if t["symbol"] == BENCHMARK)
    r["trades"] = [t for t in r["trades"] if t["symbol"] != BENCHMARK]
    r["wall_seconds"] = round(time.time() - t0, 1)
    r["benchmark_own_trades_dropped"] = n_bench
    (RAW / f"{name}.json").write_text(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[run] {name}: N={len(r['trades'])} (剔基准自身 {n_bench} 笔)"
          f" {r['wall_seconds']}s oos_start={r['data_range']['out_of_sample_start']}")
    return r


def closed(ts):
    return [t for t in ts if t["exit_date"] is not None]


def exp_r(ts):
    return None if not ts else sum(t["r_net"] for t in ts) / len(ts)


def exp4(ts):
    v = exp_r(ts)
    return None if v is None else round(v, 4)


def cum_r(ts):
    return sum(t["r_net"] for t in ts)


def yearly(ts):
    agg = defaultdict(list)
    for t in ts:
        agg[int(t["entry_date"][:4])].append(t)
    return {str(y): {"N": len(v), "cumR": round(cum_r(v), 3), "expR": exp4(v)}
            for y, v in sorted(agg.items())}


def max_dd(ts):
    seq = sorted(closed(ts), key=lambda t: t["exit_date"])
    peak = cum = mdd = 0.0
    for t in seq:
        cum += t["r_net"]
        peak = max(peak, cum)
        mdd = max(mdd, peak - cum)
    return round(mdd, 3)


def group_by(ts, keyfn):
    agg = defaultdict(list)
    for t in ts:
        agg[keyfn(t)].append(t)
    return {k: {"N": len(v), "cumR": round(cum_r(v), 3), "expR": exp4(v)}
            for k, v in sorted(agg.items(), key=lambda kv: str(kv[0]))}


# ---------------------------------------------------------------- 任务一
def task1_attribution(a_tr: list[dict]) -> dict:
    ts = closed(a_tr)
    y26 = [t for t in ts if t["entry_date"][:4] == "2026"]
    hist = [t for t in ts if t["entry_date"][:4] != "2026"]
    total26 = cum_r(y26)
    out = {
        "total_2026": {"N": len(y26), "cumR": round(total26, 3),
                       "expR": exp4(y26)},
        "total_hist": {"N": len(hist), "cumR": round(cum_r(hist), 3),
                       "expR": exp4(hist)},
        "by_symbol_2026": dict(sorted(
            group_by(y26, lambda t: t["symbol"]).items(),
            key=lambda kv: kv[1]["cumR"])[:12]),
        "by_month_2026": group_by(y26, lambda t: t["entry_date"][:7]),
        "by_stage_2026": group_by(y26, lambda t: t["trend_stage"]),
        "by_stage_hist": group_by(hist, lambda t: t["trend_stage"]),
        "by_clock_2026": group_by(y26, lambda t: t["benchmark_clock_type"]),
        "by_clock_hist": group_by(hist, lambda t: t["benchmark_clock_type"]),
        "by_regime_2026": group_by(y26, lambda t: CLOCK_CN.get(t["benchmark_clock_type"], "?")),
        "by_regime_hist": group_by(hist, lambda t: CLOCK_CN.get(t["benchmark_clock_type"], "?")),
        "by_entry_reason_2026": group_by(y26, lambda t: t["entry_reason"]),
        "by_entry_reason_hist": group_by(hist, lambda t: t["entry_reason"]),
        "by_first_touch_2026": group_by(y26, lambda t: t["is_first_touch"]),
    }

    # ---- 候选过滤器（机械枚举，全部事前可判特征）----
    def eval_drop(name: str, is_dropped) -> dict:
        d26 = [t for t in y26 if is_dropped(t)]
        dh = [t for t in hist if is_dropped(t)]
        k26 = [t for t in y26 if not is_dropped(t)]
        kh = [t for t in hist if not is_dropped(t)]
        save26 = -cum_r(d26)          # 止血量（正=省下的亏损）
        hurt_h = cum_r(dh)            # 被剔历史段的累计R（负=误伤）
        usable = (save26 >= 0.5 * abs(total26) if total26 < 0 else save26 > 0
                  ) and hurt_h >= 0 and len(kh) >= 100
        return {
            "filter": name,
            "drop_2026": {"N": len(d26), "R": round(cum_r(d26), 2)},
            "drop_hist": {"N": len(dh), "R": round(cum_r(dh), 2)},
            "kept_2026": {"N": len(k26), "cumR": round(cum_r(k26), 2), "expR": exp4(k26)},
            "kept_hist": {"N": len(kh), "cumR": round(cum_r(kh), 2), "expR": exp4(kh)},
            "save_2026": round(save26, 2),
            "hurt_hist": round(hurt_h, 2),
            "usable_label": bool(usable),
        }

    cands = []
    for k in range(0, 5):  # stage <= k 全剔（=要求 stage>=k+1）
        cands.append(eval_drop(f"stage<={k} 剔除", lambda t, k=k: t["trend_stage"] <= k))
    for r in range(1, 6):  # 时钟单类剔除
        cands.append(eval_drop(
            f"clock={r} 剔除", lambda t, r=r: t["benchmark_clock_type"] == r))
    for a, b in combinations(range(1, 6), 2):  # 时钟双类剔除
        cands.append(eval_drop(
            f"clock∈{{{a},{b}}} 剔除",
            lambda t, a=a, b=b: t["benchmark_clock_type"] in (a, b)))
    for reason in sorted({t["entry_reason"] for t in ts}):
        cands.append(eval_drop(
            f"entry_reason[{reason[:18]}…] 剔除",
            lambda t, r=reason: t["entry_reason"] == reason))
    cands.append(eval_drop("非首次触碰剔除", lambda t: not t["is_first_touch"]))
    cands.append(eval_drop("首次触碰剔除", lambda t: t["is_first_touch"]))
    # 组合：stage 门槛 × 时钟剔除（最常用组合）
    for st in (3, 4):
        for drop in ((), (1,), (2,), (1, 2), (4,), (5,), (4, 5)):
            cands.append(eval_drop(
                f"stage<{st} 或 clock∈{drop or '无'} 剔除",
                lambda t, st=st, d=drop: t["trend_stage"] < st
                or t["benchmark_clock_type"] in d))
    out["candidates"] = sorted(
        cands, key=lambda c: (-c["save_2026"], -c["hurt_hist"]))
    return out


# ---------------------------------------------------------------- 任务二
def task2_routing(a_tr: list[dict], b_tr: list[dict], oos_start: str) -> dict:
    def port(name: str, ts_raw: list[dict]) -> dict:
        ts = closed(ts_raw)
        return {
            "name": name, "N": len(ts), "expR": exp4(ts),
            "cumR": round(cum_r(ts), 3),
            "IS_expR": exp4([t for t in ts if t["signal_date"] < oos_start]),
            "OOS_expR": exp4([t for t in ts if t["signal_date"] >= oos_start]),
            "maxDD_R": max_dd(ts), "by_year": yearly(ts),
        }

    clock = lambda t: t["benchmark_clock_type"]  # noqa: E731
    groups = {
        "只做A": port("只做A（现状）", a_tr),
        "只做B'": port("只做B'（个股30/3% a6_1）", b_tr),
        "横盘别做A": port("横盘别做A（现行最小规则）",
                       [t for t in a_tr if clock(t) != 3]),
        "双层路由s3": port("路由：牛熊→A(stage>=3)，横→B'(stage>=1)",
                        [t for t in a_tr if clock(t) in (1, 2, 4, 5)
                         and t["trend_stage"] >= 3]
                        + [t for t in b_tr if clock(t) == 3
                           and t["trend_stage"] >= 1]),
        "双层路由s4": port("路由：牛熊→A(stage>=4)，横→B'(stage>=1)",
                        [t for t in a_tr if clock(t) in (1, 2, 4, 5)
                         and t["trend_stage"] >= 4]
                        + [t for t in b_tr if clock(t) == 3
                           and t["trend_stage"] >= 1]),
    }

    controls = ["只做A", "只做B'", "横盘别做A"]
    best_control_cum = max(groups[c]["cumR"] for c in controls)
    a26 = groups["只做A"]["by_year"].get("2026", {}).get("cumR", 0.0)
    yearly_ok = True
    yearly_detail = {}
    for y, row in groups["双层路由s3"]["by_year"].items():
        floor = min(groups[c]["by_year"].get(y, {"cumR": 0.0})["cumR"]
                    for c in controls) - 2.0
        ok = row["cumR"] >= floor
        yearly_ok = yearly_ok and ok
        yearly_detail[y] = {"路由": row["cumR"],
                            "对照最小": round(min(groups[c]["by_year"].get(y, {"cumR": 0.0})["cumR"]
                                                  for c in controls), 3),
                            "floor": round(floor, 3), "ok": ok}
    for tag in ("双层路由s3", "双层路由s4"):
        r26 = groups[tag]["by_year"].get("2026", {}).get("cumR", 0.0)
        groups[tag]["止血_2026"] = {"cumR": r26, "只做A_2026": a26,
                                  "减半达标": bool(r26 >= 0.5 * a26) if a26 < 0 else None}
    verdict = {
        "best_control_cum": best_control_cum,
        "threshold_115": round(1.15 * best_control_cum, 3),
        "cum_pass_s3": groups["双层路由s3"]["cumR"] >= 1.15 * best_control_cum,
        "cum_pass_s4": groups["双层路由s4"]["cumR"] >= 1.15 * best_control_cum,
        "yearly_ok_s3": yearly_ok, "yearly_detail_s3": yearly_detail,
        "stopbleed_pass_s3": groups["双层路由s3"]["止血_2026"]["减半达标"],
        "stopbleed_pass_s4": groups["双层路由s4"]["止血_2026"]["减半达标"],
    }
    verdict["effective_s3"] = bool(verdict["cum_pass_s3"] and yearly_ok
                                   and verdict["stopbleed_pass_s3"])
    verdict["effective_s4"] = bool(verdict["cum_pass_s4"] and yearly_ok
                                   and verdict["stopbleed_pass_s4"])
    return {"groups": groups, "verdict": verdict}


def export_csv(a_run: dict, b_ind: dict, b_broad: dict) -> None:
    """518850/510300 多模块买卖点 CSV（A + B 各自池参数，供工作台 K 线叠加）。"""
    for sym in ("518850.SS", "510300.SS"):
        rows = []
        for module, run, tag in (("A", a_run, "cm0.5+shrink"),
                                 ("B", b_ind if sym == "518850.SS" else b_broad,
                                  "63/10%" if sym == "518850.SS" else "20/4%")):
            for t in run["trades"]:
                if t["symbol"] != sym or not t["exit_date"]:
                    continue
                rows.append({
                    "symbol": sym, "module": module, "params": tag,
                    "signal_date": t["signal_date"],
                    "entry_date": t["entry_date"], "entry_price": t["entry_price"],
                    "exit_date": t["exit_date"], "exit_price": t["exit_price"],
                    "r_net": round(t["r_net"], 4),
                    "entry_reason": t["entry_reason"], "exit_reason": t["exit_reason"],
                    "trend_stage": t["trend_stage"],
                    "benchmark_clock_type": t["benchmark_clock_type"],
                })
        rows.sort(key=lambda r: r["entry_date"])
        out = RAW / f"trades_{sym.split('.')[0]}_multimodule.csv"
        if rows:
            with out.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        print(f"[csv] {out.name}: {len(rows)} 笔（A {sum(1 for r in rows if r['module']=='A')}"
              f" / B {sum(1 for r in rows if r['module']=='B')}）")


def main() -> None:
    stocks, etf_all = build_pools()
    print(f"个股 {len(stocks)} / ETF {len(etf_all)}")

    a_run = run_and_save(
        "A_ETF_cm05_shrink",
        BacktestParams(
            module="A", symbols=tuple(sorted(set(etf_all) | {BENCHMARK})),
            rr_min=None, entry_variant="early", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True,
            overrides=(("clock_mult", 0.5),), volume_filter="shrink"))
    bp_run = run_and_save(
        "Bp_stocks_30_3_a61",
        BacktestParams(
            module="B", symbols=tuple(sorted(set(stocks) | {BENCHMARK})),
            rr_min=None, entry_variant="breakout", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True,
            overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03)),
            volume_filter="none"))
    # 518850(行业档 63/10%) / 510300(宽基档 20/4%) 的 B 买卖点（CSV 用）
    b_ind = run_and_save(
        "B_518850_63_10",
        BacktestParams(
            module="B", symbols=("518850.SS", BENCHMARK), rr_min=None,
            entry_variant="breakout", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True,
            overrides=(("consolidation_bars", 63), ("cluster_threshold", 0.10))))
    b_broad = run_and_save(
        "B_510300_20_4",
        BacktestParams(
            module="B", symbols=("510300.SS", BENCHMARK), rr_min=None,
            entry_variant="breakout", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True,
            overrides=(("consolidation_bars", 20), ("cluster_threshold", 0.04))))

    # 复核值差异验证：基准 000300.SS 自身的 A 交易（若计入 ETF 池会多出多少笔）
    bench_only = run_and_save(
        "A_000300index_recon",
        BacktestParams(
            module="A", symbols=(BENCHMARK,), rr_min=None, entry_variant="early",
            exit_variant="a6_1_costbasis", fee_label="standard", limit_guard=True,
            overrides=(("clock_mult", 0.5),), volume_filter="shrink"))
    recon_2026 = [t for t in bench_only["trades"]
                  if t["exit_date"] and t["entry_date"][:4] == "2026"]
    print(f"[recon] 000300.SS(指数) A 2026: N={len(recon_2026)}"
          f" cumR={sum(t['r_net'] for t in recon_2026):.2f}")

    t1 = task1_attribution(a_run["trades"])
    t2 = task2_routing(a_run["trades"], bp_run["trades"],
                       a_run["data_range"]["out_of_sample_start"])
    export_csv(a_run, b_ind, b_broad)

    summary = {"date": "2026-08-27", "handoff": "docs/handoff-stage-b200-prompt.md",
               "task1": t1, "task2": t2}
    (RAW / "stage_routing_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n===== 任务一：2026 归因 =====")
    print(f"2026 总计: {t1['total_2026']}  历史段: {t1['total_hist']}")
    for k in ("by_month_2026", "by_stage_2026", "by_clock_2026",
              "by_regime_2026", "by_entry_reason_2026"):
        print(f"-- {k}: {json.dumps(t1[k], ensure_ascii=False)}")
    print(f"-- stage 全期: {json.dumps(t1['by_stage_hist'], ensure_ascii=False)}")
    print("\n-- 候选过滤器 TOP15（按 2026 止血量降序）--")
    for c in t1["candidates"][:15]:
        print(f"止+{c['save_2026']:7.2f} 误{c['hurt_hist']:8.2f}"
              f" | 2026剔 {c['drop_2026']['N']:3d}笔{c['drop_2026']['R']:8.2f}"
              f" | 历史剔 {c['drop_hist']['N']:3d}笔{c['drop_hist']['R']:8.2f}"
              f" | 留存历史 exp {c['kept_hist']['expR']}"
              f" | {'可用√' if c['usable_label'] else '  ×'} | {c['filter']}")

    print("\n===== 任务二：路由 vs 对照 =====")
    for name, g in t2["groups"].items():
        print(f"{name:10s} N={g['N']:4d} exp={g['expR']} cum={g['cumR']:9.3f}"
              f" IS={g['IS_expR']} OOS={g['OOS_expR']} maxDD={g['maxDD_R']}")
    v = t2["verdict"]
    print(f"判定 s3: cum_pass={v['cum_pass_s3']} yearly_ok={v['yearly_ok_s3']}"
          f" 止血减半={v['stopbleed_pass_s3']} => "
          f"{'有效' if v['effective_s3'] else '未达有效'}")
    print(f"判定 s4: cum_pass={v['cum_pass_s4']} yearly_ok={v['yearly_ok_s3']}"
          f" 止血减半={v['stopbleed_pass_s4']} => "
          f"{'有效' if v['effective_s4'] else '未达有效'}")
    print(f"\n落盘: {RAW}/stage_routing_summary.json")


if __name__ == "__main__":
    main()
