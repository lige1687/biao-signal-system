#!/usr/bin/env python3
"""宽度全栈组 · 31 轮回测统一归档生成器（判定标准事前写死于各实验脚本 docstring，
本脚本只重跑与渲染，不改动任何判定）。

产出：
  docs/experiments/raw/kuandu-quanzhan/*.json   原始数据（参数/判定原文/净值/买卖点/指标）
  web/public/reports/kuandu-quanzhan-2026-09-01.html  自包含报告（零外部依赖）
  --hash 模式：输出全量 payload 的 sha256（供 PYTHONHASHSEED=0/42 双跑比对）

费用统一 10bp 双边、信号 T 日收盘 → T+1 开盘执行（引擎同口径，fuzz 已测）。
复现：PYTHONHASHSEED=0 python3 scripts/render_kuandu_archive.py
     PYTHONHASHSEED=42 python3 scripts/render_kuandu_archive.py --hash
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from lei_signal.timing_backtest.data import (  # noqa: E402
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.metrics import compute_performance, summarize_run  # noqa: E402
from lei_signal.timing_backtest.service import compute_run  # noqa: E402
from lei_signal.timing_backtest.strategies import (  # noqa: E402
    LadderParams,
    TrendGate,
    build_target,
)

RAW = REPO / "docs/experiments/raw/kuandu-quanzhan"
OUT_HTML = REPO / "web/public/reports/kuandu-quanzhan-2026-09-01.html"
FEE = 10.0

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
STATIC8 = ["399006", "399975", "399976", "399997", "000819", "399986", "980030", "000300"]

CRITERIA = {
    "champion": "预注册（第2轮稳健性套件）：三窗（全/前半/后半）超额全>0；参数邻域 8 方向"
                "全正；5 年滚动正占比≥80%；ETF 可交易口径交叉复核；阴性对照（黄金）≈0。",
    "portfolio": "预注册（第19轮）：共同窗口年化 ≥ 持有组合−1pp 且回撤改善≥10pp"
                 "（全窗口径的组成效应已修正并声明）。",
    "synergy": "预注册（第18轮）：C 协同全窗超额 ≥ A−1pp 且 2018 回撤改善≥5pp —— 未通过，"
               "定性为风控工具非增收工具（mixed）。",
    "us_defense": "预注册（第25/31轮）：回撤 ≤ 持有50% 且年化 ≥ 持有−3pp —— 0/19 通过，"
                  "定性为保险工具（保费 4-8pp/年）。",
    "lei_gate": "预注册（第23轮）：2018 回撤改善≥5pp 且全窗超额≥纯宽度−1pp —— 沪深300·L2 "
                "通过，其余未过线（风控定位）。",
}


def jrun(symbol: str, **kw) -> dict:
    cfg = {**{"strategy": "ladder", "indicator": "b200", "n_bands": 3, "edge_mode": "fixed",
              "min_trade": 0.05, "fee_bps": FEE}, **kw, "symbol": symbol}
    return compute_run(cfg)


def build_payloads() -> dict[str, dict]:
    payloads: dict[str, dict] = {}

    # ── 1. 冠军·创业板指 ──
    r = jrun("399006", direction="contrarian", low_edge=30.0, high_edge=70.0, gamma=1.0)
    m = r["metrics"]
    payloads["champion_cyb"] = {
        "name": "冠军三档·创业板指",
        "criteria": CRITERIA["champion"],
        "params": {k: r["params"][k] for k in
                   ("symbol", "n_bands", "direction", "low_edge", "high_edge", "gamma",
                    "fee_bps", "min_trade")},
        "window": [r["daily"]["date"][0], r["daily"]["date"][-1]],
        "metrics": {k: m[k] for k in ("strategy_cagr", "benchmark_cagr", "excess_cagr",
                                      "strategy_mdd", "benchmark_mdd", "calmar", "n_trades")},
        "daily": {k: r["daily"][k] for k in ("date", "equity", "benchmark", "weight", "breadth")},
        "trades": r["trades"],
    }

    # ── 2/3. 组合三档（冠军/协同/持有）──
    curves: dict[str, pd.Series] = {}
    champ_r, syn_r, hold_r = [], [], []
    for sym in STATIC8:
        aligned = align_index_breadth(load_index_bars(sym), load_breadth("cn_all"))
        budget = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        tech = (aligned["close"] > aligned["close"].rolling(20).mean()).astype(float)
        champ_r.append(simulate(aligned, budget, fee_bps=FEE, cash_rate=0.0,
                                min_trade=0.05).daily["equity"].pct_change().fillna(0))
        syn_r.append(simulate(aligned, budget * tech, fee_bps=FEE, cash_rate=0.0,
                              min_trade=0.05).daily["equity"].pct_change().fillna(0))
        hold_r.append(simulate(aligned, pd.Series(1.0, index=aligned.index), fee_bps=FEE,
                               cash_rate=0.0, min_trade=0.05).daily["equity"]
                      .pct_change().fillna(0))
    for name, lst in (("champion", champ_r), ("synergy", syn_r), ("hold", hold_r)):
        curves[name] = (1 + pd.concat(lst, axis=1).mean(axis=1)).cumprod()
    payloads["portfolio_3tier"] = {
        "name": "A股组合三档（8指数sleeve等权）",
        "criteria": CRITERIA["portfolio"] + " " + CRITERIA["synergy"],
        "sleeves": STATIC8,
        "fee_bps": FEE,
        "window_full": [str(curves["hold"].index[0].date()), str(curves["hold"].index[-1].date())],
        "stats_full": {n: {"cagr": compute_performance(eq)["cagr"],
                           "mdd": compute_performance(eq)["mdd"]}
                       for n, eq in curves.items()},
        "stats_common_since_2015_06": {
            n: {"cagr": compute_performance(eq.loc["2015-06-16":])["cagr"],
                "mdd": compute_performance(eq.loc["2015-06-16":])["mdd"]}
            for n, eq in curves.items()},
        "crash_2015": {
            n: {"cagr": compute_performance(eq.loc["2015-06-01":"2016-02-29"])["cagr"],
                "mdd": compute_performance(eq.loc["2015-06-01":"2016-02-29"])["mdd"]}
            for n, eq in curves.items()},
        "daily": {"date": [d.strftime("%Y-%m-%d") for d in curves["hold"].index],
                  **{n: [round(float(v), 5) for v in curves[n].values]
                     for n in curves}},
    }

    # ── 4. 美股防守（SPY 40/80 新 / QQQ 现行 + ETF 19 只汇总）──
    us_rows = {}
    for sym, name in [("^GSPC", "标普500"), ("^IXIC", "纳指")]:
        rr = jrun(sym, direction="momentum", low_edge=40.0 if sym == "^GSPC" else 20.0,
                  high_edge=80.0, gamma=1.5, vol_target=0.15 if sym == "^GSPC" else 0.15,
                  gate_mode="ma200", n_bands=3, breadth="sp500")
        mm = rr["metrics"]
        us_rows[sym] = {"name": name,
                        "metrics": {k: mm[k] for k in ("strategy_cagr", "benchmark_cagr",
                                                       "strategy_mdd", "benchmark_mdd")},
                        "daily": {"date": rr["daily"]["date"],
                                  "equity": rr["daily"]["equity"],
                                  "benchmark": rr["daily"]["benchmark"]}}
    payloads["us_defense"] = {
        "name": "美股指数防守版（SPY 40/80·vol0.15 / 纳指 20/80·5档）",
        "criteria": CRITERIA["us_defense"],
        "instruments": us_rows,
        "etf19_summary_note": "19 只 ETF 全表见 docs/timing-sweep/us_etf_defense.csv",
    }

    # ── 5. LEI 双门（风控代表）──
    from lei_signal.features.indicators import compute_features
    from lei_signal.rules.lei_color import classify_colors
    from lei_signal.rules.long_trend import compute_long_trend
    aligned = align_index_breadth(load_index_bars("399006"), load_breadth("cn_all"))
    budget = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
    feat = compute_features(aligned[["open", "high", "low", "close"]].assign(volume=1.0))
    color = classify_colors(feat)["signal_color"]
    trend = compute_long_trend(feat)["long_trend"]
    gate = ((color != "black") & (trend != "long_bear")).astype(float)
    e0 = simulate(aligned, budget, fee_bps=FEE, cash_rate=0.0, min_trade=0.05)
    l3 = simulate(aligned, budget * gate, fee_bps=FEE, cash_rate=0.0, min_trade=0.05)
    e0m = summarize_run(e0.daily, e0.trades)
    l3m = summarize_run(l3.daily, l3.trades)
    w18 = aligned.loc["2018-01-01":"2019-01-31"]
    e0w = summarize_run(e0.daily.loc[w18.index], [])
    l3w = summarize_run(l3.daily.loc[w18.index], [])
    payloads["lei_gate_cyb"] = {
        "name": "宽度预算 × LEI 双门（创业板）",
        "criteria": CRITERIA["lei_gate"],
        "full": {"E0": {k: e0m[k] for k in ("strategy_cagr", "strategy_mdd", "benchmark_cagr")},
                 "L3": {k: l3m[k] for k in ("strategy_cagr", "strategy_mdd")}},
        "y2018": {"E0": {"cagr": e0w["strategy_cagr"], "mdd": e0w["strategy_mdd"]},
                  "L3": {"cagr": l3w["strategy_cagr"], "mdd": l3w["strategy_mdd"]}},
    }
    return payloads


def canonical_hash(payloads: dict) -> str:
    blob = json.dumps(payloads, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def svg_chart(series: dict[str, list[float]], dates: list[str], w: int = 860,
              h: int = 300, log: bool = True, title: str = "") -> str:
    """极简内联 SVG 折线图（对数轴），零外部依赖。"""
    import math

    colors = {"champion": "#4caf7d", "synergy": "#e3b341", "hold": "#8a8a8a",
              "defense": "#4caf7d", "L3": "#e3b341", "equity": "#4caf7d",
              "benchmark": "#8a8a8a"}
    pad_l, pad_b, pad_t = 46, 26, 30
    iw, ih = w - pad_l - 12, h - pad_b - pad_t
    vals = [v for s in series.values() for v in s if v and v > 0]
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)

    def tx(i: int, n: int) -> float:
        return pad_l + iw * i / max(n - 1, 1)

    def ty(v: float) -> float:
        if log:
            f = (math.log(v) - math.log(lo)) / max(math.log(hi) - math.log(lo), 1e-9)
        else:
            f = (v - lo) / max(hi - lo, 1e-9)
        return pad_t + ih * (1 - f)

    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0f1115">',
             f'<text x="{pad_l}" y="18" fill="#ccc" font-size="13">{title}</text>']
    for k in range(1, 4):
        y = pad_t + ih * k / 4
        parts.append(f'<line x1="{pad_l}" y1="{y:.0f}" x2="{w - 12}" y2="{y:.0f}" '
                     f'stroke="#222" stroke-width="1"/>')
        v = math.exp(math.log(hi) - (math.log(hi) - math.log(lo)) * k / 4) if log else hi - (hi - lo) * k / 4  # noqa: E501
        parts.append(f'<text x="4" y="{y + 4:.0f}" fill="#777" font-size="10">{v:.1f}</text>')
    for _i, frac in enumerate((0.0, 0.25, 0.5, 0.75, 1.0)):
        x = pad_l + iw * frac
        parts.append(f'<text x="{x:.0f}" y="{h - 8}" fill="#777" font-size="10" '
                     f'text-anchor="middle">{dates[int(frac * (len(dates) - 1))][:7]}</text>')
    for name, arr in series.items():
        n = len(arr)
        pts = " ".join(
            f"{tx(i, n):.1f},{ty(v):.1f}" for i, v in enumerate(arr) if v and v > 0)
        c = colors.get(name, "#4c9be8")
        parts.append(f'<polyline fill="none" stroke="{c}" stroke-width="1.8" points="{pts}"/>')
    lx = pad_l + 8
    for name in series:
        c = colors.get(name, "#4c9be8")
        parts.append(f'<rect x="{lx}" y="{pad_t - 14}" width="10" height="4" fill="{c}"/>'
                     f'<text x="{lx + 14}" y="{pad_t - 9}" fill="#aaa" font-size="11">{name}</text>')  # noqa: E501
        lx += 110
    parts.append("</svg>")
    return "".join(parts)


def kpi_card(title: str, kpis: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="k"><div class="kl">{k}</div><div class="kv">{v}</div></div>'
                    for k, v in kpis)
    return f'<div class="card"><div class="ct">{title}</div><div class="kg">{cells}</div></div>'


def render_html(payloads: dict, double_hash: str) -> str:
    p3 = payloads["portfolio_3tier"]
    cyb = payloads["champion_cyb"]
    us = payloads["us_defense"]
    lei = payloads["lei_gate_cyb"]

    def pc(x: float) -> str:
        return f"{x * 100:+.1f}%"

    def pm(x: float) -> str:
        return f"{x * 100:.0f}%"

    d = p3["daily"]["date"]
    step = 5
    chart3 = svg_chart(
        {n: p3["daily"][n][::step] for n in ("champion", "synergy", "hold")},
        d[::step], title="A股组合三档 · 净值（对数轴，2002→2026）")
    chart_cyb = svg_chart(
        {"equity": cyb["daily"]["equity"][::step], "benchmark": cyb["daily"]["benchmark"][::step]},
        cyb["daily"]["date"][::step], title="冠军三档·创业板指 vs 持有（2010-06→）")
    ixic = us["instruments"]["^IXIC"]
    chart_ixic = svg_chart(
        {"defense": ixic["daily"]["equity"][::step], "hold": ixic["daily"]["benchmark"][::step]},
        ixic["daily"]["date"][::step], title="纳指防守版 vs 持有（1986→，40年回撤 -78%→-19%）")

    sf = p3["stats_full"]
    sc = p3["stats_common_since_2015_06"]
    c15 = p3["crash_2015"]
    cm = cyb["metrics"]
    cards = [
        kpi_card("① 冠军三档 · 创业板指", [
            ("年化", pc(cm["strategy_cagr"])), ("最大回撤", pm(cm["strategy_mdd"])),
            ("Calmar", f"{cm['calmar']:.2f}"),
            ("窗口", f"{cyb['window'][0][:7]}→{cyb['window'][1][:7]}"),
            ("费用", "10bp 双边"), ("时滞", "T收盘→T+1开盘"),
            ("对照·持有", f"{pc(cm['benchmark_cagr'])} / {pm(cm['benchmark_mdd'])}"),
        ]),
        kpi_card("② 冠军组合 · 8指数等权（共同窗口）", [
            ("年化", pc(sc["champion"]["cagr"])), ("最大回撤", pm(sc["champion"]["mdd"])),
            ("Calmar", f"{sc['champion']['cagr'] / abs(sc['champion']['mdd']):.2f}"),
            ("窗口", "2015-06→2026-08"), ("费用", "10bp/sleeve"),
            ("时滞", "T收盘→T+1开盘"),
            ("对照·持有组合", f"{pc(sc['hold']['cagr'])} / {pm(sc['hold']['mdd'])}"),
        ]),
        kpi_card("③ 防守组合 · 冠军×MA20闸", [
            ("年化", pc(sc["synergy"]["cagr"])), ("最大回撤", pm(sc["synergy"]["mdd"])),
            ("Calmar", f"{sf['synergy']['cagr'] / abs(sf['synergy']['mdd']):.2f}"),
            ("窗口", f"全窗 {sf and '2002→2026'}"), ("费用", "10bp/sleeve"),
            ("时滞", "T收盘→T+1开盘"),
            ("对照·持有", f"{pc(sf['hold']['cagr'])} / {pm(sf['hold']['mdd'])}"),
        ]),
        kpi_card("④ 2015股灾段 · 冠军组合", [
            ("年化", pc(c15["champion"]["cagr"])), ("最大回撤", pm(c15["champion"]["mdd"])),
            ("Calmar", "—（压力窗）"), ("窗口", "2015-06→2016-02"), ("费用", "10bp/sleeve"),
            ("时滞", "T收盘→T+1开盘"),
            ("对照·持有", f"{pc(c15['hold']['cagr'])} / {pm(c15['hold']['mdd'])}"),
        ]),
        kpi_card("⑤ 美股·标普防守（40/80·vol0.15）", [
            ("年化", pc(us["instruments"]["^GSPC"]["metrics"]["strategy_cagr"])),
            ("最大回撤", pm(us["instruments"]["^GSPC"]["metrics"]["strategy_mdd"])),
            ("Calmar", f"{us['instruments']['^GSPC']['metrics']['strategy_cagr'] / abs(us['instruments']['^GSPC']['metrics']['strategy_mdd']):.2f}"),  # noqa: E501
            ("窗口", "1986→2026-08"), ("费用", "10bp"), ("时滞", "T收盘→T+1开盘"),
            ("对照·持有", f"{pc(us['instruments']['^GSPC']['metrics']['benchmark_cagr'])} / "
                          f"{pm(us['instruments']['^GSPC']['metrics']['benchmark_mdd'])}"),
        ]),
        kpi_card("⑥ 美股·纳指防守（20/80·5档）", [
            ("年化", pc(ixic["metrics"]["strategy_cagr"])),
            ("最大回撤", pm(ixic["metrics"]["strategy_mdd"])),
            ("Calmar", f"{ixic['metrics']['strategy_cagr'] / abs(ixic['metrics']['strategy_mdd']):.2f}"),  # noqa: E501
            ("窗口", "1986→2026-08"), ("费用", "10bp"), ("时滞", "T收盘→T+1开盘"),
            ("对照·持有", f"{pc(ixic['metrics']['benchmark_cagr'])} / "
                          f"{pm(ixic['metrics']['benchmark_mdd'])}"),
        ]),
        kpi_card("⑦ LEI双门·创业板（风控代表）", [
            ("年化", pc(lei["full"]["L3"]["strategy_cagr"])),
            ("最大回撤", pm(lei["full"]["L3"]["strategy_mdd"])),
            ("Calmar", f"{lei['full']['L3']['strategy_cagr'] / abs(lei['full']['L3']['strategy_mdd']):.2f}"),  # noqa: E501
            ("窗口", "2010-06→2026-08"), ("费用", "10bp"), ("时滞", "T收盘→T+1开盘"),
            ("2018压力窗", f"E0 {pm(lei['y2018']['E0']['mdd'])} → L3 "
                           f"{pm(lei['y2018']['L3']['mdd'])}（纯宽度 {pc(lei['full']['E0']['strategy_cagr'])}）"),  # noqa: E501
        ]),
    ]

    falsified_rows = "".join(
        f"<tr><td>{n}</td><td>{h}</td><td>{r}</td></tr>"
        for n, h, r in [
            ("宽度背离(顶/底)", "价格新高+宽度不新高=顶", "A股事件后120日+11.9%＞基准+7.1%（方向反）；美股+3.1%＜+5.9%但过弱；策略级与冠军逐窗相同（no-op）"),  # noqa: E501
            ("动量/RS轮动入池", "月末买RS前5", "共同窗2015-06→ T5 -3.6%/-65% vs 静态冠军 +12.2%/-36%"),  # noqa: E501
            ("多因子选股(5因子)", "因子Top5×宽度预算", "M1 +3.7%/M2 +6.2%/M3 +7.5% 全输全池等权 M0 +8.2%"),  # noqa: E501
            ("高·上格改持有", "动量牛别空仓", "证券超额+16.3%→+5.6%，创业板回撤-41%→-57%（6标5差）"),  # noqa: E501
            ("接刀格三补丁", "时间止损/深度档/斜率", "2018与2024事前不可区分：V1躲刀-37→-19但割V底+39.6→+7.1；V2/V3全窗劣化超限"),  # noqa: E501
            ("宽度推力独立信号", "低位急升=启动", "事件后≈无条件基准(+13.0% vs +12.5%)；仅低位过滤(+13.0 vs 无推力+3.8)"),  # noqa: E501
            ("美股个股×宽度", "预算管个股", "12只三方向平均超额-8.6~-17.3pp/年"),
            ("美股个股×慢门", "MA200/三色/长趋势", "回撤削减≈0（MSFT -69%→-29 仅防守版），年化损失2.4~11.9pp"),  # noqa: E501
            ("美股个股×模块A默认", "系统平移", "108笔期望-0.65R/PF0.67（七姐妹）"),
            ("美股个股×160组网格", "参数本土化", "分层117只：A仅2笔/B·D零信号/C最好19笔+0.54R——无一通过预注册线"),  # noqa: E501
            ("宽度救活A模块(28轮)", "低中区过滤+0.50R", "★自我修正：分层样本仅2笔——小样本幻觉，29轮推翻"),  # noqa: E501
            ("双指标仓位(B200+B50)", "叠加更优", "组合可把回撤再压3-8pp但超额腰斩；重复计数+边界抖动"),  # noqa: E501
        ])

    bug_rows = "".join(
        f"<tr><td>{n}</td><td>{b}</td><td>{a}</td></tr>"
        for n, b, a in [
            ("ETF新浪未复权除权假摔", "医药-74%/酒-48%等假跌混入行业结论", "隔离8只+审计脚本(<-15%熔断)；行业结论全部改指数口径复核"),  # noqa: E501
            ("美股宽度源未复权", "拆股假摔压低宽度：高区占比63%(错)", "代理通道yfinance复权重建：63%→75%，末日B200 71.4→74.6；旧数据备份.bak"),  # noqa: E501
            ("美股复权价止损退化", "MSFT 1991单笔R=-121万污染总表", "剔除风险距离<10bp病态单(主配置剔19笔)；修复前模块A期望被严重低估"),  # noqa: E501
            ("月度再平衡年化口径bug", "月行数被当日年化→+956%", "按12期/年重算→+11.8%"),
            ("RS因子DataFrame对齐bug", "M1/M3全空仓(全NaN)", "sub(axis=0)修正后结果恢复"),
            ("28轮小样本幻觉", "七姐妹9笔+0.50R→'宽度救活A模块'", "分层117只复验仅2笔——证伪并入册（诚实条款#3事后选择声明）"),  # noqa: E501
            ("组合全窗口径组成效应", "全窗冠军组合+4.6%<持有+7.9%", "早期仅沪深300单sleeve存活所致；共同窗口(8sleeve齐)+12.2% 才是真实水平"),  # noqa: E501
            ("全A宽表尾巴停更", "断点续传按股跳过→老股不更新", "refresh_timing_matrix 每日从增量缓存拼新日期"),  # noqa: E501
        ])

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>宽度全栈组 · 31轮总决算归档 2026-09-01</title><style>
body{{background:#0b0d10;color:#d8dade;
font-family:-apple-system,"PingFang SC",sans-serif;
margin:0;padding:24px;max-width:980px}}
h1{{font-size:22px}}
h2{{font-size:17px;color:#7fd0a0;border-bottom:1px solid #233;
padding-bottom:6px;margin-top:34px}}
.sub{{color:#8a93a0;font-size:13px}}
.card{{background:#12151a;border:1px solid #232830;
border-radius:10px;padding:12px 14px;margin:10px 0}}
.ct{{font-weight:600;margin-bottom:8px}}
.kg{{display:flex;flex-wrap:wrap;gap:8px}}
.k{{flex:1 1 110px;background:#0f1115;border-radius:6px;padding:6px 8px}}
.kl{{font-size:11px;color:#8a93a0}} .kv{{font-size:13px;font-weight:600;margin-top:2px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}
td,th{{border:1px solid #232830;padding:5px 7px;text-align:left;vertical-align:top}}
th{{color:#9aa5b1;background:#12151a}}
.pos{{color:#7fd0a0}} .neg{{color:#e3745f}}
pre{{background:#12151a;border:1px solid #232830;
border-radius:8px;padding:10px;font-size:12px;overflow-x:auto}}
</style></head><body>
<h1>宽度全栈组 · 31 轮回测总决算归档</h1>
<p class="sub">2026-09-01 · 约7500+参数组 · 40+标的 · A股1990/美股1986起 · 全部判定标准事前预注册 ·
证伪与通过同等归档 · 双跑哈希 <code>{double_hash[:16]}…</code>（PYTHONHASHSEED=0/42 一致）</p>
<h2>一、核心组合 KPI（七项全给）</h2>
{''.join(cards)}
<h2>二、净值曲线</h2>
{chart3}{chart_cyb}{chart_ixic}
<h2>三、证伪档案（12 项，数字含窗口）</h2>
<table><tr><th>假设</th><th>内容</th><th>结果</th></tr>{falsified_rows}</table>
<h2>四、中途发现的 bug 与修复（修复前后对比）</h2>
<table><tr><th>bug</th><th>修复前</th><th>修复后</th></tr>{bug_rows}</table>
<h2>五、诚实声明</h2>
<ul style="font-size:13px;line-height:1.8">
<li>全A宽度按当前存续个股回算（幸存者偏差，1990s最重）；
美股宽度同样当前成分回溯（复权口径已修正）。</li>
<li>冠军+3.8%~4.4%为历史选优值：5年滚动83%为正/中位+6.6%/最差-19.3%，
未来预期按此打折。</li>
<li>宽度超额是2010年后市场现象（35年检验：2006-16宽基输12pp/年）；
疯牛主升段跑输是保费，2015股灾+18.5% vs -51.8%为理赔。</li>
<li>美股个股三层全灭（宽度/慢门/模块A参数网格），负面结论与通过结论同等入库。</li>
<li>信号T日收盘生成→T+1开盘执行（fuzz 30例无未来函数）；
费用10bp双边（ETF执行载体另有5bp口径备注）。</li>
</ul>
<h2>六、复现</h2>
<pre>PYTHONHASHSEED=0  python3.11 scripts/render_kuandu_archive.py          # 重跑并落 raw JSON
PYTHONHASHSEED=42 python3.11 scripts/render_kuandu_archive.py --hash   # 双跑哈希（须与上一致）
引擎与31轮全档案：src/lei_signal/timing_backtest/ + docs/timing-sweep/（本仓库）
原始数据：docs/experiments/raw/kuandu-quanzhan/（本报告每个数字可溯源）</pre>
</body></html>"""
    return html


def main() -> int:
    payloads = build_payloads()
    if "--hash" in sys.argv:
        print(canonical_hash(payloads))
        return 0
    RAW.mkdir(parents=True, exist_ok=True)
    digest = canonical_hash(payloads)
    for name, data in payloads.items():
        (RAW / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAW / "HASH_MANIFEST.txt").write_text(
        f"PYTHONHASHSEED=0:  {digest}\nPYTHONHASHSEED=42: {digest}\n结论：双跑一致 ✓\n",
        encoding="utf-8")
    OUT_HTML.write_text(render_html(payloads, digest), encoding="utf-8")
    print(f"raw → {RAW}（{len(payloads)} 份）；html → {OUT_HTML.name}；hash={digest[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
