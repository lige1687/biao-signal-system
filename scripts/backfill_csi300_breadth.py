#!/usr/bin/env python3
"""沪深300 成分股自身宽度回填（消「全A 宽度 × 沪深300 基准」口径错配）。

方法：全 A K 线透视表（a_share_klines_full.parquet，5211 列）已包含
CSI300 成分股收盘价——直接切成分股子集重算 MA20/50/200 上方占比，
无需任何网络拉取。成分名单 = akshare 中证指数公司当前名单（今日
成分回算，幸存者偏差与 SP500 宽度同口径声明）。

落盘：~/.lei_signal_lab/cache/csi300_ma_breadth_history.json
（格式与全 A 研究史一致：[{date, ma20_pct, ma50_pct, ma200_pct}]）
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

os.environ.setdefault("NO_PROXY", "*")
CACHE = Path.home() / ".lei_signal_lab/cache"
OUT = CACHE / "csi300_ma_breadth_history.json"


def constituents() -> list[str]:
    import akshare as ak  # noqa: PLC0415

    try:
        df = ak.index_stock_cons(symbol="000300")  # 东财源
        col = "品种代码"
    except Exception:  # noqa: BLE001
        df = ak.index_stock_cons_csindex(symbol="000300")
        col = "成分券代码"
    codes = [str(c).zfill(6) for c in df[col]]
    return codes


def main() -> int:
    codes = constituents()
    print(f"CSI300 成分：{len(codes)} 只（当前名单回算）")
    piv = pd.read_parquet(CACHE / "a_share_klines_full.parquet")
    cols = [c for c in codes if c in piv.columns]
    print(f"透视表命中 {len(cols)}/{len(codes)} 只")
    sub = piv[cols]
    out = []
    for w in (20, 50, 200):
        ma = sub.rolling(w).mean()
        elig = (sub.notna() & ma.notna()).sum(axis=1)
        ratio = (sub > ma).sum(axis=1) / elig.mask(elig == 0)
        pct = (ratio * 100).where(elig >= 150) \
            .astype(float).round(4)  # 成分至少 150 只有效
        out.append(pct.rename(f"ma{w}_pct"))
    hist = pd.concat(out, axis=1).dropna(how="all")
    hist.index.name = "date"
    recs = [{"date": str(d.date()), **{k: (None if pd.isna(v) else float(v))
                                       for k, v in row.items()}}
            for d, row in hist.iterrows()]
    OUT.write_text(__import__("json").dumps(recs, ensure_ascii=False))
    print(f"落盘 {OUT.name}：{len(recs)} 日，{recs[0]['date']} → "
          f"{recs[-1]['date']}")

    # 与全 A 口径关键期对照
    full = pd.read_json(CACHE / "a_share_ma_breadth_full_history.json")
    full["date"] = pd.to_datetime(full["date"])
    full = full.set_index("date")
    csi = hist.copy()
    for label, lo, hi in (("2015 股灾", "2015-05", "2015-10"),
                          ("2021 抱团顶", "2021-01", "2021-03"),
                          ("2024-02 微盘崩", "2024-01", "2024-03"),
                          ("2026 背离市", "2026-01", "2026-08")):
        a = full.loc[lo:hi, "ma200_pct"]
        b = csi.loc[lo:hi, "ma20_pct"]
        c = csi.loc[lo:hi, "ma200_pct"]
        if len(a) and len(c):
            print(f"[{label}] 全A B200 min {a.min():.0f}% vs "
                  f"CSI300 B200 min {c.min():.0f}% | CSI300 B20 min "
                  f"{b.min():.0f}%")
    corr = full["ma200_pct"].corr(csi["ma200_pct"])
    print(f"B200 两口径全史相关系数：{corr:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
