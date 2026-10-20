#!/usr/bin/env python3
"""债务三复核：中证500ETF（510500）"不适合这套规则"的判负结论重审。
预注册三选一判定标准（2026-09-03 跑前写死，跑后不得调整）。

【背景】
第9轮（execution_playbook_20260827.md 排除清单）判 510500「基准过强不适配」：
全窗策略超额 -9.8%（持有年化 +18.1% 远超策略 +8.7%）。跳变审计发现该判负
建立在被污染数据上：510500 的 timing 缓存有 2 个复权断裂（2015-04-15
+248.6% 拆分未复权、2022-08-29 -12.7%），修平后全窗超额 -10.3%→+0.5%，
审计建议"重审，不直接下入选结论"。

【当初判定口径（事后重建，如实注明）】
第9轮排除清单未写明确判定线，其数字为"B200 三档逆势 30/70（无闸）全窗
超额 -9.8%、明显为负"。本复核事后重建口径为该家族第十四轮终审协议：
入选线=无闸版三窗（全窗/前半/后半，行数中点切分）超额全>0；未达线且
全窗明显为负=判负。重建依据：full_audit_20260827.py 第十四轮与
data-quality-jump-audit 对 510500 的加跑均用此框架。

【修平方法（复用审计预注册函数，不重新发明）】
flatten_jumps：跳变日 D 起 OHLC 同除 close[D]/close[D-1]（收益置0），
多跳变按时间序。跳变清单照抄审计：510500 = [2015-04-15, 2022-08-29]。

【重跑框架（原规则原参数，不调参不挑选）】
与审计/第十四轮完全一致：LadderParams(b200, 3bands, fixed, contrarian,
30/70, gamma1, min_weight0) × {无闸, +MA200闸(cap=0)} × 三窗（行数中点切分），
min_trade=0.05，cn_all 宽度，对齐后逐日模拟。费用跑两档并全部披露：
10bp（第十四轮终审标准）与 1bp（第9轮 playbook 原口径），用于检验判定
对费用这一非核心选择的稳健性——两档都不做挑选，全报。

【预注册三选一判定（跑前写死）】
- 翻案为「值得进一步验证」：修平后无闸版三窗超额全>0（全窗/前半/后半
  均为正，即达到第十四轮入选审计同一条线，明显高于"打平"），且 10bp 与
  1bp 两种费用口径下该布尔一致。即使翻案也只标记"值得进一步验证"，
  不下入选结论（审计红线）。
- 维持判负：两种费用口径下，无闸三窗均未全正（任一窗 ≤0）。
- 证据不足：修平数据无法构建（跳变日不在索引/宽度缺失），或"三窗全正"
  布尔在两种费用口径间不一致（判定对非核心选择不稳健）。

【红线】只读缓存；不产生买卖点；不合成数据；输出仅新增 JSON。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.metrics import summarize_run  # noqa: E402
from lei_signal.timing_backtest.strategies import (  # noqa: E402
    LadderParams,
    TrendGate,
    build_target,
)

OUT_DIR = REPO / "docs/experiments/raw/agent_Y_pollution_recheck"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "csi500_510500_recheck.json"

SYMBOL = "510500"
JUMPS = ["2015-04-15", "2022-08-29"]  # 审计 JUMPS 表，逐字照抄
FEES = {"fee10bp": 10.0, "fee1bp_playbook": 1.0}  # 两档全跑，无挑选

# 审计 jump_audit_results.json 510500 无闸行（复现核对用）
AUDIT_REF = {
    "raw": {"full_excess": -0.1033, "h1_excess": -0.2367, "h2_excess": 0.0181,
            "full_bench_cagr": 0.1778},
    "fixed": {"full_excess": 0.0049, "h1_excess": -0.0084, "h2_excess": 0.0185,
              "full_bench_cagr": 0.0809},
}


def load_bars(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(TIMING_CACHE_DIR / f"{symbol}.parquet")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("high", "low"):
        if col not in df.columns:
            df[col] = (df[["open", "close"]].max(axis=1) if col == "high"
                       else df[["open", "close"]].min(axis=1))
    return df[["open", "high", "low", "close"]]


def flatten_jumps(bars: pd.DataFrame, dates: list[str]) -> pd.DataFrame:
    """审计预注册修平函数逐字复刻（多跳变按时间序）。"""
    df = bars.copy()
    for d in sorted(dates):
        ts = pd.Timestamp(d)
        i = df.index.get_loc(ts)
        prev_close = df["close"].iloc[i - 1]
        ratio = float(df["close"].iloc[i] / prev_close)
        mask = df.index >= ts
        for c in ("open", "high", "low", "close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
    return df


def run_ladder(aligned: pd.DataFrame, gate: bool, fee_bps: float,
               start=None, end=None) -> dict:
    window = aligned.loc[start:end] if (start or end) else aligned
    ladder = LadderParams(
        indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
        min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
    )
    gate_p = TrendGate(mode="ma200" if gate else "off", cap=0.0)
    warmup = aligned.loc[: window.index[0]].iloc[:-1]
    target = build_target(aligned, ladder, None, gate_p, warmup, vol_target=0.0)
    result = simulate(window, target.loc[window.index], fee_bps=fee_bps,
                      min_trade=0.05)
    return summarize_run(result.daily, result.trades)


def three_windows(aligned: pd.DataFrame, gate: bool, fee_bps: float) -> dict:
    mid = aligned.index[len(aligned) // 2]
    full = run_ladder(aligned, gate, fee_bps)
    h1 = run_ladder(aligned, gate, fee_bps, end=mid)
    h2 = run_ladder(aligned, gate, fee_bps, start=mid)
    return {
        "full_excess": round(full["excess_cagr"], 4),
        "h1_excess": round(h1["excess_cagr"], 4),
        "h2_excess": round(h2["excess_cagr"], 4),
        "all_positive": bool(full["excess_cagr"] > 0 and h1["excess_cagr"] > 0
                             and h2["excess_cagr"] > 0),
        "full_strat_cagr": round(full["strategy_cagr"], 4),
        "full_bench_cagr": round(full["benchmark_cagr"], 4),
        "full_strat_mdd": round(full["strategy_mdd"], 4),
        "full_bench_mdd": round(full["benchmark_mdd"], 4),
        "window": [str(aligned.index[0].date()), str(aligned.index[-1].date())],
    }


def main() -> None:
    breadth = load_breadth("cn_all")
    bars = load_bars(SYMBOL)
    fixed = flatten_jumps(bars, JUMPS)
    al_raw = align_index_breadth(bars, breadth)
    al_fix = align_index_breadth(fixed, breadth)

    results: dict = {
        "pre_registered_criteria": {
            "翻案为值得进一步验证": "修平后无闸三窗超额全>0，且 10bp/1bp 两费用口径布尔一致",
            "维持判负": "两费用口径下无闸三窗均未全正（任一窗<=0）",
            "证据不足": "数据无法构建，或三窗全正布尔在两费用口径间不一致",
            "framework": "30/70 3bands fixed contrarian gamma1 min_trade0.05 "
                         "cn_all {无闸,+MA200闸} 三窗中点切分（第十四轮协议）",
            "verdict_note": "即使翻案也仅'值得进一步验证'，非入选结论",
        },
        "jumps": JUMPS,
        "window": [str(al_raw.index[0].date()), str(al_raw.index[-1].date())],
        "audit_reference_10bp": AUDIT_REF,
        "runs": {},
    }

    all_positive_by_fee: dict[str, bool] = {}
    for fee_tag, fee_bps in FEES.items():
        for gate in (False, True):
            tag = f"{fee_tag}_{'gate' if gate else 'nogate'}"
            raw = three_windows(al_raw, gate, fee_bps)
            fix = three_windows(al_fix, gate, fee_bps)
            results["runs"][tag] = {
                "raw": raw, "fixed": fix,
                "delta_full_excess": round(fix["full_excess"] - raw["full_excess"], 4),
            }
            if not gate:
                all_positive_by_fee[fee_tag] = fix["all_positive"]
        print(f"[{fee_tag}] 无闸修平后三窗: "
              f"全窗{results['runs'][f'{fee_tag}_nogate']['fixed']['full_excess']:+.1%} "
              f"前半{results['runs'][f'{fee_tag}_nogate']['fixed']['h1_excess']:+.1%} "
              f"后半{results['runs'][f'{fee_tag}_nogate']['fixed']['h2_excess']:+.1%} "
              f"三窗全正={all_positive_by_fee[fee_tag]}")

    # ── 预注册三选一判定（机械输出）──
    vals = set(all_positive_by_fee.values())
    if len(vals) == 1 and vals == {True}:
        verdict = "翻案为值得进一步验证（非入选结论）"
    elif len(vals) == 1 and vals == {False}:
        verdict = "维持判负"
    else:
        verdict = "证据不足（费用口径间三窗全正布尔不一致）"
    results["verdict"] = {
        "decision": verdict,
        "all_positive_by_fee": all_positive_by_fee,
    }

    # 复现核对：10bp 无闸应与审计 JSON 一致（允许末位舍入差）
    repro = results["runs"]["fee10bp_nogate"]
    ok_raw = all(abs(repro["raw"][k] - AUDIT_REF["raw"][k]) < 5e-4
                 for k in ("full_excess", "h1_excess", "h2_excess"))
    ok_fix = all(abs(repro["fixed"][k] - AUDIT_REF["fixed"][k]) < 5e-4
                 for k in ("full_excess", "h1_excess", "h2_excess"))
    results["audit_reproduction_check"] = {"raw_match": ok_raw, "fixed_match": ok_fix}

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(
        json.dumps(results, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")
    print(f"判定: {verdict}")
    print(f"审计复现核对: raw_match={ok_raw} fixed_match={ok_fix}")


if __name__ == "__main__":
    main()
