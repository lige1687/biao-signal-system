#!/usr/bin/env python3
"""同标的多模块生命周期组合实验（docs/handoff-multimodule-lifecycle-prompt.md，2026-08-27）。

任务一（前置拆混淆）：B' 退出方式独立验证。
  B'（个股池 cb30/cl3%、breakout）× 退出 {a6_1_costbasis, b3_dual} ×
  四查（全池 / 排top1 / 分年份 / IS-OOS）。
  判定（事前写死）：a6_1 优势为真 ⇔ IS expR>0 且 OOS expR>0 且
    排 top1 后 expR(a6_1) > 1.5 × expR(b3_dual 同口径排 top1)。
  为真 → B' 正式切 a6_1（建议级）；为假 → stage-b200 路由 +45% 判退出伪影。

任务二：同标的多模块生命周期组合。
  信号池：A（ETF 池现行规则 cm0.5+shrink）+ B'（个股，退出用任务一定案者）
    + C v3（个股，bias<=-15% 过滤版）+ D（个股，默认参数），trades 全并。
  生命周期路由（标的自身 trend_stage，账本 v2.0.0 五步 0..5；
    stage0=未起步/转横代理）：
    A 放行 ⇔ stage∈{3,4}（吃趋势；stage5 大幅乖离按 §13.6 不开新仓，实测 A 池无 5 档）
    C/D 放行 ⇔ stage∈{1,2}（抄底确认段）
    B 放行 ⇔ stage==0（标的转横）且 benchmark_clock_type==3（基准横）
  同标的同日多模块并存各自记账（规格 §12），重叠持仓不互斥（资金约束不在本轮）。
  对照组：只做A / 只做B' / A+B'轮动（stage-b200 双层路由口径，B' 用任务一定案退出）
    / 全模块无路由（A+B'+C+D 全并、无门禁）。
  判定（事前写死）：生命周期组合有效 ⇔
    ① cumR >= 1.15 × max(四对照 cumR)
    ② 分年不塌：每个有信号年份 cumR >= 四对照同年最小 − 2.0R
    ③ 2019-2025 段与 2026 段都 >= 四对照同段最小值。

附带：518850 / 510300 十年全模块（A/B/C/D）买卖点 CSV，落 raw/ 供工作台 K 线叠加。

纪律：不改 configs/ src/ web/；纯实验脚本；N 累计打折（本轮新增 11 个 execute_run）。
产出：docs/experiments/raw/lifecycle_combo/*.json + *.csv
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW = REPO / "docs/experiments/raw/lifecycle_combo"
RAW.mkdir(parents=True, exist_ok=True)

BENCHMARK = "000300.SS"
OOS_FALLBACK = "2024-08-25"
EXIT_A61 = "a6_1_costbasis"
EXIT_B3 = "b3_dual"

# 生命周期路由门禁（事前写死；stage5 实测 A 池不出现，按 {3,4} 执行）
GATE_A_STAGES = {3, 4}
GATE_CD_STAGES = {1, 2}
GATE_B_STAGE, GATE_B_CLOCK = 0, 3

VERDICT_T1_TOP1_MARGIN = 1.5   # 排top1后 a6_1 需 > 1.5 × b3_dual
VERDICT_T2_CUM_EDGE = 1.15     # 累计R需超最好对照 15%+
VERDICT_T2_YEAR_SLACK = 2.0    # 分年下限 = 对照同年最小 − 2.0R
SEG_HIST, SEG_2026 = range(2019, 2026), 2026


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
          f" {r['wall_seconds']}s oos_start={r['data_range']['out_of_sample_start']}"
          f" data={r['data_range']['start']}~{r['data_range']['end']}", flush=True)
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


def drop_top1(ts):
    """排 top1：剔除累计 R 贡献最大的单一标的（该组自己的 top1）。"""
    if not ts:
        return [], None, {}
    by_sym = defaultdict(list)
    for t in ts:
        by_sym[t["symbol"]].append(t)
    top = max(by_sym, key=lambda s: cum_r(by_sym[s]))
    kept = [t for t in ts if t["symbol"] != top]
    return kept, top, {s: round(cum_r(v), 3) for s, v in by_sym.items()}


def port(name: str, ts_raw: list[dict], oos_start: str) -> dict:
    ts = closed(ts_raw)
    return {
        "name": name, "N": len(ts), "expR": exp4(ts),
        "cumR": round(cum_r(ts), 3),
        "IS_expR": exp4([t for t in ts if t["signal_date"] < oos_start]),
        "OOS_expR": exp4([t for t in ts if t["signal_date"] >= oos_start]),
        "maxDD_R": max_dd(ts), "by_year": yearly(ts),
    }


# ---------------------------------------------------------------- 任务一
def task1_exit_verify(bp_a61: list[dict], bp_b3: list[dict],
                      oos_start: str) -> dict:
    def four_checks(ts_raw: list[dict]) -> dict:
        ts = closed(ts_raw)
        kept, top, by_sym = drop_top1(ts)
        hist = [t for t in ts if int(t["entry_date"][:4]) in SEG_HIST]
        y26 = [t for t in ts if int(t["entry_date"][:4]) == SEG_2026]
        return {
            "N": len(ts), "全池": {"expR": exp4(ts), "cumR": round(cum_r(ts), 3)},
            "排top1": {"top1_symbol": top, "top1_cumR": by_sym.get(top),
                       "expR": exp4(kept), "cumR": round(cum_r(kept), 3),
                       "N": len(kept)},
            "分年份": yearly(ts),
            "IS_OOS": {
                "IS": {"expR": exp4([t for t in ts
                                     if t["signal_date"] < oos_start]),
                       "N": sum(1 for t in ts if t["signal_date"] < oos_start)},
                "OOS": {"expR": exp4([t for t in ts
                                      if t["signal_date"] >= oos_start]),
                        "N": sum(1 for t in ts
                                 if t["signal_date"] >= oos_start)}},
            "seg_2019_2025": {"N": len(hist), "cumR": round(cum_r(hist), 3)},
            "seg_2026": {"N": len(y26), "cumR": round(cum_r(y26), 3)},
        }

    a61, b3 = four_checks(bp_a61), four_checks(bp_b3)
    is_pos = a61["IS_OOS"]["IS"]["expR"] is not None and a61["IS_OOS"]["IS"]["expR"] > 0
    oos_pos = (a61["IS_OOS"]["OOS"]["expR"] is not None
               and a61["IS_OOS"]["OOS"]["expR"] > 0)
    e_a, e_b = a61["排top1"]["expR"], b3["排top1"]["expR"]
    margin_ok = (e_a is not None and e_b is not None
                 and e_a > VERDICT_T1_TOP1_MARGIN * e_b)
    verdict = {
        "IS_正": is_pos, "OOS_正": oos_pos,
        "排top1_a61": e_a, "排top1_b3": e_b,
        "排top1_margin(1.5x)": round(VERDICT_T1_TOP1_MARGIN * e_b, 4) if e_b is not None else None,
        "排top1_margin_达标": margin_ok,
        "a61_优势为真": bool(is_pos and oos_pos and margin_ok),
        "结论": None,
    }
    verdict["结论"] = ("B' 正式切 a6_1（建议级）" if verdict["a61_优势为真"]
                     else "a6_1 优势不成立：stage-b200 路由 +45% 判为退出伪影")
    return {"a6_1": a61, "b3_dual": b3, "verdict": verdict}


# ---------------------------------------------------------------- 任务二
def task2_lifecycle(a_tr, bp_tr, c_tr, d_tr, oos_start: str) -> dict:
    for t in a_tr:
        t["module"] = "A"
    for t in bp_tr:
        t["module"] = "B'"
    for t in c_tr:
        t["module"] = "C"
    for t in d_tr:
        t["module"] = "D"
    merged = a_tr + bp_tr + c_tr + d_tr
    clock = lambda t: t["benchmark_clock_type"]  # noqa: E731
    stage = lambda t: t["trend_stage"]  # noqa: E731

    def lifecycle_pass(t) -> bool:
        if t["module"] == "A":
            return stage(t) in GATE_A_STAGES
        if t["module"] == "B'":
            return stage(t) == GATE_B_STAGE and clock(t) == GATE_B_CLOCK
        return stage(t) in GATE_CD_STAGES  # C / D

    bp_exit = bp_tr[0]["exit_variant"] if bp_tr else "?"
    ab_rot = ([t for t in a_tr if clock(t) in (1, 2, 4, 5) and stage(t) >= 3]
              + [t for t in bp_tr if clock(t) == 3 and stage(t) >= 1])
    lc_tr = [t for t in merged if lifecycle_pass(t)]
    groups = {
        "只做A": port("只做A（ETF池 cm0.5+shrink）", a_tr, oos_start),
        "只做B'": port(f"只做B'（个股30/3%·{bp_exit}）", bp_tr, oos_start),
        "A+B'轮动": port("A+B'轮动（stage-b200 双层路由口径）", ab_rot, oos_start),
        "全模块无路由": port("全模块无路由（A+B'+C+D 全并）", merged, oos_start),
        "生命周期路由": port("生命周期路由（stage: 3-4→A / 1-2→C·D / 0+基准横→B'）",
                        [t for t in merged if lifecycle_pass(t)], oos_start),
    }

    # 门禁通过率与被剔增量分解（每组被剔交易的构成）
    gate_detail = {}
    for mod in ("A", "B'", "C", "D"):
        src = {"A": a_tr, "B'": bp_tr, "C": c_tr, "D": d_tr}[mod]
        passed = [t for t in src if lifecycle_pass(t)]
        dropped = [t for t in src if not lifecycle_pass(t)]
        gate_detail[mod] = {
            "总N": len(src), "放行N": len(passed),
            "放行cumR": round(cum_r(closed(passed)), 3),
            "被剔N": len(dropped),
            "被剔cumR": round(cum_r(closed(dropped)), 3),
            "被剔stage分布": {str(s): len(v) for s, v in sorted(
                _group(dropped, lambda t: t["trend_stage"]).items())},
        }

    controls = ["只做A", "只做B'", "A+B'轮动", "全模块无路由"]
    treat = groups["生命周期路由"]

    def seg(ts_raw, years) -> float:
        ys = set(years) if not isinstance(years, int) else {years}
        return round(cum_r([t for t in closed(ts_raw)
                            if int(t["entry_date"][:4]) in ys]), 3)

    raw_trades = {"只做A": a_tr, "只做B'": bp_tr, "A+B'轮动": ab_rot,
                  "全模块无路由": merged, "生命周期路由": lc_tr}

    seg_hist = {c: seg(raw_trades[c], SEG_HIST) for c in groups}
    seg_2026 = {c: seg(raw_trades[c], SEG_2026) for c in groups}
    cum_pass = treat["cumR"] >= VERDICT_T2_CUM_EDGE * max(
        groups[c]["cumR"] for c in controls)

    yearly_ok, yearly_detail = True, {}
    for y, row in treat["by_year"].items():
        floor = min(groups[c]["by_year"].get(y, {"cumR": 0.0})["cumR"]
                    for c in controls) - VERDICT_T2_YEAR_SLACK
        ok = row["cumR"] >= floor
        yearly_ok = yearly_ok and ok
        yearly_detail[y] = {"路由": row["cumR"],
                            "对照最小": round(min(groups[c]["by_year"].get(y, {"cumR": 0.0})["cumR"]
                                                  for c in controls), 3),
                            "floor": round(floor, 3), "ok": ok}
    seg_hist_ok = seg_hist["生命周期路由"] >= min(seg_hist[c] for c in controls)
    seg_2026_ok = seg_2026["生命周期路由"] >= min(seg_2026[c] for c in controls)

    verdict = {
        "cum_pass": bool(cum_pass),
        "最好对照_cumR": max(groups[c]["cumR"] for c in controls),
        "阈值_1.15x": round(VERDICT_T2_CUM_EDGE * max(groups[c]["cumR"] for c in controls), 3),
        "yearly_ok": yearly_ok, "yearly_detail": yearly_detail,
        "seg_2019_2025": seg_hist, "seg_2026": seg_2026,
        "seg_hist_ok": bool(seg_hist_ok), "seg_2026_ok": bool(seg_2026_ok),
        "effective": bool(cum_pass and yearly_ok and seg_hist_ok and seg_2026_ok),
    }
    return {"groups": groups, "gate_detail": gate_detail,
            "lifecycle_module_split": {
                m: port(f"路由后·{m}", [t for t in merged
                                     if t["module"] == m and lifecycle_pass(t)],
                        oos_start)
                for m in ("A", "B'", "C", "D")},
            "seg_2019_2025": seg_hist, "seg_2026": seg_2026,
            "verdict": verdict}


def _group(items, keyfn):
    agg = defaultdict(list)
    for it in items:
        agg[keyfn(it)].append(it)
    return agg


# ---------------------------------------------------------------- CSV
def export_csv(a_run, b_gold, b_hs300, c_gold, c_hs300, d_gold, d_hs300) -> None:
    """518850 / 510300 十年全模块买卖点 CSV（A/B/C/D，供工作台 K 线叠加）。"""
    sources = {
        "518850.SS": (("A", a_run, "ETF池cm0.5+shrink"), ("B", b_gold, "63/10%"),
                      ("C", c_gold, "v3·bias-15%"), ("D", d_gold, "默认126/2")),
        "510300.SS": (("A", a_run, "ETF池cm0.5+shrink"), ("B", b_hs300, "20/4%"),
                      ("C", c_hs300, "v3·bias-15%"), ("D", d_hs300, "默认126/2")),
    }
    for sym, mods in sources.items():
        rows = []
        for module, run, tag in mods:
            for t in run["trades"]:
                if t["symbol"] != sym or not t["exit_date"]:
                    continue
                routed = (
                    (module == "A" and t["trend_stage"] in GATE_A_STAGES)
                    or (module == "B" and t["trend_stage"] == GATE_B_STAGE
                        and t["benchmark_clock_type"] == GATE_B_CLOCK)
                    or (module in ("C", "D") and t["trend_stage"] in GATE_CD_STAGES))
                rows.append({
                    "symbol": sym, "module": module, "params": tag,
                    "lifecycle_pass": "Y" if routed else "N",
                    "signal_date": t["signal_date"],
                    "entry_date": t["entry_date"], "entry_price": t["entry_price"],
                    "exit_date": t["exit_date"], "exit_price": t["exit_price"],
                    "r_net": round(t["r_net"], 4),
                    "entry_reason": t["entry_reason"], "exit_reason": t["exit_reason"],
                    "trend_stage": t["trend_stage"],
                    "benchmark_clock_type": t["benchmark_clock_type"],
                })
        rows.sort(key=lambda r: r["entry_date"])
        out = RAW / f"trades_{sym.split('.')[0]}_lifecycle_allmodule.csv"
        if rows:
            with out.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        cnt = {m: sum(1 for r in rows if r["module"] == m) for m in "ABCD"}
        print(f"[csv] {out.name}: {len(rows)} 笔 "
              f"(A {cnt['A']} / B {cnt['B']} / C {cnt['C']} / D {cnt['D']})", flush=True)


def main() -> None:
    stocks, etf_all = build_pools()
    print(f"个股 {len(stocks)} / ETF {len(etf_all)}", flush=True)
    stock_syms = tuple(sorted(set(stocks) | {BENCHMARK}))
    etf_syms = tuple(sorted(set(etf_all) | {BENCHMARK}))
    bp_base = dict(module="B", entry_variant="breakout", rr_min=None,
                   fee_label="standard", limit_guard=True,
                   overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03)))

    # ---- 任务一：B' 退出方式独立验证（2 run）
    t1_a61 = run_and_save("T1_Bp_a61", BacktestParams(
        symbols=stock_syms, exit_variant=EXIT_A61, **bp_base))
    t1_b3 = run_and_save("T1_Bp_b3", BacktestParams(
        symbols=stock_syms, exit_variant=EXIT_B3, **bp_base))
    oos = t1_a61["data_range"]["out_of_sample_start"] or OOS_FALLBACK
    task1 = task1_exit_verify(t1_a61["trades"], t1_b3["trades"], oos)
    winner = EXIT_A61 if task1["verdict"]["a61_优势为真"] else EXIT_B3
    print(f"\n[任务一] 判定: a6_1 优势为真 = {task1['verdict']['a61_优势为真']}"
          f" → B' 定案退出 = {winner}\n  {task1['verdict']['结论']}", flush=True)

    # ---- 任务二：模块池（3 新 run + B' 用定案 run）
    a_run = run_and_save("T2_A_ETF_cm05_shrink", BacktestParams(
        module="A", symbols=etf_syms, rr_min=None, entry_variant="early",
        exit_variant=EXIT_A61, fee_label="standard", limit_guard=True,
        overrides=(("clock_mult", 0.5),), volume_filter="shrink"))
    c_run = run_and_save("T2_C_stocks_v3_b15", BacktestParams(
        module="C", symbols=stock_syms, rr_min=None, entry_variant="v3",
        exit_variant=EXIT_A61, fee_label="standard", limit_guard=True,
        bias_filter=-0.15))
    d_run = run_and_save("T2_D_stocks_default", BacktestParams(
        module="D", symbols=stock_syms, rr_min=None, entry_variant=None,
        exit_variant=EXIT_A61, fee_label="standard", limit_guard=True))
    bp_run = t1_a61 if winner == EXIT_A61 else t1_b3
    task2 = task2_lifecycle(a_run["trades"], bp_run["trades"],
                            c_run["trades"], d_run["trades"], oos)

    # ---- CSV：两标的四模块单点 run（6 run）
    def single_run(name, sym, **kw):
        base = dict(rr_min=None, fee_label="standard", limit_guard=True,
                    symbols=(sym, BENCHMARK))
        base.update(kw)
        return run_and_save(name, BacktestParams(**base))

    b_gold = single_run("CSV_B_518850_63_10", "518850.SS", module="B",
                        entry_variant="breakout", exit_variant=winner,
                        overrides=(("consolidation_bars", 63), ("cluster_threshold", 0.10)))
    b_hs300 = single_run("CSV_B_510300_20_4", "510300.SS", module="B",
                         entry_variant="breakout", exit_variant=winner,
                         overrides=(("consolidation_bars", 20), ("cluster_threshold", 0.04)))
    c_gold = single_run("CSV_C_518850_v3b15", "518850.SS", module="C",
                        entry_variant="v3", exit_variant=EXIT_A61, bias_filter=-0.15)
    c_hs300 = single_run("CSV_C_510300_v3b15", "510300.SS", module="C",
                         entry_variant="v3", exit_variant=EXIT_A61, bias_filter=-0.15)
    d_gold = single_run("CSV_D_518850_default", "518850.SS", module="D",
                        entry_variant=None, exit_variant=EXIT_A61)
    d_hs300 = single_run("CSV_D_510300_default", "510300.SS", module="D",
                         entry_variant=None, exit_variant=EXIT_A61)
    export_csv(a_run, b_gold, b_hs300, c_gold, c_hs300, d_gold, d_hs300)

    # ---- 汇总落盘
    (RAW / "task1_exit_verification.json").write_text(
        json.dumps(task1, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAW / "task2_lifecycle_summary.json").write_text(
        json.dumps(task2, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n===== 任务一：B' 退出四查 =====", flush=True)
    for tag in ("a6_1", "b3_dual"):
        v = task1[tag]
        print(f"[{tag}] N={v['N']} 全池 exp={v['全池']['expR']} cum={v['全池']['cumR']}"
              f" | 排top1({v['排top1']['top1_symbol']}) exp={v['排top1']['expR']}"
              f" | IS={v['IS_OOS']['IS']['expR']}({v['IS_OOS']['IS']['N']})"
              f" OOS={v['IS_OOS']['OOS']['expR']}({v['IS_OOS']['OOS']['N']})"
              f" | 2019-25 {v['seg_2019_2025']['cumR']} 2026 {v['seg_2026']['cumR']}", flush=True)
    print(f"判定: IS_正={task1['verdict']['IS_正']} OOS_正={task1['verdict']['OOS_正']}"
          f" 排top1_margin_达标={task1['verdict']['排top1_margin_达标']}"
          f" => {task1['verdict']['结论']}", flush=True)

    print("\n===== 任务二：生命周期路由 vs 对照 =====", flush=True)
    for name, g in task2["groups"].items():
        print(f"{name:8s} N={g['N']:4d} exp={g['expR']} cum={g['cumR']:9.3f}"
              f" IS={g['IS_expR']} OOS={g['OOS_expR']} maxDD={g['maxDD_R']}", flush=True)
    print("-- 门禁通过率 --", flush=True)
    for mod, d in task2["gate_detail"].items():
        print(f"{mod:3s} 总N={d['总N']:4d} 放行N={d['放行N']:4d}"
              f" 放行cumR={d['放行cumR']:9.3f} 被剔cumR={d['被剔cumR']:9.3f}", flush=True)
    v = task2["verdict"]
    print(f"判定: cum_pass={v['cum_pass']} (阈值 {v['阈值_1.15x']})"
          f" yearly_ok={v['yearly_ok']} seg_hist_ok={v['seg_hist_ok']}"
          f" seg_2026_ok={v['seg_2026_ok']} => "
          f"{'有效' if v['effective'] else '未达有效'}", flush=True)
    bad_years = {y: d for y, d in v["yearly_detail"].items() if not d["ok"]}
    if bad_years:
        print(f"分年失败项: {json.dumps(bad_years, ensure_ascii=False)}", flush=True)
    print(f"\n落盘: {RAW}/task1_exit_verification.json / task2_lifecycle_summary.json",
          flush=True)


if __name__ == "__main__":
    main()
