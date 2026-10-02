"""T7 方法演练：同一次回撤上比较两种进入规则（人工合成例，不是行情，不代表任何效果）。

四个例子对应任务书要求：同机会、机会改变、相邻结果高度重叠、单笔极端结果。
每例的人工标准答案写在 EXPECTED，脚本计算后逐项核对并写 examples-output.json。
为了让人工答案可以手算，例子不计费用；正式合同按 T6/执行合同计入费用。

方法（详见 docs/research/proposals/remote-astra-2026-09-30/T7/）：
  1. 机会身份 = 两种规则共享的那次回撤（标的、趋势段、均线组、触碰日）；
  2. 每次回撤分别记录规则 A、B 的进入/不进入与交易结果；不进入记 0（不是删掉）；
  3. 只在两规则有差别的回撤上计算配对差 Δ = 结果_B − 结果_A；
  4. 按日历时间把评价窗口互相重叠的回撤（可跨标的、跨均线组）并成一个时间簇；
  5. 簇内取平均得到簇差，报告：簇数、方向计数、中位数、均值、去掉每个簇后的均值范围、
     最大簇占全部绝对差的比例，以及按簇做的正负号翻转精确分布（本库延伸，非论文原法）。
  6. 资金账户比较另算，把“资金被释放后多做了别的机会”单列，不并入条件本身的作用。
"""
from __future__ import annotations

import itertools
import json
import statistics
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent


def trade_return(t: dict | None) -> float:
    """单位仓位的交易结果；不进入记 0。"""
    if t is None:
        return 0.0
    return t["exit_px"] / t["entry_px"] - 1.0


def r_multiple(t: dict | None) -> float | None:
    if t is None:
        return None
    return (t["exit_px"] - t["entry_px"]) / (t["entry_px"] - t["stop"])


def classify(a: dict | None, b: dict | None) -> str:
    if a is None and b is None:
        return "neither"
    if a is None:
        return "added_by_B"
    if b is None:
        return "dropped_by_B"
    if b["entry"] > a["entry"]:
        return "delayed_by_B"
    if b["entry"] < a["entry"]:
        return "earlier_by_B"
    return "same_entry"


def paired(opps: list[dict]) -> list[dict]:
    out = []
    for o in opps:
        a, b = o.get("A"), o.get("B")
        kind = classify(a, b)
        if kind in ("neither", "same_entry") and trade_return(a) == trade_return(b):
            delta = 0.0
        else:
            delta = trade_return(b) - trade_return(a)
        out.append({"id": o["id"], "kind": kind, "delta": round(delta, 9),
                    "entry_gap": (round(b["entry_px"] / a["entry_px"] - 1, 9) if a and b else None),
                    "stop_A": a["stop"] if a else None, "stop_B": b["stop"] if b else None,
                    "R_A": round(r_multiple(a), 6) if a else None,
                    "R_B": round(r_multiple(b), 6) if b else None})
    return out


def time_clusters(opps: list[dict]) -> dict[str, int]:
    """评价窗口 [start, end]（日期）重叠即并为同一簇；跨标的、跨均线组都合并。"""
    items = sorted(opps, key=lambda o: o["window"][0])
    cluster, current, cid = {}, None, -1
    for o in items:
        s, e = (date.fromisoformat(x) for x in o["window"])
        if current is None or s > current:
            cid += 1
            current = e
        else:
            current = max(current, e)
        cluster[o["id"]] = cid
    return cluster


def cluster_values(deltas: dict[str, float], cluster: dict[str, int]) -> list[float]:
    groups: dict[int, list[float]] = {}
    for oid, d in deltas.items():
        groups.setdefault(cluster[oid], []).append(d)
    return [statistics.fmean(v) for _, v in sorted(groups.items())]


def sign_flip(values: list[float], direction: str) -> dict:
    """按簇正负号翻转的精确分布（全部 2^G 种）。direction='greater' 统计均值≥观测的比例。"""
    obs = statistics.fmean(values)
    count = 0
    total = 0
    for signs in itertools.product((1, -1), repeat=len(values)):
        m = statistics.fmean(s * v for s, v in zip(signs, values, strict=True))
        total += 1
        if (m >= obs - 1e-12) if direction == "greater" else (m <= obs + 1e-12):
            count += 1
    return {"G": len(values), "observed_mean": round(obs, 9), "share_as_extreme": round(count / total, 9),
            "smallest_attainable_share": round(1 / total, 9)}


