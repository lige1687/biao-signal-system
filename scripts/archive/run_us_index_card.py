"""美股指数跑 A 模块 + 单标的成绩单（2026-08-27 第九轮）。

用户口径：只看指数（沪深/创业板/美股），黄金彻底移出（与策略不符，
用户拍板）。本轮补美股：^GSPC / ^IXIC（池内十年 OHLCV）。

口径（事前写死）：
- 信号 = A 模块主引擎口径（early 入场 / a6_1 退出 / standard 费用 /
  clock_mult 0.5 / shrink 缩量确认 / limit_guard），标的 = ^GSPC、^IXIC，
  基准时钟自动取 us→^GSPC（引擎 BENCHMARK_BY_MARKET 现成支持）。
- 门禁 = 基准非横盘且 stage>=4（gate_a 同款，但基准为美股时钟）。
- 仓位层 = SP500 宽度 B200 五档(h_80) 调入场预算（美股指数=指数腿，
  上闸；黄金逻辑不适用，已移除）。
- 对照 = 同窗买入持有；指标同成绩单（R / 年化@1%@5% / 回撤）。
- 判定：无（成绩单展示）。新增 1 个 execute_run（美股 A，N 账本 +1），
  结果 JSON 落盘 raw/breadth_overlay/A_us_indices.json。
- 声明：美股宽度 B200 为 SP500 今日成分回算（幸存者偏差向上）；
  池内仅十年（2016-08→2026-08），样本短于 A 股口径。

复现：python3 scripts/run_us_index_card.py（首次生成 run JSON 后秒级）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_full_stack_sim import gate_a  # noqa: E402
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
RUN_JSON = RAW / "A_us_indices.json"
H80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))
SYMBOLS = ["^GSPC", "^IXIC"]


def main() -> None:
    if RUN_JSON.exists():
        r = json.loads(RUN_JSON.read_text())
    else:
        r = execute_run(BacktestParams(
            symbols=SYMBOLS, module="A", entry_variant="early",
            exit_variant="a6_1_costbasis", fee_label="standard",
            limit_guard=True, rr_min=None,
            overrides=(("clock_mult", 0.5),), volume_filter="shrink"))
        RUN_JSON.write_text(json.dumps(r, ensure_ascii=False,
                                       separators=(",", ":")))
    trades = [t for t in r["trades"] if t["exit_date"] is not None]
    print(f"[run] 美股 A：{len(trades)} 笔（closed）")

    us_br = pd.read_parquet(
        Path.home() / ".lei_signal_lab/cache/timing/breadth_sp500.parquet")
    us_br.index = pd.to_datetime(us_br.index).tz_localize(None).normalize()
    b200 = {str(d.date()): float(v)
            for d, v in us_br["b200"].items()}
    cap_h80 = cap_fn_from_map(position_cap_map(b200, H80))

    frames = load_pool_frames()
    gated = gate_a(trades)
    runs = {"A": [{**t, "module": "A"} for t in gated],
            "B'": [], "C": [], "D": []}
    for sym in SYMBOLS:
        bars = frames[sym]
        tr = strat_trades(runs, sym)
        smap = {str(d.date()): min(1.0, cap_h80(str(d.date())))
                for d in bars.index}
        m1, n, cum_r = sim_strat(bars, tr, smap)
        m5, *_ = sim_strat(bars, tr, smap, risk=0.05)
        bh = cagr_dd(sim_bh(bars))
        a, b5, c = cagr_dd(m1), cagr_dd(m5), bh
        wins = sum(1 for t in tr if t["r_net"] > 0)
        print(f"\n[{sym}]  {bars.index[0].date()}→{bars.index[-1].date()}"
              f"（{(bars.index[-1]-bars.index[0]).days/365.25:.1f} 年）"
              f"  门禁后 {len(tr)} 笔 / 累计R {cum_r:+.1f}"
              f"（胜率 {wins/len(tr):.0%}）" if tr else f"\n[{sym}] 无信号")
        print(f"  策略@1%  年化 {a['cagr']:+.1%}  回撤 {a['max_dd']:.1%}")
        print(f"  策略@5%  年化 {b5['cagr']:+.1%}  回撤 {b5['max_dd']:.1%}")
        print(f"  买入持有 年化 {c['cagr']:+.1%}  回撤 {c['max_dd']:.1%}")


if __name__ == "__main__":
    main()
