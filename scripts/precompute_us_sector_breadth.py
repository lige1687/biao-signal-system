#!/usr/bin/env python3
"""美股 11 行业板块宽度预计算（情绪页「美股板块」数据层）。

对标 A股板块情绪：每个 GICS 行业算
- 等权行业指数（成分股收盘归一后等权平均，起点=100）；
- 宽度 b20/b50/b200（行业内站上 N 日均线的个股占比 0–100）。

数据源：
- ticker→GICS 行业：Wikipedia「List of S&P 500 companies」（本宇宙表同源），
  抓一次落 cache/sp500_sector_map.json，之后离线复用（--refresh-map 重抓）；
- 行情：cache/sp500_klines.parquet（refresh_sp500_breadth_tail.py 维护）。

输出 cache/us_sector_breadth.json（覆盖式）：
{as_of, sp500_ew: [{date,index}], sectors: [{key,name_en,name_cn,etf,n,
  series: [{date,index,b20,b50,b200}], last:{...}}]}

用法：workbuddy python3 scripts/precompute_us_sector_breadth.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab" / "cache"
MAP_PATH = CACHE / "sp500_sector_map.json"
OUT_PATH = CACHE / "us_sector_breadth.json"
KLINES = CACHE / "sp500_klines.parquet"

SECTOR_CN = {
    "Information Technology": ("信息技术", "XLK"),
    "Communication Services": ("通信服务", "XLC"),
    "Consumer Discretionary": ("可选消费", "XLY"),
    "Consumer Staples": ("必需消费", "XLP"),
    "Health Care": ("医疗健康", "XLV"),
    "Financials": ("金融", "XLF"),
    "Industrials": ("工业", "XLI"),
    "Materials": ("原材料", "XLB"),
    "Energy": ("能源", "XLE"),
    "Real Estate": ("房地产", "XLRE"),
    "Utilities": ("公用事业", "XLU"),
}
MIN_ELIGIBLE = 10
OUT_DAYS = 1260  # 输出最近 5 年（MA200 预热用全史算，只裁输出）


def fetch_sector_map(refresh: bool = False) -> dict[str, str]:
    if MAP_PATH.exists() and not refresh:
        return json.loads(MAP_PATH.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        headers={"User-Agent": "Mozilla/5.0 (research data fetch)"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
    t = pd.read_html(html)[0]
    m = {str(s).replace(".", "-"): str(g) for s, g in zip(t["Symbol"], t["GICS Sector"])}
    MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return m


def main() -> int:
    sector_map = fetch_sector_map(refresh="--refresh-map" in sys.argv)
    piv = pd.read_parquet(KLINES).sort_index()
    cols = [c for c in piv.columns if c in sector_map]
    print(f"klines {piv.shape}, mapped {len(cols)}/{piv.shape[1]} tickers, "
          f"last={piv.index.max().date()}")

    groups: dict[str, list[str]] = {}
    for c in cols:
        groups.setdefault(sector_map[c], []).append(c)

    def _series(members: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        sub = piv[members]
        ret = sub.pct_change(fill_method=None)
        idx = (1 + ret.fillna(0)).cumprod() * 100
        ew = idx.mean(axis=1)  # 等权行业指数（起点=100）
        ma = {w: sub.rolling(w).mean() for w in (20, 50, 200)}
        b = {}
        for w, m in ma.items():
            elig = sub.notna() & m.notna()
            b[w] = ((sub > m).sum(axis=1) / elig.sum(axis=1) * 100).where(elig.sum(axis=1) >= MIN_ELIGIBLE)
        return ew, b

    sectors = []
    for sec_en, members in sorted(groups.items()):
        name_cn, etf = SECTOR_CN.get(sec_en, (sec_en, ""))
        ew, b = _series(members)
        rows = []
        for d in piv.index:
            i_ = ew.get(d)
            if pd.isna(i_):
                continue
            rows.append({
                "date": pd.Timestamp(d).strftime("%Y-%m-%d"),
                "index": round(float(i_), 2),
                "b20": None if pd.isna(b[20].get(d)) else round(float(b[20].get(d)), 1),
                "b50": None if pd.isna(b[50].get(d)) else round(float(b[50].get(d)), 1),
                "b200": None if pd.isna(b[200].get(d)) else round(float(b[200].get(d)), 1),
            })
        if not rows:
            continue
        rows = rows[-OUT_DAYS:]
        last = rows[-1]
        sectors.append({
            "key": etf or sec_en.replace(" ", "_"),
            "name_en": sec_en, "name_cn": name_cn, "etf": etf, "n": len(members),
            "series": rows, "last": last,
        })
        print(f"  {name_cn}({etf}) {len(members)}只 b50={last['b50']} 截至行数 {len(rows)}")

    # 全市场等权参考线（抽屉里对照用）
    all_ew, _ = _series(cols)
    sp500_ew = [{"date": pd.Timestamp(d).strftime("%Y-%m-%d"), "index": round(float(v), 2)}
                for d, v in all_ew.dropna().items()][-OUT_DAYS:]

    out = {"as_of": sectors[0]["last"]["date"] if sectors else None,
           "sp500_ew": sp500_ew, "sectors": sectors,
           "note": f"美股行业宽度：GICS 11 行业，站上 N 日均线成分股占比；等权指数起点=100。来源 Wikipedia 行业表 + sp500_klines。"}
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"OK -> {OUT_PATH} ({len(sectors)} sectors, as_of={out['as_of']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
