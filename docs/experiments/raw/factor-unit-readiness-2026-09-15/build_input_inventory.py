"""factor-unit-readiness-2026-09-15 输入资格盘点（只读资格统计，无指标/目标计算）。

统计范围：行数、首末日期、缺失、重复、非正/非有限值、日期间隔形态、字段与元数据。
明确不做：均线状态、分组收益、IC、未来标签、账户路径。
输出：input-inventory.json（含逐份 SHA-256），写入本轮 raw 目录；拒绝覆盖已有文件。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
CACHE = Path.home() / ".lei_signal_lab/cache"
RAW = REPO / "docs/experiments/raw/factor-unit-readiness-2026-09-15"
OUT = RAW / "input-inventory.json"
if OUT.exists():
    print(f"REFUSE to overwrite existing {OUT}")
    sys.exit(3)

NOW = datetime.now(timezone(timedelta(hours=8))).isoformat()

# 数据集身份在读取前冻结（12份预算；目录清单与文件头侦察不计入）
DATASETS = [
    ("carrier_510300_timing", CACHE / "timing/510300.parquet"),
    ("carrier_159915_timing", CACHE / "timing/159915.parquet"),
    ("carrier_SPY_timing", CACHE / "timing/SPY.parquet"),
    ("carrier_QQQ_timing", CACHE / "timing/QQQ.parquet"),
    ("csi300_membership_daily", REPO / "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/csi300_membership_daily.parquet"),
    ("us_aaii_survey", CACHE / "sentiment_research_2026-09/aaii_clean.csv"),
    ("us_naaim_survey", CACHE / "sentiment_research_2026-09/naaim_clean.csv"),
    ("cn_margin_history", CACHE / "sentiment_research_2026-09/margin_history.csv"),
    ("cn_northbound_net", CACHE / "sentiment_research_2026-09/northbound_net.csv"),
    ("cn_tx_sector_flow", CACHE / "tx_sector_flow_pilot.json"),
    ("us_sp500_breadth_200dma", CACHE / "sentiment_research_2026-09/breadth_sp500_200dma.csv"),
    ("frozen_research_snapshot_v2", REPO / "docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2"),
]


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def date_gap_stats(idx: pd.DatetimeIndex) -> dict:
    if len(idx) < 2:
        return {}
    gaps = np.diff(idx.values).astype("timedelta64[D]").astype(int)
    med = float(np.median(gaps))
    top = np.argsort(gaps)[-5:][::-1]
    return {
        "median_gap_days": med,
        "max_gap_days": int(gaps.max()),
        "gaps_gt_3x_median": int((gaps > 3 * med).sum()) if med else None,
        "gaps_gt_10_days": int((gaps > 10).sum()),
        "top5_gaps": [
            {"after": str(idx[int(i) + 1].date()), "days": int(gaps[int(i)])}
            for i in top
        ],
    }


def numeric_quality(s: pd.Series, must_be_positive: bool) -> dict:
    v = pd.to_numeric(s, errors="coerce")
    return {
        "missing": int(v.isna().sum()),
        "non_finite": int((~np.isfinite(v.dropna().astype(float))).sum()),
        "non_positive": int((v.dropna() <= 0).sum()) if must_be_positive else None,
    }


def inspect_series_file(key: str, p: Path, *, date_col: str, value_cols: list[tuple[str, bool]],
                        freq_hint: str, source_note: str) -> dict:
    df = pd.read_csv(p)
    df[date_col] = pd.to_datetime(df[date_col])
    dup = int(df[date_col].duplicated().sum())
    df = df.sort_values(date_col)
    entry = {
        "key": key,
        "path": str(p),
        "sha256": sha256_of(p),
        "bytes": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(),
        "declared_identity": key,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "first_date": str(df[date_col].iloc[0].date()),
        "last_date": str(df[date_col].iloc[-1].date()),
        "duplicate_dates": dup,
        "date_gaps": date_gap_stats(pd.DatetimeIndex(df[date_col])),
        "value_quality": {c: numeric_quality(df[c], pos) for c, pos in value_cols},
        "frequency_observed": freq_hint,
        "source_note": source_note,
        "metadata_file": None,
    }
    return entry


def main() -> None:
    inv: dict = {
        "task": "factor-unit-readiness-2026-09-15 Task3",
        "generated_at": NOW,
        "budget_note": "12份数据集预算；目录清单/文件头侦察不占预算但记录于scouting_notes",
        "scouting_notes": [
            "apx_510300_SS.csv / apx_159915_SZ.csv（旧情绪研究锚点文件）文件头显示为周频（date间隔约7天），不适合作为双均线日频研究载体；未纳入12份预算，仅记录头两行侦察结果",
            "cache根 510300.SS.bars.parquet 为腾讯短历史（meta.json: 641行，2024-01-23起），不满足2010-2025窗口；未纳入预算",
            "标普500历史成员名单：本仓库raw与~/.lei_signal_lab/cache搜索未见任何标普500逐日/逐期历史成员文件（仅有已算好的宽度序列），美宽度对象按设计标'未登记+成员资料缺失'",
            "timing/ 目录存在 *.parquet.quarantined 旧副本（159915/512010/512480/512690/512800/515050/515220/515880/513100/513500等），正式文件与隔离副本并存，资格以正式文件为准并记录",
        ],
        "datasets": [],
    }

    # 1-4: 四载体 timing parquet
    for key, sym, mkt in (
        ("carrier_510300_timing", "510300", "A股/沪"),
        ("carrier_159915_timing", "159915", "A股/深"),
        ("carrier_SPY_timing", "SPY", "美股/NYSE Arca"),
        ("carrier_QQQ_timing", "QQQ", "美股/Nasdaq"),
    ):
        p = CACHE / f"timing/{sym}.parquet"
        df = pd.read_parquet(p)
        df = df.reset_index() if isinstance(df.index, pd.DatetimeIndex) else df
        date_col = next(c for c in df.columns if c.lower() in ("date", "datetime", "index"))
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        close_col = next(c for c in df.columns if c.lower() in ("close", "adjclose", "adj_close"))
        entry = {
            "key": key,
            "path": str(p),
            "sha256": sha256_of(p),
            "bytes": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(),
            "rows": int(len(df)),
            "columns": list(df.columns),
            "first_date": str(df[date_col].iloc[0].date()),
            "last_date": str(df[date_col].iloc[-1].date()),
            "duplicate_dates": int(df[date_col].duplicated().sum()),
            "date_gaps": date_gap_stats(pd.DatetimeIndex(df[date_col])),
            "value_quality": {
                c: numeric_quality(df[c], c == close_col) for c in df.columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])
            },
            "market_note": mkt,
            "source_note": "timing研究缓存（2026-08-27/28抓取）；具体供应商与复权口径以列名/元数据为准，本轮如实记录未知项",
        }
        inv["datasets"].append(entry)

    # 5: 沪深300逐日成员
    p = REPO / "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/csi300_membership_daily.parquet"
    mem = pd.read_parquet(p)
    entry = {
        "key": "csi300_membership_daily",
        "path": str(p),
        "sha256": sha256_of(p),
        "bytes": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(),
        "rows": int(len(mem)),
        "columns": list(mem.columns),
    }
    if {"date", "symbol"} <= set(mem.columns):
        mem["date"] = pd.to_datetime(mem["date"])
        per_day = mem.groupby("date")["symbol"].nunique()
        entry.update({
            "first_date": str(mem["date"].min().date()),
            "last_date": str(mem["date"].max().date()),
            "distinct_dates": int(per_day.shape[0]),
            "duplicate_date_symbol": int(mem.duplicated(["date", "symbol"]).sum()),
            "members_per_date_min": int(per_day.min()),
            "members_per_date_median": float(per_day.median()),
            "members_per_date_max": int(per_day.max()),
            "date_gaps": date_gap_stats(pd.DatetimeIndex(per_day.index)),
        })
    entry["source_note"] = "breadth-confirmation轮准备的沪深300逐日成员链（20交易日探测，登记卡universe.version声明可能漏段内往返）"
    inv["datasets"].append(entry)

    # 6-9, 11: CSV情绪系列
    inv["datasets"].append(inspect_series_file(
        "us_aaii_survey", CACHE / "sentiment_research_2026-09/aaii_clean.csv",
        date_col="date" if False else "reported",
        value_cols=[("bullish", False), ("neutral", False), ("bearish", False), ("bull_bear", False)],
        freq_hint="周频（调查）",
        source_note="AAII官方xls直下清洗版（旧报告口径）；无available_at列，发布时刻=周四盘前为旧报告叙述，本文件未带时点字段"))
    inv["datasets"].append(inspect_series_file(
        "us_naaim_survey", CACHE / "sentiment_research_2026-09/naaim_clean.csv",
        date_col="date", value_cols=[("naaim", False)],
        freq_hint="周频（调查）",
        source_note="MacroMicro转载NAAIM（免费源滞后约5周）；无available_at列"))
    inv["datasets"].append(inspect_series_file(
        "cn_margin_history", CACHE / "sentiment_research_2026-09/margin_history.csv",
        date_col="date",
        value_cols=[("RZYE", True), ("RZMRE", False), ("RZJME", False), ("LTSZ", True)],
        freq_hint="日频（T+1盘前披露）",
        source_note="东财datacenter沪深北两融合计；RZYE融资余额(万元量纲需核)、LTSZ流通市值"))
    inv["datasets"].append(inspect_series_file(
        "cn_northbound_net", CACHE / "sentiment_research_2026-09/northbound_net.csv",
        date_col="date", value_cols=[("NET_DEAL_AMT", False)],
        freq_hint="日频（已终止披露）",
        source_note="东财北向净买入合计；2024-08-16后披露终止，序列止于此为资料事实而非缺失"))
    inv["datasets"].append(inspect_series_file(
        "us_sp500_breadth_200dma", CACHE / "sentiment_research_2026-09/breadth_sp500_200dma.csv",
        date_col="date", value_cols=[("breadth", False)],
        freq_hint="日频",
        source_note="标普500高于200日线成分占比（MacroMicro转载），0-100百分数口径；非本仓库登记对象"))

    # 10: 腾讯板块资金流 JSON
    p = CACHE / "tx_sector_flow_pilot.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    boards = raw.get("boards") or {}
    n_points, n_missing_small, n_missing_main, dates_min, dates_max = 0, 0, 0, [], []
    for code, pts in boards.items():
        for q in pts:
            n_points += 1
            d = str(q.get("date", ""))[:10]
            if d:
                dates_min.append(d); dates_max.append(d)
            if q.get("small_yi") is None:
                n_missing_small += 1
            if q.get("main_yi") is None:
                n_missing_main += 1
    inv["datasets"].append({
        "key": "cn_tx_sector_flow",
        "path": str(p),
        "sha256": sha256_of(p),
        "bytes": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(),
        "boards": len(boards),
        "points_total": n_points,
        "date_min": min(dates_min) if dates_min else None,
        "date_max": max(dates_max) if dates_max else None,
        "missing_small_yi": n_missing_small,
        "missing_main_yi": n_missing_main,
        "fields_per_point": sorted({k for pts in boards.values() for q in pts for k in q}) if boards else [],
        "source_note": "腾讯板块聚合资金流（约246交易日/161-166板块，旧报告口径96%+与东财一致）；供应商分类不等于真实散户心理",
    })

    # 12: 冻结研究快照 v2
    p = REPO / "docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2"
    snap_meta = json.loads((p / "snapshot.json").read_text())
    norm_dir = p / "normalized"
    norm_files = sorted(x.name for x in norm_dir.iterdir()) if norm_dir.exists() else []
    inv["datasets"].append({
        "key": "frozen_research_snapshot_v2",
        "path": str(p),
        "snapshot_json_sha256": sha256_of(p / "snapshot.json"),
        "normalized_files": norm_files[:20],
        "normalized_file_count": len(norm_files),
        "snapshot_meta_keys": sorted(snap_meta.keys()),
        "symbols": snap_meta.get("symbols") or snap_meta.get("products"),
        "rows": snap_meta.get("rows"),
        "first_date": snap_meta.get("start_date") or snap_meta.get("first_date"),
        "last_date": snap_meta.get("end_date") or snap_meta.get("last_date"),
        "source_note": "冻结14产品研究快照（input-preflight报告记录14只/18916行/2019-09-02起）；冻结存量数据不因加列获得资格",
    })

    RAW.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(inv, ensure_ascii=False, indent=1) + "\n")
    print(f"written {OUT} with {len(inv['datasets'])} datasets")


if __name__ == "__main__":
    main()
