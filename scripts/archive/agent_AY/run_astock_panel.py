# -*- coding: utf-8 -*-
"""AY 任务：A 股个股面板 × 宽度择时四引擎——个股边界检验 + "跟随度"分层诊断。

【定位】AW 在美股个股上判"择时无优势"；本任务补 A 股个股侧（深池
~/.lei_signal_lab/backtest_pool，177 标的中筛出的个股），并把 AW 提出的边界
判据——"标的跟不跟全市场宽度走"——做成机制级检验：**按个股与沪深300 的
日收益相关（跟随度）五等分组，看择时引擎的胜率是否随跟随度单调上升**。
若单调，边界判据获得直接证据；若不单调，边界判据需要修正。

【面板（跑前写死）】
- 池：backtest_pool/*.bars.parquet，只取个股代码：60xxxx.SS、000xxx.SZ、
  002xxx.SZ、300xxx.SZ（SS 的 000/93x/88x 是指数，剔除）。
- 门槛：与全A宽度（breadth_cn_all，b200）对齐后 ≥1250 个交易日（≈5 年）。
- 宽度幸存者偏差与 SURVIVORSHIP_NOTE 同源登记（cn_all 早年按当前存续成分
  回算）；个股池本身也是当期存续名单——对"该不该买个股"零证明力，只用于
  引擎行为对比（与 AW 同一定位）。

【臂（逐字复用）】T3 冠军三档（43.33/56.67 冻结）、BIN_HYST（43.33/2）、
DCA 周定投、BH 首日全仓。费率 10bp 单边（登记：个股真实交易含印花税与点差
更高，但四臂同费率，引擎间对比方向不受影响）。T 收盘信号 T+1 开盘成交。

【跟随度分层（机制诊断，描述级）】
- beta_proxy = 个股日收益对沪深300（timing 缓存 000300）日收益的 OLS 斜率；
- R = 相关的平方不是重点，用 corr 本身：corr ≥0 为跟随，分组按 corr 五分位
  （Q1 最不跟随 → Q5 最跟随）；
- 每组报：BIN_HYST Calmar 胜 T3 的比例、BIN_HYST 终值胜 DCA 的比例、
  BH Calmar 最高的比例。预注册的机制预期：三个比例都应随分位单调上升
  （允许相邻分位扰动，Spearman 方向为正即可登记"支持"）。

【预注册三选一判定线（跑前写死；n=通过门槛的个股数）】
- (G1)「个股层面可泛化」：BIN Calmar 胜 T3 ≥55% 且 BIN 终值胜 DCA ≥55%；
- (G2)「个股层面无优势」：BH Calmar ≥ 两引擎 ≥55% 且（T3 或 BIN 任一）终值
  < DCA ≥55%；
- 其余「混合」。
- 机制线（独立于 G1/G2）：跟随度五分位 × 三胜率比例的 Spearman 秩相关
  （手写确定性实现）≥2/3 个为正 → "边界判据获支持"；≥2/3 为负 → "边界判据
  被反驳"；否则"不支持不反驳"。

【红线遵守】不产生买卖规则；不改生产代码/缓存/既有归档；产出全为新增。
双跑哈希 PYTHONHASHSEED=0/42 逐位一致。
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

from lei_signal.timing_backtest.data import load_breadth  # noqa: E402
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target  # noqa: E402
from run_robustness import cagr_maxdd, run_dca  # noqa: E402
from run_hysteresis import hysteresis_target  # noqa: E402

POOL = Path.home() / ".lei_signal_lab/backtest_pool"
TIMING = Path.home() / ".lei_signal_lab/cache/timing"
RAW_DIR = REPO / "docs/experiments/raw/agent_AY-astock-panel"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FEE = 10.0
MIN_DAYS = 1250
ENTRY = 100.0 / 3.0 * 1.3
T3_PARAMS = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)


def is_stock_code(stem: str) -> bool:
    parts = stem.split(".")
    if len(parts) < 2:
        return False
    code, mkt = parts[0], parts[1]
    if mkt == "SS" and code.startswith("60"):
        return True
    if mkt == "SZ" and (code.startswith("000") or code.startswith("002")
                        or code.startswith("300")):
        return True
    return False


def run_signal(aligned: pd.DataFrame, target, fee_bps: float) -> dict:
    res = simulate(aligned, target, fee_bps=fee_bps, min_trade=0.05)
    cagr, mdd, calmar = cagr_maxdd(res.daily["equity"])
    return {"final": float(res.daily["equity"].iloc[-1]), "cagr": cagr,
            "mdd": mdd, "calmar": calmar,
            "time_in_market": float((res.daily["weight"] > 0).mean())}


def run_bh(aligned: pd.DataFrame, fee_bps: float) -> dict:
    opens = aligned["open"].to_numpy(float)
    closes = aligned["close"].to_numpy(float)
    units = (1.0 - fee_bps * 1e-4) / opens[0]
    eq = pd.Series(units * closes, index=aligned.index)
    eq.iloc[0] = 1.0
    cagr, mdd, calmar = cagr_maxdd(eq)
    return {"final": float(eq.iloc[-1]), "cagr": cagr, "mdd": mdd,
            "calmar": calmar}


def spearman(x: list[float], y: list[float]) -> float:
    """确定性 Spearman 秩相关（小样本手写，无 scipy 依赖）。"""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main() -> None:
    breadth = load_breadth("cn_all")
    hs300 = pd.read_parquet(TIMING / "000300.parquet")["close"].dropna()
    hs300_ret = np.log(hs300).diff().dropna()

    stocks = sorted(
        p.name[: -len(".bars.parquet")]
        for p in POOL.glob("*.bars.parquet")
        if is_stock_code(p.name[: -len(".bars.parquet")])
    )
    out: dict = {"criteria_doc": __doc__,
                 "config": {"pool_n_parquet_stocks": len(stocks),
                            "min_days": MIN_DAYS, "fee": FEE},
                 "stocks": {}, "skipped": {}}
    rows = []
    for stem in stocks:
        df = pd.read_parquet(POOL / f"{stem}.bars.parquet")
        px = df[["open", "close"]].copy()
        px["high"] = df.get("high", df[["open", "close"]].max(axis=1))
        px["low"] = df.get("low", df[["open", "close"]].min(axis=1))
        px = px[~px.index.duplicated(keep="last")].sort_index()
        aligned = px.join(breadth, how="inner").sort_index()
        aligned = aligned[aligned["b200"].notna()]
        if len(aligned) < MIN_DAYS:
            out["skipped"][stem] = len(aligned)
            continue
        # 跟随度：对数日收益与沪深300 的相关（对齐交集）
        ret = np.log(aligned["close"]).diff().dropna()
        joined = pd.concat([ret.rename("s"), hs300_ret.rename("m")], axis=1,
                           join="inner").dropna()
        if len(joined) < 500:
            out["skipped"][stem] = f"corr_sample_{len(joined)}"
            continue
        corr = float(np.corrcoef(joined["s"], joined["m"])[0, 1])
        rec = {
            "start": str(aligned.index[0].date()),
            "end": str(aligned.index[-1].date()),
            "n_days": len(aligned),
            "corr_hs300": round(corr, 3),
            "T3": run_signal(aligned, ladder_target(aligned["b200"], T3_PARAMS), FEE),
            "BIN_HYST": run_signal(
                aligned, hysteresis_target(aligned["b200"], ENTRY, 2.0), FEE),
            "DCA": run_dca(aligned, FEE),
            "BH": run_bh(aligned, FEE),
        }
        out["stocks"][stem] = rec
        rows.append(stem)
        print(f"[{stem}] corr={corr:.2f} done", flush=True)

    n = len(rows)
    wins_calmar = sum(
        1 for s in rows
        if out["stocks"][s]["BIN_HYST"]["calmar"] > out["stocks"][s]["T3"]["calmar"])
    wins_final_dca = sum(
        1 for s in rows
        if out["stocks"][s]["BIN_HYST"]["final"] > out["stocks"][s]["DCA"]["final"])
    bh_top = sum(
        1 for s in rows
        if out["stocks"][s]["BH"]["calmar"] >= max(
            out["stocks"][s]["T3"]["calmar"],
            out["stocks"][s]["BIN_HYST"]["calmar"]))
    engine_lose_dca = sum(
        1 for s in rows
        if out["stocks"][s]["T3"]["final"] < out["stocks"][s]["DCA"]["final"]
        or out["stocks"][s]["BIN_HYST"]["final"] < out["stocks"][s]["DCA"]["final"])

    # ---- 跟随度五分位分层（机制诊断）----
    corrs = sorted(rows, key=lambda s: out["stocks"][s]["corr_hs300"])
    quintiles = [[] for _ in range(5)]
    for i, s in enumerate(corrs):
        quintiles[min(4, i * 5 // n)].append(s)
    strat = []
    for qi, group in enumerate(quintiles):
        g = len(group)
        strat.append({
            "quintile": qi + 1,
            "n": g,
            "corr_range": [out["stocks"][group[0]]["corr_hs300"],
                           out["stocks"][group[-1]]["corr_hs300"]],
            "bin_calmar_beats_t3": round(sum(
                1 for s in group
                if out["stocks"][s]["BIN_HYST"]["calmar"]
                > out["stocks"][s]["T3"]["calmar"]) / g, 3),
            "bin_final_beats_dca": round(sum(
                1 for s in group
                if out["stocks"][s]["BIN_HYST"]["final"]
                > out["stocks"][s]["DCA"]["final"]) / g, 3),
            "bh_calmar_top": round(sum(
                1 for s in group
                if out["stocks"][s]["BH"]["calmar"] >= max(
                    out["stocks"][s]["T3"]["calmar"],
                    out["stocks"][s]["BIN_HYST"]["calmar"])) / g, 3),
        })
    qs = list(range(1, 6))
    sp1 = spearman(qs, [x["bin_calmar_beats_t3"] for x in strat])
    sp2 = spearman(qs, [x["bin_final_beats_dca"] for x in strat])
    sp3 = spearman(qs, [1 - x["bh_calmar_top"] for x in strat])  # 引擎优势=1-BH占比
    mech_pos = sum(1 for x in (sp1, sp2, sp3) if x > 0)

    out["verdict_inputs"] = {
        "n_stocks": n, "bin_calmar_beats_t3": wins_calmar,
        "bin_final_beats_dca": wins_final_dca, "bh_calmar_top": bh_top,
        "engine_lose_dca": engine_lose_dca,
        "stratification": strat,
        "spearman": {"bin_vs_t3": round(sp1, 3), "bin_vs_dca": round(sp2, 3),
                     "engine_vs_bh": round(sp3, 3)},
    }
    if wins_calmar / n >= 0.55 and wins_final_dca / n >= 0.55:
        verdict = "个股层面可泛化（观察级）"
    elif bh_top / n >= 0.55 and engine_lose_dca / n >= 0.55:
        verdict = "个股层面无优势（观察级）"
    else:
        verdict = "混合"
    mech = ("边界判据获支持" if mech_pos >= 2 else
            "边界判据被反驳" if mech_pos <= 1 and sum(
                1 for x in (sp1, sp2, sp3) if x < 0) >= 2
            else "不支持不反驳")
    out["verdict"] = f"{verdict}；机制线：{mech}"

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "astock_panel_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"\nn={n}：BIN Calmar胜T3 {wins_calmar}/{n}（{wins_calmar/n:.0%}），"
          f"BIN终值胜DCA {wins_final_dca}/{n}（{wins_final_dca/n:.0%}），"
          f"BH Calmar最高 {bh_top}/{n}（{bh_top/n:.0%}），引擎输DCA {engine_lose_dca}/{n}")
    print("五分位分层：")
    for x in strat:
        print(f"  Q{x['quintile']} corr[{x['corr_range'][0]},{x['corr_range'][1]}] "
              f"n={x['n']}: BIN胜T3 {x['bin_calmar_beats_t3']:.0%} | "
              f"BIN胜DCA {x['bin_final_beats_dca']:.0%} | BH最高 {x['bh_calmar_top']:.0%}")
    print(f"Spearman: {out['verdict_inputs']['spearman']}")
    print(f"=== 判定：{out['verdict']} ===")
    print(f"sha256(canonical) = {h}")


if __name__ == "__main__":
    main()
