"""状态—未来目标描述统计（factor_unit，B0，仅合成资料验证）。

只做历史描述统计：真/假两组的目标分布、无条件参照、逐年分列、连续状态段、
固定稀疏观察视角。不产生策略收益、年化、IC、统计显著性、风险调整α；
状态真假差异是历史关联，不是因果或可成交利润。

时间语义：目标窗口按**日历位置**定位——e=观察日在交易日时刻表上的第 e_offset 格、
x=第 x_offset 格；不按数据删行后的第几行计算。主目标端点缺失不顺延；
尾部不足单列 tail_immature；窗口内缺价 → 路径（辅助下行）目标缺失。
21 日未来窗口逐日滚动有重叠，不得当独立多次成功（输出固定标注）。

B0 边界：data_mode 必须 synthetic；真实模式未实现——这不是可放行开关，
传 real 会拒绝。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FIXED_OFFSETS = {"lookback": 20, "e_offset": 1, "x_offset": 22}


def _finite(x):
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def _stat(series: list[float]) -> dict:
    if not series:
        return {"n": 0, "mean": None, "median": None, "up_ratio": None}
    arr = np.asarray([v for v in series if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean": None, "median": None, "up_ratio": None}
    return {
        "n": int(arr.size),
        "mean": _finite(arr.mean()),
        "median": _finite(np.median(arr)),
        "up_ratio": _finite((arr > 0).mean()),
    }


def _validate_inputs(values: pd.DataFrame, schedule: pd.DataFrame, contract: dict) -> None:
    if contract.get("data_mode") != "synthetic":
        raise ValueError("B0 describe_states 仅接受 data_mode='synthetic'；真实模式未实现（不是放行开关）")
    for k, v in FIXED_OFFSETS.items():
        if contract.get(k, v) != v:
            raise ValueError(f"{k} 本轮固定为 {v}")
    if contract.get("object_ref") != "candidate:lei.dual_ma.bull_state@draft-1":
        raise ValueError("object_ref 必须是双均线候选")
    need = {"symbol", "session", "state", "I"}
    missing = need - set(values.columns)
    if missing:
        raise ValueError(f"values 缺字段: {sorted(missing)}")
    if not {"session", "close_at"}.issubset(schedule.columns):
        raise ValueError("schedule 需要 session/close_at 两列")
    sched_sessions = pd.to_datetime(schedule["session"])
    if not sched_sessions.is_unique or not sched_sessions.is_monotonic_increasing:
        raise ValueError("schedule.session 必须唯一递增")
    if schedule["close_at"].isna().any():
        raise ValueError("schedule.close_at 不得缺失（缺收盘时刻的日子不能当交易日格点）")
    for v in schedule["close_at"]:
        if pd.Timestamp(v).tzinfo is None:
            raise ValueError("close_at 必须带时区（无时区时刻拒绝）")


def describe_states(values: pd.DataFrame, schedule: pd.DataFrame, contract: dict) -> dict:
    """合成状态—目标描述。执行前验证完整合同与输入结构。"""
    _validate_inputs(values, schedule, contract)

    sched = pd.DataFrame({
        "session": pd.to_datetime(schedule["session"]).reset_index(drop=True),
        "close_at": pd.to_datetime(schedule["close_at"]).reset_index(drop=True),
    })
    session_pos = {s: i for i, s in enumerate(sched["session"])}
    e_off, x_off = FIXED_OFFSETS["e_offset"], FIXED_OFFSETS["x_offset"]
    anchor = int(contract.get("sparse_anchor_days", 23))

    v = values.copy()
    v["session"] = pd.to_datetime(v["session"])
    out_symbols: dict[str, dict] = {}
    missing_date_events: list[dict] = []

    for symbol, g in v.groupby("symbol"):
        per_day = g.set_index("session").sort_index()
        # 逐观察日定位目标
        rows = []
        for session, rec in per_day.iterrows():
            if session not in session_pos:
                missing_date_events.append({"symbol": symbol, "session": str(session.date()),
                                            "reason": "session_not_in_schedule"})
                continue
            pos = session_pos[session]
            state = rec["state"]
            state_b = None if pd.isna(state) else bool(state)
            row = {"session": session, "state": state_b, "main": None, "aux": None,
                   "target_reason": None}
            e_pos, x_pos = pos + e_off, pos + x_off
            if x_pos >= len(sched):
                row["target_reason"] = "tail_immature"
                rows.append(row)
                continue
            e_sess = sched["session"].iloc[e_pos]
            x_sess = sched["session"].iloc[x_pos]
            I_e, I_x = per_day["I"].get(e_sess, np.nan), per_day["I"].get(x_sess, np.nan)
            if pd.isna(I_e):
                row["target_reason"] = "e_missing"
                rows.append(row)
                continue
            if pd.isna(I_x):
                row["target_reason"] = "x_missing"
                rows.append(row)
                continue
            row["main"] = float(I_x) / float(I_e) - 1.0
            path_days = sched["session"].iloc[e_pos : x_pos + 1]
            path_I = [per_day["I"].get(s, np.nan) for s in path_days]
            if any(pd.isna(x) for x in path_I):
                row["target_reason"] = "path_missing"
            else:
                rel = [float(x) / float(I_e) - 1.0 for x in path_I]
                row["aux"] = min(0.0, min(rel))
            rows.append(row)

        frame = pd.DataFrame(rows)
        evaluable = frame.dropna(subset=["main"])
        true_main = evaluable.loc[evaluable["state"] == True, "main"].tolist()  # noqa: E712
        false_main = evaluable.loc[evaluable["state"] == False, "main"].tolist()  # noqa: E712
        true_aux = evaluable.loc[evaluable["state"] == True, "aux"].dropna().tolist()  # noqa: E712
        false_aux = evaluable.loc[evaluable["state"] == False, "aux"].dropna().tolist()  # noqa: E712

        def group_pack(main_list: list[float], aux_list: list[float]) -> dict:
            pack = _stat(main_list)
            aux_arr = np.asarray(aux_list, dtype=float) if aux_list else np.array([])
            pack["aux_mean"] = _finite(aux_arr.mean()) if aux_arr.size else None
            pack["aux_worst"] = _finite(aux_arr.min()) if aux_arr.size else None
            return pack

        # 逐年分列（观察年份）
        years: dict[str, dict] = {}
        if not evaluable.empty:
            ev = evaluable.copy()
            ev["year"] = ev["session"].dt.year
            for year, yg in ev.groupby("year"):
                years[str(int(year))] = {
                    "true": group_pack(yg.loc[yg["state"] == True, "main"].tolist(),  # noqa: E712
                                       yg.loc[yg["state"] == True, "aux"].dropna().tolist()),  # noqa: E712
                    "false": group_pack(yg.loc[yg["state"] == False, "main"].tolist(),  # noqa: E712
                                        yg.loc[yg["state"] == False, "aux"].dropna().tolist()),  # noqa: E712
                }
        # 观察出现过的年份都要出现（空年份 n=0）
        all_years = sorted({str(d.year) for d in per_day.index})
        for y in all_years:
            years.setdefault(y, {"true": {"n": 0, "mean": None, "median": None, "up_ratio": None,
                                          "aux_mean": None, "aux_worst": None},
                                 "false": {"n": 0, "mean": None, "median": None, "up_ratio": None,
                                           "aux_mean": None, "aux_worst": None}})

        # 连续状态段（state 未知不计入任何段，且会闭合当前段）
        states = frame["state"].tolist()
        seg_counts = {"true_segments": 0, "false_segments": 0, "longest_true": 0, "longest_false": 0}
        cur, run = None, 0

        def close_segment(cur, run):
            if cur is True:
                seg_counts["true_segments"] += 1
                seg_counts["longest_true"] = max(seg_counts["longest_true"], run)
            elif cur is False:
                seg_counts["false_segments"] += 1
                seg_counts["longest_false"] = max(seg_counts["longest_false"], run)

        for s in states:
            if s is None:
                close_segment(cur, run)
                cur, run = None, 0
                continue
            if s == cur:
                run += 1
            else:
                close_segment(cur, run)
                cur, run = s, 1
        close_segment(cur, run)

        # 固定稀疏观察视角：锚点=首个有已知状态的合法观察，之后每 anchor 个时刻表格点一格
        sparse_slots = []
        known = frame[frame["state"].notna()]
        if not known.empty:
            first_pos = session_pos[known["session"].iloc[0]]
            pos_map = {r["session"]: r for r in rows}
            p = first_pos
            while p < len(sched):
                sess = sched["session"].iloc[p]
                r = pos_map.get(sess)
                if r is not None and r["main"] is not None:
                    sparse_slots.append({"session": str(sess.date()), "state": r["state"],
                                         "main": _finite(r["main"]), "aux": _finite(r["aux"])})
                # 缺失/未就绪/未知状态的格跳过不补选，锚点不变
                p += anchor
        true_slots = [s for s in sparse_slots if s["state"] is True]
        false_slots = [s for s in sparse_slots if s["state"] is False]
        sparse_view = {
            "anchor_days": anchor,
            "note": "预先固定视角：锚点=首个可评价观察，每N个时刻表日一格；缺失格跳过不补选；仅作方向一致性描述",
            "slots": sparse_slots,
            "true_slots_up": int(sum(1 for s in true_slots if (s["main"] or 0) > 0)),
            "false_slots_down": int(sum(1 for s in false_slots if (s["main"] or 0) < 0)),
        }

        reason_counts = frame["target_reason"].value_counts(dropna=False).to_dict()
        out_symbols[str(symbol)] = {
            "observations": int(len(frame)),
            "state_true": int((frame["state"] == True).sum()),  # noqa: E712
            "state_false": int((frame["state"] == False).sum()),  # noqa: E712
            "state_unknown": int(frame["state"].isna().sum()),
            "target_missing": {str(k): int(v) for k, v in reason_counts.items() if k is not None},
            "tail_immature": int((frame["target_reason"] == "tail_immature").sum()),
            "unconditional": group_pack(evaluable["main"].tolist(), evaluable["aux"].dropna().tolist()),
            "true_group": group_pack(true_main, true_aux),
            "false_group": group_pack(false_main, false_aux),
            "by_year": years,
            "state_segments": seg_counts,
            "sparse_view": sparse_view,
        }

    return {
        "data_mode": "synthetic",
        "overlapping_windows": True,
        "overlap_note": "每日期滚动的21日未来窗口互相重叠，不得当作独立多次成功；状态真假差异是历史关联描述，不是因果或可成交利润",
        "no_claims": ["strategy_return", "annualization", "IC", "significance", "risk_adjusted_alpha"],
        "symbols": out_symbols,
        "session_not_in_schedule": missing_date_events,
    }
