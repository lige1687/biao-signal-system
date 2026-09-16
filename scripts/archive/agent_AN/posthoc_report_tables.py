# -*- coding: utf-8 -*-
"""任务 AN 报告表格片段机器生成（描述性汇总 + 逐事件全表）。
不参与判定；判定数字全部来自主脚本 JSON。输出 docs/experiments/raw/agent_AN/report_tables.md"""
import json
from collections import defaultdict
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "docs/experiments/raw/agent_AN"
data = json.loads((RAW / "top_structure_events.json").read_text())
m = data["main_85"]
ev = m["events"]

TYPE_CN = {"crash": "急跌", "grind": "磨顶", "middle": "中间", None: "不可分类"}
NAME = {e["symbol"]: e["name"] for e in ev}
ORDER = ["399006", "000300", "512100", "000688.SH", "512480"]

lines = []
lines.append("## 簇覆盖与集中度（描述性）\n")
clusters_with_events = sorted({e["event_date"] for e in ev})
all_clusters = m["clusters"]
uncovered = [c for c in all_clusters if c not in clusters_with_events]
lines.append(f"- 全部 {len(all_clusters)} 簇中有标的覆盖的 {len(clusters_with_events)} 簇；"
             f"无覆盖 {len(uncovered)} 簇：{', '.join(uncovered)}\n")
crash_clusters = sorted({e["event_date"] for e in ev if e["type"] == "crash"})
lines.append(f"- 含至少一个急跌型样本的簇：{len(crash_clusters)}/{len(clusters_with_events)}"
             f"（{', '.join(crash_clusters)}）\n")
per_cluster = defaultdict(list)
for e in ev:
    per_cluster[e["event_date"]].append(e)
lines.append("\n### 逐簇样本构成\n")
lines.append("| 簇日 | 各标的类型 |")
lines.append("|---|---|")
for c in clusters_with_events:
    cells = "; ".join(
        f"{NAME[x['symbol']]}={TYPE_CN[x['type']]}" + ("(250日内未达-10%)" if x["censored"] else "")
        for x in sorted(per_cluster[c], key=lambda x: ORDER.index(x["symbol"])))
    lines.append(f"| {c} | {cells} |")

crash_rec = [e for e in ev if e["type"] == "crash"]
n_rec = sum(1 for e in crash_rec if e["upside120_pct"] and e["upside120_pct"] > 0)
lines.append(f"\n- 急跌型 {len(crash_rec)} 个中，{n_rec} 个在 120 交易日内重新收上警报日收盘"
             f"（upside120>0）；upside120=0 的 {len(crash_rec)-n_rec} 个为"
             f"警报日即 120 日窗口最高。\n")
ep = [c for c in clusters_with_events if c >= "2024-10-01"]
n_ep = sum(len(per_cluster[c]) for c in ep)
lines.append(f"- 2024-10 之后的簇（{', '.join(ep)}）贡献 {n_ep}/{len(ev)} 个样本"
             f"（同一轮行情内的多簇）。\n")

lines.append("\n## 主表：逐标的汇总（双≥85）\n")
lines.append("| 标的 | 样本起 | 事件数 | 急跌 | 磨顶(其中250日未达-10%) | 中间 | t5中位(q1/q3,非截尾n) | t10中位(q1/q3,非截尾n) | t20中位(q1/q3,非截尾n) | 120日剩余涨幅中位(q1/q3)% | 峰值到来日中位 | 120日内创新高占比 | dd60中位% | r60中位% | r250中位% |")
lines.append("|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|")
for p in m["per_instrument"]:
    def fmt_q(q):
        return "—" if not q else f"{q['med']} ({q['q1']}/{q['q3']}, n={q['n']})"
    lines.append(
        f"| {p['name']} | {p['sample_start'][:7]} | {p['n_events']} | {p['n_crash']} | "
        f"{p['n_grind']} ({p['n_censored']}) | {p['n_middle']} | "
        f"{fmt_q(p['t5_quart'])} | {fmt_q(p['t10_quart'])} | {fmt_q(p['t20_quart'])} | "
        f"{fmt_q(p['upside120_quart'])} | {fmt_q(p['t_peak120_quart'])} | "
        f"{p['new_high120_share']} | {p['dd60_median']} | {p['r60_median']} | {p['r250_median']} |")

