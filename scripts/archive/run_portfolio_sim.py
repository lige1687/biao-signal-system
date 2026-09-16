#!/usr/bin/env python3
"""资金层组合模拟实验（docs/handoff-portfolio-layer-prompt.md，2026-08-27）。

背景：stage-b200 报告 §6——2026 年 A·ETF 池失血 ~80R，62 个事前信号过滤器
无解，止血必须到仓位层。本脚本把「已确立的可执行信号规则」产生的信号流
（A·ETF 池：cm0.5+shrink+门禁[基准非横市 且 trend_stage>=4]；B'·个股池：
cb30/cl3% breakout，a6_1 主口径 + b3_dual 对照口径）重放到有资金约束的
账户曲线上（src/lei_signal/backtest/portfolio.py，手册 6.3 规则）。

对照实验：无约束 R 累计（现状，资金化对照）vs 三档 risk_pct(0.5/1/2%) ×
三档 N_max(5/10/20) × 三档同池上限(3/6/不限)，另做消融（只降级 / 只并发上限）。

判定标准（事前写死）：
  资金层有效 = 2026 段权益最大回撤 <= 0.5 × 同 risk_pct 无约束的 2026 回撤
              且 全期终值 >= 0.7 × 无约束终值。
  （无约束 2026 回撤为 0 时视为无法判定，不判有效。）

纪律：不改 engine/service（模拟器为独立新模块）；基准 000300.SS 入池仅取
时钟、自身交易剔除；结论只到「建议」级；N 累计叠加，多重比较折扣适用。
产出：docs/experiments/raw/portfolio/*.json（run 留痕 + 矩阵 + 月度曲线）。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.backtest.portfolio import (  # noqa: E402
    PortfolioConfig,
    simulate_portfolio,
    unconstrained_config,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW = REPO / "docs/experiments/raw/portfolio"
RAW.mkdir(parents=True, exist_ok=True)

BENCHMARK = "000300.SS"
RISK_LEVELS = (0.005, 0.01, 0.02)
NMAX_LEVELS = (5, 10, 20)
POOLCAP_LEVELS = (3, 6, None)
BASE = {"risk_pct": 0.01, "max_concurrent": 10, "pool_concurrent_cap": 6}
YEAR_FOCUS = "2026"


def build_pools() -> tuple[list[str], list[str]]:
    """池口径与 run_stage_b200.py 完全一致（ETF 全池 + 个股池文件）。"""
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
          f" {r['wall_seconds']}s 数据截至 {r['data_range']['end']}")
    return r


def gate_stream(a_run: dict, bp_run: dict) -> list[dict]:
    """已确立可执行信号规则（勿改）：A 门禁=基准非横市且 stage>=4；B' 全量。"""
    a_gated = [
        {**t, "pool": "A_ETF"}
        for t in a_run["trades"]
        if t["exit_date"] is not None
        and t["benchmark_clock_type"] != 3
        and t["trend_stage"] >= 4
    ]
    b_all = [
        {**t, "pool": "B_STOCK"}
        for t in bp_run["trades"] if t["exit_date"] is not None
    ]
    stream = a_gated + b_all
    print(f"[gate] A 门禁后 {len(a_gated)} 笔（门禁前 {len(a_run['trades'])}）"
          f" + B' 全量 {len(b_all)} 笔 = {len(stream)} 信号")
    return stream


def slim(result: dict) -> dict:
    """矩阵行：去掉 curve/taken/dropped 明细，保留判定与统计字段。"""
    return {k: v for k, v in result.items() if k not in ("curve", "taken", "dropped")}


def verdict_vs_unconstrained(arm: dict, unc: dict) -> dict:
    dd26 = arm["by_year"].get(YEAR_FOCUS, {}).get("max_drawdown_pct")
    dd26u = unc["by_year"].get(YEAR_FOCUS, {}).get("max_drawdown_pct")
    dd_ok = None
    if dd26u is not None and dd26u > 0 and dd26 is not None:
        dd_ok = dd26 <= 0.5 * dd26u
    keep_ok = arm["final_equity"] >= 0.7 * unc["final_equity"]
    return {
        "dd_2026_arm": dd26, "dd_2026_uncon": dd26u,
        "dd_halved": dd_ok, "final_keep_70pct": keep_ok,
        "effective": bool(dd_ok and keep_ok),
    }


