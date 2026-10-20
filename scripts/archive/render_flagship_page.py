#!/usr/bin/env python3
"""旗舰组合总展示页（回测页面内的汇总展示）。

产出：web/public/reports/flagship-2026-09-01.html
内容：三大旗舰组合（两只版/B9+虹吸/ETF可交易版）各自的净值曲线、
买卖点标注、仓位条、调仓明细 + 系统思路 + 实验依据 + 后续预测。
复现：PYTHONHASHSEED=0 python3 scripts/render_flagship_page.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_ashare_axes import siphon_daily  # noqa: E402
from run_bform_mini import load_series  # noqa: E402
from run_m5_walkforward import tier_for  # noqa: E402

OUT = REPO / "web/public/reports/flagship-2026-09-01.html"
E = lambda c: f"etf_breadth/{c}_close.parquet"  # noqa: E731
COMBOS = {
    "两只版·创业板×三档+虹吸 + 纳指持有": {
        "legs": [("创业板指", "siphon_detector/cyb_399006_close.parquet", "A"),
                 ("纳斯达克", "portfolio_split/ixic_close.parquet", "H")],
        "start": "2010-06-01", "note": "16年全周期旗舰 · 事后选腿折让后预期 11-12%"},
    "B9 九标的 × 三档+虹吸": {
        "legs": [(k, v, "A") for k, v in {**rps.GATED, **rps.TREND}.items()],
        "start": "2015-06-16", "note": "唯一全套认证 · 安慰剂100分位 · 预期 6-10%"},
    "ETF可交易版·新能车+传媒+证券×三档+虹吸 + 纳指ETF": {
        "legs": [("新能车ETF", E("sh515030"), "A"), ("传媒ETF", E("sh512980"), "A"),
                 ("证券ETF", E("sh512880"), "A"), ("纳指ETF", E("sh513100"), "H")],
        "start": "2020-03-04", "note": "全部可交易标的 · 短窗6.5年 · 预期 7-13%"},
}


def combo_section(title, cfg):
    legs, start = cfg["legs"], cfg["start"]
    frames = {n: load_series(rel) for n, rel, _ in legs}
    px = pd.DataFrame(frames)
    a_names = [n for n, _, k in legs if k == "A"]
    if any(k == "H" for _, _, k in legs):
        cn = px[a_names[0]].dropna().index
        px = px.reindex(cn).ffill()
    px = px[(px.index >= pd.Timestamp(start)) & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
    b200 = rps.load_breadth()
    t0 = tier_for(b200, px.index, 43.3, 56.7)
    sip = siphon_daily(px.index)
    bud = t0.copy()
    bud[(t0 <= 0.001) & sip] = 0.5
    expo = pd.DataFrame(1.0, index=px.index, columns=px.columns)
    for n in a_names:
        expo[n] = bud
    expo = expo / px.shape[1]
    ones = pd.DataFrame(1.0, index=px.index, columns=px.columns) / px.shape[1]
    from run_bform_dynamic import simulate_direct
    eq = simulate_direct(px, expo)
    hold = simulate_direct(px, ones)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    ann = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    dd = float((eq / eq.cummax() - 1).min())
    mh = (hold.iloc[-1] / hold.iloc[0]) ** (1 / yrs) - 1
    ddh = float((hold / hold.cummax() - 1).min())
    # 事件
    a_idx_px = px[a_names].mean(axis=1)
    a_idx_px = a_idx_px / a_idx_px.iloc[0]
    ch = bud.diff().fillna(0)
    events = []
    for d in px.index[ch != 0]:
        i = px.index.get_loc(d)
        prev = bud.iloc[i - 1] if i else 1.0
        cur = bud.iloc[i]
        events.append({"date": d, "act": ("▲ 买入" + ("（满仓）" if cur == 1.0 else "（半仓）")) if cur > prev
                       else ("▼ 卖出" + ("（清仓）" if cur == 0.0 else "（减半）")),
                       "price": float(a_idx_px.iloc[i] * 100)})
    dates = px.index
    def chart(w=960, h=300):
        pad = {"l": 56, "r": 14, "t": 26, "b": 26}
        s1, s2 = eq / eq.iloc[0], hold / hold.iloc[0]
        lo, hi = np.log10(min(s1.min(), s2.min())), np.log10(max(s1.max(), s2.max()))
        x0, x1 = dates[0].timestamp(), dates[-1].timestamp()
        X = lambda d: pad["l"] + (d.timestamp() - x0) / (x1 - x0) * (w - pad["l"] - pad["r"])
        Y = lambda v: h - pad["b"] - (np.log10(v) - lo) / (hi - lo) * (h - pad["t"] - pad["b"])
        parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0b1220;border-radius:10px">',
                 f'<text x="{pad["l"]}" y="16" fill="#94a3b8" font-size="12">净值（对数轴）：组合 vs 等权持有</text>']
        for f in (0, 0.5, 1.0):
            t = lo + f * (hi - lo)
            y = h - pad["b"] - f * (h - pad["t"] - pad["b"])
            parts.append(f'<line x1="{pad["l"]}" y1="{y:.0f}" x2="{w-14}" y2="{y:.0f}" stroke="#1e293b"/>')
            parts.append(f'<text x="{pad["l"]-6}" y="{y+4:.0f}" fill="#64748b" font-size="10" text-anchor="end">{10**t:.1f}x</text>')
        for yr in range(dates[0].year + 1, dates[-1].year + 1, 2):
            d = pd.Timestamp(f"{yr}-01-01")
            if x0 < d.timestamp() < x1:
                parts.append(f'<line x1="{X(d):.0f}" y1="{pad["t"]}" x2="{X(d):.0f}" y2="{h-pad["b"]}" stroke="#1e293b"/>')
                parts.append(f'<text x="{X(d):.0f}" y="{h-8}" fill="#64748b" font-size="10" text-anchor="middle">{yr}</text>')
        for s, c, wd, nm in [(s2, "#64748b", 1.3, "等权持有"), (s1, "#34d399", 2.2, "组合")]:
            step = max(1, len(s) // 450)
            pts = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in list(s.items())[::step])
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="{wd}"/>')
        for ev in events:
            x, y = X(ev["date"]), Y(ev["price"] / 100 * s1.iloc[dates.get_loc(ev["date"])] / (s1.iloc[dates.get_loc(ev["date"])] / 1))
            y = Y(float(s1.iloc[dates.get_loc(ev["date"])]))
            buy = "▲" in ev["act"]
            c = "#34d399" if buy else "#f87171"
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="{c}" stroke="#0b1220"/>')
        parts.append(f'<rect x="{w-320}" y="6" width="10" height="3" fill="#34d399"/><text x="{w-306}" y="11" fill="#cbd5e1" font-size="11">组合</text>')
        parts.append(f'<rect x="{pad["l"]+70}" y="6" width="10" height="3" fill="#64748b"/><text x="{pad["l"]+84}" y="11" fill="#cbd5e1" font-size="11">等权持有</text>')
        parts.append(f'<circle cx="{pad["l"]+170}" cy="8" r="3" fill="#34d399"/><text x="{pad["l"]+178}" y="11" fill="#cbd5e1" font-size="11">▲▼ 调仓点</text>')
        parts.append("</svg>")
        return "".join(parts)
    def strip(w=960, h=80):
        cmap = {1.0: "#34d399", 0.5: "#fbbf24", 0.0: "#ef4444"}
        x0, x1 = dates[0].timestamp(), dates[-1].timestamp()
        segs, cur, st = [], bud.iloc[0], dates[0]
        for d, v in list(bud.items())[1:]:
            if v != cur:
                segs.append((st, d, cur)); cur, st = v, d
        segs.append((st, dates[-1], cur))
        X = lambda d: 10 + (d.timestamp() - x0) / (x1 - x0) * (w - 20)
        parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0b1220;border-radius:10px">',
                 '<text x="12" y="14" fill="#94a3b8" font-size="11">仓位（绿=满 黄=半 红=空）</text>']
        for s_, e_, v in segs:
            parts.append(f'<rect x="{X(s_):.1f}" y="22" width="{max(X(e_)-X(s_),1):.1f}" height="34" fill="{cmap.get(v,"#64748b")}" opacity="0.9" rx="2"/>')
        parts.append("</svg>")
        return "".join(parts)
    ev_rows = "".join(
        f"<tr><td>{e['date'].date()}</td><td class=\"{'ok' if '▲' in e['act'] else 'bad'}\">{e['act']}</td><td>{e['price']:.0f}</td></tr>"
        for e in list(events)[::-1][:18])
    return f"""
