#!/usr/bin/env python3
"""腾讯个股资金流聚合板块·按天全市场并集版（research_proxy，2026-09-05）。

架构：一天一次拉「全部目标板块成分股并集（去重）」的 asfund 批量
（并集 ~2400 只 ÷ 50/批 ≈ 48 批/天），再按成分归属拆分聚合到各板块——
比逐板块抓快一个数量级（161 板块 × 246 天约 35 分钟）。

口径一致性（2026-09-05 实测，半导体全成分 vs 东财 push2his）：
主力/中单/小单偏差 2-4%，超大单档划分略宽（~10%）；跨源结论以源内
自洽为准（回测 --flows-file 消费，字段自动映射）。

输出：~/.lei_signal_lab/cache/tx_sector_flow_pilot.json
    {"fetched_days": n, "boards": {code: [{date, main_yi, jumbo_yi, mid_yi, small_yi, n_stocks}]}}
断点续跑：已存在 (板块, 日期) 的点不重抓（按天粒度：某天任一板块已有
该日数据则视为该日已完成，直接跳过）。

用法：PYTHONPATH=src python3 scripts/tx_fund_flow_pilot.py --mode byday
      [--boards all_l1l2] [--start 2025-09-01] [--conc 12]
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
    import pandas as pd

    df = pd.read_parquet(CACHE / "a_share_klines.parquet", columns=["date"])
    days = sorted(set(df["date"].astype(str)))
    return [d for d in days if start <= d <= end]


# npx 并发会因 npm 缓存锁批量失败（实测 12 并发全军覆没）；优先用 npx 缓存
# 的包入口直接 node 调用（无锁、省 ~1.5s/批），回落 npx。
_PKG = Path.home() / ".npm/_npx/f124025a92f4edba/node_modules/westock-data-skillhub/scripts/index.js"
_CMD_BASE = ["node", str(_PKG)] if _PKG.exists() else ["npx", "-y", "westock-data-skillhub@1.0.3"]


def fetch_batch(syms: list[str], date: str) -> dict[str, dict]:
    for attempt in (1, 2):
        try:
            r = subprocess.run(
                [*_CMD_BASE, "asfund", ",".join(syms), "--date", date],
                capture_output=True, text=True, timeout=240,
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
        time.sleep(1.5 * attempt)
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="byday", choices=["byday"],
                    help="byday=按天抓全市场并集（推荐，快一个数量级）")
    ap.add_argument("--boards", default="all_l1l2",
                    help="all_l1l2=快照全部一、二级行业；或逗号分隔 BK 代码")
    ap.add_argument("--start", default="2025-09-01")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--conc", type=int, default=12)
    ap.add_argument("--batch", type=int, default=50)
    args = ap.parse_args()

    members = json.loads((CACHE / "sector_members.json").read_text())["boards"]
    if args.boards == "all_l1l2":
        snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text())
        board_list = [b["code"] for b in snap["boards"] if (b.get("level") or 3) <= 2]
    else:
        board_list = [c.strip() for c in args.boards.split(",") if c.strip()]

    sym_to_boards: dict[str, list[str]] = {}
    board_members = {b: members.get(b, {}).get("members", []) for b in board_list}
    for b, mem in board_members.items():
        for s in mem:
            sym_to_boards.setdefault(s, []).append(b)
    all_syms = sorted(sym_to_boards)
    days = trading_days(args.start, args.end)
    print(f"{len(board_list)} 板块 · 成分并集 {len(all_syms)} 只 × {len(days)} 交易日"
          f"（{days[0]}~{days[-1]}），每 {args.batch} 只一批", flush=True)

    out_path = CACHE / "tx_sector_flow_pilot.json"
    result: dict = {"fetched_days": 0, "boards": {}}
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
        except Exception:
            pass
    for b in board_list:
        result["boards"].setdefault(b, [])
    have = {b: {p["date"] for p in result["boards"][b]} for b in board_list}
    # 按天续跑：目标板块中已有 >=80% 记录该日的天视为完成
    done_days = {d for d in days
                 if sum(1 for b in board_list if d in have[b]) >= len(board_list) * 0.8}
    todo = [d for d in days if d not in done_days]
    print(f"断点续跑：已完成 {len(done_days)} 天，待抓 {len(todo)} 天", flush=True)

    n_batches = (len(all_syms) + args.batch - 1) // args.batch
    lock = {"days": 0}

    def work(day: str) -> None:
        day_rows: dict[str, dict] = {}
        n_fail_batch = 0
        for i in range(0, len(all_syms), args.batch):
            want = all_syms[i:i + args.batch]
            rows = fetch_batch(want, day)
            if len(rows) < len(want) * 0.5:
                n_fail_batch += 1  # 单批失败宽容：只丢该批股票，不丢整天
                continue
            day_rows.update(rows)
        if len(day_rows) < len(all_syms) * 0.7 or n_fail_batch > 10:
            return
        # 按板块聚合
        for b in board_list:
            agg = {"main": 0.0, "jumbo": 0.0, "mid": 0.0, "small": 0.0}
            n = 0
            for s in board_members[b]:
                rec = day_rows.get(s)
                if not rec:
                    continue
                try:
                    agg["main"] += float(rec.get("MainNetFlow") or 0)
                    agg["jumbo"] += float(rec.get("JumboNetFlow") or 0)
                    agg["mid"] += float(rec.get("MidNetFlow") or 0)
                    agg["small"] += float(rec.get("SmallNetFlow") or 0)
                    n += 1
                except ValueError:
                    continue
            if n < 10:
                continue
            have[b].add(day)
            result["boards"][b] = [
                p for p in result["boards"][b] if p["date"] != day
            ] + [{
                "date": day,
                "main_yi": round(agg["main"] / 1e8, 2),
                "jumbo_yi": round(agg["jumbo"] / 1e8, 2),
                "mid_yi": round(agg["mid"] / 1e8, 2),
                "small_yi": round(agg["small"] / 1e8, 2),
                "n_stocks": n,
            }]
            result["boards"][b].sort(key=lambda p: p["date"])
        lock["days"] += 1
        if lock["days"] % 10 == 0:
            result["fetched_days"] = sum(len(v) for v in result["boards"].values())
            out_path.write_text(json.dumps(result, ensure_ascii=False))
            print(f"  完成 {lock['days']}/{len(todo)} 天", flush=True)

    with ThreadPoolExecutor(max_workers=args.conc) as ex:
        list(ex.map(work, todo))

    result["fetched_days"] = sum(len(v) for v in result["boards"].values())
    out_path.write_text(json.dumps(result, ensure_ascii=False))
    n_full = sum(1 for b in board_list if len(result["boards"][b]) >= len(days) * 0.9)
    print(f"落盘 {out_path}：{n_full}/{len(board_list)} 板块 ≥90% 天数覆盖，"
          f"合计 {result['fetched_days']} 板块日")
    return 0


if __name__ == "__main__":
    sys.exit(main())
