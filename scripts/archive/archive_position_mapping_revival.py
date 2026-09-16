#!/usr/bin/env python3
"""复活尝试归档：宽度仓位映射——连续/平滑映射 + 逐标的条件化触发（2026-09-01）。

════════════════════════════════════════════════════════════════════════
本任务为 Prompt F（全灭复活）。已判负的先例（跑前必读，本脚本不重复测）：
  1. huanjing-ARCHIVE-2026-09-01 第二节：br_half / br_quarter / combo /
     combo_trend——全部是「b50 过阈值 → 固定档位 E」的阶跃映射，3×3 邻域全测后判负。
  2. lei-ARCHIVE-2026-09-01 第二节「利率档位闸」——分位阈值→档位的阶跃映射，
     且面板哑铃为全样本分位前视假象，判负。本任务数据口径内无利率序列，
     不重测利率维度（两个复活机制假设均为宽度基，见下）。
════════════════════════════════════════════════════════════════════════

机制假设（跑前写死，报告开头必须逐一回答"这次是否真的不同"）：

  H1 连续/平滑映射：已判负机制均为阶跃函数（b50 过 0.40 一刀切到 0.5/0.25，
     宽度弱占 42/80 个月→常态半仓，年化受损）。本任务测 E = f(b50) 的连续函数
     （线性 ramp 与 sigmoid 两种形式），仓位随宽度连续变化、无档位跳变，
     假设可保留部分回撤保护同时少砍常态仓位。

  H2 逐标的条件化触发：已判负机制均为组合级整体缩仓（环境层一刀切全池）。
     本任务把判断颗粒度下沉到逐标的：仅当「市场宽度弱(b50<br_lo) 且 该标的
     自身处于 LEI 黑色(Close<EMA20 且 Close<Close_20日前)」同时成立时，
     才把该标的权重乘 scale，其余标的权重不受影响（空出的权重留现金，
     与 trend200 的 freed-weight-to-cash 处理同口径）。

判定标准（跑前固化，复用 huanjing-ARCHIVE 原公式，跑完不改）：
  主区间 2020-01-01→2026-08-18 判定；2021-01-01 起仅作敏感性，不覆盖主判定。

  改善比 r = Calmar(变体) / Calmar(等权满仓基准) - 1

  - passed（通过）  ：r > +10% 且 CAGR ≥ 基准 CAGR
  - watch（中性观察）：不满足通过、且 r > -10% 且 CAGR ≥ 基准 CAGR − 3pp
  - falsified（证伪）：r ≤ −10%，或 CAGR < 基准 CAGR − 3pp

  参数邻域稳健性（每个复活版本的主点通过后的附加检验，沿用 combo 规则的
  严格度）：主点所在 3×3 网格中，Calmar ≥ 基准 Calmar 的格子数 ≥ 6/9 才算
  邻域稳健；主点即便 r>+10% 且 CAGR 达标，若邻域 <6/9，降级为
  falsified（邻域不稳健）。网格格子不单独判通过——只服务稳健性计数，
  不得从网格里挑最优点当作发现（多重比较税）。

  诊断臂（cond_black_only：不看宽度、仅 LEI 黑色就减仓）不参与通过判定，
  只用于归因「宽度条件是否必要」；即便数字好看也不得宣称为发现。

复现对账：本脚本第一段先复算 base 与 br_half，与 huanjing 归档 JSON 逐位
  对账（容差 1e-9），不一致则中止——保证引擎/口径与已归档实验完全同源。

网格定义（跑前固化）：
  cont_lin 主点：lo=0.30, hi=lo+0.20, E_min=0.50（阶跃 0.40→0.5 的连续类比）
              网格：lo∈{0.20,0.30,0.40} × E_min∈{0.25,0.50,0.75}（宽度固定0.20）
  cont_sig 主点：mid=0.40, s=0.08, E_min=0.50
              网格：mid∈{0.30,0.40,0.50} × s∈{0.04,0.08,0.15}（E_min固定0.50）
  cond    主点：br_lo=0.40, scale=0.50（br_half 的逐标的条件化类比）
              网格：br_lo∈{0.30,0.40,0.50} × scale∈{0.25,0.50,0.75}

已知前视/局限（解读必带）：
  ① 宽度/RV 用 a_share_klines_full.parquet（当前存续股回溯，幸存者偏差）。
  ② ETF 缓存残缺个股以动态入池（上市满253日）自然处理（同 huanjing 归档④⑤）。
  ③ 样本 6.6 年单区间，2024-09 式 V 型样本只有 1 个。
  ④ E_min=1.0 或 scale=1.0 等价于基准，若网格边缘出现"接近基准"的格子，
     不构成支持证据（无操作≠有效）。

防未来函数：b50/LEI 黑色/池子均在月末 t 收盘计算，t+1 收盘执行生效；
  现金 1.5%/年；单边成本 0.1%。EMA20 用生产同款 seeded_ema（首窗口 SMA 种子，
  alpha=2/21，src/lei_signal/features/indicators.py）。

复现：PYTHONHASHSEED=0 python3 scripts/archive_position_mapping_revival.py
双跑：PYTHONHASHSEED=0/42 各跑 --dump-hash，哈希一致才入档。

数据源（与 huanjing 归档共享缓存）：/Users/yongbiaoli/.lei_signal_lab/cache/
产出：docs/experiments/raw/position-mapping-revival/*.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import archive_huanjing_cangwei as hz  # noqa: E402  引用已归档引擎，保证同口径

RAW = REPO / "docs/experiments/raw/position-mapping-revival"
END, START_MAIN, START_ALT = hz.END, hz.START_MAIN, hz.START_ALT
CRITERIA_CN = ("改善比 r=Calmar变体/Calmar基准−1；passed: r>+10% 且 CAGR≥基准；"
               "watch: −10%<r≤+10% 且 CAGR≥基准−3pp；falsified: 其余；"
               "邻域附加：主点通过后需 3×3 网格 ≥6/9 格 Calmar≥基准，否则降级证伪"
               "（原文见脚本 docstring，跑前固化）")

LIN_GRID = {"lo": (0.20, 0.30, 0.40), "emin": (0.25, 0.50, 0.75), "width": 0.20}
SIG_GRID = {"mid": (0.30, 0.40, 0.50), "s": (0.04, 0.08, 0.15), "emin": 0.50}
COND_GRID = {"br_lo": (0.30, 0.40, 0.50), "scale": (0.25, 0.50, 0.75)}
PRIMARY = {"cont_lin": (0.30, 0.50), "cont_sig": (0.40, 0.08), "cond": (0.40, 0.50)}


# ── LEI 黑色（生产 lei_color 公式的向量化重算，同 seeded EMA 口径）────────
def lei_black_frame(close: pd.Series) -> pd.Series:
    values = close.astype(float).to_numpy()
    result = np.full(len(values), np.nan)
    period, n = 20, len(values)
    if n >= period:
        result[period - 1] = values[:period].mean()
        alpha = 2.0 / (period + 1.0)
        for i in range(period, n):
            result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    ema20 = pd.Series(result, index=close.index)
    lag20 = close.shift(20)
    ready = close.notna() & ema20.notna() & lag20.notna()
    return ready & (close < ema20) & (close < lag20)


# ── 通用回测：月末 t 信号 → t+1 收盘执行（逐月权重全量重算）──────────────
def backtest(px, b50, start, weight_fn, meta_fn=None):
    p = px.loc[:END]
    W = pd.DataFrame(0.0, index=p.index, columns=p.columns)
    book = []
    mes = [d for d in hz.month_ends(p.index) if pd.Timestamp(start) <= d <= pd.Timestamp(END)]
    for i, t in enumerate(mes):
        e_idx = p.index.get_loc(t) + 1
        if e_idx >= len(p.index):
            continue
        e, nt = p.index[e_idx], (mes[i + 1] if i + 1 < len(mes) else p.index[-1])
        e_next = p.index[min(p.index.get_loc(nt) + 1, len(p.index) - 1)]
        cand = [c for c in p.columns
                if p[c].loc[:t].notna().sum() >= 253 and pd.notna(p[c].loc[t])]
        if len(cand) < 2:
            continue
        w_row, rec = weight_fn(p, t, cand, b50.asof(t))
        mask = (W.index > e) & (W.index <= e_next)
        W.loc[mask] = w_row.values
        book.append(rec | {"signal_date": str(t.date()), "exec_date": str(e.date()),
                           "n_pool": len(cand)})
    eq = hz.run_from_weights(p.loc[start:], W.loc[start:])
    return eq, book


def w_cont(form, a, b_):
    """连续映射权重：E=f(b50) 全池同乘。"""
    def fn(p, t, cand, b50_t):
        if form == "lin":
            lo, emin = a, b_
            E = emin + (1 - emin) * float(np.clip((b50_t - lo) / LIN_GRID["width"], 0.0, 1.0)) \
                if pd.notna(b50_t) else 1.0
        else:
            mid, s = a, b_
            E = 0.50 + 0.50 / (1.0 + np.exp(-(b50_t - mid) / s)) if pd.notna(b50_t) else 1.0
        w = pd.Series(0.0, index=p.columns)
        w[cand] = E / len(cand)
        return w, {"E": round(float(E), 4), "b50": round(float(b50_t), 4) if pd.notna(b50_t) else None}
    return fn


def w_cond(br_lo, scale, require_breadth=True):
    """逐标的条件化权重：宽度弱 ∧ LEI 黑色 → 该标的 ×scale，其余不受影响。"""
    def fn(p, t, cand, b50_t):
        weak = pd.notna(b50_t) and b50_t < br_lo
        fac = {}
        for c in cand:
            black = bool(BLACK[c].asof(t)) if require_breadth is False else (
                bool(BLACK[c].asof(t)) and weak)
            fac[c] = scale if black else 1.0
        w = pd.Series(0.0, index=p.columns)
        for c in cand:
            w[c] = fac[c] / len(cand)
        hit = sum(1 for c in cand if fac[c] < 1.0)
        return w, {"b50": round(float(b50_t), 4) if pd.notna(b50_t) else None,
                   "weak": bool(weak), "n_hit": hit, "frac_hit": round(hit / len(cand), 3),
                   "E_eff": round(sum(fac.values()) / len(cand), 4)}
    return fn


def yearly(eq: pd.Series) -> dict:
    y = eq.resample("YE").last().pct_change().dropna()
    y.iloc[0] = eq.resample("YE").last().dropna().iloc[0] - 1
    return {str(k.year): round(float(v) * 100, 1) for k, v in y.items()}


# ── 核心计算 ────────────────────────────────────────────────────────────
BLACK: dict[str, pd.Series] = {}


def compute_all():
    b50, rv_pct = hz.load_env()
    px = hz.load_px()
    # LEI 黑色用原始 bars（生产口径），不用合并池的 ffill 序列（假平盘会污染比较）
    for c in px.columns:
        raw_close = pd.read_parquet(hz.CACHE / f"{c}.bars.parquet")["close"].astype(float)
        BLACK[c] = lei_black_frame(raw_close)

    # 复现对账：base / br_half 必须与 huanjing 归档逐位一致，否则中止
    archived = json.loads((REPO / "docs/experiments/raw/huanjing/base.json").read_text())
    eq_base = hz.build(px, b50, rv_pct, START_MAIN, "base")[0]
    ok1 = abs(hz.metrics(eq_base)["Calmar"] - archived["metrics"]["Calmar"]) < 1e-9
    arch_br = json.loads((REPO / "docs/experiments/raw/huanjing/br_half.json").read_text())
    eq_brh = hz.build(px, b50, rv_pct, START_MAIN, "br_half")[0]
    ok2 = abs(hz.metrics(eq_brh)["Calmar"] - arch_br["metrics"]["Calmar"]) < 1e-9
    if not (ok1 and ok2):
        print("REPLICATION MISMATCH: base/br_half 与归档不一致，中止", ok1, ok2)
        sys.exit(2)

    out = {"meta": {"pool": hz.ETF_POOL, "start_main": START_MAIN, "start_alt": START_ALT,
                    "end": END, "cost": hz.COST, "rf": hz.RF_ANNUAL,
                    "primary": {k: list(v) for k, v in PRIMARY.items()},
                    "grids": {"lin": {k: list(v) if isinstance(v, tuple) else v
                                      for k, v in LIN_GRID.items()},
                              "sig": {k: list(v) if isinstance(v, tuple) else v
                                      for k, v in SIG_GRID.items()},
                              "cond": {k: list(v) for k, v in COND_GRID.items()}},
                    "replication_check": {"base_calmar_match": ok1, "br_half_calmar_match": ok2}},
           "main:base": {"metrics": hz.metrics(eq_base), "nav": [],
                         "dates": [str(d.date()) for d in eq_base.index]},
           "ref:br_half_step": {"metrics": hz.metrics(eq_brh)}}

    primaries = [("cont_lin", w_cont("lin", *PRIMARY["cont_lin"])),
                 ("cont_sig", w_cont("sig", *PRIMARY["cont_sig"])),
                 ("cond", w_cond(*PRIMARY["cond"])),
                 ("cond_black_only", w_cond(0.0, 0.50, require_breadth=False))]
    books: dict[str, list] = {}  # 逐月记录，仅供 raw 归档，不进 results_hash 载荷
    for name, fn in primaries:
        for tag, start in [("main", START_MAIN), ("alt", START_ALT)]:
            eq, book = backtest(px, b50, start, fn)
            books[f"{tag}:{name}"] = [{k: v for k, v in r.items()
                                       if k in ("signal_date", "b50", "E", "E_eff",
                                                "weak", "n_hit", "frac_hit")} for r in book]
            out[f"{tag}:{name}"] = {"metrics": hz.metrics(eq),
                                    "yearly": yearly(eq) if tag == "main" else None,
                                    "nav": [round(float(v), 8) for v in eq] if tag == "main" else [],
                                    "dates": out["main:base"]["dates"] if tag == "main" else [],
                                    "rebalance_stats": {
                                        "mean_E": round(float(np.mean([r.get("E", r.get("E_eff")) for r in book])), 4),
                                        "min_E": round(float(np.min([r.get("E", r.get("E_eff")) for r in book])), 4),
                                        "months_E_below_0.6": sum(1 for r in book if r.get("E", r.get("E_eff")) < 0.6),
                                        "months_any_hit": sum(1 for r in book if r.get("n_hit", 0) > 0),
                                        "mean_frac_hit": round(float(np.mean([r.get("frac_hit", 0.0) for r in book])), 4)},
                                    "n_rebalance": len(book)}
    for lo in LIN_GRID["lo"]:
        for emin in LIN_GRID["emin"]:
            eq, _ = backtest(px, b50, START_MAIN, w_cont("lin", lo, emin))
            out[f"grid:lin:{lo}:{emin}"] = {"metrics": hz.metrics(eq)}
    for mid in SIG_GRID["mid"]:
        for s in SIG_GRID["s"]:
            eq, _ = backtest(px, b50, START_MAIN, w_cont("sig", mid, s))
            out[f"grid:sig:{mid}:{s}"] = {"metrics": hz.metrics(eq)}
    for brl in COND_GRID["br_lo"]:
        for sc in COND_GRID["scale"]:
            eq, _ = backtest(px, b50, START_MAIN, w_cond(brl, sc))
            out[f"grid:cond:{brl}:{sc}"] = {"metrics": hz.metrics(eq)}
    return out, books


def results_hash(res: dict) -> str:
    payload = json.dumps({k: v for k, v in res.items()
                          if k.startswith(("main:", "alt:", "grid:", "ref:"))},
                         sort_keys=True).encode()
    return hashlib.md5(payload).hexdigest()


# ══════════════════════ main ══════════════════════
if __name__ == "__main__":
    res, books = compute_all()

    if "--dump-hash" in sys.argv:
        print(results_hash(res))
        sys.exit(0)

    RAW.mkdir(parents=True, exist_ok=True)
    base = res["main:base"]["metrics"]

    def verdict(m: dict) -> tuple[str, float]:
        r = m["Calmar"] / base["Calmar"] - 1
        if r > 0.10 and m["CAGR"] >= base["CAGR"]:
            return "passed", r
        if r > -0.10 and m["CAGR"] >= base["CAGR"] - 0.03:
            return "watch", r
        return "falsified", r

    verdicts, ratios, grid_ok = {}, {}, {}
    for name, cells in [("cont_lin", [(f"grid:lin:{lo}:{e}", e) for lo in LIN_GRID["lo"]
                                      for e in LIN_GRID["emin"]]),
                        ("cont_sig", [(f"grid:sig:{m_}:{s}", None) for m_ in SIG_GRID["mid"]
                                      for s in SIG_GRID["s"]]),
                        ("cond", [(f"grid:cond:{b}:{sc}", None) for b in COND_GRID["br_lo"]
                                  for sc in COND_GRID["scale"]])]:
        v, r = verdict(res[f"main:{name}"]["metrics"])
        ok = sum(1 for key, _ in cells if res[key]["metrics"]["Calmar"] >= base["Calmar"])
        grid_ok[name] = f"{ok}/9"
        if v == "passed" and ok < 6:
            verdicts[name] = "falsified（邻域不稳健）"
        else:
            verdicts[name] = v
        ratios[name] = r
    v_diag, r_diag = verdict(res["main:cond_black_only"]["metrics"])
    verdicts["cond_black_only"] = f"diagnostic（{v_diag}，不参与判定）"
    ratios["cond_black_only"] = r_diag

    hash_path = RAW / "hash.json"
    hashes = json.loads(hash_path.read_text()) if hash_path.exists() else {}
    for name in ("cont_lin", "cont_sig", "cond", "cond_black_only"):
        m = res[f"main:{name}"]["metrics"]
        rec = {"experiment": f"position-mapping-revival:{name}",
               "hypothesis_cn": {"cont_lin": "H1 连续线性ramp映射 E=f(b50) 替代阶跃档位",
                                 "cont_sig": "H1 连续sigmoid映射 E=σ((b50−mid)/s) 替代阶跃档位",
                                 "cond": "H2 逐标的条件化：宽度弱∧LEI黑色才减该标的",
                                 "cond_black_only": "诊断臂：仅LEI黑色即减仓（宽度条件消融）"}[name],
               "params": {"primary": list(PRIMARY.get(name, [])), "window": f"{START_MAIN}→{END}",
                          "cost_1side": hz.COST, "rf": hz.RF_ANNUAL},
               "criteria_cn": CRITERIA_CN,
               "verdict": verdicts[name], "calmar_ratio_vs_base": round(ratios[name], 4),
               "metrics": m, "alt_window_metrics": res[f"alt:{name}"]["metrics"],
               "yearly": res[f"main:{name}"]["yearly"],
               "monthly": books.get(f"main:{name}", []),
               "rebalance_stats": res[f"main:{name}"]["rebalance_stats"],
               "base_metrics": base,
               "dual_run_hash": hashes.get("seed0"), "dual_run_hash_42": hashes.get("seed42")}
        (RAW / f"{name}.json").write_text(json.dumps(rec, ensure_ascii=False))
    GNAME_TO_VERDICT_KEY = {"lin": "cont_lin", "sig": "cont_sig", "cond": "cond"}
    for gname, cells in [("lin", [(f"grid:lin:{lo}:{e}", f"lo={lo},E_min={e}") for lo in LIN_GRID["lo"]
                                  for e in LIN_GRID["emin"]]),
                         ("sig", [(f"grid:sig:{m_}:{s}", f"mid={m_},s={s}") for m_ in SIG_GRID["mid"]
                                  for s in SIG_GRID["s"]]),
                         ("cond", [(f"grid:cond:{b}:{sc}", f"br_lo={b},scale={sc}") for b in COND_GRID["br_lo"]
                                   for sc in COND_GRID["scale"]])]:
        rec = {"experiment": f"position-mapping-revival:{gname}-grid",
               "criteria_cn": CRITERIA_CN,
               "neighborhood_pass_count": grid_ok[GNAME_TO_VERDICT_KEY[gname]],
               "cells": {lab: res[key]["metrics"] for key, lab in cells}}
        (RAW / f"{gname}_grid.json").write_text(json.dumps(rec, ensure_ascii=False))

    print("base:", json.dumps(base, ensure_ascii=False))
    for name in ("cont_lin", "cont_sig", "cond", "cond_black_only"):
        m = res[f"main:{name}"]["metrics"]
        print(f"{name}: CAGR={m['CAGR']*100:.1f}% MaxDD={m['MaxDD']*100:.1f}% "
              f"Calmar={m['Calmar']:.2f} r={ratios[name]*100:+.0f}% "
              f"alt_CAGR={res[f'alt:{name}']['metrics']['CAGR']*100:.1f}% "
              f"verdict={verdicts[name]} grid_ok={grid_ok.get(name, '—')}")
    print("replication:", res["meta"]["replication_check"])
    print("br_half(阶跃参照) Calmar:", round(res["ref:br_half_step"]["metrics"]["Calmar"], 3))
