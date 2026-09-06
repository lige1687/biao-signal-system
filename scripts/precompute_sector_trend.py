#!/usr/bin/env python3
"""行业板块趋势工作台 · 预计算（P1.2）。

本地定时任务（建议工作日 16:45，错开 16:30 的全A宽度/日K 维护）跑一次：
  1. 拉全量板块成分股映射（东财 clist ``fs=b:{code}``，6 并发 + 0.2s 抖动，当日命中即跳过）；
  2. 读 ``a_share_klines.parquet``（由 ``precompute_a_share_ma.py`` 维护的逐只日K缓存）；
  3. 全部纯函数计算（等权指数 / RS / 宽度 / 趋势读出 / 阶段判定）；
  4. 原子写三份 json：``sector_trend_snapshot.json`` / ``sector_trend_history.json`` / ``sector_members.json``。

判定标 ``research_proxy``（研究代理），不冒充 LEI 原始规则，不出买卖点。
东财 push2 板块日K 不可达 → 板块指数一律本机合成（等权），口径在快照 ``research_proxy_note`` 常驻声明。

用法
----
  export PYTHONPATH=/path/to/lei-signal-lab/src
  python scripts/precompute_sector_trend.py

  # 同交易日已拉过成分股则跳过取数；强制重算加 --force
  python scripts/precompute_sector_trend.py --force

  # 调试：只算前 N 个板块
  python scripts/precompute_sector_trend.py --limit 20

返回码
------
  0  成功（或成分股当日已缓存跳过取数）
  1  取数失败（网络受限 / 成分股或 K线缓存缺失）
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from lei_signal.market_context import sector_trend as st  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="预计算行业板块趋势（等权指数/RS/宽度/阶段）")
    ap.add_argument("--limit", type=int, default=0, help="只算前 N 个板块（调试用）")
    ap.add_argument("--no-save", action="store_true", help="跳过落盘")
    ap.add_argument("--force", action="store_true", help="强制重算（忽略成分股当日缓存）")
    ap.add_argument(
        "--backfill-history",
        action="store_true",
        help="把 320 日窗口的指数/b50/RS 分位序列一次性回填进历史文件（已有实录优先）",
    )
    args = ap.parse_args()

    t0 = time.time()
    try:
        limit = args.limit if args.limit > 0 else None
        snap = st.run_sector_trend(
            limit=limit,
            no_save=args.no_save,
            force=args.force,
            backfill=args.backfill_history,
        )
    except FileNotFoundError as exc:
        print(f"✗ 前置缓存缺失：{exc}")
        print("  请先跑 scripts/precompute_a_share_ma.py 生成 a_share_klines.parquet。")
        return 1
    except Exception as exc:  # noqa: BLE001 - 取数/网络失败统一返回 1
        print(f"✗ 预计算失败（取数或计算异常）：{exc}")
        return 1

    boards = snap.get("boards", [])
    n_stage = sum(1 for b in boards if b.get("stage"))
    print(f"✓ 板块数 {len(boards)} · 已判定阶段 {n_stage} · 代表交易日 {snap.get('date')}")
    if snap.get("warnings"):
        print(f"  ⚠ 层级校验告警 {len(snap['warnings'])} 条（已写入快照 warnings 字段）")
    if not args.no_save:
        print("✓ 已落盘 sector_trend_snapshot.json + sector_trend_history.json + sector_members.json")
        print("  后端 /api/sectors/* 直接读冻结快照（重启不丢）；刷新页面即见板块趋势。")
    else:
        print("  [--no-save] 未落盘")

    # 腾讯聚合资金流当日追加（散户情绪终版信号的数据源；失败不阻断主流程）
    if not args.no_save:
        try:
            import subprocess
            from datetime import datetime as _dt

            today = _dt.now().strftime("%Y-%m-%d")
            r = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent / "tx_fund_flow_pilot.py"),
                 "--mode", "byday", "--boards", "all_l1l2",
                 "--start", today, "--end", today, "--conc", "6"],
                capture_output=True, text=True, timeout=900,
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
            )
            print("✓ 腾讯资金流当日追加：" + (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "无输出"))
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ 腾讯资金流当日追加失败（不影响主快照）: {exc}")

    print(f"⏱ 耗时 {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
