# -*- coding: utf-8 -*-
"""AV 任务：双≤20 极端底部——价格阶梯执行 vs 时间分批 vs 一次性。

预注册全文（跑前写死，跑完不得回头调整判定线）。

【研究问题】AK/AM 链条已确认：A 股双≤20 极端底部的"二次下探"真实存在
（警报后 60 日中位 −5.5%~−10.7%），但**时间分批**兑现不了这个结构（AM：分批
少赚 1.7~2.3pp，晚投批次成本更贵）。本任务测剩下唯一直接利用"底部是过程"
结构的执行形态：**价格阶梯**——首批立即进场，后续批次不在日历上等，而在
价格跌到预设深度时才接（跌不深就持现金到截止日）。核心张力：V 型反弹时
后批买不到/买更贵（AE/AM/美债三轮已见的"反弹罚金"），阴跌时后批接到更便宜。
哪个占优是实证问题。

【事件集（复用 AK，禁止重定义）】AK extreme_bottom_events.json 的 37 簇 × 5
标的 = 79 (symbol, event_date) 样本；对齐断言与 AM 逐字同逻辑（searchsorted
≤7 自然日 + event_trade_date 断言），本脚本 import AM 的实现，不允许复制走样。

【时间线（跑前写死，修掉 AM 的窗口不对称批评）】
  - i0 = 事件交易日（警报收盘对齐日，AK 的 event_trade_date）。
  - 建仓截止 D = i0 + 250 交易日：所有臂（含价格阶梯）必须在此前满仓，
    阶梯未触发的批次在 D 收盘按市价补齐（登记 never_triggered 率）。
  - 评估终点 E = i0 + 500 交易日收盘；收益 = 账户总值/C − 1（C=1.0）。
  - 回撤窗 [i0, E] **所有臂同窗**（AM 的批评口径）。
  - i0+500 越界 → 该事件所有配对缺失（不外推）。
  - 价格全部 close-to-close；复用 AK/AM 公司行为前复权（隔夜|±50%|）。

【臂（等额资金批；费用每笔买入 10bp，与 AM 同）】
  - lump：i0 收盘一次满仓（基准）。
  - staged12：12 笔按 21 交易日间隔（AM 12m 臂的重建，作对照，应复现 AM ≈ −2pp）。
  - pl3x5【主判定臂】：3 等批；批1 i0 收盘；批2 触发价 P0×0.95；批3 P0×0.90；
    未触发批 D 收盘补齐。
  - pl3x8【探索臂】：同上但 −8%/−16%（测"更深的耐心"）。
  - pl_half10【探索臂】：1/2 i0 收盘 + 1/2 @ P0×0.90 或 D。
  - pl_newlow【探索臂】：3 等批；批1 i0；批2 = 首个"自 i0 起运行新低"收盘
    （t ≥ i0+5 且 close ≤ min(close[i0..t])，即跌破建仓以来全部收盘含 P0）；
    批3 = 下一个新低且距批2 ≥10 交易日；未触发 D 补齐。
  多重性处理（写死）：**只有主臂 pl3x5 参与判定**；探索臂与对照臂任何数字
  只描述，探索臂"赢了"也不触发判定输出，只登记。

【设计偏差诚实登记】阶梯深度(−5/−10)是在看过 AK 二次下探深度(−5.5~−10.7%)
之后选的，属样本内设计；本实验对"结构是否存在"是样本内、对"该不该用"
只有描述级效力。转折级结论需等下一轮真实极端底部的前瞻样本。

【度量（每事件×每臂）】ret_pct(i0+500)、dd_pct(同窗)、平均成本 vs lump
（等额资金调和平均，pp）、n_trades、never_triggered 批次数、各批成交日。

【配对与聚合】diff = 臂.ret − lump.ret（pp）；dd_impr = lump.dd − 臂.dd（pp，
正=阶梯更浅）。合并池中位数/四分位/正占比；分标的中位（≥2 配对才有资格）；
AK type 分组（process/middle/event_v）中位；配对符号检验（复用 AM 确定性实现，
描述级）。

【预注册三选一判定线（只对主臂 pl3x5，跑前写死）】
  样本下限：合并池配对数 ≥10，否则直接"证据不足"。
  - 「价格阶梯更优」同时满足：
    (P1) 池中位 diff(pl3x5 − lump) ≥ +1.0pp
         [依据：AM 时间分批代价 −1.7~−2.3pp；阶梯要改变执行决策，收益增量
          至少要抵掉时间分批代价的一半，否则不值得偏离 AM 已收案的"一次性"]；
    (P2) 池中位 dd_impr ≥ +1.0pp
         [依据：AK 二次下探中位 −5.5~−10.7%，阶梯现金批天然躲一半，实际
          改善不足 1pp 说明现金批没起到保护作用]；
    (P3) ≥3/5 个有资格标的（配对 ≥2）分标的中位 diff > 0。
  - 「价格阶梯无效」满足任一：
    (N1) 池中位 diff ≤ 0；或
    (N2) |池中位 diff| < 0.5 且 dd_impr 中位 < 1.0（收益平、保护也无）。
  - 其余 = 「证据不足/交换」（如收益为正但不足 +1pp 且回撤改善明显——
    按登记如实报"交换"结构，不硬塞进两极）。

【红线遵守】不回答"该不该建仓"；不产生买卖规则（阶梯深度是实验参数不是
推荐参数）；不改生产代码/缓存/既有归档；产出全为新增。
双跑哈希：PYTHONHASHSEED=0 / 42，sha256(canonical json) 逐位一致。
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

from extreme_bottom_staged_entry_validation import (  # noqa: E402  AM 逐字复用
    AK_JSON,
    FEE,
    INSTRUMENTS,
    account_path,
    adjust_corporate_actions,
    max_drawdown,
    med,
    sign_test,
)

RAW_DIR = REPO / "docs/experiments/raw/agent_AV-price-ladder"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DEADLINE = 250   # 建仓截止（交易日）
EVAL = 500       # 评估终点（交易日）
MONTH_TD = 21
X_RET = 1.0      # P1 线（pp）
X_DD = 1.0       # P2 线（pp）
MIN_POOLED = 10
MIN_PER_INSTR = 2


def fill_ladder_thresholds(px_vals: np.ndarray, i0: int, p0: float,
                           depths: list[float | None]) -> dict:
    """阈值阶梯：批 k 在 close ≤ P0×(1−depth_k) 触发；depth=None 表示首批。
    未触发批在截止日 i0+DEADLINE 收盘补齐。返回成交索引/价格/单位。"""
    n = len(depths)
    fill_idx: list[int | None] = [None] * n
    d_line = min(i0 + DEADLINE, len(px_vals) - 1)
    for t in range(i0, d_line + 1):
        for k in range(n):
            if fill_idx[k] is not None:
                continue
            if depths[k] is None:
                if t == i0:
                    fill_idx[k] = t
            elif float(px_vals[t]) <= p0 * (1.0 - depths[k]):
                fill_idx[k] = t
        if all(f is not None for f in fill_idx):
            break
    for k in range(n):  # 截止补齐
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


def fill_ladder_newlow(px_vals: np.ndarray, i0: int) -> dict:
    """新低阶梯：批1 i0；批2/3 在自 i0 起运行新低（含 P0）触发，间隔 ≥10td。"""
    n = 3
    fill_idx: list[int | None] = [i0, None, None]
    d_line = min(i0 + DEADLINE, len(px_vals) - 1)
    last_fill = i0
    run_min = float(px_vals[i0])
    for t in range(i0 + 1, d_line + 1):
        c = float(px_vals[t])
        if c < run_min or abs(c - run_min) < 1e-12:
            if c < run_min and (t >= i0 + 5) and (t - last_fill >= 10):
                if fill_idx[1] is None:
                    fill_idx[1] = t
                    last_fill = t
                elif fill_idx[2] is None:
                    fill_idx[2] = t
                    last_fill = t
            run_min = min(run_min, c)
        if all(f is not None for f in fill_idx):
            break
    for k in range(n):
        if fill_idx[k] is None:
            fill_idx[k] = d_line
    tranches, never = [], 0
    cap = 1.0 / n
    for k in range(n):
        px_k = float(px_vals[fill_idx[k]])
        if k > 0 and fill_idx[k] == d_line:
            never += 1
        tranches.append((int(fill_idx[k]), cap * (1 - FEE) / px_k, cap, px_k))
    return {"tranches": tranches, "never_triggered": never,
            "deadline_idx": int(d_line)}


def fill_time_staged(px_vals: np.ndarray, i0: int, m: int) -> dict:
    """AM 时间分批的重建（12 笔 × 21td）。"""
    fill_idx = [i0 + MONTH_TD * k for k in range(m)]
    d_line = min(i0 + DEADLINE, len(px_vals) - 1)
    tranches = []
    cap = 1.0 / m
    for k in range(m):
        idx = min(fill_idx[k], d_line)
        tranches.append((int(idx), cap * (1 - FEE) / float(px_vals[idx]), cap,
                         float(px_vals[idx])))
    return {"tranches": tranches, "never_triggered": 0,
            "deadline_idx": int(d_line)}


def evaluate_arm(px_vals: np.ndarray, i0: int, filled: dict) -> dict | None:
    i_eval = i0 + EVAL
    if i_eval >= len(px_vals):
        return None
    tranches = filled["tranches"]
    units = sum(u for _, u, _, _ in tranches)
    ret = (units * float(px_vals[i_eval]) - 1.0) * 100
    path_tr = [(idx, u, cap) for idx, u, cap, _ in tranches]
    dd = max_drawdown(account_path(px_vals, i0, i_eval, path_tr))
    prices = [p for _, _, _, p in tranches]
    n = len(prices)
    harm = n / sum(1.0 / p for p in prices)
    p0 = float(px_vals[i0])
    return {
        "ret_pct": round(ret, 2),
        "dd_pct": round(dd, 2),
        "cost_vs_p0_pp": round((harm / p0 - 1.0) * 100, 2),
        "n_trades": n,
        "never_triggered": filled["never_triggered"],
        "fill_days": [int(idx - i0) for idx, _, _, _ in tranches],
        "build_end_offset": max(idx for idx, _, _, _ in tranches) - i0,
    }


ARMS: dict[str, dict] = {
    "lump": {"kind": "thresholds", "depths": [None], "role": "baseline"},
    "staged12": {"kind": "time", "m": 12, "role": "control"},
    "pl3x5": {"kind": "thresholds", "depths": [None, 0.05, 0.10],
              "role": "primary"},
    "pl3x8": {"kind": "thresholds", "depths": [None, 0.08, 0.16],
              "role": "exploratory"},
    "pl_half10": {"kind": "thresholds", "depths": [None, 0.10],
                  "role": "exploratory"},
    "pl_newlow": {"kind": "newlow", "role": "exploratory"},
}


def main() -> None:
    ak = json.loads(AK_JSON.read_text())
    ak_map = {(e["symbol"], e["event_date"]): e for e in ak["events"]}

    events, all_jumps = [], []
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
            i0, p0 = int(loc), float(px_vals[loc])
            ev = {"symbol": sym, "name": name, "event_date": d,
                  "event_trade_date": ak_e["event_trade_date"],
                  "type": ak_e["type"], "p0": round(p0, 4), "arms": {}}
            for arm, spec in ARMS.items():
                if spec["kind"] == "thresholds":
                    filled = fill_ladder_thresholds(px_vals, i0, p0, spec["depths"])
                elif spec["kind"] == "time":
                    filled = fill_time_staged(px_vals, i0, spec["m"])
                else:
                    filled = fill_ladder_newlow(px_vals, i0)
                res = evaluate_arm(px_vals, i0, filled)
                if res is not None:
                    ev["arms"][arm] = res
            events.append(ev)
        print(f"[{sym}] done", flush=True)

    # ---- 配对（臂 vs lump，同事件两侧齐全才算配对）----
    pairs = {arm: [] for arm in ARMS if arm != "lump"}
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
        per_instr = {}
        for sym in INSTRUMENTS:
            sub = [p for p in ps if p["symbol"] == sym]
            if len(sub) >= MIN_PER_INSTR:
                per_instr[sym] = {"n": len(sub),
                                  "diff_med": med([p["diff"] for p in sub]),
                                  "dd_med": med([p["dd_impr"] for p in sub])}
        by_type = {}
        for tp in ("process", "middle", "event_v"):
            sub = [p for p in ps if p["type"] == tp]
            if sub:
                by_type[tp] = {"n": len(sub), "diff_med": med([p["diff"] for p in sub]),
                               "dd_med": med([p["dd_impr"] for p in sub])}
        return {
            "n_pairs": len(ps),
            "diff_med": med(diffs), "diff_q25": None if not diffs else round(
                float(np.percentile(diffs, 25)), 2),
            "diff_q75": None if not diffs else round(
                float(np.percentile(diffs, 75)), 2),
            "diff_pos_rate": None if not diffs else round(
                sum(1 for x in diffs if x > 0) / len(diffs), 3),
            "dd_impr_med": med(dds),
            "per_instrument": per_instr, "by_type": by_type,
            "sign_test": sign_test(diffs),
        }

    out: dict = {
        "criteria_doc": __doc__,
        "config": {"deadline_td": DEADLINE, "eval_td": EVAL,
                   "fee": FEE, "arms": {k: v["role"] for k, v in ARMS.items()}},
        "corporate_action_adjustments": all_jumps,
        "events": events,
        "pooled": {arm: pooled(arm) for arm in pairs},
    }

    # ---- 判定（只对主臂 pl3x5；最后算）----
    pl = out["pooled"]["pl3x5"]
    n_pairs = pl["n_pairs"]
    p1 = pl["diff_med"] is not None and pl["diff_med"] >= X_RET
    p2 = pl["dd_impr_med"] is not None and pl["dd_impr_med"] >= X_DD
    elig = {s: r for s, r in pl["per_instrument"].items()
            if r["diff_med"] is not None}
    p3 = sum(1 for r in elig.values() if r["diff_med"] > 0) >= 3
    n1 = pl["diff_med"] is not None and pl["diff_med"] <= 0
    n2 = (pl["diff_med"] is not None and abs(pl["diff_med"]) < 0.5
          and (pl["dd_impr_med"] or 0) < X_DD)
    if n_pairs < MIN_POOLED:
        verdict = "证据不足（样本下限未达）"
    elif p1 and p2 and p3:
        verdict = "价格阶梯更优（主臂 pl3x5）"
    elif n1 or n2:
        verdict = "价格阶梯无效（主臂 pl3x5）"
    else:
        verdict = "证据不足/交换（主臂 pl3x5）"
    out["verdict_inputs"] = {"n_pairs": n_pairs, "P1": p1, "P2": p2, "P3": p3,
                             "N1": n1, "N2": n2}
    out["verdict"] = verdict

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "price_ladder_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"\n事件样本(含缺评估的): {len(events)}")
    for arm in pairs:
        p = out["pooled"][arm]
        print(f"{arm:<10} n={p['n_pairs']:<3} diff中位={p['diff_med']}pp "
              f"dd改善中位={p['dd_impr_med']}pp 正占比={p['diff_pos_rate']}")
    print(f"\n=== 判定：{verdict} ===")
    print(f"sha256(canonical) = {h}")


if __name__ == "__main__":
    main()
