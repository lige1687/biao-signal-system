#!/usr/bin/env python3
"""三层串联完整账户模拟器：宽度定闸 × 资金层定重 × 信号层定点（2026-08-27）。

依据 docs/handoff-full-stack-sim-prompt.md；实现
src/lei_signal/backtest/full_sim.py（去重 + 宽度 cap）与 portfolio.cap_fn。

信号口径：A（ETF cm0.5+shrink，门禁=基准非横且 stage>=4）+ B'（个股
cb30/cl3% breakout a6_1）；全模块合并（A 未门禁 + B' + C v3·b15 + D 默认）
仅用于任务一去重对账。宽度 = A 股全市场 B200（周频信号 t+1 生效）。

判定标准（事前写死）：
  考题1（阴跌段）= 串联版 2021-06-18→2024-02-29 段内最大回撤
      <= 0.6 × 去重后无资金约束口径（1%）同段回撤；
  考题2（2026 背离市）= 串联版 2026 年内权益回撤 <= 10%；
  考题3（全期）= 串联版终值 >= 去重后无约束终值 × 0.7。
  三题全过 = 系统完整形态成立。主口径 = V2@B200 档（宽度报告推荐档），
  V1@B200 为敏感性对照（同判定，另披露）。

纪律：不改 configs/web/engine/service；N 累计打折（本轮 0 个新 execute_run，
复用 2026-08-27 已留痕 run JSON，--rerun 可再生成）。
产出：docs/experiments/raw/full_stack/*.json + *.csv
复现：python3 scripts/run_full_stack_sim.py [--rerun]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V1,
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    load_b200_series,
    position_cap_map,
    reconcile,
)
from lei_signal.backtest.portfolio import (  # noqa: E402
    PortfolioConfig,
    simulate_portfolio,
    unconstrained_config,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW = REPO / "docs/experiments/raw/full_stack"
RAW.mkdir(parents=True, exist_ok=True)
BENCHMARK = "000300.SS"
# 阴跌段窗口（宽度样本起点 2021-06-18，晚于 2021-02 峰——半覆盖，标注）
SEG_LO, SEG_HI = "2021-06-18", "2024-02-29"
VERDICT_SEG_RATIO = 0.6
VERDICT_DD26_MAX = 10.0
VERDICT_KEEP_FINAL = 0.7

RUNS = {
    "A": (REPO / "docs/experiments/raw/portfolio/A_ETF_cm05_shrink.json",
          dict(module="A", entry_variant="early", exit_variant="a6_1_costbasis",
               fee_label="standard", limit_guard=True, rr_min=None,
               overrides=(("clock_mult", 0.5),), volume_filter="shrink"),
          "etf"),
    "B'": (REPO / "docs/experiments/raw/portfolio/Bp_stocks_30_3_a61.json",
           dict(module="B", entry_variant="breakout", exit_variant="a6_1_costbasis",
                fee_label="standard", limit_guard=True, rr_min=None,
                volume_filter="none",
                overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03))),
           "stock"),
    "C": (REPO / "docs/experiments/raw/lifecycle_combo/T2_C_stocks_v3_b15.json",
          dict(module="C", entry_variant="v3", exit_variant="a6_1_costbasis",
               fee_label="standard", limit_guard=True, rr_min=None,
               bias_filter=-0.15), "stock"),
    "D": (REPO / "docs/experiments/raw/lifecycle_combo/T2_D_stocks_default.json",
          dict(module="D", entry_variant=None, exit_variant="a6_1_costbasis",
               fee_label="standard", limit_guard=True, rr_min=None), "stock"),
}


def build_pools() -> tuple[list[str], list[str]]:
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


def load_runs(rerun: bool) -> dict[str, list[dict]]:
    stocks, etf_all = build_pools()
    pools = {"stock": tuple(sorted(set(stocks) | {BENCHMARK})),
             "etf": tuple(sorted(set(etf_all) | {BENCHMARK}))}
    out = {}
    for mod, (path, kw, pool_key) in RUNS.items():
        if path.exists() and not rerun:
            r = json.loads(path.read_text(encoding="utf-8"))
        else:
            r = execute_run(BacktestParams(symbols=pools[pool_key], **kw))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(r, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
        trades = [t for t in r["trades"]
                  if t["symbol"] != BENCHMARK and t["exit_date"] is not None]
        for i, t in enumerate(trades):
            t["module"] = mod
            t["seq"] = i
        out[mod] = trades
        print(f"[run] {mod}: {len(trades)} 笔（closed，剔基准）"
              f"{'（缓存）' if path.exists() and not rerun else ''}")
    return out


def gate_a(a_trades: list[dict]) -> list[dict]:
    """A 门禁（已确立规则勿改）：基准非横市且 stage>=4。"""
    return [t for t in a_trades
            if t["benchmark_clock_type"] != 3 and t["trend_stage"] >= 4]


def seg_max_dd(curve: list[dict], lo: str, hi: str) -> float | None:
    """段内最大回撤（%）。峰值种子 = 段前最后一个权益点。"""
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


def slim(res: dict) -> dict:
    return {k: v for k, v in res.items() if k not in ("taken", "dropped")}


def write_monthly_csv(curve: list[dict], breadth: dict[str, float],
                      cap_map: dict[str, float], path: Path) -> None:
    cap_fn = cap_fn_from_map(cap_map)
    last: dict[str, dict] = {}
    for p in curve:
        last[p["date"][:7]] = p
    rows = []
    for m, p in sorted(last.items()):
        month_end = max((d for d in breadth if d[:7] == m), default=None)
        rows.append({
            "month": m, "equity": p["equity"], "cum_R": p["cum_R"],
            "n_open": p["n_open"], "cap_month_end": cap_fn(p["date"]),
            "b200_month_end": round(breadth[month_end], 2) if month_end else "",
        })
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_daily_csv(curve: list[dict], breadth: dict[str, float],
                    cap_map: dict[str, float], path: Path) -> None:
    """宽度-仓位-回撤三线同图数据（事件日粒度）。"""
    peak, rows = -1.0, []
    for p in curve:
        peak = max(peak, p["equity"])
        dd = (1 - p["equity"] / peak) * 100 if peak > 0 else 0.0
        rows.append({"date": p["date"], "b200": round(breadth[p["date"]], 2)
                     if p["date"] in breadth else "",
                     "cap": p.get("cap", 1.0), "equity": p["equity"],
                     "drawdown_pct": round(dd, 3)})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_trade_csvs(res: dict, src_index: dict, path_prefix: Path) -> None:
    """518850 / 510300 全部成交（含仓位与风险预算），join 回源 trades 取价格。"""
    for sym in ("518850.SS", "510300.SS"):
        rows = []
        for t in res["taken"]:
            if t["symbol"] != sym:
                continue
            src = src_index.get((t["symbol"], t["signal_date"],
                                 t["entry_date"], t["exit_date"]), {})
            rows.append({
                "symbol": sym, "module": src.get("module", t["pool"]),
                "signal_date": t["signal_date"], "entry_date": t["entry_date"],
                "entry_price": src.get("entry_price", ""),
                "stop_price": src.get("stop_price", ""),
                "exit_date": t["exit_date"], "exit_price": src.get("exit_price", ""),
                "r_net": t["r_net"], "risk_budget": t["budget"],
                "shares": t["shares"] if t["shares"] is not None else "",
                "deesc_factor": t["factor"], "cap": t["cap"],
                "pnl": t["pnl"], "entry_reason": src.get("entry_reason", ""),
                "exit_reason": src.get("exit_reason", ""),
            })
        out = path_prefix.parent / f"{path_prefix.name}_{sym.split('.')[0]}.csv"
        if rows:
            with out.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        print(f"[csv] {out.name}: {len(rows)} 笔")


def main() -> None:
    rerun = "--rerun" in sys.argv
    runs = load_runs(rerun)
    a_gated = [{**t, "pool": "A_ETF"} for t in gate_a(runs["A"])]
    b_all = [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
    stream_raw = a_gated + b_all
    full_merged = runs["A"] + runs["B'"] + runs["C"] + runs["D"]

    # ---- 任务一：三口径去重对账 ----
    rec_a = reconcile(a_gated, "A 门禁后（ETF cm0.5+shrink）")
    rec_b = reconcile(b_all, "B' 全量（个股 cb30/cl3% breakout a6_1）")
    rec_full = reconcile(full_merged, "全模块合并（A 未门禁 + B' + C + D）")
    task1 = {"A": rec_a, "B'": rec_b, "full": rec_full}
    print("\n===== 任务一：去重前后 R 对账 =====")
    for _k, r in task1.items():
        print(f"[{r['label']}] 前 N={r['before']['n']} cumR={r['before']['cumR']:+.1f}"
              f" → 后 N={r['after']['n']} cumR={r['after']['cumR']:+.1f}"
              f"（水分 {r['water_pct']}% / 2026: {r['r2026_before']:+.1f}"
              f" → {r['r2026_after']:+.1f}）"
              f" 去重构成 {r['dedup_stats']}")

    # ---- 任务二：三层串联 ----
    stream, _ = dedup_signals(stream_raw)
    print(f"\n[串联输入] A门禁+B' 去重后 {len(stream)} 笔 / "
          f"cumR {sum(t['r_net'] for t in stream):+.1f}")

    b200 = load_b200_series()
    cap_map_v1 = position_cap_map(b200, TIERS_V1)
    cap_map_v2 = position_cap_map(b200, TIERS_V2)

    unc = simulate_portfolio(stream, unconstrained_config(0.01))
    fund_only = simulate_portfolio(
        stream, PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                                pool_concurrent_cap=6, dd_deescalate=True))
    full_v1 = simulate_portfolio(
        stream, PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                                pool_concurrent_cap=6, dd_deescalate=True,
                                cap_fn=cap_fn_from_map(cap_map_v1)))
    full_v2 = simulate_portfolio(
        stream, PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                                pool_concurrent_cap=6, dd_deescalate=True,
                                cap_fn=cap_fn_from_map(cap_map_v2)))

    seg_dd = {name: seg_max_dd(r["curve"], SEG_LO, SEG_HI)
              for name, r in (("unc", unc), ("fund", fund_only),
                              ("full_v1", full_v1), ("full_v2", full_v2))}
    dd26 = {name: r["by_year"].get("2026", {}).get("max_drawdown_pct")
            for name, r in (("unc", unc), ("fund", fund_only),
                            ("full_v1", full_v1), ("full_v2", full_v2))}

    def verdict(arm: dict) -> dict:
        return {
            "seg_dd_arm": seg_max_dd(arm["curve"], SEG_LO, SEG_HI),
            "seg_dd_unc": seg_dd["unc"],
            "q1_seg_le_60pct": seg_max_dd(arm["curve"], SEG_LO, SEG_HI)
            <= VERDICT_SEG_RATIO * seg_dd["unc"],
            "q2_dd2026_le_10": dd26 and arm["by_year"].get("2026", {})
            .get("max_drawdown_pct") is not None
            and arm["by_year"]["2026"]["max_drawdown_pct"] <= VERDICT_DD26_MAX,
            "q3_final_ge_70pct": arm["final_equity"]
            >= VERDICT_KEEP_FINAL * unc["final_equity"],
        }

    verdicts = {"full_v2_primary": verdict(full_v2),
                "full_v1_sensitivity": verdict(full_v1)}
    for _k, v in verdicts.items():
        v["all_pass"] = bool(v["q1_seg_le_60pct"] and v["q2_dd2026_le_10"]
                             and v["q3_final_ge_70pct"])

    print("\n===== 任务二：三层串联 vs 对照 =====")
    print(f"无约束@1%（去重后）: 终值 {unc['final_equity']:.0f}"
          f" 全局DD {unc['max_drawdown_pct']}%"
          f" 阴跌段DD {seg_dd['unc']}% 2026DD {dd26['unc']}%")
    for name, r in (("资金层(无cap)", fund_only), ("串联V1@B200", full_v1),
                    ("串联V2@B200", full_v2)):
        print(f"{name:<12} 终值 {r['final_equity']:>12.0f}"
              f" 全局DD {r['max_drawdown_pct']:>6.2f}%"
              f" 阴跌段DD {seg_max_dd(r['curve'], SEG_LO, SEG_HI):>6.2f}%"
              f" 2026DD {r['by_year'].get('2026', {}).get('max_drawdown_pct')}%")
    print(f"判定（主口径 V2）: {verdicts['full_v2_primary']}")
    print(f"判定（敏感 V1）  : {verdicts['full_v1_sensitivity']}")

    # ---- 落盘 ----
    src_index = {(t["symbol"], t.get("signal_date", "")[:10],
                  t["entry_date"], t["exit_date"]): t
                 for t in runs["A"] + runs["B'"]}
    write_monthly_csv(full_v2["curve"], b200, cap_map_v2,
                      RAW / "monthly_position_curve.csv")
    write_daily_csv(full_v2["curve"], b200, cap_map_v2,
                    RAW / "breadth_position_drawdown_daily.csv")
    write_trade_csvs(full_v2, src_index, RAW / "trades_fullsim")

    out = {
        "date": "2026-08-27",
        "data_end": max(t["exit_date"] for t in stream),
        "task1_dedup": task1,
        "task2": {
            "stream_size": len(stream),
            "stream_cumR": round(sum(t["r_net"] for t in stream), 3),
            "unc": slim(unc), "fund_only": slim(fund_only),
            "full_v1": slim(full_v1), "full_v2": slim(full_v2),
            "seg_dd_2021_2024": seg_dd, "dd2026": dd26,
            "verdicts": verdicts,
            "verdict_rules": {
                "q1": f"阴跌段({SEG_LO}~{SEG_HI})串联DD <= {VERDICT_SEG_RATIO}x无约束",
                "q2": f"2026年内DD <= {VERDICT_DD26_MAX}%",
                "q3": f"终值 >= {VERDICT_KEEP_FINAL}x无约束终值",
            },
        },
    }
    (RAW / "full_stack_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n落盘: {RAW}/")


if __name__ == "__main__":
    main()
