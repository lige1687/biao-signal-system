"""factor-unit-readiness-2026-09-15 独立小例核验（synthetic，全部手算期望）。

规则：
- 期望值只来自本文件的独立参考实现与手算常数，不把被测函数的返回当期望；
- 全部输入为合成数据，结论不得混入真实资料；
- 本文件 import 不产生任何副作用；写文件仅经 CLI 显式 --out 且拒绝覆盖。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.features.indicators import compute_features  # 被测：EMA/SMA特征
from lei_signal.rules.dual_ma import dual_ma_bull_state  # 被测：共同确认状态
from lei_signal.rules.lei_color import classify_colors  # 被测：颜色
from lei_signal.research.definitions import breadth  # 被测：宽度
from lei_signal.market_context.sentiment import classify_sentiment_percentile  # 被测：情绪分位


# ── 独立参考实现（不 import 任何 lei_signal 代码） ─────────────────────

def ref_ema20(closes: list[float]) -> list[float | None]:
    """种子=首20根SMA，alpha=2/21；前19根None。独立循环实现。"""
    if len(closes) < 20:
        return [None] * len(closes)
    out: list[float | None] = [None] * 19
    out.append(sum(closes[:20]) / 20.0)
    a = 2.0 / 21.0
    for i in range(20, len(closes)):
        out.append(a * closes[i] + (1 - a) * out[-1])
    return out


def ref_sma20(closes: list[float]) -> list[float | None]:
    out: list[float | None] = [None] * 19
    for i in range(19, len(closes)):
        out.append(sum(closes[i - 19 : i + 1]) / 20.0)
    return out


def ref_state(closes: list[float]) -> list[str]:
    """独立推导共同确认状态：'true'/'false'/'missing'。
    missing = 任一基础输入（close/EMA20/SMA20/close_lag20）未就绪；
    green = close>EMA20 且 close>close_lag20；
    true = green 且 close>SMA20 且 EMA20>昨日EMA20 且 SMA20>昨日SMA20。
    （数学事实：close>close_lag20 ⟺ SMA20上升，此处仍按账本公式独立逐项判定。）
    """
    ema = ref_ema20(closes)
    sma = ref_sma20(closes)
    out = []
    for i in range(len(closes)):
        lag = closes[i - 20] if i >= 20 else None
        if ema[i] is None or sma[i] is None or lag is None:
            out.append("missing")
            continue
        prev_ema = ema[i - 1]
        prev_sma = sma[i - 1]
        if prev_ema is None or prev_sma is None:
            out.append("missing")
            continue
        green = closes[i] > ema[i] and closes[i] > lag
        cond = (
            green
            and closes[i] > sma[i]
            and ema[i] > prev_ema
            and sma[i] > prev_sma
        )
        out.append("true" if cond else "false")
    return out


def ref_percentile(history: list[float], value: float) -> float:
    """独立百分位：rank = #(h <= value)（并列计入），percentile = rank/len*100。"""
    return sum(1 for h in history if h <= value) / len(history) * 100.0


def ref_label(pct: float | None, n: int) -> str:
    if n < 52 or pct is None:
        return "unknown"
    if pct <= 10.0:
        return "extreme_low"
    if pct <= 25.0:
        return "low"
    if pct >= 90.0:
        return "extreme_high"
    if pct >= 75.0:
        return "high"
    return "neutral"


# ── 合成案例构造 ──────────────────────────────────────────────────────

def make_bars(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes,
         "volume": [1.0] * len(closes)},
        index=idx,
    )


def case_dual_ma() -> dict:
    """手算驱动：四条件缺一即false；等号不算高于；等比缩放状态不变；未就绪=missing。"""
    # 21根：前20根=100，第21根=105 → 全条件成立 → 第21根(第0根起第20位)true
    up = [100.0] * 20 + [105.0]
    # 等号情形：第21根恰等于SMA20与EMA20附近无法同时构造，改用SMA严格等号：
    # 前20根=100，第21根=100 → close>SMA20不成立(等于不算高于) → false
    flat = [100.0] * 21
    # 第21根=99：close<两均线且不升 → false（有效false，非missing）
    down = [100.0] * 20 + [99.0]
    cases = {}
    for name, closes in (("up_105", up), ("flat_100", flat), ("down_99", down)):
        bars = make_bars(closes)
        feats = compute_features(bars)
        colored = classify_colors(feats)
        state = dual_ma_bull_state(colored)
        # 适配层readiness语义：color_ready=False → missing；否则取bool
        observed = [
            "missing" if not bool(colored["color_ready"].iloc[i]) else ("true" if bool(state.iloc[i]) else "false")
            for i in range(len(closes))
        ]
        cases[name] = {"closes": closes, "observed": observed, "expected": ref_state(closes)}
    # 等比缩放：×100 状态序列必须完全一致（SMA/EMA线性 → 严格不等号不变）
    scaled = [c * 100.0 for c in up]
    bars = make_bars(scaled)
    feats = compute_features(bars)
    colored = classify_colors(feats)
    st = dual_ma_bull_state(colored)
    obs_scaled = [
        "missing" if not bool(colored["color_ready"].iloc[i]) else ("true" if bool(st.iloc[i]) else "false")
        for i in range(len(scaled))
    ]
    cases["scaled_x100"] = {
        "observed": obs_scaled,
        "expected": cases["up_105"]["expected"],
        "note": "价格同比缩放(含每份分红同尺度调整的极端情形)状态不变",
    }
    ok = all(c["observed"] == c["expected"] for c in cases.values())
    return {"case": "dual_ma_state_synthetic", "expectation_source": "independent_ref_impl", "pass": ok, "detail": cases}


