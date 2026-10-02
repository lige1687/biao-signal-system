"""运行 T2 案例：推荐读法、生产读法（参考实现）、生产代码（注入时钟/周线/ATR/构造）三方对照。

用法：python run_cases.py  （仓库根目录下任意位置均可；只写本目录 case-results.json）
生产代码只在内存中替换 first_ma_pullback 模块内的四个辅助函数引用，不改任何源文件。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path[:0] = [str(HERE), str(REPO / "src")]

import lei_signal.rules.first_ma_pullback as fmp  # noqa: E402
from cases import CASES, INIT  # noqa: E402
from lei_signal.features.pivots import confirmed_pivots  # noqa: E402
from lei_signal.rules.reward_risk_filter import compute_reward_risk  # noqa: E402
from lei_signal.rules.strict_structure import SIDE_BOTTOM, StrictStructure  # noqa: E402
from lifecycle_ref import PRODUCTION, RECOMMENDED, run_reference  # noqa: E402
from synth import make, rows_of, table  # noqa: E402


def production(frame: pd.DataFrame, structures: list[dict]):
    injected = [StrictStructure(side=SIDE_BOTTOM, confirmed_date=date.fromisoformat(s["confirmed_date"]),
                                reference_price=s["ref_low"], trigger_price=s["ref_low"] + 1,
                                final_price=s["ref_low"] + 2, reference_date=date.fromisoformat(
                                    s["confirmed_date"]), contained_bars_merged=0,
                                structure_id=s["id"], invalidated_date=(
                                    date.fromisoformat(s["invalidated_date"])
                                    if s.get("invalidated_date") else None)) for s in structures]
    fmp.average_true_range = lambda f, p=20: pd.Series(1.0, index=f.index)
    fmp.clock_series = lambda f: f["clock"].fillna(0).astype(int)
    fmp.weekly_env_series = lambda f: f["weekly"].map(lambda v: v is True)
    fmp.detect_strict_structures = lambda f: list(injected)
    return fmp.detect_first_ma_pullback_events(frame, "SYN")


def summarize_prod(events, g):
    out = {"touches": [], "signals": [], "cancels": []}
    for e in events:
        x = e.evidence
        if x.get("ma_period") != g:
            continue
        d = e.available_date.isoformat()
        if x["sub_rule"].endswith("touched"):
            out["touches"].append([d, x["is_first_touch"]])
        elif x["sub_rule"].endswith("confirmed") and x.get("entry_variant") == "early":
            out["signals"].append([d, x["is_first_touch"], round(x["stop_price"], 6),
                                   x.get("a3_structure_id")])
        elif x["sub_rule"].endswith("failed"):
            out["cancels"].append([d, x.get("failure_reason")])
    return out


def summarize_ref(events, g):
    out = {"touches": [], "signals": [], "cancels": []}
    for e in events:
        if e.get("group") != g:
            continue
        if e["type"] == "touch":
            out["touches"].append([e["date"], e["first"]])
        elif e["type"] == "signal" and e.get("variant", "early") == "early":
            out["signals"].append([e["date"], e["first"], round(e["C"], 6), e.get("a3_structure")])
        elif e["type"] == "cancel":
            out["cancels"].append([e["date"], e["reason"]])
    return out


PROD_REASON = {"收盘跌破回撤结构低点（A5 结构失效）": "A5_low_broken_before_entry",
               "趋势生命周期重置（排列破坏/跌破SMA120/转黑）": "lifecycle_reset",
               "价格离开回撤区且未触发入场": "left_zone_no_entry"}
REF_RESET = {"black", "stack_or_sma120", "data_gap"}


def _norm(cancels, prod):
    if prod:
        return [[d, PROD_REASON.get(r, r)] for d, r in cancels]
    return [[d, "lifecycle_reset" if r in REF_RESET else r] for d, r in cancels]


def main() -> int:
    expected = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
    results, failures = {}, []
    for name, spec in CASES.items():
        g, structs = spec["focus"], spec.get("structures", [])
        frame = make(spec["days"], INIT)
        rows = rows_of(frame)
        mode = spec.get("a3_mode", "any")
        rec = summarize_ref(run_reference(rows, structures=structs, **{**RECOMMENDED, "a3_mode": mode}), g)
        prod_mode = summarize_ref(run_reference(rows, structures=structs, **PRODUCTION), g)
        prod_events = production(frame, structs)
        prod = summarize_prod(prod_events, g)
        item = {"focus_group": g, "a3_mode": mode, "recommended": rec,
                "reference_in_production_mode": prod_mode, "production_code": prod,
                "input_table": table(frame, groups=(20, g) if g != 20 else (20,))}
        exp = expected[name]
        got = {k: [row[:3] for row in rec[k]] if k == "signals" else rec[k] for k in rec}
        ok = all(got[k] == exp[k] for k in ("touches", "signals", "cancels"))
        if spec.get("a3_compare"):
            sr = summarize_ref(run_reference(rows, structures=structs,
                                             **{**RECOMMENDED, "a3_mode": "structure_required"}), g)
            item["structure_required"] = sr
            e2 = exp["structure_required"]
            ok = ok and all(([r[:3] for r in sr[k]] if k == "signals" else sr[k]) == e2[k]
                            for k in ("touches", "signals", "cancels"))
        mirror = (prod_mode["touches"] == prod["touches"]
                  and _norm(prod_mode["cancels"], False) == _norm(prod["cancels"], True)
                  and prod_mode["signals"] == prod["signals"])
        item["recommended_matches_hand_answer"] = ok
        item["production_mode_reference_matches_production_code"] = mirror
        if spec.get("target_check"):
            entry = next(e for e in prod_events if e.evidence.get("ma_period") == g
                         and e.evidence.get("entry_variant") == "early")
            rr = compute_reward_risk(frame, entry, confirmed_pivots(frame))
            item["production_reward_risk"] = {"target_b": rr.target_b, "source": rr.target_source,
                                              "rr": rr.reward_risk, "computable": rr.computable}
        if not ok:
            failures.append(f"{name}: recommended != hand answer")
        if not mirror:
            failures.append(f"{name}: production-mode reference != production code")
        results[name] = item
    (HERE / "case-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n",
                                            encoding="utf-8")
    for name, item in results.items():
        print(name, "hand_ok=", item["recommended_matches_hand_answer"], "prod_mirror=",
              item["production_mode_reference_matches_production_code"])
        print("   recommended:", item["recommended"]["signals"], item["recommended"]["cancels"])
        print("   production :", item["production_code"]["touches"], item["production_code"]["signals"],
              item["production_code"]["cancels"])
        if "production_reward_risk" in item:
            print("   production R/R:", item["production_reward_risk"])
    print("FAILURES:", failures or "none")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
