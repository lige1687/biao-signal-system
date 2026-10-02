"""T3 真实覆盖计数（只数事件，不算收益）：生产模块 B 在 GitHub 两只 ETF 日线上产生多少密集区与触发，
以及每次突破的参照价与“整理期（开区前时钟三类寿命覆盖的区间）最高价”相差多少。输出 real-coverage.json。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
T2 = HERE.parent / "remote-astra-T2-2026-09-30"
sys.path[:0] = [str(T2), str(REPO / "src")]

from lei_signal.features.indicators import compute_features  # noqa: E402
from lei_signal.rules.clock_classifier import TYPE3_SIDEWAYS, clock_series  # noqa: E402
from lei_signal.rules.dense_breakout import _state_age_series, detect_dense_breakout_events  # noqa: E402
from lei_signal.rules.lei_color import classify_colors  # noqa: E402
from real_coverage import SYMBOLS, load  # noqa: E402


def main() -> None:
    out = {"_note": "只计数；名义价，510300 前复权为研究代理；构造与时钟为生产函数。"}
    for symbol in SYMBOLS:
        frame = classify_colors(compute_features(load(symbol)[0]))
        clock3 = clock_series(frame) == TYPE3_SIDEWAYS
        age = _state_age_series(clock3, exit_bars=20)
        events = detect_dense_breakout_events(frame, symbol)
        kinds = Counter((e.evidence["sub_rule"].replace("dense_breakout_", ""), e.evidence.get("variant"))
                        for e in events)
        detail = []
        for e in events:
            if e.evidence["sub_rule"] != "dense_breakout_watch":
                continue
            i = frame.index.get_loc(e.available_date.isoformat())
            a = int(age.iloc[i])
            span = frame.iloc[max(0, i - a + 1): i + 1]
            real3 = int(clock3.iloc[max(0, i - a + 1): i + 1].sum())
            later = [x for x in events if x.lifecycle_id == e.lifecycle_id and x.evidence.get("variant") == "breakout"
                     and x.evidence["sub_rule"].endswith("confirmed")]
            detail.append({"open_date": e.available_date.isoformat(), "age_days": a, "clock3_days_in_age": real3,
                           "consolidation_high": round(float(span["high"].max()), 4),
                           "open_day_high": round(float(e.evidence["reference_price"]), 4),
                           "breakout": ({"date": later[0].available_date.isoformat(),
                                         "reference": round(float(later[0].evidence["breakout_reference"]), 4),
                                         "close": round(float(later[0].evidence["close"]), 4),
                                         "close_below_consolidation_high": float(later[0].evidence["close"])
                                         <= float(span["high"].max())} if later else None)})
        out[symbol] = {"events": {f"{k[0]}:{k[1]}": v for k, v in kinds.items()}, "zones": detail,
                       "zones_with_age_less_than_126_real_clock3_days": sum(d["clock3_days_in_age"] < 126 for d in detail)}
    (HERE / "real-coverage.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in SYMBOLS:
        print(s, out[s]["events"], "zones", len(out[s]["zones"]), "short_real", out[s]["zones_with_age_less_than_126_real_clock3_days"])
        for d in out[s]["zones"]:
            print("   ", d)


if __name__ == "__main__":
    main()
