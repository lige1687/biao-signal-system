"""factor_evidence 稳定性与区间重叠审计（纯计算，无输入许可概念）。

- ``state_summary``：共同合法集合两组统计与全期 delta；辅助保留中位数差、
  上涨比例差与原 aux 描述——只描述，不据它们另选赢家。
- ``year_stability``：信号发生年分组（跨年目标归观察年）、年度差正/零/负
  计数、逐年留出（leave-one-year-out）全期 delta、两组都有值年度差的
  等权均值。所有年份保留，未知与空组结构化输出；缺任一组 delta=null+原因。
- ``overlap_audit``：标签区间重叠审计。区间单位是**相邻交易日的价格变动
  区间**（(前session, 后session] 对，按日程位置识别），不是共同日期点数；
  输出相邻观察共享区间数量/比例、全表总区间引用数与唯一区间数；重用比
  只是描述，不是有效样本数。稀疏锚点只审计原规则，不扫描其他起点。

所有函数先按 session 显式排序再计算，不依赖输入行序；单组/空集/缺值
一律结构化 null+原因，不静默丢弃年份。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EMPTY_GROUP = {"n": 0, "mean": None, "median": None, "up": 0, "down": 0,
               "zero": 0, "up_ratio": None, "aux_n": 0, "aux_mean": None,
               "aux_worst": None}


def _sorted_legal(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values("session", kind="mergesort").reset_index(drop=True)


def _group_stats(mains: list, auxs: list) -> dict:
    if not mains:
        return dict(EMPTY_GROUP)
    arr = np.asarray(mains, dtype=float)
    aux_arr = np.asarray(auxs, dtype=float) if auxs else np.array([])
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "up": int((arr > 0).sum()),
        "down": int((arr < 0).sum()),
        "zero": int((arr == 0).sum()),
        "up_ratio": float((arr > 0).mean()),
        "aux_n": int(aux_arr.size),
        "aux_mean": float(aux_arr.mean()) if aux_arr.size else None,
        "aux_worst": float(aux_arr.min()) if aux_arr.size else None,
    }


def _split(frame: pd.DataFrame):
    """共同合法集合 → (true_mains, true_aux, false_mains, false_aux)。"""
    legal = frame[frame["legal"] == True]  # noqa: E712
    t = legal[legal["state"] == True]  # noqa: E712
    f = legal[legal["state"] == False]  # noqa: E712
    tm = t["main"].dropna().astype(float).tolist()
    fm = f["main"].dropna().astype(float).tolist()
    ta = t["aux"].dropna().astype(float).tolist()
    fa = f["aux"].dropna().astype(float).tolist()
    return tm, ta, fm, fa


def state_summary(frame: pd.DataFrame) -> dict:
    """全期共同合法集合两组统计与 delta（单位小数；展示×100记百分点）。"""
    f = _sorted_legal(frame)
    tm, ta, fm, fa = _split(f)
    st, sf = _group_stats(tm, ta), _group_stats(fm, fa)
    out = {
        "n_rows": int(len(f)),
        "n_legal": int((f["legal"] == True).sum()),  # noqa: E712
        "true": st, "false": sf,
        "delta": None, "null_reason": None,
        "median_diff": None, "up_ratio_diff": None,
        "unit": "小数变化率；×100 后读作百分点",
        "reading": ("状态为真的观察之后的目标均值 minus 未成立组均值；"
                    "是历史描述差，不是因子贡献或因果"),
    }
    if st["n"] == 0 or sf["n"] == 0:
        missing = []
        if st["n"] == 0:
            missing.append("true_group_empty")
        if sf["n"] == 0:
            missing.append("false_group_empty")
        out["null_reason"] = "not_estimable:" + ",".join(missing)
        return out
    out["delta"] = st["mean"] - sf["mean"]
    out["median_diff"] = st["median"] - sf["median"]
    out["up_ratio_diff"] = st["up_ratio"] - sf["up_ratio"]
    return out


def _year_of(session: str) -> str:
    return str(session)[:4]


def year_stability(frame: pd.DataFrame) -> dict:
    """逐年、留一年与等权年度差；所有年份保留，空组结构化输出。"""
    f = _sorted_legal(frame)
    full = state_summary(f)
    years_seen = sorted({_year_of(s) for s in f["session"]})

    years: dict[str, dict] = {}
    for y in years_seen:
        yf = f[f["session"].str.startswith(y)]
        ytm = yf[(yf["legal"] == True) & (yf["state"] == True)]  # noqa: E712
        yfm = yf[(yf["legal"] == True) & (yf["state"] == False)]  # noqa: E712
        yst = _group_stats(ytm["main"].dropna().astype(float).tolist(),
                           ytm["aux"].dropna().astype(float).tolist())
        ysf = _group_stats(yfm["main"].dropna().astype(float).tolist(),
                           yfm["aux"].dropna().astype(float).tolist())
        entry = {"true": yst, "false": ysf, "delta": None, "null_reason": None}
        if yst["n"] == 0 or ysf["n"] == 0:
            missing = []
            if yst["n"] == 0:
                missing.append("true_group_empty")
            if ysf["n"] == 0:
                missing.append("false_group_empty")
            entry["null_reason"] = "not_estimable:" + ",".join(missing)
        else:
            entry["delta"] = yst["mean"] - ysf["mean"]
        years[y] = entry

    sign = {"positive": 0, "zero": 0, "negative": 0}
    for entry in years.values():
        d = entry["delta"]
        if d is None:
            continue
        if d > 0:
            sign["positive"] += 1
        elif d < 0:
            sign["negative"] += 1
        else:
            sign["zero"] += 1

    loo: dict[str, dict] = {}
    for y in years_seen:
        rest = f[~f["session"].str.startswith(y)]
        r_t = rest[(rest["legal"] == True)  # noqa: E712
                   & (rest["state"] == True)]["main"].dropna().astype(float).tolist()  # noqa: E712
        r_f = rest[(rest["legal"] == True)  # noqa: E712
                   & (rest["state"] == False)]["main"].dropna().astype(float).tolist()  # noqa: E712
        entry = {"n": len(r_t) + len(r_f), "true_n": len(r_t),
                 "false_n": len(r_f), "delta": None, "null_reason": None}
        if not r_t or not r_f:
            missing = []
            if not r_t:
                missing.append("true_group_empty")
            if not r_f:
                missing.append("false_group_empty")
            entry["null_reason"] = "not_estimable:" + ",".join(missing)
        else:
            entry["delta"] = float(np.mean(r_t)) - float(np.mean(r_f))
        loo[y] = entry

    valid = [(y, e["delta"]) for y, e in years.items() if e["delta"] is not None]
    equal_weight = {
        "years": [y for y, _ in valid],
        "mean_delta": float(np.mean([d for _, d in valid])) if valid else None,
        "full_period_delta": full["delta"],
        "note": ("两组都有值年度差的等权均值；改变了权重，只是另一描述视角，"
                 "不替代全期结果，不是因果校正"),
    }

    # 不完整年份标记：评价窗边界年（首年首观察晚于年初/末年末观察早于年末）
    partial = []
    if years_seen:
        first_y = years_seen[0]
        first_sessions = f[f["session"].str.startswith(first_y)]["session"]
        if first_sessions.size:
            s0 = first_sessions.iat[0]
            if int(s0[5:7]) > 1 or int(s0[8:10]) > 7:
                partial.append(first_y)
        last_y = years_seen[-1]
        last_sessions = f[f["session"].str.startswith(last_y)]["session"]
        if last_sessions.size and last_y != first_y:
            s1 = last_sessions.iat[-1]
            if int(s1[5:7]) < 12 or int(s1[8:10]) < 24:
                partial.append(last_y)

    return {
        "years": years,
        "sign_counts": sign,
        "leave_one_year_out": loo,
        "equal_weight_year_delta": equal_weight,
        "partial_years": partial,
        "partial_year_note": "评价窗边界年（近似标记：窗口未覆盖整年）",
        "year_key": "信号发生年（session 年）；跨年目标归观察年，不当独立时期验证",
        "sign_note": ("年度差严格符号计数，无预定阈值分类；"
                      "不能由全期数值推出多数年份同向"),
    }


def overlap_audit(frame: pd.DataFrame, schedule: pd.DataFrame,
                  anchor: str, step: int) -> dict:
    """标签区间重叠审计：相邻交易日价格区间，不是共同日期点数。"""
    days = schedule["session"].tolist()
    pos = {d: i for i, d in enumerate(days)}
    f = _sorted_legal(frame)

    label_sets: list[set[int]] = []
    axis_positions: list[int] = []
    rows_without = 0
    for session, e, x in zip(f["session"], f["e_date"], f["x_date"],
                             strict=True):
        if not (isinstance(e, str) and isinstance(x, str)):
            rows_without += 1
            continue
        e_pos, x_pos = pos[e], pos[x]
        # 区间以右端点位置标识：(s_{k-1}, s_k]，k ∈ (e_pos, x_pos]
        label_sets.append(set(range(e_pos + 1, x_pos + 1)))
        axis_positions.append(pos[session])

    total_refs = sum(len(s) for s in label_sets)
    unique = set().union(*label_sets) if label_sets else set()

    # 相邻观察 = 交易日轴位置相差 1（不是行序相邻）
    by_pos = dict(zip(axis_positions, label_sets, strict=False))
    adjacent_hist: dict[int, int] = {}
    adjacent_pairs = 0
    shared_sum = 0
    for p in sorted(by_pos):
        if p + 1 in by_pos:
            shared = len(by_pos[p] & by_pos[p + 1])
            adjacent_hist[shared] = adjacent_hist.get(shared, 0) + 1
            adjacent_pairs += 1
            shared_sum += shared
    per_label = len(label_sets[0]) if label_sets else None

    # 稀疏锚点审计：只审原规则（锚点 + 步长），不扫描其他起点；
    # 网格沿完整交易日轴按 (轴位置-锚点位置) % step == 0 推进
    window_positions = sorted(by_pos)
    anchor_pos = pos.get(anchor)
    grid: list[int] = []
    if anchor_pos is not None:
        grid = [p for p in window_positions
                if p >= anchor_pos and (p - anchor_pos) % step == 0]
    # 相邻格点成对比较：两个序列长度差 1 是刻意为之，strict=False
    sparse_shared = [len(by_pos[a] & by_pos[b])
                     for a, b in zip(grid, grid[1:], strict=False)]

    return {
        "interval_unit": ("相邻交易日的价格变动区间（按日程位置识别的相邻对）；"
                          "不是共同日期点数"),
        "rows_audited": len(label_sets),
        "rows_without_interval": rows_without,
        "per_label_intervals": (len(label_sets[0]) if label_sets else None),
        "total_interval_refs": int(total_refs),
        "unique_intervals": int(len(unique)),
        "reuse_ratio": (total_refs / len(unique) if unique else None),
        "reuse_note": "重用比只是描述，不是有效样本数",
        "adjacent_definition": "相邻观察 = 完整交易日轴位置相差 1",
        "adjacent_pairs": adjacent_pairs,
        "adjacent_shared_mean": (shared_sum / adjacent_pairs
                                 if adjacent_pairs else None),
        "adjacent_shared_histogram": {str(k): v for k, v
                                      in sorted(adjacent_hist.items())},
        "adjacent_shared_ratio": ((shared_sum / adjacent_pairs) / per_label
                                  if adjacent_pairs and per_label else None),
        "sparse": {
            "anchor": anchor, "step": step,
            "grid_points": len(grid),
            "grid_policy": "只审计原规则锚点，不扫描其他起点选最好",
            "adjacent_pairs": len(sparse_shared),
            "adjacent_shared_max": max(sparse_shared) if sparse_shared else None,
            "note": ("锚点步长23的格点标签观察窗口不重叠（区间级）；"
                     "不重叠不等于统计独立"),
        },
    }
