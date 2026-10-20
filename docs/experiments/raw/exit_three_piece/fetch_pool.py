#!/usr/bin/env python3
"""任务 J（a6_5 三件套）· 环境重建第一步：从腾讯源重建参考池。

背景（2026-09-02 数据工程现状，必须先读）：
- 8-31 出场矩阵与 9-1 两轮出场实验所依赖的回测深池
  （``~/.lei_signal_lab/backtest_pool``，175 标的，东财 10 年回填）已从磁盘
  消失，且池成分未入 git；stash a816485f（v2 检测器富版本）与 9-1 的
  工作台历史 run 记录（``~/.lei_signal_lab/backtest_runs/*.json``）也已丢失
  （本仓库为 fresh clone，reflog 仅 3 条，stash 对象不存在）。
- 幸存锚点：``raw/lifecycle_combo/`` 下三个 git 归档 run JSON（2026-08-27
  工作台产出，含全量逐笔行）——
    A : T2_A_ETF_cm05_shrink.json  early+shrink+cm0.5+a6_1，45 ETF，283 笔
    B': T1_Bp_a61.json             breakout+cb30/cl3%+a6_1，83 个股，101 笔
    C : T2_C_stocks_v3_b15.json    v3+bias−15%+a6_1，       83 个股，177 笔
  逐笔行带 symbol/signal_date/stop_price/target_price/reward_risk 等全部
  spec 契约字段（与 9-1 stop-loss-matrix 的「参考 run 逐笔反构」同源做法）。
- 本脚本把这三个 run 的标的并集（127 个，全部 A 股）用腾讯分页接口
  （backfill_tencent_paged.py 同款 Plan B；东财源在本机网络不可达）回填
  2016-01→今的前复权日线，裁齐到参考数据窗起点 2016-08-24，写入
  ``raw/exit_three_piece/pool/``，供主实验脚本以
  ``LEI_BACKTEST_POOL_ROOT`` 指向使用。

已知偏差（报告必须复述）：参考 run 数据为东财 fqt=1 前复权（2026-08-27
抓取），本池为腾讯 qfq 前复权（2026-09-02 抓取）——两家复权因子与抓取日
不同，历史价格存在小幅漂移；specs 直接取自参考 run 逐笔行（不受漂移影响），
模拟层数值（ATR/抵扣价条件时点）受漂移影响，由主脚本的逐笔锚定校验量化。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.data.cache import ParquetCache  # noqa: E402
from lei_signal.data.providers import (  # noqa: E402
    DataUnavailableError,
    TencentPriceProvider,
)
from lei_signal.data.symbols import is_a_share, resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402

RAW_DIR = REPO / "docs/experiments/raw/exit_three_piece"
POOL_DIR = RAW_DIR / "pool"
REF_DIR = REPO / "docs/experiments/raw/lifecycle_combo"
REFERENCE_RUNS = {
    "A": "T2_A_ETF_cm05_shrink.json",
    "B": "T1_Bp_a61.json",
    "C": "T2_C_stocks_v3_b15.json",
}

WINDOWS: tuple[tuple[str, str], ...] = (
    ("2016-01-01", "2017-12-31"),
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2026-12-31"),
)
SLEEP = 1.0
TRIM_START = "2016-08-24"  # 参考run data_range.start（三 run 一致）
MAX_PASSES = 6  # 断点续跑：每轮只补缺失标的，连续两轮无进展则放弃


def fetch_windowed(provider: TencentPriceProvider, symbol: str) -> pd.DataFrame:
    info = resolve_symbol(symbol)
    if not is_a_share(info):
        raise ValueError(f"{symbol} 不是 A 股标的")
    code = provider._tencent_symbol(info)
    frames: list[pd.DataFrame] = []
    adjusted_flags: set[bool] = set()
    # web.ifzq.gtimg.cn 被腾讯 WAF 拦截（HTTP 501，2026-09-02）；
    # proxy.finance.qq.com 为同数据备用入口（qfq 口径一致）。
    hosts = (
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get",
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
    )
    last_exc: Exception | None = None
    for host in hosts:
        frames = []
        adjusted_flags = set()
        try:
            for start, end in WINDOWS:
                params = {"param": f"{code},day,{start},{end},800,qfq"}
                url = f"{host}?{urllib.parse.urlencode(params)}"
                try:
                    frame, adjusted = provider._parse_payload(
                        provider._fetch_text(url), symbol
                    )
                except DataUnavailableError as exc:
                    if "未返回 qfqday/day" in str(exc):
                        time.sleep(SLEEP)
                        continue
                    raise
                if not frame.empty:
                    frames.append(frame)
                    adjusted_flags.add(adjusted)
                time.sleep(SLEEP)
            if frames and len(adjusted_flags) == 1:
                break
            if not frames:
                raise ValueError(f"{symbol} {host} 所有窗口均无数据")
            raise ValueError(f"{symbol} {host} 复权口径不一致: {adjusted_flags}")
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
    if not frames:
        raise ValueError(f"{symbol} 全部入口失败: {last_exc}")
    out = pd.concat(frames)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out[out.index >= pd.Timestamp(TRIM_START)]
    # 腾讯 qfq 对高股息个股的减法复权会把最早年份调成非正价；这些行的
    # 参考信号全部在 2018+（远离截断点），裁掉非正价前缀后重验。
    price_cols = [c for c in ("open", "high", "low", "close") if c in out.columns]
    if price_cols and (out[price_cols] <= 0).any().any():
        ok_mask = (out[price_cols] > 0).all(axis=1)
        first_ok = out.index[ok_mask][0] if ok_mask.any() else None
        if first_ok is not None:
            out = out[out.index >= first_ok]
            # 前缀之外若仍有零星非正价行（不应发生），直接剔除该行
            out = out[(out[price_cols] > 0).all(axis=1)]
    return out


def main() -> None:
    symbols: set[str] = set()
    ref_meta: dict[str, dict] = {}
    for mkey, fname in REFERENCE_RUNS.items():
        data = json.loads((REF_DIR / fname).read_text(encoding="utf-8"))
        sym_list = data["params"]["symbols"]
        symbols.update(sym_list)
        ref_meta[mkey] = {
            "file": f"raw/lifecycle_combo/{fname}",
            "run_id": data["run_id"],
            "trades": len(data["trades"]),
            "symbols": len(sym_list),
            "data_start": data["data_range"]["start"],
            "data_end": data["data_range"]["end"],
        }
    pool_symbols = sorted(symbols)
    print(f"参考 run 并集 {len(pool_symbols)} 标的；写入 {POOL_DIR}")
    (RAW_DIR / "pool_manifest.json").write_text(
        json.dumps(
            {"reference_runs": ref_meta, "pool_symbols": pool_symbols,
             "trim_start": TRIM_START, "windows": [list(w) for w in WINDOWS],
             "fetch_date": "2026-09-02"},
            ensure_ascii=False, indent=1, sort_keys=True,
        ),
        encoding="utf-8",
    )

    provider = TencentPriceProvider(attempts=2, backoff=3.0)
    cache = ParquetCache(str(POOL_DIR))
    rows_report: dict[str, int] = {}
    # 恢复上一轮已抓取的行数记录
    prev_rows = RAW_DIR / "pool_rows.json"
    if prev_rows.exists():
        rows_report.update(json.loads(prev_rows.read_text(encoding="utf-8")))
    failures: list[str] = []
    todo = [s for s in pool_symbols if s not in rows_report]
    print(f"待抓 {len(todo)} / 总 {len(pool_symbols)}（断点续跑）")
    for _pass in range(1, MAX_PASSES + 1):
        if not todo:
            break
        print(f"--- 第 {_pass} 轮，剩 {len(todo)} 标的 ---", flush=True)
        still_missing: list[str] = []
        for i, symbol in enumerate(todo, 1):
            try:
                frame = fetch_windowed(provider, symbol)
                bars, _report = validate_bars(
                    frame, symbol=symbol, provider="tencent", adjusted=True,
                    min_rows=300,
                )
                cache.write(symbol, bars, provider="tencent")
                rows_report[symbol] = len(bars)
            except Exception as exc:  # noqa: BLE001
                still_missing.append(symbol)
                if i % 10 == 0 or i == len(todo):
                    print(f"[{_pass}:{i}/{len(todo)}] {symbol} 失败: {exc}",
                          flush=True)
                continue
            if i % 20 == 0:
                print(f"[{_pass}:{i}/{len(todo)}] ok", flush=True)
                (RAW_DIR / "pool_rows.json").write_text(
                    json.dumps(rows_report, ensure_ascii=False, indent=1,
                               sort_keys=True),
                    encoding="utf-8",
                )
            time.sleep(SLEEP)
        if len(still_missing) == len(todo):
            print("本轮零进展，停止重试", flush=True)
            failures = still_missing
            break
        todo = still_missing
        # 轮间长歇，等限流窗口过去
        time.sleep(30.0)
    (RAW_DIR / "pool_rows.json").write_text(
        json.dumps(rows_report, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    missing = [s for s in pool_symbols if s not in rows_report]
    print(f"完成：成功 {len(rows_report)} / 缺失 {len(missing)}")
    if missing:
        print("缺失清单：")
        for f in missing:
            print("  ", f)


if __name__ == "__main__":
    main()
