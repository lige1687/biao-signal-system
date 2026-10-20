"""Render dependency-free SVG net-value and drawdown charts."""
from pathlib import Path
import html
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results/fee-10bp"
OUT = HERE / "charts"
OUT.mkdir(exist_ok=True)
COLORS = {"W0":"#2563eb","W1":"#f97316","W2":"#a855f7","W3":"#059669","B0":"#111827","B1":"#dc2626","B2":"#6b7280"}


def path_points(x, y, left, top, width, height, ymin, ymax):
    xx = left + (x - x.min()) / (x.max() - x.min()) * width
    yy = top + (ymax - y) / (ymax - ymin) * height
    return " ".join(f"{a:.1f},{b:.1f}" for a,b in zip(xx,yy))


def render(symbol, source, label):
    methods=["W0","W1","W2","W3","B0","B1","B2"]
    data={}
    for m in methods:
        src=source if m.startswith("W") else "baseline"
        p=RESULTS/f"{symbol}-{src}-{m}-10bp-daily.parquet"
        d=pd.read_parquet(p)
        d=d[d.is_quote_day].copy()
        eq=d.equity.to_numpy()/1_000_000
        dd=eq/np.maximum.accumulate(np.r_[1.0,eq])[-len(eq):]-1
        data[m]=(d.date,eq,dd)
    W,H=1200,800; left,right=90,30; pw=W-left-right; ph=250
    ymax=max(v[1].max() for v in data.values())*1.04; ymin=min(v[1].min() for v in data.values())*.96
    ddmin=min(v[2].min() for v in data.values())*1.05
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<rect width="100%" height="100%" fill="white"/>',
       f'<text x="{left}" y="36" font-size="24" font-family="sans-serif" font-weight="700">{html.escape(symbol)} · {html.escape(label)}（0.1% 单边成本）</text>',
       f'<text x="{left}" y="68" font-size="16" font-family="sans-serif" fill="#374151">完整账户金额（百万元）</text>']
    for frac in np.linspace(0,1,5):
        y=90+ph*frac; val=ymax-(ymax-ymin)*frac
        s += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}" stroke="#e5e7eb"/>',f'<text x="{left-10}" y="{y+5:.1f}" text-anchor="end" font-size="12" font-family="sans-serif" fill="#6b7280">{val:.1f}</text>']
    for m,(dates,eq,dd) in data.items():
        x=dates.astype('int64').to_numpy(float)
        s.append(f'<polyline fill="none" stroke="{COLORS[m]}" stroke-width="2" points="{path_points(x,eq,left,90,pw,ph,ymin,ymax)}"/>')
    s.append(f'<text x="{left}" y="390" font-size="16" font-family="sans-serif" fill="#374151">从此前高点回落</text>')
    for frac in np.linspace(0,1,5):
        y=410+ph*frac; val=0+(ddmin-0)*frac
        s += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}" stroke="#e5e7eb"/>',f'<text x="{left-10}" y="{y+5:.1f}" text-anchor="end" font-size="12" font-family="sans-serif" fill="#6b7280">{val:.0%}</text>']
    for m,(dates,eq,dd) in data.items():
        x=dates.astype('int64').to_numpy(float)
        s.append(f'<polyline fill="none" stroke="{COLORS[m]}" stroke-width="2" points="{path_points(x,dd,left,410,pw,ph,ddmin,0)}"/>')
    for i,m in enumerate(methods):
        row=i//4; col=i%4; lx=left+col*250; ly=710+row*28
        text={"W0":"W0 原三档","W1":"W1 B50转强","W2":"W2 B200转强","W3":"W3 价格确认","B0":"B0 持有","B1":"B1 价格200日","B2":"B2 半仓"}[m]
        s += [f'<line x1="{lx}" y1="{ly}" x2="{lx+24}" y2="{ly}" stroke="{COLORS[m]}" stroke-width="3"/>',f'<text x="{lx+30}" y="{ly+5}" font-size="13" font-family="sans-serif">{text}</text>']
    s += [f'<text x="{left}" y="778" font-size="12" font-family="sans-serif" fill="#6b7280">区间：2018-07-05 至 2026-06-30；2026 仅上半年。金额包含等待期现金、费用和公司行动。</text>','</svg>']
    (OUT/f"{symbol}-{source}-netvalue-drawdown.svg").write_text("\n".join(s))


render("510300","all_a","全 A 宽度")
render("510300","csi300","沪深300历史成分宽度")
render("159915","all_a","全 A 宽度")
