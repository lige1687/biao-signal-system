"""指数版三形态对比：双线宽度仓位层 vs 买入持有（2026-08-27 第七轮）。

用户口径（事前写死）：
- 标的 = 指数（先不测个股）：美股 ^GSPC / ^IXIC / QQQ / SPY（宽度 =
  SP500 成分 B50/B200，1986 起，幸存者偏差声明）；A股 000300 沪深300 /
  399006 创业板指（宽度 = 全 A B50/B200，1993 起回填史）。
- 仓位层 = 双线双重确认（与第六轮同口径）：双低（B50&B200 同 <= L）→
  1.0；双高（同 >= H）→ 0.25；其间 → 0.6。档位 (20,80) 与 (15,85)。
- 对比 = WIDTH 双线仓位版 vs BH 买入持有（同窗、等额、5bp、周频判定
  次日开盘执行）；输出必须带时间跨度（用户要求）。
- 判定：无（效果展示）。黄金 518850 已定豁免宽度闸（用户拍板），
  不在本轮标的内。

纪律：纯实验脚本。输出 raw/breadth_overlay/index_showcase.csv
复现：python3 scripts/run_index_showcase.py（<1 分钟）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_symbol_showcase import (  # noqa: E402
    cagr_dd,
    dual_state_map,
    sim_bh,
    sim_width,
)

RAW = REPO / "docs/experiments/raw/breadth_overlay"
TIMING = Path.home() / ".lei_signal_lab/cache/timing"
COST = 0.0005


def load_index(name: str) -> pd.DataFrame:
    df = pd.read_parquet(TIMING / f"{name}.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["open", "close"]].astype(float).sort_index()


def load_us_breadth() -> pd.DataFrame:
    df = pd.read_parquet(TIMING / "breadth_sp500.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    out = df[["b50", "b200"]].astype(float)
    out.columns = ["ma50_pct", "ma200_pct"]
    return out.sort_index()


def main() -> None:
    cn_br = load_breadth()
    us_br = load_us_breadth()
    targets = [
        ("^GSPC 标普500", "us", "^GSPC"),
        ("^IXIC 纳指综合", "us", "^IXIC"),
        ("QQQ 纳指100ETF", "us", "QQQ"),
        ("SPY 标普500ETF", "us", "SPY"),
        ("000300 沪深300", "cn", "000300"),
        ("399006 创业板指", "cn", "399006"),
    ]
    rows = []
    for label, mkt, fname in targets:
        try:
            bars = load_index(fname)
        except FileNotFoundError:
            print(f"[skip] {label}: 无 {fname}.parquet")
            continue
        br = us_br if mkt == "us" else cn_br
        # 公平窗口：价格起点不早于宽度 b50 首个完整日（美股 1986-03-13）
        bstart = br["ma50_pct"].first_valid_index()
        bars = bars[bars.index >= bstart]
        br = br[br.index >= bars.index[0] - pd.Timedelta(days=400)]
        states = {"W_20_80": dual_state_map(br, 20.0, 80.0, 0.25),
                  "W_15_85": dual_state_map(br, 15.0, 85.0, 0.25)}
        rec = {"symbol": label,
               "span": f"{bars.index[0].date()} → {bars.index[-1].date()}"
                       f"（{(bars.index[-1]-bars.index[0]).days/365.25:.1f} 年）",
               "BH": cagr_dd(sim_bh(bars))}
        for k, sm in states.items():
            rec[k] = cagr_dd(sim_width(bars, sm))
        rows.append(rec)
        print(f"\n[{label}]  {rec['span']}")
        for k in ("BH", "W_20_80", "W_15_85"):
            m = rec[k]
            print(f"  {k:9s} 终值 {m['final']:>13,} 年化 {m['cagr']:+.1%}"
                  f" 回撤 {m['max_dd']:.1%}")
    pd.DataFrame([{"symbol": r["symbol"], "span": r["span"],
                   **{f"{k}_{m}": r[k][m] for k in
                      ("BH", "W_20_80", "W_15_85") for m in r[k]}}
                  for r in rows]).to_csv(RAW / "index_showcase.csv",
                                         index=False)
    (RAW / "index_showcase.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1, default=str))
    print(f"\n落盘: {RAW}/index_showcase.csv")


if __name__ == "__main__":
    main()
