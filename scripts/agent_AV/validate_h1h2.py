#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模块B 栖息地过滤假设 H1/H2 正式验证（Prompt AV，2026-09-04）

=====================================================================
预注册（2026-09-04 跑前写死，跑后不得回头调）
=====================================================================
任务：验证 AO 在 ETF 池 37 笔上登记的两条栖息地过滤假设——
  H1：入场时标的自身 60 日波动率分位贴地（rv60_pctl < 20）的信号期望劣化；
  H2：入场时 20 日宽度 5 年分位拉满（b20_pctl5y >= 80）的信号大赢缺席。
以 AQ 个股池 98 笔已平仓交易为独立样本做主检验；ETF 池做时间对半分段
稳定性辅助。判定对象是"过滤假设成立与否"，不是"要不要启用过滤"。

【样本（冻结）】
- 独立样本（主检验）：AQ 个股池 98 笔已平仓交易。
  来源 docs/experiments/raw/agent_AQ/moduleB_stock_pool.json：
  trades_detail 共 99 行，剔除 exit_reason=invalid_nonpositive_risk 的
  1 笔（600519.SS 2025-04-03，r_net=0.0，holding_bars=0）——该笔不进任何
  指标，仅在明细表登记其标签。逐笔 AO 标签取
  habitat_labels_descriptive.trades，按 (symbol, signal_date) 一对一连接。
- ETF 池（辅助）：docs/experiments/raw/module_b_regime/moduleB_regime.json
  ::state_table 全部 37 行（均为已平仓）。

【过滤规则（AO 登记原口径，边界一字不改，不得微调）】
- H1 命中 = rv60_pctl < 20.0（0-100 分位制）→ 该笔被过滤。
- H2 命中 = b20_pctl5y >= 80.0 → 该笔被过滤。
- b20 标签为 null 的笔（晚于宽度文件末端、仅 1 笔）在 H2 下视为未命中
  （保留在过滤后池中），如实登记；rv60 标签无 null。
- H1、H2 单独测，不组合（组合是下一层的事）。

【锚校验（任一不过则中止并如实报告，不得继续判定）】
A1. AO 37 笔 r_net 均值 = +0.9441（|diff| <= 0.0005）。
A2. AQ habitat 标签表 99 行与 trades_detail 一对一连接成功且 r_net 逐笔一致。
A3. 本脚本按全部 99 行（含无效笔）复算的 rv60/b20 桶统计（n、mean_r、sum_r）
    与 AQ JSON 已发表的 bucket_stats_rv60 / bucket_stats_b20 逐桶一致
    （容差 1e-6，键按桶名对齐）。
A4. 数值规则与桶标签逐笔一致（两池、两变量）：
    (rv60_pctl < 20) <=> 桶名以 "Q1" 开头；(b20_pctl5y >= 80) <=> 桶名以
    "Q5" 开头（b20 为 null 的行豁免）。

【主检验量（个股池 98 笔，对 H1、H2 各自）】
E0 = 全 98 笔 r 均值；E1 = 剔除命中笔后均值；EF = 命中笔均值；NF = 命中笔数。
登记过滤前后胜率（r>0 占比）、赢单均/输单均、被剔除笔逐笔明细、
两池 top5 大赢单是否落入命中桶（描述性，不参与判定）。

【ETF 分段（冻结切法）】
37 笔按 (signal_date, symbol) 升序排序：前 18 笔为 A 段、后 19 笔为 B 段。
段内方向一致 <=> 段内命中笔均值 <= 段内保留笔均值；段内无命中笔记"无矛盾"
（视为一致，如实登记）。按年份的分布另作描述性附表，不参与判定。

【三选一判定线（按序求值，命中即止；对 H1、H2 分别判）】
1. 成立  <=> (E1 - E0 >= +0.20) 且 (EF < 0) 且 (ETF A、B 两段方向均一致)。
2. 不成立 <=> (E1 - E0 <= 0) 或 (EF > 0 且 NF >= 10)。
3. 其余 -> 证据不足。

