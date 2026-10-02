"""T3 模块 B（均线密集区突破）八个人工案例＋一个补充：现行生产函数的实际行为 vs 按原文的判断。

只在内存中替换 dense_breakout 模块里的 clock_series（注入时钟类型）；带宽、寿命、
埋伏、突破、失效全部走生产代码。均线值直接给定（不是行情），因此可精确控制
“是否密集”“是否多头排列”“20 组是否下弯”。运行：python b_cases.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

import lei_signal.rules.dense_breakout as db  # noqa: E402

DENSE = dict(sma20=100.0, sma60=100.0, sma120=100.0, ema20=100.0, ema60=100.0, ema120=100.0)
ALIGNED = dict(sma20=100.8, sma60=100.4, sma120=100.0, ema20=100.9, ema60=100.5, ema120=100.1)  # 带宽 0.9%
WIDE = dict(sma20=100.0, sma60=100.0, sma120=95.0, ema20=100.0, ema60=100.0, ema120=95.0)  # 带宽 5.3%
NAN = float("nan")


def R(c, h=None, l=None, lines=DENSE, lag20=None, clock=3, **over):
    if c is None:
        return {"open": NAN, "high": NAN, "low": NAN, "close": NAN, "close_lag20": NAN,
                **{k: NAN for k in DENSE}, "_clock": 0}
    row = {"open": c, "high": c + 0.2 if h is None else h, "low": c - 0.2 if l is None else l, "close": c,
           "close_lag20": c if lag20 is None else lag20, **lines, "_clock": clock}
    row.update(over)
    return row


def frame_of(rows):
    f = pd.DataFrame(rows)
    f.index = pd.bdate_range("2024-01-01", periods=len(f))
    return f


def run(rows):
    f = frame_of(rows)
    clock = f.pop("_clock").astype(int)
    db.clock_series = lambda frame: clock.reindex(frame.index).fillna(0).astype(int)
    out = []
    for e in db.detect_dense_breakout_events(f, "SYN"):
        x = e.evidence
        out.append([int(f.index.get_loc(pd.Timestamp(e.available_date))),
                    x["sub_rule"].replace("dense_breakout_", ""), x.get("variant"),
                    None if x.get("reference_price") is None else round(float(x["reference_price"]), 4)])
    return out


def flat(n, **kw):
    return [R(100.0, **kw) for _ in range(n)]


CASES = {}

# 1 半年但从未真正整理：141 天里只有每 20 天一天是时钟三类，其余是二类（稳定上涨）
CASES["B1_half_year_never_consolidated"] = [R(100.0, clock=3 if i % 20 == 0 else 2) for i in range(150)]
# 2 短暂密集：时钟三类 200 天，六线只有第 150 天一天收敛到 2% 以内
CASES["B2_brief_density"] = ([R(100.0, lines=WIDE) for _ in range(150)] + [R(100.0)]
                             + [R(100.5, h=100.7)] + [R(100.5, lines=WIDE) for _ in range(48)])
# 3 成熟区域后一天离开：箱体早期最高 105，密集到第 190 天才达标；第 191 天收盘 100.6
_b3 = [R(100.0, lines=WIDE) for _ in range(190)]
_b3[50] = R(104.5, h=105.0, lines=WIDE)
CASES["B3_mature_zone_leaves_next_day"] = _b3 + [R(100.0, h=100.4), R(100.6, h=100.8)] + flat(8)
# 4 突破当天抬高区域边界：第 130 天最高 101.5、收盘 100.5
CASES["B4_breakout_day_raises_bound"] = flat(130) + [R(100.5, h=101.5), R(101.2, h=101.4)] + flat(18)
# 5 两失效动作相隔数天：130 突破（参照 100.2）；132 跌回参照下方但 20 组未下弯；136 20 组下弯但价在参照上方
_b5 = flat(130) + [R(100.6, h=100.8), R(100.7)]
_b5 += [R(100.1, lag20=100.0, **{**DENSE, "sma20": 99.9}), R(100.7), R(100.8), R(100.8)]
_b5 += [R(100.5, lag20=100.8, **{**DENSE, "sma20": 100.9})] + flat(13)
CASES["B5_two_failure_actions_days_apart"] = _b5
# 6 埋伏先失效再突破：128 多头排列刚形成；133 SMA20<=SMA60；140 收盘突破
_b6 = flat(128) + [R(100.0, lines=ALIGNED) for _ in range(5)]
_b6 += [R(100.0, lines={**ALIGNED, "sma20": 100.3})] + flat(6) + [R(100.6, h=100.8)] + flat(19)
CASES["B6_ambush_fails_then_breakout"] = _b6
# 7 缺价：105 天三类，随后 20 天无报价，再继续三类
CASES["B7_missing_quotes"] = flat(105) + [R(None) for _ in range(20)] + flat(35)
# 8 同区域重复触发：130 突破，133 两动作同日失效，134 起同一箱体
_b8 = flat(130) + [R(100.6, h=100.8), R(100.7), R(100.6)]
_b8 += [R(99.7, lag20=100.5, **{**DENSE, "sma20": 100.0})] + [R(99.8, h=100.0), R(100.1, h=100.2)] + flat(30)
CASES["B8_same_zone_repeat"] = _b8
# 9 补充：多头排列早已存在，不是“刚形成”
CASES["B9_supplement_alignment_not_new"] = [R(100.0, lines=ALIGNED) for _ in range(140)]


def main() -> int:
    exp = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
    out, fails = {}, []
    for name, rows in CASES.items():
        got = run(rows)
        e = exp[name]
        ok = got == e["predicted_code"]
        out[name] = {"production_events": got, "predicted_code": e["predicted_code"],
                     "original_reading": e["original_reading"], "code_matches_prediction": ok,
                     "code_matches_original_reading": got == e["original_reading"].get("events"),
                     "needs_user_choice": e["needs_user_choice"], "note": e["note"]}
        if not ok:
            fails.append(name)
    out["_note"] = "人工合成；时钟类型为注入值；其余为生产 dense_breakout 2.0.0 实际行为。事件格式 [第几天, 类型, 版本, 参照价]。"
    (HERE / "cases-output.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in out.items():
        if isinstance(v, dict):
            print(k, "pred_ok=", v["code_matches_prediction"], "orig_eq=", v["code_matches_original_reading"])
            print("   code:", v["production_events"])
    print("PREDICTION FAILURES:", fails or "none")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
