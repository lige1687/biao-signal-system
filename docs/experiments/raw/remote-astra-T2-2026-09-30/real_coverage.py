"""T2 机会覆盖与口径差异计数（只数事件与标签，不计算任何未来收益）。

输入：GitHub 已跟踪的两只 ETF 名义日线（冻结宽基技术研究 inputs/bars），510300 按
inputs/actions.json 现金分红做前复权（研究代理，仅用于技术指标，不是成交价）。
特征、时钟、周线、ATR、严格底部构造全部调用生产函数；两种生命周期读法共享同一输入，
差异只来自 lifecycle_ref 的开关。构造识别沿用生产全历史计算（已知包含K线合并可能改写
历史，见 factor-system-increment-review-2026-09-27 §4），此处两种读法共用，不影响对比口径。
输出：real-coverage.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path[:0] = [str(HERE), str(REPO / "src")]

from lei_signal.features.indicators import average_true_range, compute_features  # noqa: E402
from lei_signal.features.weekly_context import weekly_env_series  # noqa: E402
from lei_signal.rules.clock_classifier import clock_series  # noqa: E402
from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events  # noqa: E402
from lei_signal.rules.lei_color import classify_colors  # noqa: E402
from lei_signal.rules.strict_structure import SIDE_BOTTOM, detect_strict_structures  # noqa: E402
from lifecycle_ref import PRODUCTION, RECOMMENDED, run_reference  # noqa: E402

INPUTS = REPO / "docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/inputs"
SYMBOLS = ("sh510300", "sz159915")


def load(symbol: str) -> tuple[pd.DataFrame, list[dict]]:
    bars = pd.read_csv(INPUTS / f"bars/{symbol}-nominal.csv", parse_dates=["date"]).set_index("date")
    applied = []
    actions = json.loads((INPUTS / "actions.json").read_text(encoding="utf-8"))
    for act in sorted((a for a in actions if a["symbol"] == symbol and a["type"] == "cash_dividend"),
                      key=lambda a: a["effective_date"]):
        ex = pd.Timestamp(act["effective_date"])
        before = bars.index[bars.index < ex]
        if len(before) == 0 or ex > bars.index[-1]:
            continue
        prev_close = float(bars.loc[before[-1], "close"])
        factor = (prev_close - float(act["cash"])) / prev_close
        for col in ("open", "high", "low", "close"):
            bars.loc[bars.index < ex, col] *= factor
        applied.append({"ex_date": act["effective_date"], "cash": act["cash"], "factor": factor})
    return bars, applied


def features(bars: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    frame = classify_colors(compute_features(bars))
    frame["clock"] = clock_series(frame).astype(int)
    frame["weekly"] = weekly_env_series(frame).astype(bool)
    frame["atr20"] = average_true_range(frame, 20)
    structs = [dict(id=s.structure_id, confirmed_date=s.confirmed_date.isoformat(),
                    invalidated_date=s.invalidated_date.isoformat() if s.invalidated_date else None)
               for s in detect_strict_structures(frame) if s.side == SIDE_BOTTOM]
    return frame, structs


def rows_of(frame: pd.DataFrame) -> list[dict]:
    keep = ["open", "high", "low", "close", "clock", "weekly", "atr20"] + [
        f"{p}{n}" for p in ("sma", "ema", "close_lag") for n in (20, 60, 120)]
    out = []
    for ts, rec in zip(frame.index, frame[keep].to_dict("records"), strict=True):
        row = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in rec.items()}
        row["weekly"] = bool(row["weekly"])
        row["clock"] = int(row["clock"])
        row["date"] = ts.date().isoformat()
        out.append(row)
    return out


def prod_events(frame: pd.DataFrame, symbol: str) -> list[dict]:
    out = []
    for e in detect_first_ma_pullback_events(frame, symbol):
        x = e.evidence
        sub = x["sub_rule"].replace("first_ma_pullback_", "")
        if sub == "confirmed" and x.get("entry_variant") != "early":
            continue
        out.append(dict(date=e.available_date.isoformat(), group=x["ma_period"], kind=sub,
                        first=x["is_first_touch"], touch=x.get("touch_date"),
                        C=round(float(x["stop_price"]), 9) if x.get("stop_price") is not None else None,
                        structure=x.get("a3_structure_id"), reason=x.get("failure_reason")))
    return out


def ref_events(rows, structs, opts):
    out = []
    for e in run_reference(rows, structures=structs, **opts):
        if e["type"] not in ("touch", "signal", "cancel"):
            continue
        if e["type"] == "signal" and e.get("variant") != "early":
            continue
        kind = {"touch": "touched", "signal": "confirmed", "cancel": "failed"}[e["type"]]
        out.append(dict(date=e["date"], group=e["group"], kind=kind, first=e["first"],
                        touch=e.get("touch", e["date"]), C=round(e["C"], 9) if "C" in e else None,
                        structure=e.get("a3_structure"), reason=e.get("reason")))
    return out


def mirror(prod, ref):
    key = lambda e: (e["date"], e["group"], e["kind"], e["first"], e["C"])  # noqa: E731
    p, r = Counter(map(key, prod)), Counter(map(key, ref))
    return {"production_events": sum(p.values()), "reference_events": sum(r.values()),
            "only_production": sorted(map(list, (p - r).elements()))[:10],
            "only_reference": sorted(map(list, (r - p).elements()))[:10],
            "identical": p == r}


def summarize(events):
    sig = [e for e in events if e["kind"] == "confirmed"]
    tch = [e for e in events if e["kind"] == "touched"]
    by_group = {}
    for g in (20, 60, 120):
        gs, gt = [e for e in sig if e["group"] == g], [e for e in tch if e["group"] == g]
        by_group[g] = {"touches": len(gt), "touch_first": Counter(str(e["first"]) for e in gt),
                       "signals": len(gs), "signal_first": Counter(str(e["first"]) for e in gs),
                       "signal_years": Counter(e["date"][:4] for e in gs),
                       "a3_structure": sum(1 for e in gs if e["structure"])}
    return by_group


def compare(prod, rec, structs):
    """把生产入场映射到推荐读法的同一次回撤（同组、生产入场日落在推荐回撤存续期内）。"""
    inval = {s["id"]: s["invalidated_date"] for s in structs}
    rec_sig = [e for e in rec if e["kind"] == "confirmed"]
    rec_windows = {}
    for e in rec:
        if e["kind"] in ("confirmed", "failed"):
            rec_windows.setdefault(e["group"], []).append((e["touch"], e["date"], e))
    out = {"production_signals": 0, "matched_same_pullback": 0, "first_flag_differs": 0,
           "stop_raised_vs_pullback_low": 0, "stop_lowered": 0, "unmatched_production": 0,
           "stale_structure_citations": 0, "recommended_signals": len(rec_sig), "examples": []}
    for e in (x for x in prod if x["kind"] == "confirmed"):
        out["production_signals"] += 1
        if e["structure"] and inval.get(e["structure"]) and inval[e["structure"]] <= e["date"]:
            out["stale_structure_citations"] += 1
            out["examples"].append({"type": "stale_structure", **e})
        hit = next((w for w in rec_windows.get(e["group"], []) if w[0] <= e["date"] <= w[1]), None)
        if hit is None:
            out["unmatched_production"] += 1
            continue
        out["matched_same_pullback"] += 1
        ref = hit[2]
        if ref["kind"] == "confirmed":
            if ref["first"] != e["first"]:
                out["first_flag_differs"] += 1
                if len(out["examples"]) < 12:
                    out["examples"].append({"type": "first_flag", "production": e, "recommended": ref})
            if e["C"] is not None and ref["C"] is not None:
                out["stop_raised_vs_pullback_low"] += e["C"] > ref["C"] + 1e-12
                out["stop_lowered"] += e["C"] < ref["C"] - 1e-12
    return out


def unmatched_reasons(frame, prod, rec, episode_opens):
    """把“不落在推荐读法任何一次回撤内”的生产入场按其触碰前发生了什么分类。

    上次结束 = 同组上一次生产候选结束（失败或两版都已发出）或趋势段开启，取较晚者；
    “整天离开” = 期间某日最低价 > SMA_g + ATR20（推荐读法的武装条件）。
    """
    clear = {g: (frame["low"] > frame[f"sma{g}"] + frame["atr20"]) for g in (20, 60, 120)}
    days = [ts.date().isoformat() for ts in frame.index]
    pos = {d: i for i, d in enumerate(days)}
    windows, ends = {}, {}
    for e in rec:
        if e["kind"] in ("confirmed", "failed"):
            windows.setdefault(e["group"], []).append((e["touch"], e["date"]))
    for e in prod:
        if e["kind"] == "failed":
            ends.setdefault(e["group"], []).append((e["date"], e["reason"]))
        elif e["kind"] == "confirmed":
            ends.setdefault(e["group"], []).append((e["date"], "previous_entry"))
    label = {"收盘跌破回撤结构低点（A5 结构失效）": "after_A5_low_cancel",
             "价格离开回撤区且未触发入场": "after_left_zone_end",
             "趋势生命周期重置（排列破坏/跌破SMA120/转黑）": "after_lifecycle_reset",
             "previous_entry": "after_previous_entry"}
    reasons, rec_hit = Counter(), set()
    for e in (x for x in prod if x["kind"] == "confirmed"):
        g = e["group"]
        w = next((w for w in windows.get(g, []) if w[0] <= e["date"] <= w[1]), None)
        if w:
            rec_hit.add((g, w))
            continue
        prior = [x for x in ends.get(g, []) if x[0] < e["touch"]]
        opens = [d for d in episode_opens if d <= e["touch"]]
        last_end = max(prior)[0] if prior else days[0]
        last_open = max(opens) if opens else days[0]
        if last_open > last_end:
            start, why = last_open, "after_episode_open"
        else:
            start, why = last_end, label.get(max(prior)[1], "other") if prior else "series_start"
        departed = bool(clear[g].iloc[pos[start] + 1: pos[e["touch"]]].any())
        reasons[("departed_" if departed else "no_departure_") + why] += 1
    rec_windows_with_signal = {(e["group"], e["touch"]) for e in rec if e["kind"] == "confirmed"}
    rec_only = sum(1 for g, ws in windows.items() for w in ws
                   if (g, w[0]) in rec_windows_with_signal and (g, w) not in rec_hit)
    return {"unmatched_production_entries": dict(reasons),
            "recommended_entries_without_production_entry_in_window": rec_only}


def main() -> None:
    result = {"_note": "只计数事件/标签/止损价差异，不含任何未来收益；名义价，510300 前复权为研究代理。"}
    for symbol in SYMBOLS:
        bars, applied = load(symbol)
        frame, structs = features(bars)
        rows = rows_of(frame)
        prod = prod_events(frame, symbol)
        ref_prod = ref_events(rows, structs, PRODUCTION)
        rec = ref_events(rows, structs, RECOMMENDED)
        rec_strict = ref_events(rows, structs, {**RECOMMENDED, "a3_mode": "structure_required"})
        rec_sig = {(e["group"], e["touch"]): e for e in rec if e["kind"] == "confirmed"}
        strict_sig = {(e["group"], e["touch"]): e for e in rec_strict if e["kind"] == "confirmed"}
        a3 = {"any_signals": len(rec_sig), "structure_required_signals": len(strict_sig),
              "same_day": sum(1 for k, v in strict_sig.items() if k in rec_sig and rec_sig[k]["date"] == v["date"]),
              "delayed": sum(1 for k, v in strict_sig.items() if k in rec_sig and rec_sig[k]["date"] < v["date"]),
              "dropped_by_structure_requirement": sum(1 for k in rec_sig if k not in strict_sig)}
        result[symbol] = {
            "rows": len(frame), "first_date": frame.index[0].date().isoformat(),
            "last_date": frame.index[-1].date().isoformat(), "dividend_adjustments": len(applied),
            "bottom_structures": len(structs),
            "days_gate_open": int(((frame["sma20"] > frame["sma60"]) & (frame["sma60"] > frame["sma120"])
                                   & (frame["ema20"] > frame["ema60"]) & (frame["ema60"] > frame["ema120"])
                                   & (frame["clock"] == 2) & frame["weekly"]).sum()),
            "mirror_check_production_mode_vs_production_code": mirror(prod, ref_prod),
            "production_code": summarize(prod), "recommended_any": summarize(rec),
            "recommended_structure_required": summarize(rec_strict),
            "production_vs_recommended": compare(prod, rec, structs),
            "unmatched_production_reasons": unmatched_reasons(
                frame, prod, rec, [e["date"] for e in run_reference(rows, structures=structs, **PRODUCTION)
                                   if e["type"] == "episode_open"]),
            "a3_mode_coverage_recommended": a3,
        }
    (HERE / "real-coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=1,
                                                        default=dict) + "\n", encoding="utf-8")
    for symbol in SYMBOLS:
        s = result[symbol]
        print(symbol, s["rows"], s["first_date"], s["last_date"], "gate_days", s["days_gate_open"],
              "structs", s["bottom_structures"])
        m = s["mirror_check_production_mode_vs_production_code"]
        print("  mirror identical:", m["identical"], m["production_events"], m["reference_events"])
        if not m["identical"]:
            print("   only_prod", m["only_production"][:5])
            print("   only_ref ", m["only_reference"][:5])
        for mode in ("production_code", "recommended_any", "recommended_structure_required"):
            print("  ", mode, {g: (v["touches"], dict(v["touch_first"]), v["signals"], dict(v["signal_first"]),
                                   v["a3_structure"]) for g, v in s[mode].items()})
        c = {k: v for k, v in s["production_vs_recommended"].items() if k != "examples"}
        print("   compare", c)
        print("   unmatched reasons", s["unmatched_production_reasons"])
        print("   a3", s["a3_mode_coverage_recommended"])


if __name__ == "__main__":
    main()
