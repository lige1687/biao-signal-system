"""Final acceptance checks. Run immediately before declaring completion."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RESULTS = HERE / "results"

summary = pd.read_csv(RESULTS / "summary.csv")
assert len(summary) == 36 and summary.account_id.nunique() == 36
assert (summary.groupby("fee_rate").size() == 18).all()
assert not summary.account_id.str.contains("chinext").any()
matrix = json.loads((RESULTS / "matrix_status.json").read_text())
assert matrix["planned_main_paths"] == 22
assert matrix["completed_main_paths_10bp"] == 18
assert matrix["paused"] == ["159915-own-index-W0/W1/W2/W3"]

main = summary[summary.fee_rate == 0.001].set_index(["symbol", "width_source", "method"])
for symbol, source in [(510300, "all_a"), (510300, "csi300"), (159915, "all_a")]:
    w0 = main.loc[(symbol, source, "W0"), "end_equity"]
    assert main.loc[(symbol, source, "W1"), "end_equity"] < w0
    assert main.loc[(symbol, source, "W2"), "end_equity"] < w0
    assert main.loc[(symbol, source, "W3"), "end_equity"] > main.loc[(symbol, source, "W1"), "end_equity"]
    assert main.loc[(symbol, source, "W3"), "end_equity"] > main.loc[(symbol, source, "W2"), "end_equity"]
assert main.loc[(159915, "all_a", "W3"), "end_equity"] > main.loc[(159915, "all_a", "W0"), "end_equity"]

for row in summary.itertuples():
    fee_dir = RESULTS / ("fee-10bp" if row.fee_rate == 0.001 else "fee-20bp")
    daily = pd.read_parquet(fee_dir / f"{row.account_id}-daily.parquet")
    assert daily.cash.min() >= -1e-6
    assert np.allclose(daily.equity, daily.cash + daily.receivable + daily.units * daily.mark, atol=0.005)
    assert np.allclose(np.mod(daily.units, 100), 0, atol=1e-9)
    try:
        trades = pd.read_csv(fee_dir / f"{row.account_id}-trades.csv")
    except pd.errors.EmptyDataError:
        trades = pd.DataFrame()
    if not trades.empty:
        assert np.allclose(np.mod(trades.qty, 100), 0, atol=1e-9)
        assert not trades.groupby("date").side.nunique().gt(1).any()

quality = json.loads((HERE / "prepared/data_quality.json").read_text())
assert quality["all_a"]["grade"] == "B" and quality["all_a"]["first_valid"] == "2018-07-05"
assert quality["csi300"]["grade"] == "B"
assert quality["chinext"]["grade"] == "C"
membership = pd.read_parquet(HERE / "prepared/csi300_membership_daily.parquet")
assert membership.groupby("date").symbol.nunique().eq(300).all()

check = json.loads((HERE / "diagnostics/independent_arithmetic_check.json").read_text())
assert check["passed"] and check["accounts"] == 36
for chart in (HERE / "charts").glob("*.svg"):
    ET.parse(chart)
assert len(list((HERE / "charts").glob("*.svg"))) == 3

report = ROOT / "docs/experiments/etf-breadth-source-and-confirmation-backtest-2026-09-09.md"
text = report.read_text()
for required in ["## 一句话结论（大白话）", "## ARCHIVE", "18/22", "不修改生产规则"]:
    assert required in text
for link in re.findall(r"\]\((raw/[^)]+)\)", text):
    assert (report.parent / link).exists(), link
registry = json.loads((ROOT / "docs/experiments/registry.json").read_text())
assert str(report.relative_to(ROOT)) in registry["entries"]

print(json.dumps({"status": "passed", "accounts": 36, "main_paths": 18, "charts": 3, "tests_expected": 7}, ensure_ascii=False))
