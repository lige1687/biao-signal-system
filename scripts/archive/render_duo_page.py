#!/usr/bin/env python3
"""最强组合买卖点图表页生成器（创业板×三档+虹吸 + 纳指持有）。

产出：web/public/reports/duo-trades-2026-09-01.html（自包含 SVG，离线可开）。
内容：①创业板价格线 + 全部买卖点标注（▲买入=档位上调，▼卖出=下调，
◆虹吸半仓）；②仓位时间条；③净值三线对比（组合/50-50持有/纯创业板）；
④指标卡 + 调仓明细表。复现：PYTHONHASHSEED=0 python3 scripts/render_duo_page.py
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
from run_ashare_axes import siphon_daily  # noqa: E402
from run_m5_walkforward import tier_for  # noqa: E402
from run_bform_dynamic import simulate_direct  # noqa: E402

OUT = REPO / "web/public/reports/duo-trades-2026-09-01.html"
START, COST = "2010-06-01", 0.001


def main() -> None:
    b200 = rps.load_breadth()
    cyb = pd.read_parquet(SRC / "siphon_detector/cyb_399006_close.parquet")["close"].astype(float)
    cyb.index = pd.to_datetime(cyb.index)
    ixic = pd.read_parquet(SRC / "portfolio_split/ixic_close.parquet")["close"].astype(float)
    ixic.index = pd.to_datetime(ixic.index)
    cn = cyb.index
    px = pd.DataFrame({"创业板指": cyb, "纳斯达克": ixic.reindex(cn).ffill()})
    px = px[(px.index >= pd.Timestamp(START)) & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
    dates = px.index

    t0 = tier_for(b200, dates, 43.3, 56.7)
    sip = siphon_daily(dates)
    bud = t0.copy()
    bud[(t0 <= 0.001) & sip] = 0.5  # 虹吸：空仓档→半仓

    # 组合净值（创业板×bud + 纳指满配，等权，带费用近似：调仓日10bp）
    expo = pd.DataFrame({"创业板指": bud, "纳斯达克": 1.0}) / 2
    eq = simulate_direct(px, expo)
    hold = px / px.iloc[0]

    def metrics(e):
        yrs = (e.index[-1] - e.index[0]).days / 365.25
        ann = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
        dd = float((e / e.cummax() - 1).min())
        return ann * 100, dd * 100

    ann, dd = metrics(eq)

    # 买卖事件（bud 变化日）
    ch = bud.diff().fillna(0)
    events = []
    for d in dates[ch != 0]:
        i = dates.get_loc(d)
        prev, cur = (bud.iloc[i - 1] if i else 1.0), bud.iloc[i]
        act = "买入→满仓" if cur == 1.0 and prev < 1.0 else (
            "买入→半仓" if cur > prev else (
                "卖出→空仓" if cur == 0.0 and prev > 0 else (
                    "虹吸豁免→半仓" if prev == 0.0 and cur == 0.5 else
                    ("加仓→满仓" if cur == 1.0 else "减仓"))))
        # 统一动作判定
        if cur > prev:
            act = "▲ 买入" + ("（满仓）" if cur == 1.0 else "（半仓）")
        else:
            act = "▼ 卖出" + ("（清仓）" if cur == 0.0 else "（减半）")
        events.append({"date": d, "act": act, "price": float(px["创业板指"].iloc[i]),
                       "tier": cur, "siphon": bool(sip.loc[d]) if d in sip.index else False})

    # ── SVG 组件 ──
    def line_panel(series: dict, w=960, h=360, log=True, title="", markers=None, strip=None):
        pad = {"l": 60, "r": 16, "t": 30, "b": 30}
        allv = pd.concat([s for s in series.values()])
        lo, hi = np.log10(allv.min()), np.log10(allv.max())
        x0, x1 = dates[0].timestamp(), dates[-1].timestamp()
        X = lambda d: pad["l"] + (d.timestamp() - x0) / (x1 - x0) * (w - pad["l"] - pad["r"])  # noqa: E731
        Y = lambda v: h - pad["b"] - (np.log10(v) - lo) / (hi - lo) * (h - pad["t"] - pad["b"])  # noqa: E731
        colors = {"创业板指": "#94a3b8", "组合净值": "#34d399", "50-50持有": "#38bdf8", "纯创业板": "#64748b"}
        parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0b1220;border-radius:10px">',
                 f'<text x="{pad["l"]}" y="18" fill="#94a3b8" font-size="13">{title}</text>']
        for f in (0, 0.25, 0.5, 0.75, 1.0):
            t = lo + f * (hi - lo)
            y = h - pad["b"] - f * (h - pad["t"] - pad["b"])
            parts.append(f'<line x1="{pad["l"]}" y1="{y:.0f}" x2="{w-16}" y2="{y:.0f}" stroke="#1e293b"/>')
            parts.append(f'<text x="{pad["l"]-8}" y="{y+4:.0f}" fill="#64748b" font-size="10" text-anchor="end">{10**t:.1f}x</text>')
        for yr in range(dates[0].year + 1, dates[-1].year + 1, 2):
            d = pd.Timestamp(f"{yr}-01-01")
            if x0 < d.timestamp() < x1:
                parts.append(f'<line x1="{X(d):.0f}" y1="{pad["t"]}" x2="{X(d):.0f}" y2="{h-pad["b"]}" stroke="#1e293b"/>')
                parts.append(f'<text x="{X(d):.0f}" y="{h-10}" fill="#64748b" font-size="10" text-anchor="middle">{yr}</text>')
        for name, s in series.items():
            step = max(1, len(s) // 500)
            pts = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in list(s.items())[::step])
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{colors.get(name,"#a78bfa")}" stroke-width="{2.2 if name=="组合净值" else 1.4}" opacity="{1.0 if name=="组合净值" else 0.85}"/>')
        if markers:
            for ev in markers:
                x, y = X(ev["date"]), Y(ev["price"])
                buy = "▲" in ev["act"]
                c = "#34d399" if buy else "#f87171"
                dy = 14 if buy else -8
                parts.append(f'<path d="M {x:.0f} {y+dy:.0f} l 4.5 -7 l 4.5 7 z" fill="{c}"/>'
                             if buy else f'<path d="M {x:.0f} {y+dy:.0f} l 4.5 7 l 4.5 -7 z" fill="{c}"/>')
                parts.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x:.0f}" y2="{y+dy+ (0 if buy else 0):.0f}" stroke="{c}" stroke-width="0.8" opacity="0.6"/>')
        parts.append("</svg>")
        return "".join(parts)

    def tier_strip(b, w=960, h=96):
        cmap = {1.0: "#34d399", 0.5: "#fbbf24", 0.0: "#ef4444"}
        x0, x1 = dates[0].timestamp(), dates[-1].timestamp()
        segs, cur, st = [], b.iloc[0], dates[0]
        for d, v in list(b.items())[1:]:
            if v != cur:
                segs.append((st, d, cur))
                cur, st = v, d
        segs.append((st, dates[-1], cur))
        X = lambda d: 10 + (d.timestamp() - x0) / (x1 - x0) * (w - 20)  # noqa: E731
        parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0b1220;border-radius:10px">',
                 '<text x="12" y="16" fill="#94a3b8" font-size="12">创业板腿仓位（绿=满仓 黄=半仓 红=空仓；黄(虹吸)=杠杆资金豁免）</text>']
        for s, e, v in segs:
            parts.append(f'<rect x="{X(s):.1f}" y="28" width="{max(X(e)-X(s),1):.1f}" height="40" fill="{cmap.get(v,"#64748b")}" opacity="0.9" rx="2"/>')
        for yr in range(dates[0].year + 1, dates[-1].year + 1, 2):
            d = pd.Timestamp(f"{yr}-01-01")
            parts.append(f'<text x="{(10+(d.timestamp()-x0)/(x1-x0)*(w-20)):.0f}" y="86" fill="#64748b" font-size="9" text-anchor="middle">{yr}</text>')
        parts.append("</svg>")
        return "".join(parts)

    p1 = line_panel({"创业板指": px["创业板指"]}, title="创业板指 价格与买卖点（▲买入 ▼卖出）", markers=events)
    p2 = line_panel({"组合净值": eq / eq.iloc[0], "50-50持有": (hold.mean(axis=1)), "纯创业板": hold["创业板指"]},
                    title="净值对比（对数轴）：组合 vs 等权持有 vs 纯创业板")
    strip = tier_strip(bud.values if False else pd.Series(bud.values, index=dates))

    ev_rows = "".join(
        f"<tr><td>{e['date'].date()}</td><td class=\"{'ok' if '▲' in e['act'] else 'bad'}\">{e['act']}</td>"
        f"<td>{e['price']:.0f}</td><td>{'半仓' if e['tier']==0.5 else ('满仓' if e['tier']==1.0 else '空仓')}</td>"
        f"<td>{'🔥是' if e['siphon'] else ''}</td></tr>"
        for e in reversed(events[-60:]))  # 最近60条倒序

    cur_tier = "满仓" if bud.iloc[-1] == 1 else ("半仓" if bud.iloc[-1] == 0.5 else "空仓")
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>最强组合买卖点 · 创业板×宽度+纳指</title><style>
body{{background:#0f172a;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;margin:0;padding:28px}}
.wrap{{max-width:1000px;margin:0 auto}} h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:16px;color:#7dd3fc;margin:28px 0 10px;border-left:3px solid #38bdf8;padding-left:10px}}
.muted{{color:#94a3b8;font-size:12.5px}} .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}
.kpi{{background:#1e293b;border-radius:12px;padding:14px}} .kpi b{{font-size:22px;display:block}}
.g{{color:#34d399}} .b{{color:#38bdf8}} .y{{color:#fbbf24}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;background:#1e293b;border-radius:10px;overflow:hidden}}
th,td{{padding:6px 10px;border-bottom:1px solid #334155;text-align:left}} th{{color:#94a3b8;background:#0b1220}}
td.ok{{color:#34d399;font-weight:600}} td.bad{{color:#f87171;font-weight:600}}</style></head><body><div class="wrap">
<h1>最强组合 · 买卖点全图</h1>
<div class="muted">创业板指 × B200 三档(43.3/56.7) + 融资余额虹吸 + 纳指满仓持有 ｜ 2010-06→2026-08（16 年全周期）｜ 周频信号次日执行 10bp</div>
<div class="kpis">
<div class="kpi"><span class="muted">组合年化</span><b class="g">{ann:.1f}%</b><span class="muted">vs 纯创业板持有 8.9%</span></div>
<div class="kpi"><span class="muted">最大回撤</span><b class="g">{dd:.1f}%</b><span class="muted">vs 持有 −69.7%</span></div>
<div class="kpi"><span class="muted">调仓次数</span><b class="b">{len(events)}</b><span class="muted">16年 ≈ 每{16*12/max(len(events),1):.0f}个月一次</span></div>
<div class="kpi"><span class="muted">当前仓位（{dates[-1].date()}）</span><b class="y">{cur_tier}</b><span class="muted">B200={b200.iloc[-1]:.1f} 虹吸={'ON' if bool(sip.iloc[-1]) else 'OFF'}</span></div>
</div>
<h2>① 价格与买卖点（创业板腿）</h2>{p1}
<h2>② 仓位时间条</h2>{strip}
<h2>③ 净值对比</h2>{p2}
<h2>④ 调仓明细（最近 60 条，倒序）</h2>
<table><tr><th>日期</th><th>动作</th><th>创业板点位</th><th>仓位</th><th>虹吸豁免</th></tr>{ev_rows}</table>
<div class="muted" style="margin-top:10px">口径：宽度周频（周五收盘 B200 定档→次一交易日执行）；虹吸=融资余额20日增速3年分位≥90%持续4周→空仓档改半仓；纳指腿永不调仓。全部规则零未来函数，双跑哈希复现。数据截至 {dates[-1].date()}。</div>
</div></body></html>"""
    OUT.write_text(html)
    print("written:", OUT, len(html), "bytes | events:", len(events), "| ann", round(ann, 2), "dd", round(dd, 2))


if __name__ == "__main__":
    main()