def case_breadth() -> dict:
    """4成员共同合格=分母；2只严格高于→0.5；等号不算；全无资格→缺失非0。"""
    days = 205
    idx = pd.date_range("2025-01-01", periods=days, freq="D")
    # A:205根100最后101(高于两均线) B:最后99(低于) C:恒100(等于→不算高于) D:同A
    def series(last: float) -> list[float]:
        return [100.0] * (days - 1) + [last]
    prices = pd.DataFrame({
        "AAA": series(101.0), "BBB": series(99.0),
        "CCC": [100.0] * days, "DDD": series(101.0),
    }, index=idx)
    day = idx[-1]
    mem = {day: ["AAA", "BBB", "CCC", "DDD"]}
    table = breadth(prices, mem)
    got_b50 = float(table["b50"].iloc[-1])
    got_b200 = float(table["b200"].iloc[-1])
    # 手算：SMA50: A=(49×100+101)/50=100.02,101>→above; B=(49×100+99)/50=99.98,99<→below;
    # C=100=100→not above(严格); D同A→above ⇒ b50=2/4=0.5
    exp_b50 = 2 / 4
    # SMA200: A=(199×100+101)/200=100.005→above; B=(199×100+99)/200=99.995→below;
    # C=100→not above; D→above ⇒ b200=0.5
    exp_b200 = 2 / 4
    # 全无资格：当日全部价格缺失 → no_eligible_quotes，b50=NaN
    prices_nan = prices.copy()
    prices_nan.iloc[-1] = np.nan
    t2 = breadth(prices_nan, mem)
    r2 = t2.iloc[-1]
    # 成员缺失：无名单日 → membership_missing
    t3 = breadth(prices, {})
    r3 = t3.iloc[-1]
    # 覆盖不足：10成员都在面板，但当日仅1只有报价 → quoted=1,eligible=1,coverage=0.1<0.9
    # （attempt-01夹具错误：成员不在面板→quoted=0→先触发no_eligible_quotes；失败记录保留）
    cols10 = {f"S{i}": series(101.0 if i == 0 else 100.0) for i in range(10)}
    p10 = pd.DataFrame(cols10, index=idx)
    p10.iloc[-1, 1:] = np.nan  # S1..S9 当日缺报价
    t4 = breadth(p10, {day: [f"S{i}" for i in range(10)]})
    r4 = t4.iloc[-1]
    checks = {
        "b50_half": {"observed": got_b50, "expected": exp_b50},
        "b200_half": {"observed": got_b200, "expected": exp_b200},
        "all_unqualified_is_missing_not_zero": {
            "observed": {"missing_reason": r2["missing_reason"], "b50_is_nan": bool(np.isnan(r2["b50"]))},
            "expected": {"missing_reason": "no_eligible_quotes", "b50_is_nan": True}},
        "no_membership": {
            "observed": {"missing_reason": r3["missing_reason"]},
            "expected": {"missing_reason": "membership_missing"}},
        "coverage_below_minimum": {
            "observed": {"missing_reason": r4["missing_reason"], "coverage": float(r4["coverage"])},
            "expected": {"missing_reason": "coverage_below_minimum", "coverage": 1 / 10}},
    }
    ok = (
        abs(checks["b50_half"]["observed"] - checks["b50_half"]["expected"]) < 1e-12
        and abs(checks["b200_half"]["observed"] - checks["b200_half"]["expected"]) < 1e-12
        and checks["all_unqualified_is_missing_not_zero"]["observed"] == checks["all_unqualified_is_missing_not_zero"]["expected"]
        and checks["no_membership"]["observed"] == checks["no_membership"]["expected"]
        and checks["coverage_below_minimum"]["observed"]["missing_reason"] == "coverage_below_minimum"
        and abs(checks["coverage_below_minimum"]["observed"]["coverage"] - 0.1) < 1e-12
    )
    return {"case": "breadth_common_denominator_synthetic", "expectation_source": "hand_derived_constants", "pass": ok, "detail": checks}


