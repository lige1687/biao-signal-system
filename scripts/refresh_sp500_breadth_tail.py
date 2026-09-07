#!/usr/bin/env python3
"""增量刷新 SP500 宽度：拉成分股最近 3 个月收盘价，合并进既有透视表，
重算全史宽度并覆盖写 sp500_ma_breadth_history.json。

背景（2026-09-07）：sp500_klines.parquet 停在 2026-08-31、宽度 json 停在
2026-08-14，之后每日快照全是空壳 NULL 行——基本面页美股宽度因此显示空卡。
本脚本补齐「拉新→重算」这一步；入库用 Desktop 生产副本的
ingest_sp500_breadth_to_sqlite.py（幂等：先 DELETE 再 INSERT 全部 SP500 行）。

用法（用生产同款 python，保证 yfinance 可用）：
    /Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3 \
        scripts/refresh_sp500_breadth_tail.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab" / "cache"
PARQUET = CACHE / "sp500_klines.parquet"
JSON_OUT = CACHE / "sp500_ma_breadth_history.json"

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.market_context.us_breadth import compute_sp500_breadth  # noqa: E402


def main() -> int:
    piv = pd.read_parquet(PARQUET).sort_index()
    symbols = [c for c in piv.columns if str(c).strip().isalpha()]
    print(f"existing piv: {piv.shape}, last={piv.index.max().date()}, fetching {len(symbols)} symbols")

    import yfinance as yf

    frames: dict[str, pd.Series] = {}
    fail = 0
    t0 = time.time()
    for i, sym in enumerate(symbols):
        try:
            h = yf.Ticker(sym.replace(".", "-")).history(period="3mo", interval="1d", auto_adjust=False)
            c = h.get("Close")
            if c is not None and len(c):
                frames[sym] = c.dropna()
        except Exception:  # noqa: BLE001 —— Yahoo 限流单票失败跳过
            fail += 1
        if i % 50 == 0:
            print(f"  {i}/{len(symbols)} elapsed={time.time()-t0:.0f}s fail={fail}")
        time.sleep(0.12)

    if not frames:
        print("ERR: yfinance 全部失败", file=sys.stderr)
        return 2
    new = pd.DataFrame(frames)
    new.index = pd.to_datetime(new.index).tz_localize(None)
    # 旧值优先（combine_first），新日期追加；再按列对齐回原顺序
    merged = piv.combine_first(new)
    merged = merged[~merged.index.duplicated(keep="first")].sort_index()
    print(f"merged piv: {merged.shape}, last={merged.index.max().date()}")

    hist = compute_sp500_breadth(merged, min_eligible=100)
    hist.sort(key=lambda h: h["date"])
    if not hist:
        print("ERR: 宽度计算为空", file=sys.stderr)
        return 2
    JSON_OUT.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    merged.to_parquet(PARQUET)
    print(f"OK: json {len(hist)} 天 ({hist[0]['date']} → {hist[-1]['date']})，parquet 已更新")
    print("tail 5:")
    for h in hist[-5:]:
        print(" ", h)

    # 顺带刷新美股行业宽度（情绪页「美股板块」数据，2026-09-07 起）
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        from precompute_us_sector_breadth import main as _us_main
        rc = _us_main()
        print(f"US sector breadth refresh rc={rc}")
    except Exception as exc:  # noqa: BLE001 —— 行业宽度失败不影响主流程
        print(f"WARN: US sector breadth 刷新失败：{exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