ps = m["pooled_stats"]
def fmt_qp(q):
    return "—" if not q else f"{q['med']} ({q['q1']}/{q['q3']}, n={q['n']})"
lines.append("\n合并池（42 可分类）：\n")
lines.append(f"- t5: {fmt_qp(ps['t5_quart'])}；截尾(250日未达-5%) {42-ps['t5_quart']['n']}/42")
lines.append(f"- t10: {fmt_qp(ps['t10_quart'])}；截尾(250日未达-10%) {42-ps['t10_quart']['n']}/42")
lines.append(f"- t20: {fmt_qp(ps['t20_quart'])}；截尾(250日未达-20%) {42-ps['t20_quart']['n']}/42")
lines.append(f"- t_below(首次收于警报日价下): {fmt_qp(ps['t_below_quart'])}；250日内从未收于警报日价下 {42-ps['t_below_quart']['n']}/42")
lines.append(f"- upside120: {fmt_qp(ps['upside120_quart'])}；t_peak120: {fmt_qp(ps['t_peak120_quart'])}")
lines.append(f"- new_high120 占比: {ps['new_high120_share']}；dd60 中位: {ps['dd60_median']}%；"
             f"r60 中位: {ps['r60_median']}%；r250 中位: {ps['r250_median']}%")

lines.append("\n## 逐事件全表（双≥85，42 行）\n")
lines.append("（t5/t10/t20/t_below 单位交易日，空白=250 交易日内未出现；"
             "upside120=警报日起 120 交易日窗口最高收盘相对警报日收盘涨幅%；"
             "t_peak=该最高点距警报日交易日数（0=警报日即窗口最高）；r60/r250=前瞻收益%；）\n")
for sym in ORDER:
    name = NAME[sym]
    lines.append(f"\n### {name}（{sym}）\n")
    lines.append("| 事件日 | 类型 | t5 | t10 | t20 | t_below | up120% | t_peak | 新高 | dd60% | r60% | r250% |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|")
    for e in sorted([x for x in ev if x["symbol"] == sym], key=lambda x: x["event_date"]):
        typ = TYPE_CN[e["type"]] + ("*" if e["censored"] else "")
        lines.append(
            f"| {e['event_date']} | {typ} | {e['t5'] if e['t5'] is not None else ''} | "
            f"{e['t10'] if e['t10'] is not None else ''} | {e['t20'] if e['t20'] is not None else ''} | "
            f"{e['t_below'] if e['t_below'] is not None else ''} | {e['upside120_pct']} | "
            f"{e['t_peak120']} | {'是' if e['new_high120'] else '否'} | {e['dd60_pct']} | "
            f"{e['r60'] if e['r60'] is not None else ''} | {e['r250'] if e['r250'] is not None else ''} |")

r90 = data["robust_90"]
lines.append("\n## 稳健性（双≥90）逐事件\n")
lines.append("| 标的 | 事件日 | 类型 | t5 | t10 | up120% | r250% |")
lines.append("|---|---|---|---:|---:|---:|---:|")
for e in sorted(r90["events"], key=lambda x: (x["event_date"], ORDER.index(x["symbol"]))):
    typ = TYPE_CN[e["type"]] + ("*" if e["censored"] else "")
    lines.append(f"| {e['name']} | {e['event_date']} | {typ} | {e['t5'] if e['t5'] is not None else ''} | "
                 f"{e['t10'] if e['t10'] is not None else ''} | {e['upside120_pct']} | "
                 f"{e['r250'] if e['r250'] is not None else ''} |")

out = RAW / "report_tables.md"
out.write_text("\n".join(lines) + "\n")
print("wrote", out, len(lines), "lines")
print("clusters covered:", len(clusters_with_events), "uncovered:", len(uncovered))
print("crash clusters:", crash_clusters)
print("crash with recovery >0:", n_rec, "/", len(crash_rec))
print("post-2024-10 cluster events:", n_ep)