【判定线论证（跑前写死）】
- +0.20 改善线 = 个股池整体 expR（+0.726，AQ 已发表）的约 28%：一个"成立"
  的栖息地过滤必须在独立样本上把单笔期望提高超过整体边际的四分之一量级，
  低于此线只判"方向一致但证据不足"。披露：AQ §5.3 已发表两池桶均值（任务书
  本身引用），线的选择无法对桶均值完全无盲；本线只锚定跑前已发表量
  （AQ 整体 expR），不锚定本任务任何新算出的数。
- EF < 0：任务书成立条件之二（被过滤交易平均为负）。
- ETF 分段一致：任务书成立条件之三（分段方向不翻转）的机械化。
- NF >= 10：独立样本命中桶至少 10 笔才足以断言"栖息地为正"的方向反证；
  不足 10 笔的正桶只登记、判证据不足。10 = AQ 池 b20-Q5 已发表桶容量。

【解释性诊断 D1（不参与判定，跑前声明；结论将标注"解释性、不可判定"）】
两池 rv60-Q1 命中笔的年份分布；个股池命中笔 rv_series_n 分布（<756 短窗、
<250 极短窗占比）；年代切片（2016-2018 vs 2019+）两池 rv60-Q1 桶均值对照
（机制讨论用：两池"贴地桶"是否根本不住在同一类行情里）。

【输出与双跑】
输出 docs/experiments/raw/agent_AV/h1h2_validation.json（新增文件）。
PYTHONHASHSEED=0 与 =42 各跑一次，规范化 JSON（sort_keys、定容差舍入）
sha256 必须一致，写 stdout 供日志留档。纯确定性计算（json+算术，无随机源、
无 pandas 依赖）。

【红线】验证过滤假设不等于启用过滤；不微调边界；无显著性断言；
不使用买卖指令类词汇；只读两个既有 JSON；不执行任何 git 写操作；
不改任何既有文件，产出全部为新增。
=====================================================================

用法：
  PYTHONHASHSEED=0 python3 scripts/agent_AV/validate_h1h2.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

LAB = "/Users/yongbiaoli/Desktop/lei-signal-lab"
AO_JSON = os.path.join(LAB, "docs/experiments/raw/module_b_regime/moduleB_regime.json")
AQ_JSON = os.path.join(LAB, "docs/experiments/raw/agent_AQ/moduleB_stock_pool.json")
OUT_JSON = os.path.join(LAB, "docs/experiments/raw/agent_AV/h1h2_validation.json")

H1_LINE = 20.0   # rv60_pctl < 20 -> 命中（AO 原口径，冻结）
H2_LINE = 80.0   # b20_pctl5y >= 80 -> 命中（AO 原口径，冻结）
DELTA_PASS = 0.20   # 成立改善线（跑前写死）
NF_REVERSAL_MIN = 10  # 方向反证所需最小命中笔数（跑前写死）


def r4(x):
    return None if x is None else round(x, 4)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def stats_block(rs):
    """一组 r 值的描述统计（r>0 为赢单）。"""
    rs = list(rs)
    n = len(rs)
    if n == 0:
        return {"n": 0}
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    return {
        "n": n,
        "expR": r4(mean(rs)),
        "sum_r": r4(sum(rs)),
        "win_rate": r4(len(wins) / n),
        "avg_win_r": r4(mean(wins)),
        "avg_loss_r": r4(mean(losses)),
        "n_win": len(wins),
        "n_loss": len(losses),
    }


def trade_brief(t, extra_keys):
    row = {
        "symbol": t["symbol"],
        "signal_date": t["signal_date"],
        "r_net": t["r_net"],
        "year": t["signal_date"][:4],
    }
    for k in extra_keys:
        row[k] = t.get(k)
    return row


