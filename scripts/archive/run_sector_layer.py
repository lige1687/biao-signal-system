#!/usr/bin/env python3
"""板块选股层 + 三层完整流程回测（docs/handoff-sector-layer-prompt.md，2026-08-27）。

手册依据：3.7 行业相对强度（行业÷大盘）、4.2 大势三层、2.4 时钟五类。

任务一：三个候选板块筛选器（信号日截面，仅用当日及此前数据）：
  F1 = 板块时钟二类（稳定上涨）集合；
  F2 = RS_60 动量（板块/沪深300 比值 60 日变化率）排名 top N（N=5/8）；
  F3 = F1 ∩ RS top8。
  验证：A 模块信号（ETF 池现行规则、门禁后）只落在「入选板块对应的
  行业 ETF」（映射多对多：ETF 的任一映射板块入选即放行；未映射 ETF 剔除
  并记录）；对照 = 平池全放。四查：IS/OOS、排 top1、分年份、分标的。
  判定（事前写死）：板块层有增量 = 筛选后 expR >= 平池 expR 的 110%
  且 笔数 >= 平池的 40%。胜者 = 通过者中 expR 最高（平手取笔数多者）。

任务二：三层完整流程（宽度闸 V2@B200 × 任务一胜者板块筛选 × 资金层
  1%/降级/N10/池6 × A 池信号去重后；B' 个股池不进本轮——无板块映射）。
  三道考题（事前写死，对上轮串联版绝对值）：
  ① 阴跌段(2021-06-18~2024-02-29)回撤 <= 11.9% + 3pp = 14.9%；
  ② 2026 年内回撤 <= 8.5% + 3pp = 11.5%；
  ③ 全期终值 >= 299.8 万 × 1.05 = 314.8 万。
  对照：平池全放（A 池无板块层）+ 上轮串联版复算（A+B'，锚定上轮数字）。

任务三：逐月板块轮动面板 CSV（入选清单 / RS 排名 / 宽度 cap / 当月成交）。

纪律：不改 configs/web；src/ 改动仅 full_sim.filter_by_sector（纯函数，
默认不启用）；判定事前写死；N 累计打折（本轮 0 个新 execute_run，复用
raw/portfolio/A_ETF_cm05_shrink.json 与 Bp_stocks_30_3_a61.json）。
产出：docs/experiments/raw/sector_layer/*.json + *.csv
复现：python3 scripts/run_sector_layer.py [--rerun]
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    filter_by_sector,
    load_b200_series,
    position_cap_map,
)
from lei_signal.backtest.portfolio import (  # noqa: E402
    PortfolioConfig,
    simulate_portfolio,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402
from lei_signal.rules.clock_classifier import TYPE2_STEADY_UP, clock_series  # noqa: E402

RAW = REPO / "docs/experiments/raw/sector_layer"
RAW.mkdir(parents=True, exist_ok=True)
BENCHMARK = "000300.SS"
SEG_LO, SEG_HI = "2021-06-18", "2024-02-29"
VERDICT_EXP_MULT, VERDICT_N_FLOOR = 1.10, 0.40
V_SEGD_MAX, V_DD26_MAX, V_FINAL_MIN = 14.9, 11.5, 3_147_900.0  # 上轮 11.9/8.5/299.8万 +3pp / ×1.05
OOS_FALLBACK = "2024-08-25"

#: 同花顺行业板块（回测池 20 个，名称取自 labels 账本口径）
SECTOR_NAMES = {
    "TH881102.SECTOR": "养殖业", "TH881109.SECTOR": "化学制品",
    "TH881114.SECTOR": "金属新材料", "TH881121.SECTOR": "半导体",
    "TH881129.SECTOR": "通信设备", "TH881134.SECTOR": "食品加工制造",
    "TH881145.SECTOR": "电力", "TH881155.SECTOR": "银行",
    "TH881156.SECTOR": "保险", "TH881157.SECTOR": "证券",
    "TH881168.SECTOR": "工业金属", "TH881169.SECTOR": "贵金属",
    "TH881170.SECTOR": "小金属", "TH881267.SECTOR": "能源金属",
    "TH881272.SECTOR": "软件开发", "TH881273.SECTOR": "白酒",
    "TH881278.SECTOR": "电网设备", "TH881279.SECTOR": "光伏设备",
    "TH881280.SECTOR": "风电设备", "TH881281.SECTOR": "电池",
}

#: ETF→板块映射（名称对应，多对多；宽基/风格/无对应板块的 ETF 不入表=剔除）
#: 宽基对照（不入行业映射）：510050/510300/510500/512100/159901/159915/
#: 588000/512920/512890/515130/515300；无对应板块：512010 医药、512170 医疗、
#: 512200 房地产、512580 环保、512660 军工、512980 传媒、515210 钢铁、
#: 515220 煤炭、516010 游戏、562500 机器人、159992 创新药。
ETF_SECTOR_MAP: dict[str, tuple[str, ...]] = {
    "159611.SZ": ("TH881145.SECTOR",),                      # 电力ETF广发
    "159652.SZ": ("TH881168.SECTOR", "TH881170.SECTOR",
                  "TH881267.SECTOR"),                        # 有色ETF汇添富
    "159819.SZ": ("TH881272.SECTOR", "TH881129.SECTOR"),    # 人工智能ETF易方达
    "159825.SZ": ("TH881102.SECTOR",),                      # 农业ETF富国
    "159865.SZ": ("TH881102.SECTOR",),                      # 养殖ETF国泰
    "159928.SZ": ("TH881134.SECTOR", "TH881273.SECTOR"),    # 消费ETF汇添富
    "159995.SZ": ("TH881121.SECTOR",),                      # 芯片ETF华夏
    "512000.SS": ("TH881157.SECTOR",),                      # 券商ETF华宝
    "512400.SS": ("TH881168.SECTOR", "TH881170.SECTOR",
                  "TH881267.SECTOR"),                        # 有色金属ETF南方
    "512480.SS": ("TH881121.SECTOR",),                      # 半导体ETF国联安
    "512690.SS": ("TH881273.SECTOR",),                      # 酒ETF鹏华
    "512760.SS": ("TH881121.SECTOR",),                      # 芯片ETF国泰
    "512800.SS": ("TH881155.SECTOR",),                      # 银行ETF华宝
    "515030.SS": ("TH881281.SECTOR",),                      # 新能源车ETF华夏
    "515050.SS": ("TH881129.SECTOR",),                      # 通信ETF华夏
    "515170.SS": ("TH881134.SECTOR", "TH881273.SECTOR"),    # 食品饮料ETF华夏
    "515790.SS": ("TH881279.SECTOR",),                      # 光伏ETF华泰柏瑞
    "515880.SS": ("TH881129.SECTOR",),                      # 通信ETF国泰
    "516220.SS": ("TH881109.SECTOR",),                      # 化工ETF国泰
    "516510.SS": ("TH881272.SECTOR",),                      # 云计算ETF易方达
    "518850.SS": ("TH881169.SECTOR",),                      # 黄金ETF华夏
    "562590.SS": ("TH881121.SECTOR",),                      # 半导体设备ETF华夏
}


def build_pools():
    frames = load_pool_frames()
    available = set(frames)
    stocks = []
    for line in (REPO / "docs/experiments/raw/bcd_retrial/stock_pool.txt") \
            .read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.split()[0] in available:
            stocks.append(line.split()[0])
    etf_all = sorted(
        s for s in available
        if s.split(".")[0].startswith(("51", "56", "58", "159"))
        and not s.split(".")[0].startswith("513"))
    return stocks, etf_all


def load_a_run(rerun: bool) -> dict:
    path = REPO / "docs/experiments/raw/portfolio/A_ETF_cm05_shrink.json"
    if path.exists() and not rerun:
        return json.loads(path.read_text(encoding="utf-8"))
    stocks, etf_all = build_pools()
    r = execute_run(BacktestParams(
        module="A", symbols=tuple(sorted(set(etf_all) | {BENCHMARK})),
        rr_min=None, entry_variant="early", exit_variant="a6_1_costbasis",
        fee_label="standard", limit_guard=True,
        overrides=(("clock_mult", 0.5),), volume_filter="shrink"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    return r


def gate_a(a_run: dict) -> list[dict]:
    return [{**t, "pool": "A_ETF"}
            for t in a_run["trades"]
            if t["exit_date"] is not None
            and t["benchmark_clock_type"] != 3 and t["trend_stage"] >= 4]


# ---------------------------------------------------------------- 板块截面

def build_sector_panels(frames: dict, bench_close: pd.Series):
    """每板块：时钟序列（date→int）与 RS_60（date→动量）。"""
    panels = {}
    for sym in SECTOR_NAMES:
        f = frames.get(sym)
        if f is None:
            continue
        clk = clock_series(f)
        ratio = f["close"] / bench_close.reindex(f.index).ffill()
        rs60 = ratio / ratio.shift(60) - 1.0
        panels[sym] = {
            "clock": {d.isoformat(): int(v) for d, v in clk.items()},
            "rs60": {d.isoformat(): float(v) for d, v in rs60.items()},
        }
    return panels


def _as_of(mapping: dict, day: str):
    keys = mapping["sorted_days"]
    lo, hi = 0, len(keys) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if keys[mid] <= day:
            best = keys[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def make_sector_pass(panels: dict, mode: str, topn: int = 8):
    """返回 sector_pass(signal_date, symbol)。mode ∈ {F1, F2, F3}。

    RS 排名 = 20 板块按 RS_60 降序取前 topn；缺 RS 当日按 -inf（垫底）。
    未映射 ETF 一律剔除（False）。
    """
    for p in panels.values():
        p["sorted_days"] = sorted(p["clock"])
    syms = sorted(panels)

    def selection(day: str) -> set[str]:
        rs_scores = {}
        for s in syms:
            d = _as_of(panels[s], day)
            if d is not None:
                rs_scores[s] = panels[s]["rs60"].get(d, float("-inf"))
        top = set(sorted(rs_scores, key=lambda s: rs_scores[s],
                         reverse=True)[:topn])
        if mode == "F2":
            return top
        two = {s for s in rs_scores
               if panels[s]["clock"].get(_as_of(panels[s], day), 0)
               == TYPE2_STEADY_UP}
        return top & two if mode == "F3" else two

    cache: dict[str, set[str]] = {}

    def pass_fn(day: str, symbol: str) -> bool:
        if symbol not in ETF_SECTOR_MAP:
            return False
        if day not in cache:
            cache[day] = selection(day)
        return any(s in cache[day] for s in ETF_SECTOR_MAP[symbol])

    return pass_fn, cache


# ---------------------------------------------------------------- 四查工具

def exp_r(ts):
    return None if not ts else sum(t["r_net"] for t in ts) / len(ts)


def r4(ts):
    return None if not ts else round(exp_r(ts), 4)


def cum_r(ts):
    return round(sum(t["r_net"] for t in ts), 3)


def yearly(ts):
    agg = defaultdict(list)
    for t in ts:
        agg[t["signal_date"][:4]].append(t)
    return {y: {"N": len(v), "cumR": cum_r(v), "expR": r4(v)}
            for y, v in sorted(agg.items())}


def four_checks(ts, oos_start: str) -> dict:
    by_sym = defaultdict(list)
    for t in ts:
        by_sym[t["symbol"]].append(t)
    top = max(by_sym, key=lambda s: sum(t["r_net"] for t in by_sym[s])) \
        if by_sym else None
    kept = [t for t in ts if t["symbol"] != top]
    return {
        "N": len(ts), "expR": r4(ts), "cumR": cum_r(ts),
        "IS_expR": r4([t for t in ts if t["signal_date"] < oos_start]),
        "OOS_expR": r4([t for t in ts if t["signal_date"] >= oos_start]),
        "top1_symbol": top, "top1_cumR": cum_r(by_sym.get(top, [])),
        "no_top1_expR": r4(kept), "no_top1_N": len(kept),
        "by_year": yearly(ts),
        "by_symbol": {s: {"N": len(v), "cumR": cum_r(v)}
                      for s, v in sorted(by_sym.items())},
    }


def seg_max_dd(curve: list[dict], lo: str, hi: str) -> float | None:
    pts = [p for p in curve if lo <= p["date"] <= hi]
    if not pts:
        return None
    seed = next((p["equity"] for p in reversed(curve) if p["date"] < lo),
                pts[0]["equity"])
    peak, mdd = seed, 0.0
    for p in pts:
        peak = max(peak, p["equity"])
        if peak > 0:
            mdd = max(mdd, (peak - p["equity"]) / peak)
    return round(mdd * 100, 3)


def main() -> None:
    rerun = "--rerun" in sys.argv
    a_run = load_a_run(rerun)
    flat = gate_a(a_run)
    oos = a_run["data_range"].get("out_of_sample_start") or OOS_FALLBACK
    print(f"[A 门禁后] {len(flat)} 笔 cumR {cum_r(flat):+.1f} oos={oos}")

    frames = load_pool_frames()
    bench_close = frames[BENCHMARK]["close"]
    panels = build_sector_panels(frames, bench_close)
    print(f"[板块] {len(panels)}/20 有数据；映射 ETF {len(ETF_SECTOR_MAP)} 只"
          f"（A 池未映射剔除："
          f"{sorted({t['symbol'] for t in flat} - set(ETF_SECTOR_MAP))}）")

    # ---- 任务一：F1 / F2@5 / F2@8 / F3 ----
    flat4 = four_checks(flat, oos)
    arms = {"平池全放": flat4}
    fns = {}
    for name, mode, topn in (("F1_二类", "F1", 8), ("F2_top5", "F2", 5),
                              ("F2_top8", "F2", 8), ("F3_二类∩top8", "F3", 8)):
        pass_fn, _ = make_sector_pass(panels, mode, topn)
        fns[name] = pass_fn
        sel, st = filter_by_sector(flat, pass_fn)
        arms[name] = {**four_checks(sel, oos), "filter_stats": st}

    task1_verdicts = {}
    for name in ("F1_二类", "F2_top5", "F2_top8", "F3_二类∩top8"):
        v = arms[name]
        ok = (v["expR"] is not None and flat4["expR"]
              and v["expR"] >= VERDICT_EXP_MULT * flat4["expR"]
              and v["N"] >= VERDICT_N_FLOOR * flat4["N"])
        task1_verdicts[name] = {
            "expR_ratio": round(v["expR"] / flat4["expR"], 3)
            if v["expR"] and flat4["expR"] else None,
            "N_ratio": round(v["N"] / flat4["N"], 3),
            "pass": bool(ok)}
    passing = [n for n, v in task1_verdicts.items() if v["pass"]]
    winner = max(passing, key=lambda n: (arms[n]["expR"], arms[n]["N"])) \
        if passing else None
    # 无胜者时的降级口径（明确标注）：取 expR 最高的候选跑任务二/三，
    # 三道考题照判，但结论按「未过任务一双杠的候选」打折披露。
    fallback = max(("F1_二类", "F2_top5", "F2_top8", "F3_二类∩top8"),
                   key=lambda n: (arms[n]["expR"] or -9e9, arms[n]["N"]))
    eff_filter = winner or fallback
    print("\n===== 任务一：板块筛选器四查 =====")
    for name, v in arms.items():
        vd = task1_verdicts.get(name, {})
        print(f"{name:<12} N={v['N']:<4} exp={v['expR']} cum={v['cumR']:+.1f}"
              f" IS={v['IS_expR']} OOS={v['OOS_expR']}"
              f" 排top1({v['top1_symbol']})={v['no_top1_expR']}"
              + (f" => {'过' if vd['pass'] else '×'}"
                 f"（exp×{vd['expR_ratio']} N×{vd['N_ratio']}）" if vd else ""))
    print(f"胜者: {winner}")

    # ---- 任务二：三层完整流程 ----
    b200 = load_b200_series()
    cap_map = position_cap_map(b200, TIERS_V2)
    cap_fn = cap_fn_from_map(cap_map)
    cfg = PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                          pool_concurrent_cap=6, dd_deescalate=True)

    a_stream, _ = dedup_signals(flat)                      # 平池全放（A 池）
    sel_flat, st = filter_by_sector(flat, fns[eff_filter])
    s_stream, _ = dedup_signals(sel_flat)                  # 加板块层
    armA = simulate_portfolio(a_stream, replace(cfg, cap_fn=cap_fn))
    armS = simulate_portfolio(s_stream, replace(cfg, cap_fn=cap_fn))
    # 上轮串联版复算（A+B'，锚定上轮数字）
    bp_path = REPO / "docs/experiments/raw/portfolio/Bp_stocks_30_3_a61.json"
    bp_trades = []
    if bp_path.exists():
        bp_run = json.loads(bp_path.read_text(encoding="utf-8"))
        bp_trades = [{**t, "pool": "B_STOCK", "module": "B'"}
                     for t in bp_run["trades"]
                     if t["exit_date"] is not None]
    ab_stream, _ = dedup_signals(flat + bp_trades)
    armAB = simulate_portfolio(ab_stream, replace(cfg, cap_fn=cap_fn))

    v = {
        "q1_seg_dd": seg_max_dd(armS["curve"], SEG_LO, SEG_HI) if s_stream else None,
        "q1_pass": bool(s_stream and seg_max_dd(armS["curve"], SEG_LO, SEG_HI)
                        <= V_SEGD_MAX),
        "q2_dd26": armS["by_year"].get("2026", {}).get("max_drawdown_pct")
        if s_stream else None,
        "q2_pass": bool(s_stream and armS["by_year"].get("2026", {})
                        .get("max_drawdown_pct") is not None
        and armS["by_year"]["2026"]["max_drawdown_pct"] <= V_DD26_MAX),
        "q3_final": armS["final_equity"] if s_stream else None,
        "q3_pass": bool(s_stream and armS["final_equity"] >= V_FINAL_MIN),
    }
    v["all_pass"] = bool(v["q1_pass"] and v["q2_pass"] and v["q3_pass"])

    print("\n===== 任务二：三层完整流程 =====")
    for name, r, n in (("平池全放(A池)", armA, len(a_stream)),
                       (f"加板块层({eff_filter})", armS, len(s_stream)),
                       ("上轮串联复算(A+B')", armAB, len(ab_stream))):
        fe = r["final_equity"]
        print(f"{name:<20} N={n:<4} 终值 {fe if fe is not None else float('nan'):>12.0f}"
              f" 全局DD {r['max_drawdown_pct']:>6.2f}%"
              f" 阴跌段DD {seg_max_dd(r['curve'], SEG_LO, SEG_HI):>6.2f}%"
              f" 2026DD "
              f"{r['by_year'].get('2026', {}).get('max_drawdown_pct')}%")
    print(f"判定: {json.dumps(v, ensure_ascii=False)}")

    # ---- 任务三：逐月面板 ----
    months = sorted({t["entry_date"][:7] for t in (s_stream or [])} |
                    {p["date"][:7] for p in armS["curve"]})
    pass_fn = fns.get(eff_filter)
    panel_rows = []
    taken_by_month = defaultdict(list)
    for t in armS["taken"]:
        taken_by_month[t["entry_date"][:7]].append(t)
    if pass_fn:
        for p in panels.values():
            p["sorted_days"] = sorted(p["clock"])
    all_sector_days = sorted({d for p in panels.values() for d in p["clock"]})
    for m in months:
        month_end = max((d for d in all_sector_days if d[:7] == m),
                        default=None)
        sel = set()
        if pass_fn and month_end:
            rs_scores = {}
            for s, p in panels.items():
                d = _as_of(p, month_end)
                if d:
                    rs_scores[s] = p["rs60"].get(d, float("-inf"))
            top = set(sorted(rs_scores, key=lambda x: rs_scores[x],
                             reverse=True)[:8])
            two = {s for s in rs_scores
                   if panels[s]["clock"].get(
                       _as_of(panels[s], month_end), 0) == TYPE2_STEADY_UP}
            mode = eff_filter.split("_")[0]
            sel = top if mode == "F2" else (top & two if mode == "F3" else two)
        ranks = sorted(((panels[s]["rs60"].get(
            _as_of(panels[s], month_end), float("-inf")), s)
            for s in panels if month_end), reverse=True)
        tk = taken_by_month.get(m, [])
        panel_rows.append({
            "month": m,
            "selected_sectors": ";".join(
                f"{s.split('.')[0]}({SECTOR_NAMES.get(s, '?')})"
                for _, s in ranks if s in sel),
            "n_selected": len(sel),
            "rs_top8": ";".join(
                f"{SECTOR_NAMES.get(s, s.split('.')[0])}"
                f"{panels[s]['rs60'].get(_as_of(panels[s], month_end), 0):+.2%}"
                for _, s in ranks[:8]),
            "cap_month_end": next(
                (cap_fn(d) for d in sorted(b200, reverse=True)
                 if d[:7] == m), ""),
            "b200_month_end": next(
                (round(b200[d], 1) for d in sorted(b200, reverse=True)
                 if d[:7] == m), ""),
            "n_trades": len(tk),
            "trade_detail": ";".join(
                f"{t['symbol']}@{t['entry_date']} r={t['r_net']:+.2f}"
                for t in tk),
            "equity_month_end": next(
                (p["equity"] for p in reversed(armS["curve"])
                 if p["date"][:7] == m), ""),
        })
    with (RAW / "sector_rotation_panel.csv").open(
            "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(panel_rows[0].keys()))
        w.writeheader()
        w.writerows(panel_rows)

    # ---- 落盘 ----
    out = {
        "date": "2026-08-27",
        "etf_sector_map": {k: list(v) for k, v in ETF_SECTOR_MAP.items()},
        "sector_names": SECTOR_NAMES,
        "unmapped_flat_symbols": sorted(
            {t["symbol"] for t in flat} - set(ETF_SECTOR_MAP)),
        "task1": {"arms": arms, "verdicts": task1_verdicts, "winner": winner,
                  "fallback_used_for_task2": None if winner else fallback,
                  "rules": {"expR_mult": VERDICT_EXP_MULT,
                            "n_floor": VERDICT_N_FLOOR}},
        "task2": {
            "streams": {"flat_A": len(a_stream), "sector_A": len(s_stream),
                        "AB_anchor": len(ab_stream)},
            "sector_filter_stats": st,
            "armA_flat": {k: v for k, v in armA.items()
                          if k not in ("curve", "taken", "dropped")},
            "armS_sector": {k: v for k, v in armS.items()
                            if k not in ("curve", "taken", "dropped")},
            "armAB_anchor": {k: v for k, v in armAB.items()
                             if k not in ("curve", "taken", "dropped")},
            "verdict": v,
            "verdict_rules": {"q1": f"阴跌段DD <= {V_SEGD_MAX}%",
                              "q2": f"2026DD <= {V_DD26_MAX}%",
                              "q3": f"终值 >= {V_FINAL_MIN}"},
        },
    }
    (RAW / "sector_layer_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n落盘: {RAW}/")


if __name__ == "__main__":
    main()
