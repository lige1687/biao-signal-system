"""宽度只读模块：直读/大白话转换/降级（真路径经 monkeypatch 隔离）。"""
from __future__ import annotations

import json
import sqlite3

import pytest

from lei_signal.copilot import breadth


def test_a_share_reads_latest_and_delta(tmp_path, monkeypatch):
    f = tmp_path / "a.json"
    rows = [
        {"date": f"2026-09-0{d}", "ma20_pct": 40 + d, "ma50_pct": 55 + d,
         "ma200_pct": 25 + d}
        for d in range(1, 5)
    ]
    f.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(breadth, "_BREADTH_JSON", f)
    p = breadth.a_share_breadth()
    assert p["available"] is True
    assert p["as_of"] == "2026-09-04"
    assert p["ma20_pct"] == 44
    assert p["chg_5d"]["ma20_pct"] == pytest.approx(3.0)  # 44-41


def test_a_share_cn_uses_plain_words_no_thresholds(tmp_path, monkeypatch):
    f = tmp_path / "a.json"
    f.write_text(json.dumps([{
        "date": "2026-09-04", "ma20_pct": 49.96,
        "ma50_pct": 61.5, "ma200_pct": 25.4,
    }]), encoding="utf-8")
    monkeypatch.setattr(breadth, "_BREADTH_JSON", f)
    cn = breadth.a_share_breadth_cn()
    assert cn is not None
    assert "50%" in cn and "62%" in cn and "25%" in cn
    # 大白话描述存在且无任何阈值判定词
    assert "约一半" in cn and "约六成" in cn and "约三成" in cn


def test_a_share_missing_file_degrades(monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(
        breadth, "_BREADTH_JSON", Path("/nonexistent/a.json")
    )
    p = breadth.a_share_breadth()
    assert p["available"] is False
    assert breadth.a_share_breadth_cn(p) is None


def test_us_reads_latest_complete_row(tmp_path, monkeypatch):
    db = tmp_path / "u.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE market_breadth_snapshots (market_id TEXT, as_of TEXT, "
        "breadth_20 REAL, breadth_50 REAL)"
    )
    conn.execute(
        "INSERT INTO market_breadth_snapshots VALUES ('SP500','2026-08-14',66.2,69.3)"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(breadth, "_US_DB", db)
    p = breadth.us_breadth()
    assert p["available"] is True and p["as_of"] == "2026-08-14"
    cn = breadth.us_breadth_cn(p)
    assert "66%" in cn and "2026-08-14" in cn and "断档" in p["note_cn"]