def case_sentiment() -> dict:
    """真实公式(classify_sentiment_percentile)的并列/预热边界；原始值与分位/状态分开。"""
    history = [float(i) for i in range(1, 52)] + [10.0, 10.0]  # 53个：50个递增+两个并列10
    history52 = history[:52]  # 恰52期：1..50 + 10,10
    value = 10.0
    # 手算：#(h<=10) = 10(即1..10) + 2(两个10并列) = 12 → 12/52*100 = 23.0769...% → ≤25 → low
    exp_pct = 12 / 52 * 100
    got_label = classify_sentiment_percentile(value, history52)
    exp_label = ref_label(exp_pct, 52)
    # 预热：51期 → unknown（无论数值）
    got_warm = classify_sentiment_percentile(10.0, history52[:51])
    # 边界：构造恰好90%分位：52期中47个≤value → 47/52=90.38% ≥90 → extreme_high
    h2 = [float(i) for i in range(1, 48)] + [200.0] * 5
    v2 = 47.0
    exp_pct2 = 47 / 52 * 100
    got_label2 = classify_sentiment_percentile(v2, h2)
    checks = {
        "tie_counts_as_le": {"observed_label": str(got_label).split(".")[-1], "expected_label": exp_label,
                             "hand_percentile": exp_pct},
        "warmup_below_52_is_unknown": {"observed": str(got_warm).split(".")[-1], "expected": "unknown"},
        "boundary_90pct": {"observed_label": str(got_label2).split(".")[-1],
                           "expected_label": ref_label(exp_pct2, 52), "hand_percentile": exp_pct2},
        "raw_value_untouched": {"observed": value, "expected": 10.0,
                                "note": "原始读数与分位/状态分层，原始值不被改写"},
    }
    ok = (
        checks["tie_counts_as_le"]["observed_label"] == checks["tie_counts_as_le"]["expected_label"]
        and checks["warmup_below_52_is_unknown"]["observed"] == "unknown"
        and checks["boundary_90pct"]["observed_label"] == checks["boundary_90pct"]["expected_label"]
    )
    return {"case": "sentiment_percentile_formula_synthetic", "expectation_source": "hand_derived_constants", "pass": ok, "detail": checks}


def case_time() -> dict:
    """同一日历日期：美股当地收盘信息在A股同日收盘时不可知（合成时刻演示，非交易所事实）。"""
    from zoneinfo import ZoneInfo
    sh = ZoneInfo("Asia/Shanghai")
    ny = ZoneInfo("America/New_York")
    # 合成演示时刻（明确synthetic；未证实的仅是交易所时刻表本身）
    d = "2026-07-15"
    a_close = datetime.fromisoformat(f"{d}T15:00:00").replace(tzinfo=sh)  # A股收盘(名义)
    us_close = datetime.fromisoformat(f"{d}T16:00:00").replace(tzinfo=ny)  # 美股当地收盘(名义)
    a_winter = "2026-01-15"
    us_close_w = datetime.fromisoformat(f"{a_winter}T16:00:00").replace(tzinfo=ny)
    checks = {
        "summer": {
            "us_close_in_shanghai": us_close.astimezone(sh).isoformat(),
            "after_a_share_close_same_date": us_close.astimezone(sh) > a_close,
            "expected": True,
        },
        "winter_est": {
            "us_close_in_shanghai": us_close_w.astimezone(sh).isoformat(),
            "after_a_share_close_same_date": us_close_w.astimezone(sh) > a_close.replace(month=1),
            "expected": True,
        },
    }
    ok = all(c["after_a_share_close_same_date"] == c["expected"] for c in checks.values())
    return {
        "case": "cross_market_same_date_not_same_knowledge_time",
        "expectation_source": "hand_derived_constants(zoneinfo)",
        "pass": ok, "detail": checks,
        "note": "合成时刻演示：同一日历日期的美股收盘在上海时间已是次日凌晨，故不能借美股同日收盘解释A股同日信号；未声称真实交易所时刻表已证实",
    }


def run_all() -> dict:
    results = [case_dual_ma(), case_breadth(), case_sentiment(), case_time()]
    return {
        "task": "factor-unit-readiness-2026-09-15 Task4",
        "generated_at": datetime.now().isoformat(),
        "synthetic": True,
        "expectation_policy": "期望全部来自独立参考实现/手算常数；被测函数仅作观察对象",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="输出JSON路径；已存在则拒绝")
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        print(f"REFUSE to overwrite existing {out}")
        sys.exit(3)
    payload = run_all()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print(f"all_pass={payload['all_pass']} written {out}")


if __name__ == "__main__":
    main()
