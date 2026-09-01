#!/usr/bin/env python3
"""本轮（2026-08-27/28）回测成绩 Web 报告页生成器。

产出：web/public/reports/round-2026-08-28.html（自包含，内嵌 SVG，离线可开，
不依赖网络/CDN；不改动 web/ WIP 与 ui/ 冻结目录）。
复现：PYTHONHASHSEED=0 python3 scripts/render_round_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_portfolio_pool import build  # noqa: E402
from run_bform_global import A_LEGS, load_px  # noqa: E402
from run_bform_dynamic import simulate_direct  # noqa: E402
from run_m5_walkforward import tier_for  # noqa: E402

OUT = REPO / "web/public/reports/round-2026-08-28.html"
RAW_PS = SRC / "portfolio_split"


def jload(name):
    return json.load(open(RAW_PS / name))


def yearly(eq: pd.Series) -> dict:
    yr, base = eq.groupby(eq.index.year).last(), eq.groupby(eq.index.year).first()
    return {int(k): round((v / b0 - 1) * 100, 1) for k, v, b0 in zip(yr.index, yr.values, base.values)}


def svg_line(series: dict[str, pd.Series], w=880, h=300, log=True, title="") -> str:
    pad = {"l": 56, "r": 12, "t": 26, "b": 26}
    all_vals = pd.concat(list(series.values()))
    lo, hi = float(all_vals.min()), float(all_vals.max())
    if log:
        lo, hi = np.log10(max(lo, 1e-9)), np.log10(hi)
    dates = list(next(iter(series.values())).index)
    x0, x1 = dates[0].timestamp(), dates[-1].timestamp()

    def X(d):
        return pad["l"] + (d.timestamp() - x0) / (x1 - x0) * (w - pad["l"] - pad["r"])

    def Y(v):
        t = np.log10(v) if log else v
        return h - pad["b"] - (t - lo) / (hi - lo + 1e-12) * (h - pad["t"] - pad["b"])

    colors = {"B形态9池": "#34d399", "等权持有": "#64748b", "M5跨市场": "#38bdf8",
              "防守档": "#fbbf24", "H5等权持有": "#64748b",
              "创业板+纳指·2只": "#fb923c", "创业板+标普·2只": "#a78bfa",
              "MINI4·4只": "#38bdf8", "MINI3·3只": "#34d399",
              "2只版持有对照": "#475569", "MINI5·5只": "#f472b6",
              "科创4只·4K": "#fbbf24", "4K持有对照": "#475569",
              "科创100+纳指·2只": "#e879f9", "科创双雄+纳指·3只": "#22d3ee"}
    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0b1220;border-radius:10px">',
             f'<text x="{pad["l"]}" y="16" fill="#94a3b8" font-size="12">{title}</text>']
    # 网格与 y 轴刻度
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        t = lo + frac * (hi - lo)
        val = 10 ** t if log else t
        y = h - pad["b"] - frac * (h - pad["t"] - pad["b"])
        parts.append(f'<line x1="{pad["l"]}" y1="{y:.0f}" x2="{w-12}" y2="{y:.0f}" stroke="#1e293b" stroke-width="1"/>')
        parts.append(f'<text x="{pad["l"]-6}" y="{y+4:.0f}" fill="#64748b" font-size="10" text-anchor="end">{val:.1f}x</text>')
    for yr in range(dates[0].year + 1, dates[-1].year + 1, 2):
        d = pd.Timestamp(f"{yr}-01-01")
        if x0 < d.timestamp() < x1:
            parts.append(f'<line x1="{X(d):.0f}" y1="{pad["t"]}" x2="{X(d):.0f}" y2="{h-pad["b"]}" stroke="#1e293b"/>')
            parts.append(f'<text x="{X(d):.0f}" y="{h-8}" fill="#64748b" font-size="10" text-anchor="middle">{yr}</text>')
    for name, s in series.items():
        step = max(1, len(s) // 400)
        pts = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in list(s.items())[::step])
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{colors.get(name, "#a78bfa")}" stroke-width="1.8"/>')
    lx = pad["l"] + 8
    for name in series:
        parts.append(f'<rect x="{lx}" y="6" width="10" height="3" fill="{colors.get(name, "#a78bfa")}"/>')
        parts.append(f'<text x="{lx+14}" y="11" fill="#cbd5e1" font-size="11">{name}</text>')
        lx += 20 + len(name) * 11
    parts.append("</svg>")
    return "".join(parts)


def svg_tier(tier: pd.Series, w=880, h=90) -> str:
    dates = list(tier.index)
    x0, x1 = dates[0].timestamp(), dates[-1].timestamp()
    segs, cur, start = [], tier.iloc[0], dates[0]
    for d, v in list(tier.items())[1:]:
        if v != cur:
            segs.append((start, d, cur))
            cur, start = v, d
    segs.append((start, dates[-1], cur))
    cmap = {1.0: "#34d399", 0.5: "#fbbf24", 0.0: "#ef4444"}
    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0b1220;border-radius:10px">',
             '<text x="8" y="14" fill="#94a3b8" font-size="12">宽度三档时间轴（绿=满仓 黄=半仓 红=空仓）</text>']
    y, hh = 26, 46
    for s, e, v in segs:
        x = 8 + (s.timestamp() - x0) / (x1 - x0) * (w - 16)
        xx = 8 + (e.timestamp() - x0) / (x1 - x0) * (w - 16)
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{max(xx-x,1):.1f}" height="{hh}" fill="{cmap.get(v, "#64748b")}" opacity="0.85" rx="2"/>')
    for yr in range(dates[0].year + 1, dates[-1].year + 1, 2):
        d = pd.Timestamp(f"{yr}-01-01")
        if x0 < d.timestamp() < x1:
            x = 8 + (d.timestamp() - x0) / (x1 - x0) * (w - 16)
            parts.append(f'<line x1="{x:.0f}" y1="{y}" x2="{x:.0f}" y2="{y+hh}" stroke="#0b1220"/>')
            parts.append(f'<text x="{x:.0f}" y="{y+hh+12}" fill="#64748b" font-size="9" text-anchor="middle">{yr}</text>')
    parts.append("</svg>")
    return "".join(parts)


def heatmap(cells: dict) -> str:
    lows = ["35", "40", "43.3", "45", "50"]
    highs = ["50", "55", "56.7", "60", "65"]
    anns = [v["ann"] for v in cells.values()]
    amin, amax = min(anns), max(anns)
    rows = ['<table class="heat"><tr><th></th>' + "".join(f"<th>high {h}</th>" for h in highs) + "</tr>"]
    for lo in lows:
        cells_row = "".join(
            (lambda v: f'<td style="background:rgba(52,211,153,{0.15+0.7*(v-amin)/(amax-amin):.2f})">{v}</td>' if v is not None else "<td>—</td>")(
                cells.get(f"{lo}.0/{hi}.0", cells.get(f"{lo}/{hi}", {})).get("ann") if f"{lo}.0/{hi}.0" in cells or f"{lo}/{hi}" in cells else None)
            for hi in highs)
        rows.append(f"<tr><th>low {lo}</th>{cells_row}</tr>")
    return "".join(rows) + "</table>"


def main() -> None:
    # ── 数据 ──
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    prices, ones, expo = build(members)
    eq_b9 = rps.simulate(prices, expo)["eq"]
    eq_hold = rps.simulate(prices, ones)["eq"]
    tier = rps.tier_daily(rps.load_breadth(), prices.index)

    # 防守档（池价闸 g0.6）
    rets = prices.pct_change().fillna(0.0)
    pool_idx = (1.0 + rets.mean(axis=1)).cumprod()
    ma = pool_idx.rolling(200).mean()
    gd = pd.Series(np.where(pool_idx > ma, 1.0, 0.6), index=prices.index)
    gd[ma.isna()] = 1.0
    gw, gsig = rps.weekly_last(gd)
    gate = pd.Series(np.nan, index=prices.index)
    pos = prices.index.searchsorted(list(gsig.values))
    for p, gv in zip(pos, gw.values):
        if p + 1 < len(prices.index):
            gate.iloc[p + 1] = float(gv)
    gate = gate.ffill().fillna(1.0)
    eq_def = rps.simulate(prices, expo.mul(gate, axis=0))["eq"]

    # M5
    b200 = rps.load_breadth()
    px5 = load_px()
    n5 = px5.shape[1]
    ones5 = pd.DataFrame(1.0, index=px5.index, columns=px5.columns)
    t5 = tier_for(b200, px5.index, 43.3, 56.7)
    expo5 = ones5.copy()
    for c in px5.columns:
        if c in A_LEGS:
            expo5[c] = t5
    eq_m5 = simulate_direct(px5, expo5 / n5)
    eq_h5 = simulate_direct(px5, ones5 / n5)

    y_b9, y_hold = yearly(eq_b9), yearly(eq_hold)
    params = jload("portfolio_params_results.json")
    plac = jload("bform_placebo_results.json")
    wf = jload("bform_walkforward_results.json")
    rob = jload("portfolio_robustness.json")
    glob = jload("bform_global_results.json")
    mini = jload("bform_mini_results.json")
    duo = jload("bform_duo_results.json")
    # 配置总排行榜
    rank_rows = [
        ("B9 · 9标的×三档", "11.99", "−34.7", "0.345", "2015-06→2026-08", "11.2年",
         "全周期（股灾/熔断/18熊/19-21牛/22-23阴跌/24-26科技牛）", "★★★ 唯一全套认证", "ok"),
        ("创业板+纳指 · 2只", "15.83", "−25.6", "0.618", "2010-06→2026-08", "16.2年",
         "全周期+美股2020崩盘/2022熊（最完整）", "★★ 事后选腿，预期折让至11-12%", "ok"),
        ("MINI4 · 4只", "13.13", "−23.6", "0.556", "2010-06→2026-08", "16.2年",
         "全周期+美股两轮崩盘", "★★ 用户点名延伸，画像最优之一", "ok"),
        ("MINI3 · 3只", "11.37", "−26.5", "0.429", "2010-06→2026-08", "16.2年",
         "全周期+美股崩盘", "★ 初判通过", "ok"),
        ("M5 · 5指数", "11.42", "−23.7", "0.483", "2010-06→2026-08", "16.2年",
         "全周期", "★ 配置型可选（安慰剂91.8分位）", "ok"),
        ("防守档 · B9+池价闸", "10.51", "−24.0", "0.437", "2015-06→2026-08", "11.2年",
         "全周期", "★ 用户可选（未过采纳线）", "ok"),
        ("单做创业板（冠军）", "12.19", "−38.0", "0.321", "2010-06→2026-08", "16.2年",
         "全周期", "★ 血统策略，回撤最深", ""),
        ("科创100+纳指 · 2只", "20.46", "−25.9", "0.789", "2020-01→2026-08", "6.6年",
         "部分（新冠崩盘/阴跌/科技牛；缺2015股灾与2018熊）", "⚠ 双重折让（短窗+选腿）预期~10-12%", "warn"),
        ("科创50+100+纳指 · 3只", "18.56", "−28.4", "0.654", "2020-01→2026-08", "6.6年",
         "部分（同上）", "⚠ 激进卫星仓", "warn"),
        ("MINI5 · 5只(含科创50)", "14.59", "−22.9", "0.638", "2020-01→2026-08", "6.6年",
         "部分（同上）", "⚠ 短窗折让", "warn"),
        ("等权持有 9 标的（对照）", "−0.48", "−49.6", "−0.01", "2015-06→2026-08", "11.2年",
         "全周期", "对照基线", "bad"),
    ]
    rank_html = "".join(
        f"<tr><td><b>{n}</b></td><td class='{cls or 'muted'}'>{a}%</td><td>{d}%</td><td>{c}</td>"
        f"<td class='muted'>{w}</td><td class='muted'>{y}</td><td class='muted'>{cy}</td><td class='muted'>{cred}</td></tr>"
        for n, a, d, c, w, y, cy, cred, cls in rank_rows)
    st = json.load(open(SRC / "stock_breadth/stock_technical_results.json"))
    st_rows = ""
    for n, r in st["stocks"].items():
        h, t = r["HOLD"], r["TECH"]
        b = r.get("BREADTH")
        st_rows += (f"<tr><td><b>{n}</b><br><span class='muted'>{r['窗口']}</span></td>"
                    f"<td>{h['ann_pct']}% / {h['maxdd_pct']}%</td>"
                    f"<td>{t['ann_pct']}% / {t['maxdd_pct']}%</td>"
                    f"<td class=\"{'ok' if r['TECH减HOLD']['年化pp'] >= 0 else 'bad'}\">{r['TECH减HOLD']['年化pp']:+}pp / {r['TECH减HOLD']['回撤pp']:+}pp</td>"
                    f"<td>{(str(b['ann_pct']) + '% / ' + str(b['maxdd_pct']) + '%') if b else '—'}</td></tr>")
    lei = json.load(open(SRC / "stock_breadth/lei_stocks_results.json"))
    lei_rows = ""
    for n, r in lei["stocks"].items():
        h, l, lb = r["HOLD"], r["LEI"], r["LEI_BREADTH"]
        lei_rows += (f"<tr><td><b>{n}</b></td>"
                     f"<td>{h['cagr_pct']}% / {h['maxdd_pct']}%</td>"
                     f"<td>{l['cagr_pct']}% / {l['maxdd_pct']}%</td>"
                     f"<td class='ok'>{r['LEI减HOLD']['dd_pp']:+}pp</td>"
                     f"<td>{r['n_trades']}笔 / ΣR {r['cum_R']}</td>"
                     f"<td>{lb['cagr_pct']}% / {lb['maxdd_pct']}%</td></tr>")
    lei_v = lei["verdict"]
    st_summary = st["summary"]
    ax = json.load(open(SRC / "ashare_axes/ashare_axes_results.json"))
    scan_rows = "".join(
        f"<tr><td><b>{n}</b></td><td class='muted'>{v['窗口']}</td>"
        f"<td class='ok'>{v['M版']['ann_pct']}%</td><td class='ok'>{v['M版']['maxdd_pct']}%</td>"
        f"<td>{v['M版']['calmar']}</td><td class='muted'>{v['持有']['ann_pct']}% / {v['持有']['maxdd_pct']}%</td>"
        f"<td class=\"{'ok' if v['判定'] == '适配' else 'bad'}\">{v['判定']}</td></tr>"
        for n, v in sorted(ax["C_scan"].items(), key=lambda kv: -(kv[1]["M版"]["calmar"] or 0)))
    kc = jload("bform_kc_results.json")
    ext = jload("bform_extreme_lines.json")
    ext_rows = ""
    for pool, r in ext.items():
        ref = r["ref"]
        ext_rows += (f"<tr><td rowspan=6><b>{pool}</b></td><td>冠军线 43.3/56.7</td>"
                     f"<td class='ok'>{ref['ann_pct']}%</td><td>{ref['maxdd_pct']}%</td>"
                     f"<td class='ok'>{ref['calmar']}</td><td class='muted'>{ref['平均敞口']}</td></tr>")
        for k, v in r["lines"].items():
            ext_rows += (f"<tr><td>{k}</td><td>{v['ann_pct']}%</td><td>{v['maxdd_pct']}%</td>"
                         f"<td>{v['calmar']}</td><td class='muted'>{v['平均敞口']}</td></tr>")

    # 净值曲线（带年份时间轴）
    from run_bform_mini import POOLS as MINI_POOLS
    from run_bform_duo import POOLS as DUO_POOLS
    from run_bform_kc import POOLS as KC_POOLS
    from run_bform_mini import load_series

    def pool_eq(cfg, start):
        frames = {n: load_series(rel) for n, rel in cfg["A"] + cfg["US"]}
        px = pd.DataFrame(frames)
        if cfg["US"]:
            cn = px[[n for n, _ in cfg["A"]]].dropna().index
            px = px.reindex(cn).ffill()
        px = px[(px.index >= pd.Timestamp(start))
                & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
        n = px.shape[1]
        tier = tier_for(b200, px.index, 43.3, 56.7)
        ones = pd.DataFrame(1.0, index=px.index, columns=px.columns)
        expo = ones.copy()
        for c, _ in cfg["A"]:
            expo[c] = tier
        return simulate_direct(px, expo / n), simulate_direct(px, ones / n)

    eq_dci, h_dci = pool_eq(DUO_POOLS["DUO_CYB_IXIC"], "2010-06-01")
    eq_dcs, _ = pool_eq(DUO_POOLS["DUO_CYB_SPX"], "2010-06-01")
    eq_m3, _ = pool_eq(MINI_POOLS["MINI3"], "2010-06-01")
    eq_m4, _ = pool_eq(MINI_POOLS["MINI4"], "2010-06-01")
    chart_long = svg_line({"创业板+纳指·2只": eq_dci, "创业板+标普·2只": eq_dcs,
                           "MINI4·4只": eq_m4, "MINI3·3只": eq_m3,
                           "2只版持有对照": h_dci},
                          title="长窗净值 2010-06→2026-08（对数轴，X 轴=年份）：极简/迷你池")

    eq_k100, _ = pool_eq(KC_POOLS["KC_D100_N"], "2020-01-02")
    eq_k2, _ = pool_eq(KC_POOLS["KC_T50_T100_N"], "2020-01-02")
    eq_m5, _ = pool_eq(MINI_POOLS["MINI5"], "2020-01-02")
    eq_4k, h_4k = pool_eq(MINI_POOLS["MINI4K"], "2020-01-02")
    chart_short = svg_line({"科创100+纳指·2只": eq_k100, "科创双雄+纳指·3只": eq_k2,
                            "MINI5·5只": eq_m5, "科创4只·4K": eq_4k,
                            "4K持有对照": h_4k},
                           title="短窗净值 2020-01→2026-08（对数轴，X 轴=年份）：科创系组合")

    kc_rows = "".join(
        f"<tr><td><b>{k}</b></td><td class='muted'>{' + '.join(v['legs'])}</td>"
        f"<td class='ok'>{v['M版']['ann_pct']}%</td><td class='ok'>{v['M版']['maxdd_pct']}%</td>"
        f"<td>{v['M版']['calmar']}</td><td>{v['M版']['sharpe']}</td>"
        f"<td class='muted'>{v['等权持有']['ann_pct']}% / {v['等权持有']['maxdd_pct']}%</td>"
        f"<td class=\"{'ok' if v['判定'] == '可用' else 'bad'}\">{v['判定']}</td></tr>"
        for k, v in kc.items() if not k.startswith("_"))
    duo_rows = "".join(
        f"<tr><td><b>{k.replace('_', ' ')}</b></td><td class='muted'>{' + '.join(v['legs'])}（{v['n']}只）</td>"
        f"<td class='ok'>{v['M版']['ann_pct']}%</td><td class='ok'>{v['M版']['maxdd_pct']}%</td>"
        f"<td>{v['M版']['calmar']}</td><td>{v['M版']['sharpe']}</td>"
        f"<td class='muted'>{v['等权持有']['ann_pct']}% / {v['等权持有']['maxdd_pct']}%</td>"
        f"<td class=\"{'ok' if v['判定'] == '可用' else 'bad'}\">{v['判定']}</td></tr>"
        for k, v in duo.items() if not k.startswith("_"))
    sb = json.load(open(SRC / "stock_breadth/stock_breadth_results.json"))
    ssum = sb["summary"]
    s_top = sorted(sb["stocks"].items(), key=lambda kv: -kv[1]["gap"])[:5]
    s_bot = sorted(sb["stocks"].items(), key=lambda kv: kv[1]["gap"])[:5]
    stock_rows = "".join(
        f"<tr><td>{k}</td><td class='ok'>+{v['gap']}pp</td><td class='muted'>{v['dd_gap']:+}pp</td>"
        f"<td class='muted'>{v['ann_tier']}% / {v['ann_hold']}%</td></tr>"
        for k, v in s_top)
    stock_rows += "<tr><td colspan=4 class='muted'>⋯⋯</td></tr>"
    stock_rows += "".join(
        f"<tr><td>{k}</td><td class='bad'>{v['gap']}pp</td><td class='muted'>{v['dd_gap']:+}pp</td>"
        f"<td class='muted'>{v['ann_tier']}% / {v['ann_hold']}%</td></tr>"
        for k, v in s_bot)
    mini_rows = "".join(
        f"<tr><td><b>{k}</b></td><td class='muted'>{' + '.join(v['legs'])}<br>{v['窗口']}</td>"
        f"<td class='ok'>{v['M版']['ann_pct']}%</td><td class='ok'>{v['M版']['maxdd_pct']}%</td>"
        f"<td>{v['M版']['calmar']}</td><td>{v['M版']['sharpe']}</td>"
        f"<td class='muted'>{v['等权持有']['ann_pct']}% / {v['等权持有']['maxdd_pct']}%</td>"
        f"<td class=\"{'ok' if '可用' in v['判定'] else 'bad'}\">{v['判定']}</td></tr>"
        for k, v in mini.items())

    m = lambda e: rps.metrics(e)  # noqa: E731
    mb, mh, md, mm, mhh = m(eq_b9), m(eq_hold), m(eq_def), m(eq_m5), m(eq_h5)

    years = sorted(set(y_b9) | set(y_hold))
    yearly_rows = "".join(
        f"<tr><td>{y}</td><td>{y_hold.get(y, '')}</td><td>{y_b9.get(y, '')}</td></tr>" for y in years)

    experiments = [
        ("虹吸判别器·市场层", "B200 结构能否判别结构牛", "✗ 判负", "疯牛段亮灯、虹吸段沉默，方向反"),
        ("RS26 背离判别器", "标的与全A背离度触发下岗", "✗ 判负", "方向对但 +9.2pp<15pp 门槛；证券 −5pp"),
        ("接刀格时间止损", "超时未复苏降档", "✗ 判负", "创业板长满仓段全以 V 反收尾，汇率结构性为负"),
        ("适配分账（Donchian）", "趋势腿免闸+机械止损", "✗ 判负", "被全闸打穿 10.5pp；机械止损 2019V 再入滞后"),
        ("B 形态（组合宽度预算）", "9 标的 × B200 三档", "✓ 定稿", "年化 +12.0% vs 持有 −0.5%；回撤 −35% vs −50%"),
        ("参数高原 / 分半 / 扩池", "E1/E2/E3", "高原✓ 分半✗ 扩池✗", "24/24 格全过；扩 13 池降质，保持 9"),
        ("B walk-forward 终审", "双年滚动选参 OOS", "✓ 通过", "OOS 8.6% vs 持有 4.0%，回撤浅 9.9pp"),
        ("B 安慰剂检验", "500 次错相位平移", "✓ 满分", "真实 +12.5pp = 零分布 100 分位"),
        ("B 摩擦压力 + 档数", "30bp/T+2/5档对照", "✓ 通过", "维持 3 档（5 档 2.1% 崩）；周频确认"),
        ("结构变体 ×3", "双宽度门/池价闸/月频", "✗ 全归档", "池价闸差 0.4pp 未过线 → 防守档备选"),
        ("叠加 ×2 + 迭代", "动量倾斜/波动目标/闸值", "✗ 全归档", "逆波动率/温和动量/满仓档动量均不胜等权"),
        ("动态入池（耦合度）", "年度滚动选 9 只", "✗ 判负", "分母镜像小票池 5.0%；选池靠结构分散"),
        ("动态权重 ×3", "逆波动率/慢动量/条件动量", "✗ 全归档", "等权即局部最优（合计 4 案全败）"),
        ("跨市场 M5 主实验", "A腿三档+美腿持有", "严格口径✗ → 确认组✓", "11.4%/−23.7%/Calmar 0.483；起点 31/31、留一 5/5"),
        ("M5 walk-forward", "OOS 检验", "✗ 判负", "年化与持有打平（11.92 vs 12.0）＝风险转换器"),
        ("M5 安慰剂", "Calmar 差零分布", "✗ 91.8 分位", "3/5 腿受闸功效不足；M5 定格「配置型可选」"),
    ]

    exp_rows = "".join(
        f'<tr><td>{i+1}</td><td>{n}</td><td class="muted">{d}</td>'
        f'<td class="{"ok" if v.startswith("✓") or "✓" in v else "bad"}">{v}</td>'
        f'<td class="muted">{note}</td></tr>'
        for i, (n, d, v, note) in enumerate(experiments))

    checks = [
        ("起点偏移", "31/31 个月度起点全占优", True),
        ("参数高原", "24/24 网格全过（6.9-13.1%）", True),
        ("留一稳健", "13/13 去标的判定不翻转", True),
        ("分半冻结", "前半参数后半 OOS +4.3pp", True),
        ("walk-forward", "OOS 8.6%/+4.6pp，选参稳定", True),
        ("安慰剂", "真实超额 = 零分布 100 分位", True),
        ("摩擦压力", "30bp + T+2 优势不衰减", True),
        ("档数对照", "3 档完胜 5 档血统线", True),
    ]
    check_items = "".join(
        f'<div class="check"><span class="dot {"pass" if ok else "fail"}"></span>'
        f'<div><b>{n}</b><div class="muted">{d}</div></div></div>' for n, d, ok in checks)

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>宽度体系本轮回测报告 · 2026-08-27/28</title><style>
body{{background:#0f172a;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;margin:0;padding:32px;}}
.wrap{{max-width:960px;margin:0 auto}} h1{{font-size:26px;margin:0 0 4px}}
h2{{font-size:17px;margin:32px 0 12px;color:#7dd3fc;border-left:3px solid #38bdf8;padding-left:10px}}
.muted{{color:#94a3b8;font-size:12.5px}} .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}
.kpi{{background:#1e293b;border-radius:12px;padding:14px}} .kpi b{{font-size:22px;display:block;margin-top:2px}}
.kpi .g{{color:#34d399}} .kpi .y{{color:#fbbf24}} .kpi .b{{color:#38bdf8}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#1e293b;border-radius:10px;overflow:hidden}}
th,td{{padding:7px 10px;border-bottom:1px solid #334155;text-align:left}} th{{color:#94a3b8;font-weight:500;background:#0b1220}}
td.ok{{color:#34d399;font-weight:600}} td.bad{{color:#f87171}}
.checks{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .check{{display:flex;gap:10px;align-items:flex-start;background:#1e293b;border-radius:10px;padding:10px}}
.dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:5px}} .dot.pass{{background:#34d399}} .dot.fail{{background:#f87171}}
.heat td{{text-align:center;font-weight:600}} .flag{{background:#451a03;border:1px solid #92400e;border-radius:10px;padding:12px;margin-top:10px}}
a{{color:#7dd3fc}} .foot{{margin-top:36px;color:#64748b;font-size:12px}}
</style></head><body><div class="wrap">
<h1>宽度体系 · 本轮回测总览</h1>
<div class="muted">2026-08-27 → 08-28 · 16 个实验组 / 19+ 预注册判定 · 全部双跑哈希复现 · LEI 信号系统宽度择时工作流</div>

<div class="kpis">
<div class="kpi"><span class="muted">认证组件 年化</span><b class="g">+12.0%</b><span class="muted">vs 等权持有 −0.5%</span></div>
<div class="kpi"><span class="muted">最大回撤</span><b class="g">−34.7%</b><span class="muted">vs 持有 −49.6%</span></div>
<div class="kpi"><span class="muted">安慰剂分位</span><b class="g">100%</b><span class="muted">500 次错相位零分布</span></div>
<div class="kpi"><span class="muted">当前档位（08-18）</span><b class="y">满仓</b><span class="muted">B200 = 28.85</span></div>
</div>

<h2>B 形态 9 池 · 净值与档位（2015-06 → 2026-08）</h2>
{svg_line({"B形态9池": eq_b9, "等权持有": eq_hold, "防守档": eq_def}, title="净值（对数轴）：B形态 / 防守档 / 等权持有")}
<div style="height:8px"></div>
{svg_tier(tier)}

<h2>三档位对比（同一机械：等权 · 5% 带 · 10bp）</h2>
<details open style="margin-bottom:10px"><summary class="muted" style="cursor:pointer">📖 指标与术语解释（点开/收起）</summary>
<table style="margin-top:8px"><tr><th style="width:120px">术语</th><th>大白话解释</th></tr>
<tr><td><b>年化</b></td><td>平均每年赚多少（复利口径）。对照：9 标的不择时拿 11 年是 −0.5%/年。</td></tr>
<tr><td><b>回撤</b></td><td>从最高点跌到最低点的最大幅度 =「最惨亏过多少」。−49.6% 约等于腰斩。</td></tr>
<tr><td><b>Calmar</b></td><td>年化 ÷ 最大回撤。每吃 1% 回撤换回多少年化收益，越高越「值」。</td></tr>
<tr><td><b>Sharpe</b></td><td>年化 ÷ 整体波动。每担 1 份颠簸赚多少，衡量净值曲线「稳不稳还能赚」。</td></tr>
<tr><td><b>B200</b></td><td>全 A 站上 200 日均线的个股占比（0-100），市场参与度温度计。</td></tr>
<tr><td><b>三档 43.3/56.7</b></td><td>每周五收盘看 B200：&lt;43.3 满仓 / 43.3-56.7 半仓 / ≥56.7 空仓，次一交易日执行。</td></tr>
<tr><td><b>5% 带</b></td><td>目标仓位与实际差 ≥5 个百分点才调仓，防频繁小额交易。</td></tr>
<tr><td><b>10bp</b></td><td>bp=万分之一。10bp=0.1%，每次买卖单边收 0.1% 成本（费+滑点假设）。</td></tr>
<tr><td><b>池价 MA200 闸 0.6</b></td><td>防守档专用：池指数跌破自身 200 日线 → 总仓位 ×0.6，收复则恢复。</td></tr>
<tr><td><b>A 腿 / 美腿</b></td><td>A股指数部分 / 美股指数部分。美股腿永远满仓（任何闸均已证伪）。</td></tr>
<tr><td><b>起点偏移 31/31</b></td><td>建仓月从 2015-06 逐月后移共 31 次，每次都赢 → 不靠入场运气。</td></tr>
<tr><td><b>参数高原 24/24</b></td><td>档位线换 24 种组合全部大幅跑赢（最差 6.9%/年）→ 不是神参数碰巧。</td></tr>
<tr><td><b>留一 13/13</b></td><td>每次扔掉一只标的重跑，结论不翻转 → 不依赖某一只。</td></tr>
<tr><td><b>分半冻结</b></td><td>只用前半段选参数、冻住拿到后半段用，仍超持有 4.3pp → 排除看全历史挑参。</td></tr>
<tr><td><b>walk-forward</b></td><td>每两年只用当时可得数据重选参数往前走；OOS=样本外（未来段）成绩。</td></tr>
<tr><td><b>安慰剂</b></td><td>把宽度在时间轴上随机错位 500 次（形态还在、与行情对应打乱）重跑——最强假宽度只 +5.5pp，真实 +12.5pp 排 100 分位 → 超额来自真实信息，非机械假象。</td></tr>
<tr><td><b>摩擦压力</b></td><td>成本 0.1%→0.3%、成交 T+1→T+2 后优势不衰减。</td></tr>
<tr><td><b>pp</b></td><td>百分点（如 +4.4pp = 高 4.4 个百分点）。</td></tr>
</table></details>
<table><tr><th>配置</th><th>构成</th><th>年化</th><th>回撤</th><th>Calmar</th><th>Sharpe</th><th>身份</th></tr>
<tr><td><b>B9 纯A进攻档</b></td><td>9 标的 × B200 三档</td><td class="ok">{mb['ann_pct']}%</td><td class="ok">{mb['maxdd_pct']}%</td><td>{mb['calmar']}</td><td>{mb['sharpe']}</td><td>✓ 认证组件（全检验通过）</td></tr>
<tr><td>M5 跨市场均衡档</td><td>A 腿三档 + 标普/纳指持有</td><td>{mm['ann_pct']}%</td><td class="ok">{mm['maxdd_pct']}%</td><td>{mm['calmar']}</td><td>{mm['sharpe']}</td><td>配置型可选（安慰剂 91.8 分位）</td></tr>
<tr><td>防守档（B9+池价闸0.6）</td><td>B9 × 池价 MA200 闸</td><td>{md['ann_pct']}%</td><td class="ok">{md['maxdd_pct']}%</td><td>{md['calmar']}</td><td>{md['sharpe']}</td><td>用户可选（未过采纳线）</td></tr>
<tr><td>等权持有基线</td><td>9 标的买入持有</td><td class="bad">{mh['ann_pct']}%</td><td class="bad">{mh['maxdd_pct']}%</td><td>{mh['calmar']}</td><td>{mh['sharpe']}</td><td>对照</td></tr>
</table>
<div class="muted" style="margin-top:6px">M5/H5 为 2010-06 起 5 指数窗（创业板/沪深300/红利 × 三档 + 标普/纳指无闸）；美股任何闸（宽度逆势/价格闸）均已证伪。</div>

<h2>迷你池（3-5 只，看得过来版）</h2>
<table><tr><th>池</th><th>构成（A腿上闸 · 美腿持有）</th><th>年化</th><th>回撤</th><th>Calmar</th><th>Sharpe</th><th>等权持有对照</th><th>判定</th></tr>{mini_rows}</table>
<div class="muted" style="margin-top:6px">判定口径：C1=对自家等权持有回撤浅 ≥8pp 且 Calmar 更高；C2=年化 ≥ 同窗 B9 −2pp。MINI3/5/4K 为「可用简化版」；MINI4 绝对画像最优但对自家持有改善 7.0pp 差 1pp 未过 C1 线。2020 起短窗池（MINI5/4K）未覆盖 2015/2018，实盘前需打分卡跟踪；迷你池尚未过全套终审（下一步）。</div>

<h2>系统三层结论：哪类标的用哪一层（结论 / 依据 / 可能原因）</h2>
<table><tr><th style="width:150px">层</th><th>结论</th><th>依据</th><th>可能原因</th></tr>
<tr><td><b>面层 · 宽基组合</b></td><td>宽度 B200 三档 × 宽基/迷你池组合 = 系统主战场，全套认证</td>
<td>B9 八道终审全过、安慰剂 100 分位；迷你池 MINI3/4 初判通过；同窗 Calmar 优于一切变体</td>
<td>B200 度量全市场参与度，信号是「面」级信息，作用于资产篮子时信息/噪声比最高</td></tr>
<tr><td><b>行业 ETF（中间地带）</b></td><td>可以用，但每只要过「适配筛查」：同频型 ✓ / 独立行情型 ✗</td>
<td>同频型战绩（证券 +16.3%、地产 +11.7%）；排除名单（AI −6.5%、半导体后半窗 −11.8%、中证500 −9.8%）</td>
<td>行业 ETF = 市场 β + 行业 β 的混合体，行业 β 占比越高与宽度分母越脱钩，档位信息越接近噪声</td></tr>
<tr><td><b>点层 · 个股</b></td><td>宽度层只当弱预算背景；买卖交给 LEI 技术系统（1% 风险 + 技术止损）</td>
<td>30 只个股实测（下表）：中位超额 +1.84pp，仅为指数组（+5.53pp）的 1/3；强周期股有效、独立成长股受损</td>
<td>个股收益 = 市场 β（宽度可覆盖）+ 个性 α（宽度无信息）；空仓档躲得开市场崩盘、躲不开个股独立行情，也会错过独立牛</td></tr>
<tr><td><b>眼层 · 基本面信息</b></td><td>标注/一票否决 + 打分卡记账；验证加分后再升级为正式仓位轴（需拍板）</td>
<td>v2 交接书预留第三轴；量化层每条规则过 8 道检验而人工信息未检验</td>
<td>先用记账证明再加权，防止未检验信息稀释已认证层的优势</td></tr>
</table>

<h2>个股实测（30 只代表股：宽度三档 vs 拿着不动，2010 起，前复权）</h2>
<div class="kpis">
<div class="kpi"><span class="muted">个股中位年化差</span><b class="y">+{ssum['stock_gap_median']}pp</b><span class="muted">指数组 +{ssum['index_gap_median']}pp</span></div>
<div class="kpi"><span class="muted">正超额比例</span><b class="y">{int(ssum['stock_pos_frac']*100)}%</b><span class="muted">指数组 100%</span></div>
<div class="kpi"><span class="muted">回撤改善中位</span><b class="g">+{ssum['stock_dd_gap_median']}pp</b><span class="muted">崩盘保护可迁移</span></div>
<div class="kpi"><span class="muted">判定</span><b class="b">{ssum['VERDICT'][:12]}</b><span class="muted">G1✓ G2✗（按预注册）</span></div>
</div>
<table><tr><th>个股</th><th>年化差（三档−持有）</th><th>回撤差</th><th>年化（三档 / 持有）</th></tr>{stock_rows}</table>
<div class="muted" style="margin-top:6px">规律：强周期/金融股（万科/中信/保利/焦煤）宽度三档大幅有效——本质是「穿股票外衣的指数」；独立成长/防御股（立讯/长电/伊利/紫金/宁德）受损——空仓档错过独立牛。⚠️ 30 只均为 2026 存续股（幸存者偏差偏乐观，结论仍成立更强）。个股的买卖点应交 LEI 技术系统。</div>

<h2>极简池（1-2 只，精简代价曲线）</h2>
<table><tr><th>池</th><th>构成</th><th>年化</th><th>回撤</th><th>Calmar</th><th>Sharpe</th><th>等权持有对照</th><th>判定</th></tr>{duo_rows}</table>
<div class="muted" style="margin-top:6px">精简曲线（年化/回撤）：1只创业板 12.2%/−38.0 → 2只「创业板+纳指」<b>15.8%/−25.6</b> → 3只 MINI3 11.4%/−26.5 → 4只 MINI4 13.1%/−23.6 → 9只 B9 12.0%/−34.7。⚠️ 两只版是从 18 只候选里数据挑出的最优腿组合，带事后选择偏差，真实预期应打折；B9 因白酒 2015 上市无法回 2010 窗，C2 为跨窗比较（已声明）。两只版建议与 MINI4 并行进打分卡。</div>

<h2>精简池净值曲线（时间跨度 2010→2026 / 2020→2026）</h2>
{chart_long}
<div style="height:10px"></div>
{chart_short}

<h2>科创系组合（短窗 2020-01→2026-08，未覆盖 2015/2018）</h2>
<table><tr><th>池</th><th>构成</th><th>年化</th><th>回撤</th><th>Calmar</th><th>Sharpe</th><th>等权持有对照</th><th>判定</th></tr>{kc_rows}</table>
<div class="muted" style="margin-top:6px">⚠️ 科创系全部为 6.6 年短窗 + 事后选腿（成长顺风窗），年化数字不可外推为长期预期；B9 同窗仅 8.5%。定位=激进卫星仓，进打分卡跟踪。C2 参照 B9 2020 同窗 8.54%。</div>

<h2>极端档位线对照（15/85 ~ 35/65 vs 冠军线）</h2>
<table><tr><th>池</th><th>档位线</th><th>年化</th><th>回撤</th><th>Calmar</th><th>平均敞口</th></tr>{ext_rows}</table>
<div class="muted" style="margin-top:6px">结论：极端逆势线全败——中带过宽导致大部分时间停在半仓（15/85 满仓占比仅 11%），错过 B200&lt;43.3 冷窗的满仓收割段；而崩盘时半仓照样挨打。A股 V 型节奏要的是「该满快满、该空快空」的紧带，冠军线 43.3/56.7 在两个池上均最优（参数高原向紧带倾斜的又一次确认）。</div>

<h2>配置总排行榜（含测试期限与牛熊覆盖）</h2>
<table><tr><th>配置</th><th>年化</th><th>回撤</th><th>Calmar</th><th>测试期限</th><th>年限</th><th>牛熊覆盖</th><th>可信度</th></tr>{rank_html}</table>
<div class="muted" style="margin-top:6px">读法：可信度 = 认证层级（全套终审★3 / 长窗初判★2 / 短窗或事后选腿⚠需折让）。数字最好 ≠ 推荐：短窗+事后选腿的组合年化要按 5-7 折折让后再比较。推荐组合：MINI4 或 创业板+纳指为主力（16 年全周期）、B9 为认证锚、科创系为卫星。</div>

<h2>个股技术面贡献度实测（用户自选五股：MA200 技术闸 vs 持有 vs 宽度三档）</h2>
<table><tr><th>个股</th><th>持有（基线）</th><th>MA200 技术闸</th><th>技术−持有（年化/回撤）</th><th>宽度三档</th></tr>{st_rows}</table>
<div class="muted" style="margin-top:6px">五股中位：技术闸超额 <b class="bad">{st_summary['ann_gap_median']}pp</b>、回撤改善 <b>{st_summary['dd_improve_median']}pp</b>（J1/J2 双否）。分段规律：熊市段全部正贡献（2018 熊 +7~+17pp、2021-24 熊腾讯 +25/中微 +63pp）、牛市段全部大负（2019-21 段 −31~−178pp）——<b>朴素趋势闸=熊市保护器、牛市绞肉机</b>。⚠️ 五股皆为时代赢家（幸存者偏差最重）；MA200 为技术面保守下限，非 LEI 全套；个股买卖点的真正技术贡献须待 LEI 接入后重测。</div>

<h2>LEI 全系统个股实测（真模块 A+B'+C+D，1% 风险钉死）</h2>
<table><tr><th>个股</th><th>持有</th><th>LEI 纯版（年化/回撤）</th><th>回撤改善</th><th>交易密度</th><th>LEI+宽度预算</th></tr>{lei_rows}</table>
<div class="muted" style="margin-top:6px">判定：J1 回撤控制 <b class="ok">3/3 过</b>（+32~+73pp）；J2 资金利用率 0/3。<b>收益拆解（诊断）</b>：单股 1-3%/年 = ΣR×1% 的算术结果（茅台 28R→+28%/9.4年），非信号问题——信号池级去重叠后 ΣR <b class="ok">+831R/1681笔</b>（年均88R，茅台A模块6笔胜率83%）；真风险在亏损年（2018 −27R / 2021 −137R / 2022 −43R，1%满配≈深回撤）与单笔跳空尾部（最差 −19.6R）。<b>正确口径 = v2 体系 full_sim（1%风险+回撤降级+并发上限+分账）</b>：分账制终值 224.6万 / 回撤 9.7%（帕累托占优现行 221.5万/15.7%，v2交接书）≈ 9-10%/年 + 个位数回撤。单股裸跑 ≠ 系统。</div>

<h2>系统价值总结（本轮沉淀 · 2026-08-31）</h2>
<div class="kpis">
<div class="kpi"><span class="muted">面层引擎 B9</span><b class="g">+12pp/年</b><span class="muted">vs 持有，回撤砍 1/3，8 道终审</span></div>
<div class="kpi"><span class="muted">点层 LEI 分账</span><b class="g">~10%/年</b><span class="muted">回撤 &lt;10%，ΣR +831 实测</span></div>
<div class="kpi"><span class="muted">证伪免疫</span><b class="b">100 分位</b><span class="muted">安慰剂非运气</span></div>
<div class="kpi"><span class="muted">本轮实验</span><b class="y">19+ 组</b><span class="muted">全部双跑哈希可复现</span></div>
</div>
<table><tr><th>价值主张</th><th>数字</th></tr>
<tr><td>宽度组合 vs 拿着不动</td><td>年化 +12pp（−0.5%→12.0%）、回撤 −49.6%→−34.7%</td></tr>
<tr><td>最强精简版（创业板+纳指，16年全周期）</td><td>15.8%/−25.6%，折让后预期 11-12%</td></tr>
<tr><td>LEI 全池+正确资金层（v2 分账）</td><td>~9-10%/年、回撤个位数（224.6万/9.7%）</td></tr>
<tr><td>LEI 单股防御（1% 风险结构）</td><td>回撤 −4~−19% vs 持有 −51~−80%</td></tr>
<tr><td>未来预期管理</td><td>中位 6-10%；最大风险=A股动量化（对冲=美股腿/防守档）</td></tr>
</table>
<div class="muted">四条元规律：宽度=预算调节器非开关；选池靠结构分散；空档要空干净；美股=持有资产。完整版见 docs/SYSTEM-VALUE-SUMMARY-2026-08-31.md。</div>

<h2>A股新轴（2026-08-31）：融资余额虹吸识别 ✓ + 通用行业适配地图</h2>
<table><tr><th>新轴</th><th>结果</th><th>判定</th></tr>
<tr><td><b>融资余额虹吸识别</b>（20日增速3年分位≥90%持续4周→空仓档改半仓）</td>
<td>B9：年化 12.0→13.1%、Calmar 0.345→0.376、科技牛窗 +10.0pp、股灾段回撤仅 −14.0%、仅 3.3% 时间触发；两只版：15.8→16.5%、科技牛窗 +13.4pp</td>
<td class="ok">✓ 双池全过（B1/B2/B3）</td></tr>
<tr><td>M1 流动性轴（同比方向×预算）</td>
<td>B9 阴跌改善 +8.1pp 但 V 反代价 −11.4pp（滞后指标误杀政策反转）</td>
<td class="bad">✗ 归档为观察层</td></tr>
</table>
<div class="muted" style="margin:8px 0 4px">通用框架「A股腿×B200三档 + 纳指持有」行业适配地图（扫描 14 行业，探索性）：</div>
<table><tr><th>A股腿</th><th>窗口</th><th>年化</th><th>回撤</th><th>Calmar</th><th>持有对照</th><th>判定</th></tr>{scan_rows}</table>
<div class="muted" style="margin-top:6px">适配 = 宽度闸对持有改善 ≥8pp 且达绝对线；半导体/白酒/计算机/芯片等"不适配"多为自驱趋势型（闸改善 &lt;8pp，如国证芯片 M版 24.0% ≈ 持有 24.75%——类纳指资产该裸持有）。半导体实际为部分适配（+7pp 年化但差线 1pp）。融资余额为首个通过的价格外信息源——此前所有价格衍生判别器均判负。</div>

<h2>组合矩阵（行业×技术×个股×美腿，2026-08-31 扫描）</h2>
<table><tr><th>行业A腿(+纳指)</th><th>纯三档</th><th>三档+虹吸</th><th>适配</th><th>虹吸无害</th></tr><tr><td>国证芯片</td><td>24.0%/0.72</td><td class='ok'>26.22%/0.786</td><td>不适配</td><td>✓</td></tr><tr><td>创业板指</td><td>15.83%/0.618</td><td class='ok'>16.53%/0.645</td><td>适配</td><td>✓</td></tr><tr><td>新能车</td><td>17.62%/0.584</td><td class='ok'>18.7%/0.619</td><td>适配</td><td>✓</td></tr><tr><td>半导体</td><td>16.4%/0.585</td><td class='ok'>17.22%/0.614</td><td>不适配</td><td>✓</td></tr><tr><td>证券公司</td><td>15.56%/0.565</td><td class='ok'>16.05%/0.583</td><td>不适配</td><td>✓</td></tr><tr><td>中证白酒</td><td>16.33%/0.566</td><td class='ok'>16.76%/0.581</td><td>不适配</td><td>✓</td></tr><tr><td>中证军工</td><td>13.21%/0.555</td><td class='ok'>13.43%/0.564</td><td>适配</td><td>✓</td></tr><tr><td>中证医疗</td><td>15.63%/0.516</td><td class='ok'>15.91%/0.526</td><td>适配</td><td>✓</td></tr><tr><td>中证计算机</td><td>15.18%/0.493</td><td class='ok'>16.11%/0.523</td><td>不适配</td><td>✓</td></tr><tr><td>国证有色</td><td>15.15%/0.495</td><td class='ok'>15.61%/0.51</td><td>不适配</td><td>✓</td></tr><tr><td>中证煤炭</td><td>12.7%/0.456</td><td class='ok'>13.04%/0.468</td><td>不适配</td><td>✓</td></tr><tr><td>中证传媒</td><td>11.23%/0.394</td><td class='ok'>11.94%/0.419</td><td>适配</td><td>✓</td></tr><tr><td>国证地产</td><td>9.97%/0.352</td><td class='ok'>10.32%/0.364</td><td>不适配</td><td>✓</td></tr><tr><td>国证钢铁</td><td>9.18%/0.326</td><td class='ok'>9.41%/0.334</td><td>适配</td><td>✓</td></tr></table>
<div class="muted">虹吸叠加 14/14 行业无害且全部改善（+0.3~2.2pp）；持有腿对照：纳指 6/6 优于标普。</div>
<table style="margin-top:10px"><tr><th>强周期个股A腿(+纳指)</th><th>M版 年化/Calmar</th><th>持有对照</th><th>C1</th></tr><tr><td>万科A</td><td>13.39%/0.362</td><td class='muted'>4.99%/-50.3%</td><td class="ok">✓</td></tr><tr><td>中信证券</td><td>18.87%/0.655</td><td class='muted'>10.4%/-42.07%</td><td class="ok">✓</td></tr><tr><td>中兴通讯</td><td>20.98%/0.51</td><td class='muted'>16.31%/-41.15%</td><td class="bad">✗</td></tr><tr><td>山西焦煤</td><td>15.27%/0.452</td><td class='muted'>13.2%/-35.02%</td><td class="bad">✗</td></tr><tr><td>紫金矿业</td><td>19.89%/0.679</td><td class='muted'>23.73%/-39.68%</td><td class="ok">✓</td></tr></table>
<div class="muted">个股可插入通用框架：3/5 过线（万科/中信/紫金 ✓，Calmar 0.36-0.68）。</div>
<table style="margin-top:10px"><tr><th>三腿组合（A×2上闸 + 纳指持有）</th><th>年化</th><th>回撤</th><th>Calmar</th><th>持有对照</th></tr><tr><td>创业板指+中证医疗 + 纳指</td><td class='ok'>16.78%</td><td>-26.61%</td><td>0.631</td><td class='muted'>4.32%/-45.46%</td></tr><tr><td>中证医疗+新能车 + 纳指</td><td class='ok'>17.17%</td><td>-27.83%</td><td>0.617</td><td class='muted'>5.18%/-47.15%</td></tr><tr><td>创业板指+半导体 + 纳指</td><td class='ok'>17.63%</td><td>-29.32%</td><td>0.602</td><td class='muted'>6.78%/-45.98%</td></tr><tr><td>创业板指+中证军工 + 纳指</td><td class='ok'>15.16%</td><td>-25.27%</td><td>0.6</td><td class='muted'>5.34%/-46.27%</td></tr><tr><td>中证军工+半导体 + 纳指</td><td class='ok'>14.45%</td><td>-27.13%</td><td>0.533</td><td class='muted'>5.05%/-46.2%</td></tr><tr><td>国证有色+中证煤炭 + 纳指</td><td class='ok'>13.63%</td><td>-34.7%</td><td>0.393</td><td class='muted'>8.16%/-40.31%</td></tr></table>
<div class="muted">探索性扫描（~35 次检视），供入池筛选；单项转正需全套终审。raw: combo_matrix_results.json。</div>

<h2>⏱ 当前执行参考（数据截至 2026-08-31 收盘 · live 面板直算）</h2>
<table><tr><th>指标</th><th>当前值</th><th>系统判定</th></tr>
<tr><td>B200（全A站上年线占比）</td><td><b>24.2</b>（近5日 19.7→24.2 连升）</td><td class="ok">满仓档（&lt;43.3）</td></tr>
<tr><td>B20 / B50</td><td>62.2 / 62.2</td><td>短线参与度已修复至中位——底部右侧初段（「低·修复」格）</td></tr>
<tr><td>融资余额虹吸</td><td>20日增速 +1.2%，3年分位 0.54</td><td>OFF（无豁免）</td></tr></table>
<div class="muted">执行含义：①A股腿（适配行业/强周期股）= 系统口径的买进时机，周频纪律（周五收盘定档→次一交易日执行），建议分 2-3 批建仓；②持有腿（纳指/标普/芯片类）= 无时机，随时 DCA；③个股 LEI 卫星 = 等 LEI 信号，1% 风险，不抢跑。风险提示：B200 仍处低位区，若再度拐头向下则属 2018 型阴跌场景（宽度层无解，靠执行层止损）。宽度日更停摆中——本表由 live 个股面板直算绕过。</div>

<h2>B 形态终审矩阵（8 道全过）</h2>
<div class="checks">{check_items}</div>

<h2>参数高原（网格年化%，无孤峰）</h2>
{heatmap(params['cells'])}
<div class="muted" style="margin-top:4px">全网格 24/24 满足判定；沿用血统参数 43.3/56.7（11.99%，高原中上沿）。walk-forward 滚动选参收敛于 45-50/55 紧带。</div>

<h2>分年收益（%）</h2>
<table><tr><th>年份</th><th>等权持有</th><th>B 形态</th></tr>{yearly_rows}</table>

<h2>本轮实验时间线（判定如实，含全部判负）</h2>
<table><tr><th>#</th><th>实验</th><th>方向</th><th>判定</th><th>要点</th></tr>{exp_rows}</table>

<h2>已知缺口与运维</h2>
<div class="flag">🚩 <b>宽度日更停摆</b>：live 宽度文件被 33 年回填覆写、日更未再写入（数据停于 08-18）。修复 precompute 为合并写入需批准（v2 交接书紧急项 #1）。</div>
<div class="flag" style="border-color:#7c2d12">⚠ <b>两个已知缺口（宽度层无解已归档）</b>：2018 型阴跌（满仓 −28%）；虹吸/结构牛踏空（2025 +1.9% vs +25.1%）。解法在 LEI 执行层（B 管预算 + LEI 管买卖点），入口已侦察。</div>

<div class="foot">报告链：siphon-detector / rs26-detector / knife-timestop / portfolio-split / portfolio-params-pool / bform-final-review / bform-exploration / bform-dynamic / bform-global / m5-final-review（docs/experiments/，2026-08-27~28）<br>
一切结论建议级；转正唯一通道 = 终审通过 + 彪哥拍板。生成：scripts/render_round_report.py</div>
</div></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print("written:", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