<h2>▸ {title} <span class="muted">{cfg['note']}</span></h2>
<div class="kpis"><div class="kpi"><span class="muted">组合年化</span><b class="g">{ann*100:.1f}%</b><span class="muted">持有 {mh*100:.1f}%</span></div>
<div class="kpi"><span class="muted">最大回撤</span><b class="g">{dd*100:.1f}%</b><span class="muted">持有 {ddh*100:.1f}%</span></div>
<div class="kpi"><span class="muted">Calmar</span><b class="b">{(ann/abs(dd) if dd else 0):.3f}</b><span class="muted">持有 {(mh/abs(ddh) if ddh else 0):.3f}</span></div>
<div class="kpi"><span class="muted">调仓 {len(events)} 次 / {yrs:.1f} 年</span><b class="y">≈{yrs*12/max(len(events),1):.1f}个月/次</b><span class="muted">当前 {'满仓' if bud.iloc[-1]==1 else ('半仓' if bud.iloc[-1]==0.5 else '空仓')}</span></div></div>
{chart()}<div style="height:8px"></div>{strip()}
<details style="margin-top:8px"><summary class="muted" style="cursor:pointer">调仓明细（最近 18 条）</summary>
<table style="margin-top:6px"><tr><th>日期</th><th>动作</th><th>A腿篮子点位</th></tr>{ev_rows}</table></details>"""


def main() -> None:
    sections = "".join(combo_section(k, v) for k, v in COMBOS.items())
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>旗舰组合总览 · 回测展示</title><style>
body{{background:#0f172a;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;margin:0;padding:28px}}
.wrap{{max-width:1000px;margin:0 auto}} h1{{font-size:24px;margin:0 0 4px}}
h2{{font-size:17px;color:#7dd3fc;margin:30px 0 12px;border-left:3px solid #38bdf8;padding-left:10px}}
.muted{{color:#94a3b8;font-size:12.5px;font-weight:400}} .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}}
.kpi{{background:#1e293b;border-radius:12px;padding:12px}} .kpi b{{font-size:20px;display:block}}
.g{{color:#34d399}} .b{{color:#38bdf8}} .y{{color:#fbbf24}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;background:#1e293b;border-radius:10px;overflow:hidden}}
th,td{{padding:6px 10px;border-bottom:1px solid #334155}} th{{color:#94a3b8;background:#0b1220}}
td.ok{{color:#34d399;font-weight:600}} td.bad{{color:#f87171;font-weight:600}}</style></head><body><div class="wrap">
<h1>旗舰组合总览 · 曲线 / 买卖点 / 净值</h1>
<div class="muted">宽度 B200 三档(43.3/56.7) + 融资余额虹吸 + 美股持有腿 ｜ 周频信号次日执行 10bp ｜ 2026-09-01 生成（PYTHONHASHSEED=0 可复现）</div>
{sections}
<h2>▸ 系统思路与实验依据</h2>
<table><tr><th>层</th><th>结论</th><th>关键证据</th></tr>
<tr><td>面层·宽度预算</td><td>宽度三档×组合，不是开关/判别器</td><td>安慰剂100分位、起点31/31、高原24/24、WF OOS +4.6pp</td></tr>
<tr><td>新轴·融资虹吸</td><td>杠杆资金增速分位≥90%持续4周→空档改半仓</td><td>双池全过、14/14行业无害、邻域21/27、科技牛窗+10~13pp、2015考场回撤仅−14%</td></tr>
<tr><td>持有腿</td><td>美股/黄金/芯片类裸持有</td><td>逆势闸7.3%、价格闸5.3%等五重证伪</td></tr>
<tr><td>点层·LEI</td><td>个股分账独立、1%风险</td><td>ΣR+831/1681笔、空仓档入场质量反而最高（三重证据）</td></tr>
<tr><td>胜率表</td><td>最优入场=多头排列回踩MA50（75%）；复苏格68%；破年线37%勿接刀</td><td>创业板16年逐日条件统计</td></tr></table>
<h2>▸ 后续预判（打分卡 2026-09→2027-08 的预期，预先写死）</h2>
<table><tr><th>项目</th><th>我的预判</th></tr>
<tr><td>两只版 12 个月</td><td>年化 8-16%（中位 11%），跑输等权持有的概率 30-35%（科技牛延续情形）；回撤 −15~−25%</td></tr>
<tr><td>B9+虹吸 12 个月</td><td>年化 6-11%，回撤 −20~−30%</td></tr>
<tr><td>ETF可交易版</td><td>年化 7-13%（短窗折让）</td></tr>
<tr><td>虹吸首次实盘触发</td><td>若 B200 回到 56.7 上方且杠杆资金再加速，观察豁免是否兑现（当前 OFF）</td></tr>
<tr><td>失效判据</td><td>任一组合滚动 3 年跑输等权持有 8pp → 降级复评</td></tr>
<tr><td>待修事项</td><td>precompute 日更（红旗）、F2 组合构建 bug、双≤20 定投形态重试、虹吸版 WF+安慰剂</td></tr></table>
<div class="muted" style="margin-top:12px">一切结论建议级；转正通道 = 终审 + 打分卡实测 + 拍板。详细报告链见 docs/experiments/ 与 docs/SYSTEM-VALUE-SUMMARY-2026-08-31.md。</div>
</div></body></html>"""
    OUT.write_text(html)
    print("written:", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
