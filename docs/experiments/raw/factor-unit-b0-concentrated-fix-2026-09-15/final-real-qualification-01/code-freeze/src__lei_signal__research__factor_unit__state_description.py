"""状态—未来目标描述统计（factor_unit，B0集中修复版，仅合成资料验证）。

R2 落地：显式消费完整合同（评价起止、带时区研究截止、每产品预定稀疏锚点、
步长固定23）；成熟按标签结束格点的**逐日 close_at** 与截止比较（同日盘前未
成熟、正好收盘成熟、收盘后成熟）；主比较只用共同合法集合（状态已知∧主目标
合法∧成熟），n_true+n_false=n_comparison；全资产背景单列不混称；辅助路径
缺失独立 aux_n。数据键唯一；state 只接受真布尔/空；I 只接受正有限或显式
缺失；时刻与 session 不匹配拒绝。空输入/全部日期在窗外返回结构化零计数，
不抛 KeyError。连续状态段按完整日程序列，缺整行或未知均断开；稀疏锚点来自
合同，不按第一个已知状态动态改选。

仍只描述合成关系：不加显著性、回归、策略收益；data_mode 必须 synthetic
（真实模式未实现，字符串换身份不放行）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FIXED_OFFSETS = {"lookback": 20, "e_offset": 1, "x_offset": 22}
SPARSE_STEP = 23
EMPTY_GROUP = {"n": 0, "mean": None, "median": None, "up_ratio": None,
               "aux_n": 0, "aux_mean": None, "aux_worst": None}


def _finite(x):
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def _stat(mains: list[float], auxs: list[float]) -> dict:
    if not mains:
        return dict(EMPTY_GROUP)
    arr = np.asarray(mains, dtype=float)
    aux_arr = np.asarray(auxs, dtype=float) if auxs else np.array([])
    return {
        "n": int(arr.size),
        "mean": _finite(arr.mean()),
        "median": _finite(np.median(arr)),
        "up_ratio": _finite((arr > 0).mean()),
        "aux_n": int(aux_arr.size),
        "aux_mean": _finite(aux_arr.mean()) if aux_arr.size else None,
        "aux_worst": _finite(aux_arr.min()) if aux_arr.size else None,
    }


def _close_segment(counts: dict, cur: bool | None, run: int) -> None:
    if cur is True:
        counts["true_segments"] += 1
        counts["longest_true"] = max(counts["longest_true"], run)
    elif cur is False:
        counts["false_segments"] += 1
        counts["longest_false"] = max(counts["longest_false"], run)


def _validate_contract(contract: dict) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    if contract.get("data_mode") != "synthetic":
        raise ValueError(
            "B0 describe_states 仅接受 data_mode='synthetic'；"
            "真实模式未实现（改字符串不构成真实身份，也不是放行开关）"
        )
    for k, v in FIXED_OFFSETS.items():
        if contract.get(k) != v:
            raise ValueError(f"{k} 必须显式等于 {v}（禁止默认掩盖漏声明）")
    if contract.get("object_ref") != "candidate:lei.dual_ma.bull_state@draft-1":
        raise ValueError("object_ref 必须是双均线候选")
    window = contract.get("evaluation_window") or {}
    if not (isinstance(window, dict) and bool(window.get("start")) and bool(window.get("end"))):
        raise ValueError("evaluation_window 必须显式给出 {start, end}")
    eval_start = pd.Timestamp(window["start"])
    eval_end = pd.Timestamp(window["end"])
    if eval_start > eval_end:
        raise ValueError("evaluation_window start 不得晚于 end")
    cutoff_raw = contract.get("research_cutoff")
    if not isinstance(cutoff_raw, str):
        raise ValueError("research_cutoff 必须显式给出（带时区ISO时刻）")
    cutoff = pd.Timestamp(cutoff_raw)
    if cutoff.tzinfo is None:
        raise ValueError("research_cutoff 必须带时区")
    anchors = contract.get("sparse_anchor_session")
    if not isinstance(anchors, dict) or not anchors:
        raise ValueError("sparse_anchor_session 必须显式给出每产品锚点（不允许动态选锚）")
    step = contract.get("sparse_step")
    if step != SPARSE_STEP:
        raise ValueError(f"sparse_step 固定为 {SPARSE_STEP}（0/负/1等一律拒绝）")
    return eval_start, eval_end, cutoff


def _validate_inputs(values: pd.DataFrame, schedule: pd.DataFrame,
                     anchors: dict, eval_start: pd.Timestamp,
                     eval_end: pd.Timestamp) -> dict:
    need = {"symbol", "session", "state", "I"}
    missing = need - set(values.columns)
    if missing:
        raise ValueError(f"values 缺字段: {sorted(missing)}")
    if not {"session", "close_at"}.issubset(schedule.columns):
        raise ValueError("schedule 需要 session/close_at 两列")
    sessions = pd.to_datetime(schedule["session"])
    if not sessions.is_unique or not sessions.is_monotonic_increasing:
        raise ValueError("schedule.session 必须唯一递增")
    parsed_close = [pd.Timestamp(v) for v in schedule["close_at"]]
    for i, ts in enumerate(parsed_close):
        if ts.tzinfo is None:
            raise ValueError("close_at 必须逐日带时区（无时区时刻拒绝）")
        if ts.date() != sessions[i].date():
            raise ValueError(
                f"close_at 日期与 session 不匹配（{sessions[i].date()}）"
            )
    if not values.empty:
        keys = list(zip(values["symbol"], pd.to_datetime(values["session"]), strict=True))
        if len(keys) != len(set(keys)):
            raise ValueError("(symbol, session) 必须唯一")
        for s in values["state"]:
            if s is not None and not isinstance(s, (bool, np.bool_)):
                raise ValueError(f"state 只接受真布尔或空（收到 {s!r}，"
                                 "字符串false/数字2都拒绝）")
        levels = pd.to_numeric(values["I"], errors="coerce")
        bad_I = levels.dropna()
        if ((bad_I <= 0) | ~np.isfinite(bad_I.astype(float))).any():
            raise ValueError("I 只接受正有限数值或显式缺失（0/负/无穷拒绝）")
        symbols = set(values["symbol"])
        absent = symbols - set(anchors)
        if absent:
            raise ValueError(f"sparse_anchor_session 缺产品锚点：{sorted(absent)}")
    in_window = (sessions >= eval_start) & (sessions <= eval_end)
    if not in_window.any():
        raise ValueError("日程在评价窗内没有任何格点（窗与日程不一致）")
    return {"session_pos": {s: i for i, s in enumerate(sessions)},
            "sched_sessions": sessions}


def describe_states(values: pd.DataFrame, schedule: pd.DataFrame, contract: dict) -> dict:
    """合成状态—目标描述；合同必填显式，输入严校，空集结构化零。"""
    eval_start, eval_end, cutoff = _validate_contract(contract)
    anchors = contract["sparse_anchor_session"]
    info = _validate_inputs(values, schedule, anchors, eval_start, eval_end)
    session_pos, sched_sessions = info["session_pos"], info["sched_sessions"]
    e_off, x_off = FIXED_OFFSETS["e_offset"], FIXED_OFFSETS["x_offset"]

    v = values.copy()
    v["session"] = pd.to_datetime(v["session"])
    close_map = dict(zip(sched_sessions, pd.to_datetime(schedule["close_at"]), strict=True))

    out_symbols: dict[str, dict] = {}
    if v.empty:
        return {
            "data_mode": "synthetic", "symbols": {},
            "overlap_note": "21日未来窗口互相重叠，不得当作独立多次成功",
            "no_claims": ["strategy_return", "annualization", "IC", "significance",
                          "risk_adjusted_alpha"],
        }

    for symbol, g in v.groupby("symbol"):
        per_day = g.set_index("session").sort_index()
        rows = []
        outside = 0
        for session, rec in per_day.iterrows():
            if session not in session_pos or not (eval_start <= session <= eval_end):
                outside += 1
                continue
            pos = session_pos[session]
            state = rec["state"]
            state_b = None if pd.isna(state) else bool(state)
            row = {"session": session, "state": state_b, "main": None,
                   "aux": None, "reason": None, "mature": False}
            x_pos = pos + x_off
            if x_pos >= len(sched_sessions):
                row["reason"] = "tail_immature"
                rows.append(row)
                continue
            e_sess = sched_sessions.iloc[pos + e_off]
            x_sess = sched_sessions.iloc[x_pos]
            x_close = pd.Timestamp(close_map[x_sess])
            level_e = per_day["I"].get(e_sess, np.nan)
            level_x = per_day["I"].get(x_sess, np.nan)
            if pd.isna(level_e):
                row["reason"] = "e_missing"
                rows.append(row)
                continue
            if pd.isna(level_x):
                row["reason"] = "x_missing"
                rows.append(row)
                continue
            row["main"] = float(level_x) / float(level_e) - 1.0
            path_days = sched_sessions.iloc[pos + e_off : x_pos + 1]
            path_I = [per_day["I"].get(s, np.nan) for s in path_days]
            if any(pd.isna(x) for x in path_I):
                row["reason"] = "path_missing"
            else:
                row["aux"] = min(0.0, min(float(x) / float(level_e) - 1.0 for x in path_I))
            # 成熟判定：标签结束格点的逐日 close_at 与截止比较
            row["mature"] = bool(x_close <= cutoff)
            rows.append(row)

        frame = pd.DataFrame(rows, columns=["session", "state", "main", "aux",
                                            "reason", "mature"])
        # 主比较共同集合 = 状态已知 ∧ 主目标合法 ∧ 成熟
        comp = frame[frame["mature"] & frame["main"].notna() & frame["state"].notna()]  # noqa: F841 保持集合定义可读
        # 全资产背景（含未知状态）单列，不与比较集混称
        background = frame[frame["mature"] & frame["main"].notna()]
        true_main = comp.loc[comp["state"] == True, "main"].tolist()  # noqa: E712
        false_main = comp.loc[comp["state"] == False, "main"].tolist()  # noqa: E712
        true_aux = comp.loc[comp["state"] == True, "aux"].dropna().tolist()  # noqa: E712
        false_aux = comp.loc[comp["state"] == False, "aux"].dropna().tolist()  # noqa: E712

        # 逐年分列（同一共同集合切年）
        years: dict[str, dict] = {}
        if not comp.empty:
            cv = comp.copy()
            cv["year"] = cv["session"].dt.year
            for year, yg in cv.groupby("year"):
                years[str(int(year))] = {
                    "true": _stat(yg.loc[yg["state"] == True, "main"].tolist(),  # noqa: E712
                                  yg.loc[yg["state"] == True, "aux"].dropna().tolist()),  # noqa: E712
                    "false": _stat(yg.loc[yg["state"] == False, "main"].tolist(),  # noqa: E712
                                   yg.loc[yg["state"] == False, "aux"].dropna().tolist()),  # noqa: E712
                }
        all_years = sorted({str(d.year) for d in per_day.index
                            if eval_start <= d <= eval_end})
        for y in all_years:
            years.setdefault(y, {"true": dict(EMPTY_GROUP), "false": dict(EMPTY_GROUP)})

        # 连续状态段：按完整日程序列（评价窗内），缺整行=未知=断开
        seg_counts = {"true_segments": 0, "false_segments": 0,
                      "longest_true": 0, "longest_false": 0}
        cur, run = None, 0
        state_by_session = dict(zip(frame["session"], frame["state"], strict=True))
        for sess in sched_sessions:
            if not (eval_start <= sess <= eval_end):
                continue
            s = state_by_session.get(sess)
            if s is None:
                _close_segment(seg_counts, cur, run)
                cur, run = None, 0
                continue
            if s == cur:
                run += 1
            else:
                _close_segment(seg_counts, cur, run)
                cur, run = s, 1
        _close_segment(seg_counts, cur, run)

        # 稀疏视角：锚点来自合同（预先固定），每23格点一格；未知/缺格跳过不顺延
        anchor_session = pd.Timestamp(anchors[str(symbol)])
        sparse_slots = []
        row_map = {r["session"]: r for r in rows}
        if anchor_session in session_pos:
            p = session_pos[anchor_session]
            while p < len(sched_sessions):
                sess = sched_sessions.iloc[p]
                r = row_map.get(sess)
                slot = {"session": str(sess.date()),
                        "state": None if r is None else r["state"],
                        "main": None if r is None else _finite(r["main"]),
                        "aux": None if r is None else _finite(r["aux"]),
                        "skipped": r is None or r["main"] is None}
                sparse_slots.append(slot)
                p += SPARSE_STEP
        true_up = sum(1 for s in sparse_slots
                      if s["state"] is True and not s["skipped"] and (s["main"] or 0) > 0)
        false_down = sum(1 for s in sparse_slots
                         if s["state"] is False and not s["skipped"] and (s["main"] or 0) < 0)

        reason_counts = frame["reason"].value_counts().to_dict()
        out_symbols[str(symbol)] = {
            "observations_in_window": int(len(frame)),
            "observations_outside_window": int(outside),
            "state_true": int((frame["state"] == True).sum()),  # noqa: E712
            "state_false": int((frame["state"] == False).sum()),  # noqa: E712
            "state_unknown": int(frame["state"].isna().sum()),
            "target_missing": {str(k): int(n) for k, n in reason_counts.items()},
            "tail_immature": int((frame["reason"] == "tail_immature").sum()),
            "comparison": {
                "n": int(len(comp)),
                "definition": "状态已知 ∧ 主目标合法 ∧ 标签收盘≤截止（共同合法集合）",
            },
            "true_group": _stat(true_main, true_aux),
            "false_group": _stat(false_main, false_aux),
            "background": {
                "n": int(len(background)),
                "n_unknown_state": int(background["state"].isna().sum()),
                "note": "全资产观察背景（含未知状态），与主比较不是同一集合，不混称",
                "stat": _stat(background["main"].tolist(),
                              background["aux"].dropna().tolist()),
            },
            "by_year": years,
            "state_segments": seg_counts,
            "sparse_view": {
                "anchor_session": str(anchor_session.date()),
                "step": SPARSE_STEP,
                "slots": sparse_slots,
                "true_slots_up": true_up,
                "false_slots_down": false_down,
                "note": "锚点来自合同预声明；未知/缺格跳过不顺延",
            },
        }

    return {
        "data_mode": "synthetic",
        "overlapping_windows": True,
        "overlap_note": "每日期滚动的21日未来窗口互相重叠，不得当作独立多次成功；"
                        "状态真假差异是历史关联描述，不是因果或可成交利润",
        "no_claims": ["strategy_return", "annualization", "IC", "significance",
                      "risk_adjusted_alpha"],
        "symbols": out_symbols,
    }
