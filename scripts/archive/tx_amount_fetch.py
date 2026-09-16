#!/usr/bin/env python3
"""板块成分股成交额历史抓取（腾讯 kline，amount 列；量能维度数据源）。

输出 ~/.lei_signal_lab/cache/tx_amount_panel.parquet：date×symbol 的成交额
（元）。断点续跑：文件已存在且覆盖最新交易日则退出。
用法：PYTHONPATH=src python3 scripts/tx_amount_fetch.py [--days 260] [--conc 6]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
OUT = CACHE / "tx_amount_panel.parquet"
_CLI = ["node", str(Path.home() / ".npm/_npx/f124025a92f4edba/node_modules/"
                    "westock-data-skillhub/scripts/index.js")]


def fetch_batch(syms: list[str], days: int) -> pd.DataFrame | None:
    for attempt in (1, 2):
        try:
            r = subprocess.run(
                [*_CLI, "kline", ",".join(syms), "--period", "day", "--limit", str(days)],
                capture_output=True, text=True, timeout=300)
            header, rows = None, []
            for line in r.stdout.splitlines():
                if line.startswith("| symbol"):
                    header = [c.strip() for c in line.strip("|").split("|")]
                elif line.startswith("|") and header and "---" not in line:
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    if len(cells) == len(header):
                        rows.append(cells)
            if rows:
                df = pd.DataFrame(rows, columns=header)
                return df
        except Exception:
            pass
        time.sleep(1.5 * attempt)
    return None


def main() -> int:
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=260)
    ap.add_argument("--conc", type=int, default=6)
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()

    members = json.loads((CACHE / "sector_members.json").read_text(encoding="utf-8"))["boards"]
    snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
    canonical = {b["code"] for b in snap["boards"] if (b.get("level") or 3) <= 2}
    syms = sorted({s for c, v in members.items() if c in canonical
                   for s in v.get("members", [])})
    print(f"成分并集 {len(syms)} 只 × {args.days} 日", flush=True)

    if OUT.exists():
        old = pd.read_parquet(OUT)
        last = old.index.max()
        if str(last.date()) >= (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d"):
            print(f"已是最新（{last.date()}），退出")
            return 0

    frames: list[pd.DataFrame] = []
    frames_c: list[pd.DataFrame] = []
    lock_n = {"done": 0}

    def work(i: int) -> None:
        batch = syms[i:i + args.batch]
        df = fetch_batch(batch, args.days)
        if df is None or len(df) < len(batch) * 0.5:
            return
        try:
            piv = df.pivot_table(index="date", columns="symbol", values="amount", aggfunc="sum")
            frames.append(piv)
            piv_c = df.pivot_table(index="date", columns="symbol", values="last", aggfunc="sum")
            frames_c.append(piv_c)
        except Exception:
            return
        lock_n["done"] += 1
        if lock_n["done"] % 20 == 0:
            print(f"  完成 {lock_n['done']} 批", flush=True)

    with ThreadPoolExecutor(max_workers=args.conc) as ex:
        list(ex.map(work, range(0, len(syms), args.batch)))

    if not frames:
        print("抓取失败")
        return 1
    merged_c = pd.concat(frames_c, axis=1)
    merged_c = merged_c[sorted(merged_c.columns)]
    merged_c.index = pd.to_datetime(merged_c.index)
    merged_c = merged_c.sort_index()
    OUT_C = CACHE / "tx_close_panel.parquet"
    if OUT_C.exists():
        oldc = pd.read_parquet(OUT_C)
        merged_c = pd.concat([oldc, merged_c]).groupby(level=0).last().sort_index()
    merged_c.to_parquet(OUT_C)

    merged = pd.concat(frames, axis=1)
    merged = merged[sorted(merged.columns)]
    merged.index = pd.to_datetime(merged.index)
    merged = merged.sort_index()
    if OUT.exists():
        old = pd.read_parquet(OUT)
        merged = pd.concat([old, merged]).groupby(level=0).last().sort_index()
    merged.to_parquet(OUT)
    print(f"落盘 {OUT}: {merged.shape[0]} 日 × {merged.shape[1]} 只")
    return 0


if __name__ == "__main__":
    sys.exit(main())
