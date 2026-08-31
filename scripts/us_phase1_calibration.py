"""美股专项 Phase 1：分层抽样 + 四参数网格三窗校准。

协议：docs/timing-sweep/us_calibration_protocol.md。

前置：backtest_pool_us/ 已有 OHLCV（fetch_us_pool.py）+ us_qfq_matrix.parquet。
分层（协议修订案：无离线市值数据，改为 历史长度三分 × 波动三分 = 9 格各抽 13 只，
等价服务"防单一风格偏差"目标）：9×13=117 只，种子 42 确定性抽样。
网格（预注册）：模块 A(early)/B(ambush)/B(breakout)/C(v1)/D × RR{无,2,3,5} ×
退出{a6_1,a6_2,结构止损,b3_dual} × 宽度过滤{关, 只做低+中区(B200<56.7)}。
清洗：风险距离<10bp 剔除。三窗：全窗/前半(入场<2013-01)/后半 + 2020/2022 压力窗。
通过线：三窗期望R>0 且 PF≥1.3。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from lei_signal.backtest.service import BacktestParams, execute_run
from lei_signal.timing_backtest.data import load_breadth

POOL = Path.home() / ".lei_signal_lab/backtest_pool_us"
MATRIX = Path.home() / ".lei_signal_lab/cache/us_qfq_matrix.parquet"
GRID_RR = [None, 2.0, 3.0, 5.0]
GRID_EXIT = ["a6_1_costbasis", "a6_2_top_plus_keywave", "a6_3_structure_stop", "b3_dual"]
MODULES = [("A", "early"), ("B", "ambush"), ("B", "breakout"), ("C", "v1"), ("D", None)]


def stratified_sample() -> list[str]:
    wide = pd.read_parquet(MATRIX)
    have = {p.name[: -len(".bars.parquet")] for p in POOL.glob("*.bars.parquet")}
    cols = [c for c in wide.columns if c in have]
    df = wide[cols]
    hist = df.notna().sum()
    vol = df.pct_change(fill_method=None).std() * np.sqrt(252)
    q_hist = pd.qcut(hist.rank(method="first"), 3, labels=["h1", "h2", "h3"])
    q_vol = pd.qcut(vol.rank(method="first"), 3, labels=["v1", "v2", "v3"])
    rng = np.random.default_rng(42)
    picked: list[str] = []
    for hh in ("h1", "h2", "h3"):
        for vv in ("v1", "v2", "v3"):
            cell = [c for c in cols if q_hist[c] == hh and q_vol[c] == vv]
            picked += list(rng.choice(cell, size=min(13, len(cell)), replace=False))
    return sorted(picked)


def stats(trades: list[dict]) -> tuple:
    if not trades:
        return 0, float("nan"), float("nan")
    wins = [t for t in trades if (t.get("r_net") or 0) > 0]
    tot = sum(t.get("r_net") or 0 for t in trades)
    pf_num = sum(t["r_net"] for t in wins)
    pf_den = -sum(t["r_net"] for t in trades if (t.get("r_net") or 0) < 0)
    pf = pf_num / pf_den if pf_den > 0 else float("inf")
    return len(trades), tot / len(trades), pf


def main() -> int:
    if not any(POOL.glob("*.bars.parquet")):
        print("美股校准池为空：先跑 scripts/fetch_us_pool.py")
        return 1
    sample = stratified_sample()
    n_pool = len(list(POOL.glob("*.bars.parquet")))
    print(f"分层样本 {len(sample)} 只（池 {n_pool} 只）")
    b200 = load_breadth("sp500")["b200"]

    def zone_ok(d: str) -> bool:
        try:
            v = b200.asof(pd.Timestamp(d))
        except KeyError:
            return True
        return bool(pd.notna(v)) and v < 56.7

    results = []
    for module, variant in MODULES:
        for rr in GRID_RR:
            for exit_v in GRID_EXIT:
                res = execute_run(BacktestParams(
                    symbols=tuple(sample), module=module, rr_min=rr,
                    entry_variant=variant, exit_variant=exit_v,
                    fee_label="standard", limit_guard=False,
                ))
                trades = [
                    t for t in res["trades"]
                    if t["entry_price"] and t["stop_price"]
                    and (t["entry_price"] - t["stop_price"]) / t["entry_price"] >= 0.001
                ]
                for zone_filter in (False, True):
                    ts = [t for t in trades if (not zone_filter) or zone_ok(t["entry_date"])]
                    h1 = [t for t in ts if t["entry_date"] < "2013-01-01"]
                    h2 = [t for t in ts if t["entry_date"] >= "2013-01-01"]
                    w2020 = [t for t in ts if "2020-02-01" <= t["entry_date"] <= "2020-06-30"]
                    w2022 = [t for t in ts if "2022-01-01" <= t["entry_date"] <= "2022-12-31"]
                    n, exp_r, pf = stats(ts)
                    n1, e1, _ = stats(h1)
                    n2, e2, _ = stats(h2)
                    _, e20, _ = stats(w2020)
                    _, e22, _ = stats(w2022)
                    passed = (
                        n >= 100 and exp_r > 0 and e1 > 0 and e2 > 0 and pf >= 1.3
                    )
                    results.append(dict(
                        module=f"{module}·{variant}" if variant else module,
                        rr="无" if rr is None else f"{rr:g}", exit_v=exit_v,
                        zone="低+中" if zone_filter else "关",
                        n=n, exp_r=exp_r, pf=pf, e1=e1, e2=e2,
                        e2020=e20, e2022=e22, passed=passed,
                    ))
        df = pd.DataFrame(results)
        print(f"\n[{module}] 网格累计 {len(df)} 组，当前通过 {int(df['passed'].sum())} 组")
    df = pd.DataFrame(results)
    out = Path(__file__).parents[1] / "docs/timing-sweep/us_phase1_grid.csv"
    df.to_csv(out, index=False)
    print(f"\n全网格 {len(df)} 组 → {out.name}")
    if df["passed"].any():
        print("\n== 通过线组合 ==")
        top = df[df["passed"]].sort_values("exp_r", ascending=False).head(15)
        print(top.to_string(index=False))
    else:
        print("\n无组合通过预注册线")
    return 0


if __name__ == "__main__":
    sys.exit(main())
