"""状态—目标描述的公共纯计算（B1提取版，自 state_description 原样提取）。

本模块是从旧 ``state_description.describe_states`` 提取的**纯计算层**：
逐行目标构造、成熟判定、共同合法集合统计、逐年/连续段/稀疏视角。
它**没有输入许可概念**：core 不判断 real/synthetic 身份，"通过 core"不等于
任何用途合格。合成旧入口仍由 state_description 做 synthetic 校验与包装；
真实 B1 输入必须先通过 b1_contract 的严格资格检查，才允许调用本模块。

提取纪律：逻辑自旧实现逐行搬移，不重构不相关内容；旧 coerce 等已知宽松
行为不顺手改变（避免扩大旧行为修复范围）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

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


def _state_value(x):
    """统一状态表示：有效状态仅 bool/np.bool_；None/pd.NA/NaN 为未知。

    上游可空布尔（pd.BooleanDtype）的 pd.NA 原样接受为未知；字符串false、
    空字符串、数字0/1/2不自动转布尔，一律拒绝。在数值/布尔转换前识别标量
    缺失，不对 pd.NA 直接做真假判断；已知状态含义不变。
    """
    if x is None or x is pd.NA:
        return None
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, float) and np.isnan(x):
        return None
    raise ValueError(f"state 只接受真布尔或空（收到 {x!r}，"
                     "字符串false/数字2都拒绝）")


def _close_segment(counts: dict, cur: bool | None, run: int) -> None:
    if cur is True:
        counts["true_segments"] += 1
        counts["longest_true"] = max(counts["longest_true"], run)
    elif cur is False:
        counts["false_segments"] += 1
        counts["longest_false"] = max(counts["longest_false"], run)


def _schedule_sessions(schedule: pd.DataFrame):
    """日程结构核验与索引：session 唯一递增；close_at 逐日带时区且日期对应。"""
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
    session_pos = {s: i for i, s in enumerate(sessions)}
    close_map = dict(zip(sessions, parsed_close, strict=True))
    return sessions, session_pos, close_map


def build_observation_rows(values, schedule, *, eval_start, eval_end,
                           cutoff, e_offset, x_offset):
    """返回含 symbol/session/state/main/aux/mature/reason 的观察表及窗外计数。

    纯计算：不校验 data_mode/对象/参数身份（调用方责任）；state 经
    _state_value 统一；标签按交易日位置取端点（不用行压缩序号）；成熟按
    标签结束格点逐日 close_at ≤ cutoff。
    """
    sessions, session_pos, close_map = _schedule_sessions(schedule)
    v = values.copy()
    v["session"] = pd.to_datetime(v["session"])
    rows: list[dict] = []
    outside: dict[str, int] = {}
    for symbol, g in v.groupby("symbol"):
        per_day = g.set_index("session").sort_index()
        for session, rec in per_day.iterrows():
            if session not in session_pos or not (eval_start <= session <= eval_end):
                outside[str(symbol)] = outside.get(str(symbol), 0) + 1
                continue
            pos = session_pos[session]
            state_b = _state_value(rec["state"])
            row = {"symbol": str(symbol), "session": session, "state": state_b,
                   "main": None, "aux": None, "reason": None, "mature": False}
            x_pos = pos + x_offset
            if x_pos >= len(sessions):
                row["reason"] = "tail_immature"
                rows.append(row)
                continue
            e_sess = sessions.iloc[pos + e_offset]
            x_sess = sessions.iloc[x_pos]
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
            path_days = sessions.iloc[pos + e_offset : x_pos + 1]
            path_I = [per_day["I"].get(s, np.nan) for s in path_days]
            if any(pd.isna(x) for x in path_I):
                row["reason"] = "path_missing"
            else:
                row["aux"] = min(0.0, min(float(x) / float(level_e) - 1.0
                                          for x in path_I))
            # 成熟判定：标签结束格点的逐日 close_at 与截止比较
            row["mature"] = bool(x_close <= cutoff)
            rows.append(row)
    return {"rows": rows, "outside": outside}


def summarize_observation_rows(rows, values, schedule, *, eval_start,
                               eval_end, anchors, sparse_step):
    """返回每产品原B0统计结构；不授予用途，不内置real/synthetic身份。

    rows 为 build_observation_rows 的返回（观察表+窗外计数）。主比较只用
    共同合法集合（状态已知∧主目标合法∧成熟）；背景单列；稀疏格与主比较
    同一合法集合；锚点来自调用方预先固定，不顺延。
    """
    sessions, session_pos, _ = _schedule_sessions(schedule)
    obs_rows, outside = rows["rows"], rows["outside"]
    v = values.copy()
    v["session"] = pd.to_datetime(v["session"])
    per_day_by_symbol = {str(sym): g.set_index("session").sort_index()
                         for sym, g in v.groupby("symbol")}

    out_symbols: dict[str, dict] = {}
    rows_by_symbol: dict[str, list[dict]] = {}
    for r in obs_rows:
        rows_by_symbol.setdefault(r["symbol"], []).append(r)

    for symbol, per_day in per_day_by_symbol.items():
        sym_rows = rows_by_symbol.get(symbol, [])
        frame = pd.DataFrame(sym_rows,
                             columns=["session", "state", "main", "aux",
                                      "reason", "mature"])
        # 主比较共同集合 = 状态已知 ∧ 主目标合法 ∧ 成熟
        comp = frame[frame["mature"] & frame["main"].notna() & frame["state"].notna()]  # noqa: F841 保持集合定义可读
        # 全资产背景（含未知状态）单列，不与比较集混称
        background = frame[frame["mature"] & frame["main"].notna()]
        true_main = comp.loc[comp["state"] == True, "main"].tolist()  # noqa: E712
        false_main = comp.loc[comp["state"] == False, "main"].tolist()  # noqa: E712
        true_aux = comp.loc[comp["state"] == True, "aux"].dropna().tolist()  # noqa: E712
        false_aux = comp.loc[comp["state"] == False, "aux"].dropna().tolist()  # noqa: E712

        # 逐年分列（同一共同集合切年；按状态观察年，跨年目标归观察年）
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
        for sess in sessions:
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

        # 稀疏视角：锚点来自调用方（预先固定），每sparse_step格点一格；与主比较
        # 同一合法集合，不另写放宽条件；不合格格保留日期与skipped_reason，
        # main/aux置null，不展示成已可观察结果，不计true/false计数；辅助路径
        # 不全但主目标合法时主值保留，aux缺失由aux_n独立表达。
        anchor_session = pd.Timestamp(anchors[str(symbol)])
        sparse_slots = []
        row_map = {r["session"]: r for r in sym_rows}
        if anchor_session in session_pos:
            p = session_pos[anchor_session]
            while p < len(sessions):
                sess = sessions.iloc[p]
                r = row_map.get(sess)
                slot = {"session": str(sess.date()),
                        "state": None if r is None else r["state"],
                        "main": None, "aux": None,
                        "skipped": True, "skipped_reason": None}
                if r is None:
                    slot["skipped_reason"] = "missing_row"
                elif r["main"] is None:
                    slot["skipped_reason"] = r["reason"] or "target_missing"
                elif not r["mature"]:
                    slot["skipped_reason"] = "not_mature"
                elif r["state"] is None:
                    slot["skipped_reason"] = "state_unknown"
                else:
                    slot["skipped"] = False
                    slot["main"] = _finite(r["main"])
                    slot["aux"] = _finite(r["aux"])  # aux缺失独立表达，不拖累主值
                sparse_slots.append(slot)
                p += sparse_step
        true_up = sum(1 for s in sparse_slots
                      if not s["skipped"] and s["state"] is True and (s["main"] or 0) > 0)
        false_down = sum(1 for s in sparse_slots
                         if not s["skipped"] and s["state"] is False and (s["main"] or 0) < 0)
        sparse_aux_n = sum(1 for s in sparse_slots
                           if not s["skipped"] and s["aux"] is not None)

        reason_counts = frame["reason"].value_counts().to_dict()
        out_symbols[symbol] = {
            "observations_in_window": int(len(frame)),
            "observations_outside_window": int(outside.get(symbol, 0)),
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
                "step": sparse_step,
                "slots": sparse_slots,
                "true_slots_up": true_up,
                "false_slots_down": false_down,
                "aux_n": sparse_aux_n,
                "note": "锚点来自合同预声明；未知/缺格跳过不顺延；"
                        "与主比较同一合法集合，未成熟/未知不展示不记分",
            },
        }

    return out_symbols
