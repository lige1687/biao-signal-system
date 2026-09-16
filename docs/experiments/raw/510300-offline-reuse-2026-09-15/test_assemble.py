"""assemble.py 合成单测：全部合成夹具，独立期望直接写固定行，不引用函数输出。

覆盖：重叠同值去重 / 同日不同收盘拒绝 / 文件篡改拒绝 / 缺qfqday拒绝且不回退
day / 非正与NaN收盘拒绝 / 缺交易日拒绝 / 多出日隔离并拒绝完整资格 / 原始字符
串不舍入不修改。

运行：python3 -m pytest docs/experiments/raw/510300-offline-reuse-2026-09-15/test_assemble.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble import assemble  # noqa: E402


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write_vendor(base: Path, name: str, rows: list[list[str]],
                  field: str = "qfqday", symbol: str = "sh510300") -> dict:
    payload = {"code": 0, "msg": "", "data": {symbol: {field: rows}}}
    p = base / name
    p.write_text(json.dumps(payload))
    return {"symbol": symbol, "file": name, "sha256": _sha(p),
            "field": field, "retrieved_at": "2026-01-01T00:00:00+00:00"}


# 固定合成行（字符串原样；价格为正有限）
W1 = [["2020-01-02", "1.000", "1.100", "1.200", "0.900", "1000.000"],
      ["2020-01-03", "1.100", "1.050", "1.150", "1.000", "2000.000"]]
W2 = [["2020-01-03", "1.100", "1.050", "1.150", "1.000", "2000.000"],  # 与W1重叠同值
      ["2020-01-06", "1.050", "1.160", "1.180", "1.040", "3000.000"]]
SESSIONS = ["2020-01-02", "2020-01-03", "2020-01-06"]


def test_overlap_identical_rows_deduped(tmp_path):
    e1 = _write_vendor(tmp_path, "w1.json", W1)
    e2 = _write_vendor(tmp_path, "w2.json", W2)
    rows, audit = assemble([e1, e2], tmp_path, SESSIONS)
    # 独立期望：固定行原样、按日期排序、字符串不舍入
    assert rows == [["2020-01-02", "1.000", "1.100", "1.200", "0.900", "1000.000"],
                    ["2020-01-03", "1.100", "1.050", "1.150", "1.000", "2000.000"],
                    ["2020-01-06", "1.050", "1.160", "1.180", "1.040", "3000.000"]]
    assert audit["duplicates_deduped"] == 1
    assert audit["unique_dates"] == 3 and audit["selected_rows"] == 3
    assert audit["complete"] is True
    assert audit["extra_rows_quarantined"] == []
    assert [i["file"] for i in audit["inputs"]] == ["w1.json", "w2.json"]


def test_same_day_different_close_rejected(tmp_path):
    bad = [["2020-01-03", "1.100", "9.999", "1.150", "1.000", "2000.000"],
           ["2020-01-06", "1.050", "1.160", "1.180", "1.040", "3000.000"]]
    e1 = _write_vendor(tmp_path, "w1.json", W1)
    e2 = _write_vendor(tmp_path, "w2.json", bad)
    with pytest.raises(ValueError, match="同日冲突"):
        assemble([e1, e2], tmp_path, SESSIONS)


def test_tampered_file_rejected(tmp_path):
    e1 = _write_vendor(tmp_path, "w1.json", W1)
    e1["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="篡改"):
        assemble([e1], tmp_path, ["2020-01-02", "2020-01-03"])


def test_missing_qfqday_rejected_no_day_fallback(tmp_path):
    e1 = _write_vendor(tmp_path, "w1.json", W1, field="day")  # 只有名义价day
    with pytest.raises(ValueError, match="qfqday"):
        assemble([e1], tmp_path, ["2020-01-02", "2020-01-03"])


def test_non_positive_and_nan_close_rejected(tmp_path):
    for bad_close in ("0", "-1.5", "NaN", "inf"):
        rows = [["2020-01-02", "1.000", bad_close, "1.200", "0.900", "1000.000"],
                ["2020-01-03", "1.100", "1.050", "1.150", "1.000", "2000.000"]]
        e1 = _write_vendor(tmp_path, f"bad-{bad_close}.json", rows)
        with pytest.raises(ValueError):
            assemble([e1], tmp_path, ["2020-01-02", "2020-01-03"])


def test_missing_required_session_rejected(tmp_path):
    e1 = _write_vendor(tmp_path, "w1.json", W1)
    with pytest.raises(ValueError, match="缺交易日"):
        assemble([e1], tmp_path, ["2020-01-02", "2020-01-03", "2020-01-06"])


def test_extra_non_session_day_quarantined_not_certified(tmp_path):
    # 2020-01-04 是周六：落在覆盖窗口（01-02..01-06）内但不是交易日 → 异常隔离
    rows = W1 + [["2020-01-04", "1.000", "1.010", "1.020", "0.990", "10.000"],
                 ["2020-01-06", "1.050", "1.160", "1.180", "1.040", "3000.000"]]
    e1 = _write_vendor(tmp_path, "w1.json", rows)
    out, audit = assemble([e1], tmp_path, SESSIONS)
    # 多出日不进正式行，隔离列明；完整资格=False（待判定，不自动剔除后宣称合格）
    assert out == [["2020-01-02", "1.000", "1.100", "1.200", "0.900", "1000.000"],
                   ["2020-01-03", "1.100", "1.050", "1.150", "1.000", "2000.000"],
                   ["2020-01-06", "1.050", "1.160", "1.180", "1.040", "3000.000"]]
    assert audit["extra_rows_quarantined"] == [
        ["2020-01-04", "1.000", "1.010", "1.020", "0.990", "10.000"]]
    assert audit["complete"] is False


def test_out_of_window_rows_recorded_not_anomaly(tmp_path):
    # 窗口之外的合法交易日数据：不属本包范围，记录不算异常，不影响完整资格
    rows = W2 + [["2019-12-30", "0.900", "0.950", "0.960", "0.890", "500.000"],
                 ["2020-01-02", "1.000", "1.100", "1.200", "0.900", "1000.000"]]
    e1 = _write_vendor(tmp_path, "w1.json", rows)
    out, audit = assemble([e1], tmp_path, SESSIONS)
    assert out == [["2020-01-02", "1.000", "1.100", "1.200", "0.900", "1000.000"],
                   ["2020-01-03", "1.100", "1.050", "1.150", "1.000", "2000.000"],
                   ["2020-01-06", "1.050", "1.160", "1.180", "1.040", "3000.000"]]
    assert audit["out_of_window_rows"] == 1
    assert audit["extra_rows_quarantined"] == []
    assert audit["complete"] is True


def test_missing_file_rejected(tmp_path):
    e1 = {"symbol": "sh510300", "file": "absent.json", "sha256": "0" * 64,
          "field": "qfqday"}
    with pytest.raises(ValueError, match="原件缺失"):
        assemble([e1], tmp_path, [])
