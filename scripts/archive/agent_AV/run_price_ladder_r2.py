# -*- coding: utf-8 -*-
"""AV-b 第二轮：价格阶梯 + 追涨兜底（chase cap）——修复 V 型尾部。

【诚实登记（定位）】本脚本是在 AV 第一轮出数**之后**设计的第二轮：首轮
发现 pl3x5 在 process 型底中位 +7.2pp（5/5 标的正），但 event_v（V 型）中位
−6.9pp、最惨 −104pp，死因单一且机械——未触发批次在截止日以高出 P0
24%~52% 的价格补仓（首轮 JSON cost_vs_p0_pp 字段直接可见）。追涨兜底是对
这个已定位失效模式的针对性修复，不是新一轮搜索。因此**本轮判定级别预注册
为「假设登记 + 前瞻转正路径」，不是决策级**；对照臂（lump/staged12/pl3x5
原版）从第一轮代码逐字复用，保证两轮可比。

【追涨兜底规则（跑前写死）】pl3x5_chase10 / pl_half10_chase10：
  批次触发条件改为"双向"：close ≤ P0×(1−depth_k)（原下触发）或
  close ≥ P0×1.10（追涨线，首轮数据之前选定的"反弹确认"通用幅度，非调参
  搜索结果）——先到先成交，成交后其余批次规则不变；截止日 i0+250 兜底不变。
  直觉：V 型里后批最晚在 +10% 追涨价补齐（成本上界锁在 P0×1.10），过程型里
  追涨线大概率不先于 −5% 触发（少数先涨后跌的会少量吃亏，用 H1 线容忍）。

【臂】lump / staged12 / pl3x5（三个对照，应逐字节复现首轮）+ 新增
pl3x5_chase10（主观察臂）、pl_half10_chase10（简化变体：1/2+1/2@−10%+追涨）。
时间线/费用/评估窗/复权 全部与首轮逐字相同（DEADLINE=250, EVAL=500, 10bp）。

【预注册观察线（跑前写死；三条同时满足 → "假设登记：值得前瞻观察"，
  任何一条不满足 → 如实报不满足的那条，不做三选一包装）】
  (H1) process 型（AK type，事后标签仅用于诊断、不作执行条件）：
       chase10 的 diff 中位 ≥ +4.0pp（首轮 pl3x5 为 +7.22，允许让渡约一半）；
  (H2) event_v 型：chase10 的 diff 中位 ≥ −3.0pp（首轮 −6.92；追涨兜底的
       全部意义在此，修不到 −3 说明 +10% 线救不了 V 型尾部）；
  (H3) 合并池：chase10 diff 中位 ≥ +4.0pp 且 dd_impr 中位 ≥ 0.0pp
       （首轮 −1.84；成本上界被锁后，账面深回撤的主要来源应同步消失）。
  另登记（不设线）：chase10 的 cost_vs_p0_pp 最大值应 ≤ 10.2（追涨价+费），
  若 >10.2 即实现有 bug，本轮作废。

【红线遵守】不产生买卖规则；AK type 字段只用于诊断分组；产出全为新增；
双跑哈希 PYTHONHASHSEED=0/42 逐位一致。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "agent_AM"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AV"))

from extreme_bottom_staged_entry_validation import (  # noqa: E402
    AK_JSON, FEE, INSTRUMENTS, account_path, adjust_corporate_actions,
    max_drawdown, med, sign_test,
)
from run_price_ladder import (  # noqa: E402  首轮逐字复用
    DEADLINE, EVAL, MONTH_TD, evaluate_arm, fill_ladder_thresholds,
    fill_time_staged,
)

RAW_DIR = REPO / "docs/experiments/raw/agent_AV-price-ladder"
CHASE = 0.10  # 追涨线：高出 P0 10%


def fill_ladder_chase(px_vals: np.ndarray, i0: int, p0: float,
                      depths: list[float | None]) -> dict:
    """双向触发阶梯：下触发（≤P0×(1−d)）或追涨（≥P0×1.10）先到先成交；
    截止日补齐。首批恒为 i0。"""
    n = len(depths)
    fill_idx: list[int | None] = [None] * n
    d_line = min(i0 + DEADLINE, len(px_vals) - 1)
    chase_px = p0 * (1.0 + CHASE)
    for t in range(i0, d_line + 1):
        c = float(px_vals[t])
        for k in range(n):
            if fill_idx[k] is not None:
                continue
            if depths[k] is None:
                if t == i0:
                    fill_idx[k] = t
            elif c <= p0 * (1.0 - depths[k]) or c >= chase_px:
                fill_idx[k] = t
        if all(f is not None for f in fill_idx):
            break
    for k in range(n):
        if fill_idx[k] is None:
            fill_idx[k] = d_line
    tranches, never = [], 0
    cap = 1.0 / n
    for k in range(n):
        px_k = float(px_vals[fill_idx[k]])
        if depths[k] is not None and fill_idx[k] == d_line:
            never += 1
        tranches.append((int(fill_idx[k]), cap * (1 - FEE) / px_k, cap, px_k))
    return {"tranches": tranches, "never_triggered": never,
            "deadline_idx": int(d_line)}


ARMS: dict[str, dict] = {
    "lump": {"kind": "first", "depths": [None]},
    "staged12": {"kind": "time", "m": 12},
    "pl3x5": {"kind": "first", "depths": [None, 0.05, 0.10]},
    "pl3x5_chase10": {"kind": "chase", "depths": [None, 0.05, 0.10]},
    "pl_half10_chase10": {"kind": "chase", "depths": [None, 0.10]},
}


def main() -> None:
    ak = json.loads(AK_JSON.read_text())
    ak_map = {(e["symbol"], e["event_date"]): e for e in ak["events"]}

    events = []
    for sym, (name, path) in INSTRUMENTS.items():
        raw_px = pd.read_parquet(path)["close"].dropna()
        raw_px = raw_px[~raw_px.index.duplicated(keep="last")].sort_index()
        px, _ = adjust_corporate_actions(raw_px)
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
            i0, p0 = int(loc), float(px_vals[loc])
            ev = {"symbol": sym, "name": name, "event_date": d,
                  "type": ak_e["type"], "p0": round(p0, 4), "arms": {}}
            for arm, spec in ARMS.items():
                if spec["kind"] == "chase":
                    filled = fill_ladder_chase(px_vals, i0, p0, spec["depths"])
                elif spec["kind"] == "time":
                    filled = fill_time_staged(px_vals, i0, spec["m"])
                else:
                    filled = fill_ladder_thresholds(px_vals, i0, p0, spec["depths"])
                res = evaluate_arm(px_vals, i0, filled)
                if res is not None:
                    ev["arms"][arm] = res
            events.append(ev)
        print(f"[{sym}] done", flush=True)

    pairs: dict[str, list] = {arm: [] for arm in ARMS if arm != "lump"}
    for ev in events:
        if "lump" not in ev["arms"]:
            continue
        for arm in pairs:
            if arm in ev["arms"]:
                pairs[arm].append({
                    "symbol": ev["symbol"], "type": ev["type"],
                    "diff": round(ev["arms"][arm]["ret_pct"]
                                  - ev["arms"]["lump"]["ret_pct"], 2),
                    "dd_impr": round(ev["arms"]["lump"]["dd_pct"]
                                     - ev["arms"][arm]["dd_pct"], 2),
                })

    def pooled(arm: str) -> dict:
        ps = pairs[arm]
        diffs = [p["diff"] for p in ps]
        dds = [p["dd_impr"] for p in ps]
        by_type = {}
        for tp in ("process", "middle", "event_v"):
            sub = [p for p in ps if p["type"] == tp]
            if sub:
                by_type[tp] = {"n": len(sub),
                               "diff_med": med([p["diff"] for p in sub]),
                               "dd_med": med([p["dd_impr"] for p in sub])}
        costs = [ev["arms"][arm]["cost_vs_p0_pp"] for ev in events
                 if arm in ev["arms"]]
        return {
            "n_pairs": len(ps), "diff_med": med(diffs),
            "dd_impr_med": med(dds),
            "diff_pos_rate": None if not diffs else round(
                sum(1 for x in diffs if x > 0) / len(diffs), 3),
            "by_type": by_type, "sign_test": sign_test(diffs),
            "max_cost_vs_p0_pp": None if not costs else round(max(costs), 2),
        }

    out = {"criteria_doc": __doc__,
           "config": {"deadline_td": DEADLINE, "eval_td": EVAL, "fee": FEE,
                      "chase": CHASE},
           "events": events,
           "pooled": {arm: pooled(arm) for arm in pairs}}

    # ---- 对照臂应逐字节复现首轮 ----
    r1 = json.loads((RAW_DIR / "price_ladder_results.json").read_text())
    parity = {}
    for arm in ("staged12", "pl3x5"):
        a, b = out["pooled"][arm], r1["pooled"][arm]
        parity[arm] = {"r2_n": a["n_pairs"], "r1_n": b["n_pairs"],
                       "diff_med_r2": a["diff_med"], "diff_med_r1": b["diff_med"]}
    out["parity_vs_round1"] = parity

    ch = out["pooled"]["pl3x5_chase10"]
    h1 = ch["by_type"].get("process", {}).get("diff_med")
    h2 = ch["by_type"].get("event_v", {}).get("diff_med")
    h3a, h3b = ch["diff_med"], ch["dd_impr_med"]
    max_cost = ch["max_cost_vs_p0_pp"]
    impl_ok = max_cost is not None and max_cost <= 10.2
    out["verdict_inputs"] = {
        "H1_process_med": h1, "H1_pass": h1 is not None and h1 >= 4.0,
        "H2_eventv_med": h2, "H2_pass": h2 is not None and h2 >= -3.0,
        "H3_pooled_med": h3a, "H3_dd_med": h3b,
        "H3_pass": (h3a is not None and h3a >= 4.0 and h3b is not None
                    and h3b >= 0.0),
        "impl_cost_cap_ok": impl_ok, "max_cost_vs_p0_pp": max_cost,
    }
    all_pass = (out["verdict_inputs"]["H1_pass"]
                and out["verdict_inputs"]["H2_pass"]
                and out["verdict_inputs"]["H3_pass"] and impl_ok)
    out["verdict"] = ("假设登记：价格阶梯+追涨兜底值得前瞻观察" if all_pass
                      else "观察线未全过（明细见 verdict_inputs）")

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "price_ladder_r2_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print()
    for arm in pairs:
        p = out["pooled"][arm]
        bt = {k: v["diff_med"] for k, v in p["by_type"].items()}
        print(f"{arm:<18} n={p['n_pairs']:<3} diff中位={p['diff_med']}pp "
              f"dd改善={p['dd_impr_med']}pp 正率={p['diff_pos_rate']} "
              f"分类型={bt} 最大成本={p['max_cost_vs_p0_pp']}pp")
    print(f"\n=== 判定：{out['verdict']} ===")
    print(f"sha256(canonical) = {h}")


if __name__ == "__main__":
    main()
