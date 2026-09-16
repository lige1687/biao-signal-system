# -*- coding: utf-8 -*-
"""系统买点后的执行方式对比（第五轮）：一次性 vs 分批 vs 信号后定投窗口。

问题（用户 2026-09-07 提出）：结合系统——系统出一个买点之后，用定投或分批的
方式买入，行不行？

与既有归档的关系（跑前澄清，避免重复已判负机制）：
- AE（staged-entry-precheck-2026-09-03）测的是**宽度引擎**升满仓信号后的分批，
  判「证据不足、方向偏无增量」；
- AM（extreme-bottom-staged-entry-validation-2026-09-03）测的是**极端底部信号**
  后的分批，判「语义九买入侧关闭」；
- 本轮测的是**系统入场模块（A 趋势回调 / B 密集突破）的买点**后怎么执行——
  该问题从未被直接测过。引擎与出场冻结：a6_1_costbasis（结构止损 C + 抵扣价
  出场），fee=standard（单边 5bp），limit_guard=True，rr_min=None，全池默认
  参数（无 overrides），与止损矩阵/ETF 八标的等近期实验同一口径。

预注册判定标准（跑前写死，跑后不得改）：

- 样本：深池（~/.lei_signal_lab/backtest_pool，175 标的）全池、模块 A 与模块 B
  各跑一次引擎，取已平仓交易；剔除 exit_reason=invalid_nonpositive_risk
  （无有效风险、无持仓期的退化笔）。入场信号 T 收盘 → T+1 开盘入场（引擎口径）。
- 执行五臂（每笔预算 1.0，同 fee 模型：每批买入 5bp、出场卖出 5bp）：
  1) one_shot  一次性：入场日开盘全买（= 基线，重算口径）；
  2) staged_3x5  分 3 批，每批间隔 5 根 K 线（跨约 2 周）；
  3) staged_5x10 分 5 批，间隔 10 根（跨约 2 个月）；
  4) dca_20d     信号后定投窗口-日频：20 批、每根 K 线一批（跨约 1 个月）；
  5) dca_8w      信号后定投窗口-周频：8 批、每 5 根一批（跨约 7 周）。
  批次规则（写死）：第 k 批在「入场 K 线位置 + k×间隔」的开盘成交；到达时已
  ≥ 出场 K 线位置的批次**作废（出场优先，剩余批次不投，其现金 0 收益计入期末
  财富）**；A 股标的沿用引擎简化涨跌停规则（该批当日开盘较昨收涨幅 ≥9.5% 视为
  涨停买不进、该批作废）；全部批次作废的笔该臂记缺失。
- 度量（逐笔配对，Δ 均相对同笔 one_shot 重算臂）：
  * ΔPnL% = pnl(variant) − pnl(one_shot)；pnl = 期末财富/预算 − 1，
    期末财富 = 持仓市值（出场价成交、扣卖出费）+ 未投批次现金；
  * VWAP 差 = 已成交批次调和均价 / 一次性入场价 − 1（分批买贵了还是便宜了）；
  * 完成率 = 实际成交批数 / 计划批数；
  * 建仓期缓冲 = 同一评估窗（入场 → 最后一批成交日，含两端）内，
    分批组合（持仓市值 + 未投现金）最深权益 − 一次性组合最深权益
    （正值 = 分批在建仓期亏得浅）。
- 判定线（写死）：
  * E1 收益增量（每模块每臂）：逐笔 ΔPnL% 均值的配对 bootstrap 95% CI
    （B=10000，numpy RandomState(20260907)）下界 > 0 →「收益增量成立」；
    上界 < 0 →「负增量」；跨零 →「无显著差异」。
  * E2 成本方向：VWAP 差均值 CI 上界 < 0 →「分批更便宜」；下界 > 0 →
    「分批更贵」；跨零 → 无差。
  * E3 完成率、E4 建仓期缓冲：登记数字，不设判定线。
  * E5 跨模块一致性：A 与 B 的 E1/E2 方向是否一致，不一致逐条写明。
- 结论级别：只检验不决策。禁止买卖指令类词汇。
- 已知边界：出场信号价格驱动、与建仓方式无关，故 exit_date/exit_price 对五臂
  相同（这是本设计成立的前提，登记）；深池 2020-09 起约 5.5 年，牛熊段均含但
  无 2015/2018 型完整熊市；引擎事件检测器为当前提交版（历史漂移风险沿止损
  矩阵披露）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.backtest.runner import load_pool_frames
from lei_signal.backtest.service import BacktestParams, execute_run

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "docs/experiments/raw/dca-entry-execution-2026-09-07"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FEE = 0.0005                      # 单边 5bp（standard）
MODULES = ("A", "B")
VARIANTS = {
    "one_shot":   dict(n=1, step=0),
    "staged_3x5": dict(n=3, step=5),
    "staged_5x10": dict(n=5, step=10),
    "dca_20d":    dict(n=20, step=1),
    "dca_8w":     dict(n=8, step=5),
}
BOOT_B = 10_000
SEED = 20260907


def is_cn(symbol: str) -> bool:
    return symbol.endswith(".SS") or symbol.endswith(".SZ")


def run_module(module: str, symbols: tuple[str, ...]) -> list[dict]:
    if module == "B":
        # B 冻结口径：breakout + cb30/cl3%（止损矩阵 2026-09-01 同款；默认参数
        # 全池仅个位数笔，不可用）
        res = execute_run(BacktestParams(
            module="B", symbols=symbols, rr_min=None,
            entry_variant="breakout",
            exit_variant="a6_1_costbasis", fee_label="standard",
            limit_guard=True,
            overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03)),
        ))
    else:
        res = execute_run(BacktestParams(
            module=module, symbols=symbols, rr_min=None,
            exit_variant="a6_1_costbasis", fee_label="standard", limit_guard=True,
        ))
    return res["trades"]


def simulate_executions(frame, trade: dict) -> dict | None:
    """对一笔引擎交易重算五臂执行。返回 None 表示该笔不可重放。"""
    idx = frame.index
    dates = {pd.Timestamp(d).date().isoformat(): i for i, d in enumerate(idx)}
    e_pos = dates.get(trade["entry_date"])
    x_pos = dates.get(trade["exit_date"])
    if e_pos is None or x_pos is None or x_pos <= e_pos:
        return None
    opens = frame["open"].to_numpy(float)
    closes = frame["close"].to_numpy(float)
    entry_open = float(trade["entry_price"])
    exit_price = float(trade["exit_price"])
    if not (np.isfinite(entry_open) and entry_open > 0
            and np.isfinite(exit_price) and exit_price > 0):
        return None
    cn = is_cn(trade["symbol"])
    out = {}
    for name, cfg in VARIANTS.items():
        n, step = cfg["n"], cfg["step"]
        fill_pos: list[int] = []
        for k in range(n):
            p = e_pos if step == 0 else e_pos + k * step
            if p >= x_pos or p >= len(idx):
                continue                      # 出场优先，批次作废
            if cn and p >= 1 and opens[p] >= closes[p - 1] * 1.095:
                continue                      # 涨停买不进（引擎简化规则）
            fill_pos.append(p)
        if not fill_pos:
            out[name] = None
            continue
        open_of = {p: (entry_open if step == 0 else float(opens[p]))
                   for p in fill_pos}
        units_total = (1.0 / n) * (1.0 - FEE) * sum(1.0 / open_of[p]
                                                    for p in fill_pos)
        unfilled_cash = (n - len(fill_pos)) / n
        pnl = units_total * exit_price * (1.0 - FEE) + unfilled_cash - 1.0
        vwap = len(fill_pos) / sum(1.0 / open_of[p] for p in fill_pos)
        # 建仓期缓冲（评估窗：入场 → 最后一批成交日）
        last_pos = fill_pos[-1]
        if last_pos > e_pos:
            ones_min = float((((1.0 - FEE) / entry_open)
                              * closes[e_pos:last_pos + 1]).min())
            fills_sorted = sorted(fill_pos)
            staged_min = float("inf")
            cum_units, cum_filled, fi = 0.0, 0, 0
            for pos in range(e_pos, last_pos + 1):
                while fi < len(fills_sorted) and fills_sorted[fi] <= pos:
                    cum_units += (1.0 / n) * (1.0 - FEE) / open_of[fills_sorted[fi]]
                    cum_filled += 1
                    fi += 1
                eq = cum_units * closes[pos] + (n - cum_filled) / n
                staged_min = min(staged_min, eq)
            buffer = staged_min - ones_min
        else:
            buffer = 0.0
        out[name] = {
            "pnl": pnl, "vwap": vwap,
            "completion": len(fill_pos) / n,
            "n_fills": len(fill_pos), "buffer": buffer,
        }
    return out


def bootstrap_ci(deltas: np.ndarray) -> tuple[float, float]:
    rng = np.random.RandomState(SEED)
    n = len(deltas)
    means = np.empty(BOOT_B)
    for b in range(BOOT_B):
        means[b] = deltas[rng.randint(0, n, n)].mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> None:
    frames = load_pool_frames()
    symbols = tuple(sorted(frames))
    out: dict = {"criteria_doc": __doc__, "config": {
        "pool_symbols": len(symbols), "fee": FEE, "variants": VARIANTS,
        "boot_B": BOOT_B, "seed": SEED, "modules": MODULES,
    }, "modules": {}}

    for module in MODULES:
        trades = run_module(module, symbols)
        closed = [t for t in trades
                  if t["exit_date"] and t["exit_reason"] != "invalid_nonpositive_risk"]
        rows = []
        skipped = 0
        for t in closed:
            frame = frames.get(t["symbol"])
            if frame is None:
                skipped += 1
                continue
            sim = simulate_executions(frame, t)
            if sim is None or sim.get("one_shot") is None:
                skipped += 1
                continue
            rows.append(sim)
        n_tr = len(rows)

        rec = {
            "n_engine_trades": len(trades),
            "n_closed_valid": len(closed),
            "n_analyzed": n_tr,
            "n_skipped": skipped,
            "first_entry": min(t["entry_date"] for t in closed),
            "last_exit": max(t["exit_date"] for t in closed),
            "variants": {},
            "per_trade_delta_pnl": {},
        }
        base_pnl = np.array([r["one_shot"]["pnl"] for r in rows])
        for name in VARIANTS:
            if name == "one_shot":
                rec["variants"][name] = {
                    "mean_pnl": float(base_pnl.mean()),
                    "median_pnl": float(np.median(base_pnl)),
                    "win_rate_pnl_pos": float((base_pnl > 0).mean()),
                }
                continue
            pnls = np.array([r[name]["pnl"] if r[name] else np.nan
                             for r in rows], dtype=float)
            ok = ~np.isnan(pnls)
            deltas = pnls[ok] - base_pnl[ok]
            vw = np.array([r[name]["vwap"] / r["one_shot"]["vwap"] - 1.0
                           for r in rows if r[name]], dtype=float)
            comp = np.array([r[name]["completion"] for r in rows if r[name]])
            buf = np.array([r[name]["buffer"] for r in rows if r[name]])
            lo, hi = bootstrap_ci(deltas)
            vlo, vhi = bootstrap_ci(vw)
            e1 = ("收益增量成立" if lo > 0 else
                  "负增量" if hi < 0 else "无显著差异")
            e2 = ("分批更便宜" if vhi < 0 else
                  "分批更贵" if vlo > 0 else "无差")
            rec["variants"][name] = {
                "n": int(ok.sum()),
                "mean_delta_pnl": float(deltas.mean()),
                "median_delta_pnl": float(np.median(deltas)),
                "delta_ci95": [lo, hi],
                "win_rate_delta_pos": float((deltas > 0).mean()),
                "E1_verdict": e1,
                "mean_vwap_diff": float(vw.mean()),
                "vwap_ci95": [vlo, vhi],
                "E2_verdict": e2,
                "mean_completion": float(comp.mean()),
                "mean_buffer": float(buf.mean()),
                "median_buffer": float(np.median(buf)),
                "pct_buffer_positive": float((buf > 0).mean()),
            }
            rec["per_trade_delta_pnl"][name] = [
                round(float(x), 6) for x in deltas
            ]
            # 描述性盈亏切分（不设判定线，仅报告叙述用）
            win_mask = base_pnl[ok] > 0
            rec["variants"][name]["desc_split"] = {
                "mean_delta_on_winning_trades": float(deltas[win_mask].mean()),
                "mean_delta_on_losing_trades": float(deltas[~win_mask].mean()),
                "n_winning": int(win_mask.sum()),
                "n_losing": int((~win_mask).sum()),
            }
        rec["per_trade_base_pnl"] = [round(float(x), 6) for x in base_pnl]
        out["modules"][module] = rec
        print(f"[module {module}] 引擎 {len(trades)} 笔 / 分析 {n_tr} 笔 "
              f"({rec['first_entry']}→{rec['last_exit']})", flush=True)
        st0 = rec["variants"]["one_shot"]
        print(f"  one_shot: mean_pnl={st0['mean_pnl']*100:+.2f}% "
              f"胜率={st0['win_rate_pnl_pos']*100:.0f}%", flush=True)
        for name, st in rec["variants"].items():
            if name == "one_shot":
                continue
            print(f"  {name}: ΔPnL={st['mean_delta_pnl']*100:+.3f}pp "
                  f"CI=[{st['delta_ci95'][0]*100:+.3f},{st['delta_ci95'][1]*100:+.3f}] "
                  f"->{st['E1_verdict']} | VWAP={st['mean_vwap_diff']*100:+.3f}pp "
                  f"({st['E2_verdict']}) | 完成率={st['mean_completion']*100:.0f}% "
                  f"缓冲={st['mean_buffer']*100:+.2f}pp", flush=True)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "dca_entry_execution_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
