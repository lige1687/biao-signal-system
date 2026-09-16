"""宽度推力（Breadth Thrust）事件研究——方法层新信号族第一条（预注册协议）。

假设：宽度从极端低位的急速抬升（推力）是独立于「宽度水平」的启动信号，
对应第十二轮发现的复苏格（低·上）的更早触发器。Zweig 先验：1974-2020 美股
每次推力后均为正收益牛市段。

主指标（预注册，不做挑选）：B20 在过去 15 日内曾 < 25，当日 ≥ 60 → 推力日；
10 日内去重（事件聚簇算一次）。灵敏度面 {50,55,60,65}×{10,15,20} 全展示。

通过标准（预注册）：
  A. 事件数 ≥ 8（A股）；B. 事件后 120 日年化中位数 ≥ 无条件基准 × 1.5；
  C. 显著优于「低位无推力」对照组（否则只是低位的功劳，推力无增量）。
回报序列：A股用全A等权（1990 起全程覆盖），美股用 ^GSPC。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import TIMING_CACHE_DIR, load_breadth, load_index_bars

PRIMARY = dict(window=15, low=25.0, high=60.0, dedupe=10)


def thrust_days(b20: pd.Series, window: int, low: float, high: float, dedupe: int) -> pd.Series:
    was_low = (b20.shift(1).rolling(window).min() < low).fillna(False)
    fire = was_low & (b20 >= high)
    out = []
    last = -10**9
    for i, ok in enumerate(fire.values):
        if ok and i - last > dedupe:
            out.append(i)
            last = i
    return pd.Series([True if i in set(out) else False for i in range(len(fire))], index=b20.index)


def fwd_annualized(px: pd.Series, days: int) -> pd.Series:
    f = px.shift(-days) / px - 1
    return ((1 + f) ** (252 / days) - 1).where(f.notna())


def study(name: str, b20: pd.Series, px: pd.Series) -> None:
    both = pd.concat([b20.rename("b20"), px.rename("px")], axis=1, join="inner").dropna()
    b20, px = both["b20"], both["px"]
    ev = thrust_days(b20, **PRIMARY)
    n = int(ev.sum())
    base = fwd_annualized(px, 120)
    ev_ret = base[ev]
    # 对照组：低位(B20<25)但之后 15 日内未出现 ≥60 的日子
    no_thrust_after = ~thrust_days(b20, 15, 25.0, 60.0, 0).shift(-15).fillna(False).astype(bool)
    ctrl = base[(b20 < 25) & no_thrust_after]
    print(f"\n=== {name} {b20.index[0].date()}→{b20.index[-1].date()} | 事件 {n} 个 ===")
    if n:
        dates = [d.strftime("%Y-%m-%d") for d in b20.index[ev.values]]
        print("  日期:", ", ".join(dates))
    for label, s in [("无条件基准", base), ("推力事件", ev_ret), ("低位无推力(对照)", ctrl)]:
        if len(s) == 0:
            print(f"  {label}: 无样本")
            continue
        print(
            f"  {label}: n={len(s)} 120日年化中位 {s.median():+7.1%} "
            f"均值 {s.mean():+7.1%} 正占比 {(s > 0).mean():5.0%}"
        )
    ok_b = bool(ev_ret.median() >= base.median() * 1.5) if n else False
    ok_c = bool(ev_ret.median() > ctrl.median() * 1.5) if n and len(ctrl) else False
    print(f"  通过判定: A(事件数≥8)={n >= 8} B(≥基准1.5x)={ok_b} C(>对照1.5x)={ok_c}")
    # 灵敏度面
    print("  灵敏度（事件数 / 事件后120日年化中位）:")
    for hi in (50.0, 55.0, 60.0, 65.0):
        row = []
        for win in (10, 15, 20):
            e = thrust_days(b20, win, 25.0, hi, 10)
            r = base[e]
            row.append(f"win{win}: {int(e.sum())}个/{r.median():+.0%}" if len(r) else f"win{win}: 0")
        print(f"    high={hi:.0f}  " + "  ".join(row))


def main() -> None:
    wide_path = TIMING_CACHE_DIR.parent / "a_share_klines_full.parquet"
    wide = pd.read_parquet(wide_path)
    ew = (1 + wide.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0)).cumprod()
    cn = load_breadth("cn_all")
    study("A股·全A等权", cn["b20"], ew)
    us = load_breadth("sp500")
    study("美股·^GSPC", us["b20"], load_index_bars("^GSPC")["close"])


if __name__ == "__main__":
    main()
