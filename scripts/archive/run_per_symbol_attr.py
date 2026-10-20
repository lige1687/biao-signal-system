"""按标的的完整流程收益归因（用户口径·2026-08-27 第五轮）。

用户最终形态：市场层定仓位 → 单标的预算内 → A/B/C/D 模块信号 →
完整交易流程 → 按标的看收益率贡献（先不做同时段跨标的优选/轮动）。

口径（事前写死）：
- 三种账户配置对照：
  fund_only（无闸）、full_v2（现行五档闸全局）、split_full
  （ETF 腿 h_80 闸 50 万 + 个股腿(B'+C+D) 无闸 50 万，子账户分账）。
- 归因口径 = 组合层 taken 记录按 symbol 求和（已实现 pnl 直接加总，
  不做合约化复利；taken 已含容量竞争与降级，是真实成交口径）。
- 每标的输出：笔数 / 累计 R / 累计 pnl / 胜率 / 平均持仓交易日 /
  模块构成；按 pnl 降序。
- 判定：无（本轮是归因视图不是假设检验）；观察项 = 收益集中度
  （top5 标的 pnl 占比）与闸对各标的的改写方向。

纪律：纯实验脚本；不改 src/configs/web。
输出：docs/experiments/raw/breadth_overlay/per_symbol_attr.csv + JSON
复现：python3 scripts/run_per_symbol_attr.py（约 2 分钟）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import (  # noqa: E402
    load_breadth,
)
from run_full_stack_sim import (  # noqa: E402
    gate_a,
    load_runs,
)

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)
from lei_signal.backtest.portfolio import (  # noqa: E402
    PortfolioConfig,
    simulate_portfolio,
)

RAW = REPO / "docs/experiments/raw/breadth_overlay"


def attr_by_symbol(res: dict, label: str) -> list[dict]:
    rows: dict[str, dict] = {}
    for t in res["taken"]:
        s = rows.setdefault(t["symbol"], {
            "symbol": t["symbol"], "config": label, "module": t.get("pool", ""),
            "n": 0, "cum_R": 0.0, "pnl": 0.0, "wins": 0,
            "hold_days": 0})
        s["n"] += 1
        s["cum_R"] += t["r_net"]
        s["pnl"] += t["pnl"]
        s["wins"] += 1 if t["r_net"] > 0 else 0
        s["hold_days"] += max(
            (pd.Timestamp(t["exit_date"]) - pd.Timestamp(t["entry_date"])).days, 0)
    out = []
    for s in rows.values():
        out.append({**s, "cum_R": round(s["cum_R"], 2),
                    "pnl": round(s["pnl"], 0),
                    "win_rate": round(s["wins"] / s["n"], 3),
                    "avg_hold_d": round(s["hold_days"] / s["n"], 1)})
    return sorted(out, key=lambda r: -r["pnl"])


if __name__ == "__main__":
    import pandas as pd  # noqa: E402

    runs = load_runs(rerun=False)
    a_gated = [{**t, "pool": "A_ETF"} for t in gate_a(runs["A"])]
    b_all = [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
    cd_all = [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]]
    stream_base, _ = dedup_signals(a_gated + b_all)
    stock_stream, _ = dedup_signals(b_all + cd_all)

    br = load_breadth()
    b200_map = {str(d.date()): float(v)
                for d, v in br["ma200_pct"].items()}
    cap_v2 = cap_fn_from_map(position_cap_map(b200_map, TIERS_V2))
    cap_h80 = cap_fn_from_map(position_cap_map(
        b200_map, ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))))

    base_cfg = dict(risk_pct=0.01, max_concurrent=10, pool_concurrent_cap=6,
                    dd_deescalate=True)

    fund = simulate_portfolio(stream_base, PortfolioConfig(**base_cfg))
    full = simulate_portfolio(stream_base,
                              PortfolioConfig(**base_cfg, cap_fn=cap_v2))
    a_leg = simulate_portfolio(
        dedup_signals(a_gated)[0],
        PortfolioConfig(**base_cfg, cap_fn=cap_h80, initial_equity=500_000))
    s_leg = simulate_portfolio(
        stock_stream, PortfolioConfig(**base_cfg, initial_equity=500_000))

    tables = {
        "fund_only": attr_by_symbol(fund, "fund_only"),
        "full_v2": attr_by_symbol(full, "full_v2"),
        "split_A_leg": attr_by_symbol(a_leg, "split_A_leg(h80)"),
        "split_stock_leg": attr_by_symbol(s_leg, "split_stock_leg(nogate)"),
    }
    all_rows = [r for rows in tables.values() for r in rows]
    pd.DataFrame(all_rows).to_csv(RAW / "per_symbol_attr.csv", index=False)

    out = {"date": "2026-08-27",
           "totals": {k: {"final": round(v["final_equity"]),
                          "n_taken": v["n_taken"],
                          "cum_R": v["cum_R_taken"]}
                      for k, v in (("fund", fund), ("full_v2", full))},
           "split_full": {
               "final": round(a_leg["final_equity"] + s_leg["final_equity"]),
               "a_leg_final": round(a_leg["final_equity"]),
               "stock_leg_final": round(s_leg["final_equity"]),
               "cum_R": round(a_leg["cum_R_taken"] + s_leg["cum_R_taken"], 1)},
           "top5_by_config": {k: rows[:5] for k, rows in tables.items()},
           "concentration": {
               k: round(sum(r["pnl"] for r in rows[:5])
                        / max(sum(r["pnl"] for r in rows), 1e-9), 3)
               for k, rows in tables.items()},
           }
    (RAW / "per_symbol_attr.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    for k, rows in tables.items():
        tot = sum(r["pnl"] for r in rows)
        print(f"\n[{k}] 标的数 {len(rows)}，累计 pnl {tot:,.0f}")
        for r in rows[:8]:
            print(f"  {r['symbol']:12s} {r['module']:10s} n={r['n']:3d}"
                  f" R={r['cum_R']:+7.1f} pnl={r['pnl']:>10,.0f}"
                  f" win={r['win_rate']:.0%} hold={r['avg_hold_d']}d")
    print("\n集中度 top5 pnl 占比:", out["concentration"])