def describe(values: list[float]) -> dict:
    total_abs = sum(abs(v) for v in values)
    loo = [statistics.fmean(values[:i] + values[i + 1:]) for i in range(len(values))] if len(values) > 1 else []
    return {"G": len(values), "positive": sum(v > 0 for v in values), "negative": sum(v < 0 for v in values),
            "mean": round(statistics.fmean(values), 9), "median": round(statistics.median(values), 9),
            "leave_one_cluster_out_mean_range": [round(min(loo), 9), round(max(loo), 9)] if loo else None,
            "largest_cluster_share_of_abs": round(max(abs(v) for v in values) / total_abs, 9) if total_abs else None,
            "direction_flips_when_one_cluster_removed": bool(loo) and (min(loo) < 0 < max(loo))}


def account(opps: list[dict], rule: str) -> dict:
    """一笔资金、同时只持一笔：按进入日先后，空仓时才接受；返回复利结果与实际参与的机会。"""
    trades = sorted(((o[rule], o["id"]) for o in opps if o.get(rule)), key=lambda x: x[0]["entry"])
    wealth, busy_until, taken, blocked = 1.0, -1, [], []
    for t, oid in trades:
        if t["entry"] <= busy_until:
            blocked.append(oid)
            continue
        wealth *= 1 + trade_return(t)
        busy_until = t["exit"]
        taken.append(oid)
    return {"final": round(wealth, 9), "return": round(wealth - 1, 9), "taken": taken, "blocked": blocked}


def T(entry, entry_px, stop, exit_, exit_px):
    return {"entry": entry, "entry_px": entry_px, "stop": stop, "exit": exit_, "exit_px": exit_px}


EXAMPLES = {
    "E1_same_opportunity_delayed": [
        {"id": "510300|ep1|g60|touch=t1", "window": ["2025-03-03", "2025-03-31"],
         "A": T(5, 104.9, 100.3, 20, 108.0), "B": T(8, 105.6, 100.2, 20, 108.0)}],
    "E2_opportunity_set_changes": [
        {"id": "P1|touch=t1", "window": ["2025-03-03", "2025-03-19"], "A": T(3, 100.0, 97.0, 12, 96.0), "B": None},
        {"id": "P2|touch=t8", "window": ["2025-03-13", "2025-04-07"], "A": T(10, 50.0, 48.0, 25, 53.0),
         "B": T(10, 50.0, 48.0, 25, 53.0)}],
    "E3_adjacent_overlap": [
        {"id": "510300|g20|2025-03-03", "window": ["2025-03-03", "2025-03-28"], "delta": 0.012},
        {"id": "510300|g60|2025-03-05", "window": ["2025-03-05", "2025-03-28"], "delta": 0.010},
        {"id": "159915|g20|2025-03-04", "window": ["2025-03-04", "2025-03-31"], "delta": 0.015},
        {"id": "510300|g20|2025-09-01", "window": ["2025-09-01", "2025-09-26"], "delta": 0.008}],
    "E4_single_extreme": [
        {"id": f"cluster{i}", "window": [f"2025-0{i + 1}-01", f"2025-0{i + 1}-20"], "delta": d}
        for i, d in enumerate([-0.25, 0.02, 0.015, 0.025, 0.01, 0.02])],
}

