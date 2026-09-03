# -*- coding: utf-8 -*-
"""任务 AM：双≤20 极端底部——"一次到位 vs 分批（3/6/12 个月）"正体验证。

预注册全文（跑前写死，跑后不得回头调整判定线；中途发现只进诚实登记）。

【研究问题】在 A 股双≤20 极端底部事件上，假设已决定建仓：一次性满仓 vs
等额分批 3/6/12 个月投满，历史上哪个执行结构更好？只测执行结构，不回答
"该不该建仓"，不产生任何买卖规则。

【事件集（复用 AK，禁止重定义）】AK 归档
docs/experiments/raw/agent_AK/extreme_bottom_events.json 的 37 个簇 × 5 标的
共 79 个（标的×事件）样本；事件类型字段（process/event_v/middle）按 AK 原值
join 进来用于分组稳健性。本脚本从同一份行情缓存重新对齐（searchsorted、
≤7 个自然日容差，与 AK 逐字同逻辑），并断言对齐出的 (symbol, event_date)
样本集与 AK JSON 完全一致（防复用走样）。

【价格口径（复用 AK）】隔夜收盘比 >1.5 或 <1/1.5 视为公司行为、其前全部价格
乘以该比率前复权（AK 已登记 3 处：512100 2022-09-05、512480 2021-03-29、
512480 2026-07-03）。全部 close-to-close。

【执行方式（跑前写死）】总资金 C=1.0；批次在价格日历上按交易日计（"交易日均分"），
月间隔 = 21 个交易日（A 股月均交易日数的机械近似，注册为固定常数）。
  - lump（基准）：事件交易日 t0 收盘一次性满仓。
  - staged_3m/6m/12m：等额 M∈{3,6,12} 笔，第 k 笔（k=0..M-1）在 t0+21k 收盘，
    每笔 C/M；无信号联动、不作废、不中断。建仓完成日 = t0+21(M-1)。
  - 若某批次的索引超出价格序列末端：该（事件×档位）样本记缺失，不外推不编造。
  - 费用：每笔买入按名义额 10bp（0.001）从可买金额中扣。出处：
    docs/experiments/raw/kuandu-quanzhan/champion_cyb.json params.fee_bps=10.0；
    docs/experiments/kuandu-quanzhan-ARCHIVE-2026-09-01.md"统一口径：费用 10bp
    双边"。持有到期末不收卖出费（两方式对称，且不改变差异方向）。
  - 现金不计利息（登记为对分批偏保守的设定：分批期间平均约一半资金趴在现金上，
    现实中货基收益约 1.5-2%/年、半年约 +0.5-0.7pp 未计入）。

【度量（每事件×每方式，全部用复权收盘）】
  1. ret250：建仓完成日后第 250 个交易日的账户总值 / C - 1（净费）。
     要求 build_end+250 在序列内，否则缺失。lump 的 build_end=t0。
  2. cost_diff_pp：分批真实平均成本（等额资金 → 批次价格的调和平均）相对
     lump 成本 P(t0) 之差（pp，正=分批更贵）。lump 恒为 0。
  3. dd：窗口 [t0, build_end+250] 内账户总值（现金+市值）从运行峰值的最大回撤
     （%）。**按任务书字面口径：各方式用各自窗口**（lump 为 1 年窗，12 个月
     分批为约 2 年窗——窗口更长只会让分批的回撤更深或持平，该偏差方向对
     "分批改善回撤"的结论是保守的）。与 ret250 同一可得性条件。
  4. 换手与费用：各方式建仓买入名义总额均 = C，总费用均 = 10bp（构造上恒等），
     单列登记以证明费用不构成区分因素。
  5. 对齐口径（注册的稳健性补充，不参与判定）：同档位下 lump 与 staged 共用
     终点 t0+21(M-1)+250 与同窗回撤，消除窗口错位（AE 报告第 8.3 节的批评）。

【配对差异（每事件×每档位）】
  - ret_cost_pp = lump.ret250 - staged.ret250（正 = 分批少赚，"收益代价"）。
  - dd_impr_pp = lump.dd - staged.dd（回撤为负数，正 = 分批亏得更浅，"回撤改善"）。

【聚合】每档位（3/6/12 月分别判定，12 个月档单列）：合并池中位数与四分位、
正占比；分标的中位数（配对样本 ≥2 的标的才有资格）；AK 类型分组
（process/middle/event_v）中位数做稳健性；配对符号检验（精确二项、双侧，
math.comb 手写确定性实现——统计描述用，不参与判定线）。

【预注册判定线（跑前写死，数值论证如下）】
  - X（回撤改善门槛）= 3.0 pp（中位数）。论证：AK 证明警报后 60 日内还有
    -5.5%~-10.7%（中位）的二次下探；"分批实质改善回撤"至少要吃下这口深度的
    一半（约 3pp）才叫实质；与 AE 预注册的 +3pp 回撤线同值，跨任务可比。
  - Y（收益代价容忍线）= 1.5 pp（中位数）。论证：与 AE 预注册的 +1.5pp 收益
    实质性线互为镜像；事件后 r250 中位数为 +3%~+32%，1.5pp ≤ 典型一年中位
    收益的一半，且远大于费用差（恒 0）；超出即认为代价不再是"噪声级"。
  - 样本下限：合并池配对数 ≥10 该档位才有资格判定，否则"证据不足"；
    单标的配对数 ≥2 才参与"3/5 标的"计数。
  - 三选一（每档位独立判定）：
    a) 分批有实质改善：合并池 dd_impr 中位 ≥3.0 且 ret_cost 中位 ≤1.5，
       且 ≥3 个有资格标的各自同时满足（dd_impr 中位 ≥3.0 且 ret_cost 中位 ≤1.5）。
    b) 一次性更好：合并池 ret_cost 中位 >1.5 且 dd_impr 中位 <3.0，
       且 ≥3 个有资格标的 ret_cost 中位 >1.5。
    c) 其余（含两维度都有实质效果但方向相反的"交换"情形）：无实质差异。

【红线遵守】不回答"该不该建仓"；不设计买卖规则；事件定义复用 AK；
不使用买卖指令类词汇。本 docstring 即预注册全文。

输出：docs/experiments/raw/agent_AM/extreme_bottom_staged_entry.json
      docs/experiments/raw/agent_AM/report_tables.md（报告用 markdown 表格）
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
TIMING = CACHE / "timing"
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs/experiments/raw/agent_AM"
AK_JSON = ROOT / "docs/experiments/raw/agent_AK/extreme_bottom_events.json"

INSTRUMENTS = {
    "399006": ("创业板指", TIMING / "399006.parquet"),
    "000300": ("沪深300", TIMING / "000300.parquet"),
    "512100": ("中证1000ETF", TIMING / "512100.parquet"),
    "000688.SH": ("科创50", CACHE / "000688.SS.bars.parquet"),
    "512480": ("半导体ETF", TIMING / "512480.parquet"),
}

# ---- 预注册常数（跑前写死）----
FEE = 0.001            # 10bp 单边（每笔买入名义额）
MONTH_TD = 21          # 月间隔 = 21 交易日
TIERS = {"3m": 3, "6m": 6, "12m": 12}
HOLD = 250             # 建仓完成后持有观察窗（交易日）
X_DD = 3.0             # 回撤改善门槛（pp，中位）
Y_RET = 1.5            # 收益代价容忍线（pp，中位）
MIN_POOLED = 10        # 档位判定最低配对数
MIN_PER_INSTR = 2      # 标的参与 3/5 计数的最低配对数
MIN_INSTR_PASS = 3     # "≥3/5 标的"


def adjust_corporate_actions(close: pd.Series):
    """与 AK 逐字同逻辑：隔夜 |±50%| 视为公司行为，前复权。"""
    ret = close / close.shift(1)
    jumps = []
    adj = close.copy()
    for idx in ret.index[(ret > 1.5) | (ret < 1 / 1.5)]:
        pos = close.index.get_loc(idx)
        ratio = float(close.iloc[pos] / close.iloc[pos - 1])
        adj.iloc[:pos] = adj.iloc[:pos] * ratio
        jumps.append({"date": str(pd.Timestamp(idx).date()),
                      "overnight_ratio": round(ratio, 4)})
    return adj, jumps


def med(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return round((s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2), 2)


def q(xs, p):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return round(float(np.percentile(np.array(xs, dtype=float), p)), 2)


def sign_test(diffs):
    """配对符号检验（精确二项、双侧、确定性）。零假设：中位差=0。"""
    nz = [d for d in diffs if d is not None and d != 0]
    n = len(nz)
    if n == 0:
        return {"n_nonzero": 0, "k_pos": 0, "p_two_sided": None}
    k = sum(1 for d in nz if d > 0)
    tail = sum(math.comb(n, i) for i in range(min(k, n - k) + 1)) / (2 ** n)
    return {"n_nonzero": n, "k_pos": k, "p_two_sided": round(min(1.0, 2 * tail), 4)}


def account_path(px_vals, i0, i_end, tranches):
    """账户总值路径（现金+市值），索引 [i0..i_end] 含两端。
    tranches: list of (idx, units_bought, capital_spent)，按 idx 升序。"""
    vals = np.empty(i_end - i0 + 1)
    spent = 0.0
    units = 0.0
    ti = 0
    for i in range(i0, i_end + 1):
        while ti < len(tranches) and tranches[ti][0] <= i:
            _, u, c = tranches[ti]
            units += u
            spent += c
            ti += 1
        vals[i - i0] = 1.0 - spent + units * px_vals[i]
    return vals


def max_drawdown(vals):
    peak = np.maximum.accumulate(vals)
    return float(((vals - peak) / peak).min()) * 100.0


def evaluate(px, px_vals, i0, m, p0):
    """一个事件×一个档位的度量。m=0 表示 lump。批次越界或观测窗不足 → 缺失。"""
    if m == 0:
        idxs = [i0]
        units_list = [(1.0 * (1 - FEE)) / p0]
        n_trades = 1
    else:
        idxs, units_list = [], []
        for k in range(m):
            i = i0 + MONTH_TD * k
            if i >= len(px_vals):
                return None  # 批次越界：整档位缺失
            idxs.append(i)
            units_list.append((1.0 / m) * (1 - FEE) / float(px_vals[i]))
        n_trades = m
    b_end = idxs[-1]
    i_meas = b_end + HOLD
    tranches = [(idxs[k], units_list[k],
                 1.0 if m == 0 else 1.0 / m) for k in range(len(idxs))]
    if i_meas >= len(px_vals):
        ret250, dd = None, None
    else:
        units = sum(units_list)
        ret250 = round((units * float(px_vals[i_meas]) - 1.0) * 100, 2)
        dd = round(max_drawdown(account_path(px_vals, i0, i_meas, tranches)), 2)
    if m == 0:
        cost_diff = 0.0
    else:
        prices = [float(px_vals[i]) for i in idxs]
        harm = len(prices) / sum(1.0 / p for p in prices)  # 等额资金真实成本
        cost_diff = round((harm / p0 - 1.0) * 100, 2)
    return {
        "ret250_pct": ret250, "dd_pct": dd, "cost_diff_pp": cost_diff,
        "n_trades": n_trades, "fee_total_bp": round(FEE * 1.0 * 1e4, 1),
        "build_end_idx": int(b_end),
    }


def evaluate_aligned(px_vals, i0, m, p0):
    """对齐口径：lump 与 staged 共用终点与同窗（稳健性，不参与判定）。"""
    idxs = [i0 + MONTH_TD * k for k in range(m)]
    if idxs[-1] >= len(px_vals):
        return None
    i_meas = idxs[-1] + HOLD
    if i_meas >= len(px_vals):
        return None
    p_end = float(px_vals[i_meas])
    staged_units = sum((1.0 / m) * (1 - FEE) / float(px_vals[i]) for i in idxs)
    lump_units = (1.0 * (1 - FEE)) / p0
    staged_tr = [(idxs[k], (1.0 / m) * (1 - FEE) / float(px_vals[idxs[k]]), 1.0 / m)
                 for k in range(m)]
    lump_tr = [(i0, lump_units, 1.0)]
    return {
        "lump_ret": round((lump_units * p_end - 1.0) * 100, 2),
        "staged_ret": round((staged_units * p_end - 1.0) * 100, 2),
        "lump_dd": round(max_drawdown(account_path(px_vals, i0, i_meas, lump_tr)), 2),
        "staged_dd": round(max_drawdown(account_path(px_vals, i0, i_meas, staged_tr)), 2),
    }


def _fmt(x, suffix=""):
    return "" if x is None else f"{x:+.2f}{suffix}" if isinstance(x, float) else str(x)


def main() -> None:
    ak = json.loads(AK_JSON.read_text())
    ak_map = {(e["symbol"], e["event_date"]): e for e in ak["events"]}

    events = []       # 逐事件：含各档位度量
    all_jumps = []
    for sym, (name, path) in INSTRUMENTS.items():
        raw_px = pd.read_parquet(path)["close"].dropna()
        raw_px = raw_px[~raw_px.index.duplicated(keep="last")].sort_index()
        px, jumps = adjust_corporate_actions(raw_px)
        all_jumps.extend({"symbol": sym, **j} for j in jumps)
        px_vals = px.to_numpy(dtype=float)
        for d in ak["clusters"]:
            loc = px.index.searchsorted(pd.Timestamp(d))
            if loc >= len(px):
                continue
            aligned = px.index[loc]
            if (aligned - pd.Timestamp(d)).days > 7:
                continue
            if (sym, d) not in ak_map:
                raise AssertionError(f"对齐出 AK 外的样本: {sym} {d}")
            ak_e = ak_map[(sym, d)]
            assert ak_e["event_trade_date"] == str(pd.Timestamp(aligned).date())
            i0 = loc
            p0 = float(px_vals[i0])
            ev = {
                "symbol": sym, "name": name, "event_date": d,
                "event_trade_date": ak_e["event_trade_date"], "type": ak_e["type"],
                "p0": round(p0, 4),
                "lump": evaluate(px, px_vals, i0, 0, p0),
            }
            ev["tiers"] = {tier: evaluate(px, px_vals, i0, m, p0)
                           for tier, m in TIERS.items()}
            ev["aligned"] = {tier: evaluate_aligned(px_vals, i0, m, p0)
                             for tier, m in TIERS.items()}
            events.append(ev)

    got = {(e["symbol"], e["event_date"]) for e in events}
    want = set(ak_map.keys())
    assert got == want, f"样本集不一致: 仅本脚本{got - want} 仅AK{want - got}"

    # ---- 配对差异（每事件×档位） ----
    pairs = []
    for e in events:
        lump = e["lump"]
        for tier, m in TIERS.items():
            st = e["tiers"][tier]
            ok = st is not None and lump["ret250_pct"] is not None \
                and st["ret250_pct"] is not None
            pairs.append({
                "symbol": e["symbol"], "name": e["name"],
                "event_date": e["event_date"], "type": e["type"], "tier": tier,
                "lump_ret250": lump["ret250_pct"], "lump_dd": lump["dd_pct"],
                "staged_ret250": st["ret250_pct"] if st else None,
                "staged_dd": st["dd_pct"] if st else None,
                "ret_cost_pp": round(lump["ret250_pct"] - st["ret250_pct"], 2) if ok else None,
                "dd_impr_pp": round(st["dd_pct"] - lump["dd_pct"], 2)
                              if (st and st["dd_pct"] is not None
                                  and lump["dd_pct"] is not None) else None,
                "cost_diff_pp": st["cost_diff_pp"] if st else None,
                "complete": ok,
            })

    # ---- 聚合 + 判定（按预注册线，机械执行） ----
    tiers_out = {}
    for tier, m in TIERS.items():
        tp = [p for p in pairs if p["tier"] == tier and p["complete"]]
        pooled_rc = [p["ret_cost_pp"] for p in tp]
        pooled_dd = [p["dd_impr_pp"] for p in tp]
        per_instr = {}
        for sym, (name, _) in sorted(INSTRUMENTS.items()):
            ip = [p for p in tp if p["symbol"] == sym]
            per_instr[sym] = {
                "name": name, "n": len(ip),
                "ret_cost_med": med([p["ret_cost_pp"] for p in ip]),
                "dd_impr_med": med([p["dd_impr_pp"] for p in ip]),
                "cost_diff_med": med([p["cost_diff_pp"] for p in ip]),
            }
        by_type = {}
        for t in ("process", "middle", "event_v"):
            gp = [p for p in tp if p["type"] == t]
            by_type[t] = {
                "n": len(gp),
                "ret_cost_med": med([p["ret_cost_pp"] for p in gp]),
                "dd_impr_med": med([p["dd_impr_pp"] for p in gp]),
            }
        aligned = [e["aligned"][tier] for e in events if e["aligned"][tier]]
        al_rc = [round(a["lump_ret"] - a["staged_ret"], 2) for a in aligned]
        al_dd = [round(a["staged_dd"] - a["lump_dd"], 2) for a in aligned]
        rc_med, dd_med = med(pooled_rc), med(pooled_dd)
        qual = {s: v for s, v in per_instr.items() if v["n"] >= MIN_PER_INSTR}
        n_pass_both = sum(1 for v in qual.values()
                          if v["dd_impr_med"] is not None
                          and v["dd_impr_med"] >= X_DD
                          and v["ret_cost_med"] is not None
                          and v["ret_cost_med"] <= Y_RET)
        n_fail_ret = sum(1 for v in qual.values()
                         if v["ret_cost_med"] is not None and v["ret_cost_med"] > Y_RET)
        if len(tp) < MIN_POOLED:
            verdict = "证据不足（配对数<10）"
        elif (dd_med is not None and dd_med >= X_DD and rc_med is not None
              and rc_med <= Y_RET and n_pass_both >= MIN_INSTR_PASS):
            verdict = "分批有实质改善"
        elif (rc_med is not None and rc_med > Y_RET and dd_med is not None
              and dd_med < X_DD and n_fail_ret >= MIN_INSTR_PASS):
            verdict = "一次性更好"
        else:
            verdict = "无实质差异"
        tiers_out[tier] = {
            "m": m, "n_paired": len(tp), "n_events": len(
                [p for p in pairs if p["tier"] == tier]),
            "pooled": {
                "ret_cost_med": rc_med, "ret_cost_q1": q(pooled_rc, 25),
                "ret_cost_q3": q(pooled_rc, 75),
                "ret_cost_pos_share": round(
                    sum(1 for x in pooled_rc if x > 0) / len(pooled_rc), 3)
                if pooled_rc else None,
                "dd_impr_med": dd_med, "dd_impr_q1": q(pooled_dd, 25),
                "dd_impr_q3": q(pooled_dd, 75),
                "dd_impr_pos_share": round(
                    sum(1 for x in pooled_dd if x > 0) / len(pooled_dd), 3)
                if pooled_dd else None,
                "cost_diff_med": med([p["cost_diff_pp"] for p in tp]),
            },
            "per_instrument": per_instr,
            "by_type": by_type,
            "sign_test_ret_cost": sign_test(pooled_rc),
            "sign_test_dd_impr": sign_test(pooled_dd),
            "aligned_n": len(aligned),
            "aligned_ret_cost_med": med(al_rc), "aligned_dd_impr_med": med(al_dd),
            "verdict": verdict,
        }

    result = {
        "prereg": "见 scripts/agent_AM/extreme_bottom_staged_entry_validation.py docstring（跑前写死）",
        "constants": {"fee": FEE, "month_td": MONTH_TD, "hold": HOLD,
                      "X_dd_pp": X_DD, "Y_ret_pp": Y_RET,
                      "min_pooled": MIN_POOLED, "min_per_instr": MIN_PER_INSTR,
                      "min_instr_pass": MIN_INSTR_PASS},
        "corporate_action_adjustments": all_jumps,
        "n_events": len(events),
        "events": events,
        "pairs": pairs,
        "tiers": tiers_out,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True,
                         default=str)
    (OUT_DIR / "extreme_bottom_staged_entry.json").write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()

    # ---- 报告用 markdown 表格 ----
    md = []
    md.append("<!-- 自动生成：报告表格片段（agent_AM） -->\n")
    md.append("## tier 总表（主口径）\n")
    md.append("| 档位 | 配对N | 收益代价中位pp (q1/q3) | 分批少赚占比 | 回撤改善中位pp (q1/q3) | 回撤更浅占比 | 成本差中位pp | 符号检验p(收益/回撤) | 判定 |")
    md.append("|---|---:|---|---:|---|---:|---:|---|---|")
    for tier in TIERS:
        t = tiers_out[tier]
        p = t["pooled"]
        md.append(
            f"| {tier} | {t['n_paired']} "
            f"| {p['ret_cost_med']} ({p['ret_cost_q1']}/{p['ret_cost_q3']}) "
            f"| {p['ret_cost_pos_share']} "
            f"| {p['dd_impr_med']} ({p['dd_impr_q1']}/{p['dd_impr_q3']}) "
            f"| {p['dd_impr_pos_share']} | {p['cost_diff_med']} "
            f"| {t['sign_test_ret_cost']['p_two_sided']} / {t['sign_test_dd_impr']['p_two_sided']} "
            f"| {t['verdict']} |")
    md.append("\n## 分标的（中位数 pp）\n")
    for tier in TIERS:
        md.append(f"\n### {tier}\n")
        md.append("| 标的 | N | 收益代价中位 | 回撤改善中位 | 成本差中位 |")
        md.append("|---|---:|---:|---:|---:|")
        for sym, v in tiers_out[tier]["per_instrument"].items():
            md.append(f"| {v['name']} {sym} | {v['n']} | {v['ret_cost_med']} "
                      f"| {v['dd_impr_med']} | {v['cost_diff_med']} |")
    md.append("\n## 类型分组（中位数 pp）\n")
    md.append("| 档位 | 过程型N/代价/改善 | 中间型N/代价/改善 | V型N/代价/改善 |")
    md.append("|---|---|---|---|")
    for tier in TIERS:
        b = tiers_out[tier]["by_type"]
        md.append(f"| {tier} | {b['process']['n']}/{b['process']['ret_cost_med']}/{b['process']['dd_impr_med']} "
                  f"| {b['middle']['n']}/{b['middle']['ret_cost_med']}/{b['middle']['dd_impr_med']} "
                  f"| {b['event_v']['n']}/{b['event_v']['ret_cost_med']}/{b['event_v']['dd_impr_med']} |")
    md.append("\n## 对齐口径（稳健性；共用终点与同窗）\n")
    md.append("| 档位 | N | 收益代价中位pp | 回撤改善中位pp |")
    md.append("|---|---:|---:|---:|")
    for tier in TIERS:
        t = tiers_out[tier]
        md.append(f"| {tier} | {t['aligned_n']} | {t['aligned_ret_cost_med']} | {t['aligned_dd_impr_med']} |")
    md.append("\n## 逐事件明细（主口径）\n")
    for tier in TIERS:
        md.append(f"\n### {tier}\n")
        md.append("| 标的 | 事件日 | 类型 | 一次性ret250% | 分批ret250% | 收益代价pp | 一次性dd% | 分批dd% | 回撤改善pp | 成本差pp |")
        md.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for p in pairs:
            if p["tier"] != tier:
                continue
            md.append(
                f"| {p['name']} | {p['event_date']} | {p['type']} "
                f"| {_fmt(p['lump_ret250'])} | {_fmt(p['staged_ret250'])} "
                f"| {_fmt(p['ret_cost_pp'])} | {_fmt(p['lump_dd'])} "
                f"| {_fmt(p['staged_dd'])} | {_fmt(p['dd_impr_pp'])} "
                f"| {_fmt(p['cost_diff_pp'])} |")
    (OUT_DIR / "report_tables.md").write_text("\n".join(md) + "\n")

    print("hash:", digest)
    print("events:", len(events))
    for tier in TIERS:
        t = tiers_out[tier]
        print(tier, "N=", t["n_paired"],
              "ret_cost_med=", t["pooled"]["ret_cost_med"],
              "dd_impr_med=", t["pooled"]["dd_impr_med"],
              "cost_med=", t["pooled"]["cost_diff_med"],
              "verdict=", t["verdict"])


if __name__ == "__main__":
    sys.exit(main())
