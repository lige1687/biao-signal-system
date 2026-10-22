#!/usr/bin/env python3
"""Render already-published US French factor returns as cumulative NAV paths."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTRACT = Path(__file__).with_name("contract.json")
OUT = ROOT / "web/public/research/us-factor-reference-curves-20261022"
RECEIPT = Path(__file__).with_name("render-receipt.json")
PERIODS = ("primary", "early", "recent_public")
FACTORS = ("BM", "OP", "MOM")
SIZES = ("small", "big")
GROUPS = ("L", "N", "H", "B")
FACTOR_LABELS = {"BM": "账面价值", "OP": "经营盈利", "MOM": "过去涨幅"}
SIZE_LABELS = {"big": "大规模（高于NYSE中位数）", "small": "小规模（低于NYSE中位数）"}
PERIOD_LABELS = {"primary": "主要十年｜2015-01—2024-12", "early": "较早背景｜1963-07—2014-12", "recent_public": "最新补充｜2025-01—2026-08"}
GROUP_LABELS = {"L": "低分组 L", "N": "中间组 N", "H": "高分组 H", "B": "三组平均 B"}
COLORS = {"L": "#3b82f6", "N": "#10b981", "H": "#e24a3b", "B": "#7c3aed"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def close(a: float, b: float) -> float:
    return abs(a - b)


def metrics(points: list[dict]) -> tuple[dict, dict]:
    nav = {g: 100.0 for g in GROUPS}
    peaks = {g: 100.0 for g in GROUPS}
    dd = {g: 0.0 for g in GROUPS}
    for p in points:
        for g in GROUPS:
            nav[g] *= 1.0 + p["returns"][g]
            peaks[g] = max(peaks[g], nav[g])
            dd[g] = min(dd[g], nav[g] / peaks[g] - 1.0)
    return nav, dd


def build_html() -> str:
    return r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股公开因子组合累计曲线</title>
<style>
:root{color-scheme:light;--ink:#172033;--muted:#657187;--line:#e3e8ef;--paper:#fff;--wash:#f6f8fb;--blue:#3b82f6}
*{box-sizing:border-box}body{margin:0;background:var(--wash);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1160px;margin:0 auto;padding:28px 24px 56px}.eyebrow{color:#415b84;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
h1{font-size:clamp(25px,4vw,36px);line-height:1.15;margin:8px 0 10px}.lead{font-size:16px;color:#36445b;max-width:900px;margin:0 0 22px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 4px 16px #1c2f4a08}
.controls{display:flex;gap:14px;flex-wrap:wrap;align-items:end}.control{display:grid;gap:5px;min-width:170px}label{font-size:12px;color:var(--muted);font-weight:650}select{height:40px;padding:0 12px;border:1px solid #cbd4e1;border-radius:8px;background:white;color:var(--ink);font:inherit}
.meta{color:var(--muted);font-size:13px;margin:12px 0 5px}.chart-wrap{position:relative;margin-top:6px}svg{display:block;width:100%;height:auto;overflow:visible}.grid{stroke:#e5eaf1;stroke-width:1}.axis{fill:#68758a;font-size:12px}.curve{fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.legend{display:flex;gap:18px;flex-wrap:wrap;margin:6px 0 2px}.legend span{font-size:13px;color:#45536a;display:flex;gap:7px;align-items:center}.swatch{width:12px;height:3px;border-radius:3px;display:inline-block}.tip{position:absolute;display:none;z-index:2;padding:10px 12px;background:#16243a;color:white;border-radius:8px;font-size:12px;line-height:1.6;pointer-events:none;box-shadow:0 6px 20px #10203a30;white-space:nowrap}.summary{margin-top:20px;overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:right;padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#5a6880;font-weight:650;background:#fafbfd}.delta{margin-top:14px;padding:12px 14px;background:#f4f6fa;border-radius:9px;font-size:13px;line-height:1.7}.notes{margin-top:20px;color:#5b687d;font-size:13px}.notes p{margin:8px 0}.pill{display:inline-block;padding:3px 8px;border-radius:999px;background:#eef2f8;color:#52617a;font-size:12px;margin-right:5px}
@media(max-width:650px){main{padding:20px 12px 36px}.card{padding:14px}.control{flex:1;min-width:140px}.axis{font-size:10px}th,td{padding:8px 6px}}
</style></head><body><main>
<div class="eyebrow">存量公开数据展示 · French 202608 / CRSP CIZ</div>
<h1>美股公开因子组合累计曲线</h1>
<p class="lead">展示三种公开分组中，低分组、中间组、高分组和三组平均的月度收益连乘路径。只呈现已有组合结果，不代表逐股选股或个人账户回测。</p>
<section class="card">
<div class="controls">
<div class="control"><label for="factor">公开分组</label><select id="factor"><option value="OP">经营盈利</option><option value="BM">账面价值</option><option value="MOM">过去涨幅</option></select></div>
<div class="control"><label for="size">规模</label><select id="size"><option value="big">大规模（高于NYSE中位数）</option><option value="small">小规模（低于NYSE中位数）</option></select></div>
<div class="control"><label for="period">时期</label><select id="period"><option value="primary">主要十年｜2015-01—2024-12</option><option value="early">较早背景｜1963-07—2014-12</option><option value="recent_public">最新补充｜2025-01—2026-08</option></select></div>
</div>
<div id="periodMeta" class="meta"></div>
<div class="chart-wrap"><svg id="chart" viewBox="0 0 1000 440" role="img" aria-label="四个公开组合的月末累计净值曲线"></svg><div id="tip" class="tip"></div></div>
<div id="legend" class="legend"></div>
<div id="table" class="summary"></div>
<div id="contrasts" class="delta"></div>
</section>
<section class="notes">
<p><span class="pill">基准 B</span>每月资金各分三分之一给 L、N、H 三组；每组内部按市值加权。它不是大盘指数，也不是等权买入每只股票。</p>
<p><b>范围：</b>美国公开股票组合，美元计价，未扣个人交易费用；没有逐股历史名单、真实成交、现金配置或ETF跟踪资料。曲线从该时期开始前的100起算。</p>
<p><b>风险：</b>回撤只按月末净值计算，不包含月内更深跌幅。股票数为每月三组数量合计及高分组范围，不能据此推断持仓集中度。</p>
<p><b>时间：</b>所有历史都已公开并被研究者看过；较早时期是背景，主要十年是固定比较区间，最新20个月是短期补充。它们都不是新的未见验证。因子各自的涨跌月份也不是共同牛市、熊市或震荡定义。</p>
<p><b>解读：</b>收益差、少亏和少赚是同一组历史数据的不同描述，不能相加成额外收益。累计曲线为旧月收益的连乘展示，不是新回测或交易建议。</p>
</section></main>
<script>
fetch('./data.json').then(r=>{if(!r.ok)throw new Error('数据读取失败');return r.json()}).then(DATA=>{
const f=document.querySelector('#factor'),s=document.querySelector('#size'),p=document.querySelector('#period'),svg=document.querySelector('#chart'),tip=document.querySelector('#tip');
const labels={L:'低分组 L',N:'中间组 N',H:'高分组 H',B:'三组平均 B'},colors={L:'#3b82f6',N:'#10b981',H:'#e24a3b',B:'#7c3aed'};
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function pct(x,d=2){return (x*100).toFixed(d)+'%'} function pp(x){return (x*100).toFixed(3)+'个百分点'}
function render(){const key=[f.value,s.value,p.value].join('|'),d=DATA.datasets[key],rows=d.points,n=rows.length,W=1000,H=440,m={l:72,r:22,t:24,b:48},pw=W-m.l-m.r,ph=H-m.t-m.b;
 const vals=rows.flatMap(x=>['L','N','H','B'].map(g=>x.nav[g])),lo=Math.min(...vals),hi=Math.max(...vals),pad=(hi-lo)*.08||5,y0=Math.floor((lo-pad)/10)*10,y1=Math.ceil((hi+pad)/10)*10;
 const X=i=>m.l+(n<2?0:i/(n-1))*pw,Y=v=>m.t+(y1-v)/(y1-y0)*ph;
 const rawStep=(y1-y0)/7,mag=Math.pow(10,Math.floor(Math.log10(rawStep))),unit=rawStep/mag,step=(unit<=1?1:unit<=2?2:unit<=5?5:10)*mag;let out='';for(let v=Math.ceil(y0/step)*step;v<=y1;v+=step){out+=`<line class="grid" x1="${m.l}" y1="${Y(v)}" x2="${W-m.r}" y2="${Y(v)}"/><text class="axis" x="${m.l-10}" y="${Y(v)+4}" text-anchor="end">${v.toFixed(0)}</text>`}
 const ticks=Array.from({length:7},(_,i)=>Math.round(i*(n-1)/6)).filter((v,i,a)=>a.indexOf(v)===i);
 ticks.forEach(i=>out+=`<text class="axis" x="${X(i)}" y="${H-14}" text-anchor="${i===0?'start':i===n-1?'end':'middle'}">${rows[i].month}</text>`);
 for(const g of ['L','N','H','B']){let pts=rows.map((r,i)=>`${X(i).toFixed(2)},${Y(r.nav[g]).toFixed(2)}`).join(' ');out+=`<polyline class="curve" stroke="${colors[g]}" points="${pts}"/>`}
 out+=`<line class="grid" x1="${m.l}" y1="${m.t}" x2="${m.l}" y2="${H-m.b}"/>`;
 svg.innerHTML=out+`<rect id="hover" x="${m.l}" y="${m.t}" width="${pw}" height="${ph}" fill="transparent"/>`;
 document.querySelector('#hover').addEventListener('mousemove',e=>{const b=svg.getBoundingClientRect(),x=(e.clientX-b.left)/b.width*W,idx=Math.max(0,Math.min(n-1,Math.round((x-m.l)/pw*(n-1)))),r=rows[idx];tip.innerHTML=`<b>${esc(r.month)}${r.initial?'｜期初（不计入月数）':''}</b><br>${['L','N','H','B'].map(g=>`${labels[g]}：${r.nav[g].toFixed(2)}`).join('<br>')}`;tip.style.display='block';tip.style.left=Math.min(e.offsetX+16,b.width-175)+'px';tip.style.top=Math.max(5,e.offsetY-18)+'px'});
 document.querySelector('#hover').addEventListener('mouseleave',()=>tip.style.display='none');
 document.querySelector('#legend').innerHTML=['L','N','H','B'].map(g=>`<span><i class="swatch" style="background:${colors[g]}"></i>${labels[g]}</span>`).join('');
 document.querySelector('#periodMeta').textContent=`${d.label}｜${d.months}个月｜期初净值 100（${rows[0].month}月末）｜收益月份 ${d.first} 至 ${d.last}｜三组总股票数 ${d.firms.total.min}–${d.firms.total.max}，高分组 ${d.firms.H.min}–${d.firms.H.max}`;
 document.querySelector('#table').innerHTML=`<table><thead><tr><th>组别</th><th>期间累计涨跌（旧统计）</th><th>月均收益</th><th>月末最大跌幅（旧统计）</th><th>最差月份</th></tr></thead><tbody>${['L','N','H','B'].map(g=>{const z=d.old.performance[g];return `<tr><td>${labels[g]}</td><td>${pct(z.growth)}</td><td>${pct(z.mean)}</td><td>${pct(z.drawdown)}</td><td>${pct(z.worst)}</td></tr>`}).join('')}</tbody></table>`;
 const c=d.old.contrasts;document.querySelector('#contrasts').innerHTML=`<b>高分组的旧比较（每月差额）：</b> H−B ${pp(c['H-B'].mean)}；H−中间组 ${pp(c['H-N'].mean)}。<br><b>相对三组平均 B 的下跌/上涨月份差额：</b>下跌月 ${pp(c['H-B'].down)}，上涨月 ${pp(c['H-B'].up)}。正数表示高分组平均多赚或少亏，负数表示少赚或多亏；这些月份按该因子自己的 B 划分。`;
} [f,s,p].forEach(x=>x.addEventListener('change',render));render();
}).catch(e=>{document.querySelector('#periodMeta').textContent=e.message});
</script></body></html>'''


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    src = contract["sources"]
    monthly_path = Path(src["monthly"]["path"])
    result_path = Path(src["result"]["path"])
    input_hashes = {"monthly": sha(monthly_path), "result": sha(result_path)}
    for k, digest in input_hashes.items():
        if digest != src[k]["sha256"]:
            raise SystemExit(f"source SHA mismatch: {k}")
    old = json.loads(result_path.read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    with monthly_path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row["source"], row["size"], row["period"])
            rec = {
                "month": row["month"],
                "returns": {g: float(row[g]) for g in GROUPS},
                "firms": {g: int(row[f"Nfirm_{g}"]) for g in ("L", "N", "H")},
            }
            grouped[key].append(rec)
    expected = contract["periods"]
    datasets: dict[str, dict] = {}
    max_error = 0.0
    checked_paths = 0
    for factor in FACTORS:
        for size in SIZES:
            for period in PERIODS:
                key = (factor, size, period)
                rows = grouped.get(key, [])
                first, last = expected[period]
                want_n = 120 if period == "primary" else 618 if period == "early" else 20
                if len(rows) != want_n:
                    raise SystemExit(f"wrong months for {key}: {len(rows)} != {want_n}")
                months = [r["month"] for r in rows]
                if months[0] != first or months[-1] != last or len(set(months)) != want_n:
                    raise SystemExit(f"month endpoints/duplicates fail for {key}")
                # Month continuity check uses only the existing period axis.
                for a, b in zip(months, months[1:]):
                    y1, m1 = map(int, a.split("-")); y2, m2 = map(int, b.split("-"))
                    if (y2 - y1) * 12 + m2 - m1 != 1:
                        raise SystemExit(f"monthly gap for {key}: {a} -> {b}")
                nav, dd = metrics(rows)
                stats = old["statistics"][factor][period][size]
                for g in GROUPS:
                    growth_error = close(nav[g] / 100.0 - 1.0, stats["performance"][g]["monthly_compounded_path_growth"])
                    dd_error = close(dd[g], stats["performance"][g]["monthly_compounded_path_drawdown"])
                    max_error = max(max_error, growth_error, dd_error)
                    checked_paths += 1
                    if growth_error > 1e-10 or dd_error > 1e-10:
                        raise SystemExit(f"old statistic mismatch for {key}/{g}: growth={growth_error}, drawdown={dd_error}")
                firm_totals = [sum(r["firms"].values()) for r in rows]
                h_counts = [r["firms"]["H"] for r in rows]
                # Store NAV directly using the same one-pass compounding used for validation.
                cur = {g: 100.0 for g in GROUPS}
                y0, m0 = map(int, first.split("-"))
                prior_month = f"{y0 - 1}-12" if m0 == 1 else f"{y0}-{m0 - 1:02d}"
                points = [{"month": prior_month, "nav": {g: 100.0 for g in GROUPS}, "initial": True}]
                for r in rows:
                    for g in GROUPS:
                        cur[g] *= 1.0 + r["returns"][g]
                    points.append({"month": r["month"], "nav": dict(cur)})
                contrasts = stats["contrasts"]
                datasets["|".join(key)] = {
                    "label": PERIOD_LABELS[period], "first": first, "last": last, "months": want_n,
                    "firms": {"total": {"min": min(firm_totals), "max": max(firm_totals)}, "H": {"min": min(h_counts), "max": max(h_counts)}},
                    "points": points,
                    "old": {
                        "performance": {g: {"growth": stats["performance"][g]["monthly_compounded_path_growth"], "drawdown": stats["performance"][g]["monthly_compounded_path_drawdown"], "mean": stats["performance"][g]["mean"], "worst": stats["performance"][g]["worst_month"]} for g in GROUPS},
                        "contrasts": {"H-B": {"mean": contrasts["H-B"]["mean_paired_difference"], "down": contrasts["H-B"]["B_negative_mean_difference"], "up": contrasts["H-B"]["B_positive_mean_difference"]}, "H-N": {"mean": contrasts["H-N"]["mean_paired_difference"]}},
                    },
                }
    if len(grouped) != 18 or len(datasets) != 18 or checked_paths != 72:
        raise SystemExit(f"expected18 datasets/72 paths, got {len(grouped)}/{len(datasets)}/{checked_paths}")
    payload = {
        "schema": "us-published-factor-curves-display/1",
        "created_from_existing_returns_only": True,
        "factor_labels": FACTOR_LABELS,
        "size_labels": SIZE_LABELS,
        "period_labels": PERIOD_LABELS,
        "group_labels": GROUP_LABELS,
        "source_hashes": input_hashes,
        "datasets": datasets,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    data_path, html_path = OUT / "data.json", OUT / "index.html"
    data_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    html_path.write_text(build_html(), encoding="utf-8")
    sizes = {str(p): p.stat().st_size for p in (data_path, html_path)}
    if sum(sizes.values()) >= int(contract["small_display_estimate_bytes"]):
        raise SystemExit(f"display too large: {sum(sizes.values())} bytes")
    receipt = {
        "schema": "us-factor-reference-curves-render-receipt/1",
        "command": "python3 docs/experiments/raw/us-factor-reference-curves-2026-10-22/render.py",
        "inputs": {k: {"path": src[k]["path"], "sha256": input_hashes[k]} for k in input_hashes},
        "counts": {"input_rows": sum(map(len, grouped.values())), "datasets": len(datasets), "group_paths_checked": checked_paths},
        "validation": {"period_endpoints_months_unique_and_contiguous": True, "old_growth_and_month_end_drawdown_paths_match": True, "tolerance": 1e-10, "max_absolute_difference": max_error, "new_returns_or_condition_effects_calculated": False},
        "outputs": {str(p): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in (data_path, html_path)},
        "total_output_bytes": sum(sizes.values()),
        "browser_visual_verification": "not performed; root owner to verify",
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
