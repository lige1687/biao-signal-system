"""SP500 宽度 → SQLite snapshot/revision 表的入库脚本。

背景
----
前端 `FundamentalsPage` 的「美股 × 10Y国债」叠图展示 SP500 宽度（来自
`/api/market-context/breadth-history?market_id=SP500`）。后端实现是
`MarketContextService.get_breadth_history()`，它**直接读 SQLite** 的
`market_breadth_snapshot_revisions` 表，并不读 cache JSON 文件。

旧 SP500 行（2024-08-16 → 2026-08-18，共 530 行）全是「空壳」快照——
`breadth_20/50/200 = NULL`、`eligible_20/50/200 = 0`、
`data_status='incomplete'/'unavailable'`。SQL `WHERE data_status NOT IN
('stale','unavailable')` 把这些全过滤掉，导致前端拿到 0 行、判
`degenerate=true`、显示「数据缺失」横幅。

本脚本做的事：
1. 用 `cache/sp500_klines.parquet`（成分股收盘价透视表）+ 我已重算的
   `cache/sp500_ma_breadth_history.json` 读出每日 B20/B50/B200 与
   `eligible_20/50/200`（与项目 `compute_breadth` 一致的 ffill 算法）。
2. 删 lab.db 里 `market_id='SP500'` 的全部旧快照行
   （incomplete/unavailable，对当前显示零信息价值）。
3. 写入 `market_breadth_snapshot_revisions` 与 `market_breadth_snapshots`
   两张表，`data_status='complete'`，覆盖 1986-01-29 → 今天。

注意事项
--------
* WAL 模式 + 30s busy_timeout，后端进程运行时也能并发写入。
* 该操作是**幂等覆盖**：旧 SP500 行先 DELETE 再 INSERT，再次执行只会
  把同一批数据重写一遍。
* 不动任何其他市场的快照（CN_ALL_A 等保持原样）。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

CACHE_ROOT = Path.home() / ".lei_signal_lab" / "cache"
DB_PATH = Path.home() / ".lei_signal_lab" / "lab.db"
JSON_PATH = CACHE_ROOT / "sp500_ma_breadth_history.json"
PARQUET_PATH = CACHE_ROOT / "sp500_klines.parquet"

MARKET_ID = "SP500"
RUN_ID = "backfill:sp500_components_v1"
PROVENANCE = "sp500_components_wikipedia+akshare_sina_v1"
UNIVERSE_VERSION = "backfill_v1"
DATA_STATUS = "complete"
SOURCE_KIND = "formal"
REVISION_NO = 1

WINDOWS = (20, 50, 200)
MIN_ELIGIBLE = 100

INSERT_REV_SQL = """
INSERT INTO market_breadth_snapshot_revisions (
    market_id, as_of, universe_version, revision_no, available_at,
    run_id, source_kind, provenance, data_status,
    constituent_count, eligible_20, eligible_50, eligible_200,
    missing_20, missing_50, missing_200,
    coverage_20, coverage_50, coverage_200,
    breadth_20, breadth_50, breadth_200,
    percentile_20, percentile_50, percentile_200
) VALUES (
    :market_id, :as_of, :universe_version, :revision_no, :available_at,
    :run_id, :source_kind, :provenance, :data_status,
    :constituent_count, :eligible_20, :eligible_50, :eligible_200,
    :missing_20, :missing_50, :missing_200,
    :coverage_20, :coverage_50, :coverage_200,
    :breadth_20, :breadth_50, :breadth_200,
    :percentile_20, :percentile_50, :percentile_200
)
"""

INSERT_SNAP_SQL = """
INSERT INTO market_breadth_snapshots (
    market_id, as_of, available_at, universe_version,
    constituent_count, eligible_20, eligible_50, eligible_200,
    missing_20, missing_50, missing_200,
    coverage_20, coverage_50, coverage_200,
    breadth_20, breadth_50, breadth_200,
    percentile_20, percentile_50, percentile_200,
    source_kind, provenance, data_status, run_id
) VALUES (
    :market_id, :as_of, :available_at, :universe_version,
    :constituent_count, :eligible_20, :eligible_50, :eligible_200,
    :missing_20, :missing_50, :missing_200,
    :coverage_20, :coverage_50, :coverage_200,
    :breadth_20, :breadth_50, :breadth_200,
    :percentile_20, :percentile_50, :percentile_200,
    :source_kind, :provenance, :data_status, :run_id
)
"""


def _load_eligible_counts(parquet_path: Path) -> tuple[dict, int]:
    """从成分股 parquet 重算每窗口的当日合格样本数（ffill 抹平停牌）。"""
    piv = pd.read_parquet(parquet_path).sort_index()
    if piv.empty:
        return {}, 0
    constituent_count = int(piv.shape[1])
    piv_ff = piv.ffill()
    elig_by_window: dict[int, pd.Series] = {}
    for w in WINDOWS:
        ma = piv_ff.rolling(w).mean()
        elig = piv.notna() & ma.notna()
        elig_by_window[w] = elig.sum(axis=1).astype("int64")
    # 序列化为 dict[date_str -> int] 便于按日查
    out: dict[str, dict[int, int]] = {w: {} for w in WINDOWS}
    for d in piv.index:
        ds = pd.Timestamp(d).strftime("%Y-%m-%d")
        for w in WINDOWS:
            v = elig_by_window[w].get(d)
            out[w][ds] = int(v) if pd.notna(v) else 0
    return out, constituent_count


def ingest(dry_run: bool = False) -> int:
    if not JSON_PATH.exists():
        print(f"ERR: {JSON_PATH} 不存在，请先跑 backfill_breadth_full.py --market us", file=sys.stderr)
        return 2
    if not PARQUET_PATH.exists():
        print(f"ERR: {PARQUET_PATH} 不存在", file=sys.stderr)
        return 2
    if not DB_PATH.exists():
        print(f"ERR: {DB_PATH} 不存在", file=sys.stderr)
        return 2

    hist = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    print(f"[ingest_sp500_breadth_to_sqlite] history {len(hist)} 天 "
          f"({hist[0]['date']} → {hist[-1]['date']})")

    elig_by_window, constituent_count = _load_eligible_counts(PARQUET_PATH)
    print(f"[ingest_sp500_breadth_to_sqlite] constituent_count={constituent_count}")

    if dry_run:
        # 报告待清理/写入范围
        print(f"  DRY: 将清掉 SP500 旧行；将 INSERT {len(hist)} 行到两张表")
        # 抽样三段
        for d in (hist[0]["date"], hist[len(hist) // 2]["date"], hist[-1]["date"]):
            r = next((h for h in hist if h["date"] == d), None)
            e20 = elig_by_window[20].get(d, 0)
            e50 = elig_by_window[50].get(d, 0)
            e200 = elig_by_window[200].get(d, 0)
            print(f"    {d}  B20={r['breadth_20']} B50={r['breadth_50']} B200={r['breadth_200']}"
                  f"  elig20={e20} elig50={e50} elig200={e200}")
        return 0

    print("[ingest_sp500_breadth_to_sqlite] opening sqlite (WAL + 30s busy_timeout)")
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        cur = conn.cursor()
        # 1. 记录删除前
        prev_rev = cur.execute(
            "SELECT COUNT(*) FROM market_breadth_snapshot_revisions WHERE market_id=?",
            (MARKET_ID,),
        ).fetchone()[0]
        prev_snap = cur.execute(
            "SELECT COUNT(*) FROM market_breadth_snapshots WHERE market_id=?",
            (MARKET_ID,),
        ).fetchone()[0]
        print(f"  旧 SP500 rows: revisions={prev_rev}, snapshots={prev_snap}")
        # 2. 清旧
        cur.execute("DELETE FROM market_breadth_snapshot_revisions WHERE market_id=?", (MARKET_ID,))
        cur.execute("DELETE FROM market_breadth_snapshots WHERE market_id=?", (MARKET_ID,))
        print("  已 DELETE 全部旧 SP500 行")
        # 3. 写新
        n_inserted = 0
        batch: list[dict] = []
        BATCH_SIZE = 500
        for h in hist:
            d = h["date"]
            e20 = elig_by_window[20].get(d, 0)
            e50 = elig_by_window[50].get(d, 0)
            e200 = elig_by_window[200].get(d, 0)
            m20 = max(constituent_count - e20, 0)
            m50 = max(constituent_count - e50, 0)
            m200 = max(constituent_count - e200, 0)
            cov = lambda num, den: (num / den) if den else 0.0  # noqa: E731
            common = dict(
                market_id=MARKET_ID,
                as_of=d,
                universe_version=UNIVERSE_VERSION,
                revision_no=REVISION_NO,
                available_at=d,
                run_id=RUN_ID,
                source_kind=SOURCE_KIND,
                provenance=PROVENANCE,
                data_status=DATA_STATUS,
                constituent_count=constituent_count,
                eligible_20=e20, eligible_50=e50, eligible_200=e200,
                missing_20=m20, missing_50=m50, missing_200=m200,
                coverage_20=cov(e20, constituent_count),
                coverage_50=cov(e50, constituent_count),
                coverage_200=cov(e200, constituent_count),
                breadth_20=h.get("breadth_20"),
                breadth_50=h.get("breadth_50"),
                breadth_200=h.get("breadth_200"),
                percentile_20=None,
                percentile_50=None,
                percentile_200=None,
            )
            batch.append(common)
            if len(batch) >= BATCH_SIZE:
                cur.executemany(INSERT_REV_SQL, batch)
                cur.executemany(INSERT_SNAP_SQL, batch)
                conn.commit()
                n_inserted += len(batch)
                batch.clear()
        if batch:
            cur.executemany(INSERT_REV_SQL, batch)
            cur.executemany(INSERT_SNAP_SQL, batch)
            conn.commit()
            n_inserted += len(batch)
        print(f"  INSERT 完成：{n_inserted} 行 × 2 张表")
        # 4. 校验
        n_rev_complete = cur.execute(
            "SELECT COUNT(*) FROM market_breadth_snapshot_revisions "
            "WHERE market_id=? AND data_status='complete'",
            (MARKET_ID,),
        ).fetchone()[0]
        n_snap_complete = cur.execute(
            "SELECT COUNT(*) FROM market_breadth_snapshots "
            "WHERE market_id=? AND data_status='complete'",
            (MARKET_ID,),
        ).fetchone()[0]
        # 抽样最近 + 最远
        first = cur.execute(
            "SELECT as_of, breadth_20, breadth_50, breadth_200, eligible_200, coverage_200 "
            "FROM market_breadth_snapshot_revisions WHERE market_id=? "
            "ORDER BY as_of LIMIT 1", (MARKET_ID,),
        ).fetchone()
        last = cur.execute(
            "SELECT as_of, breadth_20, breadth_50, breadth_200, eligible_200, coverage_200 "
            "FROM market_breadth_snapshot_revisions WHERE market_id=? "
            "ORDER BY as_of DESC LIMIT 1", (MARKET_ID,),
        ).fetchone()
        print(f"  校验：rev_complete={n_rev_complete}, snap_complete={n_snap_complete}")
        print(f"  首行：{dict(zip(['as_of','B20','B50','B200','eligible200','coverage200'], first))}")
        print(f"  末行：{dict(zip(['as_of','B20','B50','B200','eligible200','coverage200'], last))}")
        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只打印待写范围，不动 SQLite")
    args = parser.parse_args(argv)
    t0 = time.time()
    code = ingest(dry_run=args.dry_run)
    print(f"[ingest_sp500_breadth_to_sqlite] done in {time.time()-t0:.2f}s exit={code}")
    return code


if __name__ == "__main__":
    sys.exit(main())
