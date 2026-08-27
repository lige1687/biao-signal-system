"""虹吸/独立行情判别器 v1：RS = 标的 N 日收益 − 全A等权 N 日收益。

定位：解决「宽度引擎何时对该标的下岗」（失效即下岗的人工判断自动化）。
检验纪律：检验集 = 12 轮回测已标记的失效(F)/有效(E)窗口，**只验证不调参**；
主指标预先注册：RS120 > +20pp 且连续 10 日（防闪断）。灵敏度面全量展示不挑选。

全A等权 = a_share_klines_full.parquet 收益逐日等权平均（与宽度同底表同偏差）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import TIMING_CACHE_DIR, load_index_bars

KLINE_FULL = TIMING_CACHE_DIR.parent / "a_share_klines_full.parquet"

PRIMARY_N, PRIMARY_THR, PERSIST = 120, 20.0, 10

# 检验集：F=失效窗口（判别器应点火=引擎下岗），E=有效窗口（应安静≥80%）
WINDOWS = [
    # ── F：虹吸/独立行情（champion 实测跑输，入册来源见 playbook）──
    ("F1", "399997", "中证白酒", "2019-01-01", "2021-02-10", "F", "抱团虹吸 -54.2%"),
    ("F2", "159819", "人工智能ETF", "2023-01-01", "2026-08-18", "F", "独立行情 -45.9%(本轮)"),
    ("F3", "980017", "国证芯片", "2023-02-01", "2026-08-18", "F", "后半窗 -11.8%起"),
    ("F4", "980030", "通信指数", "2024-09-20", "2026-08-18", "F", "本轮 -25.3%"),
    ("F5", "512720", "计算机ETF", "2024-09-20", "2026-08-18", "F", "本轮 -5.2%"),
    ("F6", "399006", "创业板指", "2013-01-01", "2014-12-31", "F", "独立牛 -10.2%"),
    ("F7", "399006", "创业板指", "2024-09-20", "2026-08-18", "F", "本轮 -21.1%(混合成因)"),
    ("F8", "588000", "科创50ETF", "2024-09-20", "2026-08-18", "F", "本轮 -18.5%"),
    ("F9", "510500", "中证500ETF", "2013-03-01", "2026-08-18", "F", "全历史 -9.8%"),
    # ── E：champion 实测有效窗口（判别器应保持安静）──
    ("E1", "399975", "证券指数", "2015-05-19", "2026-08-18", "E", "+16.3% 全历史"),
    ("E2", "399976", "新能车指数", "2014-01-01", "2026-08-18", "E", "+12.1%"),
    ("E3", "000819", "有色金属指数", "2006-01-01", "2026-08-18", "E", "进攻组成员"),
    ("E4a", "399006", "创业板指", "2010-06-01", "2013-01-01", "E", "独立牛之前"),
    ("E4b", "399006", "创业板指", "2015-01-01", "2024-09-19", "E", "2015→本轮前(含疯牛,宽容)"),
    ("E5a", "399997", "中证白酒", "2015-06-16", "2019-01-01", "E", "抱团前"),
    ("E5b", "399997", "中证白酒", "2021-02-10", "2026-08-18", "E", "抱团后"),
    ("E6", "512200", "房地产ETF", "2018-01-01", "2026-08-18", "E", "+11.7%"),
    ("E7", "159766", "旅游ETF", "2021-06-01", "2026-08-18", "E", "+9.6%"),
]


def all_a_equal_weight() -> pd.Series:
    wide = pd.read_parquet(KLINE_FULL)
    ret = wide.pct_change()
    ew_ret = ret.mean(axis=1, skipna=True)
    return (1 + ew_ret.fillna(0)).cumprod()


def rs_series(close: pd.Series, ew: pd.Series, n: int) -> pd.Series:
    both = pd.concat([close, ew], axis=1, join="inner").dropna()
    r = both.iloc[:, 0] / both.iloc[:, 0].shift(n) - both.iloc[:, 1] / both.iloc[:, 1].shift(n)
    return r * 100  # 百分点


def fire_series(rs: pd.Series, thr: float, persist: int) -> pd.Series:
    cond = rs > thr
    if persist <= 1:
        return cond
    return cond.rolling(persist).min().astype(bool)


def main() -> None:
    ew = all_a_equal_weight()
    closes: dict[str, pd.Series] = {}
    for _, sym, *_ in WINDOWS:
        if sym not in closes:
            try:
                closes[sym] = load_index_bars(sym)["close"]
            except Exception as e:  # noqa: BLE001
                print(f"!! {sym} 加载失败: {e}")
                closes[sym] = None

    rows = []
    rs_cache: dict[tuple[str, int], pd.Series] = {}
    for wid, sym, name, s, e, kind, _note in WINDOWS:
        if closes.get(sym) is None:
            continue
        if (sym, PRIMARY_N) not in rs_cache:
            rs_cache[(sym, PRIMARY_N)] = rs_series(closes[sym], ew, PRIMARY_N)
        rs = rs_cache[(sym, PRIMARY_N)].loc[s:e].dropna()
        fire = fire_series(rs, PRIMARY_THR, PERSIST)
        rows.append(
            dict(wid=wid, name=name, kind=kind, days=len(fire),
                 fire_rate=float(fire.mean()), rs_mean=float(rs.mean()))
        )

    df = pd.DataFrame(rows)
    print(f"主指标: RS{PRIMARY_N} > +{PRIMARY_THR}pp 连续{PERSIST}日 | 全A等权={KLINE_FULL.name}")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    cov = df[df.kind == "F"].fire_rate.mean()
    fa = df[df.kind == "E"].fire_rate.mean()
    print(f"\n失效窗覆盖率(F 均值): {cov:.0%}  |  有效窗误报率(E 均值): {fa:.0%}")
    print("通过标准: 覆盖≥80% 且 误报≤20%")

    # 灵敏度面（全量展示，不挑选）
    print("\n灵敏度面（F覆盖率 / E误报率）:")
    print(f"{'N':>5} {'thr':>5} {'无持续':>14} {'持续10日':>14}")
    for n in (60, 120, 250):
        for thr in (15.0, 20.0, 30.0):
            f_rates, e_rates = [], []
            for _wid, sym, _name, s, e_, kind, _note in WINDOWS:
                if closes.get(sym) is None:
                    continue
                key = (sym, n)
                if key not in rs_cache:
                    rs_cache[key] = rs_series(closes[sym], ew, n)
                seg = rs_cache[key].loc[s:e_].dropna()
                if seg.empty:
                    continue
                rate = float(fire_series(seg, thr, PERSIST).mean())
                (f_rates if kind == "F" else e_rates).append(rate)
            fm = f"{sum(f_rates) / len(f_rates):.0%}" if f_rates else "--"
            em = f"{sum(e_rates) / len(e_rates):.0%}" if e_rates else "--"
            f2 = [float(fire_series(rs_cache[(sym2, n)].loc[s2:e2].dropna(), thr, 1).mean())
                  for _w, sym2, _n, s2, e2, k2, _x in WINDOWS
                  if k2 == "F" and closes.get(sym2) is not None
                  and not rs_cache[(sym2, n)].loc[s2:e2].dropna().empty]
            e2 = [float(fire_series(rs_cache[(sym2, n)].loc[s2:e2].dropna(), thr, 1).mean())
                  for _w, sym2, _n, s2, e2, k2, _x in WINDOWS
                  if k2 == "E" and closes.get(sym2) is not None
                  and not rs_cache[(sym2, n)].loc[s2:e2].dropna().empty]
            fm2 = f"{sum(f2) / len(f2):.0%}" if f2 else "--"
            em2 = f"{sum(e2) / len(e2):.0%}" if e2 else "--"
            print(f"{n:>5} {thr:>4.0f} {fm2:>6}/{em2:<6} {fm:>6}/{em:<6}")

    # 今日状态（供后续接线）
    print("\n各标的当前状态（最新日）:")
    for sym, name in [("399006", "创业板指"), ("399975", "证券"), ("399976", "新能车"),
                      ("000819", "有色"), ("399997", "白酒"), ("980017", "国证芯片"),
                      ("980030", "通信"), ("159819", "人工智能ETF"), ("512200", "房地产ETF")]:
        if closes.get(sym) is None:
            continue
        if (sym, PRIMARY_N) not in rs_cache:
            rs_cache[(sym, PRIMARY_N)] = rs_series(closes[sym], ew, PRIMARY_N)
        rs = rs_cache[(sym, PRIMARY_N)]
        fired = bool(fire_series(rs, PRIMARY_THR, PERSIST).iloc[-1])
        state = "虹吸中·宽度引擎应下岗" if fired else "与全场同频"
        print(f"  {name}: RS120={rs.iloc[-1]:+.1f}pp → {state}")


if __name__ == "__main__":
    main()
