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
    """标签区间重叠审计（主控R2返修版）。

    主结果基于**共同合法集合**（legal 且有 e/x 端点）；非法行与缺端点行
    保留原日期轴位置、不删行（不让隔天冒充相邻交易日），只计入排除分类。
    另报 ``all_rows_with_endpoints``（所有有端点行，含非法行）——独立命名
    的诊断视角，不是有效研究观察集合，不得混称。
    稀疏锚点沿**原轴**推进（不从观察行集合推进）：应有格点、可审计格点、
    缺失原因（非法行/缺端点/缺行）分开输出；只审计原规则锚点，不扫描其他
    起点选最好。
    """
    days = schedule["session"].tolist()
    pos = {d: i for i, d in enumerate(days)}
    axis_positions = [i for i, w in enumerate(schedule["in_window"].tolist())
                      if w]
    f = _sorted_legal(frame)

    def _intervals(e: str, x: str) -> set[int]:
        # 区间以右端点位置标识：(s_{k-1}, s_k]，k ∈ (pos(e), pos(x)]
        return set(range(pos[e] + 1, pos[x] + 1))

    def _collect(selector) -> tuple[list[set[int]], list[int]]:
        label_sets, axis_pos = [], []
        for session, legal, e, x in zip(f["session"], f["legal"],
                                        f["e_date"], f["x_date"],
                                        strict=True):
            if not selector(legal, e, x):
                continue
            label_sets.append(_intervals(e, x))
            axis_pos.append(pos[session])
        return label_sets, axis_pos

    def _stats_for(label_sets: list[set[int]], axis_pos: list[int]) -> dict:
        total = sum(len(s) for s in label_sets)
        unique = set().union(*label_sets) if label_sets else set()
        by_pos = dict(zip(axis_pos, label_sets, strict=False))
        hist: dict[int, int] = {}
        pairs = 0
        ssum = 0
        for p in sorted(by_pos):
            if p + 1 in by_pos:
                shared = len(by_pos[p] & by_pos[p + 1])
                hist[shared] = hist.get(shared, 0) + 1
                pairs += 1
                ssum += shared
        per_label = len(label_sets[0]) if label_sets else None
        return {
            "rows_audited": len(label_sets),
            "per_label_intervals": per_label,
            "total_interval_refs": int(total),
            "unique_intervals": int(len(unique)),
            "reuse_ratio": (total / len(unique) if unique else None),
            "adjacent_pairs": pairs,
            "adjacent_shared_mean": (ssum / pairs if pairs else None),
            "adjacent_shared_histogram": {str(k): v for k, v
                                          in sorted(hist.items())},
            "adjacent_shared_ratio": ((ssum / pairs) / per_label
                                      if pairs and per_label else None),
        }

    def has_endpoints(e, x) -> bool:
        return isinstance(e, str) and isinstance(x, str)

    # 主结果＝共同合法集合（legal 且有端点）
    primary_sets, primary_pos = _collect(
        lambda legal, e, x: bool(legal) and has_endpoints(e, x))
    primary = _stats_for(primary_sets, primary_pos)
    illegal_excluded = sum(
        1 for session, legal, e, x in zip(f["session"], f["legal"],
                                          f["e_date"], f["x_date"],
                                          strict=True)
        if bool(legal) is False)
    legal_missing = sum(
        1 for legal, e, x in zip(f["legal"], f["e_date"], f["x_date"],
                                 strict=True)
        if bool(legal) is True and not has_endpoints(e, x))

    # 另报：所有有端点行（含非法行）——独立命名，不与主结果混称
    sec_sets, sec_pos = _collect(lambda legal, e, x: has_endpoints(e, x))
    secondary = {
        **_stats_for(sec_sets, sec_pos),
        "note": ("含非法行的所有有端点观察；只是诊断视角，"
                 "不是有效研究观察集合，不与主结果混称"),
    }

    # 稀疏锚点：沿原轴推进，分类应有/可审计/缺失原因
    anchor_pos = pos.get(anchor)
    reasons: dict[str, int] = {}
    auditable_grid: list[int] = []
    expected_points = 0
    row_index = {s: (lg, e, x)
                 for s, lg, e, x in zip(f["session"], f["legal"],
                                        f["e_date"], f["x_date"],
                                        strict=True)}
    if anchor_pos is not None:
        for p in axis_positions:
            if p < anchor_pos or (p - anchor_pos) % step != 0:
                continue
            expected_points += 1
            rec = row_index.get(days[p])
            if rec is None:
                reasons["missing_row"] = reasons.get("missing_row", 0) + 1
            elif bool(rec[0]) is False:
                reasons["illegal_row"] = reasons.get("illegal_row", 0) + 1
            elif not has_endpoints(rec[1], rec[2]):
                reasons["missing_endpoints"] = \
                    reasons.get("missing_endpoints", 0) + 1
            else:
                auditable_grid.append(p)
    grid_sets = [dict(zip(primary_pos, primary_sets, strict=False))[p]
                 for p in auditable_grid]
    sparse_shared = [len(a & b) for a, b in zip(grid_sets, grid_sets[1:],
                                               strict=False)]

    return {
        "interval_unit": ("相邻交易日的价格变动区间（按日程位置识别的相邻对）；"
                          "不是共同日期点数"),
        "primary_set": "共同合法集合（legal ∧ 有 e/x 端点）",
        "rows_audited": primary["rows_audited"],
        "illegal_rows_excluded": illegal_excluded,
        "legal_missing_endpoints": legal_missing,
        **{k: v for k, v in primary.items() if k != "rows_audited"},
        "reuse_note": "重用比只是描述，不是有效样本数",
        "adjacent_definition": "相邻观察 = 完整交易日轴位置相差 1（非法行保留原轴位置，不删行）",
        "all_rows_with_endpoints": secondary,
        "sparse": {
            "anchor": anchor, "step": step,
            "expected_points": expected_points,
            "auditable_points": len(auditable_grid),
            "reasons": reasons,
            "grid_policy": "锚点沿完整交易日轴推进；只审计原规则锚点，不扫描其他起点选最好",
            "adjacent_pairs": len(sparse_shared),
            "adjacent_shared_max": max(sparse_shared) if sparse_shared else None,
            "note": ("可审计格点间标签观察窗口不重叠（区间级）；"
                     "不重叠不等于统计独立"),
        },
    }
