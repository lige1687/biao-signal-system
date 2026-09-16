"""指数全模块成绩单：A+B'+C+D 在宽基指数上的拼合（2026-08-27 第十轮）。

用户口径（事前写死）：
- 标的 = 指数（用户明确）：A 股 6 只宽基 ETF + 美股 ^GSPC/^IXIC。
  黄金移除（用户拍板，与策略不符）。
- 模块 = 全家桶拼合（用户心智：一个标的上哪个形态出现走哪个模块）：
  A = 主引擎口径（门禁：基准非横+stage>=4，已缓存 run 提取）；
  B' = breakout cb30/cl3% + a6_1；C = v3 b15 + a6_1；D = default + a6_1
  （参数与 full_stack RUNS 完全一致，B/C/D 无门禁，标的内去重叠）。
- 仓位层 = 指数腿上闸：A 股 ETF 用全 A B200 五档(h_80)；美股用 SP500
  B200 五档(h_80)。
- 对照 = 同窗买入持有；指标：笔数/累计R/分模块 R/年化@1%@5%/回撤。
- 判定：无（成绩单）。新增 execute_run 6 个（B/C/D × 两市场，N 账本
  +6），JSON 落盘 raw/breadth_overlay/。
- 声明：B'/C/D 参数为个股池标定值，用于指数属跨口径移植（方向探索，
  不作转正依据）；美股 ^IXIC 门禁基准 = ^GSPC 时钟（引擎市场映射）。

复现：python3 scripts/run_index_abcd_card.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_full_stack_sim import gate_a, load_runs  # noqa: E402
from run_symbol_showcase import (  # noqa: E402
    cagr_dd,
    sim_bh,
    sim_strat,
    strat_trades,
)

from lei_signal.backtest.full_sim import (  # noqa: E402
    cap_fn_from_map,
    position_cap_map,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
H80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))
CN_IDX = ["510300.SS", "159915.SZ", "510050.SS", "510500.SS",
          "512100.SS", "159901.SZ"]
US_IDX = ["^GSPC", "^IXIC"]


def run_or_cache(name: str, symbols, kw: dict, module: str) -> list[dict]:
    path = RAW / f"{name}.json"
    if path.exists():
        r = json.loads(path.read_text())
    else:
        r = execute_run(BacktestParams(symbols=symbols, **kw))
        path.write_text(json.dumps(r, ensure_ascii=False,
                                   separators=(",", ":")))
    return [{**t, "module": module}
            for t in r["trades"] if t["exit_date"] is not None]


KW_B = dict(module="B", entry_variant="breakout",
            exit_variant="a6_1_costbasis", fee_label="standard",
            limit_guard=True, rr_min=None, volume_filter="none",
            overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03)))
KW_C = dict(module="C", entry_variant="v3", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True, rr_min=None,
            bias_filter=-0.15)
KW_D = dict(module="D", entry_variant=None, exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True, rr_min=None)


def main() -> None:
    frames = load_pool_frames()
    # ---- A 股：A 从已缓存全池 run 提取；B/C/D 新跑 ----
    cn_runs = load_runs(rerun=False)
    cn_runs["B'"] = run_or_cache("Bp_cn_indices", CN_IDX, KW_B, "B'")
    cn_runs["C"] = run_or_cache("C_cn_indices", CN_IDX, KW_C, "C")
    cn_runs["D"] = run_or_cache("D_cn_indices", CN_IDX, KW_D, "D")
    br = pd.DataFrame(
        json.loads((Path.home() /
                    ".lei_signal_lab/cache/a_share_ma_breadth_history.json"
                    ).read_text()))
    br["date"] = pd.to_datetime(br["date"])
    br = br.set_index("date").sort_index()
    b200 = {str(d.date()): float(v)
            for d, v in br["ma200_pct"].items()}
    cap_cn = cap_fn_from_map(position_cap_map(b200, H80))

    # ---- 美股：A 已缓存；B/C/D 新跑 ----
    us_a = json.loads((RAW / "A_us_indices.json").read_text())
    us_runs = {"A": [{**t, "module": "A"} for t in gate_a(
        [t for t in us_a["trades"] if t["exit_date"] is not None])],
               "B'": run_or_cache("Bp_us_indices", US_IDX, KW_B, "B'"),
               "C": run_or_cache("C_us_indices", US_IDX, KW_C, "C"),
               "D": run_or_cache("D_us_indices", US_IDX, KW_D, "D")}
    us_br = pd.read_parquet(
        Path.home() / ".lei_signal_lab/cache/timing/breadth_sp500.parquet")
    us_br.index = pd.to_datetime(us_br.index).tz_localize(None).normalize()
    us_b200 = {str(d.date()): float(v)
               for d, v in us_br["b200"].items()}
    cap_us = cap_fn_from_map(position_cap_map(us_b200, H80))

    for label, syms, runs, cap in (("A股宽基", CN_IDX, cn_runs, cap_cn),
                                   ("美股指数", US_IDX, us_runs, cap_us)):
        print(f"\n===== {label}（全模块拼合）=====")
        for sym in syms:
            bars = frames[sym]
            tr = strat_trades(runs, sym)
            smap = {str(d.date()): min(1.0, cap(str(d.date())))
                    for d in bars.index}
            m1, n, cum_r = sim_strat(bars, tr, smap)
            m5, *_ = sim_strat(bars, tr, smap, risk=0.05)
            bh = cagr_dd(sim_bh(bars))
            a, b5 = cagr_dd(m1), cagr_dd(m5)
            by_mod = {}
            for t in tr:
                r_ = by_mod.setdefault(t["module"], [0, 0.0])
                r_[0] += 1
                r_[1] += t["r_net"]
            mods = " ".join(f"{k}:{v[0]}笔{v[1]:+.1f}R"
                            for k, v in sorted(by_mod.items()))
            print(f"[{sym:11s}] {n}笔 累计R {cum_r:+6.1f} | {mods}")
            print(f"    年化@1% {a['cagr']:+.1%} 回撤{a['max_dd']:.1%}"
                  f" | @5% {b5['cagr']:+.1%} 回撤{b5['max_dd']:.1%}"
                  f" | 持有 {bh['cagr']:+.1%}/{bh['max_dd']:.1%}")


if __name__ == "__main__":
    main()