EXPECTED = {
    "E1_same_opportunity_delayed": {"kind": "delayed_by_B", "delta": -0.006824681, "entry_gap": 0.006673022,
                                    "R_A": 0.673913, "R_B": 0.444444},
    "E2_opportunity_set_changes": {"paired_delta": {"P1|touch=t1": 0.04, "P2|touch=t8": 0.0},
                                   "account_A_return": -0.04, "account_B_return": 0.06,
                                   "account_gap": 0.10, "capital_reuse_part": 0.06,
                                   "account_A_blocked": ["P2|touch=t8"]},
    "E3_adjacent_overlap": {"naive_G": 4, "cluster_G": 2, "cluster_values": [0.012333333, 0.008],
                            "naive_smallest_share": 0.0625, "cluster_smallest_share": 0.25},
    "E4_single_extreme": {"mean": -0.026666667, "median": 0.0175, "positive": 5,
                          "loo_range": [-0.037, 0.018], "largest_share": 0.735294118,
                          "flips": True, "sign_flip_share_le_observed": 0.5},
}


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def main() -> int:
    out, fails = {}, []
    # E1
    p = paired(EXAMPLES["E1_same_opportunity_delayed"])[0]
    e = EXPECTED["E1_same_opportunity_delayed"]
    ok = (p["kind"] == e["kind"] and close(p["delta"], e["delta"]) and close(p["entry_gap"], e["entry_gap"])
          and close(p["R_A"], e["R_A"]) and close(p["R_B"], e["R_B"]))
    out["E1_same_opportunity_delayed"] = {"paired": p, "matches_hand_answer": ok}
    # E2
    opps = EXAMPLES["E2_opportunity_set_changes"]
    pd_ = {x["id"]: x["delta"] for x in paired(opps)}
    acc_a, acc_b = account(opps, "A"), account(opps, "B")
    e = EXPECTED["E2_opportunity_set_changes"]
    gap = acc_b["return"] - acc_a["return"]
    reuse = gap - sum(pd_.values())
    ok = (all(close(pd_[k], v) for k, v in e["paired_delta"].items()) and close(acc_a["return"], e["account_A_return"])
          and close(acc_b["return"], e["account_B_return"]) and close(gap, e["account_gap"])
          and close(reuse, e["capital_reuse_part"]) and acc_a["blocked"] == e["account_A_blocked"])
    out["E2_opportunity_set_changes"] = {"paired_delta": pd_, "account_A": acc_a, "account_B": acc_b,
                                         "account_gap": round(gap, 9),
                                         "capital_reuse_part_not_condition_effect": round(reuse, 9),
                                         "matches_hand_answer": ok}
    # E3
    opps = EXAMPLES["E3_adjacent_overlap"]
    deltas = {o["id"]: o["delta"] for o in opps}
    cl = time_clusters(opps)
    cv = cluster_values(deltas, cl)
    naive = sign_flip(list(deltas.values()), "greater")
    clus = sign_flip(cv, "greater")
    e = EXPECTED["E3_adjacent_overlap"]
    ok = (naive["G"] == e["naive_G"] and clus["G"] == e["cluster_G"]
          and all(close(a, b) for a, b in zip(cv, e["cluster_values"], strict=True))
          and close(naive["smallest_attainable_share"], e["naive_smallest_share"])
          and close(clus["smallest_attainable_share"], e["cluster_smallest_share"]))
    out["E3_adjacent_overlap"] = {"clusters": cl, "cluster_values": [round(v, 9) for v in cv],
                                  "naive_sign_flip": naive, "cluster_sign_flip": clus,
                                  "describe_clusters": describe(cv), "matches_hand_answer": ok}
    # E4
    opps = EXAMPLES["E4_single_extreme"]
    cv = cluster_values({o["id"]: o["delta"] for o in opps}, time_clusters(opps))
    d = describe(cv)
    sf = sign_flip(cv, "less")
    e = EXPECTED["E4_single_extreme"]
    ok = (close(d["mean"], e["mean"]) and close(d["median"], e["median"]) and d["positive"] == e["positive"]
          and all(close(a, b) for a, b in zip(d["leave_one_cluster_out_mean_range"], e["loo_range"], strict=True))
          and close(d["largest_cluster_share_of_abs"], e["largest_share"])
          and d["direction_flips_when_one_cluster_removed"] == e["flips"]
          and close(sf["share_as_extreme"], e["sign_flip_share_le_observed"]))
    out["E4_single_extreme"] = {"describe": d, "sign_flip": sf, "matches_hand_answer": ok}
    for k, v in out.items():
        if not v["matches_hand_answer"]:
            fails.append(k)
    out["_note"] = "人工合成例；不计费用；只证明比较方法按约定工作，不代表任何市场效果。"
    (HERE / "examples-output.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                               encoding="utf-8")
    for k, v in out.items():
        if k != "_note":
            print(k, "matches_hand_answer=", v["matches_hand_answer"])
    print("FAILURES:", fails or "none")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
