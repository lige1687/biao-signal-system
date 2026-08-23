#!/usr/bin/env python3
"""回填标普500 市场宽度历史（MA20/50/200 上方占比），供叠加图/趋势图使用。

为什么需要它
------------
系统按「时点成分」(point-in-time universe) 计算宽度：
`universes/SP500.parquet` 里 503 只成分股的 effective_from 全是 2026-08-04
（wikipedia 抓取日），所以 2026-08-04 之前系统认为标普500「没有成分股」，
constituent_count=0、宽度写 NULL。这是设计上的诚实闸门，不是 bug——
它拒绝用今天的名单去算历史。

代价与取舍（务必知情）
----------------------
成分股日K只有当期 501 只（tests/fixtures/.../component_bars/，2024-08-16 起
每只 500 根），期间被剔除的公司没有行情，**真正的时点成分宽度算不出来**。
本脚本的做法是显式接受存活者偏差：把成分名单的 effective_from 回溯到第一根
K线那天，用当期名单倒推历史宽度。被剔除的公司通常是走弱后被踢，故历史宽度
会**系统性偏高**。为了让这个偏差可追溯：

  - 不改仓库里的 fixture（它记的时点语义是真的）；另建回填专用根目录，
    indices/component_bars 软链回仓库，只替换 universes/SP500.parquet
  - 回溯版名单的 source 标记为 `wikipedia_sp500_backdated`，该字符串会写进
    market_breadth_snapshot_revisions.provenance 列，DB 里一查即知

用法
----
    python scripts/backfill_sp500_breadth.py                  # 回填到今天
    python scripts/backfill_sp500_breadth.py --as-of 2026-08-14
    python scripts/backfill_sp500_breadth.py --no-backdate    # 只算真时点成分那几天

只删改 market_id='SP500' 的行（回填脚本按市场清revision后重写），不碰 A 股。
耗时约 1.7s/交易日，500 个交易日约 14 分钟。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BACKDATED_SOURCE = "wikipedia_sp500_backdated"


def _repo_fixtures() -> Path:
    root = REPO / "tests" / "fixtures" / "market_context"
    if not (root / "universes" / "SP500.parquet").exists():
        raise SystemExit(f"✗ 找不到成分名单: {root}/universes/SP500.parquet")
    if not (root / "component_bars" / "AAPL.parquet").exists():
        raise SystemExit(
            f"✗ 找不到成分股日K: {root}/component_bars/AAPL.parquet\n"
            "  没有成分股行情就算不出宽度（不会伪造）。",
        )
    return root


def _earliest_bar_date(fixtures: Path, sample: int = 40) -> date:
    """成分股日K里最早的交易日——回溯生效日不该早于它（早了也没数据）。"""
    import pandas as pd

    bars = sorted((fixtures / "component_bars").glob("*.parquet"))
    us = [p for p in bars if p.stem.replace(".", "").isalpha()][:sample]
    firsts: list[date] = []
    for p in us:
        try:
            df = pd.read_parquet(p, columns=["date"])
        except Exception:  # noqa: BLE001
            continue
        if not df.empty:
            firsts.append(pd.to_datetime(df["date"]).min().date())
    if not firsts:
        raise SystemExit("✗ 成分股日K为空，无法确定回溯起点")
    return min(firsts)


def _build_backfill_root(fixtures: Path, backdate_to: date | None) -> Path:
    """搭一个回填专用的 fixture 根：软链行情、只替换成分名单。"""
    import pandas as pd

    root = Path.home() / ".lei_signal_lab" / "sp500_backfill_root"
    mc = root / "fixtures" / "market_context"
    (mc / "universes").mkdir(parents=True, exist_ok=True)

    for name in ("indices", "component_bars", "sentiment"):
        src, dst = fixtures / name, mc / name
        if not src.exists():
            continue
        if dst.is_symlink() or dst.exists():
            dst.unlink() if dst.is_symlink() else None
        if not dst.exists():
            dst.symlink_to(src, target_is_directory=True)

    for p in (fixtures / "universes").glob("*.parquet"):
        dst = mc / "universes" / p.name
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        if p.stem == "SP500" and backdate_to is not None:
            df = pd.read_parquet(p)
            df["effective_from"] = pd.Timestamp(backdate_to).date().isoformat()
            df["source"] = BACKDATED_SOURCE
            df["source_version"] = f"{df['source_version'].iloc[0]}+backdated_{backdate_to}"
            df.to_parquet(dst, index=False)
            print(f"  成分名单: {len(df)} 只，effective_from 回溯至 {backdate_to}，"
                  f"source={BACKDATED_SOURCE}")
        else:
            dst.symlink_to(p)
    return root


def _coverage(db: Path) -> None:
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            """SELECT COUNT(*), SUM(breadth_20 IS NOT NULL), SUM(breadth_50 IS NOT NULL),
                      SUM(breadth_200 IS NOT NULL), MIN(as_of), MAX(as_of)
                 FROM market_breadth_snapshot_revisions WHERE market_id='SP500'""",
        ).fetchone()
        n, b20, b50, b200, first, last = row
        print(f"✓ SP500 宽度快照 {n} 行（{first} ~ {last}）")
        print(f"  有值: B20={b20}  B50={b50}  B200={b200}")
        win = conn.execute(
            """SELECT MIN(as_of), MAX(as_of) FROM market_breadth_snapshot_revisions
                WHERE market_id='SP500' AND breadth_50 IS NOT NULL""",
        ).fetchone()
        if win[0]:
            print(f"  B50 覆盖窗口: {win[0]} ~ {win[1]}")
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="回填标普500 宽度历史")
    ap.add_argument("--as-of", default=None, help="回填截止日（默认今天）")
    ap.add_argument("--no-backdate", action="store_true",
                    help="不回溯成分生效日（只算真时点成分覆盖的那几天）")
    args = ap.parse_args(argv)
    as_of_max = date.fromisoformat(args.as_of) if args.as_of else date.today()

    fixtures = _repo_fixtures()
    backdate_to = None if args.no_backdate else _earliest_bar_date(fixtures)
    if backdate_to:
        print(f"▶ 搭回填根目录（存活者偏差已知情，起点 {backdate_to}）…")
    else:
        print("▶ 搭回填根目录（--no-backdate：严格时点成分）…")
    root = _build_backfill_root(fixtures, backdate_to)

    # cache_root() 每次调用都读环境变量；DB 路径不受它影响（走 DEFAULT_CACHE_DIR.parent）
    os.environ["LEI_CACHE_ROOT"] = str(root)
    from lei_signal.api import config  # noqa: E402
    from lei_signal.market_context.types import MarketId  # noqa: E402
    from scripts.round5_repro.backfill_breadth_history import backfill  # noqa: E402

    db = Path(config.sqlite_path())
    print(f"▶ 回填 SP500 → {db}（只动 market_id='SP500' 的行）…")
    rc = backfill(as_of_max=as_of_max, market_ids=(MarketId.SP500,))
    if rc != 0:
        return rc
    _coverage(db)
    print("提示：宽度历史由后端 /market-context/breadth-history 直读 DB，无需重启后端。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
