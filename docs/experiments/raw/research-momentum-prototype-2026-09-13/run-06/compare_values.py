"""run-04 真实动量值的独立逐值比对（momentum-research-prototype-2026-09-13）。

对 run-04/values.csv 的每个数值做两条独立核对：
1. 冻结引擎既有表达式（definitions.quote_features 的 shift 表达式）；
2. 直接位置公式：在有效报价序列上按第 i-21、i-252 个位置直接取数。
同一函数的两次调用不算独立复算——这里的位置公式独立于引擎实现。

选取类别（预定规则；某类不存在则记录不存在）：
普通月末（每产品首/中/末三个观察日）、253 边界（首个可算行）、273 边界、
分红/拆分前后（每个事件生效日紧邻的观察日）、缺报价前后（缺口紧邻观察日）。
全量有效动量行另用独立 shift 表达式批量核对。

只读冻结输入与 run-04 产物；输出 comparison.csv / summary.json / report.md。
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from lei_signal.research.definitions import quote_features  # noqa: E402
from lei_signal.research.momentum_prototype import (  # noqa: E402
    adapt_company_events, reconstruct_symbol_economic_index,
)
from lei_signal.research.data_snapshot import load_snapshot  # noqa: E402

RAW = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
RUN = RAW / "run-04"
PROTOCOL = json.loads((RAW / "protocol.json").read_text())
ATOL, RTOL = 1e-12, 1e-12


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---- 冻结输入与行动（同 CLI 同一读取路径） ----
inputs = PROTOCOL["inputs"]
loaded = load_snapshot(inputs["snapshot_dir"]["path"])
assert loaded.verified, "快照完整性核验失败，中止比对"
actions = json.loads(
    Path(inputs["actions"]["path"]).read_text(encoding="utf-8"))["events"]
# 裸码 → 快照规范身份（与 CLI 相同的既有明确映射）
bare_to_canon = {}
for sym in loaded.frames:
    code = sym.split(".")[0]
    assert code not in bare_to_canon or bare_to_canon[code] == sym
    bare_to_canon[code] = sym

run_values: dict[tuple[str, str], float] = {}
with open(RUN / "values.csv") as f:
    for row in csv.DictReader(f):
        run_values[(row["symbol"], row["date"])] = float(row["momentum"])

rows_out: list[dict] = []
batch_max_diff = 0.0
batch_checked = 0
batch_fail = 0
events_by_symbol: dict[str, list[dict]] = {}


def event_ids_between(symbol: str, lo: str, hi: str) -> str:
    evs = events_by_symbol.get(symbol, [])
    ids = [
        e["event_id"] for e in evs
        if lo < str(e["effective_date"])[:10] <= hi
    ]
    return ";".join(ids) if ids else ""


for raw_symbol in sorted(loaded.frames):
    close = loaded.frames[raw_symbol]["close"].astype(float).dropna()
    close = close[close > 0]
    canon_sym = raw_symbol
    events = [e for e in actions
              if bare_to_canon.get(str(e.get("symbol", "")).split(".")[0]) == canon_sym]
    adapted = adapt_company_events(events)
    events_by_symbol[canon_sym] = adapted
    # 与 CLI 相同：先重建经济指数，再在其上取动量（对象输入是 I，不是名义价）
    econ, unknown = reconstruct_symbol_economic_index(close, adapted)
    # 引擎既有表达式（冻结口径，作用于经济指数）
    engine = quote_features(econ)["momentum"]
    # 独立位置公式：有效报价序列上直接取数
    valid = list(econ.index)
    vals = econ.to_numpy()
    # ---- 全量批量核对（独立 shift 表达式 + 位置公式） ----
    for k in range(252, len(valid)):
        engine_val = engine.iloc[k]
        pos_val = vals[k - 21] / vals[k - 252] - 1
        batch_checked += 1
        d1 = abs(float(engine_val) - pos_val)
        batch_max_diff = max(batch_max_diff, d1)
        if d1 > ATOL + RTOL * abs(pos_val):
            batch_fail += 1
        date_key = valid[k].strftime("%Y-%m-%d")
        run_val = run_values.get((raw_symbol, date_key))
        if run_val is not None and abs(run_val - pos_val) > ATOL + RTOL * abs(pos_val):
            batch_fail += 1

    # ---- 选类逐值 ----
    obs_dates = sorted(d for (s, d) in run_values if s == raw_symbol)
    valid_positions = {valid[k]: k for k in range(len(valid))}
    selected: dict[str, list[str]] = {}
    if obs_dates:
        selected["普通月末-首"] = [obs_dates[0]]
        selected["普通月末-中"] = [obs_dates[len(obs_dates) // 2]]
        selected["普通月末-末"] = [obs_dates[-1]]
        first_valid_obs = next(
            (d for d in obs_dates if d in valid_positions
             and valid_positions[d] >= 252), None)
        if first_valid_obs:
            selected["253边界"] = [first_valid_obs]
        obs_273 = next(
            (d for d in obs_dates if d in valid_positions
             and valid_positions[d] == 272), None)
        selected["273边界"] = [obs_273] if obs_273 else []
        for ev in adapted:
            eff = str(ev["effective_date"])[:10]
            before = [d for d in obs_dates if d <= eff]
            after = [d for d in obs_dates if d > eff]
            if before:
                selected.setdefault(f"行动前-{ev['event_id']}", []).append(before[-1])
            if after:
                selected.setdefault(f"行动后-{ev['event_id']}", []).append(after[0])
        # 缺报价前后：报价序列内的日历缺口
        gaps = []
        for a, b in zip(valid, valid[1:]):
            between = pd.bdate_range(a, b)
            if len(between) > 2:  # 工作日口径下有缺口
                gaps.append((pd.Timestamp(a).strftime("%Y-%m-%d"),
                             pd.Timestamp(b).strftime("%Y-%m-%d")))
        for a, b in gaps[:4]:
            before = [d for d in obs_dates if a < d < b]
            if before:
                selected.setdefault(f"缺报价-{a}~{b}", []).append(before[0])
        if not gaps:
            selected["缺报价"] = []
    for category, dates in selected.items():
        if not dates:
            rows_out.append({
                "category": category, "symbol": raw_symbol, "date": "",
                "endpoint_t_minus_21": "", "endpoint_t_minus_252": "",
                "action_ids": "",
                "run04_value": "", "engine_value": "", "positional_value": "",
                "abs_diff": "", "verdict": "类别不存在",
            })
            continue
        for d in dates:
            k = valid_positions.get(pd.Timestamp(d))
            run_val = run_values.get((raw_symbol, d))
            engine_val = float(engine.iloc[k]) if k is not None else None
            pos_val = (float(vals[k - 21] / vals[k - 252] - 1)) if k is not None and k >= 252 else None
            t21 = valid[k - 21].strftime("%Y-%m-%d") if k is not None and k >= 21 else ""
            t252 = valid[k - 252].strftime("%Y-%m-%d") if k is not None and k >= 252 else ""
            diff = (abs(run_val - pos_val)
                    if run_val is not None and pos_val is not None else None)
            ok = diff is not None and diff <= ATOL + RTOL * abs(pos_val)
            rows_out.append({
                "category": category, "symbol": raw_symbol, "date": d,
                "endpoint_t_minus_21": t21, "endpoint_t_minus_252": t252,
                "action_ids": event_ids_between(raw_symbol, t252, d) if t252 else "",
                "run04_value": repr(run_val) if run_val is not None else "",
                "engine_value": repr(engine_val) if engine_val is not None else "",
                "positional_value": repr(pos_val) if pos_val is not None else "",
                "abs_diff": repr(float(diff)) if diff is not None else "",
                "verdict": "一致" if ok else "不一致",
            })

out_rows_csv = RUN.parent / "run-06"
out_rows_csv.mkdir(exist_ok=True)
cols = ["category", "symbol", "date", "endpoint_t_minus_21", "endpoint_t_minus_252",
        "action_ids", "run04_value", "engine_value", "positional_value",
        "abs_diff", "verdict"]
with open(out_rows_csv / "comparison.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows_out)

n_ok = sum(1 for r in rows_out if r["verdict"] == "一致")
n_bad = sum(1 for r in rows_out if r["verdict"] == "不一致")
summary = {
    "batch_checked_rows": batch_checked,
    "batch_max_abs_diff_engine_vs_positional": batch_max_diff,
    "batch_failures": batch_fail,
    "selected_rows": len(rows_out),
    "selected_ok": n_ok,
    "selected_mismatch": n_bad,
    "tolerance": {"absolute": ATOL, "relative": RTOL},
    "inputs": {k: sha(Path(v["path"]) / "snapshot.json" if k == "snapshot_dir"
                      else Path(v["path"]))
               for k, v in inputs.items()
               if isinstance(v, dict) and "path" in v},
    "run04_values_sha256": sha(RUN / "values.csv"),
}
(out_rows_csv / "summary.json").write_text(
    json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
