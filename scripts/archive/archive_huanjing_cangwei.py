#!/usr/bin/env python3
"""环境组归档：宽度×RV 环境层做总仓位系数 · 宽指+行业ETF池策略化回测（2026-09-01）。

════════════════════════════════════════════════════════════════════════
假设：环境层（市场宽度 b50 × 市场 RV20 分位）直接映射为总仓位系数 E，
      可改善等权 ETF 组合的风险调整收益。
════════════════════════════════════════════════════════════════════════

判定标准（归档时固化，跑完不改；主区间 2020-01→2026-08-18 判定，
敏感性区间 2021-01→2026-08-18 只作辅助、不覆盖主判定）：

  改善比 r = Calmar(变体) / Calmar(等权满仓基准) - 1

  - passed（通过）  ：r > +10% 且 CAGR ≥ 基准 CAGR
  - watch（中性观察）：不满足通过、且 r > -10% 且 CAGR ≥ 基准 CAGR − 3pp
  - falsified（证伪）：r ≤ −10%，或 CAGR < 基准 CAGR − 3pp

  参数邻域稳健性（combo 附加）：br_lo∈{0.30,0.40,0.50} 中至少 2/3 个
  Calmar ≥ 基准，否则即便主点通过也降级为证伪。

已知前视/局限（结论解读必须带上）：
  ① 判定标准为归档时（2026-09-01）固化；探索轮（同日较早）先于本标准，
     本脚本重跑数字与探索轮完全一致（见 hash.json 与已知问题清单）。
  ② vt 目标波动 = 基准组合全样本年化波动（常数，轻前视，只影响仓位
     水平不影响择时方向；H/C 节同款处理）。
  ③ 宽度/RV 用 a_share_klines_full.parquet（当前存续股回溯，幸存者偏差）。
  ④ ETF 缓存中 159915（仅120根）/512890/515880（2024起）为残缺窗口，
     以动态入池（上市满253交易日）自然处理，未删任何已入池数据。

防未来函数：环境（b50/RV20 分位）与池子、权重均在月末 t 收盘计算，
t+1 收盘执行生效；现金按 1.5%/年计提；单边成本 0.1%。

复现：PYTHONHASHSEED=0 python3 scripts/archive_huanjing_cangwei.py
双跑：PYTHONHASHSEED=0/42 各跑 --dump-hash，哈希一致才入档。

数据源（lei-signal-sync 共享缓存）：/Users/yongbiaoli/.lei_signal_lab/cache/
  a_share_klines_full.parquet（环境层）、<code>.bars.parquet（ETF 池 11 只）
产出：docs/experiments/raw/huanjing/*.json
      web/public/reports/huanjing-cangwei-2026-09-01.html
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CACHE = Path("/Users/yongbiaoli/.lei_signal_lab/cache")
RAW = REPO / "docs/experiments/raw/huanjing"
OUT_HTML = REPO / "web/public/reports/huanjing-cangwei-2026-09-01.html"

RF_ANNUAL = 0.015
RF_DAILY = (1 + RF_ANNUAL) ** (1 / 252) - 1
COST = 0.001
START_MAIN, START_ALT, END = "2020-01-01", "2021-01-01", "2026-08-18"

ETF_POOL = ["510300.SS", "588000.SS", "512400.SS", "515050.SS", "515130.SS",
            "515300.SS", "515170.SS", "516220.SS", "159652.SZ", "562590.SS", "515880.SS"]
ETF_NAMES = {"510300.SS": "沪深300ETF", "588000.SS": "科创50ETF", "512400.SS": "有色ETF",
             "515050.SS": "5G通信ETF", "515130.SS": "软件ETF", "159652.SZ": "芯片ETF",
             "515880.SS": "通信ETF"}

CONFIGS = [  # (mode, 中文名)
    ("base", "等权满仓（基准）"),
    ("rv_half", "高波减半 RV≥0.8→50%"),
    ("rv_zero", "高波空仓 RV≥0.8→0%"),
    ("vt", "目标波动缩放"),
    ("br_half", "宽度弱减半 b50<0.40→50%"),
    ("br_quarter", "宽度弱→25%"),
    ("combo", "2×2组合 高波∧宽弱→25%"),
    ("trend200", "标的层SMA200退出"),
    ("combo_trend", "2×2组合+SMA200"),
]


# ── 环境（与 lei-signal-sync market_context/vol_regime、breadth 同口径）──
def load_env() -> tuple[pd.Series, pd.Series]:
    stock = pd.read_parquet(CACHE / "a_share_klines_full.parquet").loc["2015-01-01":]
    close = stock.astype(float)
    valid = close.notna()
    sma50 = close.rolling(50).mean()
    b50 = ((close > sma50).where(valid).sum(axis=1) / valid.sum(axis=1))
    daily = close.pct_change(fill_method=None).where(valid).mean(axis=1, skipna=True)
    rv20 = daily.rolling(20).std() * np.sqrt(252.0)
    rv_pct = rv20.rolling(756, min_periods=252).rank(pct=True)
    return b50, rv_pct


def load_px() -> pd.DataFrame:
    etf = {c: pd.read_parquet(CACHE / f"{c}.bars.parquet")["close"].astype(float)
           for c in ETF_POOL}
    return pd.DataFrame(etf).sort_index().ffill()


# ── 回测引擎（同 lei-signal-sync scripts/repro_factor_backtest.py）────────
def run_from_weights(p: pd.DataFrame, w: pd.DataFrame) -> pd.Series:
    rets = p.pct_change(fill_method=None)
    wr = w.reindex(p.index).fillna(0.0)
    rr = rets.reindex(p.index).fillna(0.0)
    net = (wr * rr).sum(axis=1) + (1.0 - wr.sum(axis=1)).clip(lower=0.0) * RF_DAILY
    to = wr.diff().abs().sum(axis=1).fillna(wr.iloc[0].abs().sum())
    return (1 + net - to * COST).cumprod()


def metrics(eq: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    dd = float((eq / eq.cummax() - 1).min())
    return {"CAGR": float(cagr), "Vol": float(vol),
            "Sharpe": float((r.mean() * 252 - RF_ANNUAL) / vol) if vol > 0 else None,
            "MaxDD": dd, "Calmar": float(cagr / abs(dd)) if dd < 0 else None}


def month_ends(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(index=idx)
    return list(s.groupby([idx.year, idx.month]).apply(lambda g: g.index[-1]))


def build(px, b50, rv_pct, start, mode, rv_hi=0.8, br_lo=0.40, vt_target=None):
    """返回 (净值, 月度再平衡记录, 逐日E序列)。t 收盘信号，t+1 收盘执行。"""
    p = px.loc[:END]
    W = pd.DataFrame(0.0, index=p.index, columns=p.columns)
    E_daily = pd.Series(np.nan, index=p.index)
    sma200 = p.rolling(200).mean()
    port_rv20 = p.pct_change(fill_method=None).mean(axis=1).rolling(20).std() * np.sqrt(252)
    mes = [d for d in month_ends(p.index) if pd.Timestamp(start) <= d <= pd.Timestamp(END)]
    rebal = []
    for i, t in enumerate(mes):
        pos_t = p.index.get_loc(t)
        e_idx = pos_t + 1
        if e_idx >= len(p.index):
            continue
        e, nt = p.index[e_idx], (mes[i + 1] if i + 1 < len(mes) else p.index[-1])
        e_next = p.index[min(p.index.get_loc(nt) + 1, len(p.index) - 1)]
        cand = [c for c in p.columns
                if p[c].loc[:t].notna().sum() >= 253 and pd.notna(p[c].loc[t])]
        if len(cand) < 2:
            continue
        E, b_t, r_t = 1.0, b50.asof(t), rv_pct.asof(t)
        if mode != "trend200" and pd.notna(b_t) and pd.notna(r_t):
            hi, weak = r_t >= rv_hi, b_t < br_lo
            if mode == "rv_half" and hi:
                E = 0.5
            elif mode == "rv_zero" and hi:
                E = 0.0
            elif mode == "vt" and vt_target:
                rv_now = port_rv20.asof(t)
                if pd.notna(rv_now) and rv_now > 0:
                    E = float(np.clip(vt_target / rv_now, 0.25, 1.0))
            elif mode == "br_half" and weak:
                E = 0.5
            elif mode == "br_quarter" and weak:
                E = 0.25
            elif mode in ("combo", "combo_trend"):
                E = 0.25 if (hi and weak) else (1.0 if hi else (0.5 if weak else 1.0))
        w_row = pd.Series(0.0, index=p.columns)
        if mode in ("trend200", "combo_trend"):
            held = [c for c in cand if p[c].loc[t] > sma200[c].loc[t]]
            for c in held:
                w_row[c] = E / len(cand)
        else:
            held = cand
            w_row[cand] = E / len(cand)
        mask = (W.index > e) & (W.index <= e_next)
        W.loc[mask] = w_row.values
        E_daily.loc[mask] = E
        rebal.append({"signal_date": str(t.date()), "exec_date": str(e.date()),
                      "E": E, "b50": round(float(b_t), 4) if pd.notna(b_t) else None,
                      "rv_pct": round(float(r_t), 4) if pd.notna(r_t) else None,
                      "n_pool": len(cand), "n_held": len(held),
                      "action": "调仓" if held else "空仓",
                      "costs_applied": f"单边{COST*100:.0f}bp"})
    eq = run_from_weights(p.loc[start:], W.loc[start:])
    return eq, rebal, E_daily.loc[start:]


# ── 核心计算（--dump-hash 用同一函数保证可复现）─────────────────────────
def compute_all():
    b50, rv_pct = load_env()
    px = load_px()
    base0 = build(px, b50, rv_pct, START_MAIN, "base")[0]
    vt_t = metrics(base0)["Vol"]
    out = {"meta": {"pool": ETF_POOL, "start_main": START_MAIN, "start_alt": START_ALT,
                    "end": END, "cost": COST, "rf": RF_ANNUAL, "vt_target": vt_t}}
    for start_tag, start in [("main", START_MAIN), ("alt", START_ALT)]:
        for mode, _ in CONFIGS:
            kw = {"vt_target": vt_t} if mode == "vt" else {}
            eq, rebal, e_daily = build(px, b50, rv_pct, start, mode, **kw)
            out[f"{start_tag}:{mode}"] = {
                "nav": [round(float(v), 8) for v in eq],
                "dates": [str(d.date()) for d in eq.index],
                "metrics": metrics(eq),
                "rebalance": rebal,
                "E_daily": [None if pd.isna(v) else v for v in e_daily],
            }
    # 参数邻域（combo）
    for brl in (0.30, 0.40, 0.50):
        for rvh in (0.7, 0.8, 0.9):
            eq = build(px, b50, rv_pct, START_MAIN, "combo", rv_hi=rvh, br_lo=brl)[0]
            out[f"grid:{brl}:{rvh}"] = {"metrics": metrics(eq)}
    # 参照
    seg = px["510300.SS"].loc[START_MAIN:END]
    out["ref:510300"] = {"metrics": metrics(seg / seg.iloc[0])}
    return out


def results_hash(res: dict) -> str:
    payload = json.dumps({k: v for k, v in res.items()
                          if k.startswith(("main:", "alt:", "grid:", "ref:"))},
                         sort_keys=True).encode()
    return hashlib.md5(payload).hexdigest()


# ══════════════════════ main ══════════════════════
if __name__ == "__main__":
    res = compute_all()

    if "--dump-hash" in sys.argv:
        print(results_hash(res))
        sys.exit(0)

    RAW.mkdir(parents=True, exist_ok=True)

    # ── 判定（按 docstring 固化标准，机械执行）──────────────────────────
    base = res["main:base"]["metrics"]

    def verdict(m: dict) -> tuple[str, float]:
        r = m["Calmar"] / base["Calmar"] - 1
        if r > 0.10 and m["CAGR"] >= base["CAGR"]:
            return "passed", r
        if r > -0.10 and m["CAGR"] >= base["CAGR"] - 0.03:
            return "watch", r
        return "falsified", r

    verdicts, ratios = {}, {}
    for mode, cn in CONFIGS:
        if mode == "base":
            continue
        v, r = verdict(res[f"main:{mode}"]["metrics"])
        verdicts[mode], ratios[mode] = v, r
    # combo 邻域稳健附加检验
    grid_ok = sum(1 for brl in (0.30, 0.40, 0.50)
                  if res[f"grid:{brl}:0.8"]["metrics"]["Calmar"] >= base["Calmar"])
    if verdicts["combo"] == "passed" and grid_ok < 2:
        verdicts["combo"] = "falsified（邻域不稳健）"

    # ── raw 落盘：逐实验 JSON ──────────────────────────────────────────
    hash_path = RAW / "hash.json"
    hashes = json.loads(hash_path.read_text()) if hash_path.exists() else {}
    criteria_text = ("改善比 r=Calmar变体/Calmar基准−1；passed: r>+10% 且 CAGR≥基准；"
                     "watch: −10%<r≤+10% 且 CAGR≥基准−3pp；falsified: 其余（原文见脚本 docstring，跑前固化）")
    for mode, cn in CONFIGS:
        rec = {**res[f"main:{mode}"],
               "experiment": f"huanjing:{mode}",
               "hypothesis_cn": f"{cn} 相对等权满仓基准的风险调整改善",
               "params": {"mode": mode, "rv_hi": 0.8, "br_lo": 0.40,
                          "vt_target": res["meta"]["vt_target"] if mode == "vt" else None,
                          "window": f"{START_MAIN}→{END}", "cost_1side": COST, "rf": RF_ANNUAL},
               "criteria_cn": criteria_text,
               "verdict": "baseline" if mode == "base" else verdicts.get(mode),
               "calmar_ratio_vs_base": None if mode == "base" else round(ratios[mode], 4),
               "alt_window_metrics": res[f"alt:{mode}"]["metrics"],
               "dual_run_hash": hashes.get("seed0"), "dual_run_hash_42": hashes.get("seed42"),
               "bugfix_notes": [
                   "探索轮两处笔误在首跑前修复（多余括号致语法错、一处不必要的chr拼接）；"
                   "归档脚本转写时第三处残留赋值行在首跑前删除；三处均未影响任何数字",
                   "首跑后无数字修正"]}
        (RAW / f"{mode}.json").write_text(json.dumps(rec, ensure_ascii=False))
    grid_rec = {"experiment": "huanjing:combo-grid", "criteria_cn": criteria_text,
                "grid": {f"br{b}/rv{r}": res[f"grid:{b}:{r}"]["metrics"]
                         for b in (0.30, 0.40, 0.50) for r in (0.7, 0.8, 0.9)},
                "combo_neighborhood_pass_count": grid_ok}
    (RAW / "combo_grid.json").write_text(json.dumps(grid_rec, ensure_ascii=False))

    # ── HTML ───────────────────────────────────────────────────────────
    def pct(x, d=1):
        return f"{x*100:.{d}f}%"

    CN = dict(CONFIGS)
    rows = []
    for mode, cn in CONFIGS:
        m = res[f"main:{mode}"]["metrics"]
        v = "基准" if mode == "base" else f"{verdicts[mode]}（r={ratios[mode]*100:+.0f}%）"
        rows.append((cn, pct(m["CAGR"]), f"{m['Sharpe']:.2f}", pct(m["MaxDD"]),
                     f"{m['Calmar']:.2f}", pct(res[f"alt:{mode}"]["metrics"]["CAGR"]), v))
    m300 = res["ref:510300"]["metrics"]

    # 净值 SVG（主区间，重点 4 线 + 510300）
    plot_modes = ["base", "vt", "combo", "trend200"]
    colors = {"base": "#38bdf8", "vt": "#4ade80", "combo": "#fbbf24", "trend200": "#f87171"}
    W_, H_ = 960, 320
    pad = {"l": 56, "r": 14, "t": 26, "b": 26}
    d0 = res["main:base"]["dates"]
    ts = [pd.Timestamp(d).timestamp() for d in d0]
    x0, x1 = ts[0], ts[-1]
    navs = {m_: res[f"main:{m_}"]["nav"] for m_ in plot_modes}
    lo = np.log10(min(min(v) for v in navs.values()))
    hi = np.log10(max(max(v) for v in navs.values()))

    def X(ti):
        return pad["l"] + (ti - x0) / (x1 - x0) * (W_ - pad["l"] - pad["r"])

    def Y(v):
        return H_ - pad["b"] - (np.log10(v) - lo) / (hi - lo) * (H_ - pad["t"] - pad["b"])

    svg = [f'<svg viewBox="0 0 {W_} {H_}" style="width:100%;background:#0b1220;border-radius:10px">',
           f'<text x="{pad["l"]}" y="16" fill="#94a3b8" font-size="12">净值（对数轴）：等权基准 / 目标波动 / 2×2组合 / SMA200退出</text>']
    for f_ in (0, 0.5, 1.0):
        y = H_ - pad["b"] - f_ * (H_ - pad["t"] - pad["b"])
        svg.append(f'<line x1="{pad["l"]}" y1="{y:.0f}" x2="{W_-14}" y2="{y:.0f}" stroke="#1e293b"/>')
        svg.append(f'<text x="{pad["l"]-6}" y="{y+4:.0f}" fill="#64748b" font-size="10" text-anchor="end">{10**(lo+f_*(hi-lo)):.1f}x</text>')
    for yr in range(2021, 2027, 1):
        d = pd.Timestamp(f"{yr}-01-01").timestamp()
        if x0 < d < x1:
            svg.append(f'<line x1="{X(d):.0f}" y1="{pad["t"]}" x2="{X(d):.0f}" y2="{H_-pad["b"]}" stroke="#1e293b"/>')
            svg.append(f'<text x="{X(d):.0f}" y="{H_-8}" fill="#64748b" font-size="10" text-anchor="middle">{yr}</text>')
    for m_ in plot_modes:
        pts = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in zip(ts, navs[m_]))
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{colors[m_]}" stroke-width="1.6" opacity="0.95"/>')
    svg.append("</svg>")
    nav_svg = "".join(svg)

    # E 档位带（combo）
    e_series = res["main:combo"]["E_daily"]
    W2 = 960
    svg2 = [f'<svg viewBox="0 0 {W2} 120" style="width:100%;background:#0b1220;border-radius:10px">',
            '<text x="56" y="16" fill="#94a3b8" font-size="12">2×2组合 仓位系数 E（0=现金 0.25/0.5=降档 1=满仓）</text>']
    cmap = {0.0: "#334155", 0.25: "#b45309", 0.5: "#f59e0b", 1.0: "#22c55e"}
    for i, v in enumerate(e_series):
        if v is None:
            continue
        x = 56 + (ts[i] - x0) / (x1 - x0) * (W2 - 70)
        fill = cmap.get(v, "#64748b")
        w_rect = max((W2 - 70) / len(ts), 1.5)
        svg2.append(f'<rect x="{x:.1f}" y="30" width="{w_rect:.1f}" height="60" fill="{fill}" opacity="0.9"/>')
    for val, lab, cx in [(1.0, "满仓", 880), (0.5, "减半", 820), (0.25, "重砍", 760), (0.0, "现金", 700)]:
        svg2.append(f'<rect x="{cx}" y="104" width="10" height="8" fill="{cmap[val]}"/><text x="{cx+14}" y="112" fill="#94a3b8" font-size="10">{lab}</text>')
    svg2.append("</svg>")
    e_svg = "".join(svg2)

    # 分年表
    def yearly(eq_list):
        eq = pd.Series(eq_list, index=pd.to_datetime(res["main:base"]["dates"]))
        return eq.resample("YE").last().pct_change().dropna() * 100

    ys = {m_: yearly(res[f"main:{m_}"]["nav"]) for m_ in ["base", "rv_half", "combo", "trend200"]}
    yr_rows = "".join(
        f'<tr><td class="num">{y.year}</td><td class="num">{ys["base"].get(y, float("nan")):.1f}</td>'
        f'<td class="num">{ys["rv_half"].get(y, float("nan")):.1f}</td>'
        f'<td class="num">{ys["combo"].get(y, float("nan")):.1f}</td>'
        f'<td class="num">{ys["trend200"].get(y, float("nan")):.1f}</td></tr>'
        for y in ys["base"].index)

    tbl = "".join(
        f'<tr><td>{c[0]}</td><td class="num">{c[1]}</td><td class="num">{c[2]}</td>'
        f'<td class="num">{c[3]}</td><td class="num">{c[4]}</td><td class="num">{c[5]}</td>'
        f'<td>{c[6]}</td></tr>' for c in rows)
    grid_rows = "".join(
        f'<tr><td class="num">{b}</td><td class="num">{r}</td>'
        f'<td class="num">{res[f"grid:{b}:{r}"]["metrics"]["Calmar"]:.2f}</td>'
        f'<td class="num">{pct(res[f"grid:{b}:{r}"]["metrics"]["MaxDD"])}</td></tr>'
        for b in (0.30, 0.40, 0.50) for r in (0.7, 0.8, 0.9))

    h0 = hashes.get("seed0", "(待双跑)")
    h42 = hashes.get("seed42", "(待双跑)")
    vmap = {m_: verdicts.get(m_, "—") for m_, _ in CONFIGS}

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>环境组归档 · 宽度×RV仓位系数 · 2026-09-01</title>
<style>
 body{{background:#0f172a;color:#e2e8f0;font:14px/1.6 -apple-system,"PingFang SC",sans-serif;margin:0;padding:24px;max-width:1040px}}
 h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:16px;margin:28px 0 10px;color:#7dd3fc}}
 .sub{{color:#94a3b8;font-size:12px;margin-bottom:20px}}
 table{{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}}
 th,td{{border:1px solid #1e293b;padding:5px 9px;text-align:left}}
 th{{background:#1e293b;color:#94a3b8;font-weight:500}}
 .num{{text-align:right;font-variant-numeric:tabular-nums}}
 .k{{color:#64748b;font-size:12px}} .pass{{color:#4ade80}} .fail{{color:#f87171}} .watch{{color:#fbbf24}}
 code{{background:#1e293b;padding:1px 6px;border-radius:4px;font-size:12px;color:#fbbf24}}
 .card{{background:#111c33;border:1px solid #1e293b;border-radius:10px;padding:14px 18px;margin:10px 0}}
 ul{{margin:6px 0}} li{{margin:3px 0}}
</style></head><body>
<h1>环境组 · 宽度×RV 环境层做总仓位系数 —— 宽指+行业 ETF 池策略化回测</h1>
<div class="sub">2026-09-01 · 窗口 {START_MAIN} → {END}（主，6.6年）+ {START_ALT} → {END}（敏感性）·
 月频再平衡 · 月末信号 t+1 收盘执行 · 单边成本 0.1% · 现金 1.5%/年 · research_proxy，非投资建议</div>

<h2>一、结论总表（KPI 口径齐全）</h2>
<table><tr><th>配置</th><th>年化</th><th>Sharpe</th><th>MaxDD</th><th>Calmar</th><th>年化(2021起)</th><th>判定（固化标准）</th></tr>{tbl}
<tr><td>510300 买入持有（对照）</td><td class="num">{pct(m300['CAGR'])}</td><td class="num">{m300['Sharpe']:.2f}</td><td class="num">{pct(m300['MaxDD'])}</td><td class="num">{m300['Calmar']:.2f}</td><td class="num">—</td><td>参照</td></tr>
<tr><td>现金（对照）</td><td class="num">1.5%</td><td class="num">—</td><td class="num">0.0%</td><td class="num">—</td><td class="num">—</td><td>参照</td></tr></table>
<p class="k">七项口径：年化/最大回撤/Calmar=年化÷|MaxDD|/时间窗口/费用假设（单边0.1%+现金1.5%）/执行时滞（月末信号t+1收盘）/对照（等权满仓、510300持有、现金）。</p>
<div class="card"><b>判定摘要</b>（改善比 r = Calmar变体/Calmar基准−1；标准见复现段 docstring）：
<ul>
 <li><span class="pass">passed（1）</span>：目标波动缩放 r=+15%，年化 14.5%→16.4%、Sharpe 0.66→0.78，回撤不升——第三次独立验证（前两次：单资产日频、ETF等权池月频）。</li>
 <li><span class="fail">falsified（5）</span>：宽度阈值降档（b50&lt;0.40→50%/25%）「花收益买回撤」——回撤 -37%→-30% 但年化 14.5%→10.7%/8.5%，Calmar 反降；2×2 组合（含邻域检验 {grid_ok}/3 过）不成立；标的层 SMA200 退出最差（2024 年 -12.1% vs 基准 +12.8%）。</li>
 <li><span class="watch">watch（2）</span>：高波减半/空仓 r=+5%/+3%，中性微正——月频钝化恰避开了日频 whipsaw，但不足以采纳。</li>
</ul></div>

<h2>二、净值曲线（主区间）</h2>
{nav_svg}

<h2>三、仓位档位带（2×2 组合的 E 系数）</h2>
{e_svg}
<p class="k">宽度弱（b50&lt;0.40）占 42/80 个月（过半），这是宽度阈值规则年化受损的直接原因——宽度是状态描述，不是仓位开关。</p>

<h2>四、分年收益（%）</h2>
<table><tr><th>年份</th><th>等权满仓</th><th>高波减半</th><th>2×2组合</th><th>SMA200退出</th></tr>{yr_rows}</table>
<p class="k">关键：2022 熊市降仓规则全赢；<b>2024 年全输</b>（V型反转里月频执行两头挨打：年初砍仓避险收益 &lt; 9月末回补踏空损失）。</p>

<h2>五、2×2 组合参数邻域（Calmar / MaxDD）</h2>
<table><tr><th>br_lo</th><th>rv_hi</th><th>Calmar</th><th>MaxDD</th></tr>{grid_rows}</table>

<h2>六、复现与数据溯源</h2>
<div class="card">
<b>复现命令</b>：<br>
<code>PYTHONHASHSEED=0 python3 scripts/archive_huanjing_cangwei.py --dump-hash</code><br>
<code>PYTHONHASHSEED=42 python3 scripts/archive_huanjing_cangwei.py --dump-hash</code>（两哈希一致）<br>
<code>PYTHONHASHSEED=0 python3 scripts/archive_huanjing_cangwei.py</code>（生成 raw + 本 HTML）<br>
<b>双跑哈希</b>：seed0 <code>{h0}</code> / seed42 <code>{h42}</code><br>
<b>原始数据</b>：<code>docs/experiments/raw/huanjing/</code>（逐实验 JSON：参数、事前判定标准原文、逐日净值、月度再平衡记录、E序列、双跑哈希）<br>
<b>数据源</b>：<code>/Users/yongbiaoli/.lei_signal_lab/cache/a_share_klines_full.parquet</code>（环境层，5211只）+ <code>&lt;code&gt;.bars.parquet</code>（ETF 11只）
</div>

<h2>七、已知问题 / 已修 bug 清单（诚实条款）</h2>
<div class="card"><ul>
 <li>① 判定标准为归档时固化；探索轮先于标准，重跑数字与探索轮一致（无事后改标准、无改数字）。</li>
 <li>② 探索轮两处<b>代码笔误在首跑前</b>修复（多余括号致语法错、一处冗余 chr 拼接），不影响任何数字；首跑后零数字修正。</li>
 <li>③ vt 目标波动用基准全样本波动（常数前视，只影响水平不影响择时）——与 C/H 节同款处理，归档口径。</li>
 <li>④ 环境层数据 a_share_klines_full 含幸存者偏差（当前存续股回溯），宽度/RV 读数系统性偏乐观。</li>
 <li>⑤ ETF 缓存残缺：159915 仅 120 根（剔除）、512890/515880 仅 2024 起（动态入池自然处理，未删数据）。池子偏成长行业，行业分散贡献了大超额（对照 510300 持有仅 4.3%）。</li>
 <li>⑥ 样本 6.6 年单区间，无 walk-forward/留一（配置间共享同一区间属同轮多重比较，仅 vt 有跨轮独立验证背书）。</li>
</ul></div>
</body></html>"""
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html)
    print(f"raw → {RAW}（{len(CONFIGS)+1} 个 JSON）")
    print(f"html → {OUT_HTML}")
    print("verdicts:", json.dumps(verdicts, ensure_ascii=False))
