# -*- coding: utf-8 -*-
"""AU 任务（决策级）：二元+滞回(E=43.33, b=2pp) vs 现役冠军三档——正面对比。

预注册全文（跑前写死，跑完不得回头调整判定线；AJ/AP 两轮均明确"只检验不
决策"，本任务是第一次决策级对比，但结论级别登记为"系统内决策依据"——
两侧参数（43.33 档位线、带宽 2pp）都在重叠样本上选定过，这不是样本外证明）。

【实现勘误（诚实登记，AM 先例）】首跑后发现 J3 实现 `hy.mdd >= t3.mdd - 2.0`
与本 docstring "MDD ≥ T3 MDD − 2.0pp" 语义不符：cagr_maxdd 的 mdd 是小数
（-0.40 = -40%），-2.0 等于 -200pp 使 J3 恒真。修正为 -0.02（= 2pp 原意）。
修正时点：首跑出数之后、任何判定发布之前；本行即登记。

【研究问题】AJ 证明 A 股 4/4 标的"二元(43.33)赢定投、且终值 ≥ 三档"；AP 证明
加 2pp 滞回带后二元对进仓线位置的敏感度从 ~34% 压到 ~12%（8 层全收窄）、
赢定投格 23/24、代价中位 ≤10%。剩下唯一没回答的问题：**要不要把现役三档
换成二元+滞回？** 本任务正面回答。

【臂（全部逐字复用既有认证实现，禁止重写引擎）】
  - T3（现役冠军三档）：LadderParams(n_bands=3, contrarian, low_edge=30,
    high_edge=70, gamma=1.0)，b200 档位线 43.33/56.67，满/半/空三档，
    min_trade=0.05（与 AJ 三档臂逐字同参）。
  - BIN_HYST（挑战者）：AP 施密特触发器，进仓 b200<=43.3333、出仓 b200>45.3333
    （带宽 2pp，AP 唯一同时过 (D)(C)(W) 三线的档）。
  - BIN0（参照）：无滞回二元 b200<=43.3333——仅用于与 AJ 已发布数字 parity 对账。
  - DCA（基线）：AJ 逐字复用的周定投。
  - BH（对照）：首日开盘全仓持有至末（单边费一次）。
  全部 T 收盘信号 → T+1 开盘成交（引擎 simulate），费率单边 {1bp, 10bp}。

【标的】
  - 决策核心（预注册，判定只看这 8 层）：399006 创业板指、510300 沪深300ETF、
    512100 中证1000ETF、588000 科创50ETF × 2 费率（AJ/AP 同 4 标的，可比性优先）。
  - 扩展面板（仅描述，不进判定）：159915/510500/512480/512880/512010/512800/
    512660/515030/515790/515880/512400/159928/000300/SH000001/SZ399001，
    门槛 ≥1500 个对齐交易日，报告 T3 vs BIN_HYST 的 Calmar/终值胜负计数。
  - 组合层（仅描述）：核心 4 标的分账制等权（各 25% 初始资金独立运作、不再
    平衡，即已认证合体组的分账口径），报告三引擎组合 CAGR/MDD/Calmar。

【度量】每格：终值、年化、最大回撤、Calmar、在场时间、交易数、费用、换手。
核心 4 标的另出分年度收益表（fee=10bp，T3 vs BIN_HYST）。

【预注册三选一判定线（跑前写死；数值依据来自 AJ/AP 已发布数字）】
  8 层 = 4 标的 × 2 费率。以 Calmar 为主度量（用户口径"性价比"），
  终值/回撤为守门线：
  - 「换：二元+滞回更优」= 四条同时成立：
    (J1) Calmar：BIN_HYST > T3 于 ≥6/8 层；
    (J2) 终值不塌：BIN_HYST 终值 ≥ 0.95 × T3 终值 于 ≥6/8 层
        [依据：对定投优势中位 ~37%，5% 终值让渡 ≤2pp 年化量级，可接受]；
    (J3) 回撤不恶化：BIN_HYST MDD ≥ T3 MDD − 2.0pp 于 ≥6/8 层；
    (J4) 定投底线：BIN_HYST 终值 > DCA 终值 于 ≥6/8 层
        [依据：AJ b=0 已 4/4 过，AP b=2 已 23/24 格过；此线防跨样本退化]。
  - 「维持三档」= 两条同时成立：
    (K1) Calmar：T3 ≥ BIN_HYST 于 ≥5/8 层；且
    (K2) 终值：T3 > BIN_HYST 于 ≥5/8 层。
  - 其余 = 「混合/证据不足」（如 Calmar 与终值方向分裂）。
  判定输出顺序：全部数字先落盘、后打印判定。扩展面板与组合层任何数字
  不允许参与判定（写死为描述级）。

【红线遵守】不产生买卖指令；不改任何生产代码/缓存/既有归档；产出全为新增。
双跑哈希：PYTHONHASHSEED=0 / 42，sha256(canonical json) 必须逐位一致。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AJ"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AP"))

from lei_signal.timing_backtest.data import INSTRUMENTS  # noqa: E402
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target  # noqa: E402
from run_robustness import cagr_maxdd, load_aligned, run_dca  # noqa: E402  AJ 逐字复用
from run_hysteresis import hysteresis_target  # noqa: E402  AP 逐字复用

RAW_DIR = REPO / "docs/experiments/raw/agent_AU-binary-hyst-vs-t3"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CORE = ["399006", "510300", "512100", "588000"]
PANEL = [
    "159915", "510500", "512480", "512880", "512010", "512800", "512660",
    "515030", "515790", "515880", "512400", "159928", "000300", "SH000001",
    "SZ399001",
]
FEES = [1.0, 10.0]
ENTRY = 100.0 / 3.0 * 1.3          # 43.3333，AJ/AP 同值
BAND = 2.0                          # AP 唯一全过档
T3_PARAMS = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)
AJ_RAW = (
    REPO / "docs/experiments/raw/agent-AJ-binary-vs-tiered-vs-dca"
    / "binary_vs_tiered_vs_dca_results.json"
)


def run_signal(aligned: pd.DataFrame, target: pd.Series, fee_bps: float) -> dict:
    res = simulate(aligned, target, fee_bps=fee_bps, min_trade=0.05)
    cagr, mdd, calmar = cagr_maxdd(res.daily["equity"])
    return {
        "final": float(res.daily["equity"].iloc[-1]),
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "n_trades": len(res.trades),
        "time_in_market": float((res.daily["weight"] > 0).mean()),
        "fees": float(sum(t["fee"] for t in res.trades)),
    }


def run_bh(aligned: pd.DataFrame, fee_bps: float) -> dict:
    """首日开盘全仓持有至末（单边费一次）。"""
    opens = aligned["open"].to_numpy(float)
    closes = aligned["close"].to_numpy(float)
    units = (1.0 - fee_bps * 1e-4) / opens[0]
    eq = pd.Series(units * closes, index=aligned.index)
    eq.iloc[0] = 1.0
    cagr, mdd, calmar = cagr_maxdd(eq)
    return {"final": float(eq.iloc[-1]), "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "n_trades": 1, "time_in_market": 1.0,
            "fees": fee_bps * 1e-4}


def yearly_returns(daily_eq: pd.Series) -> dict[str, float]:
    """分年度收益（首年相对 1.0）。"""
    out: dict[str, float] = {}
    prev = 1.0
    for year, grp in daily_eq.groupby(daily_eq.index.year):
        last = float(grp.iloc[-1])
        out[str(year)] = round((last / prev - 1.0) * 100, 2)
        prev = last
    return out


def run_symbol(sym: str, *, is_core: bool) -> dict:
    aligned = load_aligned(sym)
    rec: dict = {
        "name": INSTRUMENTS[sym].name,
        "start": str(aligned.index[0].date()),
        "end": str(aligned.index[-1].date()),
        "n_days": len(aligned),
        "arms": {},
    }
    for fee in FEES:
        f = int(fee)
        tgt_t3 = ladder_target(aligned["b200"], T3_PARAMS)
        tgt_hyst = hysteresis_target(aligned["b200"], ENTRY, BAND)
        tgt_bin0 = hysteresis_target(aligned["b200"], ENTRY, 0.0)
        rec["arms"][f"T3_fee{f}"] = run_signal(aligned, tgt_t3, fee)
        rec["arms"][f"BIN_HYST_fee{f}"] = run_signal(aligned, tgt_hyst, fee)
        rec["arms"][f"BIN0_fee{f}"] = run_signal(aligned, tgt_bin0, fee)
        rec["arms"][f"DCA_fee{f}"] = run_dca(aligned, fee)
        rec["arms"][f"BH_fee{f}"] = run_bh(aligned, fee)
    if is_core:
        # 分年度（fee=10bp，判定不看、报告用）
        res_t3 = simulate(aligned, ladder_target(aligned["b200"], T3_PARAMS),
                          fee_bps=10.0, min_trade=0.05)
        res_hy = simulate(aligned, hysteresis_target(aligned["b200"], ENTRY, BAND),
                          fee_bps=10.0, min_trade=0.05)
        rec["yearly_fee10"] = {
            "T3": yearly_returns(res_t3.daily["equity"]),
            "BIN_HYST": yearly_returns(res_hy.daily["equity"]),
        }
    return rec


def portfolio_layer(core_results: dict) -> dict:
    """分账制等权组合：4 腿各自引擎曲线等权平均（描述级）。"""
    out = {}
    for arm in ("T3", "BIN_HYST", "BIN0"):
        curves = []
        for sym in CORE:
            aligned = load_aligned(sym)
            if arm == "T3":
                tgt = ladder_target(aligned["b200"], T3_PARAMS)
            elif arm == "BIN_HYST":
                tgt = hysteresis_target(aligned["b200"], ENTRY, BAND)
            else:
                tgt = hysteresis_target(aligned["b200"], ENTRY, 0.0)
            res = simulate(aligned, tgt, fee_bps=10.0, min_trade=0.05)
            curves.append(res.daily["equity"].rename(sym))
        df = pd.concat(curves, axis=1).ffill().fillna(1.0)
        port = df.mean(axis=1)
        cagr, mdd, calmar = cagr_maxdd(port)
        out[arm] = {
            "final": float(port.iloc[-1]), "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "window": [str(port.index[0].date()),
                                         str(port.index[-1].date())],
        }
    return out


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "core": {}, "panel": {},
                 "config": {"core": CORE, "panel": PANEL, "fees": FEES,
                            "entry": ENTRY, "band": BAND}}

    # ---- 核心 4 标的 ----
    for sym in CORE:
        out["core"][sym] = run_symbol(sym, is_core=True)
        print(f"[core {sym}] done", flush=True)

    # ---- parity：BIN0 与 AJ 已发布二元数字逐格对账 ----
    aj = json.loads(AJ_RAW.read_text())
    parity = []
    for sym in CORE:
        for fee in FEES:
            f = int(fee)
            mine = out["core"][sym]["arms"][f"BIN0_fee{f}"]["final"]
            theirs = aj["symbols"][sym]["cells"][f"bin_base_fee{f}"]["final"]
            parity.append({"sym": sym, "fee": f, "mine": mine,
                           "aj": theirs, "absdiff": abs(mine - theirs)})
    out["parity_vs_AJ"] = {"n_cells": len(parity),
                           "max_absdiff": max(p["absdiff"] for p in parity)}

    # ---- 扩展面板（描述级） ----
    for sym in PANEL:
        try:
            aligned_probe = load_aligned(sym)
            if len(aligned_probe) < 1500:
                out["panel"][sym] = {"skipped": "insufficient_history",
                                     "n_days": len(aligned_probe)}
                continue
            out["panel"][sym] = run_symbol(sym, is_core=False)
            print(f"[panel {sym}] done", flush=True)
        except Exception as e:  # noqa: BLE001 - 面板标的数据缺失不致命
            out["panel"][sym] = {"skipped": f"error: {e}"}
            print(f"[panel {sym}] SKIP: {e}", flush=True)

    # ---- 组合层（描述级） ----
    out["portfolio_fee10"] = portfolio_layer(out["core"])

    # ---- 判定（最后算，禁止先看再定） ----
    layers = []
    for sym in CORE:
        for fee in FEES:
            f = int(fee)
            t3 = out["core"][sym]["arms"][f"T3_fee{f}"]
            hy = out["core"][sym]["arms"][f"BIN_HYST_fee{f}"]
            dc = out["core"][sym]["arms"][f"DCA_fee{f}"]
            layers.append({
                "sym": sym, "fee": f,
                "calmar_win_hyst": hy["calmar"] > t3["calmar"],
                "final_ok_095": hy["final"] >= 0.95 * t3["final"],
                "mdd_ok_2pp": hy["mdd"] >= t3["mdd"] - 0.02,  # mdd 为小数，2pp=0.02
                "dca_win": hy["final"] > dc["final"],
            })
    n = len(layers)
    c1 = sum(l["calmar_win_hyst"] for l in layers)
    c2 = sum(l["final_ok_095"] for l in layers)
    c3 = sum(l["mdd_ok_2pp"] for l in layers)
    c4 = sum(l["dca_win"] for l in layers)
    k1 = sum(not l["calmar_win_hyst"] for l in layers)
    k2 = sum(t3_beats := (not l["final_ok_095"]) for l in layers)
    out["verdict_inputs"] = {
        "n_layers": n, "J1_calmar_hyst_wins": c1, "J2_final_ge_095x": c2,
        "J3_mdd_not_worse_2pp": c3, "J4_beats_dca": c4,
        "K1_calmar_t3_wins": k1, "K2_final_t3_wins_strict": k2,
        "layers": layers,
    }
    if c1 >= 6 and c2 >= 6 and c3 >= 6 and c4 >= 6:
        verdict = "换：二元+滞回更优"
    elif k1 >= 5 and k2 >= 5:
        verdict = "维持三档"
    else:
        verdict = "混合/证据不足"
    out["verdict"] = verdict

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "binary_hyst_vs_t3_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"\n=== 判定：{verdict} ===")
    print(f"J1 Calmar:{c1}/8  J2 终值≥0.95x:{c2}/8  "
          f"J3 回撤不恶化:{c3}/8  J4 赢定投:{c4}/8")
    print(f"K1 T3 Calmar胜:{k1}/8  K2 T3 终值胜:{k2}/8")
    print(f"sha256(canonical) = {h}")


if __name__ == "__main__":
    main()
