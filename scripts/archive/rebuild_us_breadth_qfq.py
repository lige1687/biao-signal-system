"""美股专项 Phase 0 收尾：用复权矩阵重建 SP500 宽度并替换旧数据。

前置：us_qfq_matrix.parquet 就绪（fetch_us_pool.py）。
动作（全部有备份）：
  1. breadth_sp500.parquet ← 复权口径 B20/B50/B200（旧文件备份 .unadjusted.bak）
  2. sp500_klines.parquet ← 复权矩阵（旧备份 .unadjusted.bak；siphon 美股等权受益）
  3. 打印新旧宽度的关键差异（末日 B 值、高区时间占比）供入册
用法：python3.11 scripts/rebuild_us_breadth_qfq.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import TIMING_CACHE_DIR, compute_breadth_from_close_matrix

CACHE = TIMING_CACHE_DIR.parent
MATRIX = CACHE / "us_qfq_matrix.parquet"


def main() -> int:
    if not MATRIX.exists():
        print(f"缺 {MATRIX}，先跑 scripts/fetch_us_pool.py")
        return 1
    wide = pd.read_parquet(MATRIX)
    new_b = compute_breadth_from_close_matrix(wide)

    old_breadth = TIMING_CACHE_DIR / "breadth_sp500.parquet"
    old_klines = CACHE / "sp500_klines.parquet"
    if old_breadth.exists() and not old_breadth.with_suffix(".unadjusted.bak").exists():
        shutil.copy2(old_breadth, old_breadth.with_suffix(".unadjusted.bak"))
    if old_klines.exists() and not old_klines.with_suffix(".unadjusted.bak").exists():
        shutil.copy2(old_klines, old_klines.with_suffix(".unadjusted.bak"))

    # 裁到 1986-01 起：与旧口径同一起点，避免早年成分过少（<100 只）的噪声
    new_b = new_b.loc["1986-01-01":]
    new_b.to_parquet(old_breadth)
    wide.to_parquet(old_klines)

    old = pd.read_parquet(old_breadth.with_suffix(".unadjusted.bak"))
    merged = new_b.join(old, rsuffix="_old", how="inner")
    print(f"复权宽度: {new_b.index[0].date()}→{new_b.index[-1].date()} {len(new_b)} 行")
    last = merged.iloc[-1]
    print(
        f"末日 B200: 复权 {last['b200']:.1f} vs 未复权 {last['b200_old']:.1f} | "
        f"B50: {last['b50']:.1f} vs {last['b50_old']:.1f}"
    )
    hi_new = (new_b["b200"] >= 56.7).mean()
    hi_old = (old["b200"] >= 56.7).mean()
    print(f"B200≥56.7 时间占比: 复权 {hi_new:.0%} vs 未复权 {hi_old:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
