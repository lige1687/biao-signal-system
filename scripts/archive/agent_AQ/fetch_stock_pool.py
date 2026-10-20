#!/usr/bin/env python3
"""任务 AQ（前置）：高流动性 A 股个股池数据抓取 · 名单跑前写死。

【标的池（跑前固化，2026-09-03）】15 只，按当前市值/流动性挑选（全部为
千亿级市值、日成交额长期居前的大盘蓝筹；跨 13 个行业）：

  600519.SS 贵州茅台(白酒)      000858.SZ 五粮液(白酒)
  601318.SS 中国平安(保险)      600036.SS 招商银行(银行)
  300750.SZ 宁德时代(新能源电池, 2018-06 上市, 样本起点晚于 2016 如实登记)
  002594.SZ 比亚迪(新能源整车)  600900.SS 长江电力(公用事业)
  601899.SS 紫金矿业(有色金属)  000333.SZ 美的集团(家电)
  600030.SS 中信证券(券商)      600276.SS 恒瑞医药(医药)
  002415.SZ 海康威视(电子)      000063.SZ 中兴通讯(通信)
  601857.SS 中国石油(石油石化)  000725.SZ 京东方A(面板/消费电子)

【幸存者偏差（大白话）】这份名单是"今天还活着、而且活得很大"的公司。
用它们回测历史，天然高估收益——当年同样大但后来衰败的公司不在样本里。
这是本测试的已知上限，结论只能用于方向性判断。

【抓取方式】复用仓库现有腾讯分页先例（scripts/backfill_tencent_paged.py）：
同一接口（web.ifzq.gtimg.cn fqkline/get）、同一窗口切分（2016-01-01 起 5 个
两年窗、每窗 800 根）、同一行格式解析（与 providers.TencentPriceProvider
._parse_payload 的 qfqday 分支同构）。落盘到本任务自己的池目录（不动
~/.lei_signal_lab 共享缓存）：
  docs/experiments/raw/agent_AQ/pool/{sym}.bars.parquet（provider=tencent）

【复权口径：hfq（后复权），跑前定死】实测腾讯 qfq（前复权）对长历史大额
分红个股会"负值化"：贵州茅台 2016 年起 qfq 价格为负（负数域里 OHLC 大小
关系翻转，validate_bars 拒收 125 行）、宁德时代 2018-19 窗口 qfqday 直接
为空、紫金矿业 qfq 序列出现 0.45/1.68 等乱比率——qfq 口径对个股长历史
客观不可用（先例 backfill_tencent_paged 的标的是 ETF，分红极少无此问题）。
改用同一接口的 hfq（后复权）：对同一只股票，hfq 与 qfq 在除权日之外只差
乘性正常数，均线密集/突破/止损/R 归一全部计算在两口径下数学等价（Y 任务
已实证模块B 的 R 倍数对价格整体乘性平移不敏感）；hfq 价格恒为正。全池
15 只统一 hfq，不混用。

【复权修正（必须步，规则来自 scripts/agent_AK/extreme_bottom_event_study.py）】
机械兜底规则原样执行（防送转除权残留假跳变）：任一隔夜收盘比 >1.5 或
<1/1.5 视为公司行为，把跳变日之前全部价格（open/high/low/close 四列同乘，
AK 原版仅 close、此处推广到 OHLC，ratio 由 close 计算）乘以该比率做前复权。
修正后重扫直至无 >1.5 跳变。每只标的的 jump 清单如实写进 manifest。
（hfq 口径下除权日应连续，预期 jump 为空；非空即数据异常的如实记录。）

【合法性扫描（登记不修改）】主板(60/00 开头) |单日收益|>11%、创业板(300 开头)
2020-08-24 后 |单日收益|>21% 的大幅日登记为 big_days（学习 Y 任务 F2 取证）。

输出：docs/experiments/raw/agent_AQ/pool_manifest.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.data.providers import DataUnavailableError, TencentPriceProvider  # noqa: E402
from lei_signal.data.symbols import is_a_share, resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402
from lei_signal.data.cache import ParquetCache  # noqa: E402

POOL_ROOT = REPO / "docs/experiments/raw/agent_AQ/pool"
MANIFEST = REPO / "docs/experiments/raw/agent_AQ/pool_manifest.json"

# (symbol, 简称, 行业, 板)——板用于大幅日合法性判断
STOCK_POOL: tuple[tuple[str, str, str, str], ...] = (
    ("600519.SS", "贵州茅台", "白酒", "main"),
    ("000858.SZ", "五粮液", "白酒", "main"),
    ("601318.SS", "中国平安", "保险", "main"),
    ("600036.SS", "招商银行", "银行", "main"),
    ("300750.SZ", "宁德时代", "新能源电池", "chinext"),
    ("002594.SZ", "比亚迪", "新能源整车", "main"),
    ("600900.SS", "长江电力", "公用事业", "main"),
    ("601899.SS", "紫金矿业", "有色金属", "main"),
    ("000333.SZ", "美的集团", "家电", "main"),
    ("600030.SS", "中信证券", "券商", "main"),
    ("600276.SS", "恒瑞医药", "医药", "main"),
    ("002415.SZ", "海康威视", "电子", "main"),
    ("000063.SZ", "中兴通讯", "通信", "main"),
    ("601857.SS", "中国石油", "石油石化", "main"),
    ("000725.SZ", "京东方A", "面板/消费电子", "main"),
)

WINDOWS: tuple[tuple[str, str], ...] = (
    ("2016-01-01", "2017-12-31"),
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2026-12-31"),
)
SLEEP = 0.5
OHLC = ("open", "high", "low", "close")


def fetch_windowed(provider: TencentPriceProvider, symbol: str) -> pd.DataFrame:
    """与 backfill_tencent_paged.fetch_windowed 同构（窗口分页 + 合并去重）。

    唯一差异：fq 参数用 hfq（后复权）——理由见 docstring【复权口径】节。
    行解析与 TencentPriceProvider._parse_payload 的 qfqday 分支同构。
    """
    info = resolve_symbol(symbol)
    if not is_a_share(info):
        raise ValueError(f"{symbol} 不是 A 股标的")
    code = provider._tencent_symbol(info)
    frames: list[pd.DataFrame] = []
    for start, end in WINDOWS:
        params = {"param": f"{code},day,{start},{end},800,hfq"}
        url = f"{provider._HOST}?{urllib.parse.urlencode(params)}"
        payload = json.loads(provider._fetch_text(url))
        if int(payload.get("code", 0)) != 0:
            raise DataUnavailableError(
                f"{symbol} 腾讯返回错误：code={payload.get('code')} msg={payload.get('msg')!r}")
        market_data = next((v for v in payload.get("data", {}).values()
                            if isinstance(v, dict)), None)
        if market_data is None:
            raise DataUnavailableError(f"{symbol} 腾讯返回缺少行情子对象")
        rows = market_data.get("hfqday")
        if not isinstance(rows, list) or not rows:
            # 与先例 backfill_tencent_paged 一致：空窗口跳过（上市前窗口）
            time.sleep(SLEEP)
            continue
        records = []
        for item in rows:
            records.append({"date": item[0], "open": float(item[1]),
                            "close": float(item[2]), "high": float(item[3]),
                            "low": float(item[4]), "volume": float(item[5])})
        frame = pd.DataFrame(records)
        frame["date"] = pd.to_datetime(frame["date"])
        frames.append(frame.set_index("date"))
        time.sleep(SLEEP)
    if not frames:
        raise DataUnavailableError(f"{symbol} 所有窗口均无数据（未上市或代码错误）")
    merged = pd.concat(frames)
    return merged[~merged.index.duplicated(keep="last")].sort_index()


def adjust_corporate_actions(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """AK 机械复权兜底（隔夜比 >1.5/<1/1.5 前复权），推广到 OHLC 四列。"""
    out = df.copy()
    jumps: list[dict] = []
    while True:
        ret = out["close"] / out["close"].shift(1)
        bad = ret.index[(ret > 1.5) | (ret < 1 / 1.5)]
        if len(bad) == 0:
            return out, jumps
        ts = bad[0]
        pos = out.index.get_loc(ts)
        ratio = float(out["close"].iloc[pos] / out["close"].iloc[pos - 1])
        out.loc[out.index[:pos], list(OHLC)] = out.loc[out.index[:pos], list(OHLC)] * ratio
        jumps.append({"date": str(pd.Timestamp(ts).date()), "overnight_ratio": round(ratio, 4)})


def scan_big_days(bars: pd.DataFrame, board: str) -> list[dict]:
    ret = bars["close"].pct_change(fill_method=None)
    limit = 0.21 if board == "chinext" else 0.11
    # 创业板 2020-08-24 注册制改革前仍为 ±10%
    out = []
    for ts, v in ret[ret.abs() > limit].items():
        d = pd.Timestamp(ts)
        if board == "chinext" and d < pd.Timestamp("2020-08-24"):
            continue
        out.append({"date": str(d.date()), "ret": round(float(v), 4)})
    return out


def main() -> None:
    POOL_ROOT.mkdir(parents=True, exist_ok=True)
    provider = TencentPriceProvider()
    cache = ParquetCache(POOL_ROOT)
    manifest = []
    for sym, name, industry, board in STOCK_POOL:
        try:
            merged = fetch_windowed(provider, sym)
            merged = merged[merged.index >= pd.Timestamp("2016-01-01")]
            fixed, jumps = adjust_corporate_actions(merged)
            bars, _ = validate_bars(fixed, symbol=sym, provider="tencent",
                                    adjusted=True, min_rows=21)
        except (DataUnavailableError, ValueError) as exc:
            print(f"[FAIL] {sym} {name}: {type(exc).__name__}: {exc}")
            manifest.append({"symbol": sym, "name": name, "industry": industry,
                             "board": board, "ok": False, "error": str(exc)})
            continue
        big = scan_big_days(bars, board)
        cache.write(sym, bars, provider="tencent")
        entry = {
            "symbol": sym, "name": name, "industry": industry, "board": board,
            "ok": True, "rows": int(len(bars)),
            "start": str(bars.index[0].date()), "end": str(bars.index[-1].date()),
            "adjusted": "hfq", "corp_action_jumps": jumps, "big_days": big,
        }
        manifest.append(entry)
        print(f"[OK] {sym} {name}: {len(bars)} 根 {entry['start']}~{entry['end']} "
              f"jumps={jumps} big_days={len(big)}")
    MANIFEST.write_text(json.dumps(
        {"fetched_at": "2026-09-03", "pool": manifest,
         "windows": [list(w) for w in WINDOWS], "fq": "hfq",
         "adjust_rule": "AK: 隔夜收盘比 >1.5 或 <1/1.5 → 跳变日前 OHLC 同乘比率（前复权连续化），迭代至无跳变"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for m in manifest if m["ok"])
    print(f"完成 {ok}/{len(STOCK_POOL)}，manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
