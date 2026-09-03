"""语义七前置验证（agent AD）——数据准备脚本。

产出（全部为新增文件，写入 docs/experiments/raw/overnight-us-cn-2026-09-03/）：
  - us_gspc_daily.parquet  标普500 日收盘（YahooPriceProvider，period=max，截取 2021 起）
  - us_ixic_daily.parquet  纳斯达克综合指数 日收盘（同上）
  - cn_breadth.parquet     全A MA 宽度（~/.lei_signal_lab/cache/a_share_ma_breadth_history.json，
                           ma20/ma50/ma200_pct = 全A 收盘价站上 20/50/200 日均线的股票占比%）
  - cn_csi300_daily.parquet 沪深300 OHLC（本地行情缓存 000300.SS.bars.parquet，腾讯前复权）
  - prep_summary.json      数据来源与范围说明（供报告引用与审计）

数据获取纪律：
  - 美股：复用 src/lei_signal/data/providers.py::YahooPriceProvider（现有 provider，
    不新建抓取方式）。指数无分红除权，auto_adjust 口径对指数即原始点位。
  - A 股宽度：读现有预计算缓存文件（scripts/precompute_a_share_ma.py 每日收盘后落盘）。
  - 沪深300：直接读本地 parquet 缓存（providers 链路的落盘产物）。

不修改任何现有文件；网络失败即报错退出（不编造数据）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.data.providers import YahooPriceProvider  # noqa: E402

RAW_DIR = REPO / "docs" / "experiments" / "raw" / "overnight-us-cn-2026-09-03"
CACHE = Path("/Users/yongbiaoli/.lei_signal_lab/cache")
BREADTH_JSON = CACHE / "a_share_ma_breadth_history.json"
CSI300_PARQUET = CACHE / "000300.SS.bars.parquet"

US_START = "2021-01-01"  # 仅截取，实际样本起点由 A 股宽度数据（2021-06-16）决定


def fetch_us(symbol: str) -> pd.DataFrame:
    provider = YahooPriceProvider()
    data = provider.fetch(symbol, min_rows=1000)
    bars = data.bars[["close"]].copy()
    bars = bars[bars.index >= pd.Timestamp(US_START)]
    if len(bars) < 800:
        raise RuntimeError(f"{symbol} 截取后仅 {len(bars)} 行，不足以覆盖 A 股宽度样本期")
    return bars


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    gspc = fetch_us("^GSPC")
    ixic = fetch_us("^IXIC")
    gspc.to_parquet(RAW_DIR / "us_gspc_daily.parquet")
    ixic.to_parquet(RAW_DIR / "us_ixic_daily.parquet")

    breadth_raw = json.loads(BREADTH_JSON.read_text())
    breadth = pd.DataFrame(breadth_raw)
    breadth["date"] = pd.to_datetime(breadth["date"])
    breadth = breadth.set_index("date").sort_index()
    breadth.to_parquet(RAW_DIR / "cn_breadth.parquet")

    csi = pd.read_parquet(CSI300_PARQUET)[["open", "close"]]
    csi = csi[csi.index >= pd.Timestamp("2021-01-01")]
    csi.to_parquet(RAW_DIR / "cn_csi300_daily.parquet")

    summary = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "us_source": "YahooPriceProvider (yfinance, auto_adjust, period=max), providers.py 现有源",
        "cn_breadth_source": str(BREADTH_JSON),
        "cn_index_source": f"{CSI300_PARQUET} (tencent 前复权, 000300.SS 沪深300)",
        "ranges": {
            "gspc": [str(gspc.index.min().date()), str(gspc.index.max().date()), len(gspc)],
            "ixic": [str(ixic.index.min().date()), str(ixic.index.max().date()), len(ixic)],
            "breadth": [str(breadth.index.min().date()), str(breadth.index.max().date()), len(breadth)],
            "csi300": [str(csi.index.min().date()), str(csi.index.max().date()), len(csi)],
        },
    }
    (RAW_DIR / "prep_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print(json.dumps(summary["ranges"], indent=2))


if __name__ == "__main__":
    main()