def monthly_curve(result: dict, year: str | None = None) -> list[dict]:
    """月末权益/R（year=None 全期）。年初首个点带种子值。"""
    pts = result["curve"]
    if year is not None:
        seed_eq = next((p["equity"] for p in reversed(pts)
                        if p["date"] < f"{year}-01-01"), None)
        pts = [p for p in pts if p["date"][:4] == year]
        if seed_eq is not None and pts:
            pts = [{"date": f"{year}-01-01", "equity": seed_eq, "cum_R": None,
                    "n_open": 0}] + pts
    out: dict[str, dict] = {}
    for p in pts:
        out[p["date"][:7]] = p
    return [{"month": m, "equity": p["equity"], "cum_R": p["cum_R"],
             "n_open": p["n_open"]} for m, p in sorted(out.items())]


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
    bp_runs = {}
    for tag, exit_variant in (("a61", "a6_1_costbasis"), ("b3", "b3_dual")):
        bp_runs[tag] = run_and_save(
            f"Bp_stocks_30_3_{tag}",
            BacktestParams(
                module="B", symbols=tuple(sorted(set(stocks) | {BENCHMARK})),
                rr_min=None, entry_variant="breakout", exit_variant=exit_variant,
                fee_label="standard", limit_guard=True,
                overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03)),
                volume_filter="none"))

    matrix_out = {}
    for tag in ("a61", "b3"):
        stream = gate_stream(a_run, bp_runs[tag])
        cum_r_raw = sum(t["r_net"] for t in stream)
        unc_by_risk = {}
        for risk in RISK_LEVELS:
            res = simulate_portfolio(stream, unconstrained_config(risk))
            unc_by_risk[risk] = res
        arms = []
        for risk in RISK_LEVELS:
            for nmax in NMAX_LEVELS:
                for pcap in POOLCAP_LEVELS:
                    cfg = PortfolioConfig(
                        risk_pct=risk, max_concurrent=nmax,
                        pool_concurrent_cap=pcap, dd_deescalate=True)
                    res = simulate_portfolio(stream, cfg)
                    arms.append({
                        "risk_pct": risk, "max_concurrent": nmax,
                        "pool_concurrent_cap": pcap,
                        "result": slim(res),
                        "verdict": verdict_vs_unconstrained(
                            res, unc_by_risk[risk]),
                    })
        # 消融（基准档 1%/10/池6）：分解「回撤降级」与「并发上限」各自贡献
        ablation = {}
        for name, cfg in {
            "full_降级+并发": PortfolioConfig(**BASE),
            "only_降级": PortfolioConfig(
                risk_pct=0.01, max_concurrent=None, pool_concurrent_cap=None,
                dd_deescalate=True),
            "only_并发": PortfolioConfig(
                risk_pct=0.01, max_concurrent=10, pool_concurrent_cap=6,
                dd_deescalate=False),
        }.items():
            res = simulate_portfolio(stream, cfg)
            ablation[name] = {"result": slim(res), "verdict":
                              verdict_vs_unconstrained(res, unc_by_risk[0.01])}

        matrix_out[f"Bp_{tag}"] = {
            "stream_size": len(stream),
            "stream_cum_R": round(cum_r_raw, 3),
            "unconstrained": {str(r): slim(res) for r, res in unc_by_risk.items()},
            "matrix": arms,
            "ablation_1pct_10_6": ablation,
            "monthly_2026": {
                "base": monthly_curve(simulate_portfolio(
                    stream, PortfolioConfig(**BASE)), YEAR_FOCUS),
                "unconstrained": monthly_curve(unc_by_risk[0.01], YEAR_FOCUS),
            },
        }

        print(f"\n===== B' 退出={tag}（信号 {len(stream)} 笔 / R 累计 "
              f"{cum_r_raw:+.1f}）=====")
        unc1 = unc_by_risk[0.01]
        print(f"无约束@1%: 终值 {unc1['final_equity']:.0f} "
              f"({unc1['total_return_pct']:+.1f}%) "
              f"2026DD {unc1['by_year'].get(YEAR_FOCUS, {}).get('max_drawdown_pct')}%")
        for a in arms:
            if a["risk_pct"] != 0.01:
                continue
            r, v = a["result"], a["verdict"]
            lost_r = sum(x["forfeited_R"] for x in r["dropped_by_reason"].values())
            print(f"N{a['max_concurrent']:<3} 池{str(a['pool_concurrent_cap']):<4}"
                  f" 终值 {r['final_equity']:>12.0f} ({r['total_return_pct']:>+7.1f}%)"
                  f" 全局DD {r['max_drawdown_pct']:>6.2f}%"
                  f" 2026DD {str(v['dd_2026_arm']):>7}%"
                  f" 丢 {r['n_dropped']:>3} 笔(让R {lost_r:>+7.1f})"
                  f" 利用率 {str(r['concurrency']['avg_utilization']):>6}"
                  f" => {'有效' if v['effective'] else '×'}")
        for name, ab in ablation.items():
            r, v = ab["result"], ab["verdict"]
            print(f"[消融] {name:<12} 终值 {r['final_equity']:>12.0f}"
                  f" 2026DD {str(v['dd_2026_arm']):>7}%"
                  f" 减半 {'√' if v['dd_halved'] else '×'}"
                  f" 保终值 {'√' if v['final_keep_70pct'] else '×'}")

    out = {"date": "2026-08-27",
           "handoff": "docs/handoff-portfolio-layer-prompt.md",
           "data_end": a_run["data_range"]["end"],
           "risk_levels": RISK_LEVELS, "nmax_levels": NMAX_LEVELS,
           "poolcap_levels": [str(x) for x in POOLCAP_LEVELS],
           **matrix_out}
    (RAW / "portfolio_matrix.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"\n落盘: {RAW}/portfolio_matrix.json")


if __name__ == "__main__":
    main()
