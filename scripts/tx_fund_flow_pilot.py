#!/usr/bin/env python3
"""腾讯个股资金流聚合板块试点（research_proxy，2026-09-05）。

目的：东财板块资金流历史上限 120 个交易日；本脚本用 westock-data skill
（腾讯自选股源，asfund 个股日资金流，可查 2020 年起）按板块成分股聚合，
产出长历史的板块五档资金流，验证散户热度信号在更长窗口的方向。

口径一致性（2026-09-05 实测，半导体 BK1036 全成分 vs 东财板块值）：
主力/中单/小单偏差 2-4%（高度一致），超大单档内划分略宽（约 10% 偏差），
主力=超大+大 汇总口径几乎一致。跨源结论以方向/单调性对照为主，
阈值须在腾讯源内自洽重校准。

输出：~/.lei_signal_lab/cache/tx_sector_flow_pilot.json
    {"fetched_days": n, "boards": {code: [{date, main_yi, jumbo_yi, mid_yi, small_yi}]}}
（亿元；大单可由 main-jumbo 推导。）

用法：PYTHONPATH=src python3 scripts/tx_fund_flow_pilot.py [--board BK1036]
      [--start 2025-09-01] [--conc 6]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))


def trading_days(start: str, end: str) -> list[str]:
    """交易日历来自 a_share_klines.parquet 的日期列（全市场对齐窗口）。"""
    import pandas as pd

    df = pd.read_parquet(CACHE / "a_share_klines.parquet", columns=["date"])
    days = sorted(set(df["date"].astype(str)))
    return [d for d in days if start <= d <= end]


def fetch_batch(syms: list[str], date: str) -> dict[str, dict]:
    """一批股票单日 asfund（npx 输出 markdown 表解析）。"""
    for attempt in (1, 2):
        try:
            r = subprocess.run(
                ["npx", "-y", "westock-data-skillhub@1.0.3", "asfund",
                 ",".join(syms), "--date", date],
                capture_output=True, text=True, timeout=180,
            )
            header = None
            rows: dict[str, dict] = {}
            for line in r.stdout.splitlines():
                if line.startswith("|") and "JumboNetFlow" in line:
                    header = [c.strip() for c in line.strip("|").split("|")]
                elif line.startswith("|") and header and "---" not in line:
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    if len(cells) == len(header):
                        rows[cells[1]] = dict(zip(header, cells))
            if rows:
                return rows
        except Exception:
            pass
        time.sleep(2 * attempt)
    return {}


def aggregate(rows: dict[str, dict]) -> dict | None:
    agg = {"main": 0.0, "jumbo": 0.0, "mid": 0.0, "small": 0.0}
    n = 0
    for rec in rows.values():
        try:
            agg["main"] += float(rec.get("MainNetFlow") or 0)
            agg["jumbo"] += float(rec.get("JumboNetFlow") or 0)
            agg["mid"] += float(rec.get("MidNetFlow") or 0)
            agg["small"] += float(rec.get("SmallNetFlow") or 0)
            n += 1
        except ValueError:
            continue
    if n < 10:
        return None
    return {
        "main_yi": round(agg["main"] / 1e8, 2),
        "jumbo_yi": round(agg["jumbo"] / 1e8, 2),
        "mid_yi": round(agg["mid"] / 1e8, 2),
        "small_yi": round(agg["small"] / 1e8, 2),
        "n_stocks": n,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="BK1036")
    ap.add_argument("--boards", default="", help="逗号分隔多板块代码（覆盖 --board）；"
                    "传 all_l1l2 时自动取快照全部一级+二级行业")
    ap.add_argument("--start", default="2025-09-01")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--conc", type=int, default=6)
    ap.add_argument("--batch", type=int, default=50)
    args = ap.parse_args()

    members = json.loads((CACHE / "sector_members.json").read_text())["boards"]
    if args.boards == "all_l1l2":
        snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text())
        board_list = [b["code"] for b in snap["boards"] if (b.get("level") or 3) <= 2]
    elif args.boards:
        board_list = [c.strip() for c in args.boards.split(",") if c.strip()]
    else:
        board_list = [args.board]
    days = trading_days(args.start, args.end)
    print(f"目标 {len(board_list)} 板块 × {len(days)} 交易日（{days[0]}~{days[-1]}）", flush=True)

    out_path = CACHE / "tx_sector_flow_pilot.json"
    result: dict = {"fetched_days": 0, "boards": {}}
    if out_path.exists():  # 断点续跑
        try:
            result = json.loads(out_path.read_text())
        except Exception:
            pass
    for b in board_list:
        result["boards"].setdefault(b, [])
    n_total = 0

    for bi, board in enumerate(board_list):
        stocks = members.get(board, {}).get("members", [])
        if not stocks:
            continue
        done_dates = {p["date"] for p in result["boards"][board]}
        todo = [d for d in days if d not in done_dates]
        if not todo:
            continue
        lock = {"n": 0}

        def work(day: str, board=board, stocks=stocks, todo_done=done_dates) -> None:
            if day in todo_done:
                return
            pts = []
            for i in range(0, len(stocks), args.batch):
                rows = fetch_batch(stocks[i:i + args.batch], day)
                if not rows:
                    return  # 当日有批次失败 → 整日跳过（不冒充）
                pts.append(rows)
            merged = {k: v for p in pts for k, v in p.items()}
            agg = aggregate(merged)
            if agg is None:
                return
            result["boards"][board].append({"date": day, **agg})
            result["boards"][board].sort(key=lambda p: p["date"])
            lock["n"] += 1

        with ThreadPoolExecutor(max_workers=args.conc) as ex:
            list(ex.map(work, todo))
        result["fetched_days"] = sum(len(v) for v in result["boards"].values())
        out_path.write_text(json.dumps(result, ensure_ascii=False))
        n_pts = len(result["boards"][board])
        n_total += 1
        print(f"[{n_total}/{len(board_list)}] {board}: +{lock['n']} -> {n_pts} 天", flush=True)

    out_path.write_text(json.dumps(result, ensure_ascii=False))
    print(f"落盘 {out_path}，合计 {result['fetched_days']} 板块日")
    return 0


if __name__ == "__main__":
    sys.exit(main())