def main():
    ao = json.load(open(AO_JSON))
    aq = json.load(open(AQ_JSON))

    # ---------------- 锚校验 ----------------
    anchors = {}
    etf = ao["state_table"]
    etf_expR = mean([t["r_net"] for t in etf])
    anchors["A1_ao_N37_expR"] = {"N": len(etf), "expR": r4(etf_expR),
                                 "pass": len(etf) == 37 and abs(etf_expR - 0.9441) <= 0.0005}

    hl = aq["habitat_labels_descriptive"]["trades"]
    td = {(t["symbol"], t["signal_date"]): t for t in aq["trades_detail"]}
    join_ok = (len(hl) == 99 and len(td) == 99
               and all((h["symbol"], h["signal_date"]) in td for h in hl)
               and all(abs(h["r_net"] - td[(h["symbol"], h["signal_date"])]["r_net"]) <= 1e-9 for h in hl))
    anchors["A2_aq_join_99"] = {"pass": join_ok}

    # A3：按 99 行复算 AQ 桶统计并对表
    def bucket_stats(rows, key):
        out = {}
        for h in rows:
            b = h[key]
            b = "null" if b is None else b
            out.setdefault(b, []).append(h["r_net"])
        return {b: {"n": len(v), "mean_r": r4(mean(v)), "sum_r": r4(sum(v))} for b, v in out.items()}

    mine_rv = bucket_stats(hl, "rv60_bucket")
    mine_b20 = bucket_stats(hl, "b20_bucket")

    def cmp_stats(mine, pub):
        diffs = []
        for b, s in pub.items():
            m = mine.get(b)
            if m is None:
                diffs.append(f"{b}: missing")
                continue
            if m["n"] != s["n"]:
                diffs.append(f"{b}: n {m['n']}vs{s['n']}")
            ps = s.get("sum_r")
            if ps is not None and abs(m["sum_r"] - ps) > 1e-6:
                diffs.append(f"{b}: sum {m['sum_r']}vs{ps}")
            pm = s.get("mean_r")
            if pm is not None and abs(m["mean_r"] - pm) > 1e-4:
                diffs.append(f"{b}: mean {m['mean_r']}vs{pm}")
        return diffs

    d_rv = cmp_stats(mine_rv, aq["habitat_labels_descriptive"]["bucket_stats_rv60"])
    d_b20 = cmp_stats(mine_b20, aq["habitat_labels_descriptive"]["bucket_stats_b20"])
    anchors["A3_aq_bucket_stats_match"] = {"rv60_diffs": d_rv, "b20_diffs": d_b20,
                                           "pass": not d_rv and not d_b20}

    # A4：数值规则 vs 桶标签（两池）
    a4_bad = []
    for h in hl:
        if (h["rv60_pctl"] < H1_LINE) != (str(h["rv60_bucket"]).startswith("Q1")):
            a4_bad.append(["AQ", h["symbol"], h["signal_date"], "rv60", h["rv60_pctl"], h["rv60_bucket"]])
        if h["b20_pctl5y"] is not None and (h["b20_pctl5y"] >= H2_LINE) != (str(h["b20_bucket"]).startswith("Q5")):
            a4_bad.append(["AQ", h["symbol"], h["signal_date"], "b20", h["b20_pctl5y"], h["b20_bucket"]])
    for t in etf:
        if (t["rv60_pctl"] < H1_LINE) != (str(t["bk_rv60_pctl"]).startswith("Q1")):
            a4_bad.append(["ETF", t["symbol"], t["signal_date"], "rv60", t["rv60_pctl"], t["bk_rv60_pctl"]])
        if t["b20_pctl5y"] is None or (t["b20_pctl5y"] >= H2_LINE) != (str(t["bk_b20_pctl5y"]).startswith("Q5")):
            a4_bad.append(["ETF", t["symbol"], t["signal_date"], "b20", t["b20_pctl5y"], t["bk_b20_pctl5y"]])
    anchors["A4_rule_label_consistency"] = {"n_bad": len(a4_bad), "bad": a4_bad, "pass": not a4_bad}

    all_anchors_pass = all(v["pass"] for v in anchors.values())
    if not all_anchors_pass:
        out = {"task": "AV h1h2 验证", "anchors": anchors, "aborted": "锚校验未过，按预注册中止"}
        dump(out)
        print(json.dumps({"aborted": True, "anchors": anchors}, ensure_ascii=False, indent=1))
        sys.exit(2)

    # ---------------- 样本冻结 ----------------
    stock_all = [dict(h, exit_reason=td[(h["symbol"], h["signal_date"])]["exit_reason"],
                      entry_date=td[(h["symbol"], h["signal_date"])]["entry_date"]) for h in hl]
    invalid = [t for t in stock_all if t["exit_reason"] == "invalid_nonpositive_risk"]
    stock = [t for t in stock_all if t["exit_reason"] != "invalid_nonpositive_risk"]
    assert len(invalid) == 1 and len(stock) == 98

    def hit_h1(t):
        return t["rv60_pctl"] < H1_LINE

    def hit_h2(t):
        return t["b20_pctl5y"] is not None and t["b20_pctl5y"] >= H2_LINE

    # ---------------- 主检验（个股池 98 笔） ----------------
    def pool_filter_eval(rows, hitf):
        hits = [t for t in rows if hitf(t)]
        kept = [t for t in rows if not hitf(t)]
        e0 = mean([t["r_net"] for t in rows])
        e1 = mean([t["r_net"] for t in kept])
        ef = mean([t["r_net"] for t in hits])
        return {
            "before": stats_block([t["r_net"] for t in rows]),
            "after": stats_block([t["r_net"] for t in kept]),
            "filtered": stats_block([t["r_net"] for t in hits]),
            "delta_expR": r4((e1 - e0) if e1 is not None else None),
            "filtered_detail": [trade_brief(t, ["rv60_pctl", "rv60_ann", "rv_series_n",
                                                "b20_raw", "b20_pctl5y", "exit_reason"]) for t in hits],
        }

    h1_stock = pool_filter_eval(stock, hit_h1)
    h2_stock = pool_filter_eval(stock, hit_h2)

    # top5 大赢与命中桶的关系（描述性）
    def top5(rows, hitf, tag):
        srt = sorted(rows, key=lambda t: -t["r_net"])[:5]
        return [{"symbol": t["symbol"], "signal_date": t["signal_date"], "r_net": t["r_net"],
                 "hit_" + tag: bool(hitf(t))} for t in srt]

    top5_stock = {"H1": top5(stock, hit_h1, "H1"), "H2": top5(stock, hit_h2, "H2")}
    top5_etf = {"H1": top5(etf, hit_h1, "H1"), "H2": top5(etf, hit_h2, "H2")}

    # ---------------- ETF 分段稳定性（辅助） ----------------
    etf_sorted = sorted(etf, key=lambda t: (t["signal_date"], t["symbol"]))
    segA, segB = etf_sorted[:18], etf_sorted[18:]

    def seg_eval(seg_rows, hitf):
        hits = [t["r_net"] for t in seg_rows if hitf(t)]
        kept = [t["r_net"] for t in seg_rows if not hitf(t)]
        if not hits:
            return {"n": len(seg_rows), "n_hit": 0, "verdict_seg": "无矛盾（段内无命中笔）",
                    "consistent": True,
                    "date_range": [seg_rows[0]["signal_date"], seg_rows[-1]["signal_date"]]}
        mh, mk = mean(hits), mean(kept) if kept else None
        return {"n": len(seg_rows), "n_hit": len(hits),
                "mean_r_hit": r4(mh), "mean_r_kept": r4(mk),
                "sum_r_hit": r4(sum(hits)),
                "consistent": (mk is None) or (mh <= mk),
                "verdict_seg": "一致" if ((mk is None) or (mh <= mk)) else "翻转",
                "date_range": [seg_rows[0]["signal_date"], seg_rows[-1]["signal_date"]],
                "hit_trades": [trade_brief(t, ["rv60_pctl", "b20_pctl5y"]) for t in seg_rows if hitf(t)]}

    etf_seg = {
        "split_rule": "按 (signal_date, symbol) 升序，前18为A段、后19为B段（跑前冻结）",
        "H1": {"A": seg_eval(segA, hit_h1), "B": seg_eval(segB, hit_h1)},
        "H2": {"A": seg_eval(segA, hit_h2), "B": seg_eval(segB, hit_h2)},
    }

    # ETF 全样本（对表用）
    etf_full = {
        "H1": {"filtered": stats_block([t["r_net"] for t in etf if hit_h1(t)]),
               "kept": stats_block([t["r_net"] for t in etf if not hit_h1(t)]),
               "delta_expR": r4(mean([t["r_net"] for t in etf if not hit_h1(t)]) - etf_expR)},
        "H2": {"filtered": stats_block([t["r_net"] for t in etf if hit_h2(t)]),
               "kept": stats_block([t["r_net"] for t in etf if not hit_h2(t)]),
               "delta_expR": r4(mean([t["r_net"] for t in etf if not hit_h2(t)]) - etf_expR)},
    }

    # ETF 按年份描述性附表（不参与判定）
    def by_year(rows, hitf):
        out = {}
        for t in rows:
            y = t["signal_date"][:4]
            out.setdefault(y, {"n": 0, "n_hit": 0, "sum_r": 0.0, "sum_r_hit": 0.0})
            out[y]["n"] += 1
            out[y]["sum_r"] += t["r_net"]
            if hitf(t):
                out[y]["n_hit"] += 1
                out[y]["sum_r_hit"] += t["r_net"]
        for y in out:
            out[y]["sum_r"] = r4(out[y]["sum_r"])
            out[y]["sum_r_hit"] = r4(out[y]["sum_r_hit"])
        return out

    etf_year_tab = {"H1": by_year(etf, hit_h1), "H2": by_year(etf, hit_h2)}

    # ---------------- 判定（预注册三选一，按序求值） ----------------
    def verdict(h_stock, seg):
        e0 = h_stock["before"]["expR"]
        delta = h_stock["delta_expR"]
        ef = h_stock["filtered"]["expR"]
        nf = h_stock["filtered"]["n"]
        seg_ok = seg["A"]["consistent"] and seg["B"]["consistent"]
        if delta >= DELTA_PASS and ef is not None and ef < 0 and seg_ok:
            v = "成立"
        elif delta <= 0 or (ef is not None and ef > 0 and nf >= NF_REVERSAL_MIN):
            v = "不成立"
        else:
            v = "证据不足"
        reasons = []
        if v == "成立":
            reasons = [f"delta={delta}>=+0.20", f"EF={ef}<0", "ETF两段方向一致"]
        elif v == "不成立":
            if delta <= 0:
                reasons.append(f"delta={delta}<=0（独立样本无改善或恶化）")
            if ef is not None and ef > 0 and nf >= NF_REVERSAL_MIN:
                reasons.append(f"EF={ef}>0 且 NF={nf}>=10（栖息地为正，方向反证）")
        else:
            reasons = [f"delta={delta}（未达+0.20成立线）" if delta < DELTA_PASS else "分段方向翻转",
                       f"EF={ef}", f"NF={nf}"]
        return {"verdict": v, "delta_expR": delta, "EF": ef, "NF": nf,
                "E0": e0, "E1": h_stock["after"]["expR"],
                "etf_segments_consistent": seg_ok, "reasons": reasons}

    verdicts = {"H1": verdict(h1_stock, etf_seg["H1"]), "H2": verdict(h2_stock, etf_seg["H2"])}

    # ---------------- 解释性诊断 D1（H1 反向机制，不参与判定） ----------------
    def year_hist(rows):
        out = {}
        for t in rows:
            y = t["signal_date"][:4]
            out[y] = out.get(y, 0) + 1
        return dict(sorted(out.items()))

    etf_h1_hits = [t for t in etf if hit_h1(t)]
    stock_h1_hits = [t for t in stock if hit_h1(t)]
    n_short = sum(1 for t in stock_h1_hits if t["rv_series_n"] < 756)
    n_vshort = sum(1 for t in stock_h1_hits if t["rv_series_n"] < 250)

    def era(rows):
        a = [t["r_net"] for t in rows if t["signal_date"][:4] <= "2018"]
        b = [t["r_net"] for t in rows if t["signal_date"][:4] >= "2019"]
        return {"2016-2018": stats_block(a), "2019+": stats_block(b)}

    d1 = {
        "note": "解释性、不可判定；仅描述性支撑 H1 反向机制讨论",
        "etf_rv60Q1_year_hist": year_hist(etf_h1_hits),
        "stock_rv60Q1_year_hist": year_hist(stock_h1_hits),
        "stock_rv60Q1_rv_series_n": {
            "n": len(stock_h1_hits), "n_lt_756_short": n_short, "n_lt_250_vshort": n_vshort,
            "min": min(t["rv_series_n"] for t in stock_h1_hits),
            "median": sorted(t["rv_series_n"] for t in stock_h1_hits)[len(stock_h1_hits) // 2],
            "full_window_756": len(stock_h1_hits) - n_short,
        },
        "era_split_etf_rv60Q1": era(etf_h1_hits),
        "era_split_stock_rv60Q1": era(stock_h1_hits),
        "era_split_stock_nonQ1": {
            "2016-2018": stats_block([t["r_net"] for t in stock if t["signal_date"][:4] <= "2018" and not hit_h1(t)]),
            "2019+": stats_block([t["r_net"] for t in stock if t["signal_date"][:4] >= "2019" and not hit_h1(t)]),
        },
    }

    # ---------------- 汇总输出 ----------------
    out = {
        "task": "模块B 栖息地过滤假设 H1/H2 正式验证（AV，2026-09-04）；预注册全文见 scripts/agent_AV/validate_h1h2.py docstring",
        "rules_frozen": {
            "H1": f"rv60_pctl < {H1_LINE} -> 命中（AO 原口径）",
            "H2": f"b20_pctl5y >= {H2_LINE} -> 命中（AO 原口径；null 标签视为未命中）",
            "delta_pass_line": DELTA_PASS, "nf_reversal_min": NF_REVERSAL_MIN,
            "combined": False,
        },
        "anchors": anchors,
        "population": {
            "stock_closed_N": len(stock),
            "stock_rows_total": len(hl),
            "invalid_trade": invalid,
            "b20_null_trades": [trade_brief(t, ["rv60_pctl", "exit_reason"]) for t in stock if t["b20_pctl5y"] is None],
            "etf_N": len(etf),
        },
        "stock_pool_main_test": {"H1": h1_stock, "H2": h2_stock},
        "etf_full_sample": etf_full,
        "etf_segments": etf_seg,
        "etf_by_year_descriptive": etf_year_tab,
        "top5_bigwin_membership_descriptive": {"stock": top5_stock, "etf": top5_etf},
        "verdicts_pre_registered": verdicts,
        "d1_explanatory_h1_reversal": d1,
    }
    dump(out)

    # stdout 摘要（供双跑日志）
    print("=== AV H1/H2 验证（预注册判定，跑前冻结线）===")
    print(f"anchors: all_pass={all_anchors_pass}")
    for h, v in verdicts.items():
        print(f"[{h}] verdict={v['verdict']} E0={v['E0']} E1={v['E1']} delta={v['delta_expR']} "
              f"EF={v['EF']} NF={v['NF']} etf_seg_consistent={v['etf_segments_consistent']}")
        print(f"      reasons: {v['reasons']}")
    normalized = json.dumps(out, sort_keys=True, ensure_ascii=True)
    print("sha256(normalized_json) =", hashlib.sha256(normalized.encode("utf-8")).hexdigest())


def dump(out):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
