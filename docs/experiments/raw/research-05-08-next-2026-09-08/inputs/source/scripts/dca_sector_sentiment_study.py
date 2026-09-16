# -*- coding: utf-8 -*-
"""行业情绪 × 定投（第十九轮）：情绪页 b50 机会位/压力位 + 散户净流入，接进定投买卖。

问题（用户 2026-09-08 提出）：情绪页的「半导体情绪 / 有色情绪」（价格×情绪对照图）
能不能结合定投策略制定买入卖出？具体信号（代码口径，情绪页同源）：

- **b50 情绪强度** = 板块内收盘 > 自身 50 日均线的成分股占比（0~100；
  情绪页阈值：≤20 机会位 / ≥80 压力位，market_mood.py 同线）；
- **散户净流入** = 板块小单净流入 small_yi（亿元，腾讯资金流；
  信号化 = 20 日滚动和的 point-in-time 扩展分位，暖机 250 日）。

数据现实（决定矩阵）：
- 半导体（BK1036）散户流 2022-09-09 即断（154 点）→ **半导体不测流臂**；
- 有色（BK0478）流 2021-08→2026-09 完整（561 点）；
- b50 由逐股日K（2023-01 起）+当前成分回溯合成（含前视偏差，模块自身声明，
  本轮沿用并登记）→ b50 可用窗约 2023-03 起；
- 价格用真实 ETF（512480 半导体 2019-06 起 / 512400 有色 2017-09 起），
  无合成指数前视。

预注册口径（跑前写死，跑后不得改）：

- 主窗 W=2023-03-20→2026-08-24（b50 暖机后首个可用日起，约 3.4 年，
  全臂同窗；**短窗如实登记**——第四轮教训：3 年单段行情易翻案）。
- 引擎沿十六轮骨架：周投（ISO 周末次日开盘执行）、费 10bp 双边、现金 0
  收益、信号日收盘判定次日开盘执行。
- 入场四臂：
  E0 平投（基线）；
  E1 b50 机会位加码：b50≤20 当周投 2 倍，其余同平投；
  E2 散户割肉加码（仅有色）：小单 20 日和 ≤ 扩展 P10 当周投 2 倍；
  E3 埋伏式触发投：b50≤20 触发后 252 根内周投，其余时间不投（门控版）。
- 出场四臂：
  X0 不退出（期末估值）；
  X1 止盈 +50%：市值/累计成本−1 ≥50% 清仓落袋、暂停 126 根后回场继续
  （可循环；对齐十六轮 P1t）；
  X2 b50 压力位清仓：b50≥80 清仓+暂停买入（新钱攒池），b50≤50 回场
  一次性买回（对齐 P1m 精神）；
  X3 散户沸点清仓（仅有色）：20 日和 ≥ 扩展 P90 清仓+暂停，≤P50 回场。
- 判定线（写死）：比较臂 vs 基准臂，"赢" = **资金加权年化（XIRR）更高**
  且回撤不比基准深 2pp 以上（加码臂多花钱、门控臂少花钱，终值不可比，
  XIRR 为资金加权口径）；格子赢率 ≥70% 成立 / ≤30% 判负 / 其余混合
  （占比制：半导体缺散户流臂，绝对格数因标的而异，如实计数）。
- 预注册方向预期（如实登记落空）：P1 b50 加码无效或有害（沿宽度加减码
  判负先例）；P2 散户流加码无效（沿五族情绪判负先例，开放）；P3 触发投
  输平投（沿门控判负先例）；P4 止盈在高波动行业赢不退出（沿十五轮）；
  P5 b50 压力清仓砍牛腿（沿"宽度热出场最差"先例）。
- 结论级别：只检验不决策；禁止买卖指令类词汇。短窗+成分回溯前视双局限，
  结论最高只能到「本窗观察」，不得改写十六轮终局形态。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "docs/experiments/raw/dca-sector-sentiment-2026-09-08"
RAW_DIR.mkdir(parents=True, exist_ok=True)

LAB = Path.home() / ".lei_signal_lab"
KLINE = LAB / "cache" / "a_share_klines.parquet"
MEMBERS = LAB / "cache" / "sector_members.json"
FLOW = LAB / "cache" / "tx_sector_flow_pilot.json"
POOL = LAB / "backtest_pool"

TARGETS = {
    "512480.SS": {"name": "半导体ETF", "board": "BK1036", "flow": False},
    "512400.SS": {"name": "有色ETF", "board": "BK0478", "flow": True},
}
W_MAIN = ("2023-03-20", "2026-08-24")
FLOW_WARMUP = 250
FLOW_SUM = 20
FEE = 10.0
ENTRIES = ("E0", "E1", "E2", "E3")
EXITS = ("X0", "X1", "X2", "X3")


def load_etf(code: str) -> pd.DataFrame:
    df = pd.read_parquet(POOL / f"{code}.bars.parquet")
    return df[["open", "close"]].sort_index()


def b50_series(board: str) -> pd.Series:
    """板块 b50：成分收盘 > 自身 50 日均线的占比（沿 sector_trend 口径）。"""
    mems = json.loads(MEMBERS.read_text())["boards"][board]["members"]
    pq = pd.read_parquet(KLINE, columns=["symbol", "date", "close"])
    pq = pq[pq["symbol"].isin(mems)]
    wide = pq.pivot(index="date", columns="symbol", values="close").sort_index()
    wide.index = pd.to_datetime(wide.index)   # parquet date 为 object，须归一
    valid = wide.notna()
    wff = wide.ffill()
    ma = wff.rolling(50).mean()
    denom = (valid & ma.notna()).sum(axis=1).replace(0, np.nan)
    num = ((wff > ma) & valid & ma.notna()).sum(axis=1)
    return (num / denom * 100.0).dropna()


def flow_series(board: str) -> pd.Series:
    data = json.loads(FLOW.read_text())["boards"][board]
    s = pd.Series({pd.Timestamp(r["date"]): float(r["small_yi"]) for r in data})
    return s.sort_index()


def flow_signal(s: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """20 日和 + point-in-time 扩展分位 P10/P50/P90（暖机 250 日）。

    腾讯流数据约半数交易日缺失（561 点/5 年）：20 日和允许窗内至少 10 个
    有效点（min_periods=10），分位用 nanquantile 忽略缺失——稀疏口径，
    预注册登记（原始口径 roll(20).sum() 因缺日在该数据上永不触发，等于没测）。
    """
    roll = s.rolling(FLOW_SUM, min_periods=10).sum()
    def expanding_pct(x, q):
        return x.expanding(FLOW_WARMUP).apply(
            lambda a: float(np.nanquantile(a, q)), raw=True)
    return roll, expanding_pct(roll, 0.10), expanding_pct(roll, 0.50), expanding_pct(roll, 0.90)


def xirr(flows, end_date, end_value):
    cfs = list(flows) + [(end_date, end_value)]
    t0 = min(d for d, _ in cfs)

    def npv(r):
        return sum(a / (1.0 + r) ** ((d - t0).days / 365.25) for d, a in cfs)

    lo, hi = -0.95, 10.0
    if npv(lo) * npv(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def run(ohlc: pd.DataFrame, b50: pd.Series, fl: dict | None,
        entry: str, exit_: str) -> dict:
    idx = ohlc.index
    n = len(idx)
    o = ohlc["open"].to_numpy(float)
    c = ohlc["close"].to_numpy(float)
    b = ohlc.index.map(b50).to_numpy(float) if b50 is not None else np.full(n, np.nan)
    fr = fp10 = fp50 = fp90 = None
    if fl is not None:
        fr = ohlc.index.map(fl["roll"]).to_numpy(float)
        fp10 = ohlc.index.map(fl["p10"]).to_numpy(float)
        fp50 = ohlc.index.map(fl["p50"]).to_numpy(float)
        fp90 = ohlc.index.map(fl["p90"]).to_numpy(float)
    f = FEE * 1e-4

    s = pd.Series(np.arange(n), index=idx)
    wk = s.groupby([idx.isocalendar().year, idx.isocalendar().week]).max()
    ends = sorted(int(v) for v in wk)
    end_set = set(ends)
    base = 1.0 / len(ends)

    cur = 0.0
    cost = 0.0
    cash = 0.0            # 卖出落袋 + 暂停期新钱（回场一次性买回）
    paused_until = -1     # X1 时间回场
    active = entry != "E3"
    camp_end = -1
    flows = []
    eq = np.empty(n)
    for i in range(n):
        sig = i - 1
        if i > 0 and sig in end_set:
            # 出场检查（收盘判定，次日开盘执行）
            if exit_ != "X0" and cur > 0 and cost > 0:
                hit = False
                if exit_ == "X1" and cur * c[sig] / cost - 1.0 >= 0.50:
                    hit = True
                if exit_ == "X2" and np.isfinite(b[sig]) and b[sig] >= 80:
                    hit = True
                if exit_ == "X3" and fr is not None and np.isfinite(fr[sig]) \
                        and np.isfinite(fp90[sig]) and fr[sig] >= fp90[sig]:
                    hit = True
                if hit:
                    cash += cur * o[i] * (1.0 - f)
                    flows.append((idx[i], cur * o[i] * (1.0 - f)))
                    cur = 0.0
                    cost = 0.0
                    if exit_ == "X1":
                        paused_until = i + 126
            # 回场（X1 时间 / X2 b50≤50 / X3 流≤P50）
            if exit_ in ("X1", "X2", "X3") and cur == 0.0 and cash > 0:
                ok = (exit_ == "X1" and i >= paused_until) or \
                     (exit_ == "X2" and np.isfinite(b[sig]) and b[sig] <= 50) or \
                     (exit_ == "X3" and fr is not None and np.isfinite(fr[sig])
                      and np.isfinite(fp50[sig]) and fr[sig] <= fp50[sig])
                if ok:
                    cur += (cash - cash * f) / o[i]
                    cost += cash
                    flows.append((idx[i], -cash))
                    cash = 0.0
            # 入场乘数与埋伏触发
            mult = 1.0
            if entry == "E1" and np.isfinite(b[sig]) and b[sig] <= 20:
                mult = 2.0
            if entry == "E2" and fr is not None and np.isfinite(fr[sig]) \
                    and np.isfinite(fp10[sig]) and fr[sig] <= fp10[sig]:
                mult = 2.0
            if entry == "E3":
                if not active and np.isfinite(b[sig]) and b[sig] <= 20:
                    active = True
                    camp_end = i + 252
                if active and i > camp_end:
                    active = False
            paused = (exit_ == "X1" and i < paused_until) or \
                     (exit_ in ("X2", "X3") and cur == 0.0 and cash > 0)
            if active and not paused:
                amt = base * mult
                cur += (amt - amt * f) / o[i]
                cost += amt
                flows.append((idx[i], -amt))
        eq[i] = cur * c[i] + cash
    final = float(eq[-1])
    series = pd.Series(eq, index=idx)
    return {"final": final, "xirr": xirr(flows, idx[-1], final),
            "mdd": float(((series / series.cummax()) - 1.0).min()),
            "total_in": len(ends) * base}


def wins(a: dict, b: dict) -> bool:
    """预注册判定：XIRR 更高且回撤不比基准深 2pp 以上。"""
    return a["xirr"] > b["xirr"] and a["mdd"] >= b["mdd"] - 0.02


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "targets": {}, "verdicts": {}}
    cells: dict[str, dict] = {}

    for code, meta in TARGETS.items():
        ohlc = load_etf(code)
        b50 = b50_series(meta["board"])
        # 主窗起点=b50 首个可用日（实测 2023-07 起：成分回溯数据起点晚于名义窗），
        # 预注册口径即"b50 暖机后首个可用日起"，按实测修正并登记。
        w_start = b50.index[0]
        m = (ohlc.index >= w_start) & (ohlc.index <= W_MAIN[1])
        ohlc = ohlc[m]
        fl = None
        sig_cov = {"window_start": str(w_start.date()),
                   "b50_le20_days": int((b50 <= 20).sum()),
                   "b50_ge80_days": int((b50 >= 80).sum())}
        if meta["flow"]:
            roll, p10, p50, p90 = flow_signal(flow_series(meta["board"]))
            fl = {"roll": roll, "p10": p10, "p50": p50, "p90": p90}
            mwin = (roll.index >= w_start) & (roll.index <= W_MAIN[1])
            sig_cov["flow_le_p10_days"] = int(
                ((roll <= p10).to_numpy() & mwin).sum())
            sig_cov["flow_ge_p90_days"] = int(
                ((roll >= p90).to_numpy() & mwin).sum())
        rec: dict[str, dict] = {}
        for e in ENTRIES:
            if e == "E2" and not meta["flow"]:
                continue
            for x in EXITS:
                if x == "X3" and not meta["flow"]:
                    continue
                rec[f"{e}_{x}"] = run(ohlc, b50, fl, e, x)
        cells[code] = rec
        out["targets"][code] = {"name": meta["name"], "board": meta["board"],
                                "window": [str(ohlc.index[0].date()),
                                           str(ohlc.index[-1].date())],
                                "n_days": len(ohlc),
                                "signal_coverage": sig_cov,
                                "cells": rec}
        b0 = rec["E0_X0"]
        print(f"[{meta['name']} {ohlc.index[0].date()}→{ohlc.index[-1].date()} "
              f"{len(ohlc)}日] E0_X0 终值{b0['final']:.3f}/"
              f"年化{b0['xirr']*100:.2f}%/回撤{b0['mdd']*100:.1f}% "
              f"| 信号覆盖 b50≤20:{sig_cov['b50_le20_days']}天 "
              f"b50≥80:{sig_cov['b50_ge80_days']}天"
              + (f" 流≤P10:{sig_cov['flow_le_p10_days']}天 "
                 f"流≥P90:{sig_cov['flow_ge_p90_days']}天" if meta["flow"] else ""),
              flush=True)
        for e in ENTRIES[1:]:
            if e == "E2" and not meta["flow"]:
                continue
            for x in EXITS:
                if x == "X3" and not meta["flow"]:
                    continue
                r = rec[f"{e}_{x}"]
                print(f"  {e}_{x}: 终值{r['final']:.3f}"
                      f"({(r['final']/rec[f'E0_{x}']['final']-1)*100:+.1f}% vs E0同出场)"
                      f" 年化{r['xirr']*100:.2f}% 回撤{r['mdd']*100:.1f}%", flush=True)

    def verdict(arm: str, bmk: str, label: str, vary: str):
        """vary='entry'：在每个出场内比两入场臂；vary='exit'：在每个入场内比两出场臂。"""
        w, detail = 0, {}
        for code, rec in cells.items():
            for other in (EXITS if vary == "entry" else ENTRIES):
                ka = f"{arm}_{other}" if vary == "entry" else f"{other}_{arm}"
                kb = f"{bmk}_{other}" if vary == "entry" else f"{other}_{bmk}"
                if ka not in rec or kb not in rec:
                    continue
                ra, rb = rec[ka], rec[kb]
                win = wins(ra, rb)
                w += win
                detail[f"{code}|{ka}_vs_{kb}"] = {
                    "a_xirr": ra["xirr"], "b_xirr": rb["xirr"],
                    "a_final": ra["final"], "b_final": rb["final"],
                    "a_mdd": ra["mdd"], "b_mdd": rb["mdd"], "win": win}
        total = len(detail)
        share = w / total if total else 0.0
        v = "成立" if share >= 0.70 and total >= 3 else \
            "判负" if share <= 0.30 and total >= 3 else "混合"
        out["verdicts"][label] = {"wins": w, "total": total,
                                  "share": share, "verdict": v, "detail": detail}
        print(f"{label}: {w}/{total} ({share*100:.0f}%) -> {v}", flush=True)

    verdict("E1", "E0", "V1a_b50机会位加码", "entry")
    verdict("E2", "E0", "V1b_散户割肉加码(仅有色)", "entry")
    verdict("E3", "E0", "V1c_b50触发投(门控版)", "entry")
    verdict("X1", "X0", "V2a_止盈50vs不退出", "exit")
    verdict("X2", "X0", "V2b_b50压力位清仓", "exit")
    verdict("X3", "X0", "V2c_散户沸点清仓(仅有色)", "exit")

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "sector_sentiment_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
