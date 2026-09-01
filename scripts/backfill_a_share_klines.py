#!/usr/bin/env python3
"""深回填全A K线缓存：腾讯日K单次上限 800 根，用 end 参数向前翻页，
把每只股票的收盘价序列加深到 ~TARGET 根（默认 2600 ≈ 10.4 年），
之后跑 precompute_a_share_ma.py --backfill 即可重建 10 年级真宽度历史。

设计：
  - 幂等可续跑：每只股票只补「早于现有最早日期」的页，中断后重跑接着来；
    每 CHECKPOINT 只股票落盘一次 parquet，崩溃不丢进度。
  - 只改 K 线缓存，不动宽度历史/冻结快照（重建由 --backfill 负责）。
  - 次新股自然截断（翻不到更早就停），不造假点。

用法：
  PYTHONPATH=src python3 scripts/backfill_a_share_klines.py [--target 2600] [--threads 4]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from lei_signal.market_context.a_share_breadth import (  # noqa: E402
    _fetch_kline,
    get_a_share_codes,
    load_kline_cache,
    save_kline_cache,
)

PAGE = 800  # 腾讯单次上限


def page_before(sym: str, end_date: str) -> list[tuple[str, float]]:
    """拉 end_date（不含）之前的一页（最多 800 根）。"""
    import requests

    _H = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
    url = (
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"
        f"?param={sym},day,,{end_date},{PAGE},qfq"
    )
    for _ in range(3):
        try:
            r = requests.get(url, timeout=12, headers=_H)
            node = ((r.json() or {}).get("data") or {}).get(sym) or {}
            arr = node.get("qfqday") or node.get("day") or node.get("hfqday") or []
            out = []
            for row in arr:
                if str(row[0]) < end_date:  # 保险：严格早于 end
                    out.append((str(row[0]), float(row[2])))
            return out
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    return []


def deepen_symbol(sym: str, existing: list[tuple[str, float]], target: int) -> list[tuple[str, float]]:
    series = list(existing)
    for _ in range(8):  # 最多翻 8 页（800×8=6400 根 ≈ 25 年，够到绝大多数上市点）
        if len(series) >= target:
            break
        earliest = series[0][0] if series else datetime.now().strftime("%Y-%m-%d")
        page = page_before(sym, earliest)
        if len(page) < 5:
            break  # 上市初期自然截断
        series = page + series
        time.sleep(0.05)
    return series


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=int, default=2600, help="每只目标根数（默认 2600 ≈ 10.4 年）")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 只（调试）")
    args = ap.parse_args()

    cache = load_kline_cache()
    if not cache:
        print("✗ K线缓存为空：请先跑一次 precompute_a_share_ma.py 拉当前 800 根。")
        return 1
    print(f"现有缓存 {len(cache)} 只，目标深度 {args.target} 根/只")

    todo = [c for c, s in cache.items() if len(s) < args.target]
    if args.limit:
        todo = todo[: args.limit]
    print(f"待加深 {len(todo)} 只（{args.threads} 线程，可中断续跑）")

    t0 = time.time()
    done = 0
    changed = 0
    CHECKPOINT = 400

    def work(sym: str):
        return sym, deepen_symbol(sym, cache[sym], args.target)

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {ex.submit(work, s): s for s in todo}
        for fut in as_completed(futures):
            sym, deep = fut.result()
            done += 1
            if len(deep) > len(cache[sym]):
                cache[sym] = deep
                changed += 1
            if done % CHECKPOINT == 0:
                save_kline_cache(cache)
                el = time.time() - t0
                print(f"  进度 {done}/{len(todo)}（加深 {changed}）· {el/60:.1f}min · 已落盘", flush=True)

    save_kline_cache(cache)
    total_bars = sum(len(s) for s in cache.values())
    print(f"✓ 完成：加深 {changed}/{len(todo)} 只，缓存总K线 {total_bars:,} 根")
    print("  下一步：PYTHONPATH=src python3 scripts/precompute_a_share_ma.py --backfill 重建宽度历史")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
