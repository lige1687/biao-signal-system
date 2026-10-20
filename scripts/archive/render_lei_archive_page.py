#!/usr/bin/env python3
"""LEI组 统一归档报告生成器：主系统（信号×仓位×终审×信息源）全档案。

产出：web/public/reports/lei-zuhe-zhongshen-2026-09-01.html
内容：四组合 KPI 卡（七项齐全）→ 净值曲线（对数轴 SVG）→ 宽度档位带
→ 明细表（闸演化/终审/信息源面板/按标的/证伪清单）→ 复现命令与
已知问题清单。单文件零外部依赖，离线双击可开。
复现：PYTHONHASHSEED=0 python3 scripts/render_lei_archive_page.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)

RAW = REPO / "docs/experiments/raw"
H80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))


def load_breadth() -> pd.DataFrame:
    """研究史 33 年（独立于 live 管线，见 run_breadth_overlay 同名函数）。"""
    full = Path.home() / (
        ".lei_signal_lab/cache/a_share_ma_breadth_full_history.json")
    df = pd.DataFrame(json.loads(full.read_text()))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()[["ma50_pct", "ma200_pct"]]


def sim_weighted(trades, weight, cap_fn, initial):
    """按标的加权的事件日重放（研究拷贝，对齐 portfolio.simulate：
    先平后开、当日开当日平立即结算、回撤降级 0.8/10%、并发 10 按 cap 缩；
    预算 = equity×1%×factor×cap×weight）。出处 run_symbol_tilt.py。"""
    by_entry: dict[str, list] = {}
    for t in trades:
        t = dict(t)
        t["pool"] = t.get("pool", "main")
        by_entry.setdefault(t["entry_date"], []).append(t)
    equity, peak = initial, initial
    open_pos: dict[str, dict] = {}
    curve, taken = [], []
    days = sorted(set(by_entry) | {t["exit_date"] for t in trades})
    for day in days:
        for sym in sorted(open_pos):
            pos = open_pos[sym]
            if pos["t"]["exit_date"] == day:
                equity += pos["budget"] * pos["t"]["r_net"]
                peak = max(peak, equity)
                taken.append({"symbol": sym, "r_net": pos["t"]["r_net"],
                              "budget": round(pos["budget"], 2)})
                del open_pos[sym]
        day_cap = min(1.0, max(0.0, cap_fn(day))) if cap_fn else 1.0
        for t in by_entry.get(day, []):
            if t["symbol"] in open_pos or equity <= 0:
                continue
            if len(open_pos) >= max(1, math.ceil(10 * day_cap)):
                continue
            w = weight(t["symbol"], day)
            dd = (peak - equity) / peak if peak > 0 else 0
            factor = 0.8 ** int(dd / 0.10)
            budget = equity * 0.01 * factor * day_cap * w
            if budget <= 0:
                continue
            if t["exit_date"] == day:
                equity += budget * t["r_net"]
                peak = max(peak, equity)
                taken.append({"symbol": t["symbol"], "r_net": t["r_net"],
                              "budget": round(budget, 2)})
            else:
                open_pos[t["symbol"]] = {"t": t, "budget": budget}
        curve.append({"date": day, "equity": round(equity, 2)})
    return {"final": equity, "curve": curve, "taken": taken}


def merge_curves(a, b):
    """两腿曲线按日合并（出处 run_symbol_tilt.py）。"""
    ca = {p["date"]: p["equity"] for p in a["curve"]}
    cb = {p["date"]: p["equity"] for p in b["curve"]}
    out, last = [], [next(iter(ca.values()), 0), next(iter(cb.values()), 0)]
    for d in sorted(set(ca) | set(cb)):
        last = [ca.get(d, last[0]), cb.get(d, last[1])]
        out.append({"date": d, "equity": sum(last)})
    by_year, prev = {}, 1_000_000.0
    for y in sorted({p["date"][:4] for p in out}):
        win = [p for p in out if p["date"][:4] == y]
        pk, mdd = prev, 0.0
        for p in win:
            pk = max(pk, p["equity"])
            if pk > 0:
                mdd = max(mdd, (pk - p["equity"]) / pk)
        by_year[y] = round(mdd * 100, 3)
        prev = win[-1]["equity"]
    return {"final": out[-1]["equity"], "curve": out, "by_year": by_year,
            "taken": a["taken"] + b["taken"]}

POOL = Path.home() / ".lei_signal_lab/backtest_pool"
RUN_FILES = {  # engine 断链时绕开 runner/service，直读缓存 run JSON
    "A": RAW / "portfolio/A_ETF_cm05_shrink.json",
    "B'": RAW / "portfolio/Bp_stocks_30_3_a61.json",
    "C": RAW / "lifecycle_combo/T2_C_stocks_v3_b15.json",
    "D": RAW / "lifecycle_combo/T2_D_stocks_default.json",
}


def load_runs() -> dict[str, list[dict]]:
    out = {}
    for mod, path in RUN_FILES.items():
        r = json.loads(path.read_text())
        trades = [t for t in r["trades"]
                  if t["symbol"] != "000300.SS" and t["exit_date"] is not None]
        for t in trades:
            t["module"] = mod
        out[mod] = trades
    return out


def gate_a(trades: list[dict]) -> list[dict]:
    return [t for t in trades
            if t["benchmark_clock_type"] != 3 and t["trend_stage"] >= 4]


def pool_close(symbol: str) -> pd.Series:
    df = pd.read_parquet(POOL / f"{symbol}.bars.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df["close"].astype(float).sort_index()

OUT = REPO / "web/public/reports/lei-zuhe-zhongshen-2026-09-01.html"
CSS = """
body{background:#0d1420;color:#dce6f2;font:14px/1.6 -apple-system,sans-serif;margin:0;padding:24px}
.wrap{max-width:1000px;margin:0 auto}
h2{margin:4px 0 2px;font-size:22px} h3{margin:26px 0 8px;font-size:16px;color:#9fc3ee}
.sub{color:#8aa0b8;font-size:12.5px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}
.kpi{background:#111a2b;border:1px solid #233247;border-radius:10px;padding:12px 14px}
.kname{font-size:13px;font-weight:600;color:#cfe0f5}
.krow{margin:6px 0 4px;display:flex;gap:10px;align-items:baseline}
.kv{font-size:22px;font-weight:700} .up{color:#3fd08c} .kd{color:#e06c5a;font-size:13px}
.kc{color:#d9a441;font-size:12px} .kmeta{font-size:11.5px;color:#8aa0b8;margin-top:2px}
.knote{font-size:11.5px;color:#6f87a3;margin-top:4px}
table{width:100%;border-collapse:collapse;margin:8px 0;font-size:12.5px}
th{text-align:left;padding:6px 8px;color:#8aa0b8;font-weight:500;border-bottom:1px solid #233247}
td{padding:6px 8px;border-bottom:1px solid #1a2638;font-variant-numeric:tabular-nums}
.pass{color:#3fd08c} .fail{color:#e06c5a} .dim{color:#6f87a3} .warn{color:#d9a441}
.box{background:#111a2b;border:1px solid #233247;border-radius:10px;padding:12px 16px;margin:12px 0}
code{background:#1a2638;padding:1px 6px;border-radius:4px;font-size:12px;color:#9fd0ff}
.fals{display:inline-block;margin:3px;padding:2px 8px;border-radius:10px;
background:#2a1e22;color:#c98a80;font-size:11.5px;text-decoration:line-through}
"""


RAW = REPO / "docs/experiments/raw"
FZ80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.0), (999, 0.0))
W1F = lambda s, d: 1.0  # noqa: E731


def curves():
    runs = load_runs()
    br = load_breadth()
    b200 = {str(d.date()): float(v) for d, v in br["ma200_pct"].items()}
    caps = {"none": None,
            "full_v2": cap_fn_from_map(position_cap_map(b200, TIERS_V2)),
            "h80": cap_fn_from_map(position_cap_map(b200, H80)),
            "fz80": cap_fn_from_map(position_cap_map(b200, FZ80))}
    a_leg = dedup_signals([{**t, "pool": "A_ETF"}
                           for t in gate_a(runs["A"])])[0]
    s_leg = dedup_signals(
        [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
        + [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]])[0]

    def split_with(cap):
        a = sim_weighted(a_leg, W1F, cap, 500_000)
        s = sim_weighted(s_leg, W1F, None, 500_000)
        return merge_curves(a, s)

    out = {}
    out["no_gate"] = split_with(None)
    out["full_v2"] = split_with(caps["full_v2"])
    out["split_h80"] = split_with(caps["h80"])
    out["g4_stopbuy"] = split_with(caps["fz80"])
    bench = pool_close("000300.SS")
    out["bench"] = [{"date": str(d.date()), "equity": float(v)}
                    for d, v in bench.items()]
    # 宽度档位带（h80 五档，周频生效）
    tier_series = []
    days = sorted(b200)
    for d in days:
        v = b200[d]
        cap = next((w for th, w in H80 if v <= th), H80[-1][1])
        tier_series.append((d, v, cap))
    return out, tier_series, s_leg, a_leg


def kpi(curve, name, note, fee, lag, bench_note):
    eq = pd.Series({p["date"]: p["equity"] for p in curve["curve"]}
                   ).sort_index()
    yrs = (pd.Timestamp(eq.index[-1]) - pd.Timestamp(eq.index[0])).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    dd = float((eq / eq.cummax() - 1).min())
    return {"name": name, "cagr": cagr, "dd": dd,
            "calmar": cagr / abs(dd) if dd else None,
            "window": f"{eq.index[0]} → {eq.index[-1]}（{yrs:.1f}年）",
            "fee": fee, "lag": lag, "bench": bench_note, "note": note}


def svg_lines(series_map, w=960, h=320, log=True):
    import math

    all_dates = sorted({p["date"] for c in series_map.values()
                        for p in (c if isinstance(c, list) else c["curve"])})
    if not all_dates:
        return ""
    x0, x1 = pd.Timestamp(all_dates[0]), pd.Timestamp(all_dates[-1])

    def vals(c):
        pts = c if isinstance(c, list) else c["curve"]
        return {p["date"]: p["equity"] for p in pts}

    frames = {k: vals(v) for k, v in series_map.items()}
    lo, hi = math.inf, -math.inf
    for f in frames.values():
        for v in f.values():
            if v > 0:
                ll = math.log10(v) if log else v
                lo, hi = min(lo, ll), max(hi, ll)
    pad = (hi - lo) * 0.05
    lo, hi = lo - pad, hi + pad

    def X(d):
        return 60 + (pd.Timestamp(d) - x0).days / max(
            (x1 - x0).days, 1) * (w - 80)

    def Y(v):
        ll = math.log10(v) if log and v > 0 else v
        return h - 30 - (ll - lo) / max(hi - lo, 1e-9) * (h - 60)

    colors = {"split_h80": "#4da3ff", "full_v2": "#d9a441",
              "no_gate": "#7f8c9b", "g4_stopbuy": "#3fd08c",
              "bench": "#e06c5a"}
    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:'
             f'#0b1220;border-radius:10px">',
             '<text x="70" y="22" fill="#8aa0b8" font-size="12">'
             '净值（对数轴，初始=100万归一）</text>']
    for i in range(5):
        yy = 30 + i * (h - 60) / 4
        v = hi - i * (hi - lo) / 4
        parts.append(f'<line x1="60" y1="{yy:.0f}" x2="{w-20}" y2="{yy:.0f}"'
                     f' stroke="#1c2a40" stroke-width="1"/>')
        parts.append(f'<text x="8" y="{yy+4:.0f}" fill="#5c718a"'
                     f' font-size="10">{10**v:,.0f}</text>' if log else "")
    for key, f in frames.items():
        col = colors.get(key, "#888")
        base = None
        path = []
        for d in all_dates:
            if d in f and f[d] > 0:
                if base is None:
                    base = f[d]
                path.append((X(d), Y(f[d])))
        if not path:
            continue
        d_attr = " ".join(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}"
                           for i, (x, y) in enumerate(path))
        parts.append(f'<path d="{d_attr}" fill="none" stroke="{col}"'
                     f' stroke-width="1.6" opacity="0.95"/>')
        lx, ly = path[-1]
        parts.append(f'<text x="{lx-90:.0f}" y="{ly-6:.0f}" fill="{col}"'
                     f' font-size="11">{key}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_strip(tier_series, w=960, h=80):
    if not tier_series:
        return ""
    x0 = pd.Timestamp(tier_series[0][0])
    x1 = pd.Timestamp(tier_series[-1][0])
    span = max((x1 - x0).days, 1)
    cmap = {1.0: "#2d6b4f", 0.8: "#3fd08c", 0.6: "#d9c441",
            0.5: "#e08c3f", 0.25: "#e06c5a"}
    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:'
             f'#0b1220;border-radius:10px">',
             '<text x="70" y="18" fill="#8aa0b8" font-size="12">'
             '宽度档位带（B200 五档 → ETF 腿新仓乘数，周频 t+1 生效）</text>']
    for _i, (d, _v, cap) in enumerate(tier_series):
        x = 60 + (pd.Timestamp(d) - x0).days / span * (w - 80)
        col = cmap.get(round(cap, 2), "#555")
        parts.append(f'<rect x="{x:.1f}" y="30" width="3" height="28"'
                     f' fill="{col}"/>')
    parts.append(f'<text x="{w-330}" y="72" fill="#5c718a" font-size="10">'
                 f'绿=满仓1.0 · 黄绿=0.8 · 黄=0.6 · 橙=0.5 · 红=0.25</text>')
    parts.append("</svg>")
    return "".join(parts)


KPI_TMPL = """<div class="kpi"><div class="kname">{name}</div>
<div class="krow"><span class="kv up">{cagr}</span><span class="kd">{dd}</span>
<span class="kc">Calmar {calmar}</span></div>
<div class="kmeta">窗口 {window}</div>
<div class="kmeta">费用：{fee}</div>
<div class="kmeta">时滞：{lag}</div>
<div class="kmeta">对照：{bench}</div>
<div class="knote">{note}</div></div>"""


def main() -> None:
    cv, tiers, s_leg, a_leg = curves()
    fee_sys = "引擎 standard 费用档（r_net 已含进出费用），组合层不另收费"
    lag_sys = "信号 t收盘生成 → t+1 开盘执行；宽度周频 t+1 生效；无未来函数"
    bench_cn = "沪深300 买入持有同窗 89.4万/-39.8%（价格口径）"
    kpis = [
        kpi(cv["split_h80"], "最终形态候选：ETF/个股分账 + 宽度五档(h80)",
            "与现行同收益、回撤砍1/3；黄金豁免；个股腿无闸",
            fee_sys, lag_sys, bench_cn),
        kpi(cv["full_v2"], "现行定版：五档闸全局",
            "交接书既有定版，作为对照基线",
            fee_sys, lag_sys, bench_cn),
        kpi(cv["g4_stopbuy"], "防守增强候选：≥80 停新买",
            "回撤全场最优；未过收益线（该线为收益型修法设），观察档",
            fee_sys, lag_sys, bench_cn),
        kpi(cv["no_gate"], "纯信号系统（无仓位层）",
            "收益上限参照：多赚52%但回撤2.7倍",
            fee_sys, lag_sys, bench_cn),
    ]
    for k in kpis:
        k["cagr"] = f"{k['cagr']:+.1%}"
        k["dd"] = f"回撤 {k['dd']:.1%}"
        k["calmar"] = f"{k['calmar']:.2f}" if k["calmar"] else "—"

    me = json.loads((RAW / "module_e/module_e_results.json").read_text())
    wf = json.loads((RAW / "breadth_overlay/walkforward_results.json").read_text())  # noqa: F841 归档引用

    def row(cells, cls=None):
        tds = "".join(
            f'<td class="{cls[i]}">{c}</td>' if cls and cls[i] else
            f"<td>{c}</td>" for i, c in enumerate(cells))
        return f"<tr>{tds}</tr>"

    u1 = me["us"]["arms"]["v1_hedge50"]
    u3 = me["us"]["arms"]["v3_hedge50"]
    s0 = me["us"]["baselines"]["S0_buy_hold"]["final"]
    s1 = me["us"]["baselines"]["S1_weekly_dca"]["final"]
    me_rows = "".join([
        row(["v1 双线极值买入+对冲50%（33 信号）", f"{u1['final']:,.0f}",
             f"{u1['cagr']:+.1%}", f"{u1['max_dd']:.1%}",
             f"{u1['cagr']/abs(u1['max_dd']):.2f}", "单边 5bp",
             "宽度收盘确认→次日开盘；冷却 4 周",
             f"周定投 {s1:,.0f}（跑赢 +6.1%）/ 买入持有 {s0:,.0f}"]),
        row(["v3 三线极值（14 信号，全为大底）", f"{u3['final']:,.0f}",
             f"{u3['cagr']:+.1%}", f"{u3['max_dd']:.1%}",
             f"{u3['cagr']/abs(u3['max_dd']):.2f}", "单边 5bp", "同上",
             "12 个月远期 +24.3%/胜率 86%；24 个月胜率 100%"])])
    wf_rows = "".join([
        row(["自适应逐折重选（预登记主判）", "+4.8%", "-36.9%", "零前视",
             "✗", "贪心选参奖励激进档→样本外打脸；136 万 vs 固定 247 万"],
            cls=[None, None, "fail", None, "fail", "dim"]),
        row(["零前视冻结（2016-19 选参）", "+10.0%", "-54.0%",
             "完全零前视", "✗", "收益 7 倍于指数 · 无闸回撤爆"],
            cls=[None, None, "fail", None, "fail", "dim"]),
        row(["零前视冻结 + 宽度闸", "+12.0%", "-27.1%", "闸为全样本标定",
             "✓", "刚过线 0.1pp；闸参数干净来源唯一欠账（前段已补核验）"],
            cls=[None, "pass", None, None, "pass", "dim"])])
    fp_rows = "".join([
        row(["全A B200 宽度", "+27.7%", "+28.3%", "+17.5%",
             "唯一闸 · 5 次同台胜出"],
            cls=[None, "pass", "pass", None, "pass"]),
        row(["国债利率", "-8.9%", "+21.6%", "+3.4%",
             "事后视角重考后失效（前视假象）"],
            cls=[None, "fail", "pass", None, "fail"]),
        row(["制造业 PMI", "-10.6%", "+12.8%", "+5.9%",
             "滚动分位后缩水至边缘"],
            cls=[None, "fail", "pass", None, "warn"]),
        row(["基金仓位", "+15.4%", "+16.3%", "+4.9%",
             "满仓≠顶部（假设证伪）；清仓=底部（三地一致）"],
            cls=[None, "pass", "pass", None, "warn"]),
        row(["北向/NAAIM/两融/美债/其余 6 指标", "详见 fundamental_panel.json",
             "", "", "底部反向叙事 / 顺势叙事 / 不显著"],
            cls=[None, "dim", "dim", "dim", "dim"])])
    syms = [("518850 黄金ETF（豁免闸）", 13, "+76.8", "-14.5%",
             "+15.8% / -30.3%"),
            ("510300 沪深300ETF", 5, "+40.5", "-10.3%", "+5.7% / -44.8%"),
            ("603993 洛阳钼业", 2, "+37.3", "-6.5%", "+20.4% / -71.7%"),
            ("159915 创业板ETF", 5, "+36.5", "-8.6%", "+5.1% / -56.6%"),
            ("300003 乐普医疗", 4, "+26.8", "-7.4%", "-3.4% / -80.4%"),
            ("600030 中信证券", 7, "+25.5", "-8.9%", "+8.5% / -45.5%")]
    sym_rows = "".join(row([a, str(b), c, d, e],
                           cls=[None, None, "pass", None, "dim"])
                       for a, b, c, d, e in syms)
    bug_rows = "".join([
        row(["对冲费用耗干分批现金（第1轮）", "模块E买入笔数 33→9",
             "已修：费用入权益累计，修后 33 笔全部恢复"], cls=[None, None, "pass"]),
        row(["已实现对冲盈亏未入权益（第1轮）", "对冲臂权益少 40 万",
             "已修：realized 累计与 mark 分离，账务闭合"], cls=[None, None, "pass"]),
        row(["回撤比较方向写反（第2轮）", "J3 误判通过", "已修并重跑全臂"],
            cls=[None, None, "pass"]),
        row(["宽度乘数表索引错位（第2轮）", "生效日落 1993-2000，全臂失效",
             "已修：日频索引 t+1"], cls=[None, None, "pass"]),
        row(["分账合并初始为 0（第4轮）", "全局回撤虚高至 52-62%",
             "已修：按初始资金填充"], cls=[None, None, "pass"]),
        row(["dd_improve 公式符号反（第14轮）", "窗口 B 误判不通过",
             "已修：实际 +35.8% 通过"], cls=[None, None, "pass"]),
        row(["CSI300 口径 2017 前无数据（第14轮）", "窗口 A 首跑等价持有",
             "已修：改全A口径补跑并声明"], cls=[None, None, "pass"]),
        row(["宽度文件双写者覆写（08-27）", "33 年史被 live 管线清成 10.7 年",
             "已修：管道分离+研究快照"], cls=[None, None, "pass"]),
        row(["面板全样本分位前视（第18轮）", "利率「哑铃」假信号",
             "已清算：滚动分位复检制度"], cls=[None, None, "pass"]),
        row(["幸存者偏差（多处）", "宽度/标的池均为今日名单回算",
             "未修（工程大）：底部信号偏保守、顶部偏多，结论打折"],
            cls=[None, None, "warn"])])
    fals = ("两档制仓位(85/15、80/20)", "极值高强平卖出", "B50+B200双线常态仓位",
            "RS动量倾斜(3变体)", "低波降权", "背离路牌×0.3/×0.6",
            "B20过热确认/崩盘刹车", "利率档位闸", "美股指数A模块", "参数滚动重选")
    fals_html = "".join(f'<span class="fals">{x}</span>' for x in fals)

    L = []
    A = L.append
    A('<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">')
    A('<title>LEI组归档 · 主系统（信号×仓位×终审×信息源）</title>')
    A(CSS)
    A('</head><body><div class="wrap">')
    A('<h2>LEI组归档 · 主系统全档案</h2>')
    A('<div class="sub">2026-08-27→28 · 19 轮实验 · 判定量约 70 组 ·')
    A('判定标准事前写死于脚本 docstring · 双跑复现（PYTHONHASHSEED=0/42）')
    A('哈希一致 · 信号收盘生成次日开盘执行、宽度周频 t+1（无未来函数）·')
    A('一切结论建议级（终审通过+拍板才转正）</div>')
    A('<h3>① 核心组合 KPI（七项齐全）</h3>')
    A('<div class="grid">' + "".join(KPI_TMPL.format(**k) for k in kpis)
      + '</div>')
    A('<h3>② 净值曲线（2016-08 → 2026-08，100 万起，对数轴）</h3>')
    A(svg_lines({k: cv[k] for k in
                 ("split_h80", "full_v2", "g4_stopbuy", "no_gate", "bench")}))
    A(svg_strip(tiers))
    A('<h3>③ 模块 E（美股 1986→2026，手册口径首次全面过线）</h3>')
    A('<div class="box"><table>')
    A('<tr><th>组合</th><th>终值(100万起)</th><th>年化</th><th>回撤</th>'
      '<th>Calmar</th><th>费用</th><th>时滞</th><th>对照</th></tr>')
    A(me_rows)
    A('</table><div class="dim">只做多用户：去掉对冲腿后 v1≈聪明定投')
    A('（赢 DCA 不赢持有）；对冲腿净赚 +18.2 万但不降回撤')
    A('（宽度离场即平，2008 慢崩无保护）。</div></div>')
    A('<h3>④ walk-forward 终审（2020-01→2026-08）</h3>')
    A('<div class="sub">同期沪深300 买入持有：年化 +1.4% / 回撤 -45.6%</div>')
    A('<div class="box"><table>')
    A('<tr><th>版本</th><th>年化</th><th>回撤</th><th>干净度</th>'
      '<th>判定</th><th>说明</th></tr>')
    A(wf_rows)
    A('</table><div class="warn">铁律：参数冻结永不滚动重选（重调版少赚 45%）；')
    A('信号引擎零前视真实；宽度闸必需（-54% → -27%）。</div></div>')
    A('<h3>⑤ 信息源大比拼（防前视清算后，12 指标）</h3>')
    A('<div class="box"><table>')
    A('<tr><th>指标</th><th>极端高后12m</th><th>极端低后12m</th>'
      '<th>基线</th><th>清算后定位</th></tr>')
    A(fp_rows)
    A('</table><div class="warn">新纪律：面板显著性 ≠ 可交易信号，')
    A('必须滚动分位复检（防前视）才能进闸实验。</div></div>')
    A('<h3>⑥ 按标的成绩单（头部 6，全量 96 见 raw）</h3>')
    A('<div class="box"><table>')
    A('<tr><th>标的</th><th>笔数</th><th>累计R</th><th>策略回撤</th>'
      '<th>持有（年化/回撤）</th></tr>')
    A(sym_rows)
    A('</table><div class="dim">96 标的回撤改善中位数 +63.7pp（无一例外）；')
    A('利润集中于少数大赢家（趋势系统属性）。</div></div>')
    A('<h3>⑦ 已证伪并封存（10 项，不要重测）</h3>')
    A(f'<div class="box">{fals_html}</div>')
    A('<h3>⑧ 复现与溯源</h3><div class="box">')
    A('<code>PYTHONHASHSEED=0 python3 scripts/run_breadth_overlay.py</code>'
      '（宽度闸主链路，双跑哈希 1846d92d…）<br>')
    A('<code>PYTHONHASHSEED=0 python3 scripts/run_walkforward.py</code>'
      '（终审七折）<br>')
    A('<code>PYTHONHASHSEED=0 python3 scripts/run_module_e.py</code>'
      '（模块E，哈希 11f3c4e6…）<br>')
    A('<code>PYTHONHASHSEED=0 python3 scripts/render_lei_archive_page.py'
      '</code>（本页）<br>')
    A('原始数据：docs/experiments/raw/lei/（本组归档副本 + HASHES.txt + '
      'MANIFEST.md）；原始位置 raw/ 下 module_e、breadth_overlay、'
      'sentiment 三目录。</div>')
    A('<h3>⑨ 已知问题 / 已修 bug 清单（诚实条款）</h3>')
    A('<div class="box"><table>')
    A('<tr><th>问题</th><th>影响</th><th>处置</th></tr>')
    A(bug_rows)
    A('</table></div>')
    A('<div class="sub" style="margin-top:18px">LEI组 · 归档会话 '
      '2026-08-27~28 · 详细档案：docs/experiments/lei-ARCHIVE-2026-09-01.md'
      '</div>')
    A('</div></body></html>')
    html = "\n".join(L)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"落盘 {OUT}（{len(html)/1024:.0f} KB）")


if __name__ == "__main__":
    main()
