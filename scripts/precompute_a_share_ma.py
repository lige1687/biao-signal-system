#!/usr/bin/env python3
"""本机预计算：真全A 市场宽度（MA20/50/200 上方占比）「冻结快照」。

为什么需要它
------------
受限网络下东财历史K线(push2his.eastmoney.com)不可达，改用腾讯日K线
(proxy.finance.qq.com/ifzqgtimg，白名单放行)。真·宽度（站上均线股票占比）由本机(正常网络)
逐只拉腾讯日K线计算。

本脚本在你本机跑一次（建议每个交易日收盘后由定时任务触发），计算并「冻结」：
  - B20/B50/B200 上方占比（真·市场宽度）
  - 收盘时点的全A涨跌家数
落盘到 LEI_CACHE_ROOT 下的磁盘文件（重启不丢）：
  - a_share_ma_breadth.json        冻结快照（global-strip 直接读，次日整天+周末不重算）
  - a_share_ma_breadth_history.json  历史序列（趋势图，逐日累积）
  - a_share_klines.parquet          逐只日K收盘价缓存（增量更新，断网可复用）

落盘后后端无需重启：global-strip 直接读这份「冻结快照」，次日整天与周末均不重算，
下次刷新页面即见真宽度。

用法
----
  export PYTHONPATH=/path/to/lei-signal-lab/src
  python scripts/precompute_a_share_ma.py

  # 同交易日已算过则自动跳过；强制重算加 --force
  python scripts/precompute_a_share_ma.py --force

  # 指定缓存根目录
  LEI_CACHE_ROOT=/your/cache python scripts/precompute_a_share_ma.py

  # 调试：只算前 N 只（快速验证链路，不落盘正式缓存）
  python scripts/precompute_a_share_ma.py --limit 50

耗时：首跑约 5~15 分钟（全A 5000+ 只）；之后有 K线磁盘缓存，仅补最新几天，几分钟内。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

# 腾讯K线源(proxy.finance.qq.com/ifzqgtimg)在 WorkBuddy 透明代理白名单内，受限网络下
# 走代理即可拉取；本机无代理环境则直连腾讯(国内可达)。两种环境均可用，无需特殊处理。

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from lei_signal.market_context.a_share_breadth import (  # noqa: E402
    append_ma_breadth_history,
    backfill_ma_breadth_history,
    fetch_advance_decline,
    fetch_ma_breadth,
    get_a_share_codes_with_status,
    get_cached_ma_breadth,
    save_ma_breadth_cache,
    save_ma_breadth_qualification,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="预计算真全A MA 上方占比宽度(冻结快照)")
    ap.add_argument("--limit", type=int, default=0, help="只算前 N 只（调试用，不落盘正式缓存）")
    ap.add_argument("--no-save", action="store_true", help="跳过落盘")
    ap.add_argument("--force", action="store_true", help="兼容旧命令；不覆盖既有快照或历史")
    ap.add_argument("--backfill", action="store_true",
                    help="从K线缓存回溯历史；须按既有历史重建授权单独运行")
    args = ap.parse_args()

    if args.backfill:
        print("▶ 从 K线缓存回溯全历史宽度序列…")
        hist = backfill_ma_breadth_history()
        if hist:
            print(f"✓ 回溯完成：{len(hist)} 个交易日（{hist[0]['date']} → {hist[-1]['date']}）")
        else:
            print("✗ 回溯失败（K线缓存为空？请先不带 --backfill 跑一次拉取K线）")
        return 0

    t0 = time.time()
    print("▶ 拉取全A代码列表(沪+深+北交所)…")
    code_result = get_a_share_codes_with_status(include_bj=True)
    codes = code_result["codes"]
    if not codes:
        print("✗ 代码列表为空，网络可能无法访问交易所官网(akshare)。请在本机正常网络下运行。")
        return 1
    print(f"  共 {len(codes)} 只")

    if args.limit:
        codes = codes[: args.limit]
        print(f"  [debug] 仅计算前 {len(codes)} 只")

    print("▶ 拉取实时涨跌家数(腾讯快照)…")
    ad = fetch_advance_decline(codes)
    total = ad["total"]
    up_pct = ad["up"] / total * 100 if total else 0
    adv_dec = ad["up"] / ad["down"] if ad["down"] else None
    print(f"  涨 {ad['up']} / 跌 {ad['down']} / 平 {ad['flat']} · 上涨占比 {up_pct:.1f}%")

    print("▶ 逐只拉腾讯日K线(带磁盘缓存)，计算 MA20/50/200 上方占比（首跑较慢）…")
    target_day = datetime.now().strftime("%Y-%m-%d")
    ma = fetch_ma_breadth(
        codes,
        target_day=target_day,
        code_sources=code_result["sources"],
        persist_cache=not args.no_save and not args.limit,
    )
    if not ma:
        print("✗ 腾讯K线拉取失败（接口可能临时不可用或被网络策略拦截）。")
        print("  请确认本机可正常访问 web.ifzq.gtimg.cn，或检查代理设置。")
        return 1

    trading_day = ma.get("trading_day", "")
    quality = ma["qualification"]
    quality["applied_to_snapshot"] = False
    print(f"  代表交易日: {trading_day}")
    print(f"  同日覆盖 {quality['same_day_available']}/{quality['universe_total']}；"
          f"E20={quality['eligible20']} E50={quality['eligible50']} E200={quality['eligible200']}；"
          f"资格={quality['status']} {quality['reasons']}")

    if not args.no_save and not args.limit and not save_ma_breadth_qualification(quality):
        print("✗ 资格证据写入失败；旧快照和历史保持不变。")
        return 2
    if quality["status"] != "verified":
        print("✗ 成员来源或同日行情未核齐；旧快照和历史保持不变。")
        return 2

    # 同交易日已算过则跳过落盘（除非 --force），保留冻结快照不覆盖
    if not args.no_save and not args.limit:
        existing = get_cached_ma_breadth()
        if existing and existing.get("date", "") >= trading_day:
            print(f"✓ 交易日 {trading_day} 已有快照，保留旧原件，不覆盖。")
            print(f"⏱ 耗时 {time.time() - t0:.1f}s")
            return 0

    if not args.no_save and not args.limit:
        saved = save_ma_breadth_cache(
            ma["ma20_pct"], ma["ma50_pct"], ma["ma200_pct"],
            eligible=ma.get("eligible", len(codes)),
            up=ad["up"], down=ad["down"], flat=ad["flat"], total=total,
            up_pct=up_pct, adv_dec_ratio=adv_dec,
            limit_up=ad["limit_up"], limit_down=ad["limit_down"],
            trading_day=trading_day,
            source="腾讯日K线(本机收盘后预计算)",
            qualification=quality,
        )
        if not saved:
            print("✗ 宽度快照写入失败；未更新历史。")
            return 2
        if not append_ma_breadth_history(
            ma["ma20_pct"], ma["ma50_pct"], ma["ma200_pct"], trading_day=trading_day
        ):
            print("✗ 宽度历史写入失败；快照已写入，需核对后再显示。")
            return 2
        quality["applied_to_snapshot"] = True
        if not save_ma_breadth_qualification(quality):
            print("✗ 资格证据最终读回文件写入失败；宽度仍须待核。")
            return 2
        print("✓ 已落盘宽度快照、历史和逐股K线缓存")
        print("  global-strip 直接读冻结快照（次日整天+周末不重算）；刷新页面即见真全A宽度。")
    else:
        print("  [--no-save/--limit] 未落盘正式宽度快照")

    print(f"⏱ 耗时 {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
