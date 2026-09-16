"""run-04 真实动量值的独立逐值比对 v2（返修 D1，主控复核 §5）。

对 run-04/values.csv 做四类核对，全部期望独立构造：

1. 全量批量：冻结引擎既有表达式 vs 直接位置公式（有效报价序列第 k-21、
   k-252 个位置直接取数），并核对存在的正式键；
2. 正式键集合精确核对：预期有值的 (产品, 月末观察日) 键集合与 run-04
   逐键比对，报告缺失/多余/重复数量——不以"共 15,388 行"混同正式输出；
3. 选类逐值：普通月末（首/中/末）、253/273 日级公式边界（按实际第 253/273
   个有效报价位置取值；非正式月末输出时 run04_value 标"不适用"并注明，
   不写"不存在"）、每个分红/拆分行动生效日紧邻的观察日、缺报价前后
   （按已核日历找每产品应有报价日，再取缺口前后实际观察日）；
4. 全部类别"不存在"必须给出检查依据，不得因类型错误或漏选点而误报。

与旧 run-06/compare_values.py 的差异：统一日期类型；边界按位置取值；
缺口用已核交易日历而非工作日推算；新增键集合核对；--out 拒绝覆盖。
旧脚本与 run-06 产物封存，不重跑。本脚本只读冻结输入与 run-04。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.dont_write_bytecode = True

from lei_signal.research.definitions import quote_features  # noqa: E402
from lei_signal.research.momentum_prototype import (  # noqa: E402
    complete_month_last_trading_days, reconstruct_symbol_economic_index,
)
from lei_signal.research.trading_calendar import TradingCalendar  # noqa: E402
from run_momentum_research_prototype import (  # noqa: E402
    _load_protocol, _verify_protocol_codes, _verify_protocol_identity,
    _verify_protocol_inputs,
)

RAW = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
RUN04 = RAW / "run-04"
ATOL, RTOL = 1e-12, 1e-12


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True,
                        help="输出目录（必须不存在；拒绝覆盖已封存证据）")
    parser.add_argument("--run", default=str(RUN04),
                        help="被比对的正式运行目录（默认 run-04，只读）")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        print(f"输出目录已存在，拒绝覆盖：{out}", file=sys.stderr)
        return 3

    protocol, protocol_sha = _load_protocol(RAW / "protocol.json")
    _verify_protocol_codes(protocol)
    _verify_protocol_identity(protocol)
    input_paths = _verify_protocol_inputs(protocol)

    run_dir = Path(args.run)
    run_manifest = json.loads((run_dir / "manifest.json").read_text())
    run_values: dict[tuple[str, str], float] = {}
    duplicate_keys = 0
    with open(run_dir / "values.csv") as f:
        for row in csv.DictReader(f):
            key = (row["symbol"], row["date"])
            if key in run_values:
                duplicate_keys += 1
            run_values[key] = float(row["momentum"])

    # 冻结输入（与 CLI 同一核验路径）
    from lei_signal.research.data_snapshot import load_snapshot

    loaded = load_snapshot(input_paths["snapshot_dir"]["path"])
    assert loaded.verified, "快照完整性核验失败，中止比对"
    calendar = TradingCalendar.from_file(
        input_paths["calendar"]["path"], input_paths["publication"]["path"]
    )
    actions = json.loads(
        Path(input_paths["actions"]["path"]).read_text(encoding="utf-8")
    )["events"]
    start = protocol["inputs"]["evaluation_start"]
    end = protocol["inputs"]["evaluation_end"]
    observations = sorted({
        pd.Timestamp(d).strftime("%Y-%m-%d")
        for d in complete_month_last_trading_days(calendar, start, end)
    })
    # 裸码 → 快照规范身份（既有明确映射，同 CLI）
    bare_to_canon = {}
    for sym in loaded.frames:
        code = sym.split(".")[0]
        assert code not in bare_to_canon or bare_to_canon[code] == sym
        bare_to_canon[code] = sym
    events_by_symbol: dict[str, list[dict]] = {s: [] for s in loaded.frames}
    for ev in actions:
        canon = bare_to_canon.get(str(ev.get("symbol", "")).split(".")[0])
        if canon:
            events_by_symbol[canon].append(ev)

    rows_out: list[dict] = []
    batch_checked = 0
    batch_max_diff = 0.0
    batch_fail = 0
    expected_keys: set[tuple[str, str]] = set()
    key_value_mismatch = 0

    for raw_symbol in sorted(loaded.frames):
        close = loaded.frames[raw_symbol]["close"].astype(float).dropna()
        close = close[close > 0]
        econ, _unknown = reconstruct_symbol_economic_index(
            close, events_by_symbol[raw_symbol]
        )
        engine = quote_features(econ)["momentum"]  # 冻结引擎表达式（作用于经济指数）
        valid = list(econ.index)
        vals = econ.to_numpy()
        valid_positions = {d.normalize(): k for k, d in enumerate(valid)}

        # ---- 1. 全量批量核对 ----
        for k in range(252, len(valid)):
            pos_val = float(vals[k - 21] / vals[k - 252] - 1)
            engine_val = float(engine.iloc[k])
            batch_checked += 1
            d1 = abs(engine_val - pos_val)
            batch_max_diff = max(batch_max_diff, d1)
            if d1 > ATOL + RTOL * abs(pos_val):
                batch_fail += 1
            date_key = valid[k].strftime("%Y-%m-%d")
            run_val = run_values.get((raw_symbol, date_key))
            if run_val is not None and abs(run_val - pos_val) > ATOL + RTOL * abs(pos_val):
                key_value_mismatch += 1
                batch_fail += 1

        # ---- 2. 正式键集合：预期有值 = 月末观察日 ∩ 有限动量 ----
        for d in observations:
            key_ts = pd.Timestamp(d).normalize()
            k = valid_positions.get(key_ts)
            if k is not None and k >= 252 and pd.notna(engine.loc[key_ts]):
                expected_keys.add((raw_symbol, d))

        # ---- 3. 选类逐值 ----
        sym_run_dates = sorted(dd for (s, dd) in run_values if s == raw_symbol)

        def emit(category, date_str, basis=""):
            k = valid_positions.get(pd.Timestamp(date_str).normalize())
            run_val = run_values.get((raw_symbol, date_str))
            engine_val = float(engine.iloc[k]) if k is not None else None
            pos_val = (float(vals[k - 21] / vals[k - 252] - 1)
                       if k is not None and k >= 252 else None)
            t21 = valid[k - 21].strftime("%Y-%m-%d") if k is not None and k >= 21 else ""
            t252 = valid[k - 252].strftime("%Y-%m-%d") if k is not None and k >= 252 else ""
            if pos_val is None:
                verdict, diff = "类别不存在", ""
            else:
                diff = (abs(run_val - pos_val) if run_val is not None else None)
                ok = (run_val is None) or (diff <= ATOL + RTOL * abs(pos_val))
                verdict = "一致" if ok else "不一致"
                if run_val is None:
                    verdict = "一致（run04 键不适用：日级公式边界非月末输出）"
            rows_out.append({
                "category": category, "symbol": raw_symbol, "date": date_str,
                "endpoint_t_minus_21": t21, "endpoint_t_minus_252": t252,
                "action_ids": "", "run04_value": repr(run_val) if run_val is not None
                else ("不适用" if pos_val is not None else ""),
                "engine_value": repr(engine_val) if engine_val is not None else "",
                "positional_value": repr(pos_val) if pos_val is not None else "",
                "abs_diff": repr(float(diff)) if diff not in (None, "") else "",
                "verdict": verdict, "basis": basis,
            })

        def emit_absent(category, basis):
            rows_out.append({
                "category": category, "symbol": raw_symbol, "date": "",
                "endpoint_t_minus_21": "", "endpoint_t_minus_252": "",
                "action_ids": "", "run04_value": "", "engine_value": "",
                "positional_value": "", "abs_diff": "",
                "verdict": "类别不存在", "basis": basis,
            })

        if sym_run_dates:
            emit("普通月末-首", sym_run_dates[0])
            emit("普通月末-中", sym_run_dates[len(sym_run_dates) // 2])
            emit("普通月末-末", sym_run_dates[-1])
        else:
            emit_absent("普通月末", "该产品在 run-04 无任何正式动量键（全部缺失）")

        for label, pos_needed in (("253边界", 252), ("273边界", 272)):
            if len(valid) > pos_needed:
                d = valid[pos_needed].strftime("%Y-%m-%d")
                basis = (
                    f"第 {pos_needed + 1} 个有效报价位置；"
                    + ("是正式月末键" if (raw_symbol, d) in run_values
                       else "非正式月末输出，run04_value 不适用，按两条公式互核")
                )
                emit(label, d, basis)
            else:
                emit_absent(label,
                            f"该产品仅 {len(valid)} 个有效报价，不足第 "
                            f"{pos_needed + 1} 个位置")

        for ev in events_by_symbol[raw_symbol]:
            if ev.get("type") not in {"split", "cash_dividend"}:
                continue
            eff = str(ev["effective_date"])[:10]
            before = [d for d in sym_run_dates if d <= eff]
            after = [d for d in sym_run_dates if d > eff]
            if before:
                emit(f"行动前-{ev['event_id']}", before[-1])
            else:
                emit_absent(f"行动前-{ev['event_id']}",
                            f"生效日 {eff} 前该产品无正式月末键")
            if after:
                emit(f"行动后-{ev['event_id']}", after[0])
            else:
                emit_absent(f"行动后-{ev['event_id']}",
                            f"生效日 {eff} 后该产品无正式月末键")

        # 缺报价：已核日历应有报价日 vs 实际报价行
        if len(valid) >= 2:
            first_q, last_q = valid[0], valid[-1]
            tds = [pd.Timestamp(d) for d in calendar.trading_days(
                pd.Timestamp(first_q).strftime("%Y-%m-%d"),
                pd.Timestamp(last_q).strftime("%Y-%m-%d"))]
            quote_set = {d.normalize() for d in valid}
            gaps = [d for d in tds if d.normalize() not in quote_set]
            if gaps:
                shown = 0
                for g in gaps:
                    before = [d for d in sym_run_dates
                              if pd.Timestamp(d).normalize() < g.normalize()]
                    after_ = [d for d in sym_run_dates
                              if pd.Timestamp(d).normalize() > g.normalize()]
                    if before and after_ and shown < 4:
                        emit(f"缺报价前-{g.strftime('%Y-%m-%d')}", before[-1],
                             f"依据：已核日历 {g.strftime('%Y-%m-%d')} 为交易日"
                             "而该产品无报价行")
                        emit(f"缺报价后-{g.strftime('%Y-%m-%d')}", after_[0],
                             f"依据：已核日历 {g.strftime('%Y-%m-%d')} 为交易日"
                             "而该产品无报价行")
                        shown += 1
                if shown == 0:
                    emit_absent("缺报价",
                                f"该产品有 {len(gaps)} 个日历缺口日，但缺口前后"
                                "无可核对的正式月末键（缺口未跨越可观察月末）")
            else:
                emit_absent("缺报价",
                            "依据：已核交易日历在该公司报价区间内逐日核对，"
                            "无应报价而缺报价的日期")

    # ---- 2. 键集合精确核对 ----
    run_keys = set(run_values)
    missing_keys = sorted(expected_keys - run_keys)
    extra_keys = sorted(run_keys - expected_keys)

    out.mkdir(parents=True)
    cols = ["category", "symbol", "date", "endpoint_t_minus_21",
            "endpoint_t_minus_252", "action_ids", "run04_value", "engine_value",
            "positional_value", "abs_diff", "verdict", "basis"]
    with open(out / "comparison.csv", "w") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)

    n_ok = sum(1 for r in rows_out if r["verdict"].startswith("一致"))
    n_bad = sum(1 for r in rows_out if r["verdict"] == "不一致")
    n_absent = sum(1 for r in rows_out if r["verdict"] == "类别不存在")
    summary = {
        "protocol_sha256": protocol_sha,
        "run_dir": str(run_dir),
        "run04_values_sha256": _sha(run_dir / "values.csv"),
        "batch_checked_rows": batch_checked,
        "batch_max_abs_diff_engine_vs_positional": batch_max_diff,
        "batch_failures": batch_fail,
        "formal_key_check": {
            "run04_unique_keys": len(run_keys),
            "run04_duplicate_key_rows": duplicate_keys,
            "expected_keys_recomputed": len(expected_keys),
            "missing_from_run04": len(missing_keys),
            "extra_in_run04": len(extra_keys),
            "value_mismatches_on_common_keys": key_value_mismatch,
            "missing_samples": [list(k) for k in missing_keys[:10]],
            "extra_samples": [list(k) for k in extra_keys[:10]],
        },
        "selected_rows": len(rows_out),
        "selected_ok": n_ok,
        "selected_mismatch": n_bad,
        "selected_absent_with_basis": n_absent,
        "tolerance": {"absolute": ATOL, "relative": RTOL},
        "inputs": {k: v["sha256"] for k, v in input_paths.items()},
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
