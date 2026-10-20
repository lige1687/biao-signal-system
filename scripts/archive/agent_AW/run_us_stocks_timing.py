# -*- coding: utf-8 -*-
"""AW 任务：宽度择时在美股大盘股个股层面的泛化检验（T3 vs 二元+滞回 vs 定投 vs 持有）。

【定位】泛化探针（观察级），不是决策级实验。系统已有结论：A 股宽基域
二元+滞回胜（AU 判"换"），A 股行业 ETF 域三档更稳（AU 扩展面板）；美股指数域
"择时（三档/二元）远输定投"（AJ）。从未测过的是：**个股**。本任务在 12 只
美股大盘股 + 2 只美股 ETF 锚（SPY/QQQ）上，用标普500 成分宽度（b200）跑
同一组引擎，回答"宽度择时的有效性边界是否延伸到个股"。

【幸存者偏差诚实登记（最高优先级）】12 只个股是 2026 年视角挑出的当期
明星大盘股（AAPL/MSFT/NVDA/GOOGL/AMZN/META/TSLA/JPM/JNJ/KO/PG/XOM），
天然偏向长期赢家——**对"这些股票该不该被交易"零证明力**，只用于检验
"引擎在个股级价格动力学上的行为差异"。BH（买入持有）在这组样本上必然
被幸存者偏差抬高，本任务所有"赢 BH"的计数一律不构成推荐。

【口径】
- 宽度：breadth_sp500（b200），与 AJ 美股侧同源；行情×宽度取交集后剔 b200
  为 NaN 的首段。
- 引擎（全部逐字复用认证实现）：T3 冠军三档（43.33/56.67）、BIN_HYST
  （43.33 进 / 45.33 出，AP 带宽 2pp）、DCA 周定投（AJ）、BH 首日全仓。
  T 收盘信号 → T+1 开盘成交，min_trade=0.05。
- 费率：1bp 单边（美股零佣金现实；不跑 10bp——个股结论本就是观察级）。

【度量】每标的四臂：终值/年化/回撤/Calmar/在场/交易数。

【预注册判定线（跑前写死；计数型，输出为观察级结论）】
  14 标的（12 股 + SPY + QQQ）：
  - (G1)「个股层面可泛化」：BIN_HYST Calmar > T3 于 ≥8/14 且
        BIN_HYST 终值 > DCA 于 ≥8/14。
  - (G2)「个股层面择时无优势」：BH Calmar ≥ max(T3, BIN_HYST) 于 ≥8/14
        且 (T3 或 BIN_HYST 任一) 终值 < DCA 于 ≥8/14。
  - 其余 = 「混合」。
  SPY/QQQ 两行单独与 AJ 美股侧结论对照（应同向：择时输定投），不一致
  时如实登记不调和。

【红线遵守】不产生买卖规则；不改生产代码/缓存/既有归档；产出全为新增。
双跑哈希 PYTHONHASHSEED=0/42 逐位一致。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AJ"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AP"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    align_index_breadth, load_breadth, load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target  # noqa: E402
from run_robustness import cagr_maxdd, run_dca  # noqa: E402
from run_hysteresis import hysteresis_target  # noqa: E402

RAW_DIR = REPO / "docs/experiments/raw/agent_AW-us-stocks-timing"
RAW_DIR.mkdir(parents=True, exist_ok=True)

STOCKS = [
    "US_AAPL", "US_MSFT", "US_NVDA", "US_GOOGL", "US_AMZN", "US_META",
    "US_TSLA", "US_JPM", "US_JNJ", "US_KO", "US_PG", "US_XOM",
]
ANCHORS = ["SPY", "QQQ"]
FEE = 1.0
ENTRY = 100.0 / 3.0 * 1.3
BAND = 2.0
T3_PARAMS = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)


def load_us_aligned(symbol: str) -> pd.DataFrame:
    bars = load_index_bars(symbol)
    breadth = load_breadth("sp500")
    aligned = align_index_breadth(bars, breadth)
    return aligned[aligned["b200"].notna()]


def run_signal(aligned: pd.DataFrame, target, fee_bps: float) -> dict:
    res = simulate(aligned, target, fee_bps=fee_bps, min_trade=0.05)
    cagr, mdd, calmar = cagr_maxdd(res.daily["equity"])
    return {"final": float(res.daily["equity"].iloc[-1]), "cagr": cagr,
            "mdd": mdd, "calmar": calmar, "n_trades": len(res.trades),
            "time_in_market": float((res.daily["weight"] > 0).mean())}


def run_bh(aligned: pd.DataFrame, fee_bps: float) -> dict:
    opens = aligned["open"].to_numpy(float)
    closes = aligned["close"].to_numpy(float)
    units = (1.0 - fee_bps * 1e-4) / opens[0]
    eq = pd.Series(units * closes, index=aligned.index)
    eq.iloc[0] = 1.0
    cagr, mdd, calmar = cagr_maxdd(eq)
    return {"final": float(eq.iloc[-1]), "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "n_trades": 1, "time_in_market": 1.0}


def main() -> None:
    out: dict = {"criteria_doc": __doc__,
                 "config": {"stocks": STOCKS, "anchors": ANCHORS, "fee": FEE}}
    rows = []
    for sym in STOCKS + ANCHORS:
        aligned = load_us_aligned(sym)
        rec = {
            "start": str(aligned.index[0].date()),
            "end": str(aligned.index[-1].date()),
            "n_days": len(aligned),
            "T3": run_signal(aligned, ladder_target(aligned["b200"], T3_PARAMS), FEE),
            "BIN_HYST": run_signal(
                aligned, hysteresis_target(aligned["b200"], ENTRY, BAND), FEE),
            "DCA": run_dca(aligned, FEE),
            "BH": run_bh(aligned, FEE),
        }
        out[sym] = rec
        rows.append(sym)
        print(f"[{sym}] {rec['start']}→{rec['end']} done", flush=True)

    n = len(rows)
    g1a = sum(1 for s in rows if out[s]["BIN_HYST"]["calmar"] > out[s]["T3"]["calmar"])
    g1b = sum(1 for s in rows if out[s]["BIN_HYST"]["final"] > out[s]["DCA"]["final"])
    g2a = sum(
        1 for s in rows
        if out[s]["BH"]["calmar"] >= max(out[s]["T3"]["calmar"],
                                         out[s]["BIN_HYST"]["calmar"]))
    g2b = sum(
        1 for s in rows
        if out[s]["T3"]["final"] < out[s]["DCA"]["final"]
        or out[s]["BIN_HYST"]["final"] < out[s]["DCA"]["final"])
    out["verdict_inputs"] = {
        "n": n, "G1_bin_calmar_beats_t3": g1a,
        "G1_bin_final_beats_dca": g1b,
        "G2_bh_calmar_top": g2a, "G2_either_engine_loses_dca": g2b,
    }
    if g1a >= 8 and g1b >= 8:
        verdict = "个股层面可泛化（观察级）"
    elif g2a >= 8 and g2b >= 8:
        verdict = "个股层面择时无优势（观察级）"
    else:
        verdict = "混合"
    out["verdict"] = verdict

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "us_stocks_timing_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"\nG1: BIN Calmar胜T3 {g1a}/{n}, BIN终值胜DCA {g1b}/{n}")
    print(f"G2: BH Calmar最高 {g2a}/{n}, 引擎输DCA {g2b}/{n}")
    print(f"=== 判定：{verdict} ===")
    print(f"sha256(canonical) = {h}")


if __name__ == "__main__":
    main()
