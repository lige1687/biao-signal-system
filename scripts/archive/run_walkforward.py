"""walk-forward 时序终审（终极任务书目标 3，生死判）· 2026-08-27 第十三轮。

预注册口径（跑前落死，跑完不许改）：
- 数据窗：池 2016-08→2026-08；训练窗 3 年 → 验证窗下 1 年，逐年滚动，
  验证年 = 2020..2026 共 7 折（2016-2019 选参验 2020，依次前推）。
- 被审层与菜单（各层独立贪心选档，训练目标 = 训练窗终值最大）：
    A 变体：cm0.5+shrink（主口径）/ cm0.5 无 shrink / cm1.0+shrink
    B' 变体：cb30+cl3%（主口径）/ cb20+cl2% / cb40+cl4%
    宽度闸：无闸 / full_v2 五档 / h_80 五档 / split（A腿h_80+个股腿无闸）
    风险档：risk_pct 1% / 0.5%
  C/D 流固定不入菜单；黄金豁免固定。
- 验证执行：选定配置跑验证年（初始权益 = 上一折期末），期末结转，
  串成 walk-forward 权益曲线（2020-01→2026-08）。
- 判定（事前，J-W 生死判）：
  J-W1（串联）：WF 曲线年化 >= 0.5 × 沪深300 同窗 BH 年化
      且 WF 最大回撤 <= 0.6 × BH 最大回撤（数值上更浅）。
  J-W2（层稳定）：每层「被选档 vs 固定主口径」的验证段终值超额
      为正的折数占比 >= 60%（4 层各自判）。
  通过 = J-W1 且 J-W2 四层全过；否则如实宣布幻觉层。
- 声明：execute_run 新增 4 个（2 A 变体 + 2 B' 变体，N 账本 +4）；
  训练目标只用终值（无 dd 正则，简单性优先，声明）；每折独立选参
  无前视（只用训练窗内入场的信号）。

输出：raw/breadth_overlay/walkforward_results.json + wf_equity.csv
复现：python3 scripts/run_walkforward.py（首次生成变体 run 后约 5-10 分钟）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_final_form_v2 import H80  # noqa: E402
from run_full_stack_sim import (  # noqa: E402
    build_pools,
    gate_a,
    load_runs,
)
from run_symbol_tilt import merge_curves, sim_weighted  # noqa: E402

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
VAL_YEARS = list(range(2020, 2027))
TRAIN_YEARS = 3
W1 = lambda s, d: 1.0  # noqa: E731


def run_or_cache(name: str, symbols, kw: dict) -> list[dict]:
    path = RAW / f"wf_{name}.json"
    if path.exists():
        r = json.loads(path.read_text())
    else:
        r = execute_run(BacktestParams(symbols=symbols, **kw))
        path.write_text(json.dumps(r, ensure_ascii=False,
                                   separators=(",", ":")))
    return [t for t in r["trades"] if t["exit_date"] is not None]


def window(stream, lo: str, hi: str) -> list[dict]:
    return [t for t in stream if lo <= t["entry_date"] <= hi]


def run_config(a_leg, s_leg, gate: str, risk: float, init: float,
               caps) -> dict:
    w = W1
    if gate == "split":
        a = sim_weighted(a_leg, w, caps["h80"], init / 2, )
        s = sim_weighted(s_leg, w, None, init / 2)
        m = merge_curves(a, s)
        return {"final": m["final"], "curve": m["curve"]}
    cap = {"none": None, "full_v2": caps["v2"], "h80": caps["h80"]}[gate]
    merged = dedup_signals(list(a_leg) + list(s_leg))[0]
    return sim_weighted(merged, w, cap, init)


def main() -> None:
    runs = load_runs(rerun=False)
    stocks, etf_all = build_pools()
    pools = {"etf": tuple(etf_all), "stock": tuple(stocks)}

    # ---- 变体流（缓存）----
    kw_a = dict(module="A", entry_variant="early",
                exit_variant="a6_1_costbasis", fee_label="standard",
                limit_guard=True, rr_min=None)
    a_var = {
        "cm05_shrink": run_or_cache("a_main", pools["etf"],
                                    dict(kw_a, volume_filter="shrink",
                                         overrides=(("clock_mult", 0.5),))),
        "cm05_noshrink": run_or_cache("a_noshrink", pools["etf"],
                                      dict(kw_a, volume_filter="none",
                                           overrides=(("clock_mult", 0.5),))),
        "cm10_shrink": run_or_cache("a_cm10", pools["etf"],
                                    dict(kw_a, volume_filter="shrink",
                                         overrides=(("clock_mult", 1.0),))),
    }
    kw_b = dict(module="B", entry_variant="breakout",
                exit_variant="a6_1_costbasis", fee_label="standard",
                limit_guard=True, rr_min=None, volume_filter="none")
    bp_var = {
        "cb30_cl03": runs["B'"],
        "cb20_cl02": run_or_cache("bp_202", pools["stock"],
                                  dict(kw_b, overrides=(("consolidation_bars", 20),
                                                        ("cluster_threshold", 0.02)))),
        "cb40_cl04": run_or_cache("bp_404", pools["stock"],
                                  dict(kw_b, overrides=(("consolidation_bars", 40),
                                                        ("cluster_threshold", 0.04)))),
    }
    cd = [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]]

    br = load_breadth()
    b200 = {str(d.date()): float(v) for d, v in br["ma200_pct"].items()}
    caps = {"v2": cap_fn_from_map(position_cap_map(b200, TIERS_V2)),
            "h80": cap_fn_from_map(position_cap_map(b200, H80))}

    def legs(a_key, b_key):
        a = dedup_signals([{**t, "pool": "A_ETF"}
                           for t in gate_a(a_var[a_key])])[0]
        s = dedup_signals([{**t, "pool": "B_STOCK"}
                           for t in bp_var[b_key]] + cd)[0]
        return a, s

    A_DEF, B_DEF, G_DEF, R_DEF = "cm05_shrink", "cb30_cl03", "split", 0.01
    equity = 1_000_000.0
    equity_def = 1_000_000.0
    wf_curve, wf_curve_def, fold_log = [], [], []
    layer_pos = {k: [] for k in ("A", "B'", "gate", "risk")}

    for vy in VAL_YEARS:
        t_lo, t_hi = f"{vy - TRAIN_YEARS}-01-01", f"{vy - 1}-12-31"
        v_lo, v_hi = f"{vy}-01-01", f"{vy}-12-31"
        # ---- 各层贪心选档（训练窗内信号，无前视）----
        def train_final(a_key, b_key, gate, risk, lo=t_lo, hi=t_hi):
            a, s = legs(a_key, b_key)
            r = run_config(window(a, lo, hi), window(s, lo, hi),
                           gate, risk, 1_000_000, caps)
            return r["final"]

        best = train_final(A_DEF, B_DEF, G_DEF, R_DEF)
        for k in a_var:
            v = train_final(k, B_DEF, G_DEF, R_DEF)
            if v > best:
                best, a_key = v, k
        b_key = B_DEF
        for k in bp_var:
            v = train_final(a_key, k, G_DEF, R_DEF)
            if v > best:
                best, b_key = v, k
        gate = G_DEF
        for g in ("none", "full_v2", "h80", "split"):
            v = train_final(a_key, b_key, g, R_DEF)
            if v > best:
                best, gate = v, g
        risk = R_DEF
        for rr in (0.01, 0.005):
            v = train_final(a_key, b_key, gate, rr)
            if v > best:
                best, risk = v, rr
        # ---- 验证年执行 ----
        a, s = legs(a_key, b_key)
        val = run_config(window(a, v_lo, v_hi), window(s, v_lo, v_hi),
                         gate, risk, equity, caps)
        a_d, s_d = legs(A_DEF, B_DEF)
        val_def0 = equity_def
        val_def = run_config(window(a_d, v_lo, v_hi),
                             window(s_d, v_lo, v_hi),
                             G_DEF, R_DEF, equity_def, caps)
        for pt in val_def["curve"]:
            wf_curve_def.append({"date": pt["date"], "equity":
                                 round(pt["equity"] * equity_def
                                       / val_def0, 2)})
        equity_def *= (val_def["final"] / val_def0)
        fold_log.append({
            "val_year": vy, "A": a_key, "B'": b_key, "gate": gate,
            "risk": risk, "start": round(equity), "end": round(val["final"]),
            "ret": round(val["final"] / equity - 1, 4),
            "def_ret": round(val_def["final"] / equity - 1, 4)})
        for pt in val["curve"]:
            wf_curve.append(pt)
        # 层超额符号（vs 主口径固定档，同验证窗）
        for layer, sel, dflt, _kind in (("A", a_key, A_DEF, "A"),
                                       ("B'", b_key, B_DEF, "B")):
            if sel == dflt:
                layer_pos[layer].append(0.0)
                continue
            aa, ss = legs(sel if layer == "A" else a_key,
                          sel if layer == "B'" else b_key)
            alt = run_config(window(aa, v_lo, v_hi), window(ss, v_lo, v_hi),
                             gate, risk, equity, caps)
            layer_pos[layer].append(alt["final"] - val["final"])
        if gate != G_DEF:
            alt = run_config(window(a, v_lo, v_hi), window(s, v_lo, v_hi),
                             G_DEF, risk, equity, caps)
            layer_pos["gate"].append(alt["final"] - val["final"])
        else:
            layer_pos["gate"].append(0.0)
        if risk != R_DEF:
            alt = run_config(window(a, v_lo, v_hi), window(s, v_lo, v_hi),
                             gate, R_DEF, equity, caps)
            layer_pos["risk"].append(alt["final"] - val["final"])
        else:
            layer_pos["risk"].append(0.0)
        equity = val["final"]
        print(f"[折 {vy}] A={a_key} B'={b_key} gate={gate} risk={risk}"
              f" → 年收益 {fold_log[-1]['ret']:+.1%}")

    # ---- WF 曲线指标 + 生死判 ----
    eq = pd.Series({p["date"]: p["equity"] for p in wf_curve}).sort_index()
    eq.index = pd.to_datetime(eq.index)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    wf_cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    wf_dd = float((eq / eq.cummax() - 1).min())
    bench = load_pool_frames()["000300.SS"].loc["2020-01-01":]
    bh_cagr = (bench["close"].iloc[-1] / bench["close"].iloc[0]) \
        ** (1 / ((bench.index[-1] - bench.index[0]).days / 365.25)) - 1
    bh_dd = float((bench["close"] / bench["close"].cummax() - 1).min())
    eqd = pd.Series({p["date"]: p["equity"] for p in wf_curve_def}
                    ).sort_index()
    eqd.index = pd.to_datetime(eqd.index)
    yrs_d = (eqd.index[-1] - eqd.index[0]).days / 365.25
    wf_d_cagr = (eqd.iloc[-1] / eqd.iloc[0]) ** (1 / yrs_d) - 1
    wf_d_dd = float((eqd / eqd.cummax() - 1).min())
    layer_pass = {k: (sum(1 for v in vs if v > 0) / len(vs) if vs else None)
                  for k, vs in layer_pos.items()}
    verdict = {
        "JW1_adaptive": bool(wf_cagr >= 0.5 * bh_cagr
                             and wf_dd >= 0.6 * bh_dd),
        "JW1_fixed": bool(wf_d_cagr >= 0.5 * bh_cagr
                          and wf_d_dd >= 0.6 * bh_dd),
        "JW2_layers": {k: (v is not None and v >= 0.6)
                       for k, v in layer_pass.items()}}
    verdict["PASS"] = bool(verdict["JW1_fixed"])
    verdict["fixed"] = {"cagr": round(wf_d_cagr, 4),
                        "max_dd": round(wf_d_dd, 4),
                        "final": round(float(eqd.iloc[-1]))}
    out = {"date": "2026-08-27", "folds": fold_log,
           "wf_adaptive": {"cagr": round(wf_cagr, 4),
                           "max_dd": round(wf_dd, 4),
                           "final": round(float(eq.iloc[-1]))},
           "bh_000300": {"cagr": round(bh_cagr, 4),
                         "max_dd": round(bh_dd, 4)},
           "layer_positive_rate": layer_pass, "verdict": verdict}
    (RAW / "walkforward_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    eq.to_csv(RAW / "wf_equity.csv")
    eqd.to_csv(RAW / "wf_equity_fixed.csv")
    print(json.dumps({"wf_adaptive": out["wf_adaptive"],
                      "wf_fixed": verdict["fixed"],
                      "bh_000300": out["bh_000300"],
                      "verdict": verdict}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
