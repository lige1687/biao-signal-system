#!/usr/bin/env python3
"""run-08 只读核验（S2）：正式键双向检查在真实数据上的结论。

不重跑派生、不写任何运行产物：读取 run-08 派生快照的 economic_index 列
（只读计算动量）与协议 v1.0.3 冻结的窗口/日历/池，独立推导"应比对键
集合"，与 run-04 参考值（0db2492a…）双向分类核对。输出 summary 到
rework-s123/run08-readonly-check-02/（排他创建）。
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from lei_signal.research import momentum_prototype as mp  # noqa: E402
from lei_signal.research.data_snapshot import load_snapshot  # noqa: E402
from lei_signal.research.trading_calendar import TradingCalendar  # noqa: E402

TASK = ROOT / ("docs/experiments/raw/research-fixed-etf-evidence-integration"
               "-2026-09-13")
OUT = TASK / "rework-s123/run08-readonly-check-02"
OUT.mkdir(parents=True, exist_ok=False)

RUN04 = (ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
         "/run-04/values.csv")
protocol = json.loads((TASK / "protocol-v1.0.3.json").read_text(encoding="utf-8"))
inputs = protocol["inputs"]
run08 = TASK / "run-08/snapshot"

# 输入身份复核（与 run-08 manifest 声明一致）
manifest = json.loads((TASK / "run-08/manifest.json").read_text(encoding="utf-8"))
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()
assert manifest["declared_inputs"]["reference_values"]["sha256"] == _sha(RUN04)
assert manifest["protocol"]["sha256"] == _sha(TASK / "protocol-v1.0.3.json")

loaded = load_snapshot(str(run08))
assert loaded.verified, "run-08 派生快照读回核验失败"
calendar = TradingCalendar.from_file(
    ROOT / inputs["calendar"]["path"], ROOT / inputs["publication"]["path"])
start, end = inputs["evaluation_start"], inputs["evaluation_end"]
observations = [str(d) for d in
                mp.complete_month_last_trading_days(calendar, start, end)]
symbols = list(loaded.frames.keys())
expected_all = {(s, o) for s in symbols for o in observations}

derivable: dict[tuple[str, str], float] = {}
for sym in symbols:
    frame = loaded.frames[sym]
    close = frame["close"].astype(float)
    close = close[close > 0].dropna()
    # economic_index 列即 run-08 派生结果（只读重算动量）
    econ = frame["economic_index"].astype(float).dropna()
    momentum = mp.compute_momentum(econ)
    for obs in observations:
        key = pd.Timestamp(obs)
        if key in momentum.index:
            v = float(momentum.loc[key])
            if math.isfinite(v):
                derivable[(sym, obs)] = v

# 参考值（run-04，只读）
run04: dict[tuple[str, str], float] = {}
with open(RUN04) as f:
    for row in csv.DictReader(f):
        run04[(row["symbol"], row["date"])] = float(row["momentum"])

ref_keys = set(run04)
reference_missing = sorted(derivable.keys() - ref_keys)
out_of_scope = sorted(ref_keys - expected_all)
without_derived = sorted(k for k in (ref_keys & expected_all) if k not in derivable)
mismatch = []
for k in sorted(derivable.keys() & ref_keys):
    got, expected = derivable[k], run04[k]
    if abs(got - expected) > 1e-12 * max(1.0, abs(expected)):
        mismatch.append({"symbol": k[0], "date": k[1],
                         "derived": repr(got), "reference": repr(expected)})

complete = bool(
    not reference_missing and not out_of_scope and not without_derived
    and not mismatch)
summary = {
    "purpose": "S2 双向正式键检查在真实 run-08 数据上的只读核验",
    "date": "2026-09-13",
    "expected_observation_combinations": len(expected_all),
    "observations": len(observations),
    "symbols": len(symbols),
    "derivable_keys": len(derivable),
    "unique_reference_keys": len(run04),
    "reference_missing_expected_key": [
        {"symbol": s, "date": d} for s, d in reference_missing],
    "reference_out_of_scope": [
        {"symbol": s, "date": d} for s, d in out_of_scope],
    "reference_without_derived_value": [
        {"symbol": s, "date": d} for s, d in without_derived],
    "mismatch": mismatch,
    "complete_consistent": complete,
    "tolerance": "阈值 = 1e-12 * max(1.0, |expected|)",
    "inputs_verified": {
        "run04_values_sha": _sha(RUN04)[:16],
        "protocol_v103_sha": _sha(TASK / "protocol-v1.0.3.json")[:16],
        "run08_snapshot_verified": loaded.verified,
    },
}
(OUT / "summary.json").write_text(
    json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items()
                  if k not in ("purpose",)}, ensure_ascii=False, indent=1))
print("RESULT:", "COMPLETE" if complete else "INCOMPLETE")
