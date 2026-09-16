"""B1 真实历史描述计算层（仅新入口；只由已通过资格的 CLI 调用）。

复用 close_state（生产公式，只用 close）与 description_core（公共纯计算），
不调用 describe_states、不冒用 synthetic 身份。返回 states / observations /
summary / quality 四部分；**计算与写盘分离**——本模块不写盘。

结果身份：post_hoc_historical_description；data_mode=real；
historical_reconstruction_only=true；无预测资格、无 PIT verified。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.research.factor_unit.close_state import compute_close_state
from lei_signal.research.factor_unit.description_core import (
    build_observation_rows,
    summarize_observation_rows,
)

RESULT_IDENTITY = "post_hoc_historical_description"
NO_CLAIMS = ["strategy_return", "annualization", "significance", "IC", "alpha",
             "production_advice", "factor_effective", "total_return_wealth",
             "point_in_time_verified"]


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _state_str(x):
    if x is None or x is pd.NA:
        return ""
    return "true" if bool(x) else "false"


def describe_b1(prices: pd.DataFrame, schedule: pd.DataFrame, contract: dict) -> dict:
    """对已通过资格的输入做真实历史描述。

    prices：DatetimeIndex + close（浮点，严格解析已在 b1_contract 完成）。
    schedule：session/close_at（包内日历逐日 15:00 Asia/Shanghai）。
    contract：validate_b1_protocol 返回的合同（测试可手工构造同字段）。
    """
    window = contract["evaluation_window"]
    eval_start, eval_end = pd.Timestamp(window["start"]), pd.Timestamp(window["end"])
    _require(eval_start <= eval_end, "evaluation_window start 不得晚于 end")
    cutoff = pd.Timestamp(contract["label_maturity_cutoff"])
    _require(cutoff.tzinfo is not None,
             "label_maturity_cutoff 必须带时区（无时区拒绝）")
    symbol = contract["symbol"]
    anchor = contract["sparse_anchor_session"]
    step = contract["sparse_step"]

    sessions = pd.to_datetime(schedule["session"])
    price_dates = pd.DatetimeIndex(prices.index)
    _require(len(price_dates) == len(sessions)
             and bool((price_dates == sessions).all()),
             "prices 与 schedule 必须逐日对齐（缺行/错位拒绝，不用压缩序号）")

    # 状态：完整共同确认调用生产函数（不用等价简式替代）；缺失准备不变 false
    calc = compute_close_state(prices["close"])
    values = pd.DataFrame({
        "symbol": symbol,
        "session": sessions,
        "state": calc["state"].array,
        "I": prices["close"].to_numpy(dtype=float),
    })

    built = build_observation_rows(
        values, schedule, eval_start=eval_start, eval_end=eval_end,
        cutoff=cutoff, e_offset=contract["e_offset"], x_offset=contract["x_offset"])
    core_summary = summarize_observation_rows(
        built, values, schedule, eval_start=eval_start, eval_end=eval_end,
        anchors={symbol: anchor}, sparse_step=step)

    # ── states 表（准备期如实标 missing_reason；布尔有明确 true/false/空） ──
    states = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in sessions],
        "close": prices["close"].to_numpy(dtype=float),
        "state": [_state_str(s) for s in calc["state"].array],
        "missing_reason": ["" if r is None or r is pd.NA else str(r)
                           for r in calc["missing_reason"].array],
    })

    # ── observations 表（含 e/x 日期、成熟时刻、分组资格、排除原因） ──
    session_pos = {s: i for i, s in enumerate(sessions)}
    e_off, x_off = contract["e_offset"], contract["x_offset"]
    obs_records = []
    for r in built["rows"]:
        pos = session_pos[r["session"]]
        e_sess = sessions.iloc[pos + e_off] if pos + e_off < len(sessions) else None
        x_sess = sessions.iloc[pos + x_off] if pos + x_off < len(sessions) else None
        state_known = r["state"] is not None
        main_legal = r["main"] is not None
        in_comp = bool(r["mature"] and main_legal and state_known)
        if in_comp:
            primary = ""
        elif not state_known:
            primary = "state_unknown"
        elif not main_legal:
            primary = r["reason"] or "target_missing"
        else:
            primary = "not_mature"
        obs_records.append({
            "session": r["session"].strftime("%Y-%m-%d"),
            "state": _state_str(r["state"]),
            "e_date": "" if e_sess is None else e_sess.strftime("%Y-%m-%d"),
            "x_date": "" if x_sess is None else x_sess.strftime("%Y-%m-%d"),
            "main": r["main"],
            "aux": r["aux"],
            "mature": bool(r["mature"]),
            "reason": r["reason"] or "",
            "flag_state_known": state_known,
            "flag_main_legal": main_legal,
            "flag_mature": bool(r["mature"]),
            "in_comparison": in_comp,
            "primary_exclusion": primary,
        })
    observations = pd.DataFrame(obs_records)

    # ── B1 稀疏输出层：窗外独立标 out_of_evaluation_window（F1）；
    #    有效真/假组各报总数与上涨/下跌/零变化（F3，三者相加=组n） ──
    sym_summary = core_summary[symbol]
    sparse = dict(sym_summary["sparse_view"])
    slots = []
    for s in sparse["slots"]:
        s = dict(s)
        sess = pd.Timestamp(s["session"])
        if not (eval_start <= sess <= eval_end):
            s["skipped"] = True
            s["skipped_reason"] = "out_of_evaluation_window"
            s["main"] = None
            s["aux"] = None
        slots.append(s)
    groups = {}
    for want, label in ((True, "true"), (False, "false")):
        valid = [s for s in slots if not s["skipped"] and s["state"] is want]
        up = sum(1 for s in valid if s["main"] > 0)
        down = sum(1 for s in valid if s["main"] < 0)
        zero = sum(1 for s in valid if s["main"] == 0)
        groups[label] = {"n": len(valid), "up": up, "down": down, "zero": zero}
    sparse["slots"] = slots
    sparse["groups"] = groups
    sparse["group_note"] = ("有效真/假组分别报总数与上涨/下跌/零变化（严格>0/<0/=0），"
                            "三者相加等于该组n；无分母不报比例")
    sym_summary["sparse_view"] = sparse
    sym_summary["by_year_note"] = "按状态观察年分组，跨年目标归观察年，不当作自然年度收益"

    # ── 对账（两种分母分开：可重叠标记 vs 互斥主要排除原因） ──
    in_window = int(len(observations))
    n_true = int((observations["state"] == "true").sum())
    n_false = int((observations["state"] == "false").sum())
    n_unknown = int((observations["state"] == "").sum())
    n_comp = int(observations["in_comparison"].sum())
    comp_true = int((observations["in_comparison"] & (observations["state"] == "true")).sum())
    comp_false = int((observations["in_comparison"] & (observations["state"] == "false")).sum())
    excl = observations.loc[~observations["in_comparison"], "primary_exclusion"]
    primary_exclusion_counts = {str(k): int(v) for k, v in excl.value_counts().items()}
    warmup = int(contract["warmup_sessions"])
    reconciliation = {
        "observations_in_eval_window": in_window,
        "state_true": n_true, "state_false": n_false, "state_unknown": n_unknown,
        "states_sum_equals_window": n_true + n_false + n_unknown == in_window,
        "comparison_n": n_comp,
        "comparison_true": comp_true, "comparison_false": comp_false,
        "true_plus_false_equals_comparison": comp_true + comp_false == n_comp,
        "flag_counts_overlapping": {
            "state_known": int(observations["flag_state_known"].sum()),
            "main_legal": int(observations["flag_main_legal"].sum()),
            "mature": int(observations["flag_mature"].sum()),
            "note": "可重叠标记，只作标记，不得相加冒充剔除人数",
        },
        "primary_exclusion_counts": primary_exclusion_counts,
        "primary_exclusion_note": "互斥主要排除原因；与in_comparison相加等于窗内观察数",
        "exclusion_plus_comparison_equals_window":
            int(sum(primary_exclusion_counts.values())) + n_comp == in_window,
        "outside_window_rows": int(sum(built["outside"].values())),
        "warmup_sessions_before_window": warmup,
        "warmup_note": "准备期20行在评价窗前单列，不伪称评价窗内未知20行",
        "sparse_true_group_sum": groups["true"]["up"] + groups["true"]["down"]
                                 + groups["true"]["zero"] == groups["true"]["n"],
        "sparse_false_group_sum": groups["false"]["up"] + groups["false"]["down"]
                                  + groups["false"]["zero"] == groups["false"]["n"],
    }

    quality = {
        "result_identity": RESULT_IDENTITY,
        "data_mode": contract["data_mode"],
        "historical_reconstruction_only": contract["historical_reconstruction_only"],
        "historical_available_at": None,
        "adjustment_anchor": contract["adjustment_anchor"],
        "object_ref": contract["object_ref"],
        "symbol": symbol,
        "target_basis": contract["target_basis"],
        "target_main": contract["target_main"],
        "target_aux": contract["target_aux"],
        "target_note": "21个变动区间，不是22段；aux是相对起点最差收盘变化，"
                       "不是最高点到最低点回撤",
        "vendor_wealth_note": "供应商调整价与含分红财富等价性未核；不加现金分红、"
                              "不重复复权，不声称已获得真实成交利润",
        "knowledge_time_note": "输入快照2026-09-08取回；成熟截止2026-02-03T15:00+08"
                               "是标签窗口截断，不是2月已拥有9月快照的证明",
        "reconciliation": reconciliation,
        "no_claims": NO_CLAIMS,
    }
    summary = {
        "result_identity": RESULT_IDENTITY,
        "symbols": {symbol: sym_summary},
        "overlap_note": "相邻日期的21日未来窗口互相重叠，不得当作多次独立成功；"
                        "状态真假差异是历史关联描述，不是因果或可成交利润",
    }
    return {"states": states, "observations": observations,
            "summary": summary, "quality": quality}
